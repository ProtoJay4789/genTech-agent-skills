---
name: handoff-watcher-maintenance
description: "Use when a watcher cron repeats alerts or nags."
version: "1.0.0"
---

> # ⛔ RETIRED 2026-09-30 — DO NOT RE-CREATE
>
> All four Handoff Watcher jobs are **disabled** (gentech `058ecaad8ca3`, gentech-treasury
> `066eb8c8024`, gizmo `577dce1eecdb`, pixel `dad3fbe6663a`). Jordan: *"yes good idea. it's in
> every group."* Full reasoning: `00-HQ/RETIRED-handoff-watcher-2026-09-30.md`.
>
> **Three structural defects, none fixable by tuning:**
>
> 1. **Its wake path could never succeed from cron.** Every firing read `📣 WOKE THE SEAT (0 sent)`
>    then `dm … timed out after 60 seconds`. `hermes peer dm` works fine from a shell and **times
>    out from cron context** — so the same handoffs were re-reported for days (39h, 55h, 31h).
>    **The cycling was the noise.** A watcher whose action cannot succeed is a nag with a receipt.
> 2. **It watched files that are not handoffs** — daily-generated `*-forge-tasks.md` flagged at 0h.
> 3. **Its truth check was a category error** — it diffed a point-in-time handoff against the LIVE
>    build queue and called time passing "a stale claim". It flagged a queue item that had shipped
>    20 minutes earlier. It fires on every completion, forever.
>
> **Replaced by nothing scheduled, deliberately.** The vault is the record, the mesh surfaces
> unopened notes, peer DMs work when an agent chooses to send one, and work state is answered by
> `10-Labs/build_queue_query.py` (pull, not push).
>
> **Before rebuilding:** ask what a nudge adds that the record does not already have. If you build
> one anyway, it MUST verify its own delivery and report failure AS failure — never a header
> claiming success above a body reporting zero sent.



Stateful no-agent cron scripts that report exceptions. One script per seat, same logic,
per-seat config.

## Rule 1 — One script, many seats. Never fork per seat.
A watcher copied per seat and edited per seat WILL diverge. Found 2026-09-17: four copies,
two designs (992-line vs 274-line), four md5s. HQ ran the one without noise control and
nagged the human for weeks; the workers had noise control but no detection.
**When you fix one seat's copy, propagate it to every seat in the same change.**

## Rule 2 — Eligibility and DISPLAY are separate. A cap gates display ONLY.
The bug that produced the actual complaint:
```python
shown = stuck[:MAX_PER_RUN]
alerted += [r for ... in shown]     # WRONG - only the shown ones get stamped
```
Run 1 shows 5 and stamps 5; run 2 shows the *next* 5. The cap **defers** the backlog
instead of suppressing it — visually identical to no dedup at all.
```python
eligible = []                        # stamp EVERYTHING past threshold + out of cooldown
for item in candidates:
    if cooled(item): continue
    eligible.append(item)
    ...                              # collect for display separately
shown = items[:MAX_PER_RUN]          # cap display only
```

## Rule 3 — Cooldown beats set-difference dedup.
`cur - prev` re-alerts whenever an item leaves the set and comes back (e.g. a reply note
gets archived, so the item re-enters the "no reply" set). Store `{rel: last_alerted_iso}`
and suppress while `now - last < RENAG_HOURS`. A new item alerts immediately; an old one
reminds daily, never every 15 minutes.

## Rule 4 — Lane scope every seat.
Without scope, N agents scan one vault and mail N copies of one fact. Each seat reports
only lanes it can act on; the coordination seat sees all.

## Rule 5 — Separate human lanes from agent transit.
A handoff moving between two agents is the system working, not news. Only two things earn
a human's attention: a NEW handoff addressed to a human, and something STUCK.

## Rule 6 — Age from the filename date, never mtime.
Git sync/commit/checkout re-touches every mtime. A `YYYY-MM-DD` filename prefix is the only
reliable "how long has this been open" signal. Midday-anchor it so same-day ≈ 12h.

## Rule 7 — Respect desktop seats' sleep.
A laptop that powers down overnight is not late. Measure age in *awake* hours inside
explicit availability windows, or you train the human to ignore the alert.

