---
name: cron-health-standard
description: "Fleet-wide standard for cron health: every job declares its INTENT, every ring ships a self-healing sentinel that retries once before it speaks, alerts ONCE per distinct problem and re-arms on success, and a monitor that cannot read its own job list reports UNKNOWN — never healthy."
tags: [cron, health, self-healing, intent, monitoring, debounce, agent-kit, fleet-standard]
trigger: "When creating, registering or auditing ANY cron job, in ANY profile — and whenever a cron job fails, goes quiet, repeats an alert, or someone asks 'is everything still running?'."
related_skills:
  - ../cron-truth-layer/SKILL.md          # verify data before acting; this verifies the JOB
  - ../verify-after-every-action/SKILL.md # a change is not done until it is re-read
  - ../../devops/cron-delivery-audit/SKILL.md
  - ../../devops/stateful-alert-monitoring/SKILL.md   # the debounce pattern, generalized
version: 2.0.0
author: Gentech
---

# Cron Health Standard (fleet-wide)

**Every cron job in every profile declares what it is FOR, is watched by a sentinel that reads
its recorded outcome, is retried once before anyone is woken up, and is reported ONCE per
distinct problem instead of once per run.** A job that fails silently is indistinguishable from
a job that never ran — and nobody finds out by being asked afterwards.

This is the generalization of the one-profile treasury sentinel. Measured before it existed:
**130 jobs across 4 profiles, and the health sentinel lived in ONE ring.** Every other ring had
exactly the blind spot the treasury had.

---

## The rules

### 1. DECLARE INTENT — every job says what it is FOR, machine-readably

**Rule: every cron job has a one-line `intent` resolvable by machine.** A failure is triaged
against *purpose*, never reported as an opaque error string. `last_error: "exit code 1"` tells a
human nothing; `INTENT: weekly country-adoption scan for the AVAX laggard thesis` tells them
whether to care at 3am.

**Where intent is recorded — the registry.** `/opt/data/.obsidian-vault/10-Labs/agent-kit-self-tracking/cron-intents.json`
(vault canonical; a copy ships next to the sentinel in each profile's `scripts/`):

```json
{ "by_id":     { "<job id>": { "intent": "…", "profile": "…", "source": "curated" } },
  "by_name":   [ { "profile": "*", "match": "^Wake ", "intent": "…" } ],
  "lookup_order": ["job.intent", "by_id[<id>].intent", "by_name[].match regex", "derived (flagged)"] }
```

**How a job's intent is looked up — deterministic order** (implemented in
`cron_health_fleet.py::intent_for`, do not invent a second scheme):

