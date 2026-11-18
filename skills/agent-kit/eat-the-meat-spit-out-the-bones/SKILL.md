---
name: eat-the-meat-spit-out-the-bones
description: "Use when processing an archive, backup or handed artifact."
---

# Eat the meat, spit out the bones

**Jordan's rule, 2026-11-02:** *"Whenever we have some type of archive or something like that, let's go
through it… we just wanna take the stuff we need and get rid of the stuff we don't, so that way we
always stay trim."*

**An archive is not a thing to keep. It's a thing to process.** Left unprocessed, it becomes weight that
every backup, every sync and every search has to carry — and it hides the things worth keeping inside
things that aren't.

---

## The rule in one line

**Nothing gets archived by default. Everything gets read once, kept if it earns it, and dropped if it
doesn't — with a written reason either way.**

---

## The procedure

### 1 · Name what it actually is

Before opening anything, answer in one sentence: **what is this, and why does it exist?**

- an old copy of something we still have? → **bones, almost certainly**
- a working directory that leaked into a notes tree? → **move, don't archive**
- the only surviving copy of work that died? → **meat, and it needs a decision**
- a daily report accumulating forever? → **meat in aggregate, bones individually**

**⚠️ "I don't know what this is" is itself a finding.** An archive nobody can describe is one nobody
will ever use.

### 2 · Measure before you judge

```
size, file count, age range, file types
duplicate-of-live check     ← is this a copy of something that still exists?
reference check             ← does anything actually read from here?
```

**⚠️ The duplicate check is the highest-value single test.** Today's example: a 624 MB "backup" sitting
inside the vault it was backing up — it was a copy of the live vault, three levels deep. **Bones.**

**And the reference check saves you from breaking things.** Today: eight cron scripts read a file from
a directory that looked like a dead archive. Deleting it would have killed four monitors. **It was meat
wearing bones' clothing.**

#### A recovery tree is not a superset — count FILES, and compare both directions

When the thing you are holding is a **recovery or pre-wipe snapshot**, the instinct is that it contains
everything and the live copy is a subset of it. The opposite happens routinely: the snapshot is the older
object with **more** files, because work continued after it was taken.

```
right: per-file comparison in BOTH directions against the live canonical copy
  file absent from the snapshot   -> the live copy is the only source; copy it INTO the merged tree
  file NEWER in the live copy     -> the live copy wins; the snapshot version is history
  file only in the snapshot       -> meat, and it needs a decision
wrong: "the snapshot has more files, so it is the master"
```

Measured: a recovered tree carried **521 files** against the live copy's **22** — and the 22 were newer on
five files and were the *only* home of two documents written after the wipe. Restoring the 521 as canonical
would have silently reverted a month of work, including the revisions that recorded the very decisions being
recovered. **File count is not authority; mtime plus absence is.**

- **Merge, do not pick a winner.** Copy the newer/unique side in, then re-read the merged result and confirm
the specific facts that differed (a referenced section, a value, a line count) now come from the right side.
- **Write the merge down** — one line naming the rule ("live copy wins where newer or unique") and where the
  pre-merge copies were. A merge nobody recorded is indistinguishable from a wrong restore next time.
- **A backup DIRECTORY is not a backup.** Count the files inside it before treating its existence as
  protection. A dated `backups/<name>/` tree holding **zero files** reads as coverage in every listing and
  guards nothing — the failure surfaces only on the day someone needs it.

### 3 · Separate meat from bones

**MEAT — keep, and keep *deliberately*:**
- the only copy of anything
- work someone will resume
- the reasoning behind a decision, even a killed one
- a working procedure that isn't written anywhere else
- **aggregate facts**: how bad a problem was, when it started, whether it's fixed

**BONES — drop, without ceremony:**
- copies of things that still exist
- generated output that can be regenerated
- daily reports that repeat the same three findings
- dependencies, build artifacts, caches
- **raw material whose only value was already extracted** into a note

### 4 · Extract the meat before you drop the bones

**This is the step everyone skips.** Do not delete an archive and call the content "handled" — read it
and pull out:

```
the decision it recorded     → one line in the right note
the number it measured       → the figure, not the 40,000-line report
the procedure it discovered  → a skill, if it's reusable
the thing that failed        → recorded, so it isn't rediscovered
```

**A 1.5 MB report whose only value is "one file had a hardcoded key on August 23" is 60 characters of
meat and 1.5 MB of bones.**

### 5 · Compress or remove — and pick by reversibility

```
redact then archive      if it contains anything sensitive
compress to one file     if the aggregate history has value
move out of the synced tree   if it's needed on disk but not needed everywhere
delete                   only when it is provably a duplicate, or regenerable
```

**⚠️ Never delete the last copy of anything, even bones.** "We can regenerate it" is a claim — verify it
before acting on it.

**Moving is not deleting — say which one you are doing, and mean it.** When the user says "move it off
and clean it up," the safe reading is **move only**: the content stays on disk, outside the transport
that was costing money or space, and nothing becomes unrecoverable. Reserve deletion for provable
duplicates. A move plus a symlink is reversible; a delete is not.

#### When you move a directory, symlink the old path back and re-run the consumers

**A path that looks like an archive can be load-bearing.** Before moving anything, grep every script
tree for the path (`grep -rl '<path>' */scripts scripts`). If anything references it, `mv` then
`symlink` the original location to the new one, then **run each consumer and check its exit code** —
not just that the file exists.

**⚠️ A symlink also stops the transport from carrying the bytes** (Obsidian Sync, Dropbox, git all skip
or minimize links), so it achieves the space win *and* keeps the readers working. Verify the target
still resolves and a representative file opens through the link.

#### A size audit must state whether it follows links

