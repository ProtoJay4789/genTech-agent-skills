# On-chain payment attribution — proving revenue, and the limits of that proof

**Two separate stores record a sale, and they do not join themselves:**

| store | proves | cannot say |
|---|---|---|
| access log (paths, status codes, user-agents) | traffic happened | whether anything was **paid** — a `402` and a `200` are free to produce |
| the chain (inbound token transfer to `payTo`) | **money arrived**, how much, from whom, when | **which endpoint earned it** — a transfer carries no service identifier |

**Rule: never report a count of `402`s or a count of `200`s as revenue evidence.** A `200` may be a free route or a monitor; a `402` is a refusal. The only revenue proof is the chain.

---

## Procedure — find and decode an inbound payment

1. **Read the token's `Transfer` logs filtered on the recipient.** Filter by `address` = the **token contract**, `topics[0]` = the ERC-20 `Transfer` signature hash, and `topics[2]` = the receiving address zero-padded to 32 bytes (`0x` + 24 zeros + the 40-hex address). The recipient filter is what makes this cheap.

2. **⚠️ Chunk the block range, and re-split on the error.** Public RPCs cap `eth_getLogs` ranges and the caps differ wildly per host and per chain — do not assume one number. A range error (`block range too large: … exceeds the maximum of N blocks`) is **a cap, not a failure**: re-split smaller and loop. A bounded backward walk from the chain tip in fixed-size chunks finds a recent event in a handful of calls:

   ```bash
   RPC=<chain rpc>
   TOKEN=<erc20>
   PAYTO=<our payTo>
   TIP=$(curl -s -X POST "$RPC" -H 'content-type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' \
     | python3 -c "import sys,json;print(int(json.load(sys.stdin)['result'],16))")
   # walk back in chunks, halving the chunk on a range error
   curl -s -X POST "$RPC" -H 'content-type: application/json' \
     -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getLogs\",\"params\":[{\"fromBlock\":\"0x$(printf %x $LO)\",\"toBlock\":\"0x$(printf %x $HI)\",\"address\":\"$TOKEN\",\"topics\":[\"0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef\",null,\"0x000000000000000000000000${PAYTO:2}\"]}]}"
   ```

3. **Decode — and separate the PAYER from the EXECUTOR.** `topics[1]` is the token sender (the buyer). `data` is the amount in the token's decimals (USDC = 6). **These are not always the transaction's sender:** when the payer is a smart-contract account, `eth_getTransactionByHash.from` names a **relayer/bundler**, not the buyer. A transaction whose `input` starts `0x82ad56cb` is Multicall3 `aggregate3` — a bundled call. Report the buyer from the **log** and the executor separately; naming the executor as the customer is a wrong answer with the right shape.

4. **Confirm the timestamp against the human's own view.** `eth_getBlockByNumber` for the event's block → compare against the timestamp the user reports from their wallet. A minute-level match turns "money moved somewhere" into "this is the event you saw."

5. **Check for a repeat payer before calling it new business.** Grep the vault for the payer address. A wallet that already paid months earlier is a **returning customer**, which is a materially stronger finding than a first sale — and it may exist in an old snapshot even when no live record names it.

---

## ⚠️ The attribution limit — state it, do not paper over it

A chain proof and a service attribution are **two different claims** and only the first is available from the chain:

- ✅ *"A payment of N landed at `payTo` at time T from address X"* — proven.
- ❌ *"Endpoint Y earned it"* — **UNPROVEN** unless the service recorded something at write time that joins the request to the payment.

The join is the hard part: the ledger and the chain are separate, the payment may arrive out-of-band, and x402 has **no accounts** — the payer is a wallet, not a user — so "most popular endpoint" is not answerable by counting requests. **What makes it answerable is recording, at the moment of serving a paid request, an identifier that the settlement can be matched back to.** Until that exists, report the two facts separately and never blend them into one sentence.

**Consequence for reporting:** *"we were paid"* and *"here is what sold"* are answered by different instruments. Say which one you have.

---

## Headers that make a join possible

- The client's payment proof arrives in **`PAYMENT-SIGNATURE`** (accept the legacy `X-Payment` alias too, but **document and teach `PAYMENT-SIGNATURE`** — publishing the legacy name in buyer-facing docs teaches the wrong header).
- The server emits **`PAYMENT-RESPONSE`** with settlement details — and the v2 spec requires it *"after attempting settlement, whether successful or failed,"* so a **failed settlement refusal owes the buyer a receipt too**. Otherwise a compliant client cannot tell *"you did not pay"* from *"we could not settle."* Make such a header change **additive only**: it may add a header, never alter a status code, and an encoding failure must be swallowed rather than allowed to break a refusal.

## Discovery is not attribution

Being listed in a directory or a registry does **not** tell you which listing produced a payment. Treat "where did this buyer find us?" as an open question with its own investigation — a wrong rail choice by the payer is a **clue** (they chose the network our listing on that chain advertised), not a conclusion.
