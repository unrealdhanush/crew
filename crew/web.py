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


def search(query: str, n: int = 5, fresh: bool = False) -> list[dict]:
    """Google results via the SERP API. Returns [{title, link, snippet}]."""
    if not fresh:
        hit = _cache_get("serp", query, config.WEB_CACHE_SECONDS)
        if hit:
            return hit["results"][:n]
    params = urllib.parse.urlencode({"q": query, "brd_json": 1, "gl": "us", "hl": "en"})
    resp = _post({
        "zone": config.BRIGHTDATA_SERP_ZONE,
        "url": f"https://www.google.com/search?{params}",
        "format": "raw",
    })
    try:
        data = resp.json()
    except ValueError:
        data = json.loads(resp.text)
    results = [
        {
            "title": item.get("title", ""),
            "link": item.get("link") or item.get("url", ""),
            "snippet": item.get("description") or item.get("snippet", ""),
        }
        for item in data.get("organic", [])
        if item.get("link") or item.get("url")
    ]
    _cache_put("serp", query, {"results": results})
    return results[:n]


# ---------- untrusted content handling ----------

_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) instructions"
    r"|disregard (all |the )?(previous|prior|above)"
    r"|you are now|new instructions:|system prompt"
    r"|</?(system|assistant|developer)>)",
    re.IGNORECASE,
)


def sanitize(text: str, limit: int = 20000) -> str:
    text = (text or "").replace("\x00", "")
    text = _INJECTION.sub("[removed]", text)
    return text[:limit]


def wrap_untrusted(text: str, limit: int = 20000) -> str:
    return f"<untrusted_web_content>\n{sanitize(text, limit)}\n</untrusted_web_content>"


def page_title(markdown: str, fallback: str) -> str:
    for line in (markdown or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:150]
    return fallback
