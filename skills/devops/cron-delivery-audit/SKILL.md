---
name: cron-delivery-audit
description: Audit and fix cron job delivery targets to ensure jobs deliver to connected channels or origin, preventing silent failures when targeting disconnected Telegram groups.
tags: [cron, hermes, telegram, delivery, audit, ops]
related_skills:
  - ../cron-health-standard/SKILL.md
  - ../../agent-kit/verify-after-every-action/SKILL.md
triggers:
  - Creating or updating cron jobs
  - Cron jobs not appearing in groups
  - Troubleshooting missing cron output
  - Setting up new Telegram groups for Hermes
---

# Cron Delivery Audit

Systematic approach to ensure Hermes cron jobs deliver correctly and don't collide with each other.

## The Real Problem

Hermes cron jobs deliver through the Telegram gateway — **all groups the user belongs to are reachable**. The old model of "only HOME_CHANNEL is connected" was outdated once the gateway matured. The actual failure modes are:

- **Wrong delivery target** — typos in chat IDs
- **Time collision** — multiple jobs hitting the same group at the same minute
- **Job never ran** — script error, not delivery issue
- **Empty output** — script ran but produced nothing

## Delivery Target Reference

| Target | When to Use |
|--------|-------------|
| `origin` | Default — delivers to the chat where the job was created. Safe choice for single-user. |
| `local` | Internal maintenance only (vault sync, health checks). No Telegram delivery. |
| `telegram:<telegram-group-id>` | HQ — coordination, decisions, status reports |
| `telegram:<telegram-group-id>` | Social Media — games, deals, social content, Vanito |
| `telegram:<telegram-group-id>` | **Treasury** — finance, DeFi, portfolio, yield, market signals (renamed from "Strategies" Sep 7, 2026; chat ID unchanged) |
| `telegram:<telegram-group-id>` | Labs — code, SDKs, technical output |

**All groups are reachable.** If output isn't appearing, check `last_status` first — the job may have errored before delivery.

## Delivery contract — gateway message origin

A cron job that delivers through a Telegram **gateway** can carry a **message-origin JSON** supplied with the delivery (platform, chat_id, chat_type, user_id, profile, message_id, source_message_id). That JSON is the SOURCE leg of the delivery:

1. **Read it verbatim.** The canonical file (for example `cron/gateway-origin.json`) is the source of truth — never re-derive the fields from the job's own `origin` dict or from the job name.
2. **Know what it does NOT say.** The fields name who SENT the message and which room it landed in. They do **not** name a bot chat, a reply-to address, or any destination. The JSON is the sender + room, not a reply-to.
3. **Never guess a reply destination from it.** If the JSON carries no destination field, no reply destination is set — the delivery keeps its configured route (`origin` stays as configured). Record the gap in the output instead of inventing a target.
4. **Verify the delivery's legs, not just the run.** `last_status: completed` answers only that the job ran. Measure which leg happened: the script produced output (file exists, nonzero bytes) and the message arrived where the route says. A delivery that has never been observed arriving is a delivery that is unverified — name that rather than quoting a run status.
5. **State which leg you measured** in every delivery: **ran / produced / delivered** (or the measured gap for the ungenerated leg).

**The tenant in one line:** a delivery's origin says WHO SENT and WHERE — never WHERE TO REPLY. If the data does not contain the destination, the route answers, not the origin. A delivery you never observed arriving is a delivery you never verified.

## Multi-User Staggering

When multiple users have cron jobs targeting the same group:

| Risk | Scenario | Fix |
|------|----------|-----|
| **Same time collision** | Two jobs fire at :00 to same group | Move one to :00, the other to :15 |
| **Cross-user overlap** | Jordan + Vanito both at 12:00 Wed | Stagger by 1+ hour |
| **Same-user pileup** | Two Vanito jobs at 13:00 Wed | Offset by 15 min |

**GenTech convention (established Jul 2026):**
- Jordan's shop jobs → Wed 12:00
- Vanito's Game Release Intel → Sun/Wed 13:00
- Vanito's Weekly Sales Sweep → Wed 13:15 (staggered by 15 min)
- Name jobs with user prefix: `[Jordan]` / `[Vanito]`

## Audit Checklist

