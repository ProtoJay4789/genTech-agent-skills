---
name: hermes-memory-and-restart
description: Use when memory fills, restarts lose context, or a session forgets.
---

# Hermes memory, and surviving a restart

**Written from a fleet that lost work to each of these.** Every rule below is a failure that actually
happened, not a precaution.

---

## Memory is frozen when the session starts

**Your memory files (`MEMORY.md`, `USER.md`) are read once, at session start, and injected into every
turn from a snapshot.** Editing them mid-session does **not** change what you are currently seeing.

**⚠️ The practical consequence:** at 2pm you may be honouring a memory entry that you deleted at 11am.
The injected text is a photograph, not a live feed.

**`/new` refreshes the SESSION, and only the user can send it. But the frozen *prompt* can be rebuilt without one.**

```bash
hermes sessions refresh-prompts -p <profile> --session <session-id-or-prefix> [--json]
hermes sessions refresh-prompts -p <profile>            # every continuing session in that profile
```
**What it does:** marks each session to rebuild its stored system prompt from current sources **on its next turn** —
history and session id kept, cost is **one prompt-cache miss**. **Critical: the refresh is REQUESTED, then applied
later. You cannot observe success in the same run.** Measured: two seats accepted the request and neither took a turn
while the script was live, so their `system_prompt_hash` was unchanged — the request is not the result.

**The only proof it landed is the stored prompt changing.** Compare `sessions.system_prompt_hash` before and after that
seat's next turn (it lives in `profiles/<seat>/state.db`). **If the same seat is still frozen on the next check, the
request did not land — that is when it genuinely needs `/new` or a restart.**

**So a watcher can FIX this class instead of asking a human.** A scheduled job that finds a session older than its
threshold should call `refresh-prompts` for that session and report *"refresh REQUESTED — applies on its next turn (not
yet observed)"*. **Do not report "fixed"; do not report "/new needed" when a request was accepted.** And note the loop
that cannot be broken from outside: **a seat that never takes a turn keeps the refresh queued forever** — a silent seat
is a different alarm from a stale one, and conflating them hides both.

### Staleness and cost are two different alarms, and only one needs a human

Once `refresh-prompts` exists, **freshness no longer needs `/new`.** What still needs it is **context length**: every
turn resends the session's whole history, so a long conversation is a standing bill and a slow drift in coherence.
Keep the two apart in any report and in any answer to *"how often do I have to do this?"*:

- **Stale memory → automatic.** The watcher refreshes it. The human action is *checking*, not resetting.
- **Context size → human.** Report `message_count` beside the session age, because age alone is the wrong trigger:
  a 4-day session with 13 messages costs nothing, and a 1-day session with 250 messages costs every turn.
- **Cadence: watch daily, act weekly.** A silence-gated daily watcher costs nothing when clean; the reset itself
  belongs at a natural boundary (a finish, a handoff, a morning start), not on the day the counter first blinks.
- **Say which number drove the recommendation.** "240 messages" is actionable; "that seat is stale" invites the user to
  reset everything, including the seats that are fine.
- **Verify a reset by the SESSION ROW, not by the user's word.** A new session appears with `message_count = 0` and a
  fresh `started_at` while the old row stays on disk with its full history — confirm both, and confirm the watcher has
  gone silent, before reporting the reset landed.

**So:** when a memory fact is wrong and the user cares, **say it is corrected on disk and will take
effect next session.** Do not claim the correction is live.

## The character budget is hard, and it counts

Memory has a fixed character budget, checked **only on the final state** of a batch. Two consequences:

- **Batch your changes.** Add + remove in ONE call — the limit is evaluated after the whole batch, so a
  batch that frees space and adds a fact succeeds where an add alone would be rejected.
- **Order the batch: `remove` BEFORE `patch` when the patch would restate text another op matches on.** Ops apply
  in order against evolving state, so a `patch` that expands an entry to include a phrase already present in a
  second entry makes a later `remove` match **two** entries — and the batch is atomic, so the whole thing is
  rejected and nothing is written. Remove first, or give each `old_text` something unique to its entry.
- **A merge is where a fact disappears.** Before removing an entry as "duplicate of X", enumerate **every sentence**
  in it. Measured: a consolidation dropped a standing capital rule (the cousin's Tier-2, recommend-only, no
  capital moves without his word) because it lived in the second half of a sentence about something else. Re-read
  the merged result **against the removed text**, not against your memory of it — that is the same verify-the-
  rewrite pass this file already requires, applied to a one-line merge.
