---
name: wall-clock-scheduling
description: "Use when scheduling at the user's local wall-clock time."
category: ops
version: 1.0.0
author: Hermes curator
license: MIT
tags: [cron, scheduling, timezone, dst, reminders, one-shot]
metadata:
  hermes:
    tags: [cron, scheduling, timezone, dst, reminders, one-shot]
---

# Wall-clock scheduling

Turning *"remind me Friday at 6:30"* or *"run this every morning at 9"* into a schedule has two failure
modes, and both are **silent**: an offset that is off by an hour, and a reminder whose text nobody
reviewed. This is the procedure for both.

## When to Use

- The user gives a time in their own words — "after work", "tomorrow 6:30pm", "Sunday morning".
- Creating or editing a cron job or one-shot pinned to a local time.
- The user asks you to **fix** a scheduled time.
- **After a DST boundary**, for any job pinned to a local time, and for `TZ`-derived quiet hours.
- The agent reports a wrong day or hour, or the user asks whether the fleet "knows what time it is".

## 0. Your OWN clock is configuration — measure it before trusting a single time you say

**Rule: an agent has no internal clock, and `hermes_time.now()` returns SERVER-LOCAL unless the profile
configures a `timezone`. On a UTC container that means every seat silently speaks UTC while the user reads
local.** Before any time-bearing claim, resolve both the clock and the zone, in one call:

```bash
date -u; date '+%Z %z'; python3 -c "from hermes_time import get_timezone_name, now; print(get_timezone_name() or '(unset)', now())"
```

- **`''` or `None` from `get_timezone_name()` is the defect, not a detail.** It means no `timezone` key exists in
  the profile's `config.yaml`; the loader falls back to server-local. `get_timezone()` returning `None` is the
  tell that a UTC answer is a fallback rather than a configuration.
- **Fix it per seat:** `HERMES_HOME=/opt/data/profiles/<seat> hermes config set timezone America/New_York`.
  The profile selector is **`HERMES_HOME`** — `HERMES_PROFILE` writes the default profile's config three times
  while reporting success each time.
- **Verify through the real loader per seat**, not by grepping the YAML: `HERMES_HOME=<seat> python3 -c "from
  hermes_time import get_timezone_name, now; print(get_timezone_name(), now().strftime('%H:%M %Z %a'))"`.
  A config value that the loader does not read is the same as absent.
- **Set it on EVERY seat in the same pass.** One seat thinking UTC and another local produces two different
  answers to "is it too late to bother the user?" — the same class of defect as seats on different rails, and
  just as invisible until someone acts on the wrong one.
- **Config timezone governs how an agent SPEAKS. It does NOT decide when a cron job fires — and an ABSENT
  `timezone` on the job does not mean UTC.** Measured across one fleet: **43 of 47 enabled jobs carried no
  `timezone` field and every one evaluated on the profile's LOCAL clock**, so hours authored as UTC fired five
  hours late and landed overnight. Only an explicit `timezone` (or a job already anchored to `+00:00`) is UTC.
  Convert explicitly when pinning a job to the user's day, and name the conversion you used ("16:00 ET =
  21:00 UTC in EST") so the reader can check it. See §1.5 — the offset on `next_run_at` says which zone a job
  is really using.
- **Write the user's standing pattern down where every seat can read it** (a `schedule.md` in the vault: working
  hours, when they are reachable, what is not assumed). Chat silence during known work hours is not
  disagreement, and a queue is the right place for anything needing their hands — not a repeated question.
- **Record the DAYS, not just the hours, and quote the user's own words.** A pattern written as "most days,
  until ~16:00" is wrong in both directions the moment the real one is "Thursday–Sunday, 06:30–15:30, home ~16:00":
  it invents work on the off days and puts the shift an hour late. Store the weekdays explicitly, the shift
  window, the commute estimate, and a line saying **overtime is announced, never inferred** — otherwise an agent
  explains a slow reply by inventing a late shift, and every downstream time decision inherits the guess.
- **Verify the day logic by evaluating a whole week, not just "now".** A single correct-looking reading proves
  nothing about Thursday. Run the classifier over seven days at the hours that matter and print the verdict per
  row; a wrong weekday set shows up immediately as "AT WORK" on a day the user said they were off.
