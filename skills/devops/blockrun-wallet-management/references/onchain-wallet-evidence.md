# On-chain wallet evidence — proving liveness, funds and attribution

A balance read answers "what is there right now". These recipes answer what actually blocks a run:
*is this the wallet we think*, *is it spendable*, *who spent*, and *did my probe change anything*.

Run `scripts/usdc_transfer_scan.py <address> [blocks]` for the scan; this file explains how to read it and how
to derive addresses safely.

---

## 1. Derive the address from a `.session` file — without the SDK, without printing the key

Use when several seats hold session files and you need to know which address each controls, or when the SDK
path is what you are testing.

**Put the script inside the directory that owns `node_modules` and use CJS `require`.** An ESM script elsewhere
fails with `ERR_MODULE_NOT_FOUND` — `ethers/lib.esm` and `viem` both use extensionless internal imports, so an
absolute-path ESM import breaks and a `viem` import from outside the tree cannot resolve at all.

```js
// <tools-dir>/derive_address.cjs   — run: node <tools-dir>/derive_address.cjs <file> [...]
const { readFileSync } = require("node:fs");
const { Wallet } = require("ethers");
for (const path of process.argv.slice(2)) {
  let raw;
  try { raw = readFileSync(path, "utf8").trim(); }
  catch (e) { console.log(`${path}\tUNREADABLE (${e.code})`); continue; }
  if (!/^0x[0-9a-fA-F]{64}$/.test(raw)) { console.log(`${path}\tINVALID-SHAPE len=${raw.length}`); continue; }
  console.log(`${path}\t${new Wallet(raw).address}\tkeylen=${raw.length}`);   // address only
  raw = null;
}
```

**Digest every session file before and after the probe and compare.** `getOrCreateWallet()` mints a brand-new key
when a session file is missing, so a "read-only" probe can create a wallet and move where the money has to go.
`sha256sum` before/after is the only proof it did not.

**Never print two keys to compare them.** Compare **digests** and report `MATCH` / `DIFFER`, then report the
derived address — the address is public, the key is not.

---

## 2. Reading a transfer scan

| pattern | conclusion |
|---|---|
| `sum(IN) − sum(OUT)` equals the current balance (6 dp) | one wallet, no hidden movement — the reading is explained |
| the balance moved and OUT entries exist | the wallet is **live** and spending; not stranded |
| the address only ever receives, never sends | stranded candidate — confirm the key separately |
| the arithmetic does **not** close | a second address, a different token, or a wrong address — stop |
| every RPC endpoint errors | **UNMEASURED**, never `$0` |

**Timestamps matter more than totals.** A payment at 22:58 explains a 0.127 difference between two agents'
readings; without the timestamps the same two numbers look like a disagreement about which wallet is funded.
Both readings were correct — they were minutes apart.

**Attribution:** the sender field is the same address whichever seat signed. Report "ten payments left this
wallet between T1 and T2" and, if that contradicts a "nothing was spent" report, say so as a measurement and
name the next probe (which process), not a culprit.

---

## 3. `getWalletAddress()` is synchronous — fix the guard, not just the promise

```js
let address;
try { address = getWalletAddress(); }            // returns a STRING in 3.x
catch (e) { console.error("🛑 cannot derive wallet:", e.message); process.exit(4); }

const EXPECTED = "0x...";                        // the address on record
if (address.toLowerCase() !== EXPECTED.toLowerCase()) {
  console.error(`🛑 REFUSING — spend-from ${address} ≠ on record ${EXPECTED}`);
  process.exit(4);
}
```

**Fixing only the `.then`/`.catch` is dangerous on a multi-seat host:** every seat derives a *different* address
from its own `HOME`, so a script that merely stops throwing will happily spend from whichever key that seat
holds — including an unfunded one created minutes earlier. The assertion is the safety half of the fix.
