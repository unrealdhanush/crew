"""Crew command line: `pip install -e .` (or `pipx install .`) gives you `crew`; `python -m crew.cli` also works.

On a teammate's machine (talks to the team's Crew server, set CREW_SERVER or pass --server):
  crew scan <handle> [path] [--name billing-api] [--dry-run]   send package names from local code, nothing else
  crew open                                                    open the team's Crew in the browser

On the machine hosting Crew (needs FalkorDB):
  crew serve                                                   web app, graph view and MCP endpoint
  crew init|reset
  crew team data/team.json
  crew agenda https://githubuniverse.com/... [--fresh]  |  crew agenda-file data/agenda.sample.json
  crew plan | blind | ripple <pkg> | why <handle> <session>
  crew note <handle> "<text>" [--session "<title>"]
  crew ask "<question>" | digest
  crew forge-setup                                             create/update Crew's agents in TrueForge
  crew scout [--direct]                                        run Crew Scout (in TrueForge, or OpenAI directly)
"""
import argparse
import json
from pathlib import Path

from . import config, digest, forge, ingest, memory, notes, planner, queries, scout
from . import graph as G


def print_progress(message: str, level: str = "info") -> None:
    print(("! " if level == "warn" else "· ") + message, flush=True)


def scan(args) -> dict:
    """Read dependency files on this machine and send only the package names to Crew. Code never leaves."""
    import httpx

    root = Path(args.path).resolve()
    deps, dev, files = ingest.scan_dir(root)
    if not files:
        return {"error": f"No dependency files found under {root}"}
    payload = {"handle": args.handle, "name": args.name or ingest.slug(root.name) or "project",
               "deps": sorted(deps), "dev_deps": sorted(dev), "via": "crew scan"}
    if args.dry_run:
        return {"read": files, "would_send": payload}
    headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"} if config.ACCESS_TOKEN else {}
    resp = httpx.post(f"{args.server.rstrip('/')}/api/import", json=payload, headers=headers, timeout=60)
    return {"read": files, "sent": f"{len(deps)} package names, nothing else", "crew": resp.json()}


def main() -> None:
    ap = argparse.ArgumentParser(prog="crew")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("reset")
    sub.add_parser("team").add_argument("file")
    a = sub.add_parser("agenda")
    a.add_argument("urls", nargs="+")
    a.add_argument("--fresh", action="store_true")
    sub.add_parser("agenda-file").add_argument("file")
    sub.add_parser("plan")
    sub.add_parser("blind")
    sub.add_parser("ripple").add_argument("package")
    w = sub.add_parser("why")
    w.add_argument("handle")
    w.add_argument("session")
    n = sub.add_parser("note")
    n.add_argument("handle")
    n.add_argument("text")
    n.add_argument("--session")
    sub.add_parser("ask").add_argument("question")
    sub.add_parser("digest")
    sub.add_parser("serve")
    sub.add_parser("forge-setup").add_argument("--server", default="", help="a deployed Crew to read the team from")
    sub.add_parser("scout").add_argument("--direct", action="store_true", help="skip TrueForge, call OpenAI directly")
    sub.add_parser("open").add_argument("--server", default=config.CREW_SERVER)
    s = sub.add_parser("scan")
    s.add_argument("handle")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--name")
    s.add_argument("--server", default=config.CREW_SERVER)
    s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.cmd == "serve":
        from . import server

        return server.main()
    if args.cmd == "open":
        import webbrowser

        webbrowser.open(args.server + "/" + (f"?token={config.ACCESS_TOKEN}" if config.ACCESS_TOKEN else ""))
        return print(f"Opened {args.server}/")
    if args.cmd not in ("scan",) and not (args.cmd == "forge-setup" and args.server):  # these only talk to a server
        G.init_schema()
    result = {
        "init": lambda: {"ok": True},
        "reset": lambda: (G.reset(), {"ok": True})[1],
        "team": lambda: ingest.ingest_team(args.file),
        "agenda": lambda: ingest.ingest_agenda(args.urls, args.fresh),
        "agenda-file": lambda: ingest.ingest_agenda_file(args.file),
        "plan": planner.plan_coverage,
        "blind": queries.blind_spots,
        "ripple": lambda: queries.ripple(args.package),
        "why": lambda: planner.explain(args.handle, args.session),
        "note": lambda: notes.add_note(args.handle, args.text, args.session),
        "ask": lambda: memory.ask_team(args.question),
        "digest": digest.draft_digest,
        "scan": lambda: scan(args),
        "forge-setup": lambda: forge.setup(args.server),
        "scout": lambda: scout.auto_tag(print_progress) if args.direct else forge.run_scout(print_progress),
    }[args.cmd]()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
