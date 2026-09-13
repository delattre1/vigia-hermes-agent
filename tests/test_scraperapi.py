"""The registry's chain and the ScraperAPI fallback layer."""

import pytest

import vigia.sources as sources_pkg
from vigia.sources import scraperapi
from vigia.sources.base import SourceError


class TestChain:
    def test_generic_chain_without_key(self, monkeypatch):
        monkeypatch.delenv("SCRAPERAPI_KEY", raising=False)
        readers = sources_pkg.readers_for("jsonld")
        assert [reader.__module__ for reader in readers] == ["vigia.sources.jsonld"]

    def test_ml_chain_with_key_appends_the_fallback(self, monkeypatch):
        monkeypatch.setenv("SCRAPERAPI_KEY", "k")
        readers = sources_pkg.readers_for("mercadolivre")
        assert len(readers) == 3
        assert readers[-1] is scraperapi.fetch

    def test_disabled_without_key(self, monkeypatch):
        monkeypatch.delenv("SCRAPERAPI_KEY", raising=False)
        assert scraperapi.enabled() is False

    def test_fetch_through_the_proxy(self, monkeypatch):
        monkeypatch.setenv("SCRAPERAPI_KEY", "k")
        seen = {}

        def fake_fetch(url, **kw):
            seen["url"] = url
            return 200, (b'<script type="application/ld+json">'
                         b'{"@type":"Product","name":"X","offers":{"price":9.9,"priceCurrency":"BRL"}}'
                         b'</script>')

        monkeypatch.setattr(scraperapi.http, "fetch", fake_fetch)
        found = scraperapi.fetch("https://blocked.example/produto")
        assert found.price == 9.9
        assert "api.scraperapi.com" in seen["url"] and "blocked.example" in seen["url"]

    def test_without_key_refuses(self, monkeypatch):
        monkeypatch.delenv("SCRAPERAPI_KEY", raising=False)
        with pytest.raises(SourceError):
            scraperapi.fetch("https://x.example/p")
