---
name: record-ledger-integrity
description: "Use when a script sweeps or renumbers records in a list."
version: 1.0.0
tags: [ledger, registry, dedupe, ids, lists, sweep, data-loss]
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [ledger, registry, dedupe, ids, lists, sweep, data-loss]
    related_skills: [build-queue-maintenance, destructive-write-guards, guard-verification, falsifiable-tests]
---

# Record Ledger Integrity

## When to Use

Load this when you are writing, editing, or auditing a script that:

- **sweeps** finished rows out of a list into a registry, archive, or completed pile;
- **renumbers** rows (positions 1..N recomputed on every change);
- **dedupes** records on an id;

or when a ledger's count looks right but you suspect a record went missing, or before hand-editing a
ledger file with a one-off snippet.

A ledger is any list whose rows are **moved between states by a program**: a build queue whose finished
rows leave for a completion registry, a task list that renumbers nightly, an inbox that archives what it
acks. These systems fail in a specific, quiet way — **the sweeper reports success, every count reads
correct, and a record is simply gone.** Nothing looks broken, because the only thing wrong is an item the
reader never sees again.

The failure modes below were each measured on a live four-list ledger (build queue / orchestrator list /
pending / completion registry) swept by a nightly steward.

## Rule 1 — Identity comes from CONTENT, never from the row's position

If the same process **renumbers** rows, then a visible number is *by design* re-used. It is a position,
not an identity, and anything derived from it inherits that instability.

Measured: the sweep wrote a registry entry with id `buil:14`. An earlier completion had also been position
14, so the registry's dedupe saw the id as already present and **skipped the new entry** — after the row
had already been deleted from the live list. The queue count was right; the registry was silently one item
short, permanently.

```python
# WRONG — the row's number is today's position, reused after every renumber
dedup_note = {"id": f"{prefix}:{num}", ...}

# RIGHT — content hash; stable across every renumber
cid = hashlib.sha1(f"{title}|{source}".encode()).hexdigest()[:8]
note = {"id": f"{prefix}:{cid}", "was_position": num, ...}   # keep the number as provenance only
```

- The same rule covers **dedupe keys, archive filenames, and any anchor built from a row index.**
- Assert uniqueness before writing (`assert len(hits) == 1`) when you must match a row at all.
- **Prefer matching by content** (`"fx-tracker" in name`) over matching by number, always.

## Rule 2 — A sweeper must reconcile COUNTS on both sides of the move

A move that drops a record is invisible unless the mover compares what left against what arrived.

```python
moved = sweep(rows)                 # rows removed from the live list
delta = len(moved)                  # what SHOULD have been added
assert ledger_growth == delta, f"moved {delta}, recorded {ledger_growth} — a record was dropped"
```

Assert it **after every run**, not once at build time. A dedupe that silently skips is exactly the code
path that makes "the sweep succeeded" true and "the record survived" false.

## Rule 3 — When you find a position-derived key, backfill what it dropped AND re-key the legacy rows

Fixing the writer does not recover what it already swallowed, and it leaves legacy collision-prone ids in
place. Do all three:

1. **Backfill** the dropped entries — their text nearly always survives somewhere else (an activity log,
a completions file, a message record). Reconstruct from that, never from memory.
2. **Re-key every legacy entry** to a content hash, keeping the old number in a `was_position` field so
the change stays traceable.
3. **Update the ledger's own stated schema** if it documents the key — a rule that says "id = the row
number" will teach the next writer the same bug.

## Rule 4 — Falsify the fix with the exact collision, then clean up

A fix proven by reading the patch is not proven.

1. Insert a **throwaway row carrying a number that was already used**, marked done.
2. Run the **real** sweep entry point.
3. Assert the new entry **lands** (count +1) — this is the case that used to vanish.
4. Remove the probe and assert the ledger returns to its prior count.

Also re-prove that the guard still bites on a genuinely stranded record, or the fix may have been
achieved by making the check toothless.

## Rule 5 — Editing the ledger file itself: never write a path and read it in one expression

`open(p, "w")` **truncates at open**, so a filter-in-place idiom reads the file it has already emptied.
The write lands as an empty string — total, silent data loss with exit 0 and no exception.

