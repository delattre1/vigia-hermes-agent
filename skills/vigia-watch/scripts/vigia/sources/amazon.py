"""Amazon, best-effort: one fetch, JSON-LD first, then the page's own price state.

Amazon bot-walls aggressively and its product pages rarely ship JSON-LD; the
price lives in the page's embedded state (`priceAmount`) or the buy-box spans
(`a-offscreen`). When both miss, the sweep marks the item stale and the agent
asks for a screenshot instead of pretending to know.
"""

from __future__ import annotations

import re

from kit import http

from vigia.sources import jsonld
from vigia.sources.base import Observation, SourceError, parse_price

_PRODUCT_TITLE = re.compile(r'id="productTitle"[^>]*>\s*([^<]{5,200}?)\s*<')
_PRICE_AMOUNT = re.compile(r'"priceAmount"\s*:\s*([\d.]+)')
_OFFSCREEN = re.compile(r'<span class="a-price[^>]*><span class="a-offscreen">\s*([^<]{3,30})</span>')


def from_screenshot_price(text: str, currency_hint: str = "") -> float | None:
    """A price the model read off a screenshot, cleaned to a number.

    Accepts "R$ 4.999,00", "US$129.99", "$ 1,234.56", "R$ 4.999". The caller
    decided this number is trustworthy -- the model read it -- so this only
    formats, with one heuristic: a lone three-digit tail after a dot is a
    thousands separator, because prices rarely have three decimal places.
    """
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rpartition(",")[2]
        cleaned = cleaned.replace(",", ".") if len(tail) != 3 else cleaned.replace(",", "")
    elif "." in cleaned:
        head, _, tail = cleaned.rpartition(".")
        if len(tail) == 3 and head.isdigit() and len(head) <= 3:
            cleaned = cleaned.replace(".", "")
    return parse_price(cleaned)


def _currency_for(symbol_text: str, url: str) -> str:
    if "R$" in symbol_text:
        return "BRL"
    if "$" in symbol_text:
        return "USD"
    host = url.split("//", 1)[-1].split("/", 1)[0]
    return "BRL" if host.endswith(".com.br") else "USD"


def fetch(url: str) -> Observation:
    status, body = http.fetch(url)
    if status != 200:
        raise SourceError(url, f"page answered HTTP {status}")

    structured = jsonld.parse_html(body)
    if structured is not None:
        return structured

    html = body.decode("utf-8", errors="replace")
    title_match = _PRODUCT_TITLE.search(html)
    title = title_match.group(1).strip() if title_match else ""

    price: float | None = None
    currency = ""
    amount = _PRICE_AMOUNT.search(html)
    if amount is not None:
        price = parse_price(amount.group(1))
    offscreen = _OFFSCREEN.search(html)
    if price is None and offscreen is not None:
        price = from_screenshot_price(offscreen.group(1))
    if price is None:
        raise SourceError(url, "no price found in the page -- the wall won this round")
    currency = _currency_for(offscreen.group(1) if offscreen else "", url)

    return Observation(title=title, price=price, currency=currency, available=None)
