"""The data model: items, observations, alerts. Serialization is explicit --
the store file is a contract, not a dict dump."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

HISTORY_CAP = 200


class StoreKind(StrEnum):
    MERCADO_LIVRE = "mercadolivre"
    AMAZON = "amazon"
    OLX = "olx"
    GENERIC = "jsonld"


@dataclass
class PricePoint:
    at: str
    price: float | None
    status: str                     # "ok" | "stale" | "error"

    def as_dict(self) -> dict[str, Any]:
        return {"at": self.at, "price": self.price, "status": self.status}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PricePoint":
        return cls(at=raw["at"], price=raw.get("price"), status=raw.get("status", "ok"))


@dataclass
class Item:
    id: str                         # stable short hash of the canonical URL
    url: str
    kind: StoreKind
    title: str
    currency: str
    added_at: str
    target: float | None = None     # alert when price <= target
    threshold_pct: float | None = None  # alert on a drop >= this; None = config default
    history: list[PricePoint] = field(default_factory=list)
    low: float | None = None        # lowest price ever observed
    low_at: str | None = None
    available: bool | None = None   # last stock reading
    condition: str = ""             # "" unknown | "novo" | "usado" -- a used price
                                    # never compares against a new-store price
    last_checked_at: str | None = None
    last_status: str = "new"        # "new" | "ok" | "stale" | "error"
    last_error: str | None = None
    last_alert: dict[str, Any] | None = None  # {"kind":..., "value":..., "at":...} for dedup

    def last_price(self) -> float | None:
        for point in reversed(self.history):
            if point.price is not None:
                return point.price
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "kind": str(self.kind),
            "title": self.title,
            "currency": self.currency,
            "target": self.target,
            "threshold_pct": self.threshold_pct,
            "added_at": self.added_at,
            "low": self.low,
            "low_at": self.low_at,
            "available": self.available,
            "condition": self.condition,
            "last_checked_at": self.last_checked_at,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_alert": self.last_alert,
            "history": [point.as_dict() for point in self.history[-HISTORY_CAP:]],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Item":
        return cls(
            id=raw["id"],
            url=raw["url"],
            kind=StoreKind(raw.get("kind", StoreKind.GENERIC)),
            title=raw.get("title", ""),
            currency=raw.get("currency", ""),
            target=raw.get("target"),
            threshold_pct=raw.get("threshold_pct"),
            added_at=raw.get("added_at", ""),
            low=raw.get("low"),
            low_at=raw.get("low_at"),
            available=raw.get("available"),
            condition=raw.get("condition", ""),
            last_checked_at=raw.get("last_checked_at"),
            last_status=raw.get("last_status", "new"),
            last_error=raw.get("last_error"),
            last_alert=raw.get("last_alert"),
            history=[PricePoint.from_dict(point) for point in raw.get("history", [])],
        )


@dataclass
class Alert:
    """One movement worth telling the user about, decided by engine.alerts."""

    kind: str                       # "drop" | "target" | "new_low" | "out_of_stock" | "back_in_stock"
    item_id: str
    title: str
    price: float | None
    previous: float | None
    currency: str
    pct: float | None = None        # drop size, when it is one
    low: bool = False               # all-time low in this watch

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "item_id": self.item_id,
            "title": self.title,
            "price": self.price,
            "previous": self.previous,
            "currency": self.currency,
            "pct": self.pct,
            "low": self.low,
        }