- **Do the ARITHMETIC before composing the batch, not between attempts.** A batch is atomic: a rejection applies
  NOTHING, so guessing costs a full round-trip and leaves the file untouched. Compute
  `current + Σ(adds) + Σ(patch deltas) − Σ(removes) ≤ cap` first, then trim to a margin of 30–50 characters in
  that same call — one character of headroom is a second retry waiting to happen.
- **Use the rejection's own number, and over-shoot it.** The error states the overflow exactly (*"free at least
  N chars more"*). Three consecutive rejections at 209 → 83 → 33 characters is one batch that should have been
  computed once: each retry re-paid the same work and none of them wrote anything.
- **Shorten an entry before you remove one.** A `patch` that compresses a verbose entry keeps every fact; a
  `remove` deletes one. Compress entries no task depends on (dated receipts, long parentheticals, restated
  paths) — never the standing rules, and never a value you have not re-read from its source.
- **When it fills, cut — don't skip.** Write cut lines to a vault archive, not to `/dev/null`. The
  archive is the point: *"memory is the buffer, the vault is the system of record."*

### An over-cap file presents as FORGETTING, not as an error

**A memory file can be PAST its cap and still sit on disk, and from that moment every write is refused with
no signal to anyone.** The file does not corrupt, the tool does not crash, and nothing appears in the
transcript — the seat simply stops accumulating what it is told.

**⚠️ Measure in the unit the ENFORCER uses — characters, never bytes.** `wc -c` reports BYTES; the cap counts
`len()` of the joined text (`memory_tool_store.py`: *"budgets are in chars (model-independent)"*,
`len(ENTRY_DELIMITER.join(entries))`). A file dense in `—`, `§`, `→`, `≠` costs 2–3 bytes per glyph but **1 char**, so
a byte reading over-reports by ~2% — and in the alarming direction. Measured: a seat was reported at
`USER.md 1,831/1,800 (−31, already over)` from `wc -c`; the enforced figure was **1,701/1,800 (+99 free)** and it had
never refused a write. **Read the number from the enforcing code before calling a file over-cap** — the correction
cost two minutes; acting on the byte figure cost a rewrite of a file that was never full.

**The external symptom is a colleague forgetting a conversation, not a memory error.** If a seat "forgot what
we discussed yesterday", measure the file before investigating the session, the retrieval, or the model.

- **Measure HEADROOM IN CHARACTERS — signed — and report the tighter file.** `3200 - size` / `1800 - size`;
  a **negative** number means writes are already being refused, which no percentage display shows once it
  rounds to `100%`. Do not compare raw byte counts across the two files: the caps differ.
- **A probe that only reports "near the cap" misses the past-the-cap state entirely.** Make the pass condition a
  floor (e.g. ≥200 chars free ≈ two durable facts), so over-cap is a failure rather than a rounding artifact.
- **A GREEN AT LOW HEADROOM IS A WARNING — use two tiers, not one.** Measured 2026-11-23→24 on this seat:
  `USER.md` sat at **294 bytes free**, the nightly probe read ✅, and it was at **34** the next evening. The
  failure was visible for a full day and looked like health. Below ~400 free, carry the warning **in the text a
  human reads** (`· ⚠️ THIN — trim before it fails`), keeping the hard fail at 200. A binary pass/fail cannot
  distinguish "has room" from "has not failed yet".
- **Measure in BYTES, not `len(str)`.** `3200 - os.path.getsize(p)`: a character count under-reports by ~22 B on
  a file with em-dashes, en-dashes and `§` separators — enough to turn a green into a fail when you are near
  the line.
- **Trim by VERIFYING FACTS, not by eye.** Back the file up, rewrite compactly, then assert every fact survives
  with a substring checklist (measured: **46/46 kept, 1,766 → 1,514 bytes**). A trim that drops one fact is
  worse than no trim, because nobody re-reads a file they believe is fine.
- **When a fact must leave, MOVE IT AND LEAVE A POINTER — verify the destination ranks before you shrink the
  source.** Two notes written to vault memory (career lane, games lane), each searched by its own phrase to
  confirm it comes back **#1** (`score 63.8` and `52.9`), and only then was `USER.md` cut from **1,514 → 1,145
  B (286 → 655 free)**. The pointer line names the exact search phrase and the instruction (*"read the matching
  note BEFORE advising"*) — a pointer that merely says "see vault" is a broken link in practice.
  - **Keep the judgment rules in the every-turn block, move only the detail.** "Exit Amazon ASAP judges every
    initiative" stays (it changes every recommendation); the SOH2 shift times go (they only matter when
    scheduling). Test each fact: *would this change what I do on an unrelated task?*
  - **Verify BOTH directions after the split:** the 22 facts that stayed are present (22/22) **and** the pointer
    phrases are present (3/3), then run the probe. A trim verified only in one direction cannot tell you which
    half broke.
