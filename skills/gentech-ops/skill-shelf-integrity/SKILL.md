---
name: skill-shelf-integrity
description: "Use when merging skills or clearing dangling references."
version: 1.0.0
author: Gentech
license: MIT
metadata:
  hermes:
    tags:
      - skills
      - shelf
      - references
      - citations
      - fleet
    related_skills:
      - skill-library-maintenance
      - fleet-compatible-skills
---

# Skill Shelf Integrity

Keeping a multi-tree skill shelf **honest**: merging skills without losing the only copy of a lesson,
and clearing `references/` citations that point at nothing.

> Overlaps `skill-library-maintenance` (size caps, extraction) and `fleet-compatible-skills`
> (propagation, drift). Those cover editing and distributing a skill; this covers the two operations
> that quietly destroy content: **overwriting a richer copy**, and **a citation that rots**. If that
> overlap is unwanted, fold this in — but do not keep two answers to "what do I do about a dangling
> pointer".

## When to Use

- CORE has merged or renamed skills and each seat must adopt the change.
- A skill cites a `references/` file that does not exist (a sweep reports dangling citations).
- You are about to overwrite, delete or "clean up" any skill directory on a seat.

## Rule 1 — Diff before you overwrite; a seat copy can be RICHER than CORE

The seat is not automatically the older copy. Overwriting is the only irreversible step in a shelf
change, so measure direction first:

```python
import difflib
a = open(seat_md).read().splitlines(); b = open(core_md).read().splitlines()
new = [l for l in difflib.ndiff(a, b) if l.startswith('- ')]   # only in the seat
```

- **Zero lines unique to the seat** → the copy-down is strictly additive. Safe.
- **Any unique line** → the seat is richer. **Promote that line UP to CORE first.** Copying down now
deletes the only copy of a lesson, and no later audit will report it, because the file looks healthy.

Unique lines that are just *stale paths* CORE already corrected are not content — read them before
treating them as a reason to block.

## Rule 2 — Delete an absorbed skill only on a byte-identical proof

Before `rm -rf` of a directory whose body CORE claims to have preserved:

1. `md5sum` the seat body against CORE's preserved copy. Equal hashes, or no delete.
2. `tar czf` the seat directories first. A backup costs a second; a lost lesson costs a session.
3. Delete, then **verify by index arithmetic**: the enabled skill count must move by exactly
   `-absorbed +added`. The filesystem cannot tell you a skill vanished; this can.

A body preserved under `references/` must **not** still be named `SKILL.md` — that file is re-indexed as
a live skill and silently undoes the merge. Check with `find <tree> -path '*references*' -name SKILL.md`.

**Then sweep the tree for the absorbed skill's NAME.** Other skills still carry it in `related_skills`,
in prose pointers, and in comparison tables. Repoint the pointers; **leave scope and permission tables
alone** — a scope name that happens to match a skill name is data, not a reference, and rewriting it
corrupts the table's meaning. A `references/` scanner never reports a dangling *skill* name, so this
pass is manual: `grep -rn '<absorbed-name>' <tree> --include=SKILL.md` and read each hit in context.

## Rule 3 — Never repoint a dangling citation at "something similar"

A wrong pointer answers with confidence, which is worse than a known gap. Exactly three moves:

| situation | move |
|---|---|
| the file exists at the **same skill path** in another tree | **restore** it (copy in) |
| the citation names a **wrong base** for the same artifact (a vault variable, a dead skill name) | **correct the base** to where that artifact actually lives |
| no copy exists anywhere | **declare** it under `## Missing references`, naming what it should be |

Substituting a different file that merely sounds related is the failure this rule exists to stop.
When a same-named file lives in another skill, ask whether it is the *same artifact*; if it is a
different document (an index versus a ledger, say), declare instead and say why.

## Rule 4 — Fix the instrument before you trust its count

A raw dangling count inflates. Three measurement defects were enough to produce 22% false
positives on a real sweep:

