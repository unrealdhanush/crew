"""Load the team (people -> repos -> dependencies) and the conference agenda into the graph."""
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

from . import config, llm, web
from . import graph as G

# ---------- normalization (shared names are what make the graph join) ----------

ALIASES = {
    "github-copilot": "copilot",
    "copilot-agent": "copilot",
    "model-context-protocol": "mcp",
    "modelcontextprotocol": "mcp",
    "@modelcontextprotocol/sdk": "mcp",
    "nodejs": "node",
    "node.js": "node",
    "langchain-core": "langchain",
    "@langchain/core": "langchain",
    "actions": "github-actions",
    "gh-actions": "github-actions",
}


def norm_pkg(name: str) -> str:
    name = (name or "").strip().lower()
    if not name.startswith("@"):
        name = re.split(r"[<>=!~\[;\s(]", name, maxsplit=1)[0]
    name = name.replace("_", "-").strip()
    return ALIASES.get(name, name)


def norm_topic(name: str) -> str:
    name = re.sub(r"[^a-z0-9+.#\- ]", "", (name or "").strip().lower())
    return re.sub(r"\s+", "-", name).strip("-")


def slug(text: str, limit: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:limit]


# ---------- dependency file parsers ----------

def parse_requirements(text: str) -> set[str]:
    deps = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http://", "https://")):
            continue
        deps.add(norm_pkg(line))
    return {d for d in deps if d}


def parse_package_json(text: str) -> set[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    deps = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps |= {norm_pkg(name) for name in (data.get(key) or {})}
    return {d for d in deps if d}


def parse_package_json_dev(text: str) -> set[str]:
    """Packages that are only devDependencies (build/lint/test tooling)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    runtime = {norm_pkg(n) for key in ("dependencies", "peerDependencies") for n in (data.get(key) or {})}
    return {norm_pkg(n) for n in (data.get("devDependencies") or {})} - runtime - {""}


def parse_pyproject(text: str) -> set[str]:
    try:
        import tomllib  # Python 3.11+

        data = tomllib.loads(text)
        items = list(data.get("project", {}).get("dependencies", []))
        for group in (data.get("project", {}).get("optional-dependencies") or {}).values():
            items += group
        poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        items += [k for k in poetry if k.lower() != "python"]
    except Exception:
        block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
        items = re.findall(r"[\"']([^\"']+)[\"']", block.group(1)) if block else []
    return {norm_pkg(i) for i in items if norm_pkg(i)}


def parse_go_mod(text: str) -> set[str]:
    deps = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("module", "go ", "//", ")", "require (")) or not line:
            continue
        line = line.removeprefix("require ").strip()
        mod = line.split()[0] if line.split() else ""
        if "/" in mod:
            deps.add(norm_pkg(mod.split("/")[-1]))
    return deps


DEP_FILES = [
    ("requirements.txt", parse_requirements),
    ("pyproject.toml", parse_pyproject),
    ("package.json", parse_package_json),
    ("go.mod", parse_go_mod),
]
PARSERS = dict(DEP_FILES)


def parse_manifest(filename: str, text: str) -> tuple[set[str], set[str]]:
    """(dependencies, dev-only dependencies) from one dependency file, picked by its file name."""
    name = Path(filename).name.lower()
    if name.startswith("requirements") and name.endswith(".txt"):  # requirements-dev.txt etc.
        name = "requirements.txt"
    parser = PARSERS.get(name)
    if not parser:
        raise ValueError(f"Unsupported dependency file: {filename} (use one of {', '.join(PARSERS)})")
    deps = parser(text)
    dev = parse_package_json_dev(text) if name == "package.json" else set()
    return deps, dev


def parse_sbom(sbom: dict) -> tuple[set[str], set[str]]:
    """Direct dependencies from GitHub's dependency-graph SBOM (SPDX), plus the ecosystems they come from.
    The SBOM also lists transitive packages from lockfiles; only the root's DEPENDS_ON edges are direct."""
    doc = sbom.get("sbom", sbom)
    packages = {p.get("SPDXID"): p for p in doc.get("packages", [])}
    rels = doc.get("relationships", [])
    roots = {r["relatedSpdxElement"] for r in rels if r.get("relationshipType") == "DESCRIBES"}
    direct = [r["relatedSpdxElement"] for r in rels if r.get("relationshipType") == "DEPENDS_ON" and r.get("spdxElementId") in roots]
    deps, ecosystems = set(), set()
    for spdx_id in direct or packages:
        for ref in packages.get(spdx_id, {}).get("externalRefs", []):
            if ref.get("referenceType") != "purl":
                continue
            kind, _, rest = ref.get("referenceLocator", "").removeprefix("pkg:").partition("/")
            path = urllib.parse.unquote(rest.split("@", 1)[0].split("?", 1)[0])
            if kind == "githubactions":
                name = "github-actions"  # workflows use Actions: that's the bridge to Actions sessions
            elif kind == "github" or not path:
                continue  # the repo itself
            elif kind == "npm":
                name = path  # keeps @scope/name
            else:
                name = path.split("/")[-1]  # golang/maven/etc: last segment, like parse_go_mod
            if norm_pkg(name):
                deps.add(norm_pkg(name))
                ecosystems.add(kind)
    return deps, ecosystems


# ---------- GitHub (github.com or GitHub Enterprise Server via GITHUB_API_URL) ----------

USERNAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
REPO_RE = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}")
PUBLIC_API = "https://api.github.com"


