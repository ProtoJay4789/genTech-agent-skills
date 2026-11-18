# Superteam Earn — scan it, then execute one

Solana-ecosystem bounty marketplace (SuperteamDAO). Pays USDC/USDG/SOL. It is the only source in the paid-work
set that pays for a **submission**, not a **hire** — no interview, no résumé, the work is the application.

---

## 1 · Discovery — the public JSON feed, no key

```bash
# every open listing in one call
curl -s "https://superteam.fun/api/listings?take=500&type=bounty"

# one listing's full body — REQUIRED, the feed carries no description
curl -s "https://superteam.fun/api/listings/details/<slug>"
```

Use `superteam.fun` directly. `earn.superteam.fun` 308-redirects and `-L` is enough, but the canonical host
saves a hop. The feed is a plain JSON array — parse it, never scrape the rendered page for the listing set.

**Do NOT read an empty agent endpoint as "nothing is available".**
```bash
curl -s -H "Authorization: Bearer $KEY" https://superteam.fun/api/agents/listings/live
```
This endpoint lists only `AGENT_ALLOWED` / `AGENT_ONLY` listings. It can legitimately return `[]` while the
public feed shows a dozen open bounties, because the human tier dominates. Measured: `[]` under every
parameter combination while every open listing carried `agentAccess: HUMAN_ONLY`. **Report that as
`empty`, not as a failure and not as "no bounties"** — a dead feed and an empty feed must never print the
same sentence.

Registration (`POST /api/agents`, first required field `name`) mints an identity and a **claim code**. Treat it
as a decision with a side effect, not as a step in a scan.

## 2 · Read the fields that decide, not the headline

| Field | What it actually means |
|---|---|
| `rewardAmount` + `token` | the headline, not the payout. A project-token prize is a guessed dollar value |
| `rewards` (detail route) | **the real split** — `{"1":125,"2":50}` means a "$500 bounty" pays $125 to first |
| `compensationType` | `fixed` = a number; `range` / `variable` = **a ceiling** |
| `_count.Submission` | competition. 100+ entries for a small prize is a lottery ticket |
| `agentAccess` | `HUMAN_ONLY` / `AGENT_ALLOWED` / `AGENT_ONLY` — measure how many actually carry the agent tier |
| `region` + `eligibility[]` | region lock and free-text screening questions on the detail route |
| `status` | filter to `OPEN` |

**Region lock is a JSON field, so filter it in code.** Many listings are open to one country only (and the
chapter listings — Nepal, Brazil, Canada-only, etc. — are ineligible for a US-based claimant). Reading
individual listing pages to discover this is wasted work; the detail route already carries `region`.

Rank on **per-place payout × win probability**, not on prize pool. Drop content-only titles (thread / article
/ meme / explainer / video) outright — they are the majority of any batch and they are not a build lane.

## 3 · The payout wall

**An agent can submit here. An agent cannot receive.** KYC happens at payout and the claim code must be
claimed by a human who completes a talent profile. Consequences:

- Never present this as agent income. It is a **submission pipeline that pays a named human**.
- An unattended loop that registers and submits builds an unclaimable balance.
- Identify the human claimant *before* the work starts, not after.

## 4 · Executing the one you picked

Choosing is half the job; the submission is a small engineering project with its own gates.

**Step 1 — write the brief before any code.** Pull the detail route's full description and separate:
- **hard gates** — the conditions that void the entry (a funded wallet, a minimum deposit, a platform signup,
  a mandated public post, a submission form). Missing one is not a low score, it is a disqualification.
- **judging criteria** — what ranks you (volume, breadth of usage, consistency, quality of execution,
  social contribution). These shape the artifact; the hard gates shape whether it counts at all.

Keep them in a `REQUIREMENTS.md` next to the code, quoted from the listing. A brief reconstructed from memory
loses exactly the clause that voids the entry.

**Step 2 — check the money gate against the user, immediately.** If the rules require funding a wallet, a
minimum deposit, or paid credits, that is a **spending decision**, not a build step. Say so at the top of the
plan and get an explicit yes. Do not build a plan that quietly assumes the funds exist.

**Step 3 — build the provable half offline, first.** Anything that needs a funded wallet can wait; the part
the judges score on execution quality usually cannot. Build it so it runs with **no key and no funds** and
demonstrates the graded property in a test suite. The shape that worked for a "governed capital agent" bounty:

```
mandate → policy check → simulation gate → signer interface → append-only receipt
```

- **deny by default** — a cap that defaults to unlimited is not a control; an unset allowlist forbids everything
- **not-simulated ≠ passed** — a gate that could not run reports `UNAVAILABLE` and **blocks**; only a real pass proceeds
- **the signer is an injected interface that refuses offline** — never generate or store a keypair to "demo" a flow
- **`0 ALLOWED` is the correct offline result** — if a harness prints allowed rows on a machine with no wallet, it is lying
- **append-only ledger** — one receipt per attempt, denial and block included; a skipped action must never vanish

**Step 4 — name what the offline artifact cannot prove.** Live XP, on-chain volume, real signatures. Mark them
`NEEDS LIVE WALLET` in the code and the README. A submission that implies live activity it does not have is
the one failure mode that costs the whole entry.

## 5 · Yield reality

Global, dev-shaped, low-competition bounties are rare in any batch; most listings skew content/UGC, and the
best-fitting dev work is often region-locked. Check the submission count before committing: 100+ entries with
days left is a long shot, not a sprint. **The durable return is usually the artifact**, which keeps paying as a
portfolio link long after the pool is split.

## 6 · Docs drift

Third-party guides name `superteam.fun/skill.md` and an `/earn/agents` landing page; both returned 404 when
probed while the endpoints above worked. When a guide and the live host disagree, **the live host is the spec**
— probe first, read the guide as colour.
