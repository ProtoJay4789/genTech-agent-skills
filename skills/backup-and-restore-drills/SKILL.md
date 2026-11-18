---
name: backup-and-restore-drills
description: "Use when building, auditing, or restoring a backup."
version: 1.0.0
author: gentech
license: MIT
tags: [backup, restore, disaster-recovery, cron, verification, encryption]
metadata:
  hermes:
    tags: [backup, restore, disaster-recovery, cron, verification, encryption]
    related_skills:
      - devops/safe-update-restart
      - devops/service-health-monitoring
      - agent-kit/cron-truth-layer
---

# Backup and Restore Drills

## When to Use

- you are asked to back up a host, a volume, or the data directory of a running agent
- you are designing or auditing disaster recovery for a machine something depends on
- you are auditing whether an existing backup is real — a scheduled job existing is not evidence
- you are wiring or reviewing the cron job that is supposed to protect state overnight
- a bundle, its manifest, or its restore drill is missing and you have to decide what to add first

The deliverable is never "a backup job exists" — it is a bundle this session **opened and read a file
back out of**.

## The rule

**A backup that has never been restored is a hypothesis.** Ship three artifacts together, always: the
bundle, the freshness assertion, and the restore drill. Any one of them alone is decoration — a bundle
nobody checked, a check that only fires on error, or a drill that has never run.

## Procedure

### 1. Build an include list — never "everything"

Whitelist the state that must survive. Blacklist the trees that are reproducible or worthless: package
caches, installed dependencies, tool binaries, `node_modules`, logs, `*.wal` / `*.shm` / `*.lock`. A
bundle that is 90% reproducible cache is slower to make, slower to restore, and buries the state you
actually needed.

**Include the config and credential files.** They are inside the encrypted bundle, so including them
costs nothing and omitting them produces a restore that comes back up with no credentials — which is
not a restore, it is a rebuild with extra steps.

Print how many of the requested paths were present (`including : N of M`). A silently absent path is
how a backup quietly stops protecting one thing.

### 2. Encrypt, and state the key's failure domain out loud

```bash
tar -C "$DATA" -cf - $EXCLUDES $INCLUDES \
 | xz -T0 -3 -c \
 | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass "file:$PASS_FILE" -out "$OUT.part"
# then: check rc and non-empty, mv -f "$OUT.part" "$OUT", chmod 600
```

Generate the passphrase once (`openssl rand -base64 48 > "$PASS_FILE"`, mode 600). Build to a `.part`
name and `mv` into place — the bundle is read by other scripts, and rename is atomic.

**If the passphrase lives in the same directory or volume as the ciphertext, that is a single factor
wearing a two-factor costume.** It is tolerable ONLY while the bundle never leaves the host, and that
sentence belongs in the script header as a named residual risk — not left for a future reader to
discover. The upgrade path: encrypt each bundle with a random AES key, then wrap that key with an RSA
**public** key whose private half the human holds offline. The host then never holds a decryption
secret, and losing the host leaks nothing.

### 3. The manifest is the field that proves it ran

Append one JSON line per bundle: `ts`, `file`, `bytes`, `sha256`, include list, and `dest`. Append-only —
never rewrite it. This is what lets "did the backup run?" be answered without a message having been
delivered, and it is what the freshness check and any readiness gate both read.

### 4. Freshness check that asserts values, and alarms on ABSENCE

One row per assertion, each printing PASS/FAIL **with the observed value**, exiting non-zero on any
failure: bundle exists · age ≤ limit · on-disk hash equals the manifest hash · manifest parseable ·
key material present · off-host copy exists.

A check that only speaks on error cannot see the failure that matters most — a job that silently
stopped running. **Alarm on absence, not just on error.**

Keep the off-host row present while it is still a gap, and label it `GAP` with the consequence spelled
out. A gap that only exists in a code comment is a gap nobody acts on; a gap that appears in the output
of every run is a decision waiting to be made.

### 5. Restore drill — decrypt, list, extract, read back

```
openssl enc -d ... -in <newest> -out scratch/data.tar.xz   # 1. decrypt
xz -d -c ... > scratch/data.tar                            # 2. decompress
tar -tf scratch/data.tar > scratch/list.txt                # 3. count entries
# 4. assert REQUIRED paths appear in list.txt
tar -xf scratch/data.tar -C scratch <a required file>     # 5. extract one and PARSE it
```

