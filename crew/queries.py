"""The two queries only a graph answers: blind spots and ripple."""
from . import graph as G
from .ingest import norm_pkg


def blind_spots(limit: int = 15) -> dict:
    """Sessions about something our code depends on that nobody on the team is assigned to,
    plus dependencies Universe doesn't cover at all (no path = proof, not a guess)."""
    rows = G.rows(
        "MATCH path = (o:Person)-[:OWNS]->(r:Repo)-[:DEPENDS_ON]->(k:Package)<-[:MENTIONS]-(s:Session) "
        "OPTIONAL MATCH (s)<-[a:ASSIGNED_TO]-(:Person) "
        "WITH path, s, k, r, o, a WHERE a IS NULL "
        "RETURN path, s.title, s.start, k.name, r.full_name, o.handle "
        f"ORDER BY s.start LIMIT {int(limit)}"
    )
    paths = [G.path_json(r[0]) for r in rows]
    uncovered = [
        {"session": r[1], "start": r[2], "package": r[3], "repo": r[4], "owner": r[5], "path": p["text"]}
        for r, p in zip(rows, paths)
    ]
    dark = G.rows(
        "MATCH (r:Repo)-[d:DEPENDS_ON]->(k:Package) WHERE NOT coalesce(d.dev, false) "
        "OPTIONAL MATCH (k)<-[m:MENTIONS]-(:Session) "
        "WITH k, collect(DISTINCT r.full_name) AS repos, count(m) AS mentions "
        "WHERE mentions = 0 RETURN k.name, repos ORDER BY size(repos) DESC, k.name LIMIT 10"
    )
    G.highlight("Blind spots: our dependencies on stage with nobody assigned", paths)
    return {
        "unassigned_sessions_touching_our_code": uncovered,
        "dependencies_not_covered_at_conference": [{"package": r[0], "repos": r[1]} for r in dark],
    }


def bridges() -> list[dict]:
    """The shared nodes where the team's code or goals meet the agenda: every plan reason passes through one."""
    rows = G.rows(
        "MATCH (:Repo)-[:DEPENDS_ON]->(k:Package)<-[:MENTIONS]-(:Session) RETURN DISTINCT 'package' AS kind, k.name AS name "
        "UNION MATCH (:Repo)-[:TAGGED]->(t:Topic)<-[:COVERS]-(:Session) RETURN DISTINCT 'topic' AS kind, t.name AS name "
        "UNION MATCH (:Person)-[:INTERESTED_IN]->(t:Topic)<-[:COVERS]-(:Session) RETURN DISTINCT 'topic' AS kind, t.name AS name"
    )
    kinds: dict[str, str] = {}
    for kind, name in rows:  # a name can bridge as both; the package (dependency) link is the stronger one
        if kinds.get(name) != "package":
            kinds[name] = kind
    return [{"kind": kind, "name": name} for name, kind in sorted(kinds.items(), key=lambda x: (x[1] != "package", x[0]))]


def stats() -> dict:
    counts = {
        label.lower() + "s": G.rows(f"MATCH (n:{label}) RETURN count(n)")[0][0]
        for label in ("Person", "Repo", "Package", "Session", "Note")
    }
    return counts | {"bridges": len(bridges())}


def ripple(package: str) -> dict:
    """A change in `package` was announced: which of our repos are affected, who owns them, and what's the evidence."""
    name = norm_pkg(package)
    impact = G.rows(
        "MATCH path = (k:Package {name: $pkg})<-[:DEPENDS_ON]-(r:Repo)<-[:OWNS]-(o:Person) "
        "RETURN path, r.full_name, o.handle",
        {"pkg": name},
    )
    evidence = G.rows(
        "MATCH path = (w:Person)-[:WROTE]->(n:Note)-[:MENTIONS]->(k:Package {name: $pkg}) "
        "OPTIONAL MATCH (n)-[:CITES]->(src:Source) "
        "WITH path, n, collect(src.url) AS urls "
        "RETURN path, n.text, urls ORDER BY n.created_at DESC LIMIT 3",
        {"pkg": name},
    )
    sessions = G.rows(
        "MATCH path = (s:Session)-[:MENTIONS]->(k:Package {name: $pkg}) RETURN path, s.title LIMIT 3",
        {"pkg": name},
    )
    paths = [G.path_json(r[0]) for r in impact + evidence + sessions]
    G.highlight(f"Ripple: {name}", paths)
    affected: dict[str, list[str]] = {}
    for _, repo, owner in impact:
        affected.setdefault(owner, []).append(repo)
    return {
        "package": name,
        "affected": [{"owner": o, "repos": sorted(set(r))} for o, r in affected.items()],
        "evidence_notes": [{"note": r[1], "sources": r[2]} for r in evidence],
        "sessions": [r[1] for r in sessions],
        "paths": [p["text"] for p in paths],
        "verdict": "No repo of ours depends on it." if not impact else f"{len(affected)} owner(s) need to check this.",
    }


def readonly_cypher(cypher: str, limit: int = 50) -> dict:
    """Escape hatch for the agent: run a read-only query (writes are rejected by FalkorDB's ro_query)."""
    res = G.ro(cypher)
    header = [h[1] if isinstance(h, (list, tuple)) else str(h) for h in (res.header or [])]
    out = []
    for row in (res.result_set or [])[:limit]:
        out.append([
            G.node_json(v)["name"] if hasattr(v, "labels") else
            G.path_json(v)["text"] if hasattr(v, "nodes") else
            v
            for v in row
        ])
    return {"columns": header, "rows": out}
