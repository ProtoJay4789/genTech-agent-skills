# Triage a bloated SKILL.md — measure the workflow/specifics split

Use when a skill exceeds ~30 KB (or when asked "how much of this is reusable?"). Everything here is
read-only analysis; run it before proposing any move.

## 1. Per-section byte accounting

A skill's bulk is section-shaped, so measure sections, not the file:

```python
import re
p = '/opt/data/profiles/<seat>/skills/<path>/SKILL.md'
lines = open(p, encoding='utf-8').read().splitlines(True)
heads = [i for i, l in enumerate(lines) if re.match(r'^#{1,3} ', l)] + [len(lines)]
for k in range(len(heads) - 1):
    i, j = heads[k], heads[k + 1]
    chunk = ''.join(lines[i:j])
    if len(chunk) >= 1200:                 # ignore trivia; the big blocks are the finding
        print(f"{len(chunk):6d} B  {lines[i].strip()[:80]}")
```

Read the output for three smells: sections that belong to another job, several sections about one named
project, and one "example" section larger than the workflow itself.

## 2. Project-name share — how much is one project's history

```python
NAMES = re.compile(r'<client>|<character>|<project-codename>', re.I)
proj = [l for l in lines if NAMES.search(l)]
total = sum(len(l) for l in lines)
print(f"{len(proj)} lines name a project -> {sum(len(l) for l in proj)} B ({100*sum(len(l) for l in proj)/total:.1f}%)")
```

Then split it honestly, because the two halves move to different places:

- **sections titled for the project** (whole `##`/`###` blocks) → vault; these are pure project history.
- **project names inside generic workflow sections** → mostly illustrative examples; often keep the section
  and genericise the example. Do not count them as removable without reading them.

Thresholds that held up: below ~10% project share the skill is fine; **10–30% is a trim; above ~30% it is
two documents pretending to be one**.

## 3. Duplicate sections — the cheapest win

```python
from collections import Counter
c = Counter(l.strip() for l in lines if re.match(r'^#{2,4} ', l))
for k, v in c.items():
    if v > 1: print(f"x{v}  {k[:80]}")
```

Repeated headings after incremental edits are common; each duplicate is 0.7–2.5 KB of the same procedure
stated twice, and the two copies have usually drifted. Keep the richer one, say which was dropped.

## 4. Where each class of bytes goes

| finding | destination | effect on `SKILL.md` |
|---|---|---|
| reusable workflow | stays in `SKILL.md` | none — that is the point of the skill |
| deep but occasional detail (tables, long recipes) | `references/<topic>.md` | shrinks; loaded only when needed |
| one project's names/history | the vault note that owns the project | shrinks; leaves the fleet copy |
| material belonging to another job | that skill's `references/` | shrinks; the other skill grows only in references |
| duplicated section | deleted | shrinks by the duplicate |

## 5. Report shape

Give per skill: current bytes → bytes after, the destination of every removed block, and the arithmetic
("15,166 relocated + 11,689 to vault + 1,601 dedupe + 34,343 into `references/` = 62,799") so a reviewer can
check the split adds up instead of trusting the total. **State what you refused to merge and why** — a
survey that only proposes cuts reads as a licence to delete.

## 6. Finding the duplicate a keyword-matched slice MISSES

A consolidation brief built by matching skill *names* against a lane will miss the skill that actually
duplicates the bloated one — the duplicate rarely carries the lane's vocabulary. **Find duplicates by SHARED
SECTION TITLES, not by name:**

```bash
# distinctive headings from the bloated file, searched across the whole tree
grep -rl "Character Count Constraints\|Full Lyrics Format" /opt/data/profiles/<seat>/skills --include=SKILL.md
```

Measured: a brief named two skills as suspected duplicates and asked whether they were interchangeable.
Neither duplicated the other — a **third skill the brief never listed** (a format/syntax skill for the same
renderer) carried the same section title and the same job. The right survivor was that third skill, and the
brief's proposed merge would have folded a craft skill into a house-format skill.

**Reconcile the brief's own numbers against the box before answering.** A survey that echoes the requester's
sizes cannot detect that its list is wrong: report tree total, count and largest file from your own `find`, then
state the delta in one line. Measured drift on one brief: slice **27 skills / 352,804 B** as given vs **33 /
590,233 B** measured, and "largest overall 100,700 B" vs **101,233 B** on disk. Neither number is an accusation —
but a slice count built from name matching is a *lower bound*, and answering a merge question from a lower bound
can miss the only duplicate that matters.

## Pitfalls

- **Do not count lines as bytes** when quoting savings; multi-byte text makes the two disagree and the
  arithmetic stops reconciling.
- **A project-titled section is not automatically vault material** if the skill's whole job is that project;
  the test is whether another seat would ever load it.
- **Never fold a whole bloated skill into an umbrella as its payload.** Absorbing 60 KB into a survivor's
  `references/` removes a `SKILL.md` and saves nothing; the win is deleting the project history, not
  relocating it.
- **Read the survivor before merging into it.** Two skills claiming one job usually disagree in one rule;
  that disagreement is the reason to merge, and it must be resolved explicitly, not by whichever body was
  pasted last.
