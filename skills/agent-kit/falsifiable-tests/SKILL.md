---
name: falsifiable-tests
description: "Use when writing or debugging a test, guard, or assertion."
trigger: "Writing a new test or assertion, adding a regression guard, or when a test FAILS and you are about to change the code it covers."
tags: [testing, verification, assertions, false-red, harness]
version: 1.0.0
author: Gentech
---

# Falsifiable tests

## A check that has never been seen to FAIL is not a check

**Before trusting any clean result from a checker, detector or audit script, plant the failure and
watch it go red.** A checker that points at a path that no longer exists, silently skips a source it
cannot read, or exits 0 in the mode a human reads will report "✅ clean" for months and mean *nothing
was examined*. The result looks identical to health, and that identity is the whole danger.

**Do this in three directions, always:**
1. **Clean** — the real input passes. (Proves it doesn't always cry wolf.)
2. **Planted defect** — the exact failure it exists to catch, in a scratch copy. Must exit non-zero and
   name the specific item.
3. **Unreadable input** — delete a source, break a permission. Must NOT read as clean. *"Unverifiable"*
   and *"drift"* are different words for a reason; both must fail.

### Pitfalls that produce a fake green

- **A half-planted failure passes.** If you plant a broken flag but leave the line's own `RESOLVED`
  annotation beside it, the tool correctly says clean and your test proves nothing. **When the planted
  case passes, suspect the plant before the tool** — then re-plant the failure completely.
- **Missing input handled by `continue`**, not by a finding. The most common silent skip in any scanner.
- **Exit-code inversion:** `sys.exit(1 if quiet else 0)` exits **0** in the mode a human reads, so the
  cron wrapper cannot tell drift from clean. The exit code must not depend on verbosity.
- **A regex that matches in isolation but not in the file** is usually a flag-scope bug: inline `(?i)`
  does not propagate across an alternation, so `^`-anchored branches compile without `re.M` and never
  match a mid-file line. Pass `re.I | re.M` explicitly.
- **Accept the shape the producer actually writes, not the shape you imagined.** If the first real ack
  is prose and your matcher demands a table, the matcher is wrong — and it teaches everyone to write
  for the tool instead of for the reader.
- **A declared argument that is never USED** is an interface that lies. `argparse` accepts it, the
  usage line documents it, the call succeeds — and the artifact the caller asked for is never written,
  so the caller silently gets nothing and re-derives by hand. **A flag is not implemented because it
  parses; it is implemented when its output exists.** Falsify by running the tool with the flag and
  `ls`-ing the target: no file, no flag. Worse than a missing option, because a missing option errors
  and an inert one looks done to everyone who reads the interface instead of the artifact.
- **A fixture that omits a directory the scanner needs** fails the CLEAN case; that is a bad fixture,
  not a bad tool. Fix the fixture before "fixing" the tool.

### The mirror defect: a check that can never go GREEN

A control that always fails is as damaging as one that always passes — it is the same zero-information
signal, and it trains the reader to skip the section just as fast. The usual cause is
**non-reproducible output** in the thing being compared.

- **A generated artifact must be BYTE-IDENTICAL on re-generation.** Any wall-clock timestamp, run id,
  hostname, absolute path or nondeterministic ordering embedded in the output makes `--check` fail on
  every future run for a reason that has nothing to do with drift. Proven: a catalog generator wrote
  `generated_at` to the second, so its own drift check reported "DIFFERS from the live manifest"
  immediately after a clean rebuild — forever. A **date** was sufficient provenance; a timestamp was
  the bug.
- **Prove reproducibility the same way you prove falsifiability:** generate, hash, generate again, and
  require the hashes to match. A generator you have only run once is not known to be reproducible.
- **Distinguish "the artifact drifted" from "the artifact was rebuilt at a different second".** If the
  check cannot tell those apart, the check cannot be acted on.

### A verdict must be a SHARE, not an ABSENCE

When a script classifies something (good / poor / healthy / broken), the bar must be a **proportion of
real observations**, not the mere absence of the worst error class.

```python
# WRONG — "no 5xx" passes a route that answered 1 of 4,924 requests
if server_errors == 0 and served > 0:
    return "good"

# RIGHT — the denominator is every observation, and the share decides
if samples == 0: return "no traffic"
if served == 0: return "never worked"
if server_errors / samples > 0.05: return "poor"
worked = served / samples
return "good" if worked >= 50 else "partial" if worked >= 1 else "rarely works"
```

A label that a near-total failure can satisfy is worse than no label: it is published to a reader who
will trust it. **Ask of every threshold: what is the worst system state that still passes this?** If
the answer is "almost total failure with zero of one specific error", the threshold is an absence test
wearing a health verdict's name.

A test earns its place by being able to go RED for the right reason and GREEN for the right reason.
**A test that fails on CORRECT code costs as much as one that passes on broken code** — it sends you
to "fix" something that was never wrong, and it teaches the reader to distrust the whole suite.

Every rule below was hit while verifying a guard that was already correct.

**First reflex when a new test fails: suspect the ASSERTION, not the code.** Especially on a guard you
just wrote and reasoned about carefully — read the assertion again before touching the implementation.

## A selector that selects the WHOLE POPULATION measures nothing

The mirror of an absence test (which passes on near-total failure) is a **selection rule satisfied by every
observation**: it cannot discriminate, so its output is the input re-printed with extra steps.

Measured: a promotion pass proposed any item "seen on 3 distinct runs". Against the real corpus, **77 of 77
observations reached exactly 3 runs** — because the items persist until someone deletes them. The rule was
measuring *persistence*, which everything in the corpus already has.

- **After building any rule, scorer, ranker, filter or proposal engine, run it on the REAL population and print
  the selection rate before trusting it.** "It proposed 77 items" and "it proposed 3 of 77" are different
  products; only one of them is a filter.
- **Ask what a corpus member could DO to be excluded.** If no such action exists, the rule has no negative class
  and cannot rank. Redesign the condition around an event the corpus can actually perform (for a memory
  promotion: *removed, then re-observed* — not merely *still present*).
- **Both failure directions look like a clean run:** selects everything (no discrimination) and selects nothing
  (condition unreachable). **Silence is not evidence of health** — print the denominator and the selected count
  every run, even when both are zero.

### A threshold must come from the code that ENFORCES it, never from the surface that DISPLAYS it

A checker whose limit is invented fires on everything, and the noise hides the true positives. The limit is
not a design choice you get to make — **some loader, schema or API already enforces a number, and your check
must read that one.**

Measured: a length lint was given a **60-character** limit because that is the width of a table cell on the
rendering page, while the loader truncated at **1,024**. The lint reported 53 oversized entries; the real
count was 1, and it was buried.

- **Grep the enforcement point for the constant before writing the check** — the parser, schema, loader or
  `export` that consumes the value. Write the limit as a named constant beside the check and cite the source
  in a comment, so the next reader can verify rather than trust.
- **A limit chosen from the output surface is a rendering opinion.** A form field, table column, terminal
  width or character budget in a UI bounds what a human SEES; it never bounds what the system accepts, and a
  check built on it measures your own display instead of the artifact.
- **Print the limit and the distribution beside the findings** (`limit=1024, 1 item over, max=1180`). A
  finding count with no threshold in the output is unreadable, and an obviously-degenerate result (53 of 54
  failing) is the tell that the threshold is wrong — not that the corpus is bad.
- **When a check fires on nearly everything, suspect the constant before the corpus.** Same reflex as
  suspecting the assertion before the code.

### Do not pipe a state-writing script into `head` — SIGPIPE kills the writer

Verifying a script that persists state, `script.py | head -20` closes the pipe the moment the reader has enough,
and the process dies **before its state write**. Measured: a dedup check "failed" twice because the state file was
never created — the code was correct and the test method destroyed the evidence.

- **Redirect to a file, then read the file:** `script > out.txt 2>&1; echo rc=$?; cat out.txt`.
- **A missing state file is ambiguous** — it means either the writer is broken or the writer never finished. Only
  the exit code distinguishes them, so capture `$?` and never diagnose from the missing artifact alone.
- **The general form: a test that signals the subject early tests the signal, not the subject.** Anything long
  enough to be truncated or killed mid-flight (`head`, `timeout` without a cleanup path, a killed background job)
  leaves state that is indistinguishable from a defect.

## Compare like with like — a DEFINITION is not an INVOCATION

Ordering assertions are the most common false-red. A `def`, signature, or module-level constant sits
where it was **written**, not where it **runs**.

```python
# WRONG — _gas_precondition is a `def` near the top of the file. It sorts before main() regardless of
# runtime order, so this measures nothing and FAILS on a correctly-placed guard.
assert src.index("acquire_lock()") < src.index("def _gas_precondition")

# RIGHT — compare against the first statement that actually EXECUTES after the guard.
# (start the search AFTER the guard, or you may match an earlier unrelated call)
assert src.index("acquire_lock()") < src.index("subprocess.run(", src.index("acquire_lock()"))
```

A definition site says where code was **written**; only a call site says when it **runs**.

This applies to every source-order assertion: import-before-use, guard-before-side-effect,
config-before-read, lock-before-sign. **Grep for the CALL form, not the declaration form** — and
search from the right offset so you measure the intended occurrence.

### A MENTION is prose — and writing documentation can turn your own guard red

The same trap one step further out: a **comment or docstring that merely names the label** sits earlier
in the file than the code that emits it, so a bare-substring anchor matches the prose.

Measured: `src.find("[4a] PROVISION GAS")` matched a docstring at char 20,500 while the real `print(`
sat at 111,742 — an ORDERING assertion went red while the execution order was untouched. Worse, the
person who wrote that docstring was the person who had just changed the code, which is exactly when you
are least likely to suspect the test.

**The tell: your two operands are one MENTION site and one call site.**

- **Anchor on the statement that EMITS the label**, not on the label:
  `re.search(r'print\(\s*f?"[^"]*' + re.escape(label), src)`. Only real code can satisfy that; a bare
  substring also matches docs, comments, and dead text.
- **Do NOT delete the comment to make the test pass.** That is the tempting one-line fix and it trades
  real documentation for a green. The guard was wrong, not the prose. If the assertion changes at all
  it gets STRICTER or stays identical — never looser.
- **State the anchor's property as its own check** — "the anchors are PRINT statements, not comments or
  docstrings" — so the guard cannot quietly drift back to reading prose.
- **Then falsify the meta-check itself.** `SRC[:i].rstrip().endswith('print(')` never matches when `i`
  lands *at* `print(`; a green meta-check you never tested is one more unfalsifiable assertion.
- **Adding docs to a file is a change like any other — re-run the suites that parse it.** Source-order
  guards read the whole file, so a comment is load-bearing whether or not you meant it to be.

## Do not assert on state an earlier section deliberately MOVED

A suite whose sections share one state object fails when a preceding section legitimately changes that
state — and the failure names the wrong culprit.

Measured: a check read a counter immediately after the prior section had, **by design**, cleared it in
order to test the clear. Correct code, reported as broken, with a `None` that sent the reader hunting
a bug that did not exist.

- **Give each section its OWN fixture** (`tmp/b.json`, `tmp/key.json`), or explicitly re-establish the
  precondition at the top of the section.
- **A section that proves a CLEAR / RESET / RE-ARM destroys the evidence the next section wants.**
  That is the point of the section, which is exactly why the next one needs its own copy.
- **Read the value where you just wrote it.** If the check needs the entry that `refused()` created,
  create it in that section — do not reach for whatever is lying around.
- Sections that depend on each other's leftovers test the ORDER of your sections, not the code.

## The first red from a new test usually indicts the test, not the code

When a test fails on code you have just reasoned about carefully, **read the assertion before you
read the implementation** — especially when the implementation is a guard. The guard may be fine;
the test may be measuring the wrong thing.

Measured twice in one session:
- **Source order vs runtime order:** a test asserted the refspec validator was called before a
  function definition near the top of the file. A `def` is written where it is declared; it executes
  when called. The check failed on correct code because it compared a call site to a declaration
  site. The fix was to compare against the first statement that actually executes after the guard.
- **Prose vs emitted text:** a test searched the whole source file for the retired flag name and
  failed because the word appeared in a docstring explaining the retirement. The search matched
  a MENTION instead of an EMISSION. The fix was to anchor on the `argparse.add_argument()` call or
  the actual parse result, not on the bare word.

**Procedure when a new test fails:**
1. **Identify the two anchors.** One is the thing the test says happens; the other is the thing it
   says happens before/after.
2. **Classify each anchor as:** definition / mention (comment, docstring, string literal) / emission
   (statement that actually runs and produces the value or side effect).
3. **If either anchor is a definition or mention, replace it with the emission.** A definition site
   is where code is written; an emission site is where it has effect. Tests must measure effect.
4. **If the test becomes looser to make it pass, stop.** Loosening is not a fix; it is a downgrade.
   Either the code is wrong (change the code) or the test is wrong (change the test to a stricter
   emission-based check), but the assertion must not move toward always-passing.
5. **Re-prove the negative control after correcting the test.** A test whose false red came from a
   bad anchor may also be unable to catch the real defect. Plant the defect and confirm red.

## A bounded read turns its OWN BOUNDARY into a defect

A check that reads a fixed-size window out of a larger artifact manufactures a defect at the seam.
Anything just outside the window is invisible, so a record that legitimately continues the one above
it reads as "orphaned" — a false red on a correct artifact, produced entirely by the reader's slice.

Measured: a structure guard read a 260-line window while its "look back one line to see whether this
header is glued to the previous entry" rule needed a 60-line lookback, so a valid entry sitting one
line above the window's start was reported as orphaned. The document was clean; the window was not.

**The deeper mechanism:** the guard sliced `lines[-(260+70):]` intending 70 lines of context, then
searched only `range(max(0, i-60), i)` **inside that slice**. The context lines were present, but the
lookback search could not see past the slice's own first line — so a header six lines above the
window's start was invisible. **The 70-line context must be added to the EVALUATION window, not merely
to the printed snippet; the lookback must be able to reach N lines above the first judged line.**
A verdict that depends on the file's length is reporting length, not structure.

- **Size the read to the QUESTION, not to the file.** If the assertion needs context N lines above a
  match, the read must extend at least N lines beyond every match it evaluates — or read the whole
  artifact and slice only for printing.
- **Do not judge anything at the window EDGE.** The first and last records of any bounded read are
  where a seam artifact lives; either widen so they are interior, or skip them explicitly.
- **Re-run the fixed guard against a REAL defect before trusting the green.** A false-red fix that is
  never re-tested against a genuine violation can just as easily have made the guard blind.

## A fixture copied from a MOVING system tests the moment, not the rule

A live system's values change. Hardcoding one — "the book has 12 bins", "the wallet holds 0.0153",
"the position resolves to a curve" — makes the assertion depend on a state that was true when you
looked. Correct code then FAILS, and the failure names the wrong culprit.

Measured: a suite hardcoded a 12-bin book and expected it to resolve to the recorded shape. 12 bins
is a PARTIAL — correctly not that shape — so the check failed. The book had been 45 bins, was 13 at
one point, and 25 by the time the suite ran. The fixture was a snapshot wearing a fixture's name.

- **Derive the fixture from the RULE, not from a reading of the system.** If the shape must be a
  curve, construct a book that IS one; never copy whatever the live object happens to be.
- **A fixture reused by several sections should be the MINIMAL one for each question.** A section
  proving "unrecognised geometry classifies as empty" needs a partial; a section proving "the record
  shape resolves" needs a full one. One shared fixture cannot be both, and whichever section it
  fails names an innocent. Give each section the fixture its own question requires.
- **Assert the PROPERTY, never the current value.** "Every supported token's address is well-formed"
  survives a token being added; "token X is absent" does not.
- **An assertion that a fact is false because it is NOT YET true expires the moment it becomes
  true.** A check asserting "this must be unsupported until verified" passes until someone verifies
  it, then fails forever on a correct system. Write what must ALWAYS hold (no malformed addresses;
  unlisted symbols are refused), not the current status of an open question — and when such a test
  goes red, suspect the FIXTURE or the ASSERTION before the code, then verify the claim against
  ground truth (read the chain, the file, the API) BEFORE editing either side.
- **A comment that calls a hardcoded constant a live measurement does not make it one.**
  `AMOUNT_IN = 0.744 * 1e18  # half of the idle WAVAX` is a snapshot wearing a caption. The
  comment says it was derived from balance, so it reads like a rule; it is still frozen at the
  moment it was written. Name the constant honestly (`FROZEN_`, `SNAPSHOT_`) or derive it at
  runtime. When you remove a frozen constant, grep its name in comments and output strings —
  prose describing a mechanism you deleted is a false claim.

## Count suite health by EXIT CODE, never by grepping the output

A suite tree is not homogeneous. Some suites are `unittest` (they print `OK`), some print a custom
`RESULT: PASS — n/m` footer, some print only a summary line. Grepping for ONE of those shapes across
the whole tree silently scores every other kind as a failure.

Measured: a full-tree sweep reported 15 of 27 passing. Twelve "failures" had never failed — several
were `unittest` printing `OK`. Re-run by exit code: 25 of 27. The audit itself was the defect, and it
was one command away from a false alarm about a healthy tree.

- **Run each suite and read `$?`:** `timeout 400 python3 "$t" > out 2>&1; rc=$?` — that is the
  verdict the suite actually publishes.
- **Grep the output only for DETAIL (which checks failed), never for the VERDICT.**
- **Spot-check ONE reported failure by hand before publishing a tree-wide count.** If it passes,
  your counter is wrong, not the tree.

### A runner that DISCARDS a failing test's output makes every red a dead end

The runner captures each test's transcript and then throws it away on failure. The verdict is then
the only artifact — and the verdict is the one thing you already have, because you know it failed.

Measured: the runner wrote `printf '%s\trc=%s' "$f" "$rc"` on failure while the cannot-judge branch
right below it mined the SAME captured output for a reason. So a red test reported a filename and an
exit code and **nothing else**, and the only way to learn why was to reproduce the run by hand, blind.
The asymmetry was the bug: one branch used the evidence it had, the other discarded it.

- **A failure must print its evidence OR its path.** Mine the test's own most informative line
  (`FAIL|RESULT|Traceback|Error|assert`) into the summary, and write the full transcript to a named
  file. A verdict whose supporting output is discarded cannot be audited — and an auditor who must
  reproduce a run to see the reason will eventually stop reproducing it.
- **The same rule applies to every aggregated verdict**, not just test runners: a monitor, a sweep, a
  fleet audit. **If the summary is the only thing that leaves the machine, the detail must be in the
  summary or on disk.** `rc=1` with no reason is a refusal to explain, not a report.
- **A red from a non-hermetic test run during a live operation is a transient, not a regression — and
  "probably flake" is not a diagnosis.** Re-run the suspect tests individually, then re-run the whole
  suite once the system is quiet, and compare. Measured: a suite went `fail=2` while a live capital
  operation was in flight — its own summary showed a third test skipped because "the wallet went busy
  mid-section" — and the quiet re-run came back `40/0/0`. Both failing tests read live state, so they
  are **non-hermetic by design**; that is worth knowing before the next live operation, not after.
- **Do not let a red suite run unattended alongside a live operation.** It manufactures failures that
  teach the reader to ignore the suite, which is the same damage as a flake — and it can mask a real
  red that arrives in the same window.

## Prove the HARNESS before believing a green

A broken stub or fake can return the same verdict on every input — and when that verdict is a refusal,
it reads as a passing guard.

Measured: a hand-rolled fake delegated to a real object for an attribute the real one did not have, so
**every** case returned "unmeasurable" — which the first version of the test scored as PASS. Eight
identical refusals looked like eight successful refusals.

**Assert the harness can produce a KNOWN-GOOD case before asserting it refuses the bad ones.** Give the
test its own section for this. If every input path yields one verdict, the harness is broken, not the
code.

## A harness built from the PATCH's own constants cannot find what the patch missed

A matrix that imports the same allow-list, the same skip conditions, and the same routing table the
fix introduced is **the fix grading itself**. It passes on the exact input the fix mishandles, and it
looks like a full sweep.

Measured: a validation fix skipped one class of item to avoid false rejections, and the test matrix
passed that class *because it read the skip list out of the patch*. Ten of ten green, deployed, and
the live request immediately returned the old wrong answer for the skipped class. The harness and the
bug shared one assumption — which is the one thing a check exists to break.

- **Derive the case list from the LIVE source of truth** — the routing table, the manifest, the config
the service actually loads — not from the constants the patch adds. The patch's constants are the thing
under test.
- **Enumerate every INDIRECTION LAYER as its own case.** Aliases, routing maps, legacy path prefixes,
  and "native" shims are exactly where a `if <special case>: return` branch hides. A service reached
  through an alias is a different code path and needs a row in the matrix.
- **Generate a row per live route, both directions** — the shape that must be ALLOWED and a sibling
  shape that must be REJECTED. A matrix with only the reject cases proves the guard fires, never that
  it fires selectively.
- **Count the cases against the population, and print both numbers.** "10/10 correct" means nothing
  until the reader knows the population was 12 and which 2 were never listed.
- **A local harness green is a hypothesis; the live call is the experiment.** When the change is
  reachable over HTTP, run the real request against the real deployment before reporting, and treat a
  divergence as evidence the HARNESS was wrong — not that the deploy failed.

## A case set you AUTHORED is not blind — generate cases from CONTENT, never from names

The previous section covers a harness that shares the patch's constants. The next door is a harness that
shares the **author's naming**: you write the notes, then write the test questions from those notes, then
measure a change that keys on the notes' names. The suite cannot fail the change, because the questions
already carry the answer.

Measured: a hand-written 14-case retrieval suite scored a filename-weighting change at **79% → 93%**. The
same change on 30 questions generated from note **bodies only**, with the filename never shown to the model,
scored **63% → 63%** — exactly zero. The 14 points were leakage, and the tempting conclusion ("the change
works, the blind run is noisy") is backwards.

- **Re-earn every ranking/filtering gain on a case set produced without exposure to the signal under test.**
  Make the generator blind MECHANICALLY, not by good intentions: feed it only the body text, never the path or
  title, and map the expected target back afterwards outside the generator's view.
- **Filter the blind set too, or it measures nothing.** Drop cases whose target sits in an archive (a live note
  should outrank history and failing to proves nothing), whose target filename is generic (`README.md`,
  `SKILL.md`, `USER.md` — "found it" is not a ranking result), or whose question is context-free ("what triggered this auto-save?") — a question with no retrievable content cannot be answered by any ranker.
- **Report the SHIPPED number, not the harness's better one.** If the experiment scores 77% and the deployed
  configuration scores 73% because they search different corpora, publish 73% and say why the two differ. A
  number quoted from the favourable variant is the same defect as the leaked gain.
- **A suite's provenance belongs IN the suite.** Record generation method, seed, filter rules, and a hash of the
  question list beside the cases. A regenerate overwrites its own output, so without a hash a stale score can
  outlive the suite it came from and pose as current — a generator that silently replaces its artifact is one
  re-run away from publishing a number for a file that no longer exists.
- **Two suites with different scores is the finding, not a problem to reconcile.** State both with what each one
  can see ("79% on hand-written cases, which favour descriptive filenames; 63% on 30 blind cases") and let the
  weaker, more honest number carry the claim.

## A state override can invert a test

A test that simulates an input or a wallet balance can make the probe pass for a state you do not
actually hold, and fail for the state you do. The verdict is then **backwards**: the code is
reported broken in the real condition and reported working in an imaginary one.

Measured: a swap-route probe set `AMOUNT_IN = 0.744 WAVAX` while the wallet held 0.0186, then added
a state override that faked a 5 WAVAX balance so the oversized probe would clear. The result:
- 0.744 WAVAX (a size we cannot fund) quoted successfully;
- 0.018 WAVAX (a size we actually hold) failed the input transfer and reported
  "the route is genuinely down".

**Rule: a state override must represent a condition the real system can actually be in, and the
probe must be sized to a live value you hold.** If the test has to fake the balance to ask
"can WE swap?", it is not asking about you. Remove the override and size the probe from the live
state; a balance too small to probe is a READ failure (2), never a verdict (1).

**Corollary: when you remove an override, grep its name in the output text.** A message that still
says "simulated with a funded balance override" after the override is deleted reports a mechanism
that no longer exists, and a reader who trusts the message will believe the test is doing something
it is not.

## Every check needs a NEGATIVE CONTROL on the REAL artifact

The strongest guard is worthless if it can only fail on its own fixture. Prove it goes red by making
the genuine defect recur in the genuine source — then revert.

- **Neuter the guard, re-run the suite.** If it still passes, the suite is guarding nothing.
- **A control against a fixture copy proves nothing about the shipped artifact** — run the real entry
  point, re-invoking `__file__` as a subprocess if needed.
- **Do not mutate production to plant the defect.** Write to a throwaway copy; a test killed between
  plant and restore leaves the mutation live with nobody watching. Make the guard's root injectable
  (`os.environ.get("X_ROOT", <default>)`), and have the test **strip any test marker it finds at
  startup** — that is the only recovery path for a run that already died mid-window.
- **After hardening a check, re-run the negative control.** A hermeticity fix can quietly make the
  suite unfalsifiable.

## A falsification must not POINT at the real protected resource

The rule above — write to a throwaway copy — covers mutating the **code**. It does not cover the test's
**target**. A test that disables a guard to prove the guard works will, in that run, do whatever the guard
prevented — **at whatever path the test handed it.** If that path is the live resource, the falsification
CREATES the hazard it was written to rule out.

Measured, and it cost real material: a key generator refused to write private keys into the synced vault. The
guard **hardcoded the real vault root**, so the test exercising it passed the **live vault path**. The mutation
itself lived in a throwaway copy, exactly as this skill prescribes — and the mutated build still wrote two real
private keys into the vault, which a later sync carried off-box before anyone noticed. The failing SUITE
noticed, not the author.

**Parameterise the protected root and inject a scratch one in tests.** Production keeps the real default; the
test hands the guard a temp tree that merely *stands in* for the resource.

```python
def assert_outside(path, *, vault_root=None):     # default = the real vault
    root = (vault_root or VAULT_ROOT).rstrip("/")
    ...

# exercises the guard, and cannot reach production even when the guard is disabled
generate("seat", str(scratch / "vault" / "keys"), vault_root=str(scratch / "vault"))
```

- **A test that must break the thing it protects in order to prove it protects is a hazard, not a test.**
- **Check the guard DIRECTLY for the real resource** — `pytest.raises(G): assert_outside(REAL_ROOT)`. A pure
  check has no write path, so it stays safe under mutation and still goes red when the guard is removed.
- **Add a TRIPWIRE for the hazard itself, with a test that FIRES it** — scan the real resource for the thing
  that must never be in it and fail loudly. A guard nobody has watched fail is a guard nobody knows works.
- **Prove the fix by re-running the falsification, not by reading the cleanup.** After the fix, disabling the
  guard must still turn the tests red **and leave the real resource untouched**; that is the difference between
  a hazard fixed and a hazard merely swept.
- **Report the incident even when the cleanup is complete.** The artifact may already be in git history or
  off-box, and a quietly removed exposure is an unassessed one. State the severity and the evidence for it
  (here: never published in a roster, never used, and a different key from the real one) rather than "cleaned".

## A test must not PIN the bug it exists to catch

A test that asserts the **exact buggy expression** is present will happily re-introduce the bug
whenever someone "tidies" the implementation. It is a green that depends on the defect surviving.

Measured: a gas-topup test checked that `unwrap_need - (plan_wei / 1e18)` appeared in the source.
That was the **float-subtraction bug** that invented phantom swap legs from binary dust. The tool was
fixed to use integer wei subtraction, the test went red, and the only honest repair was to assert the
integer form was present **and** the float form was **gone**. Re-planting the old float form made the
updated test fail; the real source made it pass.

- **When a check fails after a code fix, inspect the assertion for the old defect shape.** The failing
  assertion may be a fixture-rot check that was actually pinning the bug.
- **Assert the fixed SHAPE and the absence of the old shape.** "Integer remainder exists" AND
  "float subtraction of wei counts is absent" is a strictly stronger check than either alone.
- **A test updated to match a bug fix should be harder to pass, not easier.** If the new assertion
  is looser than the old one, the test was not updated — it was downgraded.
- **A test that goes red on a correct fix is reporting on itself.** Fix the test, not the code,
  but verify that the updated test still catches the reintroduced bug.

## A test must be HERMETIC — never assert against the host environment

A positive control that reads the real installation path only passes on machines with that layout, so
it fails everywhere else for a tool that is fine. Build fixtures in a temp tree the test owns.

- Want to report host state anyway? Emit it as an INFO line that is **never AND-ed into the result**
  — and wrap it, or an exception in an informational probe becomes a failure and the false red returns
  through another door.
- **Test both directions of every refusal.** A boundary never tested in the direction it BLOCKS is not
  known to work; a boundary never tested in the direction it ALLOWS will happily block legitimate work.
- **State the denominator.** "No issues found" is unfalsifiable without a count — it renders the same
  whether you examined 400 files or 0. Print how many you read and fail when that number is zero.

## Testing a permission/read-failure path

- **Never use `chmod 000` while running as root** — root reads through it, so the test passes for the
  wrong reason. Use a **directory named `*.py`**: `open()` raises `OSError` for any uid.
- **`py_compile` / `ast.parse` passing is NOT the module importing.** A syntax check is blind to name
  resolution. A file compiles cleanly and still dies on import when a function is called at module
  scope but defined further down. Verify by importing:
  ```python
  import importlib.util as u
  s = u.spec_from_file_location('m', path); m = u.module_from_spec(s)
  s.loader.exec_module(m)          # the real check
  ```
  Better: run the tool's own `--help` or a dry run. A sweep reporting "N/N compile" has proven
  nothing about whether those files can RUN.

## A branch your fixture cannot REACH is untested — perturb the boundary to find it

Coverage is not a property of the assertions you wrote; it is a property of the STATES your fixture
can produce. A branch that only opens under a different state is invisible: every check passes, and
the branch was never executed at all.

Measured: a tool's "cannot proceed" branch was the one path that emitted none of the
machine-readable decision tokens its test asserted on. The test passed for months because its
fixture wallet held liquid balance, and the branch only opens when the balance is fully deployed.
Changing a boundary constant routed execution down an untested path and the check went red at once.

- **Change a boundary constant and re-run the suite.** Moving a threshold, a floor, or a default is
  the cheapest way to force execution down branches your fixtures never took. A suite that stays
  green through a genuine boundary change is not reaching the boundary.
- **Enumerate branches by STATE, then require a fixture per state** — not a fixture per function.
  "Has liquid balance / has none", "file present / absent / stale", "first run / repeated".
- **When a check goes red after a threshold change, suspect the FIXTURE before the code.** The code
  is often doing exactly what it always did; the suite simply never ran there.
- **A decision branch must emit its decision.** If a path answers "no", it still has to print the
  machine-readable token saying so — absent output is indistinguishable from a crash, and a
  consumer of that output cannot tell refuse from fail.
- **When a branch goes red after a threshold change, grep the test for the TOKEN LIST before
  touching the branch.** The failing assertion is usually a membership test over a set of verdict
  words, and the honest repair is to add the missing word, not to widen the check. Two traps, and
  they pull in opposite directions:
  - **Do not delete the assertion.** It is the one guard that catches a silent branch, and removing
    it because a real branch lacked a token trades a caught defect for a covered-up one.
  - **Do not rewrite the membership test into something that cannot fail** (`if out:` or a bare
    non-empty check). A check widened until it always passes is the same defect as one that never
    fires.
  Add the token to the SOURCE and keep the strict check. If the assertion is being changed at all,
  it must get STRICTER or stay identical — never looser.
- **After any change that routes execution down a new path, list which of your fixtures reach it.**
  The count is usually zero, and that is the finding: the suite was green because nothing it owned
  ever went there.

### When the pipeline GATES the branch, extract the decision and test it directly

Sometimes no fixture can reach the branch, because an earlier stage of the same pipeline consumes the
input first. Then the guard is unreachable by construction and an end-to-end run can never exercise it —
and the run will refuse for a **different** reason, which reads like a passing test.

Measured: a dust floor was added to a swap leg to refuse amounts too small to beat gas. The end-to-end
run refused every case with exit 2 — but from the **gas-reserve** check above it, which zeroed the amount
before the floor was ever evaluated. The floor was correct, unreachable, and untested. Extracting it into
a pure function (`dust_refusal(whole, token, min, rescue) -> list[str] | None`) and importing it let a
six-case matrix run in one second, including the exact amount that originally slipped through.

- **Extract the DECISION, not the side effects**, so it can be called with hostile inputs and no funded
  account, network, or wallet. A predicate over numbers beats a script over a live system.
- **Keep the extraction honest:** the caller must still call the extracted function rather than
  re-implementing the check inline, or the tested copy and the shipped copy drift apart.
- **List the states the surrounding pipeline can produce** and note which ones gate the branch out. "The
  guard exists" and "the guard can be reached" are separate claims; only the second one is testable
  end to end.
- **A refusal for the wrong reason still exits non-zero** — so `rc=2` proves nothing about which guard
  fired. Assert the **reason string**, not just the code.

## A check that ABORTS reports nothing at all — and nothing reads as clean

A checker that raises on one missing input does not degrade to "could not check that item". It dies, and
the operator is left with a traceback where a table should be — or worse, with no output at all, which
is indistinguishable from a clean run.

Measured: an EIP-712 domain check aborted twice in one run — `FileNotFoundError` on a sibling deployment's
source that did not exist anywhere on the box, then `KeyError` on a chain with no RPC configured. Both are
**absent inputs**, neither is a mismatch. Together they killed the run after two of four rails had already
passed, so the two rails that could not be measured were never even reached, and the whole check looked
like a failure.

- **Degrade per ITEM, never abort the RUN.** Wrap each item's probe and record `UNMEASURED` with the
  reason, then continue. The rails you can measure are still evidence; throwing them away because a
  sibling is missing is a self-inflicted total loss.
- **A partial result is a distinct verdict, not a pass and not a failure.** Give it its own exit code
  (`2`) and say so in words: `PARTIAL — measured rails CORRECT · 1 rail UNMEASURED · edge UNMEASURED — this
  is NOT a pass`. Returning `0` because the items you reached were fine is the false green this whole
  skill exists to prevent.
- **Name the absent input in the output**, not just the exception type: `okx-edge/server.mjs absent from
  this box and from the snapshot` tells the next reader what to restore; `FileNotFoundError` does not.
- **A missing source is evidence about the INSTRUMENT'S COVERAGE, not about the system.** If a check
  cannot see half its population, the compliance figure it produced was never a measurement of the code.

## A test that dies on a transient external read is reporting a verdict, not a failure

A test that touches the network, chain, disk, or database and does not wrap every such call teaches
people to ignore failures — and then it hides real ones. A provider blip, RPC lag, or timeout that
raises an unhandled exception exits the process with a traceback and a non-zero code that looks
exactly like a real defect. Re-running it five minutes later passes. This is the worst kind of flake:
it trains the reader that "the suite is red again, probably nothing" and collapses the signal.

Measured: a swap-route probe wrapped every `eth_call` except `w3.eth.get_code()` and
`w3.eth.get_block("latest")`. One public-RPC hiccup killed the whole run with exit 1, no verdict,
no machine-readable status — indistinguishable from "no route exists." Five subsequent runs passed
unchanged.

- **Wrap EVERY external call in the test, not just the ones that usually fail.** The calls you
  skipped are the ones that will flake at 3am. A read that cannot complete must return an explicit
  READ-failure code (e.g., 2), never the same code as a real verdict (e.g., 1).
- **Distinguish "I could not measure" from "I measured and the answer is no."** The latter is a
  verdict; the former is a probe failure. They must not share an exit code, and the output must say
  which one happened.
- **Run the suspect test multiple times in a row before trusting it.** A test that passes 5/5 after a
  single failure is flakier than a test that always passes, but it is also evidence that the
  implementation is fine and the harness is the problem.
- **A flake is worse than a bug** — it is a bug that teaches the team to stop trusting the suite.
  Fix the harness first; only then interpret a red result as a defect in the code under test.

## Prove the negative control by REVERTING the fix in a throwaway copy

A negative control that you never saw fail is a claim, not a control. The strongest proof is to take the
shipped fix out of the equation, run the suite, and watch the relevant case go RED — then restore.

Measured: a verifier was parameterised so each §4 case could run with its responsible check removed.
The harness looked good, but the real proof came from copying the module to a temp dir, mutating it back
to the pre-fix shape, and running the tests there:

```
real code        -> 11 passed
pre-fix mutation -> 2 failed, including the regression test
```

That showed the regression test was not just a restatement of the fix; it died when the fix was absent.

**Procedure:**
1. Keep the fix in production code.
2. Create a temp dir and copy the module + tests there.
3. Apply the **inverse patch** (mechanical if the fix was small, or save the original hunk before
   patching and re-apply it).
4. Run the suite in the temp dir.
5. Confirm the case(s) that should fail DO fail.
6. Delete the temp dir; do NOT leave the mutation anywhere persistent.

**Do not mutate the real source to plant the defect.** A test killed between plant and restore leaves
the defect live. A throwaway copy is the only safe way to prove the control.

## A check that RECORDS while it CHECKS consumes evidence a later step still needs

A check that writes state while deciding whether to refuse can burn a token that a later step then needs.
If every step must agree before the request is accepted, then **recording the outcome must happen AFTER
all steps have agreed**, not during an early one.

Measured: a replay check inserted the `jti` into the store at the moment it verified uniqueness. A token
that was then refused by a later step (stale roster) had already consumed its `jti`, so when the roster
refreshed and the caller re-presented the same valid token, it was refused as a replay — for a call that
never happened. A stale roster silently invalidated every in-flight peer call.

**Rule:** separate the *read* (`is_seen`) from the *claim* (`claim`). Check early, record last. The atomic
claim stays the real accept-once gate under concurrency; the early read is for promptness and the right
error message.

**Regression test it:** present a valid token, refuse it at a late step, then present the same token again
and assert it is still accepted. If the check records early, this test fails.

## Module names can shadow the standard library and break the import chain BEFORE your code runs

A file named `token.py` looks harmless until `dataclasses → inspect → tokenize → from token import
EXACT_TOKEN_TYPES` tries to import the real `token` module and finds yours instead. The error points at
`dataclasses`, not at your file, and the code never executes a line.

**Rule:** before naming a module, check whether it collides with a stdlib module. A quick probe:

```python
import sys, importlib.util
name = "token"
if importlib.util.find_spec(name) is not None and name not in sys.builtin_module_names:
    print(f"{name!r} is a real importable module — do not shadow it")
```

**If a file must live on `sys.path` and its natural name shadows the stdlib, rename it.** The test for the
renamed module then becomes: import it under the new name and assert it resolves to the expected path,
not to the stdlib one.

## A name the RUNTIME already owns silently replaces your value

If a variable collides with a built-in the shell (or runtime) already owns, your assignment does not take,
and every read of it returns the ENVIRONMENT's value. The check then measures the host, not your input,
and reports a confident, wrong verdict.

Measured: a Telegram installer collected chat ids into `GROUPS=(...)`. **`GROUPS` is a readonly bash array
holding the process's own group IDs.** The array never held the chat ids, so the membership loop asked
about chat `10000` — the container's GID — and got "chat not found". Read literally, that says *the bot is
not in the group*; in truth the bot was in the group and the tool never asked about it. A false negative
that looks exactly like the condition the tool exists to detect.

- **Echo the value the CONSUMER received, not the one you think you passed.** `echo "$g"` before the call
  would have exposed this in one run. "The call happened" is not "the call carried my value."
- **Know the reserved names** before choosing one: bash owns `GROUPS`, `PIPESTATUS`, `BASH_VERSINFO`,
  `RANDOM`, `SECONDS`, `UID`, `EUID`, `PPID`, `LINENO`. Python owns its builtins and stdlib module names.
  Rename yours (`CHATIDS`, `RC_LIST`) rather than shadowing.
- **Prefer named flags over positional slots when two adjacent parameters share a type.** The same tool
  first took `<profile> <token> <allowed-users> <groups...>` — all numeric-id-shaped — and a group id in
  the users slot **silently overwrote a live allowlist**. Validate the shape (`^[0-9]+(,[0-9]+)*$`) and
  refuse, and make the interface `-u/-g` so the slots cannot be confused.
- **Line counts do not detect this class.** The damaged file had the same number of lines before and
  after, because one value replaced another. Compare VALUES, by shape, per key.

## A query that ERRORED looks exactly like a query that found NOTHING

The distinction this skill demands (*"I could not measure" ≠ "I measured and the answer is no"*) is
easy to lose in a **data read**, because the failure is one default argument away.

```python
d = json.loads(resp)
rows = d.get("result", [])      # a REJECTED query also has no "result" → [] → "zero found"
```

That line turns *"the server refused my request"* into *"there are none"* — and the number it produces
is confident, well-formatted, and wrong. Measured: a scan reported **zero payments in seven days** as
fact. The RPC had rejected every filtered call as `Invalid params`; nothing had been searched at all.

- **Never default the result key.** Branch on the error field FIRST and propagate a distinct failure.
  In JSON-RPC: `if d.get("error"): raise ReadFailed(d["error"])` before touching `result`. An empty
  list is a finding; a missing one is a refusal, and they must not share a code path.
- **Prove the FILTER before trusting its empty answer — query for a record you already know exists.**
  This is a positive control on the instrument, and it is the cheapest step in the whole procedure.
  Pick one known-good item (a transaction whose block number you have, a row you can see by hand),
  run the exact same predicate over a window that must contain it, and require a hit. Only then is a
  zero from that predicate evidence. A filter proven against one positive and then run over the
  population is a measurement; a filter run alone is a guess with a number attached.
- **A predicate that returns an ERROR is not a predicate that returns nothing.** Read the error text,
  not just the absence of rows — a rejected filter and an exhausted scan look identical downstream and
  are fixed by completely different things (a malformed query vs. a narrower window).
- **An "any value" placeholder is not the same as an empty value.** Where a protocol wants a wildcard
  (JSON-RPC `topics: [sig, null, addr]`), a zero-filled string is a *specific* value, so the server
  rejects the whole request or matches nothing. Emit the protocol's own wildcard token.
- **Widen the window and re-check before reporting a historical zero.** A scan that spans further back
  than the endpoint's archive depth fails per-chunk; count the FAILED chunks and refuse to report a
  total until that count is zero. "Zero across 54 chunks, 0 errored" is a result; "zero" with 200
  silent failures is the same defect as the sweep that greps its own output.

## A validator is not a test — form and function fail differently

A schema/lint/security gate proves the artifact is **well-formed**, never that it **does the job**.
Both can be green on an implementation that returns a confidently wrong answer.

Measured: a plugin passed its host's validator — every schema check, a clean security scan, import and
registration confirmed — and its core feature returned **nothing**. A query for *"which chains settle
payments"* scored **0.00** against a note containing *"settles"*, because the tokenizer matched exact
words with no inflection handling. Every gate was green; the product was broken.

- **A passing gate licenses you to RUN it, not to REPORT it.** After validate: exercise the primary
  feature on inputs a real user would produce and assert on the ANSWER. "It loads" is availability.
- **Write the behavioural case as a ranking/decision assertion with a DECOY.** Include an input that the
  wrong implementation would prefer — a document that repeats a common query word many times, a
  near-miss item that is easier to return — and require the correct one to win. A decoy turns "it
  returned something" into "it chose right".
- **Test the paraphrase the user will actually use, not the phrasing in the docstring.** The failure
  above only appears when the query's wording differs from the corpus — which is the entire point of a
  retrieval feature, and exactly what an example copied from your own notes will never show.
- **Enumerate the gates you passed and say what each one does NOT cover.** In a report, "validate 15/15"
  beside "behaviour: 5/5" is honest; "validate 15/15" alone reads as working.

### Call the HOST's entry point, not your own method — the difference is the failure mode

A plugin/hook/provider exposes a method, and the host wraps it in policy. Testing the method alone proves
your code runs; it proves nothing about what the host does when your code REFUSES. That policy is exactly
where silent data loss lives.

Measured: a provider's archive step raised correctly when its output directory was unwritable — and the
feature only mattered because the host treats providers as **best-effort by default**. Calling the method
directly cannot see that. Running the host's own manager produced the three states that actually matter:

```
manager.on_pre_compress(msgs, require_checkpoint=True)   # archive ok      -> returns, message count verified
manager.on_pre_compress(msgs, require_checkpoint=True)   # archive broken  -> HOST raises, rewrite blocked
manager.on_pre_compress(msgs)                            # same failure    -> returns '' — transcript LOST silently
```

- **Find the host helper that decides policy and call THAT**, not the plugin method it delegates to. Here it
  was the manager object plus a signature-inspection helper that gates whether the policy flag is even passed
  to you (`provider.method(X, **kwargs)` — a provider whose signature lacks the flag silently never receives
  it, and looks compliant).
- **Assert the SILENT branch, not just the loud one.** "It raises when broken" is half the contract; the other
  half is that the caller who did not opt into strict mode gets a distinguishable outcome. If the quiet and
  the failing paths return the same value, the provider cannot be trusted and the test should say so.
- **Construct the host object with the minimum surface the policy needs** (the provider list, the owning
  context flag) rather than standing up the whole application — a contract test that needs a full boot will
  be skipped, and a skipped control is not a control.

## A NUMBER a pipeline produces is an assertion — verify the unit, the field and the row

The reflex above ("suspect the assertion before the code") applies to every measurement, not just to test
files. A `find | awk` count is an assertion about the world, and it fails in the same three ways: wrong
**unit**, wrong **field**, wrong **row population**. Each produces a confident, well-formatted number that
sends you to fix working code.

- **Check the UNIT before blaming the code.** A ratio and a percentage are the same digits twice. Measured:
  `52 / 1024` is `0.05` of a unit and `5.1` percent of it, and a report printed **0.1%** for a ledger that
  was 5.1% full. Two rounds of "the calculation is broken" were both "the formula asks for the wrong unit."
  **Write the unit into the variable or the label** (`pct_used = 100 * used / cap`) so the 100 cannot be
  forgotten, and sanity-check by hand on one row before trusting a loop.
- **`awk` with `printf` and no `\n` CONCATENATES one row per file into a single number.** Measuring four
  per-profile WAL files with `ls -la … | awk '{printf "%.0f", $5/1048576}'` produced **"2548649 MB"** —
  four sizes glued together, then read as one quantity and reported to the user. Use `print` (which adds a
  newline), or a per-item loop, or take a `max` in the same pass. **A number 400× larger than the largest
  possible input is a concatenation, not a measurement** — check the magnitude against the domain first.
- **Verify a MOVE by counting the SOURCE before and after, never by what the mover printed.** A recursive
  mover reported moving 2 files when it had moved 9; the announcement describes what the command decided to
  do, not what changed. `before = count(src); move(); after = count(src); moved = before - after` is the
  only count that cannot flatter itself — and it is the same differential proof a delete needs.
- **Do not parse your own human-facing output back into variables.** Lines built for a reader (emoji,
  colons, prose) are not a data format. Measured: `sed 's/.*: \([0-9]*\) files.*/'` over a line beginning
  with an emoji returned a control byte, and the next comparison died with `Illegal number: \x01`. Give the
  tool a machine-readable mode (`--json`, or `key=value`) and read that; if none exists, parse with a
  field-aware tool and **fail loudly when the field does not parse** rather than letting an empty string
  flow on as `0`.
- **Never interpolate shell text into Python source.** `python3 -c "print(f'{${var}/1024:.1f}')"` lets the
  shell substitute first, so Python is handed a mangled expression and either errors obscurely or answers
  the wrong question. **Pass values as `argv`** (`python3 -c 'import sys; …sys.argv[1]…' "$var"`) and let
  Python do all arithmetic in one place.
- **A wrong number and a right number look identical downstream.** Both are a bare integer. So print the
  **inputs** beside the output (`notes 52 MB of 1024 MB → 5.1%`) — the arithmetic becomes checkable by the
  reader in one glance, which is the only defence against a pipeline you have already stopped suspecting.
- **Pair a label with its value by BLOCK CONTAINMENT, never by proximity.** A row's value does not necessarily
  follow its label — in many card/table layouts the badge or price sits **before** the heading, so a
  "search forward from the name" parser pairs every record with the NEXT record's value. Measured: this produced
  `5 of 7 prices WRONG` on a page where **all 18 were correct**, and the invented defect was reported to the
  user as billing-grade. **Split the document into its repeating block first (`<article>`, `<tr>`, a `##`
  section), then read both operands from INSIDE one block.**
- **Verify ONE case by hand before publishing any derived count.** Open the artifact, find the first record, and
  read its value with your eyes. A parser that is wrong in the same direction for every row produces a
  perfectly plausible table — the single hand-checked row is the only thing that catches it, and it costs one
  look. **An all-rows-wrong result is a parser bug, not a finding**: real defects are rarely uniform.
- **A conditional whose branches are IDENTICAL cannot discriminate, and a reader will assume it does.**
  `label = "UNATTRIBUTED" if not ok else "UNATTRIBUTED"` is a dead conditional that erases a real distinction
  while looking like a considered safety check. Measured: a report printed the same "unknown payer" string for
  a broken registry and for a genuine first customer, so the one event the job existed to detect was
  indistinguishable from an anomaly. **Diff the two branch strings — if they match, the branch is decoration.**
  Keep the branches distinct in the output AND in the words: `CUSTOMER` vs `UNATTRIBUTED — status UNKNOWN`,
  because the operator acts differently on each and cannot act at all if they read the same.

## Pitfalls

- **An expression used as a boolean can return a VALUE, and comparing it to `True` fails on correct code.**
  `"key" in d and d["key"]` yields the key's **value**, not `True` — so `assert (...) == True` is red the
  moment the value is a non-empty string or a non-zero number, which is precisely the healthy case. The
  same shape hides in `any(...) and something`, `a or b`, and any helper written as a predicate that
  returns its argument on success. **Assert the property, not the expression's identity:**
  `assert "key" in d` and `assert d["key"] == expected`, or `assert bool(expr) is True` when the
  expression is genuinely meant as a predicate. When a selftest fails against code you just reasoned
  through, print the operand's **type** first — a `str` where you expected `bool` indicts the assertion
  in one run, and a false red here sends you to "fix" working code.
- **A test sample must come from the DOMAIN, not from the artifact under test.** Inputs drawn from the
  lookup table the code consults measure self-consistency and discriminate nothing. Include at least
  one input you expect to FAIL — a sample where every case passes cannot falsify anything.
- **A resolver test must prove it does NOT invent paths.** Test bare-lane forms, filed subdirs,
  and alias resolution, but also assert that genuinely absent files return `None` and that empty/None
  inputs return `None`. A resolver that fabricates a location for a missing file is a false-green
  machine. Run it against the live ledger and report the resolution rate; a fixture-only suite can
  pass while most real records are unfollowable.
- **Re-measure after you fix the measurement itself.** A parser, classifier, or resolver change can
  change the count as much as the underlying state. Re-run on the same corpus before and after,
  using the same denominator. If the new number contradicts the old, debug the MEASUREMENT before
  reporting the new finding. The first corrected measurement is a hypothesis, not a fact.
- **A guard that validates a COPY of the thing is not a guard on the thing.** If the "actual" side is a
  hardcoded dict rather than the live source, the guard reports green while the real source is broken.
  Pin the EXPECTED side; derive the ACTUAL side from the artifact (import it, parse it, probe it).
- **CLI subprocess tests get fresh state per invocation.** If test A creates data and test B reads it
  via `subprocess.run`, test B sees an empty world. Create and read within one script, or call the
  module's Python API directly.
- **Define helpers BEFORE the functions that call them** in inline (non-pytest) test scripts — Python
  executes top to bottom, so a helper used at module scope must be defined earlier in the file.
- **A test that asserts success while doing nothing is the same bug class it exists to catch.** Ask of
  every new check: *what would make this print a confident PASS while the thing it guards is broken?*
  If the answer is "nothing", you have not finished writing it.
- **A CLAUSE THAT SHARES ITS EXPRESSION WITH ANOTHER CLAUSE CANNOT FAIL INDEPENDENTLY — measure what
  the LABEL names, not what is nearby.** A suite line printed `read by assert_target_safe (N)` where
  `N` was computed by the *same command* as the total-occurrence count two lines above it. The label
  named a specific function; the expression counted the whole file. Proven: a subject whose guard body
  referenced the constant **zero** times, carrying two *unrelated* references elsewhere, still
  **PASSED** — the global threshold was satisfied by uses that had nothing to do with the assertion.
  **Scope the count to the artifact the label names** (extract the function's own body and count
  there), and **fail loud when that artifact cannot be found** — a guard that cannot be located must
  not read as a guard that is satisfied.
- **THE MECHANISM A TEST CANNOT REACH IS WHERE IT IS BLIND, AND FIXING ONE RUNG REVEALS THE NEXT.**
  In a single file, the same defect appeared three times, each one inside the fix for the last:
  **(1) matching PROSE** — the grep hit the docstring explaining the defect instead of the defect;
  **(2) matching the DEFINITION** — the pattern matched `def f(...)` so `head -1` returned the
  signature and the case passed with the call site deleted entirely; **(3) matching a GLOBAL
  THRESHOLD while wearing a clause's name** (above) — and then it reappeared *inside that fix*,
  because the newly scoped extraction still included the function's docstring, which discussed the
  constant. **Assume the class survives your fix and re-run the control after each repair; verify by
  watching the case go RED, not by reading the patch.**
- **THE PROOF IS THAT THE REVERT IS CHEAP.** A control nobody can re-run in a minute is a claim, not
  a control. Prefer a fixture swap plus a restore-by-hash over a hand-edited subject: if turning the
  fix back into the bug takes one block move, the next reader will actually do it, and the control
  stays alive. Snapshot the refs first, run, restore from the hash, and assert the restore.
