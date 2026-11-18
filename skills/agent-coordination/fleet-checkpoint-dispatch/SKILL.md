---
name: fleet-checkpoint-dispatch
description: "Use when dispatching a fleet checkpoint and collecting ACKs."
category: agent-coordination
version: 1.0.0
author: Gentech
tags: [checkpoint, ack, dispatch, fleet, restart, coordination, verification]
license: MIT
related_skills:
  - checkpoint-ack
  - safe-update-restart
  - claim-provenance
metadata:
  hermes:
    tags: [checkpoint, ack, dispatch, fleet, restart, coordination, verification]
    related_skills: [checkpoint-ack, safe-update-restart, claim-provenance]
---

# Fleet Checkpoint Dispatch — the asking side

You are the coordinator: a shared disruptive event is coming (a gateway bounce, an image swap, a fleet
migration, a shared gate), and every seat must save its work and confirm before it happens.

**This is the ASKING half.** A seat answering a checkpoint uses `checkpoint-ack`. The restart mechanism,
the host topology, and the ACK gate itself live in `safe-update-restart` — **read that runbook for the
event you are about to run.** This skill covers only the dispatch loop, which is where the silent
failures live.

## When to Use

- A shared disruptive event is coming (a gateway bounce, an image swap, a fleet migration, a shared gate)
  and every seat must save its work and confirm before it happens.
- You are asked to "DM all the agents", "get everyone's ACK", or "checkpoint the fleet".
- A dispatch has gone out and you must decide whether the gate is open.

Not for: a single seat's own restart (no fleet dispatch needed), or the restart mechanism itself — read
`safe-update-restart` for that, and `checkpoint-ack` for the receiving side.

## The order is the point

1. **FILE the durable checkpoint file FIRST.** It carries both the instruction (save → log → verify →
 then ACK) and the ACK line each seat appends. It is the record; a wake is only the pointer.
2. **Re-measure the wake rail** before trusting it — a registered peer and a listening port, not an
 assumption either way. See `references/wake-path-measurement.md`.
3. **WAKE each seat**, pointing at the file and repeating the instruction in one line.
4. **COLLECT ACKs from the file and the lanes** — not from your memory of the replies. A seat may answer
 in its own lane instead of appending; the lane note is usually the richer record, so read both.
5. **Report the gate state to the human**: who is confirmed, who is UNKNOWN. **The human chooses the
 moment.**

**An ACK is only valid once the seat has finished, logged, and verified its work** — so the ask must say
so explicitly, and the ACK is the LAST step a seat performs. An ACK that arrives before the sender saved
is worse than no ACK, because it reports safety that may not exist.

## ONE EVENT, ONE FILE

**Before broadcasting, grep `01-HANDOFFS/` for the event name and today's date.** If a checkpoint for this
event already exists — filed by HQ, by a sibling, or by an earlier turn of your own — **point your DMs at
THAT file instead of filing a second one.**

**A seat that already ACKed will correctly refuse to write a second line** (*"prior ACK stands"*). Accept
that as the ACK it is and move on. Do not demand a duplicate, and do not file a parallel file: two files
for one event split the record a later reader needs whole, and manufacture exactly the duplicate-ACK noise
the one-event rule exists to prevent.

## Read the wake's RESULT, not its exit status

Three outcomes look alike at a glance, and each one, misread, produces a false "notified":

- **A 0-byte reply is UNPROVEN** — neither a delivery nor a refusal. Re-wake via the local twin and report
 it as UNPROVEN. Reporting it as "notified" is the exact failure a checkpoint exists to prevent.
- **Exit `124` is `timeout` TRUNCATING a live turn, not the peer refusing.** The seat may well have acted
 on the message; check its artefacts (a note in your lane, a touched file) before concluding anything.
- **`$?` after a pipe reports the LAST command in the pipe, not `timeout`.**
 `timeout 150 hermes peer dm … | <any truncator>` returns the LAST stage's status, so a timed-out or
 failed DM reports `exit 0`. **Redirect to files and read the code on its own line:**
 `timeout 150 hermes peer dm … > out.txt 2> err.txt; rc=$?` — then read `out.txt` for the reply and `rc`
 for the transport.

**Prove the message landed in the target's own artefacts** (a reply note in your lane, a file it touched),
not by the channel returning success. If nothing shows, the honest statement is "the wake failed".

