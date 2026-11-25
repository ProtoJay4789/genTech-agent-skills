---
name: vault-staleness-curation
description: "Use when a vault or long-lived list needs curating."
trigger: "The user asks what has gone stale, who maintains the folders, or to trim a long-running queue/list file; or you are building or repairing an overnight maintenance, audit, or curation job."
tags: [vault, obsidian, curation, maintenance, staleness, cron, ops]
version: 1.0.0
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [vault, obsidian, curation, maintenance, staleness, cron, ops]
    related_skills:
      - ../../devops/cron-delivery-audit/SKILL.md
      - ../../devops/destructive-write-guards/SKILL.md
      - ../../note-taking/obsidian/SKILL.md
---

# Vault Staleness Curation

A vault written by many agents during the day has **no one who removes anything**. Folders only grow,
work stops without a decision to stop it, and the same subject acquires six homes. The answer is not
"review it sometime" — it is a **stated TTL per class of information, checked nightly by a script, with
the result reported by one voice at wake-up.**

This skill covers three jobs that share one policy: **hygiene** (move/age out), **audit** (what nobody
has looked at), and **curation** (past its TTL, empty, or fragmented). Plus the triage procedure for a
queue file that has grown into a graveyard.

## When to Use

- The user asks what has gone stale, who maintains the folders, or to trim a long-running list file.
- You are building or repairing an **overnight maintenance, audit, or curation job**.
- A queue / ideas / considerations file has grown until its digest is unreadable.
- You need a policy for **how long information of a given kind may sit before someone must look**.

Do NOT use this skill to delete. Curation here always **proposes**; a seat or the user disposes.

## 0 · Prevention — one folder, one writer, everyone else reads

Curation is what you do AFTER divergence has happened. The cheaper rule is the ownership map that stops it;
it lives in the vault (`00-System/FOLDER-RULES.md`), and this is the part worth carrying in the skill.

**Divergence is not a discipline failure.** It happens because two seats both believed they were allowed to
edit the same file, and neither could see the other. No amount of proofreading fixes a permission ambiguity.

- **Read is not write, and a read-heavy seat reads MORE, not less.** A teaching seat (curriculum, lessons)
  needs memory files, personal notes, travel, and commercial decisions — a curriculum built without them is
  built on nothing. Its obligation is not silence but **reporting**: when a fact it teaches from is wrong or
  stale, it files a note to the writer instead of correcting it in place.
- **"Either of us may do this job" is about the WORK, not the FILE.** When two seats legitimately produce
  the same class of output (whoever happens to book the travel), the non-owner **requests** the change or
  files its own note. Shared authorship is the bug; shared output is not.
- **Admission test for a new top-level folder, asked BEFORE creating it:** *which script or job will resolve
  this path?* If nothing will ever read it, it is a draft and belongs in the ideas folder. *Which seat writes
  it?* If the answer is "whoever", do not create it.
- **A folder nobody writes to is not a folder either.** Measured: one was named for a content lane, held zero
  markdown notes, only HTML prototypes from months earlier, and no seat's code referenced it — a frontend
  dump wearing a lane's name. Rename or retire it before it becomes the next stray file's home.
- **Ownership maps rot faster than the folders they describe.** When a seat retires, its rows are the FIRST
  thing to update — a map still naming a retired seat is fiction, and it must be superseded **explicitly**
  (a new file that says so in the header) rather than silently, or a later reader cites a dead owner.

## 0b · Auditing the RULES, not just the files

When asked *"what should we change so we take better care of the brain"*, do not propose tidy-ups — test the
rules we already have against four failure classes. Each one has produced a real pile of unread notes.

| failure class | the tell | the fix |
|---|---|---|
| **one exit, and it needs a signature** | every open note stays open; the count only grows | add a **close-without-acknowledgement** (`supersede`, naming what replaced it) |
| **rules for writing, none for ceasing to be true** | a note that was overtaken months ago still reads as current | every class needs an expiry or a supersede path, stated where the writer will see it |
| **defects living in prose** | the same problem is rediscovered every few weeks | an audit's findings must land in a **tracked list**, not in a report nobody reopens |
| **a check with no cadence** | one heroic pass, then silence | assign a period per check class — structural/annual-scale checks weekly, never daily |

**A rule that makes closure impossible is not strict, it is broken.** Strictness that only permits agreement
converts every stale note into a permanent debt, and every report built on that count describes something
nobody owes — which trains the reader to ignore the number, which costs the whole mechanism.

**Cadence rule:** a check that runs once is an audit; a check that runs on a period is maintenance. Set the
period from how fast the thing rots, not from how often the reader wants a message — folders and prose need
**weekly**; a daily version of a weekly-scale check is noise the reader learns to skip.

**Two things must never be assumed healthy:** a check that could not run, and a state whose only copy is a
machine file. The first is a monitor defect; the second is a *writing* defect — when behaviour is driven by
JSON, the vault needs a prose twin naming that file as the authority (`<FOLDER>/CURRENT-STATE.md`), or every
agent reading the brain reasons from an older note and the human experiences it as *"the brain is not being
updated."* The machine knowing is not the brain knowing.

**But the prose twin then drifts, and it drifts silently.** A page whose own title was *"the one note that must
never go stale"* was wrong in three places at once, because a hand-maintained summary has no link to the data it
summarises. So the twin is only half the fix: it must **declare a machine source** and be **checked against it** by
a small auditor (header older than its source · a retired decision re-asserted unstruck · no checkable source →
exit 2 · source with no `generated_at` → UNKNOWN, never fresh). And the harder half: **a decision recorded in prose
is not applied until the file the engine reads changes** — measured, a deferral was written into two notes and
even asserted as *"cleared"* by a self-test, while the JSON still carried the dates on every seat, and the retired
state kept being served and relayed as fact. Retire such rows into `retired_dates` with the reason, never delete
them, and fix the *rationale* that justified them or the same decision returns wearing new numbers.

