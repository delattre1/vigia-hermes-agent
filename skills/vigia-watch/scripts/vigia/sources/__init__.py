"""Source registry: which readers to try, in order, for a URL.

The first success wins. Mercado Livre falls back to the generic JSON-LD
reader; Amazon has one best-effort reader; anything else starts generic.
ScraperAPI joins every chain when the user set `SCRAPERAPI_KEY` -- the
professional fallback for the stores that bot-wall direct readers.
"""

from __future__ import annotations

from collections.abc import Callable

from vigia.sources import amazon, jsonld, mercadolivre, olx, scraperapi
from vigia.sources.base import Observation, SourceError

Reader = Callable[[str], Observation]


def readers_for(kind: str) -> list[Reader]:
    if kind == "mercadolivre":
        chain: list[Reader] = [mercadolivre.fetch, jsonld.fetch]
    elif kind == "amazon":
        chain = [amazon.fetch]
    else:
        chain = [jsonld.fetch]
    if scraperapi.enabled():
        chain.append(scraperapi.fetch)
    return chain


def observe(kind: str, url: str) -> Observation:
    """Try every reader; the last error is the one reported."""
    errors: list[SourceError] = []
    for reader in readers_for(kind):
        try:
            return reader(url)
        except SourceError as error:
            errors.append(error)
    raise errors[-1] if errors else SourceError(url, "no reader for this store")
