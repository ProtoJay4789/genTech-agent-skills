---
name: config-vs-behaviour-audit
description: "Use when auditing whether config matches behaviour."
tags: [audit, cron, measurement, verification, findings, registries, fleet]
trigger: "When asked to audit or improve an existing system rather than repair it — 'would we build this the same way today?', a capability inventory, a registry or baseline claim, a delivery-mode review, or 'did the restore land?'."
related_skills: [cron-health-standard, cron-truth-layer, claim-provenance, verify-after-every-action]
license: MIT
version: 1.0.0
author: Gentech
metadata:
  hermes:
    tags: [audit, cron, measurement, verification, findings, registries, fleet]
    related_skills: [cron-health-standard, cron-truth-layer, claim-provenance, verify-after-every-action]
---

# Config vs behaviour — auditing an estate without filing false findings

**Every claim in an audit is one of two kinds: a DECLARATION (a config field, a registry row, a directory
listing, a tool that exists) or a BEHAVIOUR (what actually runs).** They diverge in both directions — a
field can be empty while the behaviour is present, and a row can exist while nothing uses it. An audit
that reports a declaration as a behaviour files findings that are confidently wrong, and the owner then
re-plumbs working machinery.

This is the measurement half of an improvement audit (the question *"is this still the best way?"* rather
than *"is it broken?"*). The checklist itself is not restated here; what follows is how to make its
numbers true.

## When to Use

- An audit or review is requested on a system that already works — *"would we build this the same way
  today?"*, a capability inventory, a delivery-mode or cadence review.
- You are about to state a count, a coverage figure or a capability claim about a live estate (jobs, skills,
  registries, restored tools) in a document another person will act on.
- A registry, standard or baseline is offered as the answer to "what do we have?" — measure its coverage
  before repeating it.
- A compound claim arrives from another owner ("it is configured and loaded", "the estate runs N jobs") and
  you are the one who has to be right about it.
- You are writing into a shared findings document alongside other owners.

This skill governs the MEASUREMENT. For a job that is failing, the repair doctrine lives in
`cron-health-standard`; for the provenance of a single number, `claim-provenance`.

## Procedure

1. **Enumerate the LIVE estate, with a timestamp.** Read the raw store (`cron/jobs.json`, the registry,
   the manifest) — not the CLI's summary, which hides mode fields. **Record the time of the read.**
   An estate mutates mid-audit: another owner can add or migrate a row minutes after your first read, and
   two owners can edit seconds apart. A count with no timestamp is unreproducible. Re-read at the end and
   report the delta instead of silently updating the number.
2. **Answer your checklist per item, and spend "unchanged" only on items you probed.** A findings list of
   nothing but defects is not an audit of an estate, it is a list of accusations. Say which items you
   verified as *correct* and name the artefact that proves it. Report the working architecture with the
   same weight as the defects — that ratio is the auditor's credibility, and the counter-evidence is what
   stops the owner over-reacting to a real but narrow finding.
3. **Before quoting a capability or mode count, ask which FIELD it came from and where the behaviour
   actually lives.** Mode fields (`no_agent`, `continuity`, `context_from`, `monitor_script`,
   `monitor_url`) are declarations. A job can gate every single run *inside its script* — empty stdout
   delivers nothing, a state file written only on change — with every field empty. Label such a count
   **field-level** and read the scripts before concluding a ring is over-running the LLM. Corollary: in an
   all-script ring there is no LLM for a gate to skip, so adding the field buys declaration and no saving;
   say that rather than proposing a re-plumb.
4. **Check registries and recorded baselines for LIVE coverage, not row count.** A registry is
   authoritative only where its ids match live ids. Compute `len(live ids ∩ registry ids) / len(live ids)`
   and report the **ratio** ("0 of 13 live ids covered"), never "the registry has 130 entries" as though
   that were coverage. A registry whose entries match nothing is a fossil of an earlier estate: its rows
   still explain history, but they triage nothing. The same applies to a numeric baseline printed inside a
   standard — it was a measurement when it was taken, so re-measure before quoting it in the present tense,
   and never let a registry's row count stand in for the size of the live estate (the two can differ by an
   order of magnitude and look identical on the page).
5. **Existence is not wiring.** For any tool, sentinel or script the fleet claims to have, grep every
   profile's `scripts/` and the job store for a reference to it, and name the job whose `script` or prompt
   invokes it. **0 references = unwired** — report "restored, not wired", never as a capability the fleet
   has. A file whose mtime is *today* is a prime suspect: a restore is not a deployment.
