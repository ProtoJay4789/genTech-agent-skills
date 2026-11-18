# The quiet-hours gate

One wrapper that stops routine job output reaching a human overnight while leaving failures loud.

## The decision table

| Exit | Output | Inside window | Result |
|---|---|---|---|
| `0` | routine report | yes | **silent** |
| `0` | routine report | no | delivered |
| `0` | carries an alert marker (🔴 / REFUSED / FAILED) | yes | **delivered** — the code lied |
| `1` | failure | yes | **delivered**, exit preserved |
| `2` | could not run / refused | yes | **delivered**, exit preserved |
| any | any | window unparseable | **exit 2** — never pass silently |

**A gate that fails open is indistinguishable from a night with no problems.** A broken window spec is an
instrument that cannot read, and rule 5 of the standard applies to it: say so, do not go quiet.

## The wrapper

```bash
#!/usr/bin/env bash
# quiet-gate.sh — wrap a job; do not edit the job's own script.
set -uo pipefail
MIRROR="${1:?script to run}"; shift
[ -f "$MIRROR" ] || { echo "🔴 quiet-gate: ${MIRROR} is missing — the job did NOT run" >&2; exit 2; }
exec python3 /opt/data/scripts/quiet-hours.py --policy alerts-only -- bash "$MIRROR" "$@"
```

Point the job at it with the CLI, never by editing `jobs.json`:

```bash
hermes cron edit <job id> --script quiet-gate.sh
hermes cron edit <job id> --help    # --script, --deliver, --failure-deliver, --schedule …
```

## Time must be computed, not offset

```python
from zoneinfo import ZoneInfo
from datetime import datetime
now = datetime.now(ZoneInfo("America/New_York"))
```

- **Never hardcode `UTC-5`.** A fixed offset is wrong for half the year and moves the boundary by an hour
  without anyone touching the job.
- Windows **wrap midnight** (`22:00-07:00`): `now >= start or now < end`. An `and` here silently produces an
  empty window that never suppresses anything.
- Accept a `--now` override so the behaviour can be tested at any hour without waiting for 03:40.

## The fixtures that prove it (all four must pass)

```bash
G="python3 /opt/data/scripts/quiet-hours.py"
# 1 suppress a routine success at night
$G --now 2026-01-15T03:40:00 -- sh -c 'echo "16 files pushed"'          # expect: no output
# 2 a failure still speaks, and keeps its code
$G --now 2026-01-15T03:40:00 -- sh -c 'echo boom; exit 3'; echo $?      # expect: boom, 3
# 3 daytime is unchanged
$G --now 2026-01-15T14:40:00 -- sh -c 'echo "16 files pushed"'          # expect: the line
# 4 boundaries, one minute either side
for t in 21:59 22:00 06:59 07:00; do $G --now 2026-01-15T$t:00 -- sh -c 'echo X'; done
# expect: AWAKE / QUIET / QUIET / AWAKE
# 5 a broken window fails closed
$G --window nonsense -- echo hi; echo $?                                # expect: 2, no output
# 6 the marker fallback — rc 0 but an explicit failure in the text
$G --now 2026-01-15T03:40:00 -- sh -c 'echo "🔴 PUSH FAILED"; exit 0'    # expect: the line
```

## Gate, reschedule, or leave it alone — decide from a measurement

**Gating a report does not quiet it, it deletes it.** The gate suppresses stdout and the run is over; a job on a
daily or weekly cadence has no second chance to carry the message that night. Before choosing a disposition, run
the candidate once on clean state and record two numbers:

```bash
out=$(timeout 240 bash profiles/<seat>/scripts/<script>.sh 2>&1); rc=$?
echo "rc=$rc bytes=${#out}"   # 0 bytes -> already compliant; >0 -> it speaks on a clean run
```

| clean-run result | disposition |
|---|---|
| `rc=0`, `0 bytes` | **leave it** — it already obeys the silence rule; gating it would suppress a real alert later |
| `rc=0`, `>0 bytes`, content is a standing report | **reschedule** into the awake window (`hermes cron edit <id> --schedule "…"`) |
| `rc=0`, `>0 bytes`, content is a genuine finding | **reschedule**, not gate — a finding is still a report at 03:00 |
| the job must run overnight (backup, mirror, sync, watchdog) | **gate** it |

**Keep the evidence.** A register of `script → clean_bytes / measured_at / disposition` lets an audit tell
"measured silent" from "called itself silent". **A job's own name is a claim** (`silent unless hot`, `silent when
flat`) — treat it as `SILENT-DECLARED` and say so, never as evidence.

## Auditing schedules: the window and the cron expression live in different clocks

A cron `expr` is UTC. The window is the human's timezone. **Compute the union of both US offsets** when deciding
whether a job can land inside the window, or a `30 3 * * *` job is silent all winter and wakes them in July.

```python
QUIET_START, QUIET_END = 23, 7          # ET
for off in (-5, -4):                   # EST, EDT — flag BOTH
    for h in range(24):
        et = (h + off) % 24
        if et >= QUIET_START or et < QUIET_END:
            flagged.add(h)
```

Over-reporting by one hour twice a year is the correct direction to be wrong; under-reporting wakes someone.

## Pitfalls

- **Suppressing the *success* message is the win, not suppressing the job.** The job still runs, still writes,
  still fails loudly. A gate that stops the work to stop the noise has broken the thing it was protecting.
- **A `silence-all` policy will one day swallow a backup failure.** If you offer it, keep the alert-marker
  check ahead of the policy branch so no policy can mute a marker.
- **Do not add a cron to fix a cron's noise.** Regenerating state on a schedule to keep a page fresh is one more
  job to monitor; ride an existing job that already runs (see the `[state]` → `[current]` bundle pattern) and
  you get freshness with no new failure surface.
- **A suppressed run must still be recorded.** Cron writes `Status: silent (empty output)` — that record is how
  you prove afterwards that the job ran and chose to be quiet, rather than never firing.
