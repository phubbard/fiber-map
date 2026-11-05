"""Bounding boxes and slippy-map tile arithmetic (no dependencies)."""
from __future__ import annotations

import math

KM_PER_DEG_LAT = 111.32


def bbox_from_center(lat: float, lng: float, radius_km: float) -> list[float]:
    """Square box of half-side radius_km around a point: [south, west, north, east]."""
    dlat = radius_km / KM_PER_DEG_LAT
    dlng = radius_km / (KM_PER_DEG_LAT * math.cos(math.radians(lat)))
    return [round(lat - dlat, 6), round(lng - dlng, 6), round(lat + dlat, 6), round(lng + dlng, 6)]


def in_bbox(lat: float, lng: float, bbox: list[float]) -> bool:
    south, west, north, east = bbox
    return south <= lat <= north and west <= lng <= east


def tile_xy(lat: float, lng: float, z: int) -> tuple[int, int]:
    """Web-Mercator tile that contains a point at zoom z."""
    n = 2 ** z
    x = int((lng + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tiles_for_bbox(bbox: list[float], z: int, margin: int = 1) -> list[tuple[int, int, int]]:
    """All (z, x, y) tiles covering the box, plus `margin` tiles on each side."""
    south, west, north, east = bbox
    x0, y0 = tile_xy(north, west, z)
    x1, y1 = tile_xy(south, east, z)
    n = 2 ** z
    return [
        (z, x, y)
        for x in range(x0 - margin, x1 + margin + 1)
        for y in range(y0 - margin, y1 + margin + 1)
        if 0 <= x < n and 0 <= y < n
    ]
