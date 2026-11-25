---
name: derived-artifact-integrity
description: "Use when a file is generated or state is keyed."
version: 1.0.0
author: arthur
license: MIT
tags: [generated-files, keyed-state, drift, silent-wrongness, reproducibility]
metadata:
  hermes:
    tags: [generated-files, keyed-state, drift, silent-wrongness, reproducibility]
    related_skills: [develop-and-verify, fleet-compatible-skills]
---

# Derived-Artifact Integrity

Two shapes, one defect: **something derived silently disagrees with the thing it was derived
from, and nothing raises an error.**

- a **generated file** drifts from its source (readings, indexes, caches, dashboards, denormalised
  tables);
- **keyed state** is keyed by a value that a transform rewrote before serving (rendered variants,
  personalisation, i18n forms, canonicalisation, A/B branches).

## When to Use

- You shipped, or are about to ship, a **file produced by a script** — readings, indexes, caches,
  dashboards, denormalised tables, generated docs.
- You are **keying stored state** by a value something later rewrites: forms, locale,
  canonicalisation, variants, branches.
- A stored record is **not accumulating** the way it should — the system behaves as though nothing
  was ever learned between runs.
- You are **editing an artifact that gets copied** to other hosts, seats or packages, and need the
  edit to still be there afterwards.

## 1. A generated file ships with its generator

A file produced by a throwaway command is a **dead end**, even after it ships and works: the next
item added to the source is served with nothing, and no tool on disk can produce its value.

- **Commit the generator beside the output, and derive from the SOURCE OF TRUTH** — the producer's
  own data or module, never a hand-typed copy of it. That is what stops the values drifting from the
  inputs actually in use.
- **Re-run the generator against the shipped file and diff to ZERO differences** before calling it
  reproducible. An unproven generator is a claim, not a tool.
- **Refuse where it cannot honestly produce output.** No input, no format handler, no converter →
  exit non-zero. Hand-writing the values it could not derive is how a generated file becomes a lie.
- **Write the artifact's own limits INTO the artifact** (a `limits`/`note` field beside the data):
  "approximate, no tone marks", "unsorted", "sampled at T". A later reader who cannot see the limit
  will assume it was handled.
- **Inventory it.** If a script is part of the package, the package's own script list must name it,
  or the next maintainer never learns a generator exists to re-run.
- **A producer behind an opt-in flag produces nothing.** If a second instrument consumes the artifact,
  the producing job must write it EVERY run. A `--json PATH` flag that the schedule never passes leaves
  the consumer reading a file that was never created, and the consumer's empty report looks like "no
  findings". Wire the write into the job, not into a flag a human has to remember.
- **A consumer must sum the key the producer WRITES — and must not paper over its absence.** A row built as
  `{"amount": x}` and consumed as `r.get("usdc") or 0` totals to zero forever: the report states "no income"
  with full confidence while the money sits in the file. `or 0` on a missing key converts a schema mismatch into
  a **fabricated zero**, which is strictly worse than an error. Name the field once and read that name, or have
  the consumer refuse when the key is absent. **Prove it by feeding the consumer one known non-zero record and
  diffing the total** — a reader that has only ever been given zero cannot tell you it works.
- **ONE VALUE UNDER TWO KEYS IS TWO VALUES THE MOMENT TWO READERS DISAGREE.** A field stored twice
  (`priceUsd` beside `price_usd`, `amount` beside `value`, a camelCase beside a snake_case) is not
  redundancy — it is two independent numbers that happen to start equal. Measured: a catalogue reader read one
  key and a CHARGING path read the other, so the published price was $0.01 while the amount taken was $0.001.
  Both readers were internally correct, both printed a plausible number, and nothing errored — the defect is
  only visible by comparing the two outputs side by side.
  * **When a field exists under more than one name, a partial update is WORSE than no update** — it converts
    two agreeing numbers into two disagreeing ones and moves the failure from "stale everywhere" to "the shop
    window lies about the till". Update every alias in one write, or refuse to write at all.
  * **Make the reader pick a precedence and say so:** read the advertised key first, fall back to the alias,
    and print a warning when they differ. Silent precedence is how the next edit drifts again.
  * **Prove it with a PARITY CHECK, not two separate reads** — fetch what the system ADVERTISES and what it
    actually CHARGES/SERVES, and assert them equal in the same test. Each side passing its own check is exactly
    the state that hid the defect.
  * **Then delete the second key.** A schema that tolerates two names for one value will grow a third.