class GitHubError(ValueError):
    pass


def _gh_get(url: str, raw: bool = False, token: str = "", accept: str = "application/vnd.github+json"):
    """GET from GitHub. `token` is a teammate's own token for private repos: it is never stored, and its
    responses are never cached, so private data can't leak into a later request made without it.
    Everything else is cached like web pages so rehearsals don't burn the 60/hour anonymous limit."""
    import httpx

    cacheable = not token
    if cacheable:
        hit = web._cache_get("github", url, config.WEB_CACHE_SECONDS)
        if hit:
            return hit["body"]
    headers = {"Accept": accept, "User-Agent": "crew-hackathon"}
    if token or config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {token or config.GITHUB_TOKEN}"
    resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    if resp.status_code == 404:
        body = None
    elif resp.status_code in (401, 403):
        if resp.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubError("GitHub rate limit reached: add a token (GITHUB_TOKEN or the field on /team)")
        raise GitHubError(f"GitHub refused access ({resp.status_code}): check the token's permissions")
    else:
        resp.raise_for_status()
        body = resp.text if raw else resp.json()
    if cacheable:
        web._cache_put("github", url, {"body": body})
    return body


def _repo_file(full_name: str, branch: str, path: str, token: str = "") -> str | None:
    if config.GITHUB_API_URL == PUBLIC_API:  # raw host isn't rate limited; it doesn't exist on Enterprise Server
        return _gh_get(f"https://raw.githubusercontent.com/{full_name}/{branch}/{path}", raw=True, token=token)
    return _gh_get(f"{config.GITHUB_API_URL}/repos/{full_name}/contents/{path}?ref={branch}", raw=True,
                   token=token, accept="application/vnd.github.raw+json")


def _repo_summary(r: dict) -> dict:
    return {
        "full_name": r["full_name"],
        "description": r.get("description") or "",
        "language": r.get("language") or "",
        "stars": r.get("stargazers_count", 0),
        "private": bool(r.get("private")),
        "pushed_at": r.get("pushed_at"),
    }


def list_repos(username: str, org: str = "", token: str = "", limit: int = 12) -> list[dict]:
    """A user's public repos, plus (with `org`) the org's repos, which include private ones when `token` can see them.
    Most recently pushed first, without forks or archived repos."""
    if not USERNAME_RE.fullmatch(username or ""):
        raise ValueError(f"Not a GitHub username: {username!r}")
    if org and not USERNAME_RE.fullmatch(org):
        raise ValueError(f"Not a GitHub org: {org!r}")
    api = config.GITHUB_API_URL
    found = []
    if org:
        repos = _gh_get(f"{api}/orgs/{org}/repos?type=all&sort=pushed&per_page=50", token=token)
        if repos is None:
            raise ValueError(f"GitHub org not found: {org}")
        found += repos
    repos = _gh_get(f"{api}/users/{username}/repos?sort=pushed&per_page=50", token=token)
    if repos is None:
        raise ValueError(f"GitHub user not found: {username}")
    seen, out = set(), []
    for r in sorted(found, key=lambda r: r.get("pushed_at") or "", reverse=True)[:limit] + repos:
        if r.get("fork") or r.get("archived") or r["full_name"] in seen:
            continue
        seen.add(r["full_name"])
        out.append(_repo_summary(r))
    return out[: limit * (2 if org else 1)]


