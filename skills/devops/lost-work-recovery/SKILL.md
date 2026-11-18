---
name: lost-work-recovery
description: "Use when work appears lost. Recover before rebuilding."
version: 1.0.0
author: gentech
license: MIT
tags: [recovery, verification, git, negative-claims, diagnosis]
metadata:
  hermes:
    tags: [recovery, verification, git, negative-claims, diagnosis]
    related_skills: [source-of-truth-verification, github-account-compliance]
---

# Lost-Work Recovery

## When to Use

- A wipe, migration, failed deploy, or a "we lost everything" handoff.
- Any moment where the next step would be **rebuilding** something.
- Any time you are about to write **gone**, **lost**, **destroyed**, **missing**, or **unsupported**.
- A script, tool, or capability that a note claims does not exist or is no longer reachable.
- A failure message (`not found`, `404`, `does not exist`) that could have more than one cause.
- You just found a question already marked settled being re-opened as an unresolved unknown.
- **You are about to adopt a recovered tree as CANONICAL.** Read §2's *a recovery snapshot can be OLDER than
  the live copy it would replace* BEFORE copying anything — a bigger file count says how much was captured,
  never how recent it is, and adopting it wholesale silently downgrades whatever survived outside it.

**The premise of this skill: a loss claim is a hypothesis, and rebuilding is the most expensive
possible way to test it.** Rebuilding on top of an unverified loss converts a recoverable artifact
into a permanent one — you pay for the work twice and the replica replaces the original.

---

## 1. Enumerate the off-host copies FIRST

A probe that walks one filesystem proves only that the artifact is absent from *that* filesystem.
A box and its synced mirror are two copies — not the set of copies.

Before writing anything off:

1. **List every account, repo, and mirror we control.** For code hosts, one `GET /user/repos`
   returns `full_name` + `clone_url` per repo — enough to find every candidate in a single call.
   **Then DIFF that list against what is already restored, and pull the remainder.** The recovery target list is
   itself lossy: it holds only the names someone already thought of. The find is the repo **nobody pulled** — and
   it is usually named for something else entirely, because it backed up a *surface* rather than the code (a
   webroot, a workspace, a profiles dump). Measured: a full account listing showed 68 repos against 4 recovered
   and one of the remainder carried the entire pre-wipe website — content that had been written off as needing a
   rebuild.
2. **Clone the candidates.** `git clone` costs **zero API quota**, so the probe is free. There is
   never a reason to conclude "lost" without having cloned.
3. **Check the synced mirror against the repo, not just against the box.** A local synced vault can
   legitimately hold **zero** of a file type the repo holds hundreds of — a sync filter, a partial
   restore, a gitignore-shaped exclusion, **or a deliberate operator decision that this class of content
   lives in the repo and not in the synced tree.** **A local mirror is not evidence of absence.**
4. **Before calling that difference DRIFT, check whether it is POLICY.** A gap identical to data loss is
   produced by a deliberate split (code kept out of a notes store, artifacts kept out of a synced tree),
   and the two need opposite responses: loss means recover it, policy means leave it alone. **A diff is not
   a finding until you know which one you are looking at** — reporting a conscious convention as an
   incomplete mirror sends the next session to "fix" it by copying the content back in, which is the exact
   cost the convention existed to avoid. When you confirm it is deliberate, **record it as a convention** so
   it does not have to be re-derived and a later reader does not reverse it.
4. **Record the scope inside the finding.** "Gone from this box" and "gone" lead to different next
   actions, and only one of them is true.
5. **To settle "was it ever in a backup?", read the BACKUP SCRIPT — not the backups.** A backup's capture list
   plus its exclusion/redaction step is a definitive answer in one read, where searching backup artifacts is
   unbounded and never quite finishes. **A negative you can quote a capture list for is closed for good; one you
   inferred by searching is still open** — and an open negative keeps getting re-litigated. Measured: reading the
   nightly script's copy list (memories, skills, config, SOUL, cron jobs) settled in one read that no repo backup
   had ever held the key being hunted, after several sessions of searching had failed to settle it.

