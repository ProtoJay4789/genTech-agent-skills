# Payment schemes and price points — the economics gate

A gateway can be perfectly compliant with `exact` and still be unsellable. **The scheme has to match the
price**, and the mismatch is invisible because every surface looks correct: valid challenge, honest price,
working paywall, nobody buying.

## The four schemes (x402 v2)

| scheme | what the buyer authorises | fits |
|---|---|---|
| **exact** | precisely the advertised amount | whole-cent-and-up calls, low frequency |
| **upto** | a maximum; the seller charges actual usage | metered work whose cost varies (analysis depth, token count) |
| **batch-settlement** | deposits into escrow once, then signs a **cumulative off-chain voucher per request**; seller verifies off-chain and redeems many channels in one transaction | high-frequency calls where settlement cost would dominate |
| **auth-capture** | authorise now, capture later | delayed or contingent delivery |

`batch-settlement` is available on EVM (stateless unidirectional payment channels) and Solana. Its documented
purpose is the sentence to test a catalogue against: *"repeated paid API calls, usage-metered endpoints and
other workloads where many small payments would be too expensive or slow to settle one-by-one."*

## The gate: a price below the settlement cost is a scheme defect, not a demand problem

**One `exact` settlement = one onchain transfer = gas paid per call.** If an endpoint's price is a tenth of a
cent and the transfer costs more than the sale, no rational buyer completes it — and the resulting silence
looks exactly like "no demand", which is why this defect survives so long.

- **Compute the ratio, don't estimate it:** `price_usd` against the gas cost of a transfer on the cheapest
  accepted rail. Where settlement cost is a material fraction of the price, the route belongs on
  `batch-settlement`.
- **Segment by price, not by service.** A catalogue can legitimately mix: `exact` for the $0.05 calls,
  `batch-settlement` for the sub-cent ones, `upto` where cost varies per call.
- **Check the ADVERTISED scheme, not the documented one.** Read `accepts[].scheme` off a live 402 — a gateway
  can implement several schemes in code while publishing only one.
- **An empty `extensions: {}` is a maturity statement too.** Extensions are the composable layer (discovery,
  receipts, signed offers, gas sponsoring); advertising none is legitimate, but know the block exists and is
  being left empty on purpose.

## Diagnosing "the price is fine and nobody pays"

In order, cheapest first:

1. **Is the scheme right for the price?** A sub-cent price on `exact` is the first suspect, not the last.
2. **Does a stranger's payment actually settle?** One settled call from an unknown wallet is the only proof the
   paywall is complete. A paid-route `200` from a free-tier key or your own probe is not a sale.
3. **Is the service discoverable at all?** Check the catalogues the target agents read, not only your own
   manifest — a seller nobody indexes has no price problem.
4. **Would the buyer's first call even land?** A route that 404s for a literal template, or an uptime a grader
   measures as half, kills the attempt before price is considered.

## Verify a scheme is really advertised

```bash
curl -s <paid-route> | python3 -c "import json,sys; d=json.load(sys.stdin); print({a['scheme'] for a in d['accepts']}); print(list(d.get('extensions',{}).keys()))"
```

Expect the set you believe you support. A single `{'exact'}` from a gateway that claims batch support means the
DEPLOY did not take — that is a deploy check, not an economics one.

## Pitfalls

- **Reporting "no demand" from a scheme mismatch.** The buyer behaved correctly; the offer was uneconomic. Say
  which one you measured.
- **Selling a sub-cent price with a per-call onchain transfer and calling the silence a marketing problem.**
  Fix the settlement path before spending on distribution.
- **Treating `accepts[0]` as cosmetic.** Client libraries that read the first entry pay on that rail;
  presentation order and payment precedence are different contracts.
- **Announcing a scheme from documentation instead of from the live challenge.** Read the 402.
