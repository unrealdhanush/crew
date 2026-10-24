"""Background builds for the onboarding pages. The page polls progress while the graph viewer watches nodes arrive."""
import json
import os
import threading
import time
import traceback

from . import config, forge, ingest, planner, queries, scout
from . import graph as G

TEAM_FILE = config.DATA_DIR / "team.json"
EVENT_FILE = config.DATA_DIR / "event.json"
SAMPLE_AGENDA = config.DATA_DIR / "agenda.sample.json"
# Pause after each step so the graph visibly grows on stage. Set CREW_BUILD_PACE=0 for full speed.
PACE = float(os.getenv("CREW_BUILD_PACE", "0.4"))

_lock = threading.Lock()
_job = {"id": 0, "kind": "", "state": "idle", "events": [], "result": None}


def status(since: int = 0) -> dict:
    with _lock:
        return {
            "id": _job["id"], "kind": _job["kind"], "state": _job["state"], "result": _job["result"],
            "events": _job["events"][since:], "next": len(_job["events"]),
        }


def _say(message: str, level: str = "info") -> None:
    with _lock:
        _job["events"].append({"at": time.time(), "message": message, "level": level})
    time.sleep(PACE)


def start(kind: str, payload: dict) -> dict:
    runner = {"team": _build_team, "event": _publish_event}.get(kind)
    if not runner:
        return {"error": f"Unknown build '{kind}'"}
    with _lock:
        if _job["state"] == "running":
            return {"error": "A build is already running"}
        _job.update(id=_job["id"] + 1, kind=kind, state="running", events=[], result=None)
        job_id = _job["id"]
    threading.Thread(target=_run, args=(runner, payload), daemon=True).start()
    return {"id": job_id}


def _run(runner, payload: dict) -> None:
    try:
        result, state = runner(payload), "done"
    except Exception as exc:
        traceback.print_exc()
        _say(f"{type(exc).__name__}: {exc}", "error")
        result, state = None, "error"
    with _lock:
        _job.update(state=state, result=result)


