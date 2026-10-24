"""Crew Scout: reads each repo's README and the team's stated goals, and maps them onto the agenda's topics.

Dependencies say what code is exposed to; Scout adds what the code is about and what people want to learn.
The judgment runs in a TrueForge agent through the MCP tools in server.py (team_repos, repo_profile, tag_repo,
map_goals). `auto_tag` does the same job with a direct model call when TrueForge isn't running.
Every result is a graph edge with its evidence, so plan reasons stay paths: '<repo> -TAGGED-> agents' (via README).
"""
import json
import re

from . import llm, web
from . import graph as G
from .ingest import fetch_readme, norm_topic

MAX_TOPICS = 6
_MARKUP = re.compile(r"[`*_#>\[\]()|]")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img[^>]*>|<picture.*?</picture>", re.S | re.I)


def _quiet(message: str, level: str = "info") -> None:
    pass


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", _MARKUP.sub("", text or "")).strip().lower()


def readme_excerpt(full_name: str, limit: int = 4000) -> str:
    return _IMAGE.sub("", fetch_readme(full_name))[:limit].strip()


def agenda_topics() -> list[str]:
    return [r[0] for r in G.rows("MATCH (:Session)-[:COVERS]->(t:Topic) RETURN DISTINCT t.name ORDER BY t.name")]


def team_repos() -> dict:
    """Repos (GitHub only: uploads have no README) and people, with whether Scout has been through them."""
    repos = G.rows(
        "MATCH (p:Person)-[:OWNS]->(r:Repo) WHERE NOT r.full_name STARTS WITH 'local:' "
        "OPTIONAL MATCH (r)-[e:TAGGED {via: 'readme'}]->() "
        "RETURN p.handle, r.full_name, r.description, count(e) ORDER BY p.handle, r.full_name"
    )
    people = G.rows(
        "MATCH (p:Person) OPTIONAL MATCH (p)-[e:INTERESTED_IN {via: 'scout'}]->() "
        "RETURN p.handle, p.goals_text, count(e) ORDER BY p.handle"
    )
    return {
        "repos": [{"owner": h, "repo": r, "description": d or "", "profiled": n > 0} for h, r, d, n in repos],
        "people": [{"handle": h, "goals": g or "", "mapped": n > 0} for h, g, n in people],
        "agenda_topics": agenda_topics(),
    }


def repo_profile(full_name: str) -> dict:
    found = G.rows(
        "MATCH (p:Person)-[:OWNS]->(r:Repo {full_name: $r}) RETURN p.handle, p.goals_text, r.description, r.language",
        {"r": full_name},
    )
    if not found:
        return {"error": f"Not a repo on the team: {full_name}"}
    owner, goals, description, language = found[0]
    deps = [r[0] for r in G.rows(
        "MATCH (:Repo {full_name: $r})-[d:DEPENDS_ON]->(k:Package) WHERE NOT coalesce(d.dev, false) "
        "RETURN k.name ORDER BY k.name LIMIT 40", {"r": full_name})]
    readme = readme_excerpt(full_name)
    return {
        "repo": full_name,
        "owner": owner,
        "owner_goals": goals or "",
        "description": description or "",
        "language": language or "",
        "dependencies": deps,
        "has_readme": bool(readme),
        "readme": web.wrap_untrusted(readme) if readme else "",
        "agenda_topics": agenda_topics(),
    }


def _clean_topics(topics) -> list[str]:
    out = []
    for t in topics or []:
        name = norm_topic(str(t))
        if name and len(name) <= 40 and name not in out:
            out.append(name)
    return out[:MAX_TOPICS]


def _light_up(title: str, cypher: str, params: dict) -> list[str]:
    paths = [G.path_json(r[0]) for r in G.rows(cypher, params)]
    if paths:
        G.highlight(title, paths)
    return [p["text"] for p in paths]


def valid_evidence(quote: str, readme: str) -> bool:
    """A real sentence (5+ words, not just a heading) that appears in the README."""
    plain = _plain(quote)
    return 10 <= len(quote) <= 300 and len(plain.split()) >= 5 and plain in _plain(readme)