```python
# WRONG — "w" truncates before the generator runs; the reader gets an empty file
open(p, "w").write("\n".join(l for l in open(p).read().split("\n") if keep(l)))

# RIGHT — read, decide in memory, then write
lines = open(p).read().split("\n")
open(p, "w").write("\n".join(l for l in lines if keep(l)))
```

Measured: a one-off cleanup snippet reduced a 22 KB list to **0 bytes**. This form appears most often in
*throwaway snippets* — precisely the code no guard is watching. When the new content must be derived from
the original, write to a temp path and `os.replace()`.

**Corollary — make the backup NON-OVERWRITING, and it becomes the recovery.** The run that destroyed the
file had already produced dated `.pre-<tool>-<date>.bak` copies, and a helper that refuses to overwrite an
existing copy (`if not os.path.exists(b): shutil.copy2(p, b)`) meant the good copy from earlier survived.
An unconditional `copy2` would have faithfully overwritten the good backup with the empty file. **Take a
dated backup before every destructive edit, and guard the backup itself.**

## Rule 6 — An automated sweeper must be idempotent, and you prove it by running it repeatedly

Run it three times in a row and assert the ledger is unchanged after the first. A sweeper that appends its
own header or summary line each run will quietly accumulate contradictions (measured: a list collected five
mutually contradictory count headers because the replace pattern required the line to end at a marker its
own output continued past). **A count line's replace pattern must match the line the writer actually
emits** — test it by running the writer twice.

**A cumulative counter must be RECOMPUTED from a dated ledger, never incremented in place.** Adding today's
count to the stored total on every invocation multiplies the total by the number of runs: one register read
`2` after a single pass, then `4`, then `6`, with the corpus unchanged. Store per-day counts
(`{"<date>": {"<key>": n}}`) and derive the total and `first_seen` from that file on each run — then N runs on
one day give the same number, and a genuinely new day appears as a new ROW rather than a bigger number.

**Never fold an unclassifiable record into a category.** A register that buckets what it cannot read under
`UNCLASSIFIED` reports a mass of new findings that are actually an absence of data — one pass produced
"36 new failure modes" from records that carried no text to classify at all. Detect the unreadable case,
print `UNKNOWN — N record(s) carry nothing to classify`, and exit non-zero; **a bucket that must always be
zero is easier to trust than a count that hides the absence.**

### Writing into a file a HUMAN owns: take a bounded, marked section — never append

A recurring job that routes findings into the user's own list (their queue, their to-do note, their
watchlist) is not a ledger writer, it is a **guest in someone else's document**. Appending there fails
twice: the file grows by one copy per run, and a human scrolling their own list cannot tell which lines
the machine wrote.

- **Own exactly one section, delimited by a marker heading, and REWRITE it wholesale each run.** Replace
  from the marker up to the next `## ` heading; leave every other byte alone. The section is bounded, so
  it shrinks when items are resolved instead of accumulating forever.
- **Stamp it** (`_Last run <ISO> — replaced, not appended._`) so a reader can tell freshness from content.
- **Write via temp file + `os.replace()`**, and return quietly if the file does not exist — never invent
  a queue because its path was wrong.
- **Prove idempotency with a marker count across two runs, and prove no collateral damage with a heading
  diff**: `diff <(grep '^## ' before) <(grep '^## ' after)` must show **only** the new section. A count
alone tells you the job ran; the diff tells you it did not eat the user's prose.
- **Only route what genuinely needs the human** — a signature, a legal agreement, a write under their
  identity. Advice the agent can act on stays in the report; a queue padded with agent work is a queue
  the human stops reading.

## Rule 7 — The sweep moves what is MARKED done; it never decides a row is dead

A script can move a completed row and keep a number honest. It cannot judge that an open item is obsolete
— that is a triage decision with a human in it. Keep the two separate, and state the limit plainly rather
than letting a green sweep imply the list is curated.

**And then define what counts as a MARK, or the rule above is unenforceable.** "Marked done" is not "the
row mentions the word done" — free prose describes future work using exactly the same vocabulary as a
finished item, so a word-anywhere matcher sweeps open plans into the completed pile.