def read_json(path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# ---------- team side ----------

def clean_team(data: dict) -> dict:
    members = []
    for m in data.get("members") or []:
        handle = (m.get("handle") or "").strip().lower()
        if not ingest.USERNAME_RE.fullmatch(handle):
            raise ValueError(f"Not a GitHub username: {handle!r}")
        members.append({
            "handle": handle,
            "name": (m.get("name") or handle).strip()[:80],
            "goals": [str(g).strip()[:40] for g in (m.get("goals") or []) if str(g).strip()][:10],
            "repos": [r for r in (m.get("repos") or []) if ingest.REPO_RE.fullmatch(r)][:10],
            "uploads": [clean_upload(u) for u in (m.get("uploads") or [])][:10],
        })
    if not members:
        raise ValueError("Add at least one teammate")
    return {"team": (data.get("team") or "Our team").strip()[:80], "members": members}


def clean_upload(upload: dict) -> dict:
    repo = ingest.upload_repo("check", upload)  # validates the name and normalizes the package list
    return {"name": upload["name"], "deps": repo["deps"], "dev_deps": repo["dev_deps"], "via": repo["source"]}


def _build_team(payload: dict) -> dict:
    team = clean_team(payload)  # drops anything not in the team format, including the token
    token = (payload.get("token") or "").strip()  # private repos: used for this build only, never written
    TEAM_FILE.write_text(json.dumps(team, indent=2))
    _say(f"Building {team['team']}: {len(team['members'])} teammates" + (" (with a token for private repos)" if token else ""))
    summary = ingest.ingest_members(team, _say, token)
    if summary["skipped"]:  # save only repos that could be read, so the form doesn't offer them again
        for m in team["members"]:
            m["repos"] = [r for r in m["repos"] if r not in summary["skipped"]]
        TEAM_FILE.write_text(json.dumps(team, indent=2))
    if payload.get("scout"):
        _run_scout()
    found = queries.bridges()
    _say(f"{len(found)} bridges between your code and the agenda: " + ", ".join(b["name"] for b in found[:8])
         if found else "No bridges yet: nothing in your code matches the agenda", "ok" if found else "warn")
    if not queries.stats()["sessions"]:
        _say("No agenda published yet, so there's nothing to plan. Ask your organizer to publish it.", "warn")
        return {"summary": summary, "bridges": found, "plan": None}
    _say("Planning coverage")
    plan = planner.plan_coverage()
    _say(f"Plan ready: {plan['covered']} of {plan['relevant_sessions']} relevant sessions covered", "ok")
    return {"summary": summary, "bridges": found, "plan": plan}


def _run_scout() -> None:
    """Crew Scout reads READMEs and goals: as a TrueForge agent when TrueForge is running, else by calling OpenAI
    directly. Scout only adds signal, so a failure here never fails the build."""
    if forge.available():
        try:
            _say("Handing off to Crew Scout in TrueForge")
            result = forge.run_scout(_say)
            _say(f"Scout finished after {result['tool_calls']} tool calls", "ok")
            return
        except Exception as exc:
            _say(f"TrueForge Scout didn't finish ({type(exc).__name__}: {exc}). Calling OpenAI directly", "warn")
    else:
        _say("TrueForge isn't running, so Scout calls OpenAI directly", "warn")
    try:
        done = scout.auto_tag(_say)
        _say(f"Scout tagged {done['repos']} repos and mapped {done['people']} teammates' goals", "ok")
    except Exception as exc:
        _say(f"Scout skipped: {type(exc).__name__}: {exc}", "warn")


def import_upload(handle: str, upload: dict) -> dict:
    """`crew scan` sends a dependency list from a teammate's machine. Add it to the graph and to team.json."""
    handle = (handle or "").strip().lower()
    team = read_json(TEAM_FILE) or {"team": "Our team", "members": []}
    member = next((m for m in team["members"] if m["handle"] == handle), None)
    if not member or not G.rows("MATCH (p:Person {handle: $h}) RETURN p.handle", {"h": handle}):
        return {"error": f"Unknown teammate '{handle}': add them on /team and build first"}
    clean = clean_upload(upload)
    member["uploads"] = [u for u in member.get("uploads", []) if u["name"] != clean["name"]] + [clean]
    repo = ingest.upload_repo(handle, clean)
    ingest.write_repo(handle, repo)
    TEAM_FILE.write_text(json.dumps(team, indent=2))
    if queries.stats()["sessions"]:
        planner.plan_coverage()
    paths = [G.path_json(r[0]) for r in G.rows(
        "MATCH path = (:Person {handle: $h})-[:OWNS]->(:Repo {full_name: $r})-[:DEPENDS_ON]->(:Package)<-[:MENTIONS]-(:Session) "
        "RETURN path LIMIT 10", {"h": handle, "r": repo["full_name"]})]
    G.highlight(f"{handle} scanned {clean['name']}", paths)
    return {"repo": repo["full_name"], "dependencies": len(repo["deps"]), "paths": [p["text"] for p in paths]}


# ---------- organizer side ----------

def _publish_event(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()[:120] or "Our event"
    urls = [u.strip() for u in payload.get("urls") or [] if u.strip().startswith(("http://", "https://"))][:5]
    sample = bool(payload.get("sample"))
    if not sample and not urls:
        raise ValueError("Add an agenda URL, or use the sample agenda")
    EVENT_FILE.write_text(json.dumps({"name": name, "urls": urls, "sample": sample}, indent=2))
    _say(f"Publishing the agenda for {name}")
    if sample:
        result = ingest.ingest_agenda_file(SAMPLE_AGENDA, _say)
    else:
        result = ingest.ingest_agenda(urls, False, _say)
    _say(f"{result['sessions']} sessions published", "ok")
    if queries.stats()["persons"]:
        _say("Re-planning coverage for the teams already signed up")
        planner.plan_coverage()
    return result
