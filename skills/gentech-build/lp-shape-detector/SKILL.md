---
name: lp-shape-detector
description: "Use when classifying LP shape from bin liquidity."
tags: [lp, shape, detector, defi, lfj, meteora, avalanche, solana, genTech-original]
trigger: "When analyzing LP positions, detecting strategy shapes, or comparing LP strategies across pools."
related_skills:
  - defi-lp-consolidated  # uses shape for efficiency calc
  - dca-rebalance-handler  # shape affects DCA strategy
version: 1.1.0
author: Gentech Labs
---

# LP Shape Detector — GenTech Original

**Detect LP strategy shapes by analyzing on-chain bin distribution.**

Works with any bin-based concentrated liquidity AMM:
- **LFJ V2.1** (Trader Joe) on Avalanche — reads `curveData.bins` from `defi-data.json`
- **Meteora DLMM** on Solana — same Spot/Curve/Bid-Ask shapes, discrete price bins
- Chain-agnostic — any AMM with discrete bin distribution

## Supported Shapes

| Shape | Pattern | Best For |
|-------|---------|----------|
| **Curve** | Bell-curve, peak at center | Range-bound markets |
| **Bid-Ask** | Liquidity at edges | Volatile/trending markets |
| **Spot** | Single bin concentration | Precision plays |
| **Asymmetric** | Skewed distribution | Directional bets |

## Platform Compatibility

| Platform | Chain | AMM Type | Shape Support | Where the bins come from |
|----------|-------|----------|---------------|-------------|
| **LFJ V2.1/V2.2** (Trader Joe) | Avalanche | Liquidity Book (bins) | Spot, Curve, Bid-Ask | `defi-data.json` → `curveData.bins`, or `balanceOf(address,uint256)` `0x00fdd58e` per bin id |
| **Meteora DLMM** (classic) | Solana | DLMM (bins) | Spot, Curve, Bid-Ask | `LbPair` + bin arrays via RPC — no reader implemented |
| **Meteora DLMM Pro** | Solana | ticks + `liquidity_net` | Spot, Curve, Bid-Ask built from up to 45 ranges | tick arrays + bitmap, IDL exported by `@meteora-ag/dlmm-pro-sdk` |

**A column saying "via RPC" is not a reader.** Verify the script exists before promising a shape — see *Preflight* below. Every row above needs a `bins-for-<chain>` adapter; none of them is a classification problem.

**Key insight:** Meteora DLMM uses the identical Spot/Curve/Bid-Ask liquidity shape system as Trader Joe's Liquidity Book. Both organize liquidity into discrete price bins with configurable distribution. The LP Shape Detector's classification algorithm (center concentration, edge concentration, peak position, symmetry, skew) works unchanged on Meteora bin data.

**Why that is true — the arithmetic, from both projects' own docs:**

```
LFJ Liquidity Book :  price(bin) = (1 + bin_step/10000) ** (bin_id - SHIFT)   # SHIFT = 2**23
Meteora DLMM       :  P_i       = (1 + bin_step/10_000) ** i
Meteora DLMM Pro   :  every tick is a 0.01% step, spacing 1..256
```

Same compounding per step. Only the offset, the account layout and the language differ — so the classifier never needs to know which chain it is reading.

**Meteora discovery context:** Jordan was comparing TAO/USDC yield farming opportunities on Solana. Meteora's DLMM surfaced as the equivalent to Trader Joe — same shape system, same strategy playbook. All existing shape analysis tools (LP Shape Detector, efficiency calculator, regime classifier) apply to Meteora positions without modification.

## Preflight — a documented command is a claim, not an installation

```bash
# run this BEFORE reporting any shape, on any venue
ls -l "${PROFILE_DIR}/scripts/lp-shape-detector.py" || echo "NO DETECTOR SCRIPT — shape analysis is NOT available"
```

**A skill that documents how to invoke a tool is not evidence the tool exists.** Measured: this skill's Usage block
named `lp-shape-detector.py`, and a full search of the data root found no such file on any seat — so "shape
intelligence" was a documented capability with no executable behind it, while the algorithm itself was fully
specified in prose. The prose is the asset; the script is a separate artifact that can go missing.

- **Search for the filename across the whole data root, not just the profile's `scripts/`.** A detector that moved
  looks identical to one that was never deployed until you look everywhere.
- **Report the split honestly:** "the classification rules exist and are complete; the reader and the CLI do not"
  is a useful finding. "Shape analysis works" is not, and someone will plan around it.
- **A shape claim with no bins behind it is the same defect as a green check on zero files** — see
  `falsifiable-tests` for the state-the-denominator rule.

## Portability — the SHAPES travel, the DATA MODELS do not

This is the design rule that keeps the detector from being rewritten per chain.

**One classifier, thin per-venue adapters.** Every adapter returns the same three fields and nothing else:

```python
# the ONLY contract between a venue and the classifier
[{"bin_id": int, "price": float, "liquidity": float}, ...]
```

Each venue does its own work below that line:

| venue | read | notes |
|---|---|---|
| LFJ Liquidity Book (EVM) | `balanceOf(address, binId)` `0x00fdd58e`, batch ~25 `eth_call`s per JSON-RPC array | single-arg `balanceOf` reverts by design; it is an LBToken, not ERC-20 |
| Meteora DLMM classic | decode `LbPair` + bin arrays | same program family as the `lb_clmm` design |
| Meteora DLMM Pro | tick arrays, `liquidity_net`, bitmap extension | read the IDL the SDK exports; do not hardcode offsets |

- **Never let the classification thresholds know a chain name.** The moment `if chain == "solana"` appears in the
  metrics, the detector is two tools wearing one name.
- **Absorb the offset in the adapter, not the classifier.** LFJ bins carry a `SHIFT = 2**23` offset; Meteora ids are
  raw ticks. Normalise to a signed index before metrics, or `peak position` and `skew` mean different things per venue.
- **Read a beta program's IDL and say which version you built against.** A 0.1.x SDK that ships releases every few
  days will move its layout; a hardcoded offset is a silently wrong shape, not an error.
- **Multi-range positions change the UNIT of classification.** Where one NFT holds up to 45 ranges, classify each
  range and report the set — classifying the pool as a single distribution will mislabel a deliberately split book.
- **Reconcile the read against a pool-level total** (`getReserves()`, pool liquidity) before classifying. A partial
  bin read produces a perfectly confident wrong shape.
- **Build the adapter for the venue holding the capital, not the newest venue.** A brand-new program proves the
  pattern and pays nothing; the live position is what makes shape analysis worth having.

## Bin ORDER is part of the contract — index 0 is the CHEAPEST price

A distribution metric is only meaningful against a known orientation. On every bin venue measured so far the id
increases with price (`price_i ∝ (1 + step) ** i`), so **index 0 / the lowest bin id is the LOWEST price**. Say
this in the adapter and assert it once; everything downstream assumes it.

Measured: an allocator that spread capital with an ascending ramp — weight rising with index — labelled the result
`bid_ask_low` and put **most of the liquidity at the TOP of the band**, the exact opposite of a wing that earns a
dip. It looked deliberate, because a named shape with a smooth distribution always does. One assertion
(`the down-tilt weights the low half`) caught it; reading the code did not.

- **Test orientation explicitly: `sum(low_half) > sum(high_half)` for a down-tilt, and the mirror for an up-tilt.**
  A shape assertion that only checks the name, or only checks that the weights sum to the capital, passes on an
  inverted book.
- **Name the orientation in the adapter's return comment** (`bin_id` ascending with price) so a future chain that
  indexes the other way is a visible mismatch rather than a silently mirrored shape. If any venue does invert,
  normalise to a signed index in the adapter — never in the classifier.
- **A mirrored distribution still produces a plausible confidence score.** Nothing about symmetry, peak position or
  center concentration can tell you the book is upside-down, because a mirror preserves all of them. Orientation is
  a separate assertion, not a metric.

## Shape ANALYSIS needs a distribution — a range book has none

The classifier reads how liquidity is spread across discrete price levels. **A venue only qualifies if it stores
liquidity per bin/tick.** A v3/Algebra-style book stores one liquidity value per position rectangle
`[tickLower, tickUpper]`, which is a range, not a distribution — there is nothing to classify, and running the
metrics on it produces a confident label for a question nobody asked.

| venue family | stores | shape analysis | shape construction |
|---|---|---|---|
| Liquidity Book / DLMM (bins or `liquidity_net` per tick) | liquidity **per price level** | ✅ | ✅ bins |
| Algebra / v3-style concentrated liquidity | **one liquidity per range** | ❌ nothing to classify | ✅ ranges, one per wing |

- **Gate on the storage model, not on the chain or the brand.** Two venues on the same chain land on opposite
  sides of this table; two venues on different chains land on the same side.
- **The strategy still travels even when the analyser cannot.** A curve-that-bends-into-a-bid-ask is buildable on a
  range venue as **several positions** — a tight low range (the dip wing), a wide middle, a tight high range. That
  is a range planner, a different emitter, not a classifier change.
- **Report the split before someone plans around it:** "analysis applies to bin venues; venue X gets the planner
  but not the classifier" is the sentence that stops a wasted build.

## Usage

```bash
python3 ${PROFILE_DIR}/scripts/lp-shape-detector.py
python3 ${PROFILE_DIR}/scripts/lp-shape-detector.py --json
```

## Detection Algorithm

1. **Read bin data** from `curveData.bins` in defi-data.json
2. **Calculate metrics:**
   - Center concentration: liquidity in middle 30% of range
   - Edge concentration: liquidity in outer 25%
   - Peak position: where max liquidity sits
   - Symmetry: left vs right balance
   - Skew: directional bias
3. **Score each shape** based on metrics
4. **Classify** with confidence percentage

## Example Output

