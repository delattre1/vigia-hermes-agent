"""The JSON-LD reader and the Mercado Livre URL parsing, against local fixtures."""

import pytest

from vigia.sources import jsonld, mercadolivre
from vigia.sources.base import SourceError

PRODUCT_PAGE = b"""<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Fone Bluetooth XYZ",
 "offers":{"@type":"Offer","price":"249.90","priceCurrency":"BRL",
           "availability":"https://schema.org/InStock"}}
</script></head><body>loja</body></html>"""

AGGREGATE_PAGE = b"""<html><head>
<script type="application/ld+json">
{"@graph":[{"@type":"Product","name":"Cadeira Gamer","offers":{"@type":"AggregateOffer",
 "lowPrice":1299,"priceCurrency":"BRL","availability":"https://schema.org/InStock"}}]}
</script></head></html>"""

BARE_PAGE = b"<html><body>sem structured data aqui</body></html>"


class TestJsonLd:
    def test_simple_offer(self, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, PRODUCT_PAGE))
        found = jsonld.fetch("https://loja.example/produto")
        assert found.title == "Fone Bluetooth XYZ"
        assert found.price == 249.90 and found.currency == "BRL" and found.available is True

    def test_aggregate_offer_low_price(self, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, AGGREGATE_PAGE))
        found = jsonld.fetch("https://loja.example/produto")
        assert found.price == 1299.0 and found.title == "Cadeira Gamer"

    def test_bare_page_is_a_source_error(self, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, BARE_PAGE))
        with pytest.raises(SourceError):
            jsonld.fetch("https://loja.example/produto")

    def test_http_error_is_a_source_error(self, monkeypatch):
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (404, b"nope"))
        with pytest.raises(SourceError):
            jsonld.fetch("https://loja.example/produto")


class TestMercadoLivreIds:
    def test_modern_product_url(self):
        assert mercadolivre.item_id("https://www.mercadolivre.com.br/coisas/p/MLB12345678") == "MLB12345678"

    def test_classic_dash_url(self):
        assert mercadolivre.item_id("https://produto.mercadolivre.com.br/MLB-98765432-nespresso") == "MLB98765432"

    def test_unrelated_url(self):
        assert mercadolivre.item_id("https://www.amazon.com.br/dp/B0XYZ") is None


class TestMercadoLivreFetch:
    def test_api_answer_becomes_observation(self, monkeypatch):
        payload = b'{"title":"Air Fryer","price":399.0,"currency_id":"BRL","status":"active","available_quantity":5}'
        monkeypatch.setattr(mercadolivre.http, "fetch", lambda url, **kw: (200, payload))
        found = mercadolivre.fetch("https://produto.mercadolivre.com.br/MLB12345678-air-fryer")
        assert found.price == 399.0 and found.available is True

    def test_api_failure_falls_back_to_jsonld(self, monkeypatch):
        monkeypatch.setattr(mercadolivre.http, "fetch", lambda url, **kw: (_ for _ in ()).throw(
            __import__("kit.http", fromlist=["HttpError"]).HttpError("blocked")))
        monkeypatch.setattr(jsonld.http, "fetch", lambda url, **kw: (200, PRODUCT_PAGE))
        found = mercadolivre.fetch("https://produto.mercadolivre.com.br/MLB12345678-x")
        assert found.title == "Fone Bluetooth XYZ"

    def test_unrecognized_url_is_refused(self):
        with pytest.raises(SourceError):
            mercadolivre.fetch("https://example.com/nope")
