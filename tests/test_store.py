"""Store and config contracts: atomic roundtrips, dedup by canonical URL."""

import pytest

from vigia import config
from vigia.engine import watchlist
from vigia.models import StoreKind
from vigia.store import canonical_url, item_id_for


class TestCanonical:
    def test_tracking_noise_is_stripped(self):
        base = "https://www.mercadolivre.com.br/produto/x/p/MLB12345678"
        assert canonical_url(base + "?matt_tool=123") == base
        assert item_id_for(base) == item_id_for(base + "?utm=spam")


class TestWatchlist:
    def test_add_get_remove_roundtrip(self, store):
        added = watchlist.add(store, "https://produto.mercadolivre.com.br/MLB12345678-thing",
                              title="Thing", currency="BRL", target=None, threshold_pct=None)
        assert store.get(added.id).title == "Thing"
        assert store.all()[0].kind == StoreKind.MERCADO_LIVRE
        watchlist.remove(store, added.id)
        assert store.all() == []

    def test_same_product_twice_deduplicates(self, store):
        url = "https://x.example/p/1"
        first = watchlist.add(store, url + "?a=b", title="A", currency="BRL", target=None, threshold_pct=None)
        second = watchlist.add(store, url + "?c=d", title="B", currency="BRL", target=None, threshold_pct=None)
        assert first.id == second.id
        assert len(store.all()) == 1
        assert store.all()[0].title == "B"  # the latest add wins

    def test_store_survives_a_reload(self, store):
        watchlist.add(store, "https://x.example/p/2", title="Persist", currency="USD",
                      target=9.99, threshold_pct=7.5)
        store.save()
        reloaded = type(store)(store.home)
        assert reloaded.all()[0].target == 9.99
        assert reloaded.all()[0].threshold_pct == 7.5

    def test_unknown_id_raises(self, store):
        with pytest.raises(KeyError):
            store.get("nope")


class TestConfig:
    def test_defaults_then_missing_keys(self, tmp_path):
        loaded = config.load(str(tmp_path))
        assert loaded["digest_time"] == "08:30"
        assert set(config.missing_keys(loaded)) == set(config.REQUIRED_KEYS)

    def test_set_and_save(self, tmp_path):
        home = str(tmp_path)
        current = config.load(home)
        current.update(timezone="America/Sao_Paulo", digest_time="07:15", language="pt-BR")
        config.save(home, current)
        assert config.load(home)["timezone"] == "America/Sao_Paulo"
        assert config.missing_keys(home) == []
