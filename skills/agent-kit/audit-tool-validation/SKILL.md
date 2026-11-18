---
name: audit-tool-validation
description: "Use before acting on an audit scan. Classify every hit."
version: 1.0.0
author: Gentech
license: MIT
tags: [audit, verification, false-positive, checker, measurement, provenance]
metadata:
  hermes:
    tags: [audit, verification, false-positive, checker, measurement, provenance]
    related_skills: [guard-verification, claim-provenance, falsifiable-tests, verification-probe-execution]
---

# Audit-Tool Validation

An audit scan arrives as a number: "46 problems across 38 files". The number is a claim about the
artifact **and** a claim about the tool. Treating it as a work list is how a careful agent spends a day
fixing things that were never broken — and how a real gap gets buried under noise nobody re-checks.

## When to use

- A peer hands you an audit result with a count, a tool, and a recommendation.
- An existing checker, linter, link-scanner or detector shows findings you are about to act on at scale.
- You are about to adopt a scan as a recurring check.
- A previous audit's number is being quoted as settled.

## Procedure

### 1. Reproduce the count yourself

Run the tool on the same target before reading the handoff's list. A number you did not produce is a
number you cannot defend, and reproduction is also the first check that the tool even runs.

### 2. Classify EVERY hit — before fixing anything

Walk the findings and put each into exactly one bucket, naming the mechanism:

| bucket | meaning | what you do |
|---|---|---|
| **real** | the defect exists | fix the artifact |
| **false positive** | the tool misread its own input | fix the tool |
| **already handled** | the item is declared/accepted by design | confirm the declaration is visible |

A count with an unknown false-positive rate is not a work list — it is a rumour with a number
attached. Report the split, never the bare total.

### 3. Know the standard extraction defects

These three account for most false positives in text-scanning tools, and every one of them looks like
a genuine finding until you read the line:

- **Scope-blindness.** A pattern matched over free text finds its token wherever it appears: in a
cross-reference that names another owner (`other-skill/<pattern>`), inside a repo path or URL, in an
example. The tool resolves it against the wrong base and reports absence.
- **Declaration-blindness.** If the sanctioned remedy for an accepted gap is to *declare* it, a tool
that cannot read declarations scores the declared item identically to a silent one. That is not neutral:
it removes the only incentive to declare.
- **Convention drift.** The tool assumes one naming or formatting convention; the corpus has three. The
mismatch surfaces as a cluster of findings in exactly the files that were written by a different hand.
- **Root-blindness.** A checker that searches a fixed list of roots reports everything outside them as absent,
  so its own blind spot is published as the corpus's lie. Measured: an audit over a 70-item work list returned
  **38 "missing target"** verdicts; widening the roots to the whole tree cut it to **10**, and several of those
  were fragments. **Before believing any "missing" verdict, resolve one basename against the entire filesystem
  once** — if the file exists somewhere you were not looking, the finding is about your roots.
- **Path-splitting.** A naive file-name regex stops at the first space, so `11-Mess Hall/registry.md` becomes
  `Hall/registry.md` and can never resolve. Capture the whole token, strip a `https?://host/` prefix from
  anything that is really a route, and validate by **existence**, not by the shape of the match.
- **Normalisation collapse.** A duplicate detector that compares *normalised names* (strip every non-letter, so
  `00-HQ` and `HQ` both become `hq`) reports a name similarity as a duplication. **Prove duplication by SHARED
  FILENAMES, never by a similar name.** Measured: the pair reported as duplicates held 566 and 26 entries with
  **zero filenames in common** — wholly disjoint — and the smaller one was the live home of a queue written by
  **seven scripts**. Acting on that finding would have broken the queue while consolidating nothing. Demote pure
  name similarity to a separate `similar_names` field the reader can see and judge, and keep `duplicates` for the
  two states that are real: same filenames in both places, or more than one redirect-only shell for one
  destination.
- **Destination-blindness.** A redirect or "moved" signpost is prose: it names the destination folder, then lists
  the files that moved **by bare filename**. Resolving those filenames against the *scan root* reports every one
  of them dead, because by definition they left that root. Resolve a bare filename inside the destination the
  note itself names, and keep the scan-root reading as a fallback, not the primary. **A false positive here is
  the most expensive kind: it says a lossless move lost something, which is the one claim a signpost exists to
  disprove.**