1. **Cross-skill citations read as local** — a citation that begins with another skill's name names its
owner and the file exists; a checker that strips the prefix looks in the citing skill and reports a gap.
2. **Declarations are invisible** — if the checker cannot parse `## Missing references`, a correctly
declared gap scores identically to a silent one, which penalises the honest fix. Count them
   separately and do not fail on them.
3. **Repository paths read as skill paths** — an absolute repo path is not a citation of this skill.

**Prove the relaxed checker can still fail**: plant one missing citation in a scratch skill and
confirm exit 1. A checker that passes everything after "fixing" false positives is broken, not calm.

**And writing a literal path example into prose creates a citation.** Documenting a checker with a
sample reference path — even as an illustration — makes it flag your own documentation. Describe the
shape in words.

### Four more over-broad classes, each measured on a claims audit

An audit of "does every path/command/skill this file names actually work" produced the same shape:
most of the count was the instrument, not the shelf. Split before you fix:

1. **A path the reader is told to RUN is a different claim from a file it merely names.** A missing
   `.py`/`.sh` is a defect (the instruction cannot be followed). A missing `state/*.json`, log or cache
   legitimately does not exist until its producer has run once. Class `SCRIPT` and `DATA` separately, and
   only report the first; an undifferentiated class buries twelve real findings under forty false ones.
2. **A skill that DOCUMENTS an absence is the fix, not the defect.** After annotating a dead reference
   with "not installed — do not assume it runs", re-running the checker must not re-report it. Teach the
   checker the negation words it will see (`absent`, `not installed`, `no longer exists`, `is not a
   command`, `example`, `placeholder`) and scope the test to the line carrying the reference.
3. **A skill naming ITSELF is not a dangling reference.** `browser-trace` mentions "browser"; a
   frontmatter `name:` matches the skill's own name. Exclude the citing skill's own directory name, and
   match on the full name — a shorter name must not be satisfied by a longer neighbour either.
4. **An alias resolves, and only running it proves that.** `hermes gui` is not in the command list and
   works (it is `desktop`). Before flagging a command as invented, run `--help` and read the exit; a
   name-based check cannot tell an alias from a fabrication.

**The tell that you are fixing the instrument and not the shelf:** the total drops and the *shelf has not
changed*. Say so in the report — "most of the drop was the checker getting honest" — because a falling
number that nobody qualifies reads as work completed.

## Rule 5 — Gate the standing check on CHANGE

A daily job that repeats the same accepted gaps gets muted within a week, and a muted checker is a
checker nobody has. Record per-tree counts in a state file; **print nothing when nothing moved**, and
report only growth (regression) or shrinkage (a fix landed). Declared gaps are the accepted baseline,
never news.

### Prove the standing check can DELIVER, not just decide

A silence-gated job can be perfectly gated and still reach nobody — and a job that is always silent
never exercises its delivery path, so nothing reveals it. `no_agent` runs record a `delivery_outcome`
per execution in `profiles/<seat>/cron/executions.db`: `suppressed` for empty stdout, `delivered` for a
run that spoke. Force the proof by moving the baseline aside so the next fire must speak, read the
outcome, and let that run rewrite the baseline — two fires then yield two opposite receipts, which
proves the rail from both ends. Each run's stdout is on disk under
`profiles/<seat>/cron/output/<job_id>/<stamp>.md`, and a silent fire writes **no** gateway log line, so
"no POST in the log" is the expected shape of silence, not evidence of a lost message. Quote the
receipt by field name (`delivery_outcome = delivered`), never "it ran": a green status says the
process exited, not that anyone heard it.

## Rule 6 — A CORE fix does not converge the seats

Every tree drifts independently, so the same sweep must run per tree or the seats keep the old
counts. Fix what you own; **report the others rather than editing another seat's tree** — a seat-only
edit is a build artifact that the next sync replaces.

