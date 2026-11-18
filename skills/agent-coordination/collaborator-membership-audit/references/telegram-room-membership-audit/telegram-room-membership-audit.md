---
name: telegram-room-membership-audit
description: Use when asked who is really in a Telegram group.
category: gentech-ops
tags: [telegram, membership, audit, collaborators, read-only]
version: 1.0.0
author: gentech-treasury
license: MIT
metadata:
  hermes:
    tags: [telegram, membership, audit, collaborators, read-only]
    related_skills: [telegram-group-ownership-diagnostic, collaborator-identification, telegram-member-recovery]
---

# Telegram room membership audit

"Who is in this room?" has exactly one valid source: **the seat whose bot is a member.** From any other
profile `getChat` returns `Bad request: chat not found`, so a central audit is not possible and every room's
roster is that seat's measurement alone. Do not accept a roster from a file when the platform can answer.

## When to Use

- Asked "who is actually in this group / room?", or for a per-group collaborator inventory.
- Building a migration manifest (e.g. Telegram → Discord) that must not carry ghost members.
- A registry file claims someone is `active` and you need the platform's answer.

## Method (read-only)

1. `getMe` — confirm which bot you are, so the row for "the bot itself" is not misread as a person.
2. `getChat` — title, type, id. This is also the membership probe: `ok:true` = your bot is in the room.
3. `getChatMemberCount` — the number you must reconcile against.
4. `getChatAdministrators` — every admin with id and status.
5. `getChatMember` per person in the collaborator registry (numeric id, not username).

**Change nothing.** No `banChatMember`, `promoteChatMember`, `unbanChatMember`, `setChat*`, no invite
creation. An audit that edits while measuring cannot be re-run against a clean state.

## Status mapping — and the two that get confused

| live status | report as |
|---|---|
| `creator` / `administrator` / `member` | **present** |
| `left` | **left** |
| `kicked` | **kicked** |
| `400 Bad Request: member not found` | **never** |

`member not found` ≠ `kicked`. `kicked` requires that the person was in the chat and is now banned;
`member not found` means Telegram has no record of that id in that chat (never joined — or an id it cannot
resolve). Collapsing the two is the exact error an audit exists to catch.

## The verification is arithmetic

`getChatMemberCount` must equal **the bot + every enumerated `present` human**. If the numbers disagree,
there is an unlisted member and the audit is **incomplete** — say that rather than shipping the roster you
happen to have. When they agree, say so explicitly: that reconciliation, not the field list, is what makes
the measurement trustworthy.

## Report shape

One row per person: `group · person · telegram_id · membership · scope · authority · verified_at`, with
**UNKNOWN** where the registry does not actually state the answer. Specific traps:

- **`permissions` arrays frequently name topics, not an authority level.** `["finance","defi"]` answers
  *scope*, not read/recommend/act. Do not upgrade a topic list into an authority.
- **A departed person has no live authority to measure** — `UNKNOWN` plus the registry's claim, not the
  registry's claim alone.
- **One `date -u` for the whole audit**, and state that all calls landed inside it.

## Drift is the normal finding

A `status: active` in a mapping file routinely reads `left`, `kicked` or `never` live. Report the measured
status **and** name the drift — "the file and the world disagree" is the deliverable, not a footnote. Also
check the handle: `getChatMember` returns the account as it is now, so `username: null` against a stored
`@handle` means username-keyed migrations will silently lose that person. Key on numeric id.

## Finding the room → bot mapping

`10-Labs/skills-distribution/agent-coordination/hermes-profile-clone-worker/references/worker-soul-and-bot-ownership.md`
carries the bot-handle / bot-id / room-id table (the same ids appear in `10-Labs/SOUL.md`). Confirm with
`getMe` + `getChat` before trusting it — the doc is a pointer, the API is the measurement.
