---
name: memory-tiering
description: "When saving/pruning memory, tier facts by relevance."
version: 1.0.0
author: Gentech
tags: [memory, context, tiering, agentic-behavior, fleet]
---

# Memory Tiering — Intelligence for Intelligence

Jordan's model (Aug 20, 2026): an agent's always-loaded memory (MEMORY.md / USER.md)
should NOT be a dump. It should be a **curated index** of the facts we touch every
session, with everything else parked in the vault brain where it's one search away.

Two tiers:
- **Always-loaded** (MEMORY.md / USER.md) — facts referenced EVERY session. Identity,
  rails, wallet, rules, standing strategy. Lean, high-signal.
- **Vault brain** (retrievable) — facts referenced less often, or RESOLVED. Not lost,
  just parked. Pull back via session_search / search_files when the topic resurfaces.

## Why (the intelligence part)
- Every session reads the memory file. Bloat = slower, more tokens, worse focus.
- **More memory = worse performance** (proven Jul 28, 2026: elaborate memory stack
  deleted → agent worked dramatically better).
- Trimming from the BACK (oldest-first) is dumb — an old high-frequency fact gets
  archived while a recent resolved worry stays loaded. Tier by **relevance**, not age.

## Tiering rules — what stays ALWAYS-LOADED vs ARCHIVES

### ALWAYS-LOADED (keep in MEMORY.md/USER.md)
- **Identity**: who the agent is, personality, speech, the boss (never call Jordan
  terms of endearment — only Vanito).
- **Core rails/keys**: payment rails, wallets, canonical repos, the strategy that
  shapes every decision.
- **Standing rules/red lines**: "never fake receipts," "spend less," "blockers flag
  immediately," "build first talk later."
- **Recurring topics** (per Jordan Aug 20): agentic treasury, x402, AWS, APIs — these
  come up every session, keep them.
- **Active commitments with near deadlines.**

### ARCHIVES TO VAULT BRAIN (low-frequency / resolved)
- **Resolved worries**: "termination risk cleared", "sweep was intentional", "bug
  fixed". Once resolved, compress to a one-liner or archive entirely.
- **One-off events**: a single hackathon that's done, a single hire, a single date.
- **Task progress / session logs**: these go to the brain (09-Green Room / 11-Mess
  Hall / handoffs), NOT persistent memory.
- **Any fact not touched in many sessions** and not needed for the standing model.

## The hard wall — budget is a correctness problem, not tidiness

Memory has a hard character cap, and **an add that would overflow is rejected at write time.** The agent
that tried to save does not get a durable failure it will remember tomorrow — it just does not remember.
So a file at 98–99% is not "nearly full", it is **one good lesson away from being unable to learn it**,
and the loss is silent: nothing errors, nothing is retried, the fact simply never existed.

Three things follow, and they are requirements rather than preferences:

1. **Keep headroom deliberately.** Aim to sit a couple of hundred characters clear of the cap, not to fill
   it. A file that has to be pruned before *every* save is pruning under pressure, and the entry that gets
   sacrificed is whichever is read last — rarely the least useful one.
2. **Every memory file records its own archive destination.** "When full, cut" is not a plan unless the
   file says *where the cut lines go* (this user's: cut lines → Mess Hall archive, fleet-wide knowledge →
   Mess Hall, ideas → Green Room, HQ facts → HQ). A file with no destination has, in practice, no cutting
   mechanism: the agent stalls instead of moving the fact.
3. **Save in ONE atomic batch.** The cap is checked against the **final** result, so a single call that
   removes two stale entries and adds one new one is legal even when the add alone would be rejected.
   Two calls — add, then prune — fails on the first.

### The rejection is silent to the AGENT, so it has to be LOUD to the OWNER

**Nothing tells the agent "I could not write that".** No error surfaces in the reply, no retry happens, and the
next session simply does not know the fact — so the failure is invisible from inside the fleet and obvious only
from outside it. The owner's phrasing of the symptom is the specification:

> *"there's also not a notification that says, hey, we can't log new information until we start trimming."*

**Therefore a fill gauge is not optional reporting — it is the only surface on which this failure is visible at
all.** Two requirements follow:

- **Measure on a cadence, not on demand.** A gauge nobody runs is a number nobody sees. The nightly/weekly
  instrument must read every seat's files and print FILL beside PORTABLE and FLOOR, so a file at 99% is
  distinguishable from a file at 99% that could honestly drop 40 points.
- **Announce BEFORE the wall, not at it.** The useful alert fires while a save can still be made — 85% is the
  alarm threshold precisely because 100% is already a failed save. An alert that only fires once writes fail is
  a post-mortem.

**A proposer with no apply path can never act, and that is usually correct.** An instrument whose only verbs are
`archive()` (a dated copy of the file) and "print advice" will report `NO RULE FIRED` forever and trim nothing —
not out of a bug but because **it was built to recommend and the acting half was never written.** Say which half
is missing before calling such a tool broken: a ranker that never fires and a ranker with no writer look identical
from the outside, and they need opposite fixes.

**Tool:** `profiles/gentech/scripts/memory-gauge.py` — prints FILL / PORTABLE / FLOOR per file, names the band,
and ends in the action (`move N chars of portable entries`) rather than a bare percentage.

### Auditing a file (yours or another seat's)

Report these five columns per seat, and read a sample of entries rather than only counting characters:

| measure | why it matters |
|---|---|
| chars / cap | the hard wall, and it is silent |
| headroom | how many facts away from the wall |
| entry count | a fat file with few entries is one giant fact, not curation |
| work-log junk | session narrative dressed as memory — the failure shape |
| archive pointer present | decides whether it can ever cut |
| **cross-seat paths** | an entry citing ANOTHER seat's profile path is a fact measured on a different machine (§ *A fact measured on another seat*) |
| **indexed corpus** | the retrieval root can point at a subfolder: a provider indexing 3 files returns results as confidently as one indexing 6,063 (§ *The recall you measured*) |

**Sample the entries, and say what you did not check.** Confirming that entries are durable, declaratively
phrased and properly shaped is a different claim from confirming each stored fact is still *true* — that is
a separate read against the world, and conflating them is how a stale fact gets a clean bill of health.

### A trim that REWRITES is a rewrite — verify truth, not membership

**Deleting lines is safe by construction; rephrasing them is not.** Once the pass merges, condenses and
re-types entries instead of cutting them, every surviving line is *newly authored* and can assert something the
file never said. Measured: a seat trimming to free space replaced a stale model line with a model-and-rail
combination it had never adopted — its own `config.yaml` said otherwise — and the trim passed a
*"all 18 load-bearing facts still present"* check that could not see the difference, because the fact was
still *there*, just false.

**The procedure, in order:**

1. **Archive the FULL original to the vault first**, one dated file, before touching the live one. The trim then
   costs nothing to reverse and the diff is auditable months later.
2. **Rewrite.**
3. **Verify each surviving fact against the world — a config key, a file path, a command's output — not against
   the old file.** Membership ("nothing was lost") and truth ("what remains is still so") are two different
   checks and only the second one catches an invented replacement.
4. **Report both counts**: before/after characters and the fact-truth check. A compression figure with no truth
   check is a claim about length wearing the clothes of a claim about accuracy.

- **The limit creates the pressure that produces the invention.** An agent trimming under a hard character cap is
  optimising for space, and the shortest way to fill a freed slot is a plausible sentence. Budget headroom on a
  schedule and the rewrite stops being done against a wall.
- **A trim is a good moment to demote a claim, not only shorten it.** If the verification cannot confirm a line,
  the honest replacement is *"UNVERIFIED here"* or a stated date, not a confident paraphrase — a downgrade is a
  successful outcome, an invention is not.
- **Expect the same pass to find a genuine defect in the file it was only supposed to shorten.** A stale model
  line caught this way usually has a sibling (a page declared live that 404s, a rail declared current that was
  retired); re-audit the rest of the entries rather than treating the one catch as the whole job.

**A memory snapshot is frozen at session start** — writing a fact to disk does not put it in front of an
agent whose session is still running. That is a lifecycle fact, not a tiering one: see the wake-vs-refresh
rule in `waking-idle-agent-seats`, and never report "they know now" when what you did was write the file.

### A fact measured on ANOTHER SEAT is the defect no cap ever catches