- **Structural pairing (off-by-one).** Extracting a value from markup you did not author: the field and its
  label are ordered by the page's LAYOUT, not by your regex. A regex that anchors on the label and then takes
  the next value silently pairs every item with its **neighbour's** value. Measured: each card rendered its
  price badge *before* its `<h3>`, so heading→next-price reported **5 of 7 prices wrong, two effectively
  swapped, "a billing-grade error"** — on a page where **all 18 values matched the manifest exactly**. That
  report went to the user and came close to blocking a launch. **Parse by BLOCK, not by proximity:** split the
  document on the repeated container element, take every field from inside ONE block, and hand-verify one case
  before reporting any derived number. **A finding that says "every single item is wrong" is a parsing bug
  until proven otherwise** — real defects cluster, instruments fail uniformly.
- **Catch-all read as health.** A host that answers **every** path with `200` and byte-identical content makes
  any status-based audit report a perfect bill of health, including for links that do not exist. Probe a path
  that cannot exist and hash it against the real one **before** trusting any `200`: if the hashes match, every
  URL on that host is the same page and the audit measured nothing. Measured: an "all 8 links resolve 200 ✅"
  verdict was worthless — `/<domain>/this-does-not-exist-xyz` returned the same 18,148 bytes as the homepage.
  **State which of the two worlds you are in**, and prefer a fix that makes the host honest (ship a `404.html`)
  over a workaround that keeps the lies coming.
- **Threshold from the wrong layer.** A limit taken from a **display truncation** is not a validation limit, and
  every artifact that exceeds it is reported as a defect. Measured: a frontmatter checker asserted the
  description field's limit was **60 characters** — the width of a table cell in the tool that *renders* the
  field. The loader's actual constant was **1024**, so the check flagged **145 healthy artifacts** and inflated
  the run from 98 real findings to 242. **Read the validator, not the formatter:** `grep` the engine for the
  constant (`MAX_*_LENGTH`, `len(...) >`, `[:N] + "..."`) and take the number the code *enforces*. A  `_truncate(x,
  60)` in a table renderer is a layout choice; the `if len(...) <= 1024` beside it is the rule. **When a finding
  set is dominated by one class, suspect the constant before the corpus** — a rule slightly too tight produces
  exactly the uniform, plausible-looking list that a real defect never does.
- **Declared-absence blindness — the negated mention.** A scanner that greps prose for a token cannot tell an
  assertion from a **correction of that assertion**. A document whose job is to say *"this tool is absent"* or
  *"`hermes version` is not a command"* carries the exact string the rule hunts, so it is scored as if it claimed
  the thing. Measured: two skills were flagged purely for the sentence *"this section describes machinery that is
  currently absent"*, and a command rule kept flagging its own repaired sentence after the correction was written.
  **Skip a mention whose line negates it** — read that line for absence markers (`absent`, `not deployed`, `does
  not exist`, `removed`, `superseded`, `example`, `placeholder`) — and print the suppressed hits, because a filter
  that hides findings is a second blind instrument. The tell: the count goes UP when you document a fix.
- **Alias read as fabrication.** A command list parsed out of `--help` is not authoritative about aliases: a
  documented `gui` that resolves to `desktop` is reported as invented. **Resolve an unknown by RUNNING it and
  accepting non-empty help** — one subprocess call per unknown candidate converts this class to zero.
- **Self-reference and substring containment.** A skill's own NAME appears throughout its own body, so a
  reference rule scores the artifact as citing something missing: measured, `browser-trace` was flagged for
  naming `browser` and a skill's own `name:` frontmatter was read as a reference to a skill of that name.
  **Exclude the subject's own name before matching**, from both the content and the frontmatter. The same
  defect bites file-name searches: `grepping` for `grant-scanner.py` matches **inside** `devgrant-scanner.py`,
  so "four files still reference the retired tool" was four false hits against one repurposed name. **Match on
  a token boundary, never a substring** — and when a rename supersedes a name, re-grep with the boundary before
  reporting leftover references.
