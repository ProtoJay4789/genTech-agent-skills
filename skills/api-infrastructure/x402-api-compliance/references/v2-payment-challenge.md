# The x402 v2 payment challenge — why a 402 can be unpayable, and how to prove it

A 402 that a client cannot build a payment from is worse than a 404: the resource looks listed,
looks priced, and no money can ever arrive. Every defect below produced a **valid-looking HTTP 402**
and was invisible from status codes. Check all of them before believing a paid endpoint works.

> **All five fields correct and it still never gets paid?** That is the *seller* side, not the challenge:
> `seller-side-settlement-failure-modes.md` — the four facilitator hostnames (three dead), fail-loudly instead
> of simulating, `402` not `400` on a malformed proof, charge-then-redirect, charge-before-validate, and the
> receipt header missing on some rails.

## 0 · Before any field: is the verifier in PRODUCTION mode?

Every field defect below is irrelevant if the server cannot verify a payment **at all**. Gateways commonly
choose a verifier from a mode variable (`auto` is the usual default) and fall back to a **simulation / dev
verifier** when production credentials are absent. That fallback fails closed, and it fails *silently*:

```
402 {"error":"payment_proof_invalid","reason":"simulation disabled: <SECRET> not configured"}
```

A valid payer with a valid proof, refused, by a reason that names a missing environment variable. **Prove the
mode before auditing a single challenge field:**

```bash
docker exec <gateway> env | grep -c '^CDP_'                 # 0 => no production verifier configured
docker exec <gateway> printenv PAYMENT_VERIFY_MODE         # unset/`auto` => silent fallback is live
```

⚠️ **Never "fix" this by setting the simulation secret.** That makes the HMAC/dev path succeed, so the server
accepts proofs that moved no money and the next revenue report counts fiction. The fix is the production
verifier's credentials — or pinning the mode to the production value so the refusal is loud and named instead
of a silent fallback. **Name the wrong fix explicitly when you report it**, because it is the shortcut somebody
will otherwise take.

⚠️ **Zero paid calls is not evidence of no demand until this check passes.** A paywall that refuses every buyer
and a market that does not want the product look *identical* from inside your own logs: 402s, no revenue, and
callers who "hit the paywall and left". One settlement attempt from a funded wallet that is not the receiving
address is the only thing that separates them. Until it runs, any demand verdict is unfounded — say so rather
than reading the zero as a market signal.

**Assert the cost.** A refused proof spends nothing, so confirm the payer's balance is unchanged afterwards
and state it — otherwise "we tested the paid path" is mistaken for "we paid for something".

## The five field-level defects, in the order they bite

### 1. `amount` — v2 clients read it, and only it

```
x402Version: 2  +  maxAmountRequired: "1000"      ← v1 field name under a v2 header
```

A v2 client reads `accepts[].amount`, finds nothing, and cannot construct a payment. **Emit both**
(`amount` for v2, `maxAmountRequired` for any surviving v1 client). Advertising both is safe;
*forwarding* both is not — see defect 4.

### 2. `extensions.bazaar` — no declaration, no discovery

Every bazaar indexes a resource **after a settled paid call**, and a call cannot be constructed
without the bazaar declaration. Missing it means the resource is invisible forever, no matter how
correct the price. Minimum shape:

```json
"extensions": { "bazaar": {
  "bazaarResourceServerExtension": true,
  "discoveryUrl": "https://<host>/.well-known/x402-bazaar",
  "info": { "input": {"type":"http","method":"GET"}, "output": {"type":"json"} }
}}
```

### 3. EIP-712 domain name/version — the deepest one

The client signs the EIP-3009 authorization using **the `extra.name` / `extra.version` the server
advertises**. If they do not match the token contract's on-chain EIP-712 domain, the token reverts:

```
FiatTokenV2: invalid signature
invalid_exact_evm_token_name_mismatch
```

**Never hardcode a token name.** Read it on-chain and use exactly what comes back:

```bash
# name()   0x06fdde03   version() 0x54fd4d50   symbol() 0x95d89b41
curl -s -X POST <rpc> -H content-type:application/json \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<token>","data":"0x06fdde03"},"latest"]}'
```

Stablecoin domains are **not** their ticker: Circle USDC on Base and Avalanche both return
`name() = "USD Coin"`, `version() = "2"`. Symbols lie; `name()` does not.

### 4. `paymentRequirements` — one object to the facilitator, an array to the client

Your challenge advertises `accepts: [ ...several networks... ]`. Facilitators such as PayAI's
`/verify` and `/settle` take **a single `PaymentRequirements` object**. Sending the array returns
`400 {"reason":"invalid_payment_requirements"}` — which reads like a schema problem and sends you
chasing the wrong field.

Select the requirement whose `network` matches the signed payload:

```js
const pick = reqs.accepts.find(a => a.network === payload?.network) || reqs.accepts[0];
const { maxAmountRequired, ...chosen } = pick;   // facilitator gets the v2 field set only
```

Also note: the client's payload may nest the accepted requirement (`payload.accepted.network`)
rather than expose it top-level, so a match on `payload.network` can silently fall through to
`accepts[0]`. Check both, and make the fallback deliberate.

### 5. Strict verifiers reject extra fields their own schema lists

A facilitator schema may *document* `maxAmountRequired` and still **400** when it arrives alongside
`amount`. Schema-listed ≠ accepted. **Advertise both, forward one.** Bisect to confirm rather than
guessing — see the harness below.

