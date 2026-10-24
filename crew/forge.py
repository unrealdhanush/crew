"""TrueForge: Crew's agents run in the TrueForge harness on OpenAI models and reach Crew through its MCP server.

One-time setup in the TrueForge UI (http://localhost:8790): Settings → Models → OpenAI (paste the key), and
Settings → Connectors → Add MCP Server, named `crew`, URL http://127.0.0.1:8765/mcp, no auth.
Then `crew forge-setup` creates the agents: crew-scout, and crew-<handle> for each teammate.
"""
import json
import os

from . import config
from . import graph as G

BASE_URL = os.getenv("TRUEFORGE_BASE_URL", "http://localhost:8790").rstrip("/")
MCP_NAME = os.getenv("CREW_FORGE_MCP", "crew")  # the connector's name in Settings → Connectors
MODEL = os.getenv("CREW_FORGE_MODEL") or f"openai/{config.OPENAI_MODEL}"
# Only publishing to the whole team needs a human. Listing it by name also replaces the default
# ["@write", "@destructive"], which would otherwise stop the agent at every note and check-in.
APPROVAL = ["publish_digest"]
PROMPTS = config.ROOT / "prompts"


def _quiet(message: str, level: str = "info") -> None:
    pass


def client():
    from trueforge_sdk import TrueForge  # imported lazily: only the host needs the SDK

    return TrueForge(base_url=BASE_URL, timeout=600)


def available() -> bool:
    import httpx

    try:
        return httpx.get(BASE_URL, timeout=2).status_code < 500
    except httpx.HTTPError:
        return False


def _spec(instructions: str) -> dict:
    return {
        "model": {"name": MODEL},
        "instructions": instructions,
        "mcp_servers": [{"name": MCP_NAME, "require_approval_for_tools": APPROVAL}],
    }


def agent_specs() -> dict[str, tuple[str, dict]]:
    """name -> (description, spec) for every agent Crew needs."""
    template = (PROMPTS / "agent.md").read_text().split("---", 1)[-1].strip()
    specs = {"crew-scout": ("Reads the team's READMEs and goals and maps them onto the agenda",
                            _spec((PROMPTS / "scout.md").read_text().split("---", 1)[-1].strip()))}
    for handle, name in G.rows("MATCH (p:Person) RETURN p.handle, p.name ORDER BY p.handle"):
        text = template.replace("{{HANDLE}}", handle).replace("{{NAME}}", name or handle)
        specs[f"crew-{handle}"] = (f"Crew conference agent for {name or handle}", _spec(text))
    return specs


def setup() -> dict:
    """Create or update Crew's agents in TrueForge. Safe to re-run after the team changes."""
    from trueforge_sdk.types.agent_spec import AgentSpec

    tf = client()
    existing = {a.name: a.id for a in tf.agents.list(limit=200)}
    done = []
    for name, (description, spec) in agent_specs().items():
        manifest = AgentSpec.model_validate(spec)
        if name in existing:
            tf.agents.update(agent_id=existing[name], manifest=manifest, description=description)
            done.append({"agent": name, "action": "updated"})
        else:
            tf.agents.create(name=name, description=description, manifest=manifest)
            done.append({"agent": name, "action": "created"})
    return {"trueforge": BASE_URL, "model": MODEL, "mcp_server": MCP_NAME, "agents": done}


def _short(arguments) -> str:
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
    except json.JSONDecodeError:
        return ""
    return ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items() if k != "evidence")


def run_scout(progress=_quiet, ask: str = "Profile every repo and teammate on the team that you haven't yet.") -> dict:
    """Run crew-scout as a TrueForge session, reporting each tool call it makes."""
    tf = client()
    session = tf.sessions.create(agent={"name": "crew-scout"})
    stream = tf.sessions.create_turn_stream(session_id=session.data.id, input=[{"type": "user.message", "content": ask}])
    calls, final = 0, None
    for event in stream:
        kind = getattr(event, "type", "")
        if kind == "model.message":
            for call in getattr(event, "tool_calls", None) or []:
                fn = getattr(call, "function", None)
                name = getattr(fn, "name", "") or ""
                calls += 1
                progress(f"Scout → {name.split('__')[-1]}({_short(getattr(fn, 'arguments', ''))})")
        elif kind == "mcp.auth_required":
            progress("TrueForge wants auth for the crew connector: set it to no auth", "warn")
        elif kind == "tool.approval_required":
            progress("Scout is waiting for an approval in TrueForge", "warn")
        elif kind == "turn.done":
            final = event.state
    status = getattr(final, "status", "unknown")
    if status != "done":
        raise RuntimeError(f"Scout turn ended with status {status}: {getattr(final, 'message', '')}")
    output = getattr(getattr(final, "output", None), "content", "") or ""
    return {"session": session.data.id, "tool_calls": calls, "summary": output if isinstance(output, str) else str(output)}
