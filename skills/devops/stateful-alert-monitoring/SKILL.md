---
name: stateful-alert-monitoring
description: "Stateful cron-based monitoring with debounced confirmation and tiered alerts — prevents alert spam while ensuring critical conditions are caught. Covers state persistence, multi-threshold logic (immediate/watch/confirmed), and integration patterns for any periodic health/event checker."
tags: ["devops", "monitoring", "alerts", "cron", "state-machine", "debounce"]
trigger: "When building or enhancing periodic monitoring scripts that need false-positive filtering via delayed confirmation, or when different condition severities require different alert urgency levels. Applies to price breakouts, efficiency thresholds, health checks, or any recurring poller where immediate reaction causes noise."
related_skills:
  - defi-lp-monitoring  # for LP-specific logic (efficiency, fees, ranges)
  - agent-coordination  # for vault logging and handoff protocols
  - system-health       # for cron health and failure alerts
version: 1.1.0
author: Gentech
---

# Stateful Alert Monitoring (Umbrella)

Reusable pattern for cron-based detectors that need **confidence confirmation** before escalating, plus **tiered urgency** based on condition severity. Prevents noise from transient spikes while ensuring real breakouts get noticed.

> **Why this exists:** Simple threshold alerts fire on every tick — painful when price ping-pongs across a boundary. This skill adds a state layer: first detection → wait N minutes → confirm → alert. Different severities get different treatment (immediate vs debounced).

## Quick Decision Table

