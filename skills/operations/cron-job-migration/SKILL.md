---
name: cron-job-migration
category: operations
description: "Use when moving or retiring a cron job between profiles."
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [cron, migration, retirement, fleet, operations]
    related_skills: [cron-delivery-audit, cron-drift-deploy-invariants, cron-health-standard, cron-improvement-audit]
triggers:
  - Moving a cron job between profiles or rings
  - Consolidating duplicate jobs across profiles
  - Migrating a job because it belongs to another team's remit
  - Retiring a finished one-shot or a superseded job
---

# Migrating a cron job between profiles

## When to Use

- A job's remit belongs to another team, so the job must move rings.
- Two profiles run the same job and it should be consolidated into one.
- A finished one-shot or a superseded job needs retiring.
- You are about to claim a job "now lives in <profile>" and need that claim to be true.

**A migration is a redirection, not a copy.** Both halves must move (the entry point AND the runtime
state), the destination must be proven before the source is retired, and the usual failure mode is
silent: the copy runs the *source* profile's code and keeps writing the *source* profile's state,
while every listing says the destination owns it.

Adjacent skills: delivery-target choices live in `cron-delivery-audit`; deciding whether a job is
still worth running at all lives in `cron-improvement-audit`; multi-profile script deployment and
drift guards live in `cron-drift-deploy-invariants`.

---

## Order of operations (do not reorder)

**Create in the destination first; retire the source last.** Create → verify → *then* disable the
source. Retiring first leaves a window in which neither ring owns the job, and if the create then
fails there is no job at all.

**There is no `hermes cron move` — stop looking, and do not build one that hand-edits two registries.**
`hermes cron` exposes `list · create · edit · pause · resume · run · cancel · remove · status · runs ·
incidents · notepad · doctor · tick` and nothing that spans profiles. **The migration IS the steps below,
run in this order on both profiles.** A wrapper script is only worth writing once you have done it by hand
and know which parts the CLI actually guarantees.

1. **Read the destination's conventions before writing.** List its jobs and copy its local grammar —
naming style, delivery targets, venv vs system interpreter, script layout (`scripts/` + `tools/`).
2. **Create with the profile-aware CLI**, never by hand-editing another profile's `cron/jobs.json`:

   ```bash
   hermes -p <profile> cron create "<schedule>" --name "<name>" \
     --script <wrapper>.sh --no-agent --deliver <platform:chat_id>
   hermes -p <profile> cron list      # read back — the create message is not proof
   ```

   The scheduler owns `jobs.json` and will overwrite a hand edit.
3. **Set `deliver` explicitly.** A job created with no delivery target inherits the *creating*
session's origin, so the migration silently changes where output lands instead of moving it.
4. **Copy the entry point as a byte-identical regular file** into the destination's `scripts/` (never
a symlink), and take its sibling dependencies with it.
5. **Carry the runtime state — unless it is already shared.** A delta-tracking job's baseline lives in its
state file; land the destination without it and the first run re-baselines and reports a false "changed" —
a wrong alert caused by the move itself. **But check WHERE the state lives before copying anything:** a tool
defaulting to a profile-neutral path (`/opt/data/backups/<tool>-seen.json`, `/opt/data/scripts/...`) is
deliberately SHARED, so a migration changes nothing about it — no copy, no re-baseline, and the delta
survives the move for free. `grep -n 'STATE\|SEEN\|state/' <the canonical tool>` settles it in one call.
Copying a shared-state file into the destination would fork the baseline and cause the exact false
"changed" this step exists to prevent. **Only per-profile state travels.**
6. **Retire the source reversibly**, recording a machine-readable reason (`migrated`), so a health
sentinel reads the pause as deliberate instead of reporting the job as broken. **The CLI has no reason
flag** — see §Retiring a job for where that reason actually has to be written.
7. **Verify the destination's run does nothing to the source.** The decisive check, below.

---

## The two hard-coded-path traps (both fail silently)

**Trap 1 — the wrapper names its original profile.** A wrapper written for one profile hard-codes
that profile's script path and interpreter. Copied into a second profile it runs the FIRST profile's
code while appearing to be the destination's job. Rewrite the wrapper for the destination; prefer a
system interpreter when the tool is stdlib-only, so the destination needs no venv.

**Trap 2 — the tool's state default names a sibling's directory.**

```python
# WRONG: every deployed copy reads and writes the OTHER profile's state
STATE = os.environ.get("APP_STATE", "/opt/data/profiles/<other>/state/history.json")

# RIGHT: resolves from this file's own location, override still available
_PROFILE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.environ.get("APP_STATE",
                       os.path.join(_PROFILE_DIR, "state", "history.json"))
```

A hard-coded sibling path is a defect **at the canonical level**: every future profile that adopts
the tool inherits it. Fix it in the shared tool and re-copy — do not paper over it in one wrapper
with an env var and leave the trap for the next adopter.

---

## Verifying the migration (the decisive check)

**Prove the destination's run does not touch the source's state.** Capture the source state file's
mtime, run the destination's entry point, and compare:

```bash
before=$(stat -c %Y <source>/state/history.json)
<destination>/scripts/<wrapper>.sh >/dev/null 2>&1
[ "$before" = "$(stat -c %Y <source>/state/history.json)" ] \
  && echo 'OK: source untouched' || echo 'FAIL: the trap is live'
```

Then confirm the destination's own state file actually grew. This single check catches the wrapper
trap, the state-default trap and a missing state migration at once — which is why it is the
verification step rather than an afterthought.

### Prove WHERE it landed — a clean status is not a destination

