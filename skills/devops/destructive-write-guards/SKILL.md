---
name: destructive-write-guards
description: "Use when automating an overwrite, sync, prune or cleanup."
version: 1.0.0
tags: [guards, data-loss, sync, idempotency, verification]
---

# Destructive Write Guards

Automations that replace, prune, or overwrite content are the ones that lose data silently. They
report success while destroying something, because a blind replace that produces the intended result
for the files it *knows about* looks identical to one that also removed what it did not.

Applies to: content sync to multiple targets, nightly maintenance/prune scripts, cache and artifact
cleanup, deploy overwrites, any `rmtree` + `copy` propagation.

## Rules

**1. Put the guard on every path that performs the operation — find them by grepping the OPERATION,
not the helper name.** A helper that does the work and an inline loop that does the same work are
two independent paths. A guard added inside the helper never runs on the inline path.

```bash
grep -n 'rmtree\|os.remove\|unlink\|shutil.move\|\bcopy\b' <file>   # the paths, not the function
grep -n 'def .*sync\|def .*prune\|def .*clean' <file>               # the tempting-but-wrong grep
```

**2. A guard must compare WHAT IS THERE against WHAT WILL BE THERE, not merely that they differ.**
Any replace of a differing artifact destroys the difference — and the difference may be the whole
point of the local copy. Compute the set of content that exists only on the receiving side and would
be lost, and name it.

**3. Warn, do not block — unless blocking is the stated intent.** For propagation (source of truth →
replicas) the source must win or drift accumulates. The fix is a loss that cannot be missed, not a
frozen pipeline. If you do block, say so explicitly and provide the override, or the next operator
disables the guard entirely to get unstuck.

**4. Never decorate a return value that other code MATCHES ON.** If a caller does
`if result in ('a', 'b')`, returning `'a (detail: N)'` matches nothing — the item silently drops out
of the caller's list while looking handled. Keep matched tokens byte-exact; report detail on a side
channel (log line, separate field). This is the guard hiding the item it warns about.

**5. Drive the REAL entry point in the test.** A test that calls the guarded helper is circular — it
exercises the code you wrote, not the code that runs. Call the same top-level function production
calls, with paths pointed at a throwaway tree, and assert the guard fires there.

**6. Make the scope injectable.** A check whose root/paths are hardcoded cannot be tested without
touching the thing it checks. Read the target from an env var or parameter, defaulting to production.

**7. Never mutate the thing under test.** Plant defects in a scratch copy, never in the live artifact.
A run killed between plant and restore leaves the mutation in production with nobody watching. Add a
startup restore-check that strips any test marker it finds — that is the only recovery for a run that
already died mid-window.

**8. Prove it can go BOTH ways.** Positive cases (real risk detected and named) and negative cases
(identical input, receiver merely behind, absent receiver, `__pycache__`/dotfile noise → clean), plus a
control proving the warning can stay silent. A guard that only ever fires is as useless as one that
never does, and only the negative cases catch a false positive that will get the guard disabled.

**9. When a rule exists to prevent a loss, verify the loss is DETECTED — not merely that the rule is
written down.** Ask which check would go red for this specific loss. If the answer is "none", the
missing artifact is the detection.

**10. An artifact that must NEVER be rewritten needs a STRUCTURAL refusal, not a conditional skip.**
Some subjects are legitimately excluded from an automated repair — human-authored marketing copy, a
contract, anything whose wording is a judgement rather than derived data. Excluding them by skipping
a check *inside* the repair is a behavioural guard, and it is one refactor away from being bypassed:
the next pattern someone adds runs before that skip. Return from the repair function **before any
pattern executes** when the subject is excluded, so no future pattern can reach it at all.

Prove it the way you would prove any other loss is impossible: run the REAL repair entry point over
the excluded subject and assert **byte-identity of the artifact** AND that **no backup file was
written** (a backup appearing is proof the write path was entered). Asserting only "the content looks
right" passes on a run that entered the path and happened to write identical bytes.

The inverse also holds: a repair must not be the only thing policing the excluded subject. Give it a
separate RED-only check anchored to that subject's own source, and **print what was excluded** — an
exemption that is silent gets read as coverage.

## Moving a directory out of a synced/owned tree is still a destructive write

Relocating a folder feels safe because nothing is deleted — but every consumer that reads its old path
breaks, and the breakage is silent until the consumer next runs. **A move has the same blast radius as a
delete for anything that hardcodes the path.**

**Check consumers BEFORE the move, not after:**

```bash
grep -rl '<old/path>' <scripts dirs> */cron/jobs.json 2>/dev/null   # who reads from here?
```

