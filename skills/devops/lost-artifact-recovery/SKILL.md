---
name: lost-artifact-recovery
description: "Use when code or data is reported lost; recover it first."
version: 1.0.0
author: Gentech
license: MIT
tags: [recovery, backup, git, data-loss, restore, scope]
metadata:
  hermes:
    tags: [recovery, backup, git, data-loss, restore, scope]
    related_skills: [pre-deletion-inventory, source-of-truth-verification, backup-and-restore-drills]
---

# Lost-Artifact Recovery

The expensive mistake is not failing to find something that was lost. It is **rebuilding it from scratch while
the original sits in an off-host copy nobody probed.** A rewrite costs a session and produces a worse artifact
than the one already sitting in a repo.

Recovery is read-only until the very last step. Nothing here authorises deleting anything.

## When to Use

- **A loss is reported** — a wipe, a bad sync, a delete, a dropped deploy, or a note asserting "we have no
  backups" / "every script behind this is gone".
- **Before rebuilding anything a wipe destroyed.** Run step 2 first; rebuilding over a recoverable original is
  the failure this skill exists to prevent.
- **Before deleting or pruning something as redundant** — especially a large archive inside a sync tree, and
  especially when the only stated reason is a layout or policy rule rather than its contents.
- **After any restore**, to close the coverage gap restores create (step 6).
- **When a clone or fetch fails** and you are about to conclude the artifact is gone.

## Procedure

### 1. Treat "gone" as a claim with an UNSTATED SCOPE

A loss claim is only as wide as the place it was measured, and the scope is almost never written down.
"Every script behind these jobs: gone" can be true of the machine and false of the fleet — if the probe
walked the local filesystem and never asked the off-host copies.

**Before acting on or propagating a loss claim:**

- Ask **where did this probe look, and where did it not?** A provenance marker on the claim ("measured")
  usually certifies the *method*, not the *breadth*.
- **Never widen a scoped claim into a fleet-wide one.** Write the scope into the sentence:
  gone **from this host** is a different statement from gone.
- **A local artifact missing a whole class of files is evidence about the local copy, not the source.**
  A deliberately partial local mirror — notes synced, code kept in a repo — looks identical to data loss
  under a naive diff. When the "lost" thing is code and the local tree syncs notes, suspect the mirror
  before the catastrophe.

### 2. Enumerate the off-host copies — this is the whole job

Do this **before** writing a single replacement line.

**Enumerate the copies from the HOST, never from a list you wrote down.** A hand-maintained "repos we
own" list is exactly how an off-host copy sits unnoticed for weeks — the escape is a repo nobody
remembered, not a repo that vanished. Ask the provider and read the result as data:

```bash
# every repo, as data — never a hardcoded list
curl -s -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user/repos?per_page=100&affiliation=owner&sort=pushed" \
  | jq -r '.[] | "\(.name)\t\(.private)\t\(.pushed_at[:10])\t\(.size)"'
```

**Then inspect a repo's file tree WITHOUT cloning it.** One API call, no disk — and it is how you find the
single file you need inside a 150 MB repo:

```bash
curl -s -H "Authorization: Bearer $TOK" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1" \
  | jq -r '.tree[] | select(.type=="blob") | .path'
```

Clone only what the tree said was worth cloning. A name-pattern pass over those paths sweeps an entire
account cheaply for the classes that matter (state files, manifests, credential-shaped names) — **but state
the blind spot out loud: it matches names, not contents, so an unremarkably-named file is invisible to it,
and a tree listing shows current HEAD, not history.**

```bash
# Every git remote that could hold it. git is FREE: zero API quota, no rate limit.
git ls-remote https://github.com/<owner>/<repo>.git

# Clone it shallow and count what actually came back.
git clone --depth 1 <url> /tmp/recovered-<repo>
find /tmp/recovered-<repo> -name '*.py' -not -path '*/.git/*' | wc -l
```

**A `--depth 1` clone proves nothing about history.** It answers "is it in the tip", which is a different
question from "did it ever exist". Before concluding a thing was **never** there — as opposed to lost —
`git fetch --unshallow` and search **all** commits. Also check whether the backup trail has an end date:
a repo whose newest commit predates the incident by weeks is a snapshot of that date, **not** of the moment
before the loss, and anything that changed in the gap cannot be proven from it at all.

Then **name the recovered artifacts individually** — the value is in the list, not the total:

```bash
find <clone> -name '*<keyword>*' -not -path '*/.git/*' | sed 's|^|  |'
```

Run the keyword sweep per subsystem (`arb`, `executor`, `recenter`, `classifier`, `watchdog`, `keystore`) — a
recovered tree answers "what existed", which is the input to every later decision.

**A cron `jobs.json` or similar definition archive inside a backup repo is the highest-value single find**: it
carries schedules, script names and prompts — i.e. the map — when the code itself is incomplete. **But a map
is not the territory.** Definitions are cheap and usually live in a git-tracked config; the *bodies* they name
are the work and are often in a path no include list ever covered (a profile `scripts/` dir outside every repo
is the common case). So on finding a manifest, immediately enumerate **every `script:` field it names against
the filesystem** and report the three-way split: **body present · body replaced under another name · body
gone.** Expect all three, and do not let one recovered config file stand in for a recovered estate.

