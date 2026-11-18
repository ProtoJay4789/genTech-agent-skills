# The control battery — the cases every guard suite needs

A guard suite that only exercises the happy path proves the guard can be satisfied, not that it can
bite. Run this set against the guard's **entry point** (the same function the caller uses), on scratch
copies with an injectable root.

## The five cases

| # | case | the verdict that proves the guard works |
|---|---|---|
| 1 | **clean input** | passes, and prints nothing alarming |
| 2 | **input carrying a real finding** | reports it AND exits non-zero — a finding count that does not drive the exit code is the guard disagreeing with itself |
| 3 | **unreadable input** (missing file, bad parse, unparseable body) | a distinct UNKNOWN/UNREADABLE state, non-zero — never the healthy value |
| 4 | **input in the wrong SHAPE** (wrong schema, wrong key path, a field the code assumes exists) | a named refusal quoting the file and the offending key — never a bare `KeyError`/`AttributeError` traceback, which names the engine and hides the file |
| 5 | **input that satisfies the form but not the property** (a claim with no evidence behind it) | flagged as a claim and **not counted** as the satisfied state |

Case 5 is the one most suites omit, and the one that matters most when the guard's job is to decide
whether something is *done*: a data file can assert its own success (`status: closed`, `verified: true`,
`complete: yes`) with nothing behind it. The guard must be able to say **"that is a claim, not a state"**
and must keep the item open while saying so.

## Two assertions that belong in every battery

- **The suite must not mutate live state.** Snapshot the real state file's mtime (or hash) before the
  suite and assert it is unchanged after. A test that writes to production manufactures exactly the
  event the guard exists to police, and the fabricated record outlives the test run.
- **Every case asserts a MESSAGE, not only an exit code.** Exit codes collide (2 for both "no such
track" and "evidence too thin"); matching a phrase the refusal must contain is what distinguishes
"refused for the right reason" from "refused for an unrelated reason".

## Running it

1. Point the guard at a scratch root (`os.environ.get("X_ROOT", <live default>)`), never at production.
2. Run all five cases in one invocation and print `GREEN`/`RED` per case — a battery assembled from
   five separate manual runs cannot be re-run by the next person.
3. Re-run the whole battery immediately after any edit to the guard, including edits that look cosmetic.
4. Assert the **default** root separately: a fixture that injects a scratch root leaves the shipped
   default untested, and the default is what runs in production (a dead default fails open, silently).
