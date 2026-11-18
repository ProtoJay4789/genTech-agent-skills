---
name: Provider Tank Inventory
description: How to check each model provider's "tank" — balance, subscription status, reset cycles — before routing a job there. Tank exhaustion is silent until you hit a 429; check first.
---

# Provider Tank Inventory

> ## 🔴 RE-MEASURED 2026-11-15 19:30–19:36 UTC — fleet is on OLLAMA CLOUD; all three rails answer; Nous paid still $0
>
> - **Ollama Cloud (PRIMARY, all 5 seats) `deepseek-v4.1-flash` → HTTP 200 `RAIL OK` in 0.34 s.** Provider meter `/api/usage` 7d: **$6.82783 · 2,486 requests · in 644,924,281 / out 1,512,832 tokens** (621.9M of the input was cached). Day burn **$4.05 (Nov 14) → $2.78 by 19:30Z Nov 15** ≈ **$3.4/day → ~$103 per 30 d**. **This rail publishes USD, not an allowance percentage** — there is no percent to quote and no reset date; the ceiling is unmeasurable until a 429.
> - **Gate state file is STALE, don't quote it:** `usage-gate-state.json` was last written **2026-11-13T23:00Z** (rolling 100% / CRITICAL) — that is the **retired OpenCode window**. The `--report` path exits before `save()`, so the file froze at the rail switch.
> - **OpenCode Go `deepseek-v4.1-flash` → still HTTP 200 `RAIL OK` in 2.15 s** (browser UA + `x-opencode-session: rail-review-1`): `billing_source: go`, `allowance 8.37e-06` vs `list_cost 1.395e-05`. It answers, but the subscription was **cancelled 2026-11-13** (key valid to ~2026-11-28) — a dying rail, not a fallback.
> - **Nous free `upstage/solar-mini4:free` → HTTP 200 `RAIL OK` in 2.16 s**; remaining **5,999,936 / 6,000,000 tokens (1h)** and **2,099 / 2,100 requests**. **Paid `deepseek/deepseek-v4.1-flash-1017` → 404 `insufficient_credits_for_paid_model` — fifth consecutive week unfunded.** **`x-nous-credits-remaining-usd` is still ABSENT on a 200** — only `x-ratelimit-*` headers exist. Nous credit is **$0 for paid ids and not readable as a number**.
> - **Config: no `delegation:` key in any of the 5 configs** (the `delegation` toolset name is not a config block) → subagents inherit the parent seat model.
> - **Cron blast radius: 66 jobs — 58 script-only (`no_agent`, zero LLM, immune), 8 LLM-backed, 0 pinned.** All 8 LLM jobs live in `gentech`, all enabled, and every `model`/`provider`/`base_url` is null → all follow a config change. Split: gentech 46 (38/8), gentech-treasury 19 (19/0), default 1 (1/0), arthur 0, protojay 0.
> - **`fallback_providers` intact in all 5 configs** (`upstage/solar-mini4:free` → `deepseek/deepseek-v4.1-flash-1017`) — the stripper did not fire this week; still verify after every restart.
>
> ## (superseded) RE-MEASURED 2026-11-08 19:33–19:41 UTC — chain had vanished AGAIN; re-wired in 5 seats
>
> - **OpenCode Go `deepseek-v4.1-flash` → HTTP 200 `RAIL OK` in 1.32 s** (browser UA + `x-opencode-session` + bearer). Billing real: `billing_source: go`, `allowance 1.053e-05` vs `list_cost 1.755e-05` on a 57-token call. Gate: **monthly 33% / weekly 41% (binding) / rolling 1%**; weekly resets **2026-11-09T00:00Z**, monthly **2026-11-30T00:43:42Z**. Cron `68e9895a1582`. Healthy — normal burn.
> - **Nous free tier WORKS: `upstage/solar-mini4:free` → 200 `RAIL OK` in 0.69 s, `cost 0`, `source: free_path`.** Token valid to 2026-11-08T19:55:53Z.
> - **Nous paid `deepseek/deepseek-v4.1-flash-1017` → 404 `insufficient_credits_for_paid_model`** ("account balance is too low to use paid models"). Unchanged since 2026-11-01 — still unfunded.
> - **THE CREDIT HEADER STILL DOES NOT EXIST.** Today's full Nous header set on a 200 carried `x-ratelimit-*` (limit/remaining requests + tokens, 1h and 60s windows) and **zero** credit/balance/budget headers. `x-nous-credits-remaining-usd` is **absent, not zero**. Readable meters: `x-ratelimit-remaining-tokens-1h` and per-call `usage.cost` (0 on free ids).
> - **⚠️ REGRESSION REPEATED: `fallback_providers: []` in ALL 5 configs** at 19:33Z (`hermes fallback list` → "No fallback providers configured" in every seat, fleet-wide zero fallback). **Re-wired 19:41Z** (free id first, paid id second) and verified in all 5 via `hermes fallback list`. Backups: `config.yaml.bak-fallback-20261108-*`. **The stripper is still unidentified — assume it recurs after any restart.**
> - **Config: still no `delegation:` key in any of the 5 configs** → subagents inherit the parent seat model.
> - **Cron blast radius: 52 jobs — 48 script-only (`no_agent`, zero LLM, immune), 4 LLM-backed, 0 pinned** (every `model`/`provider`/`base_url` null → all follow a config change). Split: gentech 34 (30/4), gentech-treasury 17 (17/0), default 1 (1/0), arthur 0, protojay 0. Three of the 4 LLM jobs are enabled; `9c36623258ee` is completed.
>
> ## (superseded) RE-MEASURED 2026-11-01 19:31–19:39 UTC — the paid Nous fallback is DEAD, and the chain had vanished
>
> - **OpenCode Go `deepseek-v4.1-flash` → HTTP 200 `RAIL OK` in 0.86 s** (browser UA + `x-opencode-session` + bearer). Billing is real: `usage.opencode.billing_source: go`, `allowance 1.017e-05`, `list_cost 1.695e-05`. Allowance **11% monthly / 23% weekly / 9% rolling**, binding window **weekly at 23%**; 0.8%/day over 29.8 d → 100% ~**2027-02-09 14:53Z**, far past the **2026-11-30T00:43:42Z** monthly reset (`runs_out_before_reset: false`). Healthy — no action.
> - **Nous paid id `deepseek/deepseek-v4.1-flash-1017` → HTTP 404 `insufficient_credits_for_paid_model`** ("account balance is too low to use paid models"). The token is NOT the problem: `/v1/models` returns 200 with 378 ids. **The account cannot serve paid models today** — so the id wired as our fallback since 2026-10-18 answers nothing.
> - **Nous free tier WORKS:** `upstage/solar-mini4:free` 200 `RAIL OK` in 1.03 s, `reflection/beam-1.0-501b-a23b:free` 200 in 0.50 s, `stepfun/step-3.7-flash:free` 200 in 3.16 s (empty content), all `cost 0`. Catalog shrank 428 → **378**; free ids down 8 → **4** (`ornith/ornith-1.5-122b:free` is new).
> - **THE CREDIT HEADER DOES NOT EXIST — re-confirmed.** Full header dump on a live Nous call: `CF-RAY, Connection, Content-Type, Date, Server, Transfer-Encoding, access-control-*`, `cf-cache-status`, `vary`, `x-hikari-trace`, `x-railway-edge`, `x-railway-request-id` — **zero** credit/balance/budget headers. `x-nous-credits-remaining-usd` is absent, not zero. **Never quote a Nous dollar balance. The 404 is the only readable credit signal.**
> - **⚠️ REGRESSION CAUGHT 19:34:30Z: `fallback_providers` was stripped from all 5 configs by the fleet restart.** Present at 19:33:47Z (`backups/pre-restart-20261101-1933/config-gentech.yaml`), gone at 19:34:30Z, and `hermes fallback list` then printed *"No fallback providers configured"* in **every** seat. Between the strip and the repair the fleet had **zero** fallback. Re-wired 19:38Z (free id first, paid id second) and verified in all 4 seats. **Any restart may do this again — check `hermes fallback list` after every one.** Backups: `config.yaml.bak-fallback-20261101-193851`.
> - **Config: no `delegation:` key in any of the 5 configs** → a subagent inherits the parent seat's model.
> - **Cron blast radius:** **46 jobs, 40 script-only (`no_agent`, zero LLM), 6 LLM-backed, 0 pinned** — all 6 live in the `gentech` seat and every `model`/`provider`/`base_url` is null, so all 6 follow a config change.
>
> ## (superseded) RE-MEASURED 2026-10-25 19:31 UTC — both rails live-probed (weekly Usage & Provider Review)
>
> - **OpenCode Go `deepseek-v4.1-flash` → HTTP 200 `RAIL OK` in 1.21 s** (browser UA + `x-opencode-session` required). Tank is **91% monthly / 11% weekly / 1% rolling**; 3.5%/day → 100% ~**2026-10-28 08:42Z**, i.e. **~2.5 days BEFORE the 2026-10-30T00:43:42Z reset**.
> - **Nous `deepseek/deepseek-v4.1-flash-1017` → HTTP 200 `RAIL OK` in 0.54 s**; body reports `usage.cost` **$0.0000327** for a 200-token call. Token was valid to 20:10Z (≈1 h TTL — refresh before judging).
> - **The Nous credit header does NOT exist.** Full header dump on both live calls: **0** headers matching credit/balance/budget; `/v1/credits`, `/v1/me`, `/v1/usage`, `/v1/balance` all **404**. What IS readable: `x-ratelimit-remaining-tokens-1h` = 167,999,968 / 168,000,000 and per-call `usage.cost`. **Never quote a Nous dollar balance — it is not API-readable.**
> - **Config: no `delegation:` key in any of the 4 seat configs** → a subagent inherits the parent seat's model. All 4 seats carry `fallback_providers: [nous / deepseek/deepseek-v4.1-flash-1017]`.
> - **Cron blast radius:** 25 jobs total — **3 LLM-backed, 0 pinned** (every `model`/`provider` field is null → all 3 follow a config change), **22 script-only** (`no_agent`, zero LLM, immune to any rail switch).
>
> ## (superseded) RE-MEASURED 2026-10-18 19:35 UTC — every Status cell below is live-probed, not inherited
>
> Measured today with `hermes fallback list`, `hermes auth list/status`, raw `curl`, and an end-to-end
> `hermes --profile gentech -z "…" --provider nous` call:
> - **The fallback chain EXISTS and it WORKS.** All 4 profiles carry `fallback_providers: [nous /
>   deepseek/deepseek-v4.1-flash-1017]`. `hermes fallback list` → *Primary: deepseek-v4.1-flash (via
>   opencode-go); Fallback 1: deepseek/deepseek-v4.1-flash-1017 (via nous)*. **The old "nothing behind
>   opencode-go" note is dead.**
> - **Nous is a WEAPON, not a hope.** Raw curl with the pooled bearer → **200 in 0.61 s** on
>   `deepseek/deepseek-v4.1-flash-1017`; through Hermes end-to-end → **"RAIL OK"**. Catalog: **428 models,
>   8 carry `:free`**. We hold a real **OAuth device_code credential** (label `jordanjones0902@gmail.com`,
>   scope `inference:invoke`) in the **shared root pool `/opt/data/auth.json`** — `hermes auth status nous`
>   reads *logged in* from **all four** profiles. **We do hold a Nous credential;** the earlier "0 key
>   values" note referred to the `NOUS_API_KEY` env var, which is still absent — and unneeded.
> - **The one real defect: the token lives ~1 h and lapsed silently.** Stored `expires_at`
>   2026-10-18T18:29:36Z; at 19:32Z the raw key returned **401** *"Your API key is invalid, blocked or out
>   of funds"* on both a free and a paid model. `hermes auth refresh nous` → **"Refreshed … status: ok"**,
>   and the same calls then returned 200. **Refresh before judging a tank** — no key and no Jordan needed.
> - **The wired fallback model is a PAID id** (`deepseek/deepseek-v4.1-flash-1017` is *not* among the 8
>   `:free` entries: `poolside/laguna-s-2.1:free`, `poolside/laguna-xs-2.1:free`,
>   `upstage/solar-mini4:free`, `stepfun/step-5-preview:free`, `meituan/longcat-2.0:free`,
>   `stepfun/step-3.7-flash:free`, `meituan/longcat-2.5-preview:free`,
>   `reflection/beam-1.0-501b-a23b:free`). `upstage/solar-pro4:free` and `tencent/hy3:free` are **gone**;
>   `upstage/solar-pro4` (no suffix) and `upstage/solar-mini4:free` exist. `nousresearch/`, `hermes` → 0.
> - **OpenCode Go is the tank running dry:** 86% of the **monthly** allowance (binding), 16% weekly, 0%
>   rolling; **4.6%/day** → 100% projected **2026-10-21 20:53 UTC**, ~9 days before the
>   **2026-10-30T00:43:42Z** reset. Cron `68e9895a1582`; weekly resets 2026-10-19T00:00Z.
> - Unauthenticated `/v1/chat/completions` → **402 x402 challenge** (`network: solana`,
>   `maxAmountRequired: "0"`, `payTo: AAyBzWYM5MQPcTQC3hgU5hXvGvtA4V1RbzUDuukXpWsq`); a `:free` model still
>   demands auth. No `/v1/credits`, `/v1/me`, `/v1/usage` (all 404) → **balance is not API-readable.**
>
> **A weekly job (`4aa9fc4edb5f`, Sundays 19:30 UTC) re-probes every tank and rewrites this table** — read
> the measured timestamp above before trusting any row.


