"""Build site/data.json: permits in the area, source-wide stats, news, tiles."""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from . import __version__, config, geo, history, permits
from .news import fetch_news
from .tiles import ensure_tiles

log = logging.getLogger(__name__)


def _new_counter():
    return {"total": 0, "fiber": 0, "row": 0, "traffic": 0, "encroachment": 0}


def summarize(items: list[permits.Permit], today: date | None = None) -> dict:
    """Counts by creation year and company, plus trailing-12-month vs prior-12-month."""
    today = today or date.today()
    cutoff12 = (today - timedelta(days=365)).isoformat()
    cutoff24 = (today - timedelta(days=730)).isoformat()
    by_year: dict[str, dict] = defaultdict(lambda: defaultdict(_new_counter))
    trailing12: dict[str, dict] = defaultdict(_new_counter)
    prior12: dict[str, dict] = defaultdict(_new_counter)
    active = fiber_active = 0
    for p in items:
        created = p.created or ""
        year = created[:4] or "unknown"
        buckets = [by_year[year][p.company]]
        if created >= cutoff12:
            buckets.append(trailing12[p.company])
        elif created >= cutoff24:
            buckets.append(prior12[p.company])
        for b in buckets:
            b["total"] += 1
            b[p.kind] = b.get(p.kind, 0) + 1
            if p.fiber:
                b["fiber"] += 1
        if p.phase in ("active", "planned"):
            active += 1
            if p.fiber:
                fiber_active += 1
    return {
        "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        "trailing12": dict(trailing12),
        "prior12": dict(prior12),
        "active": active,
        "fiber_active": fiber_active,
        "total": len(items),
    }


def default_links(cfg: dict, source_info: dict) -> list[dict]:
    lat, lng = cfg["center"]
    links = [
        {
            "label": "FCC broadband map here",
            "url": f"https://broadbandmap.fcc.gov/location-summary/fixed?vlat={lat}&vlon={lng}&zoom=14&br=r",
        },
        {"label": "AT&T Fiber availability", "url": "https://www.att.com/internet/fiber/coverage-map/"},
        {"label": "T-Mobile Fiber", "url": "https://www.t-mobile.com/home-internet/fiber"},
        {"label": "Google Fiber", "url": "https://fiber.google.com/"},
    ]
    links.extend(source_info.get("extra_links") or [])
    links.extend(cfg.get("links") or [])
    return links


def build(config_path: str, no_tiles: bool = False, no_news: bool = False) -> dict:
    cfg = config.load(config_path)
    data_dir, site_dir = cfg["data_dir"], cfg["site_dir"]
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(site_dir, exist_ok=True)
    cfg = config.resolve_area(cfg, data_dir)
    log.info("area %s center=%s radius=%.1f km bbox=%s", cfg["label"], cfg["center"], cfg["radius_km"], cfg["bbox"])

    source = permits.get_source(cfg["permits"]["source"])
    all_permits, source_info = source.fetch(cfg, data_dir)
    in_area = [p for p in all_permits if p.lat is not None and p.lng is not None and geo.in_bbox(p.lat, p.lng, cfg["bbox"])]
    in_area.sort(key=lambda p: (p.created or "", p.id), reverse=True)
    log.info("%d telecom permits source-wide, %d in area", len(all_permits), len(in_area))

    news = [] if no_news else fetch_news(cfg)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state_path = os.path.join(data_dir, "state.json")
    state = history.load_state(state_path)
    first_build = "last_build" not in state
    if first_build:
        # Nothing is "new" just because the tool is new: date items by their own dates.
        for p in in_area:
            state["permits"].setdefault(p.id, (p.created or now_iso[:10]) + "T00:00:00Z")
        for n in news:
            state["news"].setdefault(n["link"], n["published"] or now_iso)
    history.mark_seen(state["permits"], (p.id for p in in_area), now_iso)
    history.mark_seen(state["news"], (n["link"] for n in news), now_iso)
    state["last_build"] = now_iso
    history.save_state(state_path, state)

    tiles_info = {"mode": "remote"} if no_tiles else ensure_tiles(cfg, site_dir)

    permit_rows = []
    for p in in_area:
        d = p.to_dict()
        d["first_seen"] = state["permits"].get(p.id, now_iso)
        permit_rows.append(d)
    for n in news:
        n["first_seen"] = state["news"].get(n["link"], now_iso)

    out = {
        "generated_at": now_iso,
        "version": __version__,
        "area": {
            "label": cfg["label"],
            "zip": cfg.get("zip"),
            "center": cfg["center"],
            "radius_km": cfg["radius_km"],
            "bbox": cfg["bbox"],
        },
        "new_window_days": cfg["new_window_days"],
        "source": source_info,
        "permits": permit_rows,
        "stats": {"area": summarize(in_area), "source": summarize(all_permits)},
        "news": news,
        "tiles": tiles_info,
        "links": default_links(cfg, source_info),
    }
    out_path = os.path.join(site_dir, "data.json")
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, out_path)
    log.info("wrote %s (%d permits, %d headlines)", out_path, len(permit_rows), len(news))
    return out
