# Client-side signing: why a protocol-correct 402 can still be unpayable

A challenge can pass every schema check and still be impossible for a real client to pay. The fields below are
where that happens. Check them before concluding "nobody wants it".

## `extra.name` and `extra.version` are the signature, not labels

On an EVM `exact` rail, the client builds a `transferWithAuthorization` payload and signs it against the
**EIP-712 domain** derived from those two fields. So:

- They must match the token contract's own `name()` and domain version — not a human-readable label you pick.
- A token whose `name()` is `USDC` signed with `{name: "USD Coin"}` produces a different domain separator and
the signature is rejected. Verify by hashing against the token's on-chain `DOMAIN_SEPARATOR` before shipping.
- Never copy `version: "2"` across assets. Different stablecoins on different chains carry different domain
versions; each rail needs its own verified pair.

## `assetTransferMethod` — declare it, don't rely on the default

`PaymentRequired.extra.assetTransferMethod` tells the client which transfer path to use (`eip3009`, `permit2`,
`erc7710`). The spec says a client that finds it missing **defaults to `eip3009`**. That default is silent, and it
is wrong for any asset that does not implement EIP-3009:

- Set `assetTransferMethod: eip3009` explicitly on rails whose asset genuinely supports it (Circle-issued USDC
does on Base, Avalanche, and Celo).
- If a rail's settlement asset is a non-EIP-3009 wrapper, leaving the field out advertises a method the token
cannot perform — the client signs, the settle fails, and the buyer sees a broken service, not a config bug.

## `accepts[0]` is the rail a blind client pays on

Most clients read the first entry and sign it. Order therefore decides whether anyone can pay at all.

- Put the **most standard-compliant, most widely-held** asset first — native USDC on Base is the rail open
  clients sign out of the box.
- When a marketplace validator demands a specific chain first (it rejects multi-network `accepts`, or pins a
  charter), satisfy it on the **alias/probe routes that validator actually calls**, not by reordering the
  challenge every other client receives. Two orderings, one implementation: the validator path emits a
  single-rail challenge; the general path emits the multi-rail one with the standard rail first.
- Precedence applied in code beats precedence set in environment variables: an env-only ordering in a container
you cannot inspect silently reverts the first time nobody is looking.

## Diagnosing "traffic but no revenue"

Do not read 402s as demand, and do not read the absence of payments as a pricing problem. Separate the callers:

| pattern | meaning |
|---|---|
| hits a paid route once, then keeps probing paid routes | an API consumer trying to buy — **cannot complete payment** |
| hits a paid route, retries a free path (`/openapi.json`, another unpaid route) | looking for something free; not a buyer yet |
| never reaches a paid route at all | a crawler, monitor, or health check |
| hits a paid route then vanishes | either repelled or broken — check the challenge before pricing |

If consumers hit the paywall and keep trying paid routes but never settle, the fault is in `accepts[]`, not in the
price. Reproduce their position: attempt to build a valid payload against `accepts[0]` by hand. If you cannot
produce something a facilitator would settle, no client can.

## After you change the ordering — four checks, then one signal

Reordering `accepts` is a **falsifiable experiment**, not a fix you can declare. Verify in this order
immediately after the restart, because three of the four can break while the challenge still looks right:

1. **`accepts[0]` is the rail you intended** — read it back from the live 402, not from the source file.
2. **Decode the `payment-required` header the way a client does** and confirm the domain fields arrived:
   `{name, version, assetTransferMethod}` on the leading rail. A value that is correct in code but absent
   on the wire has not shipped.
3. **The validator/marketplace route still gets its pinned single-rail challenge.** If the ordering change
   also moved the route that a marketplace validator probes, the fix broke the thing the ordering existed
   for — check the alias path explicitly, including that its extensions block is still absent.
4. **The paid routes still answer 402 and health still answers 200.** A challenge that cannot be issued is
   worse than a bad ordering.

