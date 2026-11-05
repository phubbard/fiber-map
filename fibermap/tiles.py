"""Cache OpenStreetMap tiles for the area at build time so viewers' browsers never
talk to a third party. A few hundred tiles, fetched once, with a proper User-Agent
as the OSM tile usage policy asks."""
from __future__ import annotations

import logging
import os
import time

from .geo import tiles_for_bbox
from .http import fetch_bytes

log = logging.getLogger(__name__)

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTRIBUTION = "&copy; OpenStreetMap contributors"


def ensure_tiles(cfg: dict, site_dir: str, max_fetch: int = 1500) -> dict:
    tiles_cfg = cfg["tiles"]
    zooms = sorted(int(z) for z in tiles_cfg.get("zooms", []))
    info = {"mode": tiles_cfg.get("mode", "local"), "zooms": zooms, "attribution": ATTRIBUTION}
    if info["mode"] != "local":
        return info
    fetched = present = 0
    for z in zooms:
        for (_, x, y) in tiles_for_bbox(cfg["bbox"], z, margin=1):
            dest = os.path.join(site_dir, "tiles", str(z), str(x), f"{y}.png")
            if os.path.exists(dest):
                present += 1
                continue
            if fetched >= max_fetch:
                log.warning("tile fetch cap (%d) reached; rerun to finish", max_fetch)
                info.update(fetched=fetched, present=present, capped=True)
                return info
            data, _ = fetch_bytes(TILE_URL.format(z=z, x=x, y=y), timeout=30)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            fetched += 1
            time.sleep(0.1)
    log.info("tiles: %d present, %d fetched", present, fetched)
    info.update(fetched=fetched, present=present, capped=False)
    return info