**"The job ran" and "it landed where we said" are different claims, and only the second one is the
migration.** Everything above proves the entry point works; none of it proves the output reached the
destination's room.

- **`deliver` wins over `origin`, and the stored record will still look wrong.** Create a job in profile B and
  it inherits the **creating session's** origin, so a job whose `--deliver` names room Y can carry
  `origin.chat_id = X` — the room you migrated it *away* from. The send uses `deliver`; `origin` stays stale.
  **Do not hand-edit `origin`** (the scheduler owns the file) and **do not read the record as evidence of
  destination**. Two fields disagreeing is expected here, not a defect to fix.
- **The only artifact that names the real target is the scheduler's own delivery line**, in the DESTINATION
  profile's log:
  ```bash
  grep 'delivered to' <destination>/logs/agent.log | tail -3
  # cron.scheduler: Job '<id>': delivered to <platform>:<chat_id>   ← this is the receipt
  ```
- **`last_status: ok` and `last_delivery_error: None` are identical for the right room and the wrong one.** A
  clean status proves the run completed, never where the output went. A migration verified only by
  `last_status` is blind to the single failure it exists to prevent.
- **Check BOTH rooms.** Grep the destination log for its own chat id **and** the source job's target for the
  old one — a delivery to both is the duplicate the pause was supposed to prevent, and it does not appear in
  either job's status.
- **A silent job cannot be verified by looking in the room.** A digest with nothing new delivers an *empty*
  result, so "no message appeared" is compatible with success **and** with non-delivery. Read the log line
  first; the room is corroboration, never evidence.

**Two related checks worth running at the same time:**

- **Byte-identical copies:** if the same tool must exist in two profiles, diff them afterward and
  keep them identical — a fix applied to one copy is drift the moment the other is forgotten.
- **A tool that exits 0 having discovered ZERO of its targets is failing silently.** Read the
  discovery count, not the exit code. This is the standard symptom when a copy carries path
  defaults from another host or profile.

---

## Retiring a job (with or without a migration)

- **Pause is only a retirement if it HOLDS — verify it after the next scheduler tick, and delete a DUPLICATE
  outright.** A pause preserves the definition for reversal, so it is the right default for a job you may want
  back. **But a pause can silently revert:** measured here, `hermes cron pause` reported success, `hermes cron
  list` printed `[paused]`, and `jobs.json` showed `enabled: false` — then roughly forty minutes later the job
  ran and the file read `enabled: true` again, because the running scheduler persisted its own in-memory copy
  over the CLI change. **So "I paused it" is not evidence: re-read the listing after a tick, and never report a
  job as retired on the strength of the pause command's own output.**
  - **When the job duplicates one that survives elsewhere, DELETE it** (`hermes cron delete <id>`; it takes no
    `--yes` but does confirm). A deleted job cannot un-delete itself, and the definition is still held by the
    surviving copy — exactly the case where a pause buys nothing and its unreliability costs the most.
  - **Establish ownership by PROFILE, not by name.** Two jobs with near-identical names can be one job copied to
    a second seat; `HERMES_HOME=profiles/<seat> hermes cron list` is what shows which seat owns the survivor.
- **Attach a machine-readable reason** (`migrated`, `archived`, `deprecated`, `user_paused`) — but not through
  the CLI, which does not offer one. `hermes cron pause <job_id>` accepts **only** the id; `--reason` is
  rejected as `unrecognized arguments` and the pause never happens. Put the reason where a reader will
  actually look: the vault note for the migration, the pending/completion row, and a note beside the job in
  whatever registry you keep. A pause with no reason anywhere is indistinguishable from a job that broke and
  was silenced — which is how a job disappears for days while everyone assumes it is healthy.
- **Retire finished one-shots.** A completed one-shot left in the registry is clutter that every
  future audit must re-read and re-adjudicate. Removing it is a legitimate finding of an improvement
  audit.
- **Removing a parked source job is the last step, never the first** — and only after the
destination is proven.

---

## Pitfalls

- **Hand-editing another profile's `jobs.json`** — the scheduler owns that file; your edit is
  overwritten and the migration silently never happened.
- **A `jobs.json` edit can also be INVISIBLE rather than overwritten.** Measured: a schedule changed in the file
to `0 5,17 * * *` and `hermes cron list` still printed `0 5` with the old next-run time — the scheduler reads its own
copy, so the file and the running schedule disagreed and the file looked correct. **Change through the tool
(`hermes cron edit <id> --schedule '<expr>'`) and verify through the tool (`hermes cron list | grep -A4 <id>`); treat
the file as an artifact, never as the source of truth.** The same applies to a job's `prompt`: it is the documented
contract, so when a script's behaviour changes, update the prompt with `hermes cron edit --prompt` in the same pass —
an accurate script under a stale contract teaches the next reader the wrong thing.
- **A job added by appending to the file may never be registered at all.** Add one with `hermes cron create`, then
  confirm it appears in `hermes cron list` with the expected next-run time. A job that is absent from the listing is
  not "pending", it is not scheduled.
- **Trusting the create confirmation.** Re-read the registry (and the CLI listing) before retiring
  anything. A success message is not a registered job.
- **Leaving the source enabled "just in case"** — two rings now run the same job, and the duplicate
  output looks like a real alert.
- **Migrating the script but not the state** — the destination re-baselines and emits a false
  "changed" on its first run, which reads as the migration having broken something.
- **Copying a wrapper verbatim** — it carries the source profile's identity with it.
- **Adding a credential to a seat you retired** — backwards. Retire the profile directory too, or
  the next dispatch counts it again.
