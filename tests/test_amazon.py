"""The Amazon reader: JSON-LD when the page ships it, page state when it doesn't."""

import pytest

from vigia.sources import amazon
from vigia.sources.base import SourceError

PRODUCT_PAGE = (
    b'<html><span id="productTitle">Notebook Acer Aspire 5 A515-45-R043</span>'
    b'<script>{"priceAmount":4339.90}</script>'
    b'<span class="a-price" data-a-size="xl"><span class="a-offscreen">R$\xc2\xa04.339,90</span></span></html>'
)

NO_PRICE_PAGE = b'<html><span id="productTitle">Only a title here</span></html>'


class TestAmazonProductPage:
    def test_price_amount_wins(self, monkeypatch):
        monkeypatch.setattr(amazon.http, "fetch", lambda url, **kw: (200, PRODUCT_PAGE))
        found = amazon.fetch("https://www.amazon.com.br/dp/B083LGFDGJ")
        assert found.price == 4339.90
        assert "Acer Aspire 5" in found.title
        assert found.currency == "BRL"  # from the offscreen symbol beside it

    def test_offscreen_fallback(self, monkeypatch):
        body = b'<span id="productTitle">Teclado</span>' \
               b'<span class="a-price"><span class="a-offscreen">R$\xc2\xa0249,90</span></span>'
        monkeypatch.setattr(amazon.http, "fetch", lambda url, **kw: (200, body))
        found = amazon.fetch("https://www.amazon.com.br/dp/B0X")
        assert found.price == 249.90

    def test_jsonld_page_still_answers(self, monkeypatch):
        body = (b'<script type="application/ld+json">'
                b'{"@type":"Product","name":"X","offers":{"price":9.9,"priceCurrency":"BRL"}}'
                b'</script>')
        monkeypatch.setattr(amazon.http, "fetch", lambda url, **kw: (200, body))
        assert amazon.fetch("https://www.amazon.com/dp/B0X").price == 9.9

    def test_walled_page_refuses(self, monkeypatch):
        monkeypatch.setattr(amazon.http, "fetch", lambda url, **kw: (200, NO_PRICE := b"<html>captcha</html>"))
        with pytest.raises(SourceError):
            amazon.fetch("https://www.amazon.com/dp/B0X")

    def test_http_error_refuses(self, monkeypatch):
        monkeypatch.setattr(amazon.http, "fetch", lambda url, **kw: (404, b"nope"))
        with pytest.raises(SourceError):
            amazon.fetch("https://www.amazon.com/dp/B0X")


class TestPriceText:
    @pytest.mark.parametrize(("text", "expected"), [
        ("R$ 4.999,00", 4999.0), ("R$4.122,90", 4122.9), ("US$129.99", 129.99),
        ("$ 1,234.56", 1234.56), ("R$ 4.999", 4999.0), ("499,90", 499.9),
        ("4091.07", 4091.07), ("sem numero", None),
    ])
    def test_formats(self, text, expected):
        assert amazon.from_screenshot_price(text) == expected