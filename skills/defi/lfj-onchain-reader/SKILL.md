---
name: lfj-onchain-reader
description: Read LFJ V2.2 LP positions from on-chain data using correct keccak256 selectors
---

# LFJ On-Chain LP Reader

Reads live wallet + LP position from Avalanche blockchain for LFJ V2.2 pools.

## CRITICAL: Keccak256 vs SHA3-256

Python's `hashlib.sha3_256()` is **NOT** Ethereum's keccak256. They are different hash functions. NIST standardized SHA-3 differs from the original Keccak that Ethereum uses.

**Wrong (will revert every call):**
```python
import hashlib
selector = hashlib.sha3_256(b'getActiveId()').hexdigest()[:8]  # 0x80afabfa ❌
```

**Correct:**
```python
from Crypto.Hash import keccak
selector = keccak.new(digest_bits=256, data=b'getActiveId()').hexdigest()[:8]  # 0xdbe65edc ✅
```

## Correct Selectors for LFJ V2.2

⚠️ **Do not hand-type these.** The first draft of a reader carried `getBinStep()` as `0x17e0d70c` — one hex
digit-group off from the real `0x17f11ecc` — and the adapter reverted against a live pool while looking
perfectly plausible in review. This table is here for READING; in code, derive each selector with keccak and
assert the derivation against one value in this table.

| Function | Selector |
|----------|----------|
| `getActiveId()` | `0xdbe65edc` |
| `getBinStep()` | `0x17f11ecc` |
| `getReserves()` | `0x0902f1ac` |
| `getTokenX()` | `0x05e8746d` |
| `getTokenY()` | `0xda10610c` |
| `balanceOf(address,uint256)` | `0x00fdd58e` |
| `getBin(uint24)` | `0x0abe9688` |

## Reading the pair contract safely

### A short bytecode length is a proxy, not a stub

A Liquidity Book pair may be a **minimal proxy**: a few dozen bytes of delegating code whose implementation
holds the real logic (kilobyte-scale).

- Measure size in **bytes**: `(len(code) - 2) // 2`. The `0x`-prefixed string is **hex characters**, so a
  97-byte proxy renders as 194 characters. Reporting the character count as a byte count makes a live pool
  look like a ~196-byte stub.
- If the code is short, look for a delegating pattern, read the embedded implementation address, and check
  **that** contract's size before concluding anything.
- **A revert is not proof of absence.** On a proxied pair several getters revert while the ones you need
  answer normally (`getActiveId`, `getBinStep`, `getReserves`). Try the whole selector set before deciding
  the address is wrong.
- **An address is refuted by a successful call returning nonsense — not by one failed call, and not by an
  empty log query.** Public RPCs cap `eth_getLogs` block ranges and answer `0` rather than erroring, so an
  idle-looking pool and a capped query are indistinguishable without a control (read a busy token's logs in
  the same window to prove the log path works).

### It is an LBToken, not an ERC-20 — the single-argument `balanceOf` reverts by design

A Liquidity Book pair answers `symbol()` with `LBT` and holds liquidity as **bin-keyed** balances, so the
ERC-20 shape does not exist on it.

- `balanceOf(address)` (`0x70a08231`) → **`execution reverted`**, for every wallet, always. That is not a
  failed read of a zero balance and it is not an empty position.
- The real reads are `balanceOf(address,uint256)` (`0x00fdd58e`) per bin id, or `getUserPositionIds` /
  `balanceOfBatch` to enumerate the ids first.
- **A revert is UNKNOWN, not zero.** Printing `0` because the call reverted converts "I could not read the
  position" into "the position is closed" — the exact inversion that precedes a wrong rebalance
  recommendation. Say COULD NOT READ and name the call.
- **Use a working getter as the control.** When `symbol()` and `getReserves()` answer normally in the same
  breath, the pair is reachable and only *your call shape* is wrong. A contract that answers one getter and
  reverts another is a selector problem, not a dead pool — do not conclude absence from a missing answer.

### `getReserves()` returns TWO words — decoding it as one integer invents a number

An LB pair's `getReserves()` returns `(uint128 reserveX, uint128 reserveY)` — **two ABI words**. Reading the
return as a single `uint256` concatenates both reserves and produces a 79-digit figure that looks like a
balance and is not one.

