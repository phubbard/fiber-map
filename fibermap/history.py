"""Remember when each permit and headline was first seen, so the page can say "new"."""
from __future__ import annotations

import json
import os


def load_state(path: str) -> dict:
    try:
        with open(path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    state.setdefault("permits", {})
    state.setdefault("news", {})
    return state


def mark_seen(section: dict, keys, now_iso: str) -> dict:
    for k in keys:
        if k:
            section.setdefault(k, now_iso)
    return section


def save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)