Then stop touching it and wait for **exactly one signal**: a `402 → 200` on a paid route carrying a payment
header. Nothing else counts — not more traffic, not a monitor repeating the challenge, not a crawler listing
you. **If that signal does not arrive, the ordering was not the blocker**, and the next move is to say so
plainly rather than reordering again.

## Also verify, in the same pass

- The advertised `resource.url` is byte-identical to the route that issues the challenge (no trailing-slash
  redirect in between).
- Every rail in `accepts` has a configured `payTo`. A rail advertised without one fails the buyer after they
  have committed.
- Any `chains` field in the discovery manifest is **derived** from `accepts`, never hand-written — a payment
  field must not carry coverage claims.
- A rail with a malformed CAIP-2 identifier can invalidate the **entire** 402 for a strict validator, not just
  that one rail. Validate every identifier before adding a network.

## When you are the CLIENT: four rules for a payer that reports the truth

A self-payment client (paying your own endpoint to prove the rail, refresh a listing, or produce a receipt) is an
instrument. These four failures make it lie while returning success.

1. **Read `PAYMENT-RESPONSE` case-insensitively.** The header arrives lower-cased on the wire
   (`payment-response`); a case-sensitive lookup on the response object misses it and the script reports
   "not settled" on a settlement that already landed on chain. Build a `{k.lower(): v}` map before reading.
2. **Normalise the decoded receipt to a dict before touching a field.** SDK decoders commonly return a **model
   object**, not a mapping — `object.get("transaction")` then returns `None` **without raising**, so every real
   settlement reports as `settled: false`. Convert with `dict(vars(obj))` (or the SDK's own `to_dict`) first.
3. **Verify the money, not the status code.** A 200 with a body proves the resource was served; only the receipt's
   `transaction` plus an `eth_getTransactionReceipt` with `status: 0x1` and the expected `Transfer` amount proves
   it was **paid**. Log `payer`, `transaction`, `network`, `success`, `errorReason` — never the signature payload.
4. **Echo the `extensions` object back in the payment payload.** x402 v2 requires the client to copy the server's
   declared extensions; catalogues index **what the client echoes**, so a client that drops them can settle
   successfully and still register nothing. Assert on the built payload that `extensions` is non-empty before
   sending.
5. **Put `resource` INSIDE `paymentPayload`, not only in the 402.** §5.2.2 marks it **Optional** in
   `PaymentPayload`, so nothing rejects a payload without it and no validator warns — but a facilitator
   catalogues a resource *from the settlement payload*: "the payment payload sent to the facilitator must
   include `paymentPayload.resource` so CDP knows which resource to catalog." Omit it and the money moves
   while the listing never appears: **the settlement is real and unattributable.** Take the URL from the
   request being served, never from the caller's payload, so a payment can never be credited to a route that
   was not called. **Optional-in-spec is not optional-for-discovery** — test for it explicitly.
6. **Transmit `uint256` fields as STRINGS; sign over integers.** The `exact` EVM scheme carries
   `payload.authorization.value`, `validAfter`, `validBefore` as strings. Sending `1000` instead of `"1000"`
   returns `400 request body has an error: Error at "/paymentPayload/payload/authorization/..."` — a message
   that names the path but not the type, so it reads like a shape bug and sends you rewriting a correct
   payload. Build the EIP-712 message from ints, serialise the JSON with strings.
7. **Never truncate a facilitator's error body when relaying it.** `resp.text[:200]` cuts the message at
   exactly the field name — the buyer sees `Error at "/paymentPayload/payloa` and has to guess. Keep ~800
   characters so `correlationId`, `errorLink` and the full `errorMessage` survive. **A truncated error is the
   bug that hides the bug**: every extra field in the message is one fewer bisection round.

**Bonus that changes cost models:** catalogue indexing also runs on `/verify`, and verification moves no funds —
so a listing can be registered or refreshed for **free**, without a settled payment. Reach for a verify before
budgeting a settle.

