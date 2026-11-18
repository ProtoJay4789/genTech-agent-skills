# Building or rebuilding an x402 gateway as a Cloudflare Worker

Use when an edge gateway must be created, revived, or repaired. An edge estate exists to
serve when the VPS does not — so its routes must be **edge-native and keyless**, and anything
needing the Docker backends is marked unservable *with its reason* rather than proxied into a
dependency that shares the VPS's fate.

## STEP 1 — pick a facilitator that settles your networks (the fatal trap)

**A uniform 500 on every PAID route while every FREE route answers 200 is one shared
initialisation failure, and the usual cause is an empty intersection between the networks you
advertise and the networks your facilitator settles.** The x402 middleware initialises by
fetching facilitator support; an empty intersection makes `initialize()` throw, and a default
error handler turns that into a bare 500 with no explanation.

```bash
# read the facilitator's own list, then intersect against what YOU advertise
curl -s https://<facilitator>/supported | python3 -c "import sys,json;print(sorted({k['network'] for k in json.load(sys.stdin)['kinds']}))"
```

| Facilitator | Networks | Auth |
|---|---|---|
| **`facilitator.payai.network`** | broadest — avalanche, base, polygon, xlayer, arbitrum, sei, skale-base, eip155:56, plus testnets | **keyless** |
| `facilitator.goplausible.xyz` | base, solana, algorand (mainnet + testnet) | keyless |
| `facilitator.naven.network` | Robinhood chain (4663), 8453, 196, 2368 | keyless |
| `x402.org/facilitator` | **testnets only — never wire a mainnet rail to it** | keyless |
| `api.cdp.coinbase.com/platform/v2/x402` | base, polygon, arbitrum, world, solana | **needs auth; 401 on Basic/Bearer/X-API-Key for a plain-string secret** |

**Prefer a keyless facilitator — then there is no credential SHAPE to get wrong.**

- `POST /verify {}` is a cheap schema probe: a live facilitator answers
  `400 {"isValid":false,"invalidReason":"invalid_payment_requirements"}`.
- `/verify` and `/settle` take `{x402Version, paymentPayload, paymentRequirements}`.
- **Re-measure `/supported` before trusting any table, including this one.** The network list is
  the whole failure mode, and it changes without notice.
- **State the intersection explicitly** in the reply: `we advertise [X] · facilitator has [Y] ·
  intersection [X∩Y]`. "Non-empty and complete" is the pass condition.

## STEP 2 — write the 402 yourself; do not re-add middleware that can fail at init

~100 readable lines: build `paymentRequirements`, emit **402 + `PAYMENT-REQUIRED`** (base64 JSON,
`x402Version:2`, `resource{…}`, `accepts[]{scheme,network,asset,payTo,maxAmountRequired,…}`), then
on `PAYMENT-SIGNATURE` (or legacy `X-Payment`) call `/verify` → `/settle` → serve.

- **Emit `PAYMENT-RESPONSE` on the settlement-FAILURE path too** — the spec owes a receipt
  "whether successful or failed".
- **Never let an exception produce a bare 500.** Catch at the top and return a JSON body naming
  what broke; the 500-with-no-explanation is what made this estate undiagnosable from outside.

## STEP 3 — TWO RULES THAT MATTER MOST

**① Gate the challenge on deliverability: never sell what you cannot serve.**
A route with no working data source answers **503 with its reason and issues NO challenge** — so
no money can move against a route that would fail afterward. Carry the reason in the payload
(`NOT_READY: <why>`), not just a status code.

**② Exercise the delivery path BEFORE promoting**, using a **shadow-only selftest route** that
calls every data fetcher with no payment. This is not a formality — it caught the one real
defect: **CoinGecko answers 429 from Cloudflare's shared egress IPs**, so the price route would
have charged and then failed.

Keyless sources verified reachable from the edge: `8004scan.io` (ERC-404/8004 agents),
`api.dexscreener.com` (LP pairs), `api.coinbase.com/v2/prices/<SYM>-USD/spot` (with
`api.kraken.com` as fallback), `api-mainnet.magiceden.dev/v2/collections` (limit must be a
multiple of 20). **Binance answers 451 from restricted locations.**

**Strip the selftest route from the promoted artifact and prove it 404s afterwards.**

## STEP 4 — deploy, and the three traps

1. **`Content-Type` must be `application/javascript`, `text/javascript` or `multipart/form-data`.**
   `application/javascript+module` → **415**. With `application/javascript` the script is
   **service-worker syntax**, so `export default {fetch}` is invalid — use
   `addEventListener("fetch", e => e.respondWith(...))`.
2. **An uploaded script is not a served script.** The PUT returns `success:true` and the URL still
   **404s (code 1042)**, because `workers.dev` routing is **disabled by default**.
   Fix: `POST /accounts/:id/workers/scripts/:name/subdomain {"enabled":true}`.
   *A 200 on upload is not a 200 on the address.*
3. **Shadow first, then promote.** Deploy to a `<name>-vN` shadow → verify → PUT the clean
   artifact onto the real name → **DELETE the shadow**. Never promote a build whose delivery path
   is untested.

## Diagnosing an existing Worker without guessing

The deployed source is retrievable — read it instead of inferring behaviour:

```bash
curl -H "Authorization: Bearer $CF" \
  "https://api.cloudflare.com/client/v4/accounts/$A/workers/scripts/<name>"
```

It returns **multipart**; parse the part named `worker.js`. **`/content` answers 405.** Also worth
reading: `/pricing`, `/openapi.json` (the authoritative route list — probe those paths rather than
inventing them), and `.../deployments` (who deployed it and when).
