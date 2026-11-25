---
name: skill-library-maintenance
description: "Use when a SKILL.md hits the size limit or an edit fails."
version: 1.0.1
author: Gentech
tags: [skills, maintenance, editing, limits, fleet, references]
---

# Skill Library Maintenance

Editing, extracting from, and propagating skill files that are at or near the platform size limit.

> **Before you write a NEW skill at all: SEARCH, then STACK.** The full rule is **Rule 0 in
> `fleet-compatible-skills`**. A *variation* of an existing skill — same lesson, new name, rules renumbered
> — is far harder to spot than a duplicate, and it leaves the doctrine split in two files that each look
> healthy. Extend the existing file; author new only when the lesson is genuinely new, and say which search
> you ran.

> **And MERGE by default, not as a fallback.** The user's standing instruction: when a lesson arrives, first
> look for the skill it belongs inside and merge it there; a new file is the exception, not the habit. Two
> reasons, one of them measurable: **a near-duplicate pair makes the loading agent guess which file is
> canonical** (they will guess differently on different days), and **every skill charges the always-loaded
> index on every turn whether or not anyone loads it.** See the merge procedure below.

## Merge before you create: measure the index, then hunt the near-duplicates

**The library's cost is not its total size — skills load on demand. The cost is the INDEX**: one
name-plus-description line per skill, present in every turn of every session. Measured on this fleet:
**352 skills ≈ 33,500 chars ≈ 8,400 tokens of standing overhead.** That number, not the 7 MB of content, is
what a new skill actually spends, and it is the number to cut when the library feels heavy.

**Find merge candidates by description overlap, not by name.** Names diverge on purpose; descriptions
converge when two skills really do the same job:

```python
import glob, os, re, itertools
words = lambda d: set(re.findall(r'[a-z]{4,}', d.lower()))
rows = []
for p in glob.glob(f'{CORE}/*/*/SKILL.md'):
    txt = open(p, errors='ignore').read()
    m = re.search(r'^description:\s*(.+)$', txt, re.M)
    rows.append((os.path.basename(os.path.dirname(p)), m.group(1) if m else ''))
for (n1, d1), (n2, d2) in itertools.combinations(rows, 2):
    a, b = words(d1), words(d2)
    if a and b and len(a & b) / len(a | b) >= 0.42:
        print(round(len(a & b) / len(a | b), 2), n1, '<->', n2)
```

**≥0.42 is the review threshold; ≥0.80 is almost certainly one job wearing two names.** Read both files
before deciding — an overlap score is a lead, not a verdict, and a pair can share a description while one is
the procedure and the other the audit of that procedure.

### Merging two skills without losing either half

1. **Keep the entry with the better trigger** (the one a real request would match) as the surviving name;
   absorb the other as a named *shape* or *phase* inside it — `## Shape B — <what the other skill did>`.
   A reader arriving with the second skill's problem must find a heading that names it.
2. **Concatenate the bodies; do not summarise either one.** You are consolidating entry points, not editing
the lessons. Drop only duplicated frontmatter and the repeated `## When to Use`.
3. **Carry every `references/` file across** into the survivor and keep the filenames.
4. **Rewrite the description to cover BOTH jobs in one line** — a merged skill whose description only names
the first job will never fire for the second.
5. **Verify by counting headings on both sides before and after:** `kept_from_A + kept_from_B == original_A +
   original_B`. A merged file that reads well can still have lost a section.
6. **Leave the absorbed copy in place as a tombstone for one cycle** (it costs one index line) or delete it
   only after the survivor is confirmed on every seat — never delete first.

**Do not delete a skill because nothing references it yet.** A newly promoted lesson is cited by nothing
precisely because it is new. Emptiness of inbound references is evidence of age, not of value.

The platform keeps skills loadable by capping them. **The cap is enforced at WRITE time, not at
write-intent time** — so a skill can absorb lessons for months and only reveal it is full on the day
you need to record the most important one.

## The hard limit: 100,000 CHARACTERS

**It is characters, not bytes.** `len(open(p, encoding='utf-8').read())` — never `wc -c`, which counts
bytes and over-reports by roughly the multibyte density. Measuring in bytes has already produced a
batch of false "uneditable" flags on files that patched fine.