A seat filling up is not automatically a seat misconfigured. **Check the caps before theorising** (all four
seats read `3200 / 1800`; nothing had missed a raise) — then read the ENTRIES, because the growth is usually
real work plus a few facts that belong to someone else.

**The class: an entry carrying a fact that was true on a different seat.** It costs one line, it loads every
turn, and nothing ever re-checks it. Three shapes, all measured in one 9-entry file:

| shape | tell |
|---|---|
| **wrong-seat path** | `/opt/data/profiles/<other>/scripts/`, `.../secrets/` — the seat hunts in a directory that is not its own, and any script or credential there will not resolve |
| **a guard declared GONE** | *"the dietician and its cron are gone"* — nothing re-checks it, so the seat stops self-trimming while believing it is unmonitored. Verify the script path AND the cron id before believing "gone" |
| **half-true** | the harmless half is true (*"nothing trims automatically"* — by design), the load-bearing half is false. The most misleading kind, because a reader who checks one clause stops there |

- **Fire this rule FIRST, before every SIGNOPSIS/SUPERSEDED/POINTER/NARRATIVE ranking** — a cross-seat fact is a
defect, not a judgement call, so it does not belong in a "candidate cuts" list ranked against preferences. The
dietician's `WRONG SEAT` rule derives the seat from the file's own path (`/profiles/([a-z0-9\-_]+)/`) and flags
any entry naming a different one; prove it on a FIXTURE, because a live file is often corrected before the rule ships.
- **Name the seat and the date as part of the fact.** "a cron script must live in `.. /scripts/`" is true on
EVERY seat and therefore says nothing; "on this seat" plus `measured <date>` is what lets the next reader tell a
stale measurement from a current one. A `checked <date>` clause is precisely what let a month-old "it's gone"
survive — the NARRATIVE rule is already tuned to that phrase.
- **Never rewrite another seat's memory, even to fix an obvious error.** Extract the exact text, verify each claim
against the world (path, bytes, mtime, cron id, schedule), and hand it over as a correction with receipts; the
seat rewrites in its own voice. Handing over also produces a better fix — a seat that re-measures will correct
numbers you merely inferred (its own token's rate limit, for instance).
- **Re-read the file after the handoff, not the DM.** The correction landing is observable on disk: the entry now
names its own seat, or the seat's own measured number replaces yours. Record which entries changed and which did not.
- **A seat that says "none of this is mine" is a result.** When auditing an inherited folder or a shared file, a
seat declining ownership is the finding that closes the question — do not chase it as non-cooperation.

## Caps live in each seat's config — read them, never hardcode them

**The limit is `memory_char_limit` / `user_char_limit` under `memory:` in `profiles/<seat>/config.yaml`**, with the
engine defaults (2200 / 1375) applying only to a profile that never set them. **An instrument that hardcodes the
defaults is measuring a limit that may no longer exist** — measured: every seat had been raised to 3200 / 1800 while
the nightly checker still reported "99% full" against 2200, so a fleet in good shape looked like a fleet on fire and
the alert became noise.

- **Read the cap per profile from its own config**, and fall back to the default only when the key is absent.
- **This seat's own `config.yaml` may be write-protected** ("Agent cannot modify security-sensitive configuration").
  Use the sanctioned CLI (`hermes config set memory.memory_char_limit 3200`) rather than editing the file, and
  verify by re-reading the key afterwards — the guard refuses silently enough that a failed edit looks like success.

### The cap counts CHARACTERS, not bytes — prove the unit in the ENFORCER before diagnosing

The budget is a **character** count and the writer compares `len()` of the joined entries against it. Measuring
the file with `wc -c` or `len(bytes)` counts UTF-8 **bytes**, and every em-dash, `§` separator, `→` and `≠` costs
several. On a dense file the gap reaches tens of characters — measured, 1,739 bytes against 1,701 characters, so
a file reported as "31 chars over cap" actually held **99 characters of headroom** and had never refused a write.

- **Grep the writer's own comparison before diagnosing a cap.** `len(ENTRY_DELIMITER.join(entries))` vs `limit`
  settles the unit in one read; a byte count is a proxy that is wrong by the width of every non-ASCII glyph.
- **The two errors have opposite signs, so say which one you are making.** Measuring bytes against a char cap
  **over-reports** fill — a false "over cap" that invites a destructive trim of headroom the file already had.
  Measuring chars against a byte cap **under-reports** it — the silent direction, where a seat is told it has room
  it does not have. Only the second can cost a fact; only the first can cost trust in the instrument.
- **Never report "over cap / silently refusing writes" from a byte measurement.** It tells the owner a mechanism
  is broken when it is not, and the correction has to be made in public after the trim has already run.
- **Re-measure the same way the enforcer does, immediately after a trim**, so before/after numbers are comparable.
  A trim verified in bytes and reported in characters looks like it freed twice what it did.

### An instrument that grades "seats" must prove each one is a seat

Enumerating `profiles/*` and treating every directory as a seat grades **artifacts** as agents — a leftover test
profile with a `SOUL.md` and an empty `memories/` dir, no `config.yaml`, and no agent behind it, reported as a
filling file that needs trimming.

- **Require the artifact that proves a runnable profile** (a `config.yaml`) before grading, and say in the output
  what was excluded.
- **A seat that cannot speak is not graded — it is clutter**, and grading it manufactures a finding the owner
  cannot act on. Report the omission rather than silently dropping it, so a genuine misconfiguration is still visible.

### "NO RULE FIRED" must name the ACTION, or it reads as all-clear

The terminal-state section above says to speak the phrase out loud instead of inventing a cut. **Saying only that
no rule matched is not enough** — an operator reads *"nothing matched, the seat can choose"* as *nothing to do*, and
the alert gets skipped for weeks while the files sit at 96–100%.

- **End the line with the move**: `ACTION: this seat must consolidate BY HAND (merge same-topic entries, push detail
  to the archive)`. A ranker with no writer cannot act, so its output has to say who can.
- **A recommendation that names no actor is indistinguishable from a clean bill of health** — the same failure as a
  report whose exit code cannot separate "found something" from "crashed".

## Trimming: PROPOSE, never rewrite the file

A script that trims memory is trimming by **position**, and the lines it cuts are exactly the ones the agent would
have kept. So the decision stays with the seat; the instrument's job is to stop the seat having to hunt.

**Rank candidate cuts by rule, and print the rule that fired** — a proposal the reader cannot justify is a proposal
they will ignore:

| rule | meaning | why it is safe to offer |
|---|---|---|
| **WRONG SEAT** | the entry cites another seat's profile path, or declares a guard GONE without a receipt | it is a fact measured on a different machine — it fires before every other rule because it is a defect, not a preference |
| **SUPERSEDED** | the same key is claimed by a newer entry with a different value | the old one is the dangerous stale — a value that is no longer true, loaded every turn |
| **POINTER** | a filename or path with no claim in it | memory is for facts; the vault is for addresses |
| **NARRATIVE** | a dated account of finished work | history belongs in the archive, not in context |
| **NO RULE FIRED** | nothing matched | **say this out loud** — inventing a cut to fill the quota is worse than silence |

**Never fall back to "longest entry" as a finding.** Measured: the longest entries in one fleet's files were the
Docker bind-mount fact, the API rate-limit fact and the default media lane — load-bearing every turn. **Longest is
not least valuable.**

**A date in a memory entry is usually the fact's RECEIPT (`measured 2026-11-02`), not evidence the entry is
history.** A narrative rule keyed on "contains a date" proposes cutting exactly the measured facts that make the
memory worth keeping; key it on real narrative markers (commit sha, handoff, shipped, closed, forensics) instead.

**Write nothing unsupervised.** Closure/trimming needs an explicit, reader-confirmed list of entries — a regex
match is not a reading. Ship the worklist; require the seat to pass the entries it chose.

**Validate the ranker on the file you can judge best: your own.** Before shipping a trimming rule, run it against
the agent's own MEMORY.md and read every proposal. If it offers to cut the bind-mount path, the rate-limit numbers,
or the default media lane, **the rule is wrong, not the file** — those are the entries that make the memory worth
having, and an instrument that would delete them will do exactly that, confidently, at 100% self-reported precision.
This self-test is cheaper than any corpus and it is the only one whose ground truth you hold in your head.

**Cadence follows the danger, not the anxiety.** A seat just under the cap is not in peril *within a day*; it is in
peril at the moment it learns something and silently evicts something better. Twice a day (morning and evening)
catches both a seat that filled overnight and one that filled during the day; four runs produce four identical
alerts, and identical alerts train the reader to skip them.

## A target level is not an alarm threshold — and "NO RULE FIRED" is a terminal state

The dietician's `TRIGGER` (default `0.85`) is an **alarm threshold**: it decides when the job *speaks*, and the
job only ever PROPOSES. It is not a diet target, and moving it changes nothing about how much memory holds. When
**When someone asks for memory "trimmed to 40–50%", answer in characters first** — on the fleet's 3200 / 1800 caps that is
**~1,280 / 800 chars**, a near-total rewrite rather than a trim.

### Measure a FLOOR before promising a percentage — the two files do not have the same floor

A target percentage is a guess until someone classifies the entries. Run three numbers per file, and they answer the
question the percentage was trying to ask:

| number | how it is computed | what it decides |
|---|---|---|
| **FILL** | chars / cap | whether the next save is possible at all |
| **PORTABLE** | entries that name a concrete artefact (path, script, note) — the brain already holds that detail | how much can leave without losing a capability |
| **FLOOR** | cap − portable, i.e. identity, red lines and preferences that have no other home | how far down this file can honestly go |

**The floor is wildly asymmetric across the two files, and that asymmetry is the finding.** Measured on one seat:
MEMORY held **41% portable** (six entries that were paths and provider traps, all already documented in the vault),
so its floor was **~56%** — a real, reachable cut. The same seat's USER.md held **0% portable**: every line was a
rule about the owner, so its floor was **~98%**. **"Trim USER.md to 60%" is not a hard task, it is an impossible
one** — there is no home for those facts. The honest answer there is a question for the owner: *which of these do
you no longer want me to know?* Answering with a deletion instead invents a preference nobody stated.

- **Report the floor beside every target.** A percentage with no floor is a wish; a percentage against a measured
  floor is a plan, and when the target is under the floor the plan is "change what the file is for".
- **Portable is not the same as valueless.** Those entries were load-bearing every turn *while they were long*; they
  are still load-bearing as pointers, which is why they must be **compressed, not deleted**.

### PORTABLE = 0 is not a dead end — TIGHTEN before you escalate to the owner

**When a file's portable set is empty, the entries have no other home, but the PROSE around them is usually fat.**
The third move between "compress to a pointer" (impossible here) and "ask the owner which facts to forget" (a
question, not a fix) is a **rewrite-in-place that keeps every fact and removes the words that only restate it**.
Measured on an owner-preferences file at 90.6% with **0 chars portable**: two passes of tightening — deleting a
clause whose neighbour already said it, and replacing an explanatory tail with the rule it explained — took it to
**79.1% with all six entries and every fact intact**.

- **Tighten means fewer words for the same claim, never fewer claims.** The test is fact-by-fact, not
  character-by-character: walk the original entry, name each assertion it makes, and confirm the new text still
  makes it. A paragraph that reads tighter and has lost a "never" or a "which" has done the wrong thing well.
- **Cut in this order:** a duplicated clause (the same fact stated twice in one entry), then an explanatory tail
  (*"which is why…"*, *"this means…"*) where the rule already implies it, then decorative qualifiers. **Never**
  cut an enumerator (*"full", "every", "never", "only"*), a number, or the object of a rule — those are the
  load-bearing tokens, and a tightened sentence that loses one is a silently narrowed instruction.
- **Escalate to the owner only after tightening has been tried and measured.** *"Which of these do you no longer
  want me to know?"* is a fair question at a genuine wall; asked first, it makes the owner do work a rewrite
  would have done.
- **Say which move you used.** "Moved 724 chars of operating detail to the brain, then tightened the rest without
  dropping a fact — 93.4% → 79.8%" is reproducible and auditable. "Trimmed memory" is neither.

### Compressing to a pointer — the reversible cut

Distinct from a spill: a spill moves an entry out verbatim; **compression rewrites a long entry into a short pointer
plus a scheme for finding the detail again.**

1. **Write the DESTINATION first, whole** — one vault note with a stable section per topic (`§RAIL`, `§QUIET`,
   `§TRAPS`), containing the long form of every fact about to be shortened. **Nothing is compressed before its detail
   exists somewhere.**
2. **Assert the detail landed, by searching for the specific values, not for the file's existence.** Grep the new
   note for each concrete token the memory entry carried (the header name, the measured constant, the script path).
   A destination that exists but is missing the one value the entry protected has not received anything.
3. **Rewrite the entry to pointer shape**: *"RAIL = <the decision>; traps → `<path>` §RAIL."* Keep the **rule** in
   memory and send the **evidence** to the vault — the rule is what must load every turn; the mechanism behind it
   can be looked up.
4. **Re-measure, and report before/after.** A move of 98% → 79% on one file is a real result; the other file's
   unchanged 99% is not a failure of the technique, it is the floor doing its job.
5. **Verify every surviving pointer resolves.** A pointer to a section that does not exist is the same dead-pointer
   defect as a report naming a protocol file that was never written — cheaper to catch here than in six weeks.

**Never compress a fact whose VALUE is the detail** — a measured constant, a rate limit, a key's expiry date. Those
survive the trip to the vault badly (nobody greps for them mid-incident) and should stay whole.

Three states a checking run can be in, and each needs a different answer:

| state | what it means | the right response |
|---|---|---|
| a rule fired | a real defect, or a real stale/redundant entry | hand the list to the seat; the seat cuts in its own voice |
| **NO RULE FIRED** | every entry left is a loaded-every-turn fact — the rule engine has spent its levers | **stop tuning the instrument.** Name the architectural options (below) and let the owner choose |
| nothing flagged | the file is under the alarm threshold | say the number; never manufacture work |

**"NO RULE FIRED" is not a bug and not a shrug — it is the terminal state of a ranker whose four levers
(WRONG SEAT, SUPERSEDED, POINTER, NARRATIVE) are exhausted.** It is also the exact moment to stop editing the
checker: a rule invented to reach a quota will delete a fact the seat needs every turn. The honest next step is
architectural:

- **Move standing rules out of memory and into a skill.** A rule that governs one class of task belongs in that
  class's SKILL.md, where it loads when relevant; memory is for what applies to EVERY turn. This is the only move
  that takes a healthy file materially below ~60% without deleting identity facts, corrections or red lines.
- **Read cross-seat duplication as evidence, not as spare room.** The identity/preference block is copy-pasted into
  nearly every seat's USER.md. Measure it (whitespace-normalise the entries, then `SequenceMatcher` ≥ 0.75 or simply
  count the shared sentences) and the finding is *"this is a fleet-wide fact"* — it belongs in one skill or one
  vault doc, with each seat keeping only its own deltas. Cutting one seat's copy does not make that seat leaner in
  any useful sense; it removes a fact the seat still needs.
