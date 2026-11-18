# Venue endpoints, field maps, and funding normalisation

Live-public, keyless reads used by the venue selector. All three answered from a plain container with a
`User-Agent` header; none needs an API key. Verify the shape before trusting a field name — every one of
the mistakes listed at the bottom came from assuming a shape.

## Hyperliquid — POST only

```
POST https://api.hyperliquid.xyz/info
body: {"type": "metaAndAssetCtxs"}
```

**A GET returns HTTP 405.** The endpoint is POST-only; a 405 here is a wrong method, not a dead venue —
do not file it as an outage.

The response is a two-element array: `[meta, ctxs]`. `meta.universe[i].name` is the asset;
`ctxs[i]` is the same index — **join positionally, never by symbol lookup inside ctxs.**

| field | meaning |
|---|---|
| `markPx` | mark price |
| `dayNtlVlm` | 24h notional volume (USD) — the depth figure |
| `openInterest` | open interest in BASE UNITS — multiply by mark for USD |
| `funding` | funding rate **per hour** |
| `meta.universe[i].maxLeverage` | max leverage |

**Funding is hourly here.** Its cap is `0.00125%/hr`, which normalises to **exactly 3.000 bps/day**.
When six uncorrelated assets all print that figure, you are reading a parameter, not a market signal.

## Orderly — GET, and enumerate without a body

```
GET https://api.orderly.org/v1/public/info                    # all symbols, with per-market config
GET https://api.orderly.org/v1/public/futures/<SYM>          # mark, index, OI, 24h volume
GET https://api.orderly.org/v1/public/funding_rate/<SYM>     # est + last funding, next window
```

Symbol form is `PERP_<ASSET>_USDC`. **`POST /v1/public/info` with a `{"symbols": [...]}` body returns
HTTP 400** — the enumeration endpoint is a bodyless GET; filter the returned rows yourself.

| field | meaning |
|---|---|
| `mark_price` | mark price |
| `24h_amount` | 24h notional volume (USD) |
| `open_interest` × `mark_price` | OI in USD (the raw field is in base units) |
| `est_funding_rate` | funding **per funding window** (`funding_period` = 8h) |
| `base_mmr` / `base_imr` | maintenance / initial margin ratio; max lev = 1/IMR |
| `min_notional` | entry floor in USD |

## GMX V2 — one API per chain

```
GET https://avalanche-api.gmxinfra.io/markets
GET https://arbitrum-api.gmxinfra.io/markets
```

**Avalanche and Arbitrum are separate hosts with separate market sets** — do not assume parity.

- Market names are **`SYM/USD [COLLAT-COLLAT]`** — e.g. `AVAX/USD [AVAX-AVAX]`. **Parse on the slash.**
- **The markets endpoint publishes no volume and no funding.** So a GMX quote is `listed` and leverage
  only; depth must come from elsewhere, and a selector must show it as depth-unmeasured rather than
  ranking it.
- A response **without a `markets` array is an outage**, not an empty venue — say which.

## Funding normalisation — the only comparable unit

Venues quote on different clocks. Convert everything to **bps/day** before any comparison or ranking:

| venue | quoted | multiply by | example |
|---|---|---|---|
| Orderly | per 8h | `× 3 × 10000` | `9.894e-05` → **+2.97 bps/day** |
| Hyperliquid | per 1h | `× 24 × 10000` | `0.00125%` → **+3.000 bps/day** |
| GMX V2 | not published | — | leave `None`, never `0` |

**Sign is the trade.** Positive funding = longs pay shorts, so a short *collects* it. Reporting "funding
cost" without the sign inverts the economics of the position being described.

Same hour, same asset, both directions visible only after normalisation:

| asset | Orderly bps/day | Hyperliquid bps/day |
|---|---|---|
| AVAX | **+2.966** | **−0.534** |
| BTC | +0.357 | +3.000 (cap) |
| LINK | −0.025 | +3.000 (cap) |

AVAX shows opposite signs across two venues a few bps apart — that spread exists as an arbitrage, and it
is invisible while one side is quoted per 8h and the other per hour.

## Listing coverage is the entrance test

Measured against a book of COQ, LINK, TAO, ONDO:

| venue | underlyings listed | book coverage |
|---|---|---|
| Orderly | ~146 symbols | 3 of 4 (no COQ) |
| Hyperliquid | 234 perps | 3 of 4 (no COQ) |
| GMX V2 (Avalanche) | 12 | **0 of 4** |

**A venue can advertise 131 markets and hold none of your names.** Count the intersection before anything
else, and expect one asset — often the smallest or newest — to have no perp anywhere. That is a permanent
"spot only" finding, not a gap to keep re-checking.

## Failure modes that produce a confident wrong answer

1. **Wrong method reported as an outage.** GET against Hyperliquid's POST-only endpoint = 405. A 405 is
   your request, not their service status.
2. **A body on a bodyless endpoint.** Orderly's enumeration GET returns 400 if you POST a symbol filter.
3. **Parsing display output.** Printing `name.replace("/", "-")` for readability and then splitting the
   parser on `-` matches nothing and reports a live venue as `NOT_LISTED`. **Print `repr()` of a raw record
   when building a parser; never parse the pretty version.**
4. **Outage read as absence.** No `markets` key, empty rows, or a transport error must come back as
   `UNMEASURED` with the reason — never as `NOT_LISTED`, which silently removes a venue from the
   comparison and looks like a fact.
5. **Ranking off one venue.** With fewer than two live quotes there is no ranking to report; "best of one"
   manufactures confidence. Return no pick and say why.
