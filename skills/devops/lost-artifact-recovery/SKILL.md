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

**⚠️ A `find` bounded to one filesystem answers "is it here", not "does it exist".** `-xdev` (and any
single-mount traversal) crosses no boundary, so an artifact on a second mount returns **zero hits that read
exactly like absence**. Measured: three scripts were absent from the notes tree *and* from a `find / -xdev`
sweep, yet present on another mount that sweep never entered. Enumerate the roots and mounts **before** a
search is called conclusive, and re-run without the boundary before reporting a loss.

**A sync/merge manifest is an inventory of what was stranded, not only of what moved.** When a tool records
entries as `plan.SKIP` alongside a `path`, it has named files it deliberately did not carry — so a grep for
the basename across `*merge-manifest*.json` is a cheap index to the lost set, and it survives when the file
itself does not. Those `SKIP` rows also explain *why* the artifact vanished without anyone deleting it.

**Match the recorded digest, not the filename.** A record that quotes an md5 is the strongest available proof
that a restore is the same artifact rather than a same-named rebuild: `md5sum` the candidates against it and
report the match per file. A same-named file in a recovery tree is a candidate, not the original.

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

### 4b. A RESTORE IS NOT THE NEWEST COPY — diff the file SETS, not the trees

A recovery tree comes from a dated snapshot, so it can be **older than a copy that survived on the box**, and it
can be **missing files that only the surviving copy holds**. "I restored it, sha256 verified" proves the copy is
internally intact; it says nothing about being complete. Before calling a restore canonical:

```bash
# 1. FIND every copy, including the ones whose directory name looks like a backup
find / -maxdepth 6 -type d -name '<tree>' 2>/dev/null
# 2. per copy: file count, total bytes, newest mtime
# 3. per-file sha256 of each copy, then: only-in-A, only-in-B, content-differs
```

- **`only-in-X` is the decisive number, and it is not an age question.** A file present in one copy and absent
  from the restore is not "older" or "newer" — it is the **only** copy, and a restore that silently omits it
  loses it the moment the snapshot is treated as authoritative. Report those filenames first, by name.
- **A restore's mtimes are the restore's own timestamp.** Do not rank copies by mtime; rank by content hash and
  by **set membership**. (Same trap as §4: a bulk copy stamps everything at the moment it ran.)
- **A `backups/<date>/` directory is a label until it is counted.** An empty one — 0 files, 0 bytes — reads as
  protection in every listing and protects nothing. Print the file count, not the path.
- **Cross-copy newer-ness is real and it runs both ways.** A tree synced into a notes vault can carry edits made
  *after* the snapshot: an extended document, a patched script, a state file rewritten. When the surviving copy
  is newer on N files and holds M files the snapshot lacks, the honest answer is "the restore is not a superset —
  merge these M files in and diff these N", said before anything writes over the other copy.
- **Report the comparison as a table** (copy · files · bytes · newest · only-in · differs). A restore claim with
  no such table is a claim about one directory, not about the tree's coverage.

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
- [ ] Version choice is justified by content provenance, not size or mtime.
- [ ] Every other copy of the tree was sha256-diffed: `only-in` files are named before the restore is called complete.
- [ ] Any `backups/<date>/` copy was verified by file count, not by its directory name.
- [ ] Anything proposed for removal was probed for being the sole copy first.
- [ ] Rebuilt artifacts are committed in the same session, and the secrets gate was proven to fire.

## Support files

- `references/clone-and-auth-diagnostics.md` — the control-clone ladder, namespace traps, header formats, and
  how to test a credential without leaking it.
