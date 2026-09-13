"""OLX reader: JSON-LD when the wall lets us through, condition tagged."""

from vigia.sources import jsonld
from vigia.sources.base import Observation, SourceError


def fetch(url: str) -> Observation:
    """One read of an OLX listing page.

    OLX sits behind Cloudflare; the direct reader usually loses, and the
    chain's ScraperAPI fallback (or a screenshot) carries the item. When a
    page does come through, its JSON-LD carries the itemCondition that makes
    the used tag a fact rather than an assumption.
    """
    status, body = jsonld.http.fetch(url)
    if status != 200:
        raise SourceError(url, f"page answered HTTP {status}")
    observation = jsonld.parse_html(body)
    if observation is None:
        raise SourceError(url, "no schema.org product offer found in the listing")
    # OLX is a used marketplace by nature: when the page does not say, the
    # tag stays honest by default rather than pretending new.
    if observation.condition is None:
        observation.condition = "usado"
    return observation