| User Intent | Go To Section |
|-------------|---------------|
| "Alert only if condition persists for 5min" | [Debounce Pattern](#1-core-debounce-pattern) |
| "Different alert levels for mild vs severe" | [Tiered Alert Matrix](#2-tiered-alert-matrix) |
| "Persist state across cron runs" | [State File Schema](#3-state-file-schema) |
| "Integrate with existing script" | [Implementation Checklist](#4-implementation-checklist) |
| Avoid duplicate alerts | [Deduplication Rules](#5-deduplication-rules) |
| Health log grows 80+ lines/day of identical entries | [Delta-Based Health Logging](#12-delta-based-health-logging-log-deduplication) |

---

## 1. Core Debounce Pattern

### When to Use

- **Transient noise** expected (price wicks, brief API hiccups, temporary IL spikes)
- **Cost of false positive** > cost of delayed detection (rebasing penalties, notification fatigue)
- Condition is **discrete** (in/out of range) OR **continuous but thresholded** (efficiency below X%)
- Cron interval is shorter than desired confirmation window (e.g., script runs every 15min, want 5min confirmation)

### When NOT to Use

- **Continuous decay** metrics (efficiency trending down) — use immediate alerts with rate-limiting instead
- **High-frequency trading** contexts where 5min is too slow
- **One-shot events** (contract deployed, milestone hit) — fire once, mark done
- **Safety-critical** systems needing instant reaction (use both immediate + confirmed pathways)

### State Machine

```
          ┌─────────────┐
          │ First       │
          │ Detection   │
          └──────┬──────┘
                 │ set pending=true, timestamp=now
                 ▼
          ┌─────────────┐
          │ Pending     │◄────┐
          │ (waiting)   │     │ condition still true
          └──────┬──────┘     │ after delay?
                 │ elapsed ≥ DELAY_MIN?
                 ▼             │
          ┌─────────────┐     │
          │ Re-check    │─────┘
          │ Condition   │
          └──────┬──────┘
                 │ condition true?
         ┌───────┴───────┐
         │               │
    YES  ▼               ▼  NO
         │               │
    ┌─────────────┐ ┌─────────────┐
    │ Confirmed   │ │ Cancelled   │
    │ → ALERT     │ │ → clear     │
    └─────────────┘ └─────────────┘
         │
    stay confirmed until
    condition clears → reset
```

**Key fields:**
- `pending: boolean` — waiting for confirmation?
- `first_seen: ISO timestamp` — when condition first appeared
- `confirmed: boolean` — has condition survived delay?
- `last_alert_sent: ISO timestamp` — deduplication guard

### Timing Rules

| Metric | Recommendation |
|--------|----------------|
| `CONFIRMATION_DELAY_MIN` | 5 (balance: noise filter vs responsiveness) |
| `MAX_ALERT_INTERVAL_MIN` | 60 (rate-limit repeat alerts on persistent condition) |
| Cron frequency | Should divide evenly into delay (e.g., 15min cron → 5min delay fits) |

---

## 2. Tiered Alert Matrix

Not all conditions deserve the same urgency. Split into **three tiers**:

| Tier | Condition Type | Response | Example |
|------|---------------|----------|---------|
| **IMMEDIATE** | Continuous decay crossing threshold OR safety-critical | Alert now, no wait | Efficiency ≤30%, gas below minimum, contract paused |
| **WATCH** | Discrete boundary crossing with noise potential | Debounce (5min), then alert | Price out of range, efficiency drops below 50% |
| **INFO** | Routine state changes | Log only, no Telegram | Daily snapshot, within-range update |

**Implementation:** Two parallel checks in `should_alert()`:
```python
def should_alert(state, metrics):
    # Tier 1: Immediate (bypass debounce)
    if metrics['efficiency'] <= IMMEDIATE_THRESHOLD:
        return True, "IMMEDIATE"

    # Tier 2: Watch (go through debounce)
    if metrics['out_of_range']:
        return check_debounce(state), "WATCH"

    return False, None
```

---

## 3. State File Schema

Store in JSON at fixed path (e.g., `~/.hermes/scripts/.<script>-state.json`):

```json
{
  "last_run": "2026-05-02T14:10:00-04:00",
  "pending_breakout": {
    "condition": "out_of_range" | "efficiency_low",
    "first_seen": "2026-05-02T14:05:00-04:00",
    "price": 9.02,
    "efficiency": 28.5,
    "confirmed": false
  },
  "last_alert_sent": "2026-05-02T13:55:00-04:00",
  "counters": {
    "total_runs": 142,
    "alerts_sent": 7,
    "false_positives_cancelled": 3
  }
}
```

**Atomic writes:** Write to temp file then `os.replace()` to avoid corruption on interruption.

**Migration:** On script start, call `migrate_state(old_schema)` if version key missing.

---

## 4. Implementation Checklist

### Phase 1 — State Infrastructure
- [ ] Choose state file path (absolute, in `~/.hermes/scripts/` or script dir)
- [ ] Define `load_state()` / `save_state()` helpers with atomic write
- [ ] Add `last_run` timestamp on every execution
- [ ] Initialize `pending_*` keys as empty dicts on first run

### Phase 2 — Debounce Logic
- [ ] In main condition check, detect **first crossing** (condition true AND `pending` not set)
- [ ] Set `pending = {condition, first_seen=now, confirmed=false}`
- [ ] On subsequent runs: if `pending.confirmed == false` AND `now - first_seen ≥ DELAY`:
  - Re-evaluate condition
  - If **still true**: `confirmed = true`, send confirmed alert
  - If **false**: `pending = {}` (false positive resolved)
- [ ] Once `confirmed == true`, keep sending alerts on every run until condition clears
- [ ] On condition clear: `pending = {}`, `confirmed = false`

### Phase 3 — Tiered Alert Routing
- [ ] Define threshold constants at top of script:
  ```python
  IMMEDIATE_THRESHOLD = 30  # efficiency
  WATCH_THRESHOLD = 50
  CONFIRMATION_DELAY_MIN = 5
  ```
- [ ] Build `format_alert(metrics, tier)` → returns two Telegrams:
  - Mini-warning (pending): `"⚠️ Monitoring: condition detected — confirming..."`
  - Confirmed: `"🚨 ACTION REQUIRED: ... — Rebalance suggested"`
- [ ] Route mini-warning to same channel or separate "monitor" channel if spam critical

### Phase 4 — Deduplication
- [ ] Store `last_alert_sent` timestamp
- [ ] Before sending ANY alert, check `now - last_alert_sent < MIN_ALERT_INTERVAL_MIN`
- [ ] If too soon, skip (but keep pending state ticking)
- [ ] After sending, update `last_alert_sent = now`

### Phase 5 — Vault Logging (Optional but Recommended)
- [ ] Create daily log file in appropriate vault folder (e.g., `03-Strategies/Defi-Monitor/YYYY-MM-DD-update.md`)
- [ ] Write first entry of day even if silent (date marker)
- [ ] On every confirmed alert, append detailed entry (price, metrics, action)
- [ ] Use template from `defi-lp-monitoring` skill if applicable

---

## 5. Deduplication Rules

**Problem:** Script runs every 15min; condition persists across 4+ runs → spam.

**Solution:** Three guards:

1. **Pending escalation throttle** — once `pending.confirmed == true`, send **one** confirmed alert per condition lifetime (until reset)
2. **Global rate limit** — `MIN_ALERT_INTERVAL_MIN = 60` prevents rapid successive alerts even if multiple conditions trigger
3. **Same-day suppression** — If today's alert already sent for same condition type, add "update" footer instead of new header

**Alert journal** in state:
```json
{
  "alert_history": [
    {"condition": "out_of_range", "sent_at": "2026-05-02T14:15:00-04:00", "tier": "CONFIRMED"}
  ]
}
```
Prune entries >24h old to keep file small.

---

## 6. Testing Protocol

**Unit tests** (script-level):
```python
def test_pending_escalation():
    state = {}
    metrics = {'out_of_range': True, ...}
    # Run 1: set pending
    alert, tier = should_alert(state, metrics)
    assert tier == "PENDING"
    # Fast-forward time 5min
    state['pending']['first_seen'] = now - 6min
    alert, tier = should_alert(state, metrics)
    assert tier == "CONFIRMED"
```

**Integration tests** (real data):
1. **False positive simulation** — price crosses boundary at t0, crosses back at t+3min → expect no confirmed alert
2. **True breakout** — out-of-range at t0, still out at t+6min → expect one confirmed alert
3. **Efficiency immediate** — eff=28% → alert immediately, no pending
4. **Recovery** — condition clears → pending resets; re-trigger starts new cycle

**Smoke test** on devnet/prod:
- Force condition via mock (patch `fetch_*` functions)
- Verify Telegram delivers exactly one message per escalation
- Verify state file updates correctly
- Verify vault entry created

---

## 7. Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **Exit code 1 for alerts** | Cron logs "error" status even when script works correctly | Always exit 0 — alerts are in stdout, not exit codes. See defi-lp-monitoring §Cron Script Exit Code. |
| State file not writable | Silent failures, no persistence | Check `os.access(state_path, os.W_OK)` on startup |
| Timezone drift | first_seen in UTC but cron in local → delay mis-calculated | Use UTC everywhere, convert only for display |
| Cron overlap | Two instances run concurrently, race condition on state file | Use file lock (`fcntl` or lockfile) or ensure cron spacing > script runtime |
| Midnight rollover | Pending state from previous day never clears | Reset `pending_*` on date change (compare `last_run.date()` vs `now.date()`) |
| Memory leak | State file grows unbounded | Prune `alert_history` to last 24h on each run |
| False negative on rebound | Condition true at t0, false at t+5min, true again at t+10min → missed alert | On condition clear, reset pending; on re-trigger, start new cycle (correct behavior) |
| Timezone mismatch in Telegram messages | Timestamps wrong | Use `now_eastern()` helper only for display; store UTC in state |
| **Preflight runs before debounce gate** | User sees orphaned preflight messages with no report | Move preflight/print calls to AFTER debounce decides to send. Preflight MUST NOT run before `should_send_report()` check. Found in `defi-lp-consolidated.py` (Jun 22, 2026). |
| **[SILENT] marker leaks in no_agent scripts** | User sees "[SILENT]" text instead of actual silence | Use empty stdout (`return` or `sys.exit(0)`) — never print a silence marker. With `no_agent: true`, stdout goes directly to the user. |

---

## 8. Integration Guide

**Step 1 — Load this skill** at the top of your monitoring script:
```python
# skill: stateful-alert-monitoring
CONFIRMATION_DELAY_MIN = 5
IMMEDIATE_THRESHOLD = 30
# ... rest of config
```

**Step 2 — Add state helpers** (copy from `references/state-helpers-template.py`):
```python
def load_state(path):
    ...
def save_state(path, state):
    ...
```

**Step 3 — Wrap condition checks:**
```python
def check_conditions(metrics):
    alerts = []
    if metrics['eff'] <= IMMEDIATE_THRESHOLD:
        alerts.append(('IMMEDIATE', 'efficiency critical'))
    if metrics['out_of_range']:
        tier = 'WATCH'
        # debounce handled in should_alert()
        alerts.append((tier, 'price out of range'))
    return alerts
```

**Step 4 — Replace `print()` with `send_telegram(message, tier)`** that respects rate limits.

**Step 5 — Add vault logging** (optional): call `log_to_vault(metrics, tier)` using templates from `defi-lp-monitoring`.

---

## 9. Extensions & Variations

### 9a. Suppress-Until-Resolution Pattern (Alert Once Per Condition)

**When to use:** Jordan's preferred pattern (May 7, 2026) — after alerting on a condition, stay **completely silent** until the condition **resolves**, then re-arm for next occurrence.

**Key difference from standard debounce:**
- Standard debounce: alert → rate-limit → alert again after interval
- Suppress-until-resolution: alert → **silence** → re-arm only when condition clears

**Use cases:**
- LP position out of range → alert once → stay silent until price returns to range
- Efficiency below threshold → alert once → stay silent until efficiency recovers above threshold
- Any condition where repeated alerts add noise without new information

**Implementation pattern:**
```python
# Track per-condition alert state
oor_alerted = state.get("oor_alerted", False)
eff_alerted = state.get("eff_alerted", False)

# Check if condition resolved → reset alert flag
if oor_alerted and not out_of_range:
    state["oor_alerted"] = False  # re-arm for next occurrence

if eff_alerted and efficiency >= EFFICIENCY_CRITICAL_PCT:
    state["eff_alerted"] = False  # re-arm for next occurrence

# Only alert if not already alerted for this condition instance
if out_of_range and not oor_alerted:
    # ... send alert ...
    state["oor_alerted"] = True
```

**State fields:**
```json
{
  "oor_alerted": false,
  "oor_alert_time": null,
  "eff_alerted": false,
  "eff_alert_time": null
}
```

**Why this works:** Each condition instance gets exactly one alert. The flag resets only when the condition resolves, creating a clean cycle: detect → alert → suppress → resolve → re-arm.

**Jordan's rule:** "There can be one notification... but after that, everything else could be silent until there's an action done."

### 9b. Other Variations

- **Adaptive delay:** If false positive rate high, auto-increase `CONFIRMATION_DELAY_MIN` (max 15min)
- **Multi-condition AND:** Only confirm if BOTH efficiency low AND out-of-range (reduces false positives further)
- **Escalation ladder:** Pending → Confirmed → Critical (if persists >2h) → page Jordan
- **Histogram bins:** For continuous metrics, bucket into bins and confirm bin movement (e.g., efficiency dropped from 55% → 42% → 28%, confirm each step)
- **Cross-validation:** require second data source agreement before confirming (DexScreener + on-chain reader)

---

## 10. Smart Trigger Pattern (Cost-Optimized Agent Firing)

**When to use:** You want agent analysis (news, reasoning, web search) but only when something significant happens. The script does the cheap threshold check; the agent only fires when there's work to do.

### How It Works
```
Script runs every 2h (no_agent=true, free)
  ├─ No big moves → empty stdout → SILENT (no tokens burned)
  └─ Big moves detected → stdout with details → agent fires, searches news, delivers report
```

### Implementation
1. **Trigger script** (`no_agent=true`): Checks price/state against threshold. Outputs token details only when threshold exceeded. Empty stdout = silent.
2. **Agent job** (`no_agent=false`): Same schedule. Runs the trigger script. If script output is empty, agent stays silent. If script outputs data, agent analyzes (web search, context, reasoning) and delivers.

### Key Design Rules
- Trigger script must produce **empty stdout** (not "[SILENT]" or "nothing to report") for no_agent jobs to stay quiet
- Agent prompt must include: "If the script output is empty, respond with nothing — stay completely silent"
- Keep the trigger script lightweight — it runs every tick, even if agent doesn't fire
- Agent prompt should tell the agent exactly what to do with the data (search news, format report, etc.)

### Example: Watchlist News Alert
Jordan wanted token-specific news (exploits, partnerships, regulatory) on his CMC watchlist, but not every 2 hours — only when tokens move >5%.

**Trigger script** (`cmc-news-trigger.py`): Reads watchlist state, checks 24h/7d changes and since-last-check movement against 5% threshold. If any token exceeds threshold, outputs token details + "ACTION REQUIRED: Search for news on each big mover." If no big movers, empty stdout.

**Agent prompt**: "If the script output is empty, respond with nothing. If big movers detected, search for news on each token — look for exploits, hacks, regulatory news, partnerships. Summarize in 1-2 sentences per token."

**Result**: Price monitor runs every 2h (free). Agent only fires when AVAX drops 16% in a week or ONDO pumps 35%. Token burn = near-zero on quiet days.

### Cron Job Configuration
```json
{
  "no_agent": false,
  "script": "cmc-news-trigger.py",
  "enabled_toolsets": ["web"],
  "schedule": "every 2h",
  "prompt": "If the script output is empty, stay silent. If big movers detected, search news..."
}
```

---

## 12. Delta-Based Health Logging (Log Deduplication)

**When to use:** An append-only health/status log that grows 80+ lines/day of identical entries. Each cron cycle writes the same probe results — the log becomes noise, not signal. Real status changes (a token expiring, a service going down) are buried in a sea of identical healthy entries.

**Key difference from alert deduplication (§5):** Alert deduplication prevents repeated Telegram messages. Log deduplication prevents repeated file entries. They solve the same root problem (noise from identical repeated data) at different output layers.

### When to Apply

- **Append-only health logs** — credential-health.log, service-status.log, any probe log that runs on a fixed schedule
- **Status is discrete** — each probe has a finite set of states (200/401/SKIP/PAY_OK/NO_ACCOUNT)
- **Log is read by humans** — the user scans the log to find when something changed
- **Cron interval is shorter than expected change frequency** — e.g., script runs every 4h but credentials change monthly

### When NOT to Use

- **Continuous metrics** — price, temperature, latency (every value is new; delta would suppress nothing)
- **Audit trails** — every run must be recorded for compliance (use a separate audit log)
- **Debugging transient issues** — you want every run captured to correlate with external events
- **Logs consumed by machines** — if a downstream parser expects every run's entry, delta mode breaks it

### Implementation Pattern (Shell)

The core logic is a single guard before the append:

```bash
_log_status() {
    local provider="$1"
    local status="$2"
    local detail="$3"
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    # Delta mode: skip if the last entry for this provider has the same status.
    # Keeps the log as a clean change-history instead of growing 80+ lines/day.
    local last_status
    last_status=$(grep "| ${provider}=" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oP "${provider}=\K\S+")
    if [[ "$last_status" == "$status" ]]; then
        return 0
    fi

    echo "[${timestamp}] | ${provider}=${status} | detail=${detail}" >> "$LOG_FILE"
}
```

### Implementation Pattern (Python)

```python
import re

LOG_FILE = "/path/to/health.log"

def log_status(provider, status, detail):
    """Append a log entry only if the status changed from the last entry."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Delta mode: check last entry for this provider
    try:
        with open(LOG_FILE) as f:
            for line in reversed(f.readlines()):
                if f"| {provider}=" in line:
                    m = re.search(rf"{re.escape(provider)}=(\S+)", line)
                    if m and m.group(1) == status:
                        return  # status unchanged — skip
                    break
    except FileNotFoundError:
        pass

    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] | {provider}={status} | detail={detail}\n")
```

### Verification

```bash
# First run: writes a new entry
bash health-check.sh
tail -1 health.log | grep -q '^\[2026-07-28' && echo "FIRST RUN OK"

# Second run with no status changes: zero new lines
LINES_BEFORE=$(wc -l < health.log)
bash health-check.sh
LINES_AFTER=$(wc -l < health.log)
[ "$LINES_AFTER" -eq "$LINES_BEFORE" ] && echo "DELTA MODE OK"
```

### Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **First run on empty log** | grep returns empty string, `last_status` is empty, status comparison `"" == "200"` is false → entry written (correct) | No fix needed — first entry always writes |
| **Log file doesn't exist yet** | `grep` returns non-zero exit, `last_status` is empty | Guard with `2>/dev/null` and empty-string comparison |
| **Provider name contains regex special chars** | grep -oP pattern fails | Escape provider name: `${provider//[^a-zA-Z0-9_-]/}` or use fixed-string grep |
| **Log format changes** | grep pattern no longer matches last entry | Keep a stable format; if format must change, bump a version field and reset delta state |
| **Multiple providers with same prefix** | grep matches wrong provider (e.g., `blockrun` matches `blockrun_extra`) | Anchor the grep: `"| ${provider}="` with the pipe-space prefix |
| **Large log file (>10K lines)** | grep + tail on every call is slow | Add a state file tracking last-known status per provider (see §3 State File Schema) |
| **Midnight rollover** | Date in timestamp changes but status is same → entry still suppressed (correct) | No fix needed — delta is status-based, not time-based |
| **Log rotation** | After rotation, log is empty → first entry writes (correct) | No fix needed — delta resets on rotation |

### Integration Checklist

- [ ] Identify the append-only log file and its format
- [ ] Add the delta guard before every append call
- [ ] Test: first run writes, second run with same status skips
- [ ] Test: status change writes a new entry
- [ ] Verify the log is still human-readable (change-history format)
- [ ] Document the delta behavior in the log file's header comment

### Real-World Example

`credential-health.sh` (evolve-10, Jul 28, 2026):
- Before: 163 lines in 2 days, all showing the same 6 probes with identical statuses
- After: 0 new lines per cycle when nothing changes; 1 new line per probe that actually changes status
- The log went from noise (80+ lines/day) to signal (0-2 lines/day, only on actual changes)

---

## 13. A monitor that stops measuring (dead-canary rules)

A monitor can keep running, keep printing, and stop carrying information. Three shapes, all of which read
as diligence in the transcript and as noise in the chat.

### 13a. Never tell the reader to go measure it themselves

If a probe can decide something, it must decide it **in the run**. Emitting the result plus a shell snippet
("dump the user agents to find out what this bucket is") guarantees the finding repeats verbatim, because the
work was out-sourced to a human who is not in the loop. **Measured: the same bucket printed as an identical
`⚠️ UNVERIFIED: N` line for seven consecutive runs while it was fully resolvable from the data at hand.**

- Do the analysis inline and print the *shape* of the answer: counts by category, the widest offender, a
  sample of names.
- If the analysis truly cannot run from that script (needs a credential, another host), say **who** must run it
  and **what changes when they do** — and track it as an open item with a named owner, not as a recurring
  warning.

### 13b. A number that never changes is a dead canary

Identical output across runs means the probe is asserting yesterday's measurement. Add a cheap **delta line**
(`47 callers, +3 since last run`) computed from the last state file — the change is the signal, the stock is
context. If the delta is genuinely zero for many runs, say "no change" once and let it go quiet; a warning that
fires every run without changing is training the reader to scroll past the channel it shares with real alerts.

### 13c. A standing finding is not a broken job — do not let either impersonate the other

A scheduler treats **non-zero exit as job failure**, so a healthy monitor with a real standing finding looks
identical to a crashed script in the notification text ("failed 5 runs in a row"). Two dishonest resolutions to
avoid:

- **Do not exit 0 to silence it.** A green light over a real defect is the exact failure class this library
exists to prevent.
- **Do not let it burn red forever either.** A red the operator has learned to ignore is already broken.

The honest paths are two: **fix the cause** (preferred — usually a small spend or a one-line config), or
**record an accepted exception** and have the job report *"N accepted exceptions, 0 unplanned findings"* and exit
clean. An exception is honest only when it is written down with an owner and a date; suppressed silence is not an
exception.

### 13d. Name the blocker, not the symptom you happen to test for

A probe that looks for *its favourite kind of evidence* will report absence as failure. Measured: an image
liveness check searched four env-var API keys and reported `IMAGE generation unavailable` for five runs, while
the fleet's actual default media lane authenticated from a **key file** — so the sentence was untrue. It was only
correct once the probe read the lane's real credential **and** its spendable balance, and reported the true
blocker (`0.000000 ETH on base — cannot pay`). **So when a capability check fails, the failure text must name the
exact missing thing and be something the operator can act on in one step**; "no provider key" when the provider
keeps its key elsewhere is a wrong answer wearing a confident sentence.

### 13e. The monitor's SUBJECT and its SOURCE must be the same thing

A probe answers exactly one question, and the three shapes below all report a **confident wrong answer**
because the thing it read was not the thing it claimed to observe. Each looked healthy in the transcript.

- **A "waiting on us" predicate keyed on the LAST SPEAKER is blind to everyone else.** A checker that asks
  "does the newest message in this thread come from us?" answers *nothing is waiting* while a stranger had
  just replied to a thread we opened — the reply was not the newest *thing we had looked at*. Measured: an
  inbox audit printed `WAITING ON US — none` on the same day two outside participants posted substantive
  replies in our own threads. **Scope the predicate to the actor whose move matters** (external activity
  since our last message, mentions, new participants), not to a positional rule that a single later comment
  can invert.
- **A notification feed is not the activity.** The feed is per-recipient and can be empty while the artefact
  moved (a reply on a thread already marked read, an edit, a close, a mention delivered only to a different
  actor). Measured: `0` notifications across several days against threads that had genuinely changed.
  **Query the object** (the thread, the issue, the file, the record) and let notifications, when present, be
  an accelerator rather than the source of truth.
- **An append-only log is a SHADOW of the actor, and shadows go stale after a restart.** A "which one is live
  now?" probe that counts occurrences in a log tail resolves to the **long-lived old** entity even after a
  restart created a new one, because the log keeps every historical mention. Measured: a freshness monitor
  reported a seat frozen for weeks while that seat's own database held a session created minutes earlier —
  the probe was reading the shadow, which still carried thousands of references to the dead entity. **Read
  the system of record** (the table carrying the entity's own start time, the API's own object) ordered by
  that timestamp; treat a derived log as corroboration only. And print the identifier you resolved
  (`sid=…`, `thread=…`, `row=…`) beside the verdict, so a wrong pick is visible instead of plausible.

**The general rule:** before shipping any "is X still Y?" check, name the exact object whose state decides
it — then read that object. If the check reads something *derived* from the object (a log, a feed, a count),
it is measuring the derivation, and it will be right up until the moment the derivation stops tracking.

---

## 11. Related Skills

- `defi-lp-monitoring` — LP-specific metrics (efficiency, IL, fees) that feed into this pattern
- `agent-coordination` — vault logging, handoff protocols, Mess Hall notes
- `system-health` — cron job health check, failure alerts, gateway monitoring

---

## References (Session-Specific Detail)

**Linked files** — use `skill_view(name='stateful-alert-monitoring', file_path='...')` to read:
**Linked files** — use `skill_view(name='stateful-alert-monitoring', file_path='...')` to read:

- `references/state-helpers-template.py` — boilerplate `load_state()` / `save_state()` with atomic write + time helpers
- `references/defi-milestone-case-2026-05-02.md` — ⚠️ case study: DeFi Master Cron enhancement, Jordan's voice-approved rules (5-min debounce, efficiency≤30% immediate, bid-ask edge), implementation handoffs to DMOB + YoYo
- `references/port-health-monitor-pattern.md` — TCP-level service health monitoring when services lack `/health` endpoints. Two-level check (OS port listening + HTTP response). Bypasses Cloudflare SSL for definitive VPS-local checks.
- `templates/state-schema.json` — JSON schema for state file (pending_breakout, last_alert_sent, alert_history)
- `templates/telegram-alert-template.md` — mini-warning vs confirmed alert markdown templates for all three tiers

**Implementation example in production:**  
`03-Strategies/scripts/defi-master-cron.py` (post-enhancement) — watch for this file to appear with stateful debounce logic.

*Last updated: 2026-05-07 20:25 UTC — Added §9a "Suppress-Until-Resolution Pattern" (Jordan's alert-once-per-condition preference). Added reference: suppress-until-resolution-case-2026-05-07.md with implementation details and comparison table.*
