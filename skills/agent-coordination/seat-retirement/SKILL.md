---
name: seat-retirement
description: "Use when a seat is retired: migrate, delete, prove no wake."
version: 1.0.0
author: gentech
license: MIT
tags: [seat, retirement, profile, migration, deletion, wake, fleet]
trigger: "When a seat or agent profile is being retired or removed from the fleet — 'delete gizmo', 'retire the orphaned seats'. NOT for adding a seat (`telegram-bot-seat-provisioning`) and NOT for a repo/fork delete (`pre-deletion-inventory`)."
metadata:
  hermes:
    tags: [seat, retirement, profile, migration, deletion, wake, fleet]
    related_skills: [pre-deletion-inventory, destructive-write-guards, telegram-bot-seat-provisioning, checkpoint-ack, agent-state-disaster-recovery]
---

# Seat Retirement — migrate, remove, then prove the corpse is deaf

The add side is `telegram-bot-seat-provisioning`. This is the **remove** side, and it has one step
the add side never needed: **after the profile is gone, prove it can no longer answer a wake.**

That last step is the whole reason this skill exists. A retired profile whose directory was deleted
but whose *wake path* still resolves is not retired — it is a corpse that talks, and it signs
checkpoints, files handoffs and gets counted in a census as a live seat.

**Jordan's precondition (2026-10-18), and it is the correct order:** *migrate ALL skills and ALL
notes before ANY deletion.* Deletion is the LAST step, not the first.

## When to Use

- A seat or agent profile is being retired, removed, or "cleaned up" — including one that is already
  dead (no bot token, no API key) but still answers a wake.
- A profile directory is reported as orphaned and someone proposes deleting it.
- **NOT** for adding a seat (`telegram-bot-seat-provisioning`), and **NOT** for deleting a repo, fork
  or backup store (`pre-deletion-inventory`).

## Membership is a CREDENTIAL fact, and the authority is the owner's

Decide whether the thing is a **seat** before deciding it is a snapshot to keep. The discriminator is
credentials, not presence: a seat holds a **bot token** and an **API server key**; a profile directory
with neither is not a member however much content it holds.

**A wake proves nothing.** `hermes -p <name> -z …` runs the CLI against *any* profile directory,
member or not — so a corpse returns fluent, well-measured output and is indistinguishable from a live
seat from the inside. That is the measured defect: two non-member directories answered `PROBE_OK`
(2026-10-18 13:51) and had earlier signed a fleet checkpoint ACK. **The fleet rail is the tell** —
`hermes peer dm fleet/<name>` resolves membership, and it is the rail, not the wake, that a census
should trust. (Measured after removal: the rail rejects a retired name `HTTP 404` while the local twin
says `Profile '<name>' does not exist`.)

- **Build any roll-call from credentials, not from a directory listing.** A checkpoint dispatched to
  "all seats" will otherwise include retired directories that answer, inflating the roster and
  producing ACKs from non-members. **State which seats were excluded and on what evidence.**
- **A seat with zero jobs is not automatically a dead seat.** An empty ring has causes only the seat's
  own history can supply — a deliberate cleanup, a ring that never needed a job, or jobs never
  scheduled. Read the record before writing a cause.
- **`large` and `irreplaceable` are different properties.** Measure composition, not total: the
  38 MB `bin/` in each of these profiles was **one binary, byte-identical in all six profiles**.
- **The lead's decision is not the owner's authorization.** Retiring a seat destroys state nobody may
  have inventoried: migrate, measure, and put the evidence in front of the fleet's owner for the
  deletion — as this procedure's GO/NO-GO guard exists to do.

## Order: MEASURE → PROMOTE → CONFIRM NOTES → EXPORT → DELETE → PROVE REFUSED

### 1. MEASURE what the seat actually is

A profile directory is not a seat. Measure the three things that decide whether it is one:

```bash
P=/opt/data/profiles/<name>
grep -c '^TELEGRAM_BOT_TOKEN=\|^API_SERVER_KEY=' $P/.env   # 0/0 = no room can reach it
python3 -c "import json;d=json.load(open('$P/cron/jobs.json'));j=d if isinstance(d,list) else d.get('jobs',d);print(len(list(j.values()) if isinstance(j,dict) else j))"
stat -c 'ticker mtime=%y' $P/cron/ticker_heartbeat
```

A profile with no bot token, no API key and 0 cron jobs is **not** a seat — and it still answers a
local-twin wake, which is precisely the defect this procedure closes. Do not skip the census because
the answer looks obvious from the name.

### 2. SKILLS — run the fleet's own sweep, never a hand-built diff

```bash
python3 /opt/data/.obsidian-vault/00-System/agent-profiles/fleet-skills-sync.py --check
python3 .../fleet-skills-sync.py --promote --seat <name>     # additive: never deletes
```

