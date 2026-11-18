# Adding a settlement rail — measured procedure, never a copy-paste

A rail is real only when a buyer on that chain can sign a payload our facilitator can settle and we can verify.
Adding a chain id to an array satisfies none of those. This is the order that works.

## 0 · Record the ASK before you measure anything

**Keep a register of rails somebody actually wanted, with their name against the row.** A named request is the only
thing that separates a rail worth building from a chain that merely exists, and the register is what answers *"are
you available on X?"* later without re-deriving it from memory.

- **One row per rail:** who asked and where (comment, DM, issue, the boss's word), the date, what it needs, status.
- **Answer from the table, not from recollection.** If the answer is *no*, the asker's name goes on the list —
  *"not yet, and you are the reason it is on the list"* is an honest answer; *"I think so"* is not.
- **A rail can be wanted for weeks while you believe you already support it.** Carrying a HOWTO page, a skill, or a
  listing story for a chain is not a rail: **check `accepts[]` for that network id** before answering yes.

## 1 · Confirm the facilitator BEFORE writing config

```bash
curl -s https://<facilitator>/supported | jq '.kinds[] | select(.network=="<CAIP-2>")'
```

A facilitator that does not list the network cannot settle it, whatever its marketing page says. Prefer at least
two settlers for the same network, so one outage is not one lost rail.

## 2 · Take the token address from the facilitator, then verify it independently

The `/supported` payload usually carries the asset in `extra.assets[].address`, sometimes with `min`/`max` in atomic
units. Use that address, then confirm it is the token you think it is — a facilitator can advertise a proxy.

Probe the chain's RPC directly:

    eth_chainId()   -> must equal the numeric part of the CAIP-2 id
    name()          -> ABI-encoded string: decode offset+length, do not strip nulls blindly
    symbol()
    decimals()      -> decides your amount: accepts[].amount is ATOMIC units

A $0.002 charge on a 6-decimal token is `"2000"`, not `"0.002"`.

## 3 · DERIVE the EIP-712 `version` — never guess it

`accepts[].extra` IS the EIP-712 domain the client signs against. A wrong `name` or `version` yields a payload the
facilitator rejects, and the client cannot distinguish that from choosing not to pay. This is the most expensive
field on the rail.

Derive it by reproducing the token's own separator:

```python
from eth_utils import keccak
from eth_abi import encode

T1 = keccak(b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
for ver in (b"1", b"2", b"1.0"):
    d = keccak(T1 + encode(["bytes32","bytes32","uint256","address"],
                           [keccak(name.encode()), keccak(ver), chain_id, asset]))
    if d == onchain_domain_separator:      # eth_call 0x3644e515
        print("version =", ver)
```

If nothing matches, the token uses a different domain shape (a salt, or a non-standard type string) — treat that as
a stop sign: the token may not support the scheme, and the rail should not be advertised until it does.

## 4 · Write the entry, then gate it

    {"scheme":"exact","network":"eip155:<id>","asset":"0x…","amount":"<atomic>",
     "payTo":"0x…","maxTimeoutSeconds":300,
     "extra":{"name":"<exact name()>","version":"<derived>","assetTransferMethod":"eip3009"}}

Gate it: a rail must be DROPPED, not advertised, when its payTo is unset. `os.getenv(var, default)` returns the
default only when the var is UNSET — an empty-string env var silently yields an empty payTo, advertising a rail
nobody can pay.

One settlement address per operator is usually correct. Routing revenue to extra addresses nobody watches is how it
gets lost; split only for a real accounting reason.

### 4a · Enable it by FILE when the container's environment is expensive to change

**An env var that drives the rail list is a soft dependency on container creation.** On a container created by hand
(`docker run`, no compose project label), changing one env var means deleting and recreating it from a reconstructed
command — on the process every buyer route depends on. That is how a working container becomes an orphan.

So give the rail list a **file** the process reads at start, searched in order, ahead of the env var:

```python
candidates = [os.getenv("RAILS_FILE", '/data/.networks'),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), ".networks")]
path = next((c for c in candidates if os.path.exists(c)), None)   # absent -> "" -> fall back to env
```

- **Search BOTH the data volume and the directory beside the module.** A container mounts its app dir from the
  repo and its `/opt/data`-style path from an **anonymous docker volume** — so a file written to the HOST's
  `/opt/data` is often invisible inside, while the copy beside the module is seen. Shipping only one path produces
  a setting that silently does nothing.
- **Enabling a config file is not the same as enabling a rail:** the file changes nothing until the process
  restarts, and a rail is not live until `accepts[]` shows it. Verify the served challenge, never the file.
- **Keep the file's contents minimal and obvious** (one name per line, `#` comments) — an operator re-reads it far
  more often than the code that loads it.

## 5 · Add the verify/settle dispatch branch BEFORE advertising

A multi-rail gateway routes a proof by its network. A rail with no branch falls through to the default verifier,
which either simulates (accepting a proof that never settled) or rejects a valid one.

Advertising a rail before its verify branch exists is the worst outcome available: the buyer pays and gets nothing.
Order: branch, then advertise, then prove.

**Write ONE verifier, parameterised by facilitator base URL — not one per facilitator.** Every standard facilitator
speaks the same `{x402Version, paymentPayload, paymentRequirements}` envelope to `/verify` and `/settle`, so a second
copy of the money path is a second behaviour waiting to drift. Extract `verify_via_facilitator(proof, price, base,
label)` and point every rail at it; a per-rail wrapper should be four lines, not four hundred.

- **Confirm the envelope exists before writing the branch:** `POST {base}/verify` with an empty body. A `400`
  complaining about missing `paymentPayload`/`paymentRequirements` means the endpoint is real and standard; a `404`
  means this facilitator is not shaped like the others and needs its own reading.
- **Test equivalence, not just the happy path.** Feed the SAME two bad inputs — a proof naming an unadvertised
  network, and a malformed proof — to the new verifier and to the one that already worked, and assert both refuse
  with the same reason. That is the cheap proof that extracting the shared path did not change the old rail.
- **Fallback order is a fail-closed decision, not a retry:** only fall through to the second facilitator on
  *unreachable*, never on *invalid*. A rejection is an answer, and re-asking a different facilitator about the same
  rejected proof is how one payment becomes two.

## 6 · Prove it with one real paid call, and read the receipt on chain

Pay the endpoint from a funded wallet on that chain, capture `PAYMENT-RESPONSE`, then confirm the transaction:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionReceipt","params":["<tx>"]}' <chain-rpc>
```

Expect `status: 0x1` and an ERC-20 `Transfer` of the right amount to your payTo. Until that exists the honest
status is "rail written, not receiving" — not "we accept payments on that chain".

## Pitfalls that cost real money

- Do not lead `accepts[0]` with the newest rail. Blind clients sign the first entry; lead with the rail the widest
  set of clients can sign and let exotic rails follow.
- Token names must match byte for byte, including currency symbols and spacing. Copy from the contract's `name()`,
  never from a UI.
- Implicit `assetTransferMethod` defaults are not portable. If the token needs Permit2 rather than EIP-3009, say so
  in `extra`, or clients default to a method the token cannot execute.
- Being able to READ a chain is not having a rail on it. Reading prices there and settling there are separate
  achievements, and a docs page listing the chain is evidence of neither.
- A rail enabled by env var is a rail tied to container creation. If recreating the container is risky, read the
  rail list from a file on a mounted path instead — and check BOTH the data path and the module-adjacent path,
  because one of them is usually an anonymous volume.
