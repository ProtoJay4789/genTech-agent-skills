---
name: roadblock-ledger
description: "Use when a measurement exposes a gap. Record it."
trigger: A comparison against peers or standards reveals a gap we did not know to build; a hard external gate blocks work; or a session ends with open findings that must not evaporate.
tags: [roadblocks, gaps, compliance, learning, registry, verification]
version: 1.0.0
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [roadblocks, gaps, compliance, learning, registry, verification]
    related_skills: [guard-verification, claim-provenance, discovery-and-listing]
---

# Roadblock ledger — gaps that compound instead of evaporating

**Jordan's frame, and it governs the tone of every entry: *"I don't look at this as a time to beat ourselves
up. I look at this as always as a time to learn"* — and *"we also should be writing down the roadblocks that
we run into so that we could add them to the list of things we've run into."***

So the ledger is **not a failure log. It is a catalogue of what the market expects that we did not know to
build** — plus the gates that stopped us building it. Written in the language of a specification we have not
met yet, never in the language of a mistake.

## When to Use

**Triggers:** a comparison against a peer, a standard or a buyer reveals something we do not do; a hard
external gate blocks a build; a session ends holding open findings; a compliance sweep finds a gap that is
not yet in the ledger; or a gap you closed has no check guarding it.

A measurement disagreed with an expectation. That is the whole trigger. Not "something annoyed me".

**The test before writing: can you say what you EXPECTED, what you MEASURED, and what would have to change?**
All three stated means it is a roadblock. Any one missing means it is a mood — and a ledger of moods is
unreadable within a week.

## How gaps get FOUND — read the peers' published surfaces, in rank order

**A ledger only grows if something feeds it, and the feeder is a peer's own documentation.**

Procedure:

1. **Pick 3–5 surfaces that rank or convert where we do not** — the ones that beat us in search, or that a
   buyer reaches before us. Read the peer's OWN pages: its docs, its per-item markdown, its `llms.txt`,
   its listing copy.
2. **Extract the patterns, then split them by how many peers share them.**
   - **A pattern most of them have is a STANDARD** → an EXPECTATION GAP worth building.
   - **A pattern one of them has is STYLE** → not a gap. Note it and move on.
3. **Separate LIFT from SKIP, explicitly, in the write-up.** Marketing furniture (tracking parameters
   appended to example URLs, canned "when to prefer this" paragraphs) is noise an agent reads straight
   past. Naming what you are deliberately not copying is what stops the next session copying it.
4. **Copy the honesty, not only the features.** A peer publishing *"there are no customer stories, usage
   claims or testimonials here; the evidence is the catalogue"* is demonstrating a trust move we can
   match. A competitor admitting its limits raises the bar on our own copy more than any feature does.
5. **Record the gap the same session it is found**, in the language above — expected / measured /
   unblocks — because the finding is the deliverable and the memory of it is not.

**The most valuable class of find is the peer publishing its FAILURE MODES.** Per-route "what makes this
call fail, and what to do" is the highest-trust block on any competitor page and almost nobody does it. It
counts double when the data already exists internally (withheld-reason strings, refusal paths) — that is
not a build, it is a generator.

**Expect the first pass to be uncomfortable and say so plainly, then move on.** Finding five things we
lack in one afternoon is the normal output of this procedure, not evidence of a bad month.

## Two classes, never merged

| class | meaning | who acts | release condition |
|---|---|---|---|
| **EXPECTATION GAP** | a peer, standard or buyer does something we do not; it is now a bar we can clear | us — build it, or decide deliberately not to | a build, a file, a config, or a stated "we decline because …" |
| **HARD BLOCKER** | we cannot proceed at any effort — custody, terms of service, a third party, an unknown | whoever owns the gate | names the gate, the owner, and the fact that would release it |

**Never file a hard blocker as an expectation gap.** They read identically in a list and they need opposite
responses: one is work, the other is waiting. A gap with no owner gets re-opened every session by someone
who thinks it is unclaimed.

## Required fields per entry

```
ID + one-line title                E4 · no free sample route
EXPECTED        what a competent peer does, or what the standard says
MEASURED        the actual state, with the number and where you read it
WHY IT MATTERS  the consequence in buyer terms, one clause
UNBLOCKS        the concrete change — a file, a route, a message, a decision
STATUS          OPEN · DORMANT (with the reason) · CLOSED (with the check that guards it)
```

**A status that says only "blocked" is a shrug.** Every row names what would move it. The next reader must be
able to act without re-deriving the situation.

## The conversion rule — the reason this ledger exists

> **A roadblock that gets fixed but not checked will come back.**

Every closed **expectation gap** converts into an executable check in the same pass it is closed: a line in a
surface-parity checker, a presence probe, a cron assertion. Closing an entry without adding the check is
half the job, and the half that gets silently undone.

- **Name the checker in the CLOSED row** (`closed by <script> — asserts <the property>`), so the guard and
  the record point at each other.
- **A gap discovered by a checker is worth more than one discovered by hand** — it means the class is now
  instrumented. Say which checker found it.
- **When several gaps share a root cause, fix the root and keep the individual entries closed against it.**
  Five surfaces publishing one retired name is one root cause and five checks.

## Where it lives

- **One standing file per domain, not one per session.** New entries go at the top of their section with a
  date. A dated one-off file per incident is the failure shape — it cannot be read end to end, so nobody
  reads it.
- **Fold superseded editions in as a `## RELATED` pointer, do not merge their bodies.** A record written under
  an older frame is evidence of what we knew then.
- **Never delete an entry.** It goes `DORMANT` with the reason (the bar moved, we declined deliberately, the
  product retired), because "we decided not to" is a decision the next session would otherwise relitigate.

## Feeding compliance

The ledger is the input to the compliance sweep, not a parallel notebook:

1. Read the OPEN expectation gaps.
2. For each, ask whether a machine can decide it. If yes, it becomes a check **even while still open** — a red
   line on a scheduled sweep is a better reminder than a prose row.
3. Report from the checks, not from the prose, so the ledger cannot drift from reality.

**Ordering when several gaps are open: cheapest-and-concrete first.** A missing metadata file beats a missing
page; a missing page beats a missing integration. The same easy-to-hard rule that governs every other queue.

## Tone rule — this is the part that gets skipped

Write "we publish nine retired names" — not "we shamefully published nine retired names". **The finding is the
content; the self-assessment is noise, and it makes the honest entries harder to add.** A ledger written in a
voice that punishes the author stops being written to.

Equally: **never inflate a closed entry.** A gap is closed when the check proving it is green, not when the fix
landed. "Fixed, awaiting verification" is a legitimate status; a wrong CLOSED is worse than a missing one.
