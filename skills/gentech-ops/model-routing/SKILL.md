---
name: model-routing
description: "Use when routing, switching or measuring a model rail."
version: 7.0.0
author: gentech
tags: [hermes, model-routing, tiered-routing, cost-optimization, deepseek, kimi]
---

# District state measured 2026-11-13

## District rules (measured), in the order they run

1. **A rail is live only when a real completion answers 200.** A model list answers 200 with no key at all — a models list is not a test. The first HTTP call that matters is a chat completion.
2. **A rail reports four states, and each is a fact:** NOT CONFIGURED (no key), PLACEHOLDER (dummy key), REJECTED (key present, completion refuses), USABLE (real completion succeeded). No interpolation, no "probably".
3. **A placeholder line that looks configured is worse than none.** Comment the .env line until the key is confirmed active on the dashboard.
4. **A rail needs a buyer.** A subscription is not a rail until a completion says 200. Free variants of metered models cannot route (400 on this key) — that is a hard ceiling, not a free level.
5. **A seat's default model is the seat's decision; routing lives in jobs.json, config.yaml runs.**
6. **Gate on the provider's own number, never a local counter.**

---

# Model Routing V4 — measured 2026-10-16

## District rules (measured), in the order they run

1. **A rail is live only when a real completion answers 200.** A model list answers 200 with no key at all — a models list is not a test. The first HTTP call that matters is a chat completion.
2. **A rail reports four states, and each is a fact:** NOT CONFIGURED (no key), PLACEHOLDER (dummy key), REJECTED (key present, completion refuses), USABLE (real completion succeeded). No interpolation, no "probably".
3. **A placeholder line that looks configured is worse than none.** Comment the .env line until the key is confirmed active on the dashboard.
4. **A rail needs a buyer.** A subscription is not a rail until a completion says 200. Free variants of metered models cannot route (400 on this key) — that is a hard ceiling, not a free level.
5. **A seat's default model is the seat's decision; routing lives in jobs.json, config.yaml runs.**
6. **Gate on the provider's own number, never a local counter.**

---

# Model Routing V4 — measured 2026-10-16 — measured 2026-10-16

## ⚠️ "FLASH" IS A SPEED LABEL, NOT A THINKING LABEL (measured 2026-11-10)

**Same prompt, same facts, same rail, measured reasoning tokens:**

| model | reasoning tokens spent | content produced |
|---|---|---|
| **`glm-5.3-flash`** | **3,116** on the 220-word task | answered cleanly |
| **`deepseek-v4.1-flash`** | **~2,400 on a short probe; 3,116 on the long task** | answered **only** once the budget allowed |
| **`kimi-k3`** | **none reported** | answered cleanly |
| `minimax-m3` | 0 | answered, but **2,290 words for a 220-word ask and 6 fabricated numbers** |

**Two rules, both measured, both cheap:**

1. **Budget by model class, not by name.** A reasoning-capable model needs
   `reasoning_tokens + answer_tokens`. **A flat 3,500 output budget silently truncates
   `deepseek-v4.1-flash` and returns empty content** — which the first version of our own test then
   reported as "this model produces nothing." **It produced nothing because we starved it.**
   **Give reasoning-capable models ≥6,000; ~2,000 is enough for a model with no reasoning trace.**
   **BUT BUDGET ALONE DOES NOT FIX A SPIRAL — measured twice:** `deepseek-v4.1-flash` at 6,000 tokens with
   **no** `reasoning_effort` field spent **6,000 reasoning tokens and returned 0 content**
   (`finish=length`). Same model, same prompt, same budget, **`reasoning_effort: low` → 3,902 reasoning
   tokens, 1,224 chars of answer, `finish=stop`.** **Raising the budget buys a longer spiral; the effort
   setting is what ends it. Both knobs, not either.**
2. **`finish_reason: length` + empty content + `reasoning_tokens > 0` is BUDGET TRUNCATION.** Report it as
   that. Never as "no answer", never as a zero. **An absence must not be rendered as an answer** — the
   same defect as a ledger reader returning `[]` for a missing file.

**Hermes already banners truncation** (`agent/turn_truncation.py`): "model hit max output tokens" or "the
prompt filled the context window". **Do not build a second detector** — read the banner, then fix the
budget.

### The final measurement — three runs, one confound removed each time

| run | settings | result |
|---|---|---|
| 1 | flat 3,500, no effort field | three models returned **EMPTY** → misread as a model defect |
| 2 | per-model 6,000, no effort field | **still EMPTY** — flash spent all 6,000 on reasoning, 0 content |
| 3 | 6,000 **+ `reasoning_effort: low`** | **all three answered**, all sourced most sentences |

**Final table (run 3):** `deepseek-v4.1-flash` **166 words · 7 of 7 sentences sourced · 0 invented · 29.2s** ·
`glm-5.3-flash` 215 words · 6 of 10 sourced · 0 invented · **3.3s** · `kimi-k3` 267 words · 9 of 13 sourced ·
**1 invented** · 14.4s.

