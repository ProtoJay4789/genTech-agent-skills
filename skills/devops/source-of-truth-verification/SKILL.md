---
name: source-of-truth-verification
description: "Before changing a running service or scoping a task, confirm you are looking at the artifact that actually runs and that the capabilities the task assumes actually exist. Covers locating live source via /proc, detecting stale mirrors, and verifying capability claims in queue items and specs."
version: 1.0.0
author: gentech
tags: [devops, verification, deployment, pre-flight, debugging]
---

# Source-of-Truth Verification

Two failure modes that both produce the same outcome — work that looks shipped
but changed nothing:

1. **You edited a stale mirror**, not the code that actually runs.
2. **You scoped off a capability claim** that turned out to be aspirational.

Both are cheap to prevent and expensive to discover late. Run these checks
before the first edit.

## When to Use

- Any change to a running service (API, gateway, daemon, worker)
- Any task scoped from a build queue item, spec, handoff, or prior session note
- Any time a task description says "config-only", "already supports X", "just
  needs a flag"
- When a fix you applied appears to have no effect in production
- When live behaviour disagrees with the code you're reading

## Part 1 — Find The Code That Actually Runs

A single service commonly has 3-5 copies on disk:

- `/opt/data/.obsidian-vault/<vault>/10-Labs/<svc>/` — vault working copy
- `/root/<user>.github.io/10-Labs/<svc>/` — portfolio mirror
- `/root/repos/<svc>/` — clone
- `/opt/<svc>/` — deploy copy

They drift. Only one is what systemd actually launched.

### The resolution sequence

```bash
# 1. Which process owns the port?
ps aux | grep -i "<port>\|<service-name>" | grep -v grep
# or
ss -lptn "sport = :<port>"

# 2. Ask the kernel where it runs from — authoritative
readlink /proc/<pid>/cwd

# 3. Confirm against the systemd unit
systemctl list-units --type=service | grep -i <name>
systemctl cat <service> | grep -E "WorkingDirectory|ExecStart"
```

`readlink /proc/<pid>/cwd` is the single most reliable command here. It reports
the real working directory of the live process regardless of how it was started,
what symlinks exist, or what the unit file claims.

### Cross-check before editing

Compare live behaviour against the file you're about to modify:

```bash
curl -s http://127.0.0.1:<port>/status | python3 -m json.tool
grep -c "<known-service-name>" <candidate-file>
```

A mismatch in counts, feature names, or version strings means you found a
mirror. Go back to step 2.

### Cross-check the running executable for interpreted services

For Python / Node / Go services, the code that runs is often **installed**, not
the checkout in `~/repos/` or the vault. A stale checkout can be months behind
while `pip install -e .` or a system package runs a different copy.

```bash
# 1. PID from the live service
PID=$(pgrep -f "<service-name>" | head -1)

# 2. The actual executable the process launched from
readlink /proc/$PID/exe

# 3. The path the interpreter believes it is serving from
python3 -c "import hermes_cli; print(hermes_cli.__file__)"
```

If `readlink /proc/<pid>/cwd` points at a checkout but the live import resolves
to `/usr/local/lib/...` or `~/.local/lib/...`, **you are reading a mirror**.
The version string or mtime on the installed file is the reliable signal — a
checkout's `git log` is irrelevant if nothing reloads from it. Edit the file the
live process is actually importing, or redeploy after editing the checkout.

## Part 2 — Verify Capability Claims Before Scoping

Queue items, specs, and handoffs assert things like "config-only", "already
multi-chain", "just needs a flag flipped". **Treat every such claim as an
unverified assertion.** They are often aspirational — written when someone
intended to build it that way, or describing a design that was never finished.

```bash
grep -n "<the-thing-claimed-to-exist>" <source-file>
```

If the claim is false:

1. Say so plainly in the completion note — don't quietly paper over it
2. Then make it true
3. Only then mark the item shipped

Do **not** scope the task off the claim and mark it shipped. That produces a
queue that lies about what exists, which compounds — the next task scopes off
*your* note.

## Part 3 — State Files: Liveness Is Not In The Name

State files are the same problem from the opposite side. A filename that *sounds*
authoritative — `.steward-fee-ledger.json`, `.fee-ledger-jordan.json`,
`lp-monitor-v2.py` — tells you nothing about whether anything currently writes or
reads it. Two files with the same basename in different trees can disagree by
orders of magnitude, and the tree gives no hint which copy is canonical.

