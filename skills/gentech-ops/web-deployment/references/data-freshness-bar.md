# Data freshness on a public page — the age bar and its guard

Depth for *"A data page must state its own data's age"* in SKILL.md. Read when a page renders numbers that come
from files or feeds it does not own.

## The failure this exists for

A hub's four data fetches were pointed at the wrong owner and 404'd, so every panel showed dashes — visibly broken,
and someone went looking. The fix was to point them at the correct owner. **Behind the correct owner the data was
87–126 days old**, so the fix FILLED every panel with August prices: a token at $6.30 shown as today's price, a
"Active — Harvesting" badge over a 97-day-old snapshot.

**Dashes look broken and get investigated. Stale numbers look fine and get believed.** "It is connecting again" and
"it is telling the truth" are two different claims and only the second is worth shipping.

## The bar

- **Read each source's own `lastUpdated`** — never the page's load time, never "now". A bar stamped with the render
  clock says FRESH about data from July.
- **State every feed separately.** One aggregate "as of" hides the one source that stopped.
- **Bands: `>3d` STALE (amber) · `>30d` ARCHIVED (red).** Print the date and the age in days, not just the word.
- **When a source cannot be parsed, say so in the bar** ("rotation source is not valid JSON") rather than falling
  back to placeholder cards — a silent fallback is the page claiming data it does not have.
- **The loudest element must not contradict the data.** A status badge reading *Active* above a 97-day snapshot is
  worse than no badge: it is the strongest claim on the page and it is false.
- **Advance the "checked" stamp on each refresh** — and verify it moves. A frozen timestamp is its own lie.

## The guard (separate job, same rule)

A page that shows age can still ship stale; the check that catches the *writer* stopping is a script:

- **Per source assert (a) it parses, (b) `lastUpdated` is under N days, (c) an unreadable source prints `UNKNOWN`,
  never `0` and never "clean".** Exit codes for humans: 0 fresh · 1 stale/archived · 2 could-not-read, with
  **UNKNOWN outranking STALE** — not knowing is louder than knowing it is old.
- **Selftest with planted failures**, in both directions: 90-day-old data must classify ARCHIVED, conflict-marker
  bytes must classify INVALID with no age, a failed fetch must classify UNKNOWN with no age, and a *fresh* payload
  must classify FRESH. A guard that cannot go red is a belief.
- **The cron wrapper must translate, not forward, those codes** — a non-zero exit is delivered as "job failed",
  which mutes a real alarm within a week. See the exit-code contract in `script-only-job-wiring`.
- **Name the writer.** A freshness guard catches a stopped pipeline; it does not restart it. Say who owns
  regeneration so "we alerted" does not read as "we fixed".

## Render-clean is not markup-clean

A real browser render showing zero `Loading...` strings does not mean the page stopped saying it: the placeholder
is usually **still in the markup** and only overwritten at runtime. Measured: served source held three `Loading...`
strings while the rendered page had none — so any fetch or script failure silently restores the placeholder, and the
page looks *loading forever* rather than *broken*.

- Start placeholder nodes **empty** (or with an explicit "waiting for data" that the bar can also report), so no
  failure mode returns the page to a claim of imminent content.
- **Check both**: `grep -c 'Loading\.\.\.' served.html` on the served bytes *and* the rendered DOM text.
- **The bar itself is JS-built** — verify its text after render, not only that the markup contains a container.
