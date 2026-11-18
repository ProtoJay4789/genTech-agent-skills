---
name: script-only-job-wiring
description: "Use when a cron job must also produce a file or audio."
version: 1.0.0
author: gentech-treasury
license: MIT
metadata:
  tags: [cron, script, wiring, delivery, no-agent]
  hermes:
    tags: [cron, script, wiring, delivery, no-agent]
    related_skills: [cron-health-standard, cron-drift-deploy-invariants, duplicate-skill-merge]
---

# Wiring a step into a script-only job

## When to Use

- A scheduled job already runs correctly and **should also** produce something it does not: a rendered
  file, an audio briefing, an attachment, a second notification.
- A job has been "healthy" for days while a human keeps doing part of its work by hand.
- You are about to change a job's wrapper script, or add a second step to one that already has `exec`.

## The governing fact

**A `no_agent: true` job has no memory.** It runs its wrapper, delivers stdout, exits. There is no agent
in that path to remember a step, so **any step that exists only in someone's habit does not happen** — and
the job still reports `last_status: ok`, because nothing it did was wrong. It was incomplete in a way no
status field describes.

**Rule: when a job "should also do X", put X inside the wrapper.** The wrapper is the only place the
sequence exists. A prompt on a job that has no prompt is not an instruction, it is a comment.

## The exit-code contract — `1` means BROKEN, never "I found something"

**Hermes script-only semantics:** `exit 0 + output` → delivered verbatim · `exit 0 + empty` → silent tick ·
**any non-zero → "error alert delivered."**

So the code space is:

| code | means | use for |
|---|---|---|
| **0** | the job ran | **clean OR findings.** Findings go on **stdout**, never in the exit code |
| **2** | could not read | UNKNOWN — the input was unreadable, so no verdict may be given |
| **1** | *never* | a script-only job must not exit 1; it is indistinguishable from a crash |

**Why this matters more than it looks:** a monitor that exits 1 on a red finding **pages a human as if the
script broke on every successful run** — and a guard that always goes red is not a guard. A gate that
cannot go red is equally useless. The contract is what makes red means red: **exit 0 + a printed finding**
is a working guard reporting news; **exit 2** is a guard admitting it cannot see.

**Implement it in the wrapper, not only the tool.** The tool should already follow 0/2 (no 1); the wrapper
is where the silence policy lives:

```bash
out=$(python3 "$TOOL" 2>&1); rc=$?
[ "$rc" -eq 2 ] && { echo "⚠️ COULD NOT READ (UNKNOWN, not a pass)"; echo "$out"; exit 2; }
[ "$rc" -ne 0 ] && { echo "🔴 SCRIPT BROKEN (exit $rc); results unknown, not clean"; echo "$out"; exit 2; }
[ -n "$out" ] && { echo "$out"; echo "Findings are not breakage — exit 0 on purpose."; }
exit 0
```

**The tool must print nothing when clean** (empty output = silent tick) and print only the failing rows
when not. Printing a full PASS table every run trains the reader to ignore the message.

## Procedure

1. **Read the job record before editing the script** — `script`, `no_agent`, `prompt`, `schedule`,
   `deliver`. An empty `prompt` with `no_agent: true` means the script is the entire job.
2. **Back up the wrapper first** (`cp wrapper wrapper.bak-<what>`), then **use a targeted edit**, not a
   rewrite — an existing wrapper may carry comments and exit-code contracts you would silently drop.
3. **Decide per step whether it is BLOCKING or BEST-EFFORT, and encode that explicitly.**
   - Essential step first; check its exit code; exit non-zero **before** the optional step if it failed.
   - Optional step compares against the essential output: on failure print
     `⚠️ <step> FAILED — <essential output> above is complete` and **leave the job's exit status alone**.
   - **A cosmetic failure that turns into a failed job teaches its reader to ignore real failures.**
4. **Never leave `exec` on a step that is not last.** `exec` replaces the shell, so a second step added
   later never runs — silently, with no error, forever. Convert to a plain invocation plus an explicit
   exit-code check the first time a job gains a second step.