**The three liveness classes:**

| Verdict | Definition | Why it matters |
|---|---|---|
| **LIVE** | A script or cron job names the file, and it has been written recently. | The file is doing work. Do not treat it as dead. |
| **STALE** | A script or cron job names the file, but it has not been written recently. | The producer may be stuck, retired, or mis-scheduled. Investigate the producer. |
| **ORPHAN** | No script or job names the file, regardless of mtime. | A fresh orphan is worse than a stale live file — it has no discoverable producer. Do not delete until you know what wrote it. |

**The divergent-copy hazard:** same-named state files often live in both a profile
scripts directory and a synced vault. A cron job may write the profile copy while
the vault copy is only touched by sync. The two copies can diverge by 400% or more
with no record of which one is authoritative. An audit that picks the wrong member
of the pair reaches a wrong conclusion without ever knowing it had a choice.

**The fix is a liveness registry, not deletion.** Before acting on a "dead file"
claim, run a read-only probe that reports, for every state file: who names it
(scripts + cron job definitions), how fresh it is, and whether copies agree. Use
that output as the input to a decision. See `references/state-file-liveness.md`
and `scripts/state-file-liveness.py`.

**A dead file is evidence, not debris.** A state file with no producer may be the
only record that a job was once scheduled. Deleting it destroys the evidence
before you know what retired. Archive or annotate before removal.

## Worked Example — x402 Gateway, Aug 4, 2026

Both failure modes fired in a single task.

### Stale mirror

| Check | Mirror (`gentechlabs.github.io/10-Labs/x402-gateway/`) | Live (`vaults/gentech/10-Labs/x402-gateway/`) |
|---|---|---|
| Services defined | 7 | 8 (adds `lineage_guard`) |
| `/status` health path | `f"{url}/health"` where `url` is a 3-tuple → always `down` | `route[0]` + `/v1/health` → correct |
| Reality | two revisions behind | what systemd runs |

`curl /status` on the live gateway returned 8 services all `ok`. The mirror
defined 7 and contained a bug that would have reported all backends `down`.
Editing the mirror would have produced a commit that changed nothing live, plus
a "fix" for a bug that no longer existed.

Resolved in one command:

```
readlink /proc/219465/cwd
→ ${VAULT_DIR}/10-Labs/x402-gateway
```

### False capability claim

Build queue item #7 asserted:

> "Our x402 gateway already supports multi-chain — config-only for ALGO."

Actual code:

```python
"accepts": [
    {"scheme": "exact", "network": "eip155:8453", ...}   # single hardcoded entry
],
```

Hardcoded to one Base entry. The claim was aspirational. Scoping off it would
have produced a `shipped` item that shipped nothing. The honest path — state the
claim was false, build the real multi-network registry, then ship — took one
session and left the queue accurate.

## Pitfalls

- **`git log` on the mirror looks healthy.** A stale mirror can have recent
  commits (nightly sync jobs touch it) while still being behind on the file you
  care about. Recent commit activity is not evidence you found the live source.
- **The systemd unit file can also be stale.** `WorkingDirectory` may point at a
  path that was later moved, with the service still running from the old
  inode. `/proc/<pid>/cwd` reflects reality; the unit file reflects intent.
  When they disagree, trust `/proc` for *what is running* and fix the unit file
  before the next restart.
- **Restarting before confirming the source** loses the evidence. Once you
  `systemctl restart`, the new process picks up whatever the unit file points
  at. Read `/proc/<pid>/cwd` on the *currently running* process first.
- **A capability claim written by you last session is still a claim.** Notes
  degrade. Re-grep rather than trusting your own prior summary.
- **When two of your own notes disagree, neither is authoritative — probe the cheap fact
  before publishing either.** A later note contradicting an earlier one is the highest-risk
  edit in the vault: the newer text reads as the correction, so it propagates while the wrong
  value wins. Hostnames, endpoints and paths are the cheapest facts there are to settle
  (`getent hosts <name>`, `curl -s -o /dev/null -w '%{http_code}' <url>`), and a **non-existent
  host reads exactly like a live one in prose** — NXDOMAIN and a working service are
  indistinguishable to a reader. Probe it, correct in place, and record *what* was wrong so the
  next reader cannot re-derive the wrong value from the same reasoning.