## An unanswered seat is UNKNOWN — never "fine"

An open window is not an authorisation to restart un-ACKed seats. **Gating is not proceeding, and a dark
channel is not consent.** Collect what arrived, name the seats that did not answer, and let the human
choose the moment. Never read silence as a soft yes, and never let a checkpoint depend on an ACK that
could not have arrived.

## Verify the ROSTER before you count ACKs

The ACK roster and the seat roster are two different things, and a checkpoint fails open if you treat
them as one.

**A profile that answers is not necessarily a member.** Both wake paths (peer DM and the local twin)
reach any profile directory on the box, so a retired seat with no bot token and no peer key still
returns a fluent, well-measured ACK. Counting it as readiness inflates the gate with a seat that does
not exist. **The membership test is provisioned credentials, not responsiveness:**

```bash
grep -c '^API_SERVER_KEY=.'   profiles/<seat>/.env   # 0 = not a seat
grep -c '^TELEGRAM_BOT_TOKEN=.' profiles/<seat>/.env  # 0 = no way to be addressed
```

**A 401 from a seat you never verified is not automatically a misconfiguration.** It may be a retired
seat with no credentials, which is correct behaviour. Before filing "add the key to X", ask the human
whether X is supposed to exist — diagnosing a defect into a seat that was deliberately removed produces
an action item that should never be carried out. **State the roster you measured and ask; never infer
membership from an error code in either direction.**

## Measurement honesty during a checkpoint

You are about to report state that other people will plan around, so the ordinary claim rules apply at
full strength:

- **State the denominator when you report a zero.** "0 of N carry X" is a real finding only with the N.
 Measured: a scan that reported *"0 processes carry the key"* had seen 45 processes and could read
 **19** (`EACCES` without root) — a clean zero and an **unreadable subset** must never look alike. Report
 *"0 of the 19 I can read."*
- **A peer that re-measures your claims may REFUTE them — that is the system working.** A checkpoint that
 claims a fleet-wide rationale for a single-seat change will be caught, correctly. Accept the correction
 into the record rather than restating your original claim, and budget for it.
- **Report what the restart does NOT fix.** Blocked deliverables, known drift, jobs needing re-arming, and
 anything genuinely not rebuilt. A later reader takes a bare ACK as "all clear" and loses the rest for days.

## Pitfalls

- ❌ **Filing a second checkpoint for an event that already has one.** The duplicate-ACK noise the protocol
 exists to prevent, produced by the coordinator.
- ❌ **Waking before the record exists.** If the rail dies mid-dispatch, the pointer survived and the
 instruction did not.
- ❌ **Reading `exit 0` from a piped `peer dm` as a delivered wake.** It is the pipe's status, not the DM's.
- ❌ **Reading a 0-byte reply or a `124` as a refusal, or as a delivery.** They are UNPROVEN and
 TRUNCATED respectively — both need a different next action.
- ❌ **Collecting ACKs in your head as they arrive.** The file is the artefact; a checkpoint whose ACKs live
 only in a session log is a checkpoint nobody can audit.
- ❌ **Calling the fleet ready because most seats answered.** UNKNOWN seats are named, not averaged away.
- ❌ **Counting an ACK from a profile that is not a seat.** Verify the roster by provisioned credentials
  before the gate closes; a responsive corpse reads as a confirmed seat.
- ❌ **Filing a credential fix for a seat you never confirmed exists.** A 401 may be a retired seat
  behaving correctly — ask the human for the roster before inventing an action item.

## Verification

- [ ] One checkpoint file exists for this event (checked, not assumed).
- [ ] The file predates the first wake and names the ACK line seats should append.
- [ ] Every wake's real result is known: reply / UNPROVEN / TRUNCATED — not an exit code.
- [ ] The roster was verified by provisioned credentials — not by which profiles happened to answer.
- [ ] Every seat is either confirmed in the file or explicitly reported UNKNOWN.
- [ ] The human was told the gate state and chose the moment; no restart proceeded on silence.

## Support Files

- `references/wake-path-measurement.md` — measuring the peer DM rail (registered peer + LISTEN via
 `/proc/net/tcp`), the two observed states, the timeout-capped send, and the dark-rail fallback.
