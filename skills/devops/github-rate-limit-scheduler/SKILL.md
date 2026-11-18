---
name: github-rate-limit-scheduler
description: Budget-aware GitHub operation scheduling. Use whenever GitHub work (repo create, fork, PR, search) needs pacing or quota checking. Works on the clean GentechLabs account (5000/hr).
---

# GitHub Rate-Limit Scheduler

> 🛑 **STOP — read `devops/github-account-compliance` FIRST.** It holds the absolute rules
> (403/429 = stop, no bursts, no ad-hoc repo creation, ~30 call cap, use the helper).
> This skill covers *how to schedule* GitHub work; that one covers *what will get the
> account flagged*. Load both before any GitHub write.

## When to use
- Creating repos, opening PRs, forking, or searching GitHub API on GentechLabs
- Any GitHub work that 403s or exhausts quota
- Planning GitHub-dependent queue items

## The core facts — RE-MEASURE, do not inherit

**The numbers below were true of a FLAGGED account. Check `curl -s https://api.github.com/rate_limit`
with the token you are about to use before believing any of them** — a limit read out of a document is a
rumour about the past.

- **Authenticated REST today, measured on both tokens we hold: `core 5000/5000`.** Any note claiming 60/hr is
  describing the flagged era; the correction is one call away and the skill must not be the slower source.
- **The real binder is `search` (30/min) and `code_search` (10/min)** — not core. A code-search loop is what
  gets us throttled; a 5,000/hr core allowance is not.
- GraphQL historically hard-capped 0/0 on the flagged account — **verify before relying on it**, and prefer REST.
- Forks via API were 403-blocked; **treat a fork 403 as a boundary, not a transient** unless the current
  response says otherwise.
- **git push/clone does NOT consume API quota.**

## The scheduler (V4)
- Script: `scripts/github_sync_scheduler.py` (cron `17 */1 * * *`, no_agent, silent when idle)
- State: `${PROFILE_DIR}/state/github_sync_state.json`
- Log: `${VAULT_DIR}/11-Mess Hall/github-sync-log.md`
- Ops: `repo_create`, `repo_check`, `pr_check`, `fork_attempt` (403 → `needs_manual`)
- Budget: min(3 per tick, remaining−4 buffer). Drains queue over successive hourly ticks
- Build-queue wiring: items with `github_op` + `github_repo` fields get auto-queued by `build_queue_tick.py` (`queue_github_ops`)

## How to queue new GitHub work
1. Add op to the scheduler state queue:
   ```python
   import sys; sys.path.insert(0, "${PROFILE_DIR}/scripts")
   from github_sync_scheduler import STATE_PATH, load_state, save_state
   s = load_state(); s["queue"].append({"kind":"repo_create","name":"x","description":"d"}); save_state(s)
   ```
2. Or tag a build-queue item with `github_op` + `github_repo` — the tick pushes it automatically

## Why accounts get FLAGGED (GitHub's own documented rules, Apr 2026 ToS)
GitHub flags an account for automated/inauthentic activity (Acceptable Use §4) and secondary rate-limit abuse. The NEW account (GentechLabs, 5000/hr) MUST NOT repeat what tripped GentechLabs:

**Dangerous automation patterns (what triggers a flag / secondary limit):**
- **Bulk content creation**: >80 content-generating requests/min, >500/hr (repos, releases, issues, PRs, comments). Repo churn is the #1 flag.
- **Concurrent requests**: >100 simultaneous REST+GraphQL. Our cron batches must serialize.
- **Per-endpoint bursts**: >900 points/min REST. A POST/PUT/DELETE costs 5 points; GET costs 1. Don't hammer one endpoint in a loop.
- **Automated starring/following, inauthentic activity, fake-engagement**: instantly flagged.
- **Secondary limit cooldown**: 403/429 → stop ALL calls, wait 24-72h, exponential backoff, then throw. Continuing = integration ban.
- **Excessive bandwidth**: don't store big files (videos, binaries) in repos — use git LFS or host on VPS.

**What's SAFE on the clean account:**
- git push/clone/pull (git protocol, NOT REST — never counted against API)
- Authenticated REST within 5000/hr, spaced, <100 concurrent, <900 pts/min
- Normal human-ish rhythm: don't create/fork dozens of repos in an hour

**Why GentechLabs likely got flagged:** automated repo/fork churn + concurrent agent calls (multiple crons hitting REST in bursts) = "automated excessive bulk activity / rank abuse." The fix going forward: **gate ALL API write ops through the scheduler queue (1-3/tick, spaced), never fire ad-hoc.**

## Rules
- **ALWAYS run GitHub API work through the scheduler queue — never ad-hoc bursts** (this is what got the old account flagged)
- Never retry a fork via API — it's account-blocked, not transient
- Keep a 4-request safety buffer in quota checks
- Prefer git protocol for anything that moves bytes (push/clone/fetch)
- Search API is also restricted (422 spammy flag) — prefer direct `/repos/{owner}/{name}` calls
- Valid token lives at `secrets/github-token`; the env `GITHUB_TOKEN` was stale and must match it