At or over the cap, **every** edit is refused: no corrections, no new lessons, nothing. The skill keeps
loading, so it looks healthy — it is the writes that are dead.

**Measured, so the shape of the failure is not guessed:** an over-cap `SKILL.md` written straight to disk
**loads IN FULL** — the platform's own test writes a 200,000-char file and asserts `skill_view` returns it
*"no truncation at the storage layer"* — and the apply that installs it is a plain `rmtree` + `copytree`
that never consults the cap at all. **So there is no truncation and no refusal: the seats get a skill that
reads perfectly and that no seat can ever add a lesson to.** The cap is enforced on WRITE
(`skill_manager_tool.py`, `MAX_SKILL_CONTENT_CHARS = 100_000`), and only there.

## ⚠️ `skill_manage` edits the SEAT copy — never the vault core

**The tool operates inside the profile's `skills/` dir.** Measured: a patch against a skill whose core copy
sits in `10-Labs/skills-distribution/` landed in `/opt/data/profiles/<seat>/skills/...` while the core
file's hash did not move.

**The consequence is the reason this section exists: a shared core is edited ONLY by direct file writes, and
direct file writes do not consult the cap — so a core can cross 100,000 chars invisibly.** The gate that
refuses a seat is unreachable from the file that overwrites every seat. It has already happened once: a core
reached **103,752 chars** by a dozen ordinary lesson appends, and the next apply would have installed it
fleet-wide.

**Two rules follow, and the second is the one that stops it recurring:**

1. **Edit the CORE copy on disk (that is the source of truth), then update the seats with the sync** — never
   "fix" a seat copy: the next apply destroys it silently.
2. **A size check belongs in the APPLY path, beside the existing batch-size refusal — because the tool's own
   gate can never see the file the apply is about to copy.** Checking the core before `copytree` is the only
   place the check is reachable.

### A reconcile tool with a BASELINE must validate the baseline's SHAPE — or it never completes a run

**A sync tool that classifies each skill by comparing CORE against a stored per-seat baseline hash will raise on
the FIRST skill if the stored shape and the reading code disagree — and because the crash precedes the writer, the
baseline is never updated either. So it has never completed a run, on any schedule.**

Measured: the state file holds a **bare hash string** per seat (`{"<skill>": {"<seat>": "a08c73867492"}}`) while
the classifier called `.get("agreed")` on it → `AttributeError: 'str' object has no attribute 'get'`.

**Read the file the WRITER produces before trusting the reader.** Accept both shapes cheaply:

```python
prev = (state.get("skills") or {}).get(name, {}).get(seat)
if isinstance(prev, dict):        # older files may hold {"agreed": <hash>}
    prev = prev.get("agreed")
if prev == c_hash:   ...          # compare STRINGS, never dict-vs-string
```

- **A crash on row 1 is indistinguishable from "no drift" when a wrapper swallows the exit code.** A reconcile
  that has never reported a decision COUNT has probably never run to completion. **Ask for the count, not for the
  absence of errors.**
- **The first successful run is a FIRST-EVER comparison, not a delta.** With no valid baseline the classifier
  falls back to content-direction (which file contains the other) and mtime — a usable signal and a weak one.
  Say which basis produced the verdict when you report it.
- **Never blanket-apply a `review` verdict.** `review` means *both* sides changed since the last agreement; a
  whole-file copy in either direction deletes the other side's work. Merge **by section**, and apply only the
  verdicts you can justify individually — a strict-superset `promote` is the safe one. Measured on one repair:
  113 decisions → 38 promote · 14 sync · **61 review**, and the one skill that actually needed changing was a
  `review` that had to be merged by hand rather than applied.
- **Prove the tool by making it PRINT A VERDICT TABLE, not by reading its source.** A repair is unverified until
  the dry run emits decisions and a deliberately inconsistent fixture still exits non-zero.

### Applying PROMOTE makes CORE newer than every OTHER seat — expect the sync count to GROW, then run again

**One `--apply` is not convergence.** Promoting a seat's copy into CORE makes CORE the newest version for
*every other* seat, so the very next dry run correctly reports those seats as stale and the **sync count
rises**. That is propagation, not regression — and reading it as regression sends you back to the classifier
that just worked.