- **Vocabulary-blindness — the checker recognises fewer ways of closing than the corpus uses.** Any rule that
  counts *unacknowledged / unresolved / unsigned* items is really asserting "no closure marker is present", and
  it is only as good as its marker list. **Two artefacts that both say CLOSED can score opposite verdicts** because
  the corpus grew a new heading the checker never learned. Measured: one seat closed its two oldest escalations
  with `## STATUS: ANSWERED — closure record`, timestamped and evidenced; the SLA check (which knew only
  `## Receipt` / `## Agreement` / `## Supersede`) kept reporting them **8 days silent**, and a second checker on
  the same notes re-reported them as "nobody was asked to agree". Two instruments, one night, same blind spot.
  **Before publishing a backlog count, enumerate the closure markers actually present in the corpus**
  (`grep -hoE '^#{1,4}\s*[A-Za-z: -]{3,40}' <corpus> | sort | uniq -c`) and check every high-count heading against
  the rule's list. **A blind spot here is the expensive direction: it reports cooperation as silence, and it
  teaches the answering party that replying does not register.** The mirror-image check matters too — after
  widening the list, re-run against a genuinely open artefact and confirm it still fires; a matcher that accepts
  everything turns real work into a green report.
- **Existence asserted for GENERATED artifacts.** "The path it names does not exist" is a defect only when the
  reader is told to *run* it. Split the class by what the reader does with the path: a `.py`/`.sh` must exist
  (SCRIPT — a defect), while a state file, log or cache under `state/`/`logs/`/`cache/` legitimately appears only
  after its producer runs (DATA — cannot be a defect). Measured: one over-broad "missing path" class carried 55
  findings; the split left **12 real** and **40 that could not have been**. **Report DATA as a separate bucket and
  never let it count toward the work list** — merging the two is what makes a scan look hopeless.

### Auditing a WORK LIST, not a corpus: absence is often the assignment

When the thing under audit is a to-do list, "the file it names does not exist" proves nothing on its own — a
build item that says *write*, *create*, *add* or *build* expects absence, and flagging it inverts the item's
meaning. Bucket by the verb before bucketing by existence:

- **create/build/write items** — absence is the task. Check instead whether the *subject* already exists (it may
  have been done already).
- **fix/remove/rename items** — absence IS a contradiction: the thing cannot be fixed if it is not there.
- **Report three buckets, never one total** — `evidence present` / `unverifiable from prose` / `names an absent
  target` — because only the middle bucket tells the reader how much still needs a human read.

### 4. Fix the instrument, then the artifact

Order matters: fixing artifacts against a blind instrument leaves the false positives in place and the
real ones indistinguishable next run.

- **Make the tool resolve what it was misreading** (scoped tokens, declarations, external paths) rather
than deleting the rule.
- **Keep the contract stable** — same exit codes, same meaning — so the fleet's habit of reading the
tool still works.
- **Pair every relaxation with a planted-defect control**: plant the defect the new rule must still
catch and assert the tool fails on it. A checker that stops crying wolf by going deaf is the worse
outcome, and it looks like success in the diff.

### 5. Then fix the artifact, with a sanctioned remedy per item

- **Restore** when the missing thing exists elsewhere at the *same* identity (same path within its own
owning unit, another copy of the same artifact) — a restore, not a substitution.
- **Correct the pointer** when the reference names the wrong base but the same artifact.
- **Declare** when no copy exists anywhere, in a place the next reader and the next scan both read.
- **Never repoint at something similar.** A wrong pointer answers with confidence; a declared gap does
not. That is the whole difference between a fix and a plausible-looking one.

### 6. Adopt the scan as a standing check — gated on change, not on the count

A recurring scan that repeats the same accepted findings every run gets muted, and a muted check is
indistinguishable from a clean one. Record the accepted baseline (findings **and** declared), then speak
only on movement: a rise is a regression, a fall is a fix. Verify the monitor's own delivery path once,
deliberately, before trusting its silence.

### Age items by a clock the measured artifact cannot reset

**A backlog counter aged by `mtime` can be silenced by touching the file it is complaining about.** That is
the one direction of error that hurts: the finding disappears exactly when someone starts working on it, and
an *unfixed* item is hidden by any unrelated edit — a typo fix, a status header, an automated sweep.

