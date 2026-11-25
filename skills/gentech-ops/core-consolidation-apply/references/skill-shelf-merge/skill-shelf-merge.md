---
name: skill-shelf-merge
description: "Use when a seat applies a core skill merge to its own tree."
version: 1.0.0
author: protojay (SOCIAL seat)
license: MIT
tags: [skills, merge, propagation, core, seat, fleet]
metadata:
  hermes:
    tags:
      - skills
      - merge
      - propagation
      - core
      - seat
      - fleet
    related_skills:
      - skill-library-maintenance
      - fleet-compatible-skills
---

# Applying a shared-core skill merge to a seat's own tree

One seat, one merge. The policy that governs the library lives in `skill-library-maintenance` (size cap,
extraction to `references/`) and `fleet-compatible-skills` (Rule 0 search-then-stack, core-vs-profile
propagation) — read those for *whether* to merge. This file is the execution order and the traps that cost
real content when the order is wrong.

## When to Use

- A shared-core or umbrella skill merge lands and your seat must be brought into line with it.
- You are about to copy a shared skill down, delete an absorbed skill directory, or reconcile a seat copy
  that has drifted from the core.
- You are deciding whether to overwrite a seat copy with the core version.

## Always-on rules

- **A merge is not a rollback.** The core can be the poorer copy; the seat is sometimes the only surviving
  copy of a file.
- **Never delete before you have diffed, and never diff only the `SKILL.md`.**
- **Promote UP before copying down.** A one-way sync is a silent deletion.
- **Report the core's defects as receipts** — a gap you work around quietly is a gap no one can fix.

## Procedure

1. **Back up the whole seat skills tree:**
   `tar czf backups/skills-merge-<ts>/pre-merge-skills.tar.gz -C <profile> skills`. A per-file `.bak` cannot
   undo a deleted directory.
2. **Diff both layers for every survivor.** `SKILL.md` first, then the reference inventory:
   `for f in <mine>/references/*; do cmp -s "$f" "<core>/references/$(basename $f)" || echo "$f"; done`
   Each file listed is either missing from the core or a different version — two different findings, both to
   be resolved before any deletion.
3. **Promote up what only the seat has.** Confirm real absence across the whole core
   (`grep -rl <basename> <core>` / `find <core> -name <basename>`), then `cp -p` into the survivor's
   `references/`. **Never overwrite** an existing core file.
4. **Variants get named, not ranked.** If both versions hold unique lines, neither is a superset: promote
   the seat's copy as `<name>-<seat>-variant.md` beside the core file and say which is which. Picking a
   "winner" deletes live procedure, and the survivor still reads perfectly, so nobody notices.
5. **Copy the survivors down** only after steps 2–4 resolve: `cp -a <core>/<skill>/. <seat>/<skill>/`.
6. **Delete an absorbed directory only after `cmp -s` proves the survivor's preserved body is byte-identical
   to the `SKILL.md` you are removing.** Print the byte count, assert per directory, and **abort the whole
   deletion set** on the first mismatch.
7. **Repoint pointers in your own tree only** — `related_skills`, prose, coverage tables. A pointer into a
   `references/` path is fine to keep; a live trigger naming a directory that no longer exists is not.
   Editing another seat's tree to fix a name is a cross-seat write: flag it instead.
8. **Verify from the index, last:** `hermes -p <seat> skills list` must load, show **0 hits for every absorbed
   name**, and show the survivors; then confirm `md5sum` parity seat-vs-core for each survivor. **Reconcile the
   enabled count arithmetically:** it must move by exactly `+copied-down ��� absorbed − duplicates removed`.
   A delta that does not balance names a real defect — a duplicate still live under another path, or a copy
   that never indexed (present on disk, does nothing).
9. **ACK to the fleet handoff, not only to your own seat.** Say what you promoted up, what the core got
   wrong, and the final index count — the next seat runs the same steps against the same list, so an
   omission you absorb silently is one they repeat. Keep the rollback tar path in that record.

## Fleet-wide reconcile — direction is measured, and the copy must MIRROR

A single merge is the one-seat case. Reconciling CORE against every seat at once (the `--reconcile` mode of
`fleet-skills-sync.py`) adds four failure modes that a one-seat merge never shows.

1. **Measure which side is ahead; never assume CORE.** CORE is the source of truth by *policy*, not by
   *content* — a seat routinely holds the newer copy, and a one-way CORE→seat copy deletes it silently.
   Decide direction by **line-set containment**: if the seat's lines are a strict superset, it is strictly
   ahead and promoting cannot lose anything; if CORE's are, syncing is safe; if **both** sides added and
   removed material, neither contains the other and it is a **merge for a human**, not a copy.