Every model provider is a **tank** with its own:
- **Balance type:** free tier / monthly subscription / weekly subscription / pre-funded wallet / pay-per-token credit
- **Exhaustion signal:** HTTP 429, timeout, or "usage limit reached"
- **Reset cycle:** when the tank refills
- **How to check:** what you can query *before* routing a job

## Tank Table

## Tank Table — Status measured 2026-11-15 19:36 UTC

| Provider | Tank Type | Models (measured live) | Exhaustion Signal | Reset Cycle | How to Check | Status (2026-11-15, live-probed) |
|----------|-----------|------------------------|-------------------|-------------|--------------|----------------------------------|
| **Nous Research portal** | OAuth pooled credential (shared root pool) + free-model tier | paid: `deepseek/deepseek-v4.1-flash-1017` (**404 — account unfunded for paid ids**); 4 × `:free` live: `upstage/solar-mini4:free`, `reflection/beam-1.0-501b-a23b:free`, `stepfun/step-3.7-flash:free`, `ornith/ornith-1.5-122b:free` | **404 `insufficient_credits_for_paid_model`** on paid ids; **401** when the token lapses; **402** x402 when no auth header | Credential ~1 h TTL; free tier persistent | `hermes auth refresh nous`, then curl the base with the pooled bearer | **FREE IDS OPEN, PAID STILL $0 — MEASURED 2026-11-15 19:33Z.** `upstage/solar-mini4:free` → **200 `RAIL OK` 2.16 s, `cost 0`** (token valid to 19:46Z). **Paid fallback id `deepseek/deepseek-v4.1-flash-1017` → 404 `insufficient_credits_for_paid_model`** — fifth week unfunded; the id answers nothing. **No credit/balance header exists** — a 200 carries only `x-ratelimit-*` (remaining tokens 1h 5,999,936 / 6,000,000; requests 2,099 / 2,100). `x-nous-credits-remaining-usd` is ABSENT, not zero. **The 404 is the only readable credit signal: treat paid Nous as $0 until funded.** |
| **OpenCode Go** | Monthly subscription (~$10/mo) | `deepseek-v4.1-flash` (fleet default), `glm-5.3-flash`, `glm-5.2`, `kimi-k2.7-code`, `qwen3.6-plus`, `mimo-v2.5` | `GoUsageLimitError` (HTTP 429) | Monthly → **2026-11-30T00:43:42Z**; weekly → **2026-11-09T00:00Z** | Cron `68e9895a1582` writes `/opt/data/backups/usage-gate-state.json` | **RETIRED RAIL, STILL ANSWERS — MEASURED 2026-11-15 19:34Z.** Live probe **HTTP 200 `RAIL OK` in 2.15 s** (browser UA + `x-opencode-session`); `billing_source: go`, `allowance 8.37e-06` vs `list_cost 1.395e-05` on a 51-token call. **Jordan cancelled the subscription 2026-11-13**; the key still authenticates and is expected to die ~**2026-11-28**. Do not route cron to it and do not count it as fallback — the fleet's fallback is Nous. Any percentage in this row from previous weeks is a dead meter. |
| **Ollama Cloud** | Weekly/monthly subscription, USD-metered (no published %) | `deepseek-v4.1-flash` (**fleet default, all 5 seats**), `glm-5.3-flash:cloud`, `gpt-oss:20b` | HTTP 429 "usage limit"; `401` on a bad key | Not published — no reset date we can read | `curl https://ollama.com/api/usage?range=7d` with `OLLAMA_API_KEY` (per-profile `.env`) | **HEALTHY, PRIMARY — MEASURED 2026-11-15 19:30Z.** `deepseek-v4.1-flash` → **200 `RAIL OK` 0.34 s**. Meter: **$6.82783 / 7 d · 2,486 requests · in 644.9M / out 1.51M tokens** (621.9M cached). Daily burn **$4.05 (Nov 14) → $2.78 by 19:30Z Nov 15 ≈ $3.4/day (~$103/30 d)** — normal burn for 5 seats, no action. **No percentage and no reset exist: headroom is unmeasurable until a 429.** |

