# Listing lifecycle and payment telemetry

Depth for the two questions a seller asks monthly and can rarely answer: *why is nobody finding us?* and *is anyone
trying to pay?* Neither is fixed by a portal form, and neither is visible in a request log.

## Catalogue lifecycle

| fact | consequence |
|---|---|
| no registration form or write endpoint anywhere | "we are not listed" means no declaration reached that facilitator — never "we forgot to sign up" |
| identity comes from the **declaration the client echoes** into the payment payload | a client that drops/rewrites `extensions` registers what *it* thinks it saw; the server's declaration is not authoritative on its own |
| cataloguing runs on `/verify` **and** `/settle` | a listing or refresh can cost **zero** — try verify-only before paying |
| entries refresh without the first-listing probe | a stale row is cheap to keep alive, but its URL does not change |
| a templated row (`/v1/lp/:address`) refreshes yet keeps the template | fix the DECLARATION, then refresh; paying again will never rewrite the path |
| delist is time-based (~30 days without a settle) | age each row from the catalogue's `lastUpdated`; a row showing `0 calls` is already on the clock |
| catalogue `quality` fields (`last30dCalls`, unique payers, `lastCalledAt`) | free platform-side revenue evidence — it can confirm or contradict your own ledger, so read it before reporting either |

**Before promising a fix, probe the listed URL.** A `404` on the catalogue's resource plus a `402` on the same
service at a concrete path proves the listing is a dead link and the service is fine — two facts a status-only
catalogue check cannot separate.

## The second ledger

A request log (`timestamp, path, method, status, user-agent`) **cannot distinguish a refusal from a no-show**, which
is how a seller concludes "nobody can pay us" and is wrong. Keep a separate payment ledger:

| field | values | why |
|---|---|---|
| `hdr` | `absent` / `x402-auth` / `x402-paysig` / `x402-xpay` / `mpp` / `moove` | did a credential arrive, and in which convention |
| `stat` | `absent` / `invalid` / `verified` / `settled` | the decision, not the HTTP code |
| `rail` | CAIP-2 (`eip155:8453`, `solana:…`) | turns a rail-specific failure into a pattern instead of zero sales |
| `why` | the verifier's own reason string | never substitute a generic reason |
| `ok` | verifier result | keep separate from `stat` so "verified" never reads as "settled" |

Rules:

- **Mirror the extractor's header list.** If the code that finds a proof accepts `Authorization: x402 …`, the logger
  must not report `absent` for it. Enumerate every header the extractor reads, or the ledger lies about the one
  thing it exists to count.
- **Telemetry must never break a paid call:** wrap every write, swallow every error, never raise from a logger.
- **Store no signature, address or secret** — record *that* a credential arrived and the verdict. A ledger that
  leaks signatures is a liability.
- **State does not cross the framework boundary.** A `ContextVar` set inside the endpoint is invisible to the
  middleware that logs the response (separate task). Stamp `request.state` instead.
- **A missing state file prints `NOT RUN`/`UNKNOWN`, never `0`.** An absent ledger read as zero sales is how a false
  revenue claim reaches an investor deck.

## Proving one real settlement without an indexer

1. **Dry-run first** — fetch the 402, build the payload, print the chosen rail and amount, send nothing.
2. **Cap the spend in the client:** per-call ceiling + one preferred rail, registered *before* signing. Refuse when
   the challenge leads with another rail or exceeds the cap.
3. **Pay one cheap call on your own endpoint** and keep the `PAYMENT-RESPONSE` — it carries `transaction`,
   `network`, `payer`, `success`. That is chain-side reconciliation without an indexer.
4. **Confirm the tx receipt on chain** (status success + an ERC-20 `Transfer` of the expected amount to `payTo`)
   before believing it.

Pitfalls that make a successful payment look like a failure:

- **The SDK returns a response OBJECT, not a dict.** `settle.get("success")` on an object returns `None` **without
  raising**, so real settlements report `settled: false`. Normalise (`dict(vars(obj))`) before reading any field,
  and assert on a known-good response — a suite that only checks status codes passes straight through this.
- **Header lookup is case-insensitive; a dict lookup is not.** Read receipts through a case-folded map.
- **A multi-rail challenge leads with one rail** — the SDK takes the first acceptable one, so policy must select by
  rail explicitly or the buyer signs on a chain they never funded.