Measured on one repair: apply #1 → `promoted 53 · synced 13 · failed 0`; dry run immediately after → **sync
13 → 103**; apply #2 → synced away; dry run → `0 promote · 0 sync`, **167 review**. **The stop condition is
`promote + sync == 0` on a DRY RUN — never the exit code of an apply.**

- **Expect at least two applies.** Loop until the dry run reports zero mechanical decisions, and cap the loop:
  a count that will not fall means the classifier is comparing live CORE against a stale baseline, not that
  more syncing is needed.
- **`review` can RISE while the mechanical counts fall** (145 → 167 here) because promoted content changes the
  CORE baseline for skills that also differ elsewhere. Reporting `0 promote` alone hides the real backlog;
  publish both numbers, and say the remainder needs merges rather than a command.

### SEAT-ONLY is the quiet catastrophe: a skill that exists on exactly one machine

A skill with no CORE counterpart is a **contribution nobody promoted**. It looks normal to the one seat that
has it and is invisible to the rest — and **a seat rebuild deletes it outright**. No drift audit flags it,
because "differs from CORE" and "has NO CORE copy" are different findings and only the first one shows up as
drift.

- **Count them explicitly**, then promote additively: copy only where the destination does **not** exist and
  **refuse loudly otherwise** — an overwrite there is a merge decision wearing a copy's clothes.
- **Check the NEWEST skills first.** Work authored in the current session is the most likely to be seat-only
  and the least likely to be noticed by a human reading a long list.
- **Prove it per seat afterwards** (`2/2 present` on every seat plus CORE). "Promoted" is a claim until the
  file exists everywhere, and this is exactly the class of work that silently ships to one machine.

## ⚠️ Verify the edit reached CORE — one grep, every time

**A successful `skill_manage` edit says the write landed. It never says it landed in the file that
survives.** Treat every skill edit as unproven until the CORE copy contains it:

```bash
grep -c '<a distinctive phrase you just added>' \
  /opt/data/.obsidian-vault/10-Labs/skills-distribution/<category>/<skill>/SKILL.md
# 1 → the rule is in the source of truth
# 0 → it is only on this seat, and the next sync will overwrite it
```

**Pick a phrase that exists nowhere else.** A generic word matches text that was already there and
reports a false pass — the same keyword-as-fact error these skills keep catching.

**When the grep returns 0:** extract the section from the seat copy and insert it into CORE, then
propagate from CORE to every seat and confirm the hashes are identical. Do **not** copy the whole seat
file over CORE — the seat may be a stale or locally-edited variant, and the whole-file overwrite is how
a good CORE becomes a bad one.

### Which side is AHEAD? Determine it before copying in either direction

**"Edit CORE, never a seat" is a rule about where edits are AUTHORED. It is not a claim that CORE is
newer**, and treating it as one loses work in the other direction.

Measured: a skill's CORE copy was weeks older and was missing an entire section the seat had gained —
the seat was the superset. A naive "push CORE to all seats" would have deleted that section fleet-wide,
and a naive "CORE is authoritative, leave it" would have left every seat permanently one version behind
while the tool reported success. Neither error raises.

**Diff before you propagate, and classify the result:**

```bash
diff <core>/SKILL.md <seat>/SKILL.md | grep '^<'   # lines ONLY in CORE
# nothing  -> the seat is a strict superset: promote seat -> CORE, then fan out from CORE
# some     -> both sides have unique content: merge BY SECTION, never by file
```

- **A strict superset promotion is the safe case**, and it is the one to take when the diff proves it:
  copy seat → CORE, then CORE → every seat, then prove it with a hash table — all N seat hashes identical
to CORE is the only evidence the fleet agrees.
- **Never whole-file copy when both sides carry unique sections.** Extract the missing section and insert
  it, exactly as for the reverse direction.
- **Do not use mtime as the tell — a hand-rolled mtime classifier over-reports in the DANGEROUS direction.**
  The newer file may be the wrong one; the diff is the evidence, the timestamp is a hint. Measured: a
  purpose-written mtime classifier called **162 promote · 40 sync · 35 seat-only** on a tree where the
  content-aware reconciler said **53 promote · 13 sync · 145 review** — i.e. **145 skills had changed on BOTH
  sides**, a state no timestamp can express. Acting on the mtime verdict would have replaced CORE with one
  seat's variant on all 145 and reported success on every one.
