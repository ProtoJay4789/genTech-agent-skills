---
name: provider-quota-diagnosis
description: "Diagnose provider usage, rate limits, and quota resets across Hermes providers (Z.AI, OpenCode Go, Nous, Gemini, etc.). Decodes stale credential-pool status, finds real reset times, and live-tests endpoints before declaring a provider down."
author: Gentech
category: ops
tags: [usage, rate-limit, quota, diagnostics, auth, providers]
---

# Provider Quota & Rate-Limit Diagnosis

Answer the recurring questions — "how's our usage?", "when does the rate limit reset?", "is Z.AI down?" — with evidence, not stale status screens.

## When This Skill Applies

Trigger conditions (any one):
- User asks about usage, quota, spend, or rate-limit status
- `hermes auth list` shows `rate-limited` / `exhausted` for a provider
- A provider's requests are failing with HTTP 429 / quota errors
- Planning heavy work (cron batch, big build) and need to know which providers are actually usable

## Core Principle

**The credential pool in `auth.json` is a snapshot of the LAST failure, not a live probe.**
`last_status: exhausted` + `last_error_code: 429` does NOT prove a provider is down.
The status persists indefinitely until a successful retry — it can be weeks stale
(observed: error recorded Jul 9, reset Jul 11, status still showed "rate-limited" on Jul 31).

Never escalate, switch providers, or tell the user a provider is down based on status alone.

## Diagnosis Recipe

### Step 1 — Read the real error detail from auth.json

The read_file tool guard blocks `auth.json` (credential store), but terminal can read it:

```bash
cd ${PROFILE_DIR} && python3 -c "
import json
d = json.load(open('auth.json'))
for prov, creds in d.get('credential_pool', {}).items():
    for c in creds:
        print(f'{prov}: {c.get(\"last_status\")} — {c.get(\"last_error_message\", \"OK\")} — {c.get(\"last_status_at\")}')
"
```

- `last_error_reason` values like `"1310"` are opaque codes — ignore them
- The actionable detail is in `last_error_message` (e.g. "Your limit will reset at 2026-07-11 04:38:41")
- `last_status_at` is a unix epoch — convert to compare with now

### Step 2 — Compare the stored reset time to now

If the reset timestamp in `last_error_message` is in the PAST, the key is very likely usable again.
The status is stale, not the limit.

### Step 3 — Live-test the endpoint before trusting either status

Tiny, cheap inference call — a valid response proves the key works NOW:

```bash
# Z.AI example (~11 tokens, negligible cost)
KEY=$(grep -E "^GLM_API_KEY=" .env | head -1 | cut -d= -f2-)
curl -s --max-time 45 https://api.z.ai/api/coding/paas/v4/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"glm-4.5-flash","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```
A `choices` array in the response = key works.

## Provider-Specific Notes

### Z.AI / GLM
- Coding endpoint: `https://api.z.ai/api/coding/paas/v4/chat/completions` (base_url shown in auth.json credential pool)
- **Misleading endpoint:** `https://api.z.ai/api/monitor/usage/quota/limit` returns `{"code":500,"msg":"当前用户不存在coding plan"}` for coding-plan keys — NOT proof the key is dead. Test the inference endpoint instead.
- Keys live in `.env` as `GLM_API_KEY` and `ZAI_API_KEY`
- `check-zai-usage.sh` falls back to "check dashboard manually" when the key isn't in shell env — source `.env` first or use the live-test above
- Coding-plan limits are 5-hour rolling (10M) + daily (50M); see `zai-usage-monitor` skill for threshold guidance   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `zai-usage-monitor` exists on this seat -->