- **When the real pattern finally arrives, re-audit every job placed against the guess.** A job whose NAME embeds
  a time ("weekly — Sunday 3:30pm ET") is a fossil of the old assumption: it will keep firing an hour early
  forever and read as correct, because the schedule and the name agree with each other and both are stale.
  Enumerate the roster in the user's zone, mark every job landing inside the shift, and say which ones are
  reports (move them to the evening window) versus detection (leave them where they are).

## 1. Resolve the offset for the TARGET DATE, not from the zone label

**Rule: convert a stated wall-clock time using the calendar, never the phrase the user used for their
zone.** People say "Eastern Standard Time" year-round, but US Eastern is **UTC-4 while daylight time is
in force** and UTC-5 outside it. Ask the zone database, then convert:

```bash
TZ=America/New_York date -d '2026-10-16 18:30' '+%z %Z'   # -0400 EDT -> 22:30 UTC
TZ=America/New_York date -d '2026-11-02 18:30' '+%z %Z'   # -0500 EST -> 23:30 UTC
```

**⚠️ Never add `-u` to that command.** `-u` sets the zone for **both the parse and the display**, so it
discards the `TZ` you just set: `TZ=America/New_York date -d '2026-11-07 16:00' -u` prints `16:00 UTC`
where the answer is `21:00 UTC` — a five-hour error delivered with total confidence, and the wrong hour
lands the job early rather than late. Convert by displaying `%z`/`%Z` and doing the arithmetic, or by
epoch (`date -d '…' +%s`), or with `zoneinfo` in Python. **Whatever the method, make the offset itself an
output you read** — if you never see `-0500`, you have not converted, you have assumed.

**Second check, always: re-read the clock at the moment you report the schedule.** Convert, then subtract
from now. A target that is already in the past is a message that should say the window closed, not a
future-tense promise.

- **A stored TZ label is not evidence about today.** A note reading *"timezone: Eastern Standard Time
  (UTC-5)"* records the standard-time name; it says nothing about a date inside DST. Read it as the zone
  *identity*, then resolve the *offset* for the date in question.
- **Harvest the zone from the user's own artefacts, then verify it.** Notes, digests and previously
  scheduled jobs often state the zone and the intended waking hours — a better source than a guess, and
  still only a starting point for the measurement above.
- **Write times as explicit offsets** (`UTC-4`, `UTC-5`) when recording or reporting a schedule, so the
  DST question is answered inside the artefact instead of being re-derived by the next reader.

## 1.5 An absent `timezone` field fires on LOCAL time

**Rule: read the offset on `next_run_at` before touching any job.** `-05:00` is truthful evidence the scheduler is
evaluating that expression in New York; `+00:00` means it is already UTC. **The offset is not stale metadata — it
is the only honest statement of which zone a job is really using**, and reading it as stale is what keeps this
bug alive.

- **A mixed offset set means two evaluation zones behind one absent field** — pin the zone each job's own offset
  names (`-05:00` → `America/New_York`, `+00:00` → `UTC`), not one bulk zone. **Do not pin `America/New_York` and
  revert what moved:** the movers include human meetings and every revert is a five-hour lurch to catch.
- **`hermes cron edit` persists; `hermes cron pause` does not** — the scheduler rewrites `jobs.json` from memory.
  Verify after a ticker heartbeat advances.
- **Verify fire times from `executions.db`, never from the job's own output.** A script that stamps its header in
  UTC makes a 01:30-local run print as `06:30 UTC` — a valid slot for the expression — so the defect reads as
  correct forever.
- **Sweep job NAMES for a stated time and compare to the delivered local time.** A job named *"Sunday 3:30pm ET"*
  anchored to UTC fires at 14:30 ET, because a UTC anchor does not move at DST. Pin it local so the name stays true.
- **A pin exposes intent; it does not set the right time.** Move what is wrong *for a human* in the same sitting,
  declared rather than buried.

> Commands, the instant-diff procedure, the durability proof and the DST consequences:
> `references/cron-timezone-implicit.md`.

### 1.6 Once jobs ARE pinned, an audit that reads the expression is the defect

**Rule: the artifact you diff is the FIRE INSTANT (`next_run_at`), never the expression.** A pinned job's
expression is a local-clock statement; anything that parses its hour field as UTC invents a five-hour error and
flags correct jobs. The same rule forbids the two opposite mistakes in one pass: **converting the hours AND
pinning the zone double-applies the offset** — pick one.

- **Answer with the offset, not with an argument.** `next_run_at = …T07:30:00-05:00` is machine-generated and
  settles it in one line; show ET beside UTC as the second half.
