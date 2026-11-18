# Comparing Venue APRs — Four Numbers Wearing One Name

When someone asks "where do I earn the most", the answer depends entirely on **which APR** they mean.
The same pool routinely carries four different figures that differ by an order of magnitude, and none of
them is a data error. **Identify the kind before comparing, or the comparison is between different
quantities.**

## The four kinds

| # | kind | denominator | what it answers |
|---|---|---|---|
| 1 | **fee APR (aggregate)** | total pool TVL | what the whole pool earns per dollar of ALL capital, including idle bins |
| 2 | **fee APR (in-range)** | liquidity in the active band only | what ONE dollar placed near spot earns while it stays in range — always higher than (1) |
| 3 | **emissions APR** | position value, paid in a reward token | nominal yield that decays with the token price |
| 4 | **mean APR** | same as 1 or 2, averaged over N days | what it usually pays, vs what it pays today |

**Measured spread on one pool in one week:** 23.7% (today, aggregate) · 67.5% (30-day mean) · ~200%
(venue UI, in-range) · and a competitor advertising **663%** which was **entirely `apyReward` with
`apyBase: 0`.** Four numbers, one pool, and only two of them are comparable.

**Rules:**
- **Never compare a fee APR against an emissions APR.** A reward-token yield requires selling the
  reward; the fee yield does not. Normalise emissions to "value realisable at today's price" or
  state plainly that it is not comparable.
- **State the denominator.** "The venue shows 200%" and "the aggregator shows 24%" are both true and
  describe different capital.
- **Quote the point-in-time figure with its mean beside it.** A single-day reading on a volatile pool
  is one observation, not a rate.
- **A pool flagged `outlier` with a high `sigma` on its own APY** is telling you the rate is unstable.
  A sibling pool reporting an implausible magnitude (six figures, say) means the reward calculation
  is broken, not that the yield is enormous.

## A rising APR in a falling pool is a SHRINKAGE ARTEFACT

**Fees are roughly proportional to VOLUME. APR divides them by TVL. So when LPs leave and volume
stays, APR rises for arithmetic reasons and for no other.**

Measured on one pool:

```
2026-06-01   TVL $3,876,992   APR   7.45%
2026-06-15   TVL $  374,418   APR  85.55%   <- -90% TVL in 14 days, APR up 11x
peak-to-now  $27,967,067 -> $313,450 = -98.9% (89x)
```

**The APR was not a yield. It was the inverse of the exit.**

**Before trusting any APR, pull the pool's TVL history and compare its direction to the APR's.**
`https://yields.llama.fi/chart/{pool-id}` returns per-snapshot `tvlUsd` and `apy`.

| TVL | APR | reading |
|---|---|---|
| flat / rising | flat / rising | genuine demand |
| **falling** | **rising** | **LP exodus — you are buying into a shrinking book** |
| rising | falling | competition arriving; the edge is being arbitraged away |
| falling | falling | the venue is dying, not just under-attended |

**And it cuts the other way too:** a high APR in an abandoned pool is an *invitation*. LPs will return
and compress it. **The edge exists only while the abandonment holds** — so the monitor that matters is
TVL, not APR.

## The risk-adjusted gate: APR ÷ realised σ

**"Is the APR high" is the wrong question. "Is the APR high relative to how much this asset moves"
is the right one**, and it is a single ratio.

```
APR / sigma_annualised
  > 2      attractive - paid well above the risk taken
  ~1       fair
  < 0.5    underpaid - taking more risk than the yield compensates
```

Measured the same day, two assets: **53.2% APR on 40.4% vol = 1.32** against **23.7% APR on 55.6% vol
= 0.43** — a **3x difference in risk-adjusted terms** for a 2.2x difference in headline APR. The
headline understated the gap.

**Both terms are measurable:** realised σ from daily closes (`stdev` of log/simple returns x sqrt(365)),
APR from the venue. **Publish the ratio, not just the APR** — a 200% pool on a 200%-vol asset is a
treadmill.

## Fee density is a function of the band the price CROSSES

In a concentrated/Liquidity Book pool, **fees accrue in the bins the price actually traverses, not
across the pool.** So a narrow position's effective APR is far above the aggregate, and the aggregate
understates it — which is why a venue can honestly display 200% beside an aggregator's 24%.

**Measure the density directly:** read a span of bins around the active id (`getBin(uint24)`), value
each bin in USD, and compute what a candidate position is as a fraction of a given band.

```
band      USD value   $100 position =     in-range APR
+-0.5%    $3,189      3.04% of the band    ~2,400%
+-2.0%    $10,182     0.97%               ~770%
+-7.5%    $27,909     0.36%               ~280%
```

