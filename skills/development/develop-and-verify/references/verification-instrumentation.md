# When the checker lies — instrumentation, sampling, and classification

Every rule here was a check that reported confidently and was wrong **about its own result**.
The code was fine; the measurement was not. These are the failure modes a verification layer
commits against itself.

---

## 1. An exit code read through a pipe is the LAST command's status

```bash
python3 script.py | tail -12 ; echo "exit: $?"      # ← this is tail's exit, not the script's
```

Measured: a job reported `exit: 0` in a status update while the script had actually exited `2`.
The `0` belonged to `tail`. The correction had to be issued to the user after the fact.

- **Run the command bare, or capture explicitly:** `set -o pipefail`, or
  `python3 script.py > out.log 2>&1; rc=$?; tail -12 out.log`.
- **Never quote an exit code you did not capture directly.** The pipeline form is the default
  shape in almost every ad-hoc command, which is exactly why it bites.
- Same trap for `&&`/`||` chains and `$(...)`: the status you see is the last stage's.

---

## 2. An HTTP body parsed with the wrong line ending returns EMPTY, silently

```python
head, _, body = out.partition("\r\n\r\n")   # HTTP/2 servers may send LF, not CRLF
json.loads(body)                              # raised → caught → returned "" with no error
```

Measured: a secret scanner reported **"143 → 0 repos, 0 files, all clean"** because GitHub
answered over HTTP/2 with LF endings, the whole 650 KB response became "headers", the body came
back empty, and the parse fell into a bare `return body`. The report read as good news.

- **Split on both:** `"\r\n\r\n" if in out else "\n\n"`.
- **Treat HTTP 200 with an EMPTY body as UNKNOWN, never as zero.** A 200 that carries nothing is
the same lie as a 404 rendered as a page.
- **A parse failure must propagate.** `except: return None` on a JSON decode is how a transport
bug becomes a clean bill of health.

---

## 3. Classify by OBSERVED BEHAVIOUR, never by keyword presence

Two measured false positives in one session, both from matching a word instead of an action:

| heuristic | what it flagged | why it was wrong |
|---|---|---|
| "job `writes` to GitHub" if `push` appears | 3 read-only jobs | one prompt contained *"never pushes, per R4"* — the keyword was inside a NEGATION |
| `+2` severity if `error` appears in the body | healthy upstream PRs | the author was describing an error *type* it handles |

- **Ask what the code does, not what the prose mentions.** For a GitHub job, grep the script for
  write methods (`-X POST/PUT/PATCH/DELETE`, `gh pr create`, …) against the API host. For an issue,
  require a **symptom shape** (`traceback`, `something: error`, `expected … got`, `reverted with`)
  and never score a PR on it — a PR is work in progress, not a cry for help.
- **A keyword inside a negation is an anti-signal.** Before counting a term, check the sentence for
  `not`, `never`, `no`, `without` within a few words.
- **Follow one level of indirection.** A job whose script shells out to another script is not
  classified by the first file alone; the write may live in the callee.

---

## 4. Instrumentation must not add the cost it measures

A rate-limit guard that called `/rate_limit` before **every** request doubled the round trips of
the job whose purpose was to reduce load. It was correct and self-defeating.

- **Cache the measurement** (a short TTL is enough) and refresh periodically rather than per call.
- **Prove the overhead is not there:** count the calls. `should be 1 for 3 fetches` is a test, and
  it takes one counter.
- The same shape appears in logging (a log line per row in a loop over 100k rows), in health checks
  (a probe that opens a connection per request), and in any "pre-flight" that repeats work the
  main call will do again.

---

## 5. "File not found" is a claim about ONE path, not about the filesystem

Measured: `build_queue.json` was reported **MISSING** — the search had looked at
`/opt/data/scripts/`, while the live file had always lived at
`/opt/data/.obsidian-vault/scripts/`. A confident, wrong finding delivered to the user.

- **Before reporting a file missing, glob for the BASENAME across the tree** and glob again from
  the vault root: `find / -name 'build_queue*.json' -not -path '*/node_modules/*'`.
- **Beware same-pathed stale copies.** A recovery/backup tree (`recovered-…-<date>/`) can mirror
  the live layout exactly, so a script that globs the wrong root silently reads a month-old
  snapshot. Resolve the canonical path explicitly rather than by search order.
- **Say which path you checked** when you report absence. *"Not at /opt/data/scripts"* is true and
  useful; *"missing"* is neither.

---

## 6. Sampling: read the total before believing a page

A bazaar with a 100-item page was **30,004 items deep**. A first query returned 100 and the
absence of our entry in it nearly became "we are not listed". The same query with a control
address returned 82 hits — proving the filter worked and the zero was real.

- **Read the pagination total** (`pagination.total`, `count`, `has_more`) before concluding.
- **Run a known-present control through the same probe.** If the control also returns zero, the
  probe is broken and you have learned nothing.

---

## The one-line summary

**Before reporting a result, ask what would make this check print a confident wrong answer —
then verify that thing.** Empty bodies, piped exit codes, negation-blind keywords, doubled
probes, and wrong-root globs all produce a *successful-looking* run.
