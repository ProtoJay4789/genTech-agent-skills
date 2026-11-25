---
name: fleet-compatible-skills
description: "Use when building or changing a skill, script or cron."
version: "1.1.0"
---

# Fleet-Compatible by Default

Jordan, Sep 17: *"We need to make all of us consider making all of our skills fleet
compatible... there are times where we're doing something that everybody needs to be able
to do, and I didn't even think about compatibility."*

**The default is: every seat needs this.** Seat-specific is the exception, and it must be
declared out loud — never the silent result of who happened to write the file.

## The rule

Before writing a new skill or script, answer one question:

> **Would the other three seats ever need this?**

If yes (and the honest answer is usually yes), it goes in the shared core and works
fleet-wide from the first commit. Do not build it in one profile and hope.

## Rule 0 — SEARCH, then STACK. Never fork a variation. (Jordan, 2026-10-17)

Jordan: *"Sometimes we make variations of the same skills instead of stacking or adding."*

**Before writing a NEW skill, search the library for one that already covers it.** The failure mode here is
not duplication — it is a **variation**: the same lesson, restructured, under a new name, so that **neither
copy looks wrong** and a search for either one finds only half the doctrine.

**Measured twice in one week:**

- the receiver-side ACK doctrine existed as **three skills** — `checkpoint-ack` (protojay),
  `fleet-checkpoint-acknowledgement` (treasury), `restart-checkpoint-ack` (gentech) — the same lesson, one per
  seat, which is exactly how Jordan's FINISH→LOG→VERIFY rule stayed **invisible in two of them**;
- `gentech-ops/host-task-handoff` and `devops/host-access-delegation` — **same author, same trigger, the same
  rules renumbered.** Body-vocabulary similarity was only **34%**, so no duplicate-detector would ever have
  flagged it as a copy: the wording differs while the lesson does not.

**So, in order:**

1. **SEARCH first — by *lesson*, not by name.** A variation almost never shares the name. Grep the shared core
   for the situation, not the title: `grep -ril '<the problem this solves>' <CORE>/*/*/SKILL.md`.
2. **If a skill covers it → EXTEND it.** Add a section, add a rule, add a reference file. **Stacking is the
   default; a new file is the exception, and it needs a reason.**
3. **If two skills already cover it → MERGE them.** One home, unique content preserved, dated
   non-overwriting backup first, then promote → sync → verify in every seat.
4. **Author new ONLY when the lesson is genuinely new** — and say which search you ran, so the next reader
   knows it was checked rather than skipped.

**Why a variation is worse than a duplicate:** a duplicate is visible — two identical files shout. A variation
looks like two healthy skills. The divergence stays invisible until someone happens to read both, which is
how three seats each carried a different version of one rule. **One lesson, one home** — the enrichment goes
into the existing file, not into a sibling.

**The detector runs on structure, not on names:** near-identical **section headings** under different names,
or the same rules appearing **renumbered** in two files, are the signature. (Identical headings across
`docx`/`xlsx`/`pdf` are *not* — that is the shared house template, and a false positive.)

## The failure this prevents (measured, not hypothetical)

Three real incidents, all the same bug:

| artifact | what happened |
|---|---|
| handoff-watcher.py | **4 copies, 2 designs, 4 md5s.** HQ ran one without noise control; workers ran one without detection |
| verification-preset-system.md | auditor pointed at a dead provider on all 4 seats; each needed hand-editing |
| skills generally | **272 files diverged across 4 profiles**; 24 of them are pure drift with no seat concept at all |

Each cost real time to discover and re-fix. None needed to happen.

## The pattern that works: ONE artifact, seat-aware config derived from context

Reference implementation — `handoff-watcher.py`:

```python
SEAT_LANES = {
    "gentech": [],                                 # HQ sees all lanes
    "gizmo": ["labs", "gizmo"],
    "pixel": ["entertainment", "pixel"],
    "gentech-treasury": ["treasury", "strategies", "gentech-treasury"],
}

def _seat_from_path():
    """Identity comes from where the file lives, not from a hardcoded constant."""
    parts = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
    return parts[parts.index("profiles") + 1] if "profiles" in parts else "gentech"
```