**After symlinking content out, a plain `os.walk` + `getsize` still counts the full target — because it
follows the link.** The "before" and "after" figures then show no saving and the audit looks wrong.
Count links as links:

```python
t += 64 if os.path.islink(fp) else os.path.getsize(fp)
```

State in the report which measure you used. **A size figure without its measurement method is
unfalsifiable** — the same tree can honestly be 887 MB or 130 MB depending on whether you meant "on
disk" or "carried by sync."

#### Verify the archive holds everything before deleting the originals

**Count matching entries, not total lines.** `tar tzf` lists the `.` directory entry as well, so an
archive of 44 files reports **45** — a naive equality check fails, or worse, a `>=` check passes and
you delete originals that were never archived.

```bash
tar tzf "$ARCHIVE" | grep -c '\.md$'   # count only real members
```

Then delete originals **only on an exact match**, and keep the guard: if the count is off, leave the
originals in place and report the mismatch rather than "fixing" the archive. A refusal to delete is
the correct outcome of a failed verification.

#### A bulk move can swallow the records that describe it

**Filing hundreds of artifacts by predicate will eventually move something irreplaceable that happens
to satisfy the predicate** — and the predicate testing correct in isolation does not prove the pass
honoured it. Measured: a sweep that filed resolved handoff notes into `_archive/` also moved the two
completions ledgers recording that work, because a ledger's own body contains words like `resolved`
and `archived`. Re-running the exclusion regex returned zero false positives and a reproduction of the
exact filter came back clean — **so the filter was right and the files still moved.** Design against
that, because you will not be able to explain it afterwards.

- **Exclude by an explicit RETAIN LIST of known-irreplaceable paths, not by a name pattern.** A pattern
  is a promise about spelling; a list is a promise about identity. Ledgers, manifests, registries and
  index files go on the list by name.
- **Print every path you are about to move BEFORE moving, and read the list.** A post-hoc "what did I
  move" is a repair, not a control.
- **After the pass, re-assert the retain list is intact** — file count, byte size, and the last line —
  rather than assuming the loop respected the exclusion.
- **To repair, look at `mtime` inside the destination for the last few minutes.** That finds what
  actually moved, and it is faster and more complete than re-deriving what should have.

### 6 · Write the receipt

One line, in the completions record:

```
what it was · how big · what you kept and why · what you dropped and why · where the keep went
```

**An archive processed without a receipt is an archive that will be re-examined from scratch next time.**

---

## The trim rule

**Staying trim isn't one big cleanup — it's refusing to let accumulation happen unexamined.**

- **Anything named `archive`, `backup`, `old`, `snapshot`, `dump`, `*-bak`, `.bak-*`** gets the
  procedure above, not a filing.
- **A backup inside the thing it backs up is always bones.**
- **A daily/hourly report generator needs a retention policy from day one** — keep the last N, archive
  the rest, and never let it quote what it's scanning for.
- **If an archive has been unopened for a year and nothing references it, it is bones** — but read it
  once before you say so. "Nobody used it" and "nothing useful was in it" are different claims.

## When the "archive" is something you were HANDED

The rule is not about folders. The same procedure runs whenever something arrives whole — a shared repo, a
long thread, a vendor's product page — and the question is what of it we keep. The phrase itself is the
trigger; treat it as the instruction.

**Change one thing: find the DESTINATION before you judge the SOURCE.** A dump has no consumer, so "keep"
means "keep for its own sake". A handed artifact usually has one, and the meat is defined by it.

- **Open the thing that would receive the lesson first** — the actual track file, curriculum chapter or
  spec, not a summary of it. The adjacency is a checkable fact about that file. Mapping a vendor's ideas
  onto the *vibe* of a subject produces plausible lessons that fit nothing.
- **Then judge each element by one test: does it map to a destination that exists?** What maps is meat;
  what merely impresses is bones. An idea can be excellent and still be bones for us.
- **The artifact itself is bones when you cannot run it.** Measure the prerequisites before proposing a
  hands-on exercise; if the hardware, account or runtime is missing, say so and demote it to a case study.
  **A teardown dressed up as a lab is caught in one interview question**; a case study labelled as one is
  unimpeachable.
- **Name both lists with the reason, in the same file.** The bones list is what stops the next reader
  re-importing the whole thing.
- **Rank the meat; do not hand over five equal lessons.** A flat list reads as a summary, a ranked one
  reads as judgement — say which single idea you would keep if you could keep only one.
- **Stop at the seam of ownership.** Extracting seeds for a curriculum someone else owns is the job;
  writing their lessons is not. Hand the seeds over and say plainly that you did not write them.

## Worked example — the two that paid off today

**`privacy-sweeps/` — 49 daily files, 127.7 MB.**
Meat: which file had a secret, when. Bones: 40,000 lines repeating across 50% duplicate lines — and,
critically, **the actual secret values, quoted in plaintext, in a synced folder.**
Result: redacted (value → `[REDACTED-SECRET]`, location kept) → 55.8 MB. Then archived the 44 older
files into 3 MB, kept 5 readable → 10.9 MB. **A 92% reduction, and a security hole closed, from one
pass.**

**`pre-wipe-fleet-snapshot-2026` — 624 MB, 35,817 files.**
Test: is it a copy of the live vault? **Yes — it was the live vault, pre-wipe, living inside itself.**
Bones, moved out of the synced tree to disk. **713 MB freed across the whole cleanup.**

**⚠️ And the one that looked like bones and wasn't:** `10-Labs/x402-gateway` — a service directory with
`node_modules` and logs, obviously not notes. **Eight scripts read from it.** Moved + symlinked, then
verified all four consumers still ran. **Check references before you act on an obvious conclusion.**
