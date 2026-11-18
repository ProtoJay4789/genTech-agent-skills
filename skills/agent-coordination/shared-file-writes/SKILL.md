---
name: shared-file-writes
description: "Use when a note has more than one writer. Snapshot first."
version: 1.0.0
author: Gentech
license: MIT
tags: [coordination, handoff, vault, concurrency, ledger, receipts, verification]
metadata:
  hermes:
    tags: [coordination, handoff, vault, concurrency, ledger, receipts, verification]
    related_skills: [checkpoint-ack, handoff-mesh, claim-provenance, verify-after-every-action]
---

# Shared-File Writes

Handoff notes, ACK returns, fleet ledgers and checkpoint files often have **more than one writer within
minutes**. The failure this skill prevents is subtle: every sentence you write is true when you write it
and false a minute later, so a careful agent produces a record that is confidently wrong — and its own
corrections then read as noise.

## When to use

- Appending a receipt, ACK, verification result or correction into a note **another seat authored**.
- Publishing a ledger of who-has-done-what across seats (who ACKed, who filed, who is blocked).
- Any note where you will want to say "I read this exact version" a few minutes later.
- Correcting a line you published earlier in the same thread.

## 1. NEVER ASSERT SAMENESS — SNAPSHOT THE VERSION

Quote what you read as an identity: **`md5 + size + mtime`**, and call it a snapshot.

```bash
md5sum "$F"; stat -c '%s bytes, mtime %y' "$F"
```

- **"The same file I verified" is a claim with a shelf life of minutes.** A shared note grows between
your read and your write — a co-writer's correction, a second receipt, a state note — and the reader
cannot tell which revision your verdict applied to.
- Write **"supersedes the copy read at <time>"** when you know it moved, and **"as of <UTC time>"** on any
roster or count.
- A size you quote is point-in-time by nature; say so once and stop apologising for it.

## 2. SUPERSEDE IN PLACE — NEVER HIDE THE CORRECTION

When your own earlier line turns out to be wrong:

- **Add the corrected line and name the superseded one** ("this line is superseded here, not deleted: at
the time it was measured it was true").
- **Do not quietly rewrite history** into a record that was always right. A record that hides its own
correction is worth less than the error it corrected, because the next reader cannot see what moved.
- **Do not leave two numbers in two files contradicting each other** — if you cited a digest or size
somewhere and the artifact changed, amend the citation where it lives.
- Re-measure after every rewrite: fixing a stamp or a sentence changes the digest you just quoted.
- **A file cannot report its own digest.** Quoting the hash or size of the note you are writing *inside* that
  note makes the sentence false the moment anyone (including you) edits it again — and the follow-up edit is
  almost always required. Put the artifact's digest in a **different** record (the completions ledger, the chat
  reply, the covering handoff) and let the artifact carry content only.
- **Never write a timestamp you did not measure.** A placeholder (`11:2x`, `15:0x`) must be replaced with a real
  `date -u` value before filing, and the value must not *precede* the file's own mtime — `stat -c %y` next to
  your stamp is the check. A stamp ahead of the file it describes is the clearest possible tell that the record
  was written from expectation rather than measurement.

## 3. APPEND WHEN THE FILE HAS OTHER WRITERS

Load-modify-save is safe only while you are the sole writer. The moment a co-writer may be active:

```bash
exec 9>>"$F"; flock 9
printf '%s\n' "$BLOCK" >> "$F"
flock -u 9
grep -n '^### RECEIPT' "$F" | tail -2      # confirm by content, not by size
```

- **One receipt per event.** Check the file for an existing receipt header before appending; a re-send of
the same event gets a confirmation in chat, not a second block on disk.
- **Once two hands are on a file, stop editing it** — switch to append-only, or move to your own lane and
point at it.
- After writing, read back by **content** (line number, header, digest), never by "the write succeeded".

## 4. LEDGERS: CONTENT, NOT FILENAMES

A roster of "who has filed" is the highest-risk artifact in this class, because a false *absence* gets
escalated as a blocked deadline.

- **Never decide presence from a filename glob.** Naming does not agree across seats — one lane writes
`DATE-<kind>-name.md`, the next `<kind>-DATE-name.md` — so the pattern that matches your own lane reports
every other writer **missing**. This produces a confident, wrong "nobody has filed".
- **Enumerate by the DATE alone, then classify by content.** `ls "$LANE" | grep -F '<date>'` catches every
name order; a pattern that also encodes the kind (`*ack*<date>*`) silently drops `<date>-ack-*.md` and
reports a false absence. Then grep each hit for its verdict line and print `size + mtime` beside it — the
file's name is not its verdict, and its existence is not its verdict either.
- **A correction from the other writer is data, not noise.** When a peer returns a number that differs
from yours, re-measure before defending: if their count is right, supersede your line and say which one
it replaced. Being corrected in a shared record costs one sentence; a wrong number that two seats now
cite costs the trust in every number.
- **Classify by content**: grep each candidate for the verdict or disclaimer it must carry, and report
`size + mtime` per file.
- **Distinguish the work-before from the verdict.** A seat often files its analysis/read first and its
formal answer minutes later; a file with the right-looking name is not the answer. Count them in
separate columns.
- **Stamp the ledger "as of <UTC>"** and re-read it just before you act on it. Rosters close while you
type; the last entry can land between your last check and your summary.