**Rule: budget sets how long a model may think; `reasoning_effort` sets whether it stops.** A spiralling model
consumes any budget and returns nothing. **For receipt-writing: `reasoning_effort: low` + ≥6,000 tokens + keep
flash as the writer** (tightest and fully sourced); use `glm-5.3-flash` where latency matters; **do not use
`kimi-k3` for claims — it invented a number.**

**And more thinking is not better output.** On the receipt-note task the tightest answer won:
`deepseek-v4.1-flash` wrote **185 words, 7 of 7 sentences sourced, zero invented numbers**, while
`minimax-m3` wrote **ten times as much, sourced 17 of 189 sentences, and invented six numbers.**
**Disciplined beats capable on a task whose whole value is that every claim is checkable.**

## 🆕 AUDIT LANE — Kimi K3.1 Pro is LIVE on both rails (measured 2026-10-23)

**The senior-audit model is now reachable on the primary rail, and the failover is the same model.**

| Rail | Model id | Measured | Cost |
|---|---|---|---|
| **OpenCode Go** (primary) | **`kimi-k3.1-pro`** | **200** ✅ | against the Go allowance |
| **Nous portal** (failover) | **`moonshotai/kimi-k3.1-pro`** | **200** ✅ | **METERED** — $17.28 left of a $22 cap |

**Both need a real browser `User-Agent`**; OpenCode Go also needs the stable `x-opencode-session` header.
**`kimi-k3-pro` is the WRONG id (400).** **Budget ~16000 tokens for an audit** — a 30-token probe returns
`content: None` because the model spends it all reasoning. *(False-empty trap; see `senior-audit-kimi-k3`.)*

**⚠️ Nous caveat measured today:** `x-nous-tool-pool-gated-off: true` — **the tool pool is off on that rail.**
A reasoner that needs tools will not get them there. **Price the failover before committing.**

**Trigger for using this lane (verbatim from the audit skill):** *"A money-handling system needs an independent
read, especially after you have already fixed several faults of the same class in one session — that is the
signal that your own eyes are the limiting factor."* **Jr writes (DeepSeek V4 Flash). Sr audits (Kimi K3.1 Pro).**

## ✅ LIVE STATE — measured 2026-11-17 (authoritative — trust this over any block below)

- **Primary rail (all 4 seats):** `opencode-go` · `deepseek-v4.1-flash` · `https://opencode.ai/zen/go/v1`
- **Fallback rail (all 4 seats):** `ollama-cloud` · `deepseek-v4.1-flash`, then `nous` · `upstage/solar-mini4:free`
- **⚠️ THE ORDER HAS NOW FLIPPED BOTH WAYS, so treat any rail-order sentence in this file as history and read the
  config instead.** ollama-cloud was primary, then opencode-go was retired, then opencode-go was reinstated as
  primary with ollama as fallback. `rail.py` reports the live order per seat; the prose here cannot.
- **OpenCode Go is PRIMARY again, not retired.** Its key is reportedly active to ~2026-11-28 — **after that date a
  fleet-wide failure is the key expiring, not a code fault.** Check the date before you debug a sudden outage.
- **Fallback rail:** holds exactly ONE entry — `upstage/solar-mini4:free` via `nous`, i.e. a **metered provider
  carrying a free-tier model**. That combination cannot bill, so it is resilience without a leak. The previous
  chain also carried `deepseek/deepseek-v4.1-flash-1017`, which **could** bill; it was **METERED and silent** and
  measured a drain of **1,227,576,788 cache-read tokens**, 98% of it from one long-lived session that kept being
  re-read. A loud failure is cheaper than an invisible bill.
- **Ollama Cloud publishes a real meter:** `GET https://ollama.com/api/usage` → `totals.{request_count, usage_usd,
  input_tokens, cached_input_tokens, output_tokens}` plus per-day `buckets`. It is **USD**, not a percent. Read it
  instead of counting our own calls. (`/v1/usage` still 404s — the path is `/api/usage`.)

### Rail failover — standing rules (Jordan: *"when opencode go fills up, we switch everything to ollama cloud and use the same models. We should have rules for this"*)

1. **A monitor READS the binding, never hardcodes it.** `model.provider` in `config.yaml` is the answer. A gate
   with a constant rail in it keeps reporting on the wrong rail forever — and, worse, reports GREEN about the
   fallback while calling the rail actually serving every request "retired". The band must also rise on
   **allowance**, not only on liveness: a rail that answers at 99% of its window is about to stop answering.
2. **Trigger is measured:** any allowance window **≥ 95%**, or the primary **failing two consecutive real
   completions**. One failure is a blip; two is a rail. **A single failed probe is usually a malformed request,
   not an outage — never fail the fleet over on one.** **Check the PROBE before checking the rail:** a health probe
   that omits a header the provider requires reports a *healthy* rail as FAILED, and on this rail the missing
   `x-opencode-session` produces a 400 `MissingSessionID` that is indistinguishable from an outage in a one-line
   verdict. Measured: a failover tool read `89% allowance · completion FAILED` about a rail that was serving every
   request, and would have moved all four seats for nothing. **A false outage is its own outage** — verify the probe
   against one known-good call (the same call the seat itself is making) before acting on its verdict.