def tag_repo(full_name: str, topics: list[str], evidence: str) -> dict:
    """Write README-derived topics for a repo. `evidence` must be copied from the README, so every tag can be
    shown with the sentence that justifies it."""
    if not G.rows("MATCH (r:Repo {full_name: $r}) RETURN r.full_name", {"r": full_name}):
        return {"error": f"Not a repo on the team: {full_name}"}
    names = _clean_topics(topics)
    if not names:
        return {"error": "Give 1-6 topics"}
    quote = (evidence or "").strip()
    if not valid_evidence(quote, readme_excerpt(full_name, limit=20000)):
        return {"error": "evidence must be a full sentence (5+ words, not a heading) copied from the README"}
    G.q(
        "MATCH (r:Repo {full_name: $r}) UNWIND $topics AS t MERGE (x:Topic {name: t}) "
        "MERGE (r)-[e:TAGGED]->(x) ON CREATE SET e.via = 'readme', e.evidence = $quote",
        {"r": full_name, "topics": names, "quote": quote[:300]},
    )
    paths = _light_up(
        f"Scout read {full_name}",
        "MATCH path = (:Person)-[:OWNS]->(:Repo {full_name: $r})-[:TAGGED]->(t:Topic)<-[:COVERS]-(:Session) "
        "WHERE t.name IN $topics RETURN path LIMIT 8",
        {"r": full_name, "topics": names},
    )
    return {"repo": full_name, "tagged": names, "evidence": quote, "new_paths_to_sessions": paths}


def map_goals(handle: str, topics: list[str]) -> dict:
    """Link a teammate to topics that capture their stated goals (read with team_repos)."""
    handle = (handle or "").lower()
    found = G.rows("MATCH (p:Person {handle: $h}) RETURN p.goals_text", {"h": handle})
    if not found:
        return {"error": f"Unknown teammate '{handle}'"}
    names = _clean_topics(topics)
    if not names:
        return {"error": "Give 1-6 topics"}
    G.q(
        "MATCH (p:Person {handle: $h}) UNWIND $topics AS t MERGE (x:Topic {name: t}) "
        "MERGE (p)-[e:INTERESTED_IN]->(x) ON CREATE SET e.via = 'scout', e.evidence = $said",
        {"h": handle, "topics": names, "said": found[0][0] or ""},
    )
    paths = _light_up(
        f"Scout mapped {handle}'s goals",
        "MATCH path = (:Person {handle: $h})-[:INTERESTED_IN]->(t:Topic)<-[:COVERS]-(:Session) "
        "WHERE t.name IN $topics RETURN path LIMIT 8",
        {"h": handle, "topics": names},
    )
    return {"handle": handle, "mapped": names, "new_paths_to_sessions": paths}


# ---------- the same job without TrueForge: one direct model call per repo / person ----------

REPO_PROMPT = """You are Crew Scout. From a repo's profile, choose 2-6 topics for what the repo is about.
Use names from agenda_topics whenever they fit; otherwise short lowercase tags. Copy one full sentence (not a
heading or title) from the README, exactly as written, as evidence. Return {"topics": [str], "evidence": str}."""

GOALS_PROMPT = """You are Crew Scout. Map a teammate's stated conference goals to 1-6 topics.
Use names from agenda_topics whenever they fit; otherwise short lowercase tags. Return {"topics": [str]}."""


def auto_tag(progress=_quiet) -> dict:
    done = {"repos": 0, "people": 0}
    state = team_repos()
    for row in state["repos"]:
        if row["profiled"]:
            continue
        profile = repo_profile(row["repo"])
        if len(_plain(readme_excerpt(row["repo"])).split()) < 5:  # nothing to quote: don't spend model calls
            progress(f"{row['repo']}: README has no sentences to quote, skipped")
            continue
        progress(f"Scout reading {row['repo']}'s README")
        answer = llm.json_call(REPO_PROMPT, json.dumps(profile))
        result = tag_repo(row["repo"], answer.get("topics"), answer.get("evidence", ""))
        if result.get("error"):  # one retry with the reason, like the TrueForge agent is told to do
            retry = dict(profile, previous_answer=answer, rejected_because=result["error"])
            answer = llm.json_call(REPO_PROMPT, json.dumps(retry))
            result = tag_repo(row["repo"], answer.get("topics"), answer.get("evidence", ""))
        if result.get("error"):
            progress(f"{row['repo']}: {result['error']}", "warn")
        else:
            done["repos"] += 1
            progress(f"{row['repo']} is about {', '.join(result['tagged'])}")
    for person in state["people"]:
        if person["mapped"] or not person["goals"]:
            continue
        answer = llm.json_call(GOALS_PROMPT, json.dumps({"goals": person["goals"], "agenda_topics": state["agenda_topics"]}))
        result = map_goals(person["handle"], answer.get("topics"))
        if not result.get("error"):
            done["people"] += 1
            progress(f"{person['handle']}'s goals → {', '.join(result['mapped'])}")
    return done
