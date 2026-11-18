---
name: agent-state-disaster-recovery
description: "Use when protecting or restoring the agent's own state."
version: 1.0.0
author: gentech
license: MIT
tags: [backup, disaster-recovery, restore-drill, keys, custody, cron, vault]
trigger: "Backing up the agent's state volume, building or auditing a backup job, running a restore drill, or recovering after keys/state were lost."
metadata:
  hermes:
    tags: [backup, disaster-recovery, restore-drill, keys, custody, cron, vault]
    related_skills: [cron-health-standard, destructive-write-guards, verify-after-every-action]
---

# Agent State Disaster Recovery

The agent's own state — every profile, memory, cron job, skill, session and credential — sits on a
single mounted volume on a single host. Protecting it is a class of work with its own procedure,
and the failures that turn one incident into total loss are structural, not accidental.

## When to Use

Load this when any of the following is true:

- Backing up, verifying or drilling a restore of the agent's state volume.
- Registering or auditing a scheduled backup job.
- Recovering after a host rebuild, a wiped volume, lost keys, or a provider/account action that
  removed access to something.
- Someone asks "can we get X back?" — the taxonomy below turns that into an answerable question with
  a stated confidence, instead of a hopeful guess.

## Always-on rules

- **No key, and no state volume, may exist in exactly one place.** Not "backed up regularly" —
  single-copy is the failure. A backup that lives on the same host is a point-in-time copy, not a
  backup, and must be labelled that way in output.
- **A backup that has never been restored is a hypothesis.** Ship the drill with the backup, in the
  same change. Until a bundle has been decrypted and read back, no claim about it is supported.
- **Ciphertext must never travel with its passphrase.** A `.enc` file and a sibling `.passphrase`
  in one directory, on one host, is a single factor wearing the costume of two. The host must never
  hold a decryption secret for anything that leaves it.
- **An off-host copy on the same identity is not off-host.** If the backup target depends on the
  same account, token or provider as everything else, one account action takes both. The destination
  must be a deliberately different identity.
- **Silence-on-success is only valid when a FIELD proves the run happened.** A job that prints
  nothing when healthy is indistinguishable from a job that stopped running. Pair every silent job
  with a durable artifact — an append-only manifest line, a heartbeat file, a drill log — and say
  which field is the proof. Never treat an absent message as evidence of health.
- **Name the gap in the output, every run.** A scan that reports PASS while an off-host copy does
  not exist is lying by omission. Print the missing leg as a named gap on each run so it cannot
  become invisible through repetition.
- **Never move a credential through chat to fix a backup.** Secrets are written to a file the user
  controls or supplied at runtime; the host reads the file. Anything pasted into a conversation is
  rotated afterwards, not used.

## The failure taxonomy — what turns one incident into total loss

Diagnose any incident against these, and design against all three. They compound, and the first is
rarely the one that hurts.

| | Failure | Mechanism |
|---|---|---|
| **F1** | Single-host custody | Every key, config and session on one filesystem. One host event has one blast radius. |
| **F2** | Ciphertext and its passphrase co-located | Directory permissions defend against other local users and against nothing else. |
| **F3** | Backup that depends on the primary's own identity | A provider hold, token death or account action removes primary and backup together. |
| **F4** | The inventory was also lost | Losing keys is recoverable; losing the *record of which keys existed* is what makes a rebuild impossible. Keep the credential inventory in the notes store, never only in the host's config. |
| **F5** | The references survived, the machinery they name did not | Restoring files restores nothing that *calls* them. Skills keep citing scripts, docs keep citing paths — instructions nobody can follow, silently, because the file that loads fine is the file that lies. Audit references, not presence. |

The asymmetry to build on: a written inventory of what existed converts a rebuild from archaeology
into a checklist. Protect it as deliberately as the key material.

## Procedure

1. **Inventory what must survive, and exclude what is reproducible.** Measure the volume first
   (`du -sh <dir>/*`) and whitelist: notes store, profile configs, memories, skills, cron jobs, the
   session/state databases, scripts. Exclude caches, vendored packages, runtimes and logs — a
   bundle padded with reproducible trees trains nobody to restore it.
2. **Build the bundle as a pipeline, and fail closed.** `tar | xz | openssl` with `set -o pipefail`,
   writing to a `.part` file and renaming only on success. A partially written bundle that looks
   like a backup is worse than none.
3. **Append a manifest line per run — never rewrite it.** JSON per line: timestamp, filename, bytes,
   sha256, path count, encryption scheme, and a `dest` field that states honestly whether this copy
   is `local-only` or `off-host`. The `dest` field is what makes the gap machine-detectable.
4. **Prune by count, not by age**, and print what was pruned. Silent pruning eventually removes the
   copy you needed.
5. **Verify with an absence alarm, not an error alarm.** A separate script asserts values and prints
   them every run: bundle exists, age under the limit, on-disk hash matches the manifest, manifest
   parses, decryption material present. An error-only monitor cannot see a job that stopped running.
