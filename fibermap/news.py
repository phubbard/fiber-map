"""Headlines from Google News RSS, one query per configured topic."""
from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .http import fetch_bytes

log = logging.getLogger(__name__)

RSS_URL = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def parse_rss(data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3].rstrip()
        published = None
        pub = item.findtext("pubDate")
        if pub:
            try:
                published = parsedate_to_datetime(pub).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (TypeError, ValueError):
                published = None
        items.append({"title": title, "link": link, "source": source, "published": published})
    return items


def fetch_news(cfg: dict) -> list[dict]:
    news_cfg = cfg["news"]
    days = int(news_cfg.get("max_age_days") or 0)
    per_query = int(news_cfg.get("per_query") or 15)
    out: list[dict] = []
    seen: set[str] = set()
    for q in news_cfg.get("queries", []):
        query = q["q"] + (f" when:{days}d" if days else "")
        url = RSS_URL.format(q=urllib.parse.quote(query))
        try:
            data, _ = fetch_bytes(url, timeout=30)
            items = parse_rss(data)
        except Exception as e:  # noqa: BLE001 - one bad feed must not sink the build
            log.warning("news query %r failed: %s", q.get("label"), e)
            continue
        n = 0
        for item in items:
            if item["link"] in seen:
                continue
            seen.add(item["link"])
            item["query"] = q.get("label", q["q"])
            out.append(item)
            n += 1
            if n >= per_query:
                break
        log.info("news %r: %d items", q.get("label"), n)
    out.sort(key=lambda i: i["published"] or "", reverse=True)
    return out
