---
name: checkpoint-ack
description: "Use when a restart asks you to confirm. Measure, then ACK."
version: 2.0.0
author: GenTech fleet — consolidated 2026-10-17 from checkpoint-ack (protojay), fleet-checkpoint-acknowledgement (gentech-treasury), restart-checkpoint-ack (gentech)
license: MIT
tags: [checkpoint, ack, restart, handoff, verification, coordination, honesty, evidence]
metadata:
  hermes:
    tags: [checkpoint, ack, restart, handoff, verification, coordination, honesty, evidence]
    related_skills: [safe-update-restart, handoff-mesh, verify-after-every-action, claim-provenance, agent-state-disaster-recovery]
---

# Checkpoint ACK — answering "are you safe to restart?"

The single home for the **receiving side** of a restart checkpoint. (The **asking** side — who to ask, in
what order, when a restart may proceed — lives in the `safe-update-restart` runbook.)

> **Consolidation note (2026-10-17):** this skill absorbed `fleet-checkpoint-acknowledgement` and
> `restart-checkpoint-ack`. They were the same lesson in three copies, written by three seats — which is
> exactly how the FINISH→LOG→VERIFY rule ended up invisible in two of them. **One rule, one home.**

## When to use

- A pre-restart, migration or checkpoint handoff lands in your lane and the sender wants a return
  confirmation before a disruptive event (gateway bounce, image/container swap, fleet migration).
- Anyone outside your session asks you to state what you have in flight — a coordinator, a sibling seat,
  a maintenance window.
- You are re-verifying a fix you shipped earlier in the same handoff thread before declaring state final.
- Sibling doctrine: the dispatcher side is `safe-update-restart` (checkpoint handoff + ACK gate). Handoff
  mechanics and return lanes: `handoff-mesh`.

## RULE ONE: FINISH → LOG → VERIFY → *then* ACK  (Jordan, 2026-10-17)

**An ACK is not a promise to save; it is a claim that there is nothing left to come back to.** Jordan's
words: *"we want to make sure that there's nothing left behind, you know, nothing pending that we have to
come back to before we restart."*

So an ACK is only valid once all four of these are true, **in this order**:

1. **FINISH the current task** — actually complete it.
2. **LOG the progress in the brain** — write the work where it belongs: notes, the Mess Hall, the handoff
   lane, the ledger. **A save is only real when it is written where the next session will look for it**;
   work parked in a session's memory is not saved, it is gone.
3. **VERIFY it is done** — **re-read what you wrote and confirm it landed.** A claim of completion is not
   a completion. This is the step that makes the ACK worth anything, and the one most often skipped.
4. **THEN ACK.**

**What the ACK now means:** *"I am complete, or I am cleanly parked in the brain."*

**Corollaries that bite:**

- **An ACK given mid-task is not an ACK — it is a deferral, and it must be written as one.** If the work
  cannot be finished before the window, the honest words are **`NOT READY — mid-<task>`**, or a parked
  entry. Never "safe to restart" over unfinished work.
- **A parked item must name its resume point** — the file it landed in, the exact next step, and what
  "done" looks like. A park with no resume point is not a park, it is a loss with a timestamp.
- **"Nothing was in flight" still satisfies this rule** — if there was genuinely no in-flight work, steps
  1–3 are discharged by *measuring* that, which is the census below. The rule tightens what an ACK
  *means*; it does not manufacture work to save.
- **Finish ≠ do everything you would like to.** It means: the task you were in is closed or explicitly
  parked. Anything else is scope creep inside a restart window.
- **Finish includes closing your OWN stale record, not only shipping new work.** If a line you filed
  earlier is now false — a FAIL the cycle overturned, a verdict a later measurement contradicts — the task
  is not finished until you write the superseding line AND fix whatever froze it. Nobody assigning it to
  you this window does not make a stale verdict you own any less unfinished.

## The measurement rule

**Your ACK is a claim about your own seat, so it carries the burden of every other claim: name the
instrument, or do not state the number.** The sender cannot see your box; they will plan the window around
what you write. Three consequences drive everything below:

1. **Measure your own state — never recall it.** A session's memory of "I'm mid-task" is not evidence.
2. **"Saved nothing new — nothing was held" is a complete and acceptable ACK.** A fabricated save is
   strictly worse than an empty in-flight line: it makes the coordinator plan around work that does not
   exist.
3. **The ACK is a MEASUREMENT, not an echo.** Every line must come from a probe you ran *after* the
   request arrived: a digest, a count, a state string. Never restate the requester's claims as facts.

## Procedure

1. **List the request's claims before touching your own state.** "Your config was migrated", "your cron
   jobs were repointed", "all gateways are still per-profile" are claims *about your box*. Re-measure
   each and mark it measured/refuted with the number that settles it. Never echo a claim as fact.
2. **Separate the two categories the request conflates**, and report each separately:

   | category | survives a container recreate? | how you know |
   |---|---|---|
   | work held **in an in-memory turn** — an unwritten artifact, an open partial write | **no** | by inspection; the only thing you can actually "save" |
   | state already written under the **host bind mount** (`/opt/data`) | **yes**, by construction | mtime + size of each artifact |

3. **Held-work census** — a bounce can only destroy what is in memory: queued writes (`pending/`),
   tracked processes (`processes.json`), `*.wip` / `*.tmp` / `*.partial`, and the scratch dir (probes are
   ephemeral by design — say that, do not present them as work).
4. **On-disk state that must survive** — `stat` size + mtime for config, `.env`, `cron/jobs.json`,
   `state.db` **and its `-wal`**, memory files, script wrappers; report the secrets/keystore count, not
   the directory name. **Proof by digest, not by filename** — a filename in a list is a claim; an md5
   taken now is proof.
5. **Cron reality** — read the job store and report `N jobs, N enabled`. **The reportable fact is not the
   count: it is whether any job fires inside the restart window.** A `completed` job, or one whose
   scheduled time has passed, is **not running**; a disabled one-shot with a non-zero last status reads as
   an error and is in fact nothing held.
6. **Name the mechanism the ACK covers.** A container/process recreate keeps the bind mount and an
   un-checkpointed `state.db-wal` replays on next open (safe). A swap or replacement of the mount takes
   the WAL and everything beside it. The same words mean two different things, and the request usually
   claims only one of them.
7. **Say when a check does not apply, rather than implying it passed.** If the profile holds no git
   worktree, write "no worktree here, so there is no uncommitted branch to lose" — never "no uncommitted
   work", which claims a check you never ran.
8. **Name the holdings you cannot protect.** Two survive-with-a-caveat classes: (1) **an un-checkpointed
   SQLite `-wal`** beside `state.db` — durable, because it sits on the bind mount and replays on next
   open, but the **first casualty if the coordinator swaps the mount rather than the image**; (2)
   **queued writes** under `pending/` — on disk, so survivable, but *unapplied*, so what is at risk is a
   consolidated write, not data. State which is which.
9. **Verify fleet propagation when the artifact is a CORE skill** — compare the digest (and mtime) across
   CORE and every seat, not just your own copy. Report the seat count.
