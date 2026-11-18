# Settlement scheme selection — match the scheme to the price, before blaming demand

An x402 challenge can be perfectly compliant, correctly signed, and still unsellable, because **the
scheme decides what each call costs the BUYER in chain fees.** A sub-cent price settled per-call is not a
bargain, it is a fee the buyer pays to lose money — and they will not call it a second time.

## Read the live scheme before reasoning about anything

The scheme is a field in the challenge, so measure it there. Do not read it off the source: a deployed
environment, an older handler, or a template can each differ from what the server emits.

```bash
curl -s https://<host>/<a paid route> | python3 -c \
  'import sys,json; d=json.load(sys.stdin); print({a["scheme"] for a in d["accepts"]}); print(list(d.get("extensions",{})))'
```

Two facts come back and both matter: the set of schemes actually offered, and whether the `extensions`
block carries anything. An empty `extensions` object advertises a bare seller.

## The four schemes, and the price band each one can carry

| scheme | what it settles | fits |
|---|---|---|
| **exact** | the advertised amount, one authorization per request | whole-cent-and-up prices; low call volume |
| **upto** | buyer authorizes a maximum, seller charges actual usage | metered work whose cost varies per request |
| **batch-settlement** | escrow deposit once + off-chain cumulative voucher per call, redeemed in batches (EVM and Solana) | **repeated sub-cent calls** — the only shape that amortises chain cost |
| **auth-capture** | authorise now, capture later | deferred or aggregated delivery |

**Rule: the price band picks the scheme, not the other way round.** If the catalogue advertises fractions of a
cent and the challenge offers `exact` only, the listing is economically impossible to buy and heavy inbound
traffic will still convert at zero. Fix the scheme before touching the price, the free tier, or the funnel.

## Why the arithmetic decides it

`exact` costs the buyer a chain transfer per request. A gas/authorization cost of any size divided by a price
of `$0.001` is a negative-margin purchase for every caller. The tell in the logs is not "nobody is
interested" — it is **a very large number of 402 challenges with almost no settles**, because the buyer read
the terms and correctly walked away. Do not report that as a demand finding until the scheme has been ruled
out.

## Migrating without breaking the routes that work

- **Decide per service, not per gateway.** Keep `exact` on the handful of routes priced at cents; move the
  $-mill routes (price feeds, gas, search) to `batch-settlement`.
- **A batch route needs a channel manager.** Registration, per-channel storage, and a claim/settle/refund
  cycle are part of the change — not a config flag. Price that work before promising the migration.
- **`upto` is a smaller change than batch** and covers variable-cost analysis endpoints; take it first when
  the goal is simply "stop under-charging variable work".
- **Display order is not payment order.** If you also reorder the accepted rails for a marketplace
  requirement, keep the scheme migration and the rail reordering as separate edits with separate proofs.

## Pitfalls

- **An empty `extensions` block is not neutral.** Receipts, discovery hints and signed offers hang off it; a
  seller advertising nothing there looks like a reference implementation rather than a product.
- **A directory or grader may score you on the endpoints you REGISTERED, not the ones you serve.** Switching
  scheme does not help while duplicated or retired routes remain listed in catalogues; clean the listings in
  the same pass or the score will not move.
- **Do not conclude "no demand" from a zero settle rate before you have checked the scheme and the
  advertised price together.** The two are one fact about whether the purchase is possible.
- **The standard's own docs repo accepts documentation PRs** (neutral content, no branded links). A protocol
  fix you already made elsewhere — canonical header name, address normalisation — is a legitimate docs
  contribution; a docs PR that advertises your gateway is not.
