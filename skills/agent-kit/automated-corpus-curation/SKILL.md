---
name: automated-corpus-curation
description: "Use when a shared list or corpus needs automated upkeep."
version: 1.0.0
author: Gentech
license: MIT
tags: [curation, maintenance, cron, shared-lists, vault, routing, overnight]
trigger: "When building or auditing an overnight/periodic job that keeps a corpus current — aging stale notes, consolidating folders, or routing findings into shared work lists — or when a shared list has grown unreadably large."
metadata:
  hermes:
    tags: [curation, maintenance, cron, shared-lists, vault, routing, overnight]
    related_skills: [cron-health-standard, claim-provenance]
related_skills:
  - ../cron-health-standard/SKILL.md   # quiet hours, one voice, delivery targets
  - ../../claim-provenance/SKILL.md    # every count in a sweep report is a claim
---

# Automated Corpus Curation

## When to Use

- A shared work list (queue, inbox, registry) has grown unreadably large, or items look open that are
  not work.
- You are building or auditing an overnight/periodic job that ages stale notes, consolidates folders,
  or reports what has gone quiet.
- You need to route a sweep's findings into the user's work lists instead of sending a report.
- A scheduled job must run inside quiet hours without waking anyone.

An agent-maintained corpus only grows. During the day every seat writes into it; nobody walks the
folders. Left alone, the result is two distinct diseases, and each needs its own fix:

- **rot** — items nobody re-decides, because no rule says how long a thing may sit;
- **noise** — new findings nobody files, or filed so badly the list stops being readable.

Automation fixes both. These are the rules that make the automation trustworthy.

---

## The rules

### 1. One writer per list; readers never write

A shared list is a service with one producer. Digests, briefs, personal-assistant jobs and reporting
agents **consume**. The moment a READER also appends its own output, the list becomes that reader's log.

Measured shape of the failure: a queue file reached 480 KB / 169 sections, of which **115 were one
agent's reports about its own runs** — and because every report carried unchecked checkboxes, every log
entry also read as **open work**. Cleaning the file without fixing the writer schedules a second cleanup.

### 2. Every automated row carries a STABLE ID, and the dedupe is PROVEN

Derive the id from the finding, never from position: `sha1(class|subject)[:12]`, not an index or a
running counter. **Before writing, read the ids already present and skip any that exist.**

> **Prove the dedupe by running the writer twice in a row: the second run must add zero.** An
> un-re-run dedupe is a hope, and the file looks correct either way.

#### The same rule applies to a HUMAN-WRITTEN corpus — and that is the case people forget

A prose list accumulates entries that have no identity at all. Nothing downstream can join to them:
not a build queue, not a repo, not a completion record — and not a later audit. Measured on a
long-running ideas file: **478 substantive entries, 4 referencing anything outside the file.** The
other 474 could not be traced to work, so "did we ever build this?" was unanswerable by search.

**Stamp the identity mechanically, in place, reversibly.** A stable id in an invisible marker keeps
the prose readable and the file greppable:

```markdown
## Multi-rail Agentic Treasury <!-- idea:IDEA-0045 -->
```

- **Seed the counter from the existing registry**, never from the file's order, so ids are never
  reused and a re-run is idempotent.
- **Emit an index** (`id → title → subject words → the entries that nest under it`) so the join is a
  query instead of a read-through.
- **Count the coverage and report it.** "61 sections stamped, 4 already carried an id" is a receipt;
  "ids added" is not. A scheme applied to 5% of the corpus looks identical to one applied to all of it.
- **Do not infer what belongs to what beyond real structure** (nesting, explicit links). Deciding that
  a paragraph describes an idea is judgement, and judgement does not belong in a stamping pass.

#### ⚠️ Keyword overlap is NOT a join key — record the link, never infer it

The instinct is to match an entry to its implementation by shared words. **It does not work, and it
fails confidently.** Measured: `shape_intelligence.py` and *"Yield-Farm Scenario Intelligence"* share
the word *intelligence*; `compound-extract-protocol.md` and *"auto-compound engine"* share
*compound*. Two runs of the same matcher on the same corpus gave **different verdicts** — and one of
them declared a fully-implemented component **plan-only** while its working scripts sat on disk.