- **More frequent runs do not fix it, and that is the question users actually ask.** If the instrument's rules
  never fire on the file's shape, raising cadence multiplies the same null output — see *A proposal-only
  instrument will always read as broken* above. The bottleneck is the **decision** (or a different mechanism),
  not the sampling rate; answer the cadence question with that distinction instead of rescheduling.
- **The cap is per-file and silent, so make it a scheduled probe on every seat**, not a manual pass. One probe
  that prints signed headroom for both files, run per seat, converts "why did it forget" into a number.

**What belongs in memory:** facts that apply to *every* session — who the user is, environment facts,
standing conventions with no task home.
**What does not:** procedures (skills), task progress (session history), anything re-discoverable.

## The caps are CONFIG, and an instrument must READ them

**`memory_char_limit` / `user_char_limit` are per-profile keys** (`memory:` in `profiles/<name>/config.yaml`),
not constants. **Set them with `hermes config set memory.memory_char_limit <n>`** — a hand edit is refused by
the config writer's own guard, and a running process rewrites keys it owns.

**⚠️ Any tool that measures memory must read the cap from the same config the seat runs under.** A checker
that hardcodes the default keeps reporting `2196/2200 (100%)` after the limit moved to `3200` — the number is
arithmetic on a fiction, and the reader concludes the seats are full when they are at 68%. Measured: eight
files across four seats were "at 100%" against a limit none of them had. **Resolve the cap per profile; print
the cap beside the reading so a stale limit is visible.**

**⚠️ And it must prove each profile is a SEAT, not just a directory.** `glob('profiles/*')` returns directories;
a leftover test artifact with a `SOUL.md`, an empty `memories/` and **no `config.yaml`** was graded as a seat and
reported as a finding for a full day. Require `config.yaml` — every profile Hermes can actually run must have one —
so an instrument cannot manufacture output from clutter.

## Make the fill VISIBLE to the agent, not only to a checker

**A cap you discover by hitting it is not a limit, it is a wall.** Measured on one fleet: a seat at 2,976/3,200 and
another at 3,189/3,200 — **eleven characters of room** — and neither knew. The only signal was the memory tool
**rejecting an add**, which arrives *after* the agent has already decided what to write. A report emailed to a
human does not fix this; **the number has to reach the agent, before its own write.**

Hermes shell hooks do that in two moments: **`on_session_start`** (always — awareness) and **`pre_llm_call`**
(warn-only, at/above the band — the reading at the moment of the decision). A single top-of-session reading ages,
because memory is frozen; a per-turn reading below the band is wallpaper.

Four rules that cost a cycle each to learn:

- **Hook stdout must be JSON `{"context": "…"}`.** Plain text is **dropped** — the run reports *"contributed
  nothing to the dispatcher"* and looks like a healthy hook with no output.
- **`pre_tool_call` cannot carry context** — it accepts only `block`/`modify`/`approve`. Context belongs on
  `pre_llm_call`, which does.
- **Consent is PER-PROFILE** (`profiles/<seat>/shell-hooks-allowlist.json`), so four seats means four approvals,
  and a configured hook that is not allowlisted **never fires**. Do not set `hooks_auto_accept` to skip it.
- **Band on the EXACT ratio, never the rounded display** — 79.9% prints as `80%` and a `>= 80` test on the rounded
  value fires before its own threshold. Name the tight FILE, not just "memory".

**The config, the wire, the verification commands, the band table and the boundary fixtures:**
`references/memory-hooks.md`.

## Wrong memory outlives full memory — audit the ENTRIES, not just the percentage

When a seat's memory is near its cap, the first question is the cap (§ above) and the second is the growth
rate — but the question that actually finds defects is *what does this seat believe that is no longer true?*

**A stale belief in memory is self-reinforcing, and it is worse than a missing fact.** Measured: a seat's
memory carried *"nothing trims memory automatically (the dietician and its cron are gone)"* while the
dietician script and its twice-daily cron were both live. That seat would never self-trim — **the entry
denies the exact mechanism that would correct it**, and no scheduled job can edit the belief that disables it.

Audit for these three shapes whenever memory is near its limit:

| shape | how it reads | why it survives |
|---|---|---|
| **denial of a live mechanism** | "X is gone / nothing does Y" | the mechanism that would fix X is the one being denied |
| **another seat's path or ID** | a rule naming `profiles/<other-seat>/…`, another seat's cron id, another seat's room | it was copied as a fact, and it is *true* — just not here |
| **a superseded value** | an old limit, address, price, or endpoint, with no receipt | re-reading memory confirms it; nothing compares it to today |
| **a pointer with no target** | "detail → `<path>`" where the file was never written or has moved | the pointer reads as *the detail is safe elsewhere*, so nobody opens it; it occupies the space and hides a truncation |