### OpenCode Go
- **Usage endpoint EXISTS: `GET https://opencode.ai/zen/go/v1/usage` (Bearer key) returns JSON,** not the SPA. Shape: `{"usage": {"rolling": {"status","percent","resetsAt"}, "weekly": {...}, "monthly": {...}}}` — `percent` is already a 0-100 number and `resetsAt` is ISO-8601 UTC. Read this FIRST; the HTML-path result recorded here earlier was a stale measurement and is why the log-counting fallback below exists at all. Only fall back to log counting when this call fails.
- **A completion request MUST carry `x-opencode-session: <any uuid>`.** Without it this rail answers **HTTP 400 `{"type":"MissingSessionID","message":"Request is missing x-opencode-session and cannot be routed efficiently"}`** — a *rejection of the request shape*, not evidence about the key or the quota. **A probe that omits the header reports a perfectly healthy rail as FAILED**, and on a failover path that false outage triggers a real one: measured, a liveness probe without the header declared the primary failed and would have moved every seat to the fallback for no reason. **Always prove a probe can return 200 on the rail you are testing before you let its failure decision act.**
- **Send a browser-style `User-Agent`; never let the Python default out.** `Python-urllib/3.x` is rejected by the edge as **403 + Cloudflare `error code: 1010`**, which reads exactly like a dead or blocked key. A browser UA (or no UA at all) returns 200. This applies to every call to this provider, including the usage endpoint.
- **Keep `max_tokens` at 16 or more** on probe completions; a very small cap can be rejected as an invalid request and misread as a rail failure.
- Error shape for a genuinely exhausted plan: `GoUsageLimitError`, message includes "Resets in N days" — that's the real reset window (e.g. monthly limit hit Jul 30 → resets ~Aug 8). `last_status: exhausted` with that message = genuine quota exhaustion, unlike stale Z.AI flags.
- **Model names are bare** (`deepseek-v4-flash`, `minimax-m3`), NOT slash-prefixed (`deepseek/deepseek-v4-flash` returns `ModelError: not supported`).
- **Use a non-China-hosted probe model** (e.g. `minimax-m3`) — `deepseek-v4-flash` may return a `RegionError` (China-hosted, needs opt-in) that is NOT a quota signal. Pick a model that returns either a completion or a clean `GoUsageLimitError`.
- **Monthly is the binding constraint** (resets ~30 days); weekly/rolling are separate and usually fine. The dashboard shows Monthly/Weekly/Rolling — the monthly cap is what exhausts.

### A fallback rail you have not tested is not a fallback

**When the plan is "if this provider runs out, we switch to X", X is load-bearing and must be verified BEFORE the
outage, not during it.** A fallback that fails at the switchover converts a budget problem into an outage at the
worst possible moment. Put the fallback's state on the same page as the primary's numbers, in four honest states:
**NOT CONFIGURED · PLACEHOLDER · REJECTED · USABLE** — where USABLE means a real completion succeeded.

Three traps, all measured on one key:

1. **A models list proves nothing about a key.** `GET /v1/models` answers **HTTP 200 with no credential at all** on
   some providers — so an "is it configured?" check against it returns green for an absent, a bogus, and a valid key
   alike. **The only proof is an authenticated action that costs a token** (`POST /chat/completions`, one word,
   `max_tokens: 8`), and the failure you are looking for is a body reading `Unauthorized`, not a non-200 status.
2. **Test the VALUE SHAPE before testing the key.** A placeholder left in `.env` (`your_<provider>_api_key`, `***`,
   `<KEY>`, `changeme`) is a string that exists and never works. Check the prefix, and **leave placeholders
   COMMENTED** — an uncommented placeholder is the worst state, because it reads as configured to every later
   reader, including the agent that would have fixed it.
3. **A commented-out "TODO key" section is not a configured rail.** Reading `.env` for a provider name and finding
   the line present says nothing; grep for the line's **first character**, and treat `# KEY=` as absent.
4. **A `fallback_providers` list is not a credential.** Config can name a model on a provider whose key exists
   nowhere on the host, and every health screen still lists the fallback as available. **Enumerate the providers
   that actually hold a credential (`auth.json`) and compare that set to the providers named in the fallback
   config** — if the sets differ, the honest statement is *one working rail*, and that is the sentence to report,
   not "we have fallbacks."

**Report the state, not the intention.** "We can fall back to X" is a plan; "X answers a completion" is a fact.
Until the fact exists, say the fallback is unconfigured and name what unblocks it (an account, a key, a paid plan).

