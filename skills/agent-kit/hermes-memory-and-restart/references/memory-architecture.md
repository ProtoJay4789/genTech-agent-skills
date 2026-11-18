# Memory architecture — runtime pointers, vault library

## The shape this is for

Two layers, and the split is the whole point:

1. **Runtime memory** (`MEMORY.md` / `USER.md`) — a small, always-injected block. It is *not* the knowledge;
   it is what applies to every single session: who the user is, standing conventions, and **pointers to where
   the durable material lives**.
2. **Vault memory** — durable, inspectable, portable markdown the user owns: decisions, findings, receipts,
   procedures that only matter for one kind of task (those belong in **skills**, not memory).

**Why the current model fills up:** every fact that is useful *sometimes* gets written to the layer that loads
*always*. Nothing decays, so the file only grows until it hits the ceiling, and the instrument's whole job
becomes deciding which true fact to delete.

## Measure YOUR OWN recall before evaluating any memory product

The defect is almost always the **corpus**, not the retriever.

Measured on a live fleet: the provider's `root` setting fed **both** the read path (`_load()`) and the write
path (`write_note()`). Every seat's root pointed at its own small mirror directory, so "BM25 over the vault"
searched **3 / 7 / 1 / 4 files** against a **6,067-note** brain. The single-file seat had never once returned
a note. Scored on a 14-case suite: **0/14**.

Give the provider **two settings for two questions** — *what may I read* and *where may I write*:

- `corpus_root` (read), defaulting to `root` when empty so existing behaviour is preserved exactly.
- `root` stays per-seat: new notes land in that seat's own domain, not at the vault top level.
- An env override (`VAULT_MEMORY_CORPUS`) for tests.
- A missing corpus path **warns and falls back to `root`** — never silently collapse recall to zero.

Same suite after: **11/14 = 79%**. Cost of a 6,000-note corpus: **6.2 s cold read, 0.86 s warm search** —
acceptable, but a cold first search on turn one now costs seconds where it cost milliseconds.

**Scope the corpus deliberately.** Excluding `skills-*` (already loaded by description), logs, and `_archive`
is worth testing but measured **no score change** (79% either way) on one suite — measure it, do not assume it
helps. Fewer files is a speed win, not automatically an accuracy one.

## How to score recall — expected path in top-K

1. Each case declares **the note that holds the answer**, taken from the vault, not invented.
2. Hit only if that path appears in the top-K. *"Related" is how a memory system gets credit for an answer it
did not retrieve.*
3. **Absence of data is not a score of zero.** If the retriever cannot be constructed, report
   `COULD NOT MEASURE` — a broken instrument that prints `0%` is indistinguishable from terrible recall.
4. **Never publish a percentage off a handful of cases without saying so.** A 14-case suite has a wide error
   bar; "79%" is a direction, not a spec.
5. Drive the **real provider's own `search()`**, not a reimplementation and not the agent's tool API
   (`hermes_tools` is a tool surface, not an importable library — a cron script cannot import it).

## Three classes of miss, three different fixes

| class | symptom | fix |
|---|---|---|
| **vocabulary gap** | `hand` never matches `handoff` — the tokeniser truncates but does not stem | query phrasing (`handoff`), not code |
| **ranking** | a longer, older note repeating the query words outranks the note written today; the scorer indexes body tokens and ignores the **filename** entirely | title weighting: filename tokens boosted per overlap lifted 79% → **93%**; recency alone 86%; both 93% |
| **query formulation** | an intent-phrased question ("what did we decide about X going forward") carries no distinctive term | the agent searches with vocabulary, not intent |

**State the bias on a title-weight result:** test cases written from notes with descriptive filenames flatter
a filename boost. A ranking change applies to every turn for every seat — ship it behind a blind case set, not
after one favourable suite.

## The promotion signal must come from BEHAVIOUR, not presence

A memory line persists until someone deletes it, so "seen on N runs" measures **persistence**, and a rule built
on it fires on everything. Measured: **77 of 77** observations reached exactly N runs, and the "promotion
list" was the memory file re-printed.