- **Say plainly when the target exceeds what trimming can deliver, with the arithmetic attached.** *"~60% is
  reachable by removing duplication and stale entries; 40% requires a redesign"* is a useful answer. A rule added
  to hit the number is not.

**When the answer turns architectural, the next question is "what have others already built?"** — the
two-layer design, the ranked criteria for judging a third-party memory system, the engine's provider-swap
mechanics and the registration gate live in **`references/memory-architecture-options.md`**. Read it before
evaluating or recommending any memory framework: **a star count is not a fit criterion**, and the decisive
questions are whether it ships a provider for this engine, keeps the vault as markdown, and consolidates
without running a model.

### A promotion rule must be able to REJECT — "seen N times" measures persistence, not importance

A consolidation/dream pass that promotes "repeated" signals has an obvious-looking test — seen on N distinct runs —
and on a real corpus it promotes everything. Measured: **77 of 77 observations reached exactly 3 runs**, because a
memory line persists until someone deletes it. The condition was satisfied by *existing*.

**Measure the selection rate against the real population before trusting a promotion rule.** If it selects ~all of
them, it is the input re-printed with extra steps, not a filter.

The only local evidence that a fact deserves promotion is that it was **REMOVED and then RE-OBSERVED** — someone cut
it and needed it back. That is a signal the file cannot manufacture by sitting still. Track presence/absence per
entry each run and promote on the resulting **gap**.

