"""Watchlist operations: add, list, remove. The conversational layer above."""

from __future__ import annotations

from typing import Any

from kit import clock

from vigia import store as store_module
from vigia.models import Item
from vigia.store import VigiaStore


def add(store: VigiaStore, url: str, *, title: str, currency: str, target: float | None,
        threshold_pct: float | None) -> Item:
    """Register a product. Prices arrive later, at the first sweep or observation."""
    canonical = store_module.canonical_url(url)
    item = Item(
        id=store_module.item_id_for(canonical),
        url=canonical,
        kind=store.kind_for_url(canonical),
        title=title,
        currency=currency,
        added_at=clock.iso(),
        target=target,
        threshold_pct=threshold_pct,
    )
    return store.add(item)


def remove(store: VigiaStore, item_id: str) -> Item:
    return store.remove(item_id)


def summary(store: VigiaStore) -> list[dict[str, Any]]:
    return [store.compact_view(item) for item in store.all()]
