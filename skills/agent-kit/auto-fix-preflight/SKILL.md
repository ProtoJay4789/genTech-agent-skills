---
name: auto-fix-preflight
description: "Detect → Fix → Verify → Report pattern for preflight checks. Every issue detected gets auto-fixed, then verified, then reported."
tags: [preflight, auto-fix, verification, agent-kit, devops]
trigger: "When building preflight checks that should auto-fix issues, or when debugging why preflight keeps flagging the same issue."
related_skills:
  - ../cron-truth-layer/SKILL.md  # preflight verification pattern
  - ../preflight/SKILL.md  # the actual preflight script
version: 1.0.0
author: Gentech Labs
---

# Auto-Fix Preflight — Detect → Fix → Verify → Report

## The Problem

Preflight checks flag issues but don't fix them. The same warning appears every cron run. Users get annoyed. The issue never resolves.

## The Solution

Every preflight check should follow this cycle:

```
1. DETECT  — Find the issue
2. FIX     — Auto-fix it (if safe)
3. VERIFY  — Confirm the fix worked
4. REPORT  — Tell the user what happened
```

## Implementation Pattern

```python
def validate_something():
    """Detect → Fix → Verify → Report"""
    # 1. DETECT
    issue = detect_issue()
    if not issue:
        return ""  # silent = all good
    
    # 2. FIX (if safe)
    if is_safe_to_fix(issue):
        fix_result = attempt_fix(issue)
        
        # 3. VERIFY
        if verify_fixworked(fix_result):
            return f"✅ Fixed: {issue} → {fix_result}"
        else:
            return f"⚠️ Fix attempted but failed: {issue}"
    
    # 4. REPORT (can't auto-fix)
    return f"❌ Needs manual fix: {issue}"
```

## Example: Vault Sync

```python
def validate_vault_sync():
    """Auto-commit uncommitted vault changes."""
    # 1. DETECT
    result = subprocess.run(["git", "status", "--porcelain"], ...)
    if not result.stdout.strip():
        return ""  # nothing to fix
    
    changes = result.stdout.strip().split("\n")
    
    # 2. FIX
    subprocess.run(["git", "add", "-A"], ...)
    subprocess.run(["git", "commit", "-m", f"auto: {len(changes)} changes"], ...)
    push = subprocess.run(["git", "push"], ...)
    
    # 3. VERIFY
    if push.returncode == 0:
        return f"✅ Vault synced: {len(changes)} changes committed + pushed"
    else:
        return f"⚠️ Committed but push failed"
```

## Example: Stuck Git Rebase

```python
def validate_git_state():
    """Auto-abort stuck rebases."""
    # 1. DETECT
    if os.path.exists(".git/rebase-merge"):
        # 2. FIX
        subprocess.run(["git", "rebase", "--abort"], ...)
        # 3. VERIFY
        if not os.path.exists(".git/rebase-merge"):
            return "✅ Aborted stuck rebase"
        else:
            return "❌ Rebase abort failed — manual intervention needed"
    return ""
```

## Safe vs Unsafe Fixes

| Issue | Safe to Auto-Fix? | Why |
|-------|-------------------|-----|
| Uncommitted vault changes | ✅ Yes | Low risk, can be reverted |
| Stuck git rebase | ✅ Yes | Abort is safe, no data loss |
| Detached HEAD | ✅ Yes | Switch to main is safe |
| API key expired | ❌ No | Needs human decision |
| Config drift | ✅ Yes | On-chain is truth, auto-correct |
| Stale data | ⚠️ Maybe | Flag, but don't delete |
| Missing file | ❌ No | Needs investigation |

## Output Format

Always report in this format:

```
✅ [Fixed] What was wrong → What was done
⚠️ [Attempted] What was wrong → What was tried → Result
❌ [Manual] What was wrong → What needs to happen
```

## Critical Pitfall: Preflight Inside Debounce Gate

When a script has both preflight checks AND debounce/silence logic, the preflight MUST run AFTER the debounce check decides to send — not before.

**Wrong pattern (causes orphaned preflight messages):**
```python
def main():
    preflight()           # ← Always prints output
    if should_suppress():
        sys.exit(0)       # ← Silences report, but preflight already printed
    print(generate_report())
```

**Correct pattern:**
```python
def main():
    if should_suppress():
        sys.exit(0)       # ← Silent exit, zero output
    preflight()           # ← Only runs when report will be sent
    print(generate_report())
```

**Why this matters:** With `no_agent: true` cron jobs, stdout goes directly to the user. If preflight prints before the debounce gate, the user sees orphaned preflight messages with no report attached — exactly the noise pattern this skill is meant to prevent.

**Found:** `defi-lp-consolidated.py` (Jun 22, 2026) — preflight was printing vault-sync status even when debounce suppressed the report. Jordan explicitly flagged: "I'm still getting a lot of these preflight cron jobs instead of the cron job itself."

## ⚠️ Critical Pitfall: Auto-Fixing Drift When the Direction Is Unknown

