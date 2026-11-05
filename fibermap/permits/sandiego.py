"""City of San Diego permit source: Development Services approvals on DataSD.

Daily CSVs, one per creation year, with lat/long, permit holder and a scope line
that names the job ("AT&T FIBER (A05EE9V): Public Right of Way Permit ...").
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import date
from typing import Iterable, Iterator

from ..http import fetch_cached
from .base import Permit, phase_for
from .classify import classify, is_drop, mentions_fiber, parse_job

log = logging.getLogger(__name__)

SOURCE = "sandiego"
LABEL = "City of San Diego"
DATASET_URL = "https://data.sandiego.gov/datasets/development-permits/"
CSV_URL = "https://seshat.datasd.org/development_permits/approvals_created_{year}_datasd.csv"
EXTRA_LINKS = [
    {"label": "City Project Finder", "url": "https://sandiego-public.dotmapsapp.com/map"},
    {"label": "DataSD permits dataset", "url": DATASET_URL},
]

KIND_NEEDLES = [
    ("traffic control", "traffic"),
    ("right of way", "row"),
    ("right-of-way", "row"),
    ("encroach", "encroachment"),
]


def kind_for(approval_type: str | None) -> str | None:
    t = (approval_type or "").lower()
    for needle, kind in KIND_NEEDLES:
        if needle in t:
            return kind
    return None


def _date(value: str | None) -> str | None:
    v = (value or "").strip()
    return v[:10] if len(v) >= 10 and v[4] == "-" else None


def _float(value: str | None) -> float | None:
    try:
        f = float((value or "").strip())
    except ValueError:
        return None
    return f if f != 0.0 else None


def parse_rows(rows: Iterable[dict], extra_rules: list[dict] | None = None) -> Iterator[Permit]:
    for row in rows:
        kind = kind_for(row.get("APPROVAL_TYPE"))
        if not kind:
            continue
        holder = (row.get("APPROVAL_PERMIT_HOLDER") or "").strip()
        parts = []
        for key in ("PROJECT_TITLE", "PROJECT_SCOPE", "APPROVAL_SCOPE"):
            text = (row.get(key) or "").strip()
            if text and text not in parts:
                parts.append(text)
        scope = " | ".join(parts)
        company = classify(holder, scope, extra_rules)
        if not company:
            continue
        yield Permit(
            id=(row.get("APPROVAL_ID") or "").strip(),
            source=SOURCE,
            kind=kind,
            company=company,
            fiber=mentions_fiber(scope),
            status=(row.get("APPROVAL_STATUS") or "").strip(),
            phase=phase_for(row.get("APPROVAL_STATUS")),
            created=_date(row.get("APPROVAL_CREATE_DATE")),
            issued=_date(row.get("APPROVAL_ISSUE_DATE")),
            closed=_date(row.get("APPROVAL_CLOSE_DATE")),
            address=(row.get("GIS_ADDRESS") or "").strip(),
            lat=_float(row.get("GIS_LATITUDE")),
            lng=_float(row.get("GIS_LONGITUDE")),
            scope=scope[:400],
            holder=holder,
            job=parse_job(scope),
            drop=is_drop(scope),
        )


def fetch(cfg: dict, cache_dir: str) -> tuple[list[Permit], dict]:
    years_back = int(cfg["permits"].get("years_back", 2))
    this_year = date.today().year
    permits: dict[str, Permit] = {}
    for year in range(this_year - years_back, this_year + 1):
        url = CSV_URL.format(year=year)
        path = fetch_cached(url, os.path.join(cache_dir, f"sandiego_created_{year}.csv"))
        n = 0
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            for p in parse_rows(csv.DictReader(f), cfg["permits"].get("extra_companies")):
                if p.id:
                    permits[p.id] = p
                    n += 1
        log.info("%s: %d telecom permits from %d", LABEL, n, year)
    info = {"source": SOURCE, "label": LABEL, "url": DATASET_URL, "extra_links": EXTRA_LINKS}
    return list(permits.values()), info