Measured: a directory that looked like obvious dead weight — a service working dir with `node_modules`
and logs, nothing like the notes around it — was read by **eight** cron scripts. Removing it would have
killed four monitors that same night, each one reporting its own quiet failure.

**Moving is the answer when references exist; deleting is not.** Move the payload out of the synced tree
and **leave a symlink at the original path** — the bytes stop syncing, every reader keeps working, and
nothing is lost. Then prove it:

```bash
test -e <old/path>/<known-file> && echo 'path still resolves'
# and run each consumer once — its own exit code is the receipt
```

**⚠️ BUT CHECK FOR A MOUNTER BEFORE YOU SYMLINK ANYTHING — readers follow symlinks, mounters refuse them.**
A path that is a **docker bind-mount source** (or a systemd `BindPaths=`, or anything the kernel mounts on
startup) cannot be a symlink: docker tries to `mkdir` the source and fails with
`mkdir <path>: file exists`, and **the container will not start.**

The failure mode is what makes this expensive: docker does not re-validate a mount that is already in
place. The container stays up, keeps serving, reports healthy — **and the fault is invisible until the
first restart, which is exactly when a routine deploy happens.** A latent fault and a healthy service
are indistinguishable for as long as nobody restarts.

```bash
# before ANY move out of a tree: is this path mounted?
docker inspect $(docker ps -q) --format '{{.Names}} {{json .Mounts}}' | grep -F '<old/path>'
grep -rn 'BindPaths=<old/path>\|<old/path>' /etc/systemd/system/ 2>/dev/null
```

**If any consumer MOUNTS the path, it does not move — not at all, and not "just the heavy parts".** The
number that made the move attractive (megabytes removed from a synced tree) is outbid by an outage. Either
leave the directory in place, or move it *and* update the mount definition in the same change; a symlink
is never the third option.

### If the path IS mounted, edit the HOST side of the bind — a write from inside reports success and lands nowhere

Once a path is a bind mount, the container's view of it is a **view**, and writing to it is not the same
operation as writing to the host file.

Measured: `docker cp <file> <container>:/var/www/…/.well-known/x402-bazaar` printed
**`Successfully copied 8.17kB`** — and the file it reported writing never changed. The two follow-up
commands told the truth that the copy did not:

```
chown: changing ownership of '…/x402-bazaar': Read-only file system
chmod: changing permissions of '…/x402-bazaar': Read-only file system
```

**"Read-only file system" on an in-container path is never a permissions nuisance — it is the mount
telling you that the file lives somewhere else.** Stop and find the mount; do not escalate privileges.

**The rule:**

> **For a bind-mounted file, the edit is made at the SOURCE the mount points at, wherever that is, and
> the consumer is then restarted to re-read it. The container path is a read view, not a write target.**

```bash
# which host path is this container path? (answers it definitively)
docker inspect <container> --format '{{json .Mounts}}' | python3 -m json.tool
```

**Three consequences that cost an hour each if learned the hard way:**

- **`docker cp` and `chown`/`chmod` are the wrong instrument for a mounted file**, and their success
  messages are not receipts. **Verify by reading the file at its real path**, not by the tool's output.
- **A mounted file is usually already correct once the source is correct** — the deploy step is a
  RESTART, not a copy. Ask whether a copy is needed at all before performing one; if the source of truth
  is already the mount source, the only action is to make the consumer re-read.
- **Processes that read config ONCE at import never see a file swap.** A manifest, a dataset, a config
  loaded at startup needs a restart to change behaviour, and until that restart the file and the running
  process disagree — silently, in the direction of the old value.

**And the compound trap:** when a write "succeeds" onto a read-only bind, the operator's next step is
usually the restart — which is the same moment a latent mount defect (see above) surfaces. Two faults,
one command, and neither one names the other. **Prove the write landed, prove the mount is sound, THEN
restart.**

**The proof for a move is a restart, not a read.** Running each reader and seeing exit 0 proves the
readers work. It says nothing about the mounter. Restart the dependent container/service from a clean
stop and watch it come back before calling the move done.

**⚠️ A size audit must state whether it follows symlinks.** After a move-and-symlink, a walk that follows
links still reports the original size and the "reduction" looks like it never happened. Count synced
content with a non-following walk (`os.path.islink(fp) → 64 bytes`), or the before/after numbers describe
nobody's reality.

### Verify an archive by counting YOUR entries, not the tool's output

Before deleting originals after a tar/zip, compare the archive's contents to what you put in — and count
in a unit you control:

```bash
tar tzf out.tar.gz | wc -l              # ❌ includes the '.' entry → off by one, every time
tar tzf out.tar.gz | grep -c '\.md$'    # ✅ the files you actually archived
```