- **Retire any realigner whose premise the schema has falsified** — a registry that stores expressions "as UTC"
  because the build "has no per-job timezone field" keeps rewriting zoned jobs and then reports `In step.
  Nothing to change.` (it compares live expressions to its own registry, so *unchanged* reads as *correct*).
- **Two quiet-hours windows in play?** Schedule into the intersection, report which runs crossed which, and ask
  which is the standard. Details and the false-alarm shapes: `references/cron-timezone-mechanics.md`.

## 2. Verify before complying with a "fix the time" request

**Rule: when the user asks you to correct a scheduled time because of a zone label, measure the offset
first — and if the schedule is already right, change nothing and say so with the conversion shown.**

A correctly-set one-shot *looks* wrong to anyone reading a colloquial label, and obeying moves it an hour
the wrong way — on the one class of job where being late **is** the whole failure. Correcting a correct
value on request is a real error, not politeness. The reply that works: the measured offsets, the
sentence "nothing needs changing", and an offer to shift it if their clock actually reads differently.

Related: **a stated preference and a device's behaviour can disagree** (a machine left on the wrong zone,
someone reading the standard-time label on a phone). You cannot read their clock, so state the conversion
and let them confirm against the device they will actually be looking at.

### Reporting a scheduled time BACK to the user: convert it, or do not say it

**Rule: any time you present as *the user's* time must come from a zone-database conversion, never from
reading the cron expression and calling it local.** A schedule is stored in UTC; the user's clock is not.
An uncoverted UTC value stated as "your time" is off by the offset with total confidence, and it is the
version they will act on.

```bash
date -u; TZ=America/New_York date     # run BOTH, in one call, before writing a time into a reply
```

- **Read the current local clock in the same breath as the schedule.** "The reminder fires at 15:30 your
time" delivered at 19:31 their time is wrong twice: the conversion was skipped *and* the relationship to
"now" was never checked. If the true local time is already past the target, the honest sentence is that
the window has passed, not a future-tense promise.
- **State both zones when the number matters** ("20:00 UTC · 15:00 ET"), so the reader can check it
  without trusting your arithmetic.
- **Do not do the offset in your head, and do not re-derive it from the job's own display string.** The
  cron display is the input to the conversion, never its output.

### A one-shot ACTION scheduled as a recurring job keeps nagging after it is done

A reminder for something finite (run this command, fund this wallet, submit this form) is often created on
a daily schedule so it survives a missed day. That is a reasonable choice — **but the job has no idea the
action happened**, so it fires tomorrow about work already finished, and the reader learns to ignore it.

- **Say in the reply that it repeats**, and that it will be retired on completion.
- **Retire it the moment the user reports the action done** — and verify the removal, not the request.
- If it must be recurring, give it a **silence gate** (fire only while the condition is still true) rather
  than trusting the reader to remember which reminders are stale.

## 2.5 Quiet hours — a standing window, and how to enforce it

A one-off reminder resolves to a date (section 1). A **standing quiet-hours window** is a different shape of
problem: it applies to every scheduled job, forever, and it has to survive both the DST boundary and the next
agent who adds a job at 3am.

**Rule: define the window in UTC, write it down in one place, exempt maintenance explicitly, and enforce it
with a read-only audit.**

- **UTC, not local — but say what that costs.** A local-time window silently shifts its own edges twice a year
  (a 7am job becomes a 6am job with no edit and no warning); a UTC window keeps identical UTC hours and moves
  its *local* edges by an hour at the switch. Pick one deliberately, state the trade in the document, and
  re-check at DST. Never leave it implicit.
- **The boundary is inclusive.** An hour field of `0` is midnight UTC — which is 19:00 the previous evening at
  UTC-5, i.e. the *evening edge* of the window, not after it. An audit that treats `0` as "overnight" reports a
  violation on a job that is exactly on the edge.
- **A report is MOVED, never gated.** Suppressing a report's stdout does not defer it — the message is lost
  until the next run, and a nightly to-do buried at midnight is gone rather than quiet. Gate only what must run
  overnight (backups, sync, probes); **reschedule** anything whose product is its message. "I gated it" and "I
  fixed it" are different claims, and only the second one keeps the information.
- **Maintenance is the only exemption, and the allowlist is explicit.** A job qualifies when it is *silent
  unless broken* and exists so the morning is legible (backups, sync, hygiene, aggregation). A **report** that
  must run at 3am is a mistake, not maintenance; a **liveness probe** that is silent-by-design is maintenance.
  Keep the allowlist in the checker, not in prose, so adding to it is an edit someone can review.
