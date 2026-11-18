# Receipts, error codes and payment telemetry

At the 402 boundary a server has two jobs: take the money, and tell the client **which** problem it has. A server that
prices correctly and diagnoses generically is indistinguishable, in its own analytics, from a server nobody wants.

## The receipt exists — send it, then log it

After attempting settlement the server returns `PAYMENT-RESPONSE`: base64 JSON of the facilitator's
`SettlementResponse` — **on success AND on failure**.

Fields that matter: `success`, `transaction` (broadcast hash), `network`, `payer`, `errorReason`.

- **Log it.** A server that settles and drops the receipt can prove traffic and never revenue.
- **Never store the signature payload.** Record `payer`, `transaction`, `network`, `success`, `errorReason` — not the
  authorisation itself. A payment ledger that leaks a signature is a liability; one that counts refusals is an instrument.
- **Reconcile `transaction` on chain** before believing any local total. The hash in the receipt is the only proof a
  sale happened that does not require an indexer, a key, or a vendor's dashboard. **That only works if you KEPT the
  hash** — persist `transaction` beside the verdict at settlement time (absent stays `null`, never defaulted), or the
  ledger can report that money moved and never say which transaction. Per-receipt verification, free-explorer
  per-chain gating and the fail-loud reconciler rules: `settlement-reconciliation.md`.
- **Traffic is not demand.** Before building a route because it "gets requests", classify the callers —
  catalogue health checks and uptime probes (`*-probe`, `*-monitor`, `*-trust-*`) never pay, and a steady
  stream of `404`/`503` on one path is a stale catalogue advertising you, not a buyer knocking. Decide with
  `traffic-versus-demand.md`.

## Error codes that change what the client does

| code | correct response | why |
|---|---|---|
| `PERMIT2_ALLOWANCE_REQUIRED` | **`412 Precondition Failed`**, not 402 | tells the client to do a one-time approval and retry. A 402 reads as "you did not pay" and a client that would have self-served gives up — silently, and it looks exactly like no demand |
| `settlement_pending` | non-terminal; retry settlement **exactly once** | the tx broadcast but confirmation failed (RPC error/timeout) and **may still confirm**. Reporting failure invites a second payment for something already landing |
| duplicate settle (SVM) | reject via a settlement cache | a client resubmitting before confirmation can double-settle |

**Never flatten the facilitator's reason into one generic rejection.** The reason string is the only artefact that lets
you answer "did they refuse, or did nobody try?" months later.

## Retired routes answer 410, not 404

When a service is deliberately withdrawn:

- **`410 Gone`** = it existed and is intentionally gone — a catalogue monitor can act on it and stop probing.
- **`404`** = never existed — a monitor keeps re-probing and grades the seller as broken.
- **Never `402`** for a route you cannot serve: a challenge for an unservable resource is how an agent pays for nothing.
- Keep retired names in an explicit set so genuinely unknown paths still 404. Two different answers for two different facts.
- **Put the pointer in the BODY, not just the status.** A `410` whose body names the live inventory
  (`"live_services": "https://…/.well-known/x402"`) lets a monitor re-target instead of merely stopping — a status
  alone tells it the door is shut, the pointer tells it where the open one is. Same predicate every time: a retired
  name in the set → `410` + pointer, an unknown name → `404`, a servable name → `402`.
- **Prove all three branches in one run** before claiming it: retired → `410`, unknown → `404`, servable → `402`. A
  retirement that also 410s unknown paths has silently deleted your 404s, and one that 402s a retired path is selling
  something that does not exist.

## Telemetry: three facts per request, kept separate

Write a second ledger beside the traffic log, one row per request that touched the paywall:

| field | values | why it is separate |
|---|---|---|
| `hdr` | `absent` · `x402-auth` · `x402-paysig` · `x402-xpay` · `x402-legacy` · `mpp` · `moove` | was a credential even present? |
| `stat` | `absent` · `invalid` · `verified` · `settled` | **verified ≠ settled** — collapsing them turns a pending settlement into a sale |
| `rail` | CAIP-2 network the proof claims | a rail-specific failure shows up as a pattern instead of "no sales" |
| `why` | the verifier's own reason string | the only way to distinguish a refusal from a no-show later |
| `tx` | the settlement hash, or `null` | what a reconciler needs; `null` means "rail returned none", not "0x0" |

Rules that keep the ledger honest:

- **Mirror the extractor exactly.** If `extract_proof()` would accept a header, the telemetry classifier must not report
  `absent`. Derive both from one list of accepted header shapes — a detector that misses `Authorization: x402 …` reports
  absent on real buyers.
- **Stamp the verdict on the request object, not a context variable.** A middleware and an endpoint can run in separate
  tasks; a `ContextVar` set inside the endpoint is invisible to the middleware that logs it, and the row says `absent`
  on a request that carried a credential.
- **Wrap every write in a bare except.** Telemetry must never be the reason a paid call fails.
- **A refused credential is a first-class row.** Prove the classifier fires by sending a deliberately invalid proof and
  reading the row back.

## One implementation, N facilitators

Most facilitators speak the same `/verify` + `/settle` envelope. Parameterise **one** function as
`(base_url, label)` rather than copying the body per vendor: two copies of a money path drift, and the failure mode of a
drifted money path is a buyer who paid and was told they did not.

- **Prove equivalence** before trusting it: both implementations must refuse the same unadvertised rail and the same
  malformed proof, with the same reason shape.
- **Check the envelope exists before writing the branch** — POST `{}` to `/verify` and `/settle`; a `400
  invalid_request` naming the required fields means the endpoints are real and want the standard body.
- **A missing verify branch is worse than a missing rail.** An unknown network falls through to the default verifier and
  is rejected as "network not accepted" — a buyer who paid and was told they did not.

## Sequencing when adding a rail

1. Rail definition with the domain **measured** from the token contract (see `adding-a-settlement-rail.md`).
2. **Verify branch wired** for that network.
3. Advertise it, restart, confirm the challenge carries it.
4. **One real paid call**, receipt captured, hash confirmed on chain.

Advertising between (1) and (2) is the only ordering that can take money and refuse it.