- **Open every pointer that memory cites, once per audit.** Measured: three entries named `00-HQ/memory-detail.md`
  as their detail page and **the file did not exist**, possibly for weeks — a silent truncation wearing a citation.
  `search_files (target='files')` each target: a missing one means the entry is stale (fix the path) or was never
  true (write the note, then
  re-point). Do this **before** a trim, or the trim compacts entries whose detail nobody can reach.
- **Check every "gone" and "still does" claim against the filesystem and the job list before trusting it.**
  `search_files (target='files')` for the script and ask the scheduler — both are one call, and the memory entry is a claim like any other.
- **Measure growth as chars/hour with the file's own samples**, and read the *shape* of the jump: a step in one
  sample is one write; a smooth climb is repeated small appends. A step right after a cap change is usually a
  seat filling space it just gained, not a runaway.
- **Do NOT edit another seat's memory files.** Read them, prove the defect, and hand the correction to the
  owner — a rule with a `profiles/<other>/` path in it was written by someone else's session and its owner must
  agree to its replacement. Offer the two replacement lines and let the seat (or the user) write them.
- **Make the wrong-seat shape a PERMANENT rule in the measuring tool, not a manual pass.** Reading every entry by
  hand finds the defect once; a rule in the dietician finds it on the next seat. Implement it as the FIRST rule (it
  is a defect, not a judgement call, so it must not wait behind `SUPERSEDED`/`POINTER`/`NARRATIVE` ranking), derive
  *this seat* from the **file path** (`/profiles/([a-z0-9-_]+)/` in the path, never from an argument a caller can get
  wrong), and report both seats: *"cites gentech's profile path — a fact measured on gentech, not on protojay."*
- **Fixture the rule, because the live defect is usually already gone.** The seat that inspired it may self-correct
  before the rule ships, leaving nothing to fire on. Create a throwaway seat-shaped path (`profiles/<fake>/config.yaml`
  plus a `SOUL.md`, or a scratch dir whose path contains `/profiles/<seat>/`), plant one entry citing another seat,
  assert it is named, then delete the fixture and assert silence. A rule that has never fired is a belief.
- **A cap raise is not a fix for a bad entry.** Raising the limit moves the wall; it does not make the wall's
  text true, and it buys silence until the next fill.

## Pruning: PROPOSE with a reason, never trim by rule

**A script that trims memory cuts by POSITION, and the lines it removes are exactly the ones the agent would
have kept.** Measured the moment a rule-based proposal was turned on the agent's own file: it offered to cut
the Docker mount fact, the rate-limit fact and the media lane — **every one load-bearing every turn** — because
the rule fired on "contains a date", and a date in memory is usually the fact's *receipt* (`measured <date>`),
not evidence the entry is history.

**The shape that works:**

0. **Read `memories/MEMORY.md` off DISK immediately before deciding a cut — never prune from the injected
   snapshot.** The snapshot is a photograph of a past session start, and entries added since are simply
   *absent from what you can see*, so every visible entry looks like the whole list. Measured: a session
   trimmed from its snapshot, whose GitHub entry still read "search API closed (422 spammy)" while the file
   on disk had already been corrected to "works authed" hours earlier — the trim deleted the **newer** fact
   and archived the older one, and the loss was invisible because the snapshot agreed with itself. Reconcile
   the two, archive the **disk** version verbatim, and treat any disagreement as evidence the snapshot is
   stale rather than evidence the file is wrong.

1. **Rank candidates with an explicit rule, and print WHICH rule fired** — `SUPERSEDED` (same key, a newer
   entry claims a different value: the dangerous kind of stale, *a value that is no longer true*) · `POINTER`
   (a bare filename — the vault is the library) · `NARRATIVE` (a dated account of *finished work*, matched on
   real markers like `commit`, `handoff`, `shipped`, never on a bare date) · `VERBOSE` as a last resort that
   says outright that longest ≠ least valuable.
2. **When no rule fires, say `NO RULE FIRED`.** An instrument that invents a cut to look useful is lying about
   a dense file; on a real fleet that was six of eight files, and honesty was the correct output.
3. **Never write without an explicit, human-confirmed path list.** A keyword match is not a reading — the same
   regex offered to "close" a CV because it contained the word *shipped*.
4. **Archive the full text before any trim**, and state where: `11-Mess Hall/memory-archive/<date>/`.
5. **A trim is a REWRITE — verify TRUTH after it, not just membership** (see below).

