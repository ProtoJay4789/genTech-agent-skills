# Consolidating a vault tree

The procedure for repairing a brain that has accumulated duplicate folders, orphan rooms and split
copies — and the failure modes that make a naive "merge the duplicates" destroy data.

Use when: two folders share a name, a folder has no reader, notes for one subject live in two places,
or a seat reports that it cannot find something that clearly exists.

---

## Order: audit → triage → back up → merge → redirect → verify with a reader

Never reorder this. Each step exists because skipping it produced a wrong result.

---

## 1 · Audit — and anchor the path match

```bash
python3 /opt/data/scripts/audit-folders.py           # report
python3 /opt/data/scripts/audit-folders.py --json
```

It checks four failure classes, each of which has cost data:

- two live folders whose names normalise to the same thing (`01-Travel` / `Travel`)
- a folder no seat's code references (anchored match)
- a folder holding only a redirect or nothing
- a redirect pointing at a path that does not exist

### ⚠️ A path is a SEGMENT, not a substring

The first version of this audit searched for plain substrings, so `HQ/` also matched inside `00-HQ/`. The
two folders scored **identically**, and five orphan folders looked wired. Anchored properly they separate
cleanly. Every folder map produced before this fix double-counts, and the error is invisible because the
numbers stay plausible.

```python
pat = rf"(^|[^0-9A-Za-z_-]){re.escape(folder)}/"     # correct
pat = folder + "/"                                   # wrong: matches inside a longer name
```

The same rule applies to any grep over seat code: a bare `grep -l "EDU/"` matches `EDU/` inside a
longer path in another department.

### The audit cannot see usage, only references

A folder referenced by a script is wired. A folder a seat reads ad hoc is invisible. Report **"no code
reference"**, never **"nobody uses it"** — those are different claims and only one was measured.

---

## 2 · Triage a duplicate-name pair — reader first, content second, NEVER the name

**The folder named after the subject is not automatically the live one.** Resolve the consumers, then
compare what is inside each copy.

```bash
grep -rnE "(^|[^0-9A-Za-z_-])(01-)?Travel/" /opt/data/profiles/*/scripts /opt/data/scripts
```

Three questions, in this order:

1. **Which path do live readers resolve?** That is the canonical one — regardless of which holds the
   better data.
2. **Which copy is newer by CONTENT?** Compare field by field, not mtime and not the folder name.
3. **Does either contain something the other lacks?** If yes, it is a merge, not a copy.

Measured the hard way: every reader had been repointed to the canonical folder, and the **newest** data
was sitting in the folder they were pointed away from. Canonical path and newest content were in
different folders — so "use the canonical one" and "use the newest one" gave opposite answers, and either
chosen blindly loses something.

**A collision of identical digests is not a conflict.** `md5sum` both sides first; byte-identical copies
are duplicates to drop, not decisions to make.

**A strict superset is not a conflict either.** If copy B contains copy A verbatim plus an appended
section (a signed agreement, a receipt), retire A. Do not rewrite B from A, and do not keep both.

---

## 3 · Back up outside the vault, before the first move

```bash
mkdir -p /opt/data/backups/<change>-$(date +%Y%m%d-%H%M%S)
cp -r <every folder involved> "$_"
```

Outside the vault, and named for the change. A backup beside the thing it backs up is itself an artifact
readers will discover.

---

## 4 · Merge field by field, and prove no loss by KEY SET

For a JSON/record file the merge is per key, not per file:

```python
merged = dict(newer)
for k in older:                 # carry anything only the older copy had
    merged.setdefault(k, older[k])
```

Then verify with a set comparison against both inputs, not with a parse:

```python
lost = [k for k in older if k not in merged]
```

Measured shape: the newer copy had 36 keys, the merge produced 37, and zero were lost — the extra key
came from the older side. **"It parses" proves nothing about what is gone.**

For prose, append the later section rather than rewriting the file: a merge that rewrites a note another
seat authored produces a third version nobody agreed to.

**Carry the merge note inside the artifact** — one line naming which copy won and the conflict rule — so
the next reader is not asked to re-derive it.

---

## 5 · Retire with a redirect, never a delete

An empty shell with a signpost costs nothing. A path that 404s costs a reader, silently, on the next run
of the next job.

```markdown
# <folder> — moved <what changed>

**This folder is a redirect. The canonical folder is `<path>/`.**

Everything here was moved without loss: …
**Do not add notes here.** Readers resolve `<path>/` — see `<consumer>`.

Backup of the pre-change state: `/opt/data/backups/<change>-<stamp>/`
```

