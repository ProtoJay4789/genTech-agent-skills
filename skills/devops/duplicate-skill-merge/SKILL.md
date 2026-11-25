---
name: duplicate-skill-merge
description: Use when two skills claim the same job and must merge.
version: 1.0.0
author: gentech-treasury
license: MIT
metadata:
  tags: [skills, consolidation, fleet, merge]
  hermes:
    tags: [skills, consolidation, fleet, merge]
    related_skills: [skill-library-maintenance, fleet-compatible-skills, fleet-tool-integrity]
---

# Merging duplicate skills without losing anything

## When to Use

- Several skills claim the same trigger ("unified LP umbrella", "key custody", "membership audit") and
  an agent loading all of them reads one procedure three slightly different ways.
- A skill shelf has grown until individual skills are expensive to load. **The signal is the SIZE
  DISTRIBUTION, not the count** — see *Measure the shelf before you merge* below.
- **Not** for merging a small correct skill into a big umbrella. That is how the shelf got here.

## The default is MERGE, not create — a standing preference, not a cleanup task

**Jordan's rule for this library:** *"by default look into merging relevant skills instead of creating so many
new ones — it'd be more helpful for you too, and it'd be less confusion for agents to load up skills."*

So the question before `skill_manage create` is never *"is this worth writing down?"* — it is **"which existing
skill should absorb this?"** Write a new skill ONLY when the answer is *none*, and that means the new thing is a
different CLASS of task with a different trigger, not a different incident, tool, or subsystem.

**The cheap test, in order:**

1. `skills_list` the category, then `skill_view` the two or three closest candidates. **Searching is cheaper than
a duplicate and it is the step that actually gets skipped.**
2. Ask *would ONE procedure serve both requests?* Yes → patch the survivor (a subsection, a pitfall, or a
   `references/<topic>.md` for depth). No → two skills, and say why in the description so the next reader sees
   the boundary.
3. **A skill that grew a sub-skill is the signal to fold it back in.** When a session adds a second near-name
   beside an existing one ("…-apply" next to "…-landing"), the pair is one skill wearing two names: merge into
   the broader title, keep the losing trigger as a heading inside it.
4. **Size is never the reason to split.** A skill at the write cap gets a `references/` extraction, not a
   sibling skill — a `SKILL.md` over the cap freezes on every seat and a sibling re-indexes the same triggers.

**And when you do merge, merge the SHAPE, not the prose.** Two skills covering one job usually differ in *when*
they apply, not in what they say: give the survivor one section per shape ("Shape A — …, Shape B — …") with a
one-line note saying which condition selects which. That preserves both triggers in one body, which is exactly
what a reader needs and what two separate files failed to give them.

## Measure the shelf before you merge — the count is usually not the problem

**Run all three numbers before proposing any consolidation, because two of them are routinely mistaken
for the third.** Measured on a 346-skill fleet shelf:

| number | measured | what it tells you |
|---|---|---|
| SKILL.md count | 346 (no duplicate names, 346 distinct bodies) | how many triggers exist |
| **index cost** — every name + description, paid every turn | **~52,400 chars** | usually *bounded and fine*; this is the number people fear, and it is not the bill |
| **size distribution** | **57 skills over 30 KB, together 45% of all bytes**; median 12.8 KB, largest 100.7 KB | **this is the bill** — a triggered skill loads WHOLE, so one 100 KB skill firing costs 100 KB of context for one question |

**So "the number is high" almost always means the TAIL, not the head count.** Report the tail explicitly
(count over a threshold, its share of total bytes, the median) or the consolidation gets aimed at the
wrong end of the distribution — merging ten 3 KB skills saves nothing and loses triggers.

**Parse the frontmatter before comparing descriptions.** A naive `^description:\\s*(.+)$` regex returns the
literal `>-` for every skill written as a YAML folded block, so a similarity pass then scores unrelated
skills at ratio `1.0`. Measured: a `SequenceMatcher` sweep reported **112 "near-duplicate" pairs, every
one at 1.0** — all artifacts of the folded scalar, not one real duplicate. Fold the block scalar (or
`yaml.safe_load` the header) first; only then does a similarity score mean anything.

**Merge on the JOB, never on the topic.** Two skills can share every keyword and answer different
questions — an umbrella doctrine skill and a single-surface monitoring skill read alike and are not one
procedure. **Topic overlap predicts nothing; ask "would ONE procedure serve both requests?"** If no, they
stay two skills and the growth is real work, not duplication. If yes, absorb per the Procedure below and
put the depth in `references/`, never in a longer `SKILL.md`.

### Generate candidates mechanically, judge them by hand

A token-overlap pass over **descriptions** (Jaccard on words of ≥4 letters, threshold ≈0.42) is a cheap,
repo-free candidate generator, and its ranking is informative in a way the raw score is not:

```python
words = lambda d: set(w for w in re.findall(r'[a-z]{4,}', d.lower()))
j = len(a & b) / len(a | b)          # run over folded descriptions, never raw frontmatter
```

- **The single highest pair is usually the real duplicate** — two files that are one skill under two names.
  That is the one to merge first, because it is also the one readers hit twice.
- **A CLUSTER at the same score is usually a family of siblings**, and a family is not a duplicate. Three
  CLI-delegation skills score alike because they do the same *shape* of job for three different tools;
  merging them would delete two valid triggers. Check a cluster as a family and merge none of it.
