# The bid-only hybrid shape

**What it is:** a liquidity position in a bin pool whose bins all sit **below** the active bin. Every bin
holds 100% of the quote token (USDC), and converts to the base token (AVAX) only as price falls into it.

**What it is for:** approximating a **ladder of limit buys** in a venue that has no limit orders.

**What it is not:** a yield position. **It earns nothing until price trades into it.**

---

## Why this document exists

The `defi` umbrella has cited `references/bid-only-hybrid-shape.md` since before the 2026-10-19 merge, and
the file did not exist. The doctrine was in use; the written form was not. This is the written form.

## The trap, stated once and plainly

| shape | where the bins sit | fee income while price stays up | exposure |
|---|---|---|---|
| **range / symmetric** | around spot | **yes** | already long |
| **bid-only ladder** | **below** spot | **zero** | not long until filled |

**These two cannot be combined.** "Wait for a better price and earn while you wait" describes a shape that
does not exist. A bid ladder is a queue of limit buys that happens to be wrapped in an LP.

**This is the honest cost of the better entry, and it is the number Jordan should see before choosing the
shape — not after.**

## The geometry (LFJ V2.2 / Trader Joe Liquidity Book)

```
price(bin i) = (1 + binStep/10_000)^(i - 2^23) × 10^(decX - decY)
bin(p)       = 2^23 + ln(p / 10^(decX-decY)) / ln(1 + binStep/10_000)
```

- **`2^23` is a fixed bin offset.** Dropping it produces a price off by orders of magnitude.
- **`10^(decX - decY)` handles the decimal gap** (WAVAX 18, USDC.e 6 → 10^12). Running it the wrong way
  (`decY - decX`) gives a price of `0.0000` and looks like a broken RPC rather than a broken formula.
- **Cross-check before trusting:** the AVAX/USDC pool `0x864d4e5e…16ea`, binStep 10, activeId 8363170
  → `$9.0769`, which matches spot. **A formula that has not been cross-checked against a second source
  is an assumption.**

## Choosing the tranches — the only four numbers that matter

1. **First level below spot** — how far the market must fall before the first bid fills (`-3%` typical).
2. **Step between tranches** — with `binStep 10` (0.10%/bin), a 3-bin tranche spans ~0.30% of price. A 4%
   step therefore leaves a real gap between tranches; that is intended, not a rounding error.
3. **Bins per tranche** — wider = more fee capture *when filled*, but more capital deployed per level.
4. **Total budget** — split evenly per BIN, not per tranche, so a wider tranche gets proportionally more.

**`tools/lp_ladder.py` computes all four and prints the fill schedule** — what you hold at −2%, −5%, −8%,
−15%, and the average entry at each.

## Exit behaviour, which the entry shape hides

Once a bin fills, the position is an ordinary LP:

- **Price recovers above a filled bin** → that bin converts back to USDC, having collected fees on the
  round trip. That is the shape working as intended.
- **Price falls through the lowest bin** → **there are no further bids below.** You hold the falling asset
  with nothing left to average with. **The ladder only protects you down to its last bin.**
- **Nothing is a stop.** There is no exit trigger in a bin pool. The exit is a withdrawal, and it is a
  decision, not an automatic.

## When to use it, and when not to

**Use it when** the thesis is "I want to own this below here, and I am content to earn nothing while I
wait." That is a real, disciplined position.

**Do not use it when** the actual goal is fee income. A ladder that never fills produces **zero** while a
range position on the same capital produces yield — **and the difference is measurable, so measure it.**

## Related

- `lp-rebalance-economics` — the rebalance gate and why cadence, not gas, was the failure.
- `pool-analytics` — the pool's fee tier and turnover, which set what a fill is worth.
- `tools/lp_ladder.py` — the planner · `tools/liquidation_model.py` — the perp counterpart.