10. **Flag cross-seat drift without fixing it.** If a shared helper differs across seats, report the sizes
    and the consequence (another seat's job fails the same way). Editing another seat's profile files is a
    cross-seat write — **flag it for HQ, never do it inside a checkpoint.**
11. **Re-verify any fix you shipped earlier in the same thread — by INVARIANT, not by count.** A
    regression you quoted as "0" yesterday can legitimately be "1" today because the data moved under it.
    Re-run it, assert the thing that must never appear, and report the delta plainly.
12. **Write the return note into the sender's return lane, then verify it landed on disk** — size, mtime,
    digest, and the literal confirmation line present. Report the ACK in the shape below, then stop. **Do
    not start new long-running work until the event passes.**
13. **Append one line to your own completions record** (`01-HANDOFFS/<seat>-completions.md`) pointing at
    the ACK file and its digest. A checkpoint that leaves no trace in your record is invisible next
    session.

Full command recipe: `references/measurement-recipe.md`.

## Note shape

1. **Scope line** — which single restart event this ACK covers ("the <from> → <to> image swap"), and that
   it is **one event, not a class**. Ask to be re-pinged if the target changes or it bounces twice.
2. **What was in flight** — the census as a table of measured values, including "nothing, and here is how
   I know".
3. **State verified to survive** — mtimes / sizes / digests / counts, measured, not quoted from the
   request.
4. **Holdings I cannot protect** — each with its caveat (WAL, unapplied queue).
5. **What this restart does NOT fix** — blocked deliverables, known drift, jobs needing re-arming. A later
   reader reads a bare ACK as "all clear" and the blocked item gets lost for days.
6. **Any regression you re-ran** — command plus real output, deltas included.
7. The ACK lines: **what you saved, what you verified, and — only when this return IS the authorization
   for the event named in the scope line — the literal phrase `SAFE TO RESTART — for <this event>, now.`**,
   so a reader can assert it mechanically. **When the dispatch is explicitly a drill, or the return
   authorizes nothing, that phrase must be ABSENT and must be referred to descriptively** ("the
   restart-confirmation phrase"): a return that contains the phrase while disclaiming it fails its own
   `grep -c` check and reads as a false yes.
8. The seat name, so the note stands alone in the folder.
9. **When the dispatch asks for ONE line in place instead of a note** (a shared fleet checkpoint file),
   use its field order exactly — seat, profile, session id, UTC stamp, progress saved?, notes path,
   anything-in-flight — because the collector concatenates and reads those lines. Get your own session id
   from the DB rather than guessing:
   `python3 -c "import sqlite3;c=sqlite3.connect('file:$P/state.db?mode=ro',uri=True);print(c.execute('select id,last_activity_at from sessions order by coalesce(last_activity_at,started_at) desc limit 1').fetchone())"`.
   Say the in-flight fact in plain words on that line: it is the only part of the ACK the coordinator can
   act on (it decides whether to hold the restart), so it never gets left to a linked note.

## Delivery

**The vault note at `01-HANDOFFS/<seat>-to-<origin>/` IS the ACK; a DM is only the wake.** A DM that
succeeded but was never written to the vault is not an ACK — a bounce erases in-flight chat. Use the
**sender's** return-lane name: a return in the wrong lane name is invisible to the watcher and re-nudges
forever (`handoff-mesh` documents the alias trap). Claim only the transport you verified — on this fleet
the vault is not a git worktree, so the correct claim is *"file written on the shared mount; sync carries
it off-box"*, never *"committed/pushed"*. The chat reply is **one short line** naming the filed path and
the verdict — the artifact is the note.

**When the checkpoint is itself a shared file every seat appends to**, append to it — never rewrite it,
and never load-modify-save it, or you delete the ACKs that landed after you read it. Take a lock, write
one line in the requested shape, then read it back by line number:

```bash
exec 9>>"$F"; flock 9                      # shared append-only file
printf '%s\n' "$ACK_LINE" >> "$F"
flock -u 9; grep -n '^ACK — ' "$F" | tail -2
```

Your line number stays valid as later seats append below you; a file **size** you quote in your own record
is a point-in-time value and will move under you — that is expected, not a lost write.

## Pitfalls

- ❌ **Inventing a save because an empty in-flight line looks lazy.** This is the one failure that makes
  the whole ACK worthless, and it looks like diligence. Same class as printing a fabricated number.
- ❌ **ACKing a claim you did not check.** Even a correct, well-meaning request can carry a wrong premise
  about your state; verifying is cheap and it surfaces drift *before* the restart rather than after.
- ❌ **An idempotency guard keyed on "a line already exists in this file" freezes the record on a stale verdict.** A verify script that appends its result once per *file* can never publish the later, contradicting measurement — so the fleet keeps reading a FAIL that stopped being true hours ago. Key the guard on the **cycle/window it measured** (one line per tag+cycle), and say in the new line which earlier one it supersedes.
- ❌ **Writing the forbidden phrase while claiming you did not.** "No `SAFE TO RESTART` line appears here" still contains the phrase, so a mechanical `grep -c` on the return reports a hit and the claim reads as false. Refer to it descriptively ("the restart-confirmation phrase") so its absence is assertable.
- ❌ **A census number you do not re-measure because it matched yesterday.** Between two checkpoints the seat's own files can be edited by *other* writers — a cron job removed, a secret added. Re-run the census every time and report the delta (§) rather than quoting your own previous note.
- ❌ **Counting occurrences instead of live assignments when checking whether a credential or flag is set.**
  `grep -ci KEY <file>` counts the shipped *commented placeholder* and the help line that merely names the
  variable, so every file looks like it "has" the key and your probe **corroborates a false claim instead
  of refuting it**. Count the split and report both numbers: `grep -cE '^[[:space:]]*KEY='` (live) vs
  `grep -cE '^[[:space:]]*#.*KEY'` (commented). A pattern that cannot fail is not a verification.
- ❌ **Reporting a file that changed under you without naming the writer.** Another seat's sweep can edit
  your own config, `.env` or cron store between two checkpoints. Attribute it before you report it: match
  **size + mtime** against sibling profiles — identical size AND mtime across seats means one fleet-wide
  writer — then read your own copy and name the added block. "Grew 1,365 → 1,505 B in the 08:38 sweep; the
  added block is `fallback_providers`" is a finding; "my config changed" is noise, and never assume you
  are the one who did it.
- ❌ **Reading the request's file list as your own state.** The note describing the mechanism is not a
  measurement of your box. "Safe to restart" is a statement about your profile, not about theirs.
  **This applies to a dispatch YOUR OWN seat wrote.** A checkpoint brief is a claim about architecture; the
  box is the authority. Measured: a self-authored digest asserted "we already run one gateway per machine"
  while the service tree held five gateway slots under one process — running the checklist the dispatch
  itself printed is what surfaced it. When the box contradicts the document, correct the document, and say
  so in the ACK: the seat that wrote the brief is the seat that owns the wrong sentence.
- ❌ **Treating "the vault and profiles survive (bind mount)" as covering everything.** It covers what is
  written. It does not cover an un-checkpointed WAL, an unapplied queue, or anything mid-write.
- ❌ **Reporting "safe to restart" without naming what it does NOT fix.** The blocked deliverable or the
  known drift gets lost. A restart does not settle a payment, re-arm a disabled job, or sync a stale
  helper.
- ❌ **Reading silence or a timeout as permission.** The ACK is per event, in writing, in the vault. If you
  are mid-task and cannot park cleanly, write `NOT READY — mid-<task>` instead of ACKing.
- ❌ **Claiming a check you did not run.** If the runner's Python has no parser for the config you read,
  write **"byte-level read, not a parse."** Reading a file and parsing it are different verifications; an
  ACK must never upgrade one into the other.
- ❌ **Comparing bytes against characters.** `stat -c '%s'` reports bytes; Python's `len(open(p).read())`
  reports codepoints. On multi-byte UTF-8 the before/after comparison reads as "the file changed,"
  sending you to re-verify work that was never broken. Compare like with like.
- ❌ **Reporting a queued write as landed.** Writes in `pending/` survive as files and must be enumerated —
  labelled **unapplied**. Surviving is not applying.
- ❌ **Letting a job count stand in for a schedule measurement.** An already-fired, `enabled: false`
  one-shot is a no-op — say that.
- ❌ **Treating an empty output directory as an omission.** When a generate/render step is blocked, count
  the files (`find <dir> -type f | wc -l`) and separate the claims: "lesson data saved" ≠ "audio exists."
- ❌ **Listing scratch, cache or `_superseded` files as work in flight.** It inflates the apparent risk and
  buries the real one.
- ❌ **Totals that describe different metrics.** "N jobs" (all rows), "N enabled" and "N actually running"
  are three numbers — cite the one you mean.
- ❌ **A known-empty record treated as an omission.** If your lane is documented as having no log or no
  jobs, write "empty by fact" and cite the audit that established it, rather than leaving the reader to
  guess whether you forgot it.
- ❌ **Copying a peer's checklist.** Their exposures (a `pending/` queue, a keystore, a fund rail) may not
  exist on your seat — and yours may not exist on theirs. The census is per-seat; the *method* is shared.
- ❌ **Leaving a placeholder in a verified document.** Run `date -u` and paste the real stamp; a `21:5x` in
  a note full of digests undercuts every measurement under it.
- ❌ **Letting your own stamp drift off the file it stamps.** A rounded `00:30` on a file whose mtime is
  `00:27:32` is a receipt that cannot be true, in the same class as the `21:5x` above. After writing, `stat`
  the file and reconcile the stamp to the measured write time — in both directions.
- ❌ **Quoting a digest and then editing the artifact.** If the note changes after you cite it (a stamp fix,
  a paragraph added), re-measure and say the earlier digest was a **superseded revision** — never leave two
  numbers in two files contradicting each other.
- ❌ **Trusting a tool's success message as the verification.** A write can succeed and still be wrong: two
  batch ops that both rewrote the same entry produced an exact duplicate (usage went *up*), then `remove`
  on the duplicate deleted **both** copies (usage fell to 57%, the fact gone) — two green results, one
  silent deletion, caught only by re-reading and re-measuring. **Exact memory-tool semantics to code
  against:** the entry-rewrite action is `patch` (`replace` is rejected), `remove` deletes *every* entry
  matching that text, and a batch is all-or-nothing with the size cap checked only on the final result — so
  measure the candidate strings (`len()` in a script) *before* submitting, and `read_file` the store after.
- ❌ **Wording a DRILL return so it can be read as an authorization.** When the dispatch says DRILL or *not
  an authorization*, **withhold** the literal `SAFE TO RESTART` phrase and say you withheld it on purpose.
  A soft yes is the failure the drill exists to catch; a drill is an event that authorizes nothing.
- ❌ **Blanket-syncing CORE to every seat.** Before propagating a skill change, digest-check the seats — a
  peer may be *ahead* of CORE (edit in flight), and a CORE→seat sync clobbers it with no back-copy. Flag the
  divergence to the curator instead of "fixing" it.
- ❌ **Reading an exit code through a pipe.** `cmd | tail -3; echo $?` reports **tail's** status, not the
  command's — it made a hard-failing guard read as `exit=0` in a live check of a consolidated script.
  Capture it as `cmd > /tmp/out 2>&1; rc=$?` (or read `PIPESTATUS`), and quote the *command's* number. An
  instrument that reports 0 on the failure path is worse than no check, because it reads as proof.
- ❌ **Letting the ACK run long in chat when the ask was one line.**
- ❌ **One ACK, one event.** A confirmation given for an earlier bounce — even of the same services — does
  not authorise the next one. State the scope every time.
- ❌ **A re-run that contradicts your own earlier number belongs in the note.** Report the delta rather
  than smoothing it; a prior claim you do not correct is inherited by the next session.

## Related

- `references/measurement-recipe.md` — the full command batch: held-work census, bind-mount state, WAL,
  session-DB integrity without `sqlite3`, cron census, propagation, cross-seat drift, note verification,
  the branch-matrix recipe for re-verifying a guard you shipped (§11), the rule that a drill return's
  restart-phrase count must be 0 — plus the fill-in note form.
- `references/claim-refutation-probes.md` — probe design for settling a claim *about your seat*: live vs
  commented credential counts, attributing an unexplained edit, the metric the claim actually names, and
  how to scope a refutation to one seat without overclaiming the fleet.
- `safe-update-restart` — the **asking** side: who to ask, in what order, the ACK gate, and the
  FINISH-not-save requirement the dispatch must carry.
- `handoff-mesh` — return-lane naming and the alias trap.
