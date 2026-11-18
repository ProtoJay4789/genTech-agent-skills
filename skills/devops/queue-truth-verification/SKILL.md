---
name: queue-truth-verification
description: Verify build-queue deploy claims against the live filesystem/URL BEFORE re-deploying or trusting a queue note. Prevents duplicate deploys and stale "needs Jordan" notes when work was actually shipped in a prior session.
---

# Queue Truth Verification

## Problem
Build-queue notes are snapshots of intent, not proof of current state. An item can say "needs Jordan to deploy production build" when the artifact is ALREADY live — deployed in a prior session, or sitting at the site root. Trusting the note leads to duplicate deploys, wasted work, and a false "blocked" status.

## The Rule
**Before deploying, marking blocked, or acting on a deploy claim, VERIFY the actual current state.** The filesystem and live URL are the source of truth, not the queue note.

## Verify the PREMISE, not only the claim about state
A queue item is a **belief written by an earlier session**, and its nouns can be imaginary. The item's
verdict ("pending", "needs Jordan") is one thing; the *things it names* are another, and those are what
the prescribed command will act on.

Measured: an item said a restart "must go through the systemd unit `<name>.service`, which carries
`EnvironmentFile=…`, `X402_NETWORKS`, and the per-rail pay-to keys." **No such unit existed** — not
enabled, not disabled, absent. Following the item literally would have run `systemctl restart` against
nothing, and the environment file it described could not be confirmed either. The item was not stale
about *state*; it was wrong about *existence*.

Before running any command a queue item prescribes, confirm its subjects exist:

1. **Named service/unit** → `systemctl list-units --all | grep -i <name>` **and** `systemctl cat <name>`.
   `list-units` alone misses units that were never enabled or were removed after a migration.
2. **Named config/env file** → `test -f` it and print the variable NAMES (`grep -o '^[A-Z_]*'`), never the
   values. If it is missing, the item's fix is unimplementable as written.
3. **Named process/container** → `ss -ltnp` for its port and `docker ps -a` for its name; confirm the
   owner in the socket line, not only the name in the note.
4. **Named artifact under a doc claim** → grep the *filesystem*, not the note's description of it.

**Then decide which of three cases you are in** — and say which, in the note you leave behind:

- **The premise holds** → execute the item as written.
- **The premise is stale but the goal is right** → the item is an *X is missing* task, not a *restart X*
  task. Re-scope it before acting; do not paper over the gap with the old command.
- **The premise is gone and so is the thing** → the honest outcome is *delist / drop*, not *restore*. An
  item whose subject has no code on disk is advertising, not backlog.

**A queue that records beliefs decays silently in the same direction as its author's optimism.** When one
item turns out to name a non-existent artifact, assume the *class* is affected and schedule a re-measure
of the rest — do not extrapolate from the single verified item to the whole list in either direction.

## Rows die of SUCCESS too — re-measure the condition, not just the artifacts

The buckets above catch rows whose subject never existed. The other half of a decaying queue is rows that
were **true when written and are false now because the world moved** — and nobody edited the row, so it
reads exactly like live work.

Two shapes, both common enough to check every time:

- **The row's own remedy happened.** A row can assert a condition that its own fix, or an unrelated later
  action, has already cleared. Measured: an item stating most of a catalogue was invisible to a discovery
  index was closed with zero code changes — the act that populates that index had occurred since the
  measurement, and the index returned every one of our entries, complete. The row was a true sentence about
  a past afternoon.
- **A change made for a different reason retired the defect.** A row diagnosing a misconfiguration can be
  dissolved by a config change aimed at something else entirely, with no one touching the code the row
  named. Measured: an item describing a fallback that pointed at the primary's own provider was true when
  filed and already fixed by an unrelated provider change; working it as written would have re-broken a
  correct arrangement.

**Rule: any row asserting a condition about a LIVE EXTERNAL SYSTEM is a measurement with an expiry, not a
fact.** Before starting it, re-run the specific measurement the row was founded on and quote the fresh
result in the row — including when the fresh result closes it. **And after any config, rail, DNS or
infrastructure change, sweep the queue for rows whose defect that change could have retired** — a fix has a
blast radius in both directions, and the rows it healed are invisible unless someone looks.

**Distinguish "stale" from "wrong when written".** Both look identical in a queue and they teach opposite
lessons: a stale row means re-measure before working anything; a wrong row means the *author* was guessing,
and the whole batch from that session is suspect. You can only tell them apart by asking whether the evidence
the row cites could ever have supported it — if it could, it was true then; if it could not, it never was.

**Before trusting a re-measurement that agrees with the row, prove the probe can find something.** A query
whose filter parameter is silently ignored returns a plausible set and reads as confirmation of the original
claim. The control procedure is in `proving-a-negative` under *"A filter parameter must be proved to FILTER
before its zero means anything"* — run it whenever a fresh measurement reproduces a months-old negative.

## Audit the whole queue, then close honestly — the cheapest reduction is a verified close

Verifying one item by hand does not scale past a few dozen, and the drift runs one way: the list grows
while nothing reports it. Two operating rules keep the number honest.

