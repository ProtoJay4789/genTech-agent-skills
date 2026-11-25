---
name: build-queue-maintenance
description: >-
  Use when editing the build queue JSON or passing its gates.
always: true
---

# Build Queue Maintenance

## When to Use

Load this whenever the task touches `00-HQ/build-queue/` — adding, closing, re-gating or renumbering
rows; running a gate pass; writing a script that reads the queue JSON; or when a reporter/digest over
the queue reports something that does not match the file. Also load it before any *in-place edit* of
`build_queue.json`, because the safe-editing rules here are not discoverable from the file itself.

Deep code for the in-place edit path: `references/queue-json-surgery.md`.

## Where the queue lives, and who owns it

**`00-HQ/build-queue/` — `queue.md` (narrative) and `build_queue.json` (machine state), in ONE folder.**

- **HQ owns it.** The queue stopped being a department artifact the day its work spanned a payment gateway, a
  repo deletion, a memory system and a vault rule. **No department owns a cross-lane list, so HQ does: seats
  propose, HQ orders.** A queue filed under a code tree drifts away from its own JSON — that is not a theory,
  it is what happened, and the two lists disagreed about five finished items for weeks.
- **Never split the two files into different folders again.** Side by side is the whole fix.
- **When you move a queue, count the readers first.** Measured on one move: **8 files read the markdown and 17
  read the JSON**, referenced three different ways (a Python constant, a shell variable, a table entry).
  **Patch all of them, then RUN each one** — a grep proves a string changed, only a run proves the reader still
  resolves the path. Leave a visible signpost at the old path and update the vault's routing indexes in the same
  pass, or the next agent follows an index into a folder that no longer exists.

## Golden Rule

**After every modification to the build queue, renumber all items 1..N.**

The highest item ID must always equal the total item count. If there are 17
items, IDs are 1-17. Never 1, 2, 3, ... 87, 88, 91.

## When to Renumber

- After marking an item as `shipped` or `cancelled` (removes it from active)
- After adding a new item
- After re-prioritizing items
- After any bulk edit

## A row marked `pending`/`blocked` may be citing a gate that already RELEASED

**Re-measure the gate before trusting the status.** Several rows sat in `pending` with `needs_jordan: true` while their own
`release_condition` had already been met — the row was written at the moment the gate closed and nobody re-read it. Treat
`pending` as *"a claim about the world as at the date it was written"*, not as current fact:

- Read `gate` / `blocked_on` / `release_condition`, then **measure both halves** of the condition. A gate that names two
  conditions ("(a) reinstatement decision in, (b) vault measures clean") needs both re-measured — satisfying one is not the gate.
- If the gate is open, the row is actionable *today*; say so in the `gate` field (`RELEASED <timestamp> — evidence`) so the next
  reader does not repeat the measurement.
- `needs_jordan: true` is a claim about **Jordan**, not about the gate. Check whether the pending item is actually his decision or
  ours-behind-a-condition — a false `needs_jordan` parks work indefinitely and looks like a decision nobody made.

**⚠️ A gate that names a CREDENTIAL must be resolved against the secret store BEFORE it is repeated to the
user.** Measured: a row read *"BLOCKED ON A CREDENTIAL THAT IS NOT SELF-SERVE — <human> must apply"*, the
credential had been supplied days earlier and sat in the secrets directory mode 600, and the row was never
updated. The gate was repeated verbatim, and the human answered *"I already gave you one"* — the signup page
we sent him to was work he had already finished. **Repeating a stale gate costs the user a task, and costs the
queue its credibility.**

- **Search the store before calling anything missing:** `find <secrets-dir> -iname '*<service>*'`, then grep
  env files for the variable NAME only (never print values), then check the mtime — a key supplied after the row
  was written is the common case.
- **A credential gate is released by a CALL SUCCEEDING, not by a file existing.** A key that is present but dead
  is still a gate; make one real request with the project's own client and quote the result.
- **Rewrite the gate text in the same turn you measure it** (`CLEARED <timestamp> — <evidence>`), or the next
  reader repeats the ask. The old text is the whole mechanism of the repeat.
- **Resolve `needs_jordan` at the same time** — a credential gate that is actually cleared often also means the
  row was never his decision.

**Duplicate-key trap when writing a `gate` field:** some rows carry `gate_prev` (a nested object that itself contains `"gate"`),
plus a top-level `gate` further down the row. Inserting a second top-level `"gate"` earlier in the row parses fine in Python and
**silently loses** — `json.loads` keeps the LAST key. Grep the whole row for `"gate":` before inserting, and assert exactly one
top-level match (two spaces of indent, not three).

## Traps when EDITING build_queue.json

**1b. A row's gate that names ANOTHER ROW'S ID is a dangling pointer — ids are renumbered by this skill's own golden rule.** Measured 2026-11-24: a row read `blocked — row #50 must land first`, and current #50 was the **dropped** BOT Chain challenge — a gate that can never release — while the #50 it was originally bundled with had been renumbered to #60 and had shipped six hours before the row was written. The work the row asked for was already in the code, and the row sat blocked for weeks.

- **Resolve an id-gate by NAME and date, never by the id alone:** find the row the note's own vocabulary points at (`_orig_id`, the commit message that cites it, the note's phrasing), and check whether *that* row's status released the gate.
- **Then check whether the gate was ever needed:** if the gated work shipped in the same commit series as the thing it waited on, the gate is answered — re-gate it, do not obey it.
- **A gate on a `dropped`/`cancelled`/`superseded` row is not a gate**, it is a deadlock. Rewrite it as `own` (with the restore/retire/bundle work named) or the row is unplannable.
- **When you rewrite a gate you measured, write `RELEASED <date> — <evidence>` in the same turn**, or the next reader repeats the measurement (and the next truth pass re-blocks it from the same stale text).

**1c. An `updated_at` that never moves is a silent revert.** A truth pass can flip a genuinely shipped row (`completed_at` written by the ship commit) back to `blocked`; nothing re-opens it. **A row whose `completed_at` is set and whose status is `blocked`/`pending` is a contradiction to resolve by measurement, not a state to average.**