### A trim is a rewrite, and a rewrite needs the same verification as any other claim

**A membership check proves nothing was DROPPED. It says nothing about whether what remains is TRUE.**
Measured: a seat compacted its memory to fit the cap and replaced a stale model line with an invented one —
*"MODEL grok-4.7 (opencode-go) since <date>"* — while its own `config.yaml` read a different default and provider,
and the rail script agreed. **The invented line was worse than the stale one it replaced**: a stale line can be
checked against a date, an invented one reads as freshly verified.

**Compacting under a character limit is exactly the condition where a plausible replacement gets typed from
memory.** The writer is optimising for length, the old value is already half-remembered, and nothing in the tool
compares the new text to a source.

- **Every line you REWRITE — not merely keep — gets checked against a file, a config, or a command before the trim
  is called done.** Verify the kept set for membership; verify the *edited* set for truth. They are two passes.
- **Write the citation into the entry so the next reader can re-check it:**
  `MODEL (config.yaml:10-13, read <date>): default … · provider …`. A bare assertion cannot be audited; a path can.
- **Separate a TEST from a CONFIGURATION.** A value tried once is *"tested X on <date>, NOT adopted"*; writing
  *"since <date>"* turns an experiment into a live setting that no file supports.
- **Cut by POINTER, not by paraphrase.** Where a count, a date or an inventory lives in a file the agent can read,
  replace the number with the path. **A paraphrase is a new claim; a path is a lookup.**
- **When another seat is at its cap, send the protocol rather than editing its file:** archive first, verify
  membership AND truth, and never cut a hard rule to make room for a preference. A seat trimming at speed will
  invent — say so in the instruction, or one of them will.

### A TRIGGER is not a TARGET — an instrument with only a ceiling can never reach a goal

The pruning rules above answer *what to cut*. They do not answer *how full the file should be*, and an
instrument that only knows a ceiling reports the same files forever while the number the user asked for stays
unreachable.

- **Carry two numbers: a TRIGGER (when the instrument speaks) and a TARGET (what the file should reach).**
  Measured: a dietician fired at 85% with ranked proposals, while the operator's ask was "get these to 40–50%".
  Nothing in the tool could express that — a file at 40% was invisible, and a 97% file produced proposals that
  were individually correct and collectively insufficient.
- **`NO RULE FIRED` is a null result from the RULE SET, not a clean bill for the FILE.** When every file returns
  it, the rules have been exhausted: what remains is either genuinely load-bearing or needs a different
  mechanism. Say *"the rule set cannot decide this"* and escalate, rather than letting a reader conclude the
  file is fine. Reporting it at 97% capacity without that sentence is the confusing half of an honest tool.
- **A plan a human cannot reach is a defect in the instrument.** If the honest answer is "50% is only possible
  by moving standing rules out of memory into skills", say that and name the split — roughly 60% by cutting
  duplication and stale entries; below that requires re-architecting, not trimming. **Measure duplication across
  seats before proposing cuts**: entries copied near-verbatim into every seat's file are the cheapest real win.
- **Any output line that names a document must point at a live path.** Measured: every report instructed seats
  to trim "per `01-HANDOFFS/memory-trim-protocol.md`", and only an archived copy existed — carrying caps two
  revisions stale. **Check the path in the same change that writes the message**, and read `_archive/` presence
  as evidence the doctrine MOVED, not as the doctrine.

## Recall's corpus is not its write root — measure it before blaming the retriever

**A memory provider's read path and its write path are two different questions.** When one setting answers both,
pointing it at the whole library fixes recall and scatters every new note outside its owner's domain; pointing it
at the owner's directory keeps writes correct and searches almost nothing.

- **Give the provider a separate read root** (`corpus_root`), defaulting to the write root when empty so existing
  behaviour is preserved exactly, plus an env override for tests. A missing corpus path must **warn and fall back**,
  never silently collapse recall to zero.
- **Print the file count the retriever actually loaded, per profile, and compare it to the library.** Measured: four
  seats were searching **3 / 7 / 1 / 4** files against a 6,000+ note vault, and one seat's "BM25 over the vault" was
  BM25 over a single seed note. Nobody had ever printed the number.
- **Score recall with an expected-path test**: each case names the note that holds the answer, and it is a hit only
  if that path is in the top-K. *"Related" is how a system gets credit for an answer it did not retrieve.* A
  retriever that cannot be constructed is `COULD NOT MEASURE` — **absence of data is not a score of zero**.
- **A memory product must beat a plain filesystem before it is worth adopting**, and the published benchmark says
  that is a high bar (filesystem + grep outscored a leading specialised product on LoCoMo). Do not shop for a store
  until your own recall has been measured.