### The tell that you are about to get this wrong

A claim marked *measured* whose probe enumerates paths on **one machine**. Measured-**where** is not
measured-**everywhere**. A confident negative in a note propagates as fact, so the next reader
inherits a false premise and never re-checks it.

**Correct a false negative IN PLACE, in the original note** — not only in a newer file beside it. A
correction that lives somewhere else leaves the wrong premise as the first thing anyone reads.

## 2. A recovered original BEATS a rebuilt replacement

When you find both, the original wins the read, every time. A replacement was written from a
*summary* of the original, so it reproduces what the summary happened to preserve and **invents the
rest** — and the invented portion is undetectable by inspection, because it is written in the same
voice as the part that is true.

**Action:** diff or read the original before keeping the replica, and say in the writeup that the
original was recovered, so nobody later "reconciles" the two.

### The exception: a recovered original can itself be SUPERSEDED

"The original wins" holds when the replacement was written from a summary of it. It does **not** hold
when the replacement is a **live, maintained rebuild that has since taken over the original's job**.
There the recovered copy is the older generation, and staging it restores a **duplicate** — two tools
covering one lane, drifting apart from the moment they are both on disk.

**Before staging a recovered script, ask what already runs that lane.** Read the live job's wrapper to
see which script it actually invokes, then read that script's own header — a rebuilt tool with a later
revision date and the same four output blocks is the same lane, already done.

**Measured:** a 765-line recovered buy-list was about to be restored beside a 598-line live monitor
that already covered all four of its blocks and was the file the scheduled job ran. Staging it would
have added a second buy-list, not recovered one.

**Rule: a recovered artifact is a candidate, not a verdict.** Enumerate what already covers the lane
before copying anything, and record which recovered files you deliberately did NOT stage and why — an
unstaged file that a note lists as missing will be "recovered" by the next session.

### ⚠️ A recovery snapshot can be OLDER than the live copy it would replace

"The original wins" is about a **rebuilt** replacement. It says nothing about a **restore** — and a restore carries
the opposite risk: the tree you recovered from is frozen at the moment of the loss, while work kept happening in
whatever copy survived. **Adopting the restore wholesale is a silent downgrade.**

**Measured:** a recovery tree of 521 files was adopted as canonical, and the live copy held **22 files — five of
them NEWER, and two that existed nowhere in the recovery at all** (documents written after the wipe). Adopting the
bigger tree would have made a stale document authoritative and discarded the only copy of two files.

**Procedure — direction-diff before adopting:**

1. Walk the **live** copy file by file, not the restore. The live copy is the newer generation for whatever survived.
2. **Live wins where it is newer or where the restore lacks the file; the restore wins only where the live copy has
   nothing.** Print each resolved file with its size and hash.
3. **A path present in both proves nothing.** Compare mtime *and* internal cross-references — a document that refers
   to `PART-14` must be resolved with a copy that actually has `PART-14`, or the merge is still broken.
4. Record the merge rule with the artifact, so the next reader does not re-adopt the bigger tree.

**Size is not generational order.** 521 older files can be a regression next to 22 current ones; a recovery tree's
file count says how much was captured, never how recent it is.

### A backup directory that contains ZERO files is a label, not a backup

A path that resolves and a backup that exists are different claims. Measured in the same pass: an archival sweep
held a per-lane directory with **no files in it** — a restore target that would have been reached for and would
have silently restored nothing.

```python
n = sum(len(files) for _, _, files in os.walk(path))
if n == 0:
    print(f"EMPTY BACKUP — {path} holds 0 files; do NOT count it as a copy", file=sys.stderr)
```

**Count files in every backup before citing it**, and treat a zero as *no copy exists* — which is an honest
unknown, not coverage.

