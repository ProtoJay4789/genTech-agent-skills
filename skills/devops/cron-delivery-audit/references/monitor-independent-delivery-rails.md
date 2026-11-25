# Monitor rails — proving a monitor can report its own failure

Companion to the "A monitor must not be the only thing that would report its own failure" rule in SKILL.md.
Depth only; the four rules live in the body.

## The failure shape

A scheduled health check ran nightly, reported `completed` every time, and delivered every message into a
chat id that returned **`Chat not found`**. The error was recorded on three consecutive runs. Nothing reached
a human, because the only instrument that would have escalated it was the job whose channel was dead.

Two properties made it invisible:

- **`completed` describes the RUN, not the delivery.** The job genuinely ran; the message genuinely did not
  arrive. Both facts are true at once.
- **A configured target is not a working target.** The config was well-formed and pointed at a real-looking
  id. Nothing in `jobs.json` could distinguish it from a healthy job.

## Rails enumeration — report a count, not a promise

List every transport separately and classify each one by what has been **proven**, not by what exists:

| Rail | Proven by |
|---|---|
| The chat itself | the most recent run's recorded delivery outcome |
| A second, independent transport (cross-seat message, different bot, different network path) | the transport's own status command, and the fact that it does not share this bot's chat membership |
| Email / SMTP | credentials present AND a send actually completed |

Report the count: **`2 independent rails working`** is checkable and actionable. `email configured` is a
claim about configuration, not about delivery.

Design points that matter:

- **A rail that is declared but unconfigured must REFUSE, with the missing variable names, and exit
  non-zero.** Printing "email: ok" because the library is importable is the same false green the monitor
exists to catch. `smtplib` being present proves the language has a mail module, nothing more.
- **Never silently fall back to the monitored channel.** A fallback restores the single point of failure the
  second rail was added to remove, and it removes the evidence that redundancy was never real.
- **Cross-seat transport is a real rail, with a caveat worth stating:** it survives this bot losing this
  chat, because it goes through another seat. It is not free — it lands in that seat's inbox, not the
  human's, and it needs someone awake to read it.
- **State the residual risk when one remains.** One chat is one rail however many jobs use it.

## The per-job delivery probe

Read the durable run record, not the job config:

```python
for job in enabled_jobs:
    row = latest_run(job_id, only_with_outcome=True)
    if row is None:
        continue                      # never run — UNMEASURED, not a miss
    if row.outcome not in {"delivered", "suppressed", "not_configured"}:
        bad.append(f"{job.id}:{row.outcome}")
```

Rules:

- **Exclude jobs that have never run.** A new job with no history is unmeasured; counting it as broken makes
  the probe cry wolf on every new job and trains the reader to ignore it.
- **Treat "chose silence" as delivered.** A job that ran and deliberately suppressed its output did reach a
  decision; the outcome name should say so rather than being lumped with failure.
- **Name the job id and the outcome** in the finding (`jobA:failed`). A bare count cannot be acted on.
- **Always print which source you measured:** `N run(s) checked`, or
  `no run history yet — config checked only`. A config-only pass presented as a delivery pass is the exact
  false green this whole file is about.
- **Two states, never one:** a job that did not RUN and a job that ran but delivered nowhere are different
  defects with different fixes. Keep them in separate counters and name both in the note.

## Diagnostic order when a human says "the job ran but I never saw it"

1. Did it run? (durable run record, timestamp matching the schedule)
2. Did it produce output? (the output file exists and is non-trivial)
3. Was the payload deliverable? (size against the platform limit; media tokens are the common breaker)
4. **Reproduce it live** — this is the only step that exercises delivery.
5. Only then read gateway logs for that timestamp, looking for the platform's own error string
   (`Chat not found`, `bot was kicked`, `chat not found`).
