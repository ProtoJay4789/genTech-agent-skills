# Status codes are claims — what a paid boundary should say when it cannot serve

A status code is not a label on an error; it is a **statement about the service's future**. At a paid
boundary the difference is expensive, because the callers reading it are automated agents and
conformance suites that react to the category rather than the prose.

## The one table that matters

| code | the claim it makes | when it is honest |
|---|---|---|
| `402` | "pay me and you get this" | the backend is up and the path is real |
| `404` | "nothing here, and nothing is coming" | the service was withdrawn, never existed, or the sub-path is not one we sell |
| `410` | "this existed and is retired" | a deliberately retired product with a name people may still hold |
| `412` | "**you must satisfy a precondition, then pay**" | the buyer's authorization is well-formed but needs a one-time approval (`PERMIT2_ALLOWANCE_REQUIRED`) |
| `503` | "**temporarily** unavailable — retry later" | the backend is down right now and *is expected back* |

**`503` is the only one of these that promises a future.** Using it for a service whose code no longer
exists is a lie that costs credibility with exactly the tools now grading you: a verifier records a `503`
as an outage, so a permanently dead backend is scored as a broken gateway, every single run.

- **Withdraw, do not soften.** If the backend is gone, remove its route so the honest `404` branch fires.
  Keeping it routed with a `503` converts "we discontinued this" into "we are broken", forever.
- **Withdrawal is a route-map change, not a handler change.** The readiness gate turns "backend not up"
  into `503` *because* a route still exists; delete the entry and the existing not-deliverable branch
  answers `404` with no new code and no new failure path.
- **Never withdraw silently.** Keep the service listed in the withheld block **with the reason the system
  itself gives**, so a reader learns why rather than inferring an outage. Withheld-with-reason and
  gone-404 are consistent; withheld-and-503 is not.
- **Check the deployment gate before promising a fix.** The manifest and the backend route map are
  typically loaded once at process start, so a corrected map does nothing until the process restarts.
  Name that gate explicitly in the handoff instead of reporting the change as live.

## Always ship the control case with the withdrawal

A withdrawal removes functionality, so the test that proves it is **not** "the dead paths now 404". It is:

```
/v1/<withdrawn>        -> 404   (the fix landed)
/v1/<withdrawn-sub>    -> 404   (and no sub-path of it still challenges)
/v1/<a-live-service>   -> 402   (the control: you did not take the paid path down with it)
```

The third line is the one that catches an over-wide edit. Without it, a change that quietly removed a
working route passes every check you wrote.

## Why this is a compliance item, not a housekeeping item

Paid-boundary behaviour is graded from outside by people you cannot argue with: automated harnesses pay
per call to see what happens, indexers count your status mix, and a directory listing that describes a
service you answer with `503` reads as a bait page. Measured pattern worth internalising: one conformance
bot's status mix over three days was `200 1,706 · 402 1,029 · 503 680 · 404 313` — the largest avoidable
block was `503`, and every one of those was a service we had already stopped selling.

**An honest `404` costs a lead. A dishonest `503` costs the audit.**

## A generic `402` is a diagnosis failure — and it is indistinguishable from no demand

The `402` branch is where a compliant server tells the client **which** problem it has. Flatten every
rejection into `{"error":"payment_proof_invalid"}` and you get two costs that look nothing alike from
outside and identical in your own logs:

- **`PERMIT2_ALLOWANCE_REQUIRED` must be `412 Precondition Failed`, not `402`.** The spec reserves it to tell
a client *"do a one-time approval transaction, then retry"*. Answer `402` and a client that would have
self-served the approval gives up — and in your traffic ledger it is indistinguishable from an agent that
never wanted the service.
- **`settlement_pending` is NON-TERMINAL.** The transaction broadcast but its confirmation could not be
established (RPC error or timeout). It **may still confirm**. Retry settlement **exactly once**, and
**reconcile the broadcast hash on chain before charging again** — treating a pending settlement as a hard
rejection invites the buyer to pay twice.

**Rule:** before shipping a paywall, grep your server for every error code the facilitator can return and
confirm each has its own branch. A count of zero matches for `settlement_pending`, `412`, `PERMIT2` is the
tell that everything is being collapsed into one shape.

**Also return the receipt on failure.** The `PAYMENT-RESPONSE` header carries the facilitator's settlement
response **after attempting settlement, whether it succeeded or failed** — a client that gets a bare `402`
cannot tell "I did not pay" from "you could not settle". See `references/payment-telemetry-ledger.md`.
