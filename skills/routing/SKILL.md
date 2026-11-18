---
name: routing
description: "Unified routing — detect topic → route to group, detect complexity → route to model. One system, two dimensions."
category: core
priority: critical
version: 3.1.0
author: GenTech Labs
tags: [routing, smart-routing, model-selection, topic-detection, cost-optimization]
---

# Unified Routing

One routing system, two dimensions:
1. **Topic** → which group (**Gentech EDU**, Treasury, Social Media, HQ) — *Labs, gizmo and pixel are retired*
2. **Complexity + Domain** → which model (OpenCode Go primary; see Dimension 2 for the measured live rail)

## Dimension 1: Topic Routing (Which Group)

| Topic | Group | Chat ID |
|-------|-------|---------|
| Learning, lessons, packs, sessions (EDU) | **Gentech EDU** | `-1003872552815` |
| Finance, DeFi, portfolio, yield, market analysis | Treasury | `-1002916759037` |
| Content, social media, post tracking — ⚠️ **run by Proto J, who is Jordan's own avatar, not an agent** | Social Media | `-1004298089413` |
| Coordination, decisions, blockers, status | HQ | `-1003863540828` |
| **Forge-domain tasks** (code builds, PRs, local git, email) | **→ Handoff via** `01-HANDOFFS/gentech-to-forge/` | **Forge (Desktop) handles** |
| **Gentech-domain tasks** (infra, cron, DeFi, research) | **→ Build on VPS** | **Gentech (VPS) handles** |

### ⚠️ Retired — do NOT route here (Jordan, 2026-10-15)

| Was | Status | Where the lane went |
|---|---|---|
| **Labs** `-1003872552815` | **RETIRED — the chat ID is now Gentech EDU** | EDU, owned by Arthur |
| **gizmo** (technical) | **RETIRED** — folded, not rehomed | the build queue is a file; technical knowledge lives in the Agent Kit |
| **pixel** (social/content) | **RETIRED** | social transferred **intact** to Proto J |
| **`Entertainment/` folder** | **does NOT exist** (checked on disk) | the *inbox lane* `01-HANDOFFS/INBOX/entertainment/` still receives notes |

**Two distinctions that must not blur:**
1. **Labs' chat ID `-1003872552815` is still a live room — it is Gentech EDU now.** Routing to it is correct;
   *calling it Labs* is not. The name changed, the ID did not.
2. **"Entertainment" is a folder name, not a seat.** It survives only as a handoff lane. **Do not route a
   topic to "Entertainment" as a group** — social content goes to **Social Media**.


## Dimension 2: Model Routing (Which Model)

> **⚠️ This section was WRONG for weeks and is rewritten from measurement (2026-10-27).** It previously said
> *"Z.AI / GLM Provider Stack — migrated from Xiaomi/OpenCode Go… Z.AI (zai) | ALL — single provider with full
> ladder."* **Measured: `ZAI_API_KEY` and `GLM_API_KEY` are ABSENT from the profile `.env`; `OPENCODE_GO_API_KEY`
> is set.** The skill was instructing every loading agent to route all work to a provider we have no credential
> for. **A misrouted topic gets corrected; a misrouted model just spends the wrong money.**

**The live rail (measured):** **OpenCode Go, `deepseek-v4.1-flash` as the daily default.** The usage gate reads
**monthly — currently at 92%, band CRITICAL, resetting 2026-10-30T00:43Z** (`backups/usage-gate-state.json`).
**Check the gate before routing anything heavy.**

| Role | Model | Rail |
|---|---|---|
| **Daily default** | `deepseek-v4.1-flash` | OpenCode Go |
| **Auxiliary / vision** | `glm-5.3-flash` | OpenCode Go (pinned 2026-10-27) |
| **Senior audit** | Kimi K2.7-code / K3 | the OTHER rail (resolved at call time) |
| **Dormant fallback** | Nous | metered, limited credits |

**Rules that actually bind:**
- **The auxiliary lane is pinned, not auto-detected.** Without pinning, 9 auxiliary services fall back to
  auto-detect and can silently drain the metered rail. **See `hermes-auxiliary-config`.**
- **`glm-5.3-flash` is a REASONING model** — with `max_tokens` too low it returns HTTP 200 with **empty
  `content`** and `finish_reason: length`. **Use `max_tokens >= 512` in probes, and read both `content` and
  `reasoning`.** A broken test, not a broken model.