## Rule 7 — Scope the sync to the divergence you fixed; `--promote` is not a bounded operation

The sync tool's own advice is *"--promote then --sync"* — and that order is right, but **the two
operations have wildly different blast radius and only one of them is yours to run.**

- **`--sync`** copies CORE **down** to seats. Bounded by what CORE holds; safe to run once CORE is
  correct.
- **`--promote`** collects **every seat-only contribution in the fleet up into CORE** — including
  `seat-only` entries that are other agents' **unfinished work**. Promoting those **canonizes a
  draft as fleet doctrine**, and the sync that follows then distributes it to everyone.

**Measured shape:** a single two-skill rail fix sat beside **13 seat-only contributions on one seat,
10 on another, 6, 3** — a fleet-wide `--promote` would have published 32 unpromoted drafts as canon
to make one fix travel.

**Rule: when you have fixed a named divergence, scope the write to that divergence.** Copy those
specific paths CORE-ward or seat-ward and verify byte-equality, rather than invoking a fleet-wide
sweep. Reserve `--promote` for a session whose actual purpose is curation — deciding, item by item,
which drafts deserve to be canon.

**`--promote --seat <mine>` is the bounded form, and it is bounded by SEAT and MTIME, not by your
intent.** Fleet-wide `--promote` collects every seat's drafts; the per-seat form considers only your
tree, and its guard is *"seat copy strictly newer than CORE's + 1s"*, so a seat copy that is merely
different — older, or a peer's in-flight edit — is not swept up. Measured: three runs on one seat
published **8, then 1, then 1** skills. Read that list and confirm every entry is yours to publish:
if skills unrelated to the change you were making appear on it, a curation decision is happening by
side effect, and the fix is to name them in the report rather than to pretend the promote was scoped.

### Rule 7b — Check the DIRECTION of the stale copy before any `--sync`

A distribution claim — *"engine X is identical in CORE + 4 seats"* — is a point-in-time measurement,
and **CORE can move backwards**: a restore, a snapshot re-run, or an rsync of an older tree leaves CORE
holding the *older* file while every seat holds the newer one. In that state `--sync` is not a fix, it
**reverts the fleet** to the older artifact, silently, and each seat then reports drift that reads as
their own.

So measure direction before syncing — digest CORE against **every** seat and name which side is newer:

```bash
md5sum $CORE/<path> /opt/data/profiles/*/skills/<path> 2>/dev/null
stat -c '%s %y %n' $CORE/<path> /opt/data/profiles/*/skills/<path> 2>/dev/null | sort
```

- **seats newer, CORE older** → promote up (`--promote --seat <mine>`), re-digest, then only sync if a
  seat is still behind. Never sync first.
- **CORE newer, seats older** → sync is the right direction; run it once CORE is proven green, and
  prove the promoted copy by **executing** it (`--selftest`), not by digest alone.

**Expect the peer drift count to RISE after a correct promote.** Publishing your newer copy makes CORE
differ from the other seats' older ones, so the total moves by the published-skill count × peers (a real
session: **215 → 220**). That number is the metric reporting a true asymmetry, not a new defect: quote
both numbers and the reason, and never clear an alarm your own correct write created.

**And re-take the digest before acting on your own earlier claim.** A record that says "identical in
CORE + N seats" was true at the moment it was written; an hour, a restore or a peer's sweep can falsify
it. When the re-run contradicts it, append a superseding line that names the earlier number — never
smooth it, because the next session inherits whichever one you left standing.

### Rule 7c — mtime cannot express "both changed"; classify by CONTENT SETS

**A timestamp answers "which copy was touched last". It cannot answer "did CORE gain work while the seat
gained *different* work" — and that is the case that ruins a sync.** Measured: an mtime classifier called
**162 skills `promote`**, which reads as the safe direction. The content-hash reconciler on the same tree
reported **53 promote · 13 sync · 145 where BOTH sides had changed** — syncing on the mtime verdict would have
overwritten those 145 with CORE's half, silently dropping the seat's half, and every one would still have
looked like a file that had merely been promoted.