- **Don't fix bugs you find in the mirror.** If the mirror is stale, its bugs
  are usually already fixed upstream. Diff against the live copy before
  "fixing" anything you spot there.
- **The repository checkout is not the installed runtime for interpreted tools.**
  A package installed via `pip`, `npm -g`, or a system manager runs from its own
  tree (`/usr/local/lib/...`, `~/.local/lib/...`, `/usr/lib/...`) even when a
  newer checkout exists in the user's home directory. `git log` on the checkout
  is therefore not evidence of what the live process does. Resolve the module
  path from the running process before quoting source lines or applying a fix.
- **Two live writers, one remote (verified Sep 4, 2026).** Stale data can come
  from TWO clones of the same repo both pushing successfully to `origin/main`.
  Each writer's pushes succeed, every job reports `ok`, but each clone only
  sees its own commits — data consumers see stale or missing work. When stale
  data has no obvious cause: list every clone of the repo on disk
  (`ls -d /root/*<repo>* /root/repos/*<repo>*`), map which cron jobs write to
  which, and check `git rev-list --left-right --count HEAD...origin/main` per
  clone. Nonzero left = stranded work; nonzero right = behind. A green cron
  status means "my push worked", not "the remote is current".
- **Two folders holding the same kind of data are usually a LIVE system and a SUPERSEDED
  one — resolve which before you ever say "unify".** Spotting the same records in two
  paths reads as duplication, and "consolidate them" is cheap to say and expensive to
  act on: merging a live instrument with its own predecessor imports the retired
  contract into the working one, so the merge can only make the good copy worse. Measured:
  a per-file capture log (last real use weeks earlier, one stale stub since) and a newer
  ledger carrying a measured baseline, an append-only record and a scoreboard that refuses
  to compute on a small sample both held "signals" — and the newer system was three days
  old and strictly better. The correct action was **retire the old path and feed off the
  new one**, not merge them.
  **The tell is not which path the docs name.** A plan written before the newer system
  landed still points at the old one, so a documented path is a claim about when the doc
  was written. Check, in this order: mtimes; who READS and WRITES each path (crons,
  scripts, the newest artifact's own header stating its writer and reader); and which one
  carries MORE constraints (a schema, a refusal rule, a validation step). The copy with
  more constraints and a recent writer is the live one. **Then ask the owning seat rather
  than deciding for it** — retiring a lane is its call, and a merge proposed from outside
  is how a dead format gets resurrected into a live one.
- **A listing's shape is not a statement about content.** Directories and dotfiles
  at a folder root say nothing about what is inside them — and a lane whose root
  looks empty is often just **archived**. Prefer a recursive git query
  (`git ls-tree -r HEAD --name-only | grep '<lane>/'`) over any directory listing,
  and never generalise from one missing file to the state of a whole lane.
- **Verify the claims in a request before you ACK it.** A checkpoint or restart
  request often carries claims ("config already migrated", "push is done", "cron
  repointed"). Check them against your own files, processes, and remote refs, then
  report what you measured. Ask the remote for a push — `git ls-remote <remote> main`
  — because a clone that never fetches cannot tell you whether a push landed, and
  the remote does not require a pull to query. If a claim fails verification, say
  so in the ACK; a checkpoint ACK is a safety gate, not a politeness form.
- **When two contemporaneous messages disagree, the durable record wins unless
  the sender explicitly supersedes it.** A commit message or vault note that says
  "Jordan's" overrides a DM that says "yours" until the sender clarifies otherwise.
  Prefer the committed record and say the contradiction plainly rather than
  quietly doing nothing. This is especially true for ownership claims about
  sensitive artifacts such as backup refs, signing keys, and credential rotation.
- **Derive cryptographic public values from the stored private key before
  publishing them.** A generator that prints a public hex and a store that holds
  the private key are two separate claims; the only way to tie them is to derive
  the public key yourself with the library. Watch for the 64-char hex vs 64-byte
  raw confusion. If you publish a public key, publish the one-line verification
  you ran and its result.
- **Webroot orphans are the inverse of mirrors (Sep 4, 2026).** A webroot file
  may have NO repo source at all — deployed straight into `/var/www/` and never
  committed. Overwriting it from a repo copy that merely shares the name
  clobbers the only copy: vanito.html's 87KB dashboard was replaced with an
  unrelated 20KB profile page and the original was unrecoverable (no git
  history, no Wayback snapshot). **Fingerprint before overwriting**: grep the
  webroot file for a unique asset path/content marker, compare size+hash with
  the candidate source. No true source → fix in place, then codify into the
  repo so the next deploy can't orphan it. Sep 4 sweep found 11 orphans
  (demo, portfolio, jordan, concept*, hub-backup, hub-launcher...).
- **Repo, webroot, and Pages copies of the same page can all be different
  generations** — `md5sum` all three before assuming any is in sync. The
  webroot being newer than the repo is normal after hand-fixes; the fix is
  back-porting to the repo, not re-deploying stale repo content over it.
- **A destructive sync is audited in the TARGET tree, and survivors are the falsification.** A path that does `rmtree(dest)` + `copytree(src)` cannot leave seat-only files behind — it writes exactly the source's list. If seat-only files are still present after the sync was supposed to have run, they disprove that the destructive path executed on that directory. Check their mtimes against the sync window before accepting a claimed loss. Then verify WHICH path the tool actually took: a "blocked" shadow-namespace path and a "warn-then-replace" normal path are different functions, and a survivor in a blocked namespace means the alarm points at the wrong case.
- **A count that does not move when the counted set moves is an instrument defect, not a stable measurement.** If you remove one member of a set and the reported count is unchanged, the instrument is measuring a different quantity than its name implies — commonly "present or differing" rather than "present only." Report the observation rather than a false confirmation of no change, and fix the instrument to print the names it counts.
- **When a state-only artifact has no clock, derive movement from git history rather than adding timestamps to every writer.** Adding `created_at`/`updated_at` fields requires every writer to remember them; one forgotten writer corrupts the timeline, and legacy items remain undated forever. Git commits already carry immutable timestamps. Reconstruct snapshots per commit, key items by a stable identity (not the internal `id`, which renumbering changes), and emit events (`created`, `changed`, `returned`). Report unreadable snapshots and refuse to answer if the evidence base cannot be read —  "could not look" must never be printed as "no movement". See `references/derive-time-from-git.md`.
- **The file you edited and the file that SERVES can be the same type and a different SHAPE — assert the
  shape before you hand anyone a copy command.** Two manifests of the same format, same keys, same
  validator, can hold different populations: one is the provider-side document and one is an internal
  superset, or one is the advertise list and one includes entries deliberately withheld. `json.load`
  succeeds on both, so nothing about a parse tells you they are interchangeable — and a `cp` between them
  publishes every extra entry as a live commitment. Measured once as **14 entries in the edited copy
  against 9 in the serving artifact**; copying it would have advertised five services the operator had
  chosen to withhold.
  **Before writing the deploy instruction:** fetch the LIVE artifact (`curl` the public endpoint) and the
  file you edited in the same check and compare a structural count — entries, keys, sections — plus the
  set difference. If the counts differ, you edited a sibling, not a copy.
  **Then put the count in the install path itself:** have the installer read the artifact and refuse
  unless the count matches the expected population (`if count != 9: exit 1`). A guard on the number is
  what makes the difference between "I checked once" and "this cannot land wrong later" — a human
  following your command does not re-measure the file you told them to copy).
  **A count taken from the public endpoint is a count of the PROJECTION, not of the file.** When the
  endpoint and the file disagree, **the file is what you edit and the difference is a filter** — settle it
  by reading the file where the service itself reads it (`docker exec NAME cat <path> | head -c 200`), never
  by re-reading the endpoint more carefully. Re-reading a filtered view confirms the filter.
- **A copy that reports success may have written NOTHING — check the inode, not the message.** `docker cp`
  into a path that is a read-only single-file bind mount prints `Successfully copied …` and then
  `RemoveAll …: device or resource busy`, while the served bytes never move. Resolve the real source with
  `docker exec <ctr> grep '<basename>' /proc/self/mountinfo` (mountinfo names the HOST file; `/proc/mounts`
  shows only the device), then write that host file **in place** — a temp-file-and-rename creates a new inode
  and the container stays bound to the dead one, so the restart silently serves the old content. Prove it with
  `st_ino` before/after. Two more traps in the same shape: **`docker cp` runs on the HOST**, so the
  container's bind target (`/opt/data/...`) is not a valid source path; and **a structural diff of the live
  payload can point at the wrong file**, because the handler may filter at request time — measured, the payload
  said 9 entries while the file being served held 14. The mount table is evidence; a payload match is a
  coincidence.  Full sequence: `references/container-bind-mount-deploys.md`.
- **STAMP THE VALUE AT THE LAST PLACE IT IS CONSTRUCTED, NOT THE FIRST PLACE YOU CAN REACH — and treat an
  unchanged live response after a restart as a no-op, not as a stale deploy.** A handler that reads a
  config, decorates it, and then **rebuilds** the section you edited from a second source will discard your
  change one line later; the file is correct, the restart succeeds, and the served payload is byte-identical
  to before. Measured on a manifest: the derived field was written into the manifest copy, and the handler
  then replaced the whole services block from its own builder — so the deploy verified "successful" and
  changed nothing, twice.
  **The procedure:** grep the serving path for every assignment to the field's parent
  (`doc["services"] =`, `body = build(...)`, a decorator that recreates the dict) and apply the change to
  the LAST one before serialisation. Then **falsify by comparison, not by restart**: capture the served
  value before and after and diff it. A restart that returns the previous value is proof the code path you
  edited does not reach the wire — do not re-run the deploy, go find the rebuild.
  **And verify against the OUTPUT OBJECT, not the input you just wrote.** A unit test that calls your
  patched function and passes proves the function, not the route; exercise the function **as the handler
  calls it** (same argument, same point in the chain) or assert on the final serialised document.
- **"Not installed" from a bare invocation is a fact about YOUR SHELL, not about the system.** Wrapper
  scripts commonly prepend a private bin dir and an `XDG_CONFIG_HOME` so a tool resolves outside
  `/usr/bin`. Running the binary directly then reports `command not found` for something that is present
  and working, which is a false blocker handed to the operator. **Invoke the owner script** (it sets its
  own environment) or replicate its exported `PATH`/config vars before concluding anything is missing;
  `command -v <tool>` under the same environment is the cheap confirmation.

## Support Files

- `scripts/find-live-source.sh` — re-runnable probe. `./find-live-source.sh <port>
  [candidate-file]` resolves the live source dir via `/proc/<pid>/cwd`, compares it
  against the systemd unit's `WorkingDirectory`, lists other copies on disk as
  potential mirrors, and exits 2 if the candidate file you're about to edit sits
  outside the live directory. Run this instead of hand-typing the sequence.
- `scripts/state-file-liveness.py` — measure which `.json` state files are live,
  stale, or orphaned, and flag same-named copies that diverge in size. Exits 1
  when orphans or divergent copies are found, so it can be used as a guard. See
  `references/state-file-liveness.md` for usage and interpretation.
- `references/derive-time-from-git.md` — when a state file stores no timestamps,
  derive its movement clock from git history instead of adding a `created_at` field.
  Covers identity keying, signature design, unreadable-snapshot handling, and the
  required refusal when the evidence base cannot be read.
- `references/container-bind-mount-deploys.md` — deploying into a container that serves a bind-mounted file:
  find the host source from the mount table, why `docker cp` reports success and writes nothing, and why the
  write must preserve the inode.
- `references/negative-findings-and-ref-absence.md` — how to prove something is missing without
  overclaiming, and how to distinguish a diverged git ref from an unresolvable one. Use before
  reporting "this ref/object/capability does not exist" to another seat.
- `references/destructive-sync-audit.md` — how to audit a destructive sync tool: distinguish the
  block path from the replace path, use survivors to falsify claimed data loss, and recognise an
  instrument whose count stops tracking the set it claims to measure.

## Rule

Before the first edit to any running service:

1. `readlink /proc/<pid>/cwd` — find the real source
2. `curl` a live introspection endpoint — confirm the file matches reality
3. `grep` any capability the task assumes already exists
4. For state files, run `scripts/state-file-liveness.py` — confirm the file has a
   producer and that no divergent copy is the real source

Four checks. They cost about a minute and routinely save an entire session's work
from being written to a file nobody reads.
