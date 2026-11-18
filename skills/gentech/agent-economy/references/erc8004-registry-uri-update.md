# Updating an ERC-8004 agent's on-chain metadata URI

**Goal:** change the `metadata_uri` a directory reads for one agent token, and PROVE the new
URI serves parseable JSON before a human signs anything.

## The registry is an upgradeable PROXY — this is the trap

`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (ERC-8004 Identity Registry, CREATE2 — same
address on many chains) is a **UUPS proxy**: a ~130-byte contract that `delegatecall`s into an
implementation.

**The proxy holds the DATA; the implementation holds the CODE.** So:

> **Calling the write function on the IMPLEMENTATION address mines a transaction, costs gas,
> emits an event, and changes NOTHING about your token.** A transaction that mined is not a
> change that took effect.

Where the explorer shows no Write tab on the proxy, that is the signal to look for
**"Write as Proxy"** — never to switch to the implementation address.

## Step 1 — confirm the function exists, before anyone signs

Never trust a function name from a doc (including this one). Read the implementation's ABI:

```bash
C=0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
RPC=https://avalanche-c-chain-rpc.publicnode.com

# EIP-1967 implementation slot -> the implementation address
SLOT=0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc
curl -s -X POST "$RPC" -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getStorageAt\",\"params\":[\"$C\",\"$SLOT\",\"latest\"]}" \
  | python3 -c "import sys,json;r=json.load(sys.stdin)['result'];print('0x'+r[-40:])"

