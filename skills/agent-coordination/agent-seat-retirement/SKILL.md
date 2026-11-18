---
name: agent-seat-retirement
description: "Use when retiring or decommissioning an agent seat."
trigger: "When a seat is retired, decommissioned or removed; when a 'deleted' agent still replies; when orphaned profile directories need cleanup; when a fleet roll-call returns ACKs from seats nobody expects to exist."
tags: [fleet, seats, profiles, retirement, cleanup, orphan]
version: 1.0.0
author: gentech-treasury
license: MIT
related_skills: [hermes-profile-clone-worker, telegram-bot-seat-provisioning, fleet-skills-sync]
metadata:
  hermes:
    tags: [fleet, seats, profiles, retirement, cleanup, orphan]
    related_skills: [hermes-profile-clone-worker, telegram-bot-seat-provisioning]
---

# Retiring an Agent Seat

**Teardown is the half of seat management that has no skill.** There are procedures for cloning a
seat, provisioning one, and waking one; this is the one for taking it out of service. The failure it
exists to prevent is specific and repeatable: a seat is retired, and weeks later it answers a wake,
signs a checkpoint, and is counted as a fleet member.

## When to Use

- A seat is being retired, decommissioned or removed, and its skills and notes must survive it.
- A seat reported as deleted still answers a wake, or ACKs a roll-call.
- Orphaned profile directories need a decision: keep, migrate, or remove.

## Establish membership by CREDENTIAL, never by directory

Before retiring anything, decide whether it is a seat at all. The discriminator is credentials, not
presence:

- a live seat carries a **bot token** and an **API server key** in its `.env`;
- a profile directory with **neither** is not a seat, however much content it holds.

**A wake proves nothing.** `hermes -p <name> chat --query-file … --oneshot` runs the CLI against ANY
profile directory, member or not. A retired seat therefore returns fluent, well-measured output and
is indistinguishable from a live one from the inside. The tell is the FLEET rail: a peer message to a
real seat answers, and to a corpse is rejected because it has no key. When the two disagree, believe
the rail.

## The sequence — deletion is LAST, not first

1. **Promote seat-only files to the canonical.** Run the skills sync in its report/sync mode. Any file
the canonical lacks is a **contribution, not garbage** — the sync refusing to overwrite a seat-only
file is the tool protecting it. Promote, then re-run until clean.
2. **Confirm where the notes actually live.** Handoffs, journals and notes normally live in the
   shared brain (the vault), which is a DIFFERENT tree from the profile directory. Verify the real
   paths before assuming a delete would lose them — and do not assume the reverse either.
3. **Measure what the directory holds** before anyone signs off. A size-by-subdirectory listing is
   enough: it is typically `bin/` (largest), `skills/` (already in the canonical), caches, and a
   `state.db`. **"Large" and "irreplaceable" are not the same property**, and size alone is not a
   reason to keep or to delete.
4. **Remove the profile directory.**
5. **Prove the corpse no longer answers.** Re-run the wake probe against the removed seat and assert
   it fails. Without this step the binaries are gone and the ghost still replies — which is the exact
   condition the retirement was supposed to end.

## Roster hygiene

- **Build any roll-call from credentials, not from a directory listing.** A checkpoint dispatched to
  "all seats" will include retired directories that answer, inflating the roster and producing ACKs
  from non-members. State which seats were excluded and on what evidence.
- **A seat with zero jobs is not automatically a dead seat.** An empty ring has causes that only the
  seat's own history can supply — a deliberate cleanup, a ring that never needed a job, or jobs that
  were never scheduled. Read the record before writing a cause.

## Pitfalls

- **Treating a wake-reply as proof of life.** The wake path is profile-scoped and unconditioned; only
  the fleet rail tests membership. Count a seat as live when it holds credentials and answers on the
  rail, not when it can be made to talk.
- **Deleting before migrating.** Retirement is a migration with a deletion at the end. Doing it in the
  other order turns "retired" into "lost".
- **Retiring on size alone.** The bulk of a stale profile is usually toolchain and cache, and the
  skills in it are already in the canonical. Measure composition, not total.
- **Leaving the corpse wakeable.** Removing the directory without proving the wake now fails leaves
  the failure mode intact, and a later roll-call will quietly resurrect the seat.
- **Assuming a team lead's decision is a delegation.** Retiring a seat destroys state nobody may have
  inventoried; propose the migration and the evidence, and let the fleet's owner authorize deletion.
