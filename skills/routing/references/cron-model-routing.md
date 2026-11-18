# Cron Job Model Routing

**⚠️ REWRITTEN 2026-11-01. The previous version (June 27, 2026) described a provider stack that no
longer exists — see "What was wrong" below. Read this section first.**

## What was wrong with the old router

The old table specified three lanes:

```
Ollama (local)  FREE   qwen2.5-coder:7b    → NOT RUNNING (localhost:11434 refuses connection)
Z.AI (zai)      Pro    GLM-5.2/5/4.7        → NO KEY   (ZAI_API_KEY and GLM_API_KEY both absent)
Script-only     FREE   no_agent=True        → still valid
```

**Two of the three tiers do not exist.** That is why 29 of 29 cron jobs inherit the seat model — the
router described a world that stopped existing, so nobody followed it.

**Measured 2026-11-01:** exactly **one** provider key is live — `OPENCODE_GO_API_KEY` — and it serves
**28 models**. Routing is no longer about *providers*. It is about **which model on one rail**.

**Jordan, 2026-11-01, on the stack:** *"I did back in the day try z.ai, but I seen that GLM by itself
wasn't what I was looking for, and it became much too expensive. So now we're just using OpenCode Go,
the regular ten dollar subscription, and once I see that we need a backup or something, I'll probably
head on over to Ollama Cloud."*

**So the stack is deliberately one rail:**

```
OpenCode Go ($10/mo)   ← the ONLY lane, all 28 models          LIVE
Ollama Cloud          ← the planned backup, when/if needed      NOT CONFIGURED
Ollama local          ← not running, no plan to restore it      DEAD
Z.AI / GLM            ← tried, rejected: cost + not the right model   DEAD
```

**⚠️ Do not write Ollama Cloud or Z.AI into a live routing table.** Describe them as **planned** and
**rejected** respectively. A router that lists options the fleet does not have is how the previous
version rotted — it described a stack that no longer existed, and 29/29 jobs quietly ignored it.

## The live inventory (measured, not recalled)

`GET https://opencode.ai/zen/go/v1/models` → 28 models, all tool-capable:
`deepseek-v4.1-flash` · `deepseek-v4-pro` · `glm-5.2` · `glm-5.3` · `glm-5.3-flash` · `grok-4.7` ·
`claude-haiku-5-5` · `gpt-5.6-luna` · `gpt-6-luna` · `kimi-k2.7-code` · `kimi-k3` · `kimi-k3.1-pro` ·
`minimax-m3` · `minimax-m3.1-flash` · `mimo-v2.6-flash` · `mimo-v2.6-pro` · `qwen3.8-max` ·
`qwen3.8-flash` · `qwen3.7-plus` · `gemini-4-argon` · `hy3` · `hy4-preview` · `longcat-2.0` ·
`step-5-preview` · `beam-free` · `muse-spark-1.2-contributor` · `muse-spark-1.3-contributor` ·
`iceman-contributor-free`

**⚠️ Calls require `x-opencode-session: <id>`.** Without it the rail returns
`400 MissingSessionID` ("cannot be routed efficiently"). The harness sends it; a hand-written `curl`
does not, and will look like a failure when the key is perfectly good.

## The tiers, measured 2026-11-01

All six round-trip `200` on a trivial prompt; latency is the only cost signal a flat rail exposes.

| tier | model | latency | use for |
|---|---|---|---|
| **FAST** | `claude-haiku-5-5` | **0.7 s** | classification, one-line decisions, "is this stale?" |
| FAST | `mimo-v2.6-flash` | 1.4 s | mechanical extracts |
| FAST | `deepseek-v4.1-flash` | 1.5 s | **current seat default** — general agent turns |
| FAST | `qwen3.8-flash` | 1.6 s | bulk transforms |
| FAST | `glm-5.3-flash` | 1.8 s | vision / auxiliary (pinned) |
| FAST | `minimax-m3.1-flash` | 2.1 s | bulk transforms |
| **DEEP** | `deepseek-v4-pro`, `kimi-k3`, `gpt-6-luna`, `gemini-4-argon` | untested | audits, money code, architecture |

**⚠️ REASONING MODELS RETURN EMPTY CONTENT ON THIS RAIL.** `kimi-k3`, `glm-5.3`, and
`deepseek-v4.1-flash` with reasoning enabled burn the whole `max_tokens` budget inside
`reasoning_content` and leave `content: ""` with `finish_reason: length`. **For a structured answer:
use a non-reasoning model, read `reasoning_content`, or raise `max_tokens` substantially.** A bigger
model does not fix this — it makes the empty answer more expensive.

## Routing by job SHAPE, not by department

Departments inherit the shape; they do not determine it. Treasury's DeFi intelligence work is
judgement; Treasury's position polling is no-LLM. Proto J's media generation is not a model call at
all — it is an image/video API on the BlockRun lane, not the router.

| job shape | examples | route |
|---|---|---|
| **No LLM at all** | sync checks, list audits, backups, link checks, presence/liveness probes | `no_agent` / script only — **zero tokens** |
| **Mechanical** | sign-off scan, brain tidy, vault hygiene, cron health | **FAST** — `claude-haiku-5-5` |
| **Analysis** | revenue report, presence summary, inbox triage, opportunity scan | default — `deepseek-v4.1-flash` |
| **Judgement** | audits, money code, strategy, security review | **DEEP** — pin explicitly |

**⚠️ Most fleet crons are shapes 1 and 2.** Routing only those — off the model entirely, or to the
fast tier — removes most of the spend without touching a single reasoning job.

## Rules

1. **Validate the provider against the schema**, not against a stale doc. Dead keys fail silently.
2. **Script-first.** A job that can be a script must never be a model call. The cheapest token is
   the one you never send.
3. **Measure before pinning.** Latency on a trivial prompt is the only cost signal here — record it.
4. **Pin the tier, never the model name**, and keep the name→tier map in one place: names change,
   tiers do not. (Jordan, 2026-10-31: *intent is the constant; model names are the variable.*)
5. **Routing is Jordan's to set.** Report the recommendation with measurements; wait for the word.

## Pitfalls

1. **The provider name must exist in `config_defaults.py`** — an invalid one resolves to nothing and
   fails silently. `hermes config set` accepts any string; the validator is not a check.
2. **A metered provider in `fallback_providers` is a spend decision nobody makes.** Check it on every
   seat. Measured 2026-11-01: the `nous` fallback drained 1.23 billion cache-read tokens.
3. **`x-opencode-session` is mandatory** on this rail.
4. **Test before assigning** — a model being *listed* is not a model being *served*.
