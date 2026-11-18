# Rail failover — rules, probes and measured traps

Companion to the "Rail failover — standing rules" block in SKILL.md. Tool:
`profiles/gentech/scripts/rail-failover.py`.

## Why this exists

A subscription rail has an **allowance window**, and when it fills the fleet stops. The fallback is not a
formality: it serves traffic the moment the primary runs out, and on a metered rail it is also money. A gate
that watches only one rail leaves both the capacity that carries us and the bill invisible.

## The command surface

```bash
rail-failover.py --check              # measure + recommend, change nothing
rail-failover.py                      # automatic: switch only if a rule fires
rail-failover.py --to ollama-cloud    # force a target (proves it first, then moves every seat)
rail-failover.py --return             # back to primary, only if its window actually cleared
```

`--check` is the safe verb: run it after any config change, and before believing a green usage report.

## Probing a rail — the three things that make a probe lie

**1 · `x-opencode-session` is mandatory on opencode-go.** Without it the API answers
**`400 {"type":"MissingSessionID"}`** — which reads exactly like a dead rail. Send any value:

```python
headers["x-opencode-session"] = str(uuid.uuid4())
```

A probe missing this header reports a perfectly healthy rail as FAILED and will force an unnecessary fleet-wide
switch. **A false outage is its own outage.**

**2 · Never let the Python default `User-Agent` out.** `Python-urllib/3.13` → **403 + Cloudflare `error code:
1010`**; a browser-style UA or no UA at all → 200. Write the rule as "never let the Python default UA out" —
not "a UA-less request is blocked", which sends the next reader to debug the wrong variable.

**3 · Keep `max_tokens` ≥ 16 on opencode.** A very small budget on a reasoning-capable model can return empty
content, which a naive probe scores as a failure.

Minimal working probe body: `{"model": <model>, "max_tokens": 16, "messages":[{"role":"user","content":"reply with the word OK"}]}`.

## The meters — one per rail, and they do not share a shape

| rail | endpoint | returns |
|---|---|---|
| `opencode-go` | `GET https://opencode.ai/zen/go/v1/usage` | `usage.{rolling,weekly,monthly}.{percent, resetsAt}` |
| `ollama-cloud` | `GET https://ollama.com/api/usage` | `totals.{request_count, usage_usd, input_tokens, output_tokens}`, plus per-day buckets |
| `nous` | none known | report `NO_METER`; do not invent a number |

**A subscription rail reports PERCENTAGE, a metered rail reports DOLLARS.** A formatter written for one
`KeyError`s on the other — and because these printers usually exist in two places (a `--report` branch and a
normal path), **fixing one and not its twin leaves the job failing on the path you did not read.**

`resetsAt` is the undo condition: record it whenever you switch, because it is the only evidence that returning
is safe.

## Banding: liveness is not capacity

```
percent >= 95  -> CRITICAL
percent >= 85  -> WARN (if it was OK)
```

A rail that completes a request at 99% is minutes from not completing one. The gate's job is to speak **before**
that, not after.

## Chain reporting

Report the whole chain every run — primary plus each fallback, each against that rail's own meter:

```
PRIMARY  opencode-go    rolling 9% · weekly 10% · monthly 89% (resets <iso>)
fallback ollama-cloud   $18.44 over 7d · 5,685 requests
fallback nous           UNMEASURED — publishes no meter
```

Read the chain from `fallback_providers` in `config.yaml`, in order. If seats disagree on the primary, say so
loudly — one seat left on an old rail otherwise disappears.

## Persisting it

Write each rail's shape-tagged reading to state so the next run and the next agent can see the trend:
`{"kind": "allowance", "monthly_percent": 89}`, `{"kind": "dollars", "usd": 18.44}`, or `{"kind": "none"}`.
**Do not purge the window keys on a rail that reports windows** — the purge exists for the rail that meters in
dollars, and running it unconditionally deletes the numbers the gate was just trusted to measure.

## Sanity checks before trusting any rail report

- Four seats all on the same provider, or the report names the disagreement.
- The probe succeeded on a rail the meter says has room (a 200 with 0% used is suspicious; a 400 with 45% used
  is usually the probe's fault).
- The state file's `binding` matches the config, not last week's.
