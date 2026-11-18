---
name: chat-room-membership-audit
description: "Use when auditing who is in a chat room vs the registry."
category: agent-coordination
version: 1.0.1
author: Gentech
license: proprietary
tags: [telegram, room, membership, audit, registry, collaborators, drift]
related_skills:
  - telegram-group-ownership-diagnostic
  - collaborator-identification
metadata:
  hermes:
    tags: [telegram, room, membership, audit, registry, collaborators, drift]
    related_skills: [telegram-group-ownership-diagnostic, collaborator-identification]
---

# Chat room membership audit

## When to Use

- A per-group **collaborator audit** — "audit the people in your group and report back".
- Building a **migration manifest** before rooms move to another platform (who must be re-invited).
- "Where does the collaborator registry disagree with the live room?"
- Any ask for a **roster**: who is present / left / kicked / never joined.

Do **not** use this for "the bot isn't replying in group Y" — that is an ownership/health diagnosis
(`telegram-group-ownership-diagnostic`), and restarting a gateway is not an audit.

## What this is

An **inventory** ask ("audit the collaborators in your group", a migration manifest) is not the same as a
**diagnosis** ask. Diagnosis asks who can *see* the room; this asks who is actually **in** it, and where the
internal collaborator registry disagrees with the platform.

**The product is the disagreement, not the roster.** A list of names answers nothing; "two of five registry
people are in this room, one left, two never joined, and three registry rows claim `active`" is the finding
the requester can act on.

## Rules that apply to every cell

1. **Only the room's owning seat can measure its room.** Each bot is a member of its own room alone — a
   seat calling `getChat` on another's room gets `Bad Request: chat not found`. No central seat can audit
   all rooms; the owner's measurement is the only one that exists. Say this in the report — it is why the
   ask is addressed to the owner.
2. **The registry is the CLAIM; the platform API is the MEASUREMENT.** Never let a registry field stand in
   for a measured status, including a field that agrees with what you expect.
3. **UNKNOWN beats a guess in every cell**, and a field you could not measure is reported as UNKNOWN rather
   than omitted. An audit exists to catch the errors a confident guess would reproduce.
4. **Read-only.** No `setChat*`, `banChatMember`, `unbanChatMember`, `promoteChatMember`, no invite
   creation, no allowlist edit. List the methods you actually called so "read-only" is checkable, not
   asserted.
5. **`verified_at` is a `date -u` taken at the moment of the calls**, pasted into every row. "allowed"
   with no date is folklore.

## Procedure

1. **Find your room id and CONFIRM it.** It is usually not in `config.yaml`; recover it from the fleet's own
   bot→room registry note in the brain, then break ties between candidate ids by which one your own crons
   and tools actually deliver to. **Confirm with `getChat` before reporting anything** — a wrong id
   silently audits a different room.
2. **Identify yourself first** (`getMe`): the bot id and username make the administrators list readable and
   let you subtract yourself from the human count.
3. **Measure the room**: `getChat` (title, type) → `getChatMemberCount` (the number) →
   `getChatAdministrators` (every admin with id and status; flag which entries are bots).
4. **Measure each person** in the collaborator registry by their stored id: `getChatMember`. Wrap every call
   so a non-200 is captured as data instead of raising — for half a roster, the error *is* the answer.
5. **Reconcile the count** before writing the report:
   `getChatMemberCount` = (enumerated humans present) + (bot accounts in the room).
   When those agree there is **no unlisted human member**, and that reconciliation — not the API number — is
   what makes the roster evidence rather than a sample. It is also the one verification the reader cannot
   reproduce from their own seat.
6. **Report one row per person**, `group` on every row:
   `group · person · telegram_id · membership(present|left|kicked|never) · scope · authority(read|recommend|act) · verified_at`
   - `scope` = the registry's `topics` array.
   - `authority` = the registry's `permissions` entry **only when it names an authority level**
     (`recommend`, `all`). A `permissions` array listing topics is a scope, not an authority → UNKNOWN,
     never promoted into a level. For a non-member there is no live in-room authority to measure → UNKNOWN.
   - Show the raw statuses underneath the prose so your wording is not the only evidence.
7. **Close with the migration arithmetic**: of N registry people, how many are in the room, how many are
   former members, how many never joined. "Copy the registry forward" carries every non-member with it.

`scripts/room_membership_probe.py` runs steps 2–4 and prints the reconciliation; give it the chat id and
`mapping.json`. `references/registry-vs-world-drift.md` holds the status→membership table, the drift classes
to look for, and the portability caveat.

## Pitfalls

- ❌ **Auditing from any seat but the room's owner** — every other seat gets `chat not found`, and a report
  built on that is a report about nothing.
- ❌ **Trusting the registry's stored room id without `getChat`** — confirming the title is the only proof you
  measured the intended room.
- ❌ **Reporting the count as the roster.** It is a number; `getChatMember` only answers for ids you already
  know, so the count becomes evidence only through the reconciliation.
- ❌ **Counting your own bot as a person.** Your bot is a member and usually an admin — it inflates both the
  count and the admin list.
- ❌ **Equating "in the registry" with "in the room".** The commonest audit finding is a registry row whose
  `status: active` measures `left` or `never`.
- ❌ **Carrying one platform's method names onto another.** The discipline is portable; the calls are not —
  re-derive the read-only calls for the platform you are actually auditing.