**Classify each differing skill into exactly three buckets by comparing CONTENT:**

| bucket | test | action |
|---|---|---|
| **promote** | seat is a strict SUPERSET of CORE | copy up (additive) |
| **sync** | CORE is a strict SUPERSET of the seat | copy down (additive) |
| **merge** | each side has lines the other lacks | a human reads both; never automatic |

- **Use the tool that already classifies this** (`fleet-skills-sync.py --reconcile`, dry-run first) instead of
  hand-rolling a comparator, and **re-run `--apply` until it converges.** Promoting into CORE makes CORE newer
  than the *other* seats, so the sync count legitimately RISES before it falls (13 → 103 in one pass, then 0).
  A rising sync count after a correct promote is propagation, not regression.
- **Never act on a `promote` that came from mtime alone.** The merge bucket is invisible to timestamps and is
  exactly the content a blind sync destroys.
- **A converged tree still reports the merge bucket, forever — and that is correct.** Zero promote + zero sync
  + N merge is converged, not failing. Say so in the report, or the next pass will keep trying to "fix" it.
- **Count skills and count files separately.** A probe that hashes only `SKILL.md` reports one number while a
  full-tree diff reports roughly four times as many (`184` vs `820` on a real shelf), because reference files
  drift too and no probe watches them. Name which unit you measured before comparing two drift totals.

### Rule 7d — Rescuing SEAT-ONLY skills, additively

**A skill that exists on exactly one seat and nowhere else is a contribution nobody promoted, and a seat
rebuild deletes it.** Measured: seven such skills across four seats, two of them written that same day.

- **Copy them up by ADDING only.** Refuse if the destination directory already exists — an overwrite there is
  a merge decision wearing a copy's clothes.
- **Verify by presence on every tree afterwards**, not by a copy's exit code: N files × four seats plus CORE
  must read `N/N` everywhere.
- **Do not assume `--promote` is the right vehicle.** It is mtime-guarded and sweeps unrelated newer drafts from
  the same seat (Rule 7). A targeted copy of the seat-only set publishes exactly the orphans and nothing else.

### Rule 7e — "It promotes the same skill EVERY pass" is a CONTENT split, not a stale baseline

**The instinct is that the agreement hash never updates after a promote. Check the writer before you accept it —
the instinct is usually wrong, and pursuing it sends the next reader to the wrong file.**

Measure in this order:

1. **Read the apply loop.** If it records `state[skill][seat] = digest(CORE)` **after every copy** (not only after a
   sync, not only on success paths), the baseline refreshes by construction.
2. **Read the live state twice, minutes apart.** A baseline that moved between the two reads disproves the
   stale-hash theory with one command. If it did not move while copies were still landing, that IS the bug.
3. **Digest AND size every copy** — CORE plus each seat. The failure looks like this:

```
seat A  46,809 B  digest f507…      seat C  46,491 B  digest d4c7…
seat B  46,809 B  digest f507…      CORE    46,809 B  digest f507…
```

**Same skill, two live variants.** Both copies can carry the **same line count** — so a line-set comparator
returns *"content differs without a line-set explanation"*, `diff` prints nothing useful, and the classifier falls
through to its baseline branch: `prev == core_hash` → **"seat moved" → promote**, `prev == seat_hash` → **"CORE
moved" → sync**. With two variants and two baselines, CORE alternates and **each pass legitimately promotes** —
which is why the report says "promotes on every pass" without lying.

**Rules that follow:**

- **Same line count + different byte count = a non-superset split.** Never treat equal line counts as equal
  content; compare digests and `stat -c '%s'` on every copy, not just the two you happened to open.
