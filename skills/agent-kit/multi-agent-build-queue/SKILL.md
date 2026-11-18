---
name: multi-agent-build-queue
description: "Shared build queue for a multi-agent fleet — per-department views, a canonical count every agent can quote, and the failure modes that make a queue look like the game of telephone. Use when several agents share one work list."
version: 1.0.0
author: Gentech
tags: [agent-kit, multi-agent, build-queue, coordination, fleet]
trigger: "When multiple agents share one build queue, when a queue's item count keeps changing without explanation, or when each team needs to see only its own work."
---

# Multi-Agent Build Queue

One shared work list, many agents. The hard part is not storing the items — it is that **every
agent must be able to ask the same four questions and get the same answers.**

```
status      What are the canonical numbers?       (quote these, never an eyeball)
pending     What is open — mine, or the fleet's?
next        What is MY stopping point right now?
jordan      What is blocked on a human, and what releases it?
```

Build it as a **query tool**, not a file everyone reads directly. A file cannot answer "is it
accurate?" — it just holds whatever was last written. Accuracy is a property that must be checked.

---

## Failure 1 — The game of telephone (and why it is not what it looks like)

**The complaint:** *"the list balloons to 50–60–70, and sometimes it's 20 or 26."*

The tempting diagnosis is that items are being added and removed wildly. **Measure it before
believing that.** `git log` on the queue file gives the real series:

```
09-26  42      09-29  45      09-30  46 → 47 → 48 → 52 → 53 → 54 → 61
```

**The file never shrinks.** It grew monotonically and added 15 items in one day. Nothing is
removed — closed items stay forever as history.

So where do "20" and "26" come from? **The same file, counted four different ways.**

```
total items       61     ← "50 to 60 to 70"
open              41
  ├─ human-gated  22     NOT actionable by any agent
  └─ actionable   19     ← "20 or 26"
```

**Both numbers were correct.** They were answering different questions with no label attached.
That is the telephone: *N readers, N definitions, one name.*

**Fix:** publish one labelled set of numbers, and make quoting them the convention. An unlabelled
number is the defect, not the disagreement.

> **The generalisable rule:** when two agents report different values for "the same" metric,
> suspect two definitions before you suspect two facts.

---

## Failure 2 — A team-scoped view that silently misses its own items

Each department should run its own list — so work stops routing through one central team and back:

```bash
build_queue_query.py next --group engineering
build_queue_query.py pending --group finance
```

**This is only trustworthy if the group field has one spelling per group.** Measured on a real
queue:

```
treasury          9   ← same group
gentech-treasury  7   ← split across TWO names
(null)            7   ← invisible to every view
```

A finance-scoped run would have **silently missed 7 of its own items** and reported a clean list.
That is worse than no filter, because it looks authoritative.

**Fix — two parts, both required:**

1. **Normalise on read.** Map every known spelling onto one canonical name. A null group must fall
   back to the item's **owner**, so it stays visible somewhere instead of hiding from every view.
2. **Then standardise the data** as items are touched. The normaliser is compensation, not a fix —
   two spellings for one group is drift.

A null group is not "no group." It is a label somebody forgot.

---

## Failure 2b — Two files wearing one name

**A canonical store plus a hand-maintained human-readable mirror is two queues, not one.**

Measured on a real fleet: the canonical JSON held **102 items**, the markdown mirror held **14 rows**,
**11 of those 14 rows existed nowhere in the canonical file**, and **88 canonical items appeared in no
mirror**. The orienting doc described both as live — so the instruction *"work the build queue"* resolved to
a different list depending on which file the agent happened to open. Neither list was wrong; together they
were unusable.

**The root cause is design, not discipline.** Two writers on two files always diverge, and every addition
lands in exactly one, so the next person re-adds what the other file already holds. This is what an owner
experiences as *"the list keeps ballooning"* and *"we keep chasing a duplicate"* — the duplicate is the
steady-state output of the file pair, not an occasional mistake.

Rules:

- **Pick one direction and generate the other.** The mirror is rendered output, regenerated on every write.
  Two-way sync is how you arrive back here.
- **The mirror must carry the canonical id** on every row, so it can be matched to its record without
  name-fuzzy inference.
- **A mirror row describing already-finished work is worse than none.** It reads as live and invites an agent
  to redo it; measured, one mirror row still requested an enrichment that had shipped days earlier.
- **Never merge the orphans by name.** Rows that exist in one file only are frequently renames of records in
  the other; a name-match merge deletes real work. Surface them for a human read instead.

---

## Failure 3 — The queue with no completion timestamp

If items carry no `completed_at`, then **"what shipped recently?" is unanswerable** — and the
handler that wants to report completions has nothing to read.

Set the timestamp when the status flips. Provide a command that does it, so the safe path is also
the easy one:

```bash
build_queue_query.py ship "<substring of the item name>"
```

---

## Working an item — the process once you take one

Work comes from the **group view** (`next --group <group>`), not routed through one central team and
back. Once an item is taken it runs five steps, and these rules are the part that is actually worth
paying for.

