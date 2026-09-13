"""Name search: "pesquisa playstation 5" -> candidate products with prices.

A search answer is a menu, never a commitment: the model presents the hits
and the user picks one to watch. Each searcher is best-effort and store
specific, because search pages are the most hostile HTML there is.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from kit import http

from vigia.sources.base import SourceError, parse_price

_NEXT_DATA = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_ASIN = re.compile(r'data-asin="([A-Z0-9]{10})"')
_CARD_TITLE = re.compile(r"<h2[^>]*>\s*<span>([^<]{10,200})</span>")
_CARD_PRICE = re.compile(r'a-price-whole">([\d.,]+)</span>(?:<span class="a-price-fraction">(\d+)</span>)?')


@dataclass
class SearchResult:
    title: str
    url: str
    price: float | None
    currency: str
    store: str

    def as_dict(self) -> dict:
        return {
            "title": self.title, "url": self.url, "price": self.price,
            "currency": self.currency, "store": self.store,
        }


def search(query: str, *, country: str = "BR", limit: int = 5) -> list[SearchResult]:
    """The result list, best stores first. Never raises: failures shrink it."""
    query = query.strip()
    if not query:
        raise SourceError(query, "empty search query")
    slug = re.sub(r"\s+", "-", query.lower())
    hits: list[SearchResult] = []
    searchers = [_kabum] if country.upper() == "BR" else []
    searchers.append(_amazon)
    domain = "amazon.com.br" if country.upper() == "BR" else "amazon.com"
    for reader in searchers:
        try:
            hits.extend(reader(query, slug, domain, limit))
        except Exception:
            continue  # one dead searcher must not empty the menu
    # Dedup by url, keep order.
    unique: dict[str, SearchResult] = {}
    for hit in hits:
        unique.setdefault(hit.url, hit)
    return list(unique.values())[:limit]


def _kabum(query: str, slug: str, domain: str, limit: int) -> list[SearchResult]:
    status, body = http.fetch(f"https://www.kabum.com.br/busca/{slug}")
    if status != 200:
        raise SourceError(query, f"kabum search answered HTTP {status}")
    match = _NEXT_DATA.search(body.decode("utf-8", errors="replace"))
    if match is None:
        raise SourceError(query, "kabum search page had no data island")
    payload = json.loads(match.group(1))
    items = (payload.get("props", {}).get("pageProps", {})
             .get("data", {}).get("catalogServer", {}).get("data", []))
    results: list[SearchResult] = []
    for item in items:
        code, name = item.get("code"), item.get("name")
        if not code or not name:
            continue
        price = parse_price(item.get("priceWithDiscount") or item.get("price"))
        results.append(SearchResult(
            title=str(name), url=f"https://www.kabum.com.br/produto/{code}",
            price=price, currency="BRL", store="kabum",
        ))
    return results[:limit]


def _amazon(query: str, slug: str, domain: str, limit: int) -> list[SearchResult]:
    status, body = http.fetch(f"https://{domain}/s?k={urllib_parse_quote(query)}")
    if status != 200:
        raise SourceError(query, f"amazon search answered HTTP {status}")
    html = body.decode("utf-8", errors="replace")
    currency = "BRL" if domain.endswith(".com.br") else "USD"
    results: list[SearchResult] = []
    positions = list(_ASIN.finditer(html))
    for index, card in enumerate(positions):
        chunk_end = positions[index + 1].start() if index + 1 < len(positions) else len(html)
        chunk = html[card.start():chunk_end]
        title = _CARD_TITLE.search(chunk)
        price_match = _CARD_PRICE.search(chunk)
        if title is None or price_match is None:
            continue
        whole, fraction = price_match.group(1), price_match.group(2) or "00"
        # Whole parts carry store-local thousand separators ("4.090", "1,234");
        # the fraction is always cents, so this split is unambiguous.
        price = parse_price(f"{re.sub(r'[.,]', '', whole)}.{fraction}")
        results.append(SearchResult(
            title=title.group(1).strip(),
            url=f"https://{domain}/dp/{card.group(1)}",
            price=price, currency=currency, store="amazon",
        ))
    return results[:limit]


def urllib_parse_quote(text: str) -> str:
    import urllib.parse
    return urllib.parse.quote_plus(text)
