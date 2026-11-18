# On-Chain Position Forensics (no SDK, no indexer key, no web3 libs)

Establishing what actually exists on-chain when the question is "is there anything there, is it still
open, and when was it last touched" — and there is no config file, no API key and possibly no web3
tooling installed.

## 0. Read the chain from the standard library

A raw JSON-RPC `eth_call` over `urllib` needs nothing but `json`. Check whether a hashing library is
installed before writing code that imports one; if it is not, hard-code the selector — every selector
below is tabulated on purpose, precisely so nothing has to be derived at the moment of an
investigation.

```python
import json, urllib.request
RPC = "https://api.avax.network/ext/bc/C/rpc"
def call(to, data):
    req = urllib.request.Request(RPC, data=json.dumps(
        {"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}
    ).encode(), headers={"content-type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))["result"]

# ERC-20 balance, ERC-1155 bin balance, native balance
call(TOKEN, "0x70a08231" + addr[2:].rjust(64, "0"))
call(PAIR,  "0x00fdd58e" + addr[2:].rjust(64, "0") + format(bin_id, "064x"))
rpc("eth_getBalance", [addr, "latest"])
```

## 1. Selectors worth memorising

| Call | Selector |
|---|---|
| ERC-20 `balanceOf(address)` | `0x70a08231` |
| ERC-1155 `balanceOf(address,uint256)` | `0x00fdd58e` |
| ERC-1155 `balanceOfBatch` | `0x4e1273f4` |
| `totalSupply()` | `0x18160ddd` |
| LB pair `getActiveId()` | `0xdbe65edc` |
| LB pair `getBinStep()` | `0x17f11ecc` |
| LB pair `getBin(uint24)` | `0x0abe9688` |
| ERC-1155 `TransferBatch` topic0 | `0x4a39dc06…` |

## 2. An empty wallet does NOT mean a closed position

LP capital lives in the pair's **bins**, not in the wallet's token balances. A wallet holding only a
little gas and a dollar of stablecoin can still own a fully deployed position. Reporting "the wallet is
empty" from a balance check alone is a false negative that reads as a confident answer.

Probe the pair per bin:
```
balanceOf(address,uint256) -> 0x00fdd58e   # on the LB pair, one call per bin id
```

A bin balance of `0` is a real answer. An unqueried bin is not evidence.

## 3. Last-touched time without an Etherscan API key

Routescan serves an Etherscan-compatible API with no key:
```
https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?module=account&action=txlist&address=<addr>&page=1&offset=25&sort=desc
```

Classify each row by `to` + `input[:10]`: a position-manager/router address means a position action;
`0x095ea7b3` is an approval; `0x2e1a7d4d` is a WAVAX unwrap.

**Do NOT use `action=tokennfttx` to prove a position is absent.** Per-bin LP positions are ERC-1155
tokens that the NFT endpoint does not index, so it returns `[]` even while bins are held — the false
negative that matters most, because it looks like a clean "no position found".

## 4. Deposit vs withdrawal from logs, with no ABI

An LB add or remove emits ERC-1155 `TransferBatch` on the pair (topic0 `0x4a39dc06…`):
`topics[1]` = operator, `topics[2]` = from, `topics[3]` = to; `data` carries `ids[]` then `amounts[]`
— the bin ids, which is how the deployed range is located without guessing it.

- `from == 0x0…0` → mint = **add liquidity (deposit)**
- `to == 0x0…0` → burn = **withdraw**
- wallet → wallet → transfer

This distinguishes "position opened" from "position closed" from first principles, with no protocol
SDK.

## 5. Do not brute-force a bin range against a public RPC

Public Avalanche RPC returns HTTP 429 on a tight per-bin loop and 500s on a large JSON-RPC batch. A
few-hundred-bin scan that dies partway **looks exactly like "no bins held"** at the end. Take the
deployed range from the logs (§4) or `getBin(uint24)` per bin, and space the calls out.

## 6. Validate a hand-encoded multi-call against a single-call control

A malformed `balanceOfBatch` (`0x4e1273f4`) encoding does not revert — it returns an **all-zero
array**, indistinguishable from a genuinely empty position. Before trusting any batch result, call
the single-item selector (`0x00fdd58e`) for one id there is independent reason to believe is
non-zero. Single call non-zero + batch zero means **the encoding is wrong, not the position**.

The control generalises to any hand-rolled aggregate call: an all-zero success is the most dangerous
shape of response there is, because it is indistinguishable from a real empty state.

## 7. Reporting

Give the address, the venue, whether the position is open, the last-touched timestamp, and how the
value is distributed (wallet liquid vs held in bins). Distinguish what was **read live** from what was
inferred, and never state a position is gone on the strength of a balance check alone.
