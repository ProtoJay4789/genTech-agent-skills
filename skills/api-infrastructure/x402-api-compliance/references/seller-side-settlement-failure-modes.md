# Seller-side x402 failure modes — the five checks that decide whether you can take money

Written from the **seller's** side: an endpoint that returns a beautiful `402` challenge and still never gets
paid. Each entry is a check to run, the evidence that convicts it, and the fix. Run all five before quoting
anyone a price or publishing a listing.

---

## 0 · The facilitator hostname — four candidates, one alive

This is the single most common cause of "nobody can pay us", because it fails **before** any signature is
checked, and the error text often does not name the host.

| hostname | verdict |
|---|---|
| `https://x402.org/facilitator/platform/v2/x402/*` | **404** — retired. Still copied through old docs and old repos. |
| `https://facilitator.cdp.coinbase.com/...` | **NXDOMAIN** — **no A record at all**. Frequently recommended as the *fix* for the first row, which is how one dead endpoint becomes two. |
| `https://x402-facilitator.cdp.coinbase.com/...` | **NXDOMAIN** — a third variant in the wild. |
| **`https://api.cdp.coinbase.com/platform/v2/x402/{verify,settle,supported}`** | **alive** — answers `401` unauthenticated, which is the correct signal for an auth-gated endpoint. |

**Check:**
```bash
for u in "https://x402.org/facilitator/platform/v2/x402/verify" \
         "https://facilitator.cdp.coinbase.com/platform/v2/x402/verify" \
         "https://api.cdp.coinbase.com/platform/v2/x402/verify"; do
  printf '%s %s\n' "$(curl -s -o /dev/null -m 15 -w '%{http_code}' "$u")" "$u"
done
python3 -c "import socket; socket.gethostbyname('facilitator.cdp.coinbase.com')"  # gaierror = NXDOMAIN
```

- **A `404` and a `000` are different failures.** `000` means DNS or connection; `404` means the host answers and
the path is gone. Report which one you saw — they have different fixes.
- **`401` from the production host is success.** Do not "fix" a 401; it means the endpoint exists and wants a JWT.
- **Auth detail that costs an afternoon:** the CDP key id is issued as a **bare 36-char UUID**, and that form
  works as the JWT `kid`. Signing with a hand-assembled `organizations/<uuid>/apiKeys/<uuid>` string is the trap.

## 1 · A server that cannot reach the facilitator must not silently simulate

When verification cannot reach the facilitator, a "safe" fallback that fabricates a simulated verdict turns a
network problem into **a paying customer being refused with a message that never mentions the network** — or,
worse in the other direction, an acceptance that settles nothing.

- A verify path must **fail loudly and name the host** it could not reach.
- **Never** make a server-env secret "enable" production verification as a workaround: if the only thing
  standing between you and taking money is a flag that turns simulation into success, that flag is revenue
theatre. Fix the credential, or return a named error.
- Diagnostic that settles it in one line: `docker exec <gateway> env | grep -c '^CDP_'` — `0` means the
  container has no facilitator credentials at all, and every payer is being refused by you, not deterred by
  the market.

## 2 · Malformed proof → `402`, not `400`

A client that signs incorrectly has made a **payment** mistake, not a malformed-request one.

```
PAYMENT-SIGNATURE: not-base64!!   →  HTTP 402  {"error":"payment_proof_invalid",
                                               "reason":"proof is not valid JSON or base64 JSON"}
```

- `400` tells a compliant client "you sent a bad request" and it **stops**.
- `402` with a fresh `PAYMENT-REQUIRED` lets it **retry** — and the clients that sign wrong are exactly the
  ones that need the second chance.
- Never return `400` on the payment path. Assert the status in a test, because a framework's generic
  validation error will happily produce `400` for you.

## 3 · Overpayment — say which you accept, in the scheme text

Implement the floor only unless you have a reason not to:

```python
if Decimal(amount) < Decimal(str(int(expected_price * 1_000_000))):
    return False, "amount below required price"   # amount > required SETTLES
```

- The wording "meet the requirements" matches `>=`; an error name like `invalid_exact_...` implies `==`.
  **A server author reading the scheme will implement `>=`.** If strict equality is intended, the spec must say
  so explicitly, because the natural reading of either source gives a different answer.
- Whichever you implement, **state it on your own discovery surface** so a buyer is not guessing.

## 4 · Delivery after settlement — the check nobody runs

**The dangerous 402 is a valid one.** Payment succeeds, delivery does not, and every test that only asserts the
challenge shape passes.

Measured on the same service, two URLs differing only by a trailing slash:

```
GET /v1/.../ETH/   → settled 0.001 USDC (tx 0x9ab8…) → 307, empty body     ← money gone, nothing delivered
GET /v1/.../ETH    → settled 0.001 USDC (tx 0x810c…) → 200 + data          ← correct
```

- **The failure is reached by PATH, not by payload.** Charge-then-redirect is the same class as
  charge-before-validate.
- Fix in two places: **normalise the path before the challenge** (trailing-slash canonicalisation), and make the
  paid route's response never a redirect — resolve the redirect *before* charging.
- **Conformance test to add:** for each advertised route, assert *delivery* on the exact URL you publish,
  not just that it returns `402`.

## 5 · Charge-before-validate — an unknown resource must not be payable

If an unknown identifier returns a **payable** challenge (all rails, a `payTo`, a price) while a wholly unknown
service returns `404`, a buyer can pay and then receive `404`.

- Confirm a quote exists **before** issuing a challenge: resolve the resource, then price it, then return `402`.
- Test with `GET /v1/<known-service>/nope-xyz` — a payable 402 there is the defect.
- **Also verify the subpath rule against the manifest matrix.** A service that declares **no** parameters must
  reject extra path tails; an implementation that returns `""` (accept) when the parameter list is empty
  accepts any tail and silently charges for routes it cannot serve.

## 6 · The receipt — `payment-response` must be present on EVERY settled rail

A settled call must carry the receipt the buyer's client reads:

```
payment-response: {"network":"eip155:8453","payer":"0x…","success":true,"transaction":"0x…"}
```

- **Rail-specific gaps are invisible from outside.** Measured: the header present on the default rail and
  **absent entirely** on a second rail where the money had genuinely moved on-chain. A buyer reading the header
  concludes the payment failed while their funds are gone.
- Assert the header on **every** rail you advertise, not just the one that gets used most.
- If you cannot produce a receipt, say so in the response body — silence is the worst option.

## 7 · Rails advertised vs rails proven

Advertising N rails and settling on 2 is a normal stage, and it is fine **as long as the two surfaces tell
different, honest stories**: the machine-readable card may list rails you can *accept* on; prose must claim only
what has *settled*.

- Keep a `notServable` block with the **system's own reason** for every withheld service or rail
  (`"nothing listening on 8087"`, `"no source recovered"`) and render it — omission reads as a lie by the next release.
- Any "why isn't my payment working" on an advertised-but-unproven rail is a **funding-and-testing gap, not a
  configuration one.** Say which.

## 8 · Descriptive prose drifts; counts in prose are claims

A generated discovery document can still lie if its **description** is hand-typed. Measured: a manifest claimed
`14 live endpoints on Base, Avalanche and Ethereum` while the machines said **9 services, 2 chains**.

- **Make the description number-free.** Counts belong in the generated array; a number in prose is a claim that
  drifts silently and is never regenerated.
- Regenerate the whole document from the same inventory the server serves (`services`, `accepts`, `notServable`)
  so the card cannot disagree with what is for sale.
- ⚠️ **Fix the SOURCE the generator reads, not the output.** A generator that reads prose from a separate base
  file will faithfully regenerate the same stale claim forever.
