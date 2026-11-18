# Prediction Track Record — making the fleet answerable for its own claims

A brain that records decisions and never outcomes makes a correct call and a wrong one look identical. The
next reader inherits both as equally true, and nothing ever adjusts. This file is the shape that fixes it:
**claim → horizon → resolution → scoreboard.**

## The three tables

```sql
predictions(id, ts, seat, domain, claim, subject, horizon, confidence, evidence,
            status[open|hit|miss|void], resolved_ts, outcome_note)
patterns   (id, ts, seat, domain, statement, support, contradiction, updated_ts)
```

Storage: one SQLite file on the shared filesystem, plus a JSON export written into the synced store.
**A binary DB inside a synced folder produces conflict blobs** — the export is the sync-safe half, and the
note in the export must say it is generated and never hand-edited.

## The two refusals that make it honest

1. **No horizon, no claim.** `--by` must be a date in the future. A claim with no resolution date can never
   be scored, so accepting it manufactures confidence with no accountability.
2. **No evidence, no resolution.** `resolve` requires a note saying HOW the outcome was checked. A hit
   claimed from memory is how a track record becomes fiction.

**And a third, learned the hard way by scoring my own prediction a week early: a horizon in the future is
not an outcome.** A claim resolved before its date is an opinion with a timestamp — and a tool that permits
it is an instrument for manufacturing a track record. Refuse it, with an explicit `--early` escape for the
real case (the outcome is already known), and make `--early` demand the reason in the note.

## Commands

```bash
record --seat <seat> --domain <d> --claim "…" [--subject <path>] --by YYYY-MM-DD [--confidence 0..1]
resolve <id> --hit|--miss|--void --note "how we checked" [--early]
due            # past horizon and still open — the list that keeps everyone honest
score [--seat S] [--domain D]
calibrate      # stated confidence vs actual hit rate, bucketed
pattern-add --seat S --domain D --statement "…"   # a reusable rule earned from outcomes
patterns
export         # regenerate the synced JSON
```

## Rules that keep it from rotting

- **Surface `due` inside the existing health voice**, not as its own job. An unresolved past-horizon claim
  is a real finding; a ledger nobody reads is the same mute-instrument failure as a producer with
  `deliver: local`.
- **Never overwrite a resolution.** A second `resolve` on a closed row is refused — corrections are new
  rows or an explicit reopen that records the mistake in the note, so history keeps the error.
- **`calibrate` must refuse to speak below ~5 resolved-with-confidence rows.** A calibration table built on
  two data points is decoration, and publishing it invites a decision.
- **Seat and domain are the join keys for the scoreboard.** Per-seat rate is what makes "this seat's calls
  are worth acting on" a measurement rather than a reputation.
- **Void is a real outcome.** A claim overtaken by events was neither right nor wrong; forcing it into
  hit/miss distorts the rate in whichever direction the guess went.

## What this is NOT

The ledger scores **claims**, not trades — a trade journal with P&L is a different instrument. And it is not
a prediction market: no money, no counterparty, only accountability. Keep those apart when reporting, or the
first profitable-looking number will be read as a track record it never was.
