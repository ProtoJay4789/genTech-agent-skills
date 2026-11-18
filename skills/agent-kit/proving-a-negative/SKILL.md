---
name: proving-a-negative
description: "Use when reporting something was not found, or is clean."
trigger: "Before reporting any absence or clean result — 'no key material in any repo', 'the file isn't there', 'nothing matched', 'the sweep is clean', 'we lost nothing' — and when a read fails and you are tempted to render a default instead."
tags: [verification, absence, coverage, search, secrets, forensics]
version: 1.0.0
---

# Proving a Negative

An absence claim is a claim like any other, and it is the easiest kind to make wrongly. The failure mode
is not lying — it is running a search that **could not have found the thing**, getting an empty result,
and reporting that as a property of the world rather than of the search.

**The governing rule: a negative covers the DIMENSION you searched, not the population you walked.**
Walking every directory and reading hundreds of files says nothing about whether your selection criterion
could have matched a member at all.

## 1. Search the FIELD the target's shape implies, not the field convenient to enumerate

Filenames and paths are the convenient field. They are also the wrong one for any question about
CONTENT.

A secret's filename describes what it *does*, not what it *is*: keys live in files called `deployer`,
`rail-keys`, `bot-wallet`, `celo-rail-key` — matching no `private_key` / `*.key` / `keystore` / `mnemonic`
pattern. **An audit that enumerates candidates by key-shaped NAME and reports clean has excluded the real
key by construction.**

Select on the value's SHAPE instead: grep every text file's content for the pattern class, then classify
hits by structure.

| question | wrong field | right field |
|---|---|---|
| is there key material here? | filenames matching key words | content matching key SHAPES (bare 64-hex on its own line, `BEGIN … PRIVATE KEY`, 12/24-word mnemonic) |
| is this address published? | files named `*wallet*` | content matching `0x[a-fA-F0-9]{40}` anywhere |
| did we ever commit a secret? | filenames | blob CONTENT across `git rev-list --all --objects` |

`scripts/sweep-key-material.py` is a re-runnable content-shape sweep — run it rather than hand-rolling a
pattern list each time.

## 2. Report the PROPERTY searched, not the count of files walked

"Examined 68 repos, nothing found" names a denominator and implies a coverage it does not have. State the
property:

- ✅ **"No file's content contains a 64-hex value on a line of its own."** — falsifiable, and a reader can
  attack it.
- ❌ **"No key-shaped filenames were found."** — a much weaker, different claim wearing the same words.
- ❌ **"Scanned 6,970 files, clean."** — a count is not a criterion.

If your report gives only a number, the reader cannot tell which question you answered.

## 3. Enumerate the population — and treat anything unreadable as UNCHECKED, not empty

When the claim spans several owners, namespaces, accounts, or stores, list them explicitly and count the
ones you could not open.

- **An unreadable store returns an empty result indistinguishable from "nothing is there".** A namespace
your credential cannot read, a permission-denied tree, an empty-looking directory — each is an **open
door, not a clean one**. A secret can be read as "not present" by the exact mechanism that hides it.
- **Confirm the scope of your own credentials before trusting their output.** Which account does this
token actually belong to? One API call returns **one owner's** list; a personal account or sibling org is
a separate call and may be invisible. Enumerating 68 repos on one account is 68 of *that account's* repos.
- **Do not start from a hand-written list of "our repos/servers/keys".** Such a list is a memory of what
  someone remembered, and it is precisely where the forgotten member lives. Derive the population from the
  source of truth and diff it against the remembered list.
- **A negative about a REMOTE surface is the same rule, and it fails the same way.** There the population is
  whatever the system **itself publishes** — `openapi.json`, a `.well-known/` discovery doc, a manifest, a
  `services[]` catalogue. **Probe the DECLARED items, not a path list you invented.** A hand-written path
  list is a guess about someone else's API, so a `404` from it is evidence about your guess and says nothing
  about the service. Read the published list first, then probe it; **if no list is published, report the
  enumeration as incomplete rather than reporting absence.**

### Enumerate from the INDEX of the population, not from the files you happened to open

The cheapest way to make a false clean claim is to open two members by hand and generalise. Measured: a repo-wide
"this address appears nowhere else in the Markdown" was asserted after checking **2 of the repo's 30 Markdown
files** — the address was in a third one, in the section people copy from, and an outside reviewer found it in
minutes. **The claim was true of the scope and false of the world.**

1. **List the population first** — the tree/API index, the directory walk, the declared catalogue — and hold its
   count. `30 Markdown files` is a scope you can defend; "the docs" is not.
2. **Loop over that list**, fetching each member, even when two look sufficient. The loop is also what makes the
   claim re-runnable later.