**The off-by-one is not the danger; the danger is what an operator does when the check fails.** Measured:
a count of 45 against an expected 44 correctly refused to delete — then the tempting next move is to
"fix" the guard. **Never relax the guard to make it pass; change the unit until it measures the thing you
meant**, then re-run, confirm a true match, and only then remove the originals.

**And when the tally is wrong, the count is what is trusted — so give the count a printer.** Print
`expected N · found M` with both numbers and the filenames when they disagree. A silent boolean is
indistinguishable from a pass.

## Evicting weight from a BIDIRECTIONALLY synced tree — order is the safety property

When a sync client refuses uploads because the account is over quota, the instinct is to delete local
weight first and let sync propagate it. **That order destroys the only other copies.** A bidirectional
sync treats a local delete as an instruction to delete everywhere: the server, and every colleague's
device. The copy that was supposed to be the backup is the one that just got removed.

**The order cannot be reversed:**

1. **Copy out of the tree** to a staging location on the same host, outside the synced root.
2. **Verify file by file** — compare size against the source for each name, count them, and fail the whole
   batch on a single mismatch rather than continuing.
3. **Write a manifest** of what moved (`relpath → bytes`) so the removal step reads a list instead of
   re-deriving one.
4. **Re-check at removal time**: `if os.path.getsize(src) != size_from_manifest: skip`. A file that changed
   between staging and removal is a file the staging copy no longer represents.
5. **Remove only after 1–4 pass**, and print both totals (files, bytes).

**And never let the staged copy live inside the tree being swept** — same rule as a code backup beside the
code it protects: one glob away from gone.

### A local size drop is not quota relief — verify with an UPLOAD

The quota lives on the server. Measured: the local tree went **131.8 → 100.8 MB** after a verified eviction
and the next sync still printed the identical failure:

```
Connection successful. Detecting changes...
Uploading file <small-note>.md
Sync error: Error: Vault limit exceeded.
```

**Deletes and uploads fail independently.** In this direction deletes propagate while uploads are refused, so
a shrinking local tree can sit next to a server that still counts the old total. Report relief only when a
**probe file you just wrote uploads successfully** — a smaller `du` output is a statement about your disk,
not about the account.

- **Read the sync LOG for the operation, not the exit code or the headline.** `Connection successful` precedes
  the failure on the same run; the line that matters names the file it tried to upload and then errors.
- **Count deletions with their timestamps before panicking.** A log holding tens of thousands of
  `Deleting remote file` lines may span a month of history; printing the raw count reads as "the vault was
  wiped". Always print the first and last timestamp of the range you are quoting.
- **Confirm the local corpus is intact before telling anyone what happened** — a note count is one command and
  it settles the question in the only frame the human cares about.
- **The heavy recurring writer is the real fix, not the one-off sweep.** If a service writes its logs into the
  synced tree, evicting them buys a day and the job re-grows them. Prefer the service's own path env var
  (`<APP>_LOG_DIR`-style) so the weight is never in the synced tree, and treat the sweep as the stopgap.

### Classify REFERENCES from MENTIONS before removing any asset

**A basename grep over a notes corpus returns almost everything, because inventory notes and session
checkpoints echo filenames.** Measured: a check for whether staged media was still in use reported
**47 of 47 referenced**; tightening it to "does a file that actually LOADS assets point at this path"
returned **8**, and three of those eight were checkpoints — transcripts of past sessions — not loaders.

| match type | example | delete? |
|---|---|---|
| **loader** | `icons/icon-192.png` inside `manifest.json` / a dashboard `.html` | **no — keep** |
| **inventory** | the media queue note listing every filename | yes |
| **transcript** | a checkpoint or completions log quoting a path | yes |
| **prose** | a design note naming an image | usually yes |

- **Require the path TAIL** (last two segments), not the bare basename, inside a file type that consumes it
  (`.html`, `.json`, `.py`) — and exclude inventory/checkpoint/completions files **by name** from the hit set.
- **Keep an explicit `KEEP` set** of everything a live page loads, and assert it is untouched after the pass.
- **PWA icons and manifests are the classic near-miss**: an icon a `manifest.json` names and a dashboard
  references is load-bearing even though it looks like incidental artwork.
- **A checkpoint hit is not a consumer** — it is a recording. Treating it as a reference makes every asset
  permanently undeletable once any session has mentioned it.

## The tell that you have one of these bugs

- A count that goes **DOWN** right after you added something.
- A report of **"0 changes" / "nothing to do"** immediately after you edited the source.
- Two audits reporting **clean** over a window in which content demonstrably disappeared.