> **Procedure, the four rules and the wiring: `references/current-state-pages.md`.**

## 1. The policy is DATA, not code

Put the rulebook in a vault file the user can edit — `00-System/staleness-policy.json` — not in the
script. Classes are checked **IN ORDER** and the **first match wins**, so exemptions must come first.
Each class: `match` (globs), `max_age_days` (`null` = permanent record), `action` (what the look is).

Seed set that has held up:

| class | TTL | action |
|---|---|---|
| permanent | never | archives, `_archive/`, `**/backups/**`, `node_modules`, skills CORE, `*completions*`, snapshot dirs, **vendored clones (`github/**`, `vendor/`, `lib/`), every `**/SKILL.md`**, dated receipts (`**/*-report-*`, `**/*-audit-*`, `**/*-read-*`) |
| deadlines | 7d | verify or expire — a deadline older than its window must move forward or die |
| the user's queue | 7d | re-triage; anything not actionable this week goes to pending **with its gate named** |
| considerations / travel / projects | 14d | decide-or-park, refresh-or-archive |
| ideas | 21d | promote to the build queue, park with a revisit date, or drop |
| hq-facts / fleet notes | 30d | verify still true / still fleet knowledge |

**Two rules that make the table trustworthy:**
- **An un-exempted VENDORED TREE and an un-exempted SKILL.md both report as stale prose, and both are wrong.**
  A cloned repo under `github/<name>/` carries hundreds of third-party `.md` files whose age is upstream's
  business; a skills tree carries `SKILL.md` files that are edited when behaviour changes, not on a content TTL.
  Measured: exempting both (plus dated receipts) took one vault's over-TTL count from **1,273 → 952** with
  nothing deleted — and the remaining number was finally about our own notes. **A count padded by files the
  reader never wrote is the fastest way to teach them to ignore the count.**
- **A record must never be "refreshed."** A backup that gets updated is not a backup. Anything archival,
  generated, or machine-owned is `null`, and it must be exempted BEFORE any derived metric runs.
- **Clearing a must-not-go-stale flag means verifying a CLAIM, never touching the clock.** These files earn
  their budget because a stale sentence in them misleads a reader, so a timestamp bump fixes the report and
  leaves the lie. Read the file's factual assertions and test each against the live system; the fix is usually
  **one wrong fact**, and finding it is the whole value. Measured: a quickstart 7 days past its budget still
  named a **cancelled provider as primary** — the age was merely the trigger, the content was the finding.
  Append the corrected fact with its reason, so the next reader learns why it changed rather than finding a
  fresher mtime over the same error.
- **Per-seat copies of one data file are a CACHE, and the owning seat's copy is often the stalest.** When every
  seat carries its own copy of a shared state file, agreement today proves nothing about tomorrow, and the copy
  that lags is frequently the one belonging to the seat that owns the domain. Name the **distribution master**
  as the authority in the state note itself; a note that says *"the file wins"* without an address will be
  pointed at whichever copy a reader happens to load.
- **The exemption list is load-bearing for the derived reports too.** Compute fragmentation and
  emptiness over the NON-permanent set only, or one restored snapshot contributes 30+
  identically-named folders and floods the report as "one subject, many homes."
- **A policy file is not enforcement — test the NOTE, not the script.** A TTL table plus a scheduled
  script is the *measurement*; nothing has been closed until the note itself carries a state. Measured on a
  vault with a live `staleness-policy.json`, a curator script and a nightly cron: notes sitting **4–6× past a
  7-day TTL** were still open, because the policy's `action` strings were prose addressed to a human and the
  job only printed counts. **The check that answers "is the policy enforced?" is:** pick any note past its
  class window and read its header — if there is no `Status:`/`Next:`/supersede line, the rule is being
  *reported*, not applied, and the same pile will re-flag tomorrow forever.
- **Give every class a disposition the curator can WRITE, and make the ladder explicit.** Four states, and a
  note must leave the pile in one of them: `kept` (`Last-verified: <date>` + what was re-checked) ·
  `superseded by <path>` · `retired — <reason>` · `needs-decision — <the one question>`. Only the last is
  allowed to stay in the pile, and it must name who decides. **"Flagged" is not one of the four** — that is
  how a pile re-flags itself forever.
- **The curator proposes ANY closure and writes NONE of them unsupervised.** A generator that appends `Status:`
  from a keyword match will close things that are not closed: measured, a done/dead regex matched the word
  "shipped" **mid-paragraph** in a CV and offered to close the CV. **A match is not a reading.** Ship the
  worklist and require an explicit, human-confirmed path list before the job writes a single line; then re-run
  the same predicate and print before/after.
- **A counted pile that never shrinks trains its reader to ignore the number.** If three consecutive runs
  report the same total and close nothing, the report is describing a debt nobody owes — fix the disposition
  path before adding more categories, or the whole mechanism becomes noise the recipient scrolls past.
- **Verify which script the schedule actually runs.** A policy, a curator and a cron can all exist while the
  cron executes a *different*, older script — the files look complete and the behaviour is unchanged. Read the
  job's `command`, then read that file's header to confirm it loads the policy path you edited.

## 2. Three nightly products, one voice

Run them inside the quiet window with `deliver=local` (see the cron delivery skill for the window and
the producer/consumer pattern) and surface the result once, at wake-up. Each writes a state JSON that
the single wake-time consumer reads.

1. **Hygiene** — resolved handoff notes → `<lane>/_archive/`; `_archive/` entries older than ~7d →
   `11-Mess Hall/archive/YYYY-MM/` (**moved, never deleted**); notes still OPEN past the window →
   **flagged, not moved**.