### 6. THE ORDER OF `accepts[]` IS A PAYMENT DECISION, NOT A DISPLAY PREFERENCE

**Open clients read `accepts[0]` and sign for it.** They do not shop the array for the rail they like
best — the order is the server's recommendation and the client takes it. So the FIRST entry decides
whether a generic buyer can pay at all, and putting a special-case rail first because a partner requires
it makes the whole challenge unpayable everywhere else, while every individual field stays correct.

Measured shape: `accepts[0]` was a partner-required L2 rail settling in a non-Circle stablecoin, while
the plain Base USDC requirement — the one an off-the-shelf x402 client signs with no extra work — sat
second. The challenge validated. It simply could not be paid by the clients that discovered it.

- **Lead with the most STANDARD-COMPLIANT rail** (Circle USDC on an EVM chain clients ship support
  for), then order the rest by preference.
- **A partner rule is about what you ACCEPT, not about what you ADVERTISE FIRST.** If a validator demands
  its own rail, give that order only where the validator looks — a per-request or per-partner mode —
  rather than reordering the global challenge for every client.
- **Read the order back from the live 402**, not from the config meant to produce it: a display-order
  constant and the `accepts` builder drift, and the one that ships is whichever the handler emits.
- **Test the swap before building anything.** Reordering is one line plus a restart, needs no settlement
  work, and either produces a paid call or eliminates the strongest remaining hypothesis.

### 7. `assetTransferMethod` IS NOT OPTIONAL WHEN THE LEAD ASSET IS NOT STANDARD USDC

The `exact` EVM scheme offers three transfer methods (EIP-3009, Permit2, ERC-7710), and the spec says
*if no `assetTransferMethod` is specified in `PaymentRequired.extra`, clients default to `eip3009`*.
That default is only honest for a token that implements `transferWithAuthorization`.

**So a rail whose asset is not an EIP-3009 token, advertised with no `assetTransferMethod`, tells every
client to sign a call that cannot succeed — and the challenge still validates.** Emit the method
explicitly per rail, or drop the rail.

---

## Telling "they cannot pay" from "they do not want to" — the traffic test

The settlement ledger alone cannot separate a paywall that refuses every buyer from a market that does
not want the product. The request log can, in one pass:

1. **Bucket callers by actor class first** — monitors/crawlers, generic clients (`node`, `undici`,
   `python-httpx`, `Go-http-client`, `Deno`, bare `curl`), browsers, no-UA. The generic bucket is the only
   population that can become a buyer; never label it as a bot.
2. **Follow each caller's sequence after its first paid `402`:**
   - next request is **another paid route** → they are *trying to buy*; the defect is on your side.
   - next request is a **free path** (`/openapi.json`, another unpaid route) → they are shopping for
     something free; demand or capability problem, not yet a paywall defect.
   - **no next request** → they left at the wall.
3. **Report all three counts.** "498 never reached a paid route, 55 hit a 402 and tried another paid route,
   14 left" is a diagnosis; "0% conversion" is only a number.

**A zero paid-call count is not a demand finding until the challenge is proven payable** (§0 and §§3, 6, 7
above) — this split is what proves it either way.

---

## Diagnostic ladder — from "402 fine" to "settles"

Run these in order; each isolates one layer so you never fix two things at once.

0. **Confirm the verifier mode** (`§0`) and that the refusal reason is not a configuration message. A
   configuration refusal makes every later step meaningless.
1. **Decode what you actually serve.** `curl -i` the paid path, base64-decode `PAYMENT-REQUIRED`,
   and print the **field names** of `accepts[0]` — not just the values. Name mismatches are the
   whole bug class.
2. **Compare against a known-working endpoint.** If any of your own estates takes real money, diff
   its `accepts[0]` key set against the suspect one. A field present in one and absent in the other
   is the finding.
3. **Capture what a client signs, without touching production.** Stand up a local echo server that
   returns your challenge, then on the retry writes the `PAYMENT-SIGNATURE` header to a file. Decode
   it: you now have the exact signed payload for your exact requirement object. Serve
   `serve_forever()` on the **main thread** — a daemon thread exits with the parent and the client
   gets connection-refused instead of the capture.
4. **Ask the facilitator directly.** `POST` the captured `{paymentPayload, paymentRequirements}` to
   `/verify` and read `invalidReason`, which is far more specific than what your own server relays
   (
   `invalid_exact_evm_token_name_mismatch`, `invalid_payment_requirements`).
5. **Bisect the field set.** Start from the requirement that failed, delete one key, re-verify.
   Fastest possible isolation of a strict-validator rejection.
6. **Only then settle**, and confirm the receipt **on-chain** (`status`, `Transfer` and
   `AuthorizationUsed` logs), not from your own 200.

## Reading a settled call correctly

- The settlement transaction is broadcast by the **facilitator's relayer**, not by you. Its `from`
  will not be your payer wallet — that is normal, not evidence of a third party.
- A successful settle yields **two logs** on the token: `AuthorizationUsed` and `Transfer`.
  Decode topics[1]/topics[2] for from/to and divide by the token's decimals for the amount.
- Settlement relaying through **Multicall3** is expected on Base.

## Discovery consequence nobody expects

Indexing is triggered by that settled call. **The moment it lands, third-party catalogues crawl your
advertised surfaces and republish them.** If any surface still lists services you cannot serve, the
aggregator will publish that overstatement under your name within minutes — so fix the *surfaces*
before making the first real payment, not after. See `advertised-surface-agreement.md`.
