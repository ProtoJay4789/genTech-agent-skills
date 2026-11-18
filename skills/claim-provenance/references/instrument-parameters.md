# The instrument's own parameters are claims too

Two numbers can each be produced by working code, carry a plausible instrument name, and still be false —
because the **parameters inside the instrument** were wrong. These are the two shapes, both measured, both
cheap to check and expensive to miss.

---

## 1 · A summary that sums a key its reader never SETS

**Every summary is a contract between a writer and a reader, and the key name is the contract.** When they
disagree the result is not an error — it is a stable `0.0` that reads as a real observation.

Measured: an inbound-payment reader appended rows carrying `amount`. Every consumer summed `usdc`. The key
did not exist on any row, so `sum(...) == 0.0` on every run — for as long as the code had existed — and the
report said, in a confident sentence, *"not earning."* Nothing logged a warning, because reading a missing
dict key with a default is not an error.

**Checks, in order:**

1. **Print one raw row next to the aggregate.** If the aggregate is `0` and the row is not, the contract is
   broken. This one line detects the whole class.
2. **Grep the writer for the exact key string** the consumer passes to `.get()` / `[]` — not a similar name.
   `amount`, `amount_usdc` and `usdc` are three different fields.
3. **Assert a non-zero control**: run the aggregate over a fixture or a known-populated window. A sum that
   has never returned non-zero has not been tested; it has only been observed returning zero.

**Rule:** *when a metric is permanently zero, suspect the key name before believing the metric.* A real
zero fluctuates at the boundary; an unwritten key is exactly `0` forever.

---

## 2 · A window computed from an ASSUMED rate

**Any "last N days" is arithmetic over a rate. If the rate was assumed rather than measured, every number
inside the window is scaled by that error — and a narrow window looks like a quiet period, not like a bug.**

Measured: a chain scanner converted days to blocks with `BLOCKS_PER_DAY = 43_200` (the arithmetic for
2-second blocks). The chain actually produces **431,952** blocks/day — 10× faster. So a "7-day" query
covered **0.70 days**, and the report said *"0 USDC in 7d"* one day after a payment had landed. Nothing
was broken except the constant, and everything downstream was confidently wrong.

**Checks:**

1. **Derive the rate from two known points, then compare it to the constant.** One block number with a known
   timestamp is enough: `rate = blocks_elapsed / days_elapsed`. Print the measured rate beside the assumed one.
2. **State the covered span, not just the intended span.** "7d requested → 0.70d covered" is a sentence a
   reader can act on; "7d" is not.
3. **Put the measurement in the comment beside the constant**, with the derivation, so the next reader can
   re-check it instead of trusting it.

**Rule:** *a constant standing in for a measured rate is a claim, and it is the kind that never fails a
test — it only makes every answer wrong by the same factor.*

---

## 3 · Both classes pass every gate you already have

The code runs, the schema validates, the metric is a float, the window is an integer. **Neither defect throws,
neither shows up in a diff, and both look like a calm system.** That is why they belong in the report:

- **Say which layer you verified.** "The reader returns rows" and "the sum means what its label says" are
  different claims; only the second is the answer.
- **When a number surprises you, re-derive one input before doubting the conclusion.** In both cases the
  fastest path to the truth was recomputing the smallest underlying quantity, not re-reading the code.