- **Recompute counters from a dated ledger; never increment them in place.** A tally that does
  `previous + n` on every invocation double-counts the second run of the same day and inflates forever
  after. Append `{date: {key: n}}` to a ledger and derive totals from it, so re-running the generator is
  a no-op. **Prove it by running the generator twice and diffing the artifact** — identical output, or the
  counter is wrong.

## 2. Key state by the value you SERVED, after every transform

**Order is the bug.** If a record is keyed before a transform rewrites the served value, the key is
one no writer will ever write.

- **Procedure:** apply the transform FIRST (learner form, locale, canonicalisation, variant), then
  compute the key from the value actually emitted.
- **Keep the pre-transform key as a READ fallback** so records written under the old shape still
  count. A re-key must never silently wipe history.
- **Why it is silent:** the lookup misses, the record reads as `new`, and the loop that exists to
  re-serve what the user got wrong **resets forever** — with no error, no warning and no visible
  difference from a first-time user.
- **Test both halves in the same check:** plant a record keyed by the *served* value and assert it is
  picked up as needing work; then hand that same record to the **sibling identity** and assert it is
  **not** picked up. The second half is what proves the identities are actually separate — passing
  the first half alone is consistent with every identity sharing one record.

## 3. Prove an edit landed in the source of truth, not a copy something overwrites

When an artifact is propagated to copies by a sync or deploy, an edit to a copy is a **build
artifact**: it looks saved and is reverted later — including a write made through a
package/skill-management tool, which targets the installed copy.

- **An edit that landed MOVES the digest.** Hash the source directory before and after. An
  unchanged digest after an edit means the edit went somewhere that gets overwritten: the change is
  gone, not applied.
- **Belt and braces:** `grep -c '<a marker you introduced>' <source-of-truth path>`. Zero means you
  fixed a copy.
- **If the only write path you have reaches a copy, say so** — the change is copy-only and will not
  survive propagation. Reporting it as landed is the same failure as the silent revert.
- **Prove a generated DECLARATION on the surface that PUBLISHES it, not through the helper that resolves it.**
  A publisher that iterates source records (`services` keys like `gas_oracle`) and a lookup helper that resolves
  display names, keys and URL segments (`gas`) through an alias table are **two different key paths**: a fix keyed
  by the segment passes a unit call to the helper and never matches the publisher, so the served document is
  unchanged while the test is green. **Read the artifact over the transport a consumer uses** — `curl` the served
  `/openapi.json` after the restart, inspect that operation — and treat a unit-level "verified" as UNVERIFIED
  until then. A fix reported as landed that missed the published document is worse than no fix, because the
  restart already happened and nobody looks again.

## 4. "Recomputed" in the header is a CLAIM — find its producer or strip it

Some files assert their own derivation in prose: *"Recomputed from X. Never edited by hand."* That sentence is
copied boilerplate far more often than it is a fact, and **when it is false the file is worse than a static
file, because readers trust it**. Measured: a scoreboard whose header said it was recomputed from the ledger sat
unchanged for four days after the ledger had gained a resolved entry — it still said *"none resolved yet"*.

- **For every file that claims to be generated, name its producer out loud: the script AND the schedule.** No
  script, or a script nothing schedules → **the claim is folklore**. Either generate it or delete the claim.
- **Corroborate with mtime, not with the file's own text** — but treat mtime as a TRIPWIRE, not a measurement.
  A "generated" file whose mtime predates changes to its stated source is stale by definition. Compare
  `stat -c '%y'` on the artifact against the newest mtime of the source it claims to derive from. **Then read
  the producer's own stamp for the real age** — see the next bullet, because mtime alone under-reports.
- **Put the writer in the header:** *"Generated <timestamp> from <source> by <script>. Do not hand-edit — it is
  rewritten every run."* A timestamp in the file turns staleness into arithmetic instead of an argument.
