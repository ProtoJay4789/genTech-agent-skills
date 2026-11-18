# Sizing a concentrated LP position

Depth for the cases where the width of a range, not the choice of pool, is the decision.
Load this when a concentrated (bin/tick) position is being sized or re-centred.

## The fee-capture model — fees land in the bins the price CROSSES

**Do not spread daily fees proportionally across every band of the pool.** That model is wrong in the
direction that matters: dividing a pool's daily fees by the dollar value of a ±5-bin band once produced
"24% APR" for a position that actually earns in the thousands.

Fees accrue to the liquidity in the bins the price actually traverses. The numbers that decide a
position's yield are:

    your share of the band  = position / (liquidity in the traversed band + position)
    in-range APR           = daily_fees x share x 365 / position

**Read the liquidity distribution around spot before quoting any narrow-range yield.** One call per bin
(`getBin(uint24)`), batched — see `lfj-onchain-reader` for the selector, the batch pattern, and the
sweep-validation control against `getReserves()`.

What the sweep reveals is the whole opportunity. On one AVAX/USDC pair, **±60 bins held only ~9% of the
pool's TVL** — nine tenths of the capital was parked far from spot earning nothing, and a $100 position
bought **3.04% of the closest band**. That is how a small, abandoned pool can out-earn a large actively
managed one on FEE capture while being 86x smaller.

**A pool whose liquidity is parked wide is a fee-density opportunity. The aggregates cannot show it; the
bin sweep can.** The corollary: the same measurement tells you whether a *large* pool is actually
competitive — deep TVL concentrated in the near bins means your share is a rounding error no matter how
much volume it prints.

## Width is a time-in-range decision, and it scales with the SQUARE

For a random walk, expected time to exit a band of half-width `w` is `(w / σ_daily)^2` periods. Doubling
the width quadruples the hold, and the narrower band's higher APR is bought with a proportionally shorter
life.

Measured on one AVAX/USDC pair: daily fees $216, σ 2.91%/day, position $100, gas $0.0236 per rebalance.

| width | bins | liquidity in band | your share | in-range APR | hours in range | exits/day | gas/day | net/day |
|---|---|---|---|---|---|---|---|---|
| ±0.5% | 5 | $3,189 | 3.040% | 2,399% | 0.7h | 33.9 | $0.799 | **$5.77** |
| ±1.0% | 10 | $6,080 | 1.618% | 1,277% | 2.8h | 8.5 | $0.200 | $3.30 |
| ±2.0% | 20 | $10,182 | 0.973% | 768% | 11.3h | 2.1 | $0.050 | $2.05 |
| ±5.0% | 50 | $23,195 | 0.429% | 339% | 70.9h | 0.3 | $0.008 | $0.92 |
| ±7.5% | 75 | $27,909 | 0.357% | 282% | 159.4h | 0.2 | $0.004 | $0.77 |

**On a cheap-gas chain the narrow band wins even after paying for 34 rebalances per day.** Gas is not
the constraint at this size — impermanent loss is. Thirty-four daily re-entries into a falling asset is a
loss amplifier wearing a fee machine's clothes.

## Width is the SECOND decision; the regime is the first

A fee table like the one above is only valid while price oscillates. In a confirmed downtrend the same
narrow band harvests fees on the way down while accumulating the falling asset, so the fee arithmetic and
the loss arithmetic point in opposite directions: **the fee side says narrow, the IL side says wide, and
the deciding variable is chop versus trend.**

**State the regime switch beside any width recommendation.** The width is not the strategy. A band that
earns 2,399% while in range earns zero plus full directional exposure once it exits, and in a trending
market it exits constantly in the same direction.

## A venue UI's presets are already volatility-scaled — read them that way

Check the UI's offered widths against realized σ before inventing a range ladder. One venue's ±75-bin
preset (≈7.5%) matched "one week at ±1σ" (7.70%) almost exactly, while its default 11 bins (≈0.55%) held
for under four hours.

**The UI is not offering an opinion about width — it is offering a menu with an unstated holding period
per item.** Naming that holding period is what turns the menu into a decision, and it costs one σ
measurement.

## Gas as a share of income, by position size

Unit gas cost says nothing about whether a position is worth running; the ratio does, and it moves
inversely with size. Measured on a pool paying 23.7% with Avalanche at $0.0236 per rebalance:

| position | share of pool | income/day | gas as % of income |
|---|---|---|---|
| $50 | 0.0150% | $0.0325 | **72.7%** |
| $500 | 0.1503% | $0.3248 | 7.3% |
| $5,000 | 1.5028% | $3.2479 | 0.7% |

**Same pool, same gas, and the answer inverts three orders of magnitude.** Quote the percentage beside
the income every time, and state the size it applies to — a "$0.02 gas fee is negligible" claim is a
claim about a position nobody named.

At $100 the ranking inverts too: one Avalanche pool earned $0.065/day against $0.0236 to touch it
(**36% of a day's income per rebalance**), while a Solana pool earned $0.146/day against $0.00025
(**0.17%**). **At small size the chain's gas regime outranks the venue's APR**, because the decision is
whether the position can be managed at all.