- The sweep's zero must be **shown to discriminate**: the same run must report NON-zero seat-only
  skills for other seats, or the zero is a property of the instrument. Capture that output.
- `--promote` is additive at skill-dir granularity. It cannot save a seat-only **file** inside a
  skill both sides have — if the sweep reports drift inside such a dir, copy the file into CORE by
  hand and say so (`--sync` refuses the whole dir otherwise, by design).
- **The sweep's CORE is the vault distribution (`10-Labs/skills-distribution`), not
  `/opt/data/skills`.** Diffing against `/opt/data/skills` reports a large, false seat-only list,
  because that tree is itself a divergent, unmanaged generation. Compare against the CORE the tool
  names, and state which root you used.

### 3. CONFIRM NOTES — per FILE, in the vault, before anything is removed

"Their notes live in the vault" is a claim about the vault, and it is routinely half-true:

```bash
find $P -name '*.md' -not -path '*/skills/*'          # what the PROFILE holds
find /opt/data/.obsidian-vault -iname "*<name>*" | head
md5sum $P/SOUL.md $P/memories/*.md                     # is the profile copy the vault copy?
```

Measured on two retired seats: the vault held their real SOUL (3,010 B) and avatars, while the
profile held a **667 B stub SOUL identical to the stock backup**, a `MEMORY.md` that existed in
**exactly two places — both being deleted**, and `USER.md` that was a byte-copy of the default
profile's. So: real docs in the vault, real *notes* only in the profile. **Copy the profile-resident
notes to a durable vault home** (`11-Mess Hall/retired-seats/<date>-<seat>/`) and record, per file,
whether it was unique, a duplicate, or a stub — **never delete a file you have not read.**

**Never copy `.env` (or any secret-bearing file) into the vault** — the vault syncs off-box. The
export archive (step 4) is the home for those, on the host, mode 600.

### 4. EXPORT at full fidelity — use the app's own path

```bash
hermes profile export <name> -o /opt/data/backups/seat-retirement/<name>-<date>.tar.gz
sha256sum /opt/data/backups/seat-retirement/<name>-<date>.tar.gz
tar -tzf <archive> | wc -l          # record the entry count; a 0 here means an empty archive
```

An archive with no recorded digest and no entry count is not a preserve step, it is a hope.

**Probe what the archive actually holds — the app's export does NOT carry `.env`** (measured
2026-10-18: 2,047 entries for one seat, `.env` absent). A seat's secrets are therefore *not*
preserved by `export`, and "the archive has it" is a false receipt unless you listed the entries:

```bash
python3 -c "import tarfile,sys; n=tarfile.open(sys.argv[1]).getnames(); print(len(n)); print([x for x in n if x.endswith('.env')])" <archive>
cp -p /opt/data/profiles/<name>/.env /opt/data/backups/seat-retirement/secrets-600/<name>.env
chmod 600 /opt/data/backups/seat-retirement/secrets-600/<name>.env   # host-only, never the vault
```

Record the key count and whether any key is unique against the surviving seats' key set — a copy of
shared provider keys is worth preserving, but say what it is rather than calling it unique.

### 5. DELETE via the app — `rm -rf` is the wrong tool and it is not close

```bash
hermes profile delete <name> --yes
```

The supported path does five things a hand-delete does not:

1. **disables the gateway service** and drops this profile's **s6 slot** (`/run/service/gateway-<name>`);
2. **stops the gateway and any backends** still holding the SQLite connection open (an open handle
   makes `rmtree` fail `ENOTEMPTY` and **resurrects the deleted tree** — measured on this host);
3. **tombstones the profile before `rmtree`**, so a stale serve/logging `mkdir` cannot relist the
   name as live;
4. **notifies the multiplexer** and purges the profile's session/routing identity — if settlement is
   deferred it raises `ProfileIdentitySettlementPending` and names the retry
   (`hermes profile purge-identity <name>`); **run that retry rather than reporting a clean delete**;
5. removes the wrapper alias and retargets `active_profile` if it pointed here.

### 6. PROVE the wake is refused — the step that is missing today

Take the **baseline before** the delete so the test is known to discriminate:

```bash
hermes -p <name> -z "Health probe only. Reply with exactly: PROBE_OK"    # baseline: expect PROBE_OK
```

Then, after the delete, run the same command and assert **all four**:

```bash
hermes -p <name> -z "Health probe only. Reply with exactly: PROBE_OK" 2>&1 | tail -3   # (a) refused, non-zero
ls -d /opt/data/profiles/<name>          # (b) NOT re-created — a wake that re-mkdirs the profile is a resurrection
ls -d /run/service/gateway-<name>        # (c) slot gone
python3 -c "import sqlite3;print(sqlite3.connect('file:/opt/data/profiles/<name>/state.db?mode=ro',uri=True).execute('select count(*) from sessions').fetchone()[0])"  # (d) no new session
```

