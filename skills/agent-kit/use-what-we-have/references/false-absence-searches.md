# False absences: the searches that invent a gap

Every one of these produced a confident "it doesn't exist" about something that existed, and each cost a
rebuild, a re-publish, or a number going backwards.

## You search for the name of the thing you are about to build

**The most common false absence is a search for the WRONG WORD: the name of the new file, which by definition did
not exist yesterday.**

Measured twice in one night, on two seats:

- A seat built `post-log.py` to fix *"we have no post record"*. It searched `*post-log*` — **the name of the tool
  it was writing** — and found nothing. The record existed as `post-log.csv`, holding three real publications with
  message ids and one verified by a platform-side id change. Its new ledger opened at **`published 0`**: the first
  act of the fix was to erase three real publications.
- HQ grepped live scripts for `rugpull|depeg`, got zero, and reported *"that job is gone."* The owner searched the
  **recovery snapshot** and found two working artifacts, one a 500-line monitor with weighted risk factors and
  severity bands. The job was not gone; the search was one directory too narrow.

**Three rules:**

1. **Search for the RECORD and the BEHAVIOUR, never for your planned filename.** Grep the concept (`post`,
   `publish`, `ledger`, `record`), the column headers you would expect (`url`, `published`, `posted`), and the
   suffix (`*.csv`, `*.jsonl`). A CSV with a header row is invisible to a filename match for a tool that does not
   exist yet.
2. **Search every ROOT, including archive and recovery trees.** `recovered-*`, `10-Archive/`, `_archive/`,
   `.retired-*` are where a working implementation goes to be forgotten, and a live-path grep cannot see them.
3. **A new record that starts at ZERO beside an existing one is a REGRESSION, not progress.** Before creating a
   ledger, register or index, print the rows the existing one already holds and state the delta. **A fix whose
   first act is to lower a count has made the reporting worse while looking like infrastructure.**

## The negative that came from the wrong namespace

A 404 from one namespace is not a negative about the others. A user account, an org account, a zone-scoped and an
account-scoped path can each answer differently for the same resource; one of them returning "no route" reads as
"no permission" and sends the user to re-issue a credential they already hold.

## The negative that came from a slice

**Read the tool's own output code before concluding it missed something.** A list truncated at the first N renders
identically to a complete one. A checker that was reported to have "a blind spot" was working correctly — its
output was sliced at six.

## The negative that came from a stale summary

**A document's own status table is a DATED measurement, not current state.** Inheriting a row re-publishes an old
absence as a present-tense fact: *"that folder has zero files"* came from a table measured two weeks earlier, while
the folder held eleven files. Re-run the row before repeating it, and mark the corrected table superseded rather
than deleting it — the old row is the evidence the thing was later built.

## The negative that came from a remembered path

**Search by FILENAME across the tree ROOT, not by the path you remember.** A correct filename under a
mis-remembered parent produces a clean, confident "missing". `find <root> -name '<file>'` is the probe; the
remembered path is the hypothesis.

---

**The general shape:** a negative claim needs a COMPLETE probe with a stated scope — *"searched the vault for the
concept, `scripts/` for the behaviour, every profile's skills, and the recovery tree; the only artifacts are X and
Y"* — and never an impression wearing a finding's clothes.