```python
words = [int(h[i:i+64], 16) for i in range(0, len(h), 64)]   # h = hex without 0x
reserve_x, reserve_y = words[0], words[1]                     # NOT int(h, 16)
```

- **Count the words before parsing any struct return.** `len(hex)//64` is the number of values; a getter that
  returns a struct gives you several and each one needs its own decode.
- **Sanity-check the size against the token decimals** (18dp vs 6dp). A reserve that renders as trillions of
  dollars is a decode error, not a whale.

### Composing a WALLET's position needs three calls per bin — and the scan window is the trap

Per bin, the composition is a share of that bin's reserves:

```python
wallet_lp = balanceOf(wallet, bin_id)     # 0x00fdd58e
total_lp  = totalSupply(bin_id)           # 0xbd85b039
rx, ry    = getBin(bin_id)                # 0x0abe9688 — two words, token X and Y reserves
share     = wallet_lp / total_lp
amount_x  = rx * share                    # then / 10**dec_x
amount_y  = ry * share                    # then / 10**dec_y
```

- **Skip a bin where `totalSupply == 0`** rather than dividing; a bin with no LP shares issued is not a
  position and a ZeroDivisionError mid-scan aborts a read that was otherwise fine.
- **`getBin()` returns TWO words**, exactly like `getReserves()` — decode both or you invent a number.

⚠️ **Scanning ±N bins around the ACTIVE bin returns "no position" for the positions that matter most.**
An abandoned or badly-out-of-range LP sits *hundreds* of bins from spot: one measured case held 25 bins
**~355 below** the active bin, so a ±60 scan correctly reported zero balances and the honest-looking result
was a false negative. **Every position carried out of range is invisible to a spot-centred scan.**

- Take the bin range as an **argument** (`--window lo hi`), and default the scan wide enough to cover the
  range the position was opened at — not the range around today's price.
- If you have the opening range from any record (config, snapshot, a prior read), scan **that** window
  first; a near-spot scan is a liveness check, never a completeness check.
- **Report the scanned window in the output.** "0 bins found in [lo, hi]" is a true statement about your
  scan; "0 bins found" without the window reads as "this wallet holds nothing" and is wrong.

### Fee parameters: `getStaticFeeParameters()` answers, `feeParameters()` reverts

On V2.2 the fee accessor is **`getStaticFeeParameters()`** (224 bytes / 7 words); the short `feeParameters()`
and `getSwapFee()` forms revert on this pair. The base fee is packed into the first word:

```python
base_factor = words[0] & 0xFFFF
base_fee_bps = base_factor * bin_step / 10_000        # e.g. 5000 * 10 / 1e4 = 5.0 bps
```

**This is the fee PARAMETER — what the pool charges per swap — not the realised 24h yield.** Volume is not a
contract read, so a rate requires history. Report the parameter as a parameter; calling it the yield is the
one invention that turns an unknown into a profitable-looking plan.

### Verify the derived price against an independent spot feed

The formula's scale factor (`1e12`) absorbs token decimals and is **easy to invert**, so a formula that runs
without error can still be wrong by the decimal offset. Compare the derived price to a spot feed at call
time and report the drift:

- **Within ~2%** → the formula's scale is right; state the drift so a reader knows it was checked.
- **Beyond it** → report a WARNING and do not let the number drive a decision. Either the scale is inverted
  or the feed is wrong, and you cannot tell which from one side.
- **A feed that is unavailable is UNVERIFIED, not OK.** Never let a missing comparison read as agreement.

### Validate a new selector before trusting it

Derive it with keccak, then confirm the derivation against a selector already proven to work on the same
contract. A match means the derivation is right and the rest of the table is trustworthy; a mismatch means
every selector you generate is suspect, so stop and re-check the hash function rather than probing addresses.

### Reading many bins without tripping the RPC

- Batch `eth_call`s as JSON-RPC arrays (~25 per request) instead of one call per bin, and space the batches.
- A public RPC answers bursts with HTTP 429. Back off; do not retry in a tight loop.
- **Rotate ENDPOINTS inside the backoff, not just sleep between retries.** Measured: a 40-bin per-bin scan
  died mid-read on one public RPC even with retries, because the same host was being re-asked. Cycling a
  small list of mirrors (`api.avax.network`, a publicnode C-chain mirror, `1rpc.io/avax/c`, another public
  mirror) on successive attempts completed the scan in one run. Index the list by attempt number and never
  re-ask the host that just refused.
