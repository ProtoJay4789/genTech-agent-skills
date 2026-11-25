---
name: memory
description: Persistent memory management — save, load, rotate
category: core
priority: critical
---
# Memory Management
Handle persistent memory across sessions. Save durable facts, load context.

## Memory Dietician — Automatic Size Enforcement

Memory files grow over time and degrade agent performance. The Memory Dietician is a no-agent cron job that
measures the four context files, proposes cuts, and hands off to whatever relief exists.

| File | Limit | What actually acts on it |
|------|-------|--------------------------|
| MEMORY.md | **3,200 chars** | `memory-relieve.py`, at **90%** of cap — moves ONE longest reference-shaped entry into the dated archive, verbatim and ledgered. Refuses when every entry is load-bearing (the correct answer for a seat whose facts are all operating facts). |
| USER.md | **1,800 chars** | **Nothing automatic.** Facts about the user are not a size decision; a regex cannot merge them. Needs the consolidation pipeline below, or a hand. |

**Caps are CHARACTERS, not lines or bytes, and they are read from `config.yaml` where a seat overrides
them** — quote the cap you read, never a remembered one. **Above the cap the save is rejected silently**, so
an over-cap file fails to persist rather than failing loudly.

**Two thresholds, and the gap between them is the bug to look for:** the alarm speaks at **85%** (the
assistant/duty bundle's memory line) while relief acts at **90%** (`TRIGGER` in `memory-relieve.py`). A file
sitting at 86–89% therefore produces a warning that **nothing will ever act on**, once per run, forever.
Measured: three of four seats were parked inside that dead band while the warning repeated. **When a gauge
warns and nothing changes, compare the two thresholds before concluding the hand is missing.**

**Installation:** canonical logic at `/opt/data/scripts/memory-dietician.py` (`--check`), invoked through a
thin per-seat wrapper (`profiles/<seat>/scripts/memory-dietician.sh`) that also runs the dream pass and the
relief pass. Scheduling is per-seat; do not assume a time — read the job.

> **STATUS — the original was lost in a wipe and replaced with a reporting dietician.** Measured:
> `memory-dietician.py` absent and no dietician cron registered, so nothing enforced the caps. The rebuild is
> deliberately *safer than the original*: it measures, archives a dated copy, and alerts; **it never rewrites
> memory by position**, which is a destructive write of durable memory dressed as maintenance.

## USER.md was unreachable — a model proposes, a DETERMINISTIC SCRIPT writes

**The rule "facts about the user are not a size decision" is correct, and it left the one file that is
usually fullest with no hand at all.** The resolution is not to loosen the rule: it is to split proposing
from writing.

- **A model reads the file and returns a COVERAGE MAP, never new file content:**
  `{"target": "<path>", "entries": [{"from": [1,2], "text": "merged"}, {"from": [3], "text": "kept"}]}`.
- **A deterministic applier verifies and writes** (`/opt/data/scripts/memory-merge-apply.py`): every input
  entry index must appear in **exactly one** output entry. A gap refuses (`indices [3] appear in NO output
  entry`); a duplicate refuses (`index 1 appears in entry 0 AND entry 1`). **A silent deletion cannot pass,
  because the arithmetic stops closing before anything is written** — this is what makes an LLM safe on a
  memory file, and it takes three fixture tests to prove (complete map → applies; dropped index → rc 2;
  duplicated index → rc 2).
- The applier backs up, archives the pre-merge text in `11-Mess Hall/memory-archive/`, ledgers before/after
  hashes, and **rolls back if the post-write re-read disagrees**.
- **Merge by TOPIC, never by size.** Two entries making the same point about the user become one entry that
  keeps every distinct fact from both. Length is not expendability — the longest entry is often the operating
  fact the seat uses every turn.
- **A refusal is the finding.** If the map cannot be made without losing a fact, report that; do not loosen
  the map until it passes. Loosening the guard to clear a warning is silencing the instrument.

**This is wired as a cron pipeline (gate + chain) rather than a schedule:** the applier's companion probe
prints the over-trigger files with byte-stable output, so the gate suppresses the model run entirely when
nothing has crossed, and the consumer receives the dietician's own output as context. The doctrine and the
rules for building more of these live in `cron-health-standard` → *Pipelines*.

## Consolidating by hand — the procedure when no rule can decide

**When the file is over cap and no automatic hand may touch it, do it in this order and prove each step.**
Do not "trim" — consolidating is a merge, and the difference is that a merge has an audit trail.

1. **Read the whole file and number the entries** (split on a line containing only `§`). A cap decision made
   from a partial read always removes the load-bearing entry.
2. **Find the duplicate TOPIC pairs, not the long entries.** Two entries that say the same thing about the user
   are one fact written twice; the longest entry is usually the operating fact quoted every turn.
3. **Rewrite each pair as one entry that keeps every distinct fact from both** — names, paths, numbers,
   hard lines (`never`, `HARD LINE`), and any standing instruction. Merging is where a `never` gets softened
   into a preference, and the softened rule then reads as permission in a later session.
4. **Write the file whole** (`write_file`), never through an entry-structured memory tool: a `§` inside a
   content field CREATES an entry rather than replacing one (see below), so a "merge" through that path grows
   the file.
5. **Re-measure and report the pair**: `chars before → after`, `entries before → after`, and the % of cap.
   A consolidation whose numbers did not move did not happen.
6. **Say what was merged and why it was the same fact twice.** "Consolidated" with no list is indistinguishable
   from "deleted the ones I found inconvenient".

**A merge that needs a fact removed to fit is not a merge.** Move the reference-shaped detail to the dated
archive (`11-Mess Hall/memory-archive/`) verbatim and ledger it — never silently drop it, and never shorten a
rule to make room for a fact.

## A stored memory is a SNAPSHOT WITH A DATE — never a live read

MEMORY.md is frozen at session start, so every line is a photograph, not a probe. **Negative results decay
just as fast as positive ones, and they are more dangerous because they justify doing nothing.** Measured:
a memory line said a payment credential was "verified present", the credential had since been removed, and the
estate sat behind a door nobody could open while the agent quoted its own memory as evidence. In the same
session the reverse nearly happened — a line asserting a credential was *absent* was contradicted by the user
saying he had provided it weeks earlier, and both were true about different dates.

- **If a memory line is the deciding fact for a blocking action, re-measure it first** — one command settles
  it: `search_files (target='files')` for the file, `grep -c '^PREFIX_' .env` for the key, `curl -o /dev/null
  -w '%{http_code}'` for the endpoint. Quoting
  memory as proof of absence is the same class of error as fabricating a measurement.
- **Write absence with a date and a scope:** `CDP creds — ABSENT as of <date>: not in .env, not in 4 rotated
  copies, 0 in session store` beats `no CDP creds`. The dated form tells the next session exactly what to
  re-run instead of what to believe.
- **Record the SEARCH, not just the verdict.** A negative finding is only as good as its coverage: name the
  stores searched (env + rotated copies, session DB, logs, backups) so a later session can extend the search
  rather than repeat the argument.
- **When the user's recollection contradicts the memory, believe the recollection enough to search properly.**
  "I gave you that weeks ago" is a lead, not a mistake — run the search and report both facts (it existed then,
  it is gone now) rather than correcting him from a frozen line.
- **Documentation outlives the secret.** A note saying "both present in .env" survives the key's removal and
  becomes a false claim by omission. When any credential moves, append a line to the rotation log the same day
  (what changed, when, where it now lives, what restarted) — that one line prevents an hour of forensics.

## `§` in a memory-tool content field CREATES an entry — it does not replace one

Measured 2026-10-15 while trimming gentech's own memory. The memory tool's `content` is **entry-structured**
by the `§` separator. So a `replace` whose new content contains `§` **splits into two entries and adds one** —
the file *grows* while you believe you are consolidating. Observed going 1,945 → 1,991 → 2,087 chars across
three "trimming" batches before the cause was found.

- To shrink, a batch must contain an actual `remove`, or a replacement whose content has **no** `§` and is
  genuinely shorter than the entry it matches.
- **Re-read the reported usage after every batch.** If it went UP while you were trimming, you added an entry.
- `old_text` must be **unique**: if a batch fails with "matched multiple distinct entries", the duplicate is
  usually your own earlier attempt. Remove one, then retry — the batch is all-or-nothing, so nothing was applied.
- Target the **85% trigger of the cap you read**, not 100% — at the cap the save wall blocks your own writes,
  and an over-cap save is rejected **silently**, so the entry you think you wrote is simply absent next session.

**Key lesson (Jul 28, 2026):** Someone built an elaborate memory stack around Hermes, then deleted it and restored defaults — the agent worked dramatically better. More memory = worse performance. Keep MEMORY.md and USER.md lean. The Memory Dietician enforces this automatically.

**Manual pruning guidelines:**
- MEMORY.md: Condense Vanito/HIKARI entries. Remove redundant model routing info. Keep Seedance limitations (face bypass hierarchy, no lip-sync).
- USER.md: Keep financial context (rent $795, burn $1,700/mo), collaborator preferences (Vanito's detail-obsessed workflow).
- witness-log.md: Only unresolved or recently resolved entries. Trim anything older than 7 days with a resolved status.
- context-weight.md: Focus on active priorities. Stale project entries (unstarted hackathons, pending items without action) are noise.
