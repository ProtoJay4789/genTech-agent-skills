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

**4a. Match requirements inside the REQUIREMENTS BLOCK, not across the whole posting.** A body mention is not a
requirement: an endpoint-IT job that lists *Kubernetes* once among "nice to have" tooling got dropped by a
whole-description match, and the reason printed for it was wrong as well. Cut the text at the first
requirements marker (*"what you'll bring"*, *"required skills"*, *"minimum qualifications"*, *"what we're
looking for"*) and match inside that window — then say in the reason which kind of match fired, because
`needs production Kubernetes` and `title is a platform lane` are different verdicts that a reader will
otherwise treat as one.

**4b. Fit means "could do the REQUIRED list on day one" — not "closeable in N days".** Scoring on
adjacency invites a sprint to manufacture the appearance of experience, and the sprint is the thing that gets
caught in the interview. Gate on *demonstrated* operation, and keep an explicit allowlist of what the user
actually runs (a live paid endpoint, scheduled jobs, containers, backups, monitoring, a specific language
set) — score against that list, not against the market's adjective soup.

**4c. A human's own DECLINE outranks any score, permanently.** When the user says "skip that one",
record it as a separate decline list carrying their reason, and drop the row on every future run. Otherwise the
scorer re-surfaces it next week at rank six and someone re-opens a settled decision. Two different states must
never share a gate reason: `declined by the owner` and `does not meet the requirement` are not the same fact.

**4d. Flag rows the user has ALREADY APPLIED to.** A lead list answers "what should I consider" *and*
"what have I already done" — a row that reappears with no marker invites a duplicate application, which is
worse than a missed lead. Match on company+title substrings, not on a job id the board can re-key.

**4e. Report the GATED SET, not just the ranked set.** Everything a gate dropped prints in its own section
with the one-line reason, and the digest header states the rule and the count. A silently dropped row is
indistinguishable from a row the scanner never saw — and the user's first question about an empty week is
"did you even look?".

**4f. A numerical floor (years, degree, licence) is a GATE with an INPUT, and the input must be verified.**
A posting that says "2+ years" is only checkable against a number the user has actually stated — and "years of
professional work" is not the same claim as "years of software engineering", so ask which one the floor names.
Until the number is given, the honest output is a flagged row (*"floor unverified — ask"*), not a silent drop
and certainly not an assumed figure. **Never round the user's number up**: a hire date is checkable in seconds,
and an inflated figure walks them into a screen they will fail. When the verified number arrives, encode it once
(a single source of truth the scorer reads) and state the consequence in the reason string (`"5-year floor not
met until <date>"`), so the gate explains itself without a second lookup.

- **Extract the floor from the requirements window, never the whole body (§4a).** Company prose — *"10 years of
excellence"*, a founding year, an "about us" paragraph — otherwise sets the same floor on every record of that
board and every role looks senior.
- **A RANGE's floor is its LEFT number.** `3-5 years` is a 3-year floor; taking the maximum over every number in
the string returns 5 and hides a role the user can clear. Capture the ranges first, substitute them out, then
scan the leftovers for standalone floors — and test `3-5`, `2-4`, a plain `5+`, a spelled-out `five years`, and a
boilerplate year, all five, because each takes a different path.

**4g. When a user constraint CHANGES, re-run and diff the counts — a rule change is only proven by what it
moved.** Print the ranked count and the gated count before and after. An unchanged gated count after a
constraint change is the finding (the change moved no row, and saying "updated" would be a claim about code
rather than about output); an unchanged *ranked* count after a filter tightening means the filter never fired.
The diff is cheap, and it is the only evidence that a retune did anything at all.

**4h. A gate that produces a REASON must live where reasons are COLLECTED — never in a score function's reject path.**
A scoring function's reject path returns a sentinel (`None`) and nothing else, because the caller unpacks
`(score, reasons)` from the survivors. Return a reason *string* from that path and every surviving call site
raises `ValueError: too many values to unpack` — and when the exception is caught per-record or per-run, the
symptom is not a traceback but **an empty digest**, which reads exactly like a quiet week and gets explained
away as one. Any gate whose verdict must be **printed** (a screen-out with its own explanation) belongs in the
gate function beside the other gates, where the reason is collected and the row lands in the GATED section
(§4e). **After moving a gate, enumerate the return statements of the function you removed it from and assert
they are all the sentinel** — the fix is proven by a non-sentinel count of zero, not by the file parsing.

- **Order gates by what they can INVALIDATE, not by where they were easiest to insert.** A level gate that
  reads the requirement list must run **before** the title-level passes, because a junior-sounding title can
  front a mid-level requirement list — *"Software Engineer I"* beside *"highly scalable, highly available
  production systems"* is a mid-level req wearing an entry title. Checking the title first lets the flattering
  label outvote the body that contradicts it.
- **A gate that crashes the run is worse than a gate that misses a row.** The first silently deletes the whole
  digest and looks like a thin week; the second prints a lead the reader will judge. When a filter returns
  nothing, suspect the gate code before believing the market.

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

- **Mark each row's PROVENANCE in the output — employer ATS board vs aggregator feed.** A row syndicated from a
  feed is **second-hand**: the feed can carry a closed req, a talent-pool catch-all, or a training-funnel listing
  under an engineering title, and the scorer's own gates cannot see any of that. Print the source beside the
  score so the reader knows which rows were read at the employer and which were taken on trust, and so the
  cheap verification lands on the rows that matter. A digest that presents a syndicated listing with the same
  confidence as a directly-read requisition is overstating its own evidence.

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

**10. LEVEL IS A SEPARATE AXIS FROM SCORE — and only POSITIVE evidence may claim fit.**

A scorer that rejects senior titles and then treats every survivor as one pool makes each survivor *a fit*.
Seniority is a second filter with its own vocabulary — banded titles (II/III/IV, *Intermediate*, *Experienced*),
stated floors, and the absence of any junior signal — and none of it is visible in a relevance score.

- **Every emitted row carries a LEVEL, printed before the score.** Four labels, not two: `junior` · `mid-band` ·
  `not-now` · `unmeasured`. A digest of numbers with no level reads as *these are for you*.
- **Only a positively-evidenced junior row may set the "you qualify now" flag.** Absence of a requirement is
  not evidence of fit: a posting that names no years floor while asking for production-grade experience is
  mid-band. Require an entry word in the title, or an explicit entry phrase in the body.
- **`unmeasured` is its own label and can never claim fit.** A record whose body was never fetched is unread,
  not junior — print its count in the header so the reader sees how much of the corpus the filter never saw.
  Defaulting an unknown to the flattering label is the same defect as a fabricated 0%.
- **A completed or unrun record is not a miss.** Exclude it from a denominator rather than counting it failed;
  the honest states are *untried*, *failed*, and *done*.
- **Retiring a target is a RANKING decision, not a deletion.** When the owner drops a lane, remove its phrases
  from the bonus list and from the headline section and let those records fall to a demoted weight — deleting
  the words outright also deletes records that merely *mention* them. And a title-level discount alone is not
  enough: body scoring can swamp it (+16 of body bonus against a −4 title penalty still ranks #1), so exempt the
  demoted titles from the body bonus too.
- **Prove the labels with a case table, both directions.** One row per label that must fire, then the same row
  with its evidence removed and the label that must appear instead. A single-pass test proves the code runs;
  only the pair proves the label is a measurement.

- **LEVEL SORTS BEFORE SCORE — it is a lexicographic key, not a tiebreaker.** Emitting the label and then
  ranking on score alone leaves the same defect with better typography: a mid-band row at fit 44 still tops a
  list of roles the user can actually win. Sort `(level_rank, -score)` with the unmeasured label **between**
  entry and mid — unknown must not outrank a measured entry row, and must not be buried under a known mid.
  Prove it with the emitted order, not the intent: read the list back and assert every `ENTRY` row precedes every
  `MID` row.
- **The label must extend the ONE classifier that already exists — never a second opinion beside it.** If the
  report already computes a level for another purpose, the emitted token maps from that result; two
  implementations will disagree on the same row and the reader cannot tell which one ranked it.
- **A word that names a CREDENTIAL is not a seniority signal.** Vendor certification tiers reuse level
  vocabulary — *Solutions Architect – Associate* is a cert name, not a junior role, while *Associate Software
  Engineer* is genuinely entry. Strip the credential phrase before the junior test reads the title, or the
  pattern labels a mid-band posting as the flattering one.
- **A tolerance count is never the headline.** "N entry-tolerant" measures the ABSENCE of a stated floor, not
  the presence of a winnable role; when it leads the digest the reader reasonably hears "N jobs for you".
  Headline the qualified counts, and print the tolerance number one line below with what it does not claim.
- **Every level/plan adjustment prints its own reason — and the PLAN is quoted from the owner, never inferred.**
  Encode a change as explicit weighted deltas in both directions, each written into the row's reason list, so the
  reader can argue with the weighting instead of guessing at it. **But the premise behind a delta is a claim like
  any other:** a conditional fallback ("my last resort is to stay where I am for a year or two") is not a plan, and
  a weighting built on one quietly steers the list toward a future the owner has not chosen. Quote his words or
  cite the note they came from; where the only source is someone's reading of him, weight what he is *doing*
  (courses, certs, a stated search) and say that is what it is. **And when the premise is retracted, fix the code
  comment and the printed reason string in the same pass** — a correction that reaches only the handoff leaves the
  machine still carrying the false premise, and the next reader finds it in the one file that looks authoritative.

**11. When you RE-AXIS a scorer, pre-register the pass line in writing before the first run — and pre-register what
would prove the axis WRONG.**

A correction and a retreat look identical unless the correction can fail. Before running the re-axed scorer, write:
the pass condition (a number, on the emitted output), and the **empty condition** — *"if N consecutive runs produce
zero records meeting X, the axis is wrong and reverts."* Then report the tally against it every run (`1 of 3`), and
**do not move the definition mid-sequence** to save the axis. If the data suggests the instrument (a title list, a
phrase set) is wrong rather than the axis, say so as a *separate, pre-registered instrument change with its own
pass line and a fresh tally* — the goalpost move and the honest refinement look the same in a summary and nothing
like each other in a dated note.

- **Score the DELIVERABLE the posting asks you to produce, not the lane its title sits in** — and attach a
  **pointer to an artifact that exists** for every class you score against (a live endpoint, a job scheduler, a
  restore drill, dated written calls, an evidence ledger). A rubric line that says "has domain depth" with no path
  behind it rates a confident CV the same as a real record.
- **Measure the matcher's HIT RATE before believing it: a class that fires on more than ~20% of the corpus is
  vocabulary, not evidence.** Matching a deliverable noun across the whole body returned **53% of rows** — the same
  over-claim as an entry-tolerant count — because *documentation*, *monitoring* and *integration* appear in nearly
  every posting. Requiring the phrase inside the requirements window **and** within a short character window of a
  producing verb (`produce|author|write|own|deliver|publish|maintain|build`) took it to **13%**. Print the matched
  phrase beside the pointer so a reader can reject a match without re-reading the posting.
- **A reweighting rule that never fired is UNEXERCISED, not passing.** When a live run contains no record the new
  rule applies to, say so: unit-tested is not observed, and the two must not be reported as one.
- **A DEMOTION needs a carve-out for the work the owner has actually shipped.** "Demote the engineering family"
  done literally also demotes the deployments, gateway/ops surfaces and API work he has run for years — the one
  slice of that family he can defend. Keep an explicit set of deliverable classes that are exempt
  (`deployed endpoint`, `ops / scheduling`, `reliability + recovery`, `integration`, `orchestration`), skip the
  penalty when the row's named class is in it, and print `carve-out, not demoted` so the exemption is visible
  rather than silent. Distinguish inside the set: *"deploy and operate a distributed systems runtime"* is the
  build-capability deliverable that was demoted, not fleet ops — the carve-out is about the artefact, not the
  verb.
- **A lane with ZERO qualifying records says `0 in market` — it does not go silent and does not get a near-miss.**
  Silence reads as "the scanner forgot the lane", and a padded near-miss is an invented row. Print
  `N titles admitted, 0 clearing <test>`, and pair it with the outside measurement that explains it when one
  exists ("121 analyst roles in the corpus, 4 entry, all internships, none remote"), so a zero is legible as a
  fact about supply rather than a failure of the rubric.
- **Dump every fetched record BEFORE scoring, so the population can be counted independently.** A per-source raw
  dump (`raw_roles.json`, N records) is what lets you reproduce someone else's unscored read of "the same
  boards" on your own fetch, and it is the only way to tell a filter defect from a thin market. One line to
  write, and it turns an argument into arithmetic.
- **Never publish a CROSS-TAB counted by substring without inspecting the matched samples.** After tightening a
  matcher, the same laziness reappeared in a one-line counter: "analyst ∧ crypto" returned 29, and the true
  answer was 0 — every hit was company boilerplate (*"forecast supply **chain** disruptions"*, *"independent
  **blockchain** infrastructure company"*). Print five matched rows and read them before the count reaches a
  report; a counter that counts vocabulary is the same defect as a matcher that scores it.

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
- **A gate matched over the whole body** — one stray mention of a tool the user has never operated kills a
genuine lead, and the reason it prints is a lie about why. Match the requirements window (§4a).
- **A settled decision re-scored** — the owner said skip; the list resurfaces it a week later. Declines are
  data with a reason, and they beat the scorer (§4c).
- **A row the user already applied to, presented as new** — a duplicate application is a real cost, and the
  marker is two lines of substring matching (§4d).
- **A dropped set that is invisible** — a list that can only show what survived cannot tell the reader whether
  the filter worked or the week was thin (§4e).
- **A numeric floor matched against an unverified candidate figure** — the row is dropped or promoted on a
  number nobody stated. Ask, record one source of truth, and never round up (§4f).
- **A retune reported from the code, not from the output** — "the filter now excludes X" with no before/after
  counts is a claim about a diff, not about the list the user reads (§4g).
- **Dedupe keyed on a mutable display value** — see *Stable identity* above; the loss is silent.
- **A permissive noun admitting a whole other department** — an `analyst` or `engineer` in the title does not
  make a benefits, payroll, recruiting, legal or billing role technical. Wall on the DEPARTMENT words as well
  as the role noun, or an HR analyst ranks as an engineering lead on remote/degree-flex signals alone.
- **A "no gate fired" row carrying the greenest flag in the output** — the absence of a stated floor is not
  juniority (§10). Require positive evidence before a row may claim the user qualifies.
- **A reason string returned from a score function's reject path** — the caller unpacks `(score, reasons)` and
  the run dies into an empty digest that reads as a quiet week. Reason-producing gates belong in the gate
  collector, and a moved gate is only verified by counting non-sentinel returns (§4h).
- **An axis change shipped without a written pass line** — then any result reads as success, and the next session
  cannot tell a correction from a retreat (§11). Write the condition, and the condition that would kill it, first.
- **A matcher believed without its hit rate** — a deliverable/relevance class firing on half the corpus is
  vocabulary, not evidence; tighten to requirements-window + producing-verb and re-measure (§11).
- **A cross-tab published without reading its matches** — boilerplate in a company description ("supply chain",
  "blockchain infrastructure") turns a substring count into a false market fact. Sample the hits first.
- **A demotion that catches the owner's own experience** — engineering-family discounts must exempt the
  deliverable classes he has shipped, or the ranker deletes the strongest rows in the family.

## Related

- Keyword ranking is a *claim about fit*. When its output reaches a human as a finding, hold it to the same
  standard as any other measured claim: name the source of each number and the window it was measured in.
- When the scorer writes back to the corpus or a registry it is a destructive write — the guards for overwrite,
  prune and sweep apply on top of everything here.

## Learned on gentech (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

- **Rank the WINNABLE class above raw fit, and say the order out loud.** A perfect-fit row behind a two-level
  gate is a worse lead than a modest-fit row with an open door. Measured: a list advertising *"ranked
  entry-level jobs"* put a frontier-lab `Forward Deployed Engineer, Agentic Platform` at fit 44 (top) over
  every junior-adjacent row — the ordering, not the scoring, was what made the digest useless. Report the top
  rows beside their labels so the reader can see the ordering for themselves.
- **A PROXY COUNTER may never be the headline.** "N entry-tolerant" beside "ranked entry-level" reads as N
  entry-level roles; tolerant means only that the requirements named no years floor. Name every counter for the
  quantity its check actually read, keep proxies in a secondary line, and never let a proxy share a sentence
  with the promise it is standing in for.
**11. A ZERO is TWO different findings — measure the population WITHOUT the filter before touching the rubric.**
An empty lane has two causes and only one of them is about your scorer: the market holds nothing (the filter is
right and the lane should be demoted or reverted) or the market holds plenty and the rubric cannot see it (the filter
is wrong). A re-tune performed before that distinction is a guess, and a zero reported without it reads as a bug.
- **Read the same sources with NO scoring, no domain walls and no years gate**, then count by family and by
  seniority, and compute the **intersection** the lane actually asks for (family ∧ domain). Measured on one lane:
  7,358 roles in the corpus · analyst family 121 (senior 36 · mid 81 · **entry 4**) · engineer family 1,392 (entry 71)
  · analyst ∧ crypto **0** — and all four entry-level analyst rows were internships, most not remote. The scorer's
  zero was correct; the market was the finding.
- **Report `0 in market` explicitly.** A lane that prints nothing is indistinguishable from a broken lane; a lane
  that prints `0 in market, 121 at mid/senior` states a fact a human can act on — including "look somewhere else".
- **Name the sources that returned nothing.** A board that failed to answer is not a board with no matches, and a
  population count taken across silent sources understates the market in exactly the direction that makes a lane
  look dead.
- **Hand the measurement to whoever owns the test, not a verdict on their work.** "Your zero is the market, run the
  remaining passes anyway" preserves both the discipline and the evidence; "your filter is broken" does not.