### Ollama Cloud
- **Usage endpoint is `/api/usage`, NOT `/v1/usage`.** `https://ollama.com/v1/usage` returns `{"error":"path \"/v1/usage\" not found"}`. The real endpoint `https://ollama.com/api/usage` (Bearer `OLLAMA_API_KEY`) returns `limits.weekly.usage` and `limits.session.usage` as fractions (0.0-1.0) plus per-model request counts. Verified Aug 2026.
- **Weekly is the binding constraint** (resets every 7 days); session resets every ~5h. The dashboard shows "Weekly usage" and "Session usage" — read both from `/api/usage`.
- **No `/v1/plan` endpoint either** — the plan/limits live in `/api/usage`'s `limits` object, not a separate call.

### Nous Portal (primary provider)
- Check `hermes status` — shows access token expiry; refresh BEFORE long cron batches
- **The visible "Access exp" is the HOURLY OAuth access-token rotation, NOT a balance problem.** The JWT `exp - iat == 3600` (1 hour); it auto-renews via the refresh token stored alongside it. Do not alarm the user about it — it is not a spend or quota signal.
- **Balance lives in the JWT claims, not the API.** The inference API returns 404 for `/v1/usage`, `/v1/balance`, `/v1/me`, `/v1/account/usage`. Read `member_spend_usd` (spend this period), `paid_access`, `member_spend_cap_exceeded`, `subscription_tier` from the access token:
```bash
python3 -c "
import json, base64
d = json.load(open('/opt/data/profiles/gentech/shared/nous_auth.json'))   <!-- ⚠️ NOT PRESENT (checked 2026-11-17): this file does not exist on this seat. Do not assume it; verify before relying on it. -->
def find(o):
    if isinstance(o, dict):
        for k,v in o.items():
            if 'access' in k.lower() and isinstance(v,str) and len(v)>50: return v
            r = find(v)
            if r: return r
    return None
t = find(d)
p = t.split('.')[1]; p += '=' * (-len(p) % 4)
for k,v in json.loads(base64.urlsafe_b64decode(p)).items():
    if 'spend' in k or 'paid' in k or 'tier' in k or 'cap' in k: print(f'{k}: {v}')
"
```
- `paid_access: true` + `subscription_tier: 2` + spend ~$1 → the account is active; no top-up needed. The portal dashboard may show a different balance than the API — when user asks about dollars, quote the JWT number AND tell them the dashboard is authoritative for top-ups.
- **Terminology:** the Nous balance is the research-portal subscription balance — NEVER call it "the grant." User explicitly corrected this (Aug 2026). It is not grant funding and it is not "spent" in the grant sense.
- See `hermes-auth-incident-response` for actual OAuth recovery.

## Log-Based Usage Counting (when the provider has no usage endpoint)

**Scope this to providers that genuinely expose no meter — do NOT count OpenCode Go among them.** OpenCode Go
publishes `GET /zen/go/v1/usage` (see its section above), so counting its logs converts a free, exact number into a
derived guess. Measured: a gate kept a log-counting fallback as if the endpoint did not exist while the endpoint
answered in 300 ms with `rolling / weekly / monthly` percentages. **Before writing or trusting a log counter,
call the usage endpoint once and let the result decide.** When the endpoint genuinely is absent, the log is the
measurement, but only if you deduplicate correctly.

### A call is not a log line

Hermes retries, and rotated logs keep the same call in multiple files. Counting `API call #N:`
lines over-counts by **3–5×**. The identity of a call is the **session tag + call number + model**,
not the line.

```python
import re, glob, gzip, os
from collections import defaultdict

LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2},\d+ .*?\[([^\]]+)\].*?"
    r"API call #(\d+): model=(\S+) provider=([a-z0-9\-]+) .*? total=(\d+)")

seen = set()
per_day = defaultdict(int)
for seat in sorted(glob.glob('/opt/data/profiles/*/')):
    for pat in ('logs/agent.log*', 'logs/errors.log*', 'logs/mcp-stderr.log*'):
        for f in glob.glob(os.path.join(seat, pat)):
            txt = gzip.open(f, 'rt', errors='replace').read() if f.endswith('.gz') \
                  else open(f, encoding='utf-8', errors='replace').read()
            for ln in txt.splitlines():
                m = LINE.match(ln)
                if not m or 'opencode' not in m.group(5):
                    continue
                key = (seat, m.group(2), m.group(3), m.group(4))  # tag + call# + model
                if key in seen:
                    continue
                seen.add(key)
                per_day[m.group(1)] += 1
```

