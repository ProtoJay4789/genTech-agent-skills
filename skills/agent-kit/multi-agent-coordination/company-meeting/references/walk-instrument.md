# The walk instrument — CLI and semantics

The walk is only a practice until it is recorded. This is the instrument that records it: a small append-only log
plus two readers, wired into the PA suite so the meeting has something to carry forward.

Path on this fleet: `profiles/gentech/scripts/walk-log.py`, state at `profiles/gentech/state/walk-log.jsonl`
(override with `WALK_LOG` for testing — **always** override it when testing, or the suite writes into production).

## Recording a visit

```bash
python3 walk-log.py log --seat <seat> \
  --heard "what they said, in their words"   `# repeatable` \
  --in-the-way "what they named as blocking them" \
  --see "anything they wanted HQ to look at" \
  --resolves "the earlier concern this visit closes, quoted"
```

- **A visit with nothing on it is refused (`exit 2`)** — no `--heard`, no `--in-the-way`, no `--see`, no
  `--resolves` means nothing was observed. But a visit that carries **only** `--resolves` is legitimate: closing a
  concern is an observation. Get that guard right or the close path is unreachable. *(Measured: a guard that
  demanded content on every visit refused the closing visit, so a matcher bug looked like a matching failure.)*
- **`--heard` repeats.** Record several quotes; they are the most quotable part of the record.
- **Timestamps come from the clock, never from the caller.** A date a human types is a date a human can get wrong.

## Reading it (the two PA-suite sections)

```bash
python3 walk-log.py open                      # concerns no later visit closed
python3 walk-log.py followup --after 1        # concerns nobody walked again
```

Both are **silent with exit 0 when empty** and **`exit 2` on an unreadable log** — because silence means "nothing
open", and a corrupt log that reports silence is the worst available answer.

**Two different questions, never summed:**

| section | question | what it does NOT tell you |
|---|---|---|
| `open` | which concerns are still outstanding | whether anyone is working them |
| `followup` | which seats were never walked again | whether the concern was solved |

## Closing a concern

`--resolves` quotes the original `--in-the-way` text. Matching is **case-, space- and punctuation-insensitive**
and scoped to the same seat, because a human retyping a reference will never match byte-for-byte and a silent
non-match leaves a closed item listed as open forever.

Four cases to prove before trusting it:

| case | expected |
|---|---|
| exact quote | closes |
| `"NO google oauth   credential!!"` closed by `"no Google OAuth credential."` | closes |
| the same quote resolved on a **different seat** | stays open |
| an unrelated concern, nothing resolved | stays open |

## Wiring it into a daily bundle

```bash
run walk    python3 profiles/gentech/scripts/walk-log.py open
run walk    python3 profiles/gentech/scripts/walk-log.py followup --after 1
```

Check the wrapper with the parser it actually uses — a bash script with arrays needs `bash -n`, and `sh -n` will
report a syntax error that does not exist.

## What the log is for, beyond the meeting

A corpus: several departments, the same three questions, week after week, with the answers **and their
outcomes** dated. That is the one thing about a fleet that cannot be reconstructed after the fact — what actually
blocked real work on a real day — and it is the raw material if these lanes are ever used to train anything.