"Two copies differ" does **not** tell you which one is right. Before auto-fixing any
copy-drift finding, establish the direction, or you will destroy work.

**Real case (2026-09-18, api-health-check fix layer):** `revenue-monitor.py` was
**39,184 B deployed vs 31,171 B in the vault** — the *live* file was newer and held
~8 KB that had never been committed. Auto-copying the canonical over it would have
deleted live code, silently, on a schedule.

**The rule — split targets into two classes:**

| Class | Know the authority? | Action |
|---|---|---|
| **Curated / reviewed** (hand-maintained table) | ✅ Yes — the canonical is the reviewed source | Auto-FIX |
| **Auto-discovered** (found by scanning) | ❌ No | **DETECT + REPORT only** |

For discovered drift, report the **direction** (compare mtimes) and let a human decide:
- *deployed is NEWER* → the vault copy is stale → **commit the live file**
- *canonical is NEWER* → the deployed copy is stale → safe to redeploy

Collapse N discovered items into **one summary line** plus a detail command; 30 paths
in a cron message buries the signal it exists to carry.

## ⚠️ Before promising a fixer, prove each finding HAS a fix path that can run HERE

**"It reports issues" and "it can fix issues" are separate claims, and a fixer that cannot fix must say
so per finding.** Read the checker's fix branches before wiring `--fix` on a schedule: a fix has three
failure shapes, and only the first is the checker's fault.

| shape | what it looks like | what to do |
|---|---|---|
| **refuses by design** | the fix exists but returns without acting while a precondition holds (e.g. a database checkpoint when a live process owns the file — it fails closed rather than risk corruption) | leave it; name the precondition as the gate (*"needs the service stopped"*) |
| **no branch at all** | the finding is only ever printed with an instruction to run an interactive wizard | never automate it — it touches credentials or identity by design |
| **upstream-only** | the checker's own source states a local fix does not persist because the next install restores pinned versions | not your defect; say "wait for the upstream fix" or build the artifact |

**Compute the verdict, never assert it.** Print `N of M fixable by this job as configured`, derived from
the finding lines themselves, and when N is 0 say what that means: *"enabling --fix would change nothing
today — this is a report for a human, not a broken job."* That one sentence is what stops a repeated
report from reading as a recurring bug.

**Tag every finding with the hand that unblocks it**, and put the tag on the same line as the finding:

- `NEEDS-HOST` — requires the service/container stopped, or host-level access the agent lacks.
- `NEEDS-JORDAN` — an interactive credential or identity step; must not be automated.
- `UPSTREAM` — fixed only by a new release/artifact; waiting is a valid decision.
- `FIXABLE-NOW` — a branch the checker can run unattended.
- `UNCLASSIFIED` — read it before assuming a fix exists.

**The defect this fixes is not "it can't fix".** It is that the same findings were reported daily with no
owner named, so nobody acted on any of them. **A finding that repeats unchanged for days is a report
missing an owner, not a recurring bug** — classify it before adding another reminder.

### `--fix` that migrates config is not safe to schedule

**Check what `--fix` actually calls before putting it on a cron.** A repair path can legitimately invoke
a **non-interactive config migration**, which rewrites the config file. Against hand-tuned profiles, an
unattended rewrite four times a day is a worse failure than the finding it repairs — it can drop a
hand-set default with no diff and no reader.

```bash
grep -rn 'migrate_config\|write_text\|open(.*"w"' <checker>/*.py   # what does --fix WRITE?
```

If the safe subset is real, gate it: run `--fix` only when **every** finding is in the FIXABLE-NOW class,
and never when a NEEDS-HOST/UPSTREAM item is present — otherwise a harmless-looking run does nothing and
reports a green light. Take a config backup before the first scheduled run.

## Safety Gates Every Auto-Fix Needs

1. **Validate before deploying.** Compile the source text in memory
   (`compile(src, path, 'exec')`) before copying it over a working entry point.
   Deploying a broken canonical turns a quiet drift into a dead job.
2. **Verify after fixing.** Re-hash (or re-run the check) and confirm the fix landed.
   A fix that reports success without verification is indistinguishable from a no-op.
3. **Refresh the reported state.** Re-derive the finding after repairing, so the report
   never shows drift that was just healed.
4. **Report fixes — never hide them.** Silent self-healing lets the underlying habit
   (edit the source, never re-deploy) go unnoticed for months. The goal is a robust
   system, not an invisible symptom.
5. **Keep one read-only mode.** (`json`) so machine consumers and debugging can never
   trigger a write; add a `--no-fix` escape hatch.
6. **Never auto-delete.** Duplicate files, dead vhosts, anything where "remove it" is a
   plausible fix — those are **human decisions**. Diagnose instead (state latent vs live,
   give exact remedy commands) and mark them manual.

## ⚠️ A fixer's own artifacts must never land in the set it just cleaned

