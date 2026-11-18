---
name: collaborator-membership-audit
description: "Use when auditing who is in a group vs the allowlist. Verify, then report."
version: 1.0.0
author: gentech-treasury
license: MIT
tags: [fleet, groups, membership, allowlist, collaborators, audit]
trigger: "When a group must confirm its collaborators are actually present and actually authorized — periodically, after a membership change, or when an instruction names a person the agent cannot place. NOT for retiring a person's data (see pre-deletion-inventory) and NOT for adding a seat (see telegram-bot-seat-provisioning)."
metadata:
  hermes:
    tags: [fleet, groups, membership, allowlist, collaborators, audit]
    related_skills: [pre-deletion-inventory, telegram-bot-seat-provisioning, identity, handoff-mesh]
---

# Collaborator Membership Audit — is everyone here, and is everyone allowed?

**Jordan's standing instruction (2026-10-18), verbatim:**

> *"This might be something that every group needs to audit — to make sure they have the right
> collaborators in the group and that they're on the allowed list… each agent should be an admin who
> can see everybody in the group, and then if you're missing something just shoot me a message in
> the group and let me know."*

**Two questions, answered separately — they fail differently and must never be merged:**

| question | source of truth | failure mode |
|---|---|---|
| **Is this person IN the group?** | the platform (Bot API `getChatMember`) | they never see messages meant for them |
| **Is this person AUTHORIZED?** | the allowlist (`tenants.json`) | an unlisted person is served, or a listed person is refused |

**A person can be present and unauthorized. A person can be authorized and absent. An audit that answers one and claims the other is the bug this skill exists to prevent.**

---

## The procedure

1. **Enumerate the group's actual members — from the platform, not from memory.**
   ```
   getChatMember(chat_id=<group>, user_id=<id>)
   ```
   **Verify by ID, never by username.** Usernames are optional, mutable, and go stale —
   *observed: Dadrian's `@Daydream` is stale and the Bot API now reports `username: None`
   while `status: member`. The **ID** `6842745592` is the durable handle; the username is not.*

   **⚠️ Compare ID *lengths* between the two stores before believing a person is missing.** *Observed:
   `TELEGRAM_ALLOWED_USERS` carried `684274559` (9 digits) while the registry carried `6842745592`
   (10) for the same person — a **truncation**, not a second person.* A truncated id fails the
   allowlist comparison silently, that person's messages get dropped, and a membership audit then
   reports a live collaborator as **absent**. **Telegram user ids are 10 digits — a 9-digit value in an
   allowlist is always a truncation.** Diff the lengths before you diff the answers.

2. **Resolve each member to an allowlist entry.** `tenants.json` is the registry. **If a member
   cannot be resolved, that is a finding — not a guess.**

3. **⚠️ Check the registry carries the durable handle.** **The gap found on 2026-10-18:**
   **every tenant in `tenants.json` had an EMPTY `telegram_id`.** The allowlist named wallets and
   statuses but **no platform identity** — so *"is he on the allowed list"* was **unanswerable from
   the registry alone**, and worked only because a separate guard resolved the ID at runtime.
   **An allowlist that cannot name its members' platform identity cannot audit its own membership.**

4. **Report gaps — do not fix them silently.** Jordan: *"shoot me a message in the group and let me
   know."* **A gap reported is a decision he can make; a gap fixed silently is a change nobody reviewed.**

---

## ⚠️ First prove the BOT can see the room — "chat not found" indicts the bot, not the room

**Each seat's bot token sees only the rooms it was actually added to.** Query any other room and
`getChat` returns `400 Bad Request: chat not found` — the *identical* answer you get for a room that
does not exist. **So "chat not found" carries no information about the room, and an auditor who reads
it as one will report live rooms as dead.**

**Rule: measure each room with the bot that lives in it.** Hold a room→seat map and query each room
through its own seat's token:

```bash
TOK=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' /opt/data/profiles/<seat>/.env | cut -d= -f2- | tr -d '"'\'' \r)
curl -s "https://api.telegram.org/bot${TOK}/getChat?chat_id=${GROUP}"
# ok:true + title  → THIS bot can see the room; now its getChatMember answers mean something
# chat not found   → this bot is not in the room. Say NOTHING about the room.
```

**A room our own mapping lists is real until measured through a bot that is in it.** Never renumber,
delete, or "correct" a room id off a `chat not found` from the wrong seat's token.

**⚠️ Word the row as measured, not as found-or-missing.** When a central/orchestrator seat queries a room
whose bot it does not own, its row must read **"not measurable from this seat — bot is not a member"**, never
"chat not found" or "missing". A row that says *not found* about a healthy room sends the next reader to
renumber a room that was never broken, and puts a live channel on a "dead" list in a migration manifest.

