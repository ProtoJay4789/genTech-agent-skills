---
name: waking-idle-agent-seats
description: Use when waking an idle agent seat to hand it work.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [agent-coordination, handoff, cron, fleet]
    related_skills: [agent-to-agent-messaging, handoff-mesh, group-handoff-mesh]
---

# Waking an idle agent seat

## When to Use

- One agent must hand another profile's agent a task (a fleet notification, an audit, a handoff).
- You are about to claim "I notified the fleet" and need that claim to be true.
- A prior dispatch came back truncated, silent, or with no artifact to show for it.

Activating another profile's agent (`hermes -p <profile> chat ...`) is not "sending a message." It runs a
real turn on shared hardware, and the failure modes are specific: a dark channel silently becomes "no one
was told," and a short timeout silently becomes "the work was done" when it was not.

## 1. Measure the channel before promising a DM

```bash
hermes peer list                     # is there a peer registry?
ss -ltnp | grep -E ':(864[0-9])'     # is anything actually listening?
```

**"No peers registered" plus nothing listening is a dark channel — not a refusal.** A dark channel is not
consent, and an ACK that could not have arrived must never be waited for.

When the peer path is dark, say so in the handoff itself. **The durable written record IS the delivery;
the DM is only the accelerator.** Never write up an unattempted or failed wake as "notified."

- **Distinguish DARK from UNKEYED — they read identically in a status line and have opposite fixes.** A remote
  peer can answer `GET /health` → **200** and `POST /v1/chat/completions` → **401**: route, firewall and network
  are all fine and the only missing piece is the key. **A channel that answers 401 is one credential away;
  calling it dark sends the next session rebuilding infrastructure it does not need** — a host-level VPN
  install, a firewall rule, a second network identity. Probe both: `health` proves reachability, the unkeyed
  POST proves whether the door is locked or absent.
- **Re-measure the channel before repeating an old note about it.** A vault note recording "port dark, HTTP
  000" is a measurement of a moment, not a property of the peer — re-probe it before you quote it to the user
  or build a workaround on top of it, and mark the old note superseded in place when it no longer holds. A
  stale "it does not work" is more expensive than a missing note: it is a decision already made.

`scripts/wire-peer-with-proof.sh <peer> <url> <keyfile>` does the whole sequence in the right order —
measure the endpoint, validate the key file (mode 600, never argv), register, then **refuse to print LIVE
unless a DM comes back containing the probe token**. Use it instead of hand-typing `hermes peer add`; a
peer nobody has messaged is a config entry, not a channel. Its guard branches are tested; the
register-then-DM path follows the documented CLI behaviour and has not yet run against a live peer, so
treat the first real run as a test and read the output, not the exit code.

## 2. The local twin is the wake path

```bash
hermes -p <profile> chat --query-file <file> --oneshot
```

Runs a turn as that seat on the same box. Keep the query short and directive — it consumes tokens and
does real work.

## 2b. Read the seat's own lane before inventing work

When asked what an idle seat should do next, read **its open handoffs and its most recent self-audit**
before composing a brief. A seat that has been dark normally has a backlog nobody closed, and its own audit
names capabilities nobody is using. Measured: one "what else can this seat work on" brief, written from the
seat's own audit rather than from a blank page, surfaced a working messaging channel we had never used, a
memory file 26 days stale, and a note open for three weeks — none of it new work, all of it already owed.

- **Assign what the seat already owes before adding a task** — an unanswered note from three weeks ago and a
task invented this morning read identically in a queue, and only one of them is honest to the reader.
- **State the order and one "done" shape per item**, so the seat can finish unattended and cannot spend the
  session asking you which one to start.
- **Write the item your lane cannot verify as a question, not an instruction** — "can your box serve this,
  and if not, say so plainly" — otherwise a wrong assumption becomes a delivered failure.

## 3. Budget the timeout for minutes, not seconds

A seat turn runs **3–5 minutes** and tens of tool calls. **A timeout shorter than the observed run time
cuts the seat off mid-work, and that is worse than not launching it**: the seat reads the task, ACKs, and
then loses the deliverable when the turn dies.

- Use **≥900s** for a seat doing real work, or run it as a tracked background process with completion
  notification.
- A piped exit code can still read 0 after a timeout — **inspect the transcript, not the exit code.**
- If a run is cut, check whether it got far enough to write anything before re-dispatching. A second
  dispatch re-does work; a partial artifact tells you where to resume.

## 4. Instruction: write the artifact first, refine second

A partial file on disk survives a second interruption; a complete answer still in context does not.

## 5. The ACK must land in the SHARED file — never in the recipient's own session

This is the rule most often broken, and it fails silently. **"Reply in your own seat" feels polite and
produces zero shared evidence.**

- Name the exact file. Give the exact line shape. Include an ACK section to append to:
  `- **<profile> — ACK <UTC timestamp>.** <what you measured> (session <id>)`
- **A finding that lives only in a session log is a finding nobody can audit.**
- Give recipients a slot to record a failed wake too, so "we don't know if they got it" is a recorded
  state rather than an assumption.

## 5b. A wake is not a refresh — report which one you did

**Hermes freezes `MEMORY.md`/`USER.md` into the system prompt at session start, and a DM does not change
that session.** A `hermes peer dm` or `-p <seat> chat --oneshot` turn runs on that seat's *api_server*
routing key; the chat session whose stale snapshot you were worried about is untouched. Measured: a seat
answered a DM inside a **17-day-old** session and reported the age itself, unprompted.

- **"I briefed them" and "they have the new context" are different claims.** A reply proves the wake. Only a
  **new `session_id` with a `created_at` after your write** proves the refresh. Never let the first stand in
  for the second — same false-receipt class as reporting a wake that never landed.
- **Put the split in the ACK you ask for** — `wake: delivered 14:42Z · refresh: pending, needs /new` — so the
  gap sits in the shared file instead of in your head.
- **You usually cannot inject the triggering message yourself — but `--list` is NOT the test.** `hermes send
  --list <platform>` can print `(no channels discovered yet)` while an explicit
  `hermes send -t '<platform>:<chat_id>' '<text>'` in the same profile still returns `sent`. **Attempt the send
  with the explicit `platform:chat_id` and read the result**; never tell the user "the platform is unwired"
  on the strength of an empty discovery list — that turns a working action into one you asked him to perform.
- **Read the failure text to tell the two causes apart.** `Chat not found` means *that bot is not a member of
  that chat, or that chat id does not belong to that bot* — the fix is the right bot or the membership, not a
  config rewrite. An auth/token error is the credential. Reporting either as "the channel is down" sends the
  next session hunting the wrong layer.
- **When the send genuinely is not yours to make, say it as one small action** — "send one message in that
  chat" — not as a checklist.

Ask each recipient to re-measure the claim and report their own numbers. Independent seats catch errors
the sender made — including the sender's own stale figures. **An identical echo is not confirmation; a
reproduced measurement is.** Report deltas rather than reconciling them away.

## 7. Prefer a gate over a promise

When the handoff is "X will be true at <time>", have the recipient wire a check that **fails by default**
and passes only on an observed condition. Test all branches live: not-yet-true → fail, true → pass,
source unreachable → explicit UNMEASURED. **A job that can pass because the clock moved is not a guard.**

## 8. Report the outcome honestly

State how many seats were woken, how many ACKed, how many were interrupted, and what artifact exists.
"Five woken, three truncated by my timeout, one deliverable written" is a useful status; "the fleet has
been notified" is not.