- **Count absence explicitly.** Without an absence counter the gap is always 0 and the pass promotes nothing — a
  silence that reads as "nothing important" when it means "never observed". Both failure directions (promote
  everything / promote nothing) present as a clean, quiet run, so print the denominator and the selected count.
- **Retirement is the mirror, and it is also a proposal.** A standing rule unmentioned for M runs is offered for
  retirement; a pass may never delete it.
- **A classifier keyed on ONE grammatical form misfiles the other.** A rule detector built from imperative verbs
  ("always", "never", "do not", "must") classified declarative preferences ("expects full enumeration",
  "prefers stated limits") as non-rules — and declarative is how a preference about a person is usually recorded.
  Run a new classifier across the real corpus and read BOTH classes before shipping it. A length floor is the same
  trap: it silently discards short, load-bearing rules.
- **Keep the pass deterministic.** Two counters and a hash can audit their own output; a model deciding what to
  promote cannot, drifts between runs, and costs inference nightly for a job whose value is that it is boring.

### A report that names a protocol file has to prove the file is there

An instrument whose footer says *"trim per `<path>/memory-trim-protocol.md`"* is pointing every reader at a
document. **Resolve that path in the same run that prints it.** Measured: the file had never existed at the path
reported — the only copy was under `_archive/`, months old, and still stated the engine-default caps
(2200 / 1375) that the fleet had since raised to 3200 / 1800. Anyone following the instruction would trim to a
limit that no longer applied.

