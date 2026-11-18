---
name: agent-capital-custody-and-recovery
description: "Use when custody of agent-held capital is designed or lost."
version: 1.0.0
author: gentech
license: proprietary
category: devops
tags: [custody, keys, treasury, recovery, backup, wallets, disaster-recovery]
metadata:
  hermes:
    tags: [custody, keys, treasury, recovery, backup, wallets, disaster-recovery]
    related_skills:
      - gentech-ops/gentech-wallet-management
      - devops/blockrun-wallet-management
      - defi/lfj-onchain-reader
---

# Agent Capital Custody & Recovery

## When to Use

Load when agent-operated capital is being designed, audited, or recovered:
- a new rail or wallet is about to be funded (authority shape, key placement);
- a key cannot be found, or sits somewhere the agent cannot read;
- a host, account or repo was lost and something must be rebuilt or re-issued;
- a backup exists that has never been restored;
- someone asks "can we still get to it?" about a wallet or a position.

Load when agent-operated capital is being designed, audited, or recovered: a new rail or wallet being
funded, a key that cannot be found, a host that was rebuilt, a backup whose restore has never been
tried, or the question "can we still get to it?".

Scope: the *design and verification* of custody. Wallet identification and disambiguation belong to
the wallet-management skills; this skill governs whether the custody arrangement survives a failure.

## The five standing rules

Any one missing collapses the others — a single point of failure anywhere makes the other four
decorative.

1. **Threshold authority on-chain.** Control of the capital is a smart account with ≥3 owners and an
   m-of-n threshold (start 2-of-3), and the agent holds exactly ONE signer. Consequence: losing the
   agent host can neither move the funds nor freeze them.
2. **Automation holds session keys, never treasury keys.** The agent's live authority is a bounded,
   expiring, revocable session key — whitelisted contracts and rails, per-tx cap, per-epoch cap,
   expiry. A wipe or a theft kills the session; the treasury is untouched.
3. **3-2-1-0 for key material.** 3 copies, 2 media, 1 off-site, 0 plaintext. Prefer shards over
   copies: a 2-of-3 split across distinct failure domains, so that no single domain reconstructs the
   key.
4. **Ciphertext never travels with its passphrase.** Never a `.passphrase` beside the `.key.enc` it
   opens — not the same directory, not the same host. Directory modes protect against other local
   users and against nothing else.
5. **No funded wallet without a tested recovery path.** Extends "never park real funds where we don't
   hold keys" to "…where the key exists in only one place and has never been restored once."

## Two failure shapes that look like safety

- **An offsite backup on the same account identity as everything else is not offsite.** Account-level
  loss — a hold, a lockout, a suspended org — takes the backup and the original together. Independent
  targets must differ in *identity*, not merely in path or provider.
- **A backup that has never been restored is a hypothesis.** The restore drill is the only proof — and
  it is also the only way to discover that the passphrase a human is relying on no longer opens the
  ciphertext.

**Alarm on absence, not on error.** A backup job that silently stops running reports no error at all.
Assert the freshness of the artifact and fail when it is stale or missing; a monitor that only reacts
to errors cannot see a job that never ran.

## Keep the inventory even when the keys are gone

What makes a loss unrecoverable is not losing keys — it is losing the record of *which* credentials
existed. Maintain a name-level inventory in the durable brain: name → used by → re-issue path →
status, with no secret values in it. After a wipe this inventory is the asset the rebuild is planned
from; before a wipe it is the difference between re-issuing a checklist and doing archaeology.

## Report access as two gates, never one verdict

"Can we still get to it?" is two questions, and one verdict misleads the owner:

- **Reading is permissionless.** Balances, positions and full history are public-chain facts, knowable
  with no key at all. If the question is "can we see it", the answer is almost always yes — and that
  is a real answer, not a consolation prize.
- **Moving needs the signer AND the principal's word.** Where is the key, who can physically reach it,
  and — for a human's capital — that human's explicit go-ahead. Key availability alone never
  authorises movement.

State the key's actual location and permission state. When key material sits outside the agent's reach
(root-owned paths, another principal's custody), say so plainly and name the exact command the human
can run to check it. Never present an unverified "probably lost" as a finding, and never let a
permission limit read as a data limit.

## Design gate for any new rail or wallet

1. Decide the authority shape first (threshold, or a stated reason why not) — before any funding.
2. Derive or record the address and confirm it on-chain before moving value to it.
3. Place the key material in ≥2 mutually independent failure domains, and the passphrase in a third.
4. Register it in the custody map and in the inventory.
5. Verify the restore path once, on a scratch environment, before calling the rail live.

## References

- `references/recovery-drill-and-readiness-gate.md` — incident decomposition axes, the recovery ladder
  by blast radius, the readiness-gate assertions, and the monthly drill recipe.
- `references/onchain-position-forensics.md` — establishing what actually exists on-chain (positions,
  last-touched time, deposit vs withdrawal) with no SDK, no indexer key and no web3 libraries.