### Step 0: Verify Script Paths in Job Prompts (Agent-Executed Jobs)

Agent-executed cron jobs (`no_agent: false`) follow a natural-language `prompt` that may reference a script path. If the path is wrong, the agent fails before starting — the job reports `last_status: ok` (the agent ran OK) but the actual work never happened.

**Check for stale paths in prompts:**
```bash
hermes cron list | grep -i "script location\|\.sh\|\.py\|/root/" | grep -E "^[[:space:]]*[A-Za-z0-9_/:\.-]+"
```

**Verify each referenced file exists:**
```bash
ls -la ${PROFILE_DIR}/scripts/  # former default location
ls -la /root/my-music/                           # music sync location
ls -la /root/repos/hermes-brain/scripts/          # backup location
```

**Common stale path patterns:**
- `.sh` wrapper that was replaced by a Python script (prompt never updated)
- Path references `/opt/data/profiles/gentech/scripts/` but script moved to a project directory
- Script was renamed or deleted but prompt still references old name
- Path was typed manually and contains a typo

**Fix pattern:** Find the actual script, then update the prompt:
```bash
cronjob action=update job_id=<id> prompt="...actual script path..."
```

**Pitfall:** The job shows `last_status: ok` even when the path is bad, because the agent ran its full lifecycle (looked for file, didn't find it, returned a no-op result). This makes stale path errors invisible on the cron dashboard. Check agent logs for `No such file or directory` when status is `ok` but expected output is missing:

```bash
grep "vanito-music-sync\|No such file" ${PROFILE_DIR}/logs/agent.log
```

### Step 1: List All Jobs with Schedules + Deliveries

```bash
hermes cron list | grep -E "name:|schedule:|deliver:|last_status:"
```

### Step 2: Check for Time Collisions

Scan for jobs with identical cron expressions targeting the same group. Common collision patterns:
- Same user, two jobs at the same HH:00 (offset by 15 min)
- Different users, same HH:00 (stagger by 1 hr)

### Step 3: Verify Names Are Clear

Jobs should be self-explanatory in the group feed. Prefix with user name:
- `[Jordan] GenTech Shop — Weekly Sales Sweep` ✅
- `Sales Sweep` ❌ — whose?

## Fix Patterns

**Update delivery target:**
```bash
cronjob action=update job_id=<id> deliver=telegram:<telegram-group-id>
```

**Stagger by changing schedule:**
```bash
cronjob action=update job_id=<id> schedule="15 13 * * 3"
```
(`15 13 * * 3` = Wednesday at 1:15 PM)

**Rename for clarity:**
```bash
cronjob action=update job_id=<id> name="[Jordan] GenTech Shop — Weekly Sales Sweep"
```

## Common Job Types and Recommended Delivery

| Job Type | Recommended | Why |
|----------|-------------|-----|
| Single-user content (deals, intel) | Per-topic group or `origin` | Lands where user will see it |
| Team-wide updates (Daily Digest) | HQ (`<telegram-group-id>`) | Everyone sees it |
| Internal maintenance — **producer** (backup, drill, sync, metrics, staleness) | `local` | The artifact IS the product; there is nothing to say |
| Internal maintenance — **reporter** (anything that can only speak on FAILURE) | **a real room, never `local`** | `local` means saved, not known — see the section below |
| Vanito-specific content | Social Media (`<telegram-group-id>`) | Kept separate from Jordan's ops |

## `deliver: local` is SAVED, not KNOWN — a failure-only job must never have it

**A job whose whole design is silence-until-broken delivers its one important message into a text file.** The run
reads `completed`, the artifact exists, and nobody has been told anything. Measured on one seat: **22 enabled jobs
delivered to `local`, and the five that mattered were exactly the five that can only speak when something is wrong** —
a sync verifier that reports only failures, a queue flusher that reports `STUCK` messages, a settlement reconcile, a
cron-conformance check, a trends check.

- **Split the fleet by whether the job ever has good news.** A producer's artifact is the product (backup, restore
drill, maintenance, staleness, metrics) — `local` is correct there. A **reporter** that emits only on failure, drift
  or a stuck item must reach a room, or its silence is indistinguishable from a clean week.
