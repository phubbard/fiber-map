"""Load config.json and fill in the map area from the ZIP when not given explicitly."""
from __future__ import annotations

import json
import os

from . import geo
from .zcta import resolve_zip

DEFAULT_TILE_ZOOMS = [13, 14, 15, 16]


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

    if not (cfg.get("zip") or cfg.get("center") or cfg.get("bbox")):
        raise ValueError("config needs a 'zip', a 'center' or a 'bbox'")
    return cfg


def resolve_area(cfg: dict, cache_dir: str) -> dict:
    """Ensure cfg has center, radius_km, bbox and label. Looks the ZIP up if needed."""
    if cfg.get("bbox"):
        south, west, north, east = cfg["bbox"]
        cfg.setdefault("center", [round((south + north) / 2, 6), round((west + east) / 2, 6)])
        cfg.setdefault("radius_km", round((north - south) / 2 * geo.KM_PER_DEG_LAT, 2))
    else:
        if not cfg.get("center") or not cfg.get("radius_km"):
            z = resolve_zip(cfg["zip"], cache_dir)
            cfg.setdefault("center", [z["lat"], z["lng"]])
            cfg.setdefault("radius_km", z["radius_km"])
        cfg["bbox"] = geo.bbox_from_center(cfg["center"][0], cfg["center"][1], cfg["radius_km"])
    cfg.setdefault("label", f"ZIP {cfg['zip']}" if cfg.get("zip") else "Selected area")
    return cfg
