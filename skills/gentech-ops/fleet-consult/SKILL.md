---
name: fleet-consult
category: gentech-ops
version: 1.0.0
author: gentech
description: "Use when a decision needs the whole fleet's read."
hermes:
  tags: [coordination, deliberation, handoff, decisions, hackathons]
  related_skills: [handoff-mesh-coordination, develop-and-verify, agent-coordination]
---

# Fleet Consult — the fleet-wide discussion layer

## What this is (scope — do not overreach)
This is **the modern form of the old "get everyone together in the Mess Hall" discussion** (Jordan, Sep 11 2026): *"now what I'm saying is we can have a fleet-wide discussion when we talk about entering a hackathon, or when we talk about making big decisions."*

**Nothing else changes.** Normal operation, the delegation layer (HQ routes specialist work via handoff mesh), the PA Suite's decision-support role, all crons, all lanes — all function exactly as they do today. This skill adds a *discussion format* for a specific class of moment. It is **not** a new operating model, not a replacement for HQ routing, and not a standing always-on loop.

**The PA owns routine decision support** (are we too late, should we move on, deadline verdicts). This skill is for the moment **before** that — when Jordan asks for a deep dive, or a big decision is coming, and the answer genuinely benefits from every seat.

## When to Use
- Jordan asks for a **deep dive / deep discussion** on something.
- A **big or hard-to-reverse** decision: entering a hackathon, a product/pricing call, an architecture choice, adopting/retiring a tool, a spend or capital decision.
- A question where **disagreement is valuable** — where you'd rather learn you're wrong before acting.

**Do NOT use** for: routine execution, routine go/no-go (the PA has it), anything one agent clearly owns, low-stakes reversible choices, or a deadline-hours-away scramble. A consult costs 3 agents' turns — reserve it.

## Why it works (measured, Sep 11 2026)
Asked HQ's five-suite proposal to all three seats. **All three independently revised HQ's build order** — Labs from concurrency, Pixel from human/creative feel, Treasury from accountable economics. Three different seats, three different failure modes, one convergent shape. That convergence is the product: **you cannot get it by asking one agent, however smart.**

Corollary: **the synthesizer must be willing to be wrong.** HQ's original order was overridden by the returns and the revision shipped as the recommendation. A consult where the answer is predetermined is theater.

## The Procedure

### 1. Scope the question so each seat can answer from its own experience
Write ONE shared context block (what prompted this, what's already decided, the constraints), then a **seat-specific framing** for each. The seat framing is what makes the returns differ — ask each agent what *their* seat sees.

Default seats (our 4-profile fleet):
| Seat | Profile | Asks from |
|---|---|---|
| **The learning engine** | arthur | whether a learner could actually use it, pack/session fit, what confuses a human being taught |
| **Money / risk** | gentech-treasury | spend authority, accountability, economic guardrails, what is irreversible |
| **Content / public surface** | protojay | how it reads to an outside human, what we would have to publish, what we cannot claim |
| **HQ / synthesis** | gentech | coordination, routing, what the decision costs us |

**Check the roster before fanning out.** This table named two seats that have since retired; a consult built from a
stale table dispatches into nothing and returns silence that reads like agreement. Confirm every profile you are
about to message is live before writing the asks.

### 2. Ask for the same shape from everyone (so returns are comparable)
- Top 1–3 gaps/options, **ranked**, each with a one-line "why it matters."
- **What you've personally hit** — a real failure from their own lane. Concrete beats abstract; this is where the value is.
- **What you'd deliberately NOT build/do** (anti-patterns).
- **Disagreement with HQ is explicitly welcome** — say so in the handoff, in those words.
- **Ask for a NUMBER, not a verdict.** "What do you think" returns opinions; "run this and report what it says"
  returns evidence. Measured: three seats each asked for one config value returned hard numbers that **falsified the
  proposal HQ had already written** — the consult paid for itself because the questions were phrased so a
  contradiction could come back.
- **Ask each seat to run the check on ITS OWN seat.** A fleet-wide defect is usually per-seat config, so one HQ
  measurement is one data point and four seats re-measuring is four corroborating ones. Phrase it "report the number
  you find", never "confirm that ours is N".
- **State the read-only constraints and make them hard** — do not change config, do not install anything, do not
  draft the design doc. Without that last clause a consult returns three incompatible plans and HQ inherits a merge.
- A word cap (~400 words) and a named reply path.

### 3. Fan out in parallel — handoff + peer-DM
- Write the handoff to `01-HANDOFFS/gentech-to-<seat>/<date>-<topic>.md`, commit, push.
- Wake each with `hermes -p gentech peer dm <peer> "<msg>"` in the **background** (`timeout 300`–`500`, `notify=true`), all three in one turn.
- Do NOT wait on transcripts; do other work, then read the reply files.
- Replies land at `01-HANDOFFS/<seat>-to-gentech/<date>-<topic>.md`.

### 4. Synthesize — the part that actually matters
- Read ALL returns before forming the answer. **Never average them** — look for convergence and for the strongest single objection.
- **Weight disagreement heavily.** If every seat revises your plan, your plan was wrong; say so plainly and ship the revision.
- Capture per-seat **real failures** verbatim — they're the evidence.
- Where seats agree on an *anti-pattern*, that's usually the sharpest finding.

### 5. Record + act
- Write the synthesis to `09-Green Room/ideas.md` (or the relevant spec) with sources, the convergence, and the revised recommendation.
- Commit + push. Log the decision. If it changed a plan, state the new order explicitly.

## What NOT to do
- **Don't fake consensus.** If seats disagreed, report the disagreement — it's the most useful output.
- **Don't consult on everything.** A consult costs 3 agents' turns + tokens. Reserve it for decisions that are big, hard to reverse, or genuinely contested.
- **Don't let the consult become the decision.** It informs; HQ still owns the call and the accountability for it.
- **Don't skip the real-failure ask.** Generic opinions are cheap; "here's the failure I personally hit" is the whole point.

## Worked example (Sep 11 2026)
Question: *what's missing for a good agent-to-agent coordination experience in the agent kit?* → Labs: shared-state concurrency (single-writer leases + conflict detection) + loud routing + shared registry. Pixel: visual review surface + brief contract + human approval gate. Treasury: spend-authority ledger + loss attribution + fleet-wide policy. **Result:** HQ's "governance first" was replaced by "shared-state substrate → ledger with guardrails → review surface → Company Mode." Green Room `09-Green Room/ideas.md`; commits `fa541c16` (asks) → `8209a866` (synthesis). *(The two seats named in that example have since retired and their lanes moved; the format carried over unchanged.)*