**1. Match items by NAME, never by ID.** Renumbering is this skill's own golden rule, so IDs are
*by design* unstable. An item you filed as #54 can be #41 an hour later — and `if it["id"] == 54`
will silently hit a **completely different** item and overwrite its note. Proven 2026-09-30: an
id-based status write landed on "OpenDexter re-settle" instead of the fx item it was meant for,
and only a diff caught it.

```python
# WRONG — ids move
for it in items:
    if it.get("id") == 54: it["status"] = "shipped"

# RIGHT — name is the stable key; assert exactly one match before writing
hits = [i for i in items if "fx-tracker" in (i.get("name") or "")]
assert len(hits) == 1, f"expected 1 match, got {len(hits)} — refusing to write blind"
```

**2. PROVE your serializer reproduces the file byte-for-byte BEFORE you write with it.** Encoding and
indentation are both traps, and the safe settings are not fixed — they depend on how the file was last
written. Measured on the live queue: it carries **literal** em-dashes in most row text and `\uXXXX`
escapes in some, and the list is dumped at `indent=1` (opening brace one space, keys two). So
`ensure_ascii=True` re-encodes the literals, `ensure_ascii=False` re-encodes the escapes, and
`indent=2` re-indents every line. Each choice produced a **1,000+ line diff on a 46-row edit**,
burying the change so nobody could review it — twice, in opposite directions.

The check is one line, and it is falsifiable:

```python
raw = open(QUEUE).read()
assert json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + "\n" == raw, \
    "serializer does not round-trip — SPLICE instead of re-dumping"
```

If that assertion holds for the file as it is, a whole-file rewrite is safe. If it does not, **do not
guess a better pair of settings — splice the rows you touched and leave every other byte alone**
(see *Editing rows in place*).

**Check before committing:** a one-field edit must show **~2 changed lines**. A huge diff means you
re-encoded — `git checkout -- <queue>` and redo.

## WIDEN the file, never re-serialise it — json.dump over the whole queue is a 4,000-line diff

**Measured three separate times on 2026-11-18, each time by an agent who had already read this
skill.** A 46-row gate pass written with `json.dump(rows, indent=2)` produced **4,341 changed
lines**; one row updated by a raw-text splice produced **7**. Why:

- **`ensure_ascii=True` re-escapes** every literal `—` into `\u2014`. The committed file carries
  BOTH forms, so no single setting round-trips it.
- **`indent=2` re-indents** every key, because the queue stores keys at two spaces and braces at
  one. `indent=1` matches the keys but not the braces.
- **Any full re-dump changes the file's encoding surface**, and the real change disappears inside
  it. A reviewer cannot see a one-row edit through 800 lines of whitespace.

**The rule: locate the row's object span in the RAW TEXT and splice.** Use
`profiles/gentech/scripts/queue-patch-row.py` (one object at a time) or the span logic in
`queue-gate-pass.py` (many at once). Both must:

1. scan braces **outside of strings** — a JSON string can contain `{`, and counting it desyncs the
   scan so one row's text is written over its neighbour's (measured, twice);
2. measure every span against the untouched original, then splice in one pass;
3. `json.loads()` the result **before** writing it;
4. emit with `indent=2` and no leading space, which reproduces a row byte-for-byte.

**Guards that belong in the script, not in your head:**

- **Match the id as JSON-emitted text** — ids are mixed-type: `15` (int), `"rev-3"` (quoted
  string), `"#106"` (unquoted string). `str()` fails on the quoted ones.
- **A row can carry NO `id` key at all** (one superseded row has only `_orig_id`). Skip it, do not
  fail the count check on it, and never treat `_orig_id` as a target id.
- **Snapshot first** to `cache/scratch/` and `git checkout --` the file if the diff looks large. A
  huge diff is a re-encode, not a change; reverting costs nothing, reviewing 800 junk lines costs
  the edit its credibility.

**Same lesson as `shared-file-writes`: the smaller the diff, the more it can be trusted.**

**3. IDs are not always integers — and a merge is what makes them mixed.** A queue that absorbs rows from a
prose list acquires **string ids** (`rev-1`, `rev-6`) beside the numeric ones, and every reporter that assumed a
number dies at the first sort or format:

- `sorted(key=lambda i: (rank, i["id"]))` → `TypeError: '<' not supported between instances of 'str' and 'int'`
- `"#%d" % item["id"]` → `TypeError: %d format: a real number is required, not str`

**Both fail in a way that reads like a queue problem** (a digest that says "script failed"; a reconciler that
raises before reconciling anything), which is the expensive part. **Sort on a numeric extraction when there is
one, then on the id as TEXT as a tiebreaker** — a total order that cannot crash:

```python
def _k(i):
    raw = str(i.get("id", ""))
    num = "".join(ch for ch in raw if ch.isdigit())
    return (rank.get(i.get("difficulty"), 1), int(num) if num else 10**9, raw)
```

**And a merged item must not be renumbered into the sequence** — the golden rule below applies to the numeric
scheme, and renumbering a `rev-*` row to `#47` destroys the only link back to the prose it came from. **Keep the
semantic id, keep `_orig_id`, and add the numeric sequence around it**, not through it.

**4. Never invent a STATUS, and know that `needs_jordan` is a BOOLEAN FIELD, not a state.** A truth pass
re-mapped two human-gated rows and wrote `status: "needs_jordan"` on them — because that is precisely what they
were. Any reporter that switches on the status string then meets a value it has never heard of and falls through
to a default branch, which is how a queue silently stops counting an item.

```python
# WRONG — a status outside the vocabulary
item["status"] = "needs_jordan"

# RIGHT — the vocabulary status, plus the flag the file already carries for exactly this
the item's human gate is expressed as:  item["status"] = "pending"; item["needs_jordan"] = True
```

**Before writing any status, enumerate the ones already present in the file and pick from that set.** The
vocabulary is already messy enough: several words mean *done* (`shipped`, `closed`, `completed`) and several mean
*ended unhappily* (`dropped`, `cancelled`, `superseded`, `rejected`). Use the one the tooling and the reports
actually read — **never add another synonym, and never a word that is a field name elsewhere in the schema.**

## Editing rows in place (when a full re-dump is unsafe)

Assemble the new text from the ORIGINAL bytes: find each touched row's span once, then splice them in
**one forward pass**. Working copy for the scanner: `references/queue-json-surgery.md`.

```python
# 1. scan spans with a STRING-AWARE brace walker (never a regex, never brace counting)
# 2. json.dumps each edited ROW at indent=2 (a standalone object: keys land at two spaces)
# 3. splice forward, ascending by start offset, carrying a cursor
out, cursor = [], 0
for s, e, replacement in sorted(edits, key=lambda t: t[0]):
    assert s >= cursor, "overlapping spans — refusing to write"
    out += [raw[cursor:s], replacement]
    cursor = e
out.append(raw[cursor:])
open(QUEUE, "w", encoding="utf-8").write("".join(out))
```

**Span-finding: three approaches all fail before a brace-walker works.** Each one costs a corrupted file
and a round of debugging, so start with the walker:

| approach | failure |
|---|---|
| `re.finditer(r'^ \{\n.*?^ \}', raw, re.S\|re.M)` | `.*?` stops at the first `^ }`, but `.` with `re.S` also crosses row boundaries — returned **70 matches for 116 rows**, overlapping spans, one row's text written over its neighbour's |
| pairing an opening brace line with the next closing-brace line | a row with a **nested object** (`checkin: {...}`) closes at a different indent and desynchronises every pair after it |
| counting `{`/`}` per line | a JSON **string** can contain a brace (an instruction, a URL template) — depth never returns to zero |

The walker tracks `in_str`/`esc` so braces inside string literals are ignored, pushes on `{`, pops on
`}`, and yields the span when the stack empties.

**Splice boundaries — count the bytes exactly, and get this from the file, not from memory:**

- The span ends **at** the closing brace, so the trailing `,` is outside it and `replacement = block` alone.
  Appending the comma again writes `},,`; including the brace in the span and re-appending it writes `}}},`.
  Both parse-fail on the *next* run, not this one.
- **Verify by re-loading from disk**, not by trusting the write: `json.load(open(QUEUE))` in the same script,
  then assert `len(items)` unchanged and every untouched row equal to its pre-edit copy. When the diff is
  still large, diff ONE touched row and ONE untouched row by hand — untouched rows must be byte-identical.

**Refuse the batch, do not partially apply.** Before writing: every named target must exist, still be in a
state you expect, and resolve to a span. One missing target aborts the whole pass — a half-written queue has no
status that describes it.

**Adding a row is an append, not an edit.** Do not build the new row and re-dump the list, even with a
serializer that round-trips: measured, a two-row addition as a whole-file write cost **419 inserted / 381
deleted** lines, the same addition as a text append cost **40 inserted**. The append anchor and the exact
indentation recipe are in `references/queue-json-surgery.md`.

**⚠️ Another writer can change the file between your snapshot and your write — diff against the state you READ, not the snapshot on disk.** Measured: a single-row splice read 118 rows and wrote into 119, because a cron had appended a row and moved another to the tail in the ~90 seconds between snapshot and patch. The splice was still correct (only the target row differed), but a `diff snapshot live` showed 67 lines of *someone else's* work and would have read as "my one-field edit re-encoded the file" to anyone reviewing it.

- Assert row count on the WRITE (`queue_patch_row.py` does: `len(parsed) != len(rows)` refuses), then verify by comparing **parsed row objects positionally against the copy you read at write time** — not against the pre-snapshot backup.
- Report the concurrency out loud in the write-back note ("118 → 119 rows; row N reordered by another writer; only row X differs among the originals"), or the next reader reads the churn as your damage.
- A reordered row at the tail is normal, not a corruption: the steward's renumber moves finished rows down.

**Snapshot first:** `cp build_queue.json <scratch>/build_queue.bak-<date>.json` — every iteration of this
procedure is `git checkout -- <queue>` away from clean, and you will loop.

### Iterate on a COPY, not the live file — this is the step that stops the loop

**Knowing the splice rules is not enough; the session that documented them still corrupted the file eight
times.** The failures were all in the *writer* (span boundaries, id matching, offset arithmetic), and each
one was only visible after a live write — so each cost a `git checkout --`, a re-read, and a re-diagnosis.

**Make the first N runs touch a copy:**

```bash
mkdir -p <scratch>/qtest && cp build_queue.json <scratch>/qtest/q.json
python3 my_writer.py --path <scratch>/qtest/q.json      # parameterise the path, always
python3 -c "import json;json.load(open('<scratch>/qtest/q.json'))"   # parses?
diff <(python3 -m json.tool build_queue.json) <(python3 -m json.tool <scratch>/qtest/q.json) | head -40
```

- **Any writer you hand-build must take its target path as an argument** (`--path`, env var, or a module
  constant you can override) so it can be aimed at a copy. A script hardcoded to the live queue can only be
  debugged by damaging live state.
- **Assert the invariants on the copy before the real run:** the file parses, `len(items)` is unchanged (for an
  edit) or +N (for an append), and **every untouched row is byte-identical**. Diff one touched row and one
  untouched row by hand — that pair is the whole check.
- **Only when the copy is clean do you point the writer at the live file**, and then immediately `git diff --stat`.
  A large stat means you are back to a re-encode; revert, don't review it.

**A re-runnable row-patcher ships with this skill:** `scripts/queue_patch_row.py` (string-aware span finder +
single-row splice, takes `--path`). Prefer running it over re-deriving the walker; extend it with flags rather
than writing a fourth private copy.

## How to Renumber

1. Load `scripts/build_queue.json`
2. Sort active items by priority: `urgent → high → medium → low`
3. Assign sequential IDs 1..N to active items
4. Put cancelled/shipped items at the end with their own sequential IDs
5. Update `summary.total` to match `len(items)`
6. Update `summary.pending`, `summary.in_progress`, `summary.shipped`
7. Update `summary.needs_jordan` (count of active items with `needs_jordan: true`)
8. Update `gate_summary.human_gated` and `gate_summary.decision_gated`
9. Bump `version` by 1
10. Set `updated` to today's ISO date

## Priority Sort Order

```python
priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3, 'none': 4}
```

Within the same priority, sort by original ID (oldest first).

## Example

Before (17 items, highest ID 91):
```
#87 Paymenter Marketplace
#88 Pterodactyl Outreach
#89 WHMCS/Blesta Port
#90 Hippocratic AI
#91 Great Agent Hackathon
```

After renumber (17 items, highest ID 17):
```
#1  Keeperhub Hackathon (urgent)
#2  FrameForge (high)
...
#16 Hippocratic AI (low)
#17 OKX (cancelled)
```

## Standalone Renumber Script

For manual renumbering (without a Forge handoff), use:

```bash
python3 scripts/renumber_queue.py          # dry run (preview changes)
python3 scripts/renumber_queue.py --apply   # apply renumber
```

This is useful when you've manually added or removed items from the JSON file and
need to clean up IDs without going through the full tick script.

## Tick Script

The tick script at `scripts/tick_build_queue.py` handles the renumbering
automatically when run with `--apply`. It reads `forge-completions.md`,
updates the queue, and renumbers. Run it after every Forge handoff.

```bash
python3 scripts/tick_build_queue.py --apply
```

## Verification Before Removal

**Do not mark items as "disputed" or "cancelled" without direct evidence.**

The Kite AI incident (Jul 2026) proved this: an item was flagged as "disputed" (no source URL, $0K prize) and removed from the queue. Three days later, Kite AI was confirmed real — they had open-sourced 14 MIT-licensed x402 skills and had real engagement metrics we could have checked.

**Verification checklist before marking anything disputed:**

1. **Check the source URL** — if the build queue entry has a URL, fetch it with curl or web_extract. If there's no URL, search the web for the product name.
2. **Check social media** — search X/Twitter for the account/product name. Engagement metrics (likes, retweets, views) are evidence of existence.
3. **Check GitHub** — search for the org/repo. Even 0 stars with recent commits is evidence the project exists.
4. **Check the vault** — session_search the topic. We may have discussed it in a prior session.
5. **Ask Jordan first** — "Item #X was flagged as potentially fake. I checked [source/social/GitHub] and found [evidence]. Should I keep or remove it?"

**The cost of a false negative:** We miss a real ecosystem player, a real hackathon prize, or a real partnership opportunity. The cost of a false positive (keeping a dead item one more cycle) is near zero — it just sits in the queue until the next cleanup.

## Gate Summary Verification

After renumbering and updating status counts, verify the `gate_summary` section matches actual items:

```python
human_gated = sum(1 for i in data['items'] if i.get('human_gated', False))
decision_gated = sum(1 for i in data['items'] if i.get('gate_type') == 'decision')
autonomous = sum(1 for i in data['items'] if not i.get('human_gated', True))

data['gate_summary']['human_gated'] = human_gated
data['gate_summary']['decision_gated'] = decision_gated
data['gate_summary']['autonomous'] = autonomous
```

**Common drift pattern:** `human_gated` drifts when items are added/removed without updating the summary. The cancelled item (#22 OKX) still has `human_gated: true` — it counts toward the total even when cancelled. Always recount from `items[]` rather than incrementing/decrementing the old value.

## Git Push Rejection Handling

**REMOTE MAP (near-miss Aug 29, 2026 — do not repeat):** the vault has multiple remotes. `vault` = GentechLabs/gentech-vault.git (**the vault — push here**, `git push vault HEAD:main`). `origin`/`hub` = ProtoJay4789.github.io (**the portfolio site — NEVER push/pull vault content there**; different history, a `git pull --rebase origin main` in the vault tried to replay 430+ unrelated commits). The conflict recipe below is for the `vault` remote only — substitute `vault` for `origin`.

When `git push vault` is rejected because the remote is ahead (concurrent pushes from other agents or Jordan):

```bash
cd ${VAULT_DIR}
git fetch vault
git pull --rebase vault main
# If rebase conflicts on build_queue.json, resolve with theirs:
git checkout --theirs scripts/build_queue.json
git add scripts/build_queue.json
git rebase --continue
git push vault HEAD:main
```

**Why this happens:** The vault has two remotes (`origin` = portfolio site, `vault` = gentech-vault.git). Other cron jobs or Jordan's manual edits can push to the same branch between the queue read and the commit. Always expect the remote to be ahead.

## gh CLI Auth Workaround for PR Checks

The `gh` CLI may fail with `GITHUB_TOKEN` env var conflict (stale token in env overrides valid token in `hosts.yml`). When this happens, use curl with the token extracted from `hosts.yml`:

```bash
GH_TOKEN=$(grep 'oauth_token:' ~/.config/gh/hosts.yml | head -1 | awk '{print $2}' | tr -d '"')
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/search/issues?q=author:GentechLabs+type:pr+is:merged&per_page=10"
```

See the `github-auth` skill for the full GITHUB_TOKEN env var conflict resolution pattern.   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `github-auth` exists on this seat -->

## A queue that also stores reports is a log, not a queue

**The failure mode is measured, not theoretical:** a task list grew to **4,544 lines with 357
sections**, and when classified, only **16 were live items** — the rest were 221 appended brief
reports and 51 items already marked done. The queue had not lost anything. It had buried itself.

**Rule: one destination per kind of work.** A brief or status report *reports on* the queue; it
never appends into it. Reports go to a dated archive (`<archive>/reports-YYYY-MM.md`); finished
items go to the completion record. The live queue shows live items only.

### Diagnose before pruning

Split sections and classify by the markers already in the text:

| class | test |
|---|---|
| report | section header is a timestamp/run label (`## 🕐 …`, `-write-back-`) |
| closed | header or body says done / closed / resolved / shipped / cancelled / superseded |
| blocked | header says blocked / waiting on / gated / no action |
| live | none of the above |

**If `live` is a small fraction of `total`, the file is a log — say so with the counts** rather than
reporting a 300-item backlog. The difference between "327 open tasks" and "16 open tasks under 221
reports" is the whole finding.

### Prune with a reconciliation count, printed

Never prune on "looks big". Move, never delete, and prove the arithmetic:

```
sections_before == live_after + archived_reports + archived_closed
```

Print all four numbers in the change summary. A prune whose parts do not sum to the original is a
deletion, whatever it was called — and the reconciliation is what makes the operation auditable by
someone who never saw the file.

## "Routed to <seat>" is a label, not a handoff

**An item tagged `→ ROUTED: treasury` leaves the ideas list and enters no build list.** Measured:
a multi-module project carried a full spec and a routing tag in `ideas.md`, and had **zero entries**
in the build queue. Months later nobody could answer "is it built?" without reading 54 scripts — and
the answer turned out to be "four modules yes, four partial, one missing," which no list could have
told anyone.

- **Routing must create a queue entry, then link back.** The ideas line gains the queue id; the
  queue entry carries the gate and the assignee. A routing sentence with no id behind it is where
  work goes to be forgotten.
- **"Routed" is not a status.** Valid statuses live in the queue; if an idea's state is only
  expressible in prose, it has no state.
- **An investigation that answers a queue question belongs in the queue**, not only in a chat reply.
  If the finding is "module X is missing", file it as an item with a name and an assignee, or the
  next session re-derives it from scratch.

## Auditors are not actors — count both

A fleet can accumulate verification and still move nothing: five scheduled producers auditing a
knowledge base (staleness, shape, lifecycle, acknowledgements, list hygiene) and **no job that
moves an item between states.** Reports accumulate beside the things they describe.

- **When adding a monitor, ask what it CHANGES.** A producer whose only output is a report needs a
  counterpart that acts on it, or the backlog grows at the speed of the reports.
- **Bound the acting job to mechanical moves** (state transitions provable from the item's own text
  or a matching record). Leave judgement — declaring something dead, merging, reprioritising — out
  of it. A worker that reclassifies hundreds of items on a keyword score is confidently wrong about
a third of them and trusted never again.
- **Deleting is never a worker's move.** Archive with a reason; a killed item with a reason stops
  the next person proposing it.

## Two records of "shipped" means one of them is dead

A project with both an append-only completion log and a structured registry will keep exactly one
of them current, and it is always the append log — because appending is one line and updating a
record is a decision.

### The four lists, and which one is generated (settled 2026-11-06)

Jordan's four categories, in his words: **build queue** · **orchestrator list (Jordan's queue)** ·
**pending** (waiting on, e.g. a grant decision) · **completed**. Each has one job and one writer:

| list | file | who writes |
|---|---|---|
| build queue | `00-HQ/build-queue/queue.md` + `build_queue.json` | agents, via the queue |
| Jordan's queue | `HQ/jordan-queue.md` | HQ, when something needs his hands |
| pending | `00-HQ/pending-list.md` | anyone — pending *includes* blocked |
| completed | `00-HQ/completed-list.md` | **NOBODY — generated by the steward** |

**The completed list is DERIVED, and that is the whole point.** It is rendered every night from
`00-HQ/completion-registry.json` as a **7-day window** (`COMPLETED_WINDOW_DAYS`), then entries age
into `completion-archive/YYYY-MM.json`. A fourth *hand-written* list is exactly how four lists drift
apart — the same content in two places, one of them stale, and no way to tell which.

**⚠️ The registry is NOT the completion record.** It is the **swept-ideas pile**: ticked items and
fully-done sections removed from the live lists. It held 19 entries of `ideas:` paths while the lanes
below carried thousands. It once described itself as *"the single source of truth for 'is this
done?'"* — and that sentence is why readers trusted the wrong file for three months. **The canonical
record of what shipped is `01-HANDOFFS/<seat>-completions.md`.**

**Lesson for anyone tempted to feed a registry from an append log:** don't. Appending prose bullets
into a queryable structure produces thousands of rows nobody can query, and a freshness check nobody
can pass. **Keep the append log as the record; render a small, derived view for humans** — a view
that can be regenerated is a view that cannot drift.

### Thresholds a healthy file cannot meet are noise

