"""Mercado Livre, via its public item API; falls back to the page itself."""

from __future__ import annotations

import json
import re

from kit import http

from vigia.sources.base import Observation, SourceError, parse_price

_ITEM_ID = re.compile(r"(ML[ABCDEFGHJKLMNIZU])\s?-?(\d{6,})", re.IGNORECASE)
_API = "https://api.mercadolibre.com/items/"


def item_id(url: str) -> str | None:
    match = _ITEM_ID.search(url)
    return f"{match.group(1).upper()}{match.group(2)}" if match else None


def fetch(url: str) -> Observation:
    """The API first; when it refuses, the page's own JSON-LD still answers."""
    identifier = item_id(url)
    if identifier is None:
        raise SourceError(url, "not a recognizable Mercado Livre item URL")
    try:
        status, body = http.fetch(_API + identifier)
        if status == 200:
            payload = json.loads(body)
            price = parse_price(payload.get("price"))
            if payload.get("title") and price is not None:
                return Observation(
                    title=str(payload["title"]),
                    price=price,
                    currency=str(payload.get("currency_id") or ""),
                    available=payload.get("status") == "active" and (payload.get("available_quantity") or 0) > 0,
                )
    except (http.HttpError, ValueError, KeyError, TypeError):
        pass  # the API is a convenience, not a dependency
    from vigia.sources import jsonld  # local import: the registry owns cycles
    return jsonld.fetch(url)