6. **Count behaviour from the run record, not from the config.** Per-run output bodies are the evidence of
   what a job actually did (it spoke, or it was silent). Count them with a pattern that survives the
   document's own styling — a bolded label in the body makes a literal `grep 'Status: silent'` match **0**
   files and manufacture a confident verdict that is exactly backwards. See `references/estate-probes.md`.
7. **Trace the delivery chain before calling anything silent.** For a job that appears to deliver nowhere
   (`deliver=local`): (a) read the wrapper's own header — quiet-hours and state-file contracts are usually
   documented in the script comment; (b) name the *consuming* job that reads the artefact, by grepping that
   consumer's own prompt for the path; (c) only then read the failure branch. The finding is usually much
   narrower than the first reading.
   - On a wrapper that writes a state or heartbeat file, check the FAILURE branch writes it too. An early
     `exit $rc` ahead of the state write leaves the consumer reading the **previous run's PASS** — that is
     the real hole, and it is invisible from the config.
   - `failure_deliver: null` is **unset, not a decision**. A job with nobody named on "who finds out if
     this dies" has an unanswered question, not a configured answer — propose the explicit value.
8. **Split a claim that is only half true.** When the request asserts a compound fact ("the provider is
   configured on disk and the key is loaded in the running process"), re-measure each half and mark them
   separately: "the key half holds in all seats' `.env`; the config half is refuted on this seat (0
   occurrences, byte-level read, not a parse)". Laundering a half-true claim into a single verdict is the
   failure this procedure exists to prevent — and the same instinct applies to a probe you cannot complete:
   an unreadable measurement is **UNKNOWN**, never zero.
9. **Propose; do not edit the thing you audit.** An audit that mutates its subject cannot be reviewed by
   anyone else. Write each finding as `item · axis · current → proposed · why`, one line. When something is
   a design option rather than a defect, say so and state the trade explicitly (what is lost by making the
   change) — an owner can only decide between options if both sides are on the page.
10. **Filing into a shared, multi-owner document:** append to YOUR section only, leave every other
    owner's section byte-identical, and verify that on the way out (grep their headings and your own line).
    Finish with one ACK line — the findings are the deliverable, the ACK only says they are filed. If your
    measurements corrected the audit's own framing, include that correction: on a shared document it is the
    single most valuable line you can add.

## A config-bearing DOCUMENT is an estate too — audit its claims like any other

A skill, runbook or routing table that names providers, endpoints or capability stacks is a set of
**declarations about behaviour**, and it rots the same way a registry does. It is also the most
dangerous place for staleness to sit, because it loads and instructs on every use.

- **A named provider with no credential is a dead route that reads as a live one.** Verify each named
  provider against the credential store (`grep -c <PROVIDER>_API_KEY <seat>/.env`), not against the
  plausibility of its name. A documented stack can describe a provider whose key was never present.
- **Precise figures are what make a dead section look researched.** A routing table with a per-tier
  model ladder and a monthly cost total reads as measured; an obviously empty section does not. **The
  more credible a stale block looks, the more urgently it needs the credential check** — and a stale
  ladder with dollar figures is worse than no ladder, because it invites no suspicion.
- **Replace a dead block; do not annotate it.** Adding "(deprecated)" beneath a wrong table leaves the
  wrong table as the thing a reader skims. For a block whose whole content is the claim, delete the
  content and state what replaced it.
- **Fix a naming change as NAMES, not as a retirement.** When a room or service keeps its identifier and
  changes only its name, routing to that identifier stays correct — recording it as retired breaks
  working routes. Separate "this ID is dead" from "this ID is live under a new name".
- **A live label is not a live seat.** A folder, lane or chat name that still receives traffic is not
  evidence that the team, group or owner it names still exists.

- ❌ **Auditing a document's prose but not the credentials it depends on.** The declarations are the
  easy half; the key's existence is the half that decides whether any of it runs.

### Audit the RULE–MECHANISM PAIR before you audit compliance

**When asked "are our processes being followed?", the first measurement is not who skipped a step — it is
whether each rule still has a live implementation.** A rule can read as mandatory long after the script,
endpoint or path it names has gone, and then it is **unenforceable, not violated.** Those are different
findings with different repairs: the first is a restore, the second is a conversation.

