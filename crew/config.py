"""Settings, read from the environment (and a .env file in the project root)."""
import os
from pathlib import Path

_CHECKOUT = Path(__file__).resolve().parent.parent
# Running from the repo (server, demo): settings and cache live there. Installed as a CLI (`pipx install`): ~/.crew.
ROOT = Path(os.getenv("CREW_HOME") or (_CHECKOUT if (_CHECKOUT / "web").is_dir() else Path.home() / ".crew"))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
HIGHLIGHT_FILE = CACHE_DIR / "highlight.json"
DIGEST_DRAFT = CACHE_DIR / "digest_draft.md"

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.getenv("CREW_GRAPH", "crew")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
BRIGHTDATA_UNLOCKER_ZONE = os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1")
BRIGHTDATA_SERP_ZONE = os.getenv("BRIGHTDATA_SERP_ZONE", "serp_api1")
# Cached pages younger than this are reused, so a flaky venue network can't sink the demo.
WEB_CACHE_SECONDS = int(os.getenv("WEB_CACHE_SECONDS", str(6 * 3600)))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
# GitHub Enterprise Server: https://<host>/api/v3. Default is github.com.
GITHUB_API_URL = (os.getenv("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

MCP_HOST = os.getenv("CREW_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("CREW_PORT", "8765"))
# Where the CLI on a teammate's machine finds the team's Crew server.
CREW_SERVER = (os.getenv("CREW_SERVER") or f"http://{MCP_HOST}:{MCP_PORT}").rstrip("/")
