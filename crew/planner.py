"""Team coverage: who goes to which session so the team's code is covered, with a reason path for each pick."""
from collections import defaultdict

from . import graph as G

# Why a session matters to a person, strongest first.
EVIDENCE_QUERIES = [
    (
        3.0,
        "dependency",
        "MATCH (p:Person)-[:OWNS]->(r:Repo)-[:DEPENDS_ON]->(k:Package)<-[:MENTIONS]-(s:Session) "
        "RETURN p.handle, s.sid, k.name, r.full_name",
        "{repo} depends on {via}",
    ),
    (
        2.0,
        "repo topic",
        "MATCH (p:Person)-[:OWNS]->(r:Repo)-[e:TAGGED]->(t:Topic)<-[:COVERS]-(s:Session) WHERE e.via IS NULL "
        "RETURN p.handle, s.sid, t.name, r.full_name",
        "{repo} is about {via}",
    ),
    (
        1.5,
        "readme topic",  # inferred by Crew Scout, with a README quote on the edge
        "MATCH (p:Person)-[:OWNS]->(r:Repo)-[e:TAGGED {via: 'readme'}]->(t:Topic)<-[:COVERS]-(s:Session) "
        "RETURN p.handle, s.sid, t.name, r.full_name",
        "{repo}'s README is about {via}",
    ),
    (
        1.0,
        "goal",
        "MATCH (p:Person)-[:INTERESTED_IN]->(t:Topic)<-[:COVERS]-(s:Session) "
        "RETURN p.handle, s.sid, t.name, ''",
        "goal: {via}",
    ),
]


def gather_evidence() -> tuple[dict, dict]:
    """Returns (person_scores[(handle, sid)] -> {score, reasons}, session_value[sid] -> float)."""
    scores: dict = defaultdict(lambda: {"score": 0.0, "reasons": []})
    team_items: dict = defaultdict(set)  # sid -> distinct (kind, via, repo) across the team
    for weight, kind, cypher, template in EVIDENCE_QUERIES:
        for handle, sid, via, repo in G.rows(cypher):
            entry = scores[(handle, sid)]
            reason = template.format(repo=repo, via=via)
            if reason not in entry["reasons"]:
                entry["score"] += weight
                entry["reasons"].append(reason)
            team_items[sid].add((weight, via, repo))
    value = {sid: sum(w for w, _, _ in items) for sid, items in team_items.items()}
    return dict(scores), value


def overlaps(a: dict, b: dict) -> bool:
    if None in (a.get("start_min"), a.get("end_min"), b.get("start_min"), b.get("end_min")):
        return False
    return a["start_min"] < b["end_min"] and b["start_min"] < a["end_min"]


def plan(people: list[str], sessions: list[dict], scores: dict, max_per_person: int | None = None):
    """Greedy coverage: most valuable sessions first, each to the free person it matters most to.

    sessions: [{sid, start_min, end_min, value}]; scores: {(handle, sid): float}.
    Returns (assignments {sid: handle}, uncovered [sid]) where uncovered = valuable but everyone was busy.
    """
    taken: dict[str, list[dict]] = {h: [] for h in people}
    assignments: dict[str, str] = {}
    uncovered: list[str] = []
    ordered = sorted(sessions, key=lambda s: (-s.get("value", 0), s.get("start_min") or 0, s["sid"]))
    for session in ordered:
        if session.get("value", 0) <= 0:
            continue
        candidates = []
        for handle in people:
            if max_per_person is not None and len(taken[handle]) >= max_per_person:
                continue
            if any(overlaps(session, other) for other in taken[handle]):
                continue
            candidates.append((scores.get((handle, session["sid"]), 0.0), -len(taken[handle]), handle))
        if not candidates:
            uncovered.append(session["sid"])
            continue
        best = max(candidates)[2]
        assignments[session["sid"]] = best
        taken[best].append(session)
    return assignments, uncovered