**The mechanism of silent decay — state this when you report it:** *a step that cannot be executed gets
skipped, then stops being expected.* Nobody decides to abandon the rule. Its transport dies, the first few
skips look like an oversight, and within weeks the absence is the norm and no one notices the rule is
still written down.

- **Extract every MECHANISM a doc cites and test it for existence on the live box** — absolute paths, script
  filenames, service names, endpoints. Report the pairs, per document.
- **Separate GONE from STALE, and never collapse them.** *GONE* = no live copy anywhere (a real capability
  loss). *STALE* = the cited address is dead but the file exists under a migrated root (a documentation fix).
  Collapsing them either buries real losses in a pile of typos or inflates the count until nobody reads it.
  **Also flag the single dominant cause when there is one** — a post-migration root change can account for
  most STALE hits at once, and that makes the repair mechanical instead of per-document.
- **Apply a PRECISION GATE, or the audit's own output is the defect.** A path in prose is only a mechanism
  claim if it could *be* one: require a file-like tail or a root the estate owns. **URLs, API routes, CLI
  subcommands and OS paths are not filesystem claims.** Measured: without the gate an audit returned ~7,900
  "missing" mechanisms of which roughly half were routes and commands that were never mechanisms at all — **a
  list nobody can act on is worse than no list, and it discredits the real findings inside it.**
- **Apply that gate on EVERY route to the same list.** A filter added to one matcher and not to the branch
  that appends to the SAME collection leaves the noise at full volume while the fix reads as ineffective.
  This is the guard-both-paths rule; see `falsifiable-tests`.
- **A name resolving is not a rule working.** Decide *STALE* on an exact path where you can, and **read every
  STALE hit before closing it** — a same-named file inside a vendor's engine package or a dependency tree
  will resolve a helper that the estate does not actually have. **Report the label as "the name resolves",
  never as "the rule works".**
- **Rank by citation count and say that is what you did.** Frequency says how often the docs *mention* a
  mechanism, not how much it mattered. State the denominator and the ranking basis so the reader is not
  reading importance into a popularity count.
- **Prefer to fix the doc when the mechanism merely moved, and restore it when it is truly gone.** For a
  genuinely missing monitor or watcher, the honest options are rebuild or strike the reference — **a rule
  that names a missing script is a rule nobody can follow**, and leaving it written is how the next reader
  wastes an afternoon looking for it.

## A config write that SUCCEEDS is not a config that is VALID

**The setter accepts any string. The consumer silently does nothing with an unknown value.**
Measured: `config set <feature>.provider nous` printed `✓ Set …` — and `nous` was not in the
supported set at all. Every seat that lacked its own block inherited that value, the feature never
ran, and it failed with **no error in any log** because "provider not recognised" has no failure
path — the setting simply produced nothing.

**The procedure when a feature silently does nothing:**

1. **Read the ENUM from the source, not from the setter.** The valid values are usually named in a
   comment or a literal list beside the defaults (`config_defaults`-style module). The CLI's
   acceptance message is evidence that a string was stored, nothing more.
2. **Check the engine exists in the interpreter that will RUN it** — not in your shell, not in a
   sibling venv. `python -c "import <engine>"` **using the service's own interpreter path**. A
   feature can be `enabled: true` with no implementation installed anywhere near it.
3. **Check what a seat INHERITS, not only what it declares.** With a shared default config and
   per-seat overrides, one invalid default silently disables the feature on every seat that did not
   override it — and those seats look per-seat-healthy because nothing in their own file is wrong.
   Enumerate the effective value per seat, not the file contents.
4. **Distinguish "configured" from "in use" with a process check.** A setting written after the
   service started has not been read. Compare the file's mtime against the process start time, and
   say which of the two you verified — `/proc/<pid>/environ` is often unreadable, and an
   unreadable check is UNKNOWN, never "probably fine".
5. **Prefer the provider/path that needs no privileged install.** A root-owned interpreter with no
   package manager is a wall, not a puzzle: switching the documented config to a provider that
   needs no local install is a legitimate fix, and it should be stated as a substitution with its
   trade-off (e.g. audio now leaves the host for transcription — say so).

6. **A setting needs a READER, not just a WRITER.** Grep the code that CONSUMES the key and confirm it reads
   the same source the setter writes. Measured: a documented option lived only in an object attribute that
   nothing in the engine populates, so every consumer fell back to a hardcoded default and the config file was
   decoration — for months, on every seat, with the value set correctly in every file. The tell is a setter
   writing file A while the consumer reads variable B; the fix is to give the option the same loader its
   siblings already use. **A setting is implemented when a consumer reads it, not when the CLI confirms it.**