- **Sweep it with a query, then classify — do not eyeball the list:**
  ```bash
  python3 - <<'PY'
  import json, glob
  for p in sorted(glob.glob('/opt/data/profiles/*/cron/jobs.json')):
      d = json.load(open(p)); jobs = d if isinstance(d, list) else (d.get('jobs') or list(d.values()))
      for j in jobs:
          if isinstance(j, dict) and j.get('enabled', True) and 'local' in str(j.get('deliver', '')).lower():
              print(p.split('/')[3], j.get('id'), j.get('name'))
  PY
  ```
- **Zero artifacts means it never ran, which is a different defect from a quiet target.** A job created while its
  room id was unverified can sit on `local` forever without ever executing a single delivery; check
  `cron/output/<id>/` for existence before concluding the rail is merely silent.
- **Changing a delivery target is a decision, not a cleanup.** List the rows with an owner for each, let the user
  choose which rooms get the noise, then change them and re-run ONE job to confirm `delivery_outcome=delivered`.

## Group Rename Propagation (Strategies → Treasury, Sep 7 2026)

When a Telegram group is renamed (the ID does not change), a full-propagation audit must verify no config/documentation still carries the old label — the gateway keeps working because delivery is by chat ID, but docs, skill notes, and prompts go stale silently. Sweep order for a group rename:
1. **Channel directory** — the gateway's `channel_directory.json` renames the main entry automatically (the `<id>:<topic>` suffixed entries keep old names; those are historical topic labels — inert, do not edit).
2. **config.yaml** — `telegram.channel_prompts` entry for the chat ID (prompt wording may still say the old name). Update the label so the agent's opening framing matches.
3. **Live cron jobs** — enable only delivery targets need the ID (unchanged); only the `prompt` text may mention the old group name. Verify NO enabled job delivers to a chat that was actually retired.
4. **Skills + memories** — grep for the old name in `skills/**` and any docs; a stale note contradicting the rename (e.g. claiming the group is "RETIRED") must be corrected or it will mislead future sessions into wrong routing.
5. **History/logs** — old-name strings inside `state/rich_sent_index.json`, conversation logs, and topic names are inert records; leave them (editing risks nothing but touches nothing useful either).

Rule: **rename keeps the chat ID** — so cron `deliver` and `routing` tables that reference the ID are still correct; only the *label/prompt* surface needs updating. This is why the rename audit is primarily a doc-prompt-skill sweep, not a delivery-target rewrite. Only when a chat is truly RETIRED (bot kicked / group deleted) do you rewrite `deliver` targets to a live chat — a rename and a retirement are different operations.

Verify a claimed rename against the live channel directory: read `channel_directory.json` and confirm the main (non-topic) entry for the ID now shows the new name; if it does and cron `deliver` still points at that ID, no delivery rewrite is needed.

## Proactive Audit Pattern

Run this audit whenever:
- Creating or updating a cron job
- Two jobs target the same group at the same time
- User asks "where did my cron output go?"
- User asks "why are these coming at the same time?"
- **A profile split / handoff just happened** (work moved to a sibling profile) — see "Dead-Job Purge After a Profile Split" below
- **User asks to review/improve the cron fleet** (e.g. "what would you change about our cron jobs?")
- **A collaborator is leaving or a group is being retired** — see "Leaver / Group-Retirement Delivery Sweep" below

## Leaver / Group-Retirement Delivery Sweep

When a person leaves the system or a Telegram group is shut down, every cron job that
mentions them by name or targets their channel must be re-examined. A name-scan alone is
insufficient: some jobs mention the person in order to **exclude** them, and a job can
send to the leaver without containing their name if its `deliver` is `origin` and the
originator was that person.

**Stop-condition definition first.** Before changing anything, decide what "involves"
means for this sweep:

- **Job belongs to the leaver** — `deliver` resolves to their DM/group, prompt data is
  theirs, or name is in the intent.
- **Job mentions the leaver to exclude them** — name appears in a prompt that says
  "ignore / do not include / skip" — **DO NOT STOP** these; they belong to someone else.
- **Job merely shares a group the leaver was in** — belongs to the group, not the person;
  re-target the group, don't delete, unless the group itself is retired.

**Procedure:**