## 3. A work item's open question can outlive the answer that closed it

An item flagged "unresolved / worth settling" stays authoritative-looking long after some other
artifact settled it. **Grep the skill library and the notes before spending probes re-litigating.**
Re-opening a settled question is not diligence: it burns calls and produces a second, contradictory
record that the next reader has to adjudicate.

When a question genuinely IS open, answer it from the **system's own API** — not from the docs and
not from anyone's recollection. Rank the instruments: **docs < contract/on-chain < the operator's own
public API.** A stale doc list is not evidence against a live capability, and neither is a memory.

## 4. One symptom, several causes — run the CONTROL before naming a cause

A failure message with more than one common cause is not a diagnosis. Naming a cause from the message
alone is how a healthy system gets written up as broken, and a "flagged / broken / destroyed" claim
is the kind that gets repeated for months.

| Symptom | Causes that all produce it | The discriminator |
|---|---|---|
| `Repository not found` on an authenticated clone | wrong **namespace** (a user account vs an org path) · wrong auth **header format** · a genuinely hidden account | Read `owner.login` / `clone_url` from the repo list you already fetched; **anonymous-clone a known-good stranger's repo as a control** |
| Anon `404` on our own artifacts | namespace · rate limiting · an account flag | Control in the same batch + read the rate-limit headers |
| "File/script is missing" | wrong tree · wrong namespace/path · archived · genuinely absent | Recursive listing over a directory listing; enumerate sibling copies |

**Rule:** for any multi-cause symptom, (1) read identifiers out of data you **already hold** rather
than re-deriving them, then (2) run the **control** to separate *our content* from *our environment*
from *the account*. Those are three findings with three different responses.

**A rejected auth header can masquerade as a missing resource.** Some transports report an
authentication failure and a not-found identically. When a probe fails, verify the *probe* before
believing the result — and see `references/credential-safe-probes.md` for the exact config-file forms
that pass credentials without leaking them into argv (command lines land in shell history and `ps`).

## 5. Report shape

When you report a recovery, lead with the **correction of the premise**, then what was found, then
what changes because of it:

- The premise was wrong / partly wrong, and *what scope it was actually true for*.
- What was recovered, with the concrete handle (repo, path, count) — a verifiable artifact, never
  "the code is available".
- The consequence: what should now be **restored instead of rebuilt**.
- The open question that remains, if any — stated as open rather than answered by assumption.

**Never report a recovery you have not verified by reading or cloning the artifact.** A prior note's
claim that something exists is a claim, not a recovery.

## 6. Restoring a whole LANE — the script is not the unit

A **lane** is an entry script plus the siblings it imports. Copying the script alone recovers nothing:
every failure below presents as a defect in the script and is actually a mismatch in the set.

**Procedure, in order:**

1. **Locate every copy** of the entry script and each sibling — `find` over the whole tree, then a
   `grep -c 'def <function>'` per copy for a function the caller actually imports.
2. **Choose by GENERATION, not by path or recency.** Take the whole set from the **same directory as
   the entry script whose API they serve.** Siblings from a different directory are a different
   generation and will fail on the API, not on the data.
3. **Copy the whole set in one step**, then **verify each landed** by reading it back.
4. **Repoint paths AFTER the last copy — never before.** A `cp` over a file you already patched
   silently reverts the patch, and the symptom returns as if the fix had never worked. Re-grep for
   the old root after staging and assert zero live references remain.
5. **Run it end-to-end and require PER-STAGE status, not exit 0.** An entry script that wraps each
   stage in its own `try/except` and records `{"status": "error"}` will still exit 0 with every stage
   dead. Read the state file it wrote; the exit code is not a verdict.
6. **Verify determinism** — run twice and diff excluding the timestamp.

**The failure classes, in the order they bite** (each looks like a bug in the script; none is):

