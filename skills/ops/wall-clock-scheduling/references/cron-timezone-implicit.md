# The implicit-timezone cron defect — procedure and quirks

Companion to `wall-clock-scheduling` §1.5. Everything here is the depth that is only needed when you are
actually auditing or repairing a fleet's schedules.

## The defect in one line

A cron job whose schedule block has **no `timezone` key** has its expression evaluated in the **profile's local
zone**, not UTC. Hours authored as UTC therefore fire **five hours late** (at UTC-5) and the late end of a daytime
schedule lands in the middle of the night.

## Measure the split before touching anything

```bash
python3 - <<'PY'
import json, collections
jobs = json.load(open('/opt/data/profiles/<seat>/cron/jobs.json'))
jobs = jobs if isinstance(jobs, list) else jobs['jobs']
en = [j for j in jobs if j.get('enabled')]
def tz(j): return j.get('timezone') or j.get('tz') or (j.get('schedule') or {}).get('timezone')
print('enabled', len(en), 'missing tz', sum(1 for j in en if not tz(j)))
print(collections.Counter((j.get('next_run_at') or '')[-6:] for j in en))
PY
```

Observed on one seat: `47 enabled, missing tz 43` with `{'-05:00': 40, '+00:00': 7}`. **Two evaluation zones
behind one absent field** — and that split is the reason a bulk pin is unsafe.

## Pin by the offset (movers are zero by construction)

```python
zone = 'UTC' if t.utcoffset().total_seconds() == 0 else 'America/New_York'
```

1. Snapshot every `next_run_at` to a file outside `jobs.json`.
2. `hermes cron edit <id> --timezone <zone>` per job, expression unchanged.
3. Re-read and compare **instants** (`datetime.fromisoformat(...).timestamp()`), never strings.
4. Re-diff against the snapshot as an independent check, and report `0 missing, 0 drift`.

A script that prints its own success is not verification. The independent re-diff of the *file* against the
*snapshot* is.

## Durability: edit persists, pause does not

- The scheduler rewrites `jobs.json` from memory, so `hermes cron pause` has been observed not to hold (a paused
  job fired ~40 min later). Delete a duplicate rather than pausing it.
- `hermes cron edit` does persist — but prove it: re-read the file **after a ticker heartbeat advances**
  (`cat <profile>/cron/ticker_heartbeat` twice, ~60s apart), and confirm the zones are still present with the
  file mtime unchanged.

## Why it hides: the script stamps its own output in UTC

A monitor that prints `2026-11-19 06:30 UTC` in its header, while the scheduler fired it at **01:30 ET**, shows a
perfectly valid slot for its expression. **A script that formats its own timestamps in UTC makes a local-time
cron look correct indefinitely.**

Verify from the database instead:

```sql
select job_id, started_at, status from executions order by rowid desc limit 8;
-- started_at carries the real offset; the delivered text does not
```

## Second-order: a UTC anchor drifts an hour at DST

A UTC-anchored job keeps its UTC hours and slides an hour in local time at every switch. On one fleet this put a
**weekly council meeting recorded as 17:40 ET at 16:40 ET**, silently, with the ordering of the three related jobs
(16:00 → 16:40 → 16:50) intact — so nothing looked broken.

- Sweep job **names** for `am|pm|UTC|ET` and compare with the delivered local time; that is how the liar is found
  in seconds rather than by reading 47 schedules.
- Fix a named-time job by pinning local (`30 15 * * 0` + `America/New_York`), not by re-anchoring UTC.
- A monitor drifting an hour is a curiosity; a **meeting** drifting an hour is a person standing alone in a room.

## After the pin: an audit that reads the expression becomes the new defect

Once jobs carry a zone, the failure flips sides. A checker that parses the hour field and ignores `timezone`
double-shifts every pinned job and reports correct schedules as violations.

| live job | fires (from `next_run_at`) | the expr-reader's claim |
|---|---|---|
| `30 7,9,11,13,15,17,19` + America/New_York | 07:30 ET = 12:30Z | "07 UTC = 3am ET" |
| `5 11 * * *` + America/New_York | 11:05 ET = 16:05Z | "11:05 UTC = 6:05am ET" |

- **Diff instants, never strings.** `datetime.fromisoformat(a).timestamp()` on the before/after snapshot is the
  only comparison that catches a conversion error; string diffs agree with themselves.
- **Convert the hours OR pin the zone — never both, never neither.** Both = every job moves by the offset;
  neither = the job stays unpinned and drifts at DST. A pass that converted list hours with the wrong offset
  (−6 where the zone is −5) moved a whole schedule an hour early and dropped two runs back inside a quiet
  window that had just been cleared.
- **A realigner whose premise died is worse than no realigner.** One kept a registry of expressions "as UTC"
  under the docstring *"this build has NO per-job timezone field"*; after the field arrived it rewrote zoned
  jobs from stale numbers and printed `In step. Nothing to change.` — it compares live expressions to its own
  registry, so *unchanged* read as *correct*. Empty the registry, make the tool silent when it has no subject,
  pause the job, and record why in the file.
- **Two windows in play** (e.g. 23:00–07:00 ET and 01:00–11:59 UTC, three hours apart): compute both fire maps,
  move the runs that cross either, then ask which is the standard. Satisfying the stricter one silently is
  fine; satisfying neither and reporting success is not.
- **A stale `schedule_display` is a liar, and re-issuing the same expr fixes it.** `hermes cron edit <id>
  --schedule "<same expr>"` regenerates the display; hand-editing the field does not survive the scheduler.

## After the pin: re-read the local fire map

Explicitness exposes intent; it does not fix it. Print every remaining run for the next day **in the user's zone**
and check that overnight is infrastructure only (sync, backups, hygiene, probes) while every **report** sits in
the working window. Move the ones that are wrong for a human and declare each move.