**The fix inverts the design: the matcher proposes candidates; it never publishes a verdict.**

1. **An explicit field, written by whoever actually checked** — `built_as: <repo>`, `<path>`, or
   `<registry id>`. A human or an agent that looked says what it is.
2. **The auditor reports only PROVABLE drift** — "entry X claims `built_as: repo Y`, and repo Y is
   0 bytes" is a finding. "These two share a word" is not.
3. **Never let a similarity score close, merge, or reclassify anything.** Only mechanical facts may do
   that (an id exists, a checkbox is ticked, a file is absent).

**A bigger model does not fix this.** Six models were asked the same ambiguous question and split
**2-vs-4**, every one confident, none noticing the question had two halves. A larger model writes the
same coin-flip more persuasively. **Ambiguity is not a capability problem.**

### 3. Write into ONE fenced auto-section, seeded with the target's real row shape

Automation must never interleave with human rows — one marked section means the automated block can be
reviewed, diffed, or removed as a unit.

**Match the file's existing shape, including its scaffolding.** A markdown table needs its header row:
rows appended without one render as plain text, and the raw file looks completely fine, so the error
survives every read.

### 4. The registry of written ids must ACCUMULATE

A writer that persists only "what I added this run" can never detect that a row's subject has gone
away — so **nothing can ever be closed** and the list only grows. Persist the union of every id ever
written; drop an id only when its row is cleared.

### 5. Freshness policy lives in DATA, not in discipline

A rule held in an agent's habit dies with the session or the seat. Put it in a file the job reads every
run and the user can edit without touching code.

One policy file maps **class of information → how old it may get → what the look consists of.**
Classes are evaluated **in order, first match wins**, so exemptions come first — permanent records
(archives, backups, generated trees, completion records) must never be reported as overdue, and a
`permanent` file nested inside a stale-prone folder is the common false positive.

See `references/staleness-policy.md` for the working class table and precedence rules.

### 6. Automation PROPOSES; a human or the owning seat disposes

- **Move, never delete** — and write a **manifest** (`old → new`, plus every directory removed) into
  the directory the content landed in. A move without a manifest is indistinguishable from a loss.
- **Archive the closed; FLAG the open.** Ageing a live item into an archive is a disappearance dressed
  as tidiness. An item open past its window gets a line naming its owner and its age.
- **Automation does not adjudicate.** It identifies; the owning seat or the user decides. A tool that
  closes items on its own eventually closes one that mattered.

### 7. Three exits and no fourth

Route each finding into the list that OWNS it, and every row must be able to name how it leaves:

| list | holds | exit |
|---|---|---|
| the human's own list | only the human can act | he acts, or it moves to pending with a gate |
| build queue | we can act, ordered | shipped — **with proof** |
| pending | an EXTERNAL verdict is the gate | the verdict lands |
| completed | done | — |

An entry that cannot name its exit is not an entry. A row that is blocked states **its gate AND its
release condition** — "blocked" alone is a shrug the next reader cannot move.

**A cleared finding closes itself:** when a previously written id stops appearing in the sweep, mark the
row cleared in place and append a completion record whose *proof* says how it was determined to be gone.
That is the difference between a queue and archaeology.

### 8. Spread the budget, and keep ONE voice

The overnight sweep runs inside quiet hours as a **silent producer**: it writes a state file and
delivers nothing. One consumer at wake reads those state files and speaks once.

- **Cap the volume and rotate across targets** — taking the first N findings lets one class consume the
  whole night and starve every other list.
- **A finding is itself information with a shelf life.** After a window with no action, re-verdict it
  ("still true? still worth doing?") rather than re-reporting it nightly.

---

## Procedure

1. **Inventory before you write a rule.** Count files and last-touched per folder first; the policy is
   only meaningful against the shapes that actually exist. Do not invent classes for folders that hold
   nothing.
2. **Write the policy file** (rule 5). Include the exemptions first and say in the file itself that
   order matters.
3. **Build the sweep read-only**: classify every document, list past-TTL items per class, then the two
   structural findings — folders holding nothing (computed over the **subtree**) and one subject split
   across several homes.
