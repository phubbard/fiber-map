"""Turn permit-holder and scope text into a telecom company name.

Rules are ordered; the first match wins. Non-telecom utilities are excluded
first so an SDG&E job that mentions fiber is not counted as a fiber build.
"""
from __future__ import annotations

import re

EXCLUDE = re.compile(
    r"sdg\s*&\s*e|san diego gas|gas\s*&\s*electric|city of san diego|water meter|sewer lateral|storm drain",
    re.I,
)

COMPANY_RULES: list[tuple[str, str]] = [
    ("AT&T", r"at\s*&\s*t|\batt\b|pacific bell|\bsbc\b"),
    ("Spectrum", r"charter|spectrum|time warner"),
    ("Cox", r"\bcox\b"),
    ("Wyyerd", r"wyyerd"),
    ("Verizon", r"verizon|mci metro|\bmci\b"),
    ("Zayo", r"\bzayo\b"),
    ("Crown Castle", r"crown castle"),
    ("Google Fiber", r"google fiber|webpass|\bgfiber\b"),
    ("T-Mobile", r"t-?mobile"),
    ("Lumen", r"\blumen\b|centurylink|level ?3|quantum fiber"),
    ("Frontier", r"frontier comm"),
    ("Sonic", r"\bsonic\b"),
    ("Ting", r"\bting\b"),
    ("Astound", r"astound|wave broadband|\brcn\b"),
    ("GeoLinks", r"geolinks"),
    ("Fiber (other)", r"\bfiber\b|\bfibre\b|fiber-?optic"),
]

FIBER_RE = re.compile(r"\bfiber\b|\bfibre\b|fiber-?optic", re.I)
# A single customer connection rather than a neighborhood build.
DROP_RE = re.compile(r"demarcation|property owner|customer premise|service drop|\bdrop\b|to the building|existing (?:customer|business)", re.I)
JOB_RE = re.compile(r"\(\s*(?:job\s*)?([A-Z0-9][A-Z0-9 .\-]{3,}?)\s*\)", re.I)


def classify(holder: str, scope: str, extra_rules: list[dict] | None = None) -> str | None:
    """Return the company name, or None if this is not telecom work."""
    blob = f"{holder or ''} {scope or ''}"
    if EXCLUDE.search(blob):
        return None
    rules = [(r["name"], r["pattern"]) for r in (extra_rules or [])] + COMPANY_RULES
    for name, pattern in rules:
        if re.search(pattern, blob, re.I):
            return name
    return None


def mentions_fiber(text: str | None) -> bool:
    return bool(FIBER_RE.search(text or ""))


def is_drop(text: str | None) -> bool:
    """True when the scope describes a drop to one property (an SAI-to-demarcation run)."""
    return bool(DROP_RE.search(text or ""))


def parse_job(scope: str | None) -> str | None:
    m = JOB_RE.search(scope or "")
    return m.group(1).strip().upper() if m else None