Measured: a note 2.08 days past the reporting floor vanished from the next run the moment it was patched to
add the very block the report was asking for, and the same reset was hiding a second, unfixed note entirely.
Run both clocks over the same corpus and the counts differed — 50 by the immutable clock, 49 by mtime, two
items hidden. **The honest number was the larger one.**

- **Use a clock the artifact cannot rewrite:** the date embedded in the item's own name, a first-seen ledger
  written once, or a commit's author date. Fall back to `mtime` only when no immutable clock exists, and say
  so in the output.
- **Do not report a fall as a fix until you can show the item is covered, not gone.** After closing one
  finding, re-run and check the *reason* it left the list — a block that now passes is a fix; a changed
  timestamp is not.
- **A count that moves when nothing was fixed is a statement about the clock.** When a sweep or a rename
  changes the total, look for the timestamp before taking credit.

## The presence-check class: a keyword match is not a fact

The most expensive audit errors are not missed findings — they are **confident findings produced by a
pattern that matched the token instead of the property**. Every one reads as evidence, and each sends
you to fix, delete, or trust something that was never in the state you reported.

**The rule: a presence check must test the EFFECT, not the NAME.** If you cannot exercise the thing,
say `UNMEASURED` — never report the match as the state.

### The five shapes it takes

- **The commented line.** `grep -q 'FAL_KEY' .env` matches `# FAL_KEY=…` and reports a credential that
does not exist. **Anchor to the assignment form (`grep -q '^FAL_KEY=' .env`) and then test the value
by calling the provider.** A dead key and a live key look identical in a file; only a request tells
them apart.
- **The word in prose.** A regex matching `script-only` or `run: python3` flags a job described as a
script — but the same words appear in a *reasoning* job whose prompt says "the script output is the
fact." **Require the prompt to BE an instruction** (starts with the imperative, short, one command, no
analysis verb), never merely to mention the word.
- **The provider without the product.** `provider: nous` in a fallback chain is flagged as a spend
risk — but `nous` serving a `:free` model cannot bill. **Classify the pair, not the provider.**
Uniformly-red checks get ignored, and a check nobody reads is worse than no check.
- **The phrase used as a key.** Deduplicating headings on a shared sentence fragment reports three
unrelated items as one duplicate. **A join key has to identify the thing, not the words around it** —
verify against the record each hit points to before reporting a duplicate or a merge.
- **The legitimate repeat.** A prose-integrity rule for a doubled word fires wherever one token follows an
  identical token — so it fires on a markdown heading ending *"…against Brave"* followed by a paragraph
  starting *"Brave at $0.005"*, on a real compound (`over over-provisioning`), and on a real command
  (`forge script script/DeployAll.s.sol`). **A repeat must be a whole token bounded on BOTH sides, inside one
  line of prose.** Check line by line (never let `\s+` match a newline), skip headings, list markers, tables
  and fences, and require the second copy to end at a genuine token boundary — `\b` alone accepts a hyphen
  and a slash, which is exactly where the legitimate cases live. **A heading boundary is where a repeated word
  is most likely and least wrong**, so crossing one manufactures the false positive and hides the real one.

### The tell that you are in this class

**A negative control.** Run the identical check against a value you know is wrong. If garbage produces
the same output as your subject, the check is reading the token, not the property.

Measured: an API key endpoint returned `APIKey_InvalidAPIKey` for a real key **and for `ck_totally_invalid_xxxx`**
— identical. That symmetry proved the key was rejected, not merely under-scoped. A *different* error for
an empty header proved the server was reading the key at all. Two cheap probes converted a guess into a
finding.

### Where the match hides

- **Combined flags and escaping.** The same shallow match appears in shell: `unzip -oqd` parsed as a
filename, a `\s+.*` block matcher that swallows blank lines and runs into the next YAML key (one
config counted three times), `dirname` applied twice so every profile reported as `data`.
- **The tool's own display.** When a tool redacts its output, a failed string match is evidence about
the *display*, not the file. Read the bytes before concluding the file changed.

## The behaviour-inference class: a static read cannot tell you what a job DOES

Any audit that infers **runtime behaviour from source text** — "this prints every run", "this guard fires" —
is producing a hypothesis, not a measurement. Measured: one such audit produced **four false violations in a
single sitting** against correct code (header-only read, two failed multi-line regexes, thin wrappers judged
instead of their targets, an 18-line shim treated as a program).

