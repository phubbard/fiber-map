"""Load config.json and normalise it to a list of areas.

Either shape works:
  {"zip": "92122", ...}                       one area (the original layout)
  {"areas": [{"zip": "92122"}, {"zip": "92126", "label": "Mira Mesa (92126)"}], ...}
Per-area keys: zip, label, center, radius_km, bbox, zoom_offset, news.queries (added to
the shared ones), links (added to the shared ones).
"""
from __future__ import annotations

import json
import os
import re

from . import geo
from .zcta import resolve_zip

DEFAULT_TILE_ZOOMS = [13, 14, 15, 16]
AREA_KEYS = ("zip", "label", "center", "radius_km", "bbox", "zoom_offset", "news", "links")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "area").lower()).strip("-") or "area"


def normalise_areas(cfg: dict) -> list[dict]:
    raw = cfg.get("areas")
    if raw is None:
        raw = [{k: cfg[k] for k in AREA_KEYS if k in cfg and k not in ("news", "links")}]
    if not isinstance(raw, list) or not raw:
        raise ValueError("'areas' must be a non-empty list")
    areas, keys = [], set()
    for item in raw:
        a = dict(item)
        if not (a.get("zip") or a.get("center") or a.get("bbox")):
            raise ValueError(f"area {a!r} needs a 'zip', a 'center' or a 'bbox'")
        if a.get("zip"):
            a["zip"] = str(a["zip"]).strip().zfill(5)
        a.setdefault("zoom_offset", cfg.get("zoom_offset", 1))
        news = a.setdefault("news", {})
        news.setdefault("queries", [])
        a.setdefault("links", [])
        a["key"] = a.get("key") or a.get("zip") or _slug(a.get("label", ""))
        if a["key"] in keys:
            raise ValueError(f"duplicate area key {a['key']!r}")
        keys.add(a["key"])
        areas.append(a)
    return areas


def load(path: str) -> dict:
    with open(path) as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise ValueError("config must be a JSON object")
    base = os.path.dirname(os.path.abspath(path))
    cfg["_base_dir"] = base
    cfg["data_dir"] = os.path.join(base, cfg.get("data_dir", "data"))
    cfg["site_dir"] = os.path.join(base, cfg.get("site_dir", "site"))

    permits = cfg.setdefault("permits", {})
    permits.setdefault("source", "sandiego")
    permits.setdefault("years_back", 2)
    permits.setdefault("extra_companies", [])

    tiles = cfg.setdefault("tiles", {})
    tiles.setdefault("mode", "local")
    tiles.setdefault("zooms", list(DEFAULT_TILE_ZOOMS))

    news = cfg.setdefault("news", {})
    news.setdefault("queries", [])
    news.setdefault("max_age_days", 180)
    news.setdefault("per_query", 15)

    cfg.setdefault("new_window_days", 7)
    cfg.setdefault("links", [])
    cfg["areas"] = normalise_areas(cfg)
    return cfg


def resolve_area(area: dict, cache_dir: str) -> dict:
    """Ensure an area has center, radius_km, bbox and label. Looks the ZIP up if needed."""
    if area.get("bbox"):
        south, west, north, east = area["bbox"]
        area.setdefault("center", [round((south + north) / 2, 6), round((west + east) / 2, 6)])
        area.setdefault("radius_km", round((north - south) / 2 * geo.KM_PER_DEG_LAT, 2))
    else:
        if not area.get("center") or not area.get("radius_km"):
            z = resolve_zip(area["zip"], cache_dir)
            area.setdefault("center", [z["lat"], z["lng"]])
            area.setdefault("radius_km", z["radius_km"])
        area["bbox"] = geo.bbox_from_center(area["center"][0], area["center"][1], area["radius_km"])
    area.setdefault("label", f"ZIP {area['zip']}" if area.get("zip") else "Selected area")
    return area
