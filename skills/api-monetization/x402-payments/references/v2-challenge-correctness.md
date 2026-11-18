# x402 v2 — making a challenge correct, and proving it

Depth for the rules in SKILL.md. Everything here was established by exercising a real
facilitator, not by reading a schema.

---

## 1. The shape a v2 client expects

```jsonc
// PAYMENT-REQUIRED (base64 of this JSON), on a 402
{
  "x402Version": 2,
  "resource": { "url": "…", "description": "…", "mimeType": "application/json" },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "payTo": "0x…",
      "amount": "1000",                 // ← v2 REQUIRES this
      "maxAmountRequired": "1000",      // ← v1 compat only; strip before calling a facilitator
      "maxTimeoutSeconds": 60,
      "extra": { "name": "USD Coin", "version": "2" }   // ← must match the token's EIP-712 domain
    }
  ],
  "extensions": {
    "bazaar": {                            // ← without this, no catalogue can index you
      "bazaarResourceServerExtension": true,
      "discoveryUrl": "https://<host>/.well-known/x402-bazaar",
      "info": { "input": { "type": "http", "method": "GET" }, "output": { "type": "json" } }
    }
  }
}
```

A client that accepts a requirement echoes it back verbatim inside its payload, and the
facilitator compares the two. That is why advertising a field you then strip, or stripping one you
advertised, shows up as a requirements error rather than a signature error.

---

## 2. What the client actually sends back

Decoding a captured `PAYMENT-SIGNATURE` gives this shape — note that `scheme`/`network` are nested
under `accepted`, **not** at the top level of the payload:

```jsonc
{
  "x402Version": 2,
  "payload": {
    "authorization": { "from": "0x…", "to": "0x…", "value": "1000",
                       "validAfter": "0", "validBefore": "1793…", "nonce": "0x…" },
    "signature": "0x…"
  },
  "accepted": { "scheme": "exact", "network": "eip155:8453", "asset": "0x…",
                "amount": "1000", "payTo": "0x…", "maxTimeoutSeconds": 60,
                "extra": { "name": "USD Coin", "version": "2" } },
  "resource": { "url": "…" }
}
```

Consequences worth designing around:

- **Match on `payload.accepted.network`**, not `payload.network` — the latter is usually absent, so
  a naive `find(a => a.network === payload.network)` silently falls back to `accepts[0]` and works
  or fails by luck of ordering.
- **`accepted` is the clean requirement object.** It is the safest thing to forward to `/verify`
  when you want to know whether *the pair* is valid independent of your own challenge formatting.

---

## 3. The bisection procedure (how to find a bad requirements object)

Do this instead of reading a schema and guessing. Ten minutes, and it is unambiguous.

1. **Capture a real signed payload.** Point a paying client at
   `scripts/echo-402-challenge.py` — a local server that answers 402 with a requirement you
   control and writes the resulting `PAYMENT-SIGNATURE` to a file. See `scripts/x402-paid-call.py`
   for the client side.
2. **Confirm the pair verifies.** POST `{x402Version, paymentPayload, paymentRequirements}` to the
   facilitator's `/verify` with `paymentRequirements = payload.accepted`. If this is `isValid:
   true`, your signing path and domain name are correct and any failure afterwards is your
   *packaging*.
3. **Then re-send with your own requirement object** and remove one field at a time. The field
   whose removal flips `400` → `isValid: true` is the culprit. Do not assume the schema's field
   list is the accepted field list — a documented field can still be rejected in combination.
4. **Only after a clean `isValid: true`** move on to `/settle`, which is what actually moves
   money.

Worked example of why step 3 matters: a facilitator's published schema listed both `amount` and
`maxAmountRequired`, but a requirements object containing both returned
`400 invalid_payment_requirements`. Removing `maxAmountRequired` alone made it valid; removing any
other single field did not. Nothing in the schema said so.

---

## 4. Domain-name verification (the check people skip)

`extra.name` / `extra.version` are the EIP-712 domain of the token contract. They are **not** the
symbol and **not** the marketing name. Read them:

```bash
# name()  = 0x06fdde03
# version() = 0x54fd4d50
curl -s -X POST https://mainnet.base.org -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","data":"0x06fdde03"},"latest"]}'
```

Decode the ABI string: offset is the first word, length the word at that offset, then the bytes.
Circle USDC returns `"USD Coin"` / `"2"` on Base and Avalanche. A wrong name produces a
*signature* error far from the cause, which is why this is worth checking before anything else when
the facilitator says the signature is invalid but the payload looks right.

---

## 5. Proving settlement, not just a 200

A `200` with a `PAYMENT-RESPONSE` header is the server's claim. The receipt is the chain.

- Fetch the settlement hash from the response body or header, then `eth_getTransactionReceipt`.
- `status == 1`, plus a `Transfer` log on the token contract, is the proof.
- Expect the transaction's `from` to be the **facilitator's relayer**, and often `to` a
  Multicall3 contract — a facilitator settles on your behalf, so the payer address will not be the
  transaction sender. Filter the `Transfer` log topics for the real `from`/`to`/`value`.
- Report "a payment landed" and "this endpoint earned it" separately; a transfer carries no
  endpoint identity.

---

## 6. Indexing after the first settlement

Expect new catalogue entries within minutes of a settled call. Two things go wrong immediately
afterwards:

- **The count is wrong** because the catalogue crawls your `llms.txt` / `openapi.json`, and those
  still advertise services your manifests withhold. Fix every surface, not just the manifest.
- **The URLs are wrong** when a catalogue indexes a different estate than the one you just paid
  through. Compare the `resource` field of each new entry against the host you settled on before
  celebrating the number.
