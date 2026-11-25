# SLA instrument traps — when the checker and the queue lie about the same note

Four ways an escalation reports work that is not owed, and the measured test for each. Run them in this order
before answering a repeat.

## 1 · The human listing is a truncated slice

Most SLA checkers print a **capped** number of rows (commonly the first 8) under a total that counts all of them
(`57 note(s) owe a reply`, then eight lines). Grepping that output for your seat returns nothing and reads as
"my lane is clear" — the total and the listing disagree, and nobody notices because both are plausible.

```bash
# WRONG — greps a truncated listing
audit.py | grep -i '<seat>' || echo 'lane clear'

# RIGHT — read the machine output and count rows yourself
audit.py --json /tmp/audit.json >/dev/null
python3 -c "import json;d=json.load(open('/tmp/audit.json'));r=[x for x in d['rows'] if x['owed_by']=='<seat>'];print(len(r),'owed');[print(' ',x['age_days'],'d',x['note']) for x in r]"
```

- **Never state a count from a console listing.** The `--json` sink exists for this; if the tool has no JSON mode,
  compare the printed row count against the printed total and say the list is truncated.
- **"Lane clear" is a claim with a denominator.** Either quote `N rows with owed_by == <seat>` or do not say it.

## 2 · The buckets are not "open" and "closed"

The bands are typically `SILENT` (nothing read it) and `OVERDUE/ESCALATE` (read, still owed). A `## Receipt` moves a
note from the first to the second — it does **not** remove it, because a receipt is not a closer. A single
`--no-nudge` run showing the note absent from `SILENT` therefore says nothing about whether it is owed.

- Test the closer, not the band: `grep -cE '^## (Agreement|Supersede)' <note>` ≥ 1 = closed.
- A note that is genuinely blocked on a human still needs a closer (`## Agreement` with `acknowledged` + the block
  measured); leaving it in the overdue band manufactures a debt that only a signature would clear.

## 3 · The queue replays a message whose note is already closed

The nudge transport is durable on purpose: a failed delivery is spooled and retried by a timer. **The retry never
re-reads the note's state**, so a message queued while the note was open keeps arriving after it is closed — three,
five, seven times, each identical.

```bash
python3 <scripts>/peer-dm.py --status     # one entry, attempts=N, queued_at EARLIER than your closer
grep -n 'queued_at' <spool.jsonl>        # compare that stamp with the mtime of your closing block
```

- **The discriminator is the stamp, not the text.** `queued_at` before your closer's mtime = a replay, and re-answering
  it changes no bytes.
- **Remove the one obsolete entry, keep a copy** (`cp <spool> <scratch>/spool-removed-<topic>.jsonl`), then verify
  `--status` prints empty. Deleting without the copy destroys the evidence that the loop existed.
- **Never delete other seats' entries** in the same file; filter by seat and topic.
- **Propose the upstream fix, do not patch the fleet mid-thread:** a flush should re-run the SLA check and drop
  entries whose note now carries a closer.

## 4 · The escalation is a NEW event wearing the old note's name

A sender can re-issue the same filename with a new internal stamp (a new checkpoint, a re-sent brief, a re-opened
request). Before treating a repeat as a replay, diff the file: `stat -c '%s %y'`, `md5sum`, and the `Issued:` /
`Date:` line. Same name + new stamp = a new event and a new answer; identical digest = a genuine replay, answered
with the existing artifact's path and digest.

## The order that saves a round

1. Does the note carry a closer the checker parses? (No → write one, with the weakest honest state word.)
2. Does `--json` list it against you? (No → stop; the escalation is stale or replayed.)
3. Is there a spool entry with `queued_at` before the closer? (Yes → one replay, remove it.)
4. Is the return note in the lane the matcher looks for? (Alias/name-form trap — `handoff-mesh` documents it.)
