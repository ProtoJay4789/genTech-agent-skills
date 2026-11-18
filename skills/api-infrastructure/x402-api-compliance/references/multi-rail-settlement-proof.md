# Proving a rail you advertise — one chain at a time, by chain state

A challenge that lists five rails is an advertisement for five doors. **One proven rail proves one door.**
`payment-path-proof.md` covers proving the payment path; this file covers proving *each rail* of a
multi-chain gateway, where the failure mode is subtler: the client silently settles on a different chain
and reports success.

## Procedure

### 1 · Read the rail list from the challenge, not from config

The gateway's env and the manifest can both be stale. Decode the live challenge — it is what a buyer sees:

```bash
curl -s -D - -o /dev/null "https://<host>/v1/<paid-route>" \
  | grep -i 'payment-required' | sed 's/^[Pp]ayment-[Rr]equired: //' | tr -d '\r' \
  | base64 -d | python3 -c "import json,sys; [print(a['network'], a['payTo'][:12], a['amount']) for a in json.load(sys.stdin)['accepts']]"
```

That list is your test matrix. Anything advertised and untested is a promise, not a capability.

### 2 · Prove the provider supports each advertised network BEFORE paying

```bash
curl -s https://<facilitator>/supported | python3 -c "
import json,sys
for k in json.load(sys.stdin).get('kinds',[]): print(k.get('x402Version'), k.get('scheme'), k.get('network'))"
```

A rail is settleable only when **network + scheme + protocol version all match** what your challenge emits
(e.g. `eip155:56` / `exact` / `2`). A `200` on `/supported` that lists the network under a *different* version
is not coverage.

### 3 · ⚠️ Register ONLY the target rail in the client

**This is the trap that makes a rail test lie.** An SDK handed several registered schemes selects from the
challenge's `accepts[]` in order — usually `accepts[0]` — so testing "Avalanche" while Base is also registered
tests Base, returns `200`, and proves the rail you already proved. Measured exactly that way: a first
"Avalanche" run settled on Base.

```python
schemes = [SchemeRegistration(network="eip155:43114", client=ExactEvmScheme(signer=acct))]
#          ^ one entry, the rail under test. Registering Base here silently wins.
```

Register one network, run, read the receipt's `network` field, and **assert it equals the rail you meant**.
A receipt naming a different chain is a failed test, not a pass.

### 4 · Verify settlement on THAT chain — three independent reads

Do not trust a single signal; on non-Base rails the response can look emptier than the outcome:

| read | what it proves |
|---|---|
| receipt header (`payment-response`) | gateway's claim — may be **absent on non-Base rails even when settlement succeeded** |
| **payer balance delta** on that chain | money left |
| **payTo balance delta** + `Transfer` log | money arrived, and the hash to cite |

```python
# balance of an ERC-20 for an address on a specific chain, via a public RPC
call = {"to": USDC_ON_THAT_CHAIN, "data": "0x70a08231" + "0"*24 + addr[2:].lower()}
balance = int(rpc("eth_call", [call, "latest"]), 16) / 10**decimals
```

Read **before and after**, on both addresses. `payer -0.001 / payTo +0.001` is a settlement; a moved payer
balance with a flat payTo is a misrouted payment; both flat is no payment at all.

Then fetch the log to name the transaction:

```python
logs = rpc("eth_getLogs", [{"address": USDC, "fromBlock": hex(head - 40), "toBlock": hex(head),
                            "topics": [TRANSFER_TOPIC, payer_topic, payto_topic]}])
# cite: transactionHash, blockNumber, amount
```

**A missing receipt header on a working rail is itself a defect to report** — a buyer's client that reads that
header to confirm success will conclude the payment failed while the money moved.

### 5 · Know what the payer needs on that chain

With EIP-3009 (`exact` scheme) the **facilitator submits the transfer**, so the payer needs **no native gas** —
only the token. Proven: a settlement on Base and another on Avalanche both completed from a wallet holding
**0 native coin**.

So the funding arithmetic per rail is the token, and only the token:

- **EVM rails** — the chain's USDC. No gas.
- **Solana** — USDC **plus a little SOL**, because the payer's associated token account has to exist.
- **Algorand** — USDC **plus an ASA opt-in**, which is a separate transaction before the first payment; and
  check the facilitator actually lists Algorand, because a facilitator that covers the EVM rails may not.

Fund the payer wallet once, with headroom for a retry — a rail that needs a second funding trip is a rail that
does not get retested.

## Pitfalls

- **A `200` from a different chain than the one under test is the default failure**, not an unusual one. Assert
  the receipt's `network` field every time.
- **Do not infer rail coverage from a config file or a code registry.** Read `/supported` for what the facilitator
  settles, and the live challenge for what you advertise; a registry that omits a network you actually serve is a
  stale constant, and a network in the registry with no facilitator is an unpayable promise.
- **`payTo` reuse across EVM chains is correct, not a bug.** One wallet address is valid on every EVM chain; the
  same address in three `accepts[]` entries means one wallet, three chains. Before calling it a configuration
  error, read the runtime env (`docker exec <c> env | grep -E '^<PREFIX>_'`) — code defaults and runtime values
  are different facts, and only one of them is live.
- **Settlement does not imply delivery.** Confirm the response **body** is the service's data on the rail you just
  proved; a redirect or an error envelope after settlement is the charge-then-redirect defect.
- **Count the rails, not the calls.** Four settled calls on one chain is one rail proven; say "N rails proven"
  with the chain names, never "payments working" from a single chain.
- **A self-funded payer is a door test, not revenue.** Every rail proven from your own wallet belongs in the
  self/test exclusion line; reported revenue stays zero until a wallet you do not control pays.

## Reporting shape

Give per rail: chain · settled yes/no · transaction hash · amount · balance delta · body delivered. One line
each, and state which rails remain unproven and what they are waiting on (funding, opt-in, facilitator support).
That table is the difference between "we support five chains" and "we have proven two".
