# Payment telemetry and error codes — what a 402 must tell the client, and what you must log

A correct price with a wrong diagnosis is indistinguishable from no demand. Every rule here was measured on a live
gateway that served 57k knocks and near-zero sales while nobody could say whether buyers were refused or never tried.

## 1 · Send the receipt, then log it

The facilitator returns a **`Settlement Response`** which the server must return in **`PAYMENT-RESPONSE`** (base64 JSON)
— **on success AND on failure**. It carries `success`, `transaction` (the broadcast hash), `network`, `errorReason`.

**Log at minimum:** `payer`, `transaction`, `network`, `success`, `errorReason`. **Never log the signature payload.**
A server that settles and drops the receipt can prove traffic and never revenue; and without a payment field in the
request log, "buyers try to pay and fail" is unfalsifiable from your own data.

**Telemetry must never break a paid call:** wrap every write, never raise from a logger, and keep the ledger a
separate file from the request log so one cannot corrupt the other.

## 2 · Two codes that change client behaviour — do not flatten them into 402

| condition | required response | why |
|---|---|---|
| `PERMIT2_ALLOWANCE_REQUIRED` | **`412 Precondition Failed`**, not 402 | tells the client to do a **one-time approval** and retry. Return 402 and a client that would have self-served gives up — and in your ledger that is indistinguishable from an agent that never wanted the service |
| `settlement_pending` | **non-terminal**: report pending with the broadcast hash, retry settle **exactly once**, reconcile the hash on chain before charging again | the tx may still confirm; a plain 402 invites a **second payment** for something already landing |
| duplicate settle (SVM) | reject via a settlement cache | a client resubmitting before confirmation can double-settle |

**The rule:** at the 402 boundary, **name the client's actual defect.** A generic `payment_proof_invalid` is a diagnosis
failure, and diagnosis failures get counted as demand failures.

## 3 · Instrument the credential, not just the status

Log **which payment credential arrived** and **which shape**, mirroring the extractor exactly:
`Authorization: x402 …` · `PAYMENT-SIGNATURE` · `X-PAYMENT` · `x-402-token` · MPP `Authorization: Payment …` · hosted-link schemes.
Then log the **verifier's own reason string** and the **rail the client tried** (`eip155:8453`, `solana:…`).

**Pitfall — the detector must not disagree with the extractor.** A header check that misses `Authorization: x402 …`
(the v2 convention) reports "absent" on real buyers and makes the ledger lie about the one thing it exists to count.
**Derive both from the same function.**

**Pitfall — a framework's request context does not always cross the middleware→endpoint boundary.** A ContextVar set
inside the endpoint can be invisible to the middleware that logs it. Stamp the verdict on the request object itself
(e.g. `request.state`), not on task-local storage, and prove it with a live probe that carries a credential.

## 4 · One verifier implementation for N facilitators

Facilitators that speak the standard `/verify` + `/settle` envelope should share ONE implementation, parameterised by
base URL and label. Two copies of a money path drift, and the failure mode of a drifted money path is a buyer who paid
and was told they did not.

**Before writing a branch for a new facilitator, probe it:** `POST /verify` and `POST /settle` with an empty body. A
`400 invalid_request` naming `paymentPayload`/`paymentRequirements` proves the endpoints exist and want the standard
envelope — that is the whole compatibility check.

**And wire the rail into the dispatch, not just the challenge.** A network with no dispatch branch falls through to the
default verifier and is refused as "network not accepted" — *after* the buyer has signed.

## 5 · Catalogues index what the CLIENT echoes, not what you declare

Discovery catalogues refresh a listing from the payment they process, **using the discovery declaration the client
copied out of your 402 into the payload.** Consequences:

- **Publishing `input.pathParams: {}` for a templated route gives the catalogue nothing to resolve**, so it stores a
  templated row (`…/lp/:address`) that no client can call. Publish the parameter names **and** an explicit route
  template beside the concrete URL, and derive both from one source.
- **A catalogue row is refreshed by a settle (and, on some facilitators, by a `/verify` alone)** — so a stale or
dead
  row is fixed by **behaviour**, not by a listing form. Check the facilitator's own docs for whether verify alone
  refreshes: if it does, a refresh costs nothing and needs no funded wallet.
- **A resource string you cannot edit is not yours to fix — but you can re-register it** by paying/verifying on the
  concrete URL, which is the only way a catalogue row stops pointing at an unservable template.

## 6 · Pitfall — an SDK's response object is not a dict

An SDK that returns a typed object (`SettleResponse`, dataclass, pydantic model) makes `resp.get("transaction")`
return **`None` without raising**. A script built on that reports `settled: false` on real settlements — and a test that
only asserts "no exception" passes.

**Normalise before reading:** `d = resp if isinstance(resp, dict) else dict(vars(resp))`, then read fields. When a
result looks like a zero, check the **type** of the thing you parsed before you trust the zero.
