# Bulk mailbox consolidation — classify, plan, preview, then archive

For requests like "delete the bills", "keep one of each statement", "get rid of everything from the
same address". This is a bulk mutation, not triage: the deliverable is a mailbox that got smaller and a
record of exactly what moved. Get the order right or you destroy financial history with a tidy summary.

## Step 1 — Census before you design anything

Measure the real corpus first, and measure it the same way the execution will:

- Count per sender, per month, with the date range.
- Look at the SUBJECTS of the top senders, not just the counts.
- Print a handful of the actual rows you intend to delete and a handful you intend to keep.

Why: the shape of the corpus decides the rule. A sender with 60 messages may be 60 dunning emails, or 5
years of statements. Those need opposite treatments and the count alone cannot tell you which.

**A count from one page is a floor, not a total.** Fetch tools cap a page (commonly 50–100) regardless of
the `max_results` you ask for, so "98 messages" can mean "98 on page one". Page explicitly, or say the
number is a floor.

## Step 2 — Resolve label NAMES to ids before filtering

Label ids are opaque and provider-generated (e.g. `Label_6`). Passing a guessed or made-up id returns a
**successful empty result** — the same response as a genuinely empty label. So:

1. List labels, map name → id, persist that mapping.
2. Filter by the resolved id or by a name query the provider supports.
3. Treat `0 results` as "empty" only when the id came from step 1.

## Step 3 — Classify the subject into three buckets

A bill label accumulates three different things. Separate them by phrase, not by sender:

| Bucket | Signals in the subject | Action |
|---|---|---|
| `STATEMENT` | statement, invoice, your bill, amount due, payment due, autopay, payment received, new balance, account summary, e-bill | candidate to keep |
| `SOLICITATION` | save, % off, offer, promo, upgrade, reduce your, pay as little as, unwrap, last chance, act now, exclusive, reward | delete |
| `UNSURE` | matched nothing confidently | **keep, and list it** |

Rules that make this safe:

- **`STATEMENT` wins when both patterns match.** A real bill that mentions a saving is still a bill;
  over-keeping is the cheap error, over-deleting is not.
- **`UNSURE` is never deleted and never hidden.** It is the bucket that catches a new template you did
  not anticipate. If `UNSURE` is a large share, the classifier is wrong, not the mail.
- Sender-only grouping is the classic mistake: one sender can send the same solicitation for months, so
  grouping by sender preserves every copy and reports success.

## Step 4 — Group by (sender, period), not by sender

If the user asks to keep "one of each", the period is part of the identity of a bill:

- Group on `(sender, month)` — or the year for lower-volume senders.
- Within a group, keep the newest `STATEMENT` as the survivor.
- Delete only: other `STATEMENT`s in the SAME group (true duplicates), plus all `SOLICITATION`s.
- **Never** apply "keep newest" across periods. Statements arriving monthly are distinct documents;
  collapsing them to one deletes a year of records in a single pass.

A sender that mails the same statement two or three times inside one week is normal, and that cluster is
what the same-period rule exists to collapse. Confirm this by printing the dates before concluding the
rule is too aggressive.

## Step 5 — Preview, and make the summary name its axis

Default to a dry run that writes a plan file containing every message id and its chosen action. Then:

- Show per-account `KEEP` / `DELETE` counts.
- **Break the delete count into its reasons**: `N duplicate statements in the same month`, `M
  solicitations`. A bare "keep 3, delete 5" reads like history loss and cannot be distinguished from it —
  not by the user, and not by you reviewing your own output the next day.
- Show sample rows from both sides.

The plan file is the artifact. The execute step must take its ids from that file, not re-derive them, so
what ran is what was reviewed.

## Exclusions that override the classifier

A bulk pass sweeps whatever happens to carry the label, and a label is not a guarantee that the mail is
the kind of thing the user thinks it is. Before executing, gate on these — they outrank every rule above.

**Look-alike Unicode in the subject = filter evasion, not a bill.** Phishing kits spell a keyword with
Mathematical Alphanumeric codepoints (`𝐂𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐭𝐢𝐨𝐧` for `Confirmation`) because naive keyword filters
compare codepoints, not glyphs. Legitimate senders do not do this.

```python
LOOKALIKE = (0x1D400, 0x1D7FF)   # Mathematical Alphanumeric Symbols

def evasive(subject: str) -> bool:
    return any(LOOKALIKE[0] <= ord(c) <= LOOKALIKE[1] for c in subject)
```

