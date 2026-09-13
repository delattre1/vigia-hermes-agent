"""The sweep: good reads fold into history, bad reads go stale, never a crash."""

import pytest

from vigia.engine import sweep
from vigia.sources.base import Observation, SourceError


def observation(price, **kw) -> Observation:
    return Observation(title=kw.get("title", "Product"), price=price,
                       currency=kw.get("currency", "BRL"), available=kw.get("available"))


def watch_add(store, url="https://shop.example/p/1"):
    from vigia.engine import watchlist
    return watchlist.add(store, url, title="Product", currency="BRL", target=None, threshold_pct=5.0)


class TestSweep:
    def test_good_read_records_history_and_floor(self, store, monkeypatch):
        added = watch_add(store)
        prices = iter([100.0, 90.0])
        monkeypatch.setattr(sweep.sources, "observe", lambda kind, url: observation(next(prices)))
        sweep.check_all(store)
        report = sweep.check_all(store)
        item = store.get(added.id)
        assert item.low == 90.0 and item.last_status == "ok"
        assert report["alerts"][0]["kind"] == "drop" and report["alerts"][0]["pct"] == 10.0

    def test_failed_read_goes_stale_not_dead(self, store, monkeypatch):
        added = watch_add(store)
        monkeypatch.setattr(sweep.sources, "observe",
                            lambda kind, url: (_ for _ in ()).throw(SourceError(url, "walled")))
        report = sweep.check_all(store)
        item = store.get(added.id)
        assert report["failed"] and item.last_status == "stale"
        assert item.history[-1].status == "stale" and item.history[-1].price is None

    def test_one_bad_item_never_ends_the_sweep(self, store, monkeypatch):
        first = watch_add(store, "https://x.example/p/a")
        second = watch_add(store, "https://y.example/p/b")

        def flaky(kind, url):
            if "x." in url:
                raise SourceError(url, "walled")
            return observation(10.0)

        monkeypatch.setattr(sweep.sources, "observe", flaky)
        report = sweep.check_all(store)
        assert report["checked"] == 2
        assert store.get(first.id).last_status == "stale"
        assert store.get(second.id).last_status == "ok"

    def test_manual_screenshot_price_folds_in(self, store):
        added = watch_add(store)
        sweep.apply_manual(store, store.get(added.id), 55.0, None, None)
        item = store.get(added.id)
        assert item.last_price() == 55.0 and item.low == 55.0

    def test_steady_price_never_alerts_twice(self, store, monkeypatch):
        added = watch_add(store)
        monkeypatch.setattr(sweep.sources, "observe", lambda kind, url: observation(100.0))
        sweep.check_all(store)
        report = sweep.check_all(store)
        assert report["alerts"] == []
        assert store.get(added.id).last_status == "ok"