- **Never hand-roll a classifier when the repo already ships one.** Read the existing sync tool's flags before
  writing a new one: a `--reconcile`-style mode that reasons over content exists precisely because mtime was
  tried first and was wrong. Run it dry before writing a line of your own.
- **Say which direction you promoted, in the record.** The next reader needs to know whether CORE led or
  followed, or they will re-run the same guess.

The corollary worth remembering: **a rule that only exists on the seat is worse than a rule that does
not exist at all**, because the agent using it believes the fleet has it.

**Sweep the whole fleet, not the seat you happen to be in** — the same skill exists on every seat and
they drift:

```python
import glob
for p in glob.glob('/opt/data/profiles/*/skills/**/SKILL.md', recursive=True):
    n = len(open(p, encoding='utf-8', errors='replace').read())
    if n >= 90000:
        print(f'{n:>7}  {p}')       # 90k = act now. 100k = already too late.
```

**Treat 90k as the action threshold, not 100k.** A skill parked at 88–99k is a skill whose *next*
ordinary lesson silently fails to land, and the failure surfaces weeks later as "that fix never got
recorded." Headroom is the feature.

## ⚠️ A malformed FRONTMATTER blocks every future patch, not just the one that wrote it

**The write path re-parses the whole YAML frontmatter on every `skill_manage` patch** and refuses when it does
not parse — so one bad line, inherited from any earlier author, makes every later correction fail with a
message about line 2 that names nothing you touched. The file still loads and reads perfectly, which is why it
sits there for months.

Two shapes seen on live skills, both fatal to patching:

```yaml
description: "…long text…"   <!-- not installed: no skill named `x` exists -->   # ❌ a trailing comment
                                                                                #    after a quoted scalar
description: "…294 characters…"                                                 # ❌ over the 60-char index cap
```

- **Repair the frontmatter as its own first patch**, before the edit you actually came to make: it is the only
  write the guard will accept, and doing it first means a content patch does not get blamed for it.
- **`description` is index text, not documentation.** It must fit ~60 characters, one sentence, trigger first,
  ending in a period. Long prose that used to live there belongs in the body — move it, do not shorten it into
  nonsense.
- **Never leave an HTML comment or a `#` note on a frontmatter line.** A caveat about a retired skill belongs in
  the body, where a reader sees it in context, not welded to a YAML scalar.
- **A patch that fails with a YAML parse error is a finding about the file, not about your edit** — read the
  frontmatter before rephrasing the body, or you will rewrite working content chasing a fault that was above it.

## ⚠️ The cap gates ANY `skill_manage` write — extraction MOVES the problem, it does not cap it

**The 100,000-char limit is a module constant on the WRITE path, not a `SKILL.md` rule.** It fires on any
content `skill_manage` writes — `references/` files included. So "the skill fits now" is a statement about
one file at one moment, not about the skill.

**Measured 2026-09-28:** `develop-and-verify/SKILL.md` was over the cap and its pitfalls ledger was extracted
to `references/pitfalls.md` (69,923 chars). That reference then went **69,923 → 72,925 chars inside half an
hour** of continued work. **A reference is append-only by nature.** Extraction buys headroom; it does not
create a ceiling — the same failure returns at the new path, and it is the same failure: the file loads and
reads perfectly while every write against it refuses.

**Three consequences:**

1. **Watch the reference, not just the `SKILL.md`.** The thing you must budget is the whole skill dir.
2. **Any audit or guard for this must scan the WHOLE skill dir.** A `SKILL.md`-only check misses *exactly the
   file the extraction created* — the one most likely to be over, because that is where the bytes went.
3. **When a reference approaches the cap, split it BY THEME into sibling references, and move settled
   entries to a `-archive` sibling** rather than deleting them. Same rule as extraction: preserve, relocate.

**And the installing step must REFUSE, not warn.** `fleet_skills_sync.py` carries a pre-flight
(`MAX_SKILL_CHARS`, exit 4) that refuses to install any over-cap file. Refusal rather than a warning is
deliberate: that apply runs unattended at 04:30, and **a `[WARN]` there has no reader** — which is this same
defect one layer up. *A check whose output nobody can act on is a log line.*