**⚠️ Prove completeness before you claim a full roster.** `getChatMemberCount` **equal to** the number of
rows from `getChatAdministrators` means the member list is *fully* enumerated — you can say "every member is
accounted for, there is no unlisted member". When the count is **larger** than the rows you can name, that
gap *is* the finding, and it gets reported rather than smoothed over. Never write "all members checked" when
you only checked the ones the API volunteered.

---

## ⚠️ An error code is not a diagnosis — validate it against a known-real control

**Observed 2026-10-19, in two rooms on the same afternoon:** `getChatMember` returns
`400 Bad Request: PARTICIPANT_ID_INVALID` for a person with no participation record in that chat, and one
ring wrote it up as *"the id itself failed validation — the registry entry is suspect."*

**It is not.** `PARTICIPANT_ID_INVALID` and `member not found` both mean **"no participation record for this
id in this chat."** A deleted account and a perfectly valid account that never joined are
**indistinguishable** through this API.

**Rule: before you write "the ID is invalid" into a finding, run a control** — query the *same* chat for an
id you already know is real (someone recorded as a member elsewhere, e.g. Dadrian `6842745592`). If the
known-real id returns the **byte-identical** error, the error carries no information about validity. Report
**UNVERIFIED, not disproven**, and name what would actually settle it: the person messages the bot, or the
owner confirms the number. **Never "fix" a registry id off an indistinguishable error** — you will replace a
good id with a guess.

---

## ⚠️ One API answer, one vocabulary — "never" is a claim the API cannot support

**Observed 2026-10-19, four rooms, one afternoon:** the same result got **three different labels** from three
rings. `member not found` was written as **"never"** by one and **"UNKNOWN"** by another; `PARTICIPANT_ID_INVALID`
as "unknown" by one and "never" by another.

**Neither text supports any of those words.** Both mean exactly one thing: **this chat has no participation
record for this id.** A control settles it — call `getChatMember` for a **known member** (resolves), for a
**nonsense id** like `1` (returns `PARTICIPANT_ID_INVALID`), and for someone you know is real but absent
(returns the same). If a nonsense id and a real person produce the same answer, the answer says nothing about
the person.

**Proof that a good id produces it:** one collaborator returns a no-record error in three rooms and is a
**`member` of the fourth** with the identical id. The id was never wrong; the room was.

**Use these three labels, and only these:**

| label | means | evidence required |
|---|---|---|
| `present` | in the room **now** | a status came back — `creator` / `administrator` / `member` / `restricted` with `is_member: true` |
| `former` | in the room once, out now | a status came back — `left` or `kicked` |
| `no record` | no participation record **in this chat** | a 400 text; **history unknown, no claim about the person** |

**Retire "never"** unless the id has been independently confirmed valid *and* the person confirmed as never
having been in that room. A downstream consumer — a migration manifest, an allowlist, a Discord roster — reads
"never" as a measured fact, and this one is not.

---

## ⚠️ Retiring a person's identity is NOT deleting their data

**Observed the same day:** an instruction to retire a collaborator's hub artifacts also read as
*"erase that stuff in the brain."* **248 documents mention that collaborator — including his live
tenant record, custody material, and a consent signed hours earlier.**

**Rule:** **a cleanup of *presentation* (a page, a hub, a listing) is not a cleanup of *records*
(the tenant entry, custody, consent, wallet baseline).** Enumerate the set and separate the two
before touching either.

## ⚠️ And retiring a wallet has an ORDER, or it strands money

**Rule:** **you cannot untrack a wallet that still holds money.**

**Observed:** a collaborator's wallet was to be retired from the config while it still held a live
LP position. **Two failures hide in the wrong order:**

1. **The watch stops** — the jobs that monitor the position no longer look at it, silently.
2. **The guard blocks the exit** — `signer == configured wallet` means a retired wallet's signer is
   **refused**, so the very withdrawal that would empty it cannot be executed.

**Correct order — always:** **new identity exists → funds move off the old one → THEN retire the old
record → AND update every document that attests to it** (consent records name addresses; a consent
citing a retired address attests to nothing).

---

## Removing a collaborator — the gate that actually closes is the ALLOWLIST

**Removing someone from the group does not remove their authorisation.** Presence and authority are
separate stores (table at the top), so a person kicked from every room still has their id in
`TELEGRAM_ALLOWED_USERS` on every seat — and every seat still serves them.