- **Do not route to Z.AI until a key actually exists.** Re-verify with
  `grep -c ZAI_API_KEY /opt/data/profiles/<seat>/.env` — the absence is the point.


### Routing Rules

**⚠️ This block previously carried a full GLM-4.x/5.x ladder (Trivial→Complex, domain affinities, and a cost
table down to "$2.60/month") for a provider with no credential on this box.** It is replaced rather than
annotated: **a stale ladder with precise dollar figures reads as authoritative and is the most dangerous form of
a dead rule.**

**What actually routes today — two levers, not a ladder:**

| Lever | Value | How to check |
|---|---|---|
| **Daily default** | `deepseek-v4.1-flash` | `grep -A2 '^model:' /opt/data/profiles/<seat>/config.yaml` |
| **Auxiliary / vision** | `glm-5.3-flash` (pinned) | `hermes-auxiliary-config` |
| **Rail health** | OpenCode Go usage gate | `backups/usage-gate-state.json` — **read it before heavy work** |
| **Escalation** | senior audit on the OTHER rail | resolved at call time, per `develop-and-verify` |

**The cost control that matters is not model choice — it is whether the gate is near its ceiling.** Measured
2026-10-27: **monthly 92%, CRITICAL, 44h to dry.** **At that level the correct action is to pause non-essential
crons, not to hunt for a cheaper model.**

**When a heavier model is warranted:** money-code audits, security review, architecture decisions. **Route those
deliberately and say which rail answered.** Everything else rides the daily default.


### Task-Aware Scheduler (TAS) Implementation

**Location:** `${VAULT_DIR}/10-Labs/model-router/`  
**Tests:** 27/27 passing  
**Agent Kit:** `/root/projects/genTech-agent-kit/core/intelligence/model-router/`

**Usage:**
```python
from model_router import route_task

# Coding always gets GLM-5.2
result = route_task("run the build list", context="coding")
# → {'model': 'glm-5.2', 'provider': 'zai', ...}   ← STALE OUTPUT, not routable here (see the note below)

# Finance gets GLM-5
result = route_task("analyze LP position ROI")
# → {'model': 'glm-5', 'provider': 'zai', 'reasoning': 'finance / simple → glm-5'}

# Quick QA gets free Flash
result = route_task("what is GLM?")
# → {'model': 'glm-4.7-flash', 'tier': 'free', 'reasoning': 'quick_qa / trivial → glm-4.7-flash'}
```

**Cron Job Routing Pattern (current - manual):**
Use `cronjob action=update` with `model` and `provider` parameters:

```python
cronjob(action="update", job_id="5fb8a3cf8160", model={"model": "glm-4.7", "provider": "zai"})
```

**Cron Job Routing Pattern (future - automated TAS):**
Build Hermes middleware that:
1. Intercepts every request
2. Calls `route_task(prompt)`
3. Updates model/provider dynamically
4. Routes to optimal model automatically

**Provider name:** the provider is **`opencode-go`** — verify against your own config rather than trusting this
line: `grep -A5 "custom_providers\|^provider" /opt/data/profiles/<seat>/config.yaml`. **`zai` is NOT a configured
provider on this box (no key exists) — see Dimension 2.**

> ⚠️ **The Python examples above are ILLUSTRATIVE and their outputs are stale** — they return `provider: 'zai'`
> and `model: 'glm-5.2'`, neither of which is routable here. **The module they call (`model-router`) may still
> exist; treat its *output values* as unverified until re-run.** What actually routes is in Dimension 2.

## Dimension 3: Auto-Hub Detection

When someone talks about a topic, auto-detect and log to their hub. No cron — the agent does this in real-time.

### Topic → Hub Mapping

| Topic Signal | Hub | Action |
|-------------|-----|--------|
| Food, cooking, recipes, restaurants | Cookbook | Log dish, suggest next meal |
| Travel, flights, hotels, trips | Travel | Log destination, track plans |
| Fitness, workout, gym, diet | Fitness | Log routine, track progress |
| Goals, targets, bucket list | Goals | Log goal, offer support |
| Hobbies, side projects, learning | Hobby | Create hub if new, log activity |

### Detection Keywords

**Food:** cook, cooking, recipe, dish, meal, food, eat, fried, sautéed, simmered, ingredients, restaurant, grocery. Filipino: adobo, sinigang, tinola, caldereta, pancit, giniling, kare-kare

**Travel:** flight, hotel, trip, vacation, booking, airport, destination, resort, island