- **"Not named anywhere outside the library" is NOT evidence a skill is unused.** A recently written or
  recently promoted skill is unreferenced by definition, and pruning on that signal deletes the newest
  knowledge first. Reference count is a signal about age, not about value.
- **Report the index cost with the candidate list** (`sum(len(name)+len(description))`) so the reader can see
  what the merge actually buys: the per-turn bill is the index, while the per-shot bill is the size tail.

**Survey the owners before cutting.** On a multi-seat fleet each department's lane is its own measured
slice. Ask each owner for (a) the merges they would make, (b) bytes saved per merge, (c) what they refuse
to merge and why. A consolidation ordered from the centre lands as deletion; one proposed by the owner
lands as maintenance.

**Measure it with instruments, not adjectives.** The four measurements that decide a merge list — the
instrument-overlap test for job identity, the history share, the stale-procedure share, and which skill is
the clean template — are in `references/consolidation-audit.md`. Run them before proposing a cut: measured
on one lane, history was 2-7% of bytes while **stale procedure was 38-44%**, so a plan aimed at history
would have missed most of the weight.

## Why duplicates are worse than one wrong version

One wrong version is visibly wrong. **Three near-copies produce invisible disagreement** — the reader
believes there is a single procedure and never learns which variant is in force. For custody that is
fatal: *"a key is either handled or lost,"* and the agent must know which procedure applies.

## Procedure

1. **Measure before touching.** For every candidate record path, size, line count, and trigger. Rank by
   overlap, not by size.
2. **Confirm the targets are real copies, not symlinks.** If they are symlinks to CORE, editing them
   edits the fleet — stop and ask.
3. **Back up every directory first**, into one tarball, and print its size. A merge without a rollback is
   a one-way door.
4. **Diff the copies against each other AND against CORE** before merging. See *Rich copy wins* below.
5. **Pick the survivor** — the one whose trigger already covers the others' triggers.
6. **Absorb the losers' bodies verbatim** into `<survivor>/references/<skill-name>.md`. Verbatim, not
   summarised. Copy their whole supporting tree, not just `SKILL.md`.
7. **RENAME each absorbed `SKILL.md`** off that name (e.g. `SKILL.md` → `<skill-name>.md`). **A file named
   `SKILL.md` inside a `references/` tree is re-indexed as a live skill** and silently undoes the merge.
8. **Delete the absorbed directories** from the loader's view.
9. **Append a pointer block** to the survivor: absorbed → where the body now lives, and which absorbed
   skills must never be re-created.
10. **Repoint citations** that referenced absorbed names; then scan for dangling `references/` paths.
11. **Verify:** index loads, survivors enabled, absorbed names gone in the same table, `SKILL.md` count
    moved by exactly the expected amount, and **zero `SKILL.md` files inside any `references/` tree**.
12. **Promote to CORE**, then let the seats apply it themselves.

## Trap: reference trees, not just bodies

Preserving `SKILL.md` alone loses everything beside it. **A merge run on one seat promotes that seat's
view of a skill, not the fleet's** — the union of reference files across seats can be far larger. Measured
example: 31 reference files / 110 KB existed only on one seat after a "complete" merge of four skills.
**Merge each absorbed skill's whole directory, then diff the survivors across every seat.**

## Trap: rich copy wins, in both directions

**Diff before copying, never after.** A seat can be *ahead* of CORE — four sections of custody doctrine
(11 KB) existed only on a seat, and a blind "sync CORE down to the seat" would have deleted them. Check
whether one side is a strict superset (`comm -23` after sorting both files); if it is, promote the richer
copy up. If they genuinely diverge, merge by section and say so in the body.

## Trap: the seats hold independent copies

On this host each profile has its own full copy of the shelf — **no symlinks, no shared CORE**. A CORE
change does not propagate. Two consequences:

- Seat skill counts drift (measured across five trees on one day: 269–281).
- **A dispatch must tell each seat to diff first, copy second, back up before deleting.** Include the
  exact delete list. An omitted name leaves a duplicate trigger live — and the seat that notices is the
  one doing you a favour, not the one at fault.
- `rsync` may be absent; use `cp -a "<CORE>/<skill>/." "<seat>/<skill>/"` **after** proving the seat's
  copy is a subset.

## Verification tool

`skill_ref_audit.py` (stdlib only) checks dangling `references/` citations and the re-index trap:

```
python3 skill_ref_audit.py --root /opt/data/skills      # exit 0 clean, 1 findings, 2 bad root
python3 skill_ref_audit.py --root <tree> --json
```

Run it on CORE **and every seat** — counts differ per tree, and a single CORE fix cannot converge them.

## Reporting rules

- **Never publish "promoted to CORE" without reading it back from CORE.** "Created" is about where you
  wrote the file; "promoted" is about where someone else can read it. Those are different claims.
- **The correction belongs to the author of the claim.** When a dispatched seat finds a defect in the
  merge, record it in the handoff under the seat's name; do not quietly edit the finding away.
- **Expect a concurrent writer.** Another seat may promote files up mid-apply; a seat that sees CORE
  change should re-run, re-verify `diff -r` is empty, and re-freeze its fingerprint rather than ship a
  half-sync.
