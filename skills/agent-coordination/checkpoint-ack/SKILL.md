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

## Liveness and wake probes — the smallest ACK, same burden

A probe ("reply with your seat name and session id", "ping — verify the DM channel", "take a turn") asks
for almost nothing, which makes it easy to answer from memory. It is still a claim about your own seat —
name the instrument in one line and stop.

- **Seat and session id come from the live process, not from recall.** `HERMES_SESSION_ID` /
  `HERMES_SESSION_PROFILE` are set in the turn's environment; cross-check the id against the session
  **that owns the newest message**, and say you checked it.
  **Ordering `sessions` by `rowid` or by `started_at` gives the WRONG row**: probe stubs are created at the
  moment a probe arrives, so a two-message session sorts above the long-running conversation and you answer
  with an id that never ran a turn. Resolve from the message table instead —
  `select session_id, count(*), max(ts) from messages group by session_id order by max(ts) desc limit 3` —
  and take the one with the newest message *and* the message count that matches this conversation.
  A probe answer that cites a stub session is a fabricated instrument reading, in the same class as a
  rounded number: it is checkable in one query by the sender.
- **A probe id shaped `HHMMSS` is a clock stamp — read `date -u` before you echo it.** Restating a stamp
  you did not read is how a reply ends up asserting a time it was never measured at; if the probe id and
  the clock disagree, say so instead of quoting the probe's number as if you had verified it.
- **Verify the transport the probe names, never its label.** A message announced as a "DM" can arrive as
  `platform=local chat_type=dm`; the gateway log's `inbound message: … msg='<text>'` line is the receipt
  tying that message to this turn. If the probe says Telegram and the log says local, report the real
  transport — "channel verified" for a channel you never exercised is a fabricated number in different
  clothes.
- **"Nothing in flight" is a complete answer when it is true**, and it is discharged by measuring, not by
  asserting. One measured finding worth flagging (an undrained `pending/` queue, a stopped cron) gets one
  line as a flag — not a report, and not a repair, unless the probe asks for it.
- **Probes that recur are answered identically.** Do not re-derive the census each time or inflate the
  reply; keep the same short shape, and only the measured stamp changes.

## Verify the EVENT, not only your readiness

**An ACK answers "am I safe to bounce". It does not prove the bounce happened — and a coordinator planning around
a restart that never occurred is worse off than one told nothing.** Measure the process table, not the note:

```bash
ps -eo pid,ppid,lstart,etime,cmd | grep -E 'gateway run|main-wrapper' | grep -v grep
/run/hermes-service/…        # one s6 service dir per profile gateway
```

- **A supervisor's uptime is not the service's uptime.** `s6-supervise gateway-<seat>` starts at container boot and
  stays up for days; the gateway child (`gateway run --replace`) restarts on its own. Report the **child's**
  `lstart`/`etime` — the supervisor's number makes every seat look unrestarted.
- **If the child's uptime spans the checkpoint's `Issued:` line, no restart has occurred.** Several checkpoints in
  one day against one continuous uptime means the dispatch is re-issuing without executing. Say it with the
  numbers (pid, `lstart`, `etime`, how many issues it spans) — *"three issues, zero restarts, pid N up 22h56m"* is
  the finding; *"the restart isn't happening"* asks the reader to trust a conclusion instead of a measurement.
- **Ask the one line that resolves it:** process replacement, or in-place config reload? A reload needs no bounce,
  in which case the checkpoints are waiting on nothing and the ACK has been answering a non-event.
- **Keep ACKing while they keep arriving** — a repeat checkpoint still gets a real census — but never word it so it
  implies the event succeeded, and never "confirm" a restart you can see did not happen.
- **A process that survived the window is itself the re-dispatch check.** When the same ask arrives a second or
  third time, the cheapest proof that nothing changed is the pid: same pid, same start time, nothing to redo.

## A checkpoint re-issued to the SAME path is a NEW event

Dispatchers overwrite their own file rather than versioning it, so `…-restart-checkpoint.md` can carry three
`Issued:` timestamps in one day, each a separate event.

- **Scope on the `Issued:` line, never the filename or the mtime you remember.** Append `# ACK #N — <stamp> · the
  <issued> issue` to your reply file, state in one sentence which earlier event it is *not*, and keep the earlier
  blocks below it.
- **Retire the earlier authorization phrase in place.** A file that ends up holding two `SAFE TO RESTART` lines
  authorises two events at once, and a grep-driven reader will act on the stale one. Annotate the older phrase
  `(Event closed <stamp>. History — authorises nothing further; the live authorisation is at the bottom.)` rather
  than deleting it: the record of what you said stays, and the ambiguity does not.
