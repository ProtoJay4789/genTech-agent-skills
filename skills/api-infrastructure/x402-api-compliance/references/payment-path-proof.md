# Is the payment path actually open? Prove it before you read "no sales"

A 402 challenge proves the gateway will **quote** a price. It proves nothing about whether a valid
proof is **accepted**. Those are two different failures and they look identical in a traffic log: in
both cases you see plenty of 402s, zero 200s on paid routes, and zero revenue.

## The rule

**Never report "no demand" until a valid payment proof has been accepted end to end.** Zero paid-route
200s is ambiguous by construction; it is either an empty market or a shut door, and the log cannot tell
you which. The traffic ledger records HTTP status, not settlement — it will show you 402s forever and
never once mention that the buyer's proof was refused.

## The diagnostic (10 minutes, one paid route)

Run a real client on the scheme you advertise, with a funded payer key, against a live paid route and
**read the response body's `reason`** — not just the status.

```bash
# payer key read from a file, never printed; --spend discipline applies
python3 scripts/x402-paid-call.py https://<gateway>/v1/<paid-route>/<param> /path/to/payer.key
```

Three routes, not one: a single route can fail for route-specific reasons (a backend being down), and
you are testing the *verifier*, not the product.

Read the outcome as follows:

| result | meaning |
|---|---|
| **200 + `PAYMENT-RESPONSE`** with a settlement reference | path open; the market question is now real |
| **402** with a body `reason` | **the door is shut** — quote the reason verbatim, it names the cause |
| 402 with no reason | a challenge, not a rejection — check the client is actually signing |

