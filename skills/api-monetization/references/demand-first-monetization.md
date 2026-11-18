# Demand-First Monetization — Don't Build Payment Plumbing Before Proven Usage

> Jordan's correction, Aug 24 2026: "If we do the subscription, the business has to
> be taken off for me to think it's worth the investment." When asked to build
> Stripe/card checkout for paid subscription tiers, the honest answer was **not yet** —
> build infrastructure only when there is proven paying demand.

## The principle
**Build the revenue loop BEFORE the revenue plumbing.** The gate for "is the
subscription worth building" is *demand* (first real paying customer / repeated
calls), NOT infrastructure readiness. Adding Stripe webhooks, card checkout, billing
on zero usage = investing in the plumbing before the water arrives.

- **Free tier + x402 = the on-ramp** (zero-cost, already works). Keep it.
- **Paid subscription/Stripe tier = hold until there's proof of paying usage.**
- Reorient from "set up payments" to "find the first paying customer" — because that
  gate makes the subscription worth building at all.

## Why our current API portfolio under-earns (the honest diagnosis)
We have 10+ live services (token security, wallet analysis, market intel, DeFi LP
analytics, NFT search…) priced $0.01–0.10/call on 6 chains, listed on multiple
marketplaces — **and make zero revenue.** Listing ≠ being bought.

The proven earners on x402 are **high-frequency utilities agents call constantly**,
not niche analytics a crypto agent pings occasionally:

| Service type | Why it earns | Real example |
|---|---|---|
| **LLM inference resale** | Agents call 1000s×/day | blockrun ~$820/day (~$25K/mo), cost+5% |
| **Market/price data** | Every trading agent needs live prices | Bloomberg, CoinGecko on Agent.market |
| **Web search/scraping** | Agents research constantly | Linkup, Apify |
| **Media/thumbnail gen** | Built-in Coinbase demo | x402 Thumbnail Generator |

**Reposition at least one service to a high-frequency category agents actually buy
in volume (inference resale, live market data) rather than only $0.02 analytics.**

## The demand-discovery lever (first paying customer)
1. **Get discovered where agents actually browse** — Coinbase Agent.market
   (69K active agents, $50M cumulative volume, where Agentic Wallets plug in
   by default), x402scan manual registration. We're validator-compliant.
2. **Drive traffic to listings** — fresh registrations climb "Most Used" rankings
   once they get request volume; that surfaces us to agents.
3. **Real settlements land first** — the first on-chain paid call is the proof
   that justifies building paid-plan plumbing on top.

## Application to the Human Pricing gateway (#56)
- Free tier (50 calls/mo) + x402 are LIVE and earning-capable — good on-ramp.
- Paid $69/$269 plans need Jordan's Stripe account + webhook.
- **Decision: defer Stripe build until there's proven paying usage.** When a real
  customer starts paying, Stripe is a short add-on, not a speculative build.

## x402scan revenue-listing-map correction
The earlier `revenue-listing-map.md` said x402scan "auto-indexes from /openapi.json."
That is FALSE as the listing path — settlement/openapi crawling does NOT list us
(0.015 USDC settled Aug 19, stayed 0). The working path is the **manual "Add API"
form** (see `platform-registration` skill → `references/x402scan-manual-registration.md`).

---

# DIAGNOSING ZERO CONVERSION — segment the traffic by what each caller SAYS it is

Before concluding "our price is wrong", measure who is knocking. The gateway already logs a
`User-Agent` per request, and on x402 a large share of callers describe themselves in it — including,
literally, that they do not pay.

## The classification (do this first, it costs one script)

Group every request in the traffic log by self-declaration:

| caller kind | how you spot it | can it pay? |
|---|---|---|
| **monitor / uptime / liveness / healthcheck** | `uptime-probe`, `liveness check`, `monitor`, `beat`, `watch` | **no — by design** |
| **directory / crawler / list-observer** | `crawler`, `list-monitor`, `router`, `directory`, `catalog`, `observer`, `archive` | **no — indexing, not buying** |
| **conformance tester** | `Conformance`, `validator`, `checker`, `spec` | **no — verifies the spec** |
| **raw HTTP client, no identity** | `python-requests`, `axios`, `node`, `curl`, `okhttp` | unknown |
| **other** | anything left | possibly |

**Measured on one live catalogue:** **72% of 7,612 requests came from self-declared non-payers** —
uptime probes ~3.2k, directories/crawlers ~2.3k, conformance testers ~0.4k. Two of them say it in the
header itself: `... (unpaid liveness check, never settles)` and `... (independent endpoint monitor;
never pays)`. A single uptime prober produced 703 requests, 703 × 402, and zero served calls.

## The numbers that decide the verdict

```
quotes (402) for the period     : 50,185
served on PAID routes           :     15   ← the only figure that is a sale or a keyed call
served on public/free routes    : 30,124   ← index, manifest, docs, MCP handshake: NOT sales
```

- **A 402 is a QUOTE, not a decline.** Counting knocks as demand makes a crawler look like a market.
  Reporting "50,000 requests" as traction is the flattering number that hides the gap for weeks.
- **Check WHO the served-on-paid-route traffic came from.** Measured: all 585 of the "deep route" 2xx
  came from exactly two agents — a list-monitor and a conformance tester. Both are infrastructure.
- **The verdict when 0% of quotes convert on healthy backends: there are no buyers in the funnel.**
  Not a broken price, not a broken route — an empty room. Every backend reporting `ok` is evidence
  *against* an outage explanation.

## Rule pricing OUT with evidence, before touching a price

- **If the CHEAPEST route converts at zero, price is not the gate.** Measured: a market route priced
  **5× under** a household-name competitor ($0.001 vs $0.005) took ~800 quotes and sold zero. A price
  war cannot fix an empty room, and discounting to impress crawlers only destroys margin.
- **Do not buy more listings.** If directories are already crawling you, more listings reaches the
  same non-buying layer. Distribution to the discovery layer is not distribution to buyers.
- **State what would falsify the price theory** and check it: does any route, at any price, convert at
  all? If nothing converts anywhere, the variable is not price.

## Where to look instead (the three questions that actually move it)

1. **Where do agents WITH BUDGETS live?** That is a sales problem, not an SEO one. A **facilitator**
   appearing in your own traffic is a lead — facilitators settle for others and therefore see which
   agents actually pay. Ask them what buyers are requesting, not what you should list.
2. **What do they buy that you already have?** A buyer with a budget buys **a decision it cannot make
   itself** — not a feed it can get free from a public API. The routes priced like *judgement* (verdicts,
   risk, blast-radius) are the right shape; raw lookups are the commodity floor.
3. **Is the free → paid on-ramp designed at all?** Tens of thousands of free serves is enormous
   distribution converting to nothing. Either the free tier is too generous to ever need the paid one, or
   the upgrade moment was never built. Audit that before adding another route.
