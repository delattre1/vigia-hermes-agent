"""The alert rules, pure: threshold drops, targets, floors, stock transitions."""

from kit import clock

from vigia.engine.alerts import decide, new_low
from vigia.models import Item, PricePoint, StoreKind
from vigia.sources.base import Observation


def item(**overrides) -> Item:
    base = dict(
        id="abc123", url="https://x/p/1", kind=StoreKind.GENERIC, title="Product",
        currency="BRL", added_at=clock.iso(),
    )
    base.update(overrides)
    return Item(**base)


def observation(price, available=None, title="Product") -> Observation:
    return Observation(title=title, price=price, currency="BRL", available=available)


def seed_history(watched: Item, *prices) -> Item:
    for price in prices:
        watched.history.append(PricePoint(at=clock.iso(), price=price, status="ok"))
        if price is not None and (watched.low is None or price < watched.low):
            watched.low = price
    return watched


class TestDrops:
    def test_drop_past_threshold_alerts_with_pct(self):
        watched = seed_history(item(threshold_pct=5.0), 100.0)
        alerts = decide(watched, observation(90.0), default_threshold_pct=5.0)
        assert len(alerts) == 1 and alerts[0].kind == "drop"
        assert alerts[0].pct == 10.0 and alerts[0].previous == 100.0

    def test_drop_below_threshold_is_silent(self):
        watched = seed_history(item(threshold_pct=5.0), 100.0)
        assert decide(watched, observation(97.0), 5.0) == []

    def test_default_threshold_comes_from_config(self):
        watched = seed_history(item(), 100.0)  # no per-item threshold
        assert decide(watched, observation(94.0), 5.0)  # 6% drop fires
        assert not decide(watched, observation(97.0), 5.0)


class TestTargets:
    def test_target_hit_alerts(self):
        watched = seed_history(item(target=90.0), 100.0)
        first = decide(watched, observation(89.0), 5.0)
        assert any(alert.kind == "target" for alert in first)

    def test_target_repeat_at_same_price_is_deduped(self):
        watched = seed_history(item(target=90.0), 100.0)
        watched.last_alert = {"kind": "target", "value": 89.0, "at": clock.iso()}
        again = decide(watched, observation(89.0), 5.0)
        assert all(alert.kind != "target" for alert in again)


class TestFloor:
    def test_first_observation_is_the_low(self):
        assert new_low(item(), observation(50.0))

    def test_lower_beats_the_floor(self):
        watched = seed_history(item(), 100.0)
        assert new_low(watched, observation(99.0))
        assert not new_low(watched, observation(101.0))


class TestStock:
    def test_running_out_alerts(self):
        watched = seed_history(item(), 100.0)
        watched.available = True
        alerts = decide(watched, observation(100.0, available=False), 5.0)
        assert [alert.kind for alert in alerts] == ["out_of_stock"]

    def test_back_in_stock_alerts(self):
        watched = seed_history(item(), 100.0)
        watched.available = False
        alerts = decide(watched, observation(100.0, available=True), 5.0)
        assert [alert.kind for alert in alerts] == ["back_in_stock"]

    def test_steady_stock_is_silent(self):
        watched = seed_history(item(), 100.0)
        watched.available = True
        assert decide(watched, observation(100.0, available=True), 5.0) == []

    def test_unknown_stock_never_alerts(self):
        watched = seed_history(item(), 100.0)
        watched.available = None
        assert decide(watched, observation(100.0, available=False), 5.0) == []