The consolation prize is real: for **prompt-only** jobs the prompt *is* the implementation, so those survive
wherever the config survived — which is usually a large fraction of a job list, and worth stating so nobody
re-derives them as code archaeology.

Also enumerate **backup stores, nightly archives, and any tarball/archive directory on the host**, and compare
a large archive against the repos before treating it as redundant (step 5).

### 3. Prove it with a read-back, not the tool's own word

A write tool reporting success is a claim about the *request*. Verify the *state* from a second direction:

- After a `git push`, re-read the remote path and count the files that came back. Do not report a push from
  the push's own output.
- Report the **verify step as part of the result**, and quote what it returned.
- **A push of a branch name that does not exist fails benignly** (`src refspec main does not match any`) — the
  remote's default may be `master`. Rename or push the branch that exists; do not conclude the remote is broken.

### 3b. A restore is a bulk copy with three proofs — hash, parse, manifest

**Restoring the files you think you need produces a tree that cannot run.** A recovered module's imports, test
fixtures and data files are part of the artifact; cherry-picking the obvious entry point is how a restore becomes
a rewrite by accident. **Copy the whole subtree, then prove it.**

Three proofs, in this order, and none of them is "the copy command returned 0":

1. **Hash every file against the source.** A byte-for-byte `sha256` comparison with a zero-mismatch count is the
   only evidence the copy is the original and not a truncated or re-encoded relative.
2. **Parse every file you restored.** A restored `.py` that cannot compile is not restored — it is a file with the
   right name. Run the language's own syntax check on each one, and treat any failure as an incomplete restore
   rather than a cosmetic warning.
3. **Write a manifest** (`{path, bytes, sha256}` per file, plus source, timestamp and mismatch count) next to the
   restore, outside the artifact tree. A later reader must be able to audit what was copied without trusting the
   session that copied it.

**Restore OUTSIDE the note-sync tree.** Recovered code inside a synced vault bloats the sync and can trip its
size limits — the same rule as the backup shape below, applied at the moment it matters most.

**Then state the next action correctly: a restored artifact needs a RUN, not a build.** If a queue row named it,
the row does not become `shipped` on restore — it stays open until something executes it and returns a result.
*Built, restored, and never executed* is its own state, and collapsing it into "done" is how a dead tool reads as
working.

### 4. Choose between versions by CONTENT PROVENANCE, never by size or mtime

When a recovered copy and a local copy both exist, "which is newer" is not answerable from the filesystem:

- **mtime from a fresh clone is the CLONE time.** A bulk clone stamps every file with the same instant, so
  every recovered file looks brand new. Use history instead:
  `git log -1 --format='%ad %s' --date=short -- <path>`.
- **Bigger is not newer.** A large recovered script and a small local one can be, in that order, the
  *pre-incident original* and its *post-incident reconstruction*. "Take the latest" cannot be decided from size.
- **Read both provenance headers** (docstring, header comment) before choosing. A rebuild usually says so, and
  says what it could not do — that note is the reason it is smaller.
- **A larger original that depends on inputs which no longer exist cannot run, and a smaller one that reads
  what exists can.** Comparing line counts picks the wrong one. Check the recovered version's declared inputs
  against the host, and prefer the **merge**: the recovered decision logic running on feeds that exist, with
  the rebuild's honesty about what is missing.
- **FILE COUNT IS NOT AUTHORITY — the same trap one level up, and it is the one that bites.** A snapshot restore
  routinely lands as a huge superset (hundreds of files) next to a small live tree (tens), which reads as
  "the restore is clearly the fuller, better copy." It is not: the small tree can be **newer on several files
  and contain files the snapshot cannot possibly hold** — anything written *after* the snapshot was taken.
  Declaring the restore canonical then silently shadows post-snapshot work.

  **So a restore is a MERGE, never a replacement. Before treating a restored tree as authoritative, walk the
  existing tree and produce two lists:**

  ```bash
  # 1) files the restore DOES NOT HAVE at all (post-snapshot additions)
  for f in $(cd "$LIVE" && find . -type f); do [ -e "$RESTORE/$f" ] || echo "ABSENT: $f"; done
  # 2) files the LIVE tree has NEWER than the restore
  for f in $(cd "$LIVE" && find . -type f); do
    [ -e "$RESTORE/$f" ] && [ "$LIVE/$f" -nt "$RESTORE/$f" ] && echo "NEWER: $f"
  done
  ```

  **The live tree wins on both lists; everything else comes from the restore.** Then prove the merge took by
  checking a *content* fact, not a byte count — a restored document that "references neither amendment" (0
  matches) is the tell that you copied the pre-amendment version. Write the merge decision, with both lists,
  to the manifest so the next reader can audit it.

