"""Live web data through Bright Data (Web Unlocker + SERP API), with a disk cache.

Everything fetched here is untrusted: it may contain prompt injection, so it is
sanitized and wrapped before it ever reaches a model.
"""
import hashlib
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone

from . import config

API_URL = "https://api.brightdata.com/request"


class WebError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- cache ----------

def _cache_path(kind: str, key: str):
    digest = hashlib.sha256(key.encode()).hexdigest()[:24]
    folder = config.CACHE_DIR / kind
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{digest}.json"


def _cache_get(kind: str, key: str, max_age: int):
    path = _cache_path(kind, key)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if time.time() - data.get("_ts", 0) > max_age:
        return None
    return data


def _cache_put(kind: str, key: str, data: dict) -> None:
    data = dict(data, _ts=time.time())
    _cache_path(kind, key).write_text(json.dumps(data))


# ---------- Bright Data ----------

def _post(payload: dict, timeout: int = 120):
    import httpx

    if not config.BRIGHTDATA_API_KEY:
        raise WebError("BRIGHTDATA_API_KEY is not set")
    resp = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {config.BRIGHTDATA_API_KEY}"},
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise WebError(f"Bright Data returned {resp.status_code}: {resp.text[:300]}")
    return resp


def fetch_markdown(url: str, fresh: bool = False) -> dict:
    """Fetch a public page as markdown via Web Unlocker. Returns {url, markdown, fetched_at, cached}."""
    if not fresh:
        hit = _cache_get("page", url, config.WEB_CACHE_SECONDS)
        if hit:
            return {**hit, "cached": True}
    resp = _post({
        "zone": config.BRIGHTDATA_UNLOCKER_ZONE,
        "url": url,
        "format": "raw",
        "data_format": "markdown",
    })
    data = {"url": url, "markdown": resp.text, "fetched_at": now_iso()}
    _cache_put("page", url, data)
    return {**data, "cached": False}


# google.com, google.de, google.co.uk, google.com.au, and their subdomains; not lookalikes like evilgoogle.com
_GOOGLE_HOST = re.compile(r"(?:[a-z0-9-]+\.)*google\.(?:com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})")


def real_link(link: str) -> str:
    """Unwrap Google's /url?q=... redirects; drop /goto links, whose target is an opaque token ("" means skip)."""
    parsed = urllib.parse.urlparse(link or "")
    if _GOOGLE_HOST.fullmatch(parsed.hostname or "") and parsed.path in ("/url", "/goto"):
        query = urllib.parse.parse_qs(parsed.query)
        target = (query.get("url") or query.get("q") or [""])[0]
        return target if target.startswith(("http://", "https://")) else ""
    return link or ""


def search(query: str, n: int = 5, fresh: bool = False) -> list[dict]:
    """Google results via the SERP API. Returns [{title, link, snippet}]."""
    if not fresh:
        hit = _cache_get("serp", query, config.WEB_CACHE_SECONDS)
        if hit:  # filter here too: results cached by older versions may hold Google redirect links
            results = [dict(r, link=real_link(r.get("link", ""))) for r in hit["results"]]
            return [r for r in results if r["link"]][:n]
    params = urllib.parse.urlencode({"q": query, "brd_json": 1, "gl": "us", "hl": "en"})
    data = None
    for _ in range(2):  # the SERP API occasionally answers with a non-JSON body; one retry, then a normal WebError
        resp = _post({
            "zone": config.BRIGHTDATA_SERP_ZONE,
            "url": f"https://www.google.com/search?{params}",
            "format": "raw",
        })
        try:
            data = resp.json()
            break
        except ValueError:
            continue
    if data is None:
        raise WebError(f"SERP returned non-JSON for {query!r}: {resp.text[:120]!r}")
    results = []
    for item in data.get("organic", []):
        link = real_link(item.get("link") or item.get("url", ""))
        if link:
            results.append({
                "title": item.get("title", ""),
                "link": link,
                "snippet": item.get("description") or item.get("snippet", ""),
            })
    _cache_put("serp", query, {"results": results})
    return results[:n]


# ---------- untrusted content handling ----------

_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions"
    r"|disregard (all |the )?(previous|prior|above)"
    r"|you are now|new instructions:|system prompt"
    # role tags, and our own delimiters, so web text can't close its wrapper or pose as a teammate's note
    r"|<\s*/?\s*(system|assistant|developer|untrusted_web_content|user_note)\s*>)",
    re.IGNORECASE,
)


def sanitize(text: str, limit: int = 20000) -> str:
    text = (text or "").replace("\x00", "")
    text = _INJECTION.sub("[removed]", text)
    return text[:limit]


def wrap_untrusted(text: str, limit: int = 20000) -> str:
    return f"<untrusted_web_content>\n{sanitize(text, limit)}\n</untrusted_web_content>"


# Site chrome that scraped pages often put before the real title (GitHub starts with "Navigation Menu").
_CHROME_HEADINGS = {"navigation menu", "repository navigation", "skip to content", "menu", "search", "footer",
                    "table of contents", "contents", "on this page"}
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")


def page_title(markdown: str, fallback: str) -> str:
    """The page's first top-level heading, else its first heading that isn't site chrome, else `fallback`."""
    headings = []
    for line in (markdown or "").splitlines():
        m = _HEADING.match(line.strip())
        if m and m.group(2).strip().lower() not in _CHROME_HEADINGS:
            headings.append((len(m.group(1)), m.group(2).strip()))
    best = next((h for h in headings if h[0] == 1), headings[0] if headings else None)
    return best[1][:150] if best else fallback
