# Running an x402 gateway as a Cloudflare Worker

Everything here is measured against a live Worker deployed through the Cloudflare API.
Use it when building, rebuilding or debugging an edge x402 estate.

## Rule 1 — a middleware that initialises remotely can take the whole estate down

**Symptom: every free route answers 200 and every PAID route answers 500.**

That split is the signature. Free routes bypass the payment middleware; paid routes go
through it, so a uniform 500 on paid routes only means one shared initialisation failure
— not a backend problem. The `@x402` middleware initialises by fetching the facilitator's
`/supported` list and intersecting it with the networks the gateway advertises.

**An EMPTY INTERSECTION throws, and the framework's default error handler renders it as a
bare `Internal Server Error`.** So the cause is invisible from the response, and the
gateway silently sells nothing for as long as nobody checks a body instead of a status.

- **Always assert the intersection explicitly before deploying:** fetch the facilitator's
  networks and the gateway's advertised networks and prove they overlap. A test that cannot
  fail is not a test; print the intersection.
- **Prefer writing the 402 yourself over adopting a middleware you cannot read.** The whole
  protocol is ~100 lines: build the requirements, emit `402` + `PAYMENT-REQUIRED` (base64
  JSON: `x402Version`, `resource{}`, `accepts[]{scheme,network,asset,payTo,amount,…}`, and
  `extensions.bazaar{}`), and on `PAYMENT-SIGNATURE` (legacy `X-Payment` accepted) call
  `/verify` then `/settle`. **`amount` is the v2 field — `maxAmountRequired` alone makes the
  challenge unpayable to every v2 client.** A dependency that fails at init is a dependency
you cannot debug at 2am. See `v2-payment-challenge.md` for the full field contract.
- **Emit `PAYMENT-RESPONSE` on the settlement-FAILURE path too** — the spec owes a receipt
  "whether successful or failed". Success-only receipts under-report refusals.

### Reading a deployed Worker's source when you cannot see the repo

```
GET /accounts/:id/workers/scripts/:name        → multipart; parse the part named `worker.js`
GET /accounts/:id/workers/scripts/:name/content → 405 method_not_allowed
GET /accounts/:id/workers/scripts/:name/deployments | /settings → metadata (compat date, bindings)
```

Diagnose from the deployed bytes, never from what the notes claim is deployed.

## Rule 2 — pick a facilitator whose supported networks overlap yours

**Testnet-only facilitators wired to mainnet rails are the single most common way an x402
gateway dies quietly.** Coverage measured live:

| Facilitator | Networks | Auth |
|---|---|---|
| `facilitator.payai.network` | broadest EVM + Solana, incl. base, avalanche, polygon, xlayer, arbitrum, sei, bnb, skale | **keyless** |
| `facilitator.goplausible.xyz` | base, solana, algorand (mainnet + testnet) | keyless |
| `facilitator.naven.network` | robinhood chain, base, xlayer | keyless |
| `x402.org/facilitator` | **testnets only** — never wire a mainnet rail to it | keyless |
| `api.cdp.coinbase.com/platform/v2/x402` | base, polygon, arbitrum, world, solana | **needs auth; rejects Basic / Bearer / X-API-Key with a plain-string secret** |

**Prefer a keyless facilitator: it removes the entire class of credential-shape failures.**
When one does need auth, probe it before committing — `GET /supported` (no auth) says what
it serves; `POST /verify {}` returns a schema-shaped error you can read the expected payload
from.

## Rule 3 — the challenge gate must be LIVE, not compile-time

**A `servable: true` flag proves a data source EXISTED when the code was written. It cannot
prove the upstream answers NOW.** Free public data APIs throttle shared datacentre egress
hard — measured: CoinGecko, DexScreener and GeckoTerminal all answer `200` from an ordinary
host and `429` from Cloudflare's IPs. A static gate therefore lets the gateway charge for a
call it then fails.

```
request → is the route servable at all?     no  → 503 with the reason, NO challenge
        → fetch the data ONCE               fail→ 503 DELIVERY_PREFLIGHT_FAILED, NO challenge
        → cache the payload (short TTL, in-isolate)
        → no PAYMENT-SIGNATURE              → 402 + PAYMENT-REQUIRED
        → verify → settle → serve FROM CACHE (no second upstream dependency)
```

- **Fetch before quoting.** The pre-flight costs one upstream call per paid request and is
  the only thing that makes "no challenge for what we cannot deliver" true rather than
  aspirational.
- **Serve the paid request from the cache**, never from a second upstream call — otherwise
  you pay twice and can still fail after the money moved.
- **Retry-on-429/5xx with backoff wraps every upstream call, but never rely on it.** It
  softens the throttle; it cannot make a throttled provider reliable.
- **Carry the refusal reason in the body**, not just in the status — a crawler reading the
  `503` should learn *why* and that nothing was charged.

### Keyless edge data sources, and their quirks

| Need | Source | Quirk |
|---|---|---|
| spot price | Coinbase `/v2/prices/<SYM>-USD/spot` | Binance answers `451` from restricted regions |
| spot price (fallback) | Kraken `/0/public/Ticker?pair=X<SYM>ZUSD` | |
| LP / pool data | `api.geckoterminal.com/api/v2/networks/<net>/tokens/<addr>/pools` | throttles CF egress |
| LP / pool data (fallback) | `api.dexscreener.com/latest/dex/tokens/<addr>` | throttles CF egress; empty `pairs` for unknown tokens |
| ERC-8004 agents | `8004scan.io/api/v1/agents` | |
| NFT collections | `api-mainnet.magiceden.dev/v2/collections` | `limit` must be a multiple of 20 |
| token risk | `api.gopluslabs.io/api/v1/token_security/<chainId>?contract_addresses=` | chain id in the path |
| gas | any public RPC, `eth_gasPrice` | |

