---
name: agent-cost-control
description: "Use when cutting an agent fleet's inference bill."
trigger: "Someone asks how to make the fleet cheaper, a token bill or usage figure appears, or a new periodic job / extra agent seat is about to be added."
tags: [cost, tokens, cron, runtime, efficiency, fleet]
version: 1.0.1
author: gentech
license: MIT
related_skills: [cron-health-standard, cron-truth-layer, agent-state-disaster-recovery]
metadata:
  hermes:
    tags: [cost, tokens, cron, runtime, efficiency, fleet]
    related_skills: [cron-health-standard, cron-truth-layer, agent-state-disaster-recovery]
---

# Agent Cost Control

The bill is not driven by how long the agent's replies are. It is driven by **how many turns run** and
**how much context each turn carries**. Every rule below follows from that, and every optimisation
that ignores it fails.

## When to Use

- Someone asks how to make the fleet cheaper, or a bill/usage figure arrives and needs explaining.
- A recurring job is about to be created — pick its cost class before it exists, not after.
- An extra agent seat is being considered.
- A token-usage alarm fires and the cause is not obvious.

## The model of the cost

```
cost ≈ (turns per day) × (context size per turn) × (price per token of the chosen tier)
```

Measured on this fleet: a **one-shot turn answering a one-line prompt cost ~17,800 input tokens**.
Read that as the base unit. A recurring watcher on a quiet feed pays that base unit every tick to say
"nothing new" — which is why the frequency of a job, not the eloquence of its output, is the thing to
attack.

## Measure first, then cut

Never optimise against a plausible formula. Each turn logs its own bill:

```bash
grep 'API call #' <state>/profiles/<seat>/logs/agent.log | tail -50
# → API call #N: model=… in=… out=… total=… latency=… cache=…/… (…%)
```

- `in=` is the number that matters; `out=` is usually trivial by comparison.
- `cache=` shows how much of the input was served from the prompt cache — cached input is a small
  fraction of the price, so a raw token count without it overstates the bill.
- Before quoting any number, check the notes store for an existing **measured** cost review. Quote
  what was observed, and say when it was observed.

## The levers, in order

**1. Script jobs cost zero — use them.** Every check that is a *check* rather than a judgement
belongs in a script: health assertions, freshness checks, syncs, scrapes, file inventory. Register it
so no model is involved at all. This is the largest available saving and it needs no routing decision.

**2. Gate the agent behind a change detector.** A job can compare its own output against the previous
run and **skip the model entirely when nothing changed**. An hourly watcher on a quiet feed goes from
full price per tick to free on the ticks that matter least. Reach for this before touching a model
tier.

**3. Suppress the post-turn review on unattended runs.** The background memory/skill review fork is
**on by default** and measured at roughly **40% of fleet spend** — on the order of 200K tokens per
event, because it re-reads the whole turn context. It exists to improve a *human's* next session, so
it earns nothing on a scheduled run. Clearing it for automated work is worth more than every
model-tier decision combined, and it is a configuration change rather than an architectural one.

**4. Curate: fewer, bigger jobs.** One nightly digest replaces five hourly watchers and divides the
cost by the run count. An estate that grew one job per idea is the actual problem; merging is a cost
lever.

**5. Tier the model last.** Once 1–4 are done, whatever remains genuinely needs reasoning, and
routing that residual to the cheaper tier is the small term. Doing this first produces a visible
change and a barely-moved bill.

**6. Do not add seats to a fleet with no work.** Consolidating many seats onto one host makes hosting
cheaper and inference no cheaper at all — and the redundancy gained is at the task level, never the
host level, so extra seats buy no resilience against the host dying. Work decides when a new seat
earns its keep; nothing else does.

**7. Every delivered message is also a spend line.** An alert that repeats an unresolved problem
every tick costs tokens per tick (and trains the reader to ignore it). Alert once per distinct
problem and re-arm on success — see `cron-health-standard`.

## Call COUNT is the cost term inside a turn — bundle the checks

Frequency is not the only multiplier. Within a single run, **every tool call is another round-trip to
the model, and every round-trip re-sends the whole cached context.** Measured on one recurring job:

```
cache-read PER API CALL    62k  63k  60k  67k  49k  46k  37k  34k   ← flat
API CALLS PER RUN          27   37   19   18   12   14   11   12   ← varies 3×
```

**Context size was constant; call count tripled.** So a run that "does more things" pays in
round-trips, not in prompt length — and the fix is not a cheaper model, it is **fewer trips**.

**Bundle the cheap checks into ONE invocation.** Three scripts called separately is 3+ round-trips for
one answer; the same three inside one shell command is 1:

```bash
#!/usr/bin/env bash
# sections prefixed, exit contract preserved: 0 clean / 2 findings / 3 could-not-read
run() { local tag="$1"; shift
  local out; out="$("$@" 2>&1)"; local e=$?
  [ -n "$out" ] && printf '%s\n' "$out" | sed "s/^/[$tag] /"
  [ "$e" -eq 2 ] && rc=2; [ "$e" -eq 3 ] && rc=3; return 0; }
run signoff python3 scripts/signoff-check.py
run tidy    python3 scripts/brain-tidy.py
run lists   python3 scripts/list-audit.py
exit $rc
```

**Then tell the job to read further only when the bundle printed findings.** The prompt is the other
half of the saving: an agent that "checks the output and opens three files to confirm" has re-spent
everything the bundle saved.

**Measure it, do not assert it.** Per-run call counts live in `state.db`:

```bash
sqlite3 "file:<state>/profiles/<seat>/state.db?mode=ro" \
  "SELECT session_id, api_call_count, input_tokens, cache_read_tokens
   FROM session_model_usage WHERE session_id LIKE 'cron_%' ORDER BY first_seen DESC LIMIT 10;"
```

`api_call_count` per run is the number the bundle is supposed to move. **If it does not fall after the
bundling, the overhead is in the harness, not the prompt** — and the next lever is the tier, not the
schedule. Shortening the interval is usually the wrong move: it buys the saving by losing coverage,
while bundling buys the same saving and keeps it.

**Same table answers "who charged us":** group by `billing_provider` to prove which lane a run actually
spent on — a fallback can move traffic onto a metered provider without a single log line saying so.

## Pitfalls

- **Shrinking the prompt or the reply to save money.** Output length is noise in the cost equation.
  Cutting a watcher's run frequency, gating it, or converting it to a script is what moves the bill.
- **Reporting a saving without a source.** State the measured figure, the window it covers, and how
  it was read from the logs. An unauditable saving cannot be checked and is usually not there.
- **Assuming a cheap default model means the bill is already optimised.** The expensive term is
  usually the invisible per-turn overhead, not the headline model price. Check what runs *around*
  every turn, not just which model runs in it.
- **Reading raw input tokens as the bill.** Prompt-cache hits are a small fraction of the price; a
  fleet with a high cache-read ratio costs far less than its raw token count suggests.
- **Optimising before measuring.** A change that halves a term you guessed at, while the dominant
  term runs untouched, reads as failure and discredits the whole exercise.

## Reporting

Give the observed numbers with their source and window, name which lever each saving came from, and
separate measured from projected. If a saving is designed but not yet running, say that instead of
folding it into a total.
