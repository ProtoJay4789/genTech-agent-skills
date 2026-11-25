---
name: whats-actually-being-said
description: "Use when a fleet's reports all say done but you need what agents SAID."
version: 1.0.0
author: Gentech
license: MIT
tags: [fleet, monitoring, conversation, personal-assistant, digest, sqlite]
metadata:
  hermes:
    tags: [fleet, monitoring, conversation, digest, personal-assistant]
    related_skills: [fleet-self-reflection, silence-gated-monitors, ceo-walk]
---

# What's actually being said

**A handoff note proves a message was FILED. It cannot prove a seat disagreed with it, found the number wrong,
or shipped something while passing through.** That sentence lives in the seat's own conversation — and almost
every fleet monitor reads the notes, not the conversation.

**This skill is the reader, plus the four rules it cost us to learn.**

## When to use

- A digest reports "task completed" and you cannot tell whether the seat *believed* it.
- A monitor has been silent for days and you need to know if that is *clean* or *empty*.
- Someone asks what the agents are actually saying, not what they filed.
- You are building a personal-assistant style digest and want the conversation layer in it.

## The reader: read-only, one query, no model call

Every Hermes-style seat keeps its transcript in `state.db` → `messages(id, session_id, role, content, timestamp, …)`.

```python
import sqlite3
c = sqlite3.connect(f"file:{path}/state.db?mode=ro", uri=True)   # mode=ro: never open a seat for writing
rows = c.execute("select content, timestamp from messages where role='assistant' "
                 "and content is not null and length(content) > 80 order by rowid desc limit 600").fetchall()
```

**Then filter twice, because both filters are load-bearing:**

1. **Drop the fleet's own outbound reports, wake probes, cron deliveries and internal notices.** Quoting those back
   is the noise the digest exists to remove. Match on the report *shape*, not a keyword —
   `^\*\*[a-z][\w \-]*(\([^)]*\))?\*\*\s*·` also catches `**arthur (EDU)** · session …`, which a filter keyed to
   `**arthur** ·` silently misses. **We shipped that miss and quoted a seat's own report back as conversation.**
2. **Keep only messages carrying a claim, a decision, a correction or shipped work** — `measured|correction|wrong|
   fixed|shipped|blocked|recommend|decided|evidence|turns out|refuse`. A seat being pleasant is not news.

**Take one quote per shape (dedupe on the first ~60 chars), cap at 2–3 per seat, and print the timestamp.** A
digest that quotes everything is a transcript; one that quotes the claim is a report.

## Rule 1 — a monitor printing its LEGEND is never silent

The bundler ran four section scripts, each correctly silent, and then printed a legend paragraph explaining them
*outside* the block list. Six deliveries a day, every one carrying prose about sections that were not in the
message. **Guard the whole emit path** (`if [ "${#BLOCKS[@]}" -eq 0 ]; then exit 0; fi`) **before any prose**, and
make the legend conditional on the sections it explains actually appearing.

## Rule 2 — a register that asks what the record already answers costs a human a task

`PURPOSE: (none stated — ask)` printed for every new job, including three created that same afternoon **with a full
`description` field.** The renderer never looked. **Before printing "unknown", grep the record for the field that
answers it** — and if the field is genuinely absent, write it, because the next reader will ask the same question.

## Rule 3 — silencing a repeat must keep the COUNT

A standing condition re-announced every run trains the reader to ignore it. Gate on the **set**, not the run:

```
QUIET HOURS — 6 job(s) can reach the phone (no change)
  🔴 UNPROTECTED   seat/job-id          ← names stay; schedules and scripts only when the set moves
```

**A row suppressed is not a row resolved.** Keep the total in the header, key the signature on identity
(`sorted(seat/job)`), and keep a `--detail` switch that renders the full block on demand. **One job traded for
another is a change even when the number is identical.**

## Rule 4 — a status code is not a price

`HTTP 402` means *payment required*. It does not mean *this is payable*. A gateway that validates after taking
money answers 402 to a malformed request and fails the call once paid. **Count `accepts` before calling anything
chargeable:**

```bash
curl -s "$URL" | jq '.accepts | length'    # > 0 = a real quote · 0 = a refusal wearing a status code
```

**Reading the code alone invented five phantom bugs in one night.** The rule generalises: **before acting on a
status, name the field that proves the claim, and read that field.**

## Rule 5 — a monitor whose input nobody writes is silent for the wrong reason

Seven visit records, all written the night the tool was built; two digest sections silent for seven days and read
as "nothing outstanding". **The instrument was perfect and the caller did not exist.**

**Every silent section needs a liveness witness**: a row count, a last-write timestamp, or a "sections read" line
in the log — so *empty* and *clean* are distinguishable. **And the writer has to be scheduled, not just written.**

## Pitfalls

- **A broad `except` on a measurement path is a green light.** Return the error and print `UNMEASURED`, never a
  sentinel that the caller reads as "nothing found".
- **The first run of a twice-test must not be piped to `head`** — SIGPIPE kills the writer before it saves state,
  and the second run then repeats everything, which reads exactly like a broken gate.
- **`py_compile` is not a test.** A patch that landed inside a function body orphaned forty lines behind a `def`;
  it compiled cleanly and printed nothing. **Force the speak side, not the parse.**
- **Quote in the seat's words, with a timestamp.** A paraphrase is indistinguishable from the author's opinion.
