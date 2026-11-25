---
name: core-consolidation-apply
description: "Use when a skill-core merge must be applied to a seat."
version: 1.0.1
author: arthur
license: MIT
tags: [skills, fleet, core, consolidation, merge, propagation]
trigger: "When the shared skill core consolidates several skills into one (absorb/merge), adds new skills, or hands each seat a copy-down instruction — and whenever a seat is told to 'apply to your own copy' after a library change."
metadata:
  hermes:
    tags: [skills, fleet, core, consolidation, merge, propagation]
    related_skills: [fleet-compatible-skills, skill-library-maintenance, derived-artifact-integrity, verify-after-every-action]
---

# Applying a core consolidation to a seat — without losing what the seat learned

**The hazard is one-directional and silent:** a copy-down replaces the whole skill directory. Every file the
seat held that the core does not is gone, with no error — the seat looks healthy and reads perfectly.

**So the order is fixed: DIFF → PROMOTE UP → COPY DOWN → PROVE THE INDEX.** Never start at copy-down because
the handoff's step list puts it first.

## When to Use

- A fleet handoff says the core consolidated skills (N → 1, "bodies preserved in `references/`") and instructs
  each seat to **apply it to its own copy**.
- New skills were added to the core and each seat must pick them up.
- You are about to overwrite any seat skill directory from a core copy — the diff-first order applies even when
  the change looks purely additive.
- **Not for:** editing one skill's text (edit the core copy, then sync), or a seat-specific skill you are
  deliberately keeping divergent — say so in the skill itself instead.

## 1. Verify the handoff's claims against the core

A note saying *"X was promoted into the core"* is a **claim**. Search the core for it
(`find <CORE> -maxdepth 3 -iname '*x*'`) before copying it down; a skill absent from the core cannot be copied
from it, and building a seat copy from another seat's tree **forks the two unless it comes from the authoring
copy and the md5 matches**.

## 2. Diff per file set and per heading — not by eyeball

```bash
comm -23 <(cd $SEAT/$p && find . -type f | sort) <(cd $CORE/$p && find . -type f | sort)   # files only I have
comm -23 <(grep -o '^#\+ .*' $SEAT/$p/SKILL.md | sort -u) \
         <(grep -o '^#\+ .*' $CORE/$p/SKILL.md  | sort -u)                                # sections only I have
```

**A line diff alone under-reports.** Rows pointing at renumbered paths, or a footer differing by a trailing
newline, are noise; a file that exists only on the seat is not. Classify every delta as *stale in the seat* or
*missing from the core* before overwriting anything.

### ⚠️ Two buckets are not enough — there is a third, and it is the one that loses work

"Stale in the seat" and "missing from the core" both imply one side is a **superset**, so a copy resolves
them. The third case is **both sides changed**: the core gained lines *and* the seat gained lines. Neither is
the newer version, and a copy in either direction silently deletes real work with no error.

**Timestamps cannot tell these apart, and they fail in the dangerous direction.** Measured on one drifted
tree: an mtime comparison classified **162** skills as "seat is newer, promote". A content-hash classifier on
the same tree found **53 promote, 13 sync, and 145 where both sides had changed** — a state no mtime can
express. Acting on the timestamp verdict would have promoted one side and dropped the other's half, then
reported success.

So classify by **content**, into three buckets:

| bucket | test | action |
|---|---|---|
| **promote** | seat content is a strict superset of core | copy up |
| **sync** | core content is a strict superset of seat | copy down |
| **review** | **each side has lines the other lacks** | **never automatic — a human reads both** |

- **Never run a bulk sync or promote against a drifted tree without a dry-run that prints the bucket counts
  first.** A tool that refuses to guess is correct; a script that guesses is the defect.
- **The counts move as you apply, and that is propagation, not regression.** Promoting into the core makes the
  core newer than every other seat, so the sync count *rises* on the next pass. Re-run until promote and sync
  are both zero — convergence, not one sweep. Do not read the rise as damage you caused.
- **A seat-only skill is a contribution, not clutter.** A directory present on one seat and nowhere in the core
  is work nobody promoted. Promote it **additively and refuse to overwrite** an existing core path — an
  overwrite there is a merge decision wearing a copy's clothes. A seat rebuild loses it permanently, and it is
  usually the newest knowledge in the building.
- **Rescue the seat-only set by name.** Listing them is cheap and they are the entries most likely to be lost:
  a report that says "7 seat-only" is actionable; "some drift" is not.

## 3. Promote UP before any copy-down

- Copy with `cp -p` so the original mtime survives, and **never overwrite a core file with a seat file** — if
  the core's copy is a superset, the core's stays.
- **A dangling `references/…` path inside the core's own `SKILL.md` is the strongest promote-up signal.** The
  core cites a file it does not hold; often exactly one seat holds the only live copy. Resolve every
  `references/` path the core mentions against the core tree before assuming the file is gone.
- **A file with no copy anywhere is a real gap — say so, do not invent one.** Name the path and the search you
  ran; a missing reference the next reader knows about is cheaper than a plausible substitute.

