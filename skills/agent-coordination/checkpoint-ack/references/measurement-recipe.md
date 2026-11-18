# Measurement recipe — the full pre-restart probe batch

Merged 2026-10-17 from three seat copies (`receiver-measurement-recipe`, `checkpoint-ack-measurement`,
`probe-commands`). All commands are **read-only**; nothing here restarts or writes anything.
Substitute `P=/opt/data/profiles/<seat>`.

---

## 0 — The two categories the request conflates

| category | survives a container recreate? | how to check |
|---|---|---|
| work held **in an in-memory turn** (an unwritten artifact, an open partial write) | **no** | by inspection; the only thing you can actually "save" |
| state written under the **host bind mount** (`/opt/data`) | **yes** | mtime + size of each artifact below |

Report both. "Nothing was in flight" is a complete and valid answer; an invented save is worse than no
save, because the ACK is read as evidence.

---

## 1 — Is anything actually running?

```bash
P=/opt/data/profiles/<seat>
cat  $P/processes.json 2>/dev/null || echo "no processes.json -> 0 tracked processes"
ls -la $P/cron/ | grep lock                 # sentinels only; note ticker_heartbeat mtime
ls -la $P/pending 2>/dev/null || echo "no pending dir -> 0 queued writes"
find $P -maxdepth 3 \( -name '*.wip' -o -name '*.tmp' -o -name '*.partial' -o -name '*.swp' \) | head
ls -la $P/cache/scratch/                    # probes/caches: ephemeral by design -> NOT held work
```

An absent `pending/` and an absent `processes.json` are **findings**: report them as "0 queued writes",
"0 tracked processes" — a missing file and a broken read produce the same empty screen, so **say which
one you saw**.

**Queued writes: enumerate, do not assume applied.**

```bash
find $P/pending -type f        # e.g. pending/memory/<id>.json = an unapplied batch
```

---

## 2 — Does the profile even hold a git worktree?

```bash
find $P -maxdepth 3 -name .git -type d      # empty => no uncommitted branch to lose
```

Write *"no worktree here, so there is no uncommitted branch to lose"* — never "no uncommitted work",
which claims a check you never ran.

---

## 3 — On-disk state that must survive (bytes + mtime, per artefact)

```bash
stat -c '%n %s B mtime=%y' $P/config.yaml $P/.env $P/cron/jobs.json \
  $P/state.db $P/state.db-wal $P/memories/*.md $P/scripts/*
ls -la $P/secrets/ $P/keystores/ 2>/dev/null || echo "absent -> report a count of 0, not a directory"
```

Include the vault copies your lane's continuity rests on (completion record, lane notes) and say where
they live. Size **and** mtime, per artefact.

### Proof by digest (step 2)

```bash
md5sum <handoff notes> <lesson/pack files> <CORE skill> <patched script>
stat -c '%s bytes  %y  %n' <the same files>
```

Quote **size + mtime + digest** per artifact. Use `stat -c %s` (bytes) consistently — do **not** mix in
Python `len()` character counts (multi-byte UTF-8 makes them disagree and manufactures a false delta).

### Empty output dirs are evidence

```bash
find <cache-or-output-dir> -type f | wc -l
```

A zero here is a finding worth printing, especially when a blocked step explains it. Separate the
claims: "lesson data saved" ≠ "audio exists."

---

## 4 — Session DB: integrity + count, no `sqlite3` CLI required

```bash
python3 -c "import sqlite3; c=sqlite3.connect('file:$P/state.db?mode=ro', uri=True); \
print('sessions:', c.execute('select count(*) from sessions').fetchone()[0]); \
print('integrity:', c.execute('pragma quick_check').fetchone()[0])"
ls -la $P/state.db*          # WAL sitting at a few MB is a plain file; it survives a recreate
```

`file:…?mode=ro` with `uri=True` reads a live database (WAL included) **without taking a writer lock.**

---

## 5 — Cron: count, and does anything fire inside the window?

```bash
cat $P/cron/jobs.json                     # N jobs; count enabled: true
ls -la $P/cron/output/                    # last run body per job id, if asked what was in flight
cat $P/cron/ticker_heartbeat $P/cron/ticker_last_success
```

```bash
python3 -c "
import json
d=json.load(open('$P/cron/jobs.json'))
jobs=d if isinstance(d,list) else d.get('jobs',d)
jobs=list(jobs.values()) if isinstance(jobs,dict) else jobs
print('count:', len(jobs))
for j in jobs: print('-', j.get('name'), '| sched:', j.get('schedule'), '| enabled:', j.get('enabled'),
                     '| last:', j.get('last_status'), j.get('state'))"
```

Report `N jobs, N enabled`. **The reportable fact is not the count — it is whether any job's next run
falls inside the window.** An already-fired one-shot with `enabled: false` is a **no-op**; say so. A
`completed` one-shot with a non-zero `last_status` reads as an error in a listing and **is not one**.
Heartbeat/lock files are freshness signals, not jobs.

---

## 6 — The WAL

A non-empty `state.db-wal` is un-checkpointed write-ahead data. Its fate is a property of the **restart
mechanism**, not of your seat:

| restart kind | WAL fate |
|---|---|
| container / process recreate | **safe** — the mount persists, SQLite replays the WAL on next open |
| swap / replacement of the mount | **lost**, along with everything else on the mount |

**Name which one the ACK is being given for.**

---

## 7 — Config: label the depth of the check

```bash
cat $P/config.yaml        # quote the version key + model.default / model.provider
```

If no YAML parser is available, the ACK says **"byte-level read, not a parse."** Reading a file and
parsing it are different verifications.

Also record `hermes --version` and the install method, and confirm you are on the **same** image the
coordinator says it is replacing — a mismatch is a finding worth reporting **before** the swap, not after.

---

## 8 — Fleet propagation across CORE + every seat (when the artifact is a CORE skill)

```bash
for f in <CORE>/SKILL.md <profiles>/*/skills/<name>/SKILL.md; do md5sum "$f"; stat -c '%y %s %n' "$f"; done
```

Identical digest **and** mtime on CORE plus all seats = the sync propagated. Report the **count**
("identical on CORE + all 6 seats"), not "my copy is right."

---

## 9 — Cross-seat shared-helper drift

```bash
for f in <profiles>/*/scripts/<shared-helper>.py; do [ -f "$f" ] && stat -c '%s bytes  %y  %n' "$f"; done
```

A wide size spread (e.g. 8,204 / 3,916 / 2,650 B) means seats hold **different generations** of the same
helper. Report it **with the consequence** (another seat's job fails the same way) and **leave the fix to
HQ** — editing another seat's profile files is a cross-seat write, never a checkpoint action.

---

## 10 — The return note

```bash
F=/opt/data/.obsidian-vault/01-HANDOFFS/<seat>-to-<sender>/<date>-<topic>-ack.md
md5sum "$F" && stat -c '%s bytes  %y' "$F" && grep -c . "$F"
grep -c 'SAFE TO RESTART' "$F"        # 1 = the literal phrase is present
date -u '+%Y-%m-%d %H:%M:%S UTC'      # stamp the real time in the header, not a placeholder
```

**In a DRILL, or any return that authorizes nothing, that count must be `0`.** Refer to the phrase
descriptively ("the restart-confirmation phrase") instead of writing it — a note that contains the phrase
while disclaiming it fails its own mechanical check and reads as a false yes. If you edit the note again
after measuring it, re-take the size and digest: a note cannot quote its own hash and stay true, so for
the note itself write *re-take it with `stat` / `md5sum`* and quote digests only for the artifacts you
measured.

Use the **sender's** return-lane name, not your own description of the note: a return in the wrong lane
name is invisible to the watcher and re-nudges forever (`handoff-mesh` documents the alias trap). Claim
only the transport you verified — on this fleet the vault is not a git worktree, so the correct claim is
*"file written on the shared mount; sync carries it off-box"*, never *"committed/pushed"*.

---

## 11 — Re-verifying a fix or a guard you shipped (branch matrix)

When the checkpoint's work includes your own verifier rather than only your state:

```bash
# 1. make the guard's inputs injectable, then exercise EVERY branch on a SCRATCH copy
EL_HANDOFF=/tmp/scratch/t.md EL_KEY=/nonexistent/key bash $P/scripts/<script>   # unmeasured branch
#    pass / fail / unmeasured / a REPEAT of each — the repeat is the one that proves the dedupe key bites
# 2. prove the shared artifact untouched by the matrix
grep -c '<the new line marker>' <real handoff>     # 0 before the real run
md5sum <real handoff>; stat -c '%s %y' <real handoff>
```

**Key idempotency on the CYCLE measured** (a reset timestamp, a build id, a window label) — a guard gated
on "this file already has a line" writes once per FILE and can never publish the next cycle's
contradicting verdict, so its stale first answer stands as the standing one with a timestamp on it. Have
each new line name the earlier one it supersedes, and leave the old line in place: a write-once record
must stay write-once, and a reader who sees only the new verdict cannot tell a correction from a
contradiction.

**Run the real one only after the matrix passes**, and re-take the live digest afterwards: a branch you
never ran is a branch you cannot claim, and "the scratch copy behaved" is not "the artifact changed only
as intended."

---

## The note, fill-in form

```markdown
# CHECKPOINT ACK -> <origin> — <seat> state measured before <the event>

**Filed:** <UTC timestamp> · **Re:** <the request's path>
**Scope:** this ACK covers ONE restart event — <from> -> <to>. Not a class of events.

## 1. What was in flight
| check | measurement |
|---|---|
| in-flight turns / held writes | <none — this turn is reads only / what was held> |
| processes.json | <value> |
| pending/ queued writes | <count, labelled UNAPPLIED> |
| newest cron execution | <id, state, delivery, exit code> |
| worktree | <none / list> |
| lockfiles | <sentinels only; heartbeat mtime> |

## 2. State verified to survive
<artifact, bytes, mtime / digest> — measured, not quoted from the request.

## 3. Holdings I cannot protect
<un-checkpointed -wal; unapplied pending/ writes; each with its caveat>

## 4. Regression re-run
<command> -> <real output>; deltas vs my earlier report: <...>

## 5. What this restart does NOT fix
<blocked deliverables, known drift, jobs needing re-arming>

## 6. ACK
Saved: <...>. Verified: <...>. <the confirmation line for the event — ONLY when this return authorizes
that event; a drill or any no-authorization return states the same verdicts and leaves it out.>
```

## Delivery

The vault note at `01-HANDOFFS/<seat>-to-<origin>/` **is** the ACK. The chat reply is **one short line**
naming the filed path and the verdict. A DM that succeeded but was never written to the vault is not an
ACK, because a bounce erases in-flight chat. Then append one line to your own completions record pointing
at the note and its digest — a checkpoint that leaves no trace in your record is invisible next session.