The registry's freshness limit was 96h and it fired **every day**, because a swept-ideas pile only
gains rows when something is swept, and sweeps are rare. A red flag with no action attached trains
the reader to skip the section — which is worse than no flag. **Set the threshold from the real
mechanic** (here: the steward's 30d TTL), not from a plausible-looking number.

- **Name the structured record canonical**, and write shipped work into it at ship time, with a
  proof token (commit / tx / path) rather than a narrative.
- **A heuristic that infers completion is not a completion record.** "No longer present in the
  state file, so it was probably acted on" produces entries that read like verified shipments and
  carry no evidence at all. Mark inferred entries as inferred, or do not write them.
- Before trusting a "what shipped" number, check the record's own last-modified date against the
  volume of work you believe was done in that window.

### A date baked into a heading goes stale by itself

`## 📅 TOMORROW (Thu 2026-11-05)` was still in the queue on 2026-11-06, with a table of steps for a
day that had already happened. **No process reads a heading and computes "is that still true?"** —
and a file-level mtime check cannot see it, because the file is edited daily for other reasons.

- **Store a DATE, not a relative word.** `WAITING SINCE 2026-11-05` ages visibly; `TOMORROW` is a
  claim that rots silently.
- **Audit headings, not just the file.** A queue's freshness is per-item, and only the item knows
  when it was born.

### One gate, one row — extend it rather than opening a second door

The human queue is where Jordan's hands are needed. **When a new fix lands behind a gate that already
has a row, EDIT that row.** A second row for the same command splits one decision across two places,
and he will run one of them — usually the older text.

- **Three labelled facts per row, never one:** what is **on disk** (written, syntax-checked),
  what is **deployed** (the restart/apply has or has not run), and what is **proven** (which probes
  returned what). Collapsing them lets a row say "already on disk" about work nobody wrote, or "fixed"
  about a process still running yesterday's code.
- **Put the verification probes in the row, and include a CONTROL** — one probe that must keep
  answering the old way. Without it, "the new behaviour appeared" and "the route broke" are
  indistinguishable from a single exit code.
- **Ask only for what the human can do.** One command plus the probes, not a checklist the agent could
  have run itself.
- **Discriminate "live differs from disk" before claiming a bug.** If the public surface disagrees with
  the generator while disk carries the newer value, the running process predates the code — that is a
  deploy gap, and it resolves on restart rather than in the source.


## `needs_jordan` is a gate, not a difficulty label — audit the flag

**A human queue that is mostly our own work stops being read.** Measured on one pass: **23 open rows carried
`needs_jordan`, and 19 of them needed nothing from him** — index a service, refresh registry records, resolve a
folder-case collision, wire a publisher. Every false flag lengthens the one list that can only be cleared by a
person, and the cost is not tidiness: it is that he stops opening it.

**A row keeps the flag only if it needs one of four things:**

1. **money** moved or committed,
2. a **credential** only he holds,
3. an **account or signature in his name** (KYC, signup, a submission under his identity),
4. a **decision that is genuinely his** — build this at all? does this surface exist? which of two directions?

**Everything else: set `needs_jordan: false`, give the row an owner, and keep it in the build queue.** A row that
is merely *hard*, *blocked on our own unblocking work*, or *waiting on another seat* does not belong here —
blocked/pending work has its own list, and "waiting on someone else" is never a human queue entry.

- **Report both numbers when you clean the flag** — flagged before, flagged after — so the shrink is visible and
  the audit is auditable.
- **State the reason on the row you clear** (`not a Jordan decision — ours to do`), or the next truth pass re-flags
  it from the same misreading.
- **Keep the human list short enough to answer in one sitting.** If it cannot be, the flag is doing the work of a
  priority field and the queue has stopped prioritising.

## Capture at arrival, or it does not exist

**A request that is not written into a list during the turn it arrives does not survive the
session.** No error occurs, no alarm fires — the request simply leaves the visible conversation the
moment a louder task arrives, and hours later someone has to ask whether it was ever done.

The test, applied before the turn continues: **if this turn ended now, would this request still
exist tomorrow?** If not, append it — one line, its destination, its gate — before the next tool
call. Storage is cheap; recall is not.

## A queue whose statuses never advance cannot be prioritized

**A backlog's credibility is a single number: how many rows move to a terminal state without a human
pushing them.** Measured on one queue of 111 rows — 12 `in_progress`, and **nine of those said
`SHIPPED` / `BUILT` / `LANDED` in their own note text.** The rows were not wrong about the work; they were
wrong about the state, and a list that cannot say "done" cannot say "next" either.

**Nothing in the queue writes a status, so statuses only ever move when someone remembers.** That makes
`in_progress` a parking space rather than a claim, and it is the reason a user asks *"what haven't we
started?"* about work that is half-finished and *"did we drift?"* about work that was never listed.

### Count the four populations separately before calling any of it a backlog

| population | test | what it actually needs |
|---|---|---|
| **unstarted** | `pending` / `open` | a decision: start, gate, or drop |
| **unproven** | `needs-evidence` | proof, not building — a different work type |
| **unmoved** | `in_progress` whose own text says shipped/built/landed | a **truth pass**, nothing else |
| **lost** | artifact named in the row does not exist at its stated path | restore, or re-file as open |

**A queue with 47 `needs-evidence` and 17 unstarted is not "64 items behind" — it is two different jobs.**
Reporting the sum invites a plan that builds more when the bottleneck is proof.

### `in_progress` needs a THIRD terminal state: `RESTORE-FROM-SNAPSHOT`

**An artifact can be built, lost, and still be described as in progress — and that state has no name in a
queue with only open/done.** Measured: eight of nine "done" rows named scripts that existed **only** under a
recovery snapshot (`recovered-github-<date>/`), not in any live path. Calling them `shipped` claims a
deployed artifact; calling them `open` discards finished work that merely needs restoring.

- **Before advancing any status, RESOLVE THE ARTIFACT, not the note.** Search for the basename across the
  whole tree, excluding `backups/` and `.git/` — a path that fails to resolve under one root is not evidence
  of absence. *(A naive per-row path check said "0 of 6 artifacts found" on rows whose files existed in a
  different root; the negative was the checker's, not the world's.)*
- **The outcomes are different rows:** live **and invoked** → `shipped` (with the live path as the proof token) ·
  live but **nothing calls it** → `pending`, with the missing invoker named as the next action · snapshot-only →
  `RESTORE-FROM-SNAPSHOT` (with the snapshot path) · nothing anywhere → `open`, and say so.
- **A file is not a deployment: check the SCHEDULER, not just the filesystem.** Measured: a reconciliation tool
  sat in a live scripts directory marked built-and-ready, and **no cron job on any seat referenced it** — so the
  ledger it was supposed to write had never been written once. **Search the jobs file for the basename** before
  calling anything shipped; "the tool exists" and "the tool runs" are different rows, and only the second one
  produces the artifact the row promises.
- **A restore is a copy plus a test, never a rebuild.** Work that exists in a snapshot is the cheapest queue
  movement available; re-deriving it is the expensive way to produce a second, unverified version.
- **⚠️ Compare the snapshot against the LIVE copy before you call it canonical — a snapshot can be OLDER than
  what survived.** "Newer than the wipe" is not "newest." Measured: a 521-file restore was **four weeks older**
  than a 22-file live copy and was **missing two documents that existed only there** — installing it would have
  made a stale version the source of truth, silently, because the file set looked bigger and therefore better.
  Compare **file set and mtime per file**, not total size, and merge with **live winning where it is newer or
  unique**; the restore wins only where the live tree has no file at all. Write the merge rule down with the
  manifest so the next reader does not re-litigate it.
- **Count the files in a backup before trusting its name.** A directory called `vault-sweep-<date>` holding
  **0 files** is a label, not a copy — and it is the one nobody opens, so it is the one that loads the
  "we are backed up" belief. `find <dir> -type f | wc -l` is the entire check.

### A new mechanism the queue never asked for is drift — file it in the same turn

**Six mechanisms were added in one night** (audits, a sweep, a gauge, a meeting, a walk), **none of them a
queue row.** Each was individually justified and, measured against the queue, the night spent its budget on
work the backlog had never requested — while two rows marked top priority stayed untouched.

- **Add the row for a new mechanism in the turn you build it**, with its gate — otherwise the queue silently
excludes whatever the fleet actually spends its time on, and its ordering describes a fleet that no longer
exists.
- **Before building anything that is not a row, ask what it displaces.** "This is cheap" is the wrong test;
  the right one is "which queued item did not happen because this did".
- **Drift that reconnects is still drift worth naming.** If the unqueued work turns out to serve a queued
  item (an audit that cleans the catalogue a row already demanded), say so in the row rather than letting the
  queue and the work keep two separate stories.

### `needs-evidence` is the bucket that lies twice

**`needs-evidence` fills up with work nobody started, because "not done" and "done but unproven" look identical
to whoever is filing.** Measured on one queue: **47 rows in the bucket, and only 10 named an actual proof gap** —
the other **28 described an action not yet taken** ("remove it", "add a staleness check", "extend the trace",
"reconcile the ring"). That is unstarted work wearing a label that makes the backlog look half-finished when it is
simply large — the exact reason a user asks *"what haven't we started?"* while the list appears to be all in flight.

**Re-bucket by reading the row's own text, not by pattern-matching the status:**

| the row says | it is |
|---|---|
| an imperative / a next step / "needs to" / "extend" / "reconcile" | `pending` — nobody started |
| "measured", a number, a contradiction, a silent failure | **keep it here** — this is a defect with a receipt |
| "built / landed / shipped", with no live artifact | `RESTORE-FROM-SNAPSHOT` (see above) |
| a named gate (funding, a human, another row's completion) | `blocked`, with the gate written on the row |

**What survives that filter is the most valuable pile in the queue**, and it is not a build list: every row is a
**number or status that is currently untrue about money or about delivery**. Triage those separately and first —
a defect with a receipt costs minutes, and one of them quoted an `--amount 1.0` that printed SUCCESS having moved
six micro-units.

**⚠️ Re-measure before you fix. A defect recorded months ago may already be fixed and simply never closed.** One
row described a wrapper printing an instruction its own parser rejected; the restored build carried
`EXEC="--execute --yes"` and a comment documenting the bug and the fix. **Read the current artifact and try to
reproduce before writing a patch** — otherwise you "fix" working code and add a second behaviour beside the first.

## Ask the owner before you start their row

**A row is a stale claim; the owner is the live fact.** Measured on one queue: **68 of 68 open rows had no record
that anyone had ever asked the assignee**, and **26 of them belonged to a seat other than HQ.** Every one of those
rows had a status somebody guessed at, and a status nobody checked is the same evidence as no status.

**Before starting any row whose `assigned_to` is another seat, ask and RECORD the answer on the row** — who was
asked, when, and what they said. Then the row carries two facts instead of one.

- **A check-in has a shelf life.** An answer from a week ago describes a different build; enforce a short window
  (24h is enough) and require a fresh one before `--start`.
- **A check-in from anyone other than the row's owner does not count.** *Someone else's opinion is not the owner's
  answer* — a peer's summary of another seat's progress is a claim about a claim.
- **An empty answer is not an answer.** Refuse a blank note; "I am on it" with no state is a placeholder that
  blocks the next real check-in.
- **`--start` should REFUSE (exit 2), not warn.** A warning is skipped under time pressure; a refusal is the
  whole mechanism. Silence from an owner is not permission.

**Check whether they are already mid-work before you touch their files.** A seat that received a handoff is
likely already moving: its `state.db` tail and its recently-modified files tell you which rows it is on. Measured:
a seat was found investigating two of the exact defects HQ was about to "fix", having edited no files yet — so the
collision was avoidable by looking, not by asking twice.

**⚠️ A test that writes a check-in onto the LIVE queue leaves a fabricated receipt.** Exercising
`--record`/`--start` writes into the real file; remove every test-written check-in before reporting, and say you
did. A record that contains a probe's opinion is exactly the class of lie the check-in exists to prevent.

## A closed STATUS is not a completion — audit the closed rows for proof

**"N closed" is a count of status flips unless each row carries its own proof.** Measured on one queue:
**44 rows in done statuses, and only 12 carried any evidence** — and the completion registry held **zero**
matching entries, because the harvest postdated most of them. There was no second source to fall back on.

Run the check as a script over **three buckets** and report all three numbers, in this order:

| bucket | test |
|---|---|
| **proven by the row** | an `evidence` / `proof` / `verified_by` field, or a commit, tx, path or URL on the row itself |
| **proven by a record** | a matching completion-registry / completions-lane entry that itself carries proof |
| **unproven** | the status says done and nothing backs it |

- **Say what the unproven bucket IS, not what it is not.** Most of it is real work that finished before the
  proof convention existed. The finding is *nobody can check it* — and **a closed row nobody can check is
  indistinguishable from one that was quietly abandoned.** That sentence, with the counts, is the report.
- **Never backfill evidence you did not witness.** Writing `proof: "shipped"` into rows to make the number
  look better is a forged receipt, and it destroys the only signal the bucket carried. Re-derive the proof
  or leave the row unproven.
- **Decision rows are a separate bucket — do not fold them in.** `dropped` / `rejected` / `superseded` /
  `cancelled` need a stated **reason**, not proof of work; counting them with completions inflates the
  unproven number with endings that were never going to carry evidence. Report `done-status` and
  `decision-status` separately, always.
- **Match titles with a threshold and PRINT the score.** A fuzzy join that accepts a 0.4 similarity
  manufactures proof out of unrelated rows. Below the threshold the honest answer is "no match", not a
  best guess.
- **Report the delta, not just the total.** "57 closed" and "12 provable" are two different facts and the
  second one is the one a reader can act on.

## The gate pass — every open row names its gate and its release

**A queue that says "pending" 49 times without saying what would move it cannot be planned from.** The standard:
**every pending/blocked row carries a gate AND a release condition** — "waiting on X to do Y; released when Z is
true." A row that says only "blocked" is a shrug, and the next reader cannot tell what would move it.

Run the pass as a script, not an edit session, so it is re-runnable and reviewable (`--check` previews,
refuses if any target's status moved).

1. **Count the gap honestly, in two classes.** Rows with **no gate at all** and rows with **a gate but no
   release phrase** are both failures, and reporting them as one number hides the second. Measured: 31 + 15 = 46
   of 63 open, not "30 gateless."
2. **Classify by WHO releases it**, using the vocabulary already in the file, never a new synonym:
   `human` (money, a credential or account in Jordan's name, a decision that is genuinely his) · `decision`
   (ours, but a design call with a consequence) · `external` (someone else's verdict, venue or account — does
   not move by working harder) · `own` (releases when our own work lands).
3. **Write `release_condition` as an observable state**, not as an intention. "The 5 dead rows are removed and
   re-read live showing 0 dead templates" — not "clean up the catalogue."
4. **Snapshot every previous value into `gate_prev`** on each row you touch, so the pass is reversible and the
   next reader can see it was a pass and not a rewrite.
5. **Verify as a PREDICATE, re-read from disk** — `has_gate(r) and has_release(r)` over every open row — and
   print `open / fully gated / still missing`. A count of rows written is not a count of rows correct.
6. **Expect the split to move toward `human` and `external` once the gates are written.** Gates make the
   honestly-not-ours population visible, so the "we can do this" number usually *falls*. Say that out loud
   rather than presenting the post-pass split as if it were the pre-pass one.
7. **Zero placeholders, or the pass is not done.** A curated table plus a fallback entry silently fills every
   row you missed with a generic "owner must name one" gate — and a placeholdered row *looks* gated, so the
   coverage count reads complete while the queue has learned nothing. Print the ids that fell through and
   require the count to be **0** before writing. If it is not zero, go back and read those rows rather than
   shipping the placeholder: the seven rows that fall through are the ones whose text you did not read.

**A missing gate is a route to a wrong number, not a formatting defect.** The two rows that most needed one
carried "we advertise something that is not true" (`state of record OVER-reports deployed capital`; _"N weekly
503s"_) and sat in the backlog because nothing said what would close them. Price those first.

## The board is an EXECUTION surface, not a view of the queue

Mirroring the queue onto a kanban board is the right shape — the vault holds *what and why*, the board
holds *who and when* — but the board has a **dispatcher**, and several of its defaults make a naive
mirror dangerous. **Creating a card RUNS it.**

- **`kanban.dispatch_in_gateway` defaults TRUE.** The gateway process claims `ready` cards and spawns a
  worker within a tick, with no human in the loop. `auto_decompose` also defaults TRUE and fans triage
  cards into LLM-generated child cards, so a bulk load grows beyond what you created.
- **Sync creates into `triage`, never `ready`.** Triage does not dispatch; moving a card OUT of triage
  is the human approval gate, and it is one command. A sync that produces runnable work is a fuse, not
  a mirror.
- **Set `kanban.dispatch_profiles: []`** — the framework's own fail-closed claim allowlist ("an empty
  list claims nothing"). A claim-time refusal outlives any startup flag.
- **Park with `block`, never `reclaim`/`release`.** A release returns the card to claimable and it is
  re-dispatched on the next tick — so the "stop" verb restarts the work.
- **⚠️ Archiving a card's CHILDREN promotes the PARENT back to dispatchable.** A decomposer-created parent
  wakes when its children complete, and archiving counts as completion — so a cleanup pass on child cards
  re-armed eight workers seconds later. **Park the parent FIRST, then archive the children**, and re-read the
  board after any bulk archive before believing the fleet is quiet.
- **⚠️ The dispatcher reads its config at GATEWAY START, so `dispatch_in_gateway: false` is a file, not a
  behaviour.** Set it mid-session and the running dispatcher keeps claiming cards on the old value — the
  setting only takes effect after the gateway restarts, which an agent inside that gateway cannot do. Sequence:
  set the flag → **park what is claimable now** (that is what actually stops the spawn) → have the human
  restart → re-probe. Reporting "dispatch is off" on the strength of the config read alone is the exact
  defect this section exists to prevent.
- **`--idempotency-key` is NOT a dedupe key.** Repeating the same key creates a SECOND card and prints
  the same id. Dedupe by reading the board and matching a marker you write into the card body.
- **Prove the loop is off with a stimulus probe, not a config read** — post a card the dispatcher would
  claim, wait past one tick, assert nothing spawned, then archive it. The method is in
  `verification-vantage` ("A loop you disabled is not a loop you measured").
- **Read board JSON with `--board <slug>` BEFORE the verb**, and slice the payload from the first `[` —
  the CLI prints a banner line ahead of the JSON, so a naive `out.index('{')` throws away the list
  wrapper and fails to parse. The SQLite file under `kanban/boards/<slug>/kanban.db` is the authority
  when the CLI view looks empty: a CLI call can exit 0 with no output, which reads exactly like an
  empty board and would duplicate every card on the next run.
- **A worker that writes the queue back will re-serialise it.** Enforce the splice rules below on the
  write-back path too, and if a re-serialisation already happened, prove the change was formatting by
  comparing parsed rows field-by-field against `git show HEAD:<queue>` — print which rows changed and
  assert the count is only what you intended.

Once the board is safe, most of its value is still unused: `specify` (turns a vague idea into a real
spec — the bridge from Mess Hall to queue), `--completion-contract` (the task carries its own definition
of done), `request-review`/`request-changes` (review as a state, not a comment), `swarm`, `notify-subscribe`,
`link`/`--parent`, `schedule`, `attach`. Depth: `references/kanban-execution-surface.md`.

## Why This Matters

- Clean IDs make the queue readable at a glance
- Prevents confusion when discussing item numbers ("#91" when there are 17 items)
- Makes maintenance scripts simpler
- Jordan doesn't have to mentally map "item 87" to "the 4th item"