## ⚠️ Placement: a rule that must fire on EVERY task does not belong in a skill

**Skills load by TRIGGER.** A standing rule placed inside a skill is read only when that skill is loaded —
so a rule about how to treat any external repo, how to speak, or what never to touch is invisible on exactly
the runs where the skill does not fire. Three placements, in order of reach:

| reach | where | use for |
|---|---|---|
| **every turn** | each seat's `SOUL.md` standing-rules list | user preferences and gates that apply to *every* instance of the task |
| **when the skill fires** | that class-level skill's `SKILL.md` | the procedure for the class of task |
| **on demand** | `references/<topic>.md` | decision tables, recipes, domain depth |

**Seats do not all use `## Rules`.** One may carry *"the lines that do not move"* and have no `## Rules` at
all. Find each seat's equivalent section and append there — **adding a new heading that nothing loads is
the same defect as writing the rule nowhere**, while looking like a completed task.

**Propagation is four steps, and only the last one is proof:**

1. Write it in the **CORE** skill (`10-Labs/skills-distribution`) — then grep CORE for a distinctive phrase,
   because `skill_manage` writes the SEAT copy (see the section above). A successful edit message never says
   *which* file it landed in.
2. Add the **same wording** to every seat's standing-rules list. Do not paraphrase per seat — differing
   phrasings make the fleet answer the same question differently, which reads as disagreement.
3. `hermes -p <seat> sessions refresh-prompts` for each seat, so live sessions rebuild from the file without
   a `/new`.
4. **Ask a seat cold** — one question whose correct answer *is* the rule, with no context. A seat that
   answers with all the parts from memory has loaded it. **A file containing the text proves nothing about
   the prompt**, and the gap between them is where "we told them" quietly fails.

**A rule buried at the end of a large `SKILL.md` is effectively not loaded.** If you re-derive a rule that
already exists deep in a file, the fix is **placement, not another copy** — move it to where it is actually
read, then delete the stale duplicate so the two cannot drift.

### Count the heading before you add one — an append-grown skill accumulates duplicate blocks

**A skill edited by many hands, one append at a time, grows a stack of near-identical header blocks**: the
same six rules under the same `##` heading, two or three times, each copy with its own date stamp, and often
a mangled heading from a re-append (`# Title — date — date`). Measured on a live skill: three copies of the
same six-rule block before the real content began, one of them under a heading that repeated its own date.

- **`grep -c '^#\{1,3\} <heading text>' <skill>` before adding a section.** A count above 1 means the rules
there are already written — extend ONE copy and delete the others, never append a fourth.
- **The duplicated block is not just noise, it is a contradiction risk:** the copies drift apart the moment
  one is corrected, and a reader who quotes the wrong copy is quoting a rule the file also denies.
- **A repeated date in a heading marks a re-append**, not a revision — collapse to one heading and one block.
- **Do the collapse as its own edit, verified**, rather than folding it into a content change: the diff should
  show only removals, and nothing in the surviving block's wording should move.

## Procedure — extract to `references/`, never delete

1. **Back up first.** `shutil.copy2(SKILL.md, SKILL.md + '.bak-<what-you-are-doing>')`. Do not skip this
   because the edit is mechanical — mechanical edits are exactly the ones that go wrong silently.
2. **Rank sections by size and extract the largest NARRATIVE ones** — changelogs, incident
   post-mortems, long runbooks, historical session logs. They are *depth*, not *procedure*. **Start
   with the single biggest:** one oversized changelog commonly accounts for most of the overage, and
   extracting it alone restores full headroom without touching procedural content.
3. **Write each to `references/<topic>.md`, named by TOPIC** (`evolution-changelog.md`,
   `cron-execution-workflow.md`, `common-pitfalls.md`) — never by date or incident. Convert the
   section's H2 into an H1 in the extracted file so it reads as a standalone document.
4. **Leave a pointer in `SKILL.md`**: the section's original H2 heading, plus one line naming the
   reference path, its character count, and that it is read on demand. The heading must survive so
   the skill's table of contents still describes itself.
5. **Prove editability with a REAL edit.** Apply a `skill_manage` patch and let it succeed. A character
   count is a proxy for editability; **the write is the gate** — and the write is what you were fixing.
