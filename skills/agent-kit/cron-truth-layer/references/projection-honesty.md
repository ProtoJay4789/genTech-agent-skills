# Projection honesty — forecasting an exhaustible allowance

A monitor that forecasts "when do we hit the ceiling" is only as good as its **window start**. Everything
below was measured on a live allowance gate that reported a 21% month as `WARN` with a projection that
changed every day.

## 1 · Three inputs, only one of which is usually measured

| input | typical source | honest? |
|---|---|---|
| current percent | the provider's API | measured |
| reset timestamp | the provider's API | measured |
| **window start** | a constant in the code (`reset - 30d`) | **assumed — and it drives everything** |

`rate = pct / (now - start)`. Get `start` wrong and the rate is wrong by the same factor, and the rate is
the only thing the projection is built from. A hardcoded cycle length is the most common defect and it is
invisible because the output has a decimal point and a timestamp.

```python
# ❌ the rate is a function of a constant nobody checked
start   = reset - timedelta(days=30)
elapsed = (now - start).days
rate    = pct / elapsed
```

**Measure the start instead — the observations already contain it.** Take the provider's percent over time
(the monitor's own output files are a perfectly good series), find the reset (a hard drop), then
back-extrapolate the post-reset burn to 0%:

```python
# post-reset points: (t, pct). Median adjacent slope = real burn.
rates = [(p2 - p1) / ((t2 - t1).total_seconds() / 86400) for (t1, p1), (t2, p2) in zip(obs, obs[1:]) if p2 >= p1]
burn  = statistics.median(rates)                  # %/day, measured
start = last_t - timedelta(days=last_pct / burn)  # when the window opened, measured
```

Measured once: an assumed 30-day cycle implied 4.6%/day; the log series gave a **4.00%/day** median over
five points and a window start (~30.7 days before the reset) that matched the observed reset. Same
projection date to within a day — but now it stops moving.

## 2 · An assumed input must not manufacture a derived quantity

If the start is assumed, the only honest elapsed span is **the one actually watched** — first observation in
this window until now. Reset-date arithmetic on a guessed window length invents elapsed time, and elapsed
time is the rate's denominator.

Measured failure mode: a window 4 hours old, evaluated against a 30-day guess, yields an "elapsed" of
~26 days, so a 4%/day burn becomes ~0.9%/day and the projection lands **110 days out** — or, depending on
which constant is in play, several days too early. Either way the date is an artefact of arithmetic rather
than a forecast.

## 3 · Escalation must only fire on a window that can actually bind

This is the defect that produces a permanent, ignorable alarm.

> A window whose reset arrives **before** the projected exhaustion is a **refill**, not a wall. Escalating on
> it warns about a ceiling that opens.

```python
days_to_reset = (reset - now).total_seconds() / 86400
binds_work    = days_left is not None and days_left < days_to_reset   # only this can stop work
```

Measured: a monthly allowance at 21% with 25 days to refill and a 17-day runway escalated to `WARN` on every
run — four times a day — while nothing was wrong. Every one of those alarms was the monitor reading its own
forecast.

**Grep for every assignment to the verdict, not just the function that computes it.** The same script had a
`band()` function *and* a later block that re-raised the band when `runs_out_early` was true. Fixing the
first left the alarm firing, because the second silently reassigned it. Any variable named `band`, `level`,
`status` or `severity` should be assigned in exactly one place.

## 4 · Validate the model against an event that actually happened

The previous window's exhaustion is a free calibration point. Compare every past prediction to the real
event and measure the miss:

```
last four pre-reset predictions missed by -0.2 to +0.6 days
→ the maths is sound; the INPUT is broken. Repair the input, do not rewrite the model.
```

This distinction decides the shape of the fix and stops a future session from "simplifying" a model that was
never the problem. Write the measurement down next to the code.

## 5 · The tell, and the test

**A forecast whose date moves on every run is reading `now`, not forecasting.** Four consecutive runs
produced `Nov 10 → Nov 17 → Nov 19 → Nov 21`. An ETA that creeps toward you at one day per day is
`now + constant` wearing a timestamp.

**And a band that has not changed across runs while the underlying percent has** is a level alarm being
driven by an invariant. When the user says *"it has said WARN for a while now"*, that sentence is the
finding — an alarm nobody reacts to is worse than silence.

Test the decision function as a **truth table**, not by reading the output once:

| state | expected |
|---|---|
| low %, window refills after the ETA | silent (the refill makes exhaustion harmless) |
| high %, window still refills after the ETA | CRITICAL (a real wall) |
| mid %, window refills *before* the ETA | silent (cannot bind) |
| high %, window does not refill before the ETA | CRITICAL |

All four must be exercised in one script run. If only the live state was tested, the escalation branch was
never proven.

## 6 · Report the basis in the same line as the number

```
rate: 4.05%/day over 5.2d (30d monthly cycle, rate over 5.2d watched) · basis: assumed
projected to hit 100% around 2026-11-22 — 17.4 days of headroom
⚠️ projection rests on an ASSUMED window start — treat the date as indicative, not booked
```

- **Name the basis and its confidence** (`measured` / `assumed`) on every report and persist both in state, so
the next run cannot quietly upgrade a guess to a measurement.
- **Guard the sane range.** A rate that would exhaust a full window in under a day, or cannot exhaust before
the refill, is not a date — print "burns too slowly to exhaust before the reset" instead of a fabricated
timestamp.
- **Prefer the measured cycle over the assumed one whenever the series exists**, and keep the constant as the
  documented fallback with a comment stating how it was measured and when.
