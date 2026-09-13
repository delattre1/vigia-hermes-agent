"""Name search: kabum's data island, amazon's card chunks, dedup, dead searchers."""

import pytest

from vigia.sources import search
from vigia.sources.base import SourceError

KABUM_ISLAND = b"""<html><script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"data":{"catalogServer":{"data":[
 {"code":989702,"name":"Console PS5 Digital","price":4399,"priceWithDiscount":4091.07},
 {"code":934759,"name":"Console PS5 Leitor","price":4899,"priceWithDiscount":null},
 {"name":"sem code"}]}}}}}</script></html>"""

AMAZON_CARDS = (
    b'<div data-asin="B0AAAAAA11"><h2 aria-hidden="true"><span>Console PlayStation 5 Slim Digital</span></h2>'
    b'<span class="a-price"><span class="a-offscreen">R$\xc2\xa04.090,00</span>'
    b'<span class="a-price-whole">4.090</span><span class="a-price-fraction">00</span></span></div>'
    b'<div data-asin="B0AAAAAA22"><h2><span>Bundle PS5 + GTA</span></h2></div>'  # no price: skipped
    b'<div data-asin="B0AAAAAA33"><h2><span>Controle DualSense</span></h2>'
    b'<span class="a-price"><span class="a-price-whole">489</span><span class="a-price-fraction">90</span></span></div>'
)


class TestKabum:
    def test_island_becomes_results(self, monkeypatch):
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, KABUM_ISLAND))
        hits = search._kabum("playstation 5", "playstation-5", "amazon.com.br", 5)
        assert [hit.price for hit in hits] == [4091.07, 4899.0]
        assert hits[0].url.endswith("/produto/989702") and hits[0].currency == "BRL"

    def test_page_without_island_refuses(self, monkeypatch):
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, b"<html>no island</html>"))
        with pytest.raises(SourceError):
            search._kabum("x", "x", "amazon.com.br", 5)


class TestAmazon:
    def test_cards_become_results_priced_ones_only(self, monkeypatch):
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, AMAZON_CARDS))
        hits = search._amazon("playstation 5", "playstation-5", "amazon.com.br", 5)
        assert [hit.price for hit in hits] == [4090.0, 489.90]
        assert hits[0].url == "https://amazon.com.br/dp/B0AAAAAA11"

    def test_us_uses_dollars(self, monkeypatch):
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, AMAZON_CARDS))
        hits = search._amazon("ps5", "ps5", "amazon.com", 5)
        assert hits[0].currency == "USD"


class TestSearch:
    def test_dead_searcher_shrinks_the_menu(self, monkeypatch):
        def kabum_boom(*a, **kw):
            raise SourceError("x", "down")
        monkeypatch.setattr(search, "_kabum", kabum_boom)
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, AMAZON_CARDS))
        hits = search.search("playstation 5", country="BR", limit=5)
        assert hits and all(hit.store == "amazon" for hit in hits)

    def test_dedup_and_limit(self, monkeypatch):
        monkeypatch.setattr(search.http, "fetch", lambda url, **kw: (200, KABUM_ISLAND))
        hits = search.search("playstation 5", country="BR", limit=1)
        assert len(hits) == 1

    def test_empty_query_refuses(self):
        with pytest.raises(SourceError):
            search.search("   ")
