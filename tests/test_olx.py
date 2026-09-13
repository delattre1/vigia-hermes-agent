"""OLX: a used marketplace, tagged as such, reachable when the wall allows."""

import pytest

from vigia import store as store_module
from vigia.engine import watchlist
from vigia.models import StoreKind
from vigia.sources import jsonld, olx


OLX_PAGE = (
    b'<html><script type="application/ld+json">{"@type":"Product","name":"PS5 Slim Digital 825GB",'
    b'"offers":{"price":2500,"priceCurrency":"BRL",'
    b'"itemCondition":"https://schema.org/UsedCondition","availability":"https://schema.org/InStock"}}'
    b'</script></html>'
)


class TestKind:
    def test_olx_url_detected(self, store):
        assert store.kind_for_url("https://mg.olx.com.br/belo-horizonte-e-regiao/x") == StoreKind.OLX
        assert store.kind_for_url("https://sp.olx.com.br/x") == StoreKind.OLX


class TestCondition:
    def test_used_condition_from_the_page(self, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, OLX_PAGE))
        found = olx.fetch("https://mg.olx.com.br/x")
        assert found.price == 2500.0
        assert found.condition == "usado"

    def test_olx_add_tags_usado_even_before_first_read(self, store, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (403, b"cloudflare"))
        import watch as watch_cli
        watch_cli.HOME = store.home
        argv = ["add", "https://mg.olx.com.br/belo-horizonte-e-regiao/console/ps5-1"]
        monkeypatch.setattr("sys.argv", ["watch.py", *argv])
        code = watch_cli.main()
        assert code == 0
        added = type(store)(store.home).all()[0]  # the CLI wrote its own store
        assert added.kind == StoreKind.OLX and added.condition == "usado"
        assert store.compact_view(added)["condition"] == "usado"

    def test_new_condition_read_on_a_new_store(self, monkeypatch, store):
        NEW_PAGE = OLX_PAGE.replace(b"UsedCondition", b"NewCondition")
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, NEW_PAGE))
        found = jsonld.fetch("https://loja.example/x")
        assert found.condition == "novo"
