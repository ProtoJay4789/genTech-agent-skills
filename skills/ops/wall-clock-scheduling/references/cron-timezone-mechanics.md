# Cron timezone mechanics — why a right-looking expression fires at the wrong hour

Depth for the rule in SKILL.md: **a job with no `timezone` field is evaluated in the profile's LOCAL zone.**
This file carries the measurement, the traps, and the whole-profile normalisation procedure.

## The measured defect

A job at `30 11,13,15,17,19,21,23,1,2 * * *` with **no `timezone` key** fired at:

```
11:30am 1:30pm 3:30pm 5:30pm 7:30pm 9:30pm 11:30pm 1:30am 2:30am ET
                                            └──── 3 overnight ────┘
```

The hours had been chosen as **UTC** slots for 6:30am–9:30pm ET; nothing converted them. The literal hour
numbers were read as Eastern, so every run was five hours late and three of nine landed overnight. It had been
running that way for days.

## The trap that hid it: a UTC-stamping script

The monitor's own output header read `06:30 UTC` — **a valid slot for the expression** — while the scheduler had
fired it at `01:30 ET`. Two consequences:

- **A script that formats its own timestamps in UTC makes a local-time cron look correct indefinitely.** Anyone
  auditing from the delivered text sees a plausible schedule.
- **It inverts the reading of `next_run_at`.** A `-05:00` offset there is **truthful evidence of local
  evaluation**, not stale metadata. A note claiming those offsets are stale cosmetic artefacts will keep the bug
  alive, because the one field that proves it is the one being explained away.

**Read the execution log, not the delivered text:**

```bash
python3 -c "import sqlite3;c=sqlite3.connect('<profile>/cron/executions.db');print([r[0] for r in c.execute(\"select started_at from executions where job_id='<id>' order by rowid desc limit 8\")])"
```

- **`cron/output/` filename mtimes are UTC; `executions.db.started_at` carries the real offset.** When they
  disagree, believe the database — the filename is written by the runner, the header by the script.

## The fix — both halves are required

Author the hours **in the zone you pin**, then pin it:

```bash
hermes cron edit <id> --schedule '30 6,8,10,12,14,16,18,20,21 * * *' --timezone America/New_York
# verify the FIELD exists; a right-looking expression proves nothing
python3 -c "import json;[print(j.get('timezone'),(j.get('schedule') or {}).get('expr'),j.get('next_run_at')) for j in (json.load(open('<profile>/cron/jobs.json')).get('jobs') or []) if j.get('id')=='<id>']"
```

Pinning `America/New_York` while writing UTC hours recreates the bug with extra steps.

## Normalising a whole profile without moving a single fire time

**Pinning the zone is the second step, not the first. Record every `next_run_at`, pin, then diff as instants —
and restore any job that moved.**

**An absent `timezone` does not mean one thing.** Some jobs are evaluated locally; others are UTC-anchored (their
`next_run_at` carries `+00:00`, typically because a DST-alignment job manages their anchor). Bulk-pinning
`America/New_York` fixes the first group and **shifts the second by five hours.** Measured on a 15-job profile:
**8 unchanged, 7 moved +5h** — and the 7 included the weekly council meeting.

```bash
# 1. capture BEFORE — id -> next_run_at for every job lacking a timezone
python3 - <<'PY'
import json
d=json.load(open('<profile>/cron/jobs.json'))
j=d if isinstance(d,list) else (d.get('jobs') or list(d.values()))
if isinstance(j,dict): j=list(j.values())
print(json.dumps({x['id']:x.get('next_run_at') for x in j if isinstance(x,dict)
                  and not (x.get('timezone') or (x.get('schedule') or {}).get('timezone'))}, indent=1))
PY

# 2. pin the zone, expression UNCHANGED
hermes cron edit <id> --timezone America/New_York

# 3. diff as instants: datetime.fromisoformat(s).astimezone(timezone.utc)
#    |delta| < 1s  -> it was local. Done; behaviour preserved.
#    moved (+/-5h) -> it was UTC-anchored. Restore it:
hermes cron edit <id> --timezone UTC
```

- **Require zero drift before reporting success.** "All zones explicit" is worthless if a fire time moved; the
  deliverable is *explicitness at identical instants*, not a new schedule.
- **`--timezone` alone changes the zone and leaves the expression alone** — that is what makes the pass safe.
  Never re-supply `--schedule` during a normalisation sweep; a typo there becomes a second, silent change.
- **A moved job is information, not an error to suppress.** The restored UTC jobs are the ones to inspect
  afterwards: a UTC-anchored *human* meeting drifts an hour twice a year, so one intended for 17:40 ET quietly
  becomes 16:40 ET when DST ends. Surface those and let the owner pick the anchor.

## Auditing overnight hours across the fleet

**Convert each job's hour set through that job's OWN zone.** A raw-keyword scan that ignores `timezone` flags a
UTC job at the wrong hours and can miss the real one.

```python
from datetime import datetime
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
# for each job: spread its hour field over a fixed date in the job's zone, then astimezone(ET).hour
```

Run it after the fix and require zero violations. Distinguish the three outcomes:

| shape | action |
|---|---|
| a **report** firing overnight | move it into the waking window; compress cadence rather than stretching into the night |
| a **liveness probe** (stop watchdog, position guard) | **leave it alone** — silent by design, and its value is coverage while nobody watches |
| a cadence the **user chose** (their own "every 4 hours") | recommend, never edit; overriding it is not your call |

## Applying the same audit to other profiles

Read-only across every seat — never edit another profile's `cron/jobs.json`:

```bash
for p in /opt/data/profiles/*/cron/jobs.json; do
  python3 - "$p" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); j=d if isinstance(d,list) else (d.get('jobs') or list(d.values()))
if isinstance(j,dict): j=list(j.values())
en=[x for x in j if isinstance(x,dict) and x.get('enabled',True) and (x.get('schedule') or {}).get('expr')]
miss=[x for x in en if not (x.get('timezone') or (x.get('schedule') or {}).get('timezone'))]
print(sys.argv[1].split('/profiles/')[1].split('/')[0], 'enabled:', len(en), 'missing tz:', len(miss))
PY
done
```

Report the counts per seat and hand each owning seat the procedure — the fix belongs to the seat that owns the
jobs. Fleet-wide, this is worth checking whenever a monitor surprises the user at an odd hour: one seat's
complaint is usually a class, not a one-off.