**1 · The queue needs an owner that SPEAKS.** A queue with no scheduled reporter is a list nobody is
accountable for: it grew 48 → 78 items without anyone noticing, because the job that used to summarise it
had been retired and the personal-assistant audit read four other lists and never opened the queue file.
- **A digest, not a watchdog.** Watchdog jobs stay silent when nothing changes; a *list* needs "nothing
  changed" said out loud, daily, or the absence of news reads as health.
- Print: open / actionable-by-us / gated counts, the next few by difficulty, and the audit buckets below.
- **Grep the cron definitions for the queue path before assuming something reports it.** A skill document
  describing a reporting job is not evidence the job exists.

**2 · Bucket every open item by what can be CHECKED, in one pass.**

| bucket | test | what it means |
|---|---|---|
| evidence present | the files/scripts/cron-ids it names resolve on this machine | safe to work as written |
| unverifiable from prose | it names no checkable artifact | needs a human read; the honest largest bucket |
| names an absent target | the thing it says must be fixed/built is not there | the claim cannot be true as written |

- **Bucket by the verb first.** An item that says *write / create / build* EXPECTS its target to be absent —
  absence is the assignment, not a contradiction (see audit-tool-validation for the full rule).
- **A cron id or service name in the item is a cheap oracle:** check it against the live cron/service list
  before believing the item's premise. Dead ids are the most common way an item stays "open" forever.

**3 · Close with proof, and say why it closed.** Of five items checked by hand in one pass, two described
infrastructure that had **never existed** and one had been fixed weeks earlier. Closing those is not
bookkeeping — it removes work that was never work.
- Write a `resolved` field naming the evidence (`verified live at <url>/<status>`) or the supersession
  (`job <id> no longer exists; replaced by <new job>`). An item closed without a reason will be reopened by
  the next reader.
- **Do not delete closed rows in the same pass.** Deleting is fine later, but the resolution note is the
  only record of why something stopped being real.

**4 · `len(items)` is not the work count.** Retained `shipped` and `closed` rows inflate any total derived
from the array; the summary object is not authoritative either. Compute open as
`status in (pending, open, in_progress)` and report that number alongside the shipped/closed totals, rather
than quoting the array length.

## Verification Checklist
Run these BEFORE any deploy/undeploy/status change:

1. **Check the claimed live URL** — `curl -s -o /dev/null -w "%{http_code}" URL` and confirm it serves the right content (grep for a distinctive title/string, not just a 200 — nginx SPA fallback returns 200 even for missing paths).
2. **Inspect the deploy target filesystem** — `ls` the directory; confirm the expected files exist before you copy over them.
3. **Check alternate locations** — the artifact may live at a different path than the queue implies (e.g. a game that is the site root `/` rather than a `/cabinet/<name>/` subdir).
4. **Only then** update the queue note to reflect reality and do the minimal action (or none).

## Pattern (proven Aug 3, 2026)
Super Arcade Tennis queue item #4 said "needs Jordan to deploy production build." It was ALREADY live at arcade.gentechlabs.net root (it's the landing page). Result of not checking first:
- Deployed a redundant copy to `/cabinet/super-arcade-tennis/`
- Added a duplicate nav link
- Then had to revert both after discovering the root already served it.

**Fix:** curl the root URL first, read the title, `grep -c` a distinctive game string, check the cabinet dir. Then update #4 to "game is LIVE — only x402 crypto-payments wiring remains (Jordan-gated: needs wallet/funds)."

## What's Genuinely Jordan-Gated vs Not
When triaging a "needs Jordan" deploy note, separate:
- **Actually shippable by me** (static HTML/JS, no build step, no funds) → deploy it, don't defer.
- **Genuinely gated** (needs real wallet/funds for crypto-payments, MetaMask signature, private keys) → leave Jordan-gated and say why.

## Pitfalls
- **HTTP 200 ≠ deployed.** SPA fallback returns 200 for missing paths. Always grep for actual content.
- **The site root can BE the product.** Don't assume a `/cabinet/<name>/` subdir exists just because other cabs use that convention.
- **Stale notes are common** — a "deploy" done in a prior session leaves the note untouched. Verify, don't trust.
- **`shipped` status can be stale/mislabeled, not just notes (Aug 10, 2026).** After a merge-conflict resolution or overnight maintenance, items can carry `status: "shipped"` that doesn't match reality — the conflict resolution kept `[SHIPPED by labs]` annotations even for items that were NOT actually done. **Red flag: a `shipped` item with `needs_jordan: true` is almost always mislabeled** — a genuinely shipped item doesn't need Jordan. Before running the build list, audit every `shipped` item's `note` for "REMAINING", "needs Jordan to submit/register", or a pending deadline; correct to `pending`/`in_progress`/`cancelled` (missed deadlines → `cancelled`). Real example (Aug 10): 8 items wrongly `shipped` — KeeperHub (proof tx live but demo video + form pending → `in_progress`), DataHub + Arc (deadlines passed, unsubmitted → `cancelled`), BOT Chain/Telegraph/Gemini/Krexa (need Jordan registration → `pending`). A clean queue is honest: it won't skip live hackathons as "done" and won't waste time on missed ones.