7. **A path setting can be TWO questions — what to READ and where to WRITE.** Before repointing one, enumerate
   every consumer. Measured: a single root fed both the search index read and the note write, so widening it
   to fix recall would have simultaneously scattered writes outside the owner's write domain. Neither half is
   acceptable alone, and the fix is two settings, not a chosen failure — say which one you split and why.
8. **A profile-scoped write can land on the WRONG profile and still print `✓`.** The success message names the
   path it wrote, and that path is the thing to read — not the message. Measured: three writes issued with the
   wrong profile selector each confirmed `✓ Set …` and each went into the *same* seat's config, because the
   selector variable the CLI honours is not the one the caller assumed. The damage is silent in the worst way:
   every file is valid, every message is green, and the intended targets are untouched.
   - **Verify the TARGET, not the status.** Re-read each seat's file and grep for the key; a setting that is
     absent from the file you meant to edit is an unwritten setting, whatever the CLI said.
   - **Resolve the effective value through the ENGINE's own loader**, with the variable that loader actually
     honours — that is the only reading that matches what will run. An env var accepted by your shell but
     ignored by the loader produces a verification that tests your assumption instead of the system.
   - **Assert the per-object difference you expect.** If N seats were meant to receive the change, the proof is
     N files that differ from each other in the way you intended (each seat's own lane/path), not N greps that
     each matched the same file. A loop that prints one identical line N times is the tell.
   - **When the setter cannot be trusted to route, write the file directly and re-verify through the loader.**
     Editing the known path with a backup is more auditable than a CLI whose profile resolution you have not
     confirmed — and it leaves a diff a reviewer can read.

**❌ Calling a feature "configured" because the config key exists.** The key is a declaration;
step 2 is the behaviour.

### A comment that ENUMERATES its own structure is a claim about the SET — test membership

**The rule–mechanism check above asks whether a named mechanism EXISTS. This one is subtler: the mechanism
exists, the set is short.** A docstring or inline comment says *"X and Y are retired"*, and the enforcement is
a literal `set` / list / regex that omits one of them. **Both halves read as correct in isolation**, which is
why the drift survives review — so the only detector is a membership test.

Measured, twice in one estate, in two different file types:

- A route builder's docstring stated that two specific paths *"are RETIRED and answer 410"*. The
  `RETIRED` set held **three other names** and neither of those two, so they answered **404** instead. The
  observable consequence is not cosmetic: a catalogue monitor reads `404` as *this seller's link is broken*
  and keeps probing — **650 and 580 requests in 2.7 days from 28 and 33 user-agents** — where `410 Gone`
  says *deliberately removed, stop asking*.
- A `.gitignore`'s own comment said the exclusion was *"scoped to media by TYPE, at any depth … notes
  (.md/.py/.json) stay tracked"*, and then listed a **whole directory**. That folder held **32 files of HTML
  dashboards and JSON data — not media** — so a rule promising they are tracked sat beside the line that
  excludes them from the backup.

**Rules:**

- **Read the enforcement structure immediately after any comment that explains WHY it exists**, and check every
  name the comment asserts is a member. The comment is a design statement; the literal is what runs.
- **Assert membership AND non-membership in one test.** A test that only checks "the retired ones are in the
  set" passes while a widened set silently retires a live route. Both directions, every claimed member.
- **One list, not two.** If the comment enumerates, either derive the enforcement from that list or delete the
  enumeration and point at the code. A comment plus an independent literal is two sources of truth and they
  will diverge.
- **Verify the OBSERVABLE consequence, not the constant.** For an exclusion/retirement list the thing a user
  sees is the status code or the absence of a file — `410` vs `404`, tracked vs ignored. Both look like a clean
  refusal in a log, and only one stops a crawler re-probing.
- **These cluster — sweep the same file for siblings** (`RETIRED` sets, allowlists, ignored paths, enums,
  deny-lists) once you find one.
- **⚠️ Decide WHICH half is wrong before editing.** Sometimes the comment is the stale half and the code is
  correct, in which case "fixing the code to match the comment" changes live behaviour to satisfy prose.
  Where the fix changes what the system does — what the backup carries, what answers 410 — **flag it and get
  the owner's word**; where it only makes the code match a promise already made to users, fix it.

## A RENDERED section is not a GATE — trace the display to the decision's INPUTS

**The most expensive version of this defect class: a report that renders N layers, and a decision that
consults one of them. Every section prints, so the board "looks layered", and nothing in it can change
the answer.** The tell is a sentence like *"posture: do not open a new position inside this window"* —
that is prose a human reads, not a branch the code takes.

**The test is the decision function's SIGNATURE.** Read the classifier/decider and list its parameters.
**A quantity that is not a parameter cannot affect the decision, no matter how prominently it is printed.**
Measured: a board rendered seven layers above and below the verdict, and the classifier took three
arguments — price change, range position, structure — none of which was the macro calendar it displayed a
posture for. The fix was not to reformat the display; it was to add the fourth parameter.

- **Check the call ORDER as well as the signature.** A gate computed *after* the decision it is supposed to
  constrain has already been made cannot influence it. Hoist the gate above the loop that consumes it, then
  pass the same value both to the classifier and to the change-tracker so the two cannot disagree.
- **Prove it by FALSIFICATION, not by reading the output.** Force each gate state and assert the decision
  changes: `clear → the permissive verdict`, `blocked → the restrictive one`, `absent → the restrictive one`.
  If every state yields the same verdict, it is decoration. Do not report "X is wired" on the strength of a
  paragraph appearing on screen under a heading.
- **An unreadable gate must FAIL CLOSED.** Absent, unparseable, stale or `None` all resolve to the restrictive
  verdict. **Defaulting to permission is how a gate stops being a gate** — and a `None` default that silently
  means "clear" reproduces the original defect one layer down.
- **Apply a SEVERITY FILTER the moment you widen the source.** A gate that fires on *any* record in a window
  will, as soon as the feed is broadened, start shutting on context-level noise — a sentiment print halting
  capital. **A gate that fires on everything is always shut, and an always-shut gate is indistinguishable
  from a broken one.** Rank the records, gate on the top rank, and still record the lower ranks for display.
- **Give the gate a staleness ceiling and age it from the producer's stamp.** A stopped producer must make the
  gate abstain, not leave yesterday's permission standing. Age from the content (`generated_at`), never from
  mtime — see `derived-artifact-integrity`.
- **When every item shares one verdict, say it once.** Printing the same word on twenty rows reads as twenty
  alarms and trains the reader to scroll past the section; state the decision once, name the reasons, and let
  the per-row mark carry the thing that actually varies.
- **If a displayed value never changes, suspect the SELECTOR, not the data.** A glyph keyed on a status field
  that is constant across all rows will print the same colour forever, and that looks identical to a working
  gauge reading a stable system. Colour the quantity that moves; label the one that does not.

**❌ Reporting "the layer is wired" because the section renders.** Rendering is the display path; wiring is
whether the value reaches the branch. They are separate paths and only one of them was checked.

## Pitfalls

- ❌ **Counting declarations and calling it behaviour.** The plausible-looking version of a false finding.
- ❌ **Quoting a registry's row count as the size of the live estate.** Two different metrics, one number.
- ❌ **Reporting a restored tool as a deployed one.** Grep for the reference; name the job that runs it.
- ❌ **A grep pattern that can never match**, returning 0 and inverting the verdict (bolded labels,
  differently-worded status lines). Verify a counting pattern against a file you *know* is non-silent
  before you trust its zero.
- ❌ **A count with no timestamp** on an estate that changes under you.
- ❌ **Filing only defects.** No verified-correct items and no stated trade reads as an agenda, not an audit.
- ❌ **Letting a repeated request re-trigger the work.** A second delivery of the same ask is not a new
  event: re-measure the delta, reaffirm in one line, and do not file a second artifact — two artifacts with
  two digests is how an owner ends up counting one item twice.
- ❌ **Editing the estate you are auditing**, even to fix an obvious defect you just found.
- ❌ **Trusting a comment that enumerates its own structure.** A docstring naming the members of a `set`,
  an ignore file explaining which paths are excluded, or an allowlist's prose can each disagree with the
  literal beside them — and both halves look right read alone. Membership test, in both directions.

## Reference

- `references/estate-probes.md` — the concrete probe set: live enumeration with timestamp, registry
  coverage ratio, wiring check, silence counting from run bodies, delivery-consumer trace, failure-branch
  read, and the per-field capability census.