- **A backup directory can be a label rather than a copy.** A timestamped, plausibly-named backup path that
  contains **0 files** passes every name-based check and fails the only one that matters. Count the files
  inside a candidate backup before citing it as coverage — and report a zero as a finding about the backup
  regime, not as an absence of the artifact.

### 5. A sole copy is not waste — verify before anything is removed

A large archive inside a sync tree can be, at once, the biggest violation of the layout rules **and** the only
copy in existence. Those are independent facts, and cleanup is exactly where they diverge.

- **Probe whether it exists anywhere else before proposing a move or delete.** If it is the sole copy, the
  answer is not "prune it" — it is "land it somewhere durable first".
- **Order: preserve → verify → remove.** Never remove → discover.
- **Fix the shape without destroying the content:** a **tarball committed to a repo** beats committing tens of
  thousands of loose files — one object, compresses hard, avoids a huge loose-object push.
- **"Probably redundant" is a reason to measure the overlap, not a licence to destroy the only copy.**

### 6. Close the asymmetry: back up what you rebuilt, in the same session

The freshest work is routinely the least protected. A restore rebuilds from *old* sources, so the new code
lands on the box that was just rebuilt and in no repo, while the repo still holds the pre-incident tree.

**After any recovery, diff local artifacts against the remote before assuming the backup is current:**

```bash
# names present locally that appear in no recovered repo = the unprotected set
comm -23 <(find <local> -name '*.py' -exec basename {} \; | sort -u) \
         <(find <clone>  -name '*.py' -exec basename {} \; | sort -u)
```

The gap runs the dangerous way: custody/security code written after the incident is the most likely to be
box-only. **Back the rebuilt artifacts up in the session that produced them**, not after the next incident.

## Keeping the backup shape right

- **Code in a repo, notes in the note-sync — never code inside the note sync.** A code tree inside a synced
  notes vault bloats the sync (size and time both), and the repo is the surviving copy of the code anyway.
  When a user states this split, it is a standing convention: **do not "fix" a local notes mirror that lacks
  code.** That absence is the design.
- **Check whether the destination repo already exists before creating one.** Repo creation is churn, and churn
  is the documented way an account gets flagged. Probe for an existing lane first; a parallel repo fragments
  the record.
- **Private by default for strategy / engine code.** A publishable-face repo is a separate, sanitised thing —
  a scanner published as a tool is promotion; the rebalancer and classifier are the engine.

## Pitfalls

- **A failed clone is not evidence of loss until a control clone succeeds.** `remote: Repository not found`
  and an anonymous `404` are byte-identical whether the repo is gone, hidden, or **addressed under the wrong
  owner** — user vs org names often differ by one character. Run an anonymous clone of a stranger's
  well-known repo in the same batch: if that works, git and the network are fine and the cause is the path.
  Read `owner.login` / `full_name` / `clone_url` off data you already fetched rather than guessing the
  namespace. See `references/clone-and-auth-diagnostics.md`.
- **A wrong auth header looks exactly like a dead credential.** git-over-HTTPS wants
  `Authorization: Basic base64(x-access-token:<token>)`; a `Bearer` header there fails and reads as an invalid
  token. Before declaring a credential dead, re-issue the request in the format the tool expects.
- **Do not put a token in `argv`.** It lands in the process list. Pass secrets via a `chmod 600` config file
  (`GIT_CONFIG_GLOBAL=`, `curl -K` header files) and delete it in the same command.
- **A verification gate that always trips is worse than none** — it teaches the operator to ignore it. A shell
  pipeline's exit status is its LAST command's, so `if grep … | head; then` tests `head` (always 0) and fires
  on a clean tree; `cmd | tail || fallback` never runs the fallback for the same reason. Use `grep -q` with no
  pipe, or read `${PIPESTATUS[0]}`. **Then plant the defect the gate is meant to catch** (a fake secret of the
  exact shape the pattern matches) and watch it go red — a gate never driven red is a decoration.
- **Nothing leaves without a secrets sweep first**, covering the shapes that matter: private keys, 64-hex
  keys, provider token prefixes, and `.env` / `keystore*` / `*secret*` filenames. Run it as a gate that blocks
  the push, and record that you ran it.
- **Recovered archives can carry credentials.** A nightly profile/backup repo may contain cron job definitions
  and prompts — job configs are a credential surface. Audit before trusting an archive as a restore source.

## Verification

- [ ] The loss claim's scope is stated, and off-host copies were enumerated before any rewrite.
- [ ] Recovered artifacts are named individually, not just counted.
- [ ] Every write is verified by reading the target back, not by the writer's own status.
- [ ] A restore is the whole subtree, hash-verified with zero mismatches, parse-checked file by file, and recorded in a manifest outside the tree.
- [ ] A restored artifact is not reported as working until something has RUN it.
- [ ] Version choice is justified by content provenance, not size or mtime.
- [ ] Anything proposed for removal was probed for being the sole copy first.
- [ ] Rebuilt artifacts are committed in the same session, and the secrets gate was proven to fire.

## Support files

- `references/clone-and-auth-diagnostics.md` — the control-clone ladder, namespace traps, header formats, and
  how to test a credential without leaking it.