- **Exclude these from every bulk mutation and surface them to the user by sender, subject and date.**
  Archiving a fraud attempt buries evidence and can silently extend the attacker's window.
- Two different subdomains of one brand sending the same forged subject on the same day is the tell —
  report it as a phrase ("two `asahi.com` subdomains sent forged receipts"), never as a count.
- This is a *keep and report* bucket, not a *keep quietly* bucket. A classifier that puts suspected
  phishing in `UNSURE` and says nothing has hidden the most important thing it found.

**Anything older than the stated scope is out of scope even when it matches.** If the user says "last

year's bills", a 2015 bill is not included, and neither is one dated next month. Filter on the date
window the user named; do not widen it because the query happened to return more.

**A sender's unusual age or a one-off inbox arrival is a signal to look, not to delete.** Outliers in a
dense cluster (one 2015 message among fifty 2025 ones) are exactly the rows where a wrong rule does the
most damage, and they are cheap to inspect by eye before the batch runs.

## Step 6 — Execute with the reversible verb, and keep a ledger

- `archive` = remove the inbox label, keep the message. Searchable, restorable, nothing lost.
- `trash` = recoverable for the provider's retention window only.
- permanent delete = no undo. Do not implement it by default; if asked, make it a separate explicit
  change and say plainly that it is unrecoverable.

Append every action to a ledger (`timestamp, account, message id, action, ok, error`). A bulk run that
cannot explain what it did is indistinguishable from a bulk run that guessed.

### A successful write is not an effective write

**Archiving removes the inbox label. For a message that is not in the inbox, that call succeeds and
changes nothing.** So a purge can report "2,591 archived, 0 failed" while the inbox barely moves — every
number true, the implied effect false.

Measured: a duplicate purge removed 2,591 copies and the inboxes went from roughly 4,000 / 1,645 to
roughly 4,000 / 1,645. The duplicates had already been filtered out of the inbox months earlier, so the
reversible verb had nothing to remove. Duplicates were never the lever for inbox size.

- **Before the run, measure how many targets are actually IN the inbox** (`<query> in:inbox`) and state
  that as the expected reduction. "Archive N" and "inbox shrinks by N" are two different claims.
- **After the run, measure the inbox again** and report the delta. If it did not move, say so plainly —
  the messages are still de-duplicated, but the outcome the user pictured did not happen.
- **When the goal is a smaller inbox, the query is the tool**: date windows, categories and sender
  filters select what is *visible*, which is the thing the user is looking at.


## Provider mechanics are NOT restated here

This file stays provider-neutral on purpose. The concrete mechanics of doing this through Composio Gmail —
unwrapping the `data.messages` envelope, the constant `resultSizeEstimate`, `verbose:false`, page floors,
the `GMAIL_BATCH_MODIFY_MESSAGES` slug and its camelCase fields, `--account` selection — live in
`composio-toolkit-linking` → `references/gmail-tool-operations.md`. Load that when the provider is Composio;
keep this file the place for the RULES that decide what may be archived.

## ⚠️ Stop when the measured size contradicts the size you were approved for

**An approval is for the set the user saw, not for the class of work.** If the stated plan was "779
messages" and the faithful enumeration comes back **2,472**, do not execute. Say the number changed,
show the evidence that the larger set is genuine, and take a fresh go-ahead.

Measured: the 779 came from a **capped sample** (4,000 rows paged out of a deeper inbox, years counted off
that slice); the filtered query reached all of it. The rule above says a page count is a floor — the
dangerous version is a user-facing number derived from one and then quoted as a total.

- **Re-derive the number from the query that will actually run**, never from a neighbouring sample.
- **A 3× jump is not a rounding difference.** Reversible verbs lower the stakes; they do not convert an
  approval for 779 into an approval for 2,472.
- **Show one page of the real rows** as evidence the larger set is what the user expects — dates and
  senders, not a claim.
- **Only then act.** Correcting a count downward is housekeeping; executing 3× upward silently is the
  failure this section exists to prevent.

## Verification

- [ ] Census counts were paged, not taken from one page.
- [ ] Label ids came from a label listing, not from memory or guesswork.
- [ ] Sample `DELETE` rows were read and agree with the user's stated intent.
- [ ] No `STATEMENT` from a distinct period was deleted.
- [ ] `UNSURE` rows were kept and surfaced.
- [ ] Execute consumed a reviewed plan file; the write verb was reversible.
- [ ] The inbox was measured before AND after — a successful archive of mail already outside the inbox is
      a no-op, and the reduction claim matches the observed delta.
- [ ] Ledger line count equals the number of actions attempted.