2. **Do not infer direction from mtime.** A copy preserves timestamps, so `copy2`/`cp -p` can leave the
   older-looking side holding the newer content, and content written minutes apart reads as decisive when
   it is not. Recency is the weakest available signal; containment is evidence.
3. **The apply must MIRROR, never merge.** `copytree(dirs_exist_ok=True)` and `cp -a` leave files the
   destination has and the source lacks, so the two trees never become equal — the next run re-reports the
   same skill, and if the agreed-hash is then recorded from the *merged* destination the classifier reads it
   as "the source moved" and repeats forever. Copy to `<dst>.tmp`, then `rmtree(dst)`, then `os.replace` —
   a failed copy leaves the destination untouched.
4. **Baselines are per-DESTINATION, not per-skill.** One agreed hash per skill cannot describe N seats:
   after syncing seat A the shared hash matches CORE while seat B still differs, and B reads as "moved" and
   gets promoted though it never changed. Key the baseline `state[skill][seat]`.

### Three buckets, and the biggest one is not a to-do

A hash-based reconcile returns exactly three verdicts, and the shape of the result decides whether the job is
done:

| bucket | meaning | action |
|---|---|---|
| **sync** | one side is a strict superset (CORE ahead) | copy CORE → seat |
| **promote** | the seat is a strict superset (seat ahead) | copy seat → CORE |
| **review** | BOTH sides added and removed material | **a human reads both; never automated** |

- **`review` is normally the LARGEST bucket, and reaching zero is not the success criterion.** Measured: 211
divergent items reduced to 160 review in two passes, every remaining row needing a merge. Report the split —
*"mechanical drift cleared; N need judgment"* — rather than implying the shelf is now clean, and rather than
implying nothing was achieved.
- **A hand-rolled mtime classifier will massively over-count `promote`.** Measured the same day: a fast mtime
  script said *162 promote / 40 sync*; the containment classifier said *53 promote / 13 sync / 145 review*. A
timestamp cannot express "both edited", so every one of those 145 got filed as a safe promotion — which would
  have discarded CORE's half of each file. **If a quick script and the sanctioned tool disagree, the tool is
  right; do not act on the script's number.**
- **`review` does not mean the file is idle** — the common case is one side gained a section while the other
gained a different section, and both are live procedure.

### SEAT-ONLY skills hide inside `review` — rescue them explicitly

A skill that exists on exactly one seat and nowhere in CORE is a **contribution nobody promoted**: it is filed
under `review` (because it is not a mechanical copy), so an apply pass leaves it there indefinitely, and a seat
rebuild destroys it. Measured: seven such skills, two of them written the same day.

- **Rescue them as a separate, additive operation** — copy each seat-only directory into CORE, and **refuse if
the destination exists** (an overwrite there is a merge decision, not a copy). Assert CORE lacked the path
before copying so the operation is provably lossless.
- **Verify by presence on every seat afterwards**, not by the copy's success message: the point of a rescue is
  that the skill survives the loss of the seat it came from.
- **Then propagate** — a promoted skill makes CORE newer than the other seats, so the next reconcile shows a
  fresh `sync` batch. That rise is propagation, not a regression; converge it before reporting.

### Count SKILL.md drift and FILE drift separately — audits usually see only the first

A fleet probe that hashes only `SKILL.md` reports one number; the whole tree reports another, and the gap is
where the unreviewed content lives. Measured simultaneously: **184 `SKILL.md` files** differed while **820 total
files** did (636 `references/` and other files, watched by no probe at all).

- Named and reported separately, both are true and neither is alarming. Collapsed into one number, either one
  is misleading.
- **Before claiming a drift fixed, say which metric you fixed.** "0 mechanical drift" while 636 reference
  files differ is honest only when the second number is on the page.

**Order that converges:** run `--reconcile` (dry) and read every decision → apply → **run again**. A second
apply is normally required, because promoting changes the reference side and exposes skills that were equal
before; expect the count to fall to zero in two passes, not one. Re-running to zero is the proof that the
copy mirrored.

**Prove nothing was lost, by counting, before saying it worked.** Compare file counts per tree against the
pre-apply archive: `lost` must be **0** for CORE and for every seat, and `gained` should be positive. A
reconcile that reports success while a tree lost files is the exact failure this whole skill exists to stop.

### A skill that promotes on EVERY pass is usually TWO VARIANTS, not a stale hash

When the same seat reports `promote` run after run, the tempting hypotheses are "something rewrites the file on a
schedule" and "the agreement hash never updates". **Both are cheap to disprove and usually wrong.** The
disproving reads, in this order:

1. **Read the state file twice, minutes apart.** If the baseline values for that skill MOVE, the writer is fine
   and the hypothesis is dead. The apply loop records `state[skill][seat] = digest(CORE-after-copy)` after every
   copy, so a refreshed baseline is visible as a changed value, not as a promise in the code.
2. **Compute the tool's own digest for CORE and for every seat, plus the byte size.** Two seats at
   `46,491 B` and two at `46,809 B` with the **same line count** is the tell: the line-set comparison cannot call
a superset, so the classifier prints `content differs without a line-set explanation` and takes the **baseline
   branch** — `prev == CORE` → "the seat moved" → promote; `prev == seat` → "CORE moved" → sync. Two variants plus
   per-seat baselines means **CORE alternates**, and each pass has a legitimate reason to act. That reads exactly
   like a promote loop.
3. **Check whether the promoting seat's own mtime moves between passes.** If it does, someone is AUTHORING that
   file and every addition is a genuine strict superset — the tool is correct, the "loop" is a person typing.

Consequences worth stating in the report:

- **The losing variant is unrecoverable, so say so instead of reconstructing it.** Once the mirror swap runs, all
  copies hold the winner; a daily vault mirror or an old backup will predate both versions. "I cannot tell you
  what those bytes said and I will not guess at a diff I can no longer run" is the complete answer.
- **A non-superset divergence should be `review`, not an action.** If several seats hold the other variant,
  majority is not correctness. The upstream fixes: treat "non-superset + more than one seat holding the
  alternative" as review, require the same observation twice before flipping CORE, and refuse to overwrite a
  destination that carries lines the incoming copy lacks (a pre-copy line-set check, not a merge).
- **Print byte sizes in the report row, not just digests.** `core_hash`/`seat_hash` cannot distinguish "different
  content" from "different length", and the length is what makes two variants visible to a reader.
- **Stabilise the read before believing a comparison.** A file being written while you hash it yields a garbage
  line set — measured: one call reported `+597` lines against a real delta of `+29`, and five re-reads plus a
  direct per-file count all read `+29`. Read size+mtime twice and only act when they agree; an unstable read
  that lands on `promote` mirrors a truncated file into CORE.

## Pitfalls — each with the mechanism

- **An umbrella merge keeps the `SKILL.md` bodies and drops the absorbed skills' own `references/` files.**
  Copy-down-then-delete therefore destroys them, and the loss is invisible because the umbrella reads fine.
  That is why step 2 diffs the reference inventory and step 3 runs upward first.
- **The merge instruction's delete list is itself a claim.** Sweep by name:
  `find <skills> -maxdepth 3 -type d -name <absorbed-name> | grep -v references`. A duplicate left live
  re-indexes the very trigger the merge removed — the merge undoes itself while reporting success.
- **Find the absorbed skills the list never mentioned by listing what the survivor already absorbed.**
  `ls <survivor>/references/` names the skills whose bodies are preserved; any of those names still sitting
  as a **live** directory in your tree is a duplicate the handoff omitted. The references directory is the
  absorption record, so it catches the ones a name-by-name sweep cannot.
- **A skill the merge says it promoted may not be in the core at all.** Verify with `grep -rl` before
  assuming the shelf has it; when it exists only on seat trees, promote the byte-identical copy up, take it
  down, and report the gap.
- **The preserved-body trap is a naming rule:** a body under `references/` still named `SKILL.md` re-indexes
  as a live skill. Check `find <skills> -path '*/references/*' -name 'SKILL.md'` **after** all copies and
  deletions, not before — an early check can pass and a later copy reintroduce it.
- **Keep backups OUTSIDE the skills tree.** A `.bak-<stamp>` **directory** copied beside a skill still holds a
  `SKILL.md`, so the loader indexes it as a second live skill with a nonsense name — the same mechanism as the
  preserved-body trap, one directory up. Copy backups to a cache/backup path outside `<profile>/skills`, and
  sweep `find <skills> -name '*.bak-*'` to catch ones left by earlier passes.
- **`cp -a` never removes extras,** so a seat survivor can keep files the core dropped. Usually the outcome
  you want, but it means "the directories match" is never proven by a copy — only by the inventory diff.
- **A file copied correctly but not re-indexed looks identical on disk and does nothing.** The index check and
  the digest check answer different questions; run both.
- **A long reconcile prints its PLAN first and its VERDICT last — read the tail before concluding nothing was
  written.** Measured: an apply whose output was examined only from its opening lines looked identical to the
  dry run (same counts, same list), and the conclusion was "the apply silently wrote nothing" while 63 files
  had in fact changed. Reading only the front of a report hides the one line
  (`APPLIED — promoted N · synced N · failed N`) that answers the question. Read the LAST lines and confirm with
  `git status --short` on the target tree — a changed-file count is the cheapest possible disproof of "no write
  happened".