def fetch_repo(full_name: str, token: str = "") -> dict:
    if not REPO_RE.fullmatch(full_name or ""):
        raise ValueError(f"Not a GitHub repo: {full_name!r}")
    api = config.GITHUB_API_URL
    meta = _gh_get(f"{api}/repos/{full_name}", token=token)
    if not meta:
        raise ValueError(f"Repo not found (private repos need a token): {full_name}")
    branch = meta.get("default_branch", "main")
    deps: set[str] = set()
    dev_deps: set[str] = set()
    source = "dependency graph"
    try:  # GitHub's own dependency graph covers every ecosystem it knows, in one call
        sbom = _gh_get(f"{api}/repos/{full_name}/dependency-graph/sbom", token=token)
    except GitHubError:
        sbom = None
    ecosystems: set[str] = set()
    if sbom:
        deps, ecosystems = parse_sbom(sbom)
    if not deps:  # dependency graph off for this repo: read the dependency files ourselves
        source = "dependency files"
        for filename, _ in DEP_FILES:
            text = _repo_file(full_name, branch, filename, token)
            if text:
                file_deps, file_dev = parse_manifest(filename, text)
                deps |= file_deps
                dev_deps |= file_dev
    elif "npm" in ecosystems:  # the SBOM doesn't mark devDependencies; package.json does
        text = _repo_file(full_name, branch, "package.json", token)
        if text:
            dev_deps = parse_package_json_dev(text) & deps
    return {
        "full_name": meta["full_name"],
        "description": meta.get("description") or "",
        "language": meta.get("language") or "",
        "stars": meta.get("stargazers_count", 0),
        "topics": [norm_topic(t) for t in meta.get("topics", [])],
        "deps": sorted(deps),
        "dev_deps": sorted(dev_deps),
        "source": source,
    }


def fetch_readme(full_name: str, token: str = "") -> str:
    """The repo's README as text ("" if none). Untrusted: callers wrap it before a model sees it."""
    if not REPO_RE.fullmatch(full_name or ""):
        return ""
    text = _gh_get(f"{config.GITHUB_API_URL}/repos/{full_name}/readme", raw=True, token=token,
                   accept="application/vnd.github.raw+json")
    return text or ""


# ---------- dependency lists that never touch GitHub: uploads and `crew scan` ----------

UPLOAD_RE = re.compile(r"[A-Za-z0-9._-]{1,60}")
SCAN_SKIP = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "__pycache__", ".tox", ".cache"}


def scan_dir(root: str | Path, max_depth: int = 4) -> tuple[set[str], set[str], list[str]]:
    """Find and parse dependency files under `root` on this machine. Returns (deps, dev_deps, files read).
    Only dependency files are opened; source code is never read."""
    import os

    root = Path(root)
    deps, dev, files = set(), set(), []
    for folder, dirs, names in os.walk(root):
        depth = len(Path(folder).relative_to(root).parts)
        dirs[:] = [] if depth >= max_depth else sorted(d for d in dirs if d not in SCAN_SKIP and not d.startswith("."))
        for name in sorted(names):
            try:
                found, found_dev = parse_manifest(name, (Path(folder) / name).read_text(errors="replace"))
            except ValueError:
                continue  # not a dependency file
            deps |= found
            dev |= found_dev
            files.append(str((Path(folder) / name).relative_to(root)))
    return deps, dev & deps, files


def upload_repo(handle: str, upload: dict) -> dict:
    """A dependency list sent from the team's own machine. Only package names; no code, no repo access."""
    if not UPLOAD_RE.fullmatch(upload.get("name") or ""):
        raise ValueError(f"Bad project name: {upload.get('name')!r}")
    deps = sorted({norm_pkg(d) for d in upload.get("deps") or [] if isinstance(d, str) and norm_pkg(d)})[:500]
    dev = sorted({norm_pkg(d) for d in upload.get("dev_deps") or [] if isinstance(d, str)} & set(deps))
    via = upload.get("via") if upload.get("via") in ("upload", "crew scan") else "upload"
    return {
        "full_name": f"local:{handle}/{upload['name']}",
        "description": f"Dependency list sent by {via}",
        "language": "",
        "stars": 0,
        "topics": [],
        "deps": deps,
        "dev_deps": dev,
        "source": via,
    }


def _quiet(message: str, level: str = "info") -> None:
    pass


def ingest_team(team_file: str | Path, progress=_quiet) -> dict:
    """team.json: {"team": "...", "members": [{"handle", "name", "goals": [...], "repos": ["owner/repo"],
    "uploads": [{"name", "deps", "dev_deps", "via"}]}]}"""
    return ingest_members(json.loads(Path(team_file).read_text()), progress)