**The rule: a behaviour claim needs a probe. If you cannot run the thing, say `UNMEASURED`.**

- **Probe by running it twice and counting bytes.** `SILENT` (run 2 empty) / `REPEATS-UNCHANGED` (identical
twice — the real finding) / `CHANGES-EACH-RUN` / `UNKNOWN`. Probe read-only scripts only, with a hard timeout.
- **Follow the indirection.** `exec`, `run_path`, and `CANONICAL = "..."` make the file you opened a pointer,
not a program. **Line count is the wrong test for a wrapper** — an 18-line shim whose body is a docstring
passes any size check. Ask: does it forward, and print nothing itself?
- **Walk the lines to find a gate.** An early exit sits under an `if`; one clever multi-line regex matches
nothing and accuses correct code.
- **The probe overrides the parser.** `VIOLATION` + probe `SILENT` → downgrade; + `REPEATS-UNCHANGED` →
upgrade. Print the downgrades so the reader knows which verdicts are load-bearing.
- **The tell you are in this class:** findings keep changing as you improve the parser while the artifacts
never change. A real defect is stable under better instruments.

Full probe recipe, the indirection table and the gate walker: `references/behaviour-vs-source.md`.

### Silence on EVERY input is a statement about the rules, not the corpus

**A rule-based proposer that reports "nothing to do" on 100% of its inputs has not measured anything** — it has
told you its rules never matched. The tempting read is "the corpus is clean"; the correct read is
"these rules do not describe this corpus".

Measured: a nightly memory-trimmer printed `NO RULE FIRED` for every file, every run, for weeks. Loading the
script as a module and running each rule over the real entries gave the answer in one pass: **0 matches for every
rule** — not because the entries were exemplary, but because the rules were written for a corpus of bare
filenames and dated history, while the actual corpus was dense `key = value` facts whose only sensible cut is a
**rewrite**, which none of the rules could express. A second rule compared values only when two entries carried
an *identical* key string, so a key annotated with its measurement date never compared to anything.

- **Count matches PER RULE, not findings per run.** `import` the checker, run each rule over the real corpus,
  print the count beside the rule name. Four zeros is a diagnosis; one zero is a fact.
- **Ask what the rule was designed to match, and whether the corpus has that SHAPE.** A rule that is correct for
  one artifact type is silent on another, and silence is indistinguishable from a pass.
- **A proposer whose only fallback is "the longest entry" should have no fallback.** Naming load-bearing content
  as "the biggest" deletes the thing that matters; refusing to guess is the honest behaviour, and if that means
  the tool always refuses, the tool is the thing that needs building, not the corpus that needs cutting.
- **Do not fix this by lowering the threshold.** The repair is a rule that expresses the real edit (consolidate
  two entries into one, rewrite a fact shorter), and a proposal the operator approves — not a looser match that
  starts proposing bad cuts.

## The shape-matching class: a credential detector that matches SHAPES matches everything

A rule that fires on a *shape* (`0x` + 64 hex, a 40-char base58 run, `-----BEGIN … PRIVATE KEY-----`) has no
notion of context, so it fires on bytecode, documentation, placeholders and — most reliably — **on its own
source**. Measured: a weekly secret audit reported **891 findings, 705 of them CRITICAL**, and classifying all
891 produced **zero real secrets**. The control had been exiting "findings" every week for months, which is why
nobody had read it.

**Classify by context before assigning severity**, and print the reason beside every suppressed hit so the
filter stays auditable. **Build artifacts · config references · placeholders · test paths · published test
keys · the scanner's own source · values repeated across many files** — the class table, the per-class rules
and the selftest gate live in `references/secret-scanner-false-positives.md`.

Three rules from it that apply to any shape-matching detector:

- **Match the detector's own source out first.** A regex literal inside the scanner is the most embarrassing
  false positive in this class, and it is trivially excluded by path.
- **Frequency is a classifier, never a verdict.** One leaked key pasted into ten tutorials is still a leak.
- **State what was suppressed.** "N findings, 0 real, suppressed by class" is auditable; a silent filter is a
  second blind instrument.

### Prove the CLASSIFIER before trusting its silence — selftest in both directions, every run