- **State the consequence the user is accepting**: with reporting confined to the window, nothing reports
  overnight and a 2am breakage is discovered when the window opens. Say it once, at the change, rather than
  letting them find out during an incident.

**Rescheduling an existing set — enumerate before editing.** Do not hand-edit schedules from memory:

```bash
# list every job with its cron expression and enabled state
python3 - <<'PY'
import json
jobs = json.load(open('<profile>/cron/jobs.json'))
jobs = jobs if isinstance(jobs, list) else jobs['jobs']
for j in jobs:
    if j.get('enabled'):
        print(j['id'], (j.get('schedule') or {}).get('expr'), j.get('name'))
PY
```

- Parse the **hour field** (handles `*`, `*/N`, `a,b`, `a-b`) and flag every job whose hours fall outside the
  window; that set is the work list, and it is the only reliable one.
- Move reporting jobs into the window (compress cadence rather than stretching into the night — a 4-hourly job
  in a 12-hour window is 3–4 runs, not 6), and leave the maintenance allowlist alone.
- Re-run the audit afterwards and require **zero** violations before reporting success.

**Ship the audit as a script the schedule can call**, so the rule is enforced rather than remembered:

```python
while j.get('enabled'):
    hs = hours_of(schedule_expr)          # set of hours the job fires
    bad = [h for h in hs if h not in ALLOWED and job_id not in MAINTENANCE]
```

Read-only, exit 2 on violation, and scheduled weekly inside the window. A rule nobody checks becomes a rule
that was true once.

### The schedule is a POSITIONAL argument to `hermes cron create` — there is no `--schedule` flag

A schedule passed as `--schedule "40 * * * *"` exits with `unrecognized arguments: --schedule` **before the job
exists**, and the tail of that output is a usage banner — which reads like a broken tool rather than a wrong
invocation. The expression goes first, positionally:

```bash
hermes cron create "45 22 * * *" "One line stating the job's purpose — required, see below." \
  --name "<name>" --script <name>.sh --no-agent --deliver origin \
  --timezone America/New_York
```

- **`--script` alone is REFUSED** — `create requires either prompt or at least one skill`. The prompt is
  mandatory even in script mode, and it is not filler: it is the register entry, so write the job's purpose in it
  rather than passing a placeholder. A bare `--script` exits before the job exists.
- **`--timezone <zone>` pins the expression to a local clock, and it is the right shape for a standing
  local-time job.** `"45 22 * * *" --timezone America/New_York` fires at 22:45 ET all year; `next_run` prints the
  offset (`2026-11-17T22:45:00-05:00`), which is how you confirm the zone took. Prefer this over hand-converting
  a standing job to UTC — a UTC expression keeps its UTC hours and slides an hour in local time at every DST
  switch, which is exactly how a 23:00 quiet-window job starts quietly waking the user at 22:00 without an edit.

- **`--no-agent` plus `--script`** is the shape for anything that must deliver fixed text: the script's stdout is
  delivered verbatim with no model in the path, so what a human reviews is exactly what fires.
- **Read `hermes cron create --help` once per session** rather than trusting a remembered flag set — the
  positional/optional split is the part memory gets wrong, and the failure appears before any job is written.
- **Never hand-edit `jobs.json`** to work around the CLI; read it to confirm the job landed (`id`, `schedule.expr`,
  `script`, `no_agent`), then use `hermes cron run <id>` to prove the wiring rather than only running the script
  by hand.

## 3. One-shot reminders: fixed text, no agent in the path

**Rule: build a reminder as `no_agent: true` + a script that prints fixed text + an absolute ISO schedule
+ `repeat: 1`.** With no model in the path the delivered text is exactly the text that was reviewed, it
cannot be re-worded at fire time, and it costs nothing to run. A reminder that rewrites its own wording is
one the recipient has to re-read to trust, which defeats the point of a reminder.

```bash
# wrapper: plain stdout, delivered verbatim
cat <<'EOF'
🔑 REMINDER — <what and when>
...the steps...
...the do-NOT rules...
EOF
```

- **Schedule an absolute instant**, e.g. `schedule="2026-10-16T22:30:00"` with `repeat=1` — not a
  recurring cron expression. A date-pinned cron entry (`30 22 16 10 *`) repeats annually and quietly
  becomes a bug; the ISO one-shot is the honest shape. Note that `cronjob update` rejects the
  `"once at <date>"` prose form some listings display.