3. **State the denominator in the sentence**: "of the 30 Markdown files in the repo, zero contain it" — a reader
   can then attack the denominator instead of guessing at it.
4. **When someone reports a hit you did not see, suspect the CLOCK before the claim** — a raw-content CDN can
   serve pre-commit text while the commit-aware API at that ref is already clean, so name the instrument each of
   you used before either calls the other wrong. **The same holds for the QUERY, not just the clock:** two people
   can ask the same endpoint family with different selectors and both be right. Measured, one check counted **30**
   pairs from a token-address lookup and the other **14** from a free-text search for the same symbol; the
   contradiction was published as "one of these numbers is wrong" and neither was. **Reproduce with the exact
   request the other side ran before contradicting it** — a number is only wrong relative to a stated question,
   and a pair-count (like a result-count) must never become a constant in a spec, because it is query-dependent. The full rule (including the contents-API form that settles it)
   lives in `claim-provenance` under *"a repair inherits the claim's surface"*, together with the sibling case —
   a doc naming a mechanism no code implements. Do not restate it here: read it there before disputing a fix.

### A walk that prunes by SUBSTRING can prune the whole population

Path filters written as `if "/skipme" in root` also match the ROOT itself when the root's own path
contains the token. A tree at `/opt/data/.vault` filtered on `/.vault` walks **zero** directories and
returns a clean zero — which reads exactly like a verified empty result.

- **Compare path COMPONENTS, not the joined string:**
  `parts = set(os.path.relpath(root, base).split(os.sep))` then `if parts & {"node_modules", ".git"}`.
  Relpath first, so the root is `"."` and cannot match its own exclusion token.
- **Sanity-check a suspicious zero against an INDEPENDENT form of the same question** before reporting
  it — a second script, `search_files (target='files')`, or anyone else's count. A zero that disagrees with an
  independent count is an instrument fault, not a finding.
- **Name the COUNTING UNIT in the claim.** "47 empty folders" was counted at the top level only; the
  same question at any depth was 158, and 2,671 tree-wide. *Folders directly under X* and *directories at
  any depth* are different populations with a threefold gap — say which one you counted, or the reader
  silently supplies the other number.

## 4. Never let a failed read render as a value

An unknown that displays as a number is a fabricated measurement, and it is worse than a blank because it
looks like data.

- **`.get(key, default)` does NOT apply its default when the key EXISTS with a `None` value.** A failed
price fetch then flows onward as `None` and either crashes the renderer or prints as a placeholder. Guard
the value (`if x is None`), not the lookup.
- **`AVAX: $0.00` is not "unmeasured" — it is a false zero.** Reserve a distinct representation for "I
could not measure": an explicit `UNMEASURED` / `None` / read-failure code, never `0`, never an empty
string, never a default.
- **Separate "I could not measure" from "I measured and the answer is no."** They must not share an exit
code or an output shape; a consumer cannot otherwise tell a refusal from a failure.
- **A `0` default on a numeric field is a lie waiting for a failure.** Prefer no default and a loud error
  over a silent plausible value.

### A measured ZERO can be a units fault — check the field name and the window before believing it

A zero that came from a real read of a real source is still not a finding until the arithmetic behind it
is checked. Two mechanisms account for most false zeros, and both survive every "did the read succeed?"
test because the read DID succeed:

- **The summary sums a key the reader never sets.** A collector writes `amount`; the aggregate reads `usdc`
  and gets `None` for every row, which sums to `0.0` — a permanent, confident zero that no payment can ever
  move. **Grep the aggregation for the exact key the row-builder emits**, and when a helper produces rows for
  several callers, emit the canonical key as well rather than fixing one consumer and leaving the next one
  broken in the same way.
