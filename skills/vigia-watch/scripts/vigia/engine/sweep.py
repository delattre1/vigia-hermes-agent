"""The sweep: read every item, record history, decide alerts, never die on one."""

from __future__ import annotations

from typing import Any

from kit import clock

from vigia import config, sources
from vigia.engine import alerts as alerts_engine
from vigia.models import Alert, Item, PricePoint
from vigia.sources.base import Observation
from vigia.store import VigiaStore


def check_item(store: VigiaStore, item: Item, default_threshold_pct: float) -> tuple[list[Alert], str | None]:
    """One item, one read. Returns (alerts, error). The store is updated in place."""
    try:
        observation: Observation = sources.observe(str(item.kind), item.url)
    except Exception as error:  # a sweep survives anything one item raises
        failure = str(error)
        item.last_checked_at = clock.iso()
        item.last_status = "stale"
        item.last_error = failure[:300]
        item.history.append(PricePoint(at=item.last_checked_at, price=None, status="stale"))
        _trim(item)
        store.save()
        return [], failure

    decided = alerts_engine.decide(item, observation, default_threshold_pct)
    _fold(store, item, observation, decided)
    return decided, None


def check_all(store: VigiaStore, *, only_ids: list[str] | None = None) -> dict[str, Any]:
    """The whole watch list. One bad item never ends the sweep."""
    default_threshold = float(config.load(store.home)["threshold_pct"])
    items = store.all()
    if only_ids is not None:
        wanted = set(only_ids)
        items = [item for item in items if item.id in wanted]

    alerts: list[Alert] = []
    failures: list[dict[str, str]] = []
    for item in items:
        found, error = check_item(store, item, default_threshold)
        alerts.extend(found)
        if error is not None:
            failures.append({"id": item.id, "title": item.title, "error": error})
    return {
        "checked": len(items),
        "alerts": [alert.as_dict() for alert in alerts],
        "failed": failures,
        "at": clock.iso(),
    }


def apply_observation(store: VigiaStore, item: Item, observation: Observation) -> list[Alert]:
    """Fold any good observation in -- first read, sweep read, screenshot."""
    decided = alerts_engine.decide(item, observation, float(config.load(store.home)["threshold_pct"]))
    _fold(store, item, observation, decided)
    return decided


def apply_manual(store: VigiaStore, item: Item, price: float, title: str | None,
                  currency: str | None) -> list[Alert]:
    """An observation the model read off a screenshot, folded in like a scrape."""
    observation = Observation(
        title=title or item.title,
        price=price,
        currency=currency or item.currency,
        available=None,
    )
    return apply_observation(store, item, observation)


def _fold(store: VigiaStore, item: Item, observation: Observation, decided: list[Alert]) -> None:
    """Fold one good observation into the item: history, floor, stock, dedup."""
    instant = clock.iso()
    item.title = observation.title or item.title
    item.currency = observation.currency or item.currency
    item.available = observation.available if observation.available is not None else item.available
    item.last_checked_at = instant
    item.last_status = "ok"
    item.last_error = None

    item.history.append(PricePoint(at=instant, price=observation.price, status="ok"))
    _trim(item)
    if alerts_engine.new_low(item, observation):
        item.low = observation.price
        item.low_at = instant
    # Record the strongest alert of this read, so the same one cannot repeat.
    if decided:
        item.last_alert = {"kind": decided[0].kind, "value": decided[0].price, "at": instant}
    store.save()


def _trim(item: Item) -> None:
    if len(item.history) > 200:
        del item.history[:-200]
