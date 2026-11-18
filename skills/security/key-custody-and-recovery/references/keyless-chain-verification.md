# Keyless chain verification — what still exists, with no key and no API key

Use during any custody or recovery investigation: you have addresses, you have no keys, and you need
verifiable balances plus the history of what each wallet did.

## Wallet history — keyless Etherscan-compatible indexer

Routescan serves an Etherscan-compatible API **with no API key**, which is far cheaper than scanning
`eth_getLogs` in 2048-block chunks. `txlist` returns `input` (method selector), `to`, `timeStamp`,
`gasUsed` and `isError` per transaction — enough to date a wallet's last real activity.

```python
base = "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api"  # 43114 = Avalanche
api({"module": "account", "action": "txlist", "address": ADDR,
     "page": "1", "offset": "25", "sort": "desc"})
```

Other chain ids slot into the same path (`8453` Base, `42220` Celo, `1` Ethereum). Useful `action`
values: `txlist`, `txlistinternal`, `tokentx` (ERC-20), `tokennfttx`.

Read `input[:10]` to identify an operation with no ABI. For LFJ, `0xa3c7271a` on the router is an
add/remove-liquidity call; the pair is visible in that transaction's receipts.

## Native + ERC-20 balances

```python
rpc("eth_getBalance", [addr, "latest"])                      # wei → /1e18
rpc("eth_call", [{"to": TOKEN, "data": "0x70a08231" + addr[2:].lower().rjust(64, "0")}, "latest"])
```

Public endpoints verified to answer `eth_blockNumber` and `eth_call`:

| Chain | Working endpoint |
|---|---|
| Avalanche | `https://api.avax.network/ext/bc/C/rpc` |
| Base | `https://base-rpc.publicnode.com` |
| Celo | `https://celo-rpc.publicnode.com` |

**Always hold a fallback list and keep the first endpoint that answers `eth_blockNumber`.** A quiet
endpoint can return *nothing* — no exception, no error body — which reads exactly like a zero
balance. When reporting a multi-chain census, confirm each chain answered or mark that row unknown.

## LFJ bin shares — literal selector, no keccak, no library

`balanceOf(address,uint256)` is `0x00fdd58e` and encodes by hand:

```python
data = "0x00fdd58e" + holder[2:].lower().rjust(64, "0") + format(bin_id, "064x")
rpc("eth_call", [{"to": PAIR, "data": data}, "latest"])
```

This answers over plain `eth_call` on the live V2.2 pair; do not assume a proxy revert requires a
Node/viem reader until you have actually seen one.

**Never sweep bin ids.** A 512-call JSON-RPC batch answers HTTP 500 and a few hundred sequential
calls answer 429, and a swept range that times out loses every result. Derive the bin set from the
wallet's own events and probe only those.

## Which bins moved, and in which direction

```python
rc = rpc("eth_getTransactionReceipt", [tx_hash])
for log in rc["logs"]:
    if log["address"].lower() != PAIR.lower():
        continue
    if log["topics"][0][:18] == "0x4a39dc06d4c0dbc6":      # ERC-1155 TransferBatch
        op, frm, to = ("0x" + t[-40:] for t in log["topics"][1:4])
        # from == 0x0 → mint (deposit) · to == 0x0 → burn (withdraw) · otherwise a transfer
```

Bin ids live in `data` (ABI: offset, length, ids[], values[]). Filter to the pair's own logs — a
router transaction emits several events and only the pair's are position movements. `TransferSingle`
is `topic0 0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62`, with
operator/from/to in topics 1-3 and `(id, value)` in `data`.

## Reporting a census

One row per wallet: label, chain, full address, native balance, known token balances, last activity
date. State the total in dollars. This table is what makes "what did we actually lose" a fact rather
than a feeling — and it is the artifact to hand the operator before any recovery attempt.