6. **Propagate `SKILL.md` AND the new `references/` to every seat**, keeping the original as a `.bak`
   on each, then re-sweep to confirm zero remain over the threshold.

**Never drop content to make a skill fit.** Extraction preserves it in `references/`; deletion destroys
it. A skill that sheds its own history to pass a size check has lost the thing that made it valuable.

## Apply ONE skill through the fleet sync, and count its items before and after

**A fleet sync guards the batch, not just the file: a whole-library apply refuses at `--max-changes`
(often 25) and tells you nothing was changed.** So a single-skill edit routed through it needs the
narrow form, and the refusals arrive in a fixed order — batch first, size second — which means fixing
the size and re-running still refuses if the batch gate was the real blocker:

```bash
python3 $VAULT/00-System/agent-profiles/fleet_skills_sync.py --check | grep -i '<skill>'   # see the diff
python3 $VAULT/00-System/agent-profiles/fleet_skills_sync.py --only <skill>                 # the narrow apply
```

**`--only` takes the change-list FORM of the name, `<category>/<skill>` — not the bare directory name.**
Passing the bare name answers `✗ not in shared core (nothing to sync): <skill>` for a skill that is sitting
right there, which reads as *the file was never created* and sends you to re-check a write that already
landed. Read the dry-run line (`agent-kit/<skill>:would-add`) and pass exactly that string.

**Read the refusal, do not retry it:** `exceed --max-changes` means *use `--only`*; `over-cap` means
*extract first*. Raising the batch limit to get one skill through is the wrong dial — it is the guard
that stops a broad apply from shipping 39 unreviewed changes.

**Then prove the split by COUNTING ITS ITEMS, not by reading the diff.** Pick the unit the content is
authored in — bullets, entries, headings — count it in the section BEFORE the split, and assert
`kept + moved == original`:

```python
pit = sum(1 for l in lines[s:e] if l.startswith('- **'))      # section in the trimmed SKILL.md
mv  = sum(1 for l in open(ref) if l.startswith('- **'))      # the extracted reference
assert pit + mv == ORIGINAL_COUNT, (pit, mv)
```

**A bullet count taken over the WHOLE file is not this check** — it also counts bullets in every other
section and reports a false "lost some". Scope the count to the section boundaries (from its heading to
the next `## `), and state both numbers when you report the split, because "nothing was dropped" is a
claim a count can prove and a diff cannot.

## ⚠️ Split on `\n(?=## )`, never `(?=\n## )`

The lookahead placement decides whether the heading comes back with its section:

```python
secs = re.split(r'(?=\n## )', text)   # ❌ captures the leading newline INTO the section
                                        #    -> s.split('\n')[0] is '' -> title detection blank
                                        #    -> pointers land with EMPTY headings
                                        #    -> references get named section-5.md, section-18.md

secs = re.split(r'\n(?=## )', text)   # ✅ heading stays at the front of its own section
```

**A blank title does not raise.** It silently produces pointer blocks with no heading text and
placeholder filenames — plausible-looking output from a script that reported success. This is a
one-character defect whose damage is invisible until someone opens the skill.

## Verify the OUTPUT, not the operation's success

**A tool that prints an APPLY report has told you what it INTENDED, not what it wrote.** Measured: an
`--apply` invocation printed the complete decision report and the tree was **unchanged — `git status` showed
zero files**; the same command re-run wrote 63. Nothing in either output distinguished the two.

- **Assert the write, never print the result.** `git status --short <tree> | wc -l`, or a fresh dry run whose
  counts actually moved, is the evidence. `APPLIED` / `✓` is a claim made by the same code that failed to write.
- **Capture the TAIL, not the head.** A decision report prints dozens of rows before its summary, so `head -N`
  truncates away exactly the `failed N` / `APPLIED` line you needed — and the run then reads as "produced a
  list and did nothing".
- **Re-running the dry run is the check.** Counts that did not move prove nothing happened, whatever the log said.

## ✅ Validate against the OFFICIAL spec before publishing a skill outward

**The Agent Skills reference validator** (`skills-ref`) is the same one third-party packs run in CI:

```bash
uvx --from "git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref" skills-ref validate <skill_dir>
```