## Rule 8 — Cron has no script-args field.
You cannot pass `--own-lanes` from the job. Derive the seat from the script's own path:
```python
parts = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
seat = parts[parts.index("profiles") + 1] if "profiles" in parts else "gentech"
```

## Rule 9 — Identical scripts are NOT identical seats. Audit the JOB CONFIG too.
Found 2026-09-18, after a fleet audit prompted by "gizmo's watcher doesn't look updated".
All four copies were byte-identical (same md5) — the propagation rule had been obeyed — yet
the seats behaved differently, because the drift had moved into the cron job config:
- **Cadence** — HQ ran `*/20`, every worker ran `*/15`. The seat that reports the most was the slowest.
- **Window** — one seat's hour range ended an hour early (`0-2` vs `0-3`).
- **A `display` string that contradicted its own `expr`** (`*/10` displayed, `*/20` actual) while the
  job NAME said a third number. Three values, one job.
- **A retired model** left on a `no_agent` job — harmless until the flag is flipped.
- **Names that lie** — `handoff-watcher-hourly` running every 15 minutes. This is what makes a human
  conclude a watcher "wasn't updated".
After any script fix, diff the JOB CONFIG across seats: expr, schedule.display, name, deliver,
model/provider, no_agent, enabled. Unify it in the same change, then read every job back.
`hermes cron doctor` reports NO issues on all of the above — it checks health, not sameness.

## Rule 10 — Separate "quiet because clear" from "quiet because blind".
A silent seat is not evidence of a working seat. To prove it, probe the script with a throwaway state
so the real cooldown state is untouched, then cross-check what it reported against what is actually in
the lanes:
```
python3 <seat>/scripts/handoff-watcher.py --state /tmp/probe-<seat>.json
ls /opt/data/.obsidian-vault/01-HANDOFFS/INBOX/<seat>/
```
A seat reporting zero FOR YOU while its INBOX holds items is broken; a seat reporting zero with an empty
INBOX is working. The `--state` trick also proves an alert fired without spending a cooldown stamp.

## Rule 11 — A count that never moves is a FILING problem, not a threshold problem

**Before tuning a quota or re-baselining a date, find out what the monitored set actually is.**

Measured on a coverage check that had reported a flat number for days: of ~538 tracked notes, **372
declared themselves resolved**, 107 declared blocked *and* resolved, 46 were unmarked, and only ~9 were
genuinely open. The check was counting **closed history nobody had filed**.

**The root cause is the same defect class as Rule 10, one layer up:** agents answered each other in the
**body** of a note — `✅ What was done … answered / closed` — and never moved the file. A note whose
header says `**Status:** open` over a body that says "resolved" reads as open work to every counter
thereafter.

**So: a record's LOCATION is its state. A status header is a claim about its state.**

Rules that follow:

- **Triage before you chase.** Split the monitored set into `declares resolved`, `declares open with no
  completion`, `declares open and shows completion`, `unmarked` — and report those four counts. Often
  the fourth and third buckets are the whole "backlog".
- **File resolved items to the archive instead of signing them.** Moving the file *is* the resolution
  signal; it is also reversible, whereas a backfilled signature is permanent and false.
- **Never backfill acknowledgements onto closed history to make a number fall.** Historical agreement
  produces exactly the evidence-free signatures the check exists to catch. Either file them, or
  formally re-baseline to an adoption date so the metric counts from there.
- **Report the delta and the adoption rate, not the stock.** A stock number that cannot move trains the
  reader to skip it — the crying-wolf failure this whole family of monitors keeps re-learning.
- **Keep an explicit retain list when filing in bulk.** A bulk pass by predicate will eventually move
  something irreplaceable that satisfies the predicate — the ledger recording the very work being
  filed contains words like `resolved` and `archived`. Exclude known-irreplaceable paths **by name**,
  print the move list before moving, and re-assert the retain list afterwards (count, size, last line).

## Rule 12 — Closure and lane-set are each defined ONCE, in every instrument

**Two read-side defects that keep a closed note alive in a report, measured 2026-11-13 on the sign-off check:**

