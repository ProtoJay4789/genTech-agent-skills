# Proving cron delivery from the run record

Depth for the "set ≠ works" rule in SKILL.md. The question every audit is really asking is not *is this
job configured to deliver* but *did the last run's work reach anyone*, and only the delivery ledger
answers it.

## The ledger

Every attempt is recorded in `<profile>/cron/executions.db`, one row per run, with a
`delivery_outcome` column. Read it in read-only mode so an audit can never mutate the thing it audits.

```python
import sqlite3
con = sqlite3.connect(f"file:{ROOT}/cron/executions.db?mode=ro", uri=True)
row = con.execute(
    "SELECT delivery_outcome, started_at FROM executions WHERE job_id=? "
    "AND delivery_outcome IS NOT NULL ORDER BY started_at DESC LIMIT 1", (jid,)).fetchone()
```

| outcome | means | counts as delivered? |
|---|---|---|
| `delivered` | the message arrived | yes |
| `suppressed` | the job chose silence; it had nothing to say | yes |
| `suppressed_acked` | silence, acknowledged | yes |
| `not_configured` | job declares `deliver=local` by design | yes |
| `failed` | the send was attempted and refused | **no** |
| NULL / no row | never ran, or no outcome recorded | **excluded, not failed** |

## Two rules that make the check honest

**Exclude jobs with no recorded run.** Untried is not a miss. A job created an hour ago has no history;
failing it produces a false red on day one, and a false red teaches the operator to add an exemption.

**`status` and `delivery_outcome` are separate facts.** Classify by both, in order: `status != completed`
is *did not run* (a crash); `status == completed` with an outcome outside the delivered set is *ran but
delivered nowhere*. A probe that ORs the two loses exactly the distinction it exists to make.

## Why the config-shaped check fails

A target that names a chat the bot cannot reach is a perfectly configured job. Measured shape: a
reflection monitor printed `0 enabled job(s) with no delivery target` ✅ for three consecutive nights
while a job sent into a chat that answered **"Chat not found"** — logged in `errors.log` at the
scheduled minute every night, unseen, because the only instrument that would have escalated it was the
job whose channel was dead.

Config checks answer *"is a target set"*. The ledger answers *"did it land"*. On a seat with no
`executions.db` at all, say `no run history yet — config checked only` rather than going red on a seat
that is merely new.

## Counting the rails

Before trusting a silent-when-healthy daily job, enumerate how many INDEPENDENT paths could tell a human
that it broke:

| rail | proven by | independent? |
|---|---|---|
| telegram | `delivery_outcome` on the latest run | no — it is the monitored channel |
| cross-seat / peer transport | a second script that crosses profiles, `--status` returning live rows | yes |
| email | SMTP settings present **and** a send that returned 0 | yes |

- **One working rail is a single point of failure, not a redundancy.**
- **A declared-but-unconfigured rail is NOT CONFIGURED**, named with the missing variables. It is never
  counted as working and never silently substituted by the Telegram rail — substituting rebuilds the
  failure the second rail exists to remove.
- **A rail's `--test` must refuse honestly.** `smtplib` being importable is not a rail; a test path that
  reports success it did not achieve is worse than no test.

## In-flight exclusion for self-grading monitors

A monitor that grades the job it runs inside reads a stale row: the current run's record is written after
the process exits. See `guard-verification` §3d — exclude the in-flight instance by row age, and never by
an identifier variable you have not confirmed the scheduler exports.

## `--json` purity

A machine-readable mode that emits the document **and then** a human verdict line is not machine-readable;
`json.loads()` fails with "Extra data" and the error blames the consumer. Under `--json`, send the verdict
to **stderr**. The cron path still needs it on stdout, so make the destination conditional on the flag
rather than deleting the line.

## One-shots and the disabled count

`enabled: false` alone is not a defect: a job with `state='completed'` ran, delivered and retired — that is
success, and counting it makes a working reminder a permanent red. Test the PAIR (`enabled` false **and**
`state` not completed). Separately assert that at least one enabled job holds a `next_run_at`: a seat whose
every scheduled instant is in the past otherwise reads healthy.