Step 5 is the one that matters: **a listing is not integrity.** Extract a required file and actually
read it (parse the JSON, confirm it is what it claims to be). Clean the scratch dir with a
`trap ... EXIT`.

Log one line per drill — timestamp, PASS/FAIL, bundle name, entry count — so a readiness gate can
assert *"last PASS within N days"*. A drill with no record cannot be distinguished from one that was
disabled.

### 6. Watchdog wrapper: silent on success, and a log written EVERY run

A nightly job that reports success on success gets muted, and then it is not a watchdog. So: print
nothing when healthy, and prove health by the field — manifest row, heartbeat file, and a verify log
written on **every** run, pass or fail. The point: the gap must be a recorded field first, so a muted
message cannot hide it.

Failure paths are loud and non-zero. Distinguish three outcomes explicitly, because they need different
responses: backup failed (data at risk) · verify failed (bundle untrustworthy) · ship failed (still only
local).

### 7. Wire the off-host leg as a separate, gated step

Probe the remote cheaply first (`rclone lsd remote:`), and **exit 0 silently while it is not yet
authorized** — a pending human consent is not an error the script can fix, and a nightly nag about it
gets muted. Once authorized: copy, verify the remote by a hash the remote exposes (Drive exposes md5),
append a `dest:"off-host"` manifest row, prune the remote to N. Any *actual* ship failure is loud and
non-zero.

Keep the destination's identity separate from the agent's identity: a human-granted token to an account
the fleet does not control is the point, not an inconvenience.

### 8. Schedule it with pointers, not copies

See the pitfall below before wiring cron/loader script paths.

## ⚠️ Restoring a ledger is NEVER a merge — and "differs from the backup" is not a restore signal (2026-10-17)

A restore tool that copied the backup over any file whose live copy **"differed from the backup"**
silently wrote **older copies over newer files in 16 instances** — including an append-only ledger that
lost **74 unique entries**. The rule it broke:

> **For an append-only record, differing from its backup is the HEALTHY state — it is what appending looks like.**

Three rules, in order of how expensive the mistake is:

1. **LEDGERS ARE NEVER RESTORED.** `completions?*.md`, `completion-registry.json`, `pending-list.md`,
   `*-queue.md`, `*.jsonl`, any roster/inventory. **Restoring a ledger is a rollback with extra steps.**
   Their contract is "rows are appended, never rewritten" — a copy from any earlier point deletes work.
   A ledger's repair is a **UNION of both copies, deduped**, and it belongs to whoever owns the record.
2. **GATE ON MTIME, NOT DIFFERENCE.** Minimum bar:
   `if os.path.getmtime(dest) > os.path.getmtime(src): skip`. **"Differs" is not evidence of damage** —
   it is the normal state of anything living. A restore that overwrites a newer file with an older copy
   is not a merge.
3. **BACKUPS MUST BE NON-OVERWRITING AND DATED.** An unconditional `copy2` to a fixed `.bak` name means
   a **second run overwrites the good copy with the already-lossy one**, destroying the only recovery.
   `if not os.path.exists(bak): copy`, with a timestamp in the filename. The recovery that existed in
   the incident above survived **only because it was the first run** against that destination.

**Two corollaries worth carrying:**

- **`copy2` preserves mtime, so reverting your own damage is decidable rather than guessable.** A
  pre-change backup still carries the file's original timestamp; the newer of (backup, current) is the
  correct content. This is how you repair a rollback without guessing — and it is why the backup must be
  made *before* the write, not after.
- **Never revert a file another seat has repaired in the meantime.** In the incident, the owner had
  already union-merged the ledger back to health; a blind revert of "my damage" would have destroyed
  their repair. **Ownership decides who fixes it, not who broke it.**

### A SNAPSHOT is not a superset — set difference is the half mtime cannot see

