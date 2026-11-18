# Success that did not happen — the silent-success family

A tool that reports success while doing nothing is worse than a tool that fails, because failure
produces a signal and success produces a decision. Every case below was read as good news at the
time. Check each before a "worked" verdict leaves your hands.

## 1. An exit code that cannot vary is not a verdict — read the OUTPUT

When a command exits 0 in every case, its status code carries no information and the only evidence
is its stdout.

```bash
# ob sync: exit 0 whether it synced or the remote is unreachable
out=$(ob sync --path "$VAULT" 2>&1); rc=$?
case "$out" in *"Fully synced"*) ok=1 ;; *) ok=0 ;; esac
```

**Require a specific success STRING, and treat anything else — including silence — as UNKNOWN.**
Record what moved (upload/download/delete lines) alongside the verdict, so a run history can
distinguish "nothing to do" from "configured at an empty remote": a sync that "succeeds" while
moving nothing for many consecutive runs is the shape of a config that looks fine and does nothing.

> Corollary: `cmd | tail -5; echo "exit=$?"` reports `tail`'s status. Use `out=$(cmd); rc=$?` or
> `set -o pipefail`. This exact mistake produced a false "exit 0" report about a job that had
exited 2.

## 2. An empty body is UNKNOWN — never an empty result

A parse that fails on an empty string can land in a `return body` path and hand back `""` with no
error attached. The caller then sees `err=None` and an empty collection, which reads as "nothing
found".

```python
if status == 200:
    if not body.strip():
        return None, "HTTP 200 with an EMPTY body — UNKNOWN, not zero"
    try:
        return json.loads(body), None
    except Exception:
        return body, None          # ← silent empty lives here unless the check above exists
```

**Before a 200 becomes data, assert the body is non-empty.** Then carry an explicit UNKNOWN state
to the caller so "could not read" and "read found nothing" never render the same way.

## 3. Split ON BOTH header boundaries — HTTP/2 does not always send CRLF

A response-header split hardcoded to `\r\n\r\n` never matches a host that answers with bare `\n`.
The entire payload then becomes "headers", the body is empty, and every downstream parse yields
nothing — silently.

```python
if "\r\n\r\n" in raw:
    head, _, body = raw.partition("\r\n\r\n")
else:
    head, _, body = raw.partition("\n\n")
```

Symptom to recognise: a request that returns 650 KB and parses to `""`. **A response that large
cannot be empty — if the body comes back empty, the split is wrong before the data is.**

## 4. A validator that accepts every value is not a validator

A CLI that prints `✓ Set X = Y` has confirmed it wrote a string to a file. It has not confirmed the
string is legal.

Measured: a config command accepted a provider name that the engine's own defaults file does not
list among its valid choices, and reported success. The value resolved to nothing at runtime and the
feature failed silently for every consumer inheriting it.

**Read the enumerated legal set from the SOURCE** (`config_defaults.py`, a schema module, a
`choices=[...]`), not from the CLI's acceptance. A validator is only evidence when it can refuse.

**Sibling case:** a schema that *documents* a field and *rejects* it when sent alongside its modern
equivalent. Schema-listed ≠ accepted — bisect the field set rather than trusting the docs table.

## 5. Matching a verb in PROSE is not evidence of the action

A scan for a write operation matched the word inside a description that said the opposite — a job
whose own text reads "never pushes, per R4" was classified as one that pushes.

**Anchor the detector to the ACTION, not the word:** an HTTP method, a CLI verb with write
semantics, a call site. And when a negation can appear near the term, require the action to be
positive rather than merely present.

Same shape as counting a status code out of a timestamp: the token matched, the event did not.

## 6. A guard that checks its own budget per call doubles the load it exists to reduce

A rate-limit guard that fetched `/rate_limit` before **every** request doubled both the round trips
and the latency of the job it was protecting. Cache the value (a short TTL, say 60s) and refresh on
a threshold, never per call. **Measure the guard's own cost with the same instrument you use on the
thing it guards** — a guard is not exempt from the claim rules.

## 7. Your tool's REDACTION of its output is not evidence about the file

When a secret-looking string is masked in what a tool *shows you*, a failed string match against the
masked form is a fact about the display, not the artifact. Measured: three attempts to `replace()`
a masked token in a file failed while the file held the real expression the whole time.

**Verify against BYTES before concluding a file is wrong:**

```python
raw = open(p, "rb").read()
print(b"the-real-form" in raw, b"the-masked-form" in raw)   # the file, not the view
```

**A failed search on a redacted view proves nothing.** Scope the claim to what you actually read —
"absent from the rendered output" is not "absent from the file".

## 8. A page of results is not a total

When a paginated endpoint returns a round number (100, 50, 25), read the pagination envelope before
treating the page as the population.

```bash
# the negative you are about to report may be true only of page 1
curl -s "$API?limit=100" | jq '.pagination.total'
```

Measured: 100 items out of **30,004** was nearly reported as "not present in the catalog". **State
the denominator whenever the number came from a page.**

## The pair that makes a negative trustworthy

Before reporting that something is ABSENT from a filtered or searched collection, run one input you
know must MATCH through the same probe:

- filter returns the control → the filter works, and the negative is real
- filter returns nothing for the control either → the filter is inert, and the search never happened

**Prove the instrument can produce a positive before you trust its negative.** Two separate
instruments, or two deliberately different inputs, or you have an assumption wearing a result.