- **A scan that dies mid-loop must not return a partial position.** Either retry to completion or fail loudly;
  a half-read bin set summed into a total is a smaller number wearing a measurement's clothes.
- **Validate the read against `getReserves()`**: the summed per-bin reserves should reconcile with the
  pair's total. If they do not, you are reading the wrong function or the wrong range.
- **Report coverage, not the impression of a full read.** A wide span that captures only a small share of
  total reserves means most liquidity sits far from spot — which is itself the finding, because it is what
  makes a near-spot position earn an outsized fee share.

## A lost KEY removes the ability to SIGN — never the ability to READ

Before writing off a position because its wallet is unreachable, separate the two capabilities. **Reading a
position needs only the ADDRESS; signing needs the key.** So a wallet whose key is gone still holds a position
that is fully measurable on-chain, and reporting it as "lost" or "gone" discards information that is still
true.

Measured: a wallet whose key was destroyed in a host wipe still held **25 bins** of LFJ liquidity; the position
read normally, valued at spot, and was ~355 bins out of range. The money was unreachable, not absent — and the
two are different sentences to hand an operator.

- **State `reachable` as an INPUT you were told, never a value this reader can infer.** An on-chain read cannot
  see whether a key exists; a plausible `false` invented by the tool is the same defect as a zero invented by a
  failed call.
- **"Unreachable" and "lost" are different claims.** The position exists and its composition is known; what is
  gone is the ability to withdraw. Say which.
- **The general form, beyond this venue:** ask what the missing credential actually gated before declaring the
  artifact lost. A dead API key may still leave a public read endpoint; a revoked session may still leave the
  resource publicly enumerable.
- **A position carried far out of range is a pure one-sided holding** — `amount_y: 0.0` with every bin below spot
  means the book sold the quote token entirely on the way down, and reporting it as "a position" without saying
  so reads as a working LP when it is now a naked long.

## Price Formula

```python
SHIFT = 2**23  # 8,388,608
price = (1 + bin_step / 10000) ** (bin_id - SHIFT) * 10**12
```

## Usage

```bash
# Read LFJ V2.2 position (Avalanche) — CORRECT invocation
python3 ${VAULT_DIR}/scripts/onchain-reader.py --wallet 0x7ebff188f2Eba16518C02864589b1403a5d1296a --dex lfj --chain avalanche --json
```

## On-Chain Range Verification Protocol (Jul 22, 2026)

**Jordan's rule:** "No wrong range. Check on chain data." The on-chain reader is the authoritative source.

**Steps:**
1. Run reader with `--dex lfj --chain avalanche --json`
2. Extract `activeBin` from the response
3. Compute range from bin IDs:
   ```python
   SHIFT = 2**23  # 8388608
   bin_step = 10  # 0.1%
   for bin_id in bin_ids:
       price = (1 + bin_step / 10000) ** (bin_id - SHIFT) * 10**12
   ```
4. The lowest bin_id → range_low, highest bin_id → range_high
5. Update config files with verified range

**Pitfall:** The LFJ UI shows 149 bins in the slider by default, but the actual deployed position may have far fewer (e.g. 21 bins). The UI shows the available range, not what's actually active. Always verify with on-chain data.

## Verified Working State (Jul 22, 2026)

The reader now works correctly. Tested against the live LFJ V2.2 pool:
- Active bin: 8362850
- Bins with liquidity: 21
- Computed range: $6.48 – $6.61
- Active price: $6.59

**All selectors confirmed working.**

## Pool Details

- **Pool:** LFJ V2.2 AVAX/USDC (binStep 10)
- **Address:** `0x864d4e5ee7318e97483db7eb0912e09f161516ea` — a **97-byte proxy**; the implementation it
  delegates to carries the real bytecode. This address IS the pool; do not re-derive it from a partial one.
- **Wallet:** `0x7ebff188f2Eba16518C02864589b1403a5d1296a` — a **personal, self-custody** MetaMask wallet,
  not a treasury wallet. Treasury books use their own drilled keystore wallets; do not conflate the two.
- **RPC:** `https://api.avax.network/ext/bc/C/rpc` (rate-limits bursts — keep a second endpoint available)