2. **Audit** — what nobody has looked at: folder shape and which folders have gone quiet; open items in
   the idea/decision lists; and **ideas whose words appear in no handoff anywhere** (never routed,
   never discussed). That never-routed query is the highest-value finding this class produces — it
   surfaces grants, moats, and lanes that went dark without a decision to stop.
3. **Curator** — TTL violations grouped by class with the class's `action`, top-level folders holding
   **nothing anywhere in their subtree**, and subjects fragmented across several folders.

**The curator PROPOSES; a seat or the user DISPOSES.** It moves nothing and deletes nothing. Past-TTL
means *someone must look*, not *delete it* — and an auto-archived open item is a **disappearance, not a
tidy-up**. A job that files open work away to make a report look clean destroys the only signal it had.

### Every nightly check must leave a DATED PAGE in the brain — a state file is not a report

A state JSON that each run overwrites answers "what is true now" and nothing else. The moment the night ends,
*"what did maintenance actually do?"* becomes unanswerable, and the vault — the system of record — holds no trace
of the work that keeps it clean. **Ship the machine file AND a prose twin:** `</path>/maintenance/YYYY-MM-DD-nightly.md`,
written at the END of the wrapper so it reports what the checks just wrote, with its retention stated in the page
header, a `README.md` beside it, and the prune enforced by the script.

**The mechanics live in `script-only-job-wiring`** (dated page per run · parse the date from the FILENAME not the
mtime · prune only the pattern and print what was pruned · prove it with a planted old/new pair · coerce drifting
state fields instead of dumping raw JSON). What belongs to *this* skill is the register it joins: **the maintenance
page is one of the nightly products, and a missing state file must print `NOT RUN — no state file`, never a zero.**

### Sweeping artifact clutter — the class the policy forgets

A vault also accumulates things that are **not notes at all**, and the TTL table above has no home for them:
backup copies (`*.bak`, `*.pre*`, `*.rolledback*`, `*.premerge*`), **dependency trees** (`node_modules`
inside project folders), and dead generated files at the root. Measure before proposing:

```bash
for d in */; do printf "%-28s %s\n" "${d%/}" "$(find "$d" -type f | wc -l)"; done | sort -k2 -nr
du -sh .                                            # size
find . -type f \( -name '*.bak*' -o -name '*.pre*' -o -name '*.rolledback*' \) | wc -l
ls -d */ | wc -l                                    # vs. folders holding <5 files
```

**A dependency tree is a build artifact, not a document.** It belongs outside the system of record, because
19k vendored files inflate every "files in folder" metric in every report and slow every search. Sweep it:

1. **Move, never delete**, preserving the relative path, into `backups/<class>-<date>/`, and write a
   `_MANIFEST.txt` listing every moved path. In a vault with no git there is no other undo.
2. **Two restore modes, stated per class:** copy back (real content — notes, backups) vs **regenerate**
   (`npm ci` from the lockfile — dependency trees). Leave a `RESTORE-<what>.md` at the old location so the next
   reader does not have to guess which mode applies.
3. **Verify by re-measuring, not by the move succeeding:** artifact count → 0, size before/after, and **re-probe
   every service that could have depended on the moved tree**. Nothing in the app should reference a vendored
tree, but "nothing references it" is a claim to check — grep the app source and the runbook before moving,
   then hit the health endpoint after.
4. **Never sweep a root-level file the routing index names as read at runtime** (a dashboard JSON, a hub data
   feed). Grep the index for each filename first; a tidy-up that breaks the site is not a tidy-up.
5. **Never sweep a backup OF A CODE FILE — it is a rollback point, not clutter.** Measured: a `.bak` taken
   minutes earlier to protect a live `server.py` was swept out of the gateway folder by the artifact rule, and
   the rollback command handed to the user answered `cp: cannot stat` — the agent had eaten its own undo.
   Exempt any artifact whose base name has a code extension (`.py .js .mjs .ts .sol .go .rs .sh`); note backups
   (`.md.bak`, `.json.bak`) sweep normally, code backups stay where the code is until the change is settled.
   **Corollary:** before handing over any rollback command, `ls` the backup path you are naming — an artifact
   sweep you ran earlier in the same session may have moved it.

**The policy gap that causes it:** a hygiene job whose rule is "an auto-archived open item is a disappearance"
ends up refusing to move *anything*, so backups accumulate for months with no one permitted to touch them.
Scope the refusal to **open notes** and let the same job sweep artifact classes freely — otherwise the correct
rule licenses the mess.

### Consolidating folders — check the READERS before you move anything

The artifact sweep shrinks the vault; folder consolidation is a different job, and it is the one that breaks
things. **A duplicate-looking folder is far more often a live hardcoded path than dead weight.** Measured on a
vault with `HQ/` (14 files) beside `00-HQ/` (908): `HQ/jordan-queue.md` was actively written by one script and
audited by two more — three hardcoded paths. Merging the folder would not have consolidated anything; it would
have silently broken the user's own queue, which is the exact failure the routing index warns about ("an index
that calls a folder dead while something still writes to it").

Classify every candidate by **who touches it**, before proposing a move:

```bash
# 1 · is the path hardcoded anywhere live?
grep -rn "HQ/jordan-queue\|'HQ/\|\"HQ/" scripts/ profiles/*/scripts/ 2>/dev/null | head
grep -rln "Travel/travel-jordan.json\|DeFi/defi-data.json" . --include="*.py" --include="*.sh" --include="*.json"
# 2 · is it a routing stub already?  (a folder holding only .redirect.md / .gitkeep)
find <folder> -type f | sed 's|.*/||' | sort -u
# 3 · is it byte-identical to a canonical sibling?  (only then is it free to archive)
diff -q <folder>/<file> <canonical>/<file>
```

Three verdicts, three different actions:

| verdict | evidence | action |
|---|---|---|
| **dead duplicate** | byte-identical file, or sole content of a retired agent | move whole folder to `10-Archive/legacy-<name>-<date>/` — free |
| **live path** | any script or cron reads/writes inside it | **code change first**: patch the paths → move → run the readers → prove the surface still loads. Never the reverse |
| **redirect stub** | only a signpost (`.redirect.md`, `_MOVED.md`, `README.md`) / `.gitkeep` | delete the folder once the signpost's target is confirmed to exist |

**Root-level files are the same trap one level up.** Several are runtime feeds (a dashboard JSON, a hub data
feed) named in the routing index as read at runtime. Grep the index for each filename before proposing a sweep;
report root strays to the user and move none of them without that check.

**A MOVED FILE has the same hazard as a moved folder, and it fails more quietly.** Measure the readers by **shape**, not by count — one substitution pattern hits only one of the three that show up:

- a **Python constant** — `QUEUE = "/opt/data/.obsidian-vault/scripts/build_queue.json"`   <!-- ⚠️ NOT PRESENT (checked 2026-11-17): this file does not exist on this seat. Do not assume it; verify before relying on it. -->
- a **shell variable** — `Q=/opt/data/.obsidian-vault/scripts/build_queue.json`
- a **table entry or docstring line** — `"build": ("10-Labs/build-queue.md", "table")`

A patch that handles the first leaves the other two pointing at a path that no longer exists, and **the failure is silent because a missing list file reads as an empty list** — the digest then reports zero items and looks healthy. Patch every shape, then **run each reader and print its resolved path**: a grep is not a load, and `--help` is not a load either (argparse exits before any module-level constant resolves).

**Merge the CONTENTS before you move the file.** Two copies of the same list in different folders are not two views of one thing, they are two truths, and moving them together only changes their address. Fold the smaller/older one into the canonical one first (marking the duplicated rows `superseded_by` so one piece of work cannot be counted twice), **then** move, **then** repoint. Keep the prose document and its machine state **in one folder** afterwards — they drift apart precisely when one lives inside a code tree and the other in a shared scripts directory.

**A merged list breaks every instrument that assumed its ids were numbers.** Adding string ids (`rev-1`, `abc123`) beside integers makes `sorted()` raise `'<' not supported between str and int` and `%d` raise `TypeError` — three separate instruments died on this in one pass, each looking like a queue problem rather than a code one. Before merging, grep the tooling for `sort(`, `%d`, and any `int(item["id"])`, and sort on a **numeric part extracted from the string, then on the text** so the order is total and cannot crash. **Fix every hit in ONE pass before running any of them:** each broken reader surfaces only when you run it, so fix-one-run-one buys the same crash five times and makes a single merge look like five unrelated bugs. When a fix lands inside a nested function or a wrapper, re-read the indentation and `py_compile` before moving on — an anchor that matches at the wrong indent compiles into an `IndentationError` that reads as a new defect.

**When you vacate a path, leave a VISIBLE signpost** (`_MOVED.md`, `README.md`) naming the new home, so a
reader following an old note lands somewhere real instead of in an empty directory. **Not a dot-prefixed
`.redirect.md`:** dot-paths are excluded from vault sync, so on every other host the retired folder still
reads as live-and-empty while the file that explains the move sits only on the host that wrote it. Check
the signpost's target exists, resolving it from the root it was written in — a target may legitimately live
outside the vault (a consumer script under `profiles/…`).

### A RENAME request names a GROUP — measure whether the folder is that thing before you move it

**When the user says "rename folder A to B because the team changed name", they are correcting a LABEL, not
asking for a directory operation. The folder may not hold the thing the old name described, and the reference
count decides whether the edit is a rename or a demolition.** Two measurements settle it, both cheap:

1. **Does the folder the user is naming actually exist, and what is it?** A name that matches a retired
   team is not evidence that a folder carries that team's identity. Measured: "rename `Labs` to `EDU`" met
   **no `Labs/` folder at all** — the real path was `10-Labs/`, a build tree holding the skills distribution,
   service source and plugin code, and `EDU/` **already existed separately** with its own charter, curriculum
   and state file. Renaming one into the other would have relocated the code every seat reads into a
   curriculum folder. **The migration had already happened; only the vocabulary had not.**
2. **How many live references point at the path?** Anchor the top-level segment and count before proposing
   anything (see the substring pitfall in §4). A path with four figures of references is infrastructure; a
   word the user wants corrected is a documentation edit, and they cost nothing like each other.

**A rename already done in NAME is not done in CONTENT.** A newly created lane folder whose README describes
the new activity can still be full of the previous activity's by-products — prototypes, dashboards, generated
HTML — while the folder whose name is being retired holds an unrelated estate. Measured: the "social" lane
held **12 frontend prototype files**, while the folder called "entertainment" held **73 files of film, music
and character production**. Merging on the strength of the two names would have filed character sheets into a
publishing log. **Classify each side by what its files ARE, then decide.**

**So the honest deliverable is a measurement, not an edit** — and it is often the answer the user did not ask
for but does want: *the names moved; the folders never had to.* State, in this order:

- which folder they named, and whether it exists;
- what it actually holds, with the reference count;
- what already exists under the new name, and what is in it;
- the two or three options with their real costs — **name-only rename** (N files of edits, nothing moves),
  **content migration** (which readers must be repointed first), or **fix the language and leave the tree**;
- one line saying nothing has been renamed and which call is theirs.

**Never execute a structural rename to satisfy a naming request before that comparison exists.** A rename that
breaks four figures of references to fix one word is a bad trade, and the user cannot see the tradeoff from the
name alone — that measurement is the whole value you add.

**The third outcome is usually the right one: keep the name, name a CUSTODIAN.** When the user's real complaint is
*"nobody is managing that folder"*, a rename answers a question they did not ask. Say the name stays, then assign
one owner per subtree — and **ask the occupants before assigning**: a folder of mixed inheritance belongs to
whichever lane actually holds material in it, and a seat that is handed the wrong thing will refuse it in terms
that are more useful than the assignment was.