**The trade-off is TIME.** Expected time to exit a band of half-width `w` under a random walk scales as
`(w / sigma_daily)^2` — **quadratically**, so narrowing by 10x costs 100x the holding time:

```
+-0.5% (5 bins, binStep 10)   ~0.7h before exit   ~34 exits/day
+-2.0% (20 bins)              ~11h                ~2 exits/day
+-7.5% (75 bins)              ~160h (a week)      ~0.2 exits/day
```

**A venue's preset rungs are usually volatility-calibrated whether or not it says so** — the widest
rung on this venue (±75 bins = ±7.5%) landed within 3% of `sigma_daily x sqrt(7)`, i.e. "one week at
one standard deviation". **Compute the rung a user needs from their holding period rather than accepting
the default**, which is typically far too narrow: the default 11-bin opening was ±0.55% = ~4 hours of
holding time.

## Gas is a floor, not the decision — except at small size

Rebalancing cost is per-transaction, so its share of income scales as `1 / position_size`:

```
gas as a share of ONE DAY's income, $500 position
  Avalanche ~$0.024/tx    7.3%
  Solana    ~$0.00025/tx  0.03%     (~240x less drag)
```

**At a few hundred dollars the fee math says "narrow, and rebalance often"; the constraint that
actually binds is impermanent loss and trend, not gas.** A band narrow enough to earn 2,400% exits 34

times a day — in chop that is 34 harvests, and **in a trend it is 34 re-entries into a falling asset.**
**The width decision is downstream of the structural one**: width is the second question; whether to be
in the pool at all is the first, and a broken structure answers it before any APR does.

## The comparison table to produce

For each candidate venue, fill every column — a table missing the last two invites the wrong choice:

| pool | TVL | 24h volume | turnover | APR (kind named) | sigma | APR/sigma | gas share at size |
|---|---|---|---|---|---|---|---|

**Turnover (volume/TVL) is the fastest sanity check on any APR**: at a known fee tier,
`APR ≈ turnover x fee_tier x 365`. If a quoted APR cannot be reproduced that way, find out which
assumption differs before believing it.

**⚠️ But run that formula on MEAN turnover, never on one day's.** `x365` turns a single observation into an
annual claim, and a spike day therefore produces a **ceiling, not a rate.** Measured: one day's turnover
gave a $50 position an implied **234.8% APY against the feed's 54.6%** — a **4.3x** overstatement, because
the day measured was a scheduled-release/selloff spike. Quoting that figure as the yield is the same error
as a 1,693% pool priced off a window that did not persist.

**Publish BOTH, labelled:** the feed's own smoothed `apyBase` as the **planning number**, and the
vol-derived figure as the **ceiling**. Any secondary number computed off the fee estimate (gas payback in
days, IL payback in days) inherits the same multiplier — computing gas payback off the spike denominator
gave `1.2 days` where the sustainable figure was `5.3`, and both were reported before the error was caught.

## Size does not change the fee-to-IL ratio — only the fixed costs

**Fee income and impermanent loss both scale linearly with the deposit, so any ratio between them is
SIZE-INVARIANT.** IL payback measured in days of fees is therefore identical at every size:

```
LFJ joe-v2.2, sustainable base 54.6%, IL @2x divergence = 5.72%
  $50     0.0154% of pool   $0.0748/day   IL $2.86   ->  38.2 days
  $500    0.154%            $0.7483/day   IL $28.60  ->  38.2 days
  $5,000  1.54%             $7.4828/day   IL $286.00 ->  38.2 days
```

**What size actually buys is the amortisation of FIXED costs** — gas above all: a `$0.40` round trip is
`5.3 days` of sustainable fees on a $50 book and `0.05 days` on `$5,000`. **That is the entire case for a
larger book, and it is worth about five days.**

**What size does not buy is safety.** IL is proportional, so a bigger position is a **bigger absolute loss**,
not a safer one. A table that shows IL shrinking as a percentage with size is showing the fixed-cost effect
and mislabelling it.

**The cost that never amortises is attention** — a $50 range and a $5,000 range cost the same monitoring,
and that is the honest reason a small book is *tuition* rather than income. Say that in those words instead
of implying the small position earns a worse per-dollar rate; **it does not, and saying so is a category
error.**

**Before claiming any size effect, check whether the numerator and denominator measure the same dimension.**
If both scale with size, there is no size effect to report — only a fixed-cost effect.

## The shape question is downstream of the structural one
