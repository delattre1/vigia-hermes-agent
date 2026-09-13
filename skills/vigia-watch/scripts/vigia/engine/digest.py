"""The daily digest payload: movements, standing quiet, what needs a word."""

from __future__ import annotations

from typing import Any

from kit import clock

from vigia.store import VigiaStore


def build(store: VigiaStore) -> dict[str, Any]:
    """What the morning digest says, as data. The skill owns the words."""
    items = store.all()
    watched: list[dict[str, Any]] = []
    for item in items:
        last = item.last_price()
        watched.append({
            **store.compact_view(item),
            "at_low": last is not None and item.low is not None and last <= item.low,
            "to_target": last is not None and item.target is not None and last <= item.target,
        })
    return {
        "at": clock.iso(),
        "timezone": _timezone(store),
        "items": watched,
        "stale": [item.id for item in items if item.last_status in ("stale", "error")],
        "quiet": bool(items) and all(
            item.last_status == "ok" and item.last_price() is not None and
            not (item.low and item.last_price() <= item.low)
            for item in items
        ),
    }


def _timezone(store: VigiaStore) -> str:
    from vigia import config
    return str(config.load(store.home)["timezone"])
