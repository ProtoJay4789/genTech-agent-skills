# Demand radar — reading what an ecosystem needs from its bug trackers

A bug tracker is the most honest survey ever conducted: nobody files an issue for a feature they don't want, and
they file fastest while losing money. This is the method for turning that into a ranked read, plus the two ways
the instrument lies.

## When to use

- "What does this ecosystem actually need?" / "who else is having this problem?"
- Choosing which feature to build or which service to sell next.
- Before committing to a niche, to check that the pain recurs rather than being one person's afternoon.

## Procedure

### 1 · Turn each hypothesis into a phrase query, not a keyword soup

One hypothesis per query, written as a **quoted phrase** plus `is:issue`. Quote the exact error string, hostname,
or parameter name the failure produces — those are the phrases people paste verbatim.

```python
from urllib.parse import quote
url = "https://api.github.com/search/issues?per_page=10&sort=updated&order=desc&q=" + quote(q, safe='')
```

Good queries: `"<exact_error_string>"`, `"<dead_hostname>"`, `"<header_name>"` + product name, `<product> <topic> is:issue`.
Bad queries: parenthesised OR-groups, unquoted multi-word phrases, hand-escaped strings (see pitfall 1).

### 2 · Record three numbers per query, never one

For each hypothesis keep: **total matches**, **how many of the newest N are OPEN**, and the **repo/number/title**
of the top examples. The open count is the demand signal; the total is mostly history.

### 3 · Rank by SPECIFICITY, not volume

A high total is usually contaminated by adjacent noise and agent-generated issue spam (one repo alone can carry
six figures of auto-filed issues). A **small, sharp** count is stronger evidence: if only two issues in the whole
ecosystem mention a specific error string, that error is rare — and therefore almost nobody has fixed it, and the
people who hit it are stuck alone. Six issues about a dead hostname outrank a thousand loose matches, because
dead-hostname means *a person who cannot take money*.

### 4 · Read the specific ones by name, in the thread

The ranked list is a map, not a decision. Open the handful of sharp hits and read what the person actually
needs — a fix, a recipe, or a decision. That reading is what turns a count into a product.

## Pitfalls

### 1 · A query that has degraded returns the same total for every hypothesis

**Symptom:** several unrelated queries all report the identical total (e.g. 29,573 back to back). That is not a
coincidence in the ecosystem — it is one collapsed query being run six times, and every conclusion drawn from the
ranking is fiction.

**Cause:** hand-rolled escaping (`q.replace(' ','+').replace('"','%22')…`) and/or parenthesised OR-groups, which
this endpoint mangles into a generic match. Fix: `urllib.parse.quote(q, safe='')`, quoted phrases only.

**Guard worth shipping with the instrument:** if three or more hypotheses return the same total, print
`QUERY DEGRADED — treat this run as invalid, not as a ranking` and refuse to present it. A tie of two at a small
number is legitimate (two errors with two issues each); a tie of three is a broken query.

### 2 · The instrument is the thing most likely to be wrong

Before reporting a ranking, ask what the instrument would have to look like to produce this table by accident —
then check for that shape. A broken instrument producing a confident table is worse than no table, because the
table gets quoted.

### 3 · Rate limits are per-endpoint, and search is the tight one

Authenticated search allows ~30 requests/minute; core REST allows 5,000/hour. A battery of ten queries needs a
sleep between calls and a hard ceiling in the script, not good intentions. A throttled run that silently returns
zeros reads exactly like "nobody has this problem".

### 4 · Volume counts include self-promotion and bot spam

Directory-submission posts, "please add my service" issues, and agent-filed issue floods all match product-name
queries. Exclude or discount them by title shape (`docs:`, `add`, `awesome`, `listing`) before treating a count as
demand — the same distinction as stuck-vs-advertising in lead scanning.

## Output shape that survives the next session

Per hypothesis: `failure_mode · total · open_in_sample · 3 example (repo#n, state, title) · what it means for us`.
Plus one explicit line naming how far the numbers can be trusted — the contamination caveat is part of the result,
not a footnote.
