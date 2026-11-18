# Reading cron execution history

How to answer "what ran, what failed, and how often" from the execution record — without touching the live
scheduler and without a second monitoring system.

---

## Where it lives

```
/opt/data/profiles/<seat>/cron/
  executions.db     SQLite, one row per run  ← the ground truth
  jobs.json         the job specs: id, name, schedule, script, delivery
  output/           per-job stdout, if configured
```

Every seat has its own file. `jobs.json` and `executions.db` are **different files with different keys** — the
job id in `executions.db.job_id` matches `jobs.json.jobs[].id`; the human name only exists in the jobs spec.

---

## The schema (as measured)

`executions` columns:

| Column | Meaning |
|---|---|
| `id` | execution row id |
| `job_id` | joins to `jobs.json.jobs[].id` |
| `status` | `completed` · `failed` · (others as added) — **see the conflation note below** |
| `started_at`, `finished_at` | ISO-8601 UTC; duration = difference |
| `error` | the failure text, including captured stdout |
| `delivery_outcome` | `delivered` · `not_configured` · … |
| `scheduled_instant` | when it was due (compare with `started_at` for lag) |

**`status: failed` conflates two different things:** a job that crashed, and a job that exited non-zero *on
purpose* to report a finding (which is what the health standard prescribes). Always read `error` before
calling a job broken. An `error` starting with a structured report (`Script exited with code 1\nstdout:\n<finding>`)
is an alerting monitor; a traceback is a break.

---

## Read it read-only

**Never `cat`/`head`/`tail` a `.db` file** — it is binary and dumps pages of unreadable noise into the
transcript (this cost a full turn). Query it, with `mode=ro` so there is no chance of writing to a live log:

```python
import sqlite3
con = sqlite3.connect(f"file:/opt/data/profiles/{seat}/cron/executions.db?mode=ro", uri=True)
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute("SELECT * FROM executions")]
con.close()
```

Discover the table before assuming its name:

```python
[ r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'") ]
[ r[1] for r in con.execute('PRAGMA table_info("executions")') ]
```

---

## The report that answers the question

Compute, per seat and fleet-wide:

1. **total executions** (all time) and **in the window** — window is an argument, default 24h;
2. **non-zero exits in the window** — *not* "broken jobs";
3. **grouped by `job_id`, most frequent first**, with the top error signature beside each — the count is what
   ranks it, the signature is what makes it actionable;
4. **last good run / first bad / last bad** — the ticket's own first question;
5. **duration median, p95, max** from `started_at`→`finished_at` — reveals a job that is quietly timing out;
6. **`delivery_outcome`** per failing job — a failure with `not_configured` has no reader.

A self-contained HTML page plus a `report.json` is enough. No dependencies, no writes to the DBs, and it runs
before the first person asks.

---

## What the numbers do not prove

- **A job with no failures is not a healthy job** — it may be an unobserved one that never ran. Join to
  `jobs.json` and compare enabled jobs against jobs with rows before calling anything healthy.
- **The window is a window.** Three failures in 24h is a reading, not a trend. Do not infer a weekly pattern
  from a daily slice.
- **A growing age is the real signal.** For freshness gates, read the observed age across consecutive runs: if
  it climbs by ~24h per day, nothing is producing — that is a broken producer, not a threshold that is too tight.
