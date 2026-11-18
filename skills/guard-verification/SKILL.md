---
name: guard-verification
description: Harden guards so they fail on real defects, not fixtures.
trigger: Writing a new guard or watcher, adding a negative control, or when a guard/test/watcher produces a false red, false green, or silent miss.
tags: [guards, watchers, negative-control, tests, verification, false-value]
version: 1.0.0
author: Gentech
license: MIT
---

# Guard Verification

A guard is only useful if it goes red when the thing it protects is broken and stays green when it
is not. This skill covers the design, testing, and maintenance of guards, watchers, and negative
controls — the patterns that keep them honest and loud.

## Procedure

### 1. Design the verdict first

Before writing the guard, state the exact question it answers and the two ways it can be wrong:

| wrong direction | name | symptom |
|---|---|---|
| says broken when healthy | false red | wastes time, trains people to ignore the guard |
| says healthy when broken | false green | silent failure, usually worse |

A guard that cannot fail in either direction is a decoration. If you cannot describe both failure
modes, you are not done designing it.

### 1b. A guard's name and its enforcement can be two different things

**The declaration that carries the name may be inert while the actual protection has no name.**
This is the hardest guard defect to see, because the named symbol reads as enforcement to a
reviewer and the real enforcement looks like an implementation detail.

Measured: a script declared `NEVER_TOUCH = "main"` with a comment calling it "non-negotiable", and
referenced it zero times. The protection that actually held was a hardcoded refspec on the push
line. The thing with the name did nothing; the thing that did the work had no name. Two auditors
initially read the named guard as the enforcement.

**Rule:** grep the guard's identifier and count the READS. One occurrence (its own assignment) is the
alarm. A declaration plus a comment is indistinguishable from enforcement to the next reader.

**Fix:** make the named guard read the string the action actually uses, and order it
`build → validate → use`. The test should assert the ORDER, not the presence. A guard called after the
action is decoration; a guard called on a different string than the action uses is theatre.

**Prove it fires with the target-rewritten case.** A guard that only reads the declaration passes the
obvious tests and fails exactly where it matters: the target is rewritten to the forbidden value
while the variable still reads the permitted one. If that case does not fail, the guard is a name
without a mechanism.

**When retiring a dangerous word: remove it from the CLI surface, keep the reason in docs.** Rename a
flag (`--force-run` → `--now`) so it cannot be reached; leave the docstring explaining the
withdrawal. Assert against the emitted statement (the argparse call), never the whole file — a check
that forbids its own explanation pressures the next editor to delete the doctrine.

### 2. Read the field, not your own expectation of it

**A parser that reads the field it guards must be format-agnostic.** Real inputs declare state in
bold (`**Status:** open`), as list items (`- status: open`), inside blockquotes, and in table cells.
A reader that only matches a bare plaintext prefix misses real declarations and returns `none` for
a note that plainly has a status.

**Rule:** strip Markdown decoration before classifying. A reader that cannot see its own input is a
false-negative generator — the same class it exists to stop.

### 2a. A guard that demands a receipt must verify the receipt is FOLLOWABLE

**Requiring a `return_note` is not enough — the path it records must resolve for the next reader.**
A malformed path looks like diligence while being as untrustworthy as no note at all:

- Bare lane form with no `01-HANDOFFS/` prefix.
- Stale lane alias (`gentech-to-treasury` when the real lane is `gentech-treasury-to-gentech`).
- A file that was filed into `_archive/` or `_closed/` but the record still points at the live lane.

When a guard checks `answered` records against their note, **measure the live ledger's resolution rate**
before declaring the guard sufficient. If most paths do not resolve literally, the guard is catching
"no note" but missing "note that names nothing." Both are false receipts.

**Fix read-side and write-side together:**
- Provide `resolve_return_note(note, near=)` that walks the vault prefix, lane aliases, and filed
  subdirs so old records become followable WITHOUT rewriting them. A write-once record's hash must
  not be disturbed by a retrospective edit.