5. **Emit the delivery token the job's delivery layer understands** (an attachment path marker, a JSON
   field) **and also print a human line naming the file and its size**, so a run whose attachment was
   dropped is still legible in the transcript.
6. **Run the WRAPPER, not the tool it wraps.** A tool proven by hand says nothing about the entry point.
   Assert on real output: the file exists and is non-empty, the token is present, the exit code is the
   one you designed.
7. **Then confirm the SCHEDULED run**, not the manual one. Delivery-layer behaviour (whether an
   attachment marker is honoured, whether the message arrives as a file or a path string) is only proven
   by a fire the scheduler itself performed. Until that has been observed, report it as unproven — do not
   upgrade "the script emits it" to "you will receive it".
8. **Record the wiring in the job's own comment header** — what was added, why it was missing, and what
   the failure mode is if the step is dropped again.

## Pitfalls

- **A job whose script CRASHES is indistinguishable from a job with nothing to report.** When a job has
  been quiet, read `last_error`, not only `last_status`. Prefer a job that fails loudly to one that
  returns an empty success.
- **Silence is not evidence of a step running.** If a scheduled job has produced no artefact for days and
  the humans have not noticed, assume the step is not wired and check the wrapper's last line first.
- **A tool with an exit-code contract must not be piped before its status is read.** `cmd | head` reports
  the downstream command's status, so a refusing gate reads as success. Capture the code, or read the
  tool's `--json` decision field.
- **Don't add a second job to cover the missing step.** Two schedules for one artefact means two
  frequencies that can disagree; wire the existing job.
- **`--script` must resolve inside `profiles/<seat>/scripts/`, not a shared tools directory.** Job creation
  rejects a canonical tool that lives elsewhere: *"Script file not found: /opt/data/profiles/<seat>/scripts/<name>.py.
  Create it in … first."* Keep the canonical logic where it belongs and place a thin wrapper — or a copy — in the
  seat's own `scripts/` dir, then create the job and **read the record back** to confirm the resolved path. The
  scheduler validates against its profile root, not against your working directory.
- **Pass the script as a BARE FILENAME, and create with the right subcommand.** Two shapes the CLI rejects, and
  both fail before anything is scheduled:
  - an **absolute or `~` path** for `--script` → *"Script path must be relative to /opt/data/profiles/<seat>/scripts/.
    Got absolute or home-relative path"*. Pass `x402-signal.sh`, not `/opt/data/profiles/<seat>/scripts/x402-signal.sh`.
  - **`hermes cron add --schedule "…"`** — there is no `add`/`--schedule`; the verb is **`create`** and the
    schedule is a **positional first argument**: `hermes cron create "50 15 * * *" --name … --script name.sh
    --no-agent --deliver origin`. Confirm the interface with `hermes cron create --help` rather than guessing from
    another scheduler's grammar.
  After creation, **fire it once by hand** (`hermes cron run <id>`) and confirm the run row exists
  (`hermes cron runs <id>`) — a created job is a claim, a completed run is evidence.
- **If a SECOND consumer reads this job's output, write the artefact EVERY run to a default path.** An opt-in
  flag (`--json PATH`) that no scheduled invocation ever passes leaves the consumer with a stale or absent file,
  and a consumer with no input reports an ABSENCE as a finding — one such queue produced *"36 new failure modes"*
  that were in fact unreadable records. Default the dump path inside the tool, keep the flag only as an override,
  and make a failed write loud on stderr while leaving the job's exit status alone.
- **A dependency the wrapper needs must be resolvable from the wrapper's working directory.** `cd` into
  the profile dir before invoking the tool, or a config/key file read by relative path resolves against
  the scheduler's cwd and the step fails only when scheduled.

## Related

- `cron-health-standard` — whether the job is *watched* (health, debounce, heal). This skill is about
  whether the job *does what it claims*.
- `cron-drift-deploy-invariants` — script deployment paths, copy drift, and data-file resolution.
- `duplicate-skill-merge` — promoting a changed skill from one seat to the fleet.
