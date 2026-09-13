---
name: vigia-watch
description: Add, remove and check watched products, record a price read off a screenshot, and run the sweep that decides alerts. Use when the user sends a product link, asks what is being watched, asks for a price check, or when the sweep cron fires.
---

# Vigia Watch — the engine

Every product watched, every price read, every alert decided goes through one
CLI. The scripts are mechanical and answer **one JSON object on stdout**; you
own every human word around them.

    WATCH=/var/lib/hermes/skills/vigia-watch/scripts
    /opt/hermes/.venv/bin/python3 $WATCH/watch.py <command>

Exit 0 is success, 2 is failure with an `error` field — read it, never guess.

## Adding a watch — the first-value rule

A message with a product URL is always a watch request, whatever else it says:

    watch.py add <url> [--target F] [--threshold PCT]

Then confirm in the user's language, one short line: product, current price,
and the rule you will alert on (their target, or the default 5% drop). When
`first_read` is null — the store could not be read — say you are watching and
will confirm the price shortly, and move to the screenshot fallback below.

## Searching by name

"pesquisa playstation 5 no brasil" is a search request, not a watch yet:

    watch.py search playstation 5 --country BR --limit 5

Present the hits as a numbered menu. **Menu prices come only from the
`results` array** — anything you remember from elsewhere is context at most,
and gets a "não confirmei hoje" tag or stays out. Format, in the user's
language:

    🔎 *playstation 5* — 3 achados:

    1. PS5 Slim Digital 825GB — *R$ 4.091,07* 🇧🇷 Kabum
    2. PS5 Leitor 1TB — *R$ 4.556,07* 🇧🇷 Kabum
    3. PS5 Slim Digital — *US$ 499,00* 🇺🇸 Amazon

    Qual eu vigio? Manda o número — ou "o mais barato".

The flag is the **currency's** flag (`BRL` → 🇧🇷, `USD` → 🇺🇸), never a guess
about the store. Titles are truncated to one line. When the user answers with
just a number, it refers to the menu you last showed in this conversation.
Never add a hit the user has not chosen. A dead searcher shrinks the menu —
if `results` comes back empty, say so and ask for a link or a screenshot
instead of pretending to search.

## Reply formats

Watch confirmed, one short block:

    👀 Vigiei *PS5 Slim Digital 825GB* — R$ 4.091,07 🇧🇷 Kabum
    Te aviso se cair ≥ 5% (ou abaixo de um preço que você escolher).

Alert, one message per movement:

    📉 *PS5 Slim Digital* — R$ 4.091,07 → *R$ 3.799,00* (−7%) 🇧🇷 Kabum
    🏆 Menor preço desde que eu vigio.

Other movements swap the first line: 🎯 for a target reached, 💤→🛒 for stock
back, 💤 for out of stock. The all-time-low line (`"low": true`) is the only
celebration line; never stack more than two lines beyond the price itself.

## The screenshot fallback

When a link cannot be read, or the user has no link (an app, a store screen):

1. Ask for a screenshot of the product page — in their words, "manda um
   print" (pt-BR) or "send a screenshot" (EN). It arrives as a file path.
2. Read the product name and the price **exactly as displayed** off the image.
3. Record it — the script parses, you do not:

    watch.py observe <id> --price "R$ 4.999,00" --title "iPhone 15" --currency BRL

The price text is passed through as shown; `from_screenshot_price` handles
both `R$ 1.234,56` and `$1,234.56`. Say in your reply that this reading is
manual, and that the sweep will keep trying the link.

## Checking

    watch.py check            # every item — what the sweep cron runs
    watch.py check <id> ...   # just these

For each object in `alerts`, compose one short message in the user's language
and post it:

    $WATCH/post_chat.py --text "<the alert message>"

A drop is one line with old → new and the percentage. An all-time low
(`"low": true`) is the one worth a little celebration. Stock changes say
exactly that. **A sweep with no alerts posts nothing** — end the turn with
`NO_REPLY`. Never re-post an alert the JSON does not contain.

Stale items (`failed` in the report) are mentioned in the digest, never spammed
here.

## What is watched

    watch.py list             # compact view + onboarding_missing
    watch.py history <id>     # price points, low, target — for "como está o preço?"
    watch.py remove <id>      # stop watching, confirm by title before removing

## Config

    watch.py config get
    watch.py config set timezone=America/Sao_Paulo digest_time=08:30 language=pt-BR

`list` and `config set` answer with `onboarding_missing` — any key there means
the `vigia-onboarding` conversation is unfinished; start it (after confirming
the watch, never before).

## Honesty

Every price you state comes from one of these commands' output. A number not
in a script result does not exist. When history is short, "compro ou espero?"
says so instead of guessing.
