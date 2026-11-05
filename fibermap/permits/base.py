"""The permit record every source adapter produces."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

# Source status text -> coarse phase used for styling and counting.
PHASES = {
    "opened": "planned",
    "applied": "planned",
    "pending": "planned",
    "issued": "active",
    "inspecting": "active",
    "inspection followup": "active",
    "approved upon final payment": "active",
    "closed": "done",
    "completed": "done",
    "finaled": "done",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "expired": "cancelled",
    "withdrawn": "cancelled",
}


def phase_for(status: str | None) -> str:
    key = (status or "").strip().lower()
    if not key:
        return "unknown"
    return PHASES.get(key, "active")


@dataclass
class Permit:
    id: str
    source: str
    kind: str            # "row" (right-of-way construction), "traffic" (traffic control), "encroachment"
    company: str
    fiber: bool
    status: str
    phase: str
    created: Optional[str]
    issued: Optional[str]
    closed: Optional[str]
    address: str
    lat: Optional[float]
    lng: Optional[float]
    scope: str
    holder: str
    job: Optional[str] = None
    link: Optional[str] = None
    drop: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