- Make `close()` write the COMPLETE resolved, vault-relative path (`01-HANDOFFS/<lane>/_archive/...`)
  so new records are followable by construction.
- Keep a canonical alias table (`gizmo==labs`, `pixel==entertainment`) in ONE place, not scattered
  across call sites.

**Negative control:** an absent reply must resolve to `None`. A resolver that fabricates a plausible
path for a missing file is worse than no resolver, because it turns "genuinely missing" into
"found it, trust me."

**Measure against the live corpus, not a fixture.** A test with only hand-crafted good paths cannot
prove the resolver handles the real historical mess.

### 3. Classify by leading word, not substring

**A classifier must test the LEADING WORD of the declared value, not a substring over free text.**
Substring tests are wrong in both directions:

- `closed — nothing open here` contains the target word and reads as open (false positive).
- `no further action — the one open class is a design question` describes an open item but contains
  no literal target word and reads as closed (false negative).

After fixing the parser, re-read the live corpus and count. The leading word is the verdict:
`open`, `closed`, `answered`, `acked`, etc. The target word should match exactly the genuine cases,
and every other leading word should map to its actual state.

**A word in free text is not a behaviour.** Audit what a script DOES by the mechanism it invokes,
never by grepping for the verb. A description of the absence of an action contains the action's
word: a job whose prompt reads "never pushes, per R4" flags as a pusher, and "handles error strings"
flags as errored. **Read the mechanism — the HTTP method actually issued, whether the object is a PR
or an issue, the exit code, the API verb — and quote that in the finding.** Measured: three of
fourteen jobs were reported as writing to GitHub on the word "push"; all three were read-only, and
one of the three said "never pushes" in its own documentation. A keyword census answers "does this
file mention the concept", which is not the question any audit is asking.

### 3b. Assert the PROPERTY, and measure the SUBJECT you name

A guard fails in both directions from one defect: **it tests a NAME where the property it claims requires a
property test, or it reads an artifact other than the one its label names.** Either way the verdict is
confident and teaches the reader the wrong lesson.