1. **Read every active job's stored `deliver` and, for `deliver=origin`, its resolved
   `origin` field.** The `origin` record contains `chat_id`, `chat_name`, and `user_id`;
   it is the only place that shows who the job actually wakes. Do not infer from the job
   name alone.
2. **Enumerate fleet-wide targets.** For each profile, list jobs grouped by `deliver` and
   resolved origin. The leaver may have jobs in seats they do not own.
3. **Pause jobs owned by the leaver.** Prefer `pause` over `delete` unless the work is
   permanently migrated; pausing preserves the definition for reversal.
4. **Re-target jobs that should continue but landed in the leaver's DM.** Pick the
   replacement target by enumeration, not convention: look at where similar fleet-health
   or role-equivalent jobs already deliver (usually HQ for ops, the renamed equivalent
   group for content). Update `deliver` to an explicit `telegram:<id>`; do not leave it as
  `origin`.
5. **Verify every change by reading the state file back.** A `hermes cron update` success
   message is not proof of the new `deliver` value; re-read `cron/jobs.json`.
6. **Document the exact job IDs changed** and any job left for the founder's decision
   (e.g. a fleet-health report whose recipient is a policy choice, not a technical fix).

**After the immediate leaver cleanup, sweep the `origin` trap class:**

Any enabled job with `deliver=origin` is a time bomb: its audience silently follows whoever
originally created it. When that person leaves, the report continues to land in their DM or
an old chat. Resolve each `origin` to its stored `chat_id` and `user_id`; if any resolves to
a leaver or defunct group, re-target it. Then decide whether to convert **all** long-lived
`origin` jobs to explicit targets as a hygiene pass — that is the durable fix.

**Pitfall — false positives from name search:** six jobs may match the string "vanito" but
only three involve him; the other three mention him to exclude him. A naive search-and-stop
would pause the owner's own reports.

**Pitfall — assuming a group retirement breaks nothing:** if a group is shut down, verify
**every** job that ever delivered there, including `origin` jobs whose resolved origin is
that group. Even `local`/no-agent jobs may chain output to the group via `context_from`.

## A disabled job is a SILENT DECISION — give every one a verdict, and most verdicts are DELETE

**A health probe that counts disabled jobs is right to flag them, and wrong to leave the fix at "re-enable or
not".** Measured: four disabled jobs on one seat, of which **three were finished** — not broken:

| shape | evidence it is finished | action |
|---|---|---|
| **OBSOLETE** — it watched for a condition that has since resolved | the watched lane is alive *measured today* (quota restored, service back) | **delete** |
| **COMPLETED one-shot** | `repeat: {times: 1, completed: 1}` | **delete** — finished is not paused |
| **DUPLICATE of a step inside another job** | the same script runs in the bigger job's bundle (`grep` the bundle for the filename) | **delete** the standalone job |
| **DELIBERATE, still needed** | a live purpose, but too loud (e.g. 3×/day wake probes) | **keep, and reduce the frequency** rather than leaving it off |

- **Run each disabled job once before judging it.** A silence-gated watch exits 0 and prints nothing when
  healthy, so "it produced no output" is not evidence either way — read its own header for what silence means,
  then decide from the world it watches.
- **"Disabled forever" is how a fleet accumulates the noise that hides a real finding.** A red probe whose only
  remedy is a threshold change was never a finding; a job that completed its purpose belongs deleted, with the
  reason in the record.
- **Record the verdict, not just the action**, and name what remains open if anything does — *"kept at 1×/day
  because the wake path still matters"* is a decision a later reader can revisit.

## Dead-Job Purge After a Profile Split (Aug 11, 2026)

When work is handed to a sibling profile (gentech → treasury/gizmo) or a job is superseded, the old profile keeps orphaned paused/disabled jobs. They don't run, but they bloat every `cronjob list`, clutter health checks, and get counted in "how many jobs" audits.

**Signature of a migrated job:** `paused_at` set + `paused_reason` reads "migrated to <profile> (swap <date>)", or a duplicate of a job now owned by another profile.