- **Promotion and retirement signals must come from behaviour, not presence.** A line that merely persists is not
  important — only one that was *removed and then needed again* is. And report **injected bytes**, not note count:
  trimming archives into the vault, so trimming grows the count.
- **Depth before design: print the RANK DISTRIBUTION before rewriting the scorer.** If every expected target appears
  somewhere in the top-N (none "never found"), the retriever works and the complaint is about `k`, not about
  ranking. Measured: 19 of 30 cases in the top 5, 23 in the top 20, **0 unfindable** — so widening the result count
  took the score 63% → 73% for a one-line change, while every re-ranking idea measured zero.
- **`k` is a token cost, not a free win — check what consumes it per turn.** Where the retriever's top-k is injected
  into the prompt on every non-trivial turn, raising 5 → 10 adds roughly a thousand characters to *every message*.
  Measure the score gain per added thousand characters and pick the knee; the last +1 case for another +1000 chars is
  usually not worth it.
- **Exclude growing append-only logs from the retrieval corpus; do not cap note length.** A log file is the classic
  corpus poison: measured corpus median **462 tokens** against one completions log at **281,754** — 600× the median.
  BM25's length normalisation then makes every normal note look short, and repetition beats relevance, so an answer
  note sharing 5 of 6 query terms still lost. Capping every note at 1,500 tokens scored **identically** to excluding
  the logs — because the giant notes *were* the logs. One fix, not two, and the log stays on disk where a file
  search can still reach it.

> The two-layer architecture this aims at, the retrieval-measurement recipe and miss taxonomy, the promotion/
> retirement design, the candidates evaluated, and the gates that must be proven before adopting a provider:
> `references/memory-architecture.md`.

### How far it can honestly go: classify PORTABLE vs FLOOR before cutting anything

**"Trim to 40%" is not an answer, because a percentage is not a property of the file — it is a property of what
the entries are FOR.** The measurable question is: *which entries must be loaded every turn, and how many
characters do they need?*

Sort every entry into two classes:

| class | test | what to do |
|---|---|---|
| **PORTABLE** | the entry names a path, script, filename or config key — i.e. **the vault already holds the detail** | move the long form into one vault note and leave a pointer (15–40 chars saved per entry, often 100+) |
| **FLOOR** | identity, a hard rule, or a preference with no other home | **stays. This is the minimum the file can reach without the agent forgetting what it is.** |

**The FLOOR share is the honest answer to "how low can it go?"** Measured on both files of one seat: memory had
~41% portable and a ~56% floor, so 55–60% was achievable; the user file had **0% portable and a 97% floor** —
**so it could not be trimmed at all, and the only real fix is deciding which fact the user no longer wants known.**
Saying that plainly is more useful than a target number that cannot be reached.

**Procedure, in this order — the verification comes BEFORE the shrink:**

1. Snapshot the file (`cp` to `state/memory-pretrim-<stamp>.md`) so a bad trim is one `cp` from undone.
2. Write the long forms into ONE vault note (e.g. `00-HQ/memory-detail-<date>.md`) with a section per topic.
3. **Assert every fact is present in that note before touching memory** — grep one distinctive token per entry
   (`x-opencode-session`, the blocks/day number, the cron id). A pointer to a note that lacks the detail is a
   deletion wearing a citation.
4. Patch each memory entry down to a pointer that names what left and where it went.
5. Re-run the gauge and record both numbers (before → after) in the same reply, so the move is visible.

**The gauge:** `profiles/gentech/scripts/memory-gauge.py` prints, per file, fill %, headroom, PORTABLE count and
chars, and the FLOOR chars/%. Run it before proposing any trim and after performing one — `--json` for a machine
reading. **Its value is that it ends in an action ("move N chars of portable entries") instead of a percentage.**

### A proposal-only instrument will always read as broken

**A tool that can only PROPOSE looks to its user like a tool that will not act.** Measured: a nightly dietician
printed proposals twice a day for weeks while the operator said, correctly, *"it's finding issues but it's not
actually activating to trim."* The script had an `archive()` (a copy) and **no write path at all** — no apply, no
rewrite, not one line changed by design.

- **Name it for what it does.** A tool that measures is a GAUGE; a tool that measures and edits is a DIETICIAN.
  Shipping the first under the second's name guarantees the user reports it as broken.
- **If it cannot propose honestly, it must not propose.** Rules built for one file shape (bare filenames, dated
  history, duplicate keys) return `NO RULE FIRED` on dense declarative facts every run — **a checker with the same
  output on 100% of its inputs is measuring nothing**, and the honest fix is fewer rules or a different mechanism
  (the PORTABLE/FLOOR split above), not more regex.
