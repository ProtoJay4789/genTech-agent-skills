---
name: agent-seat-dispatch
description: "Use when dispatching work to another agent seat."
version: 1.0.0
author: Gentech
license: MIT
category: agent-coordination
tags: [agents, dispatch, handoff, delegation, coordination, fleet]
metadata:
  hermes:
    tags: [agents, dispatch, handoff, delegation, coordination, fleet]
    related_skills:
      - agent-to-agent-messaging
      - group-handoff-mesh
      - handoff-mesh
      - fleet-consult
---

# Dispatching a task to another agent seat

**Messaging reaches a seat; dispatching makes it produce something you can audit.** The difference is
entirely in what you put in the task text and what you demand back. A dispatch that *feels* successful —
the child ran, exited 0, and did real work — can leave **zero evidence** behind. That is the failure this
skill exists to prevent.

## When to use

- A task belongs to another seat and you are not going to do it yourself.
- You are fanning one notice or audit out to several seats at once.
- You found one seat's work missing and are re-dispatching after a cut-off.

For sending a short message or a checkpoint, use `agent-to-agent-messaging` instead. This skill is about
*handing over work*.

## Step 0 — Pick and MEASURE the channel before relying on it

Never assume the peer channel is up. Measure it, and treat "nothing listening" as **not the peer
refusing** — it is your wake path being absent:

```bash
ss -ltnp | grep -E ':(864[0-9])'    # any listener at all?
hermes peer list                     # what is actually registered?
```

**Nothing is listening → do not read it as consent, do not wait, do not report it as a wake.** Fall
through to the local twin below and **say in the record that the peer path failed**.

**When it IS registered, the wake form is `hermes peer dm fleet/<seat> "…"` — the seat is a SUFFIX of the
single registered peer, not a separate peer name.** `hermes peer dm <seat>` resolves nothing and looks like
a silent seat. `hermes peer dm fleet` with no suffix messages the router. Print `hermes peer list` before
composing, so you send to a name that exists rather than one that reads well.

**A DM's reply is the seat's own summary of what it did, not evidence that it did it.** The reply text comes
from the seat's turn and can be confidently wrong in the flattering direction. Treat it like any self-report:
accept the wake, then verify in the artefact (see Step 4).

## Step 1 — Write the durable record FIRST

The vault handoff is the delivery; the wake is only the accelerator. File it before dispatching, so an
interrupted or failed dispatch still leaves the task on disk where the seat's own watcher can find it.

## Step 2 — The task text carries a contract. Three clauses are not optional.

### 2a. Name the identity pair, because the child inherits YOURS

A dispatched turn **inherits the parent's `HERMES_SESSION_*` environment.** The child therefore sees
`HERMES_SESSION_PROFILE=<the sender>` and the sender's chat name while `HERMES_HOME` correctly names its
own profile. **A seat that reads its identity off the session variable records its work as the sender** —
silently, under the wrong name, into the wrong lane.

The trustworthy identity pair, in order:

1. **`HERMES_HOME` + `HERMES_SCRATCH_DIR`**
2. the `state.db` it is actually writing
3. `ps -eo args | grep 'hermes -p'`

Put this in the task text. It cannot be inferred from inside the child, and it is the **default, not an
anomaly** — every dispatched seat hits it.

### 2b. Name the FILE and the LINE SHAPE for the result

`"ACK in your own session"` reads as reasonable and produces **nothing auditable**. A dispatch can run
dozens of tool calls, do real work, and update its own memory while the handoff file stays
**byte-identical**. Findings that live only in a session log are findings nobody can audit.

Give an explicit template:

```
- **<seat> — ACK <UTC ts>.** <what you measured> — <what changed> (session <id>)
```

And state that **"nothing changed" is itself a required finding** — it is the line that stops the next
seat re-deriving work that was already done. Where several seats are dispatched, give them all the *same*
file and an ACK section, so the file's growth is your progress bar.

### 2c. State the write ORDER and the constraints

- **Write the deliverable to disk FIRST, then refine it.** A seat that drafts the file before polishing
  loses nothing when it is cut off; a seat that reasons first and writes at the end loses everything.
- State the constraints explicitly and call them hard (what must not be installed, enabled, scheduled, or
  edited) — a seat will otherwise reasonably assume that "restore" means "create".
- **Tell it the count to expect and to report the count it actually read**, so a number that disagrees
  with the source is loud rather than silent.
- Hand it the **prior art path** if any exists, or it will re-derive a solved problem.

## Step 3 — Dispatch, and size the run to the work

**Two routes, and the peer DM is the faster one when it is registered.**

```bash
hermes peer dm fleet/<seat> "<task text or a pointer to the handoff file>" >/dev/null
```

- **A DM does real work, not just an ACK.** Measured on a three-seat consult: each seat ran its own turn and
  appended to the shared artefact, the file growing 2.6 KB → 6.0 KB → 9.8 KB in seat order, total wall clock
  ~110 s for all three. That is far faster than three serial local twins.
- **Send them concurrently, not in a loop you wait on.** The three DM calls are independent; batching them in
  one turn is what makes the elapsed time the slowest seat rather than the sum.
- **Keep the task text short and point at the file.** The handoff carries the contract; the DM only has to say
  "this exists, answer in it". A long DM is a second copy of the brief that will drift from the first.