## Rule 4 — test the delivery path BEFORE promoting, with a shadow-only selftest route

**A free `__selftest` route that calls every data fetcher with no payment** is the cheapest
test that can find a charged-then-failed path. It found the throttling above, which no
amount of reading the code would have.

Then, in order:

1. Deploy to a **shadow name** and enable its route.
2. Hit `__selftest`; every fetcher must report its source.
3. **Strip the selftest route from the promoted artifact** and prove it `404`s afterwards —
   a free data route on a paid surface is a leak.
4. PUT the clean artifact onto the **real** name, then **DELETE the shadow**.

## Rule 5 — the Cloudflare deploy API has traps that all return a plausible 200

1. **Content-Type.** `application/javascript`, `text/javascript` or `multipart/form-data`.
   `application/javascript+module` → **415**. Plain `application/javascript` means
   **service-worker syntax** — `export default {fetch}` is invalid there; use
   `addEventListener("fetch", e => e.respondWith(...))`.
2. **An uploaded script is not a served script.** PUT returns `success: true` and the URL
   still **404s (code 1042)**, because `workers.dev` routing is **disabled by default**:
   `POST /accounts/:id/workers/scripts/:name/subdomain {"enabled":true}`.
   **A 200 on upload is not a 200 on the address** — curl the address before believing it.
3. **`node --check <file>` before every upload.** A duplicate `let x` declaration comes back
   from the API as `400 / code 10021 "Identifier 'x' has already been declared"`. **A 400
   here means the OLD version is still serving**, so any probe afterwards is measuring the
   previous build — never read those results as the new build's.
4. **Deploy with bindings as multipart, using BOTH the part name and the filename:**
   `-F 'worker.js=@build.js;filename=worker.js;type=application/javascript+module'` plus
   `-F 'metadata=@meta.json;type=application/json'` where metadata carries
   `{"main_module":"worker.js",...}`. **The module name comes from the uploaded FILENAME, not
   the form part name** — with the part named `worker.js` but the file called `build.js`, the
   API rejects the upload with `10021 "No such module: worker.js"`. Both must say `worker.js`.

   **Secret bindings cannot be re-declared without their values.** Listing
   `{"type":"secret_text","name":"API_KEY"}` in metadata returns
   `10021 "invalid or missing text property for binding API_KEY"`. **Omit secrets from the
   upload entirely — they are preserved** — and re-declare only the bindings that carry an id
   (`d1`, `kv_namespaces`, etc.). A failed upload leaves every existing binding intact, so a
   400 during a bindings experiment is recoverable: fix the metadata and PUT again.
5. **D1 bindings REQUIRE ES module format** (`100329` otherwise), and bindings then arrive as
   **`env.DB`, not a global**. Converting to modules changes how you reach every binding.
6. **The PUT returns `success: true` with an EMPTY `bindings` array.** The response does not
   echo them. **Prove a binding by writing a row and reading it back**, never by reading the
   deploy response.
7. **`success: true` is a claim about the API, not about what is being served.** Two checks
   close the gap, in this order: (a) fetch the deployed source back
   (`GET /workers/scripts/:name`, parse the `worker.js` part) and grep it for the change you
   just made — that proves the bytes landed, without trusting the response; then (b) curl the
   live route. **Edge propagation lags the upload by a few seconds**, so a live read that
   still shows the OLD value immediately after a successful deploy is not a failed deploy —
   re-read before concluding either way, and never report "deployed" on the strength of the
   PUT alone.

## Rule 6 — give the edge estate its own traffic ledger

A Worker has no filesystem, so an estate without a log sink is invisible to every report
that reads the other estate's log file — and the report looks complete while covering half
the surface.

- **D1 is usually the right sink**: the writer needs a binding, the READER does not — the
  reporting job can query `POST /accounts/:id/d1/database/:uuid/query {"sql":"…"}`.
  Analytics Engine is a natural fit when available but is a permission-scoped API (it can
  return `403` on a token that works fine for Workers and zones).
- **Log ONCE per request, AFTER the response is built, with the TRUE final status.** Logging
  at each branch counts one request two or three times.
- **Wrap the log in try/catch and fire it via `ctx.waitUntil`** — telemetry must never break
  a response.
- **Reuse the reporting job's caller vocabulary** (`discovery` / `self` / `other` / `unknown`)
  or the two estates cannot be read together.
- **Report the estates side by side, never summed** — sharing one `payTo` means merging
  double-counts. Money measured on-chain stays correct across both; only behaviour needs the
  union.
- **A failed read must never print as `0`.** Emit `COULD NOT READ — not zero, UNKNOWN`,
  because a failed read rendered as zero is exactly how a blind monitor passes. Verify a new
  telemetry path by generating traffic and reading the rows back.

## Rule 7 — an edge estate is only worth having if it is edge-native

Its whole reason to exist is to serve when the VPS does not. **Routes that need the VPS
belong marked unservable *with the reason attached*, never proxied into a dependency that
shares the VPS's fate** — and the reason must say which kind of absent it is (no source
exists at all vs. the source is internal vs. a credential is missing), because those have
different remedies.

**Before calling a route blocked, test it.** Half the blocked routes in one rebuild turned
out to be assumptions: a public RPC covers gas, and a keyless token-security API covers
risk scoring, both reachable from the edge all along.
