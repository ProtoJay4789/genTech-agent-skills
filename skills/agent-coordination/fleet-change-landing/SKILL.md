---
name: fleet-change-landing
description: "Use when a fleet-wide change must land on YOUR seat."
version: 1.0.0
author: arthur (EDU) — curator-managed
license: MIT
tags: [fleet, skills, core, merge, update, restart, verification, evidence]
metadata:
  hermes:
    tags: [fleet, skills, core, merge, update, restart, verification, evidence]
    related_skills: [fleet-compatible-skills, skill-library-maintenance, checkpoint-ack, hermes-update-assessment, claim-provenance]
---

# Fleet Change Landing — applying someone else's change to your own seat

Two shapes, one spine: a change authored **outside** your seat has to be applied **inside** it, with no
content lost and with evidence a later session can check.

- **Shape A — a CORE shelf consolidation** (several skills merged into one, bodies preserved under
  `references/`) that every seat must apply to its own copy.
- **Shape B — a scheduled engine swap** (image/container recreate, runtime or default changes) where the
  seat must be parked and measured **before** the restart, because the restart wipes session memory.

**Sibling doctrine, do not duplicate it here:** the ACK shape and the FINISH→LOG→VERIFY→ACK rule live in
`checkpoint-ack`; the user-facing translation of a changelog lives in `hermes-update-assessment`; the
shared-core and drift rules live in `fleet-compatible-skills` and `skill-library-maintenance`. This skill
is the **apply/prep mechanics** those four point at.

## When to Use

- A fleet-wide skill consolidation is published to CORE and every seat must apply it to its **own** copy.
- A scheduled engine/image swap is announced and your seat must be parked, measured and ACKed before it.
- You are diffing your seat against CORE and need the order that loses nothing.
- You are writing the post-restart acceptance test and need the baseline that makes it a comparison.

## Shape A — apply a CORE shelf consolidation to your seat

**Never overwrite before diffing. Three ways, because each misses what the others catch:**

| diff | catches | misses |
|---|---|---|
| line diff both directions | stale path strings, an older revision of a table | an entire file that exists only on your seat |
| heading-set (`comm` on `^#+ ` lines) | a section CORE lacks entirely | a subtle re-wording inside a shared heading |
| file inventory (incl. `references/`) | a reference file only your seat holds | content changes inside same-named files |

Then, in this order:

1. **Promote UP first.** Anything your seat holds that CORE lacks — most often a reference file that
   CORE's own `SKILL.md` **cites** but does not contain — goes into CORE (`cp -p`, mtime preserved)
   **before** the copy-down.
   A dangling reference in CORE is the tell: for every `references/…` path named in CORE's `SKILL.md`,
   confirm the file exists. If it does not and your seat has it, you are holding the only live copy.
2. **Copy the whole directory down:** `cp -a "$CORE/$p/." "$SEAT/$p/"`. **`rsync` is not installed on
   these hosts** — plan for `cp -a`, and do not reach for delete-style sync semantics until the promote-up
   has landed in CORE.
3. **Delete an absorbed skill dir only after proving duplication per file** — `diff` the doomed
   `SKILL.md` against CORE's preserved, renamed body (expect 0 lines) — and **tar the seat dirs first**.
   A body that differs is seat-only procedure: promote it, never delete it.
4. **Assert the re-index trap is absent in CORE *and* the seat.** A preserved body left named `SKILL.md`
   inside `references/` is re-indexed as a live skill. `find <skills> -path '*/references/*' -name
   SKILL.md | wc -l` must be **0**.
5. **Repoint what the merge invalidated** — `related_skills` entries and prose naming absorbed skills —
   then **re-parse the YAML** of every edited file: a frontmatter typo disables a skill silently, with no
   error anywhere. Leave a domain-vocabulary table row alone (a permission-scope matrix is not a pointer).
6. **Verify by diff, not by count:** `diff -r` must return 0 lines per surviving skill, and the live index
   must show no absorbed name as a row.

### ⚠️ CORE moves under you while the fleet applies

Peers promote files up **while you copy down**, so a clean copy goes stale in minutes — a reference count
can grow substantially between two of your own commands, with the new files wearing **old mtimes**
(a restore, not an edit). Fingerprint before and after, loop until both conditions hold:

```bash
fp() { ( cd "$1" && find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum | cut -d' ' -f1 ); }
# stable fingerprint ACROSS the copy  AND  diff -r == 0   -> then stop
```

**Quote the fingerprint with the time it was taken**, and say your counts describe the tree *as of that
moment*. A file count is not a durable fact in a tree other agents are writing into.