### ⚠️ Name it so it actually travels

**A dot-prefixed marker (`.redirect.md`) is excluded from vault sync** — the file that explains the move
to every other host is exactly the one that never arrives. On any other machine the folder then looks
live and empty, and a writer files into it.

Use a **visible** name (`_MOVED.md`, `MOVED-<date>.md`, `README.md`), and check that no sync exclusion
also covers the underscore prefix.

---

## 6 · Verify with the CONSUMER, not the diff

A file that parses is not a file that works. Load the actual reader and prove it resolves:

```python
# import the engine and print the constant it resolves + whether the path exists
print(m.DATA_DIR, m.DATA_DIR.exists())
```

Then, in order:

1. every file in the backup has a home in the canonical tree (walk both, diff the name sets)
2. the merged artifact parses and its key count is ≥ the larger input
3. the real consumer loads and reports the canonical path

---

## 7 · Stop and ask on live records

Merging is mechanical on prose and dangerous on **live obligations** — bookings, credits, balances,
schedule entries. A wrong merge on a booking record strands a credit, and no later audit will find it
because both files will look complete.

Rule: a folder holding live obligations merges **item by item with the owner's word**, not in a batch.

---

## 8 · An orphan folder is a DECISION, not a chore

A folder no code references needs one of two answers, and the owner picks:

- **Rename it to what it is.** Cheap, truthful, reversible. A folder called after a department it does not
  contain misleads every later audit.
- **Make it real.** That requires a **writer** and a **schedule**. A folder with neither fills with drafts
  that never ship — which is what a `drafts/` directory of unshipped work is evidence of.

**A new top-level folder is a decision.** Before creating one, name the reader that will resolve it. If no
script or job will ever point at it, it is a draft, not a folder.

### A folder full of files can still be EMPTY

**Count files that match what the folder's NAME promises, not files.** Measured: a folder named for a
content department held 11 files and zero notes — HTML portfolios and frontend prototypes, untouched for
weeks. Every "11 files" count made it look active while the department it named had never had a writer.
The reverse bites too: a folder with two notes that a nightly job actually reads is more real than one
holding eighty files nothing points at.

### If you choose "make it real", the README is the deliverable

Creating the lane does not create the behaviour, so write that difference down where the next reader will
hit it. The README states:

- **what belongs** — the four or five artifact types, each with a one-line purpose
- **what does NOT belong** — the adjacent work that will otherwise flood in (drafts, ideas, prototypes)
- **the first three things to write here** — concrete filenames, because an empty lane with a good name is
  still an empty lane
- **the honest writer count** — if no cron job and no seat is pointed at it yet, say **zero**. A lane that
  reads as live while nothing writes it is the `drafts/` trap with better branding, and the next audit can
  only report "no code reference".

---

## 9 · Before RENAMING a live folder: is the name wrong, or the contents?

**A department dissolving renames a LANE, not a path.** They are different changes with different risk, and
confusing them offers a cheap rename as a solution to a custody problem.

Measure two numbers before agreeing to anything:

1. **What is actually inside, by subfolder and file count.** Measured: a folder named after a build department
   held 2,181 files — **1,710 in the fleet's shared skills tree** and **104 in a live production service** —
   and **not one curriculum, lesson, or learner.** Renaming it after the successor department would have
   transferred the skill registry and the payment server to a seat whose remit is teaching.
2. **How many live files resolve that path, with an ANCHORED match** (§1). Measured: **73 files**, one
   subfolder alone named in 47. A rename is that many edits, and **every miss fails silently — a missing path
   reads as an empty result**, which is the defect class this whole reference exists to prevent.

Then separate the two claims out loud, because the human usually believes he is making one:

- *"The lane belongs to the successor"* — true, and it is a routing rule: their seat owns the FUNCTION
  wherever the work happens.
- *"This folder's contents are theirs"* — a separate claim, and usually false for anything load-bearing.

**Custody is ASSIGNED by asking the claimants, never inferred from a name.** Send the ownership question to
every seat, with the measured file counts, and accept three answers: *mine* (they take it and keep it tidy),
*not mine* (they decline, which is the answer that matters most), and *none of it is mine* — which is the
proof that the rename was never about contents. Only move what a seat actually claimed; the unclaimed
remainder stays with whoever is present. A handoff that reassigns work without asking is how a fleet stops
trusting its own routing.

**Keep the path, name the custodian.** One line in the routing map beats a refactor: *the folder is a shared
workshop, these are its custodians, the lane lives with the successor.* The new tenant does not need the old
folder to own the function.