- **A dead pointer is the cheap version of the wrong-seat fact**: the instruction loads every time and lands
  nowhere.
- **A protocol document that states limits must read them from config, or carry the date it was written.** A cap
  written into prose is a constant, and constants rot silently.

## The recall you measured is only the corpus it indexed

**Before reporting any recall or search quality, count the documents the configured root actually indexes.** A
vault-backed provider takes a root path, and that path is commonly ONE subfolder — the place new notes are written —
not the brain. Measured across four seats: **1, 3, 4 and 7** markdown files indexed against a **6,063-note** vault.
The worst seat's "BM25 over the vault" was BM25 over a single seed note, and it had never once returned anything
outside that file.

**Why it survives:** a search that returns *something* looks identical to a search that returns the right thing.
Nothing errors, the instrument reports a score, and the score is about the wrong corpus.

Score one question set twice — configured root, then the whole vault (a root env var override is usually enough) —
and report both:

| corpus | top-5 score |
|---|---|
| configured root (3 files) | **0 / 14** |
| whole brain (6,063 files) | **11 / 14 = 79%** |

Cost of the fix, measured so nobody calls it free: **6.2 s cold corpus read, 0.86 s warm search** over 6k notes.

- **Name the misses, not just the score.** One vocabulary gap, one ambiguous question, one genuine routing miss.
  79% over fourteen cases has a wide error bar; ship the misses beside the number or the number is overstated.
