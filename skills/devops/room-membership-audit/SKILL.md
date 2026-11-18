---
name: room-membership-audit
description: "Use when auditing who is really in a chat room."
category: devops
tags: [telegram, discord, audit, membership, registry, migration, read-only]
related_skills: [telegram-group-ownership-diagnostic, telegram-member-recovery, verify-after-every-action, claim-provenance]
version: 1.0.0
author: Gentech fleet
license: MIT
metadata:
  hermes:
    tags: [telegram, discord, audit, membership, registry, migration, read-only]
    related_skills: [telegram-group-ownership-diagnostic, telegram-member-recovery, verify-after-every-action, claim-provenance]
---

# Room membership audit — what the room actually contains

Inventorying a chat room's real membership and checking it against a collaborator registry. **Read-only by
default: add, remove, promote, invite, unban — none of them.** This is the manifest work that precedes a
migration, an access review, or a registry cleanup.

## When to use

- A coordinator orders a per-group collaborator audit ("who is really in your room?").
- A registry `status: active` is suspected of disagreeing with the platform.
- A room migration is planned (Telegram → Discord, one platform → another): **the inventory IS the
  manifest**, and a mapping copied forward without it carries ghosts.
- Someone left, was removed, or vanished, and the question is which of those three it was.

## The constraint that shapes everything

**A seat's bot is a member of its own room only.** `getChat` on any other seat's room answers
`Bad Request: chat not found`, so **no central seat can audit all rooms** — each room's inventory exists
only in the seat that owns it.

- Say this in the report. It explains why the audit was delegated, and it is why the result cannot be
  cross-checked from outside: the reconciliation below is the only proof there is.
- **Never let a "can't see it" from your own position be reported as "it isn't there"** — that is a claim
  about the room made from outside the room.

## Procedure

1. **Resolve the room before trusting any registry.** Registries list people and handles, not rooms. Take
   the chat id from the fleet doc that pairs bot → room, then confirm live: `getChat` → `id`, `title`,
   `type`. A title you did not expect means you are about to audit the wrong room.
2. **Take the room's own count:** `getChatMemberCount`.
3. **Take the admin list:** `getChatAdministrators` → for each, `status`, `user.id`, `username`, `is_bot`.
   Bots appear here; label them as bots, never as people.
4. **Probe every registry person individually:** `getChatMember(chat_id, user_id)`. There is no roster call
   — Telegram returns a number and an admin list, nothing more.
5. **Reconcile the count** (see below).
6. **Report one row per person** in the fields the ask names — group, person, platform id, membership,
   scope, authority, verified-at — with **one timestamp shared by every row**, taken at the moment of the
   calls, so a reader can tell the rows are one observation and not an afternoon of them.

## Verification is the reconciliation, not the per-person list

**`getChatMemberCount` must equal: bots in the room + humans you resolved as present.**

- **If it balances, you have proven there is no unlisted human in the room.** That is the finding worth
  reporting, and it is the only thing that turns a list of ids you already knew about into an inventory.
- If it does **not** balance, you have found someone the registry does not know about — report the gap and
  the size of it, and do not guess at names.
- State the arithmetic in the note ("3 = bot + jordan + dadrian"), so the reader can re-derive it without
  re-running your calls.

## Status → membership, and the word that must not be used

| API result | membership |
|---|---|
| `creator` / `administrator` / `member` | **present** — carry the raw status too: `creator` is not `member` |
| `left` | **former** |
| `kicked` | **kicked** — banned, and distinct from leaving |
| `400 member not found` / `PARTICIPANT_ID_INVALID` | **no record** |

**Never write "never" / "never joined".** The platform returns `member not found` both for an account that
had no participation record and for an id it cannot resolve in that chat; it is the *absence of a record*,
not proof of absence. The same id can return different text in different rooms — that inconsistency is the
tell that the wording is not load-bearing.

## Authority: never lift a topic list into an authority level

A registry `permissions` array often names **topics** (`finance`, `defi`) rather than an authority level.

- Report `read` / `recommend` / `act` **only** when the registry states one (`"recommend"`, `"all"`) **or**
  the platform corroborates it (`creator` plus full permissions).
- Otherwise write **`UNKNOWN`** and say why. A person who is not in the room has no live in-room authority
  to measure: `UNKNOWN`, with the registry's claim noted beside it — not silently upgraded.
- **`UNKNOWN` is a valid answer and a good one.** A topic list promoted to "act" is the exact error the
  audit exists to catch.

## Read-only, and prove it

Enumerate the calls you made in the report — `getMe`, `getChat`, `getChatMemberCount`,
`getChatAdministrators`, `getChatMember × N` — and state plainly that no `setChat*`, `banChatMember`,
`promoteChatMember`, `unbanChatMember` or invite creation was issued. "Read-only" asserted without the call
list is a promise; the list is a receipt.

## Drift classes this audit finds

- **Registry `active` vs room `former`** — the file and the world disagree. Report the pair, not just the
  room result: this is the finding, and it is usually several rows at once, not one.
- **Registry `active` vs room `no record`** — no participation record, or an id that does not resolve in
  that room. Rarer, worse, and invisible to anyone reading only the registry.
- **A missing status field** — reads as "fine" to every consumer that assumes presence, which is why the
  *absence* is the defect worth reporting.
- **Handle drift** — the registry stores a `username` the account no longer carries (or carries in a
  different case). Harmless for membership, **fatal for a username-keyed migration**.
- **A person with no id at all** — unprobeable. List the row as unprobeable rather than dropping it.

## Limits to state, not paper over

- Join dates, historical membership, invite links, pending join requests and *why* someone left are not
  exposed by these methods. Do not substitute inference for them.
- `getChatMemberCount` is a number, never a roster.
- If two rooms disagree about the same person, report both readings; do not average them into one verdict.

## Reporting shape

Use `templates/room-audit-report.md`. Required sections: room measured · one row per person · drift found ·
limits · changes made (none) · filed-vs-sent. **Deliver into the requesting seat's return lane and say
"filed", not "sent", unless you can point at a delivery receipt** — a DM that hangs or 401s prints nothing
and looks like success.

## Related

- `telegram-group-ownership-diagnostic` — the other question: "agent X isn't replying in group Y" (token
  ownership, kick vs stuck tool vs flood control). Use it when the ask is *why*, this one when the ask is
  *who*.
- `telegram-member-recovery` — a removed member cannot rejoin; bans vs link minting vs the allowlist.
- `verify-after-every-action` — the general discipline behind the reconciliation rule.
