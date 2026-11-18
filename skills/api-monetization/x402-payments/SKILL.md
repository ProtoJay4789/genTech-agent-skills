---
name: x402-payments
description: "How to build x402 payment-gated APIs for AI agents. Covers facilitators (GoPlausible, Naven, CDP), settlement flows, session management, and multi-chain payment rails."
---

# x402 Payments for AI Agents

x402 is the HTTP-native payment standard. When an agent hits an endpoint without payment, the server returns `402 Payment Required` with a challenge. The agent signs the payment and retries. The server verifies and serves the resource.

## Payment Flow

```
Agent                    Server                   Facilitator
  │                        │                          │
  ├── GET /api/data ──────►│                          │
  │◄── 402 Payment ───────┤                          │
  │     Required           │                          │
  │                        │                          │
  ├── POST /facilitator/verify ──────────────────────►│
  │◄── Verified + Receipt ───────────────────────────┤
  │                        │                          │
  ├── GET /api/data ──────►│                          │
  │     (x402 header)      │                          │
  │◄── 200 OK + Data ─────┤                          │
```

## Supported Networks

| Network | Facilitator | Token | Chain ID |
|---------|-------------|-------|----------|
| Algorand | GoPlausible | ALGO | algorand:localnet |
| Robinhood Chain | Naven Network | USDG | `eip155:4663` |
| Base | CDP Facilitator | USDC | `eip155:8453` |

## GenTech Kit Tools

```python
from gentech_agent_kit.plugins.algorand_x402 import register_gentech_plugin
from gentech_agent_kit.plugins.robinhood_x402 import register_gentech_plugin
```

Tools auto-discovered. No manual config needed.

## Session Management

Payments open a 60-minute session. Session token (HMAC-signed) is passed on subsequent calls:

```python
session = algorand_verify_payment(payment_proof)
# session_token = "agent_1234567890_abc123:1712345678:signature"
data = algorand_get_quote("BTC", session_token=session_token)
```

## Pricing Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| Exact | Fixed price per call | $0.001 USDG per quote |
| Tiered | Different prices for different data | $0.001 crypto, $0.005 stocks |
| Subscription | Batch pricing, session-based | 10 queries for $0.01 |

## Best Practices

- Always validate session tokens before serving paid data
- Return clear 402 errors with machine-readable challenge bodies
- Log all payment verifications for audit trails
- Use the Output Enforcer to validate paid response schemas

## Making a challenge actually payable

A 402 can carry the right header, a plausible body and a real price, and still be impossible for
any agent to pay. These four fail silently, each fix is one line, and each one alone is enough to
keep an endpoint unsold forever:

1. **Emit `amount`, not only `maxAmountRequired`.** `x402Version: 2` alongside only the v1 field
   name means a v2 client looks for `amount`, finds nothing, and cannot build a payment. Emit both
   while v1 clients still exist.
2. **`extensions.bazaar` must be present** (`bazaarResourceServerExtension: true` plus a
   `discoveryUrl`). Without it no bazaar can index the resource, however many calls settle.
3. **A facilitator takes ONE `paymentRequirements` object, not your `accepts` array** — select the
   entry whose `network` matches the signed payload. Strip v1-only keys from that object: a
   facilitator may reject requirements carrying both `amount` and `maxAmountRequired` even though
   its own schema lists both. Advertise both, verify with the v2 set only.
4. **The EIP-712 domain name must equal the token's on-chain `name()`.** Circle USDC on Base and
   Avalanche is `"USD Coin"` version `"2"` — `"USDC"` is the *symbol*, and advertising it makes
   the client sign for a different domain, so the token reverts `FiatTokenV2: invalid signature`
   and the facilitator reports `invalid_exact_evm_token_name_mismatch`. Read it from chain:
   `eth_call` `0x06fdde03` = `name()`, `0x54fd4d50` = `version()`.