1. the job spec's own `intent` field, if a job ever carries one;
2. `by_id["<job id>"]` in the registry;
3. the first `by_name[]` rule whose `match` regex hits the job name (`profile` `*` or the job's own);
4. otherwise **derived from the job's own prompt** (`derive_intent`) and **flagged `DERIVED`** in
   every report, with a standing instruction to curate it.

**Curation is the job author's, at authoring time.** A derived intent is a starting point, never
a substitute. When you register a job, add its `by_id` entry in the same change — an intent that
is not written down is an intent nobody can triage against.

### 2. EVERY RING SHIPS A SENTINEL THAT READS, HEALS, THEN SPEAKS

**Rule: every profile's cron ring runs a health sentinel on a ~30-minute cadence.** In order:

1. **READ** every job's recorded outcome — `last_status`, `last_error`, `last_delivery_error`,
   `failure_streak`, `enabled`. These fields already exist; **a field nobody reads is not a
   monitor, it is a diary.**
2. **CLASSIFY** — apply self-exemption, then the paused-broken rule, then the healthy-silent rule
   before any heal or speak step. (See the sub-rules below for the exact ordering.)
3. **HEAL** — re-fire a failed **SCRIPT** job **once**, immediately. Most failures are transient
   (lagging RPC, rate limit, node timeout) and the retry clears them.
4. **SPEAK** only about what healing could not fix — and only once per distinct problem (rule 3).

#### The classification rules (applied in this order)

**PAUSED IS NOT RETIRED — a disabled job with a failure record is still a finding.**

`enabled: false` ends retries, not accountability. A paused job that left a `failure_streak`
behind it is a broken thing we stopped trying to fix. Report it as `PAUSED_BROKEN` with its intent
and last error, **unless** the pause carries an explicit, machine-readable reason that says it was
deliberately retired (`archived`, `deprecated`, `migrated`, `user_paused`).

Why: a sentinel that skips every disabled job cannot distinguish "we turned this off on purpose"
from "this thing broke, we hit pause, and now it rots silently." The latter is how a money cron
disappears for three days while everyone assumes it is healthy.

**Classification order, hard:**
1. `is_self()` — sentinel/health jobs: exempt, never report on itself.
2. `enabled == false`:
   - reason in `{"archived", "deprecated", "migrated", "user_paused"}` → **silent** (legitimate retirement);
   - any other reason or no reason, and `failure_streak > 0` or `last_status == "error"` → **PAUSED_BROKEN finding**;
   - otherwise → silent.
3. `last_status == "ok"` and no error → silent.
4. `heal` branch — retry once if script exists and idempotent.
5. Remaining unhealed failures → finding.

The PAUSED_BROKEN branch must run **before** the heal branch, so a paused job can never be
re-fired. A refactor that moves the `is_self()` or pause checks below the heal call re-introduces
the exact outage this ordering prevents. Pin the ordering with a test that asserts `is_self()` and
`PAUSED_BROKEN` return before the heal call site.

**Rule: every deliberate pause must declare its reason.** A pause with no reason is a bug report
waiting to happen. Write the reason into the job's metadata (`pause_reason`) or registry entry at
the same moment you pause it; a reason added afterwards is indistinguishable from a cover-up.

**A PAUSE IS A REQUEST, NOT A GUARANTEE — verify it LATER, and DELETE a duplicate instead.**
`hermes cron pause <id>` rewrites `jobs.json`, but the **running scheduler holds its own copy in memory and
re-persists it** on its next state write. Measured: a duplicate job was paused, confirmed `[paused]` in
`hermes cron list` **and** `enabled: false` in `jobs.json ` — and **40 minutes later it was `enabled: true` and
delivered to HQ anyway.** A pause verified only at the moment you set it proves nothing.

- **The check is a second look after a window, not a second look immediately.** Re-read `enabled` on a later
  turn (or from the sentinel, which does run later) before believing a job is stopped.
- **For a duplicate or retired job, delete it.** A deleted job cannot be re-persisted; a paused one can. Pausing
  is for *keep it, stop firing*; deletion is for *this must never run again*.
- **Never report "I paused it" as the control.** The control is `enabled: false` observed after the scheduler
  has had a chance to write. Same class as a green check that never exercised the thing it claims to verify.

**Rule: a PAUSED_BROKEN finding uses the same debounce as any other finding.** It is not a special
class that re-alerts every tick; it alerts once, then stays silent until the condition changes or
the job is unpaused and fails again.

**Rule: HEAL BEFORE SPEAKING, and treat a silent successful retry as the ideal outcome.** The
fleet repaired itself and nobody was woken up for it. An alarm that fires on a transient blip
teaches the humans to ignore alarms.

#### A job whose PERIOD is long must carry its own retry budget

**The sentinel's heal is an IMMEDIATE single re-fire. That is the right shape for a job on a short
cadence and the wrong shape for a job on a long one.**

A failure that clears in seconds (a lagging RPC, a stale node) is fixed by an immediate retry. A failure
that clears in **minutes** — a rate limit, a throttled upstream, a cold start — is not: retrying at once
hits the same wall, and the sentinel's next tick is 30 minutes away while the job's own next run may be a
week away. **For a weekly job, one failed run is not a bad run; it is a dark feature for seven days**, and
the thing it was built to feed goes on without it.

**So the retry budget belongs to the JOB, sized to the job's period and to the failure's observed recovery
time:**

- **One bounded wait, not a burst.** `attempt → if failed, wait N minutes → attempt once more → refuse`.
  Two attempts is usually right; a third rarely changes the outcome.
- **Space it to the recovery time, not to a convenient number.** A rate limit measured to clear in minutes
  needs the wait in minutes. An immediate second attempt after a throttle is not a retry, it is the same
  request that already failed.
- **Never stack quick retries against a rate limit.** That deepens the block and turns a one-period outage
  into a multi-period one. **Waiting is the fix; retrying harder is the cause.**
- **The second attempt must be in the wrapper the job actually runs**, not in a human's memory. A retry
  described in a runbook is a retry that does not happen at 14:00 on a Friday.
- **Refusal is a real outcome — make it loud and accurate.** After the budget is spent, print `UNMEASURED`
  with the reason and **write no artifact**. A stub file produced to look complete is worse than a missing
  one, because the consumer cannot tell the difference.
- **Say what the absence means.** The downstream reader must be able to report *"no input on file"* rather
  than implying the upstream was legitimately quiet.

**Test both branches with a stub** (a script that always fails, and one that succeeds) before trusting the
retry: the failure path is the one that never gets exercised in production until the day it matters.

**Rule: a ring heals only its OWN profile's jobs.** The ring that owns a job is the one that
re-fires it, so a money script is never double-fired by two rings seeing the same failure. A
wedged ring's jobs are still detected and reported by the others.

**Rule: register it as `no_agent: true` with `--quiet-unless-bad`.** Empty stdout delivers
nothing, so a healthy fleet is literally zero notifications. Silence means *nothing changed*.

**Rule: a sentinel must not grade its own report.** Exclude every health job from its own scan
(by name / id / script). A sentinel that exits non-zero when it finds a problem records *itself*
as a failed job, and the next run sees a permanent failure it can never heal — an alarm that can
never be cleared. The report states the exemptions it made.

**Rule: an agent-prompt job has no script and CANNOT be re-fired mechanically.** Report it as
`cannot retry: no script (agent-prompt job)`. Never print a retry that did not happen.

**Rule: idempotency is the job author's call, not the monitor's.** A job that must never be
double-fired (a partially-executed money action) sets `"heal": false` in its registry entry or
`heal: false` in its spec; the sentinel then reports `retry suppressed: job is marked
non-idempotent` instead of firing it. The sentinel exports `HERMES_HEAL=1` / `STEWARD_HEAL=1` on
every retry so a money script can behave conservatively when it knows it is a heal.

### 2b. SILENCE WHEN THERE IS NOTHING TO SAY — the reporting job's default state

**Jordan, 2026-11-15:** *"Silence when there's nothing to say should also be a standard rule for the cron
jobs that have to report something."*

**Rule: a reporting job that finds nothing emits NOTHING** — not a header, not a legend, not "all clear".
Empty stdout is the success signal.

**Why it is a rule and not a preference:** a job that always says something **cannot report an anomaly**,
because its reader has no baseline of quiet. Six "13 notes still missing" messages a day make the seventh —
the one that matters — indistinguishable from the six that did not.

**Four obligations, in order:**
1. **Silent when clean.** No output at all.
2. **Speak with the NUMBER that changed** when it finds something.
3. **Say so when it CANNOT read** (`COULD NOT READ — NOT a clean result`). *Silence from a broken
   instrument is the worst outcome of all: it reads as health.*
4. **Report once, then quiet until it changes** — a STANDING condition (true and staying true) speaks once;
   only a FLAPPING one re-speaks. The test is not "is this true?" but **"have I told them since it became
   true?"**, so a reporter compares against what it last REPORTED, never against yesterday.

**Exit 0 on findings.** A non-zero exit means *the instrument could not run*, not *it found something*.
Hermes cron logs any non-zero exit as a failed run — which is how healthy checkers spent weeks showing a
warning light.

> **Scope, because rule 5 states a different set of codes and both cannot be true for one script.**
> Rule 5's `0/1/2` describes the **fleet sentinel** (`cron_health_fleet.py`), whose whole purpose is to signal a
> new problem upward — and whose `exit 1` is therefore expected and is documented in the `status: failed` table.
> **An ordinary REPORTING job is the opposite case: it must exit `0` when it has a finding**, because its
> message *is* the delivery and a non-zero exit only paints its own run row red. Use `2` for "could not read".
> If you are writing a job that reports to a human, follow rule 2b. If you are writing a sentinel that reports
> on other jobs, follow rule 5. Say which one the script is in its header.

**The one legitimate exception — DIGESTS.** A digest may speak on its cadence, because *"nothing changed" IS
the information.* The test: **"Would a week of quiet hide information the user asked for?"** Yes → digest, and
its header must say so. No → watchdog, and a watchdog is silent.

*(A second, narrower exception exists — the closing ritual the human asked for, one line, in §4. It is not a
digest: it reports no content and carries no detail. Do not let it become permission for a periodic report.)*

**This rule's depth lives in `silence-gated-monitors`** — the gate contract, the FLAPPING/STANDING table, the
`last-reported` state recipe (including the bug where state loaded as `.get("routes")` made the compared key
permanently `None`), the legend-line defect that makes a gate unreachable, and the fleet-wide audit that
separates a digest from a watchdog. **Audit silence by RUNNING a job twice and counting bytes, never by reading
its source** — static analysis of behaviour produced four false violations in one sitting. Do not restate any
of it here; load the sibling skill.

### 2c. EVERY NEW JOB ANNOUNCES ITSELF — the register and the delta

**Jordan, 2026-11-17:** *"I didn't even know I had a cron job for 11 Labs running. What is it for? Do we even
need it?"* — he learned it **from a self-reflection**, weeks after the job had done its work and **720 runs
past the point it should have stopped**.

> **A job an agent creates while the human is at work must be a message the next morning, not a discovery
> later.** Nothing in rules 1–8 catches this: the job was healthy, declared an intent, ran silently — and was
> **invisible to the person paying for it.**

**Two artifacts, both mandatory:**

1. **`00-HQ/cron-register.md`** — one line per job: **purpose · RETIRES WHEN · owner.** A job with no stated
   purpose is itself a finding, because intent cannot be inferred from a name.
2. **`cron-register-delta.py`, wired into the PA suite as the `[new]` section** — keyed by `seat+job id`,
   reporting only jobs that **appeared, changed, or vanished** since the last snapshot. **Silent when the
   fleet is unchanged** (rule 2b). Prints `PURPOSE: (none stated — ask)` for a job that has none.

**Rules that make the delta honest:**

- **The first run is not news.** It baselines and prints one line. A first run that lists 66 jobs teaches the
  reader to skip the section forever.
- **An unreadable `jobs.json` is `exit 3`, never silence.** A register that cannot read a seat reports a
  **partial** delta and says so — a baseline that silently loses a seat reports nothing for that seat forever.
- **A snapshot that could not be written must repeat the report next run**, and say so. Otherwise the baseline
  never advances and the same job is announced daily, or worse, is announced once and then never again.
- **Key on `seat + job id`, never on name.** Renaming a job is not a new job, and an id is the only stable key.

### 2d. A ONE-SHOT MUST PROVE IT CAN STOP

**Measured 2026-11-17:** the ElevenLabs lane watch existed to announce one transition and **retire itself**.
It fired **2026-10-18** and then ran **720 more times** over 30 days. Its kill switch had **two independent
fatal defects**, and `|| true` hid both:

```bash
SELF_ID="${ELEVENLABS_SELF_ID:-}"        # (1) the job's env is null, so this is ALWAYS empty
if [ -n "$SELF_ID" ]; then
  hermes cron pause "$SELF_ID" --reason "…"   # (2) `--reason` is not a flag pause accepts
fi
```

**The rule: a bounded-purpose job's retirement is a test, not a comment.** At the moment you write a job that
says *"announces once, then retires"*, prove the retire path executes at least once — point it at a throwaway
job id, run it, and confirm `hermes cron list` shows `PAUSED`. **`hermes cron pause` takes a job id and nothing
else; it has no `--reason` flag, so never pass one and never assume it was recorded.**

**Corollary — never let a kill switch depend on an env var you did not set.** Fall back to the job's own id
(`${SELF_ID:-<literal id>}`), so retirement cannot be disabled by a missing variable.

**And the tell that finds these without reading code:** a job whose **name or prompt** mentions *watch, once,
until, then goes silent* — grep the fleet for those words and check each one actually stopped.

### 2e. A FAILURE PATH THAT EXITS 0 IS A SUCCESS CLAIM

**Measured:** a backup script had **eight failure paths, every one `exit 0`** — including
`echo "🔴 PUSH FAILED — the vault is not backed up"`. Cron recorded **`succeeded`**, the health sentinel saw
`ok`, and the only surface that would have shown the alarm was the message being suppressed. The backup could
have been dead for weeks with a green row every hour.

**The rule: the exit code is the job's claim about whether it did its work. `echo "FAILED"; exit 0` is a lie
that every layer above it then repeats.**

- **Three outcomes, not two.** `0` = did the work, or legitimately had nothing to do · `1` = ran and failed ·
  `2` = could not run, or refused a precondition. **"Nothing to commit" is a real `0`** — do not turn a no-op
  into an alert, or the job cries wolf on its most common night.
- **A refusal is not a success.** A compliance gate that blocks a push (media staged, file over the size
  ceiling, repo over budget) exits non-zero: the thing the job exists to do did **not** happen. Rejecting bad
  input is an outcome worth reporting, not a quiet one.
- **Never infer severity by grepping the output.** Matching words like "error" is the same class of mistake as
  reading a sync log for its reason line and finding it empty. Codes carry severity; prose does not.
- **But do not trust the codes either.** Any wrapper that gates on severity — quiet hours, delivery,
  escalation — must ALSO honour one explicit, fleet-conventional marker (🔴) **at exit 0**. You did not write
  the script you are wrapping, and the marker costs a string comparison.
- **Auditing the class:** grep each job's script for a failure word on the same line as `exit 0`. That finds
  only single-line patterns, so the count is a **lower bound** — say so. A clean scan is not a clean fleet, and
  claiming otherwise is the same false-clean this rule exists to stop.

### 3. ALERT ONCE PER DISTINCT PROBLEM, RE-ARM ON SUCCESS

**Rule: a monitor that reports the same unresolved failure on every tick trains its reader to
ignore it.** At a 30-minute cadence that is 48 identical messages per day for one problem. The
sentinel is therefore **quiet by default even when something IS broken** — it speaks when the
problem is NEW, and then stops.

This is a first-class requirement of the standard, not an implementation detail:

- **DEDUP BY SIGNATURE.** The debounce state (`<state dir>/cron-health-fleet.json`, key
  `<profile>:<job id>`) records the failure signature already reported — the normalized error
  text plus the escalation bucket. Same signature next tick → **silent**, recorded, no message.
- **RE-ARM ON SUCCESS.** When a job is healthy again its entry is cleared, so the NEXT failure
  alerts again. *A problem that recurs after being fixed is news; one that never stopped is not.*
- **ESCALATION IS A CHANGE.** Re-alert when the streak crosses a threshold (3, 6, 12, 24, 48, 96),
  not on every increment.
- **THE DEBOUNCE MUST NOT BE ABLE TO HIDE A NEW PROBLEM.** Suppression is keyed per job id and
  signature: job B failing while job A is silenced alerts normally. Prove this two-directionally
  whenever you touch the logic.
- **ONE VOICE.** All four rings run the same scan and read the SAME state file, and all deliver to
  the same place (Gentech HQ). The first ring to observe a new problem claims it and speaks; the
  others find it claimed and stay silent. That is **one message per distinct problem, from a
  single destination, with four independent readers** — so one wedged scheduler cannot blind the
  fleet and cannot multiply the noise either. (If a ring ever genuinely needs its own lane, give
  it its own `--state` file and destination; do not let four rings each alert to four rooms.)
- **A RING RUNS ONE HEALTH SENTINEL, NOT TWO.** When the fleet sentinel lands in a ring that
  already had a local health job, SUPERSEDE the local one (pause it) — two sentinels for one
  problem is two voices, and the older one usually has no debounce. (Live example: the treasury's
  original 30-minute sentinel would have repeated one known failure 48 times a day; it was paused
  when this standard landed.)
- **THE DEBOUNCE STATE IS SHARED AND ATOMIC.** The state file is read-modify-written under
  `flock`; the claim is what makes "first one wins" true rather than racy.

### 4. QUIET HOURS APPLY TO THE SENTINEL TOO

**Rule: outside working hours, RECORD and HEAL — do not deliver.** A failure discovered at 04:00
is still read, still retried, still recorded in the state file; only the MESSAGE waits, and it is
flushed by the first run after the window (default `00:00–08:00 America/New_York`, override with
`HERMES_CRON_QUIET_HOURS` / `HERMES_CRON_QUIET_TZ`). Discipline is not an exemption from the
hours it is protecting: waking the founder at 04:00 for something the morning digest can carry is
the same noise failure as a repeated alert.

**Quiet hours are not only the sentinel's problem.** Audit every enabled job whose schedule can land inside the
window and whose `deliver` is a chat: a job on `40 * * * *` spends **nine of its twenty-four daily runs** in a
22:00–07:00 window, and every one of them announced itself. Count them before believing a window is quiet.

**THREE DISPOSITIONS PER JOB, and they are not interchangeable.** Decide per job, from a measurement, never from
its name:

| the job | disposition | why |
|---|---|---|
| **must run overnight** — backup, mirror, sync, watchdog | **GATE it** (wrap in the quiet gate) | it keeps running and stays quiet; only the message waits |
| **its message IS its product** — a morning report, a to-do list | **RESCHEDULE it** into the awake window | **gating a report deletes it**, because there is no later run to carry it |
| **already silent on success** | **leave it alone** | its speech IS the alert; gating it suppresses the one message you wanted |

**Measure before you gate:** run each candidate once on a clean state and record its **exit code and output byte
count**. Zero bytes means the job already obeys rule 2b and needs nothing. Non-zero on a clean run means it is a
report — move it, do not mute it.

**Auditing schedules needs a DST union, not an offset.** A cron expression is in UTC while the window belongs to
the human's timezone: `23:00–07:00 ET` is `04:00–11:59Z` in winter and `03:00–10:59Z` in summer, so a job at
`30 3 * * *` is silent in January and awake in July. **Flag the union of both offsets** — over-reporting by one
hour twice a year is the correct direction to be wrong.

**Implement it as a wrapper, not an edit.** Write one gate, wrap the job's script with it, and repoint the job
with `hermes cron edit <id> --script <wrapper>` — copying the quiet logic into each script means the next script
written forgets it. **The window belongs to the human's timezone and must be computed, not offset**: a hardcoded
UTC range drifts by an hour twice a year and silently moves the boundary.

**Recipe, decision table, fixtures and the fail-closed rules:** `references/quiet-hours-gate.md`.

**A JOB NAME IS NOT EVIDENCE THAT A JOB IS SILENT.** Three verdicts, and only one of them is proof:

| verdict | meaning |
|---|---|
| **GATED** | it runs through the gate — routine output cannot reach a chat |
| **SILENT-EVIDENCED** | a clean run was measured at **0 output bytes**, with the date recorded |
| **SILENT-DECLARED** | its name or description says *"silent unless…"* — **a claim, and the audit must say so** |

Keep the evidence in one file keyed by **script basename** with `clean_bytes`, `measured`, `seat` and
`disposition` — not in the audit's memory, so the next seat can add its own measurements without editing code.
The audit then reports the three states separately and exits non-zero while any job is merely *declared*.
**Why it matters:** the scripts that lied about their exit code were also the ones described in their own
names as silent. A description of intent is written by the same person who wrote the bug.

**The audit that keeps it true must recompute the DST union every run** (see above) and must be wired into a
daily consumer, or the window rots the first time someone adds a job at 02:00. Silent when the fleet is clean
(rule 2b), exit 1 when a job could speak, exit 2 when a seat's `jobs.json` cannot be read.

#### The closing ritual — a scheduled sweep BEFORE the window, not inside it

**A quiet window is only as honest as what was true when it closed.** Anything needing a human has until the
last minutes of the awake window to be said out loud, or it waits until morning and the human finds it late.

**Schedule one sweep 15 minutes before the boundary** (22:45 for a 23:00 close) on the **human's timezone, not
UTC** — `hermes cron create "45 22 * * *" … --timezone America/New_York`, otherwise DST slides it into the very
window it protects. It should **resolve first and report second**: refresh the state files and re-run the
audits it already owns, then report only what is still unresolved.

**This is the second legitimate exception to rule 2b, and it is narrow.** A clean night emits **one line** —
*"last call — nothing needs you"* — because **a ritual that speaks only when something is wrong is
indistinguishable from a job that has quietly died.** Two constraints keep it from becoming the heartbeat rule
2b forbids: it is **one line with no detail**, and the script carries a `--quiet` that restores strict silence
for any other caller. A periodic *report* is still forbidden; a *closing ritual the human asked for* is not.

**Register it like any other job, with an exit that can actually fire** (rule 2d): review at 30 days, and
**retire a sweep that has found nothing for four consecutive weeks** rather than keeping it as ceremony.

### 5. A MONITOR MUST BE ABLE TO SAY "I DO NOT KNOW"

**Rule: an unreadable job list reports UNKNOWN and exits non-zero — never healthy.** The two
states that must never look alike:

```
"nothing is wrong"   -> silence (exit 0)
"I could not tell"   -> SPEAKS, exit 2, and it speaks EVEN UNDER --quiet-unless-bad
```

This is the same trap as a failed `eth_call` reading as a real zero: a monitor blind to its own
blindness reports perfect health, which is worse than reporting nothing. **Silence doctrine
protects against noise from good news; it must never be used to hide blindness.**

Exit codes: `0` healthy, or nothing new · `1` a NEW/unresolved problem needs a human · `2` UNKNOWN.

**`status: failed` in the execution record does NOT mean "the job is broken" — and a health view that prints it
as one is lying.** This standard deliberately uses non-zero exits for *"a human should look at this"* (rule 5
above), while the execution recorder writes every non-zero exit as `status: failed`. The two meanings are
indistinguishable at the `status` column:

| What happened | `status` | What it means |
|---|---|---|
| job ran, found a real problem, exited 1 per this standard | `failed` | **working monitor** — do not "fix" it |
| job threw, could not run | `failed` | broken job — heal or report |
| job ran, exited 0 | `completed` | healthy **or unobserved**, if it never actually did work |

So when reporting fleet health from the execution history: say **"N non-zero exits"**, not "N broken jobs";
read the error text to split a structured finding from a traceback before calling anything broken; and never
propose silencing a job that exited non-zero to report a true condition. That is the same class of error as a
failed read being reported as a real zero.

**Check `delivery_outcome` on every failing job.** A failing alarm with `delivery_outcome: not_configured` is
not monitoring — it is writing a diary. The failure is real, the reader is nobody, and it will fail forever
without anyone learning. Verify the delivery destination of any job that fails before concluding the alerting
path works; "the job reports" and "someone is told" are two separate facts.

See `references/execution-history-reading.md` for the schema and read-only query recipe.

### 6. REPORT A FAILURE WITH ITS INTENT AND ITS ERROR

**Rule: every failing job is reported as `name / id / profile / INTENT / failure_streak /
last_error`** — plus one line saying what the retry did or why none was possible. Name alone is a
page with no information; intent is what makes it triageable by whoever reads it.

### 7. SAFETY — A MONITOR NEVER MOVES MONEY, AND YOU NEVER TEST ON LIVE MONEY

- A health script performs exactly one action: the read-only retry of a job's own script.
  It never reads keys, never signs, never invents a money action.
- **Never prove the heal path by re-firing a real money job.** Build a throwaway job — a script
  that exits 1 the first run and 0 afterwards, off a state file, in a scratch dir — and prove the
  heal on that.
- Registering a job in a profile's own `cron/jobs.json` is expected. Nothing else in another
  profile is in scope.

### 8. WHERE IT LIVES (paths are part of the standard)

| Thing | Path |
|---|---|
| Fleet sentinel tool (canonical) | `/opt/data/.obsidian-vault/10-Labs/agent-kit-self-tracking/cron_health_fleet.py` |
| `no_agent` wrapper registered per ring | `…/agent-kit-self-tracking/cron-health-fleet.sh` |
| INTENT registry (canonical) | `…/agent-kit-self-tracking/cron-intents.json` |
| **Debounce state (shared by all rings)** | `/opt/data/profiles/gentech/state/cron-health-fleet.json` |
| Deployed copies (a cron `--script` must resolve inside the profile) | `/opt/data/profiles/<profile>/scripts/` |
| Sync manifest (vault → repos + profile, md5-verified) | `…/agent-kit-self-tracking/sync-treasury-scripts.sh` |
| Per-ring sentinel job | `Fleet Cron Health Sentinel (self-healing, 30m)`, `*/30 * * * *`, `no_agent: true`, deliver → Gentech HQ |
| Nightly fleet-wide record | `/opt/data/profiles/gentech/scripts/nightly-maintenance.py` → `00-System/nightly-reports/` |
| **HQ escalation path** | `/opt/data/.obsidian-vault/01-HANDOFFS/gentech-treasury-to-gentech/<date>.md` (append-only) + a dated line in `gentech-treasury-completions.md` |

---

## Operating it

```bash
# the cron invocation (what the registered job runs)
python3 /opt/data/profiles/<profile>/scripts/cron_health_fleet.py --heal --quiet-unless-bad

# right now, would it heal anything? (never delivers)
python3 …/cron_health_fleet.py --heal --dry-run

# what is failing and why it is currently quiet
python3 …/cron_health_fleet.py --show-silenced --no-quiet-hours

# the whole fleet, machine-readable
python3 …/cron_health_fleet.py --json

# one ring only
python3 …/cron_health_fleet.py --profiles gentech-treasury

# after adding jobs: seed intents for anything unrecorded (curated entries are never overwritten)
python3 …/cron_health_fleet.py --emit-intents

# make the next run speak again about a known problem (ops)
python3 …/cron_health_fleet.py --no-debounce          # once
python3 …/cron_health_fleet.py --reset-state          # forget everything
```

## Anti-patterns (each one cost real time)

- **Counting `status: failed` as "broken jobs".** The recorder writes an alerting non-zero exit and a real
  crash to the same column, so a dashboard built on `status` alone reports a working monitor as infrastructure
  failure — and the reader then learns the dashboard is noise. Split them by reading the error text.
- **Assuming a failing job has a listener.** `delivery_outcome: not_configured` on a failing job means the
  alarm has been failing into a void, possibly for days. Check delivery on the job, every time.
- **Repeating an unresolved failure on every tick** — 48 messages a day for one problem, and the
  founder learns to ignore the channel. Alert once per distinct problem; re-arm on success.
- **Trusting the sentinel's immediate re-fire for a weekly job.** An immediate retry clears a lagging
  RPC; it does not clear a rate limit. A weekly job that fails is dark for a week — give the wrapper its
  own bounded wait sized to the recovery time, then refuse loudly.
- **A monitor whose output nobody reads** is a diary. Read `last_status`/`last_error` or do not
  claim to monitor.
- **Exiting non-zero on an alert without self-exemption** → the sentinel becomes the permanent
  failure it can never heal (live example: the treasury sentinel flagged an agent-prompt job,
  exited 1, and was itself the next failing job with `failure_streak=1`).
- **Reporting a retry that could not happen** on an agent-prompt job — say `no script`.
- **Treating "I could not read the list" as healthy** — the blindness failure this standard exists
  to prevent.
- **Letting the debounce state be per-ring while four rings alert** — you get 4 different rooms
  reporting the same problem, each of which then goes quiet on its own. One state, one voice.
- **A new file not in the sync manifest** never reaches the executed copy; it looks written and
  does nothing. Enrol the tool, the wrapper and the registry together, then verify md5.
- **Skipping disabled jobs blindly** — `enabled: false` hides both deliberate retirement AND a
  broken job we paused in panic. Distinguish them by `pause_reason`; report the latter as
  `PAUSED_BROKEN`.
- **Moving the classification checks below the heal call** — a refactor that reorders `is_self()`
  or `PAUSED_BROKEN` after `heal()` can re-fire a paused or non-idempotent money job. Pin the
  ordering with a test that targets the heal **call site**, not the function definition.
