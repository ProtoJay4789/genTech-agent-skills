# Proving a payment landed — and attributing it

For the question *"did we actually get paid, by whom, and for what?"* The chain is the only
witness: a payment arrives out-of-band and the request log carries no account, so a payer's
address usually appears in the traffic log **zero times**. Prove it on-chain, not from logs.

## 1. Find the transfer by scanning the token's logs for the recipient

`eth_getLogs` with a filter on the token contract and the **third** topic (topic[2] = `to`):

```json
{"method":"eth_getLogs","params":[{
  "fromBlock":"0x…","toBlock":"latest",
  "address":"<token contract>",
  "topics":[
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    null,
    "0x000000000000000000000000<recipient, lowercased, no 0x>"
  ]}]}
```

The first topic is the canonical `Transfer(address,address,uint256)` signature. Leave topic[1]
(`from`) as `null` to catch every sender.

## 2. Chunk the range — a wide window is refused, not slow

Public RPCs cap the **block range per request**, and the cap is low and per-provider (measured
100 blocks on an Avalanche C-Chain public RPC; others differ). A request wider than the cap
returns a JSON-RPC error, **not** an empty result:

> `block range too large: total block range in this request exceeds the maximum of 100 blocks`

Walk **backwards** from the tip in cap-sized chunks and stop when you have the event. Do not
report "no transfers found" from a single wide request — that is a refusal read as a negative.

**Estimate the range from time, not from a guess:** a chain's block time converts "the payment
arrived 20 minutes ago" into a block window. Scanning a bounded window back from the tip finds a
recent event in a handful of calls.

## 3. The log's `from` is NOT the transaction's `from`

A batched payment has two different senders, and conflating them misattributes the money:

| field | who it is |
|---|---|
| the tx's `from` | the **executor** — a relayer, bundler, or smart-account entrypoint |
| the Transfer log's topic[1] | the **actual paying account** — attribute to this one |

**The tell is the input selector.** `0x82ad56cb` is `aggregate3((bool,bytes)[])` on the
canonical **Multicall3** contract (`0xcA11bde05977b3631167028862bE2a173976CA11`): one transaction
carrying several calls. A high nonce on the executor plus a multicall wrapper means an
**automated payer**, not a person clicking send — which is a materially different signal about
the buyer than the amount is.

## 4. Before quoting an amount

- **Apply the token's decimals.** USDC is 6, so a base-unit `10000` is `0.01`. A raw integer
  quoted as an amount is wrong by six orders of magnitude.
- **Read the amount from the log's `data`**, not from a wallet UI. A phone screenshot is a
  prompt to go and check, never the measurement itself.
- **Cross-check the time** by decoding the block timestamp — it is the independent confirmation
  that you are looking at the same event the human described.

## 5. What a payment does and does not prove

- **It proves money moved. It does not prove the service ran.** Settlement can precede delivery:
  a gateway that settles first and proxies second has already been paid when the backend refuses
  the connection. *"Paid twice for a route with nothing behind it"* is a coherent, reachable
  state — see the 402 rule in this skill and in `service-health-monitoring`.
- **It does not identify the product.** With no accounts in the protocol, the payer is a wallet,
  so joining a chain event to a specific request is a separate (harder) problem. Say the service
  is **unknown** rather than inferring it from the amount — an amount that matches no published
tier is a finding, not noise to be rounded into one.

## 6. Public RPCs fail per-request; try a second endpoint before concluding

A single public endpoint can rate-limit, 429, or return a Cloudflare error page for one call and
answer the next. **A parse failure is not a "no data" result.** Retry, then try a second
provider, and only then report the negative. Record which endpoint answered, because a cap is a
property of the provider.