One file, four seats, zero forks. Behaviour differs; the artifact does not.

**Cron has no script-args field** — you cannot pass `--seat` from the job. Deriving from
the path is the only mechanism that works fleet-wide without editing every cron entry.

## Checklist before shipping

- [ ] **No absolute profile path** hardcoded (`/opt/data/profiles/<one-seat>/…`)
- [ ] **No seat name as a constant** — derive it, or make it a config map keyed by seat
- [ ] **No credentials** in the artifact; read them from the profile `.env` at runtime
- [ ] **Silent when idle** — a fleet-wide job that prints on every run nags four seats at once
- [ ] **Declares its own degradation** rather than silently using a weaker path
- [ ] **Placed in the shared core**, not one profile's `skills/`
- [ ] **Verified on more than one seat** before calling it done
- [ ] **Tests and guard scripts ship in the SAME deploy manifest as the artifact they verify** — a test with no sanctioned propagation path is a seat-only build artifact and will drift silently

## The gate (step (c) — a check that runs, not a convention)

The checklist above is a promise. These two tools are the enforcement:

```bash
cd /opt/data/.obsidian-vault/00-System/agent-profiles
python3 fleet_compat_scan.py    # exit 1 = a skill references another seat's filesystem
python3 fleet_compat_fix.py     # dry-run plan; --apply rewrites only what it can prove resolves
```

**Why a new tool was needed (measured 2026-09-17):** the drift audit compares seat to seat, so a
defect present in *every* copy reads as `identical` — healthy. It reported a clean fleet while
**731 references on the three worker seats told their reader to use HQ's filesystem**
(`/opt/data/profiles/<the-HQ-seat>/…`), 452 of them in executable context. Pixel's own copy of
`github-api-helper` inserted the HQ seat's `scripts` directory on `sys.path`; pixel's
`arc-cli-tooling.md` told the reader to run the HQ seat's `arc-canteen`. Add the scan to the pre-ship
check: if it names a seat that is not the reader's, it is not fleet-compatible, however many
copies agree.

The fixer refuses rather than guesses, and the refusals are the interesting part:
- a path that does not resolve on the reading seat (222 hits reference files that exist only on the
  HQ seat — substituting them would produce a path that resolves to nothing: a green light pointing
  at nothing);
- code files (`.py`/`.sh`) — `${PROFILE_DIR}` is not a variable there, so the substitution that
  fixes a `SKILL.md` would break a script;
- a seat copy whose skill also lives in the shared core, when the core copy would refuse the same
  substitution — a seat-only edit is a build artifact and the next sync replaces it;
- a line that names a second seat, or a file not already written portably.

Full finding: `00-HQ/fleet-compat-2026-09-17.md`.

## Where the shared core is

```
/opt/data/.obsidian-vault/10-Labs/skills-distribution/     <- SHARED_CORE (source of truth)
/opt/data/.obsidian-vault/00-System/agent-profiles/fleet_skills_sync.py
```

```bash
python3 fleet_skills_sync.py --check    # report drift, change nothing
python3 fleet_skills_sync.py            # apply
```

Nightly propagation is `nightly-skills-sync.py` — silent on 0 changes, prints the DELTA.

## The sharing boundary — what is shared, what is NEVER copied

Jordan: *"everybody has a copy of GenTech, but everybody can create their own memories as they
work on stuff."*

**Shared by default:** skills, scripts, plugins, the vault, shared secrets, model/provider config,
stt/tts config. **Private per seat, never copied across:** `SOUL.md`, `memories/MEMORY.md`,
`memories/USER.md`, `cron/jobs.json`, `.env`.

