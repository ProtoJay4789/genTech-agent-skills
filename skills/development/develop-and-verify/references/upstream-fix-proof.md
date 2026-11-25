# Proving a fix to someone else's code

The evidence a maintainer needs before a PR goes up — and the evidence your own gate needs before you say "fixed".
A contribution is not "the patch looks right"; it is "this failed before, it passes now, and here is the proof in
one record".

## 1 · Install the toolchain the repo asks for, not the one you have

Read the version directive FIRST — `go.mod`'s `go 1.x`, `.nvmrc`, `rust-toolchain.toml`, `python_requires`,
`engines` in `package.json`. Measured: a Go repo declared `go 1.26.10`; a toolchain fetched at 1.23.4 could not
build it, and the wasted download is the cheap half of the cost — the expensive half is diagnosing the resulting
build error as a code problem.

Install into a profile-local directory and put it on PATH for the command only. Do not modify the host's
toolchain to satisfy one repository.

## 2 · Write the test so it fails for the RIGHT reason

- **Assert the BEHAVIOUR, not the internal value the fix computes.** A test that reads the variable your patch
  sets passes on the patch by construction and says nothing about the old code. Find the observable — a network
  call, a counter, a written row — and count that.
- **Add a CONTROL test that must pass both before and after.** Without it, the primary test can pass simply
  because the harness never triggers the behaviour at all.
- **Keep the control cheap to satisfy.** If it needs a registration or fixture the buggy path did not, that is a
  signal the control is exercising a different route, not extra work to skip.

## 3 · A build failure is not a red test

Changing a public type means a test written against the old API **will not compile** against the new one.
`[build failed]` is evidence of a type mismatch, not of the bug. To get a genuine red you need the OLD-API shape
run against PRISTINE upstream code, producing a behavioural assertion failure:

```
SyncFacilitatorOnStart: false was ignored — GetSupported called 1 time(s) during construction; want 0
```

Keep a separate pristine clone for this. Do not use `git stash` or `git checkout` inside the working tree to
manufacture the comparison — that also reverts the fix you are trying to measure, and you end up staging the
revert as part of the evidence.

## 4 · Prove red → green in one record

Three runs, same test, same command, reported together:

| run | expectation |
|---|---|
| pristine upstream + old-API test | FAIL, with the assertion message |
| your branch + new-API test | PASS |
| full suite of every package you touched | ok |

A PR body that says "adds a test" is a claim. One that shows the failing message from before and the passing
run after is a receipt.

## 5 · Read the root cause as a TYPE before treating it as a CONDITION

**When an explicit value is ignored, ask first whether the API can REPRESENT "not set" separately from "set to
the zero value".**

A `bool` field cannot: `false` and unset are the same value, so an explicit `false` is unrepresentable and **no
amount of internal logic can honour it**. The same holds for `int`/`0`, `string`/`""`, and any struct field whose
default is its zero value.

The fix is a pointer (`*bool`, nil = unset) or an explicit `...Set` sentinel plus a documented default — never a
cleverer condition.

Measured: a guard `if config.Timeout != 0 { syncOnStart = true }` was identified as the defect and rewritten, and
the bug survived — because `Timeout` had been assigned its default two lines above, so the condition was
always true regardless. The condition was the *symptom*; the type was the *cause*. The reporter's own diagnosis
was one layer short, and so was the first patch.

## 6 · Re-prove your own counter-example after the first attempt

The first rewrite kept the defective shape — `if !syncOnStart && facilitator != nil { syncOnStart = true }` is
the same unconditional override in fewer lines. It was only caught by **instrumenting the value at the decision
point** and reading it: `syncOnStart=true` under the patch.

**After rewriting a guard, feed it the exact input that proved the original wrong and read the value at the
decision point.** A patch that looks different is not a patch that behaves differently, and a diff review will
not tell you which one you wrote.

## 7 · State the compatibility cost, and name the alternative you did NOT choose

A change to an exported type is breaking for every caller. In the PR body:

- say **"this is a breaking change"** in its own paragraph, not buried in a list
- enumerate what moved (internal call sites, existing tests — with a count)
- name the backward-compatible shape you rejected and why (e.g. a sibling `...Set bool` that keeps the old field
  but creates two fields that can disagree)

The maintainer owns that trade. Presenting it is what turns a contribution from presumptuous into reviewable —
and it is the difference between a PR that gets a considered reply and one that gets closed unread.