**Current fleet wiring (verified 2026-11-15 19:36Z — configs + live probes, all 5 configs: 4 seats + default):**
- **Ollama Cloud `deepseek-v4.1-flash` = the live PRIMARY** (`model.provider: ollama-cloud`, `base_url: https://ollama.com/v1`). Carries the whole fleet; **$6.83 spent over 7 d / 2,486 requests** (measured 2026-11-15). Healthy — normal burn.
- **Nous = fallback, 2 entries, both on the same provider:** `upstage/solar-mini4:free` (verified 200 today) then `deepseek/deepseek-v4.1-flash-1017` (**404 — unfunded; kept so funding restores it without an edit**). Free id first is deliberate: a fallback that 404s is not a fallback.
- **OpenCode Go = retired (cancelled 2026-11-13) but its key still returns 200.** Never route to it: a rail that can be revoked mid-week is not capacity.
- **⚠️ The chain was silently stripped TWICE — 2026-11-01 19:34:30Z and again by 2026-11-08 19:33Z.** Both times every config was rewritten without `fallback_providers` and `hermes fallback list` said "No fallback providers configured" fleet-wide until re-wired. **The stripper is still unidentified. Verify the chain after every restart, and at every weekly review.**
- **Two credentialed providers exist fleet-wide, both in the shared root pool `/opt/data/auth.json`: `nous` and `opencode-go`.** Everything else in this table is keyless or down.
- **Nous credential hygiene:** the pooled token is ~1 h lived. Run `hermes auth refresh nous` before any rail verdict — otherwise a stale token masquerades as a dead provider (401). **A 404 `insufficient_credits_for_paid_model` is a different animal — no refresh fixes it; only funding does.**