- **Promote when a line was removed and then RE-OBSERVED** — the only local evidence that a fact was needed
  back. Track an absence counter and increment a gap counter on return.
- **Retire on non-use**, as a proposal with a last-seen run, never a deletion.
- **Classification decides what can be promoted at all:** a *standing rule* is obeyed, not recalled, so its
  evidence is "I got it wrong once"; an *environment fact* rots fastest and belongs in a generated command
  card, not in always-loaded text.
- **Keep the consolidation pass deterministic.** A model deciding which of its own lines become policy cannot
  be audited (re-running it gives a different answer), drifts week to week, and costs inference nightly for a
  job whose value is that it is boring. Two counters are enough.

## The metric is injected BYTES, not note count

Trimming **archives into** the vault, so trimming **grows** the note count (observed climbing as three seats
trimmed). Note count therefore rewards the wrong behaviour. Report active bytes, and the vault total beside it
(§ spilling in the parent skill: memory down + vault up = moved; memory down + vault flat = lost).

## Decision record: vendors evaluated

Scored on one question — *does it implement the split above for THIS fleet, without adding a second place to
look?* Popularity was not the criterion.

| Candidate | Status |
|---|---|
| **`itechmeat/open-second-brain`** | **Gated and rejected as a replacement.** It *does* register on an older engine (the version-gap fear was wrong), but its recall is **case-insensitive substring on page titles** — weaker than body BM25 — its per-turn context hook returned an **empty preferences file**, and its `health()` reports `ok: true` with its runtime absent. Take the deterministic consolidation idea; not the runtime, not the 124-tool MCP surface. |
| `eugeniughelbur/obsidian-second-brain` | Very popular, markdown-in-vault; agent adapters are Claude Code / Codex / Cursor class, **no Hermes provider** — we would be the integration project. |
| `breferrari/obsidian-mind` | Wants to own the vault's structure, which fights a curated vault; no Hermes provider. |
| `mem0ai/mem0` | A memory **service** with its own backend — the opposite of the ask: a second place to look. |
| `Gentleman-Programming/engram` | SQLite-first: the brain becomes a database rather than readable markdown. |

### The benchmark that settles the category

A plain **filesystem + grep** scored **74.0%** on LoCoMo (the standard long-conversation retrieval benchmark) versus
**68.5%** for the best-performing specialised memory product's own reported number. The authors' conclusion:
specialised memory tools lose to letting the agent iteratively search its own files, because file tools are
heavily represented in model training data.

**So a memory product must beat a filesystem to be worth adopting, and that is a high bar.** Stop shopping for a
store; the gap is *what gets written down and in what form*.

## Gates that must be proven BEFORE adopting any provider

1. **Does it register on the engine actually running?** Run the engine's own discovery predicate against the
   checkout, then import it under the loader's synthetic namespace and confirm the class subclasses the
   engine's provider base. A doc written against a later release is a hypothesis about yours.
2. **Is the runtime dependency installable here?** A missing binary is an install, not a blocker — but measure
   it before writing the plan. Prefer a user-level install into a scratch dir over anything needing root.
3. **Does every hook work without that dependency?** Some providers route *all* hooks through a subprocess
   bridge; a passing import proves registration, not function.
4. **Is the vendor's health check a real check?** A `health()` that only tests file presence will report healthy
   on a system that cannot serve one request — treat it as documentation, not evidence.
5. **Multi-profile correctness.** A multiplexed gateway serves several profiles from one process; each needs its
   own identity setting in its **own** `.env`, or every seat writes under one name.
6. **Does the vault stay the source of truth?** The provider must read FROM it and mirror writes INTO it. If the
   vault becomes a cache of the provider's store, the split has been inverted.

## If the provider gate fails

The architecture does not depend on the vendor. The retrieval half is a vault-backed provider with BM25, and
the write policy is the trim protocol in the parent skill. **Order of work either way:** define the write policy
first, then pick the tooling — a tool installed ahead of a policy just fills the vault faster.