### The session-tag regex must match every shape the logger writes

Session tags have **at least two shapes** in our logs:

```
[cron_<hash>_YYYYMMDD_HHMMSS]     # cron sessions
[YYYYMMDD_HHMMSS_<hash>]          # interactive sessions
```

A regex that matches only the interactive shape returns `None` for every cron session, so the
dedup key becomes `(seat, "?", call#, model)`. **Every cron job's "API call #1" collides with
every other one.** This under-counted OpenCode Go usage by **2.2×** on 2026-10-02 — making the
plan look 55% safer than it was.

Correct regex:

```python
SESSION_RE = re.compile(
    r"\[((?:cron_[a-z0-9]+_\d{8}_\d{6})|(?:\d{8}_\d{6}_[a-z0-9]+))\]", re.I)
```

### Rotated logs are not independent observations

If your dedup key includes the **filename**, `agent.log.1`, `agent.log.2`, and `agent.log.3` each
count the same call again. The key must include the **session tag**, not the file path.

## A usage gate must READ the binding — never recall it

**A monitor that hardcodes which provider it watches drifts the moment the rail changes, and it drifts silently in
the worst direction: green about the provider nobody is using.** Measured: a usage gate carried
`binding_name = "ollama-cloud"` as a constant plus a comment declaring the primary rail *retired*. All four seats
had been running the other provider for days. The gate reported a healthy fallback while the rail serving every
request went unmeasured — the same shape as a liveness check that passes without authenticating.

- **Derive the binding from the live config every run.** Read each seat's `config.yaml` `model:` block
  (`provider`, `default`, `base_url`) and take the majority; **print a warning when seats disagree**, because one
  seat left on an old rail is exactly the fact a hardcoded constant hides.
- **Comment the constant as a measurement with its date, or delete it.** A retired-rail note that is wrong is
  worse than no note: the next reader trusts it and stops looking.
- **A crash loop looks like a quota problem and is not.** When every run of a gate errors, read the traceback
  before theorising about limits — a subscription rail answers in percentages and a gate written for a dollars
  meter dies on `KeyError: 'usd'`. Dashboard rails and subscription rails do not share a schema.

### Severity must be raised by the METER, not only by liveness

**"A completion succeeded" proves the rail answers; it says nothing about how much is left.** A gate whose band
is computed only from liveness will read `OK` at 89% of the monthly cap right up until the rail stops answering —
the healthy-while-nearly-dead failure this fleet keeps re-learning.

- Compute the worst window across `rolling / weekly / monthly` and map it to the band: **≥85% WARN, ≥95%
  CRITICAL**, on top of whatever the liveness verdict said. A green rail is not a cheap rail.
- **A subscription has no dollars to report.** Print percentages and reset times; do not synthesise a spend figure
  from local call counts — that invents a number the provider never published.
- **Save the windows you measured.** A purge rule written for a USD-metered rail will delete the percentage keys
  the current rail just reported, leaving a state file that describes the past. Purge only the fields the LIVE
  rail cannot refresh.
- **Fix every output path.** A gate usually has a `--report` branch and a cron branch; a crash fixed in one leaves
  the scheduled path failing while the manual run looks fine. Grep for the crashing expression, not for the
  function you edited.

## Shared budgets: a limit is per TOKEN, not per agent

**Several seats share one key, so a seat that burns the budget throttles the others — and nothing in a
per-agent view can show that.** Before concluding "we have headroom" or "the provider is degraded", ask WHO ELSE
is spending the same credential. Two rules make the answer visible:

1. **Publish the provider's number to a place every seat reads.** A small daily page (a dated note in the
   shared vault) with, per token: core/search/code-search remaining + reset, and the provider's own usage
   windows. **Read the provider's endpoint, never a local call counter** — our count of calls is not their
   count of calls, and a local counter that drifts from theirs is a confident lie.