# that implementation's verified ABI (no API key needed on routescan/snowtrace V1 shape)
curl -s "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?module=contract&action=getabi&address=$IMPL" \
  | python3 -c "import sys,json;abi=json.loads(json.load(sys.stdin)['result']);\
print([(f['name'],[i['type'] for i in f.get('inputs',[])],f.get('stateMutability')) for f in abi if f.get('type')=='function' and 'URI' in (f.get('name') or '')])"
```

**Expected on this registry:** `setAgentURI(uint256,string)` (nonpayable) + event
`URIUpdated(uint256,string,address)`, plus the `tokenURI(uint256)` view.

⚠️ **`setTokenURI` does NOT exist on this implementation.** An earlier version of this note named
it; it was wrong. Confirm from the ABI every time — a wrong function name fails at signing, or
worse, silently reverts.

**No local toolchain needed for any of this** — it is `curl` + public RPC + an explorer API. The
same recipe answers "does this function exist, with what signature and mutability" for any
deployed contract, which is what you need before asking a human to sign.

## Step 2 — capture the BEFORE value, so the change is provable

The whole write is one field; without a before/after you cannot show it worked.

```bash
# tokenURI(agentId) - selector 0xc87b56dd + left-padded id
curl -s -X POST "$RPC" -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$C\",\"data\":\"0xc87b56dd$(printf '%064x' 1770)\"},\"latest\"]}" \
  | python3 -c "import sys,json;h=json.load(sys.stdin)['result'];\
off=int(h[2:66],16)*2+2;ln=int(h[off:off+64],16)*2;print(bytes.fromhex(h[off+64:off+64+ln]).decode())"
```

Also useful for attribution: `ownerOf(id)` (`0x6352211e`) and `balanceOf(address)` (`0x70a08231`).
**The registry is not enumerable** — `totalSupply()` / `tokenOfOwnerByIndex()` revert — so find your
token id from records or from the URI you expect, not by listing holdings.

**Confirm the signing wallet holds the token AND has gas** before asking for a signature:
`eth_getBalance` on the owner. A write is ~50–80k gas; check it, don't discover it at signing.

## Step 3 — point it at a URI that serves JSON, not a web page

⚠️ **The URI must return `Content-Type: application/json` and PARSE. A `200` is not enough.**
A host whose SPA fallback answers every path returns `200 text/html` for a path that 404s — the
directory fetches it, cannot parse, and renders the agent's skills/domains **blank while the
description still shows**. An apex that serves `/.well-known/*` from a static site is the usual
culprit.

Check it the way that catches this, **before** the write:

```bash
curl -s -o /dev/null -w 'http=%{http_code} type=%{content_type}\n' "$URL"     # want application/json
curl -sL "$URL" | python3 -c 'import json,sys; json.load(sys.stdin); print("VALID JSON")'
```

**And a valid JSON can still be a lie.** A hosted copy that parses can still list services you
cannot deliver. **Generate the published metadata from the same inventory your service gate uses**
so an unavailable item cannot appear, and record the withheld ones *with reasons*. A directory
entry is an advertisement.

## Step 4 — the write (human-signed)

**Preferred: the contract UI.** Open the **proxy** address page → Contract → **Write as Proxy** →
`setAgentURI`:

```
agentId   1770
newURI    https://<host-that-serves-json>/<metadata>.json
```

Connect the owner wallet and sign.

**Alternative: direct call (Python).** Use only when a UI is unavailable; the key must never be
pasted into chat or a shared file — the operator places it in a local file the script reads.

⚠️ **Prefer the surface where the key never touches the server, and say so as a recommendation.**
A browser wallet extension on a machine the operator controls is not a fallback — it is the better
answer, because a personal wallet key written to a file on a shared host is a standing liability.
Measured: exporting a personal-wallet key to a file on the VPS to satisfy this one write ended with
key material in a chat log (via the signing script's own refusal path) and a server-side cleanup.
One metadata URI is not worth that.

⚠️ **If the operator cannot obtain the key — which is normal and correct for a modern wallet app —
the task is BLOCKED, not failed.** Everything else stays shipped (the JSON route, the corrected
metadata, the ABI verification). File it as pending with the exact remaining call and the preferred
surface, and move on. **Do not coach a user into exporting a personal wallet's private key.**

### If you do build a signing script, these four guards are the minimum

1. **Read the key from a FILE, never argv** (argv lands in shell history and `ps`), and never print it.
2. **Extract the value** (`(?:0x)?([0-9a-fA-F]{64})`) — wrapped pastes (`<key>`, quotes) are a
   formatting problem, not a wrong key. Then **verify the derived address equals the expected owner**
   and refuse otherwise. **Extraction cannot make a wrong key look right; the identity check is the guard.**
3. **Default to `--dry-run`**; broadcasting needs an explicit flag. Print the decoded args and the
   signed txid, broadcast nothing.
4. **Redact hex runs out of every error message.** Libraries include the offending input in their
   exceptions (`invalid hexlify value (… value="<0x…")`) — a validator that refuses a bad key must not
   print the bad key.

```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(RPC))
contract = w3.eth.contract(address=PROXY, abi=[{  # abi from Step 1, not from memory
    "inputs": [{"internalType":"uint256","name":"agentId","type":"uint256"},
               {"internalType":"string","name":"newURI","type":"string"}],
    "name": "setAgentURI", "outputs": [], "stateMutability": "nonpayable", "type": "function"}])
txn = contract.functions.setAgentURI(1770, NEW_URI).build_transaction({
    "from": owner, "nonce": w3.eth.get_transaction_count(owner),
    "gas": 100000, "gasPrice": w3.eth.gas_price})
```

**If the local interpreter lacks `web3`/`eth_account`, do not install on the host to save a step —
check a container image you already run, or hand the UI path to the operator.** Discovering that
`web3` is absent is environment state, not a rule about the technique.

## Step 5 — verify on-chain, not via the directory

```bash
# re-run the Step 2 tokenURI read; expect the NEW uri
```

Then re-fetch that URI and **parse it** (Step 3 checks). An explorer's own "read" tab and the
directory's listing are both caches with unknown refresh; **`tokenURI` from the chain is the only
ground truth that the write landed.**

⚠️ **Do not verify through the directory's API.** It can be rate-limited, geo-blocked, or hang
indefinitely while every other path on the same host answers instantly — a hang is not a `404`,
and neither is evidence about your write. Verify the chain, then verify the URL's content.

## Registry addresses

| chain | proxy |
|---|---|
| Avalanche C-Chain | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (impl `0x7274e874ca62410a93bd8bf61c69d8045e399c02` at time of check) |

**Re-read the EIP-1967 slot each time — an implementation address is a moving target after an
upgrade. A cached impl address is a stale pointer.**
