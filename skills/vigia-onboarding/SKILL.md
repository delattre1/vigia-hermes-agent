---
name: vigia-onboarding
description: First-contact setup — timezone, language, digest time and alert preference. Use when a watch list exists but onboarding is unfinished (onboarding_missing is non-empty), or the user asks to change these preferences.
---

# Vigia Onboarding — once, after the first value

The first-value rule outranks this conversation: **a product link is watched
before any question is asked.** Onboarding starts only after a watch is
confirmed, and it is a conversation, not a form — one or two questions per
message, in the user's language.

Finished means `watch.py list` answers `onboarding_missing: []`.

## The questions, in order

1. **Language** — you detect it from their messages; no question. Save it the
   first time they reply (`config set language=pt-BR`).
2. **Timezone** — needed so the resumo da manhã lands at the right local
   hour. Say "resumo" to the user, never "digest" — that is the command's
   name, not a word for people. Ask plainly; if they say a city, use its
   IANA zone. Save it.
3. **Digest time** — offer the default: "resumo todo dia às 08:30, bom?"
   Save as `digest_time=HH:MM`, and `digest_enabled=false` if they decline.
4. **Alert rule** — offer the default: "aviso quando cair 5%". If they name a
   price instead, save it as the watched item's target
   (`watch.py add ... --target` on the next link, or per item with
   `--threshold`).

## Timezone is fixed at boot

The container's `TZ` is set from `timezone` in the config **when the
container starts**. After saving a timezone, compare it with the current
`echo $TZ`:

- Same: register the schedules now (below).
- Different: say the zone lands "no próximo reinício" and register the
  schedules only after that restart. **Never register schedules whose zone
  disagrees with the container** — they would fire at the wrong local hour,
  silently, which is the one failure a watcher cannot absorb.

## Registering the schedules (after config is complete)

Schedules are registered once, by you, from a turn (a turn carries the
gateway's environment; a bare exec does not):

    /opt/hermes/bin/hermes cron create "0 9,15,21 * * *" \
      "Run the vigia sweep now: execute watch.py check, compose each alert in the user's language, post each one with post_chat.py; if there are no alerts post nothing and end with NO_REPLY." \
      --name vigia-sweep --skill vigia-watch \
      --model anthropic/claude-sonnet-5 --provider plow

    /opt/hermes/bin/hermes cron create "30 8 * * *" \
      "Run the vigia digest now: execute watch.py digest and compose the morning digest in the user's language as your final response." \
      --name vigia-digest --skill vigia-digest \
      --model anthropic/claude-sonnet-5 --provider plow \
      --deliver "plow_chat:${PLOW_HOME_CHANNEL}"

A cron created without `--model` and `--provider` lands with no LLM provider
and fails every run with "No LLM provider configured" — always pass both.

Two changes to honor, with a restart between them: a new `digest_time`
re-registers the digest cron (remove the old one first — `hermes cron remove
vigia-digest`), and a new timezone needs the restart above before anything is
registered or re-registered. If a job already exists, skip it — never
duplicate a schedule.