**⚠️ Copying a memory across seats corrupts BOTH** — it overwrites what one seat learned with what
another happened to know, and afterwards nothing distinguishes them. Before and after any bulk
sync, hash the private set (`SOUL.md`, both memory files) on every seat: **all hashes must still
differ.** Identical hashes there are the alarm, not the goal.

### Two classes of script that must NOT be blanket-synced

Fleet-compatible is the default, but it is not unconditional. **Exclude by what the file DOES, not
by whether it would run elsewhere:**

| class | example shape | why |
|---|---|---|
| **credential-handling** | signs with a key, imports/derives a wallet, reads a secret to write it | it belongs where that credential is, nowhere else. A copy on another seat is a second place to leak from |
| **seat-retargeting** | rewrites a *specific* seat's gateway/bot/channel config | run from the wrong seat it silently reconfigures the wrong agent |

Name the exclusions out loud when you sync, and re-check the exclusion list whenever a new script is
added — a blanket `cp` does not distinguish a tool from a liability.

### Verify the SET, not the count — and verify on the receiving seat

- **Equal counts prove nothing.** Four seats holding 72/72/73/73 skills looked aligned while the
  *same nine* were missing from three of them — the totals matched because each seat carried
  different extras. Compare `set(core) - set(seat)` and print the names.
- **A missing fleet-operational skill is the highest-signal gap** (shared-file-writes,
  fleet-update-protocol, key-rotation). A seat's specialist extras are legitimate and should stay —
  a seat with nothing its siblings lack is a duplicate, not a specialist.
- **Copy preserves the source's mode, so a non-executable source yields an unrunnable tool** that
  still looks installed. After any script sync, set `+x` on every `.sh` and every `.py`/`.mjs` with a
  shebang, then confirm the mode **on the destination** (`stat -c '%a'`), not on the source.
- **Parse-check each copied script from inside each seat** — importing/`ast.parse`-ing in the
  receiving context is the only proof it works there; a file that lands but cannot run is worse than
  a missing one because it reads as available.
- **Never sync the source's own junk.** `*.bak`, `*.pre-*` and directories ride along in a naive
  copy and land as confusing artefacts on every seat. Filter to real files, and snapshot each seat
  before writing.

## Editing rules

**Edit the shared core, never the profile copy.** A profile copy is a build artifact; the
next sync overwrites it. This is the same trap as the vault being the source of truth for
scripts — a per-profile edit gets silently reverted.

**⚠️ `skill_manage` writes the SEAT copy, not CORE — so a successful patch is a future deletion.**
The tool's target is the profile's skills dir (`profiles/<seat>/skills/…`); CORE at
`10-Labs/skills-distribution/` is not touched. Its success message reports that the edit landed,
**never which file it landed in**, so it reads as done either way.

**Verification step, after every `skill_manage` patch — not optional:**

```bash
grep -c '<a unique phrase from the new text>' \
  /opt/data/.obsidian-vault/10-Labs/skills-distribution/<cat>/<skill>/SKILL.md
# 0    -> the rule is in the build artifact and will be overwritten. Move it to CORE now.
# >=1  -> it survives the sync.
```

Then propagate CORE → each seat and **assert the hashes match on every seat**, so seat
variation is impossible rather than merely unlikely. If the section was already written to the
seat copy, extract it and insert it into CORE at the same anchor — do not retype it, or the two
versions drift on the first edit.

**Why this is worth a command rather than a habit:** the failure is invisible from every angle the
edit itself can see. The skill loads, the content is correct, the patch reports success, and the
only reader who ever sees the truth is whoever runs the next sync.

**If a skill is genuinely seat-specific**, say so in the skill itself (a `seats:` field or a
one-line note) so the next person does not "fix" the divergence by syncing it.

## Known-open debts (re-measured 2026-09-17, Council Overnight)

- **Pure drift: 0.** It was 6 (not 24 — four of that count were Hermes machine state, not
  skills). All six are unified in the core and byte-identical on all four seats. Triage:
  `00-HQ/skill-drift-triage-2026-09-17.md`.