All three mean: re-read the artifact, do not trust the summary.

### A PATH SUBSTRING TEST SKIPS MORE THAN YOU MEANT — and a guard that never runs is silent

`if '/.obsidian' in dp: continue` was written to skip a sync metadata directory. **It matched
`/opt/data/.obsidian-vault` — the vault itself** — so the walk found **0 files** and the tool reported
**"0 examined, nothing to do"** on a corpus of 26.

**This is the dangerous shape:** the wrong answer and the right answer look the same. A guard that
silently skips its whole subject reports exactly what a clean pass reports.

- **Test a path by its COMPONENTS, not by substring:** `'.obsidian' in dp.split(os.sep)`, or prune with
  `dn[:] = [d for d in dn if d not in SKIP_DIRS]`. `in` on a string is a substring test no matter how
  path-like the operand looks.
- **A "0 items examined" result is a RED FLAG, not a pass.** If you know the population is non-empty,
  zero means your filter ate it. Assert the population before trusting the verdict.
- Same family: `endswith('.bak')` also matches `.bak-old` and `x.bak.orig`; `startswith('a/')` misses
  `./a/`. **Anchor globs and strip comments before source-inspection tests.**

## Auditing an existing overwrite path

1. `grep` every destructive call — list the paths that actually act.
2. Diff one receiver against the source and list what exists only on the receiver. If it is non-empty,
   that content is one sync away from gone.
3. Check whether any current audit compares receiver-vs-source, receiver-vs-receiver, and
   upstream-vs-receiver. Map which losses each one can and cannot see (table in the reference file).
4. Add the guard to every acting path, then prove it with the real entry point.

## Automated git commits: the sweep boundary + argv fall-through class

A script that calls `git add` and `git push` on a schedule is a destructive sync whose "receiving
side" is the same repository it is reading from. The damage is not loss to disk — it is attribution
corruption, silent cross-lane commits, and a production run triggered by `--help`. Apply every rule
above plus the following four.

**11. Add an allow-list argv dispatch before any step that can write or commit.** A maintenance script
with no argument guard treats `--help`, a typo, an editor's syntax check, and a CI health probe as
identical to "run the full job and push". Dispatch on `sys.argv` explicitly:
- `--help` / `-h` print usage and touch nothing;
- `--dry-run` exercises every step but skips commit and push;
- `--selftest` runs the built-in guard test;
- anything else exits `64` (`EX_USAGE`) with a loud `REFUSING unknown argument(s)` and zero side
effects.

Add `--dry-run` as a first-class citizen, because the only reason anyone reached for `--help` was
that there was no safe way to observe the script's behaviour. The mechanism: argv parsing is not a
user-experience nicety; it is the gate between "observing the tool" and "modifying the source of
truth."

**12. Replace the deny-list boundary with an ownership allow-list.** `git add -A` stages every
dirty file in the tree. A deny-list that excludes `Treasury/**` and `11-Mess Hall/**` can only block
paths the author already knows about; the next ledger, the next lane, the next seat artifact will
pass straight through. Build an `OWNED_GLOBS` list from what the script and its subprocesses actually
write, then stage **only** those globs. Every other path is skipped by default. Fail-closed on an
empty ownership set (stage nothing rather than "fall back to all").

The allow-list must be evidence-based — grep the script for `open(..., 'w')`, `shutil.move`,
`subprocess.run(..., output file)`, and any spawned helper that writes. A guessed list is a deny-list
with fewer entries.

**13. Treat `git add` pathspecs as a second attack surface, not syntax sugar.** Two traps turn a
seemingly correct allow-list into a silent pass:
- `git add -- . <globs>` **unions** `.` with the globs. The allow-list becomes decorative and the
  fee-ledger is staged again. Pass the globs alone: `git add -- <globs>`.
- A glob that matches nothing makes `git add` abort the whole invocation (`fatal: pathspec ... did
  not match any files`). That fails safe, but a sweeper that quietly stops sweeping is its own
  outage. Filter the globs to the ones that actually match, print the dropped globs in the report,
  and add a regression check that asserts a non-matching glob does not kill the sweep.

**14. Selftest must falsify every defect class, and the failures must be RED.** A green selftest
that only runs the correct code proves the happy path, not the guard. Mutate the production script
in a scratch copy and assert each of these goes red:
- restore a leading `.` in the `git add` invocation → a non-owned ledger is staged;
- re-add the ledger to the owned list → it is staged;
- neuter the argv guard → an unknown flag runs the job instead of exiting EX_USAGE.

After each red run, restore the correct copy and confirm green again. A guard that cannot be
provoked into a red result is not a guard.

