"""The watched-items store: one JSON file in the agent's own directory."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from kit.jsonio import load_json, save_json_atomic

from vigia.models import Item, StoreKind

_ITEMS_FILE = "items.json"


def store_path(home: str) -> str:
    return f"{home}/{_ITEMS_FILE}"


def item_id_for(url: str) -> str:
    """A stable, short id: the same product, however tracked, is one item."""
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:10]


def canonical_url(url: str) -> str:
    """Strip tracking noise so re-sends of the same product deduplicate."""
    return re.sub(r"([?#]).*$", "", url.strip())


class VigiaStore:
    """The whole watched state, loaded once, written whole and atomically."""

    def __init__(self, home: str) -> None:
        self.home = home
        raw = load_json(store_path(home), {"items": []}) or {}
        self.items: dict[str, Item] = {
            data["id"]: Item.from_dict(data) for data in raw.get("items", [])
        }

    def save(self) -> None:
        save_json_atomic(
            store_path(self.home),
            {"items": [item.to_dict() for item in self.items.values()]},
        )

    def get(self, item_id: str) -> Item:
        if item_id not in self.items:
            raise KeyError(f"no watched item {item_id}")
        return self.items[item_id]

    def add(self, item: Item) -> Item:
        self.items[item.id] = item
        return item

    def remove(self, item_id: str) -> Item:
        return self.items.pop(item_id)

    def all(self) -> list[Item]:
        return sorted(self.items.values(), key=lambda item: item.added_at)

    def kind_for_url(self, url: str) -> StoreKind:
        host = url.split("//", 1)[-1].split("/", 1)[0].lower()
        if "mercadolivre.com" in host or "mercadolibre.com" in host:
            return StoreKind.MERCADO_LIVRE
        if "amazon." in host:
            return StoreKind.AMAZON
        return StoreKind.GENERIC

    def compact_view(self, item: Item) -> dict[str, Any]:
        """What a reply or a digest needs, history summarized."""
        return {
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "kind": str(item.kind),
            "currency": item.currency,
            "price": item.last_price(),
            "target": item.target,
            "threshold_pct": item.threshold_pct,
            "low": item.low,
            "available": item.available,
            "last_status": item.last_status,
            "last_checked_at": item.last_checked_at,
            "last_error": item.last_error,
            "observations": len(item.history),
            "added_at": item.added_at,
        }
