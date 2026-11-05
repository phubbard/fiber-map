"""Small urllib helpers: honest User-Agent, conditional GET into a cache file."""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

from . import USER_AGENT

log = logging.getLogger(__name__)


def fetch_bytes(url: str, timeout: int = 60, headers: dict | None = None) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.headers)


def fetch_cached(url: str, dest: str, timeout: int = 180) -> str:
    """Download url to dest unless the server says it is unchanged.

    A sidecar ``dest + '.meta'`` keeps the ETag / Last-Modified so the next run
    can send a conditional request. Returns dest.
    """
    meta_path = dest + ".meta"
    cond: dict[str, str] = {}
    if os.path.exists(dest) and os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            if meta.get("etag"):
                cond["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                cond["If-Modified-Since"] = meta["last_modified"]
        except (OSError, ValueError):
            pass
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **cond})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            with open(meta_path, "w") as f:
                json.dump(
                    {
                        "url": url,
                        "etag": resp.headers.get("ETag"),
                        "last_modified": resp.headers.get("Last-Modified"),
                        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    f,
                )
            log.info("downloaded %s (%d bytes)", url, os.path.getsize(dest))
    except urllib.error.HTTPError as e:
        if e.code == 304 and os.path.exists(dest):
            log.info("not modified: %s", url)
            return dest
        raise
    return dest