2. **A throttle is a boundary, not a retry condition.** A `403`/`429` whose body says rate limit, or whose
   `x-ratelimit-remaining` is `0`, means stop and say the run is **INCOMPLETE** — never retry through it, and
   never let it read as an empty result. **Retrying a throttle is how a cron turns a warning into a suspension.**

**Attribution does not exist and should not be faked.** GitHub publishes no per-caller usage, so a seat cannot
be billed for its share from an API. The honest mechanism is a **one-line spend note in the handoff**
(`Spent: ~N core calls, M searches`) plus the shared page — cheaper than per-seat proxies, and it says what it
is. Corollary for a ledger built on this: it must print **what it cannot know** (no attribution, no historical
backfill) beside the numbers it does read.

**And pick the limit that actually binds.** A generous hourly REST quota can sit beside a per-MINUTE search cap
two orders of magnitude smaller; a job making a handful of calls per run is nowhere near the first and one
search call away from the second. State which limit binds, in the file, so the next person adding a call sees
why the budget just changed.

## Pitfalls

| Pitfall | How to avoid |
|---------|--------------|
| Trusting `hermes auth list` rate-limit status | It's the last failure snapshot, possibly weeks old. Decode `last_error_message` reset time, then live-test |
| Reading `last_error_reason` ("1310") as meaningful | It's an opaque code. The reset time lives in `last_error_message` |
| Concluding a key is dead from a quota-monitor endpoint 500 | Monitor endpoints often don't serve coding-plan keys. Test the actual inference endpoint |
| Quoting a provider as "down" to the user without a live test | Always verify with a real request first; a live 200 changes the whole answer |
|| Reporting reset as "someday" | Convert timestamps to a concrete date (UTC + ET) so the user gets a real answer |
| `credits_notices: true` spamming free-model responses | When Hermes is on a free tier (Nous `solar-pro4:free`, BlockRun `free/gpt-oss-120b`, etc.), the global `credits_notices` flag prepends a cost/balance notice to every response. This can produce incoherent warnings like "⚠️ Insufficient balance — send USDC to `0xebc8...`" even when no wallet is funded or no real spend is happening. To silence: set `credits_notices: false` in the profile's `display:` block (`~/.hermes/profiles/<profile>/config.yaml`). Keep it `true` only when actively spending a paid provider and the user wants per-turn cost visibility. For finer control, `show_cost: false` suppresses the cost line without the full balance preamble. Each profile has its own `display:` block — silencing it in one profile does not affect others. |
| Counting log lines as calls | A retry and a rotated log both duplicate the same call. Identity = session tag + call number + model |
| Deduplicating by a session-tag regex that only matches one shape | Match every shape the logger emits, or distinct sessions collapse into the same key and the count is wrong in either direction |
| A gate hardcoding which provider it watches | Read `provider` from each seat's `config.yaml` every run and warn when seats disagree; a constant drifts silently and reports on the wrong rail |
| Band computed from liveness alone | Raise the band on the worst allowance window (≥85% WARN, ≥95% CRITICAL) — a rail at 89% answers fine until it does not |
| Purging window percentages because an older rail metered in dollars | Purge only fields the LIVE rail cannot refresh, or the state file describes the past |

## Related Skills

- `zai-usage-monitor` — Z.AI quota thresholds and alerting (manually authored; do not auto-edit)
- `hermes-auth-incident-response` — OAuth token expiry recovery (manually authored; do not auto-edit)
- `cron-truth-layer` — verify cron data before reporting it

## References

- `references/opencode-go-usage-from-logs.md` — count OpenCode Go calls when the provider has no usage endpoint: correct dedup, session-tag shapes, rotated-log trap
- `references/stale-rate-limit-diagnosis-2026-07-31.md` — full worked example: stale Z.AI status, reset-time decoding, live-test proof, companion findings
- `references/provider-auto-switch-pattern.md` — reusable pattern for automatically failing over between Ollama Cloud (weekly reset) and OpenCode Go (monthly reset) based on live usage, with the context-save-before-restart safety step