- **Prove determinism before trusting it**: run the wrapper twice and diff —
  `a=$(./remind.sh); b=$(./remind.sh); [ "$a" = "$b" ] && echo deterministic`.
- **Encode the checklist IN the reminder, gates and refusals included.** The recipient reads it in
  isolation, without the conversation that produced it and without the governing skill loaded — so the
  *"do NOT do X"* rules are precisely the part that must survive the trip. State the one or two rules
  that, if forgotten, cause irreversible harm.
- **Point at where the detail lives** (the item file, a one-pager prepared for a third party) rather than
  inlining all of it. A reminder that is a wall of text does not get read; the pointer is what makes it
  actionable — and a one-pager addressed to someone else can be forwarded in place of material that must
  not travel through chat.

## 4. Record it where the user actually looks, in their own format

A reminder that fires but is absent from the list the user reviews is half a task. **Find their existing
tracking artefact first and match its shape** rather than inventing a second place work is tracked —
look for a dated list, an items file, or a running note, and follow its numbering and heading convention.
Adding the item in the wrong format is worse than adding nothing, because it will not be scanned.

## Pitfalls

- **Converting from the zone NAME instead of the DATE.** "EST" in speech is the zone, not the offset.
  Inside DST that label means UTC-4, and a UTC-5 conversion lands the job an hour late.
- **Comparing a UTC reading against a LOCAL schedule time.** This is subtler than forgetting to convert,
  and it produces a confident wrong conclusion rather than a wrong hour: `date` prints `23:10` (UTC) and
  an ET-pinned job shows `18:30`, so "18:30 already passed, it is 22:00" is a statement built from two
  different clocks. Measured cost: a job that was about to fire in 20 minutes was reported as already
  past, and the agent reasoned about catch-up behaviour that could never happen. **A `now` and a schedule
  time are only comparable when both were produced by the same command** — `TZ=America/New_York date
  '+%H:%M'` beside the schedule, in the same call, or neither of them.
- **Reporting "now" while the fleet clock is not the user's clock.** The container answers UTC; the user
  reads ET. Every hour you state without a `TZ=` prefix is a claim about a clock you did not read.
- **Obeying a "fix" that would make a correct schedule wrong.** Measure, then either change it or state
  that nothing needed changing. Never silently comply with a change that breaks the artefact.
- **Leaving a correct value unexplained.** If you decline a requested change, show the measurement and the
  conversion in the reply — an unexplained refusal reads as a refusal to help.
- **A recurring cron expression for a one-off.** Date-pinned cron entries fire again next year; use an
  absolute ISO timestamp with `repeat: 1`.
- **A reminder that only exists as a cron job.** No entry in the user's own list means the item is
  invisible in the only place they review.
- **Treating a DST boundary as a non-event.** Every locally-pinned recurring job drifts an hour at the
  switch; re-audit offsets and `TZ`-derived quiet hours afterwards.
- **Assuming a job with no `timezone` field is in UTC.** It runs on the profile's local clock, so a
  UTC-authored hour lands five hours late — and `next_run_at`'s `-05:00` is the evidence, not stale metadata.
  Reading the offset as "stale" is what keeps the bug alive.
- **Pinning first and reverting what moved.** Read the offset on `next_run_at` and pin the zone it names; a bulk
  pin moves UTC-anchored human meetings five hours and turns the revert into the dangerous step.
- **Assuming a clock because `date` answers.** `date` answers in whatever zone the process has — usually UTC on
  a container. A configured zone you never measured is indistinguishable from no zone at all, and the wrong
  hour arrives with total confidence.
- **Setting the zone on one seat and calling the fleet aligned.** Every seat must resolve the same zone, or two
  agents disagree about the same moment.
- **A standing pattern with no weekdays in it.** "Most days" is not a schedule; it makes every off-day look like
  a workday and every slow reply look like an emergency. Store the day set explicitly.
- **A job named after the time it fires.** The name freezes an assumption that the cron expression then keeps
  honouring; when the user's hours change, both stay wrong together and nothing looks inconsistent.

## Related

- `cron-health-standard` — whether the job is *running* (this skill is about *when* it runs).
- `cron-delivery-audit` — where a job *delivers*, quiet-hours discipline, and channel targets. It is
  **user-owned**, so its timezone guidance cannot be patched by autonomous curation; if it needs the DST
  rule, recommend `hermes curator adopt cron-delivery-audit` rather than editing it.