def ingest_members(team: dict, progress=_quiet, token: str = "") -> dict:
    """Write teammates, their goals, repos and dependencies. `progress(message, level)` hears each step.
    `token` (optional) reads private repos; it is only passed through, never stored."""
    summary = {"members": 0, "repos": 0, "packages": set(), "skipped": []}
    for member in team["members"]:
        handle = member["handle"].lower()
        progress(f"Adding {handle}")
        G.q(
            "MERGE (p:Person {handle: $h}) SET p.name = $name, p.team = $team, p.goals_text = $goals_text",
            {"h": handle, "name": member.get("name", handle), "team": team.get("team", ""),
             "goals_text": ", ".join(member.get("goals", []))},
        )
        goals = [norm_topic(g) for g in member.get("goals", []) if norm_topic(g)]
        G.q(
            "MATCH (p:Person {handle: $h}) UNWIND $goals AS g "
            "MERGE (t:Topic {name: g}) MERGE (p)-[:INTERESTED_IN]->(t)",
            {"h": handle, "goals": goals},
        )
        repos = []
        for full_name in member.get("repos", []):
            progress(f"Reading {full_name} on GitHub")
            try:
                repos.append(fetch_repo(full_name, token))
            except ValueError as exc:
                progress(f"Skipped {full_name}: {exc}", "warn")
                summary["skipped"].append(full_name)
        for upload in member.get("uploads", []):
            progress(f"Adding {handle}'s uploaded list {upload.get('name')}")
            repos.append(upload_repo(handle, upload))
        for repo in repos:
            write_repo(handle, repo)
            progress(f"{repo['full_name']}: {len(repo['deps'])} dependencies from {repo['source']}"
                     + (f", {len(repo['topics'])} topics" if repo["topics"] else ""))
            summary["repos"] += 1
            summary["packages"] |= set(repo["deps"])
        summary["members"] += 1
    summary["packages"] = len(summary["packages"])
    return summary


def write_repo(handle: str, repo: dict) -> None:
    G.q(
        "MATCH (p:Person {handle: $h}) "
        "MERGE (r:Repo {full_name: $full_name}) "
        "SET r.description = $description, r.language = $language, r.stars = $stars "
        "MERGE (p)-[:OWNS]->(r)",
        {"h": handle, **{k: repo[k] for k in ("full_name", "description", "language", "stars")}},
    )
    G.q(
        "MATCH (r:Repo {full_name: $full_name}) UNWIND $deps AS d "
        "MERGE (k:Package {name: d}) MERGE (r)-[e:DEPENDS_ON]->(k) SET e.dev = d IN $dev",
        {"full_name": repo["full_name"], "deps": repo["deps"], "dev": repo.get("dev_deps", [])},
    )
    G.q(
        "MATCH (r:Repo {full_name: $full_name}) UNWIND $topics AS t "
        "MERGE (x:Topic {name: t}) MERGE (r)-[:TAGGED]->(x)",
        {"full_name": repo["full_name"], "topics": repo["topics"]},
    )


# ---------- agenda ----------

AGENDA_PROMPT = """You extract conference sessions from a scraped agenda page.
Return {"sessions": [...]} where each session is:
{"title": str, "start": "YYYY-MM-DDTHH:MM" local time or null, "end": same or null,
 "room": str or null, "track": str or null, "abstract": str (<= 600 chars),
 "speakers": [{"name": str, "company": str or null}],
 "topics": [3-6 short lowercase tags, e.g. "agents", "supply-chain-security"],
 "packages": [libraries, tools or products the session is about, lowercase]}
Only include real sessions that appear in the text. Never invent times or speakers.
If the page gives a date only once, apply it to the sessions under it.
Prefer these existing names when they fit (they are what the team depends on):
packages: {packages}
topics: {topics}"""


def known_names(label: str, limit: int = 300) -> list[str]:
    try:
        return [r[0] for r in G.rows(f"MATCH (n:{label}) RETURN n.name LIMIT {limit}")]
    except Exception:
        return []


def _chunks(text: str, size: int = 14000) -> list[str]:
    paragraphs, chunks, current = text.split("\n\n"), [], ""
    for para in paragraphs:
        if len(current) + len(para) > size and current:
            chunks.append(current)
            current = ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(current)
    return chunks