- **A note is closed by `## Agreement` *or* `## Supersede`.** The SLA checker honoured both; the sign-off
  checker's block regex matched only `## Agreement`, so every superseded note re-reported as "nobody was asked
  to agree" forever (3 of 12 rows were already closed). **When you add a closing form to a convention, grep
  every reader of that convention in the same change** — a closure that one instrument honours and another
  ignores is not a convention, it is a coin flip.
- **Enumerate lanes from one list, not from the directory that happens to exist.** The ACK checker walked
  `INBOX/<target>/` only, so a broadcast note in `01-HANDOFFS/<sender>-to-fleet/` was invisible to it and its
  agreements were never chased. **A lane the checker cannot see reports as agreement that never arrived.**

Rule: **one definition of "closed", one definition of "a lane", referenced by every script.** Then assert it:
plant a superseded note and a broadcast-lane note in a scratch vault and prove both instruments agree.

**⚠️ And enumerate the closing forms from the CORPUS, never from the convention document.** A convention
names the forms it expects; seats invent forms that satisfy the rule and look nothing like it. Measured: a
seat closed two of the loudest escalations with a real, measured answer under
`## STATUS: ANSWERED — closure record (machine-readable)` — a heading no reader recognised — so the ledger
still called both notes `ESCALATE` at 5d and 8d while the answers sat in the same file. **Before trusting a
closure count, grep the lanes for every heading that reads like a verdict** (`ANSWERED`, `CLOSED`, `RESOLVED`,
`State: CLOSED`, any `Agreement`/`Supersede`/`Receipt`) and fold each into the one matcher. **An
acknowledgement the scanner refuses to count is indistinguishable from no acknowledgement — and it teaches
the answering seat that replying does not register.**

## Rule 13 — Suppression is a HEADLINE change, never a state change

When the human says *"stop reporting what's already been handled — only the new stuff or what needs escalating"*,
they are asking you to shorten the DISPLAY. **A suppressed item is not a resolved item**, and the ways this breaks
are all one class:

- **A guard that tests the DISPLAY list announces "all clear".** An early exit like
  `if not (uncovered or pending): return 0  # everyone agrees` prints **nothing** once suppression has emptied the
  list, while the items still exist and are still owed. Keep a separate `quiet` collection and test
  `reported or quiet`; reserve silence for a genuinely empty total.
- **Every header count must be the TOTAL.** After suppression the headline read `0 with no agreement block`
  while nine notes still lacked one — a clean bill of health manufactured by the filter. Print both numbers:
  `N (change) + M already-reported`.
- **Deltas must compare like with like.** Diffing this run's *unsuppressed* rows against last run's *total*
  produced `−9 since last run`, i.e. a fix that never happened. Store the total in the state file and diff total
  against total.
- **Suppress on a run COUNT, not a judgement.** Increment `runs` per key in the state file, list while
  `runs < 3`, and **keep suppressed keys in state** so a change re-surfaces them immediately. Dropping the key
  from state makes re-surfacing impossible and the item silently permanent.
- **Say the suppressed number out loud on every run.** A list that quietly shrinks reads as progress;
  `+ 9 already-reported` is what separates a shorter report from a cleaner world.
- **A delta must NAME the new rows, not just count them.** `+3 since last run` followed by a sampled list
  (one row per lane, oldest-first) never prints two of the three arrivals: the reader learns that something
  arrived and cannot act on it. Keep the previous key set in state, diff against it, and print **every** row
  that is new by name and age — then exclude those from the sample so nothing is listed twice. A count is a
  nag; a name is a task.

**Proof is three consecutive runs from a clean state:** run 1 lists the rows, run 2 lists the rows, run 3 lists the
COUNT and not the rows — **and the header total is identical across all three.** If the total moved, the
suppression is deleting state, not shortening a message.

## Rule 14 — A seat with no delivery channel cannot owe a reply: BLOCKED is not LATE

**An SLA clock measures the recipient's diligence. It must not be started for a seat that was never able to
receive the note.** Some seats have no peer and no inbox poller — the file arriving on their synced vault **is**
the delivery. When that transport fails, every note owed to them is *undeliverable*, and a report calling them
`SILENT` and `ESCALATE` accuses the wrong party twice: once by blaming the seat, and once by burying the one
actionable fact (the transport is down) under rows that can never move.