- **A lane that says "none" is a result, not a snag.** A seat asked whether an inherited folder is its work will
  often answer *nothing here is educational* — that is the confirmation the rename was never needed, and it must be
  recorded as the finding, not chased as non-cooperation.
- **Custody of assets is not custody of a SERVICE.** A seat may happily own brand imagery while refusing a build
  tree or a running pipeline, with the reason that decides it: *an owner who cannot read the code is not an owner.*
  Split the subtree by KIND (assets · strategy notes · code · running services) rather than assigning a folder whole.
- **Code in the vault is the third rail.** A seat that owns the numbers will refuse the source tree outright —
  *code lives in the repository, never the vault* — and it is right; the vault copy is then evidence, not the source.
- **Ask the custodian for a falsifiable CAP in the same reply.** "You own it" with no limit recreates the accretion
  the folder already suffers from; a number (live notes held, retire-before-add) is what makes the ownership
  checkable by the next curator pass. An owner with no cap is a name on a folder.
- **Record the ownership in the routing index as one line.** A stewardship that exists only in a handoff thread is
  invisible to the next agent, which then re-asks the same question and re-opens the same rename.

### Two copies that are NOT byte-identical have DIVERGED — and the OLD folder can hold the NEWER facts

The three-verdict table above assumes a candidate is either identical or live. There is a third state, and it
is the one that loses data: **two copies of the same artifact, both edited since they split.** Byte-diff says
"different"; the reader check says "one path is live"; both answers point at the canonical copy — while the
newest content sits in the folder every reader was repointed AWAY from.

