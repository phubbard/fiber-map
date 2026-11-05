"""Permit source adapters. Each exposes fetch(cfg, cache_dir) -> (list[Permit], info)."""
from __future__ import annotations

from . import sandiego
from .base import Permit, phase_for

SOURCES = {"sandiego": sandiego}


class _NoSource:
    SOURCE = "none"
    LABEL = "No permit source"

    @staticmethod
    def fetch(cfg, cache_dir):
        return [], {"source": "none", "label": "No permit source", "url": None, "extra_links": []}


def get_source(name: str):
    if name in ("none", "", None):
        return _NoSource
    try:
        return SOURCES[name]
    except KeyError as e:
        raise ValueError(f"unknown permit source {name!r}; known: {sorted(SOURCES)} or 'none'") from e


__all__ = ["Permit", "phase_for", "get_source", "SOURCES"]
