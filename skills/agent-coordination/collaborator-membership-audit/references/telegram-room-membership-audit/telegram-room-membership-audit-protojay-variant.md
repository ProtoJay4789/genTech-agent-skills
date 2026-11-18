---
name: telegram-room-membership-audit
description: "Use when auditing who is in a Telegram room."
version: 1.0.0
author: protojay (SOCIAL seat)
license: MIT
tags: [telegram, membership, audit, bot-api, roster, verification, collaborators]
trigger: "A per-room collaborator/roster audit; 'is X still in the room'; verifying which chat id is real; building a migration manifest of room members; a member's presence is disputed between a registry file and the room."
metadata:
  hermes:
    tags: [telegram, membership, audit, bot-api, roster, verification, collaborators]
    related_skills: [telegram-member-recovery, telegram-group-ownership-diagnostic, claim-provenance]
---

# Telegram room membership audit (read-only)

## When to Use

- A per-room collaborator or roster audit is asked for, or a migration manifest of room members is being built.
- Someone asks "is X still in the room", or a registry file and the room disagree about a member's presence.
- You need to confirm which chat id is the real room before anything is delivered into it.
- **Not** for changing membership — that is `telegram-member-recovery`'s territory (unban, invite, allowlist).

**Class of task:** measure, from inside one room, who is in it and in what state — and report it so a
registry can be corrected. **Never** as a membership *change*: an audit that edits the thing it measures is
worthless, so no `add`/`remove`/`promote`/`invite`/`restrict`/`unban` call is made, and you say so explicitly.

**The one rule: UNKNOWN beats a plausible verdict.** A `left`/`kicked`/`never` you did not actually measure
is the exact error these audits exist to catch — a roster is a measurement, not a narrative.

## Why a seat must do its own room

A bot only sees chats it is a **member** of. `getChat` from any other seat's bot returns
`400 Bad Request: chat not found` for a room that is alive and answering its own seat — the same answer a
deleted room gives. So a central audit is impossible by construction, and a "chat not found" line in a
report is an artifact of the wrong vantage point, never evidence of a dead room.

## Procedure

1. **Establish the id you actually own, from the config layer.** `grep -E '^TELEGRAM_HOME_CHANNEL=' <profile>/.env`
   — then settle it with a live `getChat`. **A doc layer can be wrong in either direction**: an identity/notes
   file may still declare a working id dead (or carry an old id as the truth), and it loads every turn. Trust
   the live call; when a file disagrees with it, fix the file you own and name the correction.
2. **Run the read-only probe:** `scripts/room-membership-probe.py`. It calls only `getMe`, `getChat`,
   `getChatMemberCount`, `getChatAdministrators`, `getChatMember`, never prints the bot token, and prints the
   controls for you.
3. **Room-level:** `getChat` (title, `type`), `getChatMemberCount`, `getChatAdministrators` (every admin with
   id + status).
4. **Per person:** `getChatMember` for each id in the registry, one call each — record the raw `status` or the
   raw error, never a paraphrase.
5. **Completeness check before you call the roster done:** if `getChatMemberCount == len(admins)`, every member
   is named — say that, because it is what makes "and nobody else is in here" a measurement instead of a guess.
   If the count is larger, you are **not** holding the roster: say which members you cannot enumerate and why.
   Admins are not the roster; a plain `member` never appears in `getChatAdministrators`.
6. **Run the controls — this is not optional.** A known-member id (your own bot) and a nonsense id (`user_id=1`)
   must both be probed before you interpret anyone else's result (see the ambiguity pitfall below).
7. **Report one row per person, in the fields you were asked for, including the "UNKNOWN" ones.** If the ask
   says "six fields" and lists seven, give all seven and note the count discrepancy — the collector parses
   labels, not intentions. Add the room-level block (id, title, type, count, admins) and the `verified_at`
   stamp from `date -u` at the moment you measured.
8. **State the limits in the artifact:** invite links not redeemed, join requests, and any roster you could
   not enumerate are **not measurable** from your vantage point — say so rather than implying zero.

## Pitfalls (each one cost real time)

- ❌ **Treating `400 PARTICIPANT_ID_INVALID` as "not a member".** Telegram returns that same error for a user
  who is merely not in the chat **and** for an id that is not a user at all. Probe a nonsense id as a control:
  if it returns the same error, your instrument **cannot** distinguish non-member from non-user, so `never`,
  `left` and `kicked` are all unsupportable. Report `UNKNOWN` + the one fact you do have ("absent today").
- ❌ **Reading `chat not found` from another seat's bot as a dead room.** See the vantage-point rule above;
  the correct line in a report is "not measurable from that seat (its bot is not a member)".
- ❌ **Inferring authority or scope from the room.** Telegram has no authority model; those are registry
  facts. When the registry lists topics but **no** authority keyword, the authority is `UNKNOWN` — do not
  default it to `read` because that reads like the safe answer.
- ❌ **Reporting a `status: active` registry entry as membership.** File-vs-world disagreement is the finding
  ("4 of 5 rows say active, none of them is in the room"), not a membership verdict: state the disagreement
  and leave the membership column `UNKNOWN` where it is unmeasurable.
- ❌ **Counting an idle log as proof of silence.** Absence of inbound events in `gateway.log` is **weak**
  evidence — a bot in privacy mode never receives ordinary group messages. Label it as weak when you use it.
- ❌ **Trusting a truncated or unformatted id.** Telegram user ids are 10 digits; an allowlist entry with 9
  (`684274559` against a registered `6842745592`) resolves to nothing and matches no person. Report id-shape
  defects as findings, and act on the **numeric id**, not a username.
- ❌ **Writing ids back into a report from memory.** Copy each id from the API result in the same session; a
  half-remembered id is indistinguishable from a fabricated one.

## Related

- `agent-kit/telegram-member-recovery` — what to do once a status *is* measurable (removal = ban, unban first,
  allowlist is the other half).
- `gentech-ops/telegram-group-ownership-diagnostic` — "agent X isn't replying in group Y": which bot owns the
  room, and why a non-member bot's `getChat` proves nothing.