**Fitness:** gym, workout, exercise, run, protein, diet, calorie, muscle

**Goals:** goal, target, want to, hoping to, dream, plan, by next year

**Hobbies:** hobby, interested in, learning, practicing, side project

### What To Do

1. Detect topic in message
2. Read hub registry at `${VAULT_DIR}/hubs/registry.json`
3. Find or create the person's hub
4. Log the entry (dish, trip, goal, etc.)
5. Respond naturally — don't mention logging
6. Suggest related items

### Hub Registry

```
${VAULT_DIR}/hubs/registry.json
${VAULT_DIR}/Cookbook/christel-journal.json
${VAULT_DIR}/Travels/christel-travel.json
```

### Important Rules

- **Don't be creepy** — respond like a friend, not a database
- **Don't force it** — "I'm hungry" ≠ recipe. Only log real shares
- **Suggest, don't lecture** — offer ideas, not instructions
- **Filipino vibe** — for Christel, use Filipino dish names and references

## How Routing Works

```
Message → Topic Detection → Group Selection
       → Complexity Detection → Model Selection
       → Auto-Hub Detection → Log to Hub
       → Execute in right group with right model
```

### Example

User: "Debug this Python race condition"

1. **Topic:** Code → **HQ** (*Labs retired 2026-10-15; build work happens wherever the agent is awake*)
2. **Domain:** Code
3. **Complexity:** Complex
4. **Model:** escalate deliberately, and **say which rail answered** — see Dimension 2. **Do not route to
   GLM-5.2/Z.AI; no key exists.**
5. **Execute:** build in HQ, report to HQ

User: "What's the AVAX price?"

1. **Topic:** Finance → Treasury
2. **Domain:** Finance (quick check)
3. **Complexity:** Trivial → rides the **daily default** (`deepseek-v4.1-flash`)
4. **Model:** no escalation needed
5. **Execute:** quick answer; **state the feed rung and timestamp** per the market-data ladder

## Delegation Layer v2 (Aug 29, 2026 — Jordan directive: route work, don't hoard it)

When a message in HQ clearly belongs to a specialist group, HQ does NOT absorb the work. Route it through the handoff mesh:

| Topic surfaces in HQ | Delegate to | Mechanism |
|----------------------|-------------|-----------|
| Code/SDK/contract/build tasks | **HQ** — *Labs retired 2026-10-15; the build queue is a file and work happens wherever the agent is awake* | `01-HANDOFFS/INBOX/hq/` |
| Finance/DeFi/yield/portfolio analysis | **Treasury** (Steward) | Handoff note → `01-HANDOFFS/gentech-to-treasury/` |
| Content/social/video/hackathon submissions | **Social Media** (Proto J — Jordan's avatar, not an agent) | Handoff note → `01-HANDOFFS/gentech-to-protojay/` |
| Local builds/PRs/desktop work | **Forge** (desktop, human-gated) | Handoff note → `01-HANDOFFS/gentech-to-forge/` |

**Why it works now (Aug 29 rollout):** every agent's wake trigger sweeps its lanes every 10 min (silent when clear), and the PA Suite enforces ACK→act→report with 6h-stall escalation to Jordan. Early delegation attempts failed from unseen handoffs — that failure mode is closed.

**Protocol:** write the handoff note (From/To/Date/Status: open + What's needed + Context) → announce the routing decision in the origin chat → specialist ACKs in a return lane note → work happens → return note with What was done / What you should know / What's next. HQ keeps the thread: summary in, task out, result back, all visible in git.

**Do NOT delegate:** coordination, decisions, blockers, cross-group work, anything Jordan explicitly wants in HQ.

## When to Route

**Route automatically when:**
- Message clearly fits a specialist topic
- Build task completed → **HQ** (*Labs retired; work happens wherever the agent is awake*)
- Financial decision needed → **Treasury**
- Content/social discussed → **Social Media** (*was Entertainment — retired*)
- Learning/lesson/pack work → **Gentech EDU**

**Never route to:** Labs, gizmo, pixel, or "Entertainment" as a group — **all retired 2026-10-15.**

**Stay in HQ when:**
- Topic is coordination/meta
- Asking about routing itself
- Topic spans multiple groups
- User explicitly wants HQ

## Build Queue Auto-Detection

When a buildable idea surfaces in ANY group, add to build queue — don't build immediately.

**Detection signals:** "We should build...", "This could be a...", "What if we made...", "Let's build..."

**Response:** Acknowledge → Add to `scripts/build_queue.json` → Tell user

**Exception:** "Build it now" / "green light" / "ship it" → skip queue, build immediately.

## Run the Build List Trigger (Mandatory)

When Jordan says any of the following, this **overrides all other context**:

| Trigger Phrase | Action |
|----------------|--------|
| "run the build list" | Execute build-queue skill immediately |
| "run the build queue" | Same |
| "go down the list" | Same |
| "knock out the queue" | Same |

This is not a suggestion — it's a mandatory skill trigger. Stop current topic, load the build-queue skill, execute.

## Two-List System (Orchestrator + Build Queue)

Jordan established a clean separation — June 24, 2026:

| List | Location | Who Adds | What Goes Here |
|------|----------|----------|----------------|
| **Orchestrator List** | `HQ/jordan-queue.md` | Agent or Jordan | Jordan's personal action items only |
| **Build Queue** | `scripts/build_queue.json` (canonical JSON) | Agent only | Technical build tasks, start to finish |
| **Build Queue (human-readable)** | `10-Labs/build-queue.md` | Agent only | Summary of JSON queue for quick reference |

**Pitfall:** The canonical build queue is `scripts/build_queue.json` (v50+, 28 items). The `10-Labs/build-queue.md` file is a human-readable summary that may not exist until a cron job creates it. Always read `scripts/build_queue.json` for the authoritative list. If `10-Labs/build-queue.md` doesn't exist, create it as a summary after adding items.

### Routing Rules for Cron Jobs
When a cron job finds issues, route them:

| Issue Type | Where It Goes | Who Handles |
|------------|---------------|-------------|
| Small fix (config, doc, stale data) | Auto-fix in cron | Cron job does it |
| Big task (new platform, API listing) | Build Queue | Labs agent |
| Human-only (wallet, DNS, account) | Orchestrator List | Jordan |

**Never put Jordan action items in the Build Queue. Never put build tasks in the Orchestrator List.**

### Cron Job Prompt Pattern
When updating cron jobs to be action-oriented, use this structure:

```
## ROUTING RULES

### Small fixes (do automatically)
- Code/config fixes → Make the change, commit it
- Missing documentation → Create the file
- Stale data in vault → Update the file

### Big tasks (add to Labs build queue)
- New platform registration → Add to build queue
- API listing scaffolding → Create files, add to build queue
- Competitor counter-strategy → Add analysis to build queue

### Human-only tasks (add to orchestrator list)
- Profile updates requiring wallet connection → Add to orchestrator list
- DNS changes → Add to orchestrator list
- API keys or account setup → Add to orchestrator list
```

### Pitfall: Don't Mix Lists
- Jordan's to-do items in the Build Queue get lost — he doesn't read it
- Build tasks in the Orchestrator List confuse the agent — it tries to do them itself
- Always verify which list an item belongs to before adding

## Cron Job Creation Rules

**BEFORE creating any cron job, ALWAYS:**

1. **List existing jobs** — `cronjob(action='list')`
2. **Check for duplicates** — same name, same schedule, same purpose
3. **Check for conflicts** — jobs running at the same time that could crash
4. **Check for redundancy** — jobs doing similar things that should be consolidated
5. **Report to user** — "Found X similar jobs. Creating new one anyway? Consolidate?"

**COLLABORATOR GUARD (CRITICAL):** When Vanito or any non-technical collaborator asks you to create a timed/recurring task, you MUST:
- Pause and explain: **"This will create a recurring job that runs every [X minutes/hours] and costs money each call — is that what you want?"**
- Get explicit verbal confirmation before creating it
- Do NOT assume they understand cron mechanics or billing implications
- Why: Vanito accidentally created a `every 10m` cron that ran `blockrun_video` at $0.26/clip, burning ~$35 in under 2 days without anyone knowing

**Provider name check (CRITICAL):**
When setting model on a cron job, the provider MUST match the exact `name` field in `custom_providers:` config. Check config first:
```bash
grep -A3 "custom_providers" ~/.hermes/profiles/gentech/config.yaml
```
Wrong: `custom:XiaomiMega` ❌
Right: `custom:Token-plan-sgp.xiaomimimo.com` ✅

**Delivery target selection for cron jobs (established Jul 17, 2026):**
| Cron Type | Delivery Group | Rationale |
|-----------|---------------|-----------|
| PR monitoring (PR Scout) | HQ | Inbox duty + decisions — needs Jordan's attention |
| Compliance/listing (x402 Compliance) | **Gentech EDU** *(was Labs — retired)* | Technical work, auto-queue to build list |
| Build status (Build Queue Snapshot) | **HQ** | Team visibility on active builds |
| Finance (Portfolio, Market, LP) | **Treasury** *(was Strategies)* | Financial analysis |
| Revenue (Revenue Monitor) | HQ | Bottom-line status for founder |
| Content (Shop, Social) | **Social Media** *(was Entertainment — retired)* | Content creation and distribution |
| Research (Ecosystem, Opportunity) | HQ or Origin | Depends — scanning for Jordan vs technical audit |

**Conflict detection:**
- Same time slot (within 5 min) = potential crash
- Same purpose = duplicate
- Same script = redundant
- Same delivery target + similar schedule = consolidation candidate

**Auto-consolidation rule:** If a new job overlaps with an existing one, consolidate instead of creating a duplicate. Update the surviving job's prompt to absorb the new job's responsibility.


## Cross-Channel Message Forwarding

**Two different mechanisms — do not confuse them.** `hermes send` posts *a message to a chat*; `hermes peer dm`
*walks a seat and wakes it*. **Only the second is agent-to-agent.**

### 1. Post to a channel — `hermes send`

```bash
hermes send --to telegram:-1003863540828 "Message here"
cat /tmp/message.txt | hermes send --to telegram:-1003863540828
hermes send --list          # every configured target
```

**Key point:** works without the target agent running — it reuses gateway credentials directly.

### 2. Reach a SEAT — `hermes peer dm` (⚠️ addressing corrected 2026-10-27)

```bash
hermes peer list                       # → fleet  http://127.0.0.1:8642  [key set]
hermes peer dm fleet/arthur "you have a handoff"
hermes peer dm fleet/gentech-treasury "…"
hermes peer dm fleet/protojay "…"
```

- **`fleet` is the single registered peer**, not one peer per seat. **The working form is
  `hermes peer dm fleet/<seat>`.** The **old per-seat form (`hermes peer dm arthur`) resolves nothing** —
  the seat is the *suffix*, not the peer name.
- **A DM wakes the seat and is not a record.** Delivery must be **verified** — by the reply it prints, or, when
  the client times out, by the seat's own activity in `profiles/<seat>/logs/agent.log`.
- **The vault handoff in `01-HANDOFFS/` remains the delivery of record.** **DM to wake, vault to record.**
- **Never report a wake that did not land.**

### 3. The transport trap: the vault is NOT a git repo (measured 2026-10-27)

`git -C /opt/data/.obsidian-vault rev-parse --git-dir` → **`fatal: not a git repository`**.
**Vault sync is Obsidian (`ob`), not git.** Any instruction saying *"commit and push the vault"* is currently
**unexecutable** — including the ACK rule in `01-HANDOFFS/INBOX/README.md`. **That is why the ACK lane went
quiet: not neglect, a missing mechanism.** See `00-HQ/process-audit-2026-10-27.md`.

### Channel IDs (⚠️ re-measured 2026-10-27 — the old table named retired groups)

| Channel | Chat ID | Notes |
|---|---|---|
| HQ | `-1003863540828` | coordination, decisions, blockers |
| **Gentech EDU** | `-1003872552815` | **this ID was "Labs" — the room remained, the name changed** |
| Treasury | `-1002916759037` | finance, DeFi, yield |
| Social Media | `-1004298089413` | ⚠️ **unverified** — the bot cannot see this room; confirm before relying on it |

**Do NOT list cron deliveries here.** A channel's job list changes weekly and a stale list is worse than none —
**read the live job list instead: `hermes cron list`, or `profiles/<seat>/cron/jobs.json`.** The old table in
this file named *Labs* and *Entertainment* deliveries and was wrong on both.

## Rules
1. Always announce routing decision — don't silently route
2. If ambiguous, stay in HQ and ask
3. HQ is fallback for everything
4. User can override with "stay here"
5. After routing, summarize what was sent where
6. Check vault for context before replying
7. Relaxed build exception: small in-group builds OK
8. **Telegram links must be tappable** — bare URLs on own line, not in tables
9. **Split long messages** — under 1500 chars each (Telegram hard limit is 4096, but 1500 is safe for formatting)
10. **Cron job creation** — ALWAYS check existing jobs first for duplicates/conflicts
11. **A one-word reply is not an instruction to run your own next step.** "Done", "ok", "sure" frequently
    close a thread *other than the one you just spoke in*. When the planned follow-up is a whole workstream
    (a four-seat round, a sweep, a build), spend one cheap move resolving the subject first — measure the
    thing the ack claims (the record, the DB, the file), or ask one short question. **Answer Jordan's last
    question, not your last plan.** Getting this backwards costs a full turn and reads as not listening,
    even when every number in the reply is correct.

## Pitfalls

### Provider Names Are Case-Sensitive and Specific
The custom provider name in cron jobs MUST match the `name` field in `custom_providers:` config exactly. Example: `custom:Token-plan-sgp.xiaomimimo.com` NOT `custom:XiaomiMega`. Wrong name = "Unknown provider" error. Always check config first:
```bash
grep -A5 "custom_providers" ~/.hermes/profiles/gentech/config.yaml
```

### OpenCode Go Model Availability
Not all models are available on OpenCode Go. Verified working: `qwen3.6-plus`, `mimo-v2.5`, `kimi-k2.6`. NOT working: `step-3.5-flash`. Always test a model before assigning it to cron jobs:
```bash
API_KEY=$(grep OPENCODE_GO_API_KEY ~/.hermes/profiles/gentech/.env | cut -d= -f2-)
curl -s -X POST "https://opencode.ai/zen/go/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"MODEL_NAME","messages":[{"role":"user","content":"Say hi"}],"max_tokens":10}'
```

### Wallet Ownership Rule
NEVER assume the agent controls a wallet. Always ask the user for their wallet addresses. Agent-generated wallets are unowned unless the user confirms they have the private keys. Fund only wallets the user explicitly provides.

### Model routing for cron jobs

**⚠️ The rows that used to live here named Xiaomi Custom, BlockRun and a free OpenCode Go tier — none of which
matches the measured rail.** What binds today:

- **Script-only jobs** (`no_agent=True`): **no model needed** — the cheapest correct answer.
- **Everything else**: rides the **daily default** (`deepseek-v4.1-flash` on OpenCode Go).
- **Heavy/escalated**: money-code audits and security review only — **route deliberately and record which rail
  answered.**
- **Before assigning a model to a job, check the rail gate** (`backups/usage-gate-state.json`). At CRITICAL the
  answer is fewer jobs, not a different model.

**Verify a model before trusting it in a job** — `glm-5.3-flash` is a reasoning model and returns **empty content**
under a low `max_tokens`; use `>= 512` and read both `content` and `reasoning`:
```bash
API_KEY=$(grep OPENCODE_GO_API_KEY /opt/data/profiles/gentech/.env | cut -d= -f2-)
curl -s -X POST "https://opencode.ai/zen/go/v1/chat/completions" \
  -H "Content-Type: application/json" -H "x-opencode-session: probe" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"model":"MODEL_NAME","messages":[{"role":"user","content":"Say hi"}],"max_tokens":512}'
```
**⚠️ The `x-opencode-session` header is REQUIRED** — without it OpenCode Go returns
`400 MissingSessionID`. A probe without it reports a failure that is not real.


### Known routing gap (Jun 2026) — ⚠️ OBSOLETE, kept only so it is not re-derived

**This described a MiMo-vs-GLM-5.2 trade-off. Both sides are moot: `GLM-5.2` has no provider on this box, and
MiMo is no longer the assigned model on any job.** **Do not act on this section.** For what routes today, see
Dimension 2 and "Model routing for cron jobs" above.

### Fix routing gaps on discovery
When a routing mismatch is found (wrong model for domain, suboptimal provider for task type), fix it immediately — don't just flag it in a report. Jordan's directive: "Less troubleshooting, fix all issues." Update the cron job model/provider on the spot, verify it works, then report what was fixed.

## References
- Code: `${VAULT_DIR}/10-Labs/model-router/` — Model router module (27 tests, 84.6% savings)
- GLM Model Router Guide: `references/glm-model-router.md` — Quick reference, cron update patterns, coding rule
- x402 Bazaar: `references/x402-bazaar.md` — How to get listed, API pricing, revenue monitor
- Wallet Security: `references/wallet-security.md` — Jordan's verified wallets, agent-generated wallet rules
- Cron Model Routing: `references/cron-model-routing.md` — Provider names, model availability, job distribution
- Cloudflare Setup: `references/cloudflare-setup.md` — DNS, SSL, security headers for gentechlabs.net
