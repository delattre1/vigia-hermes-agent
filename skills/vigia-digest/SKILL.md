---
name: vigia-digest
description: The morning digest of everything being watched, and "compro ou espero?" price opinions. Use when the digest cron fires, or when the user asks for a summary of their watched prices or whether to buy now.
---

# Vigia Digest — the morning read

The user never hears the word "digest": in their language it is the
**resumo do dia** (pt-BR) or **morning roundup** (EN). The command keeps
its name; the words they read do not.

One payload, one message:

    /opt/hermes/.venv/bin/python3 /var/lib/hermes/skills/vigia-watch/scripts/watch.py digest

The final response of your turn IS the digest — the cron's `--deliver` relays
it to the owner's chat. Compose it in their language, short enough to read
standing up.

## Shape

Open with a header, one line per item, most interesting first — this order,
always:

    ☀️ *Vigia do dia* — 3 produtos

    1. 🎯 PS5 Digital — *R$ 3.799,00* 🇧🇷 Kabum — no seu preço-alvo
    2. 🏆 iPhone 15 — *R$ 4.999,00* 🇧🇷 Amazon — ⬇️ 8% desde ontem, novo mínimo
    3. Air Fryer — *R$ 399,00* 🇧🇷 Kabum — sem novidades

    ⚠️ Link ilegível há 2 dias: Teclado Keychron. Me manda um print?

Top of the list first: 🎯 items on target, then 🏆 floors, then movers
(`history`'s last two points tell you the movement), then the quiet ones
compressed: "Sem novidades: Air Fryer, Echo Dot." Stale items close the
digest with a ⚠️ line — which ones, for how long, and the offer to re-check
or take a screenshot. Never show an old price as if it were current.

The flag is the item currency's flag (BRL 🇧🇷, USD 🇺🇸). One line per item,
no paragraphs.

`"quiet": true` means one or two lines total: "☀️ Tudo quieto — 4 produtos
vigia­dos, nada se mexeu." A quiet morning is a good morning; it is not
silence.

## "Compro ou espero?"

When asked, run `watch.py history <id>` and answer from what it shows:

- How long you have watched, how many observations — a 3-day history is a
  3-day history, say so.
- Where the current price sits against `low` and `target`: distance in
  percent, trend of the last points.
- A honest verdict with a caveat, never a guarantee: "está R$ 40 acima do
  mínimo que vi; se não é urgente, esperar tem histórico a favor" — or the
  reverse. You do not know tomorrow's price, and you say that once, plainly.