- **Key on a STRUCTURAL marker at a fixed position** — a checkbox state at the start of the line, a
  field value, a header token. Never a keyword anywhere in the row's text.
- **Census the signal classes before applying anything.** Count rows whose marker matches, rows whose
  marker negates, and rows that merely *mention* the vocabulary. If the third class is non-zero the
  matcher is wrong, not the data:

  ```
  bullets starting [x] or done-mark    53   reliable — safe to move
  bullets starting [ ]                 24   reliable — open, leave
  bullets mentioning done/shipped       8   PROSE — deliberately NOT moved
  ```

  Report that third line in the output even though it does nothing, so the reader sees the matcher's
  blind spot instead of trusting its silence.
- **Print what WOULD move, then read a sample of it, before the `--apply` run.** A dry run that only
  prints a count hides exactly this defect: the count looked plausible (`61`), and reading ten of the
  sixty-one showed three were descriptions of unbuilt work. **The count is not the evidence; the sample is.**
- **The same trap sinks a dedupe key built from leading prose.** Keying on the first N words of free text
  collapses unrelated rows that share an opening phrase (several different tasks all reading "Add to
  build queue as #…"), and reports a duplicate that does not exist. **Key on the identity field, and print
  the colliding PAIRS before believing the duplicate count** — a false duplicate, acted on, is data loss
  with a tidy explanation attached.

## Rule 8 — Age and status counters must key on a field the edit cannot reset

Most overdue/backlog/staleness fields are computed from **mtime** — the one field every write touches.
Measured: a note-backlog checker aged its records by `st_mtime`, so adding the missing block to a note that
had been overdue for two days made it **vanish from the report**. The fix erased its own finding; the same
reset would have hidden an unfixed record behind any typo fix or automated sweep.

- **Derive age from something immutable in the record** — a date in the filename, a `created_at` field, an
  opened-at stamp. Never mtime, never "last modified".
- **A counter that can be silenced by touching the artifact is not measuring the artifact.** Before trusting
  a backlog number, ask what write would make it go down while the defect stays.
- **Compute both clocks once and report the delta.** Measured over 54 records: 50 overdue by the filename
  clock vs 49 by mtime — 2 were hidden purely because they had been edited recently. Pick the honest clock
  deliberately and leave a comment saying why, or the next maintainer will "fix" it back.

## Rule 9 — Merging two ledgers is a SCHEMA change: id TYPE is part of the contract

When the same work has drifted into two lists (a prose/table list and a machine JSON), the fix is to merge — but the
merge changes the shape of `id`, and every consumer that assumed a number breaks.

**Measured, one merge, three instruments dead from the same assumption** (ids had been integers; the merged list
carried `rev-1`, `rev-2`, …):

- a digest's sort → `TypeError: '<' not supported between instances of 'str' and 'int'`
- an audit's sort → the same crash
- a reconciler's `%d` formatting → `TypeError: %d format: a real number is required, not str`

Each failed in a way that looked like a **data** problem ("script failed", "queue is empty"), not a type problem, so
the natural next move is to debug the data — which is wrong and endless.

**Procedure, before the merge lands:**

1. **Grep every consumer for the id's numeric uses**: `sort(`, `sorted(`, `%d`, `int(`, arithmetic, zero-padding.
   **Then count readers by RUNNING them, not by grepping** — the first grep found three, and the merge
   surfaced five. A reader can sit behind a shared helper (a `_k()` sort key, a formatting util, a
   wrapper script), so the grep sees the helper and misses every caller of it. `sort(` in the util does
   not name the id; the id flows in from a file.
2. **Make ordering total and type-agnostic** — sort on `(bucket, numeric_part_or_huge, raw_text)`, never on the raw id.
3. **Format with `%s` / `str()`**, and match ids with `re.escape(str(id))`, never `%d`.
4. **Run every consumer after the merge** — a clean grep proves a string changed, not that a reader works. Each
   instrument's success is its own output, not the absence of an exception elsewhere.

**Two rules for the merge itself:**

- **Merge INTO one file, then move.** A relocation that carries two contradictory lists just changes their address;
  the divergence survives the move.
- **Do not delete the row that covered the same work under a second name** — mark it `superseded_by: <new-id>` and say
  why. Deleting it loses the history; leaving it live double-counts the queue. A superseded row is the only honest
  third option.

**A ledger whose numbers move is not the same as a ledger that is current.** After merging, re-run the truth audit
and quote the new totals — a count that changed because the corpus changed must never be presented as work that got
done.

## Rule 10 — Two counters that read correct while being wrong: the DENOMINATOR and the STATUS

Both were measured on the same night, on the two instruments that answer *"what is still owed?"* and
*"what is done?"*. Each returned a number that was arithmetically right and semantically false.

### The denominator must exclude lanes that are RECORDS, not requests

A lane inside a request tree is not automatically a lane of requests. One scanner counted every `*.md` in
the handoff tree, including a `completions-archive/` lane of dated completion records — **14 files that
can never carry an acknowledgement, inflating an "unanswered" count of 31 to 44.** Those files could not be
fixed, either: closing them would mean writing a closure block into an archive, which is a forged receipt.

- **Detect the exclusion by NAME PATTERN, not a hardcoded list.** A literal list of exceptions is what
  creates the *next* blind spot the moment someone adds a lane — the same scanner had already spent days
  refusing to recognise the closure heading its own seats had started using. Match the shape
  (`^_`, `*archive`, `*log`) so a new archive lane can never re-enter the denominator.
- **Every exclusion you add is a claim about a lane's semantics — say it in the code**, so the next reader
  can disagree with the reason rather than just the regex.
- **Re-run the instrument after changing its denominator and quote both numbers** (44 → 31). A denominator
  change that is not reported reads as work disappearing.

### A status value is an ASSERTION; count rows that carry proof

Measured on a 119-row queue: **57 rows closed, 44 of them in a done status, and only 12 carrying any
evidence field** — and a cross-check against the 359-entry completion registry matched **zero** of the 32
unproven rows, because they predate the harvest entirely. "57 closed" was a count of status flips.

```python
DONE = {"shipped", "completed", "closed"}
evid = lambda r: bool((r.get("evidence") or r.get("proof") or "").strip())
print(len([r for r in rows if r.get("status") in DONE]), sum(1 for r in rows if evid(r)))
```

- **Report BOTH numbers, and separate decisions from shipments.** A `dropped`/`rejected`/`superseded` row
  owes a *reason*, not a proof-of-work token; mixing them into one "unproven" count overstates the problem.
- **Cross-check a second source before drawing a conclusion from a zero.** An unmatched row is not
  automatically fake work — it may simply predate the convention that records proof. Say *"nobody can check
  this"*, not *"this did not happen"*; the first is a finding, the second is an accusation you cannot back.
- **A closed item nobody can check is indistinguishable from one that was quietly abandoned.** That is the
  argument for a completion contract on the row, not for a longer narrative in it.

## Pitfalls

- **A guard that enumerates live records against a config/registry must read the SAME COMPOSED source the
  implementation reads.** If the code merges a built-in table with an overlay file and the guard checks only
  the built-in layer, every overlay-supplied record is reported broken — a false red on correct data, which
  is what gets a guard deleted. Check the composed result (`load_shapes()`), not one layer (`SHAPES`).
- **A guard that hardcodes today's list of known-uncovered records expires the moment data is added.**
  Assert the per-record property (does this resolve?) and drive the uncovered case with a **synthetic**
  record, so adding real data can never turn the guard red.
- **"The sweep succeeded" and "the record survived" are different claims.** Verify the second by counting,
  never by reading the first.
- **A count that goes DOWN right after you added something, or "0 changes" right after an edit, means
  re-read the artifact** — do not trust the summary.

## Verification checklist

- [ ] Every stored key is derived from content, with the observed position kept only as provenance.
- [ ] The sweep reconciles moved-count against recorded-count on every run.
- [ ] Legacy position-derived keys are re-keyed and any dropped records backfilled from a real source.
- [ ] The fix was falsified with a re-used position (probe landed, then cleaned up) — not merely read.
- [ ] The ledger file was edited read-then-write, never write-and-read in one expression.
- [ ] A dated, non-overwriting backup exists from before the last destructive edit.
- [ ] The sweeper is idempotent across three consecutive runs.