6. **Drill the restore.** Decrypt the newest bundle into scratch, decompress, list entries, assert
   REQUIRED paths are present, then extract one file and parse it — listing is not proof of
   integrity. Append a PASS/FAIL line to a drill log so a gate can assert "last drill under N days
   and passed".
7. **Schedule both, and prove the scheduled path.** Nightly for the backup+verify, weekly for the
   drill. Then fire the job once on demand and confirm it by reading the FIELD (a new manifest line,
   a heartbeat timestamp) — not by waiting for a message, because a healthy silent job sends none.

Working scripts for this fleet live at `/opt/data/scripts/`: `backup-data.sh`, `backup-verify.sh`,
`restore-drill.sh`, with `backup-nightly.sh` and `backup-drill-weekly.sh` as the silent cron
wrappers. Reuse them rather than rewriting the pipeline.

## Registering the backup jobs

- Register with `no_agent: true` and a wrapper script that prints **only on failure**; the scheduled
  proof is the manifest/heartbeat/drill-log, not stdout.
- **A cron `script` must be a real file inside the profile's `scripts/` directory.** A symlink that
  points outside it is rejected at creation with a traversal error, even though the target runs
  fine when invoked by hand. Use a **thin wrapper** — `exec /opt/data/scripts/<name>.sh "$@"` — so
  one canonical implementation serves both the profile path the validator requires and any other
  caller. Copying the file instead creates two versions that drift, and the drifting copy is the one
  that gets executed.
- A bare filename may resolve at runtime from a shared scripts directory that the create-time
  validator does not check, so a job can exist and work while an equivalent new job is refused.
  Match an existing working job's shape before concluding the path is wrong.

## Off-host: wrap, do not share a secret

Before the first bundle leaves the host, replace passphrase encryption with hybrid wrapping:

1. Generate a random key per bundle; encrypt the bundle with it (AES-256).
2. Wrap that key with an **RSA public key** whose private half the user holds offline.
3. Store only the public key on the host.

This is the property that matters: a compromised or lost host exposes ciphertext and a public key,
and nothing else. It is the one design that satisfies F2 instead of renaming it.

The user generates the keypair on their own machine and supplies only the public half — never send a
private key through chat, and never ask for one there.

## Auditing a restore: references, not presence

After any state loss, "the files are back" and "the estate works" are different claims and only the
second one matters. Enumerate what the surviving artifacts **point at**:

- grep the skills tree for the script paths its instructions invoke, and check each one exists. A
  skill whose script is gone loads perfectly and dies on its first command.
- grep the notes store for absolute paths and count how many name a location that no longer exists.
  Report that number; it is the size of the documentation that currently cannot be followed.
- check the *mechanisms*, not just the content: a distributor/sync tool that propagated changes
  between seats is worthless to have lost, and its absence is invisible until an edit fails to
  travel. Anything that makes future fixes stick is a first-class restore target.

Then fix drift deliberately, not with a blind find-and-replace across the store:

- **Rewriting every occurrence also rewrites history.** Incident write-ups correctly describe where
  things *used* to be; overwriting them falsifies the record. Write one canonical old→new map, fix
  the operational instructions, and mark the rest as history in place.
- **Measure "no remaining instruction is unfollowable", not "references reduced to zero".** The
  translation table legitimately contains the old paths, so a raw absolute count can rise while the
  migration is going correctly. Counting the wrong thing turns success into an apparent regression.

## Pitfalls

- **Reporting "we have a backup" because the job exists.** A job that was never proven by its field
  is a configuration, not a backup. Read the manifest.
- **Treating a directory timestamp as evidence that a lost directory survived.** Listing a parent
  directory shows when entries were added or removed there, not whether a subtree's contents still
  exist. It is a weak signal at best; state it as weak, and get a real listing of the target path
  before offering it as hope.
- **Concluding a path is gone because the agent cannot read it.** A permission-denied read and a
  missing directory are different results and only the user (or root) can distinguish them. Ask for
  the one command that settles it rather than reporting either conclusion.
- **Assuming the credentials died with the host.** Off-host copies of a service config, a template
  `.env`, or a pre-migration backup directory can look like a recovery lead and be only a stock
  template. Read the shape of the file, not just its name, before announcing a find.
- **Recovering infrastructure around an empty wallet.** Stand up custody machinery for capital that
  exists. Building threshold authority around a near-zero balance is theatre; sequence the rebuild
  by what actually holds value.

## Reporting

- Give the numbers the run actually produced (bytes, hash prefix, entry count, age) and label which
  are verified versus designed.
- State gaps as gaps, in the same message as the wins, with the one action that closes each.
- When an earlier claim of yours turns out to be wrong, correct it explicitly and say what the
  evidence really supports — an uncorrected earlier statement is inherited by the next session.
