# Operating Gmail through the Composio CLI

Linking is one problem; reading and mutating at volume is another. These are the mechanics that make the
difference between a correct census and a confident wrong answer.

## Unwrap the payload correctly, or you will report an empty mailbox

The CLI prints a stub; the actual result is written to `outputFilePath`, and **that file is itself a full
envelope**. Messages live at `data.messages` — not `messages`.

```
CLI stdout   : {successful, error, logId, storedInFile, outputFilePath}
outputFilePath: {successful, data: {messages: [...]}, error, logId}
```

Reading `blob["messages"]` yields `None`, and `len(None or [])` is `0` — **indistinguishable from a
mailbox with no mail.** This is the single most expensive mistake in this integration: it produced a
confident "0 inbox messages" for an account holding thousands.

```python
def unwrap(j):
    """(messages, error). Never returns 0 for 'could not read'."""
    if not j.get("successful"):
        return [], str(j.get("error"))[:140]
    blob = j
    if j.get("outputFilePath"):
        blob = json.load(open(j["outputFilePath"]))
    data = blob.get("data") if isinstance(blob, dict) else None
    if isinstance(data, dict):
        return (data.get("messages") or []), None
    return [], "no data.messages in payload"
```

**Every fetch helper must return `(rows, error)` and the caller must print the error.** A helper that
swallows the failure and returns `[]` is how a parsing bug becomes a reported fact.

## Get counts from the profile, not from a search

`resultSizeEstimate` on a search response is a **constant placeholder** in some responses — identical for
every query, including mutually exclusive ones. If two different filters return the same number, that
number is not a count.

For a real total, call the profile tool and read `messagesTotal` / `threadsTotal`. For a filtered count,
page to exhaustion and count the rows.

## Never derive a scope count from a capped sample

Paging N pages and then computing statistics over that slice reports the slice, not the mailbox — and the
number looks exactly like a measurement. Measured: a 4,000-message page-through of a deeper inbox produced
a year histogram reading *779 messages before this year*; the same question asked as a filtered query
(`in:inbox before:<Y>/01/01`) answered **2,472**. The answer given to the user was three times too small,
and it was used to size an approval.

- **Ask the search engine the scope question directly.** `query="in:inbox before:YYYY/01/01"` paged to
exhaustion is a total; a year histogram over an arbitrary slice is a guess wearing a number.
- **Say which you did.** "Paged 40 pages and counted" and "queried the whole scope" are different claims.
- **A stopping condition is not an ending.** `while pages < CAP` that exits on the cap has measured a
  floor; exit on `nextPageToken is None` to have measured a total.
