---
name: overnight-maintenance-window
description: "Use when auditing or building overnight cron maintenance."
version: 1.0.0
author: Gentech
license: MIT
tags: [cron, overnight, quiet-hours, maintenance, curation, fleet, agent-kit]
metadata:
  hermes:
    tags: [cron, overnight, quiet-hours, maintenance, curation, fleet, agent-kit]
    related_skills:
      - ../cron-health-standard/SKILL.md
      - ../multi-agent-build-queue/SKILL.md
trigger: "When setting up overnight maintenance, when the user asks 'who goes through all these folders', when nightly jobs are noisy or get ignored, or when auditing whether a quiet window actually holds."
---

# The Overnight Maintenance Window

## When to Use

- Setting up, rebuilding or auditing an overnight / quiet-hours maintenance window for a fleet.
- A nightly job is noisy, or its alerts are being ignored.
- Someone asks *"who goes through all these folders?"* — the answer is a scheduled maintainer, not a human.
- Auditing whether a claimed quiet window actually holds.
- A finder keeps re-surfacing something the user already decided against.
- Designing unattended upkeep for a vault, corpus or list that writers grow all day.

An agent fleet writes all day and nobody reads it. The overnight window is where a fleet stops
accumulating and starts **maintaining itself**: auditing the brain, resurfacing ideas that were
written and never routed, checking memory, and tidying what has gone stale.

Two things make it work, and both are contracts rather than scripts:

```
SILENT PRODUCERS   every overnight job writes STATE and says nothing
ONE CONSUMER       the wake-time brief reads that state and is the only voice
```

---

## 1. The window is a delivery rule, not a schedule

**Everything that runs overnight delivers `local`.** Not "quiet", not "only on failure" — silent.
A 04:00 failure gets read at 06:30 either way; the only thing a 04:00 message changes is that the user
learns to ignore the channel. **An ignored alert teaches the reader to ignore alerts.**

**The wake brief is the single delivery point.** Put its first slot at the wake boundary (not before
it) and make its prompt read the overnight state files directly, so nothing discovered at 01:00 is
lost — it simply waits until the user is up.

**A producer that only writes state must still be readable at wake.** Two fields make that possible:
its verdict and its **date**. A state file older than the cadence it claims is itself the finding —
*older than 28h* on a daily job means it never ran, which is not the same as "it ran and was fine".
Have the brief check staleness, or a dead job reports as a clean night forever.

## 2. Express the window, then PROVE it

A quiet-hours claim is a claim about every crontab in every profile, so it must be computed:

```
for each job in each profile's cron store:
    expand its schedule expression over a week
    intersect with the quiet window
    count deliveries inside it
```

**The honest output is a number** — `0 deliveries inside [03:00, 10:30) UTC` — plus the jobs expanded.
Never eyeball it: a job quiet because it is unscheduled is indistinguishable from one that is quiet
because it is disciplined.

- **Fix the wake boundary and the window in UTC, and say what they mean in the user's timezone.** A
  window written as local time in one place and UTC in another is two different windows.
- **The wake boundary is not inside the window.** If wake is 10:30Z, a job at exactly 10:30Z is the
  wake, not a violation — counting it as one makes the check unusable, and an unusable check gets
  switched off rather than fixed.
- **Cron schedules are fixed-UTC**, so state the DST consequence out loud instead of letting every
  window slide silently twice a year.
- **State the user's window as a standing preference, in both zones** (11pm–6:30am ET = `[03:00,
  10:30) UTC`), so a rebuilt job inherits it from the rule rather than from someone's memory.

## 3. The window produces THINKING, not just tidying

Tidying is the easy half. The value is the half that reads for meaning:

| Job | Question it answers |
|---|---|
| **Audit** | which ideas did nobody route anywhere? which lanes went dark? |
| **Curate** | which class of thing has gone past its shelf life? |
| **Check in** | which memory file is near its cap? |
| **Route** | where does each finding belong? |

**Every run writes a durable dated record** — a report path per day — not only an alert. The same idea
resurfacing three nights running is a signal, and it is only visible if each night was written down. An
overnight job whose output exists only as a chat message has no history at all.

**A lost idea earns a line only if it carries money, moat, or a lane gone dark.** Twelve findings is a
wall; three is a brief. Rank, cap, and say what was dropped.

## 4. Policy as DATA, so it survives a wipe

Shelf lives belong in a config file the user can edit, not in the maintainer's habits: a table of
`class → TTL`, plus a list of classes that are **permanent and never refreshed** (archives, backups,
canonical skill trees, completion records). *A record should not be "updated", and a backup that gets
refreshed is not a backup.* The rule living in data is what lets a rebuilt tool behave identically after
the script that implemented it is gone — see `references/staleness-policy.md`.

## 5. The curator PROPOSES — it never disposes

**Past-TTL means someone must look; it does not mean delete.** An auto-archived open item is a
disappearance, not a tidy-up, and the reader cannot tell a considered removal from a mistake. So:

- Flag stale things; move nothing that a human has an open claim on.
- **Three exits, no fourth** for anything routed: **Done → registry with proof**, **Waiting → pending
  with a gate AND its release condition**, **Never → archive with the reason written down**.
- A row that cannot name its exit is not a row. "Blocked" alone is a shrug, not a status.

## 6. A decided item must stop being a FINDING

**Any finder that routes into a list has to read the decisions record.** Mark the decision on the
artifact itself (`SKIPPED`, `DECLINED`, `do not re-surface`) and have the audit exclude anything
carrying that marker. Without it a declined idea returns every night as a newly-found opportunity, and
"the user dropped it" becomes indistinguishable from "we forgot it". That is the difference between a
queue and a treadmill.

## 7. Verify the maintenance itself

- **Run a new writer twice.** Run 1 routes N; run 2 must route 0. A writer run once has never
  demonstrated dedupe, and the second run is the only proof it has a key.
- **Back up before writing, then prove the human regions are byte-identical** — diff them and print it.
  An automated write that quietly rewrites a person's prose is the worst failure here, because it
  reports success.
- **Distinguish "it ran" from "it worked"**: check the run's own artifact (a dated report, a state
  file, a log line), never its timestamp alone.
- **After editing a job's prompt or schedule, confirm the edit survived a live scheduler tick** before
  reporting it as live.

## Pitfalls

- **A monitor that cannot tell "nothing happened" from "I could not read it" reports clean nights.**
  An unreadable job list is UNKNOWN, and UNKNOWN must speak.
- **One writer per list.** Two writers means no owner and no way to tell whose rows are whose; the
  producer appends and the reader never writes back. A single unkeyed writer appending nightly is how a
  500 KB list of one job's own briefs comes into existence and stops being read.
- **Never derive a state from the by-product of an action you may skip** — ask the source of truth.
- **A flag is not evidence.** Carry artifact paths, not `re-audited: true` booleans.
- **Quiet hours are not an exemption for the maintainer.** A 04:00 discovery is still recorded and
  still healed; only the message waits.
- **A finder re-emitting a decided item is not a bug in the list, it is a missing read.** See §6.

## Support files

- `references/staleness-policy.md` — the class → TTL table, the permanent classes, and the schema for
  the policy file.
