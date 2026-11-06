"""Build the site data: a shared index (site/data.json + data.js) and one file per
area under site/areas/ (<key>.json + <key>.js)."""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from . import __version__, config, geo, history, permits
from .news import fetch_news
from .permits.classify import watchlist_candidate
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
        if p.phase in ("active", "planned") and p.kind != "traffic":
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


def _iso(value: str | None) -> str | None:
    """Normalise a date or timestamp to the ISO form used in state.json."""
    if not value:
        return None
    return value + "T00:00:00Z" if len(value) == 10 else value


def mark_section(state: dict, key: str, items, now_iso: str) -> dict:
    """Record first-seen dates for `items` = (id, own_date). An item is dated by its own
    date (permit created, story published) when it has one, so a rule change that
    surfaces old permits never makes them look new; `now` is only the fallback."""
    section = state.setdefault(key, {})
    for k, own in items:
        if k and k not in section:
            section[k] = _iso(own) or now_iso
    return section


def compute_alerts(in_area: list[permits.Permit], state: dict, now_iso: str, window_days: int, source_label: str) -> list[dict]:
    """Banner lines: companies new to the area or to the source, and new right-of-way permits here."""
    now = datetime.strptime(now_iso, "%Y-%m-%dT%H:%M:%SZ")
    cutoff = (now - timedelta(days=window_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen_permits = state.get("permits", {})
    seen_companies = state.get("companies", {})
    first_in_area: dict[str, str] = {}
    for p in in_area:
        if p.kind == "traffic":   # construction permits only; traffic control is maintenance noise
            continue
        fs = seen_permits.get(p.id, now_iso)
        if p.company not in first_in_area or fs < first_in_area[p.company]:
            first_in_area[p.company] = fs
    alerts = []
    companies = set(first_in_area) | {co for co, fs in seen_companies.items() if fs >= cutoff}
    for co in sorted(companies):
        area_fs = first_in_area.get(co)
        src_fs = seen_companies.get(co)
        new_area = area_fs is not None and area_fs >= cutoff
        new_src = src_fs is not None and src_fs >= cutoff
        if not (new_area or new_src):
            continue
        if new_src and new_area:
            text = f"{co} pulled its first {source_label} permit, and it is in this area"
        elif new_src:
            text = f"{co} pulled its first {source_label} permit (outside this area)"
        else:
            text = f"{co} pulled its first permit in this area"
        dates = [d for d, flag in ((area_fs, new_area), (src_fs, new_src)) if flag and d]
        alerts.append({"kind": "new_company", "date": max(dates), "company": co, "text": text})
    for p in in_area:
        if p.kind == "traffic":
            continue
        fs = seen_permits.get(p.id, now_iso)
        if fs < cutoff:
            continue
        what = "fiber right-of-way permit" if p.fiber else ("encroachment permit" if p.kind == "encroachment" else "right-of-way permit")
        where = p.address or "an address not given yet"
        alerts.append({
            "kind": "new_fiber_permit" if p.fiber else "new_permit",
            "date": fs, "company": p.company, "permit_id": p.id,
            "text": f"{p.company}: new {what} at {where}" + (" (single drop)" if p.drop else ""),
        })
    alerts.sort(key=lambda a: (a["date"], a["kind"]), reverse=True)
    return alerts


def watchlist(unmatched: dict, seen_holders: dict, active_days: int = 365, limit: int = 20) -> dict:
    """Frequent right-of-way permit holders that matched no telecom rule, so a newcomer
    with an unfamiliar name can be spotted and given a rule."""
    since = (date.today() - timedelta(days=active_days)).isoformat()
    rows = []
    for holder, u in unmatched.items():
        telecomish = u.get("telecomish", 0)
        if (u.get("last_created") or "") < since or not watchlist_candidate(holder, telecomish):
            continue
        if u["count"] < 2 and telecomish == 0:
            continue
        rows.append({"holder": holder, "count": u["count"], "telecomish": telecomish,
                     "first_created": u.get("first_created") or None, "first_seen": seen_holders.get(holder)})
    rows.sort(key=lambda r: (-r["telecomish"], -r["count"], r["holder"]))
    return {"unmatched_holders": rows[:limit], "active_since": since}


def default_links(area: dict, source_info: dict, shared_links: list[dict]) -> list[dict]:
    lat, lng = area["center"]
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
    links.extend(shared_links or [])
    links.extend(area.get("links") or [])
    return links


def write_data(path_base: str, js_statement: str, obj: dict) -> None:
    """Write obj as <path_base>.json and as <path_base>.js (the JS form works over file://;
    '</' is escaped so no string can end the script tag)."""
    os.makedirs(os.path.dirname(path_base) or ".", exist_ok=True)
    tmp = path_base + ".json.tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path_base + ".json")
    tmp = path_base + ".js.tmp"
    with open(tmp, "w") as f:
        f.write(js_statement % json.dumps(obj).replace("</", "<\\/") + "\n")
    os.replace(tmp, path_base + ".js")


def merged_news_queries(cfg: dict, areas: list[dict]) -> list[dict]:
    queries = list(cfg["news"].get("queries", []))
    seen = {(q["label"], q["q"]) for q in queries}
    for a in areas:
        for q in a.get("news", {}).get("queries", []):
            if (q["label"], q["q"]) not in seen:
                queries.append(q)
                seen.add((q["label"], q["q"]))
    return queries


def build(config_path: str, no_tiles: bool = False, no_news: bool = False) -> dict:
    cfg = config.load(config_path)
    data_dir, site_dir = cfg["data_dir"], cfg["site_dir"]
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(site_dir, "areas"), exist_ok=True)
    areas = [config.resolve_area(a, data_dir) for a in cfg["areas"]]
    for a in areas:
        log.info("area %s (%s) center=%s radius=%.1f km", a["label"], a["key"], a["center"], a["radius_km"])

    source = permits.get_source(cfg["permits"]["source"])
    all_permits, source_info = source.fetch(cfg, data_dir)
    rows_by_area: dict[str, list[permits.Permit]] = {}
    for a in areas:
        rows = [p for p in all_permits if p.lat is not None and p.lng is not None and geo.in_bbox(p.lat, p.lng, a["bbox"])]
        rows.sort(key=lambda p: (p.created or "", p.id), reverse=True)
        rows_by_area[a["key"]] = rows
        log.info("%s: %d telecom permits in area", a["label"], len(rows))
    log.info("%d telecom permits source-wide", len(all_permits))

    news_cfg = dict(cfg)
    news_cfg["news"] = dict(cfg["news"], queries=merged_news_queries(cfg, areas))
    news = [] if no_news else fetch_news(news_cfg)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    state_path = os.path.join(data_dir, "state.json")
    state = history.load_state(state_path)
    co_first: dict[str, str] = {}
    for p in all_permits:
        if p.created and (p.company not in co_first or p.created < co_first[p.company]):
            co_first[p.company] = p.created
    unmatched = source_info.pop("unmatched_holders", {}) or {}
    mark_section(state, "permits", ((p.id, p.created) for rows in rows_by_area.values() for p in rows), now_iso)
    mark_section(state, "news", ((n["link"], n["published"]) for n in news), now_iso)
    mark_section(state, "companies", co_first.items(), now_iso)
    mark_section(state, "holders", ((h, u.get("first_created")) for h, u in unmatched.items()), now_iso)
    watch = watchlist(unmatched, state["holders"])
    state["last_build"] = now_iso
    history.save_state(state_path, state)

    tiles_info: dict = {"mode": "remote"}
    if not no_tiles:
        tiles_info = {"mode": cfg["tiles"].get("mode", "local"), "zooms": sorted(int(z) for z in cfg["tiles"]["zooms"]),
                      "attribution": "&copy; OpenStreetMap contributors", "fetched": 0, "present": 0}
    area_index = []
    for a in areas:
        rows = rows_by_area[a["key"]]
        alerts = compute_alerts(rows, state, now_iso, cfg["new_window_days"], source_info.get("label", "source"))
        if not no_tiles and tiles_info["mode"] == "local":
            t = ensure_tiles(cfg["tiles"], a["bbox"], site_dir)
            tiles_info["fetched"] += t.get("fetched", 0)
            tiles_info["present"] += t.get("present", 0)
        stats_area = summarize(rows)
        area_out = {
            "key": a["key"], "label": a["label"], "zip": a.get("zip"),
            "center": a["center"], "radius_km": a["radius_km"], "bbox": a["bbox"], "zoom_offset": a["zoom_offset"],
            "permits": [dict(p.to_dict(), first_seen=state["permits"].get(p.id, now_iso)) for p in rows],
            "stats": stats_area,
            "alerts": alerts,
            "links": default_links(a, source_info, cfg["links"]),
        }
        write_data(os.path.join(site_dir, "areas", a["key"]),
                   'window.FIBERMAP_AREAS = window.FIBERMAP_AREAS || {}; window.FIBERMAP_AREAS[%s] = %%s;' % json.dumps(a["key"]),
                   area_out)
        area_index.append({
            "key": a["key"], "label": a["label"], "zip": a.get("zip"),
            "permits": len(rows), "open": stats_area["active"],
            "fiber_12mo": sum(c.get("fiber", 0) for c in stats_area["trailing12"].values()),
            "alerts": len(alerts),
        })
        log.info("%s: %d alerts", a["label"], len(alerts))

    for n in news:
        n["first_seen"] = state["news"].get(n["link"], now_iso)
    out = {
        "generated_at": now_iso,
        "version": __version__,
        "new_window_days": cfg["new_window_days"],
        "source": source_info,
        "stats": {"source": summarize(all_permits)},
        "news": news,
        "watchlist": watch,
        "tiles": tiles_info,
        "areas": area_index,
        "default_area": area_index[0]["key"],
    }
    write_data(os.path.join(site_dir, "data"), "window.FIBERMAP_DATA = %s;", out)
    log.info("wrote %s/data.json (%d areas, %d headlines)", site_dir, len(area_index), len(news))
    return out
