# Vigia

> **Text a product link; I watch the price and tell you when it drops.**
> **Manda o link, eu vigio o preço.**

A price-watching [Plow](https://plow.co) agent. Text it a product link — or a
product name — and it watches the price for you, texts you the moment it
drops, and sends a short morning digest. Bilingual (PT-BR / EN), watching
both Brazilian and US stores.

A Hermes agent built on the
[`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent) base
image for the AI Worth Using Hackathon, September 2026.

## What it does

- **Watch by link** — text any product URL (Mercado Livre, Amazon, Kabum, or
  anything shipping schema.org JSON-LD) and it confirms the watch with the
  current price in one line.
- **Watch by name** — "pesquisa playstation 5" returns a priced menu; you
  pick what to watch.
- **Alerts that matter** — a drop past your threshold (default 5%), a target
  price you set, an all-time low, stock running out and coming back. No
  re-alerts, no noise; a quiet sweep says nothing.
- **Morning digest** — one short message: what moved, what's at its floor,
  what's unreadable.
- **Screenshot fallback** — when a store bot-walls the container, send a
  screenshot and the agent reads the price off the image.
- **"Compro ou espero?"** — opinions from collected history only, never
  invented.

## Install

One Plow line per agent. From your machine:

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"

git clone https://github.com/emanuellcoelho/vigia-hermes-agent.git
cd vigia-hermes-agent

plow-agents login             # once per account; text the activation phrase
plow-agents lines             # pick a free line
plow-agents mint ln_xxx       # writes ./plow-credentials
docker compose up --build -d
```

Watch `docker compose logs -f agent` until
`plow-init: configured ... as cht_` appears, then text your line to talk to
it. The first product link you send is a watch — onboarding happens after
that, never before.

Optional: set `SCRAPERAPI_KEY` in the environment (free tier at
[scraperapi.com](https://www.scraperapi.com)) to turn on the professional
scraping fallback for bot-walled stores.

| To | Run |
| --- | --- |
| rebuild after edits, keep memory | `docker compose up --build -d` |
| reset local state | `docker compose down -v && docker compose up --build -d` |
| retire the agent | `plow-agents revoke && docker compose down -v` |

## Architecture

```
skills/vigia-watch/scripts/
├── watch.py            # thin CLI; every command answers one JSON object
├── kit/                # domain-free infrastructure: clock, http, jsonio
└── vigia/
    ├── models.py       # Item, PricePoint, Alert — explicit serialization
    ├── store.py        # one JSON file in the agent's home, written atomically
    ├── sources/        # Source seam: ML API → JSON-LD → Amazon; search; ScraperAPI
    └── engine/
        ├── alerts.py   # pure rules: thresholds, targets, floors, dedup
        ├── sweep.py    # one bad item never ends a sweep
        └── digest.py   # the morning payload

skills/vigia-watch/SKILL.md    # the voice: menus, alerts, honesty rules
skills/vigia-digest/SKILL.md   # the morning read and "compro ou espero?"
skills/vigia-onboarding/SKILL.md  # first contact, after the first value
```

Two layers by design: **scripts are mechanical** (one JSON object on stdout,
exit 0/1/2, no human words) and **SKILL.md files are the voice** (templates,
language mirroring, what may never be invented). `kit/` knows nothing about
prices — it is the part a second agent reuses. Alert logic is pure: no IO,
no clock reads, injectable time in tests.

Schedules, registered by the agent itself during onboarding:

| name | schedule (container TZ) | delivery |
| --- | --- | --- |
| `vigia-sweep` | `0 9,15,21 * * *` | one message per alert; quiet = nothing |
| `vigia-digest` | `30 8 * * *` (yours to choose) | cron `--deliver` to your chat |

## Privacy

The usage reporter publishes **token counts only** — day × model, no prompts,
no URLs, no watched products. Watched items live in the agent's own volume
(`/var/lib/hermes/vigia/`); nothing under the tracked tree carries a
credential, a chat id, or a person's data.

## Tests

```sh
python3 -m pytest tests/ -q
```

Pure and fixture-fed: no network, no clock sleeps.

## Where changes go

- Boot, `plow-init`, gateway config, the base persona —
  [`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent). A base
  bug is fixed there and arrives here as a digest bump.
- The per-turn chat framing and Plow tools —
  [`hermes-plugin-plow`](https://github.com/plow-pbc/hermes-plugin-plow).
- This repo's own conventions and the fork guide — [`AGENTS.md`](AGENTS.md).

## License

[MIT](LICENSE) — with Apache-2.0 attributions for parts derived from
[plow-pbc](https://github.com/plow-pbc) repositories, in [NOTICE](NOTICE).