## Verification
- `curl -s https://api.github.com/rate_limit` with token → check `resources.core.remaining`
- After any op: confirm via `curl -s https://api.github.com/repos/{owner}/{name}`
- Log shows every attempt with ✅/❌/🙋 status

## Read-side: cron jobs that poll GitHub

Scheduling writes is only half the exposure. **Every cron that reads GitHub is a client GitHub
sees**, and an unspaced poller that ignores push-back is indistinguishable from abuse.

**Audit rule — enumerate, then classify by HTTP method, never by wording:**

1. List cron jobs, then map each to the script(s) it runs **one level of indirection deep** — a
   job whose prompt names a wrapper shells out to the real script, and the real script is where the
   calls are.
2. Classify each script by the methods it actually issues (`-X POST|PUT|PATCH|DELETE`, `gh … create|edit
   |merge|delete`) against `api.github.com`. **A job's prompt mentioning "push" proves nothing** —
   prompts routinely say "never pushes, per R4" and get flagged by a keyword scan. Read the code.
3. Anything that paginates is a burst risk even when every call is a GET: 143 repos × 1 tree call
   each is 143 calls in a tight loop.

**The guard contract** every reading script should satisfy (shared module, imported by each):

- **Space calls** — a floor of ~1s between requests is comfortably inside 5,000/hr.
- **Honour push-back** — on 403/429 read `Retry-After` first, else `X-RateLimit-Reset` (epoch
  seconds), sleep that long, bounded to a few minutes; never hammer through it.
- **Budget floor** — check `resources.core.remaining` and stop with a reason while budget remains
  rather than draining the hour; an account that runs dry mid-sweep looks exactly like an abuser.
- **Bounded retries with jitter**, only on 429/5xx/transient.
- **Return `(data, reason)`** so a failure is UNKNOWN and can never be read as an empty result.

**Cache the budget check.** `/rate_limit` costs no quota but is still a round trip; calling it
before every request **doubles both latency and traffic in the job whose purpose is to reduce
load**. Cache it for a minute, or re-read every ~25 calls.

## Budgets are per TOKEN, not per agent — publish the number

**Several seats share one token, so a seat that burns the budget leaves the others throttled, and a seat that
hits a 429 has no way to know it was not alone.** Two consequences, both mechanical:

1. **Write the remaining budget where every seat already reads** — a dated page in the vault
   (`11-Mess Hall/usage/<date>-quota.md`) plus a CSV line per run for the trend. Read the provider with
   `/rate_limit`; **never estimate from a local counter of calls** — our count is not theirs, and a drifting
   counter is a confident lie.
2. **Attribution is a handoff line, not a dashboard.** GitHub publishes no per-caller usage, so the only honest
   record of "who spent it" is the spender saying so: `Spent: ~N core, M searches` in its handoff. Per-seat
   proxies cost more than the question is worth.

**One gate, imported by every GitHub-touching script — never a second transport.** When a fleet already has a
shared client module, the new rules belong IN it (or in a thin façade that re-exports it); a parallel
implementation of budget guards drifts, and the older one wins by accident.

The contract that module owes every caller:

- **An identifying `User-Agent` with a contact URL on every request.** A bare client agent is what an edge
  treats as aggregate load, and it makes our traffic unattributable in the provider's own logs.
- **Writes are opt-in at the CALL SITE** (`allow_write=True`). A scheduled job that suddenly writes should be
  impossible by accident, not merely discouraged — the refusal is the feature.
- **A throttle is a BOUNDARY, not a transient.** One honouring of `Retry-After` / `X-RateLimit-Reset` is
  legitimate; a loop through it turns a warning into a suspension. After that: stop, and say **INCOMPLETE**.
- **A caller that gets `None` must report `INCOMPLETE`, never an empty result** — "nothing to report" and "the
  read failed" are different states and only one of them is true.

**Downstream jobs inherit the same discipline**: a link checker that receives 403/429 must classify it as a
boundary ("run incomplete for this path"), not as a dead link — otherwise a throttle is published as a finding
about someone else's site.

## Pitfalls

- **Splitting `curl -i` output on `\r\n\r\n` only will silently blank your response body.** GitHub
  answers over HTTP/2 with **LF** line endings, so the split never matches, the entire body becomes
  "headers", and a JSON parse of `""` yields nothing. Split on `\r\n\r\n` if present, else `\n\n`.
  **And treat a 200 with an empty body as UNKNOWN, not as zero** — this exact bug let a secret audit
  print "0 repos, 0 files, all clean" while the token was returning 143 repos. A guard that fails
  silently is worse than no guard, because the report reads as good news.
- **Do NOT update the token in `.env` without matching `secrets/github-token`** — gh CLI compares them
- A 404 on `repos/{owner}/{name}` via unauthenticated curl is a red herring — always auth
- `gh repo create/fork` silently routes through GraphQL (0/0) — always REST + raw git
