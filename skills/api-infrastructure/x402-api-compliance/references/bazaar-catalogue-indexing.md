# Bazaar catalogue indexing — why a working API is still invisible to buyers

A paid endpoint can return a perfect 402, settle real money, and still be absent from every catalogue an
agent searches. The protocol is satisfied; the *discovery* layer is not. These are different requirements.

## The gate, quoted

> *"There is no separate registration step. The CDP Facilitator catalogs your service the first time it
> **settles** a payment for that endpoint… The payment payload sent to the facilitator must include
> `paymentPayload.resource` so CDP knows which resource to catalog."*

Two consequences that decide whether listing ever happens:

1. **`verify` alone is not enough — settlement must complete.** A simulated or failed verify indexes nothing.
2. **The settle payload must name the resource.** Not the 402 body. The `paymentPayload` sent to the
   facilitator.

## `resource` is Optional in the spec and mandatory in practice

x402 v2 lists `resource` as **Optional** in `PaymentPayload`. So omitting it is not a spec violation — no
validator errors, no warning, nothing to notice. It is a *discovery* failure only.

> **Rule: when a field is Optional in the spec but the vendor's success path depends on it, the vendor's
> seller guide outranks the spec — and neither replaces reading what you actually send.**

The `resource` value is a ResourceInfo object; the SDK's own type signature is the shape check:

```
ResourceInfo(url, description, mime_type, service_name, tags, icon_url)
```

Minimum viable: `{"url": <absolute URL>, "description": ..., "mimeType": "application/json"}`.

## Attach it in ONE helper, called by EVERY settlement builder

An API with several rails has several builders — one per facilitator (CDP, PayAI, Dexter, plausable-style
routers, a generic fallback). Each constructs the same envelope. If the field is added to one path and not
the others, the rails that need it most may be exactly the ones missing it.

```python
def _with_resource(pp: dict, request_url: str | None) -> dict:
    if not request_url:
        return pp                 # degrade safely — never invent a URL
    out = dict(pp)
    out.setdefault("resource", {"url": request_url,
                                "description": "<service> resource",
                                "mimeType": "application/json"})
    return out
```

Three properties, each load-bearing:

- **`setdefault`, never assignment** — a caller that already supplied `resource` must not be overwritten.
- **URL from the request being served, never from the caller's payload** — otherwise a settlement can be
  attributed to a route that was not called.
- **No URL → return unchanged** — an absent URL is a reason to say nothing, not to guess.

Grep the count, not the presence: `grep -c '_with_resource(' server.py` must equal the number of builders
(definition + one call per builder), not 1.

## uint256 fields are STRINGS on the wire

The exact-EVM scheme carries `value`, `validAfter`, `validBefore` as **strings** in the JSON payload, while
the EIP-712 signature is computed over **integers**.

| sent as | result |
|---|---|
| `"value": 1000` (number) | `400 request body has an error at /paymentPayload/payload` |
| `"value": "1000"` (string) | accepted, settles |

**Sign over ints, transmit as strings.** If a hand-built client is rejected with a `/paymentPayload/payload`
error, check field types before suspecting the signature — the message names the section, not the field.

## Return enough of the facilitator's error to be usable

Client code that returns `resp.text[:200]` truncates precisely where the facilitator names the offending
field. Widen it (800 chars is enough for correlationId + errorLink + errorMessage).

> **A truncated error message is a bug that hides a bug.** Cost of leaving it: a debugging session and a
> support ticket, per occurrence.

## Diagnosing "are we actually listed?"

CDP exposes an MCP discovery server at `…/x402/discovery/mcp` (POST, JSON-RPC). It has three tools:
`search_resources`, `proxy_tool_call`, and — the useful one — `validate_endpoint`.

`validate_endpoint({"url": <route>, "method": "GET"})` returns, in one call:

```
active · indexed · hasBazaarExtension · lastCrawledAt · reachable · returns402
simulate: {"outcome": "accepted"}  ·  preflight: ~25 named checks, each passed/failed
```

**`indexed` and `simulate` are the vendor's own verdict — quote them instead of inferring from search.**

Preflight checks worth expecting to fail at first:

- `bazaar.info.output.example` — an output example. Do **not** invent one to satisfy it; capture a real 200
  body and serve that (see `published-response-examples.md`).
- `bazaar.info.input` / route template — a parametrised route with no published template stores as a
  templated row and cannot be called without guessing.

## Reading search results correctly

- REST `discovery/search?query=<brand>` and `discovery/resources?limit=&offset=` need **no API key**.
- `resources` is paginated over tens of thousands of rows: **you will not be on page 1.** Absence from page 1
  is not delisting. Query by name or by `payTo`, or you will report a false negative.
- MCP `search_resources` can return **0** for a resource that REST search returns many rows for — same
  catalogue, different ranking/filter. **Do not conclude delisting from one surface.**

## The exact query contract — the filter param is `pay_to`, and the wrong spelling fails silently