- **End a null result with the ACTION, never with a shrug.** `NO RULE FIRED … so this needs the seat to choose`
  reads as *nothing to do*; measured, that exact line printed twice a day while three seats sat at 96–98% and
  nobody acted. The same finding plus *"ACTION: consolidate BY HAND — merge same-topic entries, push detail to the
  archive; a rule cannot decide which facts matter"* gets acted on. **A report that names no action gets no action.**
- **Every message that names a path must point at a live one.** A report instructing seats to trim "per
  `01-HANDOFFS/memory-trim-protocol.md`" is worse than no instruction when only an archived copy exists.

### The actuator must land on EVERY seat, and it must refuse more often than it acts

**Giving the instrument a write path fixes the seat you are on. The other seats keep the copy that only proposes.**
Measured: after a relief step was added to the memory wrapper, that wrapper was **2,199 bytes** while three other
seats ran a **231-byte** copy of the older one — one seat in four could act, the rest still printed the same
proposals twice a day, and every report read healthy because each wrapper exited `0` and printed something.

- **Ship the wrapper to every seat and verify by what each one INVOKES, not by the file existing:**
  `grep -n 'relieve\|--execute' profiles/*/scripts/memory-dietician.sh`. A size gap across copies that should be
  identical is the tell that one seat was upgraded.
- **Relieve `MEMORY.md` only, never `USER.md`.** A fact about the user is not a size decision; a relief pass that
  can reach the user file will eventually delete a preference to save forty characters.
- **One entry per over-cap file per run, verbatim, into a dated archive, ledgered.** A pass that empties a file to
  hit a target deletes the judgement the file exists to hold.
- **It must be able to refuse.** When every entry is load-bearing, the correct output is a refusal that says so —
  that is the honest answer for a seat whose file is dense with standing rules, and an actuator that always finds
  something to cut is cutting the wrong things.
- **Verify by the ARCHIVE, not by the number.** The moved text must be readable in the archive file, with a header
  saying only its location changed, before the memory size is reported as improved. A size that drops without an
  archived counterpart is a deletion wearing an improvement.
- **Relief is a floor, not a diet.** It returns a file to breathing room; it does not reach a percentage target.
  Say which of the two the user asked for — most asks for "keep it from filling" are answered by the floor, while
  "get these to 40%" needs the PORTABLE/FLOOR split above, not more frequent relief.

### An alarm at one threshold and an actuator at another leaves a band nobody can act in

**Read the two numbers out of the two scripts before believing a report.** If the nightly report speaks at 85%
while the actuator only acts at 90%, every file in that five-point band generates a warning that nothing on the
box can resolve — and the reader learns the warning is noise, which is how a real fill gets ignored.

- **Make the report's threshold and the actuator's trigger the SAME constant**, or state the band in the report
  (`over 85%, actuator acts at 90%`) so the reader knows why nothing moved. A warning without a hand is worse than
  silence: it spends the reader's attention and returns nothing.
- **Check which files the hand can actually reach, and say so when a file has none.** A relief pass restricted to
  `MEMORY.md` will never touch `USER.md` — correctly, because a fact about the user is not a size decision. The
  consequence must be printed: *"USER.md at 96% — relief will not touch it; a seat must consolidate by hand."*
  Without that sentence the output reads `NO RULE FIRED` and the reader has to discover the exclusion themselves.
  **A file with no hand is a defect in the SYSTEM, not in the file.**

### When the hand must be a model, the applier must be deterministic — a COVERAGE MAP is the contract

**The user file has no rule that can merge it: two entries that make the same point about a person have to be
fused by reading them.** That is a legitimate place for a model — and the only safe shape is *the model proposes,
a script writes*.

- **Require a machine-checkable coverage map, not prose.** Every input entry index must appear in exactly one
  output entry (`{"target": "…", "entries": [{"from": [1,2], "text": "…"}]}`). A gap is a refusal; a duplicate
  is a refusal. **A silent deletion cannot pass, because the indices stop adding up before anything is written** —
  arithmetic, not trust.
- **The applier backs up, archives the pre-merge text verbatim, ledgers before/after hashes, and rolls back if a
  post-write re-read disagrees.** Reference implementation: `/opt/data/scripts/memory-merge-apply.py`
  (`--dry-run` / `--execute`); exit `0` applied, `2` refused, `3` instrument error.
- **Fixture the refusal paths before letting it run on a live file.** Complete map applies; a dropped index and a
  duplicated index both refuse with the missing index named; a 1:1 map round-trips **byte-identical** (proves the
  rewrite is lossless). An applier tested only on the happy path is an applier that deletes quietly.
