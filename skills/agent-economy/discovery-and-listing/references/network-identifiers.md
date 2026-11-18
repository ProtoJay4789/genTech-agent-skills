---
title: Network identifiers (CAIP-2) — correctness rules
tags: [x402, caip-2, network-identifier, multi-chain, validation]
parent: discovery-and-listing
use_when: "Writing or changing a `network` identifier in an x402 accepts[] entry, a multi-chain manifest, or any chain-scoped claim — and when a validator reports a `parse`/format failure you cannot place."
---

# Network identifiers (CAIP-2) — correctness rules

**Every x402 `accepts[]` entry, every multi-chain manifest and every chain-scoped claim carries a `network`
identifier. ONE malformed one can fail the WHOLE document** — so a single bad rail makes a service
unindexable everywhere while every other field it serves is perfectly correct. Measured: a validator
rejected every route with **24 of 25 checks passing**, and the only failure was one identifier's format.

## The format

`namespace:reference` — and the **reference must match `[-_a-zA-Z0-9]{1,32}`**:
**no padding characters, no `/`, no `+`, no `=`.**

| chain | identifier |
|---|---|
| EVM (`eip155`) | `eip155:<chainId>` — `eip155:8453` Base · `eip155:1` Ethereum · `eip155:137` Polygon · `eip155:42161` Arbitrum · `eip155:43114` Avalanche C-Chain |
| Solana | `solana:<genesis-hash, first 32>` — mainnet `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp` |
| Algorand | `algorand:<URL-SAFE base64 genesis hash, first 32>` — **never the quoted full base64** (see below) |

## The truncation recipe (the one that bites)

The commonly-quoted Algorand genesis hash is **standard base64, padded, 44 characters** — it *cannot* be a
CAIP-2 reference. Two changes are required, and both are easy to skip:

1. re-encode with the **URL-safe** base64 alphabet (`+`→`-`, `/`→`_`)
2. take **only the first 32 characters**

```python
import base64
gh = "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8="   # standard base64, padded
ref = base64.urlsafe_b64encode(base64.b64decode(gh)).decode()[:32]
identifier = "algorand:" + ref    # -> algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73k
```

**The trailing `=` is the specific defect:** it is base64 padding, CAIP-2 forbids it in a reference, and a
strict parser rejects the **container** rather than the field — so the error names the identifier while the
consequence is "your whole payload is invalid."

**A Solana identifier follows the same 'first 32 of the genesis hash' shape** — so if you are hand-writing a
network string from a quoted hash, assume it needs truncating and verify against a namespace registry or the
counterparty's supported-list.

## Before you change one

- **Ask the counterparty's supported-list** (a facilitator's `/supported`, a registry's namespace doc). A
  comment in your own code claiming one exact string is *"mandatory"* is a claim, not a spec — the endpoint
  may accept several forms, which turns a risky edit into a safe one.
- **Grep every copy**: live code, tests that assert the old value, and historical backups/snapshots. Fix the
  live ones; leave the historical ones — they are records, not code.
- **Check how the value is used.** A prefix test (`network.startswith("algorand:")`) survives a reference
  change; an equality comparison elsewhere does not. Confirm which, then edit.
- **Write the WHY into the comment you are replacing.** An identifier that carries a confident but stale
  justification is what made the wrong value survive — the next author copies the comment, not the code.

## Verify, do not reason

Run the vendor's validator against the **live** artifact (commonly a free, unauthenticated
`POST …/validate` taking `{resource, method}`). It names the failing check in one call.

- **A `parse`-class failure means the whole document failed** — fix the malformed value; **do not delete the
  rail** to make it pass. Deleting a settlement rail to satisfy a parser trades a compliance bug for a lost
  revenue path.
- **Re-run the validator on EVERY route after the fix**, and pass the method each route actually serves. A
  `method.matches_request` failure is the validator reporting that *you* probed a POST route with GET — the
  instrument correcting its operator, not a defect in the endpoint.