def extract_sessions(markdown: str) -> list[dict]:
    system = AGENDA_PROMPT.replace("{packages}", ", ".join(known_names("Package"))).replace(
        "{topics}", ", ".join(known_names("Topic"))
    )
    found: dict[str, dict] = {}
    for chunk in _chunks(markdown):
        data = llm.json_call(system, web.wrap_untrusted(chunk, limit=16000))
        for session in data.get("sessions", []):
            if session.get("title"):
                found.setdefault(slug(session["title"]), session)
    return list(found.values())


def to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return int(dt.replace(tzinfo=None).timestamp() // 60)


def write_sessions(sessions: list[dict], source_url: str, fetched_at: str, progress=_quiet) -> int:
    G.q(
        "MERGE (src:Source {url: $url}) SET src.fetched_at = $at, src.title = coalesce(src.title, $url)",
        {"url": source_url, "at": fetched_at},
    )
    for s in sessions:
        sid = s.get("sid") or slug(s["title"])
        progress(f"Session: {s['title'].strip()}")
        G.q(
            "MERGE (s:Session {sid: $sid}) "
            "SET s.title = $title, s.start = $start, s.end = $end, s.start_min = $start_min, "
            "s.end_min = $end_min, s.room = $room, s.track = $track, s.abstract = $abstract "
            "WITH s MATCH (src:Source {url: $url}) MERGE (s)-[c:CITES]->(src) SET c.fetched_at = $at",
            {
                "sid": sid,
                "title": s["title"].strip(),
                "start": s.get("start"),
                "end": s.get("end"),
                "start_min": to_minutes(s.get("start")),
                "end_min": to_minutes(s.get("end")),
                "room": s.get("room"),
                "track": s.get("track"),
                "abstract": (s.get("abstract") or "")[:1200],
                "url": source_url,
                "at": fetched_at,
            },
        )
        speakers = [
            {"name": sp["name"].strip(), "company": sp.get("company") or ""}
            for sp in s.get("speakers", [])
            if sp.get("name")
        ]
        G.q(
            "MATCH (s:Session {sid: $sid}) UNWIND $speakers AS sp "
            "MERGE (x:Speaker {name: sp.name}) SET x.company = sp.company "
            "MERGE (x)-[:PRESENTS]->(s)",
            {"sid": sid, "speakers": speakers},
        )
        pkgs = sorted({norm_pkg(p) for p in s.get("packages", []) if norm_pkg(p)})
        # A session about a package also covers it as a topic, so a goal like "github-actions" joins
        # a session that only lists github-actions as a package. Scoped npm names make poor topics.
        topics = {norm_topic(t) for t in s.get("topics", [])} | {norm_topic(p) for p in pkgs if "/" not in p}
        G.q(
            "MATCH (s:Session {sid: $sid}) UNWIND $topics AS t "
            "MERGE (x:Topic {name: t}) MERGE (s)-[:COVERS]->(x)",
            {"sid": sid, "topics": sorted(t for t in topics if t)},
        )
        G.q(
            "MATCH (s:Session {sid: $sid}) UNWIND $pkgs AS p "
            "MERGE (k:Package {name: p}) MERGE (s)-[:MENTIONS]->(k)",
            {"sid": sid, "pkgs": pkgs},
        )
    return len(sessions)


def ingest_agenda(urls: list[str], fresh: bool = False, progress=_quiet) -> dict:
    """Scrape agenda pages live with Bright Data, extract sessions, write them to the graph.
    `sessions` counts distinct sessions: pages that list the same session are merged into one graph node."""
    sids, details = set(), []
    for url in urls:
        progress(f"Scraping {url} with Bright Data")
        page = web.fetch_markdown(url, fresh=fresh)
        progress(f"Got {len(page['markdown']):,} characters{' (cached)' if page['cached'] else ''}. Extracting sessions")
        sessions = extract_sessions(page["markdown"])
        write_sessions(sessions, url, page["fetched_at"], progress)
        sids |= {s.get("sid") or slug(s["title"]) for s in sessions}
        progress(f"{len(sessions)} sessions from {url}")
        details.append({"url": url, "sessions": len(sessions), "cached": page["cached"], "fetched_at": page["fetched_at"]})
    return {"sessions": len(sids), "pages": details}


def ingest_agenda_file(path: str | Path, progress=_quiet) -> dict:
    """Fallback: load sessions from a JSON file ({"source": url, "sessions": [...]})."""
    data = json.loads(Path(path).read_text())
    progress(f"Loading {len(data['sessions'])} sessions from {Path(path).name}")
    count = write_sessions(data["sessions"], data.get("source", f"file://{path}"), web.now_iso(), progress)
    return {"sessions": count}