**Signature of a dead delivery:** `last_delivery_error` contains "bot was kicked from the supergroup chat" — the bot left that group but the job still targets it. The job (and the old group's jobs) can be removed if ownership moved elsewhere.

**Purge workflow:**
1. `cronjob action=list` — identify paused/disabled jobs whose replacement lives in another profile, plus completed one-shot jobs and duplicate trackers.
2. Confirm each is truly dead (not a job you want back). Keep intentionally-paused jobs that will resume.
3. `cronjob action=remove job_id=<id>` for each.
4. Re-list to verify the count dropped and no live job was caught.

**Also check for provider-switch collisions** during a fleet review: multiple mechanisms mutating the fleet's provider/model (a standalone `provider-auto-switch` cron + the canonical `cron-provider-sync.py` + a rate-limit auto-escalator + leftover one-shot "Fleet Switch" scripts) can clobber each other and flip jobs mid-day. Consolidate to ONE authority — the Auto-Sync — and pause/remove the redundant ones.

## A monitor must not be the only thing that would report its own failure

A health/reporting job that delivers through the same channel it monitors is not a monitor — it is a diary.
Measured shape: a self-reflection job spent three consecutive nights failing to send into a chat that no
longer existed (`Chat not found`), logged on every run, while its own status read `completed`. **The single
instrument that would have escalated the failure was the job whose delivery was dead.**

Four always-on rules:

1. **A monitoring/reporting job gets an EXPLICIT target, never `origin`.** `origin` is captured at creation
   and can resolve to a room the bot has since left; the failure appears at send time, after `completed`.
2. **Ask of every monitor: if this job's delivery dies, what else tells anyone?** If the answer is "nothing",
   the monitor is unbacked — give it a second rail or state plainly that it has one.
3. **A delivery probe must read the RUN, not the config.** `0 jobs with no delivery target` is a config
   assertion; a target that is **SET** is not a target that **WORKS**.
4. **A rail that is declared but unconfigured must say so and exit non-zero** — never silently fall back to
   the channel it was meant to supplement.

Rails enumeration, the per-job `delivery_outcome` probe, and the honest-config-only wording:
`references/monitor-independent-delivery-rails.md`.

## A destination that cannot RECEIVE must be PARKED, and the closure you demand must match the NOTE'S TYPE

Escalation instruments measure **silence**, and silence is identical whether the recipient is slow or
unreachable. Two shapes of that blindness cost real time:

**1 · A target with no mailbox.** A seat can be live in the fleet and still have no reader here: no profile
directory, no gateway, no registered peer — vault sync is the only carrier, so a note reaches it when a human
boots the machine. An SLA timer counts every silent day as a fault, so it escalates at a seat that cannot
answer and buries the one item that is actually actionable.

- **Keep an explicit no-reader set, next to the transport-blocked set**, and give those rows their own band
  (`NO_READER`) with a **gate** and a **release condition** — *"no profile and no peer here; vault sync is the
  only carrier; releases when the seat boots and replies, or the lane is retired."* Exclude them from the
  "owe a reply" count.
- **Prove the park lifts itself:** empty the set, re-run, and confirm the rows return to ESCALATE. A park you
  have never watched release will outlive the reason for it.
- **Re-derive the set by measurement, never by memory:** `ls -d <profiles>/<seat>` plus `hermes peer list`.
  A seat can gain a mailbox (or lose one) long after the convention was written down.

**2 · Demand the closure the note can actually produce.** A closure vocabulary is per note type: a *briefing*
asks for agreement, but an *order* ("finish, log, verify, then ACK") has nothing to agree TO — its closure is
the receipt the receiver writes back. An instrument that only accepts `## Agreement` reports every directive
as unanswered, and a `+N` jump in that count reads to the user as N new unanswered items.

- **Accept the receipt as a closure for DIRECTIVES only.** Test the note's own words: an order contains a
  required action (`must|finish|write|run|reply|ack|send|stop|hold|wait`); a briefing does not. A briefing with a
  stray receipt must still be flagged, or the check stops asking its question.
- **Close a record addressed to nobody.** A daily log entry asks nothing; it needs a `## Supersede`, not an
  agreement block, or it counts as debt forever.
- **A false accusation trains the reader to skip the section** — which is the same damage as a monitor nobody
  reads, and it costs the one real item its visibility.

## `deliver` must name a PLATFORM — a bare chat id resolves to nothing

**The target format is `telegram:<chat_id>`, never the chat id alone.** A job carrying `deliver = "-100…"`
schedules, runs, exits 0, and writes its output — then the scheduler cannot resolve a destination:

```
WARNING cron.scheduler: no delivery target resolved for deliver=<telegram-group-id>
executions.db → status=completed · delivery_outcome=failed
```

**Read `delivery_outcome` from `cron/executions.db`, not `jobs.json.last_status`.** The two disagree: the
summary field can hold a failure from days ago while later runs succeed, and it can hold `completed` while
every delivery fails. The run table is the record:

```sql
select started_at, status, delivery_outcome, error
from executions where job_id='<id>' order by rowid desc limit 5;
```

`status=completed · delivery_outcome=failed` is a **blind rail** — the work happened and nobody received it.
Fix the format, then re-run and confirm the newest row reads `delivery_outcome=delivered`. Sweep the fleet for
bare ids in one pass: any enabled job whose `deliver` is neither `origin`, `local`, nor contains `:`.

## Driving another profile's cron from the CLI

`HERMES_PROFILE` is read at config load but does **not** switch the cron resolver — `hermes cron list` keeps
reporting the active profile and `cron edit <id>` answers `Job not found` for a job that plainly exists.
Set **`HERMES_HOME=/opt/data/profiles/<seat>`** instead; the banner then names that profile and edits resolve.

## Editing a schedule does not recompute `next_run_at`

After `hermes cron edit <id> --schedule …`, the stored `next_run_at` can remain a date **in the past**, which
`cron list` renders as `Overdue: … (Nd ago — the job has not fired; is the scheduler running?)` — a false
alarm that reads like a dead scheduler. **Set the same schedule a second time** and it recomputes. Check the
field after every schedule change instead of trusting the edit's success line.

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `deliver` is a bare chat id | Runs complete, `delivery_outcome: failed`, "no delivery target resolved" | Always `telegram:<id>` |
| Reading `last_status` as the delivery verdict | A live blind rail dismissed as "stale record" | Read `executions.db.delivery_outcome` |
| Schedule edited, `next_run_at` stale | List shows the job overdue by days | Re-apply the same schedule once |
| `HERMES_PROFILE` used to target a seat | `Job not found` for a job that exists | `HERMES_HOME=<profile dir>` |
| Rows escalate every cycle at a seat that cannot read | A real item is buried under the parked ones | Explicit no-reader set + `NO_READER` band with gate and release; falsify by emptying the set |
| A closure vocabulary that ignores the note's TYPE | Every directive (`must…`, `finish…`) reported as "nobody agreed", forever | Accept `## Receipt` for directives; keep `## Agreement` required for briefings |
| Time collision | Two messages arrive simultaneously in one group | Offset one by 15+ min |
| Unclear job name | User asks "what's this?" | Prefix with `[User]` |
| Wrong group delivery | Vanito content in HQ | Set explicit `telegram:-10038...` target |
| Empty output | Job shows "ok" but no message | Check script output, maybe `no_agent` mode |
| Hardcoded old chat ID | Job delivers to defunct group | Update `deliver:` to current target |
| Stale stagger | Both jobs at same time after timezone change | Re-audit after DST or schedule overhaul |
| Overnight chat delivery | Job fires 3-7am ET into a Telegram group | `deliver=local`, or shift schedule to waking hours (see Quiet Hours Discipline) |
| Schedule format rejected on update | `Invalid schedule 'once at 2026-09-30 13:00'` | `cronjob update` accepts one-shot timestamps only as ISO — `2026-09-30T13:00:00` — not the "once at ..." prose form some listings show |
| `deliver=origin` with an invented destination | Delivery lands where you hoped, not where the data says | The origin JSON is the sender + room, not a reply-to. If it carries no destination, keep the route the job already has and record the gap — do not add one. |
| `deliver=origin` on a long-lived job | Report lands in a leaver's DM or defunct chat after personnel/group changes | Convert to explicit `telegram:<id>`; see Leaver / Group-Retirement Delivery Sweep |
| Name-only leaver search | Pausing jobs that merely mention the leaver to exclude them | Define "involves" as resolved `deliver`/`origin`, not string match |

## ⚠️ `completed` IS NOT `delivered` — the run record cannot answer the question you are asking

**The durable run record (`hermes cron runs <job_id>`) carries a `status` per attempt — `completed`,
`failed` — and NOTHING about whether a message ever reached a chat.** So every run can read
`completed` while the human received nothing, and no amount of reading the dashboard will reveal it.

**This is the failure to check for when a user says "the job ran but I didn't see it":** the script
executed, wrote its output file, and the delivery leg failed silently. Both statements are true.

**Diagnostic order — do not skip to "the job didn't run":**

1. **Prove it ran.** `hermes cron runs <job_id>` → confirm a `completed` attempt at the expected
timestamp. A timestamp that matches the schedule means the scheduler is not the problem.
2. **Prove it produced output.** `cron/output/<job_id>/<timestamp>.md` — the file existing means the
   script ran end to end. Check its byte count; a 0-byte or header-only file is a script failure that
   merely looks like a delivery failure.
3. **Check the payload is deliverable.** Size against the platform limit, and specifically whether the
   script emits a `MEDIA:` line plus audio/video — a media token is the most common thing that breaks
   an otherwise-fine text delivery.
4. **Reproduce it live.** `hermes cron run <job_id>` triggers the job on the next tick with real
   delivery. This is the only step that tests the actual delivery path rather than the run record.
5. **Only then** look at gateway logs for the exact timestamp.

**The rule:** when you report a cron job as working, name which of **ran / produced / delivered** you
actually measured. "Completed" answers only the first. A job whose delivery has never been observed
arriving is a job whose delivery is unverified — say so rather than quoting the run status.

**Corollary for recurring reports:** a weekly or monthly job that silently fails delivery costs a full
cycle before anyone notices, and the next run overwrites the evidence. Trigger a new recurring report
job once by hand immediately after creating it — the first real scheduled run is too late to be the
first test.

## Quick Reference

**List all jobs clean:**
```bash
hermes cron list | grep -E "name:|schedule:|deliver:|last_status:"
```

**Find time collisions:**
```bash
hermes cron list | grep -B 5 "schedule:" | grep -E "name:|schedule:"
```

**Safe defaults for GenTech:**
- Jordan → HQ or topic group
- Vanito → Entertainment
- Stagger like-jobs by 15+ min
- Name with `[User]` prefix

## Reference: Leaver Delivery Sweep Script

`references/leaver-delivery-sweep-script.py` reads every profile's `cron/jobs.json`, resolves
`deliver=origin` to its stored `origin` (chat_id, user_id), and reports enabled jobs whose
resolved target or prompt/intent points at a leaver or retired group. It deliberately
ignores name matches that appear inside exclusion phrases ("not", "exclude", "ignore", "skip")
because those jobs usually belong to someone else. Run it dry-run first, then act on the
listed job IDs explicitly. It is a reader, not a writer.

## Related Documentation

- Hermes docs: `https://hermes-agent.nousresearch.com/docs/cron-jobs`
- Topic routing: `routing` skill
- Single-agent multi-channel: `single-agent-multi-channel` skill   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `single-agent-multi-channel` exists on this seat -->

## Quiet Hours Discipline (Jordan, Sep 1 2026)
Fleet-wide quiet hours = **3–7am ET** (Jordan asleep). Jobs may RUN overnight (backup, sweeps, sync — silence is fine), but NO chat deliveries may land in that window:
- Recurring jobs firing 03:00–06:59 ET that post to chats → change `deliver=local`, or re-anchor the schedule to waking hours. `deliver=local` + `context_from` chaining keeps data flowing to the PA/overnight scanners with zero human noise.
- One-shot reminders created overnight (e.g. "fires 09:00 UTC = 5am ET") → re-anchor to waking hours (13:00+ UTC).
- Per-agent bot-chat wakers (`bot-chat:<agent>`) → constrain cron hours, e.g. `*/10 11-22 * * *` UTC.
- Fleet-wide directives (quiet hours, protocol changes) → write ONE dated handoff note to every agent's `INBOX/<group>/` lane in the vault (single write, all agents' wake triggers pick it up) instead of messaging N groups.
- Audit pattern: list all jobs, flag any with `deliver` targeting origin/telegram AND a cron hour in 07:00–10:59 UTC (03:00–06:59 ET) or `schedule` hitting `3,4,5,6` UTC hours; fix each (deliver=local or shift schedule). Re-audit after any fleet change — new jobs drift into overnight slots.

