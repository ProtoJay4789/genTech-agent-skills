# CURRENT-STATE pages — the currency layer

A vault's problem is rarely volume. It is that **a stale note and a current note look identical**. Search a
contested subject and you get six notes in arbitrary order, three asserting the old answer, one asserting the
new one, and nothing saying which wins. The fix is not consolidation (merging thousands of notes fixes nothing
and risks the evidence trail). The fix is a **ranked, machine-checked statement of what is true now**, one per
lane, with everything else demoted to evidence.

## The shape

```
<LANE>/CURRENT-STATE.md      the only file an agent may treat as current
  **Updated:** YYYY-MM-DD
  … Source of truth: `state/<lane>-state.json` …      <- a file that EXISTS and carries generated_at
state/<lane>-state.json      every field MEASURED by a generator, null + reason where a probe failed
```

- **One page per lane that owns state.** A lane without one answers *"what is our current state?"* by grepping
  and getting an arbitrary order.
- **The page summarises; it never originates.** If it and the JSON disagree, the JSON wins and the page is wrong.
- **The generator is not optional and not manual.** Write it before the page. A page with no machine source
  drifts the moment its author stops rereading it — which is precisely how the one page whose own title was
  *"the one note that must never go stale"* came to be wrong in three places at once, including asserting both
  *"configured, not yet sitting"* and *"the exam is sat"* on the same page.

## Prose is not data — the rule that outranks all of these

**A decision recorded in a note is not applied until the file the engine reads changes.** Measured: a deferral
was written into two audit notes, and a self-test even asserted *"`hard_dates` for C1 were cleared"* — while the
JSON still carried both dates **on every seat**. The engine kept printing a live countdown, a seat reported it,
and it was relayed to the user as fact.

- **A self-test that claims a state without reading the file is the same class as a job reporting
  `last_status: ok`.** It asserts something it never measured.
- **Retire, do not delete.** Move the rows to `retired_dates` with the reason and the user's own words. A silently
  vanished deadline cannot be audited later, and someone will re-add it because nothing says why it went.
- **After applying a deferral, grep the whole corpus for the date/claim.** Two older notes still asserted it and
  would have fed the next reader; each needed a `SUPERSEDED` banner rather than an edit — the reasoning that was
  true at the time is evidence, and rewriting it destroys the trail.
- **Fix the rationale too, not just the field.** A sequence rule justified by *"the voucher is windowed"* keeps
  re-deriving the retired order after the dates are gone. Replace the *reason* with one that still holds, or the
  same decision returns wearing new numbers.

## The checker — four rules, each falsifiable

1. **R1 HEADER STALE** — the page's `Updated:` date is older than the newest mtime of the files it **declares** as
   its source. A summary older than its source is a rumour with a URL.
2. **R2 RETIRED CLAIM** — any `retired_dates[].what` from the source appears in the page **outside a strikethrough**.
   A struck line is a correction and is fine; an unstruck one re-asserts a dead decision to the next reader.
3. **R3 NO SOURCE** — the page declares no checkable source, or names one that does not exist → **exit 2**.
   A page that cannot be checked must not be trusted, and must never report clean.
4. **R4 GENERATOR DRIFT / UNKNOWN** — the page's own mtime is well *later* than the source's internal
   `generated_at` (a page edited around a stale claim), and **a source with no `generated_at` is UNKNOWN → exit 2,
   never fresh**. A timestamp nobody wrote is not freshness.

**Implementation notes that cost time to learn:**

- **Restrict "declared source" to the `Source of truth:` line.** Treating every `*.json` mentioned in prose as a
  source makes the checker fire on pages that are correct — a false alarm in a delivered report costs as much
  trust as a miss.
- **Read the result from the EXIT CODE, not by parsing JSON out of mixed output.** A checker that prints a human
  header around its JSON and is parsed with `json.loads` reports `None` — and `None` gets called clean.
- **Silent when clean** (`--quiet`, zero bytes) or it gets muted; **exit 2 whenever it could not check**. Never a
  zero for an unreadable vault, page or source.
- **Every rule needs a planted-defect control.** Prove each fires on the thing it exists to catch, and that the
  clean run stays silent — a checker that stops crying wolf by going deaf looks like success in the diff.

## Wiring, without a second cron

Ride the maintenance job that already runs: regenerate the state **first**, then audit the pages, in one wrapper.
That keeps the page compared against *today's* numbers rather than yesterday's, and adds no new job to explain and
retire.

- **A missing state file must print `NOT RUN — no state file`, never a zero.**
- **Publish the number that hurts.** A seat running `0/0` cron because every lane job lives in another seat's
  scheduler is not a tidy figure; it is the defect, and the page is where a reader will actually see it.

## What the page is for

The page is not a dashboard for the agent that wrote it. It is the file a **different** seat reads when it has no
context, so: state, not history · every line carrying a number or an owner · the open defects named on the page
rather than in a note nobody opens · and only the actions that genuinely require the user, each with its release
condition.

**When the page has no defects listed, suspect it before trusting it.** A lane with running work always has
something in the way; a clean page usually means nobody looked.