```
📈 LP Shape Analysis

Detected Shape: Curve (center-weighted)
Confidence: 90%

Distribution Metrics:
  Bins: 37
  Center concentration: 55.2%
  Edge concentration: 25.0%
  Peak position: 0.556 (near center)
  Symmetry: 0.891

Strategy Implications:
  • Earns most when price stays near center
  • Best for range-bound markets
  • Consider switching to Bid-Ask if breakout expected
```

## Integration with Monitor

The shape detector can be called before efficiency calculations:

```python
import subprocess
result = subprocess.run(
    ["python3", "${PROFILE_DIR}/scripts/lp-shape-detector.py", "--json"],
    capture_output=True, text=True
)
# Parse JSON output for shape classification
```

## Cloudflare Worker Deployment (Jul 2, 2026)

The shape detection algorithm was ported from Python to JavaScript and deployed as an x402-monetized Cloudflare Worker:

- **URL**: https://gentech-lp-analytics.jordanjones0902.workers.dev
- **Source**: `lp-analytics/worker.js` in vault
- **Porting Notes**:
  - No external dependencies (pure JS, no numpy/pandas needed)
  - Returns 402 payment response for unpaid requests (x402 protocol)
  - Supports POST with JSON body (`{ bins: number[], volatility?: number }`)
  - Classification order adjusted: CenterConcentration checked before EdgeConcentration (ensures proper bell curves classify as Curve, not Bid-Ask)
- **Three paid endpoints**: `/api/lp/shape` ($0.025), `/api/lp/efficiency` ($0.01), `/api/lp/strategies` ($0.005)
  - `/api/lp/shape` — POST. Classifies shape from bin distribution, returns shape name + confidence + metrics
  - `/api/lp/efficiency` — POST. Takes bins + volatility (0-1, default 0.5). Returns shape-fit efficiency score (0-100) + marketFit label (High/Medium/Low)
  - `/api/lp/strategies` — GET. Returns strategy catalog (Curve, Bid-Ask, Spot, Asymmetric) with descriptions and best-fit regimes
- **Free endpoints**: `/health`, `/pricing`

### JS Thresholds (identical to Python)

```javascript
Spot:       maxBinShare > 0.6
Curve:      centerConcentration > 0.4    // checked BEFORE edge
Bid-Ask:    edgeConcentration > 0.35
Asymmetric: |skew| > 0.3
```

## For Agent Kit

This is a GenTech Labs original. When deploying agents that manage LP positions:

1. **Always detect shape first** — don't assume Bid-Ask or Curve
2. **Match shape to market** — Curve for stable, Bid-Ask for volatile
3. **Monitor shape drift** — position shape may change if bins are added/removed
4. **Use confidence score** — low confidence = need more bins or manual check

## Future: Regime-Based Shape Switching (Jun 2026)

Jordan's vision: don't stay in one shape forever. Detect the market regime and switch shape accordingly:

| Regime | Signal | Optimal Shape |
|--------|--------|---------------|
| **Volatility** | High ATR, price bouncing between bins | Bid-Ask |
| **Consolidation** | Low ATR, tight range, low volume | Curve |
| **Accumulation** | Price building a base, buyers stepping in | Spot |
| **Payout** | Price pushing into resistance, selling pressure | Widen Up |

The regime classifier would read price action history + volume + edge proximity and recommend the optimal shape. User approves before switching.

The detector already provides the shape classification. **The regime half is now partly built:**

- `Treasury/shape-intelligence.md` holds the operator standard as a measured matrix — regime → (bins, shape,
  ratio), with overrides in a fixed order (**operator pin → carry-out rate → the matrix**) and semantics for what
  each ratio MEANS, so the tilt is not a free knob.
- `scripts/lp-shape-plan.py` is the executor: it turns that row into a position set (bins + per-bin liquidity) and
  returns a mandatory cost line — fee income vs expected carry-out cost — with a verdict in
  `RUN / THIN / DO_NOT`. It is a pure function (no network, no wallet, no model), so it is testable; an adapter
  supplies the pool read and a caller signs.
- **A plan without the carry-out line is a brochure.** The matrix's own worst measurement is repair cost dwarfing
  fee income on a small book, so the planner must be able to answer `DO_NOT` — and must report `THIN` (never a
  pass) when the fee input is unknown.
- **Widen, do not flip.** A directional view changes the wing and the ratio; it does not reverse the book. That is
  the operator doctrine, and it is why `apply_direction` keeps the band and moves the tilt.
- **The capital input is a MEASURED value with a vintage, so the planner must REFUSE a stale one.** Take
  `capital_as_of` alongside the capital, apply a max age (days, not weeks), and on expiry return an explicit
  `REFUSED` with an EMPTY position set and the age in the reason — never a warning field inside an otherwise
  complete plan. A plan on stale capital is the most expensive shape of wrong: it is a well-formed instruction to
  deploy money that is not there, and the arithmetic in it is perfect. An undated input is `UNVERIFIED`, not fresh.

The detector is chain-agnostic — works with any LFJ V2.1 pool (Avalanche) or Meteora DLMM pool (Solana) using identical classification logic.
