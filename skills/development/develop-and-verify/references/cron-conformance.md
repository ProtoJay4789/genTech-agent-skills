# Applying develop-and-verify to scheduled jobs — tier first, then conform

A cron job is an artifact with the same failure classes as code, but the parts of the method that apply differ
by WHAT IT READS. Applying the whole checklist to every job is theatre; applying it to the right ones is a
standard with an edge.

## 1 · Tier by source, not by importance

| tier | what the job reads | what it needs |
|---|---|---|
| **A — NEED** | a network it does not control, or a **shared external quota** | identifying `User-Agent` · throttle treated as a boundary, not a transient · the words `INCOMPLETE` / `UNREACHABLE` when it could not look · prose gate if it prints advice · explicit write opt-in if it writes |
| **B — BENEFIT** | local files/state only, but **prints numbers a human acts on** | the one universal rule: a missing input prints `UNKNOWN` / `NOT RUN`, never `0`. Prose gate only where it recommends an action |
| **C — NEITHER** | local, mechanical, self-verifying (backup, sync, sweep, restore drill) | **nothing. Leave it alone.** Its failure is visible on its own face; a UA and a throttle guard here are decoration |

**State the tier per job, in a durable register.** A rule applied to 38 jobs is ~20 acts of theatre; applied to
the 14 that read outside the host it is real maintenance.

**Graduation trigger:** a Tier C job becomes A or B the moment it grows a network call or a human-facing
recommendation. That is the trigger — not a schedule, not a rewrite of stable jobs.

## 2 · Measure the file that ACTUALLY runs

Half of a mature fleet's cron "scripts" are two-line wrappers that exec a canonical `.py` elsewhere. A grep of
the wrapper reports "no network, no UNKNOWN" — **true of the wrapper, false of the job.** Measured: a naive pass
found 8 network jobs; resolving wrappers found 14.

```python
# follow a wrapper to its target before judging it
if len(txt.splitlines()) < 40:
    for target in re.findall(r"(/opt/data/[\w./-]+\.py)", txt):
        if os.path.exists(target):
            txt = open(target).read(); break
```

**And follow imports.** A job that calls `shared_transport.gh_get()` inherits the transport's `User-Agent`. A
per-file grep calls that a gap and manufactures a finding. Check `import <mod>` / `from <mod> import` and read
the module before reporting the absence.

## 3 · The instrument itself is subject to the audit

Two ways a conformance checker lies, both measured on the first run:

- **Vocabulary.** It looked for `UNKNOWN` and marked a job a gap for printing **`ABSTAIN — lane UNMEASURED`**,
  which is *better* wording. Match a set: `UNKNOWN|NOT RUN|INCOMPLETE|ABSTAIN|UNMEASURED|could not|cannot|couldn't|unavailable`.
- **Scope.** It checks one file and reports the answer as the world. Resolve wrappers and imports first (above).

**Fix the instrument before accusing the code.** A checker that manufactures gaps trains its reader to ignore it,
which is the same outcome as having no checker.

### Three more ways an instrument lies — all caught by RUNNING it, none by reading it

- **A record that carries only an ID cannot be classified — and printing it as `UNCLASSIFIED` is an ABSENCE
dressed as a finding.** Measured: a second-order analyser read a seen-state holding bare URLs, could not match a
single one against the evidence table, and reported **36 "new failure modes"** — the loudest and least true number
of the run. **Rule: before reporting a bucket, assert the INPUT carries the fields the classification needs; if it
does not, print `UNKNOWN — N records, none carry <field>` and exit 2.** A bucket named `UNCLASSIFIED`/`OTHER`/
`MISC` is the shape that hides this, because it looks like a result.
- **An accumulating register must be IDEMPOTENT.** A register that does `total += n` on every invocation doubles
every row the second time the same input is seen — and a cron runs twice for reasons that have nothing to do with
new data (a manual run, a retry, a second host). **Keep a dated ledger (`seen-by-day.json`) and RECOMPUTE totals
and first-seen from it every run.** Prove it by running twice on unchanged input and asserting the numbers did not
move; a register nobody has run twice is a counter, not a measurement.
- **An artifact the NEXT job depends on must be written unconditionally, not behind a flag.** Measured: a scanner
exported its findings only under `--json`, the scheduled job never passed it, so the only durable trace was a
URL→timestamp map with no text — and every downstream reader was blind while the job reported success.
**Default-on the dump, print the path when the write fails, and verify by `ls -l` after a plain run** (a dump
whose mtime predates the run is the same as no dump).

## 4 · Boundary ≠ finding (the class that hides in every monitor)