## Intentional Pause Naming Convention

When pausing a cron job for a known reason (vacation, market lull, seasonal break), rename it with a `[Reason]` prefix so the intent is clear at a glance:

- `[Vacation] Portfolio Health Check` — paused for trip, will resume on return
- `[Seasonal] Holiday Deal Scanner` — paused until next holiday season
- `[Deprecated] Old Price Monitor` — replaced by new version

This prevents confusion between "paused intentionally" and "paused because it broke." To resume, just rename the job back: remove the `[Reason]` prefix and unpause:

```bash
cronjob action=update job_id=<id> name="Portfolio Health Check"
cronjob action=resume job_id=<id>
```

## Related Documentation

- Hermes docs: `https://hermes-agent.nousresearch.com/docs/cron-jobs`
- Topic routing: `routing` skill
- Single-agent multi-channel: `single-agent-multi-channel` skill

## Learned on gentech-treasury (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

| Internal maintenance | `local` | No delivery needed |
## ⚠️ Four rungs: ran → produced → handed off → **received**
The section above stops at "completed is not delivered". One rung remains, and it is the only one the operator
cares about: **`delivery_outcome: delivered` is still the sender's word.** Measured — three jobs each recorded
`completed` *and* `delivered` in one day while the user had seen none of them and the destination held no artifact
from that day. **A job is not verified until you have opened the thing it was supposed to leave behind**; when the
artifact is missing and the flag says delivered, report *"delivered per the record, absent at the destination"*
and investigate the route. Four-rung table and the ledger rows: `references/delivery-proof-from-run-record.md`.
## A job that waits on another job's output should BE the same job
**A temporal handoff is an unenforced dependency** — two entries ten minutes apart linked by nothing but the clock.
Tells: a `for attempt in $(seq 1 15); do … sleep 60; done` loop polling for a sibling's file; a header admitting it
refuses to act when the input is absent; a comment saying a previous merge removed exactly this.
**Fix by ordering inside one script, not by tightening the schedule.** Each section keeps its own loud failure line
so one broken step is visible without aborting the rest. **This pattern re-appears after being fixed once** — new
needs look like new schedule entries. For every job ask *what file does this read, and who writes it*: if the writer
is a sibling job, they are one job.
**Consolidation hygiene:** read both scripts before editing (the absorbed one may hold a bounded wait and a clean
refusal worth keeping) → **run the merged script end to end** and confirm each section appears in order, since a
syntax check is not a run → remove the retired ids and **re-read `cron/jobs.json`** (the `Removed job:` line is a
message, not proof) → re-read each survivor's stored `timezone` and `next_run_at` and confirm the next run is the
slot you intended in the user's local zone.

