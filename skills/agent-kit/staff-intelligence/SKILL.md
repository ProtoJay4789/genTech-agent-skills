---
name: staff-intelligence
description: "Use when grading, hiring or promoting fleet agents."
---

# Staff Intelligence — grade the fleet from the record

## The premise (Jordan, 2026-10-15)
> "Agents get reborn and renamed to keep it fresh. It restarts the counter. Everybody is a copy of
> Gentech but it's their opinions in the mess hall/green room, individual work and output, and
> overall contribution to Gentech."

**Every agent runs the same base model.** Nothing about *what an agent is* can differentiate it.
The only differentiator is **the record** — and there are five surfaces of it, all already on disk.

## The five signals (all measurable)

| Signal | File | Passes when |
|---|---|---|
| **identity** | `SOUL.md` (profile dir, else `00-System/agent-profiles/<name>/`) | ≥2000 B (real soul; stock stub ≈667 B) |
| **duties** | `cron/jobs.json` | ≥1 job — does it *work*, or is it only a voice? |
| **rep** | `01-HANDOFFS/*completions*.md` | ≥1 KB (≥50 KB scores 2) — the audited record, the only honest résumé |
| **tenure** | `memories/MEMORY.md` | ≥1200 B — has it carried context long enough to have any? |
| **opinions** | files in `11-Mess Hall/` + `09-Green Room/` naming it | ≥10 — has it said anything of its own? |

Score = sum (identity 1, duties 1, rep 1–2, tenure 1, opinions 1), max 6.
**TEMPORARY** ≤1 · **WORKING** 2–3 · **TRUSTED** 4 · **SENIOR** 5+.

Always report the **weakest signal** with the grade — that is the promotion target. A grade without
a named next step is just a label.

## The rebirth rule — COUNTER vs INHERITED
A rename **restarts the counter**. Report both numbers, always:
- **COUNTER** — the record filed under *this persona's own name*. A rename resets it.
- **INHERITED** — the record filed under the **lane** (group name) and the **lineage** (ancestor
  names). A rename must **never** erase it.

> ⚠️ **The anti-pattern that made us mis-grade Treasury as a temp:** its record lives in
> `gentech-treasury-completions.md` and `labs-completions.md` / `entertainment-completions.md` —
> under **group** names, not seat names. **Grading keyed on `<seat>-completions.md` either orphans
> the record or double-counts it.** Assign each file to exactly ONE seat via the **longest matching
> alias**, and split own-name from lane/lineage.

## Lineage is the record carrier
Rebirth resets the badge, so **lineage keeps the history alive**. Record it in
`00-System/agent-profiles/README.md`. Known chain: YoYo→Treasury · DMOB→gizmo→Arthur ·
Desmond→Pixel→Proto J · gentech→gentech.

## Running it
```bash
python3 /opt/data/scripts/staff-intelligence.py          # roster table
python3 /opt/data/scripts/staff-intelligence.py --json   # machine-readable
```
The roster (seat, group, profile, own/lane/lineage aliases) is the `ROSTER` list at the top of the
file — **update it on every rename or hire**, or the grade silently drifts.

## Pitfalls
- **Do not grade on SOUL size alone.** Treasury carries the 667-byte stub and still grades SENIOR on
  8 duties, a ~1 MB record and 112 opinion mentions. The missing soul is a *paperwork* gap, not a
  behaviour gap — name it as the weakest signal, don't demote the agent.
- **A seat with a profile dir but no `SOUL.md` on disk reads `soul=none`** — check the vault roster
  fallback before calling it a temp. A seat on another host (Forge, desktop) has no profile here at
  all, so its signals are partial by construction.
- **Never pipe this script through `head`** — it raises `BrokenPipeError` and looks like a crash. The
  output auto-truncates anyway.
- **The counter reset is a cost, not just freshness.** Renaming often yields a fleet of perpetually
  new agents with no accumulated trust. Only the inherited record keeps continuity — key it to
  lineage, not to the current name.
