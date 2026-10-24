"""NFC check-in: a sticker on a session door opens /tap?s=<sid>, which records who was actually in the room."""
from . import graph as G
from . import web
from .planner import resolve_session, why_paths


def check_in(handle: str, session_ref: str) -> dict:
    handle = handle.lower()
    if not G.rows("MATCH (p:Person {handle: $h}) RETURN p.handle", {"h": handle}):
        return {"error": f"Unknown teammate '{handle}'"}
    session = resolve_session(session_ref)
    if not session:
        return {"error": f"No session matching '{session_ref}'"}
    params = {"h": handle, "sid": session["sid"]}
    G.q(
        "MATCH (p:Person {handle: $h}), (s:Session {sid: $sid}) MERGE (p)-[a:ATTENDED]->(s) SET a.at = $at",
        params | {"at": web.now_iso()},
    )
    tapped = [
        G.path_json(r[0])
        for r in G.rows("MATCH path = (:Person {handle: $h})-[:ATTENDED]->(:Session {sid: $sid}) RETURN path", params)
    ]
    why = why_paths(handle, session["sid"])
    assigned = G.rows("MATCH (p:Person)-[:ASSIGNED_TO]->(:Session {sid: $sid}) RETURN p.handle", params)
    G.highlight(f"{handle} tapped in → {session['title']}", tapped + why)
    return {
        "session": session,
        "assigned_to": assigned[0][0] if assigned else None,
        "why": [p["text"] for p in why],
    }
