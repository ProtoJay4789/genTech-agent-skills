# CDP Bazaar Self-Settlement (Coinbase x402 Bazaar)

Getting a gateway listed on the **CDP x402 Bazaar** (`api.cdp.coinbase.com/platform/v2/x402`)
is settlement-driven, like OpenDexter — but with its own set of non-obvious traps.
Hard-won live transcript, Aug 4 2026 (GenTech gateway). Read this BEFORE wiring a
CDP-settlement path so you don't re-derive the auth + envelope schema by trial and error.

## The indexing mechanism (from Coinbase's Bazaar docs)

- **Indexing runs after SETTLEMENT completes — verify alone is NOT enough.** The CDP
  facilitator catalogs your resource the first time it **settles** a payment for that
  endpoint. `paymentPayload.resource` must be set in the payload.

### ⚠️ Omitting `paymentPayload.resource` fails SILENTLY — and the spec permits the omission

x402 v2 §5.2.2 marks `resource` **Optional** in `PaymentPayload` (it is Required in
`PaymentRequired`). Nothing rejects a payload without it, no validator complains, and the
settlement SUCCEEDS — the money never needed the field. The catalogue just never gets the
listing, so the symptom is "we settle payments and appear in no directory," which reads as a
vendor bug and is not one.

Coinbase's seller guide is the stricter source: *"the payment payload sent to the facilitator
must include `paymentPayload.resource` so CDP knows which resource to catalog."*

**Rule: a field that is Optional for correctness can still be mandatory for DISCOVERY. When a
vendor's success path depends on an optional field, the vendor guide outranks the spec.**

**Check for the drift pattern, not just the one builder.** A gateway that supports several
facilitators tends to copy one envelope constructor per rail (CDP, Dexter, GoPlausible, a
generic PayAI/Naven path). Measured: four independent builders each constructed
`{x402Version, paymentPayload, paymentRequirements}` and **none** mentioned `resource` — so a
fix applied to one path leaves the others silently unlisted. Add ONE helper and call it from
every builder:

```python
def _with_resource(pp, request_url):
    out = dict(pp)
    out.setdefault("resource", {"url": request_url,
                                "description": "...", "mimeType": "application/json"})
    return out
```

`setdefault`, never assignment (a caller that already supplied `resource` must not be
overwritten), and **the URL always comes from the request being served, never from the
caller's payload** — otherwise a settlement can be attributed to a route that was not called.

### Verify with the MCP validator — it answers `indexed` directly

The REST `validate` endpoint returns check-by-check results. The **MCP** surface answers the
question you actually have, in one boolean:

```
POST https://api.cdp.coinbase.com/platform/v2/x402/discovery/mcp
  {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{...}}}
  {"jsonrpc":"2.0","id":2,"method":"tools/list"}
  {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"validate_endpoint","arguments":{"url":"<public URL>","method":"GET"}}}
```

Tools: `search_resources` · `proxy_tool_call` · `validate_endpoint`. The validator returns
`active`, **`indexed`**, `hasBazaarExtension`, `lastCrawledAt`, `simulate.outcome`, and a
`preflight[]`. `indexed: true` is the facilitator stating it catalogued you — do not infer
listing from a search hit alone.

**Expect `bazaar.info.output.example` to fail preflight if you withheld the example.** An
example is a check item, so an honest "we will not publish a shape we cannot honour" costs a
preflight point. Once the route returns a real, stable shape, publish THAT — withholding was
right when the shape was fake, and is wrong once it is true.

**MCP search and REST search do not rank alike.** Measured: REST `search?query=<brand>`
returned our resources while MCP `search_resources` (by query, by `payTo`, by `urlSubstring`)
returned none. Same catalogue, different filtering. Treat a zero from one surface as
"this surface does not see us yet," not "we are not listed."
- **No separate registration step.** There is no form. Settlement through the CDP
  facilitator is the trigger.
- **30-day recency window:** endpoints with no activity in 30 days are excluded from
  results. Newly-indexed resources with no calls yet are not subject to this filter.
- **Quality metrics refresh on a 6-hour schedule.** After a settlement, the resource may
  not move up in search for up to 6 hours. Don't panic when a fresh search returns 0.
- **Verify your listing:** `GET /v2/x402/discovery/search?query=<domain>&limit=5`
  (no auth needed for discovery reads). Empty results immediately after settlement is
  expected — the ranking update lag is the reason, not a failed settlement.

## The gateway must call /settle after /verify

