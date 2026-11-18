# Superteam Earn — bounty feed as a scanner source

**What it is:** the Solana ecosystem's bounty/grant/hackathon marketplace (SuperteamDAO). Pays USDC on Solana.
Historically $1.7M+ distributed. This is a **paid work source**, not a job board: no interview, no résumé,
a judged submission and a payout.

**Why it belongs in an opportunity scanner at all:** every other source in this scanner answers *"who is
hiring?"*. This one answers *"who is paying for a build this week?"* — a different question with a shorter
funnel, and the output is a public artifact that the job-hunting side can cite.

---

## Endpoints (verified live; no key needed for discovery)

```bash
# 1. Live listing feed — the whole open set in one call
curl -s "https://superteam.fun/api/listings?take=500&type=bounty"

# 2. One listing's full body — REQUIRED, the feed carries no description
curl -s "https://superteam.fun/api/listings/details/<slug>"

# 3. What the agent API offers (self-describing, cheap to probe)
curl -s "https://superteam.fun/api/agents"
# → {"message":"Superteam Earn Agent API",
#    "register":"POST /api/agents",
#    "submit":"POST /api/agents/submissions/create",
#    "editSubmission":"POST /api/agents/submissions/update"}
```

- **Use `superteam.fun` directly.** `earn.superteam.fun` 308-redirects and `-L` is enough, but the canonical
  host saves a hop.
- `GET /api/agents/listings/live` → `{"error":"Unauthorized"}` without a bearer key. Registration is
  `POST /api/agents`, and probing with `{}` reveals the first required field: `name`.
- **Measured 2026-11-15, after registering a real agent: `GET /api/agents/listings/live` returns `[]` under
  every parameter tried** (`?type=bounty`, `?take=50`, `?status=OPEN`) while the public feed showed 11 OPEN
  listings, **all `agentAccess: HUMAN_ONLY`**. The portal works and holds nothing agent-eligible. Report that
  as `state: "empty"`, never as a failure — an empty set and a broken endpoint are different facts.
- **Do not register as a side effect of a scan.** Registration creates an identity plus a **claim code** that
  must be handed to a human (see the payout wall below). Treat it as a decision, not a step.

## The payout wall — the single most important fact

**An agent can SUBMIT here. An agent cannot RECEIVE.** KYC happens at payout, and the claim code has to be
claimed by a human who completes a talent profile. Consequences:

- Never present this source as agent income. It is a **submission pipeline that pays a named human**.
- Any automated submission flow needs a human owner identified *before* work starts, not after.
- A script that registers an agent and submits unattended is building an unclaimable balance.

## Reading the data without being fooled

| Field | What it actually means |
|---|---|
| `rewardAmount` + `token` | **The headline, not the payout.** A 5,000-token prize in a project token is a guessed dollar value. |
| `rewards` (detail route) | **The real split**, e.g. `{"1":125,"2":75,"3":50}` — a "$500 bounty" whose top prize is $125. Always read this before ranking. |
| `compensationType` | `fixed` = a number. `range` / `variable` = **a ceiling**. |
| `_count.Submission` | Competition. Two hundred entries for a two-hundred-dollar prize is a lottery ticket, not an opportunity. |
| `agentAccess` | `AGENT_ALLOWED` / `AGENT_ONLY` / `HUMAN_ONLY`. Do not assume the agent-friendly tier is present — measure how many listings actually carry it. |
| `eligible` region / `eligibility[]` | Free-text screening questions on the detail route; some listings gate on a signup or a wallet action before any work. |
| `status` | Filter to `OPEN`. |

**The list feed has no `description` and no `skills`.** Ranking on the feed alone means ranking on a title —
the exact failure the jobs scanner was widened to fix. Fetch the detail route per candidate; degrade one row
on a detail miss rather than failing the run.

## Scoring that survives contact with the data

Drop content-only titles (thread / article / meme / explainer / video) — they are the majority of the feed and
they are not a build lane. Then reward: build-shaped title, fixed reward, stablecoin payout, thin competition
(`_count.Submission <= ~10`); penalise hard for crowding (`>= 100` entries) and flag `range` rewards and
non-stablecoin tokens as ceilings rather than values.

A working implementation of exactly this lives at `profiles/arthur/scripts/superteam-feed.py` — read-only,
no key, exit 0 with `[]` on a quiet week, and **exit 1 with `UNKNOWN (not empty)` on stderr if the endpoint
dies**, so a dead feed can never be reported as "no bounties today".

## Wiring it in: a LANE, never an `ats:` board

**Measured 2026-11-15:** running the jobs scanner's own `score()` over four live bounty records returned
`None` for **4 of 4**, because `score()` demands an FDE title family, a years number and a remote gate that a
bounty never has. **Adding this source as an `ats: "superteam"` entry in the board map therefore yields zero
rows forever, silently** — the worst possible failure for a monitor.

The shape that works: the scanner **shells out** to the bounty producer
(`superteam-feed.py --scanner`), parses its JSON, and merges it as its own lane into the state file
(`bounties`), the machine artifact (`bounty_lane`, `bounty_leads`) and the digest. Shelling out rather than
importing keeps the producer maintainable without anyone re-editing the scanner.

**Failure semantics are the deliverable.** The lane function returns `None` when the producer cannot answer
and `[]` never stands in for it: *"UNKNOWN this run (lane did not answer)"* and *"no qualifying build bounties
open"* must be two different sentences. Test it by pointing the lane constant at a nonexistent path and
confirming `None` — a lane that reports a dead feed as an empty feed has learned nothing from the closure
false-alarms that shaped the rest of this scanner.

## Docs drift — re-probe, never trust a guide

The third-party write-ups name `superteam.fun/skill.md` and an `/earn/agents` landing page. **Both returned
404 when probed**; the endpoints that work are the ones in this file, discovered by probing rather than by
reading. The general rule: when an agent-marketplace guide and the live host disagree, the live host is the
spec — probe first, then read the guide as colour.

## Not established

- Whether the authenticated agent listing set is larger or better than the public one.
- Whether `?type=project|hackathon|gig` filters at all — three different values returned an identical set,
  which is either a server-side bug or a misuse of the parameter. Do not build on the type filter until it is
  confirmed to discriminate.
