---
name: gentech-wallet-management
description: "Wallet identification, disambiguation, and ClawRouter proxy wallet swaps for media vs treasury. Load when funding wallets, switching proxy payers, checking balances, or diagnosing which wallet is active."
version: 1.1.0
author: Gentech
tags: [wallet, clawrouter, blockrun, media, treasury, usdc, base]
---

# Gentech Wallet Management

Wallet identification, disambiguation, and ClawRouter proxy wallet swaps.

## ⛔ WALLET STATUS — changed 2026-11-03

**`0xebc8c71970EEb6973bd87F1FF146B3Ec4a5972f8` (F8) is RETIRED.** Key lost in the Oct 12 wipe. It holds
**0.00151 ETH + 0.4868 USDC that nobody can spend**. **DO NOT fund it; do not expect it to work.**
Jordan, 2026-11-03: *"We don't have to use it anymore. We can retire that one."*

**Current BlockRun wallet: `0xc0A1f229a0CE65F576DC2fd885109cB3eEAf64a0`** — **ONE** shared key file at
`/opt/data/.blockrun/.session`, symlinked into every seat (verified 2026-11-03: five paths, one inode
`2162580`; all four seats derive this address through their own path).

⚠️ **It holds 0.9687 USDC and 0.000000 ETH on Base** — every BlockRun call fails until gas is funded.
That is a funding decision, not a config problem.

## 🚨 RULE — a media wallet is not "funded" until it has BOTH legs

**MEASURED 2026-11-03 (Jordan: *"we should have a BlockRun wallet with funds ready to go already"*).** The
wallet carried **0.968736 USDC and 0.000000 ETH**. BlockRun settles on-chain, so every call reverted *before
the USDC was touched* — the lane was down fleet-wide while the dashboard showed a funded balance.

- **This has now happened twice.** The retired F8 wallet worked because it had `0.00151 ETH` of gas; it was lost
  in the Oct 12 wipe. Its replacement was topped up with USDC only. **The gap is not the key, it is the second
  asset.**
- **Cost, measured:** Base base fee 0.005 gwei at ETH ≈ $2,294 → a simple transfer is **$0.000002**, a USDC
  transfer **$0.000007**, a media call with settlement **$0.00002**. **$1 of ETH ≈ 50,000 media calls.** This
  is never a budget question.
- **THE RULE:** funding a media or rails wallet means **spend asset AND gas, verified on-chain in the same
  breath**. Never accept "it has USDC" as "it is funded", and never accept a send confirmation as proof — read
  `eth_getBalance` and `balanceOf` after every top-up.
- **And never let a monitor describe this as a missing key.** `tool-liveness.py` reported "no image provider key"
  for five runs while the real fault was zero gas — fixed 2026-11-03. A wrong cause in a monitor costs more than
  no monitor, because it sends the fix in the wrong direction.

## Wallet Map

| Wallet | Address | Nickname | Purpose |
|--------|---------|----------|---------|
| ~~**BlockRun (F8)**~~ | `0xebc8c71970EEb6973bd87F1FF146B3Ec4a5972f8` | "the one ending in 72F8" | **RETIRED 2026-11-03** — key lost in the Oct 12 wipe; its 0.4868 USDC is unspendable. **Do not fund, do not use** |
| **BlockRun (CURRENT)** | `0xc0A1f229a0CE65F576DC2fd885109cB3eEAf64a0` | "the one ending in 64a0" | Media generation ONLY (image, video) |
| **GTA / Treasury (280D)** | `0xf5f99007Fc7e14133D3817dee2BA45169eA9280D` | "the Agentic Treasury" | DeFi, yield, trading, treasury ops |
| Jordan's personal | `0x7ebff188f2Eba16518C02864589b1403a5d1296a` | "Jordan's wallet" | User EOA — don't touch |

## Three-Tier Architecture (canonical — Jordan, Sep 3, 2026)