**1 · AUDIT before you trust the change.** A second model reads the **real source** — not the diff,
not the summary — and the audit is **written to a file**. Put that artifact path in the item's record;
an audit nobody can open is an opinion, and round 2 needs something to check against.

**2 · Name the auditor's provider in the artifact.** If the auditor runs on the **same provider as
the worker**, the artifact says so in its own header — *model-level check only; if this provider
degrades, worker and auditor degrade together*. Silence about it is read as independence, and a
same-provider pass is **not** a cross-provider verification. Round 2 either runs on a different
provider or says out loud that it did not.

**3 · FIX with surgical `patch` — one edit per patch.** Never a replace-script on a file that is
running: a rewrite that repairs a docstring is a rewrite wearing a fix's clothes. **Syntax-check
after every edit** — the check is what catches the corruption, not the intent behind it.

**4 · VERIFY with four independent checks:** syntax, the item's own tests, the whole suite, and
*"is the deployed copy the file I edited?"* proven by **digest (md5)** — never by report.

**5 · RE-AUDIT round 2 on the FIXES, not on the original change.** A single audit pass is not an
audit; the next bug hides in the fix. Round 2 is **its own artifact**, persisted like round 1.

**6 · CLOSE only through `ship`,** and only after round 2. No hand-edits, no id-keyed writes.

### The two gates — both generalise far past the money path

- **A non-final signal must not close an item.** A result that can still change is not a verdict.
  A timeout that fired *after* the work was broadcast closed the intent, so the gap check read
  *zero outstanding* while a transaction was still settling. The shape to hunt is the same
  anywhere: **a check that passes on a signal that can still move.**
- **A receipt is CLAIMED, not confirmed.** Label it `verified: false` until something independent
  confirms it. *"Claimed"* and *"confirmed"* have to be different words, or the first gets read as
  the second.
- **Instrumentation on a control path is a control-flow change until proven otherwise.** The
  audit's *confirmations* — exit codes unchanged, no `$?` change, the watchdog does not act
  differently — are worth more than its findings.

### A flag is not evidence — the gate is carried by `ship`, in artifact form

**Never record `re-audited: true`.** A boolean can be true while nothing ran, which is the same
dishonest receipt as a claim labelled *verified*. Carry **paths**, and have the tool check the only
thing it can honestly check — that the artifact is there:

| field | names | what `ship` checks |
|---|---|---|
| `audit_path` | the round-1 audit artifact | the file exists |
| `reaudit_path` | the round-2 artifact | the file exists |

`ship` **refuses to close** an item that declares `audit_path` with no `reaudit_path`, and refuses a
bare flag outright. It prints each artifact's path, size and mtime, so the receipt says **what was
checked** — never "verified". The tool verifies **presence, not quality**; the artifact carries its
own honesty labels. And `ship` exits **0 only when it actually wrote**: an exit-0 refusal is
indistinguishable from a completed ship to any scripted caller, which is the non-final-signal defect
wearing a different hat.

---

## Who owns it — ask before you start, and record the answer

**A row is a stale claim. The owner is the live fact.** A queue records what someone believed when they wrote the
row; the seat that owns the lane knows what is true now. Working another seat's row without asking is how you
"fix" code that was deliberately held, or edit a file the owner replaced two hours ago.

**The rule: before starting a row owned by another seat, ask them and record the answer on the row.**

```
--record <id> --who <seat> --said "still reproduces; I am taking it"   # timestamped on the row
--start  <id>                                                          # refuses without it
--audit                                                                # every open row never checked
```

Three refusals, each of which is a real defect when missing:

- **No check-in in the last 24h → refuse.** An answer from last week describes a different build; the owner's
  context moved even when the row did not.
- **Check-in from anyone but the row's owner → refuse.** *Someone else's opinion is not the owner's answer.* An
  HQ-written "I looked at it" is exactly the fake receipt the queue already suffers from.
- **An empty `--said` → refuse.** *A check-in with nothing said is not a check-in.*

**The answer is worth more than the row.** Asking a seat about its seven open defects returned, in one reply:
four **no longer reproduced**, one **was never a defect** (zero hits for the mechanism in the whole tree), one
**unmeasurable** (no data to measure), and one **still reproduces**. The queue had been carrying six fictions —
and the owner killed them faster than any re-audit could, because it remembered why each row was written.

**Ask for those four verdicts explicitly:** *does it still reproduce today · what is actually left · do you keep
it or does HQ · and what is the measurement.* A bare "still open" is the same shrug as a bare `blocked`.

**When the owner says it no longer reproduces, close the row with THEIR measurement as the evidence** — and when
they say the defect was never built, reclassify it as a build, not a fix. `not-a-defect` and `unmeasurable` are
both legitimate verdicts, and leaving them as `needs-evidence` forever is how a queue holds work that does not
exist.

### Testing the guard must not write to the real queue