- **A window is computed from an assumed constant, not a measured one.** A "last N days" window derived from
  a blocks-per-day or rows-per-hour constant inherits that constant's error and reports a *smaller* period as
  if it were the requested one. Measured: a chain's real rate was an order of magnitude above the assumed
  one, so a "7-day" window covered under a day and reported zero revenue **one day after a payment landed**.
  **Derive the rate from two real data points (a known event's position and its timestamp) and record the
  measured value next to the constant** — and treat any zero whose window is shorter than the event you know
  happened as a window bug, not as an absence.

**The tell for both: the number is zero while an independent source says otherwise.** That disagreement is
never resolved by re-running the same summary — go to the rows and print the raw keys.

### A provider RANGE CAP makes the zero a REFUSAL, not an answer

When the query is a log/event scan (`eth_getLogs`, a search API, a `since`-window cursor), the provider may
refuse the range outright — max block span, max results, max page — and **an exception swallowed inside a
loop turns that refusal into an empty list.** Measured: a 30-day transfer sweep reported `0 transfers in`
while a transfer whose receipt named a block inside that window sat in the same chain. Two faults stacked:
the window was derived from an assumed blocks-per-day constant, **and** the provider capped the range so the
real query never ran.

1. **Issue a CONTROL query first: the same window, no address filter.** If the control is refused or returns
   a suspiciously round server-side cap, the instrument is broken and every filtered `0` from it is
   meaningless. A control that says *"exceeds max results, retry with range A-B"* is the provider telling you
   your window is illegal — listen to it instead of catching the exception.
2. **Never `except: pass` around a range query.** Collect the error and print it beside the count; a count
   printed without its error is a claim about a query you do not know ran.
3. **Page the range** to whatever the provider will accept, and print how many pages were actually read
   against how many were planned — a sweep that stopped at page 2 of 12 and reports `0` has measured two
   pages.
4. **Cross-check one known member.** You often already hold a receipt, tx hash or id that must appear in the
   result set. If it is absent from a "clean" sweep, the sweep is wrong — that single known member is a
   cheaper falsification than any control query.

## 5. Falsify the negative before you publish it

Prove the search can go RED the same way you would prove a guard: **plant a member of the searched class in
the artifact, run the search, and confirm it reports a hit** — then remove the plant.

- A search never watched failing is a search whose blind field you have not measured.
- **Ask what a hit would have looked like and whether your method could have produced it.** If no input
could have made it report a match, the clean result is not evidence of anything.
- **Verify by DERIVATION, not by counting shapes.** Counting key-shaped lines proves presence, not
  correctness: derive the address from the stored key and compare it to the stored address. A count of
  matches can be satisfied by fixtures and decoys.

### A filter parameter must be proved to FILTER before its zero means anything

When the endpoint takes a filter (`?payTo=`, `?owner=`, `?status=`, `?search=`), query it with a member
**the endpoint itself just returned unfiltered** as the control:

1. Fetch one page unfiltered, pull a real value out of it (the endpoint proving it contains a member).
2. Query with `?field=<that value>`. **If the result set does not shrink to a plausible subset, the
   parameter is being silently ignored.**
3. Only then query your own value. Zero, from a probe that has just demonstrated it can go non-zero, is
   a real negative.

**A silently-ignored filter returns the FULL set, which reads as "the filter found everything" and
conceals that it found nothing.** Two failure shapes to expect: a filter that echoes the full total
regardless (broken), and a filter that is honoured (working) — you cannot tell them apart without the
control. A `total=0` beside `items=0` is the working signature; an unchanged `total` is the broken one.

### A FIRST is a negative claim — and the record usually answers it before you publish

**"The first customer", "the only one", "never been done" are absence claims over the whole record**, and they
are almost always made from a partial read: the last 30 days, the file in front of you, the ledger that was
written after the thing happened.

Measured: a payment was announced as *the first outside customer*, with a chain-verified receipt, while the vault
already held a note for an **earlier payment, eleven days prior**, also chain-verified. The confirming instrument
was a `--days 30` window and the earlier event was at day 30 — so the instrument was honest, the sentence was not.

- **Before publishing a superlative, search for the earlier instance BY PROPERTY, not by label.** Search the
  identifiers (address, tx hash, id, room id), not the phrase *"first customer"* — the earlier note was filed
  under a completely different name and would never have matched the words.
- **State the WINDOW the instrument covered**, in the sentence that carries the claim. `--days 30` proves nothing
  about day 31, and a first is a claim about all of history.
- **A wider window is usually one flag away.** Run it before writing the superlative, not after someone
  contradicts you.
- **The inverse is the more useful finding: an absence of RECORDS is not an absence of EVENTS.** The same sweep
  that overturned the *first* also surfaced a payment that appeared in **no note anywhere in the vault** — one
  payer, one receipt, zero documentation. That is not "a customer nobody told us about"; it is proof that the
  record was never complete. **Report it as a documentation gap, not as a discovery**, because the next reader
  will otherwise assume the record is now whole.

## 6. When the negative is about a loss, separate existence from recoverability

"Can we get it back?" is two questions, and they have different answers:

1. **Does it still exist?** — provable now, read-only, by anyone.
2. **Is it still movable?** — needs key custody; only the holder can settle it.

"Readable forever, movable by nobody" is a complete and useful finding, and it is very different from
"gone". **Restorable ≠ recoverable:** a backup containing job *definitions* but not job *bodies* restores a
schedule with nothing to run. A manifest is not a backup — assert the payload, not the index.

## Pitfalls

- **Reading a TRUNCATED print as a complete enumeration.** A tool that shows the first `N` results
  (`sorted(x)[:6]`) renders exactly like one that shows all of them. An item missing from the visible
  slice is not missing from the set. **Before reporting that a tool missed something, read its output
  code — and settle it with a falsification test** (plant a member, re-run, confirm the count MOVES).
  *Measured 2026-10-23: a "missing" drift item was in the set the whole time; the list was sliced at six.
  The false claim reached four seats as a written rule before a test disproved it.*
- **Reading a PAGINATED response's first page as the population.** Distinct from display truncation and
  far more dangerous, because a page size is often a suspiciously round number that looks like a total.
  **Read the envelope's `pagination.total` / `total` / `has_more` BEFORE interpreting any count.** 100
  items from a 30,004-item catalogue is one third of one percent; a `0` found in it is not an absence, it
  is an unexamined population. Search the whole set (walk the offsets), or state plainly that the claim
  covers one page — never that it covers the catalog.
- **Reporting a field as missing because it was absent from the nested slice you read.** A field declared
  at the item level is not absent because the sub-object you inspected (`accepts[]`, `data[]`, `meta`)
  lacks it. **Dump the whole object's keys before calling a field missing** — a "listed but unbuyable,
  every record malformed" headline is usually one wrong nesting level, and it is the more damaging error
  because it invents a defect rather than merely missing one.
- **Calling an empty field a DEFECT without dating the field first.** A column added last week is absent
  from every row written before it, and that absence is byte-identical to a writer that never populates
  it. Measured: a log field was reported as "never written, not once, across 15 records" — every one of
  those records predated the commit that introduced the field, so the finding was history wearing the
  costume of a bug. **Establish when the field was introduced (commit comment, file mtime, changelog) and
  compare it to the age of the rows.** Older than the field = history; newer than the field = a real
  defect. Say which you are looking at, because the two verdicts point at opposite work — one needs a
  migration of old rows or nothing at all, the other needs the writer fixed.
- **Reporting an absence produced by a path/name-based search for a content question.** The most common
  form; the whole of §1 exists because of it.
- **Treating "nothing found" as "nothing there" when part of the population was unreadable.** Name the
  unreadable part in the report.
- **Reporting a clean sweep when the sweep timed out or churned on ignored artifacts.** An empty result
  from a run that did not finish reads exactly like a verified clean tree.
- **Quoting a timestamp, a count, or a directory listing as proof of a property it does not address.** A
  directory mtime is not evidence of survival; a file count is not evidence of coverage.
- **Declaring an area closed on the strength of a method you have just seen fail elsewhere.** If the
  criterion is wrong, every result from it is suspect — re-derive the earlier verdicts too, and say that
  you did.
- **Concluding a search is done because the second attempt agreed with the first.** Agreement between two
  runs of the SAME wrong method is not corroboration.
- **Adopting a NEW positive theory on the very evidence that just refuted your negative.** When an absence
  claim falls, the pull is to explain the real state from the same incomplete probe — *"no 402 anywhere, so
  the endpoints must not enforce payment."* That is a second claim resting on the first one's artifact: it
  inherits the original error while wearing the authority of a correction. **Re-derive the probe before
  theorising about cause.** A refuted negative is not a finding; it is a signal that the enumeration was
  incomplete.
- **A tool-existence check that consults only `PATH` reports absence for anything installed beside it.**
  Measured: a presence check returned `None` for a binary that was live under a sibling install root, and the
  "not installed" verdict was one line from being filed as a capability loss — the memory entry naming the tool
  was right and the checker was the broken instrument. **Enumerate the alternate install roots as well** (a
  local `bin/`, `~/.local/bin`, a per-profile venv) **and settle it by running `<tool> --version`** — a version
  string is the only evidence that the binary exists *and* executes. Then say **"present but NOT on `PATH`"**
  when that is the case: it is the whole difference between "we do not have it" and "we have it and a bare call
  will fail", and only the second one tells the next reader what to type.
- **A recovery or backup SNAPSHOT is part of the population, and excluding it manufactures a loss.** Measured:
  an artifact declared *"gone — zero hits"* was sitting in a `recovered-<source>-<date>/` tree, and a second one
  declared missing was in a vault CSV under a name the searcher never guessed. **Before saying a thing does not
  exist, search the snapshot/mirror/archive roots by BASENAME across the whole tree** — and treat a
  snapshot-only artifact as a **third state**, neither live nor lost: `shipped` claims a deployed copy, `open`
  discards finished work that needs only restoring. **Name which of the three you found**, because "it exists"
  and "it is running" are different claims and the second is the one a reader acts on.
