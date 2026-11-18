---
name: telegram-group-routing
description: "Use when bots and humans share a Telegram room."
version: 1.0.1
author: gentech
license: MIT
category: agent-coordination
tags: [telegram, groups, routing, mentions, multi-agent, fleet]
metadata:
  hermes:
    tags: [telegram, groups, routing, mentions, multi-agent, fleet]
    related_skills:
      - agent-to-agent-messaging
      - telegram-bot-seat-provisioning
      - group-handoff-mesh
---

# Telegram group routing

## When to Use

Several bots and/or humans share one Telegram room, and you must decide who answers, who may run
commands, or whether the engine's routing features buy anything at all. Also load this when a seat is
silent in a room, when a "No home channel is set" notice appears, or before widening any group gate.

**Routing decides WHO ANSWERS a sentence in a room. It never decides whether WORK MOVED.**
Assignments, approvals and capital stay on the vault handoff; a mention is a doorbell that leaves
no residue. Confusing the two is the failure mode this skill exists to prevent.

## Measure the room before designing the routing

Two commands, no messaging, decided on evidence:

```bash
# who is actually in a room — the ONLY proof a bot can see it
grep -rho 'chat=-[0-9]*' /opt/data/profiles/<seat>/logs/*.log | sort | uniq -c
# who is allowed to give the bot orders at all
grep -E '^TELEGRAM_ALLOWED_USERS=|^TELEGRAM_ALLOWED_CHATS=' /opt/data/profiles/<seat>/.env
```

**A seat that has never logged inbound from a chat cannot be reached there — no setting fixes
absence.** Measured 2026-11-06 on this fleet: each of the four seats has exactly ONE room in its
inbound (`gentech` HQ, `arthur` EDU, `gentech-treasury` Strategies, `protojay` Social). No room is
shared. So the multi-bot-in-one-room features below buy **nothing** here, and enabling them would not
create the overlap. Say that rather than shipping a feature that looks like progress.

## The knobs (Telegram adapter, `platforms.telegram.extra` or `TELEGRAM_*` env)

| knob | default | what it does |
|---|---|---|
| `exclusive_bot_mentions` | **true** | mentioning a sibling bot routes the message away from us |
| `bots_require_mention` | false | another bot must explicitly @ us; kills two-bot quote-reply loops |
| `require_mention` | false | humans also need an @; turns free-response off |
| `mention_patterns` | unset | regex wake words for humans who won't type `@` |
| `free_response_chats` / `free_response_topics` | unset | rooms/topics where every message is answered (topic form `<chat_id>:<thread_id>`, General = `1`) |
| `observe_unmentioned_group_messages` | **false** | store skipped chatter as context, answer nothing |
| `allowed_chats` / `group_allowed_chats` / `allowed_topics` | unset | which rooms/topics the bot serves |
| `guest_mode` | false | let non-allowlisted rooms reach us via explicit @ |
| `group_sessions_per_user` | **true** (top-level) | one session per person per room |

**`observe_unmentioned_group_messages` is NOT a way to give a quiet seat ears.** It requires
`group_allowed_chats` ∩ `allowed_chats` explicitly set, and it stores at chat/topic scope — the
shared room would then see chatter that is not its own. Two settings to widen one seat's hearing, and
it changes the context of everyone sharing that room.

### Bot-loop rules worth copying into any multi-agent room

- **Human reply causality beats bot reply causality.** `bots_require_mention` gates BOTH sides of a
  bot-to-bot exchange: our reply must @ the sibling even though it replied to the human. Predictable
  (no heuristics, no infinite loop) at the cost of cosmetic @s in front of humans.
- **Names in text are not addressing.** Every room needs a structural wake that no regex can fake:
  reply-to, a slash command, or an explicit entity mention. A sibling bot's message is then a
  separate, gated channel.

### Command access is a separate axis from chat access

`allow_from` decides who may TALK to the bot; `allow_admin_from` / `group_allow_admin_from` decide
who may run SLASH COMMANDS, with a floor of `help` and `whoami` for everyone else. **No admin list
set means gating is off and every allowed user is an admin.** If a collaborator or learner is in a
room, name the floor explicitly; `/whoami` reports the effective level.

## The home channel

`TELEGRAM_HOME_CHANNEL` is the default delivery target when a job or handoff names none. It is NOT
required when every cron job carries an explicit `origin` chat id — **explicit targets are stronger
than a home channel**, and verifying them is a one-liner over `cron/jobs.json`.

**The "No home channel is set" notice fires on the first message of every NEW session while the key
is unset** — it looks like a regression after a `/new`, it is not. Setting it via `/sethome` in the
room is the only fix (it persists to config.yaml and the env). Do not troubleshoot the gateway for a
notice that is telling the truth.

## Where Hermes's design differs from ours

Hermes's Bot Mode (desktop, v0.21+) is a **conversational society**: named agents, a shared roster,
rooms where humans @-anyone. Our fleet is a **work mesh**: a file is the record, a DM is the wake, the
human is copied. Both are deliberate. Borrow the addressing conventions; do not borrow the assumption
that a conversation is a commitment.

Deliberately NOT adopted from Hermes's design:

- **Durable, resumable self-scheduled turns** (a bot scheduling its own follow-up turn). The design
  keeps the session too busy to serve the room, and a resumed turn is born from a process that forgot
  what it promised. Cron + a vault note covers the same need and both are readable afterwards.
- **`obsidian://` deep links in output.** The primary reading surface here is Telegram, where the
  scheme does not resolve. Links must be http(s) or a vault path the reader can copy.
- **`observe_unmentioned` for ears**, per the section above.

## Pitfalls

- **A room in the routing table is not a room the bot is in.** Verify with `getChat` and with inbound
  log lines; a documented id propagates through notes until it looks measured.
- **An id is not a token.** `/sethome`, `getChat` and every routing config want the numeric chat id;
  authentication wants the `NNNN:AA…` token.
- **Widening a gate to 'fix' a silent seat usually widens it for the wrong party.** Turn it on in one
  room, with a human watching, or not at all.