Measured: 6 SLA rows, 3 of them owed to such a seat, reported as `ESCALATE`/`SILENT` for days — while the
vault transport had been refusing uploads the whole time and the seat's own last written note predated the
outage. **Nothing about those three rows was ever actionable by that seat.**

- **Make the band MEASURED, never asserted.** Probe the transport on every run and classify a row `BLOCKED`
  only while it is *currently* failing, inside a recency window. **When it recovers, the rows walk back into
  their real bands by themselves** — no switch for a human to remember, and no permanent excuse for a seat
  that has long since come back.
- **⚠️ Probe the SHAPE of the attempt, never grep the log for the reason — the reason is not in it.** Measured:
  the sync client writes **`Sync error: {}`** (an error object that serialises to empty braces), so
  `grep 'Vault limit exceeded' <sync.log>` returns **0 matches while every single run is failing with exactly
  that message**. The real text reaches **stdout only**. A probe built on the message therefore reports *"no
  failure in the log"* and disables the whole band silently — a gate that always says healthy. **Read whether an
  attempt STARTED an upload and whether a failure line FOLLOWED it** (in that order, inside the recency window);
  that shape is present whatever the wording, and naming the file the attempt died on makes the gate readable.
  **Generalise it: when a probe reads a log, ask what the writer actually records — a probe that searches for a
  reason the log never contains is worse than no probe, because it reports clean.**
- **Print the GATE and the RELEASE CONDITION on the row.** *"Blocked"* alone is a shrug; the next reader must
  be able to tell what would move it and who owns that. Name the failing artifact, not just the symptom.
- **Exclude already-listed rows from EVERY other heading, not just from `SILENT`.** Otherwise the same rows
  are re-reported under a second and third heading in one message, and the total reads as a multiple of the
  real debt. Measured: 6 notes appeared in full under `ESCALATE` and again under `SILENT`, so a nine-note
  queue read as twelve problems. **A row belongs under its worst band and nowhere else** — build each later
  section as `rows - already_named`, not as its own independent filter.
- **Never nudge a seat that cannot receive.** A wake whose ACK cannot arrive is a nag with a receipt — the
  exact structural defect this family of monitors keeps re-learning.
- **Keep the genuinely-owed rows red.** Suppressing the undeliverable ones must not quiet the report: the rows
  addressed to seats that *can* answer stay in `ESCALATE`/`OVERDUE`. The headline should read
  `N owe a reply · M BLOCKED on transport`, so the split is visible rather than netted out.

**This is the same defect class as lane-verifiability (below), one layer up:** *no reply in lane* and *no reply*
are different findings — and *could not have received it* is a third, which belongs to the transport, not the seat.

## Deploying a fix to all seats
1. Back up the existing script AND state file per seat (`*.bak-<change>-<stamp>`).
2. Copy the one good script to every seat's `scripts/`.
3. Reset the state file when the state schema changes.
4. Run each seat's copy directly — run 1 alerts, **run 2 must be silent**.
5. Run the real scheduled job (`hermes -p <seat> cron run <id>`) — `hermes cron run` by
   NAME fails; use the job **id**, and pass `-p <profile>` for non-default seats.

## Test harness pitfall
`exec(open(f).read())` has no `__file__` — seat auto-detection raises NameError. Use
`importlib.util.spec_from_file_location` when testing path-derived logic.

## Lane verifiability — a stuck item may be an unverifiable seat, not an ignored one
Found 2026-09-18: two handoffs to forge read as "stuck 4d" while forge was working. Its lane state
declared `lane_state_verifiable: false` — the desktop clone had diverged from the shared vault
(deleted 873, untracked 612, behind 1,260). Its resolutions landed in `_closed/` and never synced back.
Before escalating a stuck handoff, check the RECEIVER's lane state file. "No reply in lane" and "no reply"
are different findings, and only one of them is the other agent's fault. Never auto-delete the items to
clear the alert — the fix is a lane-reconciliation decision by the owning seat.
