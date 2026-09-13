"""The generic reader: schema.org JSON-LD, which most storefronts ship."""

from __future__ import annotations

import json
import re
from typing import Any

from kit import http

from vigia.sources.base import Observation, SourceError, parse_price

_LD_SCRIPT = re.compile(
    rb'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _parse_ld_object(blob: bytes) -> Observation | None:
    """One ld+json blob, maybe an Observation. Never raises."""
    try:
        payload = json.loads(blob.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    candidates: list[dict[str, Any]] = []

    def visit(node: object) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if str(node.get("@type", "")).lower() == "product":
                candidates.append(node)
            for value in node.values():
                visit(value)

    visit(payload)
    for product in candidates:
        offer = product.get("offers") or {}
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        price = parse_price(offer.get("price") or offer.get("lowPrice"))
        if price is None:
            continue
        availability = str(offer.get("availability", "")).lower()
        item_condition = str(offer.get("itemCondition") or product.get("itemCondition") or "").lower()
        condition = "usado" if "usedcondition" in item_condition else \
                    "novo" if "newcondition" in item_condition else None
        return Observation(
            title=str(product.get("name") or "").strip(),
            price=price,
            currency=str(offer.get("priceCurrency") or ""),
            available=None if not availability else "instock" in availability,
            condition=condition,
        )
    return None


def parse_html(body: bytes) -> Observation | None:
    """Every schema.org product offer in an HTML body, first one that prices."""
    for match in _LD_SCRIPT.finditer(body):
        observation = _parse_ld_object(match.group(1))
        if observation is not None:
            return observation
    return None


def fetch(url: str) -> Observation:
    status, body = http.fetch(url)
    if status != 200:
        raise SourceError(url, f"page answered HTTP {status}")
    observation = parse_html(body)
    if observation is None:
        raise SourceError(url, "no schema.org product offer found in the page")
    return observation