**Measured: a sweep that moved operational logs out of a directory wrote a `README.md` POINTER into that same
directory.** The next run found one file, moved it, and reported `✅ FIXED — moved 1 file (48 MB)` — a claim of
work it had not done, inside a report the user reads as progress. **Write the pointer, tombstone or marker OUTSIDE
the directory you empty**, and `rm -f` any earlier marker before the next pass. A maintenance job that re-detects
its own output is not idempotent; it is a metronome that reports a fresh fix forever.

**Prove the fix by the FINDING disappearing, never by the fixer's own success line.** The honest verification for
a self-fix sweep is the detector's count before vs after (measured: 5 findings → 4 once the repaired item was
gone). *"I moved the files"* is an action; *"the finding is gone"* is the result, and only the second is what the
report is claiming.

**Count the EFFECT, not the announcement.** `mv -n … -print | wc -l` reported **2** when **9** files had moved —
`-n` silently skips existing targets and prints only what it chose to act on. A fixer's own log line is the least
reliable count it has: snapshot the set before and after (`find … | wc -l`) and report the delta, or the number in
the report is a description of the tool's mood rather than of the world.

### A number in a report must be a count, not a concatenation

`ls -la /profiles/*/state.db-wal | awk '{printf "%.0f", $5/1048576}'` reported **`2548649 MB`** for four files
totalling 64 MB. `printf` without a newline emits **one continuous string**, so a per-file format applied to N lines
concatenates N digits — and the result is a plausible-looking giant number rather than an error.

**Use a format that cannot merge lines** (`printf '%.0f\n'`), or drop into a per-item loop and take an aggregate
explicitly:

```bash
for f in /profiles/*/state.db-wal; do [ -f "$f" ] && echo $(( $(stat -c %s "$f") / 1048576 )); done | sort -rn | head -1
```

**Sanity-check any derived number against a hand-computed one before it reaches a report.** A single absurd digit
count is the tell; the fix is cheap, but a wrong number in a health report is a number nobody re-derives.

### A verified result is the SCRIPT's exit code, not the last command in the pipe

`python3 verifier.py 2>&1 | tail -4; echo "exit=$?"` printed **`exit=0`** for a verifier that actually exited **2** —
`$?` after a pipeline is the exit status of the **rightmost** command (`tail`), which succeeded at its own trivial
job while the subject failed.

```bash
out="$(python3 verifier.py 2>&1)"; rc=$?      # capture output and the real status separately
printf '%s\n' "$out" | tail -4
```

**Never put a pager or a filter between the thing whose status you are checking and the `$?` you read.** This is
the same class of error as trusting the *fixer's* success line: the measurement silently reports the wrapper.

### Route what you cannot fix into the user's durable queue — one bounded section, rewritten every run

Classifying a finding (`NEEDS-HOST` / `NEEDS-JORDAN` / `UPSTREAM`) is only half the job. **The other half is putting
it where the human will actually see it**, or the classification just makes the next identical report easier to
write.** A cron's chat output scrolls away; a durable list does not.

Keep one section of the user's own queue file owned by the job:

- **Delimit it with a stable marker heading** the job can find and replace.
- **Rewrite the section, never append to it.** An appending job at four runs a day turns a three-item queue into a
twelve-item one by lunchtime, and a queue that grows without anyone acting is the exact failure mode being fixed.
- **Replace only between the marker and the next `## ` heading**, so every other section stays byte-identical.
- **Prove idempotency by running twice**: the marker count must be identical after run 1 and run 2, and a `diff` of
  every `## ` heading before/after must show only the added section.
- **Stamp the section** (`_Last run <time> — replaced, not appended._`) so a reader can tell live findings from stale
  ones, and write `_Nothing needs your hands right now._` rather than leaving an empty section that looks broken.
- **Carry the fix report into the same section** (`**Fixed by the doctor this run:** …`) so one page answers both
  "what did it do" and "what is left for me".

**Only route what genuinely needs a human** — things no agent may do: a visible write under the user's identity, a
legal/interactive credential step, a plan or billing decision. Anything an agent can do itself belongs in the fix
step, not the queue; a queue padded with agent-doable items trains the reader to ignore it.

## ⚠️ Critical Pitfall: Matching a Word Shared by Both Branches

When summarising two opposite outcomes, never count by a substring they **both** contain.
Building this, a tally of "how many are deployed-newer" matched `"NEWER"` — but both
direction strings ended in "NEWER" (`deployed is NEWER` / `canonical is NEWER`), so it
reported **5** when the truth was **3**.

**Rule:** match the **full distinguishing phrase** (`"deployed is NEWER"`), and **check the
computed number against the underlying detail list** before shipping. A wrong count in a
health report is worse than no count — it is a plausible number nobody re-derives.

## For Agent Kit

This pattern is the "fix layer" of the truth architecture:

1. **Truth Layer** — verify data is fresh (cron-truth-layer)
2. **Fix Layer** — auto-fix what's safe (auto-fix-preflight)
3. **Report Layer** — tell the user what happened

Every cron job should have all three. Detect without fixing is noise. Fix without
verifying is guesswork. Verify without reporting is invisible. **Fix without knowing the
direction is data loss.**
