# Payment telemetry — can you prove a refusal, or only count a no-show?

A traffic ledger that records `path · method · status · user-agent` answers *how many people knocked* and
nothing else. **A `402` count is not demand and a `200` count is not revenue**: without a payment field you
cannot distinguish a buyer whose signature was rejected from a robot that read the price and left. Measured
consequence of missing it — a gateway reporting tens of thousands of knocks, zero sales, and no way to say
whether anything was ever broken.

Ship a **second ledger** beside the traffic log, one row per payment event.

## The five fields

| field | values | why it must exist |
|---|---|---|
| `hdr` | `absent` · `x402-auth` · `x402-paysig` · `x402-xpay` · `x402-legacy` · `mpp` · `moove` | did a credential arrive at all, and in which shape |
| `stat` | `absent` · `present` · `invalid` · `verified` · `settled` | the decision, not the HTTP code |
| `rail` | the CAIP-2 network the proof named (`eip155:8453`, `solana:…`) | a rail-specific refusal becomes a pattern instead of 0 sales |
| `why` | the verifier's own reason string | never a generic one — the reason is the diagnosis |
| `ok` | verifier boolean | keep **verified** separate from **settled**; verified-but-unsettled is a real state |

**Log no secret, no address, no signature.** Record that a credential was present and what was decided
about it. A ledger that stores signatures is a liability; one that counts refusals is an instrument.

## Two implementation traps that silently produce `absent`

- **The header detector must mirror the proof extractor, clause for clause.** Write the detector by reading
`extract_proof()` and matching its precedence (`Authorization: x402 …` first, then `PAYMENT-SIGNATURE`,
then `X-PAYMENT`, then the legacy header). A detector that omits the v2 `Authorization: x402 …` convention
reports **`absent` on every real buyer** — the ledger is most wrong exactly for the callers you built it
for.
- **In Starlette/FastAPI, do not pass the verdict from the endpoint to the middleware in a `ContextVar`.** The
endpoint runs in a different task than the middleware, so a context variable set inside the handler is
invisible to the logger and every row reads `absent`. Stamp it on **`request.state`** — same object, no
context propagation.

**Non-negotiable:** wrap every telemetry write in `try/except` and never let it raise. The ledger must never
be the reason a paid call fails — and it must never be silently skipped either, so record the failure
somewhere that a reader looks.

## Prove it by probing the patched server, not by reading the diff

Unit-testing the logger does not tell you whether the header is visible at the middleware. Boot the server
with a scratch ledger directory and drive it with the shapes that matter:

```bash
X402_TRAFFIC_DIR=$(mktemp -d) PAYMENT_VERIFY_MODE=simulation python3 server.py &   # note the port it prints
for h in '' 'Authorization: x402 eyJhbGciOiJub25lIn0' 'PAYMENT-SIGNATURE: eyJ2ZXJzaW9uIjoxfQ==' \
         'X-PAYMENT: junk' 'Authorization: Payment abc.def'; do
  curl -s -o /dev/null -w "%{http_code}\n" ${h:+-H "$h"} http://127.0.0.1:<port>/v1/<paid-path>
done
cat "$X402_TRAFFIC_DIR/payments.jsonl"
```

Six rows, six verdicts: no header → `absent`; each credential shape → its own `hdr` plus `invalid` with a
`why`. **A probe that shows `absent` on a request that carried a credential is the bug, not a quiet night.**
Read the port from the process output rather than assuming one — a hardcoded port boots on a different port
and every probe returns `000`.

## The receipts already exist — do not build an indexer first

The facilitator hands you the proof of sale. Capture it before reaching for chain indexing:

- `PAYMENT-RESPONSE` carries the settlement response (`transaction`, `network`, `success`, `errorReason`)
**on success and on failure**. Persisting it is the free version of an on-chain reconciler.
- **Circle Gateway Nanopayments** exposes **search x402 transfers** (paginated) and **get transfer by ID** —
the only facilitator offering a first-class transfer ledger as an API.
- **Circle Facilitator Service** exposes `/verify`, `/settle`, and **get payment status** — poll one payment,
not a history.
- **PayAI** runs free credits with no portal signup for the plain `exact` flow, and its own docs state that
a 402 alone does not prove a payment settled.
- **CDP** is authoritative for Base and for the Bazaar listing; its `/supported` requires a signed JWT, so
"unreachable without credentials" is a fact about your key, not about the API.

**None of them sells demand.** Every one answers *did the payment work*; none answers *why nobody tried*.
Telemetry closes the first question and must never be presented as progress on the second.