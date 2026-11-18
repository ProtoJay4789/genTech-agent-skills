# Quiet hours and the overnight state handoff

The consumer job (the PA / brief) is the fleet's one voice — which puts it on both ends of the quiet
window: the last delivery before quiet, and the first one after. This file is the wiring in between.

## The window (this user's standing instruction)

**23:00–06:30 ET = 03:00–10:30 UTC, half-open `[03:00, 10:30)`.** An earlier standard said 3–7am ET;
the window is now the whole night. Treat any job firing in 03:00–10:30 UTC as needing review, and put
the wake slot at the window's end so the wake delivery is not itself flagged as a violation.

## Three things must be quiet — silence on one is not silence

1. **The RUN continues.** Overnight is when maintenance belongs: backups, restore drills, vault
   hygiene, memory measurement, drift checks. Never move maintenance into the day to satisfy a
   delivery rule — the rule governs who gets woken, not what may run.
2. **The DELIVERY is silent** — `deliver=local` on every in-window job.
3. **The FAILURE notice is silent too, and `deliver=local` is NOT enough.** With `failure_deliver`
   unset, engine failure/interruption notices follow `deliver`, not your intent — so a job that is
   "silent on success, speaks on failure" still pings at 12:30am. Set **both** to local. That is only
   acceptable when the wake job reads that job's verdict and reports it; otherwise you have converted
   a loud failure into a silent one, which is worse than the noise.

## The handoff: state files, then ONE voice

- Each overnight job writes a **state file** (JSON/text at a known path) and delivers nowhere.
- The **first job after the window** reads those files and reports once, so nothing found at 3am is
  lost — it waits until the human is up instead of waking them.
- **Freshness-check, do not just parse.** An unchanged verdict file means the job did NOT run: compare
  its mtime to the schedule's period (a nightly backup's verify log older than ~28h = no backup last
  night) and report the miss as its own finding. A file that still says PASS may be last week's.
- **Name the owner.** A silenced alert still needs an owning seat by breakfast; pasting the error text
  is not a report.
- Keep the state path stable and documented in the consumer's prompt; have the producer remove or
  replace its file when clean, so "no file" means "nothing to say".

## Verify, do not eyeball

`scripts/quiet-window-check.py` expands every enabled job's cron expression across all profiles,
computes the next 24h of fires, and flags (i) non-`local` deliveries inside the window and (ii) in-
window jobs that are `local` but whose unset `failure_deliver` can still speak. Run it after any cron
change — new jobs drift into overnight slots silently.

## Editing a job by hand (schedule / prompt surgery)

`profiles/<profile>/cron/jobs.json` is hand-editable, which is worth doing when only one line of a
long prompt changes and re-sending the whole prompt would be wasteful. Facts that matter:

- the entry key is **`id`**, not `job_id` (the API answers with `job_id`; the file stores `id`);
- a schedule is stored as `{"kind": "cron", "expr": "...", "display": "..."}` plus a mirrored
  `schedule_display`, and `next_run_at` is recomputed by the gateway;
- the gateway **re-reads the file each tick**, so the edit is picked up — but prove it rather than
  assume: note `.tick.lock`'s mtime, wait for one tick, re-read the file. An edit that survives a tick
  is persisted; one that vanishes was written from a cached copy.
- assert each replacement applied by counting matches before and after, keep a `.bak-<HHMM>` beside the
  file, and re-`json.load` it before moving on.
