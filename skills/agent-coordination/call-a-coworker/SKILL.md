---
name: call-a-coworker
description: "Use when work needs a fact from another seat's jurisdiction. Ask, don't guess."
category: core
priority: critical
version: 1.0.0
author: GenTech Labs
tags: [routing, jurisdiction, peer-dm, handoff, coordination, fleet]
---

# Call a coworker — jurisdiction before inference

**Jordan, 2026-11-21:** *"the same way we have model routing for different tasks, we should also have
'call a coworker' … whenever you're referencing something that's out of your jurisdiction, you immediately go
and ask the other agent about it. It's almost like we're able to get on-demand answers about things we're
working on."*

`routing` answers **"which group does this topic belong to?"**
**This skill answers "am I allowed to state this as fact, or must I ask the seat that owns it?"**

They are different questions. A topic can be *yours to mention* and still be **theirs to decide.**

---

## The rule

> **Jurisdiction is about OWNERSHIP OF THE FACT, not about the topic's name.**

If the answer lives in someone else's lane, **asking costs one DM and gives you the real number.** Guessing
costs a wrong number in a report Jordan reads, and it is not recoverable by apologising — **he acts on
numbers.**

**Ask. It's cheaper. Every time.**

---

## It runs BOTH WAYS — this is a fleet protocol, not an HQ habit

**Jordan, 2026-11-21:** *"It can be vice versa if I start something in another group."*

**The most likely person to start work in the wrong lane is Jordan himself** — he opens a thread in Treasury
about a token, asks Arthur a question about a contract, or drops a build idea in EDU. **The seat that receives
it owns the first move**, not HQ:

| Jordan opens a thread in… | that seat must | because |
|---|---|---|
| **Treasury** (a token, a wallet, a position, a price) | answer it, **and call HQ** if the answer touches the catalogue, the API surfaces, or the fleet record | Treasury owns the number; **HQ owns the record** |
| **EDU** (a lesson, a build, "explain how X works") | answer it, **and call HQ** if it needs a build, a deploy, or a queue row | Arthur explains what we built; **HQ ships it** |
| **Social / content** (what was published, what a post says) | **Jordan is the author here** — Proto J is his avatar, not a seat | there is no third party to ask |
| **HQ** (everything else) | HQ calls the owner, **and says so** | the default |

**No lane is a dead end.** A question that starts in Treasury and needs a build **does not get silently
dropped** — **Treasury calls HQ the same way HQ calls Treasury**, with the same five fields, to the same
standard, and HQ answers within the same 2-day rule.

**The reciprocal duty is HQ's, and it is the harder half:** when a peer seat asks HQ something, **HQ answers in
their lane, on time, and does not treat a peer's question as lower priority than Jordan's.** A fleet where only
downward asks get answered is not a mesh — **it is a queue with extra steps.**

---

## The map — who owns what

| Fact / decision | Owner | Why not you |
|---|---|---|
| **Anything touching wallets, keys, capital, on-chain identity, or a financial decision** | **Treasury** | **Jordan's standing order: "anything that has to do with the wallets or anything financial, you always wanna speak to treasury."** This is the hardest line in the fleet. |
| **Explaining what we build, the lessons, the curriculum, why a product works the way it does** | **Arthur** (EDU) | Arthur is the heir to the Labs lane: `DMOB (Labs) → gizmo → folded → EDU`. **He breaks down and explains what we actually built.** |
| **The content rail, post status, what was published and when** | **Proto J** | ⚠️ **Jordan's own avatar, not an agent** — ask Jordan, or read `06-Content/`. Do not attribute work to "Proto J the bot." |
| **Home-lab capability, GPU work, Blender/ComfyUI, local builds** | **Forge** | Off-mesh by design — **vault handoff only**, no DM path. |
| **Fleet coordination, routing, verification, the record** | **You (HQ)** | Yours. Do not delegate this. |

**A queue item's owner is part of the fact.** If #92 belongs to Treasury, **asking Treasury about #92 is
not a courtesy — it is the only correct way to work the row.**

---

## The procedure

### 1 · Decide whether you are blocked
- **You may state it** if it is general knowledge or **already measured by you, with the measurement named.**
- **You must ask** if the answer depends on **a key you do not hold, a ledger you do not own, a decision
  someone else makes, or a fact that changes without your involvement.**