**15. Prove the real entry point on the real source of truth with `--dry-run` before declaring the
fix shipped.** Running a helper in a fixture repo is necessary but not sufficient. The live tree has
state, dirty files from other agents, submodules, and edge cases no fixture replays. Run the script
with `--dry-run` against the actual vault, read the `Would stage:` list, and assert the unwanted
paths are absent. Only then commit.

**16. A destructive git command dressed as a reconcile is still a destructive write.**
`git reset --hard <remote>/<branch>`, `git checkout --theirs -- .`, and `git push --force` all replace
local content with something else. On a multi-writer tree they are subject to the same guard rules as
`rm -rf` + `cp`:

- **Verify the premise before agreeing.** "It's just a re-hash" or "the remote is source of truth"
  must be proven, not assumed. A divergence number says branches differ; it does not say the local
  side is empty.
- **Measure the unique side.** Run `git cherry <remote>/<branch> HEAD~n..HEAD` and count `+` (unique
  local commits with no remote equivalent). Any `+` means a reset deletes real commits.
- **Name the files that would vanish.** `git diff --name-status HEAD <remote>/<branch> | awk '$1=="D"'`
  lists files in local HEAD but not on the remote; if any exist on disk, a reset removes them.
- **Check whether live processes read those files from this tree.** A file read by a running script or
  systemd unit is not merely uncommitted work — removing it changes live behaviour.
- **Refuse as written when the local side holds anything unique.** The safe reconcile is a normal
  merge (merge base exists) or a documented manual recovery, not a reset.

A reset is correct only when the local side holds nothing unique. Treat every other case as data loss
until proven otherwise.

**17. Before refusing an all-or-nothing write, check whether the tool can be SCOPED — "apply versus
decline" is often a false binary.** A refusal to run a fleet-wide replace is usually the right instinct and
the wrong conclusion, because the decision has three outcomes, not two: apply, decline, or **apply scoped to
the carrier**. Refusing without looking for a scope flag hands the operator a choice between two bad options
when a third was on the command line the whole time. Measured 2026-10-01: a fleet skills sync was declined on
solid grounds — its seat-only-content guard WARNS rather than BLOCKS, so an apply would destroy seat-only
files in every lane — and *the same tool* offered `--only <relpath>` and printed its own advice to "apply in
review-sized slices with `--only`". Run scoped, it delivered one corrected skill to all four seats with a
blast radius of ONE skill, and the 79 seat-only files in the neighbouring seat were untouched.

```bash
<tool> --check                                        # what it WOULD do, and to what
<tool> --help | grep -iE "only|scope|path|filter"     # is the blast radius injectable?
```

- **The refusal and the scope are not in tension.** Declining an unscoped replace is correct; declining to
  LOOK for the scope is what turns it into a false binary.
- **A tool that advises "apply in slices" is telling you it expects to be scoped.** Read its own output
  before concluding it has no safe mode.
- **Small blast radius is not small verification.** Re-check every destination afterwards: the scoped run
  touched four, and the count of changes it reported was the number of DESTINATIONS, not of edits.

#### A cleanup that classifies ARTIFACTS by filename pattern will sweep away rollback points

**A `*.bak*` glob cannot tell a stale note copy from the backup you will need in ten minutes.** A structure/hygiene
sweep built to move note backups out of a synced tree matched `server.py.bak-preprecheck-<date>` and relocated it
minutes after it was created — and the next rollback command failed with `cannot stat`, because the file it needed
had been "tidied" somewhere else.

**The rule: classify an artifact by the class of the file it is an artifact OF.**

```python
CODE_EXT = {".py", ".js", ".mjs", ".ts", ".sol", ".go", ".rs", ".sh"}

def is_code_backup(path):
    base = os.path.basename(path)
    for marker in (".bak", ".pre", ".rolledback", ".premerge", "~"):
        if marker in base:
            return os.path.splitext(base.split(marker)[0])[1].lower() in CODE_EXT
    return False
```

- **Note backups** (`.md.bak`, `data.json.bak`) → clutter, sweep freely.
- **Code backups** → **rollback points: leave them beside the code** until the change they protect is settled.
  A dependency tree is regenerable (`npm ci`); the pre-edit copy of a 200 KB production file is not.
- **Assert the exclusion, don't assume it:** create one note backup and one code backup in a scratch tree, run the
  report mode, and confirm only the note one is listed before any `--apply`.
- **Store the post-change copy OUTSIDE the swept tree as well.** The only durable guarantee is a copy no sweep rule
  can reach; a backup that lives in the folder being cleaned is one glob away from gone.

