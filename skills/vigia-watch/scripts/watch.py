#!/usr/bin/env python3
"""watch.py -- the Vigia engine's CLI. Every command answers one JSON object.

Commands:
    add <url> [--target F] [--threshold PCT]   start watching a product
    observe <id> --price F [--title S] [--currency CODE]
                                               record a price read off a screenshot
    list                                       every watched item, compact
    remove <id>                                stop watching
    check [id ...]                             sweep now (or just these items)
    history <id> [--limit N]                   one item's price points
    digest                                     the morning digest payload
    config get                                 current preferences
    config set KEY=VALUE ...                   timezone, digest_time, language, ...

Exit 0 on success, 1 on usage error, 2 on runtime failure. stdout is data
only: the skills own every human word.
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from kit import clock, jsonio  # noqa: E402,F401

from vigia import config as vigia_config  # noqa: E402
from vigia import store as store_module  # noqa: E402
from vigia.engine import digest, sweep, watchlist  # noqa: E402
from vigia.sources import amazon  # noqa: E402
from vigia.sources import search as search_module  # noqa: E402
from vigia.sources.base import Observation  # noqa: E402
from vigia.store import VigiaStore  # noqa: E402

HOME = __import__("os").environ.get("VIGIA_HOME", "/var/lib/hermes/vigia")


def emit(payload: object, code: int = 0) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return code


def fail(message: str) -> int:
    return emit({"error": message}, 2)


def cmd_add(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    kind = store.kind_for_url(store_module.canonical_url(args.url))
    from vigia.sources import observe
    try:
        first: Observation = observe(str(kind), store_module.canonical_url(args.url))
    except Exception as error:
        # No first price yet: the item is still added -- unwatched-unread, and
        # the sweep (or a screenshot) will price it later.
        item = watchlist.add(
            store, args.url, title="", currency="",
            target=args.target, threshold_pct=args.threshold,
        )
        store.save()
        return emit({"added": store.compact_view(item), "first_read": None, "note": f"no price yet: {error}"})
    item = watchlist.add(
        store, args.url, title=first.title, currency=first.currency,
        target=args.target, threshold_pct=args.threshold,
    )
    alerts = sweep.apply_observation(store, item, first)
    return emit({
        "added": store.compact_view(item),
        "first_read": {"title": first.title, "price": first.price, "currency": first.currency,
                       "available": first.available},
        "alerts": [alert.as_dict() for alert in alerts],
    })


def cmd_observe(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    try:
        item = store.get(args.id)
    except KeyError as error:
        return fail(str(error))
    price = amazon.from_screenshot_price(str(args.price))
    if price is None:
        return fail(f"cannot read a price out of {args.price!r}")
    alerts = sweep.apply_manual(store, item, price, args.title, args.currency)
    return emit({"observed": store.compact_view(item), "alerts": [alert.as_dict() for alert in alerts]})


def cmd_list(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    return emit({"items": watchlist.summary(store), "onboarding_missing": vigia_config.missing_keys(HOME)})


def cmd_remove(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    try:
        removed = watchlist.remove(store, args.id)
    except KeyError as error:
        return fail(str(error))
    store.save()
    return emit({"removed": store.compact_view(removed)})


def cmd_check(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    return emit(sweep.check_all(store, only_ids=args.ids or None))


def cmd_history(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    try:
        item = store.get(args.id)
    except KeyError as error:
        return fail(str(error))
    points = item.history[-(args.limit or 30):]
    return emit({
        "id": item.id, "title": item.title, "currency": item.currency,
        "low": item.low, "target": item.target,
        "history": [point.as_dict() for point in points],
    })


def cmd_digest(args: argparse.Namespace) -> int:
    store = VigiaStore(HOME)
    return emit(digest.build(store))


def cmd_search(args: argparse.Namespace) -> int:
    query = " ".join(args.words)
    try:
        results = search_module.search(query, country=args.country, limit=args.limit)
    except Exception as error:
        return fail(f"search failed: {error}")
    return emit({"query": query, "country": args.country, "results": [r.as_dict() for r in results]})


def cmd_config(args: argparse.Namespace) -> int:
    if args.action == "get":
        return emit(vigia_config.load(HOME))
    current = vigia_config.load(HOME)
    for pair in args.pairs:
        key, _, raw = pair.partition("=")
        if key not in vigia_config.DEFAULTS:
            return fail(f"unknown config key {key!r}")
        if key in ("digest_enabled",):
            current[key] = raw.strip().lower() in ("1", "true", "yes", "on")
        elif key == "threshold_pct":
            current[key] = float(raw)
        else:
            current[key] = raw.strip()
    vigia_config.save(HOME, current)
    return emit({"saved": current, "onboarding_missing": vigia_config.missing_keys(HOME)})


def main() -> int:
    parser = argparse.ArgumentParser(prog="watch", description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="command", required=True)

    it = verbs.add_parser("add")
    it.add_argument("url")
    it.add_argument("--target", type=float, default=None)
    it.add_argument("--threshold", type=float, default=None, help="drop percent that alerts")
    it.set_defaults(run=cmd_add)

    it = verbs.add_parser("observe")
    it.add_argument("id")
    it.add_argument("--price", required=True, help="price text as read off the screenshot")
    it.add_argument("--title", default=None)
    it.add_argument("--currency", default=None)
    it.set_defaults(run=cmd_observe)

    verbs.add_parser("list").set_defaults(run=cmd_list)

    it = verbs.add_parser("remove")
    it.add_argument("id")
    it.set_defaults(run=cmd_remove)

    it = verbs.add_parser("check")
    it.add_argument("ids", nargs="*")
    it.set_defaults(run=cmd_check)

    it = verbs.add_parser("history")
    it.add_argument("id")
    it.add_argument("--limit", type=int, default=30)
    it.set_defaults(run=cmd_history)

    verbs.add_parser("digest").set_defaults(run=cmd_digest)

    it = verbs.add_parser("search", help="find products by name")
    it.add_argument("words", nargs="+")
    it.add_argument("--country", default="BR", choices=["BR", "US"])
    it.add_argument("--limit", type=int, default=5)
    it.set_defaults(run=cmd_search)

    it = verbs.add_parser("config")
    it.add_argument("action", choices=["get", "set"])
    it.add_argument("pairs", nargs="*")
    it.set_defaults(run=cmd_config)

    args = parser.parse_args()
    try:
        return args.run(args)
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
