# Handoff closure — which block closes, and how to end an escalation honestly

Depth for the SKILL.md rule "a receipt is the cheap half, not the signature". Load this when a handoff
in your lane keeps escalating, or when you have to decide which closing block and which state word to
write.

## 1. The three blocks, exactly as the fleet checker reads them

| block | header regex the checker matches | effect |
|---|---|---|
| Receipt | `(?im)^#+\s*Receipt\b` | marks the note as **acked** — used only to split SILENT from owed |
| Agreement | `(?m)^##\s+(Agreement\|Supersede)\b` | **closes the note — never reported again** |
| Supersede | same regex as Agreement | **closes the note** |

Consequence: a note can be acked, verified, answered in words — and still be reported as owed every cycle.
That is not the checker being wrong about receipt; it is receipt meaning what the protocol says it means.

## 2. Note shapes that satisfy the checker

```markdown
## Receipt

| seat | at | doing | by |
|---|---|---|---|
| <seat> | <ISO stamp> | <what I opened and what I am doing> | <future date> |
```

```markdown
## Agreement

| seat | state | at | evidence |
|---|---|---|---|
| <seat> | acknowledged | <ISO stamp> | <the measurement that proves what I did, and the block if any> |
```

```markdown
## Supersede

| by | at | reason |
|---|---|---|
| <seat> | <ISO stamp> | replaced by `<path>` (or `no replacement / withdrawn`) |
```

## 3. Decision table — which block for which note

| the note's ask | the truth | write |
|---|---|---|
| deliverable exists and is verified | done, evidenced | `## Agreement` / `accepted` |
| deliverable exists and is live at a URL | published | `## Agreement` / `delivered` + the URL |
| deliverable blocked on a human (credential, approval, publish) | opened, verified, blocked | `## Agreement` / **`acknowledged`** + the blocker measured + the path where the unblock routes are filed |
| the request was overtaken by a newer note or artifact | nothing owed | `## Supersede` naming the replacement |
| the moment passed and nobody replaced it | withdrawn | `## Supersede` with `no replacement / withdrawn` |
| the note states no request at all | receipt only | `## Agreement` / `acknowledged` saying the note asked nothing further |

**Never** upgrade a row to make a report look clean. An `accepted` cell for an unpublished artifact is the
same failure as a printed fabricated number, and it is worse in one way: it closes the note, so nobody
re-checks it.

## 4. The escalation ladder (run it in this order)

1. **Run the checker, do not argue with the escalation.**
   ```bash
   python3 /opt/data/scripts/handoff-sla.py                              # human report
   python3 /opt/data/scripts/handoff-sla.py --json /tmp/sla.json          # rows: band + acked flag
   ```
   The row tells you the bucket: absent = closed; under `SILENT` = no `## Receipt`; listed with an age and
   `acked_on_receipt: true` = **acked but not closed**, which is the state that loops.
2. **Re-measure the note's own claims** before writing anything (file size, digest, duration). The
   closer's evidence cell is worthless if it repeats the sender's numbers.
3. **Write the weakest truthful closer.** `acknowledged` is usually the right grade for anything that needs
   a human.
4. **Re-run the checker and quote the delta** — `N notes owe a reply` → `N-1`, and the note absent from
   both buckets. That re-run is the only proof the loop stopped.
5. **If the checker and the written protocol disagree, file the defect with a tested patch** to the
   checker's owner and leave the shared script alone. Say in the finding that the patch was run against a
   real file, and what it did to the output.

## 5. The future-dated-receipt defect (a patch to propose, not to apply unilaterally)

A checker that computes age from the **filename date** and never parses the Receipt's `by` column reports a
note whose promise has not yet come due exactly like a note nobody opened — while the protocol already
names that state (*promised and missed* = a `by` date that has **passed**). Sketch, tested against a real
note (extracts the date, computes `promised >= now`, skips the row):

```python
acked = bool(re.search(r"(?im)^#+\s*Receipt\b", text))
# last cell of a Receipt row — the promised-by date
m = re.search(r"(?m)^\|[^\n]*\|\s*(20\d{2}-\d{2}-\d{2})\s*\|\s*$", text)
promised = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc) if m else None
if acked and promised and promised >= now:
    continue                      # promised, in time — not a reply owed
```

Test the pattern against the actual note before proposing it: print the captured date and the boolean.
A patch that is only asserted to work is itself an unmeasured claim.

## 6. Findings a closure can legitimately produce

- **A blocked note is not a silent seat.** The distinction the fleet keeps losing is *unread* vs *owed* vs
  *blocked on someone else*; only the first is a defect of the receiving seat.
- **A note that asks nothing still escalates** if it sits in a `-to-` lane. Report that as an over-broad
  checker, with the count of notes in that lane carrying no request.
- **Reading the checker's source is allowed and cheap.** Cite the line numbers when you report, so the owner
  can confirm in one look instead of re-deriving your reasoning.