Hard separation, three tiers: **Tier 1 PERSONAL/EXTERNAL** (Jordan's own — agent never transacts without an explicit ask; his Polymarket login proxy key is NEVER stored locally) / **Tier 2 AGENTIC-TREASURY** (capital: Steward LFJ `0x572A…5037`, CDP treasury `0x77C6…7dE`, CDP telegraph-miner `0x03d2…856E`, Solana homebase `BE815V7…pUvP` — all keys held by fleet) / **Tier 3 AGENTIC-RAILS** (service-bound plumbing: BlockRun agent `0xc0A1f229…64a0` (F8 retired 2026-11-03), per-platform credentials). Canonical detail file: vault `00-System/wallet-architecture.md`. New-rail onboarding: gen keypair → store in profile secrets → register in that file → verify address on-chain BEFORE funding.

## Identity Proof Before Delete (Sep 3, 2026 lesson)

When a "mystery" key file appears (e.g. `.session`), NEVER delete on label alone. Derive the address from the key material (`eth_account.Account.from_key(hex).address`) and match against the known wallet map, plus check the on-chain balance. Sep 3: a file was initially mislabeled "Jordan's Polymarket proxy" — derivation proved it IS the BlockRun agent wallet (`0xebc8…72f8`, key held — **that address is retired as of 2026-11-03**); deletion would have broken the live rail. Jordan: "we don't want to delete anything keeping our wallets from disappearing." Corollary: credential ≠ wallet — `almanak-steward-key` is a 64-char API token, not a private key; the wallet it references is Steward `0x572A…5037` either way.

## CDP Server Wallets (keys held via CDP, not files)

CDP-managed wallets count as key-held (we control them via the CDP API): treasury `0x77C6…7dE` (Base deposit rail) and telegraph-miner `0x03d2…856E` (miner signing + x402 payments). Working v2-SDK patterns — listing accounts, reading balances, and the Base Sepolia USDC faucet (proven Sep 3: faucet returned tx `0xaa958394…`, +1 USDC, no real cost) — are in `references/cdp-wallet-faucet.md`.

## Golden Rule

> **Media gen → BlockRun `0xc0A1f229…64a0` (CURRENT). Treasury → GTA (280D). Never the other way around.**

Jordan's directive (Aug 8, 2026): "Only use the block run wallet ending in 72f8 for media creation" — "Gta wallet is my Agentic Treasury, not for media creation."

> *The rule stands; **the address in it does not** — 72F8 was retired 2026-11-03. Read it as "the BlockRun
> wallet, currently `0xc0A1f229…64a0`".*

## How to Find the BlockRun Wallet

The health endpoint may report the GTA wallet — do NOT trust it for BlockRun.

```bash
cd /opt/data/tools/blockrun && node -e "
const { getOrCreateWallet } = require('./node_modules/@blockrun/llm/dist/index.js');
console.log('ADDRESS: ' + getOrCreateWallet().address);
"
```
→ `0xc0A1f229a0CE65F576DC2fd885109cB3eEAf64a0` (ends in `64a0`) — **if this prints 72F8 you are reading a stale key file**

## How to Check Which Wallet ClawRouter Uses

```bash
curl -s http://127.0.0.1:8402/health | python3 -c "import sys,json; print(json.load(sys.stdin)['wallet'])"
```

This reads the key from `${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key`.

## Balance Check (Base Chain)

```bash
USDC="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WALLET="<address>"
DATA="0x70a08231000000000000000000000000${WALLET#0x}"
curl -s -X POST "https://mainnet.base.org" -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC\",\"data\":\"$DATA\"},\"latest\"],\"id\":1}" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(f\"\${int(r['result'],16)/1e6:.2f} USDC\")"
```

## ClawRouter Wallet Swap

Swap the proxy from GTA wallet to BlockRun F8 (or back):

### Step 1: Extract F8 private key
```bash
cd /opt/data/tools/blockrun && node -e "
const { getOrCreateWallet } = require('./node_modules/@blockrun/llm/dist/index.js');
const w = getOrCreateWallet();
console.log(w.privateKey);
"
```

### Step 2: Backup current wallet.key
```bash
cp ${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key \
   ${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key.gta.bak
```

### Step 3: Write F8 private key
```bash
echo "<F8_PRIVATE_KEY>" > ${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key
```

### Step 4: Restart proxy
```bash
systemctl restart clawrouter-proxy
```

### Step 5: Verify (wait 3s for startup)
```bash
sleep 3 && curl -s http://127.0.0.1:8402/health
# Should show: "wallet":"0xc0A1f229a0CE65F576DC2fd885109cB3eEAf64a0"   (72F8 = retired, wrong)
```

### Revert to GTA
```bash
cp ${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key.gta.bak \
   ${PROFILE_DIR}/home/.openclaw/blockrun/wallet.key
systemctl restart clawrouter-proxy
```

## Key–Wallet Semantics & "Rotation" Language (Sep 2, 2026)

**One EVM private key = one wallet on EVERY EVM chain.** The same secp256k1 key derives the identical `0x...` address on Avalanche, Base, Ethereum, Polygon, Arbitrum, BSC, etc. The wallet is NOT "per network" — balances are per-chain, but key and address are chain-independent. (Jordan, Sep 2: "that private key goes to the wallet period, so it should be for the other networks tied to that wallet, right?" — confirmed.)

**Solana is different cryptography** (ed25519 vs secp256k1): an EVM private key NEVER works on Solana. The only bridge is the seed phrase — a 12/24-word seed derives both EVM keys and a Solana keypair (how OKX/Phantom restore both from one phrase). A raw private key alone cannot cross.

**⚠️ PITFALL — do not over-interpret "rotated":** when Jordan says a key "has been rotated," it can mean the exposure concern was RESOLVED and the SAME key stays in use — NOT that a new key replaced it. Jordan (Sep 2, verbatim): "we're still going to be using that private key." Before proposing re-loading keys, re-wiring .env files, or re-verifying derivations, confirm whether the key MATERIAL actually changed. If the answer is "same key, handled," close the thread — no re-wiring, no sweep prompts, no balance checks unless Jordan asks.

**Rotation exposure scope:** if an EVM key was ever exposed, EVERY EVM chain under that wallet was equally exposed (same key everywhere) — a security review covers all chains holding funds, not just the chain where the concern arose.

## PITFALLS

- **Deletion is never the answer**: verify identity by key-derivation + on-chain balance BEFORE removing anything. The Sep 3 "orphan" was our own active BlockRun agent wallet — deleting it would have snapped a live rail.
- **Health endpoint lies**: ClawRouter `/health` reports whatever wallet is in `wallet.key` — NOT necessarily the BlockRun wallet. Always verify with the `getOrCreateWallet()` script.
- **Proxy caches at startup**: After funding the wallet, restart the proxy so it reads the new balance. Otherwise it may route to free/congested models thinking the wallet is empty.
- **Never mix wallets**: If media charges hit the GTA wallet, that drains treasury funds for image/video gen. If treasury ops hit the F8 wallet, media funds get locked in DeFi. Keep them separate.