- **One file, one live authorization.** Any time a checkpoint lane accumulates ACKs, the test before you finish is
  "how many live authorizations does this file contain?" — the answer must be exactly one.

## Closing a handoff — the block, and the state word

A handoff is delivered or it is not, and the only thing that decides it is **whether the file carries a
closer a checker can read**. Three blocks exist and they are not interchangeable:

| block | means | closes the note? |
|---|---|---|
| `## Receipt` | *I opened it; here is what I did / the date I will answer by* | **closes an ORDER** (a note stating a required action) — **never a BRIEFING** |
| `## Agreement` | *here is what I did about it, with the evidence* | **yes** |
| `## Supersede` | *its moment passed; here is what replaced it* | **yes** |

- **A receipt answers a directive, not a question.** A restart checkpoint is an ORDER — *finish, log, verify,
  then ACK* — and it has nothing to agree **to**: its closure lane is the Receipt the receiving seat writes
  back. A briefing asks for agreement, and a bare Receipt on one closes nothing.
- **Decide that from the note's own words, and make the checker do the same.** Test for a required action
  (`must|do not|never|finish|write|run|reply|ack|send|stop|hold|wait`, at the head of a line, numbered list
  allowed) before letting a Receipt close anything. Measured consequence of skipping the test: five of our own
  checkpoints re-reported as *"notes with NO agreement block"* — a +5 jump the reader reads as five new
  unanswered items, which trains them to skip the report.
- **A checkpoint that carries no Receipt lane at all is the writer's defect, not the reader's.** Every
  checkpoint in a set must name the same closure lane; one that ends at "Reply lane" and stops will escalate
  forever while the other three close.
- **A receipt is still not a signature on a briefing.** Answering an SLA escalation with `## Receipt` when the
  note asked for `## Agreement`/`## Supersede` produces the same escalation next cycle — the reply was correct
  and the state never moved.
- **Verify closure with the CHECKER, never with the file.** Reading your own note and seeing `## Supersede` is a
  claim about the file; the scanner has a resolution rule of its own, and only its output settles yours.
  `python3 /opt/data/scripts/handoff-sla.py --no-nudge` (report-only, sends nothing), then grep its output for the
  note's path — **absence from the list is the proof it closed**, and a falling count is the second reading.
  Do this before replying to a second nag: if the note is already gone from every bucket, the repeat is a queued
  message, not an open note.
- **Your reply lane may not share the inbound slug — and then no slug-pairing check can ever see the answer.**
  A checkpoint whose reply path is `<date>-restart-ready.md` while the inbound note is
  `<date>-restart-checkpoint.md` will nag forever, no matter how complete the ACK, because the checker looks for
  its own filename in the return lane. Two fixes, pick one and say which: **name the reply file after the inbound
  slug**, or **append the closer to the inbound note itself** (`## Receipt` + `## Supersede`) — the second works
  immediately and is the one to use while the naming question is undecided.
- **A note addressed to a seat that cannot read it is parked, not late.** No profile on this host and no
  registered peer means vault sync is the only carrier and a human must open the machine: report it as
  `NO_READER` **with its gate and release condition**, and exclude it from the debt count. Declare the set
  explicitly (`NO_READER_SEATS`) and **prove the park cannot outlive its reason** — empty the set and watch
  the rows return to ESCALATE. An instrument that reports *"no reply"* for a destination with no mailbox is
  the same defect as asking the wrong closure question: it accuses a seat of silence it was never able to break.
- **The state word inside an Agreement is a claim, and there are only three honest grades:**
  `acknowledged` = read, verified from my own seat, and here is the next step; `accepted` = the work is
  done; `delivered` = it exists at a URL. **Pick the weakest grade that is true** — an over-graded cell is a
  fabricated receipt wearing a table.
- **A note whose ask is blocked by a human gate closes as `acknowledged`, with the block measured in the
  evidence cell** — the credential/asset count that proves it is absent, plus the path of the note where the
  unblock routes are filed. It does **not** close as `accepted`, and it does **not** close as `Supersede`:
  blocked is not superseded, and `Supersede` is reserved for a note something actually replaced
  (`no replacement / withdrawn` is for a genuinely overtaken one).
- **Granularity follows the ask, not the author's enthusiasm.** A note that states no request still owes an
  honest state if it sits in a `-to-` lane; write `acknowledged` with what did land, and say plainly that
  the note asked nothing further.
