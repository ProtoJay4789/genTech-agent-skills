# Paid-path failure modes, and the bazaar's real query contract

Measured on the live GenTech gateway, 2026-11-17. Two things here cost real answers.

## 1. A dict is not a Response — and the buyer has already paid

In a FastAPI/Starlette handler, `return {"status": "available"}` becomes an HTTP **500** with no body. In a
paid route that failure lands **after** verification and settlement: money moved, the buyer gets a 500, and
there is nothing to retry against.

- **Every failure path in a paid handler must return a real response object** (e.g. `JSONResponse(...,
  status_code=503)`) carrying a reason — `Service unavailable` / `Backend unavailable` — not a bare dict.
- **Check the import you reference, not just the branch you add.** A `JSONResponse` used in a new branch while
  only `Response` is imported fails at request time, not at import time, so a syntax check passes.
- **Grep the whole handler for `return {`** after fixing one — the same shape appears more than once, and the
  second path is the one that fires in production.**

## 2. Prove the guard can fail

Write a test that calls the handler directly with a key that has no backend, and assert the result **has a
`status_code`**. Then revert the fix and rerun: the test must go **red** (`dict status=MISSING`). A test that
has never failed is decoration. Exit 2 when the module cannot be imported — never a pass.

## 3. The payment log must be written after the endpoint, not inside it

If settlement is recorded inside the paid handler, a delivery failure raises out of the handler and **no
payment row is written** — the ledger silently loses the sale. Record it in the middleware after
`call_next(request)` and key the row off `request.state`: the row then exists for a 200, a 500 and a 503
alike, which is exactly the "money taken, nothing served" defence.

**Do not put verdict state in a `ContextVar` for this.** Starlette runs the endpoint in a different task from
the middleware, so a ContextVar set in the handler is invisible to the logger — measured: it logged `absent`
on a request that carried a credential.

## 4. A field added later cannot appear in older rows

Before calling a telemetry gap a defect, check **when the field was added** against the timestamps of the rows
you are counting. "Zero of 15 rows carry a tx" was history, not a bug — the capture block landed five days
after those calls. **The honest verdict for a new field with no traffic since is "untested", not "broken".**

## 5. The CDP bazaar query contract — wrong params return a confident false negative

```
GET {facilitator}/discovery/search?query=<text>&pay_to=<addr>&network=eip155:8453
```

- **`pay_to`, snake_case, on `/discovery/search`.** Using `/discovery/resources?payTo=…` returns a normal page
  of unrelated resources, so the search looks like it ran and found nothing of yours. **Always sanity-check a
  zero result by searching your own brand name** — if `query=<your brand>` returns nothing, the query is wrong,
  not the index.
- Read response arrays from **`resources`** (with `partialResults`), not `items`.
- **Indexing is triggered by a successful paid call through the CDP facilitator** — there is no registration
  form or API call. The resource's `lastUpdated` equals the payment timestamp that listed it. A seller who has
  never been paid is genuinely absent, and publishing a `/.well-known` manifest does not fix that.
- Each listed resource carries a **`quality`** block: `l30DaysTotalCalls`, `l30DaysUniquePayers`,
  `lastCalledAt`. This is third-party per-endpoint demand data, free, refreshed by the facilitator — it counts
  payers our own traffic log cannot. **Attribute those addresses against our own wallets before calling a
  unique payer a customer; our settle-test wallet is one of them.**
