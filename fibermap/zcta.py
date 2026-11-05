"""Resolve a ZIP code to a centre point and radius using the Census ZCTA gazetteer.

The gazetteer is a ~1 MB zip from census.gov, cached after the first run. ZCTAs
are the Census approximation of ZIP codes; good enough to centre a map.
"""
from __future__ import annotations

import io
import logging
import math
import os
import zipfile

from .http import fetch_cached

log = logging.getLogger(__name__)

GAZETTEER_URLS = [
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_zcta_national.zip",
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_zcta_national.zip",
]


def _download(cache_dir: str) -> str:
    dest = os.path.join(cache_dir, "gazetteer_zcta.zip")
    if os.path.exists(dest):
        return dest
    last_err: Exception | None = None
    for url in GAZETTEER_URLS:
        try:
            return fetch_cached(url, dest)
        except Exception as e:  # noqa: BLE001 - try the next vintage
            last_err = e
            log.warning("gazetteer download failed for %s: %s", url, e)
    raise RuntimeError(f"could not download the Census ZCTA gazetteer: {last_err}")


def parse_gazetteer(text: str, zip_code: str) -> dict | None:
    """Find one ZCTA row in the tab-separated gazetteer text."""
    lines = text.splitlines()
    if not lines:
        return None
    header = [h.strip().upper() for h in lines[0].split("\t")]
    try:
        i_geoid = header.index("GEOID")
        i_aland = header.index("ALAND")
        i_lat = header.index("INTPTLAT")
        i_lng = header.index("INTPTLONG")
    except ValueError as e:
        raise RuntimeError(f"unexpected gazetteer header: {header}") from e
    for line in lines[1:]:
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) <= i_lng or cols[i_geoid] != zip_code:
            continue
        area_km2 = float(cols[i_aland]) / 1e6
        return {
            "zip": zip_code,
            "lat": float(cols[i_lat]),
            "lng": float(cols[i_lng]),
            "land_km2": round(area_km2, 2),
            "radius_km": suggested_radius_km(area_km2),
        }
    return None


def suggested_radius_km(land_km2: float) -> float:
    """Half-side of a square that comfortably contains a ZCTA of this land area."""
    if land_km2 <= 0:
        return 2.0
    return max(1.0, round(math.sqrt(land_km2 / math.pi) * 1.2, 1))


def resolve_zip(zip_code: str, cache_dir: str) -> dict:
    zip_code = str(zip_code).strip().zfill(5)
    path = _download(cache_dir)
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not names:
            raise RuntimeError("gazetteer zip has no .txt member")
        with zf.open(names[0]) as f:
            text = io.TextIOWrapper(f, encoding="latin-1").read()
    row = parse_gazetteer(text, zip_code)
    if row is None:
        raise ValueError(f"ZIP {zip_code} not found in the Census ZCTA gazetteer")
    return row
