# Link and reachability audit — measuring whether the brain is WIRED, not just fresh

Companion to `vault-staleness-curation`. Age says a note may be wrong; wiring says whether a reader can
even arrive at it. A rename, a merge, or a deleted stub can turn a corridor into a dead end while every
claim inside it remains current, so the two audits are run and reported separately.

## What it measures — three defects, kept apart

| metric | definition | what a non-zero number means |
|---|---|---|
| **broken targets** | `[[target]]` where nothing on disk resolves | either the target MOVED (fix the link) or was NEVER WRITTEN (write it or drop the reference) — opposite fixes, so never bulk-repair |
| **orphans** | nothing points here, and it points at nothing | often fine (a dated log, a working-memory note) — report by folder, never delete |
| **dead ends** | it links out; nothing links in | reachable only by search — informational |

Also compute and print `inbound_by_link` and `inbound_by_mention` separately. Their ratio is the most useful
single output of the audit (see *Interpretation*).

## Two definition traps that make a naive version report nonsense

1. **Counting only wikilinks makes almost the whole vault look orphaned.** A vault written by agents mostly
   refers to notes by **path and filename in prose**, not by `[[wiki]]` syntax. Scoring reachability from
   wikilinks alone reported ~98% orphaned — a definition mismatch wearing the costume of a finding. **Reachability
   = an inbound wikilink OR a mention of the note's basename in another note** (tokenise each file, look basenames
   up in a set). Then check that the mention bucket is non-trivial before believing the orphan count.
2. **Resolution must try every form the writer might have used.** `[[considerations]]`, `[[Considerations]]`,
   `[[11-Mess Hall/considerations]]` and `[[../x/considerations.md]]` are one target. Try: exact rel path, with
   `.md`, without `.md`, basename, basename+`.md`, and attachments by name. Anything less manufactures broken
   links — and a false broken link costs a reader's trust in every other line of the report.

## Shape of the instrument

```python
# 1 · walk, skipping vendored/generated trees (skills CORE, node_modules, .git, archives)
#     and append-only logs (they hold historical receipts, not live references)
# 2 · index: rel path (lowercased) -> file, plus basename -> [rel paths], plus attachment names
# 3 · per note: extract wikilinks, DROP implausible ones (regex classes like [[:space:]], prose fragments),
#     resolve; count inbound and outbound
# 4 · reachability pass: tokenise every note, count basename mentions
# 5 · emit state JSON + print: totals, worst broken targets (with one example source each),
#     orphans grouped BY TOP-LEVEL FOLDER, dead ends
```

Filters worth keeping in `is_plausible(target)`: no `[`/`]`, not starting or ending with `:`, length ≥ 3, no
spaces, not a known prose word. These are what stop `[[:space:]]` inside a code sample from topping the
report as the most-broken target.

## Interpretation — what actually earns the reader's attention

- **The total is usually small and the structure is the finding.** A few dozen broken targets over thousands of
  notes means the seams are healthy; the sentence worth writing is the one about the graph ratio.
- **`inbound_by_link ≈ 0` means the vault is navigated by path.** State it plainly: every corridor depends on the
  reader knowing a filename in advance, which is why a single routing index carries disproportionate weight. This
  is a structural claim about the system, and it is more valuable than any list.
- **Orphans are only actionable per folder.** Grouped by top-level folder, the split is immediately legible:
  working-memory and handoff folders are *expected* to be unlinked; the folder holding decisions and facts is not.
  "N notes in the decisions folder that nothing points at" is a sentence the user can act on; "2,000 orphans" is not.
- **Classify the broken targets before proposing fixes.** Historic cross-references inside dated snapshots are
  history — repointing them edits the past to look tidy. Concept/tier labels that were never files are false
  positives. What is left is usually one or two real holes (a referenced page that does not exist under any name),
  and *that* is the whole to-do list.

## Prove the detector can fail — a positive control is mandatory

A link auditor that reports zero broken links has told you nothing unless it has been seen finding one.

```bash
printf '# plant\nsee [[definitely-not-a-real-note-xyz]]\n' > "$VAULT/00-System/_plant.md"
<run the audit>            # must list the target, and the plant as a source
rm "$VAULT/00-System/_plant.md"
<run again>                # must drop it, and the total must return to the previous value
```

Do the same for the orphan metric by planting an unlinked note. If the second run does not return to the first
run's number, the instrument is reading something other than the vault.

## Wiring it into the overnight chain

- **Exit 0 on findings, always** — cron engines read any non-zero as job failure; reserve non-zero for *the scan
  could not run*, and say so on stderr. A floor check belongs in the script: if the walk yields implausibly few
  notes, emit `status: FAILED` — a broken walk must never read as a clean vault.
- **Run it in the same wrapper as the claim-staleness pass**, after it, so one overnight job answers both
  questions and the single wake-up voice reports them separately.
- **State file, then a dated human page** (see the nightly-report rule in the parent skill) — the JSON is for
  consumers, the page is for the person asking "what changed in the brain".
- **Do not let a reaching audit edit the vault.** Findings route to a worklist; a read-only audit that starts
  rewriting is no longer an audit.