- **A non-superset split across seats should classify as `review`, never as an action.** Majority is not
  correctness: "three seats hold X" is not evidence X is right, and acting on it canonises a variant by counting.
- **A loop that alternates is a two-strike problem.** When the proposed action would flip CORE's content to a
  variant it has not held in the previous observation, record it as pending and act only if the next pass agrees.
  A genuine edit survives one delayed pass; a ping-pong does not.
- **The mirror swap destroys the losing variant, and there is usually no backup of it.** By the time you diagnose
  the loop, every copy may hold the winner and the only archived copy predates both. Say the content is
  unrecoverable rather than reconstructing what it "must have" said — and put a pre-copy line-set check on the
  DESTINATION in the fix list, because that is what would have turned the loss into a `review` row.
- **Report the byte sizes in the row, not just the two hashes.** `core_hash`/`seat_hash` cannot distinguish
  "different content" from "different length", and it is the length that tells a reader two variants are live.
- **Confirm convergence by re-digesting all five copies, then say what the next pass should report.** "All five
  identical, all four baselines matching, next pass should read `agreement`" is checkable; "it's fixed now" is not.
- **The same split explains a skill that keeps appearing in a human-merge list after a "sync".** A copy resolves a
  direction; it never merges two variants, so the item returns until a person picks one.

## Rule 8 — "Not in the drift list" is not "in sync" — and a SHORT LIST is not a COMPLETE LIST

A drift report is a claim like any other, and a clean report and a covered item are different claims —
but the first version of this rule got the **failure mode** wrong, and a wrong rule is worse than none.

**What actually happened (measured 2026-10-23):** a skill differed from CORE by **2,269 bytes on three of
four seats** and appeared nowhere in the printed drift output, which read `TOTAL DRIFT: 125`. The conclusion
drawn was *"the checker has a blind spot."*

**That conclusion was FALSE.** The checker prints only the **first six** entries per category:
```python
for k in sorted(mism)[:6]:
```
**The skill was in the mismatch set the whole time.** What looked like a blind spot was **a truncated list
read as a complete one.**

**The test that settles it — never infer a tool's coverage from its output:**
```
mutate one byte in the live target → re-run the checker → confirm the count MOVES → restore → diff
```
**Measured: baseline drift 20 → after a 1-byte mutation, 21.** The checker sees it.

**Rule: before reporting that a tool missed something, read its OUTPUT CODE and confirm the list is
complete.** A `[:6]` slice renders exactly like a full list in a terminal. **Absence from a subset is not
absence** — the same rule this fleet already applies to API probes and remote discovery surfaces.

**Cost of getting it wrong:** this rule's first version was distributed to every seat as doctrine, carrying
numbers that made an **unverified inference look like a measurement**. It said a working tool was broken.
**Correct it here, then sync — and check whether the wrong version is already on a seat.**

## Rule 9 — A BACKUP INSIDE AN ENUMERATED TREE BECOMES A PHANTOM ENTRY

Before overwriting a seat copy, backing it up is right. **Backing it up as a sibling directory inside the
skills tree is not.**

**Measured 2026-10-23:** copying each skill to `<skill>.bak-YYYYMMDD-HHMMSS` beside the original added
**6 phantom "seat-only contributions"** and inflated the fleet count by 6 — because **any directory in the
skills tree is enumerated as a skill.** Skills per seat read **278** with the backups, **276** without.

**Rule: a backup must never be a sibling named `<thing>.bak-*` inside a directory a tool enumerates.**
Put it **outside the tree** (e.g. `/opt/data/backups/<purpose>-<date>/`), or the backup you took to be safe
turns into corrupt signal about the thing you were measuring.

**Tell-tale:** after an edit, `drift` falls (good) but `seat-only` **rises** (impossible from a copy-down).
A metric that moves the wrong way is reporting your own artifact back to you.

## Procedure

Step-by-step commands, the classification pass and the report shape:
`references/sweep-and-merge-procedure.md`.
