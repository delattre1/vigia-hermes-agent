"""Source contract: turn a URL into an Observation. Adapters register by host."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceError(RuntimeError):
    """One source's failure to read one page. A sweep survives any of these."""

    url: str
    reason: str

    def __str__(self) -> str:
        return f"{self.url}: {self.reason}"


@dataclass
class Observation:
    """One successful read of a product page."""

    title: str
    price: float | None
    currency: str
    available: bool | None


def parse_price(raw: object) -> float | None:
    """A price out of whatever a store put in the page; None when unusable."""
    if raw is None:
        return None
    try:
        return round(float(str(raw).strip().replace(",", "") if isinstance(raw, str) else raw), 2)
    except ValueError:
        return None