- **Gate the model run on a byte-stable probe.** A monitor script that prints the over-cap files (no timestamps —
  prove it by running it twice and comparing `md5sum`) suppresses the agent entirely while nothing crosses, so the
  consolidation costs nothing on the days it is not needed. Pipeline mechanics: `cron-health-standard` §Pipelines.
- **Never let the model retry with a looser map after a refusal.** A refusal means the map was wrong; report it.
  Loosening until it passes converts the guard into decoration.

## Spilling beats deleting — and it needs a two-sided instrument

**Overflow does not have to be destroyed and remembered; it can be FILED and indexed.** Move confirmed entries
into `<vault>/11-Mess Hall/memory-spill/<seat>/<date>.md` and leave **one pointer line** naming what left and
where it went. Reversible by construction: the text is in the vault, the pointer carries the path.

**The metric that makes this trustworthy has two columns, and the second one is the point:**
`memory_chars` next to `vault_memory_chars`, sampled on a period.

- **memory down + vault up → the fact moved.** Working.
- **memory down + vault flat → the fact was LOST.** *Identical from the memory side*, and this is the failure
  the instrument exists to catch. A report that only shows memory shrinking reads as success either way.

**Sample hourly into a CSV, not into a message** — the curve is the experiment, and a daily alert would show
the endpoints after the fact had already gone.

## A restart is not a memory event — know what actually reloads

| what | survives a restart? |
|---|---|
| memory files on disk | ✅ yes, and they are re-read |
| config.yaml | ✅ yes — **but see the ownership trap below** |
| skills on disk | ✅ yes |
| an in-flight turn | ❌ gone |
| your "current plan" | ❌ gone — write it down BEFORE restarting |

**⚠️ Write the plan down before a restart, even a small one.** An agent that restarts mid-task and
reconstructs its intent from memory usually reconstructs it wrong — it rebuilds the *summary* of the
work, not the *next step*.

## ⚠️ The config ownership trap

**A running process owns its config keys and will write its in-memory copy back over a hand edit.**
This is not theory — a fleet edited `fallback_providers` out of five config files, and four minutes
later all five were rewritten with the key restored plus an extra entry appended.

**Rules:**

1. **Never hand-edit a key a process manages.** Use the command that owns it (`hermes config set …`).
2. **`HERMES_HOME` selects the profile — `HERMES_PROFILE` does not.** A loop that sets `HERMES_PROFILE`
   and calls `hermes config set` writes to the SAME profile every time while reporting different ones.
   **Verify by reading the path the command prints, not by trusting the variable you set.**
3. **After any config change, re-read the file.** A successful write message is not a persisted value.

## Restarting safely

**Before:**
- write down what you were doing and what the next step is
- back up the files you changed, with a timestamp in the name
- check nothing is mid-turn

**After — measure, don't assume:**
- is the process actually new? (uptime / PID start time)
- does a real turn work? (not just "the port is open")
- does the **silently-broken** thing work? (the one that failed without an error before)
- re-read each config value you changed, from disk

**⚠️ The most informative signal after a restart is a thing that *should* have changed and didn't.** If
a config edit appears to have taken but the behaviour is identical, the process did not load it.

## Silent failure is the default failure mode

The pattern to watch for: **a plausible-looking value that resolves to nothing.** It does not throw. It
does not log. The feature just never works, and looks identical to a feature nobody used.

`stt: provider: nous` silenced every voice note on every seat for weeks. `image_gen: provider: nous`
left image generation with no provider at all. Neither produced a single error.

**So: validate against the schema (the source list), not against intuition. And test the credential —
a commented-out key matches a naive search exactly like a live one.**

## Learned on gentech-treasury (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

- **A cap alarm is often a DUPLICATION alarm — search for the second copy before cutting a fact.** Measured: a
  USER file went 81% → 93% → 98% inside a day while gaining **no new information about the user** — the same rule
  had been written twice, in two sessions, each time looking like a fresh fact. Merge same-subject entries (keep
  every distinct clause), and drop anything `SOUL.md` already carries as non-negotiable; that is the cheapest cut
  and it loses nothing. Report which entries changed meaning, not just the byte drop.
- **An archive named `…REVERTED` is not evidence a revert happened — read the LIVE file.** Measured: a trim
  archived three entries to `<seat>-memory-trim-REVERTED.md` whose header says *"every entry below was REMOVED
  from live memory"*; the accompaniment was restored, the memory file was not, and the missing set included the
  freshest, highest-stakes entry. `grep` the live file for one distinctive string per archived entry, and
  `md5sum` the archive against a pre-trim copy. The archive's NAME is a claim like any other.

