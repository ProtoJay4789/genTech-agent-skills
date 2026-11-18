# Price Positioning — Surveying the Market Before Setting a Price

**Purpose:** price a paid endpoint against what buyers actually pay, not against what it cost us to
build or what felt fair. The technique is to read a competitor's machine-readable catalogue and compare
the *same job* head to head.

---

## 1. Find a machine-readable price catalogue

Large x402/AI-API marketplaces publish their whole menu as JSON. That is a free, complete, current
market survey — far better than guessing from blog posts.

```bash
curl -s -m 30 "https://<marketplace>/api/pricing" | jq '.endpoints | length'
curl -s -m 30 "https://<marketplace>/api/pricing" \
  | jq -r '.endpoints[] | "\(.price)\t\(.path)\t\(.name)"'
```

Also check `/.well-known/x402`, `/openapi.json`, and `llms.txt` — any seller advertising to agents
usually publishes prices somewhere machine-readable, because agents need them before paying.

**Record the source and the fetch date beside any figure you quote from it.** A price list is a
snapshot, and competitive pricing moves.

---

## 2. Compare the SAME JOB, not the same category

Matching on category produces false confidence. Match on the job the buyer is hiring the endpoint to do:

| job | their endpoint | their price | our endpoint | our price |
|---|---|---|---|---|
| gas estimate | `/api/gas-estimate` | $0.001 | `/v1/gas` | ? |
| token price | `/api/crypto-price` | $0.001 | `/v1/market/price` | ? |
| DEX pool data | `/api/dex-pool` | $0.002 | `/v1/defi/lp` | ? |
| wallet balances | `/api/wallet-balance` | $0.002 | `/v1/wallet/portfolio` | ? |

Pull our advertised prices from our own public surface (`llms.txt`, the bazaar manifest) so the
comparison uses what we actually charge, not what a note claims we charge.

**A ratio above ~2× on a commodity job is a finding.** A price-shopping agent selects on price; at 5–10×
we are not in the consideration set at all, however good the result is.

---

## 3. The market is bimodal — check which half you are in

Measured on a 625-endpoint catalogue:

```
median  $0.003
  ~200  ≤ $0.001          commodity floor
  ~139  $0.001–0.003
  ~163  $0.003–0.01
   ~75  $0.01–0.05
   ~48  > $0.05           ← where the margin is
```

**Everything in the expensive tail is a REPORT — multi-source synthesis with a verdict. Nothing in it
is a lookup.** Observed shapes at the top of the market:

```
$3.30  resolve + EXECUTE a tool
$2.00  ticker pack — dossier + flow + institutional
$1.10  deep research report (MAX)
$0.85  due-diligence dossier
$0.85  domain security audit (PRO)
$0.60  SEC filing report · FDA recall report · 13F fund report
```

The buyer is not paying for data. They are paying because **they asked one question and got one
answer**, with sources, instead of stitching five lookups themselves.

---

## 4. The pricing rule

> **Commodity → the floor. Synthesis or verdict → premium.**

- **Commodity** = the same job anyone can do, where the buyer compares on price: a price quote, a gas
  quote, balances, a list, a registry lookup. **Price at or near the market floor.** Charging above it
  earns nothing extra because nobody reaches checkout.
- **Synthesis** = multiple sources combined into one answer, a report, a document. **Price against the
  report tier**, not against per-lookup prices. Underselling these is the expensive mistake.
- **Verdict** = a single differentiated judgement nobody else emits (classify this as safe/risky, does
  this change break anything). Sits between: above commodity, below full report.
- **Infrastructure** (routing, provider lists) — price near cost. It is a means, not the product.

**⚠️ Before building a new premium product, check whether you already have one priced as a lookup.**
An endpoint whose contract is "input task → return analysis/text" IS the report shape the top of the
market sells, whatever it is currently named or priced. Look for it first: raising one existing price
is free, and building a new product is not.

---

## 5. Applying a price change — the file that matters is the live one

**A price list usually exists in three places, and only one of them is served:**

| copy | role |
|---|---|
| the gateway source / vault copy | the repo of record — editing it changes nothing |
| a host path the gateway reads at import (e.g. `/var/www/<domain>/.well-known/x402-bazaar`) | ⚠️ **the live one** |
| what the public URL returns | the only proof |

**Procedure:**

1. Back up the copy you are about to edit (`.bak-reprice-<stamp>`).
2. Apply the change to the canonical/source copy and record the old→new table.
3. Copy that file to the host path the gateway actually reads.
4. **Restart the gateway** — the manifest is read at import, so a file swap alone does not reload it.
5. **Verify from outside** and diff against the intended table:

```bash
curl -s https://<domain>/.well-known/x402-bazaar \
  | jq -r '.services | to_entries[] | "\(.value.priceUsd)\t\(.key)"'
```

**⚠️ Verify the live surface after every pricing edit.** If it still shows the old numbers, the edit
landed in a copy nobody serves — and a report that says "repriced" while the buyer is charged the old
amount is worse than no report. State plainly which copy is changed and which is not.

---

## 6. What a price change does and does not buy

**A price cut removes a reason to be skipped. It does not create demand.** If callers were knocking and
none loaded a payment at the old price, price was at most one factor — the honest framing is
*"this removes the reason a price-shopping bot skips us; it does not create a buyer."*

**Make the next step measurable.** The cheap experiment a repricing enables: do the commodity routes
now get called at all? That is visible in the traffic log within days, costs nothing to run, and is a
real answer either way.

**Never present a repricing and a demand strategy as the same deliverable.** The user asked for both;
saying "repriced" and stopping leaves the actual question unanswered.