- **An eval reporting `0%` when the retriever failed to load is worse than no eval.** Keep "scored zero" and
  "could not measure" in separate counters, and exit non-zero when nothing was measured. A retriever that silently
  returns `[]` produces a confident, completely false verdict.
- **Drive the provider the seat actually runs, not the agent's tool surface.** A script cannot import the agent's
  tool module (it is a tool API, not a library); load the provider class and call its `search()`.
- **Note-count is the wrong progress metric — trimming GROWS it.** Archived lines land *in* the vault, so a fleet
  that trimmed measured 6,061 → 6,062 → 6,063 while getting healthier. Report **injected bytes**; read the vault
  column as a directional check, never a target.
- **Check whether the recall corpus mirrors the memory file back.** A runtime memory write can auto-mirror a copy
  into the vault root, so the same fact is counted twice and can arrive twice per turn (memory block plus
  recalled-context block). Remove that duplication first.

## Overflow without loss — spill and return

When the file is genuinely full, the answer is not to delete: **active memory is the desk, the vault is the filing
cabinet, and the vault is already synced.** Move the overflow into `<vault>/11-Mess Hall/memory-spill/<seat>/<date>.md`
(entries verbatim, one dated file) and **leave ONE line in memory behind it** naming what left and where it went.

- **Reversible by construction** — the full text is in the vault and the pointer carries the path.
- **Not a cache.** Nothing reloads automatically and no turn gets cheaper by itself; what the spill changes is the
  PRESSURE, so the next lesson can be kept without evicting a better one.