- **52 pending sync changes across 21 skills** — visible only since the sync stopped
  comparing `SKILL.md` alone. **18 of the differing files are seat-aware**, so this is a
  review batch, not an apply batch. The sync now refuses an unattended run above 25 changes
  (`--max-changes`, exit 2) and `nightly-skills-sync.py` reports that as *"HELD, not broken"*.
- **278 files exist in only one profile** — some are legitimately seat-specific; the rest
  never got shared.
- **The detector:** `fleet_skill_drift_audit.py` (same dir as the sync). Sync answers "does
  the fleet match the core?"; the audit answers "are there files on every seat that should be
  identical and are not?" Run the audit before trusting a green `--check`.

## Lessons that cost a session each (measured 2026-09-26)

**1. A drift gate is a detector, not a cure.** It reached **0**, then read **3 eleven hours
later on the same day** — every one a seat that had *learned something* since the last pass.
Regrowth is the expected behaviour of a working fleet, so a green 0 is a **moment, not a
state**: re-run the audit, then **act** on it. Promoting the newer seat copy *into the core*
is the only edit that persists; a seat-only edit is reverted at the next sync.

**2. Measure direction per file before promoting — "superset" is a claim, not a fact.** A run
that had identified five residuals as strict supersets was wrong **twice**: one held genuine
halves (43 lines only on one seat, 54 only on the other) and another was a union. A blind
promote would have silently deleted live procedure. Diff **every** candidate, then merge.

**3. Never promote a skill as `SKILL.md` alone.** The sync's unit is the *directory*
(`rmtree` + `copytree`), so a core copy holding one file while a seat holds five will **delete
the other four, on a schedule, reported as a routine `updated`.** Copy the whole directory and
the union of its references.

**4. A size in a hygiene report is not a saving until the inode is checked.** Two overlapping
false positives in one run: a **symlinked directory** measured as its target (a "648 MB stale
artifact" was a 0-byte link to the *live* cache — `os.walk` descends symlinked dirs even when
`dirsize()` skips symlinked files), and a **hardlinked** toolchain counted as a duplicate copy
(**true reclaimable 0**). Group by inode, check `st_nlink`, and never recommend a delete from a
size alone.

**5. A test without a deploy manifest drifts exactly like the code it tests.** The canonical
`test-handoff-watcher-closure.py` was **6 checks behind** in gizmo's seat copy because the test
had no sanctioned propagation path while the watcher it validated was deployed fleet-wide. A
verification asset that lives in the same logical package as the artifact must share the same
deploy mechanism, or it will become stale and then the artifact can drift with a green suite.

- Tests are source-of-truth assets, not ad-hoc probes. Add them to the same fleet deploy script
  as the artifact they cover, and write a manifest that records which seats received them.
- A `--check` mode must be able to report seat drift by comparing the manifest digest against
  the live file — a green result is only evidence when the checker would have gone red if drifted.
- If the test is a file that cron executes, do **not** make it a symlink; cron refuses paths that
  resolve outside the profile's `scripts/` dir. Use a byte-identical copy inside `scripts/` and
  guard it against the canonical test in the core.
- Prove the drift checker can actually fail by injecting a controlled mutation (append one byte
  to a seat copy), running `--check`, confirming it reports the divergence, then restoring and
  re-confirming green. An unfalsifiable guard is worse than no guard.

**6. Fleet verification tools must be testable without touching production.** A guard that can
only be validated by mutating the live artifact risks leaving a real defect behind if the run
is interrupted between plant and restore. Test the guard against a scratch copy or a temporary
seat path, never against the canonical deployed file.

**7. A sync that names a RETIRED seat and omits a LIVE one is worse than a stopped sync.** The target
list (`PROFILES`) is hardcoded, so seat churn is invisible: the run prints `✗ <dead seat>: no skills
dir — skipping` and **never mentions the live seat at all**, because the live seat is not on the list.
Both read as a clean run. `Fleet skills sync complete` is printed either way, and a run that updated
**2 of 4** seats reports success. **Rule: read the `Targets:` line and require a per-seat change count
for EVERY live seat; audit the target list whenever a seat is added or retired, before trusting a
green sync.**

