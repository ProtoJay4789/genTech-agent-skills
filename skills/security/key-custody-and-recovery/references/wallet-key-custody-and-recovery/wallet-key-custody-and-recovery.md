---
name: wallet-key-custody-and-recovery
description: "Use when a key or treasury may be lost or locked."
version: 1.0.0
category: devops
author: gentech
license: MIT
tags: [wallet, keys, custody, disaster-recovery, treasury, backup, rpc]
metadata:
  hermes:
    tags: [wallet, keys, custody, disaster-recovery, treasury, backup, rpc]
    related_skills: [defi, lfj-onchain-reader, credential-security-behavior]
---

# Wallet Key Custody & Recovery

Use when capital may be lost or locked: a host died or was wiped, a key cannot be found, a repo or
account is unreachable, or an operator asks *"can we recover it?"*. This covers the two questions
always asked together — **what still exists on chain**, and **what it would take to move it**.

## When to Use

- A key, keystore or passphrase cannot be found, or the host that held it is gone or was rebuilt.
- An operator asks "can we recover X?" about a wallet, a position, a treasury or an account.
- You are designing where keys should live, or how a backup should be checked.
- A backup, repo or offsite copy turns out to be unreachable at the moment it is needed.

## Triage: READ and MOVE are two different questions, answered separately

Chain reads need **no key, no signature and no library** — the public address and the contract are
enough, and any position is readable by anyone. *Moving* anything needs the signer.

So answer in two parts, in this order:

1. **READ — verified now.** Quote real balances and positions. Do this before answering at all; an
   unverified opinion about recoverability is worthless.
2. **MOVE — name the single blocking gate.** Usually one missing key file, or one passphrase. Name
   it, and say who can check it. "Unknown, and it is one command from settled" is a real answer;
   "maybe" is not.

Never let the size of the key question imply a size of loss that the chain does not show. If the
wallets hold a few dollars, say so plainly — the operator is deciding whether to keep digging.

## Custody rules — the three failures that turn an outage into a total loss

- **One host is not custody.** Keys held only as files on a single machine share that machine's
  blast radius, and a wipe takes every one of them at once. Every key needs a copy in a **different
  failure domain** before the wallet is funded, not after.
- **A ciphertext must not travel with its own passphrase.** A `.key.enc` beside a `.passphrase` in
  the same directory is one factor wearing two hats: file mode 700 protects against other local
  users and protects against nothing when the host is lost. The passphrase belongs to a human and to
  a separate physical medium.
- **A backup on the same identity is not offsite.** When the offsite copy lives in the same account
  or provider as everything else, a single account hold takes the original and the backup together.
  Two targets, two identities, and at least one that depends on no account at all.
- **Never re-issue secrets into a chat.** Keys pasted into a conversation land in session history and
  logs. Point at a file path and read from there.

## Inventory beats keys — the asymmetry worth protecting

Keys can be re-issued; the *record of which keys existed* cannot be reconstructed after the fact. A
written inventory of every credential, wallet and rail — name, what it was for, its re-issue path —
converts a total loss into a checklist. Keep it in the off-host brain and update it whenever a rail
is added. When a wipe happens, that inventory is the first deliverable you produce.

## Prove what exists before promising recovery

```python
# ERC-20 balance: selector 0x70a08231 + address padded to 32 bytes
rpc("eth_call", [{"to": TOKEN, "data": "0x70a08231" + addr[2:].lower().rjust(64, "0")}, "latest"])
rpc("eth_getBalance", [addr, "latest"])            # native, wei → /1e18
```

- **A silent endpoint is not a zero balance.** Public RPCs go quiet without throwing. Hold a
  fallback list, keep the first endpoint that answers `eth_blockNumber`, and confirm each chain
  replied before publishing any balance — otherwise you report a funded wallet as empty. Endpoints
  and the keyless history lookup: `references/keyless-chain-verification.md`.
- **A malformed batch call returns zeros, not an error.** A hand-rolled `balanceOfBatch` with a wrong
  offset layout answers a vector of zeros — indistinguishable from "holds nothing", so it will make
  you report a live position as empty. Confirm any batch result with ONE single call on an entry you
  know exists. If the single call is non-zero and the batch said zero, the batch is the liar.
- **A liquid wallet balance is not the position.** Capital parked in an LP sits in the position, not
  in the wallet; a wallet showing $1 can be holding a real book. Read the position, and report the
  wallet's own balance separately from it.
- **Truncated addresses are not identities.** `0x572A…5037` cannot be queried. Resolve the full
  address from the wallet map or census first, and never infer it from a similar-looking one.

## Readiness gate — assert values, treat silence as failure

A recovery plan is decoration until something checks it. Each row prints PASS/FAIL with the observed
value, and absence is a failure:

1. Newest offsite key bundle is younger than the freshness window — alarm on **absence**, not on
   error, because a monitor that only alarms on exceptions cannot see a job that stopped running.
2. The last restore drill is inside its interval and recorded as passed.
3. Every funded wallet is either threshold-authority with the agent as a **non-sole** signer, or
   unfunded.
4. No encrypted key file keeps its passphrase in the same failure domain.
5. Automation holds bounded, expiring session authority — never the treasury key itself, so losing
   the agent host can neither move nor freeze the funds.

## Pitfalls

- **Do not run a "backup" that has never been restored.** An unrestored backup is a hypothesis; the
  drill is the evidence, and it is the only row that proves the other four work.
- **Do not answer from a cached belief about where keys live.** Read the custody map, then check the
  live filesystem for that exact path — a map records intent, not what survived.
- **Do not treat a held or suspended account as a lost cause before checking its public surface.** A
  restricted account may still serve public reads, and public repos may still exist — enough to
  establish what did and did not survive.
- **Do not narrate the incident as the plan.** The plan is the rules and gates that hold next time;
  the incident is only how you found them.