**Mtime gating only compares files present in BOTH trees, so it silently blesses a snapshot that is missing whole
files.** Measured on a real recovery: a restore from a disaster snapshot carried **521 files** against the live
tree's **22** in one directory, so a size-and-count argument said the restore was richer. It was four weeks older
on the five files both trees held — and **two files existed only in the live tree**, written after the snapshot was
taken. A pure "newer wins" merge would have overwritten the five and **left the two absent**, producing a tree that
passed every mtime check while missing the newest work.

So a merge from any frozen copy runs **two comparisons and prints both counts**:

```
for each path in union(snapshot, live):
    only in snapshot          -> never copy over live; it is OLD by construction
    only in live              -> KEEP (post-snapshot work; report the count, do not touch it)
    in both, live newer       -> keep live; report
    in both, snapshot newer   -> copy snapshot -> live; report
```

- **Print the four buckets.** The number that matters is usually the second one — *"2 files exist only in the live
tree"* is the finding, and no mtime rule can produce it.
- **Prove it landed per file, with size and digest**, not by file count: a total that matches can hide one file
restored from the wrong side.
- **Verify the restored content references what the missing files added.** After copying the newer snapshot files
in, grep the restored document for the names of the live-only files; if they are absent from both trees' index the
merge is incomplete regardless of what the byte counts say.

### A backup directory can be a LABEL

A path named `backups/<date>/<project>` proves nothing about its contents. Measured: a sweep directory that looked
like a recovery point held **0 files** — it had been created as a target and never filled, and three reports had
cited it as coverage. **`find <dir> -type f | wc -l` belongs in every claim that a backup exists**, and a zero is a
finding to report, not a directory to skip.

## Pitfalls

- **Validating a backup by its job's exit code.** A green tick proves a script ran, not that its output
  is openable. The only proof is decrypting the newest bundle and reading a file out of it.
- **Passphrase next to its ciphertext.** One host loss takes both. Name it in the header and plan the
  public-key wrap.
- **Calling a local-only bundle a "backup".** It protects against corruption, a bad cron and human
  error — it does **not** protect against losing the volume or host. Say that in the script header and
  repeat it in the check output every run, or someone will plan around protection that is not there.
- **Restoring from off-host having only ever tested local.** The off-host leg has its own failure modes
  (auth expiry, partial upload, wrong remote path). Drill against the shipped copy, not the local one.
- **A required downstream path that must hold a real file.** A copy drifts (same filename, two
  behaviours, no alarm); a symlink is refused by path-validation as traversal. Use a thin `exec`
  pointer: a real file containing no logic, so there is nothing to keep in sync, forwarding `"$@"` so
  the exit code and stdout pass straight through and a silent-on-success wrapper stays silent.
- **Pruning as the only retention.** Keep N bundles on disk *and* N at the destination, and assert the
  destination count — a prune against an empty remote deletes nothing and confirms nothing.
- **Backing up the backup.** Excluding your own output directory from the include list is not optional;
  otherwise each bundle contains the previous ones and the growth is superlinear.

### An unenforced containment is not a containment — and an encrypted local backup is NOT an export path

Two failure modes that look like safety, both from gentech-treasury's credential triage of the
pre-wipe archive (624 MB / 35,817 files of archived **memory backups** holding ~540 credential-shaped
strings, including a live-format GitHub PAT).

**1. "It's contained" must name the mechanism, not the outcome.** The archive had never entered any
repo — `git ls-files` returned 0 paths under it, and `ob sync` (encrypted) was the only transport that
moved it. That reads like a property. **It was an accident.** Nothing *enforced* it: the repo's
`.gitignore` had no rule for the archive, so a single `git add -A` from a vault-rooted checkout would
have committed 624 MB and the whole credential corpus into permanent history — and deleting it
afterwards does not un-share it. **When you report containment, name the rule, the ignore pattern or
the gate that holds it. If you cannot name one, you have a coincidence, and coincidences do not
survive the next careless commit.** (Fix pattern: ignore the *thing*, not the domain — see the
Pixel 2026-09-28 correction where a blanket folder ignore was over-reach that blocked
unrelated work forever.)

**2. The encrypted local backup is the ONE path that must NOT be gated on "contains a secret."** A
secret-scanning gate belongs on **repo, export, publish and ship** paths. Applied to the nightly
encrypted bundle it is actively wrong: the bundle's job is to carry the whole brain — archive
included — so the gate either fails every night or forces excluding the archive, and excluding it
loses the brain. **The backup's control is encryption plus a destination policy** (`dest: local-only`),
**not content inspection.** Match the control to the path's purpose; a gate on the wrong path is a
nightly false failure that trains everyone to ignore it.