A test that exercises the check-in recorder leaves a **fabricated check-in on a live row** — a fake receipt in
the file the guard exists to protect. Point the test at a copy (`BUILD_QUEUE=/tmp/q.json`), and if you do run it
against the live file, **remove exactly the rows you touched and say so**. Verify the removal by counting the
field across the whole file, not by trusting the pop.

---

## Two traps that will bite you when writing to the queue

These are not hypothetical — both happened in a single edit.

### 1. Match items by NAME, never by ID

If anything in your system renumbers the queue (and a "renumber sequentially" maintenance rule is
common), **IDs are unstable by design**. An id-based write will land on a *different item*:

```python
# WRONG — an id-based status write hit an unrelated item after a renumber
for it in items:
    if it.get("id") == 54:
        it["status"] = "shipped"

# RIGHT — name is the stable key; assert exactly one match before writing
hits = [i for i in items if needle.lower() in (i.get("name") or "").lower()]
assert len(hits) == 1, f"expected 1 match, got {len(hits)} — refusing to write blind"
```

**Print what you wrote and read it.** The only reason the wrong-item write was caught was that the
name echoed back was not the one expected.

### 2. Preserve the file's encoding

If the JSON stores non-ASCII as `\uXXXX` escapes, `ensure_ascii=False` rewrites every escape into
a literal character — a **150-line diff of pure encoding noise** on a one-field edit, which buries
the real change so nobody can review it.

```python
json.dumps(items, indent=2, ensure_ascii=True) + "\n"   # round-trips byte-identical
```

**Check:** a one-field edit must show **~2 changed lines**. A huge diff means you re-encoded —
revert and redo.

---

## Design rules

- **Human-gated is its own class.** An item waiting on a person is **not** work any agent can do.
  Exclude it from `next` and give it its own view with a stated **release condition**. A queue that
  mixes them reports a backlog nobody can action.
- **Blocked must name its gate.** "Blocked" alone is not a status, it is a shrug — the next reader
  cannot tell what would move it. Flag gated items that carry no gate as a defect.
- **Distinguish "empty" from "excluded."** A filter that matches nothing should say *why*, not
  return a calm blank.
- **Verify a negation-aware check.** A check that greps for a name will match the name inside its
  own negation — *"no human gate"* reads as *"human-gated"*. Real false positives, three in one
  run. Match structured fields first; if you must scan prose, strip negated mentions.
- **`owner` records the machine; `department` records the work — do not route on the wrong one.** A field
  whose vocabulary is a host name answers *"which box runs this"*, and department routing built on it
  silently mis-buckets: measured, **41 of 77 open items** collapsed into a catch-all because they were owned
  by a host rather than a domain. Adding a `department` field is only half the fix — **the backfill reveals
  that most items have no domain assigned at all**, and re-sorting them is the actual work.
- **The vocabulary validator must REJECT, not warn.** An unenforced field drifted to **nine spellings** across
  a 102-item queue, two of which named the same department. A warning is read once and ignored; a refused
  write is read immediately.
- **The first tool you point at a live queue is read-only and has no write flag.** Print the distribution and
  nothing else, then prove it touched nothing by comparing the file hash before and after. Trust in a tool
  that *cannot* write is worth more than a review of a tool that can.
- **Status enums drift validation-side.** If two items already carry a value the schema does not list
  (`blocked` while the enum offered only pending/in_progress), the schema is missing a value the data depends
  on — and the canonical file lies by omission while the readable mirror is correct. Fix the enum, do not
  re-label the items.
- **A status is not a boolean, and a boolean is not a status.** A row that is *waiting on a human* is a
  `status: pending` **plus** `needs_jordan: true` — writing `status: "needs_jordan"` invents a value outside the
  vocabulary and breaks anything that switches on it. Check which field carries the meaning before you set it.
- **One status doing several jobs is the real backlog defect — not a wrong count.** Measured on a 111-row
  queue: **12 rows sat in `in_progress`** and their own notes said four different things — *actually running*,
  *waiting on a human*, *deliberately held with a release condition*, and *shipped but never marked*. Nine of
  the twelve announced their own completion in prose while the status stayed `in_progress`. A second bucket
  (`needs-evidence`, 47 rows) was worse: only **10** were genuinely *work that exists and cannot be proven*; 28
  described **an action not yet taken** — *"remove it"*, *"add a check"*, *"reconcile"*. An overloaded bucket is
  indistinguishable from a backlog that is half-done, so every "what's next" answer built on it is wrong.
  **Re-bucket by reading each row's own text, and reserve each status for exactly one meaning.** Do not bulk-move
  on a keyword heuristic; read the tail of each note, where the next step is usually stated.
- **A row can be `blocked` with the gate MEASURED, not just named.** *"Blocked on capital"* is a shrug; *"blocked:
  wallet holds 0.200010 USDC, idle capital 0.4% against a >25% or ≥$10 trigger, both watchdogs `enabled=False`,
  released when idle capital crosses the trigger"* is a status a reader can act on months later.

## The one-line summary

> A shared queue is not a file every agent reads. It is a **service every agent asks**, which
> answers with **one labelled vocabulary**, and which refuses to write when it is not sure.
