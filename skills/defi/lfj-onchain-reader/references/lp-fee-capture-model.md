# LP fee capture — why the published APR is not what your capital earns

A pool's advertised APR divides **all** fees by **all** TVL. Your position earns neither of those numbers.
It earns fees in proportion to how much liquidity sits in the bins the price actually crosses, over the time
the price spends there. Two positions in the same pool can differ by an order of magnitude.

## The three numbers that get confused

| number | what it divides | when it is useful |
|---|---|---|
| **Pool APR** (aggregator) | fees / TOTAL TVL, incl. bins parked far from spot | comparing venues on one axis |
| **In-range APR** (usually the venue UI) | fees / liquidity in the active range | what you get *while in range* |
| **Your realised APR** | fees you actually kept / your capital / days held | the only one that is true after the fact |

**A UI quoting several hundred percent while the aggregator quotes tens is not a contradiction** — they are
measuring different denominators. It is not a reason to distrust either; it is a reason to stop comparing them.

## Width decides fee density and time-in-range, and they move opposite

For a bin step of 0.10% and a daily volatility σ, expected time before price leaves a band of half-width `w`
scales as **(w / σ)²**. Fee density scales roughly with **1 / (liquidity inside the band)**.

| band | liquidity inside | in-range APR | expected hours in range |
|---|---|---|---|
| ±0.5% | thin | very high | under 1 |
| ±2% | moderate | high | ~half a day |
| ±7.5% | wide | modest | ~a week |

**Do the arithmetic against gas before believing the narrow-band number.** A band that exits many times a day
pays gas many times a day. On a cheap chain gas may be affordable; on an expensive one the same width is a loss.

## ⚠️ The term the fee model omits: impermanent loss and trend

The narrow-band APR table ignores IL, and IL is what decides the outcome in a trending market. A narrow band
exiting repeatedly **re-enters the falling asset repeatedly**. In chop that is fee harvesting; in a downtrend
it is accumulating the thing you were trying to avoid.

**Fee maths says narrow. IL says wide. The deciding variable is chop vs trend, and chop vs trend is measurable
from structure (higher lows vs lower lows) — not from the APR.**

So: **width is the second decision. The first is whether to be in at all.** Compute the band only after the
structure read says the position should exist.

## Separate fee APR from emissions APR — they are different assets

An aggregator's `apy` can be entirely `apyReward` with `apyBase` at zero. That yield is paid in a token, so:

- it is **not comparable** to a fee APR;
- its realised value depends on the reward token's price when you sell;
- an `apyReward` in the tens of thousands with a high `sigma` is a broken calculation, not an opportunity.

**Rank venues on `apyBase` only when the question is "which pool pays the most fees."** Note emissions
separately, with the token named.

## Cross-venue screening that actually answers "where do I earn most"

1. **Convert every candidate to fee APR** — `(volume24h / TVL) × fee_tier × 365`. Do not rank on a reported
   `apy` you have not decomposed; several active pools report `0.00%` because fee reporting is missing, which
   reads as "no yield" when the pool is in fact busy.
2. **Daylight the depth** — TVL and 24h volume both. A high fee APR on a thin book is a fee APR you cannot exit.
3. **Divide APR by realised volatility** — `APR / σ_annualised`. Under ~0.5 you are taking more risk than you
   are paid for; over ~2 is genuinely attractive. This single ratio is more informative than either input.
4. **Then check gas per rebalance as a fraction of one day's income.** At small size this dominates: the same
   position can be viable on a cheap chain and structurally unviable on an expensive one.

## Comparing a concentrated venue to a deep one

A smaller pool with higher turnover per dollar can beat a larger pool on fee yield — and still be the wrong
choice, because the trade is **yield you can exit** against **yield you merely accrue**. Both belong in the
answer: fee APR, depth, and the gas cost of managing the position at the size actually being deployed.