Assert the **exact** refusal (a non-zero exit and the name in the error), not merely that something
failed: a typo'd profile name also fails, and it fails identically. Keep a control — the same command
against a LIVE seat must still answer PROBE_OK in the same batch.

**What a clean retirement looks like on this host (measured 2026-10-18, two seats):**

| check | expected observation |
|---|---|
| `hermes profile delete <name> --yes` | rc=0, `✓ Removed /opt/data/profiles/<name>` |
| profile directory | absent, and **still absent after the wake probes** |
| `/run/service/gateway-<name>` | absent (the delete path unregisters it) |
| `hermes profile list` | name gone; **every survivor still listed** (the discriminator) |
| local twin `hermes -p <name> -z …` | rc=1, `Error: Profile '<name>' does not exist. Create it with: hermes profile create <name>` |
| peer rail `hermes peer dm fleet/<name>` | rc=1, `Peer 'fleet' rejected the request (HTTP 404)` |
| live-seat control `hermes -p <live> -z …` | still answers `PROBE_OK`, rc=0 |
| `/opt/data/profiles/.deleted/<name>` | **appears** — the 8-byte tombstone the delete writes before `rmtree` |

The control is not optional: the two failing commands and a typo'd profile name all exit non-zero,
so without a live seat answering in the same batch you have proven only that *something* failed.

## Traps, all measured

- **A deleted directory is not a retired profile.** The wake path is `hermes -p <name> -z …` (a local
twin) and, on this host, `hermes peer dm fleet/<name> "…"` through the multiplexer. Both resolve by
name. Removal must be proven against the name, not the path.
- **The s6 slot is generated from the profile directory at container boot**
  (`/etc/cont-init.d/02-reconcile-profiles` → `hermes_cli.container_boot`), and boot registers every
  named slot **down** and folds its autostart intent into the root slot. So a lingering slot for a
  deleted profile is not a second gateway — but it IS a start target. Drop it (the delete path does)
  and verify it is gone.
- **`--replace` on every gateway run script** means starting a named slot seizes the lock from the
  multiplexer. Never hand-start a retired seat's slot to "check" it.
- **A wake probe that prints PROBE_OK after the delete means the name still resolves** — stop and
  investigate; do not report "no errors".
- **A deletion is cheaper than a recovery, so the guard belongs on the delete.** Required before
  `--yes`: archive present + digest recorded + entry count non-zero + notes copied + per-file
  classification written down.
- **One deletion per profile, with a readback between them.** Deleting two seats in one command means
  one failure is indistinguishable from two.
- **The corpus matters elsewhere too.** The same sweep that clears a retiring seat can report
  unpromoted skills in OTHER seats (measured: 3 + 3 + 1 across three live rings, and 4 skill dirs
  present only in the unmanaged `/opt/data/skills` tree). **Do not fix another ring's drift inside a
  retirement** — report it; ownership is what makes the fix reviewable.

## Report shape

```
seat · skills promoted (n) · notes confirmed in vault (y/n) · dir removed (y/n) · wake-refused proven (y/n)
```

Anything short of a measured `y` in the last column means the seat is still reachable and the task is
**not** done — say so rather than reporting the directory as gone and calling it a retirement.

## Related

- `telegram-bot-seat-provisioning` — the add side (create the profile, wire its bot, prove it is live).
- `pre-deletion-inventory` — what is uniquely inside the thing, and where else a copy lives.
- `destructive-write-guards` — the guard belongs on every path that performs the operation.
- `checkpoint-ack` — the false ACK a still-wakeable corpse signs is exactly its failure mode.
- `agent-state-disaster-recovery` — restoring a seat that was retired by mistake.

## Provenance

Merged 2026-10-18, deliberately, rather than left as two copies of one lesson: `gentech` (HQ) wrote
this procedure from the measured execution for gizmo + pixel, and `gentech-treasury` wrote
`agent-seat-retirement` for the same lesson in the same hour. **One rule, one home** — this file is the
home. Absorbed from the treasury copy: the credential-vs-directory membership test, "a wake proves
nothing", the roll-call-from-credentials rule, the empty-ring caveat, and the
size-is-not-value pitfall. **Superseded from it:** its step 4, *"remove the profile directory"* — on
this host that is `hermes profile delete <name> --yes`, which tombstones the name, drops the s6 slot,
stops the open SQLite handles, and purges routing identity; a hand `rm -rf` does none of that and is
the documented cause of the `ENOTEMPTY` resurrection. **Still open for the owner:** the seat-local copy
at `profiles/gentech-treasury/skills/agent-coordination/agent-seat-retirement/` (seat-only, never
promoted) should be removed by its own ring — a cross-seat write is not this task's to make.