| stage | action | reversible? |
|---|---|---|
| 1 MEASURE | per-room `getChatMember`, each room through its **own** bot (above) | — |
| 2 CLOSE THE GATE | delete the id from `TELEGRAM_ALLOWED_USERS` on **every** profile `.env`, then restart those seats | yes |
| 3 MARK | registry membership → `left`, permissions → `[]`, dated status note | yes |
| 4 PURGE | profile, learner directory, caches, personal media | **no** |
| 5 STOP THE ENGINE | confirm no cron or generator still emits for them | yes |
| 6 FIX THE ROSTER AGENTS READ | the hardcoded name lists in `START-HERE.md` and the `wake-up-protocol` skill — edit the **shared core** and sync | yes |

**⚠️ Stage 6 — a THIRD store: the roster as agents read it.** Presence, authority and *documentation*
are three separate stores. The collaborator list is duplicated as **prose that every arriving agent
loads at session start** — a line naming the collaborators in `START-HERE.md` and in the
`wake-up-protocol` skill. **The registry is not where an agent learns who the collaborators are; that
line is.** Leave it and every new session is taught a roster that includes someone the company has
released — which is how a removed person keeps being named in handoffs months later. It is not
reachable from the registry, not reachable from the allowlist, and only findable by grepping the roster
sentence itself. **Edit the shared core copy, then sync and verify per seat** — the seat copies are
synced artifacts, so editing a seat is work the next sync reverts.

**Stage 2 is the one that actually stops contact, and it is the one most often skipped** — it lives in
`.env` (the owner's hand: env edit + restart), while stages 3–5 live in the vault. **Never report a
person as "removed" while their id is still in an allowlist.**

**⚠️ `membership` is a per-group DICT — set every group's value, never replace the dict.** Assigning
the string `"left"` in its place flattens the schema and breaks every consumer that indexes by group.
Print the value **before** and **after** the write and assert the shape survived:
```python
assert isinstance(m["membership"], dict), "REGRESSED — membership must stay a per-group dict"
```

**⚠️ Enumerate before purging — one grep cannot prove a purge.** The same person's data sits in the
registry, a learner directory, a per-learner cache, generated media **outside** the vault, and every
seat's **copy** of a shared skill. Count the hits, split live records from backups/snapshots/logs, and
report the split before deleting anything.

**⚠️ Two classes are systematically missed:**

- **Joint artifacts** — anything authored for the *pair* rather than the person: a shared hub page, a joint trip plan, a combined "A & B" dashboard. They are titled with **both** names, so a grep on the departing person's name alone finds them only by luck, and the other party's name finds the rest. Search the other party's name too, and search by artifact TYPE as well as by name (`find <vault> -iname '*hub*' -o -iname '*trip*'`).
- **Shared-skill DATA, not just shared-skill prose.** A person's live record can sit inside a *skill's* `data/` directory — learner registries, voice maps, rosters — which the fleet sync copies to **every seat**. Purging only the person's own files leaves the skill data intact, and the next sync **re-creates the record fleet-wide**. Treat the shared core's `data/` files as purge targets, purge there first, sync, then re-grep every seat. **⚠️ Do not trust the sync tool's own success line — verify propagation per seat, and verify the tool itself is alive.** A sync script whose configured source/target paths have gone stale still exits 0 and prints nothing alarming while changing nothing; a *drift count that never falls* is the tell, so run its dry-run and treat any non-zero pending count on a supposedly-synced fleet as evidence the sync has not been running. Target lists go stale when a seat is retired — a sync still naming retired seats silently skips the live ones, and its "complete" line covers only the subset it happened to reach. **A purge is only fleet-wide when every seat's copy was independently re-grepped.**

**⚠️ The vault is a git repo.** Deleting a file removes it from the working tree; history still holds
it. **Say that plainly rather than implying an erase**, and never rewrite history unasked.

---

## What a clean audit reports

```
group:            <name/id>
members present:  <n>  (verified by ID via the platform)
on the allowlist: <n>  (resolved via the registry)
PRESENT but NOT authorized:  <list or none>
AUTHORIZED but NOT present:  <list or none>
registry carries a durable identity for each?  yes/no   ← the field that makes this audit possible
ids that returned no record:  <list>   ← UNVERIFIED, not "invalid" — run the control above
membership vocabulary:        present | former | no record   ← never write "never"
gaps reported to:            <the group, per the standing instruction>
```


## Consolidated references

These were separate skills until 2026-10-19. Their triggers duplicated this one, so the bodies moved here rather than being rewritten — **the original text is preserved verbatim**, because a merge that paraphrases a procedure loses the details that made it work.

- **`chat-room-membership-audit`** — absorbed, full text at `references/chat-room-membership-audit/chat-room-membership-audit.md`. Trigger: "chat room membership audit" questions that used to resolve to a separate skill.
- **`telegram-room-membership-audit`** — absorbed, full text at `references/telegram-room-membership-audit/telegram-room-membership-audit.md`. Trigger: "telegram room membership audit" questions that used to resolve to a separate skill.
