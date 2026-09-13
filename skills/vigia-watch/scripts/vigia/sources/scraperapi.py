"""ScraperAPI -- the professional fallback, when the user supplies a key.

Direct readers come first; this only runs when they were bot-walled. One
environment variable, `SCRAPERAPI_KEY`, turns the layer on: a SaaS proxy
with residential pools and anti-bot handling. Without the key this adapter
does not exist, and the agent stays entirely direct + screenshot.
"""

from __future__ import annotations

import os
import urllib.parse

from kit import http

from vigia.sources import jsonld
from vigia.sources.base import Observation, SourceError

_API = "https://api.scraperapi.com/"


def key() -> str:
    return (os.environ.get("SCRAPERAPI_KEY") or "").strip()


def enabled() -> bool:
    return bool(key())


def fetch(url: str) -> Observation:
    api_key = key()
    if not api_key:
        raise SourceError(url, "SCRAPERAPI_KEY not set -- professional fallback is off")
    params = urllib.parse.urlencode({"api_key": api_key, "url": url})
    if ".br" in urllib.parse.urlsplit(url).hostname or "":
        params += "&country_code=br"
    status, body = http.fetch(f"{_API}?{params}", timeout_s=30.0)
    if status != 200:
        raise SourceError(url, f"scraperapi answered HTTP {status}")
    observation = jsonld.parse_html(body)
    if observation is None:
        raise SourceError(url, "scraperapi fetched the page but no product offer was in it")
    return observation