## 4. Delete an absorbed skill only with proof

Before removing a seat directory a merge absorbed: `diff` its `SKILL.md` against the core's preserved body
(`references/<name>/<name>.md`) and require **0 lines**, then **tar the whole set first**. Back up before
mechanical work — mechanical deletes are the ones that go wrong quietly.

## 5. Copy down, then prove four things

```bash
cp -a "$CORE/$p/." "$SEAT/$p/"        # trailing /. copies contents (rsync may be absent on the host)
```

`cp -a` is safe here **only because steps 2–3 established the seat is a subset of the core.** Prove:

1. **`diff -r` = 0** for every survivor directory.
2. **The re-index trap is absent in BOTH trees** — a preserved body still named `SKILL.md` under a
   `references/` directory is indexed as a live skill:
   `find <tree> -path '*/references/*' -name SKILL.md | wc -l` → 0.
3. **The index delta matches the merge** — `hermes skills list` shows −N absorbed, +M new, no absorbed name as
   a row, survivors present.
4. **Every edited `SKILL.md` still parses as YAML.** A frontmatter typo disables a skill silently: the file
   reads fine and the loader drops it.

**A disk-vs-index gap is not automatically a defect.** Platform-gated skills (`platforms: [macos]`) are skipped
on a Linux host and toolset-gated ones (`requires_toolsets: [kanban]`) can be missing from the table yet load
fine. Confirm with `skill_view(name)`, then make the arithmetic close (on-disk − rows = gated count) **before**
reporting it.

## 6. Repoint the pointers, and leave the ones that only look similar

Fix `related_skills`, prose, and §Related entries naming an absorbed skill. **A permission-scope matrix row is
not a skill pointer** — a table using the same vocabulary as `mapping.json` `permissions` (finance / defi / x402
…) describes authorization, and rewriting it corrupts the table.

## 7. The core is a moving target during a fleet-wide apply

Other seats promote up while you work, so file counts change under you mid-apply, and files reappear wearing
**old mtimes** (a restore, not an edit). Fingerprint, copy, re-diff in a loop, and freeze only when the core is
**stable across your copy** and `diff -r` = 0:

```bash
fp() { ( cd "$1" && find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum | cut -d' ' -f1 ); }
```

Then **state the moment your numbers describe**, and name the peer whose ACK explains any mid-apply move — an
unexplained "core changed" reads as drift you caused.

## 8. File the ACK where the fleet reads it

Append to the **shared handoff file**, not only your own lane: the next seat is reading that file. The ACK
carries, per survivor, the diff verdict (including "nothing unique to me"), the promote-up with its byte count,
what was deleted with the proof it was redundant, the backup path, the index before → after, the repointed
pointer count, and every deliberate leave with its reason.

**Every number in that ACK must come from a command you ran this session.** A line count, a byte size, a
filename — if you cannot point at the command that produced it, delete the number rather than ship a plausible
one; the point of the ACK is that its digits are reproducible.

## Pitfalls

- **Filing a finding you measured minutes ago without re-measuring it.** During a fleet-wide apply another seat
  can *close* the gap you just found — a skill missing from the core is promoted up while you write the ACK — so
  the same sentence can be true at measurement and false at filing. Re-run the one check that produced the
  finding immediately before you file, and if it flipped, record both readings with their times (**"absent at
  T1, present at T2, promoted by <peer>"**). A gap report that ships after the gap closed reads as an alarm you
  invented.
- **Starting at copy-down because the handoff listed it first.** The step list describes the merge author's
  order, not your seat's risk.
- **Trusting `diff` line counts to prove superset.** Equal headings, different bodies; or one unique section
  hidden among 30 renumbered rows. Read the unique lines, do not just count them.
- **Deleting before proving byte-identity.** The preserved body is the proof; without it the deletion is a guess
  that the seat had no local edits.
- **Calling an index gap a defect without closing the arithmetic.** Gated skills load fine and still look
  missing in the table.
- **Counting in a different unit than the one you report.** A probe labelled "skills differ from core" that
  hashes only `SKILL.md` reported **184**, while every file under the same trees diffed at **820** — the
  `references/` bodies that carry most of the depth were invisible to it. Both numbers were true and they
  answered different questions. **State the unit** (files? skill roots? `SKILL.md` only?) or the reader will
  reconcile two honest reports into a contradiction.
- **Reporting a core move you cannot explain.** Say "files reappeared with old mtimes" and check the peers'
  ACKs; the explanation is usually another seat's promote-up, and guessing otherwise raises a false alarm.

## References

- `references/core-consolidation-apply-recipe.md` — copy-paste measurement, backup, copy-stable loop and
  verification commands, plus the ACK checklist.

**Absorbed:** `skill-shelf-merge` — its full body and references now live at `references/skill-shelf-merge/skill-shelf-merge.md`. Do NOT re-create `skill-shelf-merge` as its own skill: it is this one.