## Learned on arthur (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

| Internal maintenance | `local` | No delivery needed |
| Manual job run used as a preview | A debugging loop posts contradictory reds into the user's group | Edit + run the script directly; fire the job once, at the end |
## Debugging a monitor: run the SCRIPT, fire the JOB once
**A manual job run is a real delivery — it does not preview.** It posts to the job's configured
destination, and its async completion comes back as its own message. So iterating on a monitor by
firing the job turns a debugging loop into a stream of contradictory statuses in the user's room.
Measured: four consecutive manual runs of one self-reflection job posted `4/5`, `4/5`, `5/5` (from a
weaker fallback source) and `5/5` into a working group inside four minutes — and the user asked what
was going on before the last one landed. Nothing was wrong by then; the channel said otherwise.
- **Edit, then run the script directly.** `python3 profiles/<seat>/scripts/<job>.{py,sh}` exercises the
  code path and delivers nothing. Only the job fires the delivery leg.
- **Fire the job ONCE, at the end, as the proof.** That is the only run whose `delivery_outcome` you
  cite, and it should be the first state the user sees — not the fifth.
- **Announce that a fix may take several attempts BEFORE the first one**, so a stray red reads as work
  in progress rather than a live fault. Silence plus a red message is the worst combination.
- **Reconcile the out-of-order arrivals in the final message.** Name which run counts and which are
  noise, because the channel's order is not the order you ran them in, and the user cannot tell.