- **`--return` prints the spilled note**, so bringing a fact back to the desk is one command, not an archaeology dig.
- **The seat chooses what spills.** Same confirm-the-list rule as trimming.

**Prove the spill moved facts rather than destroying them.** Sample the file's size against a vault-side count (the
seat's vault-memory root) on a schedule, and read the two together:

| memory | vault | verdict |
|---|---|---|
| down | **up** | moved — the spill worked |
| down | **flat** | **LOST** — a fact left the desk and arrived nowhere |
| up | flat | the seat is learning faster than it files |

**Memory-down + vault-flat is the failure that looks identical from the memory side**, which is why the vault column
is not optional in the instrument.

### When the owner authorises an ACTING relief step — the five walls

A proposer with no apply path is safe; an actor with no walls is not. "PROPOSE, never rewrite" stays the default, but
when the owner explicitly asks for the acting half to be built, it has to be narrow enough that a bad night cannot
empty a file:

- **One entry per run, never a sweep.** A cap of one makes the worst case a single lost line and keeps every change
  reviewable. A relief step that can empty a file under pressure will, on the night pressure peaks.
- **Never the file that describes the owner.** Facts about the person have no other home and no size rule can decide
  which of them they would rather keep. Exclude that file by path in the code, and prove the exclusion by hashing it
  before and after a run — a comment saying "never touches it" is not a test.
- **Move verbatim; never rewrite.** Same rule as a manual trim: an acting step that rephrases an entry is authoring new
  memory, and the shortest way to fill a freed slot is a plausible sentence.
- **Archive before rewriting, and confirm the entry landed.** Write the entry whole to the dated archive, verify it is
  there, and only then rewrite the live file. Archive-first makes every relief reversible; the reverse order has a
  window where the fact exists in neither place.
- **Refuse when every entry is load-bearing.** *"This file needs a human"* is a correct result and the common one for
  a seat whose entries are all operating facts — model rails, addresses, credentials, paths. Printing the refusal beats
  cutting the least-bad candidate, and it is the same "NO RULE FIRED names the ACTION" discipline applied to an actor.

**Selection by size is wrong for an auto-actor, even where it is wrong for a ranker.** Longest-first picks the model
rail, the mount path and the rate-limit numbers — precisely the entries that exist to load every turn. Before ranking
by length, exclude anything that names a live system, path, command, credential or rail; length is a poor proxy for
expendability, and an automated cutter gets no second opinion.

## How to apply (standing agentic behavior — do this EVERY save)
1. Before adding a NEW memory entry, ask: "will this be needed EVERY session, or
   only when this topic comes up?" If only-on-topic → save to the Vault instead.
2. When a fact is RESOLVED (problem solved, deadline passed, task done): compress it
   to a one-liner or archive it — don't keep the full narrative loaded.
3. When at the 85% threshold: consolidate in ONE atomic batch (remove stale + add
   new) instead of cramming.
4. The fleet dietician (memory-dietician.py) uses the same relevance tiering, not
   back-of-file trimming, so low-frequency facts archive and high-frequency stay.
5. When a topic resurfaces, pull the archived entry back from the vault
   (search_files / session_search) and re-load it if it's now a standing fact.

## Verification
- MEMORY.md / USER.md stay well under cap with only high-signal facts.
- Resolved worries are compressed or archived, not carried forward.
- No durable fact is ever lost — it's in the vault brain, retrievable.

## Pitfalls
- Don't archive on a whim — if it's referenced across sessions, keep it.
- Don't keep resolved worries loaded "just in case" — archive them; the vault has room.
- The brain (vault) has room — that's its purpose. Overflow belongs there, not in the
  always-loaded memory file.
- This is a STANDING behavior, not a one-time cleanup. Apply it on every save.
- **A cap is a ratio, not a count.** "13 facts" is a budget; answering "we are full" by raising the cap without
tightening what gets written just moves the wall. Raise headroom AND keep the three writing rules: findings go to
the vault, a fact carries a receipt not a story, and **a fact that stops being true is deleted in the same turn it
is replaced** — every stale pair is a silent contradiction loaded every turn.
