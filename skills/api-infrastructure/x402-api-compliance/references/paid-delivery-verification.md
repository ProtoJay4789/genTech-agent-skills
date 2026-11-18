# Proving what a paid API actually DELIVERED (not just that it took money)

**Why this file exists:** an x402 surface can pass every challenge check and still leave the operator unable to
answer the only two questions that matter at month end — *did the buyer get the good?* and *who paid?* Both have
been lost on a live gateway while every 402 looked perfect.

---

## 1 · Three different claims, three different instruments

| question | instrument | what a pass looks like |
|---|---|---|
| will it take money? | `curl` the route | **402** with a well-formed v2 body |
| was the payment verified? | the facilitator's verdict, logged | `stat=verified` |
| did the buyer receive it? | the **delivery** status + a settlement hash | `200` **with** a `tx` |

**A 200 marked `verified` with no transaction hash is a claim, not a receipt.** Count the three separately in any
report; merging them lets a green gate hide an unproven hand-off.

## 2 · The bug class: a dictionary is not an HTTP response

**In FastAPI/Starlette, a handler that `return {...}` on a failure path produces a 500 with no body — and on a paid
route that happens AFTER the buyer has been verified and settled.** The buyer pays, receives nothing usable, and
has no reason to retry. Audit EVERY failure branch of the paid proxy:

```bash
grep -nE '^\s+return \{' server.py    # dict returns; check each one's handler
```

**Fix, in order:**
- `service_key` with no backend mapping → `JSONResponse(503)` with a reason, not a dict.
- backend connection error (`httpx.RequestError`) → `JSONResponse(503)` + the error text, not a dict.
- **check the imports the fix needs** — `JSONResponse` is easy to reference without importing it, which turns a
  handled error into a `NameError` on the failure path.
- **A dict returned by a NON-HTTP helper is fine** (a `/status` handler that FastAPI serialises). Only the paid
  proxy path is the defect surface — classify before "fixing" the whole file.

**Test it so it can go red:** call the handler directly with a bogus `service_key` and with a backend pointed at a
closed port; assert `hasattr(response, 'status_code')` and `503`. Then revert the fix and confirm the test FAILS
(`dict status=MISSING`). A guard that has never been seen failing is decoration.

**Confirm the payment still gets recorded when delivery fails:** the payment log is written in the middleware
AFTER the endpoint returns, so a downstream failure still leaves a `verified` row. Check that ordering before
claiming "money taken, nothing served is undetectable".

## 3 · Log the payer, or "N unique payers" can never become "N customers"

**Facilitator indexes publish a COUNT and never a list** (`quality.l30DaysUniquePayers`), and no per-resource
detail endpoint names them. The address is already inside the proof — read it from the EIP-3009 authorization:

- Accept both wire shapes: raw JSON (`Authorization: x402`) and **base64 JSON** (`PAYMENT-SIGNATURE`, v2).
- Walk the nested payload (`paymentPayload` → `payload.authorization.from`); do not regex the raw string.
- Take `from` / `payer` / `sender` only; **`to` is the merchant, never the payer.**
- **Normalise to lowercase** — an address compared byte-wise across two sources is how "5 unique payers" becomes 6.
- **Return `None` rather than a default.** A defaulted payer launders your own probes into customers.

**A privacy rule of "log no addresses" was written to stop a signature leaking — it over-corrected, because it also
made the payer unknowable.** The public payer address, already visible on chain in the same settlement, is the
right field; keep zero signature/nonce/payload bytes. **When you amend a documented rule, amend the comment too**,
or the next reader trusts a rule the code no longer follows.

## 4 · Measurement traps that produce confident wrong answers

- **A field that is null on every historical row is usually HISTORY, not a defect.** Check when the field's writer
  was added against the date range of the rows — *a column added after the fact cannot appear in older rows.*
  Before reporting "N rows are missing X", date the code that writes X.
- **A payer's on-chain nonce is NOT its payment count.** EIP-3009 `transferWithAuthorization` is submitted by the
  **facilitator**, so the payer never sends a transaction and its nonce stays 0 however often it pays. Nonce
  measures their *other* activity only.
- **A wrong query parameter yields a false negative that looks like a finding.** Discovery search is
  `/discovery/search?query=&pay_to=&network=`, returning `resources`. Asking `/discovery/resources?payTo=` returns a
  generic page of other sellers' entries and reads exactly like "we are not listed". **Read parameter names off the
  SDK client class before concluding absence.**
- **`partialResults: false` is what makes a search result admissible.** Without it you do not know the list was
  complete, and a partial list is not evidence of absence.
- **Indexing is triggered by a successful paid call through the facilitator, not by publishing a manifest.** So
  "we are invisible" and "nobody has paid yet" can be the same fact wearing two costumes.

## 5 · Order of verification for a paid surface

1. Every route answers **402** with a v2 body (no 404/500 anywhere).
2. `/health`, the discovery manifest, and the well-known URL answer **200**.
3. Every delivered response carries `tx` **and** `payer`.
4. Non-2xx rows carry a `why` — a 503 with an empty reason cannot be diagnosed after the fact.
5. Only then read the index's demand numbers, and attribute them against a known-wallets list before calling any
   of them a customer.