### ⚠️ Disk count ≠ index rows is usually gating, not a defect

`find -name SKILL.md | wc -l` can exceed the rows in `hermes skills list`. Platform-gated skills
(`platforms: [macos]`) and toolset-gated ones (`requires_toolsets: […]`) may not render as rows while
still loading. **Close the arithmetic** (disk − rows = the gated set), confirm one with `skill_view`, and
only then report. Filing a bug against correct behaviour costs a round trip and your credibility.

Full command batch: `references/shelf-merge-commands.md`.

## Shape B — prepare your seat for a scheduled engine swap

A restart destroys session memory and nothing else. So everything the *next* session needs must be on
disk **before** the event, and it must be a measurement rather than a recollection.

1. **Census what a bounce can actually destroy:** queued writes under `pending/`, `processes.json`,
   `*.wip/*.tmp/*.partial`, and the scratch dir (probes are ephemeral — say so, do not inflate the risk).
2. **Prove the survival claim from inside**, don't repeat the phrase "bind mount": `grep -E ' / '
   /proc/mounts` showing `overlay` for `/` and a **distinct device mount** for the state directory is the
   operative evidence — the overlay is the image layer a recreate replaces.
3. **Digest every artifact you claim survives** (`stat` size + mtime, `md5sum`), including the DB **and its
   `-wal`**, and name the holdings you *cannot* protect (an un-checkpointed WAL, an unapplied queue).
4. **Capture the baseline of the commands you will re-run afterwards.** "It still works" is unfalsifiable
   without the pre-swap output; the engine's selftest/status line and any guard's exit code are the
   comparison.
5. **Triage the release digest through YOUR lane's lens and write it to the lane folder the next session
   reads** — not to chat. Then **write the acceptance test down in order**, and say which result would
   mean the engine or its data moved rather than merely restarted.
6. **Park, with resume points, everything the triage surfaces.** An engine edit discovered ten minutes
   before a swap is a parked item, not a task. Done-looks-like must be stated.

Full baseline + acceptance-test template: `references/update-window-baseline.md`.

## Pitfalls (both shapes)

- ❌ **"CORE is updated" treated as "the fleet is updated".** A promote writes the **distribution master**; the
  seats keep running their own copies until a sync **sends** it, and nothing sends automatically. Measured: one seat
  promoted a guard to CORE and reported it done — **three of the four seats still had the previous file**, byte-for-byte
  older, so the fix was live nowhere except the seat that already had it. **Propagation is a separate verb from
  authoring**, and the only proof it landed is running the artifact **from each seat**, comparing sizes or digests
  against CORE. A `--check`-style drift report is not that proof: it counts differences across every seat and skill
  (hundreds, most of them normal), which is why a real one-seat-behind condition hides inside it. Ask the tool the
  narrow question (what is *newer* than CORE) and then read the file on disk.
- ❌ **A drift COUNT read as a defect list.** "303 differences" across four seats is four copies of the same shelf
  being slightly different — expected. Promote only what the tool says is **newer than CORE**, and say which number
  you are quoting and what it measures, or the reader concludes the library is broken.
- ❌ **Overwriting because the copy-down is "the simple case".** The one time it is not, the file you
  destroy is the only copy on the fleet — a reference CORE cites but does not contain.
- ❌ **Reporting a count you did not read off the artifact in this pass.** A plausible "eight steps" when
  the source defines four, or a line count carried from memory, poisons a note full of real digests — the
  reader cannot tell which numbers were measured. Measure it, or omit the number.
- ❌ **Treating "the whole fleet has applied it" as stable ground.** Peers are writing into CORE while you
  read it. Fingerprint, and timestamp the claim.
- ❌ **Assuming a flag or default the change notice names is set on your seat.** Grep your own config and
  report **not corroborated from this seat**; the consequence for you is the useful half of the finding.
- ❌ **Banking an advertised saving.** Two changes in one release often hit the same resource in opposite
  directions; the net is **unknown until measured**.
- ❌ **Editing another seat's profile to "fix" drift you found.** Flag it; cross-seat writes are the
  coordinator's call, never a side effect of your own apply.

## Related

- `references/shelf-merge-commands.md` — the copy-paste batch: three-way diff, promote-up check, `cp -a`,
  trap assertion, fingerprint loop, index reconciliation.
- `references/update-window-baseline.md` — what to record before a swap and the acceptance-test form.
- `checkpoint-ack` — the ACK shape, the forbidden-phrase rule, and the per-event scope line.
- `hermes-update-assessment` — turning a changelog into what it means for this user's stack.
- `fleet-compatible-skills` · `skill-library-maintenance` — shared core, drift, size caps, propagation.