3. **All seats or none.** A fleet half on each rail behaves differently depending on which agent answered —
   the hardest bug in the fleet to reproduce. A partial switch is an ALERT, not a partial success.
4. **Same model on the fallback.** A failover that also changes the model has changed two variables and tested
   neither.
5. **Prove the TARGET answers before touching config, and prove the fleet after.** A switch to a dead rail is
   worse than no switch. A config write is not a working rail.
6. **Return only on evidence** — the primary's window has reset *and* a completion succeeds there. Never on a
   timer: a timer does not know whether the provider actually reset.
7. **Never silently.** Record from, to, the measured percentage, the reason, and the reset that will undo it.
8. **Report EVERY rail in the chain, each against its own meter** (Jordan: *"This should have the primary and
   fallback usage"*). A fallback is not decoration — it serves traffic the moment the primary runs dry, and on a
   metered rail it is also money. Reporting only the primary hides both the bill and the capacity that actually
   carries the fleet. Read the chain from `fallback_providers` in `config.yaml`, in order, and label each rung.
9. **Two meter KINDS, one formatter.** `ollama-cloud` meters in **USD** (`/api/usage`); `opencode-go` meters in
   **allowance percent** (`/zen/go/v1/usage`); a rail with neither must print `UNMEASURED` with the reason. Reading
   `spend['usd']` on a percent-metering rail raises `KeyError` and kills the whole job — so the formatter must
   branch on the meter kind, and **the same fix must be applied to EVERY output path**: a report that says
   `KeyError: 'usd'` in a traceback while its summary block printed fine is a bug fixed in one of two places,
   which is not fixed at all, only hidden from whoever reads the other path.

**Tool:** `profiles/gentech/scripts/rail-failover.py` (`--check` · `--to <rail>` · `--return`).
**Full rule text, probes and measured traps:** `references/rail-failover-rules.md`.

### ⚠️ Switching a rail is a THREE-layer change, and layer 2 fails silently

Changing `model.provider` in a seat's `config.yaml` moves **nothing** on its own. All three layers must move:

| layer | what it is | how it fails if skipped |
|---|---|---|
| **1 · seat config** | `model.provider` + `model.base_url` per profile | the seat keeps calling the old base |
| **2 · per-profile keys** | `OLLAMA_API_KEY` in **each** `profiles/<seat>/.env` | **the seat silently falls back to another provider** |
| **3 · hardcoded scripts** | `.py/.sh` that embed the rail URL or key env-var | cron keeps billing/400ing the old rail forever |

**Layer 2 is the one that lies.** Hermes reads credentials **per profile, from that profile's own `.env`** — a key
in the root `/opt/data/.env` is invisible to the seats. The symptom is not an error: the log says
*"Primary provider auth failed … Falling back to nous"* and a turn **succeeds on the wrong rail**. So a
`RAIL-OK` reply is **not** proof of a switch; only the log line `provider=<expected>` and a movement in the
provider's own usage meter are.

**Layer 3 has no owner, so grep for it:** `grep -rn 'old-rail-host' /opt/data/scripts /opt/data/profiles/*/scripts`,
and resolve wrappers — a cron `--script` is usually a two-line `.sh` that execs a canonical `.py`, so a grep of
the wrapper reports clean while the job still calls the old rail.

**One resolver, not N patches.** Keep a single `scripts/rail.py` that answers `base_url()` · `key()` · `model()` ·
`headers()` from the profile's config, and have every model-calling script import it. Then a rail change is a
config change, and the next rail cannot leave a sixth hardcoded URL behind. Full procedure and verification
sequence: **`references/rail-switch-procedure.md`**.

**A configured fallback is a claim until a broken primary makes it answer.** The drill — throwaway profile,
channels muted, only its key broken, and the log line naming the rung that actually served — is in
**`references/failover-proof.md`**. Run it after every rail change, and quote the API-call line as the receipt:
a reply of `OK` is the same string whether the primary or the fallback produced it.
- ⚠️ **Grading rule:** a fallback is a spend finding only when `provider in METERED and model is not :free`.
  Flagging a bare `provider: nous` line reports a cost that does not exist and creates a permanent red light.
- ⚠️ **`fallback_providers` has an OWNER that writes back over text edits.** A regex removal validated as
  `0 armed` on all five configs came back armed — with an extra entry appended — minutes later, each config
  left with a `.bak-fallback-<timestamp>` beside it. `DEFAULT_CONFIG` for the key is `[]`, so that is not a
  schema merge: the running process re-persisted its own copy. **Change it through the command, never the file:**
  ```bash
  HERMES_HOME=/opt/data/profiles/<seat> hermes config set fallback_providers '[{"provider":"nous","model":"upstage/solar-mini4:free","base_url":"https://inference-api.nousresearch.com/v1"}]'
  hermes fallback list          # read it back through the same owner
  ```
  **`HERMES_PROFILE` is NOT the selector for `hermes config`** — it is silently ignored, so four per-seat writes
  all land in the same config while echoing different intents. **`HERMES_HOME` is the variable**, and the only
  trustworthy confirmation is the path the command prints.
- **Subagents:** **no `delegation` config exists on any seat — subagents INHERIT the parent seat's model.** Set `delegation.provider`/`delegation.model` only if you deliberately want to change that.
- **Cron jobs (30 fleet-wide):** **0 declare an explicit model or provider** — every job inherits the seat
  model. That is an unfilled decision, not a policy: mechanical jobs (backups, list audits, liveness probes)
  are on the same tier as reasoning work. **Routing is Jordan's to set; propose, never switch on an inference.**

### Route by job SHAPE, not by department

Departments *inherit* a shape; they do not *determine* one. Treasury's DeFi intelligence work is judgement;
Treasury's position polling is no-LLM. Media generation is not a router job at all — it is an image/video API.

| shape | examples | route |
|---|---|---|
| **No LLM** | sync checks, list audits, backups, link checks, presence/liveness probes | `no_agent` / script only — **zero tokens** |
| **Mechanical** | sign-off scan, tidy, vault hygiene, cron health | fast tier — `claude-haiku-5-5` |
| **Analysis** | revenue report, presence summary, inbox triage, opportunity scan | default — `deepseek-v4.1-flash` |
| **Judgement** | audits, money code, strategy, security review | deep tier, pinned explicitly |

**Measured fast-tier latency on this rail (2026-11-01, trivial prompt, all `200`):**
`claude-haiku-5-5` **0.7s** · `mimo-v2.6-flash` 1.4s · `deepseek-v4.1-flash` 1.5s · `qwen3.8-flash` 1.6s ·
`glm-5.3-flash` 1.8s · `minimax-m3.1-flash` 2.1s. **Latency is the only cost signal a flat rail exposes** —
record it when you pin a tier.

**⚠️ Pin the TIER, never the model name**, and keep one name→tier map. Names change; tiers do not.
(Jordan: *intent is the constant; model names are the variable.*)
- **Newest DeepSeek model:** V4.1-Flash (released 10 Sep 2026) — **we already run it.** A newer *build*, `-1017` (17 Oct 2026), is what our fallback points at. V4.1-**Pro** is named but not announced.
- **Metering:** `GET /usage` on the OpenCode Go rail. Gate on the **monthly** percent — it binds before weekly/rolling. See `provider-quota-diagnosis`.

**Re-measure rather than trust this block:**
```bash
python3 -c "import yaml;d=yaml.safe_load(open('profiles/gentech/config.yaml'));print(d['model'],d.get('fallback_providers'))"
```

**Two measured traps:**
- `https://opencode.ai/zen/go/v1/models` returns **403 `error code: 1010`** (Cloudflare bot block) when the request
  carries the **Python default `User-Agent`** — not when it carries no UA at all (measured: absent UA → 200).
  **A 403 from this API is your UA string before it is your key** — send a browser UA before you rotate anything.
- The Nous rail serves **427 models** (20 DeepSeek). Its `/v1/models` needs the auth header from `/opt/data/shared/nous_auth.json`.   <!-- ⚠️ NOT PRESENT (checked 2026-11-17): this file does not exist on this seat. Do not assume it; verify before relying on it. -->

---


> ⚠️ **The "V3 three-tier / Kimi" system below is SUPERSEDED.** It named Kimi K2.7 and K3 as tiers while
> our live config has run **OpenCode Go** the whole time. A rule that loads every turn and is wrong is worse
> than a missing one — that is why this section sits above it. Kept below for history only.

## The live rail (verify, don't assume)

- **Provider:** `opencode-go` · **base:** `https://opencode.ai/zen/go/v1` · **mode:** `chat_completions`
- **Models our key serves:** `deepseek-v4.1-flash` (default) · `glm-5.3-flash`
- **Two headers are mandatory** — omit either and you get a failure that looks like a permissions problem:
  - `x-opencode-session: <stable value>` → without it: `400 MissingSessionID`
  - a real **`User-Agent`** → **an ABSENT header is fine; the Python/curl DEFAULT is what gets blocked.** Measured on
    one key, one endpoint, one minute: `User-Agent: Python-urllib/3.13` → **403 + Cloudflare `error code: 1010`** ·
    a browser UA → **200** · **no UA header at all → 200**. So the trigger is the bot-shaped *string*, not the
    missing header — and a bare `urllib.request.urlopen()` is exactly the shape that trips it while looking like a
    revoked key. **Write the rule as "never let the Python default UA out", not "a UA-less request is blocked"** —
    the second reading sends the next reader to debug the wrong variable.

## Meter before you route — `/usage` EXISTS

```bash
curl -s -H "Authorization: Bearer $OPENCODE_GO_API_KEY" https://opencode.ai/zen/go/v1/usage
```

Returns rolling / weekly / monthly windows, each with `percent` and `resetsAt`:

```json
{"usage":{"rolling":{"status":"ok","percent":0,"resetsAt":"2026-10-16T20:30:49Z"},
          "weekly":{"status":"ok","percent":8,"resetsAt":"2026-10-19T00:00:00Z"},
          "monthly":{"status":"ok","percent":82,"resetsAt":"2026-10-30T00:43:42Z"}}}
```

**Measured 2026-10-16: monthly 82%, 14 days before it resets.** This endpoint is what makes
usage-aware routing possible — **route on the number, never on a feeling.**

## The free tiers are NOT a fallback for our models (measured, same key, same minute)

| Model id | Result |
|---|---|
| `longcat-2.5-preview-free` | ✅ 200 |
| `cat-jam-free` | ✅ 200 |
| `deepseek-v4.1-flash-free` | ❌ `400 Model is unavailable` |
| `glm-5.3-flash-free` | ❌ `400 Model is unavailable` |
| `nemotron-3-ultra-free` | ❌ `400 Model is unavailable` |
| `mimo-v2.6-flash-free` | ❌ `400 Model is unavailable` |

**The free variants of the two models we actually use are not reachable by API** — consistent with
OpenCode's own note that *most free tiers are OpenCode-client only.* So "switch to the free version of the
model we're on when the allowance runs low" **does not work on this rail.** The only genuinely free calls
available to us are LongCat 2.5 Preview Free and Cat Jam Free, which are unproven for agent work.

**Therefore the fallback lever is a different PROVIDER, not a free tier — and the fallback we now hold is a SECOND METERED POT, not a free one.** We do hold a Nous credential (`/opt/data/shared/nous_auth.json`, `client_id: hermes-cli`, scope `inference:invoke`, short-lived access_token + refresh_token) — the old claim that we hold no Nous key is stale. **But Nous bills against a $22.00 subscription cap (measured 2026-10-21: $19.53 remaining).** So the allowance is still a real ceiling: the control is **spending less**, and a failover decision must name which pot it spends from.

---

# Model Routing V3 — July 27, 2026 (SUPERSEDED — history only)

## Three-Tier System

**Default to DeepSeek V4 Flash.** Escalate only when the task justifies the cost.

| Tier | Model | Cost | Use For |
|------|-------|------|---------|
| **T1 — Default** | DeepSeek V4 Flash | ~$0.15/M in · ~$0.60/M out | Everything unless it fits T2 or T3 |
| **T2 — Medium** | Kimi K2.7 | ~$2/M (13x Flash) | Complex debugging, code review, retry on Flash failure |
| **T3 — Big Boy** | Kimi K3 | ~$15/M out (100x Flash) | Architecture, security audits, design reviews, full-codebase |

## When to Use Each

### T1 — DeepSeek V4 Flash (default, 80%+ of work)
- Cron jobs and daily brain audits
- Quick code generation and boilerplate
- Content drafting and summaries
- Routine terminal work
- Build queue tick and handoff
- Most Telegram replies
- Anything you're not sure about — start here

### T2 — Kimi K2.7 (when Flash isn't reliable enough)
- Complex debugging across multiple files
- Code review of non-trivial PRs
- Data analysis and pattern detection
- Retry after Flash fails or produces wrong output

### T3 — Kimi K3 (when the answer matters)
- Architecture decisions and design reviews
- Smart contract security audits
- Full-codebase analysis (1M context)
- Design audits (portfolio, UI, branding)
- Strategic planning and competitive analysis
- Any task where failure cost > $15

## K3 Thinking Config (Required for Deep Reasoning)

Kimi K3 needs explicit thinking configuration for complex tasks. Without it, K3 may spend its entire max_tokens budget on internal reasoning and produce no visible answer.

```python
# Correct — with thinking
blockrun_chat(
    message="...",
    model="moonshot/kimi-k3",
    max_tokens=8192,
    thinking={"type": "enabled", "budget_tokens": 2048}
)

# Wrong — no thinking, may return empty
blockrun_chat(message="...", model="moonshot/kimi-k3")
```

For very large outputs (full HTML pages, long code), raise max_tokens to 16384 and budget_tokens to 4096.

## K3 Compressed Variant (0.18B)

On July 28, 2026, a community member (@0x0SojalSec) claimed to have compressed Kimi K3 from 2.8T MoE down to **0.18B parameters, 0.10B activated, 700MB** — same architecture, same attention design. This is ~1000x smaller than the original.

**Reality check:** A 0.18B model won't match the full model's quality for architecture decisions or security audits. What it *could* do is run as a local fallback or for simple classification tasks on a VPS or Raspberry Pi. Worth watching — if someone distills a 7B or 13B version that runs on a single GPU, the cost picture changes entirely. For now, the API is still the right call for real work.

## Implementation

### In blockrun_chat calls
```python
# T1 — Default: omit model param
blockrun_chat(message="...")

# T2 — Medium
blockrun_chat(message="...", model="moonshot/kimi-k2.7")

# T3 — Big boy
blockrun_chat(
    message="...",
    model="moonshot/kimi-k3",
    max_tokens=8192,
    thinking={"type": "enabled", "budget_tokens": 2048}
)
```

### In cron jobs
```yaml
# Default: no model override = DeepSeek V4 Flash
# T2: model: { provider: "openrouter", model: "moonshot/kimi-k2.7" }
# T3: model: { provider: "openrouter", model: "moonshot/kimi-k3" }
```

## Provider Notes
- **DeepSeek Official API** — live in public beta as of Jul 31, 2026 (see `references/deepseek-v4-flash-official-api.md`). Native Responses API, Codex-adapted, massively upgraded agent benchmarks (DeepSWE 54.4 vs 12.8 Pro-Preview). DeepSeek docs list Hermes as an official agent integration. Open decision: evaluate switching from Nous to direct DeepSeek (api.deepseek.com).
- **Ollama Cloud** — ✅ **LIVE: the first fallback rung on all four seats** (see the LIVE STATE block above). It held the primary slot 2026-09-07 → 2026-10-15, was demoted, and was reinstated as fallback when opencode-go returned to primary — so **treat any "historical only / not a live provider" sentence you find elsewhere in this file as stale history.** The facts below (endpoint, model-name format, weekly reset) are still current.
  - **API endpoint:** `https://ollama.com/v1` (NOT `ollama.cloud` — that domain is a fake/scam site that returns a warning page. Confirmed Jul 27, 2026.)
  - **Model name format:** bare names only — `deepseek-v4-flash:0731`, `glm-5.3-flash`, `kimi-k2.7-code`. No slash prefix.
  - **Reset cadence is WEEKLY (7 days).** This is why Ollama is the primary subscription: it refills every week.
  - **`/v1/usage` and `/v1/plan` endpoints do NOT exist** on the live API (return `path not found`). To check real state, live-test the inference endpoint (`POST /v1/chat/completions`) or read the dashboard at `ollama.com/settings`.
- **Hermes portal (Nous)** — **LIVE FALLBACK**, all 4 seats, measured 2026-10-19. Model is `deepseek/deepseek-v4.1-flash-1017` — not the old `deepseek-v4-flash`. **⚠️ NOT FREE — corrected 2026-10-21 by live measurement (this used to say "Free, US infra"; it is wrong and was removed).** It is a **metered subscription with a $22.00 cap** — the rail reports its own ledger in response headers. Measured: `paid-access: true` · cap `$22.00` · remaining `$19.53` · spent `$2.47` over 3.1 days at **$0.79/day** (~25 days of runway). **So Nous is a SECOND, SMALLER ceiling than OpenCode Go's $160 allowance — failover buys time, not unlimited runway.** PRICE A FAILOVER BEFORE COMMITTING TO IT. Read the ledger (never a dashboard):
  ```bash
  # POST any tiny chat completion and read the x-nous-credits-* RESPONSE HEADERS
  # cap / remaining / purchased / paid-access / denominator-kind all live there
  ```
  `GET https://inference-api.nousresearch.com/v1/models` lists 426 models including `moonshotai/kimi-k2.7-code` and `moonshotai/kimi-k3`. Direct API calls need a browser User-Agent header (Cloudflare 403 otherwise) — full recipe in `references/nous-inference-api-direct.md`. **The portal REST API is not at portal.nousresearch.com/api/* — every guessed path 404s. The headers are the reliable surface.**
  - **⚠️ Sep 12 correction:** `glm-5.3-flash` is **dead as an AUDIT model** (Z.AI `1113`; Ollama Cloud weekly-capped 429). AUDIT second-opinion now = **Kimi K2.7-code via Nous** (`moonshotai/kimi-k2.7-code`, live). Same for the Critic slot — keep it off glm until Z.AI is re-funded. See E-17 in the error runbook.
- **OpenCode Go / Go Plus — LIVE PRIMARY (Jordan's directive, 2026-10-15 — this REPLACES the stale "RETIRED" note that used to sit here).** We run `provider: opencode-go`, `base_url https://opencode.ai/zen/go/v1`, on **Go Plus** ($40/mo). Models are included against a **per-model monthly dollar allowance**, e.g. DeepSeek V4.1 Flash **$160**, GLM-5.3-Flash **$180**, GLM-5.3 **$120**, Kimi K2.6 **$240**. **Token prices are identical on Go and Go Plus — the plan buys ALLOWANCE, not cheaper tokens.** The binding constraint is the **monthly** cap per model (5-hour = 20%, weekly = 50%, monthly = 100% of the allowance); past it, **free models (LongCat 2.5 Preview Free, Step 5 Preview Free, Cat Jam Free) remain usable rather than hard-blocking**. Requests MUST carry a stable **`x-opencode-session`** header — OpenCode uses it for routing and prompt caching, and without it you pay full price for uncached tokens. Hermes sends it only on builds after v0.21.0; ours is v0.21.5 (verified 2026-10-15). DeepSeek V4.1 Flash is **half price off-peak** — see `provider-quota-diagnosis/references/opencode-go-cost-model.md`.
- **ClawRouter (BlockRun)** — NEW fallback provider, installed + enabled Aug 7, 2026. Local proxy on `127.0.0.1:8402/v1`, 71 models/12 labs behind ONE provider, wallet-signature auth, USDC per-request via x402 on Base/Solana. By BlockRun (same as blockrun wallet). **Run as durable systemd service `clawrouter-proxy.service` (NOT a session background process — that dies on restart and kills the provider for all 4 groups).** Wallet `0xf5f99007...9280D` (Base USDC, default chain) + Solana `BX9ELMCG...`. Default pinned to `free/deepseek-v4-flash` (exact id — `free` alias routes to gpt-oss-120b). All 4 TG groups share one Hermes config, so the provider propagates automatically. Setup + pitfalls in `references/clawrouter-provider.md`.
  - **Free-tier congestion is the #1 failure mode.** `free/deepseek-v4-flash` is hammered by everyone; a slow upstream stalls the shared provider and ALL 4 groups go silent at once (looks like "Entertainment is down" but it's global). Symptom in clawrouter journal: `All models in fallback chain failed` + `Socket timeout, destroying connection`; gateway logs `httpx.ReadTimeout`. **Fix: configure a paid fallback** so a free stall auto-routes instead of going silent — see `references/clawrouter-provider.md` §Fallback chain config.
  - **Fallback chain config (Aug 2026):** `fallback_providers` is a LIST of `{provider, model, base_url}` dicts. The legacy single-dict `fallback_model` key is deprecated — `hermes config set fallback_model.*` warns "not a recognized config key". **`hermes config set fallback_providers '[…]'` DOES work on current builds** — it parses the JSON list, and `hermes fallback list` then shows the chain correctly. An older revision of this line claimed the value landed as a quoted string that `get_fallback_chain` could not parse; that is no longer true and the claim would push you off the one command that survives. **Verify with `hermes fallback list`, not grep** — the owner's rendering is the receipt, and a direct file grep proves only what is on disk, not what the running process loaded.
- **VPS (local)** — last resort, $0.

## YouTube Skills
YouTube Skills for AI Agents (432⭐, MIT) installed at `youtube-full`. Gives agents access to YouTube transcripts, video search, channel browsing, and playlist extraction. Free tier with 100 credits. Install command: `hermes skills install skills-sh/ZeroPointRepo/youtube-skills/skills/youtube-full`

## Version History

**BREAKING CHANGE:** Moonshot released Kimi K3 open-weight on July 28, 2026. 2.8 trillion parameters MoE (104B active), multimodal, agentic — free to download. Previously locked behind Ollama Cloud extra credits.

**What this means:**
- K3 is no longer gated by Ollama Cloud credits — it's open-weight and downloadable
- Self-hosting is now an option (VPS, BlockRun Modal, or local)
- New providers may offer it without the previous credit wall
- This is the world's first open 3T-class model — bigger than anything OpenAI has released publicly

**Current status (Jul 28):**
- Open-weight release confirmed via Moonshot/X (Nahid @nahid_pro09)
- Not yet evaluated on Ollama Cloud or OpenCode Go as a provider option
- Harness Critic still uses `kimi-k2.7-code` for anti-collusion — evaluate K3 as a Critic upgrade once a provider makes it available at reasonable cost or we self-host
- **Do NOT switch cron jobs to K3 yet** — wait until provider availability and pricing are confirmed

**Action items:**
1. Investigate which providers now offer K3 (Ollama Cloud, OpenCode Go, BlockRun)
2. Evaluate self-hosting on VPS or BlockRun Modal
3. If available at T2 pricing (~$2/M), upgrade Harness Critic from kimi-k2.7-code to K3
4. Update this section once provider availability is confirmed

**Kimi K3 IS available on Nous inference API.** Confirmed Aug 2, 2026 via `GET /v1/models` (291 models; includes `moonshotai/kimi-k3` and `moonshotai/kimi-k2.7-code`). The earlier "NOT available on Nous Portal" note (Jul 27) is stale — the portal UI and the inference API are different surfaces. When Ollama Cloud is rate-limited or you need the Critic family from a direct script, use `https://inference-api.nousresearch.com/v1` with the browser-UA recipe in `references/nous-inference-api-direct.md`.

**Current Harness setup (anti-collision):**
- Evolution → `deepseek-v4-flash` (ollama-cloud)
- Critic → `kimi-k2.7-code` (ollama-cloud) — different model family from Evolution for anti-collusion
- Verifier → `deepseek-v4-flash` (ollama-cloud)
- Gardener → `deepseek-v4-flash` (ollama-cloud)

## PITFALL: Cron Jobs Don't Auto-Follow Interactive Model Switches

**Symptom:** User switches models interactively (e.g., `hermes model` → picks deepseek-v4-pro), interactive session works fine, but cron jobs start failing with HTTP 429 ("Free model capacity exhausted") or provider errors. User is confused — "I switched to the paid model, why are crons still failing?"

**Root cause:** Cron jobs carry their OWN `model`/`provider` binding in `jobs.json`, independent of the session's `config.yaml`. An interactive model switch updates `config.yaml` but does NOT touch `jobs.json`. The `cron-provider-sync` job (runs 06:00 + 18:00 UTC) catches this twice daily, but manual switches between those windows leave all LLM cron jobs pinned to the OLD model — sometimes for hours.

**Fix (one command):**
```bash
python3 ${PROFILE_DIR}/scripts/cron-provider-sync.py
```
This reads the session's current `model.default` + `provider` from `config.yaml`, then re-pins every LLM cron job in `jobs.json` to match. Takes ~2 seconds. After the sync, re-run any jobs that failed during the stale window.

**NOTE (Aug 17, 2026):** The `cron-provider-sync` cron job was **removed** at Jordan's direction — we now keep most usage on Ollama Cloud and switch to OpenCode Go only occasionally, managing the two subscriptions manually. Run the script above **on demand** whenever Jordan switches providers/models. It is no longer scheduled.

**Detection:** `hermes config get model` shows the NEW model, but `cronjob list` shows jobs still on the OLD model/provider. If you see 429 errors on cron jobs while the interactive session works, this is almost certainly the cause.

**Observed:** Aug 9, 2026 — Jordan switched from V4 Flash to V4 Pro. Three cron jobs (Hub Nightly Sync, Revenue Monitor, Harness Evolution) hit 429 within the hour. All 41 LLM cron jobs were still on V4 Flash. Ran `cron-provider-sync.py` → all green.

## Rule of Thumb
If you're not sure, use Flash. If Flash fails or the output is clearly wrong, retry on K2.7. Only reach for K3 when the answer matters enough that you'd pay $15 for it.

## Version History
- **7.7.0** (Aug 9, 2026) — Added PITFALL: interactive model switches don't auto-sync cron jobs. Documented the symptom chain (429 on crons after user switches models), root cause (cron jobs carry their own model/provider in jobs.json), and the one-command fix (`cron-provider-sync.py`).
- **7.6.0** (Aug 8, 2026) — Documented ClawRouter free-tier congestion as the #1 failure mode (stalls ALL 4 groups at once; proxy healthy but upstream slow). Added correct `fallback_providers` list schema (legacy `fallback_model` deprecated; `hermes config set` stores the list as a quoted string that isn't parsed — write via config module). Added recipe to clear a per-session `/model` override. Detail in `references/clawrouter-provider.md`.
- **7.5.0** (Aug 7, 2026) — Made ClawRouter proxy a durable systemd service (`clawrouter-proxy.service`) — a session background process dies on restart and kills the provider for all groups. Documented that all 4 TG groups share one Hermes config (provider propagates automatically). Reference file `references/clawrouter-provider.md` now includes the full systemd unit + enable/verify steps.
- **7.4.0** (Aug 7, 2026) — Added ClawRouter (BlockRun) as a new fallback provider. Installed + enabled `hermes-plugin-clawrouter`, local proxy on 127.0.0.1:8402. Key pitfalls documented: `free` alias routes to gpt-oss-120b (not DeepSeek) — pin exact id `free/deepseek-v4-flash`; free tier is congested (fund wallet for paid); config.yaml is write-guarded (use `hermes config set`); no OpenClaw needed to setup. Full detail in `references/clawrouter-provider.md`.
- **7.3.0** (Aug 7, 2026) — Added the fully-automatic provider auto-switch (Ollama ⇄ OpenCode Go): script `~/.hermes/scripts/provider-auto-switch.py`, daily cron, context-save-before-restart, resume-cue message. Full mechanism in `references/provider-auto-switch.md`. Also documented the real usage endpoints: Ollama `GET /api/usage` (NOT `/v1/usage` which 404s), and OpenCode Go has NO usage endpoint (detect via live model test with `minimax-m3`).
- **7.2.0** (Aug 7, 2026) — Corrected OpenCode Go model format: BARE names, not slash (slash returns "Model not supported"). Documented that OpenCode Go's binding constraint is the MONTHLY cap (weekly/rolling can read 0% while monthly is 100%). Documented Ollama Cloud's WEEKLY reset cadence as the reason it's primary, the two-subscription flip strategy (works only when reset windows are desynced), and that `/v1/usage` + `/v1/plan` don't exist on the live API.
- **7.1.0** (July 27, 2026) — Added Kimi K3 reality check: requires extra credits, not in base plan. Harness Critic uses kimi-k2.7-code instead. Provider notes updated: Ollama Cloud is now primary, OpenCode Go is fallback.
- **7.0.0** (July 27, 2026) — V3 three-tier system. DeepSeek V4 Flash as default. Kimi K2.7 for medium. Kimi K3 for big jobs. Added K3 thinking config requirement. Jordan's directive.