5. **`accepts[0]` is the rail a blind client will ATTEMPT — order by buyer population, not by your
   preference.** Most clients try the first entry and, on failure, do not fall through politely: they either
   retry a *different paid route* or give up. Advertising an exotic rail first (a chain whose token contract
   your typical buyer's wallet does not hold, or whose EIP-712 domain differs from what the client assumes)
   converts a payable endpoint into a wall — while the endpoint looks perfectly healthy in the access log as a
   stream of `402`s. **Lead with the rail that has the most buyers; list the rest after it.**
6. **Declare `assetTransferMethod` explicitly on every exact-scheme entry.** Omitting it makes the client fall
   back to the spec default (`eip3009`) on a token that may only support `permit2` — a rejection that reads as a
   bad signature. Publish the method per entry and let the client choose, instead of letting a default decide.
7. **A partner who needs a single-rail challenge gets its OWN parameterised path, not a global reorder.**
   When one integration must only ever see one chain, pass a flag through the challenge builder (`okx=True` in a
   route alias, for example) rather than moving that chain to the front for everyone — otherwise satisfying one
   partner breaks every blind client.
8. **Carry every `uint256` in the signed payload as a STRING.** `authorization.value`, `validAfter`,
   `validBefore` are `uint256` in EIP-712 but **strings** in the exact-EVM payload JSON. Sign over the
   integers (EIP-712 hashes them numerically), then serialise them as strings. Sending `"value": 1000`
   produces a facilitator `400` whose message points at `paymentPayload/payload.<field>` and reads like a
   signature failure, so the natural next move — re-signing — is wasted effort. The split to remember:
   **integers to the signer, strings to the wire.**

**Diagnose a payment wall by behaviour, not by price.** Before concluding "too expensive" or "no demand",
classify what clients did after the `402`:

| behaviour | reading |
|---|---|
| never reached a paid route at all | catalogue/health probe — not a buyer |
| hit a `402`, then tried a **different paid route** | **they WANT to pay and cannot complete this one** — a rail/scheme defect, not a price problem |
| hit the `402` once and left | a genuine refusal, or a client with no wallet |

**Bisect, do not inspect.** When a facilitator rejects requirements, POST `/verify` yourself with a
captured payload and delete one field at a time until it passes — that separates an unknown-field
rejection from a wrong value. A structurally invalid request and an unpayable one produce the same
status code.

**Full field-level detail, including how to capture a real signed payload:**
`references/v2-challenge-correctness.md`.

## Bazaar indexing has no form — and it is keyed to what the CLIENT echoes

*Full tables, the second-ledger schema and the self-settle procedure: `references/listing-lifecycle-and-telemetry.md`.*

CDP's and PayAI's bazaars expose no registration form or endpoint — `/verify`, `/settle`,
`/supported`, `/pricing` and read-only `/discovery/*` is the whole surface. Read the facilitator's
`openapi.json` and look for a write endpoint **before** inventing a listing step; there isn't one.

A resource is catalogued from the **discovery declaration carried in the payment payload**, on `/verify`
**and** `/settle`. Three parties cooperate: your server declares it in the 402, the buyer's client copies
it into the payload (required v2 client behaviour), the facilitator upserts asynchronously.

Consequences that change the plan:

- **Cataloguing runs on `/verify`, which moves no funds** — a listing or refresh can cost **zero**. Try that
  before paying to fix a listing.
- **The registered identity is the resource the client echoed**, not the one you declared. If a row shows a
  dead templated path (`/v1/lp/:address`), a real payment will refresh `lastUpdated`/`quality` and still
  **never rewrite the URL** — fix the declaration, then refresh.
- **Delist is time-based** (commonly ~30 days with no settle). Age every row you care about from the
  catalogue's own `lastUpdated`, never from memory; a row with `0 calls` is already on the clock.
- **The catalogue's quality fields are free platform-side evidence of revenue** (`lastUpdated`, last-30-day
  calls, unique payers). They can confirm or contradict your own ledger — read them before reporting either.

So "we are not listed" means "no declaration reached that facilitator", not "we forgot to sign up".

### Your own forwarding code can drop the resource — check it before blaming the facilitator

The catalogue reads `paymentPayload.resource`, and **the resource is Optional in v2 §5.2.2**. Optional-for-
correctness and required-for-discovery are different requirements, and only the vendor's seller guide says so:
CDP states the settlement payload "must include `paymentPayload.resource` so CDP knows which resource to
catalog". Omitting it violates nothing, so nothing complains — the payment settles, the money moves, and the
catalogue stays empty. **A settlement that is real and unattributable.**

A server that rebuilds the facilitator envelope is where the field goes missing:

```python
payload = {"x402Version": v, "paymentPayload": pp, "paymentRequirements": accepted}   # drops `resource`
```

**Audit every settlement builder, not the obvious one.** One gateway may hold several — a per-facilitator
function each (CDP, Dexter, GoPlausible) plus a generic one for the rest — and they are usually *copies of the
same envelope*. Count the builders before you count the fix. Attach the field with `setdefault` from the
**request being served**, never from the caller's payload, so a settlement can never be attributed to a route
that was not called; and put it behind **one shared helper**, because four hand-edits drift apart and a field
present on three paths and absent on the fourth is the same class of bug as a rail that is not CAIP-2 clean.

**Then find your rows before paging the catalogue.** Discovery totals run to tens of thousands, so paging to
the end to answer "are we listed?" is the wrong instrument:

```
GET <facilitator>/discovery/search?query=<your-brand>     # returns just your rows
GET <facilitator>/discovery/search?query=<route-word>     # what buyers would type
```

A `search` hit after a settling call, where a page-1 scan showed nothing, means the listing landed and the
paging scan was never evidence of absence.

⚠️ **Log the facilitator's error body whole enough to name the field.** A handler that truncates to 200 chars
turns `Error at "/paymentPayload/payload.authorization.value"` into `Error at "/paymentPayload/payloa` — the
truncation then *is* the bug that hides the bug, and every debugging step after it is a guess. Keep the
diagnostic body (800 chars holds a full vendor error with its correlation id and docs link) while keeping the
buyer-facing message short and safe.