A rule slightly too wide manufactures silence, and silence is what a control is trusted for. Give the
classifier a `--selftest` with cases in both directions, run it **before** the scan, and exit non-zero if it
fails. The case list, the co-occurrence trap and the hand-clearing failure are in
`references/secret-scanner-false-positives.md`.

### A control that reports FINDINGS as a failure status cannot be trusted at all

If the checker exits non-zero on findings, the scheduler records `error` for every run — so **a dirty audit and
a broken audit look identical**, and the only way to tell them apart is to open the output nobody opens. Run the
scan, then run the classifier, and let the **classifier's verdict** set the exit code: findings that survive
classification are a failure; suppressed classes are a clean run that prints what it suppressed.

## Pitfalls

- **Acting on the count.** The number is the start of the investigation, not the end.
- **A severity label is a claim about the rule's aim, not about the hit.** 705 CRITICALs collapsed to zero real
  secrets once context was applied; report the classified split, and never forward a raw severity histogram.
- **Suppressing by pattern instead of by class.** Deleting the rule hides the next real hit; adding a context
  classifier keeps the rule and removes the noise, and the printed reason keeps it honest.
- **Fixing artifacts against a tool you have not audited.** You will "fix" correct citations and leave
the blind classes untouched.
- **Deleting the noisy rule instead of teaching it scope.** Suppression without a control is how a check
goes quiet for months.
- **Reading a tool's self-report as its behaviour.** Exit 0 means the tool ran, not that it looked.
- **The tool correctly flagging your own prose.** Documentation that reproduces a path pattern is a
citation as far as the scanner is concerned; describe the pattern instead of reproducing it.
- **Quoting the raw total in the handoff.** Report `real / false positive / declared`, plus what you
changed in the instrument — otherwise the next reader inherits the rumour.

## Precision is part of the measurement — always state the false-positive rate

A scan's raw hit count is a claim about the corpus AND a claim about the tool's selectivity. Report the split,
never the total.

Measured: a mechanism-citation scan over ~2,500 documents returned **7,931** hits. Roughly **55% were never
mechanisms** — API routes (`/health`, `/v1/models`), CLI commands, and OS paths (`/dev/sda1`,
`/proc/<pid>/environ`). The actionable set was ~1,300 distinct items. **A list nobody can act on is worse than
no list: it buries the real findings and teaches the reader to ignore the tool.**

- **Gate the extractor on "is this even a claim of the kind the rule covers?"** Require the form that can only
  mean the thing — a file-like tail, or a path under a root you own. Drop routes, commands and foreign paths.
- **Report distinct items AND citation counts.** One mechanism cited thirty times is one thing to fix.
- **Identical totals across DIFFERENT queries mean the queries collapsed, not that the corpus has equal pain.**
  Measured: six different failure-mode hypotheses returned the exact same count — a hand-rolled URL encoder had
  mangled every one into the same generic match, and the ranking built on it looked perfectly plausible. Use a
  real encoder, keep queries to simple quoted phrases when the backend silently degrades parenthesised groups,
  and **make the tool refuse to print a ranking when three or more queries share a total.** A broken instrument
  producing a confident table is the failure this whole skill exists to prevent.
- **Never publish a total you have not sampled.** Reading ten hits by hand kills a bad extractor outright; no
  aggregate will.

## A dead citation is not a missing capability — separate STALE from GONE

A documentation-drift scan asks "does this cited thing still exist?". The dangerous answer is a single `DEAD`:
it conflates an **old address** with a **lost asset**, and those need opposite responses.

- **GONE** — nothing of that name exists anywhere live. This is the real finding.
- **STALE** — the cited path is dead but the artifact exists under a new root, or a live file of that name
  exists elsewhere. **A doc fix, not a loss.**
- **SUPERSEDED** — the named artifact is gone **and its function is alive under a different name.** Measured:
  a scanner a skill told readers to run had been replaced by two scripts that both run in the audit bundle; the
  capability was healthier than the doc claimed and the only defect was the citation. **This bucket is the one
  that gets mis-filed as GONE, because a name-search for the old tool returns nothing.**