**Double-subscription-exhaustion scenario (happened Sep 5, restated with today's facts):** if Ollama Cloud 429s, **Nous is the only controllable tank** and only on its `:free` ids (credential refresh required) — the OpenCode Go key still answers but the subscription was cancelled, so it is not capacity. Local Ollama is down, Groq is keyless, BlockRun's proxy is down. That is a **one-tank fleet**, which is why the Nous credential is worth more than it costs, and why funding the paid Nous id is the cheapest real second tank.
| **Z.AI** | Pay-per-token / subscription | (not reachable — no key) | HTTP 429 "Insufficient balance" | Weekly quota | `GLM_API_KEY` present-and-empty | **NOT CONFIGURED.** Dead since Jul 4 *and* keyless — do not route here. |
| **BlockRun (Kimi)** | Pre-funded wallet | `kimi-k2.7-code`, `kimi-k3` | HTTP 429 / payment-required | When Jordan funds | Dashboard / MCP / ClawRouter | **UNVERIFIED.** Wallet session file exists (`/opt/data/.blockrun/.session`, 66 B, Oct 15) but **ClawRouter `:8402` is NOT listening** and no balance read was possible. Treat as unavailable until probed. |
| **Local Ollama** | Free (self-hosted) | `llama3.1:8b`, `llama3.1:70b`, `qwen2.5-coder:7b` | Service down / model not pulled | N/A | `curl http://localhost:11434/api/tags` | **DOWN.** No `ollama` binary on PATH; `:11434` connection refused (http 000). |
| **Groq free tier** | Free | (not configured) | 429 | Daily | `GROQ_API_KEY` | **NOT CONFIGURED** — key present-and-empty. Not a tank. |
| **OpenAI Codex** | US-only hard fallback | `gpt-5.x` | n/a | n/a | `hermes fallback list` | **CLAIM UNSUPPORTED.** No codex provider or key in any of the 4 profiles; the only fallback entry is Nous. Do not count this as a fallback. |

## Checking Each Tank

### Nous Research portal (pooled credential + free tier)
```bash
hermes auth refresh nous          # ~1 h token — ALWAYS do this first
hermes auth status nous           # expect: logged in
hermes -z "Reply with exactly: RAIL OK" --provider nous   # end-to-end proof
```
- 200 = tank open · **401 = token lapsed (run the refresh) or credential blocked/fundless** · 402 = no auth header
- Catalog: `GET https://inference-api.nousresearch.com/v1/models` (no auth needed; 428 ids, 8 `:free` as of 2026-10-18)
- The wired fallback model is **paid**; the `:free` ids are the free-tier switch targets.
- No credits endpoint (`/v1/credits`, `/v1/me`, `/v1/usage` all 404) → **balance is not readable; never quote a Nous balance you cannot read.**

### OpenCode Go (subscription)
- Error message from any API call tells you directly: `GoUsageLimitError` with workspace ID + reset link.
- Check the workspace dashboard: `https://opencode.ai/workspace/<workspace_id>/go`
- No pre-check API — the 429 *is* the check. **Our measured gate: `/opt/data/backups/usage-gate-state.json`** (written by cron `68e9895a1582`) — read that file, not the dashboard.

### Ollama Cloud (weekly subscription)
- Same as OpenCode Go — 429 is the signal. No pre-check.
- Distinguish from OpenCode Go by provider name in the error metadata.
- **2026-10-18: keyless** (`OLLAMA_API_KEY` present-and-empty in every `.env`) — confirm a key exists before treating it as a tank at all.

### Z.AI
- `glm-4.7-flash` times out (broken since Jul 4, 2026) — do not use.
- `glm-4.7`, `glm-5`, `glm-5.2` return 429 when quota exhausted.
- Check: `curl` any model with a 15s timeout; 429 = exhausted, timeout = broken model.
- **2026-10-18: keyless** (`GLM_API_KEY` present-and-empty) — double-dead, not a tank.

### BlockRun Kimi
- Check wallet balance via BlockRun dashboard or MCP. **Requires ClawRouter (`:8402`) to be up** — 2026-10-18: not listening.
- Pricing: $3/1M input, $15/1M output. Estimate before routing: `(input_tokens/1M)*3 + (output_tokens/1M)*15`.

### Local Ollama
```bash
command -v ollama                     # 2026-10-18: not found on PATH
curl http://localhost:11434/api/tags  # 2026-10-18: connection refused (http 000)
free -h                               # enough RAM for the model (8B = ~8GB, 70B = ~31GB+)
```

## Routing Rules with Tanks

1. **Always route to the cheapest healthy tank first.** Free tanks (Nous free models, local Ollama, Groq free tier) before any paid tank.
2. **Primary and fallback must be on different providers with different reset cycles.** If primary is a subscription (OpenCode Go, Ollama Cloud), the fallback must be a different tank (Nous free, DeepSeek, local). Never set `fallback_model` to the same exhausted provider — that's the stuck-agent trap (see skill body).
3. **When a tank goes dry mid-session:** don't retry the same model. Escalate tier within the same provider (Z.AI: glm-4.7 → glm-5 → glm-5.2) OR switch to a different provider's tank (Nous, DeepSeek, local).
4. **Log the tank state** with every routing decision so the cost ledger reflects reality: which provider, which model, whether the tank was healthy at route time.
5. **Refresh before you judge.** A 401 from Nous is usually a lapsed hour, not a dead provider. Call a tank dead only after `hermes auth refresh nous` has been run and the call still fails.

## Reset Calendar (measured 2026-10-18)

| Tank | Exhausted? | Reset / refill |
|------|-----------|----------------|
| Nous credential | No (refreshes on demand) | Token TTL ~1 h; free tier persistent |
| Ollama Cloud — PRIMARY | No (200, $6.83/7d) | No published reset; 429 is the ceiling (2026-11-15) |
| OpenCode Go | Retired 2026-11-13 (key answers until ~2026-11-28) | n/a |
| Z.AI | Keyless + unusable | — |
| BlockRun Kimi wallet | Unverified (proxy down) | When funded |
| Local Ollama | **Down** | When installed/started |
| Groq free tier | Keyless | — |
| OpenAI Codex | Not configured | — |

**If both OpenCode Go AND Ollama Cloud are down** (both subscription tanks empty), today the only healthy tank is:
- **Nous** (pooled credential, after `hermes auth refresh nous`) — the paid id *and* the 8 `:free` ids
- Local Ollama — **no**, down
- Groq free tier — **no**, keyless
- BlockRun Kimi — **no**, proxy down

That is a **one-tank fleet** between 2026-10-21 and the 2026-10-30 reset. Route accordingly, and keep the Nous credential fresh.