**The generalisable shape:** a cleanup rule written for one population (notes, documents, listings) run over a
mixed population will select by shape and take the exceptions. When the sweep's purpose is "declutter", the one
file class that must survive is *whatever you would need to undo the change that created it*.

### A cleanup that classifies DATA by a word will move live work — match the STATE MARKER

A tool that moves "finished" items out of a working list is a destructive write, and its whole risk
lives in the classifier. **Matching the words that describe a state captures prose that describes
future work in the past tense.**

Measured: a "done" detector matching `done|shipped|completed|resolved|closed` anywhere in a line
selected **61** items for relocation. Reading them showed **8 were plans**:

```
**What it would package (all pieces already exist in the fleet):** …
**Concrete first deliverable (cheap, high-leverage):** …
**Why it matters:** … we just shipped the Algorand rail …
```

Moving those files open plans as completed work — **the exact failure the cleanup existed to fix,
committed by the tool meant to fix it.**

**The rule: a state is a MARKER, not a vocabulary.** Classify only on the explicit, structural signal
the item carries for that purpose — a checkbox at line start (`- [x]` vs `- [ ]`), a status field, a
frontmatter key. Everything else is prose about the state and belongs to nobody.

```python
# ❌ a word search over content — negation, description and storytelling all match
DONE = re.compile(r"(?i)\b(done|shipped|completed|closed)\b")

# ✅ the marker the format defines, at the position it defines it
DONE = re.compile(r"(?i)^\s*[-*]\s*(\[x\]|✅)")
```

**Before applying, count both populations and print them side by side** — `53 ticked · 24 open · 8
mentioning` — and **list the ones you deliberately did not move.** A cleanup that silently ignores the
prose matches reads as complete; one that names them lets a reader spot the near-miss. The 8 were only
caught because the dry-run output was read line by line, not because the count looked wrong (61 is a
perfectly plausible number).

**Generalises to any reclassifying migration:** archived / stale / duplicate / obsolete. The classifier
must read the field that *means* the state, never the text that *mentions* it — and any count it
produces is a hypothesis until a sample has been read.

#### A record file must be excluded by NAME, not by pattern — and the pass must be audited after

**A bulk "file the finished items" pass moved two completion ledgers — the append-only records the
whole system's history lives in — into `_archive/` alongside the ordinary notes.** The exclusion regex
tested **TRUE** against both paths when re-run, and a reproduction of the exact filter returned zero
ledgers. **So the filter was correct and the files moved anyway, and the cause was never determined.**

**That is the argument for the guard, not against it: a pattern that is provably right can still be
wrong in operation.** Ledgers, receipts, append-only records and indexes share a directory and a
naming shape with the notes a filing pass is meant to move, so they are one classifier bug away from
being filed as finished work.

- **Exclude by an explicit basename SET, evaluated first,** before any content classification runs. A
  pattern is a claim about names; a literal list of the four files that must never move is a fact.
- **Print the full move list BEFORE moving, not a count after.** A pass that reports "filed 16" has
  told you nothing about *which* 16 — and 16 is a perfectly plausible number for either outcome.
- **Audit the destination by mtime immediately after the pass.** List what landed in the last ten
  minutes and read the names; that is the only check that catches a record riding along.
- **Recovery is a move back, and it must be verified by content, not by existence.** Restore to the
  original path and compare the **line count against the pre-move count** — a ledger whose last entry
  is the one you appended before the pass is intact; one that is merely present may be truncated.
- **Do not relax or "fix" the exclusion to make it pass on a later run.** The filter already passed; the
  unexplained part is the operation, and rewriting the pattern buries the only evidence you have.

## References

- `references/seat-sync-clobber.md` — the multi-target sync case in depth: why three audits all read
  green across a real loss, the controlled experiment that attributes a disappearance to a program
  rather than a person, and the recovery procedure.
- `references/git-sweep-boundary.md` — automated git-sweep scripts: argv fall-through, deny-list vs
  allow-list ownership boundaries, `git add` pathspec traps, and a falsification recipe for the
  selftest.

## Naming a mechanism you do not need puts it in reach on the day it is harmful

Measured 2026-09-28. A safe offer was drafted as *"force-push only the backup ref, never main."* The operation was
**already a fast-forward** (`git merge-base --is-ancestor <ref> HEAD` returned 0), so `--force` was never required —
yet the plan said the word. The reviewer's correction is the rule:

> **A plan that says *force* invites a reader to reach for `--force` on the day it is NOT a fast-forward — which is
> exactly the day forcing would destroy work.**

