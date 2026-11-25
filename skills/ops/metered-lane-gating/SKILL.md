---
name: metered-lane-gating
description: "Use when spending from a metered or paid API lane."
version: 1.0.0
author: arthur
license: MIT
tags: [quota, billing, metered, spend, tts, x402, verification, honesty]
metadata:
  hermes:
    tags: [quota, billing, metered, spend, tts, x402, verification, honesty]
    related_skills: [provider-quota-diagnosis, agent-cost-control, claim-provenance]
---

# The metered lane — gate it properly, then measure before you spend

## When to Use

Any operation that consumes a metered resource: TTS characters, paid API calls, x402/USDC spend, gas,
per-minute rendering. Trigger on either of these:

- you are **about to** run a job that costs units, or
- a metered job just **failed** with a quota or payment error.

## The rule

**The gate is the account's own STATE plus the honest SIZE of the request you intend — never a proxy.**

The two proxies everyone reaches for both lie, in opposite directions:

- **A tiny probe lies optimistic.** A **1-unit** request can succeed on an account in `past_due` while every
  real request is refused (`401 … "Your subscription has a failed or incomplete payment"`). A probe proves the
  lane accepts *a tiny request* — nothing about the one you are about to make.
- **A counter lies, both ways.** Counters round, lag, and can freeze: one recorded **+10 for a 16-unit spend**,
  then sat unchanged through an entire render. Quote a counter as a **lower bound**, never as the gate.

## Step 1 — Read the state from ONE payload

Fetch the subscription/usage payload **once** and take `status`, the usage counter, and the reset field from
that same response. Mixing a status from one call with a counter from another manufactures a state nobody is
in.

Then classify:

| What you observe | What it actually is | Action |
|---|---|---|
| credential missing / unreadable | a **lookup** problem, not a dead credential | fix the resolution order (env → the seat's own `secrets/` → seat `.env`) before concluding anything |
| `status` active, counter at/near the limit | a real quota wall | wait for the reported reset timestamp, then run |
| `status` = past_due / unpaid / suspended / canceled / restricted | **billing** — and the counter can be frozen mid-cycle, hiding it | refuse before spending; report the invoice amount |
| counter says "nothing left" but a small request passes | counter lag | trust neither number alone; measure the real cost |
| body is not the expected media type | an error body wearing a success name | treat as failure; never write it to disk |

**Deny-list, never allow-list.** An unknown or newly-invented status must **not** stop a paid, working
account. Enumerate the states that mean stop; treat everything else as proceed-and-verify.

## Step 2 — Refuse cheaply

If the state is on the deny-list, stop **before** consuming anything and report the exact amount and the
alternative. Do not render, do not partially run, and do not report a reset you did not observe — an
inferred reset date has been reported wrongly, so it is read from the field that carries it
(`next_payment_attempt_unix`, `next_character_count_reset_unix`), never derived from a billing period or
from a previous run's report.

## Step 3 — Measure the cost before spending

A metered job should have a **dry run that prints the exact units it will consume and writes nothing.**

- **Measure per subject.** The cost for one learner/tenant/record is not the cost of two; measure each.
- **Compare before spending.** If the measured cost exceeds what is available, report the shortfall and stop.
- Keep the dry run cheap and honest: it must not call the metered endpoint at all.

## Step 4 — Never leave a partial artifact

A run that dies part-way produces output that **reads as a result** — worse than no output, because nobody
re-checks it. So:

- On any refusal mid-run, **write nothing** and say so; do not assemble a half-finished file.
- Report the **exact error text**, not a summary of it. Metered lanes reuse HTTP codes (a billing failure and
  a dead credential are both `401`), so read the error **body/code**, never the status line, to tell them
  apart.

## Step 5 — Verify what landed, by measurement

- Check the **media type/format** of every artifact before delivering it.
- Check that a composed artifact is **bigger than its first part** — that is how you prove a join happened.
- When claiming two outputs differ, **compare hashes.** Equal byte counts are **not** equal content at a
  fixed bitrate; two short utterances can coincide on size.
- Quote a counter or a probe **only as what it measured**: "the lane accepts a 1-unit request" is a different
  claim from "the lane is open". If you did not prove the real request, say UNMEASURED.

## Pitfalls

- **Do not report a passing probe as "the lane is open".** It is a claim about a 1-unit request, and it is
  the single most misleading signal on a billing-broken account.
- **Do not treat a counter as the gate.** It lags and freezes; report it as a lower bound and let `status`
  decide.
- **Do not infer a reset or retry date.** Read the field. A plausible-looking inferred date gets repeated to
  the user as fact.
- **Do not bury a billing failure as "a wait".** A quota that resets is a wait — schedule just after the
  reset and have the job refuse to fabricate output if the gate is still shut. A billing failure needs the
  human: hand them the exact amount and the field-derived retry date.
- **Do not let a metered lane's failure become a "tool doesn't work" conclusion.** Separate *lookup*,
  *quota*, and *billing* — they have different fixes, and misdiagnosing one as another sends the reader to
  the wrong remedy.

## Related

- `provider-quota-diagnosis` — provider usage/rate-limit diagnosis; its live-test step is necessary but
  not sufficient on its own (see the rule above).
- `agent-cost-control` — reducing a fleet's inference bill.
- `claim-provenance` — reporting a number or status as the thing it measured.
