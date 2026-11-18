# Update-window baseline + acceptance test

Recorded **before** the swap, re-run **after**. The point of the baseline is that the post-swap check is a
comparison rather than an impression.

## What to record before the event

| item | command | why it matters |
|---|---|---|
| engine version | `hermes --version` | the from-version, so the pair is unambiguous |
| state dir mount | `grep -E ' / ' /proc/mounts` | `overlay` for `/` + a distinct device for the state dir = the recreate cannot touch state |
| DB + WAL | `stat -c '%s %y' state.db state.db-wal; md5sum state.db` | an un-checkpointed WAL replays on next open; it is the first casualty if the *mount* is swapped instead of the image |
| config / env / cron | `stat -c '%s %y' config.yaml .env cron/jobs.json` + md5 | the three files a new default would silently rewrite |
| secrets | `find .../secrets -type f \| wc -l` | count only — never read or print contents |
| in-flight queue | `find .../pending -type f \| wc -l` | enumerate, label **unapplied** |
| tracked processes | `cat processes.json` | should be `[]` for a clean window |
| skill index | `hermes -p <seat> skills list > /tmp/x; grep 'enabled,' /tmp/x` | the row count you must get back |
| invariant probe | the engine's own `--status` / `--selftest` | must print the same invariant, not merely exit 0 |

**Capture exit codes as `cmd > /tmp/out 2>&1; rc=$?`** — never through a pipe, which reports the last
stage's status and made a hard-failing guard read as success.

## Acceptance test form

Write it as an ordered list with an expected value per line, and name the failure meaning:

1. `python3 -V` → record the new runtime.
2. engine `--selftest` → **must still pass N/N**; any other number means the engine or its data moved.
3. engine `--status` → must still print the same invariant (e.g. `UNMEASURED — 0 of N`); a fabricated
   progress figure is the one failure this lane cannot ship.
4. any guard script → same exit code on the same input, and it must still **not** print the secret.
5. service shape (`ls /run/service/`) → compared against the recorded list; the seat's own entry point
   must still exist or the seat is unreachable.
6. `hermes -p <seat> skills list` → the recorded enabled count, and no absorbed skill name reappears.
7. metered-rail usage, before vs after, when the release changes prompt size or replay behaviour.

## Digest triage (the part that must reach disk)

For each item that touches your lane, answer exactly two questions and write them to the lane folder:

- **Gives:** what it enables, and the concrete thing you will do with it.
- **Breaks:** the measurement you ran, and the result.

Anything answering neither is noise for your lane. The highest-value entry is usually the item the digest
**omits** — a feature that adds cost on the same rail another feature was advertised to save.
