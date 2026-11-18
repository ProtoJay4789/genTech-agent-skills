# A full fleet-update run, measured

One worked example of PHASE 1 across a four-seat fleet, kept for the shape of the returns and the kind of
finding that only appears when you record the layout before touching it.

## The measured gap

`hermes --version` reported one version string; the published tag for that build was a **date-style tag**
(`v2026.9.24`), not the semver the version string suggested. A compare against the version string returned
`Not Found`; against the real tag it returned the true figure. The release body's own headline was roughly
double the actual jump, because a release body describes the range **since the previous major**, not since
our build.

Lesson: **the tag is data, not a guess — read the tag list.** And quote the compare's `ahead_by`, never the
release headline.

## The digest shape that worked

Two parts, both required:

- **Part 1 — Upgrade notes as RISKS.** A table of every behaviour-changing note with a third column: *why it
touches us*. This is the part people skip; it is the part that pays.
- **Part 2 — A block per department.** Just the raw material, clearly separated by lane. Each seat reads
  *its own block* and then goes looking for what the digest author missed.

Explicitly labelling Part 1 as risks and Part 2 as raw material is what lets a seat do both jobs — audit and
adopt — without conflating them.

## What the returns looked like

All four completed within a few minutes of dispatch. The strongest returns shared four properties:

1. **They measured instead of repeating the request.** One seat proved the survivability claim rather than
   echoing it — showing that `/` is the ephemeral overlay an image swap replaces while the state directory
   is a *separate mount on a different device*. That is the difference between "the data should survive" and
   "here is why it does."
2. **They gave digests and sizes for what they were preserving.** md5 + mtime per artifact, plus an
   integrity check on the state store.
3. **They named what they found in their own config**, not what the dispatch asserted about it.
4. **They disclaimed the authorization in their own words.** One deliberately withheld the restart phrase so
   that a mechanical grep for it returns zero hits. That is the protocol working without policing.

One seat also caught an urgent side-issue nobody asked about: its memory file was within a few characters of
its cap — one save away from being unable to learn anything.

## The pre-swap finding that mattered most

Before the swap, HQ recorded the service/layout shape. The config said "single multiplexed gateway" and only
one gateway process was live — but the service tree still carried **five gateway slots**: a default plus one
per seat, alongside the orchestrator and dashboard.

So the statement "we already run one gateway per machine" was **true of the process and false of the
layout** — and the fold-into-one-multiplex was precisely what the incoming commits changed.

Recorded before the swap, that distinction made the post-swap diff readable. Without it, the same
observation after the fact is indistinguishable from intended migration — and gets waved through.

## The wake that did not land

Every peer DM in this run returned no reply or timed out with exit 124. The rail itself was not down: health
and model-list endpoints answered at the same moment. So the failure was the DM leg, not the gateway.

All seats had already filed their return notes on disk. **The file is the delivery; the DM is only a wake.**
Verify a seat by its own activity and the artifact on disk — and if a wake did not land, say so rather than
reporting a delivery.