Subcommands: `validate`, `read-properties` (JSON), `to-prompt` (generates the `<available_skills>` XML).

**The spec allows exactly six frontmatter fields:** `name`, `description`, `license`, `compatibility`,
`allowed-tools`, `metadata`. **Anything else fails validation.**

**Measured on our own library (2026-09-25): 528 skills carry frontmatter, only 64 (12%) conform.** The rest use
Hermes-native fields — `version` (356), `author` (335), `tags` (249), `platforms` (116), `category` (98),
`trigger` (82), `related_skills` (44), `hermes` (26), `prerequisites` (25), `triggers` (23).

### Two rules for a skill we intend to publish or share

1. **Nest custom keys under `metadata:`** — top-level custom keys are rejected outright
   (*"Unexpected fields in frontmatter: tags"*).
2. **Write EVERY list in BLOCK style — never flow style, at any depth.** `tags: [a, b, c]` is rejected as *"ugly
   disallowed JSONesque flow mapping"* **even though it is perfectly valid YAML.** Block form passes:
   ```yaml
   metadata:
     tags:
       - a
       - b
   ```
   **⚠️ This is not a `tags:` rule.** In a six-skill sample five failed on `tags: […]`, but `creative/comfyui`
   failed on `author: [kshitijk4poor, alt-glitch, purzbeats]` — **it has no `tags:` field at all**, and it still
   fails when the flow list sits *inside* `metadata:`. **Renaming the field fixes nothing; converting every list to
   block style is the fix.** Check each failing line rather than assuming they share a cause.
   **Verified both directions:** flow → ❌, nested+block → ✅ `Valid skill`.

### ⛔ Do NOT mass-rewrite the library to satisfy the validator

**Hermes reads those fields — `version`, `tags`, `trigger`, `hermes`, `related_skills` are load-bearing in our
runtime.** Stripping them to satisfy an external spec would break our own agent. **They are not wrong; they are
non-portable.** The cost of the gap is *interoperability*, not function — so adopt the spec shape for **new
outward-facing skills**, and leave the existing 464 alone unless we start publishing into that ecosystem.

**Always run a control when a validator fails your files:** validate a known-good third-party skill in the same
batch. If theirs passes and yours fails, the finding is yours — and if *nothing* passes, your harness is broken.

An extraction can exit 0 and still have failed. Assert all four before believing it:

- reference filenames are **meaningful** (not `section-N.md`)
- every pointer heading is **non-empty**
- the **section count is unchanged** (you extracted, you did not drop)
- the extracted file's **content actually contains** the section body

### ⚠️ A REFUSED write prints exactly like a successful one if you only print its result

**A write tool that declines to act returns a structured error instead of the bytes written — and if
your wrapper prints a single field, a refusal reads as success.** Measured: a document rewrite was
announced as written while the file on disk was **still the old version at the old byte count**.
Nothing in the output said no.

```python
res = write_file(path, body)
print(res.get("bytes_written"))          # ← prints None on a REFUSAL; the run carries on
assert res.get("bytes_written"), f"write did not land: {res}"   # ← the correct form
```

**Verify by grepping for a marker you INTRODUCED** (`grep -c '<marker>' <file>`) **and confirm the
byte count changed.** Re-reading the target and finding the old text is the only test that
distinguishes "refused" from "landed" — the call itself always returns.

**Recognise the refusal that bites here:** overwriting a file that was last read with `offset`/`limit`
(a partial view) is refused until you read the whole file or use `patch` instead. Overwriting an
already-extracted `references/` file from a partial read is the same shape. The guard is working
correctly — the miss is not checking its result.

**Generalise it:** when a tool returns a structured payload, **assert its success field rather than
printing it**, because an absent key and a failure both read as `None`.

## Recovery when an extraction went wrong

**The same skill normally exists on every seat — a pristine copy is the backup you did not take.**
Restore `SKILL.md` from another seat, redo the split correctly, and **keep the damaged version as a
`.bak`** so the mistake is recorded rather than erased. Then re-verify output and re-propagate.

## Related

- `fleet-compatible-skills` — fleet-wide propagation, the shared core, and the drift audits that
  distribute whatever you fix here.
- `fleet-hygiene-audit.py` — the sweep that reports oversized skills; run it before and after.