**Write the guard as a QUESTION THE GRAPH ANSWERS, not as a capability you might use.** Ask
`git merge-base --is-ancestor <remote-ref> HEAD`; treat non-zero as **STOP and alarm**, never as "escalate to
force." A fast-forward check is decidable before the operation and cannot be deferred, so there is no case in which
the fallback is needed.

**Two corollaries:**
- **A destructive capability named in a plan is a loaded gun in the reader's hands.** If `--force` is not required,
  do not put the flag in the sentence, the variable, or the comment. Silent, footgun-shaped words are how a safe
  procedure becomes an unsafe one two maintainers later.
- **The alarm branch must RETURN NON-ZERO.** This guard's whole value is that a STOPPED state is loud: exit 1 on
  refusal, exit 0 on every quiet outcome (up-to-date / too-soon / deferred / pushed). Verify the exit code **without a
  pipe** — `cmd | sed` reports `sed`'s status, so a refusal can look like success to the scheduler that reads it.

### An UNDO must be labelled as the undo — never shipped in the same block as the deploy

**A rollback presented next to a deploy reads as a second, safer form of the deploy.** Handed a deploy command and a
restore-from-backup command in one message, an operator waiting on a restart will run the one that *ends the
incompleteness* — and silently revert the change that was just verified. Measured: a fix was deployed and verified
6/6, then the accompanying "rollback if anything looks wrong" line was run after a first `cp` had failed for an
unrelated reason; the copy succeeded on the retry, the pre-change file replaced the new one, the service restarted,
and the defect was live again with a green deploy report already sent.

- **Do not offer an undo as a standing option.** State the deploy, and hold the undo until a symptom actually exists.
  "If it breaks, tell me and I will hand you the revert" is complete; a ready-to-paste revert is an invitation.
- **Name it as the undo in the command itself**, not in a paragraph above it — a filename like
  `server.py.bak-preprecheck-<date>` beside `server.py` reads as debris, not as "the version that has none of this".
  Say the word *revert* or *undo* in the sentence that contains the command.
- **After any interrupt, re-prove state before continuing.** The next step is never "carry on from where the plan
  was"; it is `cmp` the live file against BOTH the patched copy and the pre-change copy, and say which one is
  running. A deploy is not done until the running artifact is identified, not merely reported as restarted.
- **Keep the post-change copy outside the tree the undo would overwrite.** If the only "new" copy lives beside the
  file being restored, an undo destroys the evidence of what was undone.

### A declared guard that is never READ is not a guard — and the one that works may have no name

Measured 2026-09-28: a script declared `NEVER_TOUCH = "main"` with a comment calling it
"non-negotiable" — and **referenced it zero times.** The protection that actually held was a
hardcoded refspec on the push line. **The thing that had the name did nothing; the thing that did
the work had no name** — and two agents auditing it initially read the named guard as the
enforcement. This is the destructive-write variant of the same defect, and it is worse here:
a destructive guard that is inert reads as a refusal that will never come.

- **Grep the guard's own identifier and count the reads.** One occurrence (its own assignment) is
  the alarm. A declaration plus a comment is indistinguishable, to a reviewer, from enforcement.
- **Make the named guard read the string the action actually uses**, and order it
  build → validate → use. **Assert the ORDER in a test, not the presence.** A guard called after
  the action is decoration, and one called on a different string than the action uses is theatre.
- **Prove it FIRES, with the case that matters most: the target rewritten to the forbidden value
  while the variable still reads the permitted one.** A guard that only reads the declaration
  passes the obvious tests and fails exactly there. Asserting the guard *exists* is the same
  mistake one level down.
- **When retiring a dangerous word: remove it from the SURFACE, keep the reason.** Rename the flag
  (`--force-run` -> `--now`) so it cannot be reached; leave the docstring explaining the
  withdrawal. **Assert against the CLI surface (argparse), never the whole file** — a check that
  forbids its own explanation pressures the next editor to delete the doctrine.

### The danger is a by-product being read as a state

Verified 2026-09-28: a divergence detector inferred "forked" from the **push rejection**. When the
write gate defers, git is never invoked, so **no rejection is ever observed** and a permanently
diverged branch fell through to "retry next tick" — a permanent condition reported as a wait, and
the detection was gone in the same hour the fix shipped. **Never derive a state from the by-product
of an operation you are allowed to skip.** Ask the source of truth directly
(`git merge-base --is-ancestor`), because that question cannot be skipped.

### A LIST'S LENGTH IS NOT EVIDENCE OF THE DEFECT — check what else adds to it

