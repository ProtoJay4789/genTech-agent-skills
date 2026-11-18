# CDP Bazaar / x402 Bazaar — how indexing actually works, and how to check it

**Use this when a service serves `402` correctly but no one finds it, or when a directory's record of you
is wrong.** Serves also when deciding *where to invest listing effort* — the mechanics decide which
surfaces a settle actually reaches.

---

## The mechanism: indexing is PER-FACILITATOR, not global

**A directory lists you because a payment settled THROUGH ITS OWN facilitator, not because your endpoint
is good.** From CDP's docs, verbatim: *"After the facilitator settles a payment for an endpoint that
advertises Bazaar metadata, it indexes the endpoint so buyers and agents can find it."* And from the x402
FAQ: *"Catalog indexing is a facilitator implementation detail, not something the x402 OSS repo controls."*

**Consequences that cost us days:**

- **Settling through one facilitator does NOT list you in another's catalogue.** Ours settled through
  PayAI → catalogued by PayAI. CDP's Bazaar — roughly 4× larger — knew nothing about it.
- **Facilitators with similar names are different operators with different catalogues.** Read the hostname,
  never the brand: a marketplace at `payapi.market` and a facilitator at `facilitator.payai.network` are
  unrelated, and treating them as one thing produced a confident wrong conclusion in both directions.
- **To be in N catalogues you must settle through N facilitators.** Budget one cheap settle per endpoint
  per catalogue — at CDP that is free for the first 1,000 on-chain facilitator transactions per month.
- **One indexing can fan out to several channels.** CDP's alone feeds CDP APIs, the Bazaar MCP server,
  Amazon Bedrock AgentCore, and agentic.market. **Price the fan-out before deciding which catalogue to
  chase** — the cheapest one to reach may not be the smallest.

## ⚠️ 30-day delist — a listing is a habit, not an achievement

**Resources that go 30 days without a settlement are removed from the catalogue and from search.** So an
endpoint that worked, was indexed, and then stopped receiving paid calls silently disappears. Check the
listing's `lastUpdated` / last-settlement date whenever you audit placements, and treat "listed" as a
state that needs traffic to persist.

## Checking whether YOU are indexed — get the lookup right

```bash
# ✅ THE WORKING LOOKUP — merchant by payTo
curl -s 'https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo=0xYourPayTo' \
  | python3 -m json.tool      # -> items[], pagination.total

# ❌ THIS FILTER IS SILENTLY IGNORED — it returns page 1 of the whole catalogue
curl -s 'https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?payTo=0xYourPayTo'
```

**⚠️ A filter that is ignored returns a plausible page, which reads as a real answer.** The control that
proves it: **filter by a payTo you can SEE in page 1** — if the result contains many different payTos, the
filter does nothing.

**Before concluding "we are absent" from a paged walk, verify the ordering is meaningful.** If the
catalogue is recency-ordered, absence near the top is evidence; if it is not, absence proves nothing.
Check the date range of the first page against the most recent date you expect to see.

**The counterpart check — the facilitator's own discovery layer** — does honour `payTo`:
`GET {facilitator_url}/discovery/resources?payTo=…` returns exactly that merchant's listings.

### Read the per-resource `quality` block before claiming "no traction"

**Each catalogued row carries its own evidence of use:** `lastUpdated`, plus
`quality: {l30DaysTotalCalls, l30DaysUniquePayers, lastCalledAt}`. That is a **platform-side** count of payers,
independent of your own logs — so when a local ledger is missing or lacks a payment field, **this is the number
to quote**, and it is the one number a disagreeing party can check for themselves.

- **`l30DaysUniquePayers > 0` is revenue; `calls` alone is not** — a monitor's probes land in the same counter.
- **A row whose `lastUpdated` is 30+ days stale has already passed its refresh line**, so treat it as a
  pending delist rather than a live listing.

## Doing the settle that indexes you — the working recipe

**Settling through the target facilitator IS the whole lever, and it is a script, not a form.** The
procedure that took a catalogue from a 4-service subset to all 14, in one pass:

1. **Get the credential CLASS the flow actually needs, and confirm it before a secret moves.** The
   facilitator authenticates with its **API key ID + secret pair**. It does **not** use a wallet secret —
   that provisions a provider-managed wallet, which a self-custody payer does not need. Asking for the
   wrong class costs a needless exposure; see `secret-handling-in-chat`.
2. **Read the keys inside the script from mode-600 files and set them as env in-process**
   (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` are read from the environment by the SDK). **Never interpolate
   a secret into a shell command line** — the command string lands in the transcript.
3. **Authenticate with the vendor's own client, not hand-rolled HTTP.**
   `createCdpFacilitatorClient()` from `@coinbase/cdp-sdk/x402` exposes **`getSupported` · `verify` ·
   `settle` · `createAuthHeaders`**. The auth headers are the part you cannot write by hand — and the raw
   endpoints `401` without them, **including `GET /supported`**.
4. **Sign with your OWN funded payer.** Build the payload with `x402Client` from `@x402/core/client` plus
   `ExactEvmScheme(signer)` and the private key of a wallet you control. A facilitator will not pay you.
5. **Verify first, then settle.** `client.verify(payload, requirements)` moves no funds and proves the
   payload is acceptable; only then `client.settle(payload, requirements)`.
6. **Gate the money behind an explicit flag, and default to a dry run** that signs and verifies only.
   Pace one on-chain transaction at a time — it keeps the run readable and avoids nonce races.

The client's method signatures take `(payload, requirements)`; if that shape errors, the v2 HTTP form
`({x402Version, paymentPayload, paymentRequirements})` is the fallback to try before assuming a bug.

### The signal that proves acceptance — and its ABSENCE is the diagnosis

**A Bazaar-supporting facilitator echoes this header on the settle:**

```
EXTENSION-RESPONSES: {"bazaar":{"status":"processing"}}
```

`"processing"` means *the discovery info was accepted and is being catalogued asynchronously*. **A
facilitator that does not support the extension returns no such header — which is exactly why the same
correct manifest, settled through a different facilitator, produced no listing at all: the metadata was
never ingested.** Read this header on the FIRST settle; treat its absence as the explanation, not a mystery.

- **Count the change the same day by the merchant lookup** — before/after is one unauthenticated call.
  Measured: the lookup went **4 → 15** for 14 settled routes, because parameterised variants collapse
  differently than you expect. **Report what the lookup returns, not what you settled.**
- **Cataloguing is ASYNCHRONOUS: `processing` is acceptance, not publication.** A lookup that has not
  moved yet is not a failure — re-measure later rather than re-settling.
- **A settle count is not an index count.** Print both; read presence off the lookup.

## What the catalogue actually records: the declaration the CLIENT echoes

**The facilitator does not read your 402. It reads the copy the buyer's client sent back.** The indexing chain
has three parties, and the middle one is the one that quietly decides your identity:

1. **Your server declares** the resource in the 402 (bazaar extension: `info`, `input`, `schema`).
2. **The buyer's client echoes** that declaration into the payment payload — required client behaviour in v2.
3. **The facilitator catalogues** on `/verify` and `/settle`, upserting from the **echoed** copy.

**Consequences worth building around:**

- **A client that drops or rewrites `extensions` registers nothing, no matter how many payments settle.**
  The facilitator never saw a declaration, so a successful settle produces no listing at all. Check the
  client before blaming the catalogue.
- **A declaration that names parameters but publishes no route template gives an echoing catalogue nothing to
  resolve**, so it stores a templated identity (`…/defi/lp/:address`) that no client can call. Publish the
  **concrete** resource URL *and* an explicit RFC 6570 `routeTemplate`, and make sure `input.pathParams` is
  populated — an empty `pathParams` on a service with a path parameter is the tell.
- **`pathParams` can be empty for a mundane reason:** if the manifest stores a *concrete example* endpoint
  (`/v1/defi/lp/0x7ebf…`) an extractor that looks for `{braces}` finds none. Derive names from the template,
  not from the manifest string, and never synthesise a template from a loose regex — a `symbol` pattern that
  matches any word will parameterise routes that take no parameter at all.

### ⚠️ `paymentPayload.resource` — the field the catalogue actually keys on, and the one a correct 402 omits

**A 402 that declares `resource` at the TOP LEVEL of the body is not enough. The catalogue reads
`resource` INSIDE `paymentPayload`** — CDP's own wording: *"The payment payload sent to the facilitator must
include `paymentPayload.resource` so CDP knows which resource to catalog."* The SDK type agrees; a v2
payment payload carries `[x402_version, payload, accepted, resource, extensions]`.

**So there is a whole failure mode where everything visible is correct and nothing is ever listed:**
correct manifest, `extensions.bazaar` valid, top-level `resource.url` served, six rails CAIP-2 clean,
settlements succeeding through the right facilitator — and the envelope we build for `/verify` and `/settle`
is `{x402Version, paymentPayload, paymentRequirements}` with the resource URL **nowhere inside
`paymentPayload`**. The money moves (settlement never needed the field) and the listing never appears.

**Grep the settle path for the field before theorising.** In our gateway the string `resource` appeared
**zero times** across the entire CDP verify/settle function. One grep settles a question that otherwise costs
a week of catalogue archaeology:

```bash
awk '/def verify_proof_via_cdp/,/^def /' server.py | grep -n 'resource'   # zero hits = this bug
```

**The fix belongs on EVERY facilitator path, not just CDP.** PayAI, Naven and GoPlausible take the same v2
envelope, so a field present on one builder and absent on another is the same class of defect as rails that
are not all CAIP-2 clean. Set it from the request being served — never invent it — so a settlement can never
be attributed to a route that was not called:

```python
_pp = dict(_pp); _pp.setdefault("resource", str(request.url))
```

### Prove our OWN payload before filing a ticket against the catalogue

**A ticket is only worth filing after we can show our request was well-formed** — otherwise it is a guess
with a support cost, and being wrong in a vendor's tracker permanently cheapens the next report.

**Validate against the SDK that defines the type, not against prose.** The installed `x402` package ships the
models, and `DiscoveryExtension` is a **`typing.Union`** — so `DiscoveryExtension.model_validate(...)` raises
`AttributeError` (`'typing.Union' object has no attribute 'model_validate'`). Iterate the variants instead:

```python
import typing
from x402.extensions.bazaar.types import DiscoveryExtension
for cls in typing.get_args(DiscoveryExtension):   # Query / Body / Mcp
    try: cls.model_validate(ext); print("valid as", cls.__name__); break
    except Exception as e: print(cls.__name__, str(e)[:120])
```

That call converts "our declaration looks right" into a pass/fail with a class name. **Three checks, then
the ticket** — and only in this order:

1. **Declaration valid** against the SDK type (above).
2. **Settlement went through the catalogue's OWN facilitator** (`EXTENSION-RESPONSES` seen, or the merchant
   lookup moved).
3. **The payload carried `resource`** (the grep above).

If any of the three fails, it is our bug and the ticket would be dismissed — correctly. If all three pass and
the catalogue is empty after the documented window, that is the evidence that makes a report actionable.

- **Note where the package actually lives before concluding the SDK is missing.** A `pip show x402`
  `Location:` under a profile's `home/.local/lib/...` is invisible to a bare `python3 -c "import x402"` run by
  a different interpreter; set `PYTHONPATH` to that `Location` rather than concluding the library is absent.
- **Do not report a catalogue as absent from a paged walk.** Query the merchant/payTo lookup for our own
  identifier first (see the lookup section above), state `pagination.total` beside the number scanned, and
  report **UNKNOWN** rather than "not indexed" when the bound is not the whole set.

## Refreshing a listing: verify may be enough, a settle always is

**Check the facilitator's own docs before budgeting settles.** PayAI's Bazaar documentation states that
cataloging runs on **`/verify` as well as `/settle`** because verification moves no funds — so **a listing can
be created or refreshed for $0**, and only a *first* listing of a `POST`/MCP resource or one with no declared
method is deferred until a settled payment (`resource_needs_settlement`).

- **Treat "settle monthly per route per catalogue" as the safe upper bound, not the minimum.** Where `/verify`
  catalogues, refresh by verification and keep the settle for the case that actually needs funds to move.
- **A verification-only refresh does not create a payment receipt.** If you also want the on-chain proof of
  sale, that still costs a settle — decide which of the two you are buying before you spend.
- **A settle refreshes `lastUpdated` and quality counters, but does not rewrite the resource string.** Paying a
  templated row keeps it off the delist line and leaves the identity as it was: **refresh and repair are two
different jobs**, and only the declaring side can repair.

### The 30-day clock makes this a RECURRING job, not a one-off

Because a resource is delisted after 30 days without a settle or a verify that catalogues, the refresh is a
**monthly obligation per route per catalogue**. Put it on a schedule with a durable record of the last refresh
per route, and let a separate presence check alarm when an entry drops — a refresh that is not repeated is a
listing that expires.

## The presence check that belongs beside it

**Six surfaces, and every one reads WITHOUT credentials** — measured, not assumed. That is a design
constraint worth copying: **a monitor that needs a secret to check on itself dies the day the secret
rotates.** Verify keyless readability first; it decides whether the check can be a plain script.

```bash
# all unauthenticated — probe each before building on it
https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo=<payTo>&limit=50   # CDP Bazaar
https://facilitator.payai.network/discovery/resources?payTo=<payTo>                       # PayAI Bazaar
https://x402-list.com/api/v1/services?q=<name>                                            # x402-list
https://payapi.market/api/agent/search?q=<name>                                           # payapi.market
https://<our-host>/.well-known/x402-bazaar                                                # our manifest
https://<our-host>/mcp   (POST tools/list)                                                # our MCP tools
```

**Design rules, each one earned the hard way:**

- **Diff against a STORED BASELINE; do not restate state.** A drop is the alarm ("was listed, now is
  not"); a gain is news that becomes the new baseline. A monitor that prints "15 entries" every day
  trains its reader to skim — and then the day it says 9 goes unread.
- **Silence is the DEFAULT, not an opt-in flag.** The cron contract is `0 + empty stdout` = silent tick.
  Writing `--quiet` as an opt-in inverts it: the no-change run prints a summary, so a normal run looks
  like output. Make the verbose case the flag (`--verbose`) instead.
- **A blind check is not a clean one.** If a required surface cannot be read, exit `2` and say so — never
  fall through to a quiet tick. (Fleet cron contract: `0` clean-or-findings · `2` cannot-read · never `1`.)
- **A directory with no record of you is a GAP, not a DROP.** Classify first-sighting separately, or the
  first run emits a fake alarm and the baseline never settles.
- **Store the baseline somewhere YOU can write.** The gateway container runs as **root**, so
  `10-Labs/x402-gateway/logs/` is root-owned: *reading* the ledger there works (world-readable), *writing*
  raises `PermissionError` under uid 10000. Keep our own state under `profiles/<seat>/state/`.
- **Mark surfaces `required` vs not.** `payapi.market` being absent is a known state, not a failure; the
  same absence on CDP is a five-alarm. Encode the difference or the check cries wolf.

## Metadata rules that decide whether you are indexed at all

- **A declaration that is valid is not the same as one that passes screening.** The catalogue screens
  every resource for **prompt-injection risk** — text that could *instruct* an agent rather than describe
  the endpoint. Marketing copy with imperatives in it can be read that way. Describe what the endpoint does
  and when to call it; do not address the agent.
- **Description length is enforced at `verify`/`settle`** (a limit around 500 characters) — an over-long
  description makes the *payment* fail, not just the listing.
- **Rich input/output schemas with realistic examples raise ranking** and are what let an agent construct a
  valid call without guessing. A bare declaration is enough to be *listed*; it is not enough to be *called*.
- **Ranking is usage-weighted over a rolling window and recomputed on a schedule** — a fresh settle does not
  move your position immediately, so do not conclude failure from an unchanged rank.
- **High-cardinality path segments are normalised.** A bare identifier (wallet address, tx hash, UUID) in a
  path collapses to ONE templated entry, so `/x/0xabc…` and `/x/0x123…` are one listing, not two.
- **MCP tools are a first-class listing type** with their own identifier tuple (resource + tool name) — a
  distinct surface worth listing separately from the HTTP endpoints, and much less crowded.
- **The catalogue keeps only a WHITELIST of your metadata; everything else is dropped SILENTLY.** The
  official Bazaar client sanitises each resource down to **`serviceName`, `tags`, `iconUrl`** — and nothing
  else. Any custom key you add to the resource block (a status, a change notice, a capability flag) is
  discarded before the catalogue sees it, with no error and no log line. **Before designing a feature that
  rides on the manifest or the 402 payload, confirm the field survives the client's sanitiser** — and if it
  must be seen, serve it on a route you own rather than smuggling it through metadata.

## The response contract the buyer is owed

**v2 headers are a triple, and the spelling matters:** `PAYMENT-REQUIRED` (server→client, base64 JSON),
`PAYMENT-SIGNATURE` (client→server), `PAYMENT-RESPONSE` (server→client). Read the inbound header
case-insensitively and keep the legacy name as a fallback — a client sending the current spelling must
never be refused because we only taught the old one. **Publish the current spelling in your own docs and
examples too:** a buyer-facing quickstart showing the legacy header teaches every integrator to fail.

**The spec requires the settlement receipt on FAILURE as well as success** — verbatim, *returned by the
server after attempting settlement, whether successful or failed*. Emitting it only on success leaves a
buyer who *did* attempt payment unable to tell *"you did not pay"* from *"we could not settle"* — which is
exactly the case they will be debugging.

- **Distinguish "not attempted" from "attempted and failed".** A rejected proof is not a failed settlement;
  if nothing was attempted, a receipt would be a lie. Gate the header on *an attempt having occurred*.
- **Make any receipt or telemetry ADDITIVE-ONLY.** It may add a header; it may never change a status code, a
  body, or a settlement decision — and its own encode failure must be swallowed rather than allowed to abort
  the refusal it decorates. Prove it in the direction it must NOT fire, not only the one where it should.
- **A `200` is not a sale.** Read `accepts[0].amount` (a string, /1e6) for the price, and confirm a real
  payer rather than a self-payment before calling anything revenue.
- **Decode the receipt from the actual SDK object, not a dict.** The reference Python client returns a
  `SettleResponse` **object**; calling `.get("transaction")` on it returns `None` **without raising**, so a
  real settlement reports as `settled: false` and the tx hash is silently dropped. Normalise to a dict
  (`vars(obj)`) before reading any field, and read the header **case-folded** (`payment-response` arrives
  lowercase) — a case-sensitive lookup misses the receipt entirely.
- **Verify the receipt's `transaction` on chain before believing the counter.** A receipt is a claim made by
  the facilitator you already trust; `eth_getTransactionReceipt` on a public RPC is the check that costs
  nothing and settles the question. This also makes an indexer unnecessary for chain-side reconciliation:
  the receipt carries the hash, so a funded payer wallet plus one paid call is a complete proof of sale.
- **A published health/status field must separate "down" from "could not measure".** A probe that throws is
  not a service that failed — reporting the exception as `down` publishes a false outage for live endpoints.

## Correcting a listing that is wrong

**A directory's record of you is either MEASURED or DECLARATIVE, and only the declarative half is
editable.** Measured fields (uptime, status, pricing, payTo, network set) cannot be submitted — they come
from the directory's own probes and change only when their measurement changes.

- **Before planning an update, check whether the field you want to fix is measured.** Submitting against a
  measured field is impossible; the real fix is waiting for their probe to see the corrected endpoint.
- **Where an owner-update flow exists, it is usually a two-step with a proof-of-ownership fetch:** POST an
  update request → receive a one-shot token → **serve that token at a path on the domain your listing
t declares** → POST verify-ownership. Plan the *serving* step before you start: the token must be reachable
  from the listed origin, which may mean a route that only exists after a restart.
- **Verify a listing exists before "updating" it.** Query by both id and slug. **A 404 on the API is
  authoritative; a `200` on the human-facing page is not** — single-page apps serve a byte-identical
  catch-all for every slug, including deliberately-garbage ones. **Control it:** request a known-bad slug
  and compare bytes; identical means you proved nothing.