**False green — the assertion tests a name.**
A row asserting *“no sibling `.passphrase` file`”* passes on a directory whose shards are named
`shard-N-of-3.hex`. The property under test is *“the passphrase is not in the same failure domain”*; a
filename test cannot see it. The row goes green on a directory that is fully decryptable by anyone with read
access — and the label (“different failure domain”) made the green look meaningful.

**False red — the subject is wrong.**
A row labelled *“newest offsite key-bundle age ≤ 36h”* that globs the local key store reports a months-old age
and concludes *“no nightly backup job exists”* — while the backup job ran that morning and its bundles are
hours old. The label describes one artifact; the glob reads a different one.

**Rule:** for every assertion, write the property down in words, then confirm the test reads THAT property and
not a token that merely correlates with it (a filename, a label, a directory name, a substring). For every
row, write down WHICH artifact it measures, then confirm the read path reaches that artifact.
**A name is not a property; a label is not a subject.**

**Test it by construction:** rename the artifact under test — the shard, the file, the directory — and re-run.
A property-based row does not move; a name-based row flips. If renaming does not move the row, it is testing a
name. Do this once when writing the row; it is cheaper than discovering it after the row has been trusted.

**The same defect wears an audit costume.** An assertion that matches a pattern and then reports the MATCH as
a property of the system (“found `429`” → “rate limited”; found `delegation` → “a delegation config exists”)
is this bug outside a guard. A match is not a meaning — read the context before promoting a hit to a finding.

**False green — a COUNT of a thing stands in for the thing.** *“Nobody has answered”* implemented as
`reply_count == 0` reports an item as handled the moment ANY reply lands — including one from a stranger, a
bot, or the wrong party. The property is *“the last word is not ours”*; the count is only a proxy for it, and
it goes green precisely when the thread starts waiting on somebody. **When the state you care about is “who
owes the next move”, test the ORDER (who spoke last), never the total** — a count answers “has anyone ever
spoken?”, which is a different and far weaker question.

Measured: two inbound threads sat 67 and 8 days unanswered while a count-based check reported them handled,
because each already had comments on it. **Presence of ANY activity is not evidence that OUR move is done.**
The generalisable form: for every predicate of the form “X has been handled”, ask *handled BY WHOM, and did
they move last?* — then read the actor and the ordering, not the volume.

### 3c. A guard must not be satisfiable by its own output

**If the space a guard searches includes anything the guard's own side writes, the guard answers its own
question and reports clean forever.** This is the hardest false green to see, because each individual run
looks correct: the check found a file, the file was dated after the item, the item reads handled.

Measured: a watcher reporting handoffs with no acknowledgement resolved a reply by building the lane name
`<sender>-to-<target>` — **the sender's own outbound lane.** For a note we had sent, that is the folder we
write to, so the check found OUR notes sitting there, dated after the handoff, and credited them as
acknowledgements. **Every note sent automatically acknowledged the previous one**, and one lane reported
"all acknowledged" for 26 days while its owner had never replied once. The instrument was not reading a
stale value; it was answering its own question. Same family as a health endpoint that checks itself.

**The rule: the reply is authored by the PARTY WHO OWES IT.** Name who must speak next, then search only a
space that party can write to (`<target>-to-<sender>` for a reply — never `<sender>-to-<target>`).

- **For every lookup, name the author of the thing you are looking for, then confirm the search space
  belongs to that author.** A direction error survives code review: both spellings are plausible lane names.
- **The test that finds it: instrument the lookup and print WHY each item resolved** — the space and the
  reason, not the verdict. Every item resolving through the same suspicious space is the tell.
- **Fix by REMOVAL, not addition.** Adding the correct space alongside the wrong one leaves the false
  positive intact, because the wrong space still matches. Remove the space your own side writes.
- **Confirm the correction MOVED the numbers, and report the delta.** Measured on one corpus: unacked 6 → 11,
  acked 13 → 9. If the count does not move, nothing changed.
- **Re-audit the downstream consumers.** Any report that repeated the old figures is now quoting a wrong
  number — name which reports are suspect, do not only fix the source.

### 4. Build a falsifiable negative control

**A guard without a negative control is a guard that has never been proven to bite.**

- **Neuter the guard, re-run the suite.** If it still passes, the suite is guarding nothing.
- **Run the control against the real artifact, not a fixture.** A control against a hardcoded dict
  proves the comparison arithmetic, not that the guard watches the source.
- **If the suite disables the guard by string-replacing an exact source line, a refactor of that line
  silently neuters the control.** Before touching the guarded call line, grep the test tree for any
  replacement of it. If one exists, keep the line byte-identical or update the control's target in
  the same commit. After any edit, run the control and prove it still bites.
- **Do not mutate production to plant a defect.** Write to a throwaway copy; make the guard's root
  injectable (`os.environ.get("X_ROOT", <default>)`) and strip any test marker found at startup.

### 4a. Cover the POPULATION, and every path into the guarded list

**A control that exercises one code path proves one code path.** Two defects from this class, both green
when they shipped:

- **The fixture used input shapes the population does not use.** A parser control fed *bare* paths while the
  real corpus carried the same paths inside *backticks*. The gate was written, the control passed, and the
  real run still emitted thousands of false positives — **the fixture never entered through the branch the
  population uses.** Build the fixture by copying a REAL record and leaving its formatting intact; a
  hand-written clean fixture tests the parser's manners, not its job.
- **The gate was applied to one of two branches that write the same list.** Guarding the `X` branch while the
  `Y` branch appends to the same collection is not guarding the collection. **Grep the guarded predicate's
  call sites: the count must equal the number of ways an item can enter the list.**

**A control must drive the ENTRY POINT, not just the leaf.** A self-test called the classifier directly, so it
never touched the parser producing those values — and two `NameError`s from a broken edit shipped past it.
**Exercise the same function the caller uses.**

**Re-run the controls immediately after ANY edit to a guard.** A block replacement can silently take adjacent
module constants with it (measured: four lost in one edit, two of them surfacing only as runtime
`NameError`s). The controls are the only thing that notices. Never edit a guard and a caller in one pass
without running the battery between them.

### 4b. A control can encode the DEFECT as its expectation

**When you correct a guard's logic, its negative control may go red — and the CONTROL is what is wrong.**
A fixture written while the bug was live bakes the buggy convention into its expectation, so it asserts the old
behaviour and fails against the fix. **Read which side moved before touching either.**

Measured: a watcher resolved its search space in the wrong direction (see §3c); corrected, its own self-test
began reporting `2 unacked / 0 acked` where it expected `1 / 1`. The fixture had built its reply lane under the
OLD convention — and the old convention is a name that is spelled identically while pointing the other way, so
the fixture read as correct. **Reverting the guard to make the suite green would have restored the exact
false-green the fix existed to remove.**

- **Ask which artifact the failure is about** — the guard's logic, or the fixture's assumption about it. A
  control that has only ever passed is asserting the behaviour that was shipped, defect included.
- **A control failing immediately after a logic fix is the expected consequence of the fix, not evidence
  against it.** Reverting to green a suite is how a known defect is permanently re-installed.
- **Write the corrected convention INTO the fixture, with the reason**, so the next author cannot re-derive
the old one from the surrounding code.

### 4c. A handler for a state that has NEVER OCCURRED is evidence the guard was never green

**A crash on a newly-reachable branch diagnoses the guard, not the fix.** If correcting a verdict's logic
makes it raise on a value it could always return *in theory*, that branch has never executed — which means the
guard has never once returned that verdict.

Measured: an escalation gate always reported an elevated band, so its reporting dict had no entry for the
normal band. Fixing the escalation made the normal band reachable for the first time, and it died on a missing
key. **The missing key was proof the gate had never been quiet.**

- **Treat a KeyError / unhandled case on a "newly possible" value as positive evidence about history**, and
  record it — it dates how long the defect has been live and is the cheapest proof available that a guard was
  a decoration (§1).
- **After any fix that changes which verdicts are reachable, enumerate the newly-reachable set and confirm
  each has a defined handling path** before calling the fix done.

### 4d. When a guard stops REFUSING, assert the direction it must still not permit

**Turning a refusal into a helpful response creates a new permission surface, and nothing in the old tests
covers it.** A `404 not-a-resource` that becomes `402 here-is-how-to-call-it` has gone from "no" to "yes, do
this" — and if that path can also emit a payable challenge, an agent can pay for the thing you just stopped
refusing. The old battery proves the refusal worked; it says nothing about the new branch.

**The property to assert is what the branch must NOT do.** For every refusal-to-guidance change, write the
forbidden outcome in words and test it explicitly:

- **Unresolved/invalid input → a response that CANNOT be consumed.** Assert the absence of the affordance, not
the status code. A guidance body must carry no quote, no cart, no `accepts` array, no signed URL — the check
is `assert "accepts" not in body`, because `status == 402` passes for both the safe and the catastrophic
response.
- **Resolved/valid input → the affordance IS present.** The pair is what proves the branch is selective; one
direction alone is satisfied by a branch that always fires or never fires.
- **Then test the branch in isolation.** If a readiness/health check upstream can answer first and mask it,
  you have not executed your code. Disable the upstream gate (an env switch, an injectable root) and re-probe,
  or the green belongs to a different branch.

Measured shape: the guard read its definition set, found nothing, and returned "" — so the refusal never fired
and the "unresolved" path fell through to a fully payable quote. The guard was correct; **its input was empty,
and an empty input makes a refusal guard inert** (see §7b). Both defects were in the same path and only one was
in the file being edited.

**Also: a guard that no longer refuses should not silently drop the case list it refused.** Keep the class
(`unsubstituted`, `malformed`, `missing`) as data and let one branch decide what each class now returns, so the
next class cannot arrive with no handler.

### 4e. A guard the happy path cannot REACH must be tested as a unit — and "exit 2" is not proof it fired

**An earlier gate can mask a newly-added one, so the run refuses for the wrong reason and the exit code looks
exactly right.** Measured: a minimum-size floor added to a swap path was unreachable — an upstream gas-reserve
check zeroed the amount first and the script exited `2` from *that* branch. The floor had never executed, and the
only visible evidence said "refused, as intended."

- **Read WHICH gate refused, not the status code.** Print the refusal reason and quote it. Two branches returning
the same exit code is the most convincing false proof a suite can offer, because the assertion (`rc != 0`) was
written before either branch existed.
- **Extract the predicate into a pure function** (`def dust_refusal(whole, asset, floor, override) -> list[str] | None`)
  in the same module, and drive it from the test by **importing that function**. A test that re-implements the
  arithmetic proves the re-implementation, not the guard.
- **Cover the defect's own input plus both sides of the boundary and every bypass:** the exact value that produced
  the incident, just-under, exactly-at, comfortably-above, and each flag that deliberately skips the guard. A
  bypass that silently also disables the guard is the failure the flag was added to prevent.
- **Say which part of the guard is untested end-to-end.** A unit-tested predicate behind an unreachable branch is
  an honest, useful state — but the report must state that the production path was not exercised, rather than
  letting "6/6 pass" imply a live run.

**A guard that can only be exercised by spending money or touching production is a guard tested when
convenient — which is to say, rarely.** Extract first, then test; the extraction is what makes the guarantee cheap
enough to keep.

### 5. Re-verify after hardening

A fix can make the suite unfalsifiable. After every hardening change:

1. Run the positive suite — it must pass.
2. Run the negative control — it must fail (or report the refusal).
3. Plant a real defect in a scratch copy — the guard must detect it.

### 6. Report near-misses honestly

**A green suite is not the same as a correct decision.** If reading stopped an action the guard
would have permitted, disclose the near-miss in the record rather than letting the suite imply
sufficiency. Say "I stopped this by reading, not by rule" when that is the truth.

### 7. The failing default must not be the healthy value

**When a guard cannot read its input or its own output, the default verdict must be a loud failure — never
the healthy value.** This is the one place where "safe default" is a real decision, and the wrong choice
makes a false-green generator in exactly the condition production meets most often.

- **A parse-error branch that returns the clean result fails OPEN.** Returning `0 findings` / `parseable` /
  `no change` from an `except` clause converts *"I could not read it"* into *"nothing is wrong."* Those two
  states must never look alike. **Return a distinct unparseable state and exit non-zero.**
- **A metric line you cannot populate is worse than no line.** A report that greps a log format which no
  longer matches prints a blank or `usage unavailable` while real cost accrues — the reader infers "free".
  **Read the metric from the authoritative artifact (response body, state file) and say `UNMEASURED` loudly
  rather than printing a default that reads as a real number.**
- **A verdict that reports N problems and exits success is not a verdict.** If the guard counts findings, the
  count MUST drive the exit code. `PASS` printed beside `3 findings` is the guard disagreeing with itself.
- **Prove both directions in the battery:** an unreadable fixture exits non-zero, AND a fixture carrying
  findings exits non-zero. A battery with only clean fixtures tests nothing but the happy path.
- **A well-formed response can read as EMPTY from a framing assumption, and empty must never read as zero.**
  Splitting an HTTP response on `\r\n\r\n` is wrong for any server or proxy that emits bare `\n` (HTTP/2
  over a proxy commonly does): the delimiter never matches, the ENTIRE body is consumed as "headers", the
  body comes out as `""`, and `json.loads("")` raises straight into a `return body` that hands back an empty
  string with no error. Measured: a secret audit reported **"0 repos, 0 files, all clean"** while the token
  was returning 143 repos. **Accept both delimiters, and make `200` with an empty body return UNKNOWN** — an
  empty success is a parse failure wearing the healthiest possible status code.
- **A guard that adds load to the thing it protects is not a guard.** Consulting the rate-limit endpoint
  before every request doubles the round trips and latency of a job whose entire purpose is to reduce load
  on that API. **Cache the budget reading with a short TTL** (a minute is plenty) and prove it: count the
  quota-endpoint calls across three fetches and assert one, not three. The same rule applies to any guard
  that re-reads a large artifact per item — sample it once per run.

### 7b. A guard whose REFERENCE PATH is dead fails OPEN — with no error at all

**A guard reads a root, a base directory, or a reference set to decide what is "inside" and what is
"outside". Point that constant at a path that no longer exists and the guard does not crash — it simply
never matches, so it permits everything, silently and forever.** Worse than a parse error: an error is
loud, while a dead-path guard reports success on every call.

Measured: a safety guard whose whole premise was *"refuse to write key material inside the synced vault"*
defaulted its root to a directory destroyed in an earlier migration. Every candidate path fell outside a
root that did not exist, so the guard **allowed a private key INSIDE the vault** while reading, to any
reviewer, as enforcement in place.

- **Never trust a guard's verdict on a path-shaped input until you have seen it REFUSE something it should
  refuse.** Invoke it both ways — one input that must pass, one that must be refused — and read the two
  verdicts. Reading the code proves nothing: the constant looks fine.
- **Grep the guard's root/default for paths that cannot exist** (a pre-migration home, a deleted mount, a
  `/root/…` under a non-root runtime). A dead default is the defect; a stale docstring is only its symptom.
- **Make the root injectable, and default it to the LIVE path** — `os.environ.get("X_ROOT", "<real path>")`
  — so a control can point at a scratch dir without mutating production, and the shipped default is the one
  that actually exists.
- **A guard is not verified by its own tests passing.** If the fixture injects a scratch root, the DEFAULT
  root is untested — and the default is what runs in production. Assert the default explicitly.

**A dead path has TWO failure faces, and the second one misdiagnoses itself.** The guard shape above goes
silent — permits everything, reports success. A plain READER of the same dead path fails the opposite way:
it inherits a filesystem error that names something else. Measured: a script reading its credentials from a
pre-migration home died with `EACCES: permission denied, open '<dead path>'` — which reads as a fixable
permissions problem, so the actual cause (**the path does not exist**) is never suspected. `EACCES` cannot
distinguish "present but forbidden" from "absent, and its parent is forbidden", and on a wiped or remounted
home it always means the latter.

- **When a failure names permissions, confirm the path EXISTS before touching permissions.** `ls -ld` the
  parent; a mode problem and a vanished directory produce the same errno.
- **Make the read fail loud and specific** — check existence first and print the missing path
  (`no env file at <path>`), rather than letting the filesystem error speak. A guard that reports the
  drizzle it can see is worth more than one that reports the weather in the wrong city.
- **Grep every script's defaults for pre-migration paths** (an old home, a deleted mount). A dead default is
  worse than no default: it reads as "configured" while pointing at nothing, so the failure surfaces late and
  in the wrong vocabulary.
- **Resolving the path better is only half the fix — the decision point must also refuse.** A candidate list
  (env override → host path → repo-local copy) turns a dead default into a working one, but the moment NONE
  resolve the guard is inert again and permits everything. So add an explicit gate at the point that spends or
  acts: `if not <definition set>: return <loud refusal, no affordance>`. **Loading correctly and failing closed
  are two separate changes; shipping only the first leaves the original open hole behind a healthier-looking
  log line.**
- **A startup warning is not a gate.** Printing `FATAL: <thing> is empty` and continuing into service means
  the process runs blind while the operator believes it reported the problem. Either the process refuses to
  serve the guarded surface, or the message is decoration.

### 7c. A forecast must project the window that BINDS, and declare its sample

**Two windows, one comparison, is how a healthy system gets a false alarm.** A gate tracking several rolling
windows must compute its projection from the window that binds *now*, and compare it against *that* window's
own reset. Projecting window A while window B is the binding constraint produces a confident, dated,
meaningless warning.

Measured: a usage gate warned that a 4%-of-month burn "runs out before the monthly reset" — while the binding
window was weekly at 9%, refilling in 37 hours. **A monthly figure cannot exhaust a weekly allowance**, and
the warning ignored that entirely.

- **Take `(percent, reset)` from the SAME window**, selected by whichever binds.
- **Refuse to forecast from an implausibly short sample, and say so instead of alarming.** The same warning
  was built on a rate derived from ~10 hours and extrapolated 30 days, reported to the minute. Below one full
  day of evidence a rate is a guess wearing a date: report the LEVEL, mark the forecast
  `insufficient sample`, and do not escalate on it.
- **A false alarm at 4% is not harmless — it is a WARN-band message that fires every run**, so the channel
  that exists to warn at 85% is already being ignored. When a guard speaks by default on a bad band, a wrong
  band is a standing outage of the channel.

## Pitfalls

- **Silence-on-clean must be the DEFAULT for a cron-shaped guard, never an opt-in flag.** The delivery
  contract reads empty stdout as "nothing happened", so a quiet flag that must be passed means every clean
  run delivers a summary — noise on a schedule, which is how a channel gets ignored. The flag belongs on the
  verbose side. (Measured: a flag written as `--quiet` opt-in made a no-change run speak.)
- **A hardcoded expected value rots; assert a bound, or re-derive it at run time.** An expectation baked into
  a check ("expect 14") goes red the moment the underlying count legitimately changes — a repaired check that
  cries wolf is worse than a broken one, because a broken one is obviously broken while a wrong expectation
  looks like it is working. Prefer "not fewer than N" or read the expected value from the same artifact the
  guard reads.
- **A guard that validates a COPY of the thing is not a guard on the thing.** Pin the expected side;
  derive the actual side from the live artifact (import it, parse it, probe it).
- **A parser that only handles plaintext handles only its own test fixtures.** Real inputs carry
  formatting; ignore it and you miss real cases.
- **Substring classification fails in both directions at once.** Prefer a leading-word test with a
  strict word boundary.
- **A negative control that string-replaces an exact line is a coupling.** Refactoring that line
  turns the control into a no-op that still passes. Keep the line stable or update the control
  together.
- **Never report a hash mismatch as a state change.** Digests from different normalisation rules are
  incomparable; call it unverifiable, not edited.
- **A test that asserts success while doing nothing is the same bug class it exists to catch.** For
  every check, ask: "what would make this print a confident PASS while the thing it guards is broken?"
- **A paid-only code path is an untested code path.** When the verdict logic can only be reached after an
  expensive call (an LLM request, a metered API, a long job), every test of it costs that call — so it is
  tested rarely and badly. **Give the guard a zero-cost evaluation entry point that reads an ALREADY-SAVED
  result** (e.g. `--from-json <result.json>`), and run the battery against recorded output. The fixture can
  be a genuine past result, which makes it stronger than a synthetic one and free to re-run.
- **Never read a job's exit status through a pipe.** `cmd | tail; echo $?` reports `tail`'s status, not
  `cmd`'s, so a failing job reports success in exactly the summary a human will read. Capture the code
  the moment the command runs, or run without the pipe. (The same trap applies to a delivered summary
  built from truncated output: the truncation is where the verdict gets lost.)
- **A guard that cannot go red is a decoration.** If the failure path has never been executed, say so; do not
  cite the guard as evidence.
- **A suite with no runner is a claim, not a control.** A test suite that cannot be executed — no dependency
  manifest, no runner config, restrictive file modes, or the runner simply not installed — proves nothing to
  anyone, including its author. **Size is not evidence; execution is.** Before citing a suite as proof, run it
  end to end once. A suite that has never been run *as a suite* hides its reds indefinitely, and the count of
  passing tests is then a number nobody measured.
- **Attribute every failure before calling any of it a defect.** On a first-ever run, most reds are not
  defects. Sort them at the layer that owns them: runtime/interpreter version (a call convention the test was
  written against may have been removed from the language), a dependency that installed cleanly but fails at
  import (usually a missing *extra*, not a missing package), permissions or unreadable paths, and only then
  genuine defects. **Never make a suite green by weakening an assertion** — fix the interpreter, the harness,
  or the dependency at its own layer. Report the classification with counts, so the reader can see the three
  or four reds that are real instead of the twenty that are noise.

## Verification

- [ ] No lookup is satisfiable by the guard's own output — name the author of the thing found, and confirm the search space is one that author writes.
- [ ] A guard whose count is reported has had its numbers diffed before and after any fix, and the consumers of the old figures are named.
- [ ] Silence-on-clean is the default for a cron-shaped guard; the flag is on the verbose side.
- [ ] No expected value is hardcoded where it can legitimately change — it is a bound, or re-derived.
- [ ] The guard's question and both failure modes are stated.
- [ ] The parser handles the real input formats the artifact uses.
- [ ] Classification is by leading word with a strict boundary.
- [ ] A negative control exists and is proven to bite.
- [ ] The control is not broken by a refactor of the guarded line.
- [ ] After hardening, the positive suite passes and the negative control fails.
- [ ] Every assertion tests the property it names, not a token that correlates with it.
- [ ] Every row measures the artifact its label names — rename the artifact once and confirm the row moves.
- [ ] The suite has a runner a stranger can execute (manifest + config), and it has been run end to end.
- [ ] Failures are attributed by layer (runtime, dependency extra, permission, real) before any is called a defect.
- [ ] The fixture is built from a REAL record, with its real formatting — not hand-written to suit the parser.
- [ ] Every code path that can add an item to the guarded list is covered (count the call sites).
- [ ] The control drives the caller's entry point, not only the leaf function.
- [ ] An unreadable input or output exits non-zero; it never returns the healthy value.
- [ ] Any refusal turned into a GUIDANCE response asserts the forbidden outcome by absence (no quote/cart/`accepts`/signed URL), AND the valid-input twin still carries the affordance.
- [ ] Every path-shaped guard (root/base/reference set) has been INVOKED both ways — one input permitted, one refused — and its DEFAULT root resolves to a path that exists.
- [ ] A definition/reference set that can come back EMPTY has an explicit fail-closed gate at the point that spends or acts — not only a startup warning.
- [ ] Every metric the guard prints is read from an authoritative artifact, or says `UNMEASURED`.
- [ ] The finding count drives the exit code.
- [ ] Any HTTP parsing accepts both `\r\n\r\n` and bare `\n`, and a `200` with an empty body returns UNKNOWN rather than zero.
- [ ] The guard's own overhead is measured, not assumed (quota lookups per fetch, artifacts re-read per item).
- [ ] Any exit code quoted in a report was captured from the command itself, never through a pipe.
- [ ] The verdict logic has a zero-cost re-run path (saved-result evaluation), and the battery uses it.
- [ ] Any guard masked by an upstream gate was tested by importing its predicate directly; the refusal REASON was read, not only the exit code.
- [ ] Every bypass flag was tested and none of them also disables the guard it bypasses.
- [ ] Near-misses are disclosed in the record, not hidden behind a green suite.
- [ ] After a logic fix, the control was re-read: if it failed, the FIXTURE was corrected rather than the guard reverted.
- [ ] Every verdict newly made reachable by a fix has a defined handling path (a handler added for it, not discovered by crashing).
- [ ] Any forecast projects the window that BINDS, against that window's own reset, and declares its sample length.

For verification under a throttled fleet write gate, see `references/gate-saturation.md`.
For a workable control battery (clean / findings / unreadable / missing / stale-path, with a zero-cost
saved-result path), see `references/control-battery.md`.