4. **Attach the writer** (rules 1–4) and route by class to the owning list (rule 7).
5. **Schedule it inside the quiet window** with delivery suppressed (rule 8), and give the wake
   consumer the state file path.
6. **Verify** (below) — before the first report goes to a human.

## Verification checklist

1. **Run the writer twice** — second run adds zero.
2. **Diff the target lists** against pre-run backups: human rows must be byte-identical.
3. **Print the denominator** on every number: class counts and the scan root accompany any total.
4. **Read the report as a stranger**: a wall of individually-correct rows is a failed report. Cap what
   the human sees and let the lists carry the rest.
5. **Move a copy of anything you rewrite** to a dated backup first; a reversible change is the only
   kind automation may make.

## Pitfalls

- **A word inside prose is not a STATE.** A scanner that moves any line *mentioning* done / shipped /
  completed will file open plans as finished work — and prose is exactly where those words appear:
  *"What it would package (all pieces already exist)"*, *"Concrete first deliverable…"*, *"we just
  shipped the Algorand rail…"*. Measured: a keyword rule proposed **61** moves of which **8** were
  future work. **Only an explicit, positional marker counts** — a checkbox at the start of the line, a
  `status:` field — and never the same word appearing mid-sentence. Print the would-move list and read
  it before the first `--apply`; a cleaner that misclassifies is the very defect it was written to fix.
- **A status label will get promoted to a heading.** Corpora grow sections called `Completed`, `Ready
  to Test`, `Backlog` — and everything filed beneath them is stored under a *state*, not a subject, so
  finished work sits in a section that is neither counted as done nor ever removed. Measured: two such
  headings held **42** entries. **Flag status-shaped headings; do not rename them.** Renaming is
  judgement, and the entries still need a real home chosen by someone who knows what they are.
- **A substring path test matches the ROOT'S OWN NAME.** Guarding a walk with
  `if "/.obsidian" in root: continue` skipped an entire vault whose own path was `~/.obsidian-vault` —
  the sweep reported an empty corpus and looked successful. Compare path **components**
  (`set(relpath.split(os.sep)) & {'.obsidian', '.git'}`), never substrings.
- **A generated report is a LOG, not a work item.** Classify recurring-report titles (dated digests,
  "write-back", "activity log", "nightly", "check-in") out of the work population, or the sweep's own
  history becomes its largest finding class.
- **The same rule applies to a RETRIEVAL INDEX, and there the damage is arithmetic.** A growing log in a
  search corpus does not just add noise — it breaks the index's own statistics. Measured: the corpus median
  note was ~460 tokens and one completion log was **281,754**, roughly 600×. BM25's average-document-length
  term then makes every normal note look short, and a note that repeats a query word hundreds of times beats
  the note that answers the question. Excluding log-shaped notes (name hints like `completions`, `sweep-`,
  `-log`, `ledger`, `traffic`, `payments`; plus anything past a size ceiling) moved hit@10 from 73% to 77% —
  and **capping note length scored identically, because the giant notes ARE the logs.** Two "fixes" that
  produce the same number are one fix; ship one. **A record of finished work is reference material, not a
  retrieval target** — keep it on disk and greppable, out of the index.
- **Distinguish product from content before consolidating.** Folding a `*-travel` **skill/kit** folder
  into a personal `Travel/` folder breaks the kit. Consolidate the user's content; leave the product.
- **`deliver: local` silences FAILURES too.** Failure notices follow the delivery target, so quieting a
  job's success message also quiets its failure. Acceptable only if the wake consumer reads the job's
  own verdict **and its freshness** — an artifact older than the job's period means the job did not run,
  which no success-shaped artifact will tell you.
- **Make the quiet window half-open** (`[quiet_start, wake)`). The job firing at the wake time IS the
  wake job; counting it as a violation sends you to silence the one thing the user asked for.
- **When you edit a registered job, prove the edit survived a scheduler tick.** A scheduler that
  rewrites its registry from an in-memory copy will revert a hand-edit while it looks applied. Confirm a
  tick actually ran and the change is still there afterwards.
- **Empty is computed over the subtree.** A folder whose content lives one level down is not empty, and
  calling it empty produces a false finding that gets acted on.

## Support files

- `references/staleness-policy.md` — the working class table, precedence, and the four-list routing map.
