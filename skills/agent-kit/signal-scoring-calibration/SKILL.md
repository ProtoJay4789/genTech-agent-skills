---
name: signal-scoring-calibration
description: "Use when calibrating a keyword scorer or lead filter."
version: 1.0.0
author: gentech
license: proprietary
metadata:
  hermes:
    tags: [scoring, filters, keyword-matching, lead-generation, calibration, auditability]
    related_skills: [opportunity-scanner-template, falsifiable-tests, destructive-write-guards]
tags: [scoring, filters, keyword-matching, lead-generation, calibration, auditability]
triggers:
  - "build a scanner that scores job postings or opportunities"
  - "add a signal or weight to a ranking filter"
  - "the filtered list looks confident but I can't tell why a row ranked where it did"
  - "a scored list needs a dedupe key"
---

# Signal Scoring Calibration

A keyword scorer is a filter that produces *numbers*, and numbers read as evidence even when the phrase lists
behind them are sloppy. This skill is the discipline that keeps a scored list trustworthy: it makes the filter
discriminate, makes a gate visible as a gate, and makes every score re-derivable from the data.

Applies to: job/opportunity scanners, lead-ranking crons, triage scorers, and any relevance filter over a
text corpus you rank and hand to a human.

## When to Use

- You are building or changing a script that **ranks records by keyword signals** — job/opportunity scanners,
  lead-ranking crons, triage scorers, relevance filters.
- You are adding or reweighting a **signal**, or turning a requirement into a **gate**.
- A filtered or scored list "looks confident" but you cannot explain why a row ranked where it did.
- A scored list is being deduped, registered, or published and therefore needs a stable key.

## Procedure

**1. Every signal carries a polarity AND a reason string.** A bare `score += 4` cannot be audited. Append a
named reason with the increment (`"remote-first (explicit)"`), so a row explains itself and a reviewer can
challenge one signal without re-reading the whole function.

**2. Test the PERMISSIVE list before the RESTRICTIVE one — and use `elif`, not two `if`s.** A requirement
phrase is often neutralised by its own qualifier: *"a degree **or equivalent experience**"* is the door, not
the wall. Written as two independent `if`s, the same text scores the bonus AND the penalty, firing both on the
exact phrasing that should have opened it. Permissive first, restrictive in `elif`.

**3. Keep phrases SPECIFIC — a generic term inflates the whole board and the filter stops discriminating.**
Terms like *"relevant experience"*, *"hands-on experience"*, or a bare *"github"* appear in nearly every
posting, so adding them raises the floor for everything and hides the real differences. **Measure before
adding:** score the corpus with the candidate phrase and count its hits — if it fires on most records it
belongs in neither list.

**4. A hard gate is a FLAGGED STATE, not just a subtraction.** Give a screen-out requirement its own boolean
on the record plus a loud reason string, so the lead is reported as *likely a skip* instead of quietly sitting
a few points lower where nobody notices. Mirror whatever skip-pattern the pipeline already uses for other
gates, so the report surfaces all of them the same way.

**5. Never penalise a term the user has ACCEPTED.** Ask before scoring a lifestyle or structure term
(on-call, travel, relocation, shift work, weekend coverage) as a cost. Once the user says *"that's fine"*, a
negative for it narrows their market against their own instruction. Record the decision as a comment in the
code beside the absent rule, so a later editor does not helpfully re-add it.

**6. Verify which SOURCES actually return a body before trusting any body-based check.** Body coverage is
per-source, not global: measure how many records per source carry a description. One source may return a body
for every record, another a truncated summary too short to contain the qualifications block where a degree or
years requirement lives, another none at all. **"No gate flagged" on a source with no body means "not
checked" — never report it as "checked and clear".** Enrich from a detail endpoint where the list endpoint
omits the description.

**7. Export the REASONS alongside the data you publish.** A lead set carrying only a score cannot be audited;
the entire value of the artifact is that its filter is *falsifiable*. Persist the reason array per record so
any row can be re-derived and challenged — and so the published file proves its own filter.

**8. Prove discrimination with a PAIR of near-identical inputs.** Score the same title/source twice, changing
exactly one attribute (remote vs onsite; permissive vs restrictive qualification), and assert the scores
differ AND the reason lists differ. A one-sided test proves the code runs; only the pair proves the signal
separates anything.

**9. A guard or selftest for the scorer must read the SAME source of truth the scorer reads.** A check that
validates against a built-in default list while the scorer consults a merged or extended list will fail on
valid new input and pass on the real defect. Point the guard at the exact lookup the code path uses, then
prove it still catches a genuinely invalid record.

## Stable identity for the records you emit

A scored list that is deduped, registered, or swept needs each record to have a **content-derived id** — a
hash of the identifying fields (source + title, or equivalent) — **never the record's visible position.**

- Positions are recomputed by design (renumbered nightly, compacted on completion), so they get **reused**. A
  registry keyed on the position collides with an older, already-swept record and the new one is **silently
  deduped away** — a completion that vanishes behind a success message, the same clean-success failure shape
  as any other destructive write.
- Keep the old position in a separate field (`was_position`) for traceability, and state explicitly in the
  dedupe rule that the key is content, not position.
- When you find this defect, **backfill the dropped record** — its text usually survives in a hand-written log
  or the source list — and re-key the legacy entries so they cannot collide again.

## Pitfalls

- **Two `if`s where one `elif` was meant** — a bonus and a penalty fire on the same text. The classic instance
  is a requirement phrase that contains its own permissive qualifier.
- **Generic-term inflation** — a phrase matching most of the corpus raises every score and destroys the
  ranking. Measure the hit rate before shipping a new phrase.
- **"Not flagged" reported as "checked and clear"** — on any source with no body, a body-based gate never ran.
  State the coverage limitation.
- **Reporting a count from a field you never export** — if the published record lacks the field, a count taken
  from it is zero by construction. Count what you actually write out.
- **A gate that only subtracts** — a screen-out hidden as a lower score reads as a mediocre lead, not a skip.
- **Dedupe keyed on a mutable display value** — see *Stable identity* above; the loss is silent.

## Related

- Keyword ranking is a *claim about fit*. When its output reaches a human as a finding, hold it to the same
  standard as any other measured claim: name the source of each number and the window it was measured in.
- When the scorer writes back to the corpus or a registry it is a destructive write — the guards for overwrite,
  prune and sweep apply on top of everything here.