def plan_coverage(max_per_person: int | None = None) -> dict:
    people = [r[0] for r in G.rows("MATCH (p:Person) RETURN p.handle ORDER BY p.handle")]
    if not people:
        return {"error": "No team loaded yet. Run ingest_team first."}
    sessions = [
        {"sid": r[0], "title": r[1], "start": r[2], "start_min": r[3], "end_min": r[4], "room": r[5]}
        for r in G.rows(
            "MATCH (s:Session) RETURN s.sid, s.title, s.start, s.start_min, s.end_min, s.room"
        )
    ]
    evidence, value = gather_evidence()
    for s in sessions:
        s["value"] = value.get(s["sid"], 0.0)
    assignments, uncovered = plan(
        people, sessions, {k: v["score"] for k, v in evidence.items()}, max_per_person
    )

    G.q("MATCH (:Person)-[a:ASSIGNED_TO]->(:Session) DELETE a")
    by_sid = {s["sid"]: s for s in sessions}
    schedule: dict[str, list] = {h: [] for h in people}
    for sid, handle in assignments.items():
        ev = evidence.get((handle, sid), {"score": 0.0, "reasons": []})
        reason = "; ".join(ev["reasons"][:3]) or "covering for the team (no personal match)"
        G.q(
            "MATCH (p:Person {handle: $h}), (s:Session {sid: $sid}) "
            "MERGE (p)-[a:ASSIGNED_TO]->(s) SET a.score = $score, a.reason = $reason",
            {"h": handle, "sid": sid, "score": ev["score"], "reason": reason},
        )
        s = by_sid[sid]
        schedule[handle].append({"sid": sid, "title": s["title"], "start": s["start"], "room": s["room"], "why": reason})
    for items in schedule.values():
        items.sort(key=lambda x: x["start"] or "")

    return {
        "schedule": schedule,
        "relevant_sessions": sum(1 for s in sessions if s["value"] > 0),
        "covered": len(assignments),
        "missed_due_to_clashes": [
            {"sid": sid, "title": by_sid[sid]["title"], "start": by_sid[sid]["start"]} for sid in uncovered
        ],
    }


def resolve_session(ref: str) -> dict | None:
    """Find a session by sid or by (part of) its title."""
    found = G.rows(
        "MATCH (s:Session) WHERE s.sid = $ref OR toLower(s.title) CONTAINS toLower($ref) "
        "RETURN s.sid, s.title, s.start, s.room LIMIT 1",
        {"ref": ref},
    )
    if not found:
        return None
    sid, title, start, room = found[0]
    return {"sid": sid, "title": title, "start": start, "room": room}


WHY_QUERIES = (
    "MATCH path = (p:Person {handle: $h})-[:OWNS]->(:Repo)-[:DEPENDS_ON]->(:Package)<-[:MENTIONS]-(s:Session {sid: $sid}) RETURN path LIMIT 3",
    "MATCH path = (p:Person {handle: $h})-[:OWNS]->(:Repo)-[:TAGGED]->(:Topic)<-[:COVERS]-(s:Session {sid: $sid}) RETURN path LIMIT 2",
    "MATCH path = (p:Person {handle: $h})-[:INTERESTED_IN]->(:Topic)<-[:COVERS]-(s:Session {sid: $sid}) RETURN path LIMIT 2",
)


def why_paths(handle: str, sid: str) -> list[dict]:
    """Paths from a person's code and goals to a session, strongest kind first."""
    params = {"h": handle.lower(), "sid": sid}
    paths = []
    for cypher in WHY_QUERIES:
        paths += [G.path_json(r[0]) for r in G.rows(cypher, params)]
    return paths


def explain(handle: str, session_ref: str) -> dict:
    """Why does this session matter to this person? Returns the graph paths, and highlights them."""
    session = resolve_session(session_ref)
    if not session:
        return {"error": f"No session matching '{session_ref}'"}
    paths = why_paths(handle, session["sid"])
    who = G.rows(
        "MATCH (p:Person)-[a:ASSIGNED_TO]->(s:Session {sid: $sid}) RETURN p.handle, a.reason",
        {"sid": session["sid"]},
    )
    G.highlight(f"Why {handle} → {session['title']}", paths)
    return {
        "session": session,
        "paths": [p["text"] for p in paths] or ["No path: nothing in this person's code or goals connects to it."],
        "assigned_to": who[0][0] if who else None,
        "assignment_reason": who[0][1] if who else None,
    }