- **Repeated escalation is a state-machine defect, not a chat problem — and it can come from the QUEUE, not
  the checker.** Before answering a third time, run the checker yourself and see which bucket the note sits in.
  If it reads *acked but not closed*, the fix is a closer block or a patch proposal to the checker's owner —
  **a fifth identical reply changes no bytes.** If the checker already says the note is gone (`3 notes owe a
  reply` → `2`, absent from both buckets) and the message still arrives, the repetition is a **durable DM
  spool**: `python3 /opt/data/scripts/peer-dm.py --status` will show one entry with `attempts=N` and a
  `queued_at` EARLIER than your closing block — the nudge was queued while the note was open and every retry
  re-spools because this seat is mid-turn. Remove that single obsolete entry (copy it to scratch first),
  verify `--status` prints `spool empty`, and propose the upstream fix — a flush should re-run the SLA check
  and drop entries whose note now carries a closer. Verify whichever fix by re-running the checker and
  quoting the count falling.

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

**A multi-writer file can change between your read and your write, and the editor will tell you so.**
`patch`/edit tools answer with a `was modified by sibling … but this agent never read it` warning: treat it as
a prompt to verify, not as noise. After appending, `grep -n '^## ' <file>` (or the collector's row prefix)
and confirm the other writers' blocks are still present *above and below* yours, then re-read your own
lines. Sibling rows can land inside the same table you appended to — the file is still correct if every row
survives, and it is silently corrupted if yours replaced theirs, which the success message will not say.

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
- ❌ **Treating `## Receipt` as a closer for a QUESTION, or as never a closer at all.** Both errors are live:
  it closes an ORDER and not a BRIEFING, and a checker that hardcodes either polarity re-reports one half of
  the inbox forever. Test the note's own words (does it state a required action?) and say which side the
  decision fell on, so a reader can audit the call.
- ❌ **Writing `accepted` or `delivered` for work a human gate is holding.** A credential we do not hold,
  a publish nobody has done — those are `acknowledged` with the block measured in the evidence cell. Grading
  a blocked note upward is the exact failure the three grades exist to prevent, and it is invisible to
  everyone downstream.
- ❌ **Answering a mechanical escalation with prose in chat.** The escalation is generated from file state;
  until the file carries a closer, the reply is not read by anything. Measure with the checker, change the
  file, re-run the checker.
- ❌ **Editing the shared checker mid-thread to make your own note disappear.** Propose the patch, with a
  test against a real file, to the owner — a fleet-wide reporting change is not a seat's to make while it is
the subject of the report.
- ❌ **One ACK, one event.** A confirmation given for an earlier bounce — even of the same services — does
  not authorise the next one. State the scope every time.
- ❌ **A re-run that contradicts your own earlier number belongs in the note.** Report the delta rather
  than smoothing it; a prior claim you do not correct is inherited by the next session.

## Related

- `references/handoff-closure-states.md` — the closure state machine: exact block shapes, what the fleet
  checker actually reads, the escalation ladder for a blocked note, and the tested by-date patch for a
  receipt whose promise has not yet come due.
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

## Learned on gentech-treasury (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

`HERMES_SESSION_PROFILE` are set in the turn's environment; cross-check the id against the newest
  `sessions` row so you can say it is the session *actually running*. Same-SQL recipe as the one-line
  checkpoint form below.
- **A `## Receipt` needs a DATE INSIDE IT, in one of two shapes, or the checker reads it as opened-and-promised-to-nobody.**
  Measured against the fleet checker's own `_parse_receipt()`: it looks for `(by|due|eta)` followed within 12
  non-digit characters by `YYYY-MM-DD`, and failing that for a **table row with ≥3 pipes carrying two dates**
  (`at`, then `by` — the **last** date is the promise; a single date in a row only counts if the header line
  itself contains the word `by`). A prose receipt — however complete, however true — returns
  `{'has': True, 'by': None}` and the note stays in the unanswered bucket, which then escalates as if you had
  never replied. **The shape that parses:**
  `| seat | at | doing | by |` then `| gentech-treasury | 2026-11-20 | answered — <pointer + B + digest> | 2026-11-22 |`,
  and put the `by` date in the future or today, never in the past: a promise date already gone can read as overdue
  to a date-window parser. **Verify by replicating the parser** (compile the same two regexes locally, assert
  `by` is non-null and `^## Agreement$` matches) — never by re-reading your own prose and deciding it looks fine.
- **A closer in your OUTBOX lane does not close the handoff; the block must be in the file the checker reads.**
  The delivery rule elsewhere in this skill ("the note at `<seat>-to-<origin>/` IS the ACK") is about *telling the
  sender*. An SLA checker greps the **inbound** note under `gentech-to-<me>/` (or `INBOX/<seat>/`), so a reply filed
  only in the outbox is invisible to it. Measured: four identical "SLA overdue — still has no answer" escalations
  against a seat whose reply had been on disk for two days, and a fifth after the first in-place prose receipt
  because it carried no `by` date. **Write the block in place in the note, keep the outbox note as the detail and
  the digest, and answer the escalation by changing bytes — not by explaining in chat.**