**8. A `--check` reporting a large backlog is the proof the sync was NOT running.** A sync dead for
weeks looks identical to a healthy one on the day it is repaired; the size of the first `--check`, and
its refusal above `--max-changes`, is the only evidence. Treat that backlog as a review batch, and
**never raise the cap to "catch up"** — the cap is the thing stopping an unattended run from
overwriting seat-only files that were never promoted to the core.

**9. The sync's OWN path constants rot, and the message blames the DATA.** `PROFILE_DIR` / `VAULT`
inside `fleet_skills_sync.py` are absolute literals, so a host move that relocates the vault or the
profiles leaves them pointing at a directory that no longer exists. The script then exits with
`✗ Shared skills core missing: <dead path>` — **which reads as "the skills are gone", not "the config
is wrong", and it is the most alarming possible wording for a one-line bug.** Three silent no-op modes
now, all printing something calm: a dead constant (#9), a stale seat list (#7), an unrepaired backlog
(#8). **Rule: when a shared script reports a MISSING SOURCE, check its constants against the live
filesystem before believing the source is missing** — same discipline as verifying an instrument before
trusting its negative. Substituting the live paths is the fix; the tell that it was broken is the first
`--check` afterwards listing weeks of pending changes (#8).

**10. The divergence ratchet runs ONE WAY — measure the direction before you choose a repair.** Sync
the whole library and the residual is almost never symmetric. Measured: of 72 diverged skills, **48 had
a seat copy LARGER than CORE and CORE was larger in ZERO cases.** Every divergence was a rule learned
in a seat and never promoted. **That asymmetry is the decision:** promoting seat → CORE is safe and
loses nothing; pushing CORE → seat is the direction that can delete live procedure, so it needs the
per-file diff from #2 first.

- **Size is a cheap first sort, never the verdict.** `seat > core * 1.15` is a fine filter for "worth
diffing"; it is not proof of superset (see #2 — the same run produced genuine halves and a union).
- **A seat-only skill is the other failure, and it looks like an overshoot.** After pushing CORE down,
the residual held 22 skills that existed **only** in seats (a whole LP-rebalancing and perp-venue
economics body of work). Promoting them up is correct; **silently deleting seat-only skills to make the
numbers match is not** — "not in CORE" means "never promoted", not "obsolete".
- **A private file that is merely DIFFERENT has not been shown to be WRITTEN.** The private-set check
(`SOUL.md`, `MEMORY.md`, `USER.md` all hash-distinct) proves nothing was overwritten across seats. It
does **not** prove each seat has one: an identity file consisting of the **stock Hermes prompt** is
byte-distinct from its siblings, loads fine, and leaves the seat with no role, no fleet protocol and no
ACK obligation. **Check identity by substance — does it name its own seat? — not by divergence.** A
seat that "won't follow the behaviours" is usually a seat that was never given any; verify before
diagnosing discipline.

**11. Reconcile by CONTENT DIRECTION, and expect CONVERGENCE to take more than one pass.** A
whole-tree sync is a convergence loop, not a single apply, and every cheap way of shortcutting it
produces a confident wrong answer.

- **A file's MTIME is not its direction.** A seat copy can be newer for a trivial reason (a cron touched
  it) while CORE holds the richer text, and CORE can be newer because another seat promoted first. Sorting
  by which side is newer produced **162 "promote"** on a tree where the content-hash reconciler found
  **53 promote · 13 sync · 145 both-changed**. A timestamp cannot express "both sides changed", so a
  mtime classifier silently files every merge as a promotion and drops the other half. **Direction is a
  content question; timestamps are only a hint about activity.**
- **Look for the reconciler before writing one.** The sync usually already has a mode that classifies by
  content and REFUSES ambiguity — `python3 <sync> --reconcile` (dry-run) then `--apply`. Its refusals are
  the feature: an item it will not decide is an item a human must merge (#2). A second, hand-rolled
  classifier is the variation Rule 0 forbids, and it will disagree with the sanctioned one.
- **Apply the safe half, then expect the numbers to MOVE — that is propagation, not regression.**
  Promoting content into CORE makes CORE newer than the seats that did not get it, so the very next
  dry-run reports those as `sync` (measured: sync went 13 → 103 after a promote pass). Run `--apply`
  again to push them down; it then collapses (synced 103, failed 0). **A post-apply count that looks
  worse than the pre-apply count is the loop working, not damage** — judge it by re-running, not by
  the first number you see after writing.
- **Converged is not zero — it is `review` only.** The irreducible remainder is the set where both sides
  changed. Counting it to zero would mean the tool started guessing. Report it as a review backlog with
  a size and a plan, and never automate it.
- **Verify the WRITE, not the tool's verdict.** An `--apply` printed `APPLIED — promoted 53 · synced 13
  · failed 0` on an invocation that changed **zero files**; a plain `git status` showed nothing touched.
  The next run reported the identical backlog. **Confirm with a changed-file count before reporting
  success**, then re-run the dry-run and compare category counts — the printed summary is a claim by the
  same instrument you are trying to verify.
- **SEAT-ONLY skills are the one irreversible loss, and no diff shows it.** They exist on exactly one
  seat and nowhere else, so a seat rebuild deletes work nobody knows is gone, and a set-difference report
  lists them as ordinary "extras". Rescue them by ADDING to CORE and **refusing any overwrite**: copy to
  a temp directory and `os.replace` into a destination that must not already exist. A `copytree` over an
  existing path is a merge decision disguised as a copy, and it deletes the evidence that the decision
  was ever needed.

**12. A SHARED QUEUE IS THE MOST DANGEROUS ARTIFACT TO GET THE SEAT WRONG — and a send is not a delivery.**
A spool, an outbox, a ledger written by several seats looks like any other script, and its hardcoded path is
the literal the checklist above already forbids. What makes it worse than a hardcoded read path is that a
hardcoded **write** path makes every seat's outbound mail land in ONE seat's file — and when a message is
addressed **to** that seat, its own flusher picks the row up and retries it **to itself**. The author sees a
working transport; the recipient sees the same handoff arrive on every retry.

- **Resolve the queue from the caller's profile** (`HERMES_PROFILE_DIR`, or an explicit env override), never
  from a literal. One file per sender; the consumer reads what was written *to* it.
- **A read-modify-write on a shared file needs a lock.** `os.replace` makes the WRITE atomic and does nothing
  about the READ: a cron flusher and a manual flusher both load the same row, both deliver it, both write back
  a file that no longer contains what the other saw. Measured — the same message logged twice by the receiver,
  ninety seconds apart, with neither run reporting an error. `fcntl.flock` around load → act → save is the
  one-line fix.
- **A subprocess that RETURNS is not a message that ARRIVED.** Three separate meanings hide behind one call:
  a non-zero exit is a **failure** (so check `returncode`; an unchecked one is a row deleted on a send that
  never happened), a **timeout** is usually a successful post with a slow reply, and only the receiver's own
  log is evidence of delivery.
- **Retrying on timeout multiplies REAL deliveries.** If the transport cannot distinguish "posted, no reply"
  from "never sent", every slow recipient gets the same message up to `MAX_ATTEMPTS` times — a colleague
  receiving one handoff five times is the queue, not the colleague. **Before re-sending anything, grep the
  receiver's inbound log for the text**; if it is there, mark it delivered and stop.
- **Test a queue's failure directions deliberately.** Queue one labelled probe and run two flushers
  concurrently: the pass is *exactly one* delivery and a clean spool. Then run it against an
  already-delivered row and assert it is recognised rather than re-sent.