**Corollary — know the latent doors.** A ship-to-cloud script that exits silently while its credential
is absent is not broken; it is an armed path. Name it explicitly, and tell whoever grants that
credential what rides along (in that case: the whole encrypted vault, archive inside).

## ⚠️ "Restorable" ≠ "recoverable" — back up the CODE, not just the catalog (learned 2026-10-17)

**A backup that captures job *definitions* but not job *bodies* restores a schedule with nothing to run.**

Measured on this estate: the nightly backup wrote each profile's `memories/`, `SOUL.md`, `config.yaml`
and `cron/jobs.json` — **but no profile `scripts/` directory was ever included.** The consequence, when
the container was lost and the repos recovered:

| | |
|---|---|
| Job definitions recovered | **74 of 74** (they were inside the repo) |
| Distinct script bodies referenced | 47 |
| Script bodies recovered | **26** |
| **Script bodies recoverable from nowhere** | **20** |

So a `jobs.json` gets you the schedule, the name and the intent — **never the code.** Six of the
recovered jobs were *crown* jobs (money/truth/safety) whose bodies are simply gone and must be
**re-derived, not "restored."**

**Rules:**
- **A manifest is not a backup.** If your restore procedure says "read the job list", ask what runs the
  jobs. Back up the thing that executes, or admit the backup is a catalog.
- **Prompt-only work survives; script-driven work does not.** Jobs whose behaviour lives in their
  `prompt` field are fully reconstructible from the definition file. Jobs pointing at a script path are
  recoverable only if a copy happened to land somewhere else. **Know which of your jobs are which** —
  it tells you exactly how much of a loss you are looking at.
- **Check the backup's *exclusions* before believing the backup.** This one had a documented redaction
  step for credential literals and was still, correctly, "working as designed" — the design just
  covered less than the reader assumes.
- **State the snapshot date, and treat it as the ceiling.** The recovered estate's newest snapshot was
  **13 days before the loss**; everything in that window is invisible. A restored job list is
  **"as of <date>", not "as it was."** Say the date out loud wherever you quote a count from it.
- **A missing file and a never-created file look identical.** Before reporting "X was lost", prove X
  ever existed — and if you have a shallow clone, **`git fetch --unshallow` first.** One seat turned
  "no jobs found" into a proven fact across **209 commits**, which is a different claim from "the
  search returned nothing."

## Related

- `references/offline-recovery-recon.md` — what to do when you are called in *after* a loss and no
  usable backup exists yet: the order to establish what survived before planning anything.

## tar --exclude patterns match MEMBER names — a leading './' excludes NOTHING (found 2026-10-16)

`backup-data.sh` had **every** exclude written as `--exclude='./profiles/*/cache'` while the archive was
built as `tar -C "$DATA" -cf - profiles …`, so member names were `profiles/…` and **every exclude silently
matched nothing.** The nightly bundle carried ~400 MB of reproducible cache (Treasury's cache alone: 346 MB)
and the "only copy we have" was 20% garbage, growing daily.

**Measured before/after on the uncompressed stream: 2,596 MB → 2,078 MB — 519 MB trimmed per run.**

### Rules
- **Never prefix a tar `--exclude` with `./`.** Match the member path as tar stores it. If the build is
  `tar -C /dir -cf - subdir`, the pattern is `subdir/...`, not `./subdir/...`.
- **Prove an exclude empirically — never eyeball it.** Two lines settle it:
  ```bash
  tar -C "$SRC" -cf - --exclude='<pattern>' <path> 2>/dev/null | tar -tf - | grep -c '<excluded-leaf>'
  # 0 = it works. Anything else = the pattern is dead and you are backing up garbage.
  ```
- **A backup that is too big is a backup that will not be restored.** Size is a correctness property here:
  it is the only copy, it must move off-host, and every megabyte of cache in it costs transfer, time, and
  attention.
- **A no-op guard is worse than no guard** — it reads as protection while providing none. This is the same
  failure class as a test that passes because it never runs.
