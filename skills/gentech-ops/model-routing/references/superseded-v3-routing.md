# Model Routing V3 — superseded history only

> **Do not act on anything in this file.** It is retained so that older notes citing "T1/T2/T3" or
> "Kimi K2.7 / K3 tiers" can still be read. The live routing is OpenCode Go (primary) + Nous (fallback),
> described in SKILL.md.

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

## K3 Thinking Config (required for deep reasoning)

Kimi K3 needs explicit thinking configuration for complex tasks. Without it, K3 may spend its entire
max_tokens budget on internal reasoning and produce no visible answer.

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

## K3 compressed variant (0.18B)

A community claim that Kimi K3 was compressed from 2.8T MoE to **0.18B parameters, 0.10B activated, 700MB**
— same architecture, same attention design, ~1000x smaller than the original.

**Reality check:** a 0.18B model will not match the full model for architecture decisions or security
audits. What it *could* do is run as a local fallback or for simple classification on a VPS or Raspberry Pi.
Worth watching — if a 7B or 13B distillation that runs on a single GPU appears, the cost picture changes
entirely. Until then the API is still the right call for real work.

## Implementation (as it was written under V3)

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