- **Write every derived file from the SAME run that derives the values.** Splitting them (one script emits the
  report, another "maintains" the summary) is how two artefacts come to disagree with one source.

- **AGE COMES FROM THE PRODUCER'S STAMP, NEVER FROM mtime.** A filesystem timestamp moves without the
  content being rebuilt, so an mtime-based freshness check reports a stale artifact as fresh. Three measured
  mechanisms, all of which produced a plausible and wrong number:
  * **a copy or restore bumps it** — `cp`, a backup restore, or an `ln` over the file leaves mtime at *now*
    while the contents are hours old. A "touch to test staleness" that restores by copy defeats its own test;
    restore with `os.replace` from the producer, or re-run the producer.
  * **a cosmetic edit bumps it** — hand-patching one field (adding a key, fixing a label) resets mtime without
    regenerating anything, so a 90-hour-old source reads as 26 hours old. This under-reported staleness by
    **3.5x** in the case that named this rule.
  * **a date-only stamp cannot express sub-day age** — `generated: "2026-11-05"` is measured from midnight, so
    a file rebuilt two minutes ago reports up to 24 hours of age and trips a false disagreement against a
    perfectly accurate mtime. **Write BOTH:** `generated` (date, for anything that reads it as one) and
    `generated_at` (an ISO instant). Consumers must prefer the instant and say which they used.

  **Keep mtime as a disagreement detector:** if the stamp and the mtime differ by more than the stamp's own
  resolution, something touched the file without regenerating it — say so out loud rather than silently
  picking one.

- **NEVER hand-edit a generator's OUTPUT — the next run is a delete.** A generator writes a fresh file and
  knows nothing about what someone appended to the last one, so a hand-added row survives exactly until the
  next scheduled run and then vanishes with no warning. Measured: a manual refresh dropped three hand-added
  entries (18 rows → 15) and the only reason it was caught is that the count was compared against the previous
  day's. **Declare supplements inside the generator** — a source-level list it merges on every write — and give
  each an expiry so it drops out on its own instead of accumulating as dead rows. Corollary: when a row is
  missing after a run, suspect the generator overwrote it before suspecting the source failed.

- **A collision on a key must be resolved by a RULE, not by arrival order.** `dict.setdefault(key, e)` keeps
  whichever record the upstream happened to send first, which is stable-looking and arbitrary: a sub-component
  beat a headline release on the same `(date, code)` key and the artifact then labelled a capital-gating event
  with a sub-index. Write an explicit preference function and apply it on every collision, then **test it
  against every colliding PAIR you know about, not only the pair you are fixing** — preferring the shorter name
  fixed the headline case and immediately degraded a bare ticker to beat its own qualified form.

**Corollary — a gate with no producer is a paragraph.** A checklist that lives only as prose in a plan document
is not a check. Give each row a *producer*: the measurement each row needs must exist somewhere on a schedule,
and the row must **fail when its data is absent** rather than pass by not running. Before trusting any gate,
count its rows and ask of each one *"what writes this number?"* — a gate where three of five rows have no writer
is a document describing a check, not a check.

## 5. A PUBLISHED artefact can have N copies and no canonical one

Propagation multiplies copies; nothing about copying picks a winner. **Three remotes of the same library, at three
different ages, plus a drift checker pointed at one of them** is the shape: the checker is not wrong, it is
reporting on one of three truths, and every reader assumes it is the only one.

- **Declare ONE canonical publication target, in the artefact that lists them.** Every other copy is marked as a
  pointer (archive it, or put a one-line README that names the canonical repo) — a copy that stays silently live
  is a second source of truth whether or not anyone intended it.
- **A drift report is a measurement of how long publishing was skipped, not a backlog.** When the checker says
  "N missing, M stale", the honest framing is *publishing is not part of the change*. Capture the number as the
  outage measurement, then fix the PROCESS — a publish step in the same pass that edits the source — or the same
  report returns every cycle and is eventually muted.
- **Compare live-vs-published by IDENTITY, not by count.** Equal totals hide a swapped item; report names that are
  missing, names that are extra, and names whose content differs, separately.