Measured 2026-09-28: an exclusion list holding a genuine bug (a bare folder name that failed to match nested
copies) was 63 entries long, and the length was reported as "the defect's fingerprint". **It was not.** Only **5 of
the 54 nested entries** existed because a name failed; the other **49 were auto-discovered caches** the client would
enumerate regardless. **The list's length mostly measured cache discovery, not the failure.**

- **Before using a size as evidence of a cause, enumerate the entry origins.** If most entries come from a
  different process, the size is that process's readout.
- **A number that grows for reasons unrelated to your finding is not a fingerprint of it** — and it will grow
  tomorrow too, so it cannot distinguish fixed from unfixed.
- **The real fingerprint is the SCAFFOLDING: a name and its own enumeration in the same list.** `node_modules`
  appearing bare AND as three paths is a fix left visible, specific to the failure in a way a count is not.
- **Corollary for guards: count the entries that MATCH something.** A bare top-level name can only exclude a
  top-level folder — so a bare name for a folder that no longer exists **excludes nothing while having the exact
  form of one that works.** An auditor cannot tell the live guards from the dead ones by looking.
- **Separate the failure modes of a name-based rule** rather than calling them all "wrong": (1) matches a folder but
  not its nested copies — a LEAK; (2) names a folder that no longer exists — a NO-OP that looks like protection;
  (3) correct. **Only (1) leaks; only (2) needs deleting; and only a match test separates them.**

### An acquittal is only as good as the UNIT it was computed in

Measured 2026-09-28: a source folder was acquitted of carrying sync payload because its files are unsupported
classes — **while the server's own table held two entries for it, both FOLDERS, both zero bytes.** The structure
synced and no file content did. **Class filters drop FILES; they do not drop FOLDERS.**

- **"It carries nothing" retires an investigation that should stay open.** The bytes claim was true and the shape
  claim was never made — **the second is what a folder-exclusion failure leaks through.**
- **Verify an acquittal at the CLASS level, not the instance level:** walk every instance of the excluded pattern
  and count the ones a match test misses. Here: 688 directories, 0 leaks — a class check that passed.
- **Two fields can answer confidently in the wrong unit at the same time** — a disk size given a transfer universe,
  and a file-class filter given a folder-structure question.

### The five rungs of a guard claim — and only the last one is sufficient

A guard can be satisfied at five levels, each strictly weaker than the one below. A green test at any rung tells
you nothing about the rungs beneath it. Measured on one function (`assert_target_safe`, 2026-09-28), which passed
the first three and could not fire at all:

| rung | the claim | how it fails |
|---|---|---|
| 1 | the guard **exists** | it can be inert — declared and referenced zero times |
| 2 | the guard **is read** | it can read the wrong thing — a refspec *derived from* the input instead of the input |
| 3 | the guard **is ordered** before the dangerous action | it can sit after an earlier `return` that always fires first |
| 4 | the guard **is reachable** | it can be reachable only by hand-editing the subject |
| 5 | the guard **fires on a case a test can invoke** | **this is the only sufficient rung** |

**Rung 3 is the trap, because it looks like proof.** The test asserted the guard's call preceded the push, and it
**passed on the broken code** — the order was true and the reachability was false. **Order is about where a call
sits; reachability is about whether control arrives.**

**Two further rules that fall out of this:**

- **An assertion that a value is IN A SET does not assert WHICH branch produced it.** The negative control checked
  the status was in `(STOPPED_NOT_FAST_FORWARD|STOPPED_UNSAFE_REFSPEC|MAIN_WINS_SLOT)` — so a *different* refusal
  satisfied it while the guard never ran. Assert the **exact** status, and assert the guard's **own reason string**
  is present.
- **A guard's conditions must be able to VARY.** If the checked value is derived from the input by the same line
  that builds the thing being checked, the comparison is a tautology (`name != ref` where `ref` built the refspec;
  `name not in dest` where `dest = "refs/heads/" + name`). Check the **input**, not a value derived from it.

**The only proof is the negative control at rung 5: revert the fix in a scratch copy and watch the new cases go
red while the old ones stay green.** That difference — new cases failing, order case passing — is the defect made
visible.

### Grepping the whole file matches PROSE — strip comments and docstrings before a source-inspection test

A test that greps a source file for a pattern will match the **docstring explaining the defect it is checking
for**. Two assertions false-failed this way on the same day: a line-number check read the FF status from the
comment describing the previous version, and a flag check matched the retired flag's story in the header.

**A pattern that matches text is not a check on code.** Extract code only — parse with `ast`, drop every docstring
and comment, grep the result — and if the extraction yields nothing, **fall back to the raw file and say so** rather
than passing on an empty subject. Same family as a `*.log` glob, an `--author` field, and a `name in dest`
tautology: **the unit of the check decides what the check can see.**