### 1b · Before repeating work, ask who already did it
**Jordan's rule, verbatim: *"if you want to speak with all agents and ask hey Jordan wants to do this — have
we done this in this group already?"*** A reflection pass, a cron fix sweep, a rename, a schema change: **the
same intent is routinely already in flight somewhere else, and a second run produces two records that
disagree.**

**Before starting any fleet-wide pass, one short DM per seat, three questions and no new work:**

```
(1) have you ALREADY run <this>? — date + what it changed
(2) does your seat have its own <job/skill> for it? — id + schedule, or NONE
(3) what is still BROKEN on your seat that this pass should touch?
```

**Ask for a short answer and say why** ("Jordan wants to avoid redoing work you already did") — a seat told
the purpose answers in two lines; a seat asked an open question writes a report.

**⚠️ DM replies truncate around 240 characters.** A long answer arrives cut mid-sentence and reads like a
broken transport. Follow up with **"reply in under 200 characters: finish this sentence — '<prefix> [ ? ]'"**,
which lands the missing clause in one exchange instead of three.

**⚠️ Verify the answer before repeating it, even from the owner.** A seat answers from its *belief* about its
own scripts, and a fix that landed last night is not yet in that belief. **Read the file, then report** — and
if the seat was wrong about itself, that is a finding, not a lie.

### 1c · Announce the fix to the seat that reported the bug
**A fix nobody is told about is a fix that gets re-reported forever.** When you repair something a peer seat
flagged — a wrapper grading the wrong department, a stale path, a broken job — **send that seat one line
saying it is fixed and what changed.** Otherwise its next self-report repeats the old symptom, and the fleet
spends a cycle arguing with a ghost.

### 2 · Ask the owner — both channels, in this order
```bash
# The canonical sender. Flags, NOT positional args — a positional seat+text is rejected.
python3 /opt/data/scripts/peer-dm.py --seat gentech-treasury --text "…"
python3 /opt/data/scripts/peer-dm.py --seat arthur         --text "…"
```
**A `⏳ QUEUED` reply means the ask was SPOOLED, not that it will arrive.** The seat was busy inside the answer
window, so the message went to the spool file and `peer-dm-flush.sh` retries it on cron (every 20 min). **Do not
re-send on the first queue, and do not conclude the transport is down** — a spooled row is a real, durable record
that the ask exists.

**But the spool is best-effort, and the vault note is the delivery of record — never let a queued row stand in for
the note.** Two properties of the implementation make a queue an *unverified* delivery, not a receipt:

- **The spool is ONE shared file, not one per sender** (`profiles/gentech/state/dm-spool.jsonl`), and it is written
  with a read-modify-write, no lock. **Two seats enqueuing in the same instant can lose a row.** Reproduce before
trusting any queue you have not tested: fire N concurrent enqueues of distinct texts and compare rows on disk to
  attempts — a shortfall at 60 attempts means the loss is rare, a shortfall at several hundred means it is real.
- **A queued message is never re-validated against reality.** It is delivered verbatim minutes or hours later, so a
  nudge queued at 10:31 can arrive after the item it complains about was closed at 10:33. **Read the spool row's
  `queued_at` and compare it to your own closure timestamp before doing the work again** — if your fix predates the
  queue, reply with the closure and the timestamps, and say the nag was stale in flight.

So: queue = the doorbell rang; **vault handoff = the record exists.** Write both, and when a queue is doing
something that matters, test it rather than trusting it.

**⚠️ `hermes peer dm fleet/<seat> "…"` also reaches the seat, but prefer `peer-dm.py`.** The `hermes peer dm`
form blocks until it gets a reply and **times out client-side after ~180s on any long turn** — printing nothing
that says whether the message landed. A client timeout is not a delivery failure: verify delivery from the
seat's own `logs/gateway.log` (`inbound message: platform=local user=api-peer msg='…'`), never from your
client's silence. **Symptom to recognise: a seat that keeps repeating the same handoff is usually a seat whose
ACK never reached the asker — check the spool before re-sending.**

**Then write the vault handoff — it is the delivery of record.** A DM that lands nowhere is silence.

**Forge has no peer: vault only, always.**

