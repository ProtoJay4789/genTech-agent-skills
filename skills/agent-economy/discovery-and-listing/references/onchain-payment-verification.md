# Verifying that a payment actually happened, on-chain

**Use when a revenue report says zero (or a number you doubt), or when you must prove whether a
caller paid.** The chain is the record; every hosted explorer UI and API is a claim about it.

---

## The invariant

A payment is a **log inside a transaction receipt**, nothing else:

```
topic0 = keccak("Transfer(address,address,uint256)")
         = 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
topic1 = from  (left-padded to 32 bytes)
topic2 = to    (left-padded to 32 bytes)
data   = amount in base units (USDC = 6 decimals, so ÷ 1e6)
```

**And prove the PAYER is external by looking for how they were funded** — see "Prove the payer is a
stranger" below. That step is what turns a transfer into a sale.

---

## Read logs directly over JSON-RPC — the durable path

Hosted explorer APIs are the fragile route: the big one deprecated its v1 endpoints, its v2 free
tier does not cover every chain, and a block-explorer web UI behind bot protection is not an API.
**Direct JSON-RPC works with no key and no account, and is the path to build on.**

```python
{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{
  "fromBlock": hex(lo), "toBlock": hex(hi),
  "address": USDC,
  "topics": [TRANSFER_TOPIC, None, "0x" + "0"*24 + PAYTO[2:].lower()]
}]}
```

**Filter on `topics[2]` = payTo at the RPC layer.** It makes the response tiny and it is the one
filter that cannot be silently ignored — you are matching the event itself, not a query parameter.

### ⚠️ Every public provider caps the block range — probe it before the full sweep

Observed caps, all different, all enforced as an **error** (not a clamp):

| provider | cap |
|---|---|
| `base.drpc.org` | **10,000 blocks per call**, even at 9,999 it refused |
| `1rpc.io/base` | **50 blocks** |
| `base.publicnode.com` | **50,000 blocks per call** (`exceed maximum block range: 50000`) — *and it throttles sustained sweeps completely* |
| `mainnet.base.org` | rate-limits under load — the first sweep died on `request limit reached` |
| `base.blockpi.network/v1/rpc/public` | requires a key |

⇒ **Send one deliberately-small window first and read the error text.** Then size the sweep to the
cap the provider actually reports, and move to a different provider if the cap makes the sweep
impractical.

**The recipe that completed a 14-day, 604,800-block sweep with zero errors:**

- `base.publicnode.com`, **2,000-block windows** (~303 calls), `time.sleep(0.02)` between them
- filter `topics[1]=None, topics[2]=payTo` so each response is near-empty
- record **windows ok / windows errored** beside the result

---

## ⚠️ The zero that is really a failure

**A scan loop that treats an errored window as an empty result prints `0` and looks like a
measurement.** Observed: 61 of 61 windows returned
`ranges over 10000 blocks are not supported on free plan`, the loop continued past every error, and
the output was a confident **"inbound transfers: 0"**.

**Rules:**

- **Count successes and failures separately, and refuse to answer unless successes > 0.**
  `if ok == 0: print("UNKNOWN — no window succeeded")`, never `0`.
- **A window that errors is retried at a smaller span, not skipped.** Skipping is how a whole day
  disappears from a total without changing its shape.
- **Print the coverage** (`windows ok · errors · blocks spanned`) next to the count, so a future
  reader can tell a complete sweep from a partial one.
- **Anchor against a second, independent read.** The token balance of the address is one call and
  costs nothing:
  `eth_call({"to": USDC, "data": "0x70a08231" + "0"*24 + addr[2:]})`. **A non-zero balance beside a
  zero transfer count is proof the scan is wrong**, not proof the money is unexplained.

---

## Budget the sweep, and make it RESUMABLE — a long sweep will be interrupted

**A 120-day sweep is ~100 calls at any practical chunk size, and the free endpoints will not carry it in one
go.** Measured in one session, three attempts:

| attempt | shape | result |
|---|---|---|
| 1 | one endpoint, 50k chunks | **97 transfers found, 16 chunks lost** → refused to write |
| 2 | four endpoints, retry-on-error | **98 found, 19 lost** → refused to write |
| 3 | four endpoints × 4 passes + backoff, per-chunk cache | **zero chunks completed in 4.5 minutes** — sustained `eth_getLogs` throttles outright |

**So the honest conclusion is not "retry harder": the keyless route is viable for a bounded window and not
for a long reconstruction.** Before promising a full history, either keep the window short enough to finish
in one pass, or get an indexer key — and say which one you are doing.

**⚠️ Window size is the variable that decides this, not the endpoint.** The same provider that completed a
14-day sweep with **2,000-block** windows refused or throttled **50,000-block** chunks three times running —
small, cheap requests are what the free tier actually tolerates. **So before concluding the keyless path is
dead, re-run at ~2,000 blocks with a short sleep:** attempt 3 above failed because it escalated retries and
chunk size together, which is the combination that gets blocked. Try the cheap shape once before buying the
key.

Two rules that make the attempt survivable either way:

- **Cache each completed chunk to disk, keyed by `rail-lo-hi`, and skip it on the next run.** Without this,
  an interrupted sweep restarts from block zero and the second attempt reports a different number than the
  first — which reads as the data changing rather than the scan not finishing.
- **Refuse to write on ANY lost chunk: print `INCOMPLETE`, the lost ranges, and exit non-zero.** A partial
  ledger is worse than none, because the consumer cannot tell it from a small week. Measured: the refusal
  fired three times and was right all three times; the count it protected (`98 transfers`) was never
  mistaken for a total.

---

## Prove the payer is a stranger

**A transfer to you is not automatically a sale — you pay yourself, and so do test scripts.** Two
checks, in order:

1. **Compare the payer against an explicit wallet set of your own.** Not a heuristic, not a pattern —
   a hardcoded list of every address you control (treasury, media lane, test keys). Anything outside
   it is external.
2. **Look for a FUNDING transfer to the payer inside the same transaction.** Measured on a real
   sale: the receipt carried **two** Transfer logs — one *into* the payer from a third address, and
   one from the payer to us. **A wallet being topped up and spent in one transaction is a buyer**;
   a wallet that already held the funds is ambiguous.

**And read `tx.to` to understand the route.** A purchase that routes through a **multicall / batch
router** rather than calling your contract directly still contains ordinary ERC-20 Transfer logs —
so the log scan finds it even though the top-level `to` is not you. **Do not filter transactions by
recipient address alone; read the logs.**

---

## What this means for a revenue report

- **Classify by PAYER ADDRESS. Never by transaction shape.** Bucketing settlements by pattern
  (multicall, repeated identical amounts, same-block bursts, round numbers) files a stranger's real
  purchases under "self/test" — and a bot buying 19 small calls in two bursts looks exactly like a
  test script.
- **A cross-check that compares your own two figures proves arithmetic, not classification.**
  `balance delta == log sum` can both be correct and both be describing only your own wallet.
- **When the total is zero and you believe there were customers, go to the chain before reporting.**
  Real money deflated to zero is worse than inflated self-traffic: inflated numbers make you chase a
  phantom, deflated ones make you stop looking for customers you already have.
- **Report the payer set, not just the amount.** `19 payments from 1 external address` and
  `19 payments from 1 address — ours` are the same number and opposite findings.