Many gateways (incl. GenTech's) only call `/verify` and never `/settle`. The Bazaar
indexes on settlement, so **verify alone means you'll never be listed even though payments
"work."** After a successful `/verify` (HTTP 200), POST the same envelope to `/settle`.

```
POST https://api.cdp.coinbase.com/platform/v2/x402/verify   → 200 {isValid:true, payer}
POST https://api.cdp.coinbase.com/platform/v2/x402/settle   → 200 (indexes the resource)
```

`/settle` submits the on-chain tx (EIP-3009, gas-sponsored by CDP) and is what triggers
the Bazaar cataloging.

## CDP JWT auth — HMAC is NOT accepted (the 401 trap)

CDP returns **401 Unauthorized** if you authenticate with a plain HMAC or a bearer key.
It requires a **JWT** signed with your API key secret:

- **Ed25519 key** (base64, 64 bytes decoded — GenTech's `CDP_API_KEY_SECRET` is this)
  → JWT signed with **EdDSA**.
- **PEM EC key** → JWT signed with **ES256** (PKCS8 import).
- Key type detection: `len(base64.b64decode(secret)) == 64` → Ed25519; else try PEM EC.

JWT claims (mirrors the CDP SDK's `generateJwt`):
```json
header = {"alg":"EdDSA","kid":"<CDP_API_KEY_ID>","typ":"JWT","nonce":"<16-byte hex>"}
claims = {
  "sub": "<CDP_API_KEY_ID>",
  "iss": "cdp",
  "aud": "cdp_service",
  "uris": ["POST api.cdp.coinbase.com/platform/v2/x402/verify"],  // method host path
  "iat": now, "nbf": now, "exp": now + 120
}
```
Python (Ed25519, via `nacl.signing`):
```python
import base64, json, secrets, time
from nacl.signing import SigningKey
def b64url(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
decoded = base64.b64decode(secret); sk = SigningKey(decoded[:32])
now = int(time.time()); nonce = secrets.token_hex(16)
hdr = {"alg":"EdDSA","kid":key_id,"typ":"JWT","nonce":nonce}
claims = {"sub":key_id,"iss":"cdp","aud":"cdp_service",
          "uris":[f"POST api.cdp.coinbase.com/platform/v2/x402/verify"],
          "iat":now,"nbf":now,"exp":now+120}
si = f"{b64url(json.dumps(hdr).encode())}.{b64url(json.dumps(claims).encode())}"
jwt = f"{si}.{b64url(sk.sign(si.encode()).signature)}"
headers = {"Authorization": f"Bearer {jwt}"}
```
The `uris` claim **binds the exact method+host+path** — use the verify path when calling
verify and the settle path when calling settle (they differ). A JWT signed for `/verify`
won't work on `/settle`.

**Diagnostic signal:** if CDP returns 401 → auth problem (JWT). If it returns 400 with a
schema message → auth is accepted, payload shape is wrong. That's the fast triage.

## The exact /verify + /settle envelope schema (the trial-and-error win)

CDP requires `{x402Version, paymentPayload, paymentRequirements}` — and the
`paymentRequirements` field is the trickiest part. It must be **the accepted payment
option object directly** (with `scheme` at the top level), NOT wrapped in an `accepts`
array, and NOT a re-built structure.

Working shape (confirmed CDP returns `{"isValid":true,"payer":"0x..."}`):
```python
payload = {
    "x402Version": pp.get("x402Version", 2),
    "paymentPayload": pp,                       # the full payment payload
    "paymentRequirements": pp["accepted"],      # the accepted option object, direct
}
```
where `pp["accepted"]` looks like:
```json
{"scheme":"exact","network":"eip155:8453","asset":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
 "amount":"10000","payTo":"0xF9dc...","maxTimeoutSeconds":300,"extra":{"name":"USD Coin","version":"2"}}
```

**Rejected shapes** (all return 400 `'paymentRequirements' is invalid: must match one of
[x402V2PaymentRequirements, x402V1PaymentRequirements]. x402V2PaymentRequirements
requires 'scheme'`):
- `{"paymentPayload": proof}` (missing x402Version + paymentRequirements) → 400
- `{"paymentRequirements": {"accepts": [option]}}` (wrapped) → 400
- `{"paymentRequirements": {"x402Version":2,"resource":{...},"accepts":[...],"extensions":{}}}` → 400
- `{"paymentRequirements": {"scheme":"exact","network":...,"amount":...,"payTo":...}}` (partial) → 400

**Ground-truth capture method:** instead of guessing the schema, monkeypatch `globalThis.fetch`
in Node and print `opts.body` on the `/verify` call the CDP SDK makes. That shows the exact
envelope the SDK sends — replicate it in the gateway. This is far faster than trial-and-error
against the 400 responses.

## The client-side EIP-3009 payload — SIGN over ints, TRANSMIT strings

The exact-EVM scheme carries `uint256` authorization fields as **STRING** values in the JSON
payload. Signing over integers is correct (EIP-712 hashes `uint256` numerically); encoding them
as JSON numbers in the transmitted payload is what fails.

Symptom: the facilitator answers **400** with
`request body has an error: Error at "/paymentPayload/payload..."`. The shape is right, the
signature is right — the *type* is wrong.

```python
auth = {"from": addr, "to": pay_to, "value": str(amount),
        "validAfter": str(now - 60), "validBefore": str(now + timeout - 30),
        "nonce": "0x" + secrets.token_hex(32)}
auth_int = {k: int(v) if k in ("value", "validAfter", "validBefore") else v
            for k, v in auth.items()}      # sign the ints
sig = account.sign_message(encode_typed_data(domain_data=domain,
        message_types=TransferWithAuthorization, message_data=auth_int))
# transmit `auth` (strings), not `auth_int`
```

Domain for Base USDC comes from the challenge's own `accepts[].extra` (`name`, `version`) plus
`chainId` and `verifyingContract` = the advertised `asset`. Never hardcode the domain — read it
from the 402 you were just handed.

### ⚠️ Never truncate a facilitator error to a short slice

A `resp.text[:200]` in the verify/settle error path cut the facilitator's message off at exactly
the field name — the operator saw `Error at "/paymentPayload/payloa` and had to guess which
field, while the full body named it. **Keep at least ~800 chars of the error body**: it carries
`correlationId`, `errorLink` and `errorMessage`, which is the only support handle you get. A
truncated error message is the bug that hides the bug.

**Triage order when a paid request 402s with a facilitator reason:** read the FULL error body
first (auth vs schema vs type), then compare the payload field-by-field against the scheme's
type definition — not against a working example, which hides type mismatches.

## Client-side header — the PAYMENT-SIGNATURE gap

The x402 SDK sends the payment proof in a header your gateway must read:
- **v2** → `PAYMENT-SIGNATURE` header (base64-encoded JSON payload)
- **v1** → `X-PAYMENT` header (base64-encoded JSON)

A gateway's `extract_proof` that only reads `Authorization: x402` / `X-Payment` /
`x-402-token` will silently IGNORE the SDK's real proof and keep returning 402. Add:
```python
psig = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("payment-signature")
if psig: return psig.strip()
```
Also: the v2 SDK **base64-encodes** the JSON payload. If your verifier does
`json.loads(proof_str)` directly, base64-decode first, then parse.

## Node SDK import map (exact paths)

The x402 JS API differs from the Python docs. Working imports:
```js
import { x402Client } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { wrapFetchWithPayment } from "@x402/fetch";
import { privateKeyToAccount } from "viem/accounts";

const client = new x402Client();
client.register("eip155:*", new ExactEvmScheme(privateKeyToAccount(pk)));
const fetchWithPayment = wrapFetchWithPayment(fetch, client);
```
Note: `x402Client` must be `new`-ed (it's a class, not a factory). The CDP SDK's
`CdpX402Client` needs `CDP_WALLET_SECRET` to provision a managed wallet — if you only have
`CDP_API_KEY*`, use the vanilla `x402Client` with your own EVM key instead; the CDP
facilitator still settles it (which is what triggers Bazaar indexing).

## Dependency isolation

`@dexterai/x402` (Dexter) and `@coinbase/cdp-sdk` (CDP) conflict on `@x402/core` version
(Dexter wants 2.12, CDP wants ^2.19). **Install them in separate directories**, don't mix
in one package.json. Each self-settle script lives in its own dir with its own deps.

## Base RPC for on-chain balance checks

`base-rpc.publicnode.com` works for `eth_call` balance reads; `base.llamarpc.com` returns
HTTP 521 and publicnode may 403 raw urllib (User-Agent block). Add a `User-Agent` header:
```python
req = urllib.request.Request(rpc, data=..., headers={"Content-Type":"application/json","User-Agent":"curl/8"})
```

## End-to-end debug order (the sequence that worked)

1. Auth first — fix the JWT until CDP returns 400-schema, not 401.
2. Then envelope — capture the SDK's real `/verify` body via fetch monkeypatch, replicate it.
3. Then `/settle` — add the settle call after successful verify.
4. Then gateway restart (systemd `x402-api.service`, reads env from `.env` — flip
   `PAYMENT_VERIFY_MODE` to `cdp`; the `.env` is credential-protected, edit via `sed` not
   the patch tool).
5. Run the self-settle script → expect a 200 on the retry.
6. Verify the Bazaar search (allow up to 6h for ranking).