Measured (this vault's travel ledger): every consumer resolves `00-HQ/01-Travel/`, and the consuming engine
carries a code comment recording the repoint — *"when travel consolidated into 00-HQ/01-Travel"*. The canonical
copy was **two days OLDER** than the folder it replaced. The newer fields — bookings, a credit note,
cross-checks, a cleared companion, a repriced leg, new open decisions — existed only on the abandoned side.
Every reader was correct; every reader was reading stale facts.

**Procedure — merge, never pick a winner:**

1. **Back up every candidate folder OUTSIDE the vault** (`/opt/data/backups/<purpose>-<date>/`) before touching
   one file.
2. **Diff the STRUCTURED artifact field by field, not by eye.** `set(A) ^ set(B)` for keys, then values per
   shared key. Report keys-only-in-A, keys-only-in-B, and keys-that-differ — three lists, not a boolean.
3. **Merge into the canonical path under a stated rule, and WRITE THE RULE INTO THE FILE:** newer wins per
   field, **stale-only keys are carried across, nothing discarded**. Assert `len(merged) >= len(larger input)`
   and list any key that did not survive — zero is the only acceptable answer.
4. **Move notes that exist nowhere else; COPY supporting artifacts after comparing.** A dashboard or feed the
   canonical side already holds is diffed first and only copied when it differs.
5. **Both old paths keep a VISIBLE signpost** (`_MOVED.md`) naming the canonical folder, the reason, the backup
   path, and the consumer that resolves it. Do not delete the directory — a path that 404s breaks the reader
   you did not find — and do not give the signpost a leading dot, which sync excludes: it then reads as a live,
   empty folder on every other host, ready for a writer to file into.
6. **Prove it by LOADING THE CONSUMER, not by grepping.** Grep finds a string; only an import proves the file
   resolves. Load the module that owns the path and print its resolved constant plus `exists()`:

   ```python
   import importlib.util, sys
   spec = importlib.util.spec_from_file_location("engine", "/path/to/engine.py")
   m = importlib.util.module_from_spec(spec); sys.modules["engine"] = m
   spec.loader.exec_module(m)
   print(m.TRAVEL_DIR, m.TRAVEL_DIR.exists(), m.TRIPS.exists())
   ```

   A `--help` run is not this check: argparse exits before any module-level constant is resolved, so it prints
   usage and proves nothing about the path.

**Order of work when several folders are candidates:** rank by what **rots or strands if you do nothing**, not
by effort or size. The merge that could strand a live booking outranks the rename that merely tidies a name, and
a folder holding live records is merged **first**, because the longer it stays split the further the two sides
diverge. Say which item you took and why — "it doesn't matter which one" is permission to reorder, not to
process in size order.

### The structure check is its own job — content maintenance will never see shape

Three nightly jobs can run for months and still leave a vault with 231 backup files and 56 top-level folders,
because every one of them inspects **content**: one ages handoff notes, one rewrites checklist bullets in a
single ideas file, one measures text staleness. **Nothing looks at the tree.** If you are asked "does our
maintenance handle this?", answer by listing what each job actually inspects — then add a fifth check that
walks the tree and reports: artifact files · dependency trees · near-empty top-level folders · duplicate-looking
folder pairs · root strays.

Encode the policy in that checker so it cannot drift back:

> **Hygiene may move ARTIFACTS freely. It may not move NOTES or FOLDERS.**

`--apply` moves artifacts and dependency trees only; folders and notes are **reported, never acted on**. Silent
when the shape is fine, exit 2 on findings, 3 if it cannot read the vault. Wire it into the same wrapper as the
note check with `sh -n` verified afterwards, and keep the exit codes separate so a shape finding does not turn a
healthy note check into a failure.

A working instance is `/opt/data/scripts/audit-folders.py` — four checks, exit 1 on findings, 2 if the vault is
unreadable: duplicate folders, folders no seat's code references (**anchored**, never substring), redirect-only
shells, and signposts pointing nowhere. Three generation defects to avoid in the next one:

- **Name similarity is not duplication — require SHARED FILENAMES.** Normalising away non-letters collapses
  `00-HQ` and `HQ` to `hq`, and `01-Travel` and `Travel` to `travel`; the first pair is a **live operational
  pairing** (566 vs 26 entries, **zero filenames in common**, the smaller written by seven scripts) and the
  second was **two signposts to one destination**. Reporting both under one "duplicates" heading invites a
  merge that would break a live queue while consolidating nothing. Keep `duplicates` for *same filenames in both
  places* and *more than one redirect shell for one destination*; demote the rest to a separate `similar_names`
  line the reader can judge.
- **Resolve a path against the root it was written in.** A `.redirect.md` may legitimately point OUTSIDE the
  vault (a reader script under `profiles/…`). Resolving every candidate against the vault root reported two
  live redirects as dead — a false positive in a delivered report, which costs as much trust as a miss.
- **A signpost that lists bare filenames resolves them inside the DESTINATION, not the scan root.** A move note
  names the new folder, then lists what moved by filename alone. Every one of those filenames is absent from the
  old root *by definition*, so a scan-root read reports the whole move lost. Try the destination first, then
  the vault root, then `/opt/data`.
- **A folder target is the same finding as a file target.** A pattern demanding two path segments (`A/B`)
  silently skipped a signpost to a missing folder (`Nowhere/`) and the planted test still passed — the plant
  had the wrong shape.

**Every relaxation needs a planted-defect control in the same pass.** Confirm the new rule still fires on the
thing it exists to catch — a prose checker that stops crying wolf by going deaf is the worse outcome, and it
looks like success in the diff.

## 3 · Triaging an append-only queue file

A queue/ideas/considerations file appended to for months is mostly dead. Classify every section
**mechanically**, then act — never by read-and-hope.

- Split on the top-level heading; per section capture: last date mentioned, open vs closed checkbox
  counts, and status words (`retired`, `superseded`, `done`, `no longer`).
- Three classes, not two: **LIVE** (any open box, a live marker, or recent), **DEAD** (all boxes closed,
  a dead word, or older than the class window), and **LOG** — recurring reports and dated digests that
  were never work at all.
- **A recurring report job must never append into a work queue.** Measured: 115 of 169 sections in one
  queue were the assistant's own dated reports, and because every write-back carried unchecked boxes,
  **every log entry read as an open task**. Keep agent logs out of the queue, or the queue becomes
  unreadable and every digest inflates.
- **Dry-run first, then: back up → archive the removed sections VERBATIM under a dated archive path →
  rewrite the file with the live sections only → verify.** Verify with numbers, not eyesight: chars
  before/after, section count, and **open boxes preserved**. Nothing is deleted; the archive is the undo.

### A `waiting on <seat>` row is a CLAIM — open the note it cites before keeping it

**A pending row that names another seat is an assertion about that seat's silence, and the note it points at
usually contains the disproof.** Measured: a row sat in a pending list for three weeks labelled *waiting on a
peer* while the cited handoff carried a signed `## Agreement` from that peer, accepting the scope exactly as
written, with the toolchain verified — and the remaining action parked by the **user**, not by the seat.

- **Grep the cited file's closure blocks (`## Agreement`, `## Receipt`, `## Supersede`) before letting the row
  survive a triage pass.** A signed block from the named seat means the row describes a debt that does not exist.
- **An invented debt is worse than a stale row.** Every later session inherits it, re-reports it as a
  colleague's lateness, and the colleague gets chased for work already finished — which is the same false
  accusation a checker makes when it reads the wrong lane, one layer upstream.
- **Re-write the row, do not delete it:** `PARKED ON <the real gate>` plus the evidence cited by section or line,
  so the next reader can check the claim in one hop. Deleting loses why it was ever believed open.
- **Apply the mirror test before blaming the seat:** was the note actually addressed to it? A target that is a
  retired alias, a folder, or a seat with no mailbox cannot answer, and that is a routing finding, not silence.

## 3a · Orphaned notes — four gates, then classify by how the note ENDS

Sweeping a workspace room for "forgotten ideas" fails if you start from the folder named for them: **a room named
for an activity fills with that activity's by-products.** Measured on one ideas room of 326 notes — `ideas/` held
**2**, while `context-bridge/` held 94, `specs/` 64, `job-apps/` 40, `drafts/` 13. Measure by gates, not by shelf.

**Four gates, each dropping a different false positive:**

1. no `Status:` and no `Next:` marker (a labelled note is already someone's decision);
2. age beyond the class window (30d for a working room);
3. not a process-output folder (`context-bridge`, `job-apps`, `drafts` — they are evidence of work, not asks);
4. **its title appears nowhere in the build queue** — the gate that separates "not labelled" from "not tracked".

**Then classify by the note's own CLOSING language, never by its opening tone:**

| the tail of the note says | state | what it needs |
|---|---|---|
| shipped / completed / delivered / merged | **done but unclosed** | one `Status:` line — no judgement |
| dropped / obsolete / superseded / rejected / cancelled | **dead but unburied** | one `Status:` line naming what replaced it |
| neither | **genuinely open** | a decision: idea → queue, or `superseded by <path>`, or dead |

Measured split of 98 orphans: **25 done · 9 dead · 64 open.** The 34 in the first two rows cost exactly the same
attention as lost work while containing none — so close them first; it is one field each and it halves the pile
before anyone has to think.

**Execution recipe for the first two rows — quote, never judge:**

1. **Tarball the whole room OUTSIDE the vault before the first write.** No git means that archive is the only
   undo; a per-file backup list is not a substitute for a single restorable object.
2. **Extract the closing sentence mechanically from the note's own tail** (last ~2.5 KB), then **quote it inside
   the `Status:` line**. This is what makes the closure defensible: the note already said what happened, and
   the label is a citation rather than an opinion. A sweep that *judges* each note re-opens the reading problem
   it was meant to end.
3. **A note whose closing language you cannot locate STAYS OPEN.** Measured: 31 of 34 had quotable evidence and
   were closed; **3 did not, and were left alone.** A closure you cannot quote is a decision smuggled in as
   bookkeeping, and it is unreviewable forever after. **Take the quote from the last two or three non-empty
   lines only** — a keyword found anywhere in the tail is mid-note prose about the subject, not the note's own
   verdict, and a scanner that accepts it will "close" live documents. Read the proposed quote yourself before
   any write: if it describes the topic rather than the ending, the note stays open.
4. **Re-run the SAME gate function and print before/after** (`98 → 67`). A count you assert is a claim; a count
   you recompute with the original predicate is a receipt — and it also proves the gate, not just the sweep.
5. **Know what you moved on the clock.** Appending a line rewrites `mtime`, so any report that ages notes by
   mtime will read these as freshly touched. Either age by the note's own date field, or close them after the
   current reading and say the discontinuity exists.

**Disposing of the remainder — sort by SHAPE, then ask for one decision per band.**

Closing the done/dead rows leaves the genuinely-open set, and it is still too many to read one at a time.
**Sort it by what each note IS**, read from its title and first body line, not by age: `draft` ·
`application` · `research` · `decision` · `note`. Roughly: 43 working notes, 11 research scans, 7
decisions, 3 external drafts, 3 applications — five bands you can decide in five sentences.

- **Test whether the closing vocabulary exists at all before promising closures.** Grep the remainder for
  `superseded|replaced by|obsolete`. Measured: **zero of 67** contained it — so unlike the previous batch,
  none could be closed by quoting itself, and the honest answer to the user is "these need your decision",
  not a second mechanical pass.
- **A decision is not a task and does not expire because nobody touched it.** A standing principle or a
  run-sheet that still governs how work is done is filed in the wrong room, not stale: **move it to the
  system/rules folder or its project** and say so. Auto-closing one deletes a rule nobody re-derived.
- **Applications close by DATE, and that is not a failure.** One word, `dead — deadline passed`, and the
  band is gone.
- **Drafts are the only band where value can be sitting, and the only band that needs checking rather than
  labelling.** They are finished work aimed at an outside party that was never sent. **Verify the destination
  still wants it before sending** — a weeks-old bug report lands as noise and burns credibility, which is
  worse than never sending it. Verify, then send or close; never re-send blind.
- **Verify the PREMISE, not just the address.** A draft written against a live service makes a factual claim
  ("this blocks paid execution", "this form accepts these fields"). Re-measure that claim against the service
  itself before re-sending, because nine weeks is long enough for the bug to be fixed, the offer to change, or
  the catalogue to renumber. **A live destination with a dead premise sends noise; a dead destination with a
  live premise means the draft was never the problem.**
- **A premise that is STILL true months later retires the LANE, not just the draft.** Measured: a bug report
  aimed at a marketplace whose payouts had been frozen since it was written was still exactly true when
  re-checked — `payment.wallet.operational: false` in a document the platform regenerated that same minute. The
  correct disposition is *do not post*: a bug report asks a pipe to reopen, and a pipe shut for a quarter is a
  business answer, not a queue. Record the measurement as the evidence for why the lane is closed.
- **Check the target still exists — repositories and forms MOVE.** The same draft addressed a repo path that had
  since moved to an organisation, so the prepared issue would have 404'd on a platform that was otherwise
  alive. Re-resolve the destination (repo owner, submission URL, form action) as part of the check, and prefer a
  redirect-following fetch that reports the FINAL url over assuming the old one.
- **Say which bands are pure filing debt.** If four of five bands are housekeeping, the user needs to hear
  that number plainly, or the three drafts look like 67 lost opportunities.

- **Report the THEME, not the list.** The 64 clustered into four themes (a marketplace/listing push, product ideas,
  positioning notes, a film/music thread). Naming the theme surfaces the real finding — *a whole lane went stale
  without a decision to stop it* — which a flat list of 64 titles hides completely.
- **Check the existing curator before building a new sweep.** A daily audit job was already reporting the
  never-routed ideas correctly and delivering to `local` — the right answer, in a file nobody read. Fixing the
  delivery outranks writing a second instrument (see the mute-instrument rule in `cron-delivery-audit`).
- **The structural fix is a third disposition, not a bigger sweep.** If a note can only be open, done-by-accident,
  or dead-by-accident, the backlog regenerates; give the class an explicit `superseded` state and the count stops
growing on its own.

## 3b · When one subject has six homes — and six different prices

A live commercial subject (what we sell, to whom, at what price) is the worst case for an append-only vault: every
pricing pass, every repositioning, every "here's the new offer" writes a **new dated note**, and nothing ever demotes
the previous one. An agent then reads whichever file it finds first and quotes a price we stopped charging months ago.
Measured: three different prices for the same service were simultaneously "current" in three notes.

**Fix — one canonical document per commercial subject, everything else demoted to evidence:**

| role | what it holds | rule |
|---|---|---|
| **canonical** (`<SUBJECT>-BUSINESS.md`) | what we sell, the price ladder, the live inventory, the funnel, the operating rules | the only file an agent may quote |
| **evidence** (dated notes) | settlements, forensics, audits, post-mortems | keep them; they are proof, not a competing version |
| **index** | one line at the TOP of the routing index | names the canonical file and says evidence is not a price source |

Rules that make it stick:

1. **State machine truth, not aspiration.** The canonical doc carries the inventory as the machine knows it — live
   services, withheld services **with the system's own reason**, and how many rails are advertised versus proven.
   Numbers that a file already owns belong in that file, not in prose.
2. **Give it a "what is NOT built yet" section.** A canonical page that only lists what exists invites a future
   session to assume the rest is done. Name the unbuilt product, the intake that does not exist, the page nobody
   has published — with the gate that blocks it.
3. **Index at the ROUTING layer, not by hoping.** A canonical doc nobody is routed to is one more home. Put the
   pointer above the folder table so it is read before any retrieval.
4. **Do not delete the older notes to "remove the conflict."** They are the evidence trail behind the current
   number; deleting them is how a later session cannot prove why a price or a claim is what it is.
5. **Re-check the canonical doc whenever a component changes** — a service shipped, a rail settled, a product cut.
   A canonical doc that drifts is worse than none, because it is the one file everyone trusts.

## 4. Pitfalls that cost real time

- **Excluding a directory by SUBSTRING skips the whole tree when the root's own name contains the
  token.** `if ".obsidian" in root: continue` matches every path under `/opt/data/.obsidian-vault`, so
  the walk yields nothing and the audit reports an empty vault. Compare path **components**:
  `set(os.path.relpath(root, V).split(os.sep)) & {".git", ".obsidian"}`.
- **"Empty folder" means empty SUBTREE, not no direct files.** A container folder with all its content
  in subdirectories reads as empty under a direct-files test, and you prune a live branch.
- **Count empty DIRECTORIES recursively, never just bare top-level folders.** "47 empty" is what you get when the
  test is `len(files_in_top_level_folder) == 0`; the same tree held **158 empty directories at depth** (and a
  sibling vault 2,671 across all folders) — a third of the real number was hidden one level down, and the number
  went into a handoff before anyone checked. Walk the tree, count leaves (`no subdirs and no files`), and print
  the per-subtree total: the shape of the mess decides the work (47 stubs to delete vs 158 directories to prune
  are different jobs), and an understated count reads as a job already done.
- **A folder audit that matches paths as SUBSTRINGS reads one folder as TWO.** A search for `HQ/` also matches
  inside `00-HQ/`, so both folders return the **identical** reference count — and identical scores across two
  near-identically-named folders is the TELL, not a coincidence: one match fired twice. Anchor the top-level
  segment (`(^|[^0-9A-Za-z_-])HQ/`) before believing any folder map. Measured: the unanchored version scored
  `HQ` and `00-HQ` the same and made five orphan folders look wired; anchored, they separated to 35 and 64
  references — and `HQ/` turned out to be a live folder, not a dead duplicate. Every folder map built with
  plain substring matching carries this defect.
- **TTL is timezone-free, but the human-facing window is DST-blind.** TTLs compare mtimes in UTC (safe);
  the quiet window and any "today" label are local-time — derive those from the clock, never from a
  hardcoded offset.
- **A wandering skip rule makes a confident wrong count.** After any classifier change, re-run on the
  same corpus and compare to the previous run; a jump in a count is usually the classifier, not the vault.
- **A curation report the user reads once and never acts on is a failure of routing.** Identify per-seat
  stale work AND route it into `01-HANDOFFS/INBOX/<seat>/` — otherwise the curator is a nightly report
  instead of a self-clearing system. (Name the routing gap honestly when it is not built yet.)
- **Vault bloat hides as "many folders" long after it is really "many artifacts."** 56 top-level folders with
  35 holding under 5 files read as a fragmentation problem; the fix was 231 backup files and one `node_modules`
  tree. Measure artifact classes before proposing a reorganisation — merging folders would have tidied nothing.
- **No git means the manifest is the undo.** Before any bulk move, write the list of exact paths to a file
  outside the vault; a move you cannot enumerate afterwards cannot be reversed.
- **An empty MIRROR tree is a rename artefact, not a duplicate estate.** A folder that contains **zero files**
  while reproducing the root's own subfolder names (measured: 48 of 48, and **1,754 empty directories**, `ctime`
  minutes old) is what a root-level rename or a sync client's move leaves behind. **Classify a candidate by FILE
  COUNT before anything else** — 0 files means nothing was lost and nothing needs merging, and merging content
  *into* the shell would create a second empty estate beside the real one. Delete the shell (or let the sync
  finish) and say which it was; do not "consolidate" it.
- **A DATED RECEIPT is not a stale note.** A page whose age is its identity — `2026-09-28-17-market-presence.md`,
  `brain-snapshot-2026-08-15.md`, `*-completions.md` — must be excluded from staleness scoring by **file shape**,
  not by luck. Measured: 2,121 of the files a staleness pass read were receipts, and flagging them buried the
  handful of operational notes that would actually mislead a reader today (**295 flagged → 108 after the fix**).
  **Count the exclusion** (`skipped_dated`) and print it: a filter you cannot see is indistinguishable from a
  corpus that changed, and the next reader will assume the drop was the vault getting cleaner.
- **"Stale" and "unreachable" are different defects, and one instrument cannot answer both.** Claim-age scoring
  says nothing about whether a note's links still resolve; a folder rename can hollow out a corridor while every
  claim inside it is fresh. Run both, report them separately. See
  `references/link-and-reachability-audit.md`.

## 5 · Wiring — reachability is measured separately from staleness

A stale claim and a dead link are different defects, and the second one is invisible to any age-based scanner.
Three numbers, computed over the note corpus, cover it: **broken link targets**, **orphans** (nothing points here
and it points at nothing), **dead ends** (it links out, nothing links in). The procedure, the resolution rules and
the two definition traps that make a naive version report nonsense are in
`references/link-and-reachability-audit.md`.

**The finding that outranks the counts:** if `inbound_by_link` is ~0 across the vault, **the brain is navigated by
path, not by graph** — every corridor depends on the reader already knowing a filename. That is a structural
statement about how the vault works, and it is worth more to the user than any orphan list.

## Related

- Cron delivery targets and the quiet-hours window: the `cron-delivery-audit` skill.
- Moving/archiving files safely: `destructive-write-guards`.
- The vault's own read/write rules: `note-taking/obsidian` — that skill also carries the
  **vault-consolidation** reference, the full merge/redirect procedure for when two copies have DIVERGED.