⚠️ **A surface you forget to filter is not neutral.** Catalogues crawl `llms.txt` and
`openapi.json`; leaving unservable services in either makes a third party republish your
overstatement under your name. Apply the same servable predicate to *every* public surface
(discovery manifest, bazaar document, MCP tool list, registry metadata, `llms.txt`, `openapi.json`)
and publish the withheld set **with reasons** rather than deleting it silently.

## Zero sales is ambiguous — prove the door opens before blaming demand

**A 402 proves the server will QUOTE a price. It proves nothing about whether a valid proof is
ACCEPTED.** Both failures look identical in an access log: many 402s, zero paid-route 200s, zero
revenue. The ledger records status, never settlement, so it will show you 402s forever and never
mention that the buyer's proof was refused.

**Test with a real client before drawing any market conclusion** — one run, three paid routes (a
single route can fail for route-specific reasons), then read the response BODY's `reason`, not just
the status. `scripts/x402-paid-call.py <url> <keyfile>` does this; confirm the payer's balance is
unchanged afterwards so "we tested it" does not imply a spend.

| result | meaning |
|---|---|
| 200 + `PAYMENT-RESPONSE` with a settlement reference | path open — the demand question is now real |
| 402 with a body `reason` | **the door is shut**; quote the reason verbatim, it names the cause |
| 402 with no reason | a challenge, not a rejection — the client is probably not signing |

### The trap that shuts the door silently

A verify-mode switch that falls back to a dev verifier when production credentials are missing turns
"we are not configured" into "we take no money", and the resulting 402 looks exactly like a normal
challenge-to-payment flow.

```
mode = env(PAYMENT_VERIFY_MODE, default="auto")
auto:  production verifier if its key exists, else → local HMAC simulation verifier
```

If the simulation verifier also fails closed when its HMAC secret is unset (the right call — an unset
secret must never validate forged proofs), then **no production key + no secret = every buyer
refused**. Correct engineering, catastrophic merchandising. Assert the production credentials exist in
the RUNNING process, not in a config file someone meant to load:

```bash
docker exec <gateway-container> env | grep -c <PROVIDER>_    # expect >= 1, not 0
```

⚠️ **Do not satisfy a closed door by provisioning the simulation secret.** That makes the dev verifier
succeed, so calls are accepted with no settlement — the next revenue report then shows income that
never arrived. A simulated acceptance is worse than a refusal, because a refusal is honest. Fix by
provisioning the production verifier, or pin `PAYMENT_VERIFY_MODE` to it so the failure is *named*.

### Demand side of the same log

An "unclassified callers" bucket cannot be sold to, disqualified, or fixed. Classify by shape — **the
user-agent is a claim, path breadth is evidence**: a buyer reads one resource, a walker enumerates the
manifest. Only callers that actually reached a price challenge are evidence about demand; free-surface
browsers are a *positioning* question. Method and verdict set: the caller-classification reference
inside the `x402-api-compliance` skill.

## Verifying a payment actually landed

- **The access log proves traffic, never revenue.** A `402` is a refusal and a `200` may be a free route or a monitor — neither is evidence of a sale. The only proof is an inbound token transfer to `payTo` on-chain.
- **The chain proves *that* you were paid and by whom; it does not name the endpoint that earned it.** A transfer carries no service identifier, so report *"a payment landed"* and *"this endpoint earned it"* as two separate claims, and say which one you can support.
- **The client sends its proof in `PAYMENT-SIGNATURE`** (the legacy `X-Payment` alias is accepted, but buyer-facing docs must teach `PAYMENT-SIGNATURE` — publishing the legacy name teaches the wrong header). **`PAYMENT-RESPONSE` belongs on a failed settlement refusal too**, per the spec's *"whether successful or failed"*; make such a change additive only, so a receipt header can never break a refusal.
- **Prove one settlement yourself when you have no buyers:** cap the spend in the client (per-call ceiling + a
  single preferred rail, registered before signing), pay one cheap call on your own endpoint, and keep the
  `PAYMENT-RESPONSE` — it carries `transaction`, `network`, `payer` and `success`, which is chain-side
  reconciliation **without an indexer**. Confirm the tx receipt on chain before believing it.
- **An SDK that returns a response OBJECT makes `.get()` return `None` without raising** — real settlements then
  report as `settled: false`, and a suite that only asserts status codes passes straight through it. Normalise
  (`dict(vars(obj))`) before reading any field, and read headers through a case-folded map (they arrive lowercase).
- **Full procedure** — recipient-filtered `eth_getLogs`, block-range caps and re-splitting, separating the payer from a bundler/executor (Multicall3 `aggregate3`), the repeat-payer check, and the headers that make a request-to-payment join possible: see `references/onchain-payment-attribution.md`.