- **`before:` and the message's own timestamp can disagree.** The search operator is the authority on
  scope (it is what the user's filter will match), so decide inclusion with the operator and never
  re-derive scope from header dates.

**If the real figure is materially larger than the number the user approved, stop and re-confirm.** A
reversible operation at three times the authorised size is still not the authorised operation.

## Filter, and turn verbose off, before asking for a page

A mailbox without a query can exceed the tool's response ceiling and fail with
*"The tool response payload is too large"*. That arrives as `successful: false`, and only after correct
unwrapping does it read as a failure instead of a zero.

- Pass `verbose: false` — it is roughly a 75% payload reduction and keeps sender/subject/date.
- Always pass a `query`: Gmail operators work (`label:`, `in:`, `is:`, `before:`, `after:`, `from:`).
- Keep pages small and page explicitly; a page is a floor, not a total.

## Look up the tool slug; never compose it

An invented slug fails as `Tool <NAME> not found` on **every** call — a 100% no-op that writes nothing
(safe, but it burns a full run and looks like the action ran and failed).

```bash
composio search "add or remove label from gmail message archive"   # get real slugs
composio execute <SLUG> --get-schema                               # get real field names
```

Mutating Gmail labels is **`GMAIL_BATCH_MODIFY_MESSAGES`** — there is no per-message `MODIFY_MESSAGE`
tool. Fields are camelCase: `messageIds`, `addLabelIds`, `removeLabelIds`, up to 1,000 ids per call.

```bash
composio execute GMAIL_BATCH_MODIFY_MESSAGES --account <id> \
  -d '{"messageIds":["<id>"],"addLabelIds":[],"removeLabelIds":["INBOX"]}'
```

Removing `INBOX` is archive: the message survives, keeps its other labels, and stays searchable.

## There is NO unsubscribe action

The Gmail toolkit (~9 actions) has no unsubscribe verb. A search for "unsubscribe" returns a mail-vendor
toolkit whose action removes profiles from *that vendor's own* lists — it cannot unsubscribe an inbox
from a third-party sender, and calling it does nothing to the mailbox. Do not promise unsubscribing
from inside the toolkit.

The real mechanism is the **`List-Unsubscribe` header** on a received message: fetch it, call the URL
once per sender, and confirm. **Never click the body link in unsolicited mail** — to a spammer it is a
liveness confirmation and buys more mail. State that distinction when recommending it, and never run
unsubscribe against anything that reads like a stranger or a scam.

## Deduplicating a mailbox: classify the SUBJECT, not the sender

Grouping by sender and keeping the newest is the intuitive rule and it is wrong for real mail. Two
failures, both measured on the same mailbox:

- **A sender's duplicates may be an advertisement campaign.** 62 messages from one lender were 51 copies of
  *"ask for a reduction on your … balance"* — a dunning pitch, not statements. "Keep one per month" preserved
  nine copies of the same ad and called it consolidation.
- **A sender's many messages may be distinct statements.** Eight messages from one bank arrived in clusters of
  three inside the same month (days 4/8/12) — three re-sends of ONE statement. Keeping only the newest across
  all eight would have deleted genuine monthly history.

So bucket by **what the subject says**, then apply the period rule only inside a bucket:

| class | test | action |
|---|---|---|
| **STATEMENT** | statement, invoice, amount due, payment received, autosave/autopay, new balance, e-bill | keep ONE per sender per period |
| **SOLICITATION** | save, % off, offer, promo, upgrade, reduce your, pay as little as, last chance | delete regardless of count |
| **UNSURE** | nothing matched | **never touched, always listed** |

- **Group key is `(sender, period)`, and the survivor is the newest STATEMENT inside that group.** A second
  statement in the SAME period is a genuine duplicate; one per period across periods is history.
- **UNSURE is the safety valve, not a failure.** Anything the classifier cannot place is kept and shown, so a
  gap in the patterns costs a missed deletion instead of a wrong one.
- **State the deletion AXIS in the summary.** `keep 3 · delete 5` reads like shredded history; `5 duplicate
  statements in the same month, 0 solicitations` reads like what happened. Measured: the ambiguous form made the
  author misdiagnose their own correct logic and "fix" it into a no-op. Report the axis, or the number is
  unreadable even to the person who wrote it.

## Prove one message before the batch

Mutate a single id, then read it back and confirm three things: the message **still exists**, `INBOX` is
**gone from its labels**, and the subject/body are **intact**. Only then run the bulk call. A batch that
starts without this check has no evidence that the verb means what you think it means.

## Success is not effect: measure the thing the user asked about

A batch that returns `successful: true` proves the calls were accepted, not that the mailbox got smaller.
Removing `INBOX` from a message that was **already outside the inbox** is a no-op that reports success.
Measured: 2,591 "archived" duplicates barely moved an inbox, because most were already archived.

So verify against the user's own metric — re-run the same query the user would use (`in:inbox before:X`,
`in:inbox`, a sender count) after the run and report the before/after. A ledger of successful API calls is
not a receipt for the outcome.

## Bulk-mail safety: protect by MEANING, not by brand

Deleting at volume needs a wall, and the wall must key on what a message *says*, not who sent it.
Protecting a whole domain (a bank, a card issuer) also protects its **advertising** — measured: a
sender-based wall kept "a special opportunity" and "get paid 2 days early" while the actual security
alerts were what needed saving. Protect on subject semantics instead:

- **never bulk-archive:** password / sign-in / verification / fraud / dispute / statement / payment-due
- **never bulk-archive:** anything from an unsolicited or throwaway domain
- **duplicates of a security alert are not duplicates.** Six "password reset" mails are six separate
  attempts; collapsing them to one destroys the record. Grouping by subject finds them; meaning must veto.

## Look-alike Unicode is a phishing signal, not a formatting quirk

A subject that mixes plain Latin with Mathematical Alphanumeric codepoints (U+1D400–U+1D7FF, e.g.
`C𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐭𝐢𝐨𝐧`) is filter evasion. Legitimate senders do not do it. Detect it and **exclude those
messages from any bulk action** — a phishing attempt is evidence to keep and show the user, never clutter
to sweep away.

```python
def lookalike(s):
    return any(0x1D400 <= ord(c) <= 0x1D7FF for c in s)
```

## Multi-account selection

`--account` takes an alias, a word id, or a `ca_…` connection id. Two connections reading `ACTIVE` proves
nothing about which mailbox each points at — call the profile tool per account and compare `emailAddress`,
`historyId` and `messagesTotal` before treating them as distinct.

## Labels are opaque ids

List labels and map name → id (`Bills` may be `Label_6`). Filtering by a guessed id returns
`successful: true` with zero messages — the same shape as an empty label.
