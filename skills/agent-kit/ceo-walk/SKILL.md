---
name: ceo-walk
description: "Use for a daily department reflection or on demand."
version: 1.1.0
author: Gentech
license: MIT
tags: [reflection, department, cron, strategy, fleet]
metadata:
  hermes:
    tags: [reflection, department, cron, strategy, fleet]
    related_skills: [fleet-tool-integrity, roadblock-ledger]
---

# CEO Walk — the department reflection

## When to Use

Load this when a department has to say where it stands — a daily scheduled reflection, a user asking "what
are we working on / what did we improve / what's next", or a seat that has gone quiet and nobody can say
whether it shipped anything. **Not** for the infrastructure question "are our crons working?" — that is
`dept-reflect`, and running one does not answer the other.

**Three fixed questions, per-department material.** Run it daily; run it on demand when a department needs to
say where it stands.

```
python3 /opt/data/profiles/<seat>/scripts/ceo-walk.py --seat <seat>
```

## Why it is not the self-reflection job

`dept-reflect.py` answers *"are our crons working?"* — an infrastructure question wearing a department's name.
It earns its place (it caught a delivery rail that had silently failed four nights running), but it says
nothing about whether the department is doing its job.

**The walk asks the three questions a leader asks:**

| # | question | answered from |
|---|---|---|
| 1 | what are we working on? | this department's handoff lane, plus its rows in the four lists |
| 2 | what did we improve? | its own completions (filtered to it) + its cron state as **evidence** |
| 3 | where are we going next? | the question that department is actually judged on |

## The doctrine lives in the code, not in a prompt

`DEPARTMENTS` in `ceo-walk.py` holds one entry per seat: `lane`, `next`, `measures`. **HQ's "where next" is
the delegation layer; EDU's is curriculum; Strategies' is capital; Social's is which channel carries us.**
A single generic reflection would give all four the same answer, which is the defect this replaced.

**To add a department:** add one `DEPARTMENTS` entry and one `ALIASES` entry. Do not fork the script.

## Two rules that keep it honest

1. **Filter completions to the department.** There is one fleet-wide completions file; reading it for
everybody makes four walks report the same work. Measured: the first run credited all four seats with the
same five items — a false attribution in the shape of a report.
2. **An empty week is the finding, not a gap to fill.** If a department shipped nothing, the walk prints
that. Never borrow a neighbour's row to make the section look healthy.

## Scheduling

One `no_agent` cron per seat, staggered so four reports do not arrive at once, and outside quiet hours. The
wrapper `ceo-walk.sh` converts the script's exit 2 (findings) to exit 0 — a reflection that found work is a
successful measurement, not a crash — and keeps exit 3 loud, because a walk that cannot measure must not read
as a quiet week. **Create the job with an explicit `telegram:<chat_id>` target, never `origin`, and never a
bare chat id** (`cron-delivery-audit`); where a group id is unverified, deliver `local` and say so rather than
shipping a rail that will fail silently.

## Reading the output

- `1 · WHAT ARE WE WORKING ON` — lane notes + **the department's own rows in build queue / Jordan's queue /
  pending / completed**. Read-only: a walk that writes to the lists turns a reflection into a queue edit.
- `2 · WHAT DID WE IMPROVE` — completions that name this department; cron counts appear here as evidence.
- `3 · WHERE ARE WE GOING NEXT` — the standing question plus the measures watched.

**Exit 2 means:** a cron is not ok, or the department left no trace this week. Both need a human read.

## The four lists: read all of them, write only your own rows

Every seat reads the durable lists; **ownership decides who may write.** HQ owns the file structure and any row
whose owner is gone; a department may write only rows carrying its own name; a desktop-only seat with no
profile on this host writes nothing.

**A seat editing another department's rows is the same defect as a seat promoting its own skill to the shared
core** — it looks like cooperation and it silently reassigns ownership. That is why the walk READS the lists
and never writes them: a reflection that queues work turns a status report into a queue edit, and the lists
must stay still for the readers arriving minutes apart.

**The boundary that makes the lists matter:** memory is a small fixed-size buffer; the lists are unbounded and
durable. When memory approaches its cap, the detail belongs in a list — **not deleted, and not compressed into a
shorter lie.** The failure mode is never "memory is full"; it is "memory was trimmed and the fact that mattered
went with it."

## Related

- `dept-reflect` — the infrastructure probe (kept, subordinate)
- `THE-FIVE-LISTS.md` — the four durable lists plus the Brain List; memory is a buffer, the lists are durable
- `roadblock-ledger` — record the gap when a measurement disagrees with an expectation
