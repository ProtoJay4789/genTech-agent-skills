---
name: governed-agent-execution
description: "Use when an agent will move money or sign actions."
trigger: Building, demoing or auditing an agent that executes signed actions — swaps, transfers, payments, token or tool calls — or writing the mandate/guardrail layer for one.
tags: [agents, money, mandates, guardrails, simulation, receipts, x402]
version: 1.0.1
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [agents, money, mandates, guardrails, simulation, receipts, x402]
    related_skills:
      - devops/agent-capital-custody-and-recovery
      - guard-verification
      - agent-kit/falsifiable-tests
---

# Governed Agent Execution

## When to Use

Load when any of these is true:

- an agent will **sign, pay, swap, transfer, launch or call a paid tool** — building it, reviewing it, or
  writing its permissions layer;
- a **mandate / guardrail / spend-cap** design is being decided;
- an agent demo must be **convincing without holding money**;
- someone asks "what stopped it?" or "can we prove what it did?" about an automated action.

An agent that moves value has three jobs, and they are not the same job: **decide**, **prove it is
permitted**, **leave a record that survives the person who ran it**. Most systems do the first well and
treat the other two as logging. That ordering is backwards — a guardrail that runs after the transaction
is a postmortem, not a control.

## The pipeline — and the order is the whole point

```
mandate → policy check → simulation gate → signer (injected) → append-only receipt
```

Every value movement passes all four gates in that order or does not happen. There is no side door, and
no path from intent to settlement that skips one.

### 1. Mandate — deny by default

The authority document. Everything not granted is denied, and the gaps are refusals, not defaults to
something permissive:

- **per-action cap** and **total spend cap**, in integers (micro-units) — never floats.
- **destination allowlist** — a protocol id or address off the list cannot be paid, whatever the amount.
- **expiry** — and **a mandate with no expiry is refused**, because an unbounded mandate is not a mandate.
- Checks run **before** the transaction is built, so a denied action never reaches the signer.

### 2. Simulation gate — three outcomes, not two

Build and simulate the transaction **without signing and without broadcasting**. Three distinct results:

| result | effect |
|---|---|
| passed | proceed to the signer |
| failed | **BLOCK**, recorded with the program error |
| could not run | **BLOCK**, as `SIMULATION_UNAVAILABLE` |

That third row is the one that matters. **A gate that never ran must never read as a pass** — collapsing
"unavailable" into "fine" is how a monitor starts reporting silence as a fact (see `guard-verification`
§7, same family).

### 3. Signer and settlement are INJECTED adapters, and the shipped default REFUSES

No keypair is generated, stored or held by the harness. The signer is an interface; the only implementation
in the repo is `DryRunSigner`, which raises `NO_SIGNER`. Same for any payment/settlement client
(`NO_SETTLEMENT`) and any chain RPC. Consequences to keep:

- **Offline, the correct result is ZERO permitted actions.** A harness that prints ALLOW rows on a machine
  with nothing to sign is theatre, and it teaches the next reader that the pipeline is live.
- **Never stub an adapter to return success** to make a demo look complete. A plausible `"signed"` from a
  fake is the single most expensive defect in this class.
- Wire the real adapter later against the same interface; the rest of the pipeline must not change.

### 4. Receipt — append-only, one line per attempt

Allow, deny and block all get a record. Human-readable amounts alongside the raw micro-units, the reason
string, the checks that ran, and enough detail to replay the decision by hand. **Never rewrite, dedupe or
re-sort the ledger to make output prettier.** A blocked action is recorded as blocked, never as a silent
skip.

## Metered calls (x402-shaped) are budgets, not bills

When a tool costs money per call, price it explicitly:

- **Typed catalog, price per call.** An unknown tool is **refused**, never priced at zero; a tool with a
  missing or non-positive price cannot be called.
- **Budget through the SAME mandate** as any other value movement — not a private counter.
- **Idempotency key per call.** A retry returns the original receipt; paying twice for one retry is a bug,
  because retries are normal.
- **A settlement that did not happen is not spend.** Refusing adapters mean nothing is recorded as charged.

## The write-up must keep two claims apart

**"The gates are proven" and "the wallet is funded" are different claims.** A submission, README or
portfolio page for this class of work must say which one is true:

- what was executed, what was denied, what was blocked, and the exact spend recorded;
- which requirements are **not** satisfied offline (a funded wallet, on-chain activity, a human who can
  claim a payout) — named plainly rather than implied by a working demo;
- no fabricated rate, volume, XP or balance, ever. An unmeasured axis is `UNMEASURED`, not zero.

A demo whose honest summary is *7 receipts, 0 allowed, 3 denied, 4 blocked, 0.00 spent* is stronger than one
that shows a successful swap it never made.

## Demo script shape

One command, reproducible, reading its summary back from disk rather than from its own print statements:

1. delete and recreate the ledger so the run cannot inherit a previous one;
2. drive one action per gate (an in-mandate action, an over-cap action, an off-allowlist destination, an
expired mandate) and one metered call per rule;
3. re-read the ledger and print counts per decision plus the spend total;
4. **exit non-zero if anything was ALLOWED offline** — that is the assertion that keeps the refusing
   adapters honest;
5. run both selftests and report their exit codes.

## Publishing the artifact — the link is half the deliverable

An artifact nobody can clone is a claim, not evidence. Before saying "it's published":

- **Test visibility ANONYMOUSLY, and test the clone, not the page.** `GET /repos/<owner>/<repo>` with no token, and
  `git clone` the public URL into a scratch dir, then **run the demo there**. Every source file should answer 200
  from `raw.githubusercontent.com`. A file that only exists locally does not survive the clone.
- **Publish from the identity a stranger can see.** Fleet boxes commonly hold several tokens; the one filed as
  "the" GitHub token may authenticate as an account that returns **404 to logged-out readers**. Measure each
  token's `/user` login and each repo's anonymous status before choosing — then say which account you used.
- **Repo creation is a paced, counted write** (create → PATCH visibility → topics). Space them, never loop, never
  retry through a 403/429, and report the count. See `github-account-compliance`.
- **Never commit a ledger that contradicts the run.** The demo deletes and regenerates its ledger, so the
  committed copy goes stale on the next run — regenerate **before** committing, or the committed evidence
  disagrees with the code.

## Pitfalls

- **A spend aggregate that sums one record key is blind to records of another shape.** One ledger carrying
  executed actions (`amount_usdc`) and metered calls (`price_micro`) must be summed across both; summing
  one lets paid calls bypass the budget entirely. Grep the writer for every key it can emit, confirm the
  reader names all of them, and test it by spending through both shapes.
- **A test assertion that reads a variable an earlier call rebound asserts nothing.** Give every receipt
  its own name; never reuse the variable you will compare against later. (See `falsifiable-tests`.)
- **A mandate check that runs after the transaction is built is a log line, not a control.** Order the
  calls so the deny path can be asserted to have produced no signature at all.
- **Route volume counted per hop inflates every metric.** Count a routed transfer once per route regardless
  of hops — programs that judge on volume count principal, not instructions.
- **A "preview"/"approve" step that the agent can skip is not an approval.** If the human must sign, the
  agent must be structurally unable to proceed without that signature — not merely polite about asking.
- **Custody is a separate question.** Where keys live, threshold authority and recovery belong to
  `agent-capital-custody-and-recovery`; this skill governs what the agent is permitted to do and what it
  can prove afterwards. Do not conflate "no key on the box" with "safe" — say which property you verified.

## Verification checklist

- [ ] Deny-by-default: an unset expiry, a zero cap, an empty allowlist and an unlisted destination each REFUSE.
- [ ] A denied action provably never reached the signer (empty signature, asserted).
- [ ] Simulation has three outcomes, and the "could not run" case blocks.
- [ ] The shipped signer/settlement adapters refuse, and a full offline run reports zero allowed.
- [ ] The spend total reconciles across every record shape the ledger can hold.
- [ ] Metered calls: unknown tool refused, unpriced tool refused, retry not recharged, refusal not recorded as spend.
- [ ] The ledger is append-only and every attempt — allow, deny, block — has exactly one record.
- [ ] The summary is read back from disk, and the run exits non-zero on an offline ALLOW.
- [ ] The write-up names what was NOT done (funding, on-chain activity, payout) instead of implying it.

A working reference implementation of every rule above: `profiles/arthur/scripts/steve-capital-agent/`
(`steve_harness.py`, `x402_meter.py`, `demo.py`) — read it as a template, not as a dependency.