| Symptom | Actual cause |
|---|---|
| `ImportError: cannot import name X from Y` | sibling from a different generation |
| `TypeError: ... unexpected keyword argument 'X'` | the caller was updated, the sibling was not |
| `PermissionError: '/root/...'` | pre-wipe absolute path baked into a module |
| `unsupported format string passed to NoneType` | `.get(k, default)` — see below |
| prints `0` / `$0.00` where a read failed | a default standing in for an unknown |

**`.get(k, default)` does NOT apply its default when the key EXISTS with a `None` value.** A failed
fetch stored as an explicit `None` produces a key that is present, so the default never fires and the
renderer raises. `.get(k) or default` is the null-coalescing form that actually holds.

**But fix the REPORTING, not just the crash.** Defaulting an unknown price to `0` renders a failed
read as a confident value, which is the same defect as the crash wearing a friendlier face. Render it
as **UNMEASURED** and say which sources failed. *A default substituted for an unknown is a wrong
answer that looks like an answer.*

Full recipe with the exact commands: `references/restoring-a-lane-from-a-recovery-tree.md`.

## Pitfalls

- **A recovery that lands in a scratch/temp directory is not a recovery — it is a second loss on a timer.**
  Scratch space is pruned (often within hours), so a clone you recovered into it evaporates while the note
  you wrote about it still claims the work is safe. **Move every recovered artifact to a durable path as
  part of the recovery, before reporting it.** A recovery is only complete when the artifact sits somewhere
  that survives the next cleanup — otherwise you have traded a permanent loss for a delayed one, and added a
  confident note on top of it.
- **`git clone` is free; rebuilding is not.** If you have not cloned, you have not checked. The cost
  asymmetry is enormous and it is entirely in favour of looking.
- **A claim about a REMOTE artifact is verified AT THE REMOTE — never by the command's own echo.** A push or
  publish wrapped as `cmd | tail -2 && echo "pushed"` prints the success line on a **failure**: the pipe makes
  the exit code that of `tail`, which is 0 for any input, so the guard passes on `fatal: not a git repository`
  just as happily as on a real push. Read the state back from the receiver —
  `git ls-remote origin refs/heads/<branch>` against `git rev-parse HEAD` (the two must MATCH), plus
  `git ls-tree --name-only origin/<branch> <dir>/` to confirm the files actually landed. **Read the branch from
  the clone** (`git rev-parse --abbrev-ref HEAD`) rather than recalling it: a remembered `master` where the repo
  uses `main` fails as a rejection, which then gets mis-reported as a token or permission problem. Same shape as
  every rule in this file — *"I sent it"*, from the sender's side, is a claim and not a delivery, and it is
  exactly how a peer ends up restoring from a file that never arrived.
- **A listing's shape is not a statement about content.** A root that looks empty is often just
  archived or filtered. Prefer a recursive query (`git ls-tree -r HEAD --name-only | grep '<lane>/'`)
  or a find over a plain directory listing, and never generalise from one missing file to a whole lane.
- **A tool that reports a count is not measuring what its name says.** If removing one member of a set
  leaves the reported count unchanged, the instrument measures something else. Report the observation
  rather than a false "no change", and fix the instrument to name what it counts.
- **Do not create a replacement to quiet an alarm.** Capability to create an artifact is not
  permission to create it. If the artifact is recorded as owned by someone else, or a dry-run gate is
  closed, report that you measured it — do not author a new one to make the metric go green.
- **Don't delete the evidence of a loss.** A file with no discoverable producer may be the only record
  that a job was once scheduled. Archive or annotate before removing; a fresh orphan is worse to
  diagnose than a stale live file.

## Support files

- `references/credential-safe-probes.md` — the exact `curl` / `git` forms that pass a token through a
  config file instead of argv, plus how to test a credential without printing it and run a control clone.
- `references/restoring-a-lane-from-a-recovery-tree.md` — the lane-restore recipe: picking the matched
  generation, the `/root/...` repoint pattern, the per-stage verdict, and the exact commands.
