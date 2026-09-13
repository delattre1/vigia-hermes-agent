"""Alert decisions -- pure functions over an item and a new observation.

No IO here, so every rule is testable without network, clock or store.
"""

from __future__ import annotations

from vigia.models import Alert, Item
from vigia.sources.base import Observation


def decide(item: Item, observation: Observation, default_threshold_pct: float) -> list[Alert]:
    """The movements `observation` constitutes, given the item's history."""
    price = observation.price
    if price is None:
        return stock_alerts(item, observation)
    alerts: list[Alert] = []
    previous = item.last_price()
    threshold = item.threshold_pct if item.threshold_pct is not None else default_threshold_pct

    beats_low = item.low is None or price < item.low
    if previous is not None and previous > 0 and price < previous:
        pct = round((previous - price) / previous * 100, 2)
        if pct >= threshold:
            alerts.append(Alert(
                kind="drop", item_id=item.id, title=_title(item, observation),
                price=price, previous=previous, currency=_currency(item, observation),
                pct=pct, low=beats_low,
            ))
    if item.target is not None and price <= item.target and not _already_alerted(item, "target", price):
        alerts.append(Alert(
            kind="target", item_id=item.id, title=_title(item, observation),
            price=price, previous=previous, currency=_currency(item, observation), low=beats_low,
        ))

    if stock_change := stock_alerts(item, observation):
        alerts.extend(stock_change)
    return alerts


def stock_alerts(item: Item, observation: Observation) -> list[Alert]:
    """Stock transitions only -- a steady `available` says nothing."""
    if observation.available is None or item.available is None:
        return []
    if item.available and not observation.available:
        return [Alert(kind="out_of_stock", item_id=item.id, title=_title(item, observation),
                      price=observation.price, previous=item.last_price(), currency=_currency(item, observation))]
    if not item.available and observation.available:
        return [Alert(kind="back_in_stock", item_id=item.id, title=_title(item, observation),
                      price=observation.price, previous=item.last_price(), currency=_currency(item, observation))]
    return []


def new_low(item: Item, observation: Observation) -> bool:
    """Whether this observation beats the item's recorded floor."""
    return observation.price is not None and (item.low is None or observation.price < item.low)


def _title(item: Item, observation: Observation) -> str:
    return observation.title or item.title


def _currency(item: Item, observation: Observation) -> str:
    return observation.currency or item.currency


def _already_alerted(item: Item, kind: str, value: float) -> bool:
    """Dedup: the same kind at the same price never fires twice in a row."""
    last = item.last_alert or {}
    return last.get("kind") == kind and last.get("value") == value