## 5. THE RECEIPT SHAPE

A receipt answers five questions in a handful of lines:

1. **What you read** — md5, size, mtime, and whether it supersedes an earlier copy.
2. **What you verified** — the claims re-measured independently, the number that settles each, and how
many confirmed of how many checked.
3. **What it gates** — what this unblocks and, explicitly, what it does not authorise.
4. **Where your own artifact is** — path plus digest, so the reader can chain to it.
5. **What you corrected** — including corrections to your own earlier lines.

## 6. STRUCTURAL CHANGES TO A SHARED TREE — snapshot first, enforce the written rule, stop on real ambiguity

Renaming, retiring or moving a **folder** in a tree other seats read and write is a different act from editing
a note: it can silently orphan mail, and the seats whose lanes you move cannot object while you type.

**Order: snapshot → classify → act → verify.**

```bash
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUPS/<change>-$TS" && cp -r <targets> "$BACKUPS/<change>-$TS"/
```

Nothing is deleted on the first pass — move it aside (`_RETIRED-<what>-<date>/`) so the change is reversible
and a record of what was there survives.

- **A documented rule the disk violates is not an ambiguity — enforce the rule.** A tree's own README is the
  nearest thing to a schema it has. Measured: an inbox README listed two seats as *"RETIRED … No inbox folder
  remains for it"* while both folders sat there holding mail, twelve days old. Retiring them was not a
  judgement call — the doc had already made it and the disk had not obeyed. **Read the tree's README before
  acting on the tree.**
- **A genuine ambiguity is where the doc is SILENT, or where two names are both in use — that one stops and
  asks the owner.** Measured: two sibling inboxes, one carrying the name the README's group list uses and the
  other carrying the name the seat actually answers to and receives the newest mail in. Both plausible. **Do
  not guess at a shared tree:** state which way you would merge it and why, then leave the mail where it is
  until the owner answers. A wrong merge is far harder to notice than a wrong note — and placement questions
  in a fleet vault belong to the lead, not to whoever noticed.
- **Distinguish "mail addressed to a retired seat" from "stale mail".** The tell is duplication: the *same*
  handoff (identical digest) sitting in four inboxes, three belonging to seats retired days earlier, is one
  note delivered to nobody four times — not four notes going unread. Reassign it per the retirement decision;
  do not re-nag it.
- **Report `N moved to <path>` plus the snapshot path**, so the next reader can diff the change rather than
  trust the sentence.

## 7. A FIELD YOU DID NOT INSPECT IS A SHAPE YOU WILL DESTROY

Record files — rosters, mappings, ledgers — are **schema'd**, and a naive assignment replaces a collection
with a scalar while producing perfectly valid JSON.

Measured: a collaborator `membership` field held a **per-group map** (`{group_id: state}`, one entry per
room). Setting it to the string `"left"` wrote a file that parsed cleanly, diffed small, and would have broken
every reader that keyed by group id — with nothing in the write reporting a problem.

- **Print the value BEFORE and AFTER, and assert the type is unchanged.** The only reason the flattening was
  caught is that the snapshot taken for the edit printed `before: {…}` next to `after: "left"`. That pair is
  the check; a parse or a successful write is not.
- **Edit the members of a collection, not the collection.** Set each key's state rather than collapsing the key
  space to a single value — the collection's shape usually encodes which rooms/entities the row applies to.
- **A shape error is invisible to a syntax check.** Validate the *shape* (`isinstance`, key set, per-key
  value domain) before writing, and re-read one consumer's expectation rather than trusting the parse.

## Pitfalls

- **A receipt that says "the same version I verified".** The most natural sentence to write, and the one
most likely to be false by the time it is read.
- **Silently editing a verdict you already published.** Move it, don't erase it: superseded, named.
- **Load-modify-save on a shared file.** One rewrite can drop a block another writer appended between
your read and your write; prefer append, and re-read when the tool warns the file moved. **That warning is
the signal, not the obstacle** — a patch tool reporting "modified since you last read it" means a second
hand is on the file, so switch to append rather than retrying the same edit against fresh bytes.
- **Filename-pattern rosters.** A glob that matches your own naming convention proves nothing about
anyone else's; it fabricates absences.
- **A near-miss path does not fail — it silently creates a STUB.** Appending to a long-lived shared file
by a remembered path can land *beside* the real one: the write succeeds, the tool reports success, and the
record you came to make now lives in a file no other seat reads. **Before appending, confirm the target's
size is the expected order of magnitude** — a few hundred bytes where hundreds of kilobytes belong is the
tell, and it is the only signal you get, because a write to a wrong path is not an error. **Resolve the
path from the tree or the seat's own config, never from memory of where the file "is"**, and read back by
content. The stub is also worse than a failure: it makes the next reader think the file was written to.
- **Treating a file's existence as its verdict.** The artifact's *name* is not its content — read the
verdict line.
- **Two receipts for one event.** Re-sends are normal (a DM fails, the sender retries); the second lands
in a file that already carries your receipt, so confirm rather than duplicate.
- **Quoting a size as if it were durable**, then reading the later, different size as a lost write. Sizes
move; digests identify.
