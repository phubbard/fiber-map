"""Turn permit-holder and scope text into a telecom company name.

Rules are ordered; the first match wins. Non-telecom utilities are excluded
first so an SDG&E job that mentions fiber is not counted as a fiber build.
Holders whose own name says telecom (Communications, Networks, Broadband, ...)
are kept under that name even when the scope never says "fiber", so a newcomer
shows up before anyone has written a rule for it.
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
    ("Metronet", r"metronet"),
    ("Lumos", r"\blumos\b"),
    ("SiFi Networks", r"\bsifi\b"),
    ("Ezee Fiber", r"\bezee\b"),
    ("Fidium", r"fidium|consolidated comm"),
    ("Brightspeed", r"brightspeed"),
    ("Race Communications", r"\brace comm"),
    ("GigabitNow", r"gigabitnow"),
    ("Ubiquity", r"\bubiquity\b"),
    ("Tillman", r"tillman fiber|\btillman\b"),
    ("Intrepid Fiber", r"intrepid fiber|intrepid networks"),
    ("Starry", r"\bstarry\b"),
    ("Frontier", r"frontier comm"),
    ("Sonic", r"\bsonic\b"),
    ("Ting", r"\bting\b"),
    ("Astound", r"astound|wave broadband|\brcn\b"),
    ("GeoLinks", r"geolinks"),
]

FIBER_RE = re.compile(r"\bfiber\b|\bfibre\b|fiber-?optic", re.I)
# A single customer connection rather than a neighborhood build.
DROP_RE = re.compile(r"demarcation|property owner|customer premise|service drop|\bdrop\b|to the building|existing (?:customer|business)", re.I)
JOB_RE = re.compile(r"\(\s*(?:job\s*)?([A-Z0-9][A-Z0-9 .\-]{3,}?)\s*\)", re.I)

# A holder whose name says it is a connectivity company.
TELECOM_HOLDER_RE = re.compile(
    r"communications?|networks?|telecom|telephone|broadband|\bfiber\b|\bfibre\b|fibernet|lightwave|wireless|internet|\bisp\b",
    re.I,
)
_SUFFIX_RE = re.compile(
    r"[,.\s]*\b(inc|llc|l\.l\.c|corp|corporation|co|company|ltd|lp|l\.p|of california|california|west|usa|na|north america)\b\.?\s*$",
    re.I,
)


def company_from_holder(holder: str | None) -> str | None:
    """A tidy company name from a telecom-looking holder, else None.

    "BOLDYN NETWORKS - Scott Lewis" -> "Boldyn Networks"; "HP COMMUNICATIONS INC" -> "HP Communications".
    """
    name = re.split(r"\s+[-/|]\s+|\s+c/o\s+|\s+attn", (holder or "").strip(), maxsplit=1, flags=re.I)[0].strip()
    if not name or not TELECOM_HOLDER_RE.search(name):
        return None
    prev = None
    while prev != name:
        prev = name
        name = _SUFFIX_RE.sub("", name).strip(" ,.-/")
    name = re.sub(r"\s+", " ", name)
    if not name:
        return None
    if name.isupper() or name.islower():
        name = " ".join(w if (len(w) <= 3 and w.isupper()) else w.title() for w in name.split(" "))
    return name


def _looks_like_person(holder: str) -> bool:
    words = holder.replace(".", "").split()
    return len(words) == 2 and all(w.replace("'", "").replace("-", "").isalpha() for w in words) \
        and not TELECOM_HOLDER_RE.search(holder) and not _COMPANY_TOKEN_RE.search(holder)


_COMPANY_TOKEN_RE = re.compile(r"\b(inc|llc|corp|co|company|group|partners|associates|services|solutions|enterprises|industries|holdings)\b", re.I)
WATCHLIST_SKIP_RE = re.compile(
    r"\bwater\b|homes\b|builders|paving|concrete|construction|engineering|smart city|landscap|plumbing|roofing|solar|"
    r"\bgas\b|pipeline|transit|mta\b|school|university|county of|city of|caltrans|church|realty|properties|apartments",
    re.I,
)


# Scope words that smell like telecom construction even when nobody is named.
TELECOM_SCOPE_RE = re.compile(
    r"conduit|\bducts?\b|hand ?holes?|vault|splice|strand|pull ?box|antenna|small cell|\bnode\b|telecom|\bcable\b|\bfiber\b",
    re.I,
)


def telecom_scope(text: str | None) -> bool:
    return bool(TELECOM_SCOPE_RE.search(text or ""))


def watchlist_candidate(holder: str, telecomish: int = 0) -> bool:
    """Worth a human look: not an obviously non-telecom outfit, and either a company
    name or a person with at least two permits that describe telecom-style work."""
    h = (holder or "").strip()
    if not h or EXCLUDE.search(h) or WATCHLIST_SKIP_RE.search(h):
        return False
    return telecomish >= 2 or not _looks_like_person(h)


def classify(holder: str, scope: str, extra_rules: list[dict] | None = None) -> str | None:
    """Return the company name, or None if this is not telecom work."""
    blob = f"{holder or ''} {scope or ''}"
    if EXCLUDE.search(holder or ""):
        return None
    rules = [(r["name"], r["pattern"]) for r in (extra_rules or [])] + COMPANY_RULES
    for name, pattern in rules:
        if re.search(pattern, blob, re.I):
            return name
    by_holder = company_from_holder(holder)
    if by_holder:
        return by_holder
    if FIBER_RE.search(blob) and not EXCLUDE.search(blob):
        return "Fiber (other)"
    return None


def mentions_fiber(text: str | None) -> bool:
    return bool(FIBER_RE.search(text or ""))


def is_drop(text: str | None) -> bool:
    """True when the scope describes a drop to one property (an SAI-to-demarcation run)."""
    return bool(DROP_RE.search(text or ""))


def parse_job(scope: str | None) -> str | None:
    m = JOB_RE.search(scope or "")
    return m.group(1).strip().upper() if m else None
