---
name: memory
description: Persistent memory management — save, load, rotate
category: core
priority: critical
---
# Memory Management
Handle persistent memory across sessions. Save durable facts, load context.

## Memory Dietician — Automatic Size Enforcement

Memory files grow over time and degrade agent performance. The Memory Dietician is a no-agent cron job that runs nightly and enforces size limits on the four context files:

| File | Limit | Behavior |
|------|-------|----------|
| MEMORY.md | 2,100 chars | Reports when over limit |
| USER.md | 1,300 chars | Reports when over limit |
| witness-log.md | 1,500 chars | Auto-trims resolved entries > 7 days old |
| context-weight.md | 1,200 chars | Reports when over limit |

**Installation:** Script at `scripts/memory-dietician.py`, cron job named "Memory Dietician — Nightly Trim" running at 5:00 UTC daily. Silent when healthy, reports only when trimming or over limit.

> **STATUS 2026-10-15 — the original was lost in the wipe and has been REPLACED with a reporting dietician.**
> Measured: `memory-dietician.py` absent from `/opt/data/scripts/` and every profile, and **no dietician cron
> registered** — so nothing was enforcing the caps. Rebuilt deliberately *safer than the original*: the new
> script **measures, archives a dated copy, and alerts; it never rewrites memory**. The original trimmed by
> position, which is a destructive write of the agent's own durable memory dressed as maintenance.

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
- Target the 85% trigger (MEMORY 1870 / USER 1169), not 100% — at 100% the save wall blocks your own writes.

**Key lesson (Jul 28, 2026):** Someone built an elaborate memory stack around Hermes, then deleted it and restored defaults — the agent worked dramatically better. More memory = worse performance. Keep MEMORY.md and USER.md lean. The Memory Dietician enforces this automatically.

**Manual pruning guidelines:**
- MEMORY.md: Condense Vanito/HIKARI entries. Remove redundant model routing info. Keep Seedance limitations (face bypass hierarchy, no lip-sync).
- USER.md: Keep financial context (rent $795, burn $1,700/mo), collaborator preferences (Vanito's detail-obsessed workflow).
- witness-log.md: Only unresolved or recently resolved entries. Trim anything older than 7 days with a resolved status.
- context-weight.md: Focus on active priorities. Stale project entries (unstarted hackathons, pending items without action) are noise.
