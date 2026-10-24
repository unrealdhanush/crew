"""Team digest: drafted by the agent, published only after a human approves it (TrueForge approval gate)."""
import json
import time
from datetime import datetime

from . import config, llm
from . import graph as G
from .queries import blind_spots

DIGEST_PROMPT = """Write a short team digest in Markdown for engineers who stayed home.
Sections: "What changes for us" (breaking changes and which repo/owner is affected), "Worth knowing" (one line per
note, credit the teammate, keep source links), "Gaps" (sessions touching our code that nobody covered).
Use only the data given. No filler. Under 250 words."""


def draft_digest() -> dict:
    notes = G.rows(
        "MATCH (p:Person)-[:WROTE]->(n:Note) "
        "OPTIONAL MATCH (n)-[:ABOUT]->(s:Session) "
        "OPTIONAL MATCH (n)-[:CITES]->(src:Source) "
        "OPTIONAL MATCH (n)-[:MENTIONS]->(k:Package)<-[:DEPENDS_ON]-(r:Repo)<-[:OWNS]-(o:Person) "
        "RETURN p.handle, n.text, s.title, collect(DISTINCT src.url), "
        "collect(DISTINCT {package: k.name, repo: r.full_name, owner: o.handle}) "
        "ORDER BY p.handle"
    )
    gaps = blind_spots(limit=8)["unassigned_sessions_touching_our_code"]
    data = {
        "notes": [
            {"by": r[0], "note": r[1], "session": r[2], "sources": [u for u in r[3] if u], "affects": [a for a in r[4] if a and a.get("repo")]}
            for r in notes
        ],
        "gaps": [{"session": g["session"], "package": g["package"], "repo": g["repo"]} for g in gaps],
    }
    markdown = llm.text_call(DIGEST_PROMPT, json.dumps(data, default=str))
    config.DIGEST_DRAFT.write_text(markdown)
    return {"draft": markdown, "notes_used": len(data["notes"]), "status": "draft - call publish_digest to send"}


def publish_digest() -> dict:
    """Publishes the latest draft. Gate this tool behind human approval in TrueForge."""
    if not config.DIGEST_DRAFT.exists():
        return {"error": "No draft yet. Call draft_digest first."}
    markdown = config.DIGEST_DRAFT.read_text()
    out_dir = config.DATA_DIR / "digests"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"digest-{datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(markdown)
    posted = False
    if config.SLACK_WEBHOOK_URL:
        import httpx

        resp = httpx.post(config.SLACK_WEBHOOK_URL, json={"text": markdown}, timeout=20)
        posted = resp.status_code < 300
    G.q("CREATE (:Digest {at: $at, path: $path})", {"at": time.time(), "path": str(path)})
    return {"published": str(path), "posted_to_slack": posted}