Confirm no money moved (read the payer's balance before and after). A refused proof costs nothing; say
so, because "we tested it" otherwise implies a spend.

## The trap that produces a silent shut door

A verify-mode switch that falls back to a dev path when production credentials are missing converts
"we are not configured" into "we take no money" — silently, and with a 402 that looks exactly like a
normal challenge-to-payment flow.

```
mode = env(PAYMENT_VERIFY_MODE, default="auto")
auto:  try facilitator/production verifier when its key exists
       else → simulation verifier (local HMAC)
```

If the simulation verifier also fails closed when its HMAC secret is unset (the right call — an
unset secret must never validate forged proofs), the result is: **no production key + no secret = every
buyer refused.** The failure is correct engineering and catastrophic merchandising.

**Check this first when revenue is zero:** assert the production verifier's credentials exist in the
running process, not in a config file someone meant to load.

```bash
docker exec <gateway-container> env | grep -c <PROVIDER>_   # expect >= 1, not 0
```

## ⚠️ The fix that manufactures revenue

**Do not satisfy a closed door by provisioning the simulation/HMAC secret.** That makes the *dev*
verifier succeed, so calls are accepted without any settlement — the next revenue report then shows
income that never arrived. A simulated acceptance is worse than a refusal, because a refusal is honest.

Two acceptable fixes:

1. **Provision the production verifier** (facilitator keys) → real verification and settlement.
2. **Pin the mode to the production verifier** (`PAYMENT_VERIFY_MODE=<production>`) so the fallback is
   gone and buyers get a *named* failure instead of a mystery. Loud beats silent.

## Prove it in four layers — a header is not money

One green signal is never enough, because each layer can pass while the next fails. Climb in this order; stop at
the first layer that fails and fix that one.

| layer | what you assert | how |
|---|---|---|
| **1 · credential** | the verifier's key authenticates at the facilitator | mint the token the provider expects (EdDSA for CDP) from a scratch venv and `GET /supported` → **200**. `401` = fix the credential, not the code. |
| **2 · acceptance** | a valid proof is accepted | paid call returns **200** with a `PAYMENT-RESPONSE` header |
| **3 · settlement** | money actually moved | decode the receipt, then confirm the transfer **on-chain** |
| **4 · delivery** | the buyer got the product | the response **body** is the service's output, not an error envelope and not a redirect |

**Layer 3 — decode the receipt and then read the chain.** The header is base64 JSON; a `success:true` in it is the
gateway's claim, and the transaction hash is what makes it checkable:

```python
import base64, json
r = json.loads(base64.b64decode(recv + "=" * (-len(recv) % 4)))
# {"network":"eip155:8453","payer":"0x…","success":true,"transaction":"0x…"}
```

### ⚠️ The receipt reader that reports `settled: false` on a real settlement

**The SDK helpers return OBJECTS, not dicts, and the header arrives lowercase.** Two bugs that both produce a
false negative — the worst failure mode here, because it reads as "the payment path is shut" when money moved:

- **Normalise the decoded result to a dict before reading any field.** `decode_payment_response_header()` returns a
`SettleResponse` dataclass (`success`, `transaction`, `network`, `error_reason`). `settle.get("transaction")` on an
object returns **`None` without raising**, so a script that reads it that way reports `settled: false, tx: null` on
three consecutive successful settlements — while the payer's balance drops and the block explorer shows the
transfer. `settle = s if isinstance(s, dict) else dict(vars(s))`, then read.
- **Look the header up case-insensitively by building a folded map** (`{k.lower(): v for k, v in r.headers.items()}`).
`payment-response` is what the wire carries; a lookup for `PAYMENT-RESPONSE` on a plain dict misses it.

**The general rule:** for every third-party response you decode, assert the SHAPE (`isinstance` / `vars`) on the
first real call, not just that the call returned. Forgiving access is how a true result becomes a false zero.

**And say which failure you hit:** "no receipt header" (the server did not send one) is a different defect from
"receipt present, could not parse it" (your reader). Print the raw header length before decoding so the two are
distinguishable in the transcript.

### Spending real money to prove the path — cap it, dry-run it, then verify on chain

Paying your own endpoint is the cheapest end-to-end proof that exists, and it doubles as evidence for a catalogue
(the settle is what refreshes a listing). Keep it disciplined:

1. **Dry run first.** Read the 402, pick the requirement, build and sign the payload, print `{rail, amount, payer}`
   and **send nothing**. A dry run that prints the amount is the last chance to notice a price you did not expect.
2. **Enforce the cap in code, not in your intentions.** Register the network preference and an absolute per-call
   ceiling (`max_amount(<atomic>)`) as client policies, and refuse before signing if the cheapest acceptable
   requirement exceeds it.
3. **Read the key from a mode-600 file inside the process.** Never interpolate it into a shell command line — the
   command string lands in the transcript.
4. **Confirm the balance delta and the on-chain `Transfer` log** (above), then report the hash and the total spent.
   A run that says "settled" without a hash is not evidence.
5. **Count the run as a self-payment.** It proves the door opens; it is not revenue.

A working payer that does all five is `scripts/x402-paid-call.py` in this skill.

Then confirm the transfer with `eth_getTransactionReceipt` on the advertised network and match the **USDC
`Transfer` log** — amount, payer, and `payTo` — not the receipt status alone:

```python
USDC  = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"          # token contract for that rail
XFER  = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"   # Transfer(address,address,uint256)
for lg in receipt["logs"]:
    if lg["address"].lower() == USDC and lg["topics"][0].lower() == XFER:
        amount = int(lg["data"], 16) / 10**6
        frm, to = ("0x" + lg["topics"][1][-40:], "0x" + lg["topics"][2][-40:])   # amount, payer, payTo
```

A verified receipt with the wrong `to`, or a zero-value transfer, is the failure that a `success:true` header hides.
**Report the hash and the amount** — "settled" with no hash is a claim, not a measurement.

**Layer 4 — a 3xx AFTER settlement is a paid non-delivery.** The gateway settles first and proxies second, so a
redirect produced by the proxy arrives *after* the money moved:

```
/v1/<service>/<param>/   → 307   (settled 0x…, redirected, empty body)   ← buyer paid, received nothing
/v1/<service>/<param>    → 200   (settled 0x…, body is the service data) ← correct
```

Trailing-slash normalisation (or any canonical-path redirect) therefore has to happen **before** the challenge
exists, never at the proxy. Same family as charge-before-validate: the charge must not precede a path known to be
deliverable. Do **not** "fix" it on the client by following the redirect — a second request means a second charge.
Test both spellings of every published URL and treat 3xx as a delivery defect even when the settlement succeeded.

**And classify the payer before you call it revenue.** A successful call from a wallet you control proves the door
opens and nothing else. It belongs in the self/test exclusion line of the revenue report — **reported revenue
stays zero until a wallet you do not control pays.** Say which one happened; "we took a payment" from our own
wallet is the kind of true-but-misleading line that corrupts every later metric.

## Related: the same class of bug on the demand side

Reading demand off the same log has its own trap — an "unclassified caller" bucket that is reported as
a number instead of being inspected. See `caller-classification.md` for the method (user-agent is a
claim, path breadth is evidence).