Saying "query by payTo" is not enough to reproduce the query. The parameter is **snake_case on a different
endpoint**, and getting either wrong returns a full default page that reads as "none of yours are listed."

| intent | correct | reads as a real answer when wrong |
|---|---|---|
| search | `GET {facilitator}/discovery/search?query=<q>&pay_to=<0x…>&network=eip155:8453` | `?payTo=` (camelCase) → **ignored**, default page returned |
| browse | `GET {facilitator}/discovery/resources?limit=&offset=` | querying `search` with no `query` |
| envelope | `search` → `resources[]` | `resources` → `items[]` |

**Two independent ways to get a confident zero from a healthy catalogue:**

1. **camelCase `payTo` is silently dropped.** Measured: the filtered call returned **50 generic rows from other
   sellers** — enough volume that it looked like a working query with no matches. Use the brand name as the
   control first (`?query=<brand>`), and only trust a filtered zero after an unfiltered query has shown you
   rows you recognise.
2. **The two endpoints disagree on the envelope key.** `discovery/search` returns **`resources[]`**;
   `discovery/resources` returns **`items[]`**. Parse one as the other and `len()` is `0` while the data is
   right there — a zero produced by the reader, not the catalogue. Assert both keys and print which one carried
   the rows.

Also read the envelope's own verdicts rather than inferring them: **`partialResults: false`** is the endpoint
stating the set is complete, `searchMethod` names the ranking, and `meta.searchToken` continues it. Quote
`partialResults` in the finding — "11 resources, complete set" is a claim the API made, not one you estimated.

## The demand telemetry is already there — `quality`, per resource

Every returned resource carries a **`quality`** object:

```json
{ "l30DaysTotalCalls": 18, "l30DaysUniquePayers": 5, "lastCalledAt": "2026-11-16T08:10:35.44Z" }
```

- **This is the facilitator counting payers per endpoint** — third-party demand evidence that costs nothing and
  refreshes on its own. Sum it across resources for a 30-day picture (measured: 43 calls over 11 resources).
- **`lastCalledAt` doubles as proof that indexing followed a payment.** If it equals the settlement timestamp of
  a known paid call, the catalogue learned about the resource *because* someone paid — which is the mechanism
  this whole file describes, observed rather than assumed.
- **`l30DaysUniquePayers` is a count of ADDRESSES, not of customers.** Our own settle-test and media wallets pay
  too. Attribute every address against the wallet registry before any of this becomes a customer number — an
  un-attributed unique-payer count is the easiest way to invent customers we do not have.

### …and the catalogue will never tell you WHO — record the payer yourself

The count is the whole gift; there is no per-resource endpoint that returns the addresses (the plausible
paths answer `404` or `401`). **The address is already inside the proof you receive**: the exact-EVM scheme
carries an EIP-3009 authorization whose `from` is the payer.

- **Read it in one helper, called where the verdict is stamped**, and record it as its own log field beside
  the tx hash. Do not reconstruct it later from the chain — by then the row and the payment can no longer be
  joined without an indexer.
- **Handle both wire shapes**: raw JSON (`Authorization: x402`) and base64 JSON (`PAYMENT-SIGNATURE` v2).
  One decoder that tries JSON then base64 covers both; an `except` that returns nothing is correct behaviour,
  not a bug.
- **Normalise to lowercase.** An address compared byte-wise across two sources is exactly how a "5 unique
  payers" count silently becomes 6.
- **Never default it.** No address found → `null` in the log. A default would launder our own probes into
  customers, which is the one error this field exists to prevent.
- **If the log's own header says it records "NO address", find out WHY before breaking it.** That rule is
  usually protecting signatures, and it over-corrects: it also makes the payer unknowable. Store the PUBLIC
  payer address (already public on chain, in the same payment the facilitator settles), keep zero
  signature / nonce / payload bytes, and **rewrite the comment to say the rule changed and why** — otherwise
  the next reader enforces a rule the code no longer follows.
- **It is forward-looking only.** Rows written before the field existed cannot be attributed retroactively
  from your log; only the chain can settle who those payers were. Say that plainly rather than implying the
  new field can reach backwards.

## Staying listed: the 30-day window

> *"All endpoints apply a recency filter. Resources that have been called at least once but have had no
> activity in the last 30 days are excluded from results."*

A quiet month silently removes a listing. **Silence looks identical to health** — so a presence check must
compare against a stored baseline and speak when a surface *drops*, not only when it is absent.

## Before blaming the vendor

There are public reports of settlements that carried a correct declaration, returned
`bazaar.status: "processing"`, and never appeared. That is real — and it is also the most convenient excuse
available, because it lets a missing field go unfixed.

**Order of operations: read the payload you send, field by field, against the vendor's type definition. Only
then file a ticket — and only with a resource-specific reproduction (your endpoint, facilitator, payTo,
settlement tx, and the query that returns empty).** A ticket filed before that check gets dismissed, and
correctly.