- **A DM that returns nothing has not necessarily failed** — check the artefact before concluding the seat was
  idle. Silence is a statement about the channel (see `claim-provenance`), and the file's byte count is the
  instrument that can give the other answer.

The local twin runs a real turn as that seat — use it when the peer path is absent, or when you need to watch
the turn happen:

```bash
hermes -p <profile> chat --query-file <task.txt> --oneshot
```

Use `--query-file` (not `-q`) so quotes and `$(…)` survive the shell.

- **Size the timeout to the OBSERVED run, not to your patience.** A seat doing real work runs **3–6
  minutes**. A five-minute cap truncates it **mid-write**, losing the whole turn — and worse than not
  dispatching, because the seat may already have committed to the work and half-written an artifact.
  Give 10–15 minutes.
- **Run a multi-seat batch as a BACKGROUND job**, not a foreground serial loop. A foreground loop of five
  seats runs 20+ minutes and will hit the foreground cap.
- Anti-pattern that produced this rule: with a foreground loop you cannot tell a slow seat from a hung
  one, and `timeout N` **kills the child rather than reporting on it.**

## Step 4 — PROVE it landed, from the target's side

Read the result, not the exit code, and not the tool's own status line.

- **Check the artefact you asked for, by size and by content.** A handoff file whose byte count did not
  move is proof that nothing was recorded, however clean the run looked.
- A run can exit 0 and be **interrupted** — a truncated turn writes what it managed and dies. Treat "exit
  0" as "the process ended", never as "the work completed".
- **A pipe swallows exit codes.** `cmd | <truncating filter> && echo OK` prints OK on failure, because `&&`
  tests the filter, not `cmd`. Capture with `out=$(cmd); rc=$?`, or `set -o pipefail`, whenever the exit code
  is the thing you actually care about.
- If nothing shows, the honest statement is **"the dispatch did not land"** — never "they have been
  notified".

## Step 5 — Resuming a seat you cut off

When your own timeout truncated a seat mid-work:

- **Say the cut-off was yours, not theirs**, or it will re-derive from scratch and may distrust its own
  partial work.
- **Quote back what it already established** (the counts it confirmed, the paths it read) so it resumes
  rather than restarts.
- **Re-state the write-first instruction**, because the reason it produced nothing is that it did not
  follow it last time.

## Step 6 — When the dispatch is a CONSULT (judgement, not work)

A consult asks several seats what they think of a proposal. It needs a **different contract** from a work
dispatch, because the failure mode is not an empty artefact — it is **three polite endorsements**.

- **Demand a VERDICT in a fixed vocabulary**, plus one change they would make:
  `verdict: <right shape / wrong shape / wrong question> — <the one thing you would change>`.
  Without that field you get answers to your questions and agreement with your premise, which is worth nothing:
  a proposal endorsed by everyone was never tested. Measured on a real consult, three seats given a verdict
  field **independently contradicted the parent's central design** for three different, measured reasons.
- **Ban the actions that would answer a different question.** "Do not install anything, do not change your
  config, do not edit crons, do not draft the design doc." A seat told only to "help" will install the very
  product the fleet is deciding against, and its answer will then describe a system you are not adopting. Name
  the ban *and* the reason, or it reads as caution rather than scope.
- **Give your own measurements as settled facts, marked "do not re-derive".** Otherwise N seats repeat the same
  expensive measurement N times and return the same number, which teaches you nothing.
- **Ask each seat for the one measurement only IT can make** — its own config value, its own file counts, its
  own lane's failure modes. A fleet-wide defect is confirmed by N independent reads of N independent files;
  the parent cannot see any of them from its own seat.
- **Ask them to classify their own material with counts that must add up.** "Mark each entry identity /
  convention / queue / archive and give the counts" is arithmetic the seat can self-check, and it exposes a
  design that does not fit reality better than any opinion.
- **Synthesis is the parent's job, and say so.** Three seats drafting the design produces three incompatible
  plans; three seats answering the same four questions produces one decidable answer.
- **Say which of your own claims you expect to be wrong.** It licenses the correction instead of inviting
  agreement.

## Pitfalls

- **A dispatched turn is not a session you can read later.** Design for the result landing on disk in the
  *first* pass; do not plan to mine session logs afterwards.
- **An instruction that sounds cooperative can be unauditable.** "Reply in your own lane", "acknowledge
  in your session", "report back when done" all leave no shared evidence. Name the file.
- **Do not let a seat's own report stand as the verification of its own run.** For anything with an
  external effect, read the target back yourself.
- **A long foreground dispatch loop is untestable.** Batch it in the background and poll.
- **Two seats dispatched with the same task text will produce two independent readings.** That is a
  feature — it is how you learn that one instruction was ambiguous. Read both before correcting.

## Verification

- [ ] The channel was measured, not assumed, and its failure (if any) is recorded verbatim.
- [ ] The durable handoff existed before the wake was attempted.
- [ ] The task text names the identity pair, the target file, the line shape, and the write order.
- [ ] The timeout matches an observed run, and a multi-seat batch ran in the background.
- [ ] The result was verified in the **target's** artefact, not from the dispatch's own output.
- [ ] Any cut-off is recorded as the sender's, with what the seat had already established quoted back.
