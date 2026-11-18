# Skills Distribution Contract — one CORE, N seats

How a shared skill library stays identical across an agent fleet, and how an edit made on one seat
reaches everyone instead of being destroyed.

## The model

- **CORE** — the canonical copy, living with the rest of the versioned brain (e.g.
  `<vault>/<path>/skills-distribution/`).
- **SEAT** — each agent profile's own copy (`<profiles>/<seat>/skills/`).
  **A seat copy is a BUILD ARTIFACT, not a source.**

## The two directions, and why the order matters

| direction | kind of change | may delete? |
|---|---|---|
| seat → CORE | a CONTRIBUTION | never |
| CORE → seat | a SYNC (overwrites by design) | only its own superseded content |

**Always run the contribution pass BEFORE the overwrite pass.** Push CORE out first and a seat-authored
edit is destroyed; promote first and it is preserved *and* propagated to every other seat. Verified
end-to-end: an edit made on a single seat, promoted then synced, ended up present on every seat.

## Guards a distribution tool must have

1. **Never delete a skill that exists only on a seat.** Report it as a contribution and print the
   promote command. A silent delete here is indistinguishable from housekeeping — and it was the only copy.
2. **Refuse to overwrite a seat copy that holds files CORE lacks.** Report the offending paths and write
   nothing. The warning message *is* the signal; do not read past it.
3. **Distinguish the three drift outcomes** — *missing from seat*, *differs from seat*, *seat-only* —
   because each has a different fix and only one of them is safe to automate.
4. **Exit non-zero when refusing**, or an automating caller reads "did nothing" as "all clear".

## The comparison

- **Digest CONTENT over the WHOLE skill directory**, not just the `SKILL.md`. A file-level compare reads
  clean while a `references/` file differs.
- **Never include absolute paths in the digest.** CORE and seats live at different paths on purpose, so a
  path-sensitive digest reports false drift on identical skills — and a false alarm looks exactly like
  the real drift you are hunting, costing a full round to disprove.
- **Exclude build junk** (`__pycache__`, `*.pyc`, editor droppings) or every comparison reports drift forever.
- **A large gap between CORE and seat counts is unpromoted work, not corruption.** Count before concluding.

## Wiring it as a recurring check

- **Silent and exit 0 when everything matches**; speak only on drift. That is the only form of drift
  check that survives contact with a notification channel.
- **Never hand-edit a seat copy to fix a skill.** Edit CORE, then distribute — a seat edit recreates the
  exact drift the mechanism exists to remove.
- **Report the count the comparison actually used** (e.g. "244 skills") so a reader can tell whether the
  run covered the whole library or silently undercounted.