### 2b · Prove the ask LEFT before you call it asked
**A command you ran is not a message that arrived.** Sending has three outcomes and only one of them is
success, so read which one you got:

| what you see | what it means | what to do |
|---|---|---|
| a reply from the seat | delivered and answered | go to step 4 |
| `⏳ QUEUED → <seat>` + a spool path | **delivered doorbell** — seat was busy | nothing; the flush cron retries it |
| a usage/argument error, or anything that never printed a seat name | **nothing was sent** | fix the invocation and send again |

**If the client itself errors — bad flags, a wrapper/install problem, a usage message — the message never
left, and reporting it as "I asked Treasury" is a false receipt.** The reliable sender is the script with
flags: `--seat <name> --text "…"` (positional `seat text` is rejected outright). **After any send, read
`profiles/<seat>/state/dm-spool.jsonl` — a row there is the evidence the ask exists.** Do not conclude the
transport is down from one failed invocation; a wrong argument and a dead peer are different diagnoses.

### 2c · A protocol only HQ knows is not a protocol
**When you create or change a fleet-wide protocol, message every seat it binds in the same pass — and say
what is new in one line.** A skill synced to four seats is *available*; a seat that was never told has no
reason to fire it. **The sync makes it loadable, the DM makes it live.** Do not ask for an ACK on a policy
announcement — announce, don't assign work.

### 3 · Make the ask answerable
**A vague question gets a vague answer, and that is the asker's defect.** Every ask carries:

- **the exact question** (one, not five)
- **what you will do with the answer**
- **what "done" looks like**
- **the deadline, and what happens if it is missed**
- **what you already measured**, so they correct rather than repeat

```
ASK  ·  who controls 0x24c3382f668bfa59f0ce69dae03d2d2bf22bbd0f  (X Layer tokens 2847/2848/2849/4905)?
WHY  ·  deciding whether those 8004scan entries can be retired or only reported
DONE ·  "we hold the key" / "we do not" / "unknown, and here is how to find out"
BY   ·  before the 8004scan consolidation lands
MEAS  ·  7 entries, 3 owner addresses, 4 chains — I have the list, I do not have the keys
```

### 4 · Report the answer as theirs
**Quote the seat, name the date, and never launder a peer's answer into your own voice.**
*"Treasury measured X on 2026-11-21"* — **so that when it is wrong, the record says who was wrong**, and
when it is right, **the seat that did the work gets the credit.**

### 5 · If they do not answer
**2 days to answer, escalate on day 3** (the fleet Colleague Rule). **In the meantime: mark it PENDING with
the gate named.** **Never fill the gap with a plausible number.** *Unverified* is a complete answer.

---

## What this is NOT

- **Not a replacement for measuring.** If you *can* check it yourself in one command, **check it.** Ask a
  coworker for what you cannot reach, not for what you would rather not do.
- **Not permission to route everything.** A seat that asks about its own lane is **abdicating**, and that is
  its own defect.
- **Not a substitute for the vault.** The DM is a doorbell; **the handoff note is the record.**

---

## The failure this prevents

**Measured, repeatedly, in this fleet:**

- a registry generator reading a **dead snapshot** for weeks, because nobody asked the owner which file was live
- three seats running an **11-day-old engine**, because each assumed its copy was current
- **seven 8004scan entries** treated as "duplicates to rename", when the real question — *whose keys are these?* —
  belonged to Treasury all along

**In every case the work was reasonable and the ownership was wrong.** The cost was not the question; it was
**answering it without asking.**

## Learned on gentech (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

**A `⏳ QUEUED` reply is a DELIVERED doorbell, not a failure** — and measured on 2026-11-23 it is usually **more**
than that: the message has normally already reached the seat, and only *the reply* was missing. So:
- **Never re-send because a send looked slow.** Check the seat's own `logs/gateway.log` for the text FIRST
  (`inbound message: platform=local user=api-peer msg='…'`). If it is there, the delivery happened.
- **This is what produced repeated handoffs across the fleet:** `hermes peer dm` posts, then waits for a reply;
  the wait timing out was read as *delivery failed*, so the row was retried and the seat received the same
  message up to five times. One colleague saw the same update three times in an hour, all of them genuine
  deliveries. **The fix is in `peer-dm.py`: a timeout is now checked against the seat's inbound log before any
  retry.**