**Distinguish SUPERSEDED from GONE by asking what the artifact DID, never by searching for its name.** Name a
file, grep for it, find nothing — that sequence proves only that the string is absent. Ask instead: *is the
behaviour still happening?* `grep` the schedule and the callers for the FUNCTION ("who scans handoffs and
emits returns?"), not the filename. If the behaviour runs, the finding is a citation to repoint.

Measured after a host migration: most hits were STALE — every pre-migration root had a live equivalent — while
a handful (a watcher, a scanner, a health check) were genuinely GONE. Collapsing them into one bucket would
either have buried a real loss inside a migration chore, or sent someone to rebuild something already running.

- **Check for a migrated equivalent before calling anything gone.** A mechanical prefix map (old root → new
  root) resolves most hits and converts an alarming number into a to-do list.
- **STALE can also UNDERSTATE.** A name that exists only inside a vendored dependency or an engine package
  resolves as "stale" while the instruction is genuinely dead. **Read every STALE hit before closing it.**
- **A file that resolves anywhere is not proof the INSTRUCTION resolves.** Distinguish the artifact from the
  rule that names it.

### ⚠️ Repointing by NAME-SIMILARITY is how a correct warning gets deleted

**A document that says a capability is ABSENT may be right.** Read the candidate replacement's actual surface
before you edit the sentence — a similarly named script is not the missing one.

Measured: a compliance skill warned *"nothing enforces write pacing"* and cited a `github-write-gate.py` that
did not exist. A `gh_guard.py` in the same directory looked like the answer, so the obvious fix was to repoint
the paragraph at it. Reading it first settled the opposite: `gh_guard` exposes **only a read path** (throttle,
`Retry-After`, budget floor) with **no write entry point**, and its two importers are read-only jobs. **The
warning was true; only the filename was wrong.** The correction was to name the real file and say which half
exists — not to repoint at it and silently withdraw a standing warning.

- **Verify the CAPABILITY, not the filename.** Enumerate the candidate's public entry points and check the
direction you need (read vs write, get vs post). A file whose name contains the missing noun proves nothing.
- **Withdrawing a warning is a behaviour change, not a doc cleanup.** If the code cannot enforce the rule, the
  sentence stays; only the path changes.
- **Name the half that exists.** "The read half exists in `X`; the write half does not exist anywhere" is a
  verdict a reader can act on. "See `X`" is a claim that it is covered.
- **A similarity score is not evidence.** Name-similarity ranking invites a bulk replace, and a fuzzy cutoff is a
  guess wearing a number. Measured: of five candidates matched at ≥0.72 against the installed corpus, **two would
  have been wrong** (`subagent-driven-development`→`test-driven-development`, `agent-recovery`→`agent-economy` are
  different concepts), so only three were repointed and the rest were left dangling **on purpose until read**.
  **A dangling reference is visibly unanswered; a wrong pointer is invisibly answered.** When a dangling set is
  large, file it as its own item with the rule *one sentence at a time*, never as a batch find-and-replace.



## The finding class: a rule whose MECHANISM is gone reads as mandatory and is unenforceable

The most misleading audit result is not a false positive. It is a **rule still written as mandatory while the
thing that made it executable no longer exists.** Nothing was abandoned by decision, so nobody noticed — and
every reader still treats it as a live obligation.

- **Audit the rule–mechanism PAIR, not the rule's existence.** Extract the concrete things a rule names — a
  path, a script, a command, a service — and test each against the live system. **A rule citing a missing
  script is a rule nobody can follow.**
- **Classify the outcome as UNENFORCEABLE, not VIOLATED.** "The fleet ignores this rule" and "this rule cannot
  be executed" look identical from outside and demand opposite fixes. Reporting the first when the second is
  true sends the reader to chase compliance instead of restoring a mechanism.
- **Concentrate on the cluster, not the total.** Measured: 1,303 distinct dead mechanisms, but the
  highest-citation cluster was one subsystem's four scripts — the single actionable finding, and invisible in
  a raw total.
- **A measurement that crashes and is never scheduled is indistinguishable from a clean bill of health.** If
  the auditor dies on a run nobody reads, its silence is not a pass. Check the auditor's own exit code against
  a known-bad input before trusting any quiet.
- **Make the audit terminate.** Index an expensive lookup once instead of re-walking the tree per item: one
  scan went from 452s — never finishing on the real corpus — to 2.3s. **An audit that does not finish measures
  nothing**, and a slow one gets skipped.