- **A withhold list is a DECISION, and it must be subtracted before drift is computed — with its reason.** Items
  excluded because they need your infrastructure, your wallets or your people are not drift; a checker that counts
  them produces a number nobody can act on. But an item absent *and not on the list* is the genuine finding.
- **Publishing to a shared/public surface is the owner's call, not the generator's.** A tool may prepare the
  copy and prove it byte-identical; the human decides which remote the world sees.

## Pitfalls

- **A reader that assumes the writer's OLD SHAPE fails before it can refresh its own baseline.** Measured: a
  reconcile tool's state file stored a bare digest per target (`{"skill": {"seat": "a08c73867492"}}`) while its
  classifier called `.get("agreed")` on that value. The first record raised `AttributeError`, the process died
  **before** its own writer step, and the baseline was therefore never updated — so the tool had completed **zero**
  runs and each retry began from the same stale state and failed identically. **Read one REAL instance of the state
  file before coding accessors against it**, accept both shapes across a transition (bare value *and* dict), and
  **do the bookkeeping write before any risky read** so a parse failure cannot also destroy the baseline.
  **A tool that dies before its own housekeeping cannot self-heal** — the tell is a state file whose mtime never
  advances, and the false reading is "the tool ran and found nothing to do".
- **Empty because the WINDOW is wrong** — a third shape beside "nothing happened" and "the read failed". Every
  lookback expressed in a unit with an ASSUMED rate (blocks/day, pages/day, ticks/day, epochs/day) is only as
  correct as that constant, and when the constant is too small the answer is an empty period that reads exactly
  like a quiet quarter. Measured: an assumed 43,200 blocks/day against a real 431,952 covers **0.70 days where
  7 were asked** — the revenue job reported nothing one day after a payment landed, and nothing in the output
  looked broken. **Derive the rate from two known points** (a timestamped record and the current tip) rather
  than from prose, and print the computed span beside the figure so a wrong constant is visible as a wrong span.
- **A payer is not a customer, and the sum is not revenue.** Any inbound ledger mixes the operator's own
  test traffic with real money; reporting the total as income produces two failures at once — a flattering
  number on a quiet week and a zeroed one when the classifier is wrong. Classify senders in **one audited file**
  (ours / harness / customer / unclassified, each with the evidence for its label) and report the customer line
  first, with the excluded buckets named underneath. Anything unclassified is reported as unclassified — never
  folded into revenue and never silently dropped.
- **Empty because nothing happened vs empty because the read FAILED.** A swallowed exception in a
  state loader reads as "no history" and silently recomputes every record as new. Announce damaged
  separately from absent — *"the record is damaged, not empty."*
- **A silent default in a lookup converts "we don't know which" into "use this one"** — and when the
  default is gendered, regional or currency-flavoured, the wrong one is served. Fall back only where
  the data explicitly declares a fallback, and print when you take it.
- **A rename is not a reason to lose data.** Re-keying orphans stored records; carry a legacy-key
  read path.
- **Never print a value you could not derive as a zero.** On an artifact whose whole job is honesty,
  an unmeasured field is `UNMEASURED` or `varies`, and the generating step must say which.
- **Do not test a guard by mutating the live artifact.** Plant the failure in a scratch copy, prove
  the guard goes red, leave the shipped file untouched.
- **A generated file with no generator looks identical to a healthy one.** Nothing in the artifact
  records how it was made, so audit the PROCESS (is there a committed generator? does it still run
  clean?) rather than the file's contents.
- **An audit that compares two things needs its own translation table checked first.** When a comparator
  reports a surface as wrong, an unmapped name on the AUDITOR's side produces exactly the same finding as a
  real defect — and the "fix" it invites edits a surface that was already correct. Treat "name not in <MAP>"
  in a report as a defect of the report. See `references/discovery-surface-audit.md`.

## Related

- `references/discovery-surface-audit.md` — auditing many published doors (manifest, bazaar, OpenAPI, `llms.txt`,
  MCP) against one inventory: per-surface failure table, template-brace probes, reading a crawler's log, and
  **how to rule out the auditor before you "fix" a surface**.
- `develop-and-verify` — the silent-wrongness checklist and the Jr/Sr audit that finds this class.
- `fleet-compatible-skills` — shared core vs profile copy, and the sync that reverts a copy edit.