A job that reads this host's own Cloudflare-fronted gateway gets `403`/`429` from the edge. The naive handler
records **"down"**, **"0 served"**, or **"drifted"** — a throttle reported as a fault.

- **`except HTTPError` must branch on `403`/`429` (or `retry-after` / `x-ratelimit-remaining: 0`) BEFORE it
  classifies.** Print a boundary and mark the run incomplete.
- **A failed fetch must never enter a comparison.** Measured: `live = ""` on fetch failure, then `local != live`
  counted the target as **DRIFT**, and an `--apply` flag would have redeployed a page that was never wrong.
  Keep an `unverified` bucket, and print it as its own column: `2 in sync · 0 drifted · 1 UNVERIFIED`.
- **A throttle is a boundary, not a transient.** Honouring `Retry-After` once is legitimate; retrying a
  `429` with `remaining: 0` is how a cron turns a warning into a suspension. Stop, say INCOMPLETE, leave state.

## 5 · Shared quotas are per TOKEN, not per agent

Several seats on one host often share one credential, so one job spending the budget throttles every other
seat — and nothing in the fleet says so. Keep a **daily ledger page** that reads the provider's own number:

- `GET /rate_limit` per token → core / search / code_search / graphql + reset.
- The provider's usage endpoint for model spend (rolling / weekly / monthly) — **never a local count of calls.**
  Our count is not their count, and a drifting counter is a confident lie.
- **Name the real binder.** Core 5,000/hr is generous; `search` 30/min and `code_search` 10/min are what
  actually get throttled. A code-search loop is the risk, not REST.
- **A missing key is not "plenty left".** Report `NOT CONFIGURED` / `PLACEHOLDER` / `REJECTED` / `USABLE`.

**A `/models` list answering 200 is not proof a key works** — some providers serve it anonymously. **Prove a
credential with one real completion**, then say which of the four states it is in.

## 6 · A watcher that can fix should fix

If the platform exposes a repair command, the job calls it and reports the action taken instead of asking the
human to do it manually. But keep the wording exact when the repair is **asynchronous**: *"requested — applies on
its next turn (not yet observed)"*, never "fixed". The request is not the result; name the observation that
would prove it (a changed hash, a new timestamp) and let a later run confirm.

## 7 · A detector that declines should also LEARN — the refusal is the payload

A scanner whose negative branch is *"no evidence of ours — do not reply"* throws away the most valuable thing it
produces. **Every issue it declines is a failure mode we have never paid for.** Give the job a second output that
keeps the refusals:

1. **Classify every surfaced item against the SAME evidence table the first job decides with** — one source of
truth, imported, never a copy. A second hand-maintained pattern list drifts and then disagrees with the thing that
actually gates behaviour.
2. **Write a durable REGISTER, not just a dated page:** failure mode · first seen · times seen · *do we have
evidence?* A dated page answers today; only the register answers *"what should we learn next"*, which is the
question a later session actually asks.
3. **Carry an explicit update rule into the file:** when we acquire evidence for a mode, it moves into the
scanner's table and the register marks it. **The table and the register must agree** — two lists of the same fact
that can disagree is the divergence the whole skill exists to prevent.
4. **Name the unknown bucket honestly.** A classifier that cannot recognise a shape must say so rather than
forcing a label; count it and print it, because a growing `UNKNOWN` row is itself the signal that the taxonomy is
stale.
5. **Wake the human only on a NEW mode**, not on the daily list — otherwise a monitor that found nothing new is
noise, and a monitor that found something is indistinguishable from one that did not.

**Why this is the cheapest learning in the fleet:** the failure mode was measured by someone else, on their
money, and reached us for free in a public issue tracker. The only thing we must supply is the discipline to keep
the refusals instead of discarding them with the reply we chose not to send.

## 8 · The report shape

- **Silent when clean**, speak only on a gap — and print the gap with the job name and the missing property.
- **Instrument failure is its own line**: `INSTRUMENT FAILED — not "all compliant"`.
- **One line per job, tier letter first**, so a reader can scan 40 jobs and see the shape in five seconds.

## Cost, stated honestly (because it will be asked)

Runtime is ~zero: a header, an `if` on a status code, a branch on a missing file — no extra network calls.
The real costs are two, and neither is money:

1. **A job that can report INCOMPLETE speaks on days it used to stay silent.** Correct, but it is traffic;
   budget one threshold re-tune per silence-gated monitor.
2. **The honesty shock.** A digest that said "0 dead links" now says "0 dead links, 3 unverified". It reads as a
   regression and it is the first time the number was true — **say that in the handoff that introduces it**, or
   the reader concludes you broke something.
