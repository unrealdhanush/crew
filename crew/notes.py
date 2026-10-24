"""Notes from the floor: a two-line note becomes cited, linked team knowledge."""
import re
import uuid

from . import llm, web
from . import graph as G
from .ingest import known_names, norm_pkg, norm_topic
from .planner import resolve_session
from .queries import ripple

URL_RE = re.compile(r"https?://[^\s)>\]]+")

NOTE_PROMPT = """A teammate wrote a short note during a conference session. Extract:
{"packages": [libraries/tools/products mentioned, lowercase],
 "topics": [2-4 short lowercase tags],
 "breaking": [{"package": str, "summary": str}]  // only announced breaking changes, deprecations or migrations
 "lookups": [up to 2 web search queries that would find the official docs, release notes or repo for what was mentioned]}
Prefer these existing package names when they fit: {packages}"""

SUMMARY_PROMPT = """Summarize what this page says that matters for the teammate's note, in at most 3 short bullet
points of plain facts (versions, dates, what changed). If the page is irrelevant, return {"summary": ""}.
Return {"summary": str}."""


def _write_source(nid: str, url: str, note_text: str) -> dict | None:
    try:
        page = web.fetch_markdown(url)
    except web.WebError as exc:
        return {"url": url, "error": str(exc)}
    title = web.page_title(page["markdown"], url)
    summary = llm.json_call(
        SUMMARY_PROMPT,
        f"<user_note>{note_text}</user_note>\n{web.wrap_untrusted(page['markdown'], limit=12000)}",
    ).get("summary", "")
    if isinstance(summary, list):
        summary = "\n".join(map(str, summary))
    G.q(
        "MATCH (n:Note {nid: $nid}) "
        "MERGE (src:Source {url: $url}) SET src.title = $title, src.summary = $summary, src.fetched_at = $at "
        "MERGE (n)-[c:CITES]->(src) SET c.fetched_at = $at",
        {"nid": nid, "url": url, "title": title, "summary": summary, "at": page["fetched_at"]},
    )
    return {"url": url, "title": title, "summary": summary, "fetched_at": page["fetched_at"], "cached": page["cached"]}


def note_paths(nid: str) -> list[dict]:
    """Author -> note -> everything the note links to (session, packages, topics, sources)."""
    rows = G.rows("MATCH path = (:Person)-[:WROTE]->(:Note {nid: $nid})-[]->() RETURN path", {"nid": nid}) or G.rows(
        "MATCH path = (:Person)-[:WROTE]->(:Note {nid: $nid}) RETURN path", {"nid": nid}
    )
    return [G.path_json(r[0]) for r in rows]


def add_note(handle: str, text: str, session_ref: str | None = None, max_sources: int = 3) -> dict:
    handle = handle.lower()
    if not G.rows("MATCH (p:Person {handle: $h}) RETURN p.handle", {"h": handle}):
        return {"error": f"Unknown teammate '{handle}'"}
    session = resolve_session(session_ref) if session_ref else None
    nid = uuid.uuid4().hex[:10]
    G.q(
        "MATCH (p:Person {handle: $h}) "
        "CREATE (n:Note {nid: $nid, text: $text, created_at: $at}) CREATE (p)-[:WROTE]->(n)",
        {"h": handle, "nid": nid, "text": text, "at": web.now_iso()},
    )
    if session:
        G.q(
            "MATCH (n:Note {nid: $nid}), (s:Session {sid: $sid}) CREATE (n)-[:ABOUT]->(s)",
            {"nid": nid, "sid": session["sid"]},
        )

    facts = llm.json_call(
        NOTE_PROMPT.replace("{packages}", ", ".join(known_names("Package"))),
        f"<user_note>{text}</user_note>",
    )
    packages = sorted({norm_pkg(p) for p in facts.get("packages", []) if norm_pkg(p)})
    topics = sorted({norm_topic(t) for t in facts.get("topics", []) if norm_topic(t)})
    G.q(
        "MATCH (n:Note {nid: $nid}) UNWIND $pkgs AS p MERGE (k:Package {name: p}) MERGE (n)-[:MENTIONS]->(k)",
        {"nid": nid, "pkgs": packages},
    )
    G.q(
        "MATCH (n:Note {nid: $nid}) UNWIND $topics AS t MERGE (x:Topic {name: t}) MERGE (n)-[:ABOUT_TOPIC]->(x)",
        {"nid": nid, "topics": topics},
    )

    # Live enrichment: links in the note first, otherwise search for the official source.
    urls = URL_RE.findall(text)
    if not urls:
        for query in facts.get("lookups", [])[:2]:
            try:
                results = web.search(query, n=1)
            except web.WebError:
                results = []
            if results:
                urls.append(results[0]["link"])
    sources = [_write_source(nid, u, text) for u in list(dict.fromkeys(urls))[:max_sources]]

    ripples = [ripple(b["package"]) | {"summary": b.get("summary", "")} for b in facts.get("breaking", []) if b.get("package")]
    if not ripples:  # ripple() already lit up the affected repos
        G.highlight(f"New note from {handle}", note_paths(nid))
    return {
        "note_id": nid,
        "session": session["title"] if session else None,
        "packages": packages,
        "topics": topics,
        "sources": sources,
        "breaking_changes": ripples,
    }
