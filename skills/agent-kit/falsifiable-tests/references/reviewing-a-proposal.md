# Reviewing a proposal: attacks, counter-measurements, and a review skeleton

Depth for the SKILL.md section *"Reviewing someone else's PROPOSAL: name the measurement that would make it
FALSE"*. Load this when you are the peer reviewer on someone else's design, spec or plan.

## The job

You are not the author's editor and you are not a voter. You are the reader who decides whether the
proposal's claims can be false — and, where they can, what measurement settles them.

- **Verdict up front:** CHALLENGE · AGREE · UNMEASURABLE. One word a coordinator can act on.
- **A CHALLENGE must carry a counter-measurement.** Cost it in minutes and name the command or the data source.
- **Never edit the proposal.** The review is a separate artifact; the author owns the change.
- **Say what you would keep.** A challenge that reads as "rewrite it" gets discarded; naming the parts that are
  sound makes the rest credible.
- **Verify the proposal's own facts before arguing about its logic.** Numbers invented in the brief are
  cheaper to catch than design flaws, and catching one changes the reader's trust in the rest.

## Attack bank — pick the ones the proposal invites

### 1 · Gate reachability (highest yield)

Take the proposal's numbers and compute whether its quality gate can ever open.

```
allowed_events_per_week = ceiling_rate × universe / ceiling_universe
weeks_to_gate           = gate_events / allowed_events_per_week
```

If `weeks_to_gate` is a quarter or more, the gate is a schedule nobody agreed to — and if it needs events the
universe is defined to exclude (blue-chips that do not rug; healthy services that do not fail), the gate is
**structurally unreachable**. Report the number, not the adjective.

Counter-measurement: run the detector **retrospectively over a labelled corpus you already own** and count how
many events it would have fired on before each labelled outcome. Pass condition stated in advance (e.g. "≥20
events inside 30 days of backtest"); if it fails, the gate must be rewritten before the build starts.

### 2 · Denominator

A ceiling "per 25 units" measured on 4 units is a statement about arithmetic, not behaviour. Ask for the
population, and for the count that would make the claim testable. Also check that the population is stated
consistently with the source file the coordinator would audit — a universe count that does not match the
watchlist file is itself a finding.

Counter-measurement: compute the ceiling at the real population size, and state the minimum N that makes it
meaningful.

### 3 · Who wrote the test

| what the proposal says | what it actually proves | independent version |
|---|---|---|
| "kill the endpoint, assert exit 2" | the author's own error branch runs | spec-written stubs: empty-200 · refused · hang · malformed schema |
| "unit tests attached" | the functions compose | one behavioural case with a DECOY input that a wrong implementation would prefer |
| "validated 15/15" | well-formed, not working | call the primary feature on a real user input and assert the ANSWER |

Always add: **stdout must not contain "clean" / "safe" / "ok"** on the degraded paths, asserted by count, not
by eye.

### 4 · The evasion

For every detector, complete this sentence: *"this reports clean while an adversary ___"*.

- **staged / split actions** — six 15% steps instead of one 50% move beats any per-step threshold.
- **identifier migration** — a new pool, a new pair, a new endpoint: the monitored one ages out, the new one is
  invisible.
- **indirection swap** — beacon or diamond proxies change behaviour without touching the implementation slot the
  check reads.
- **derived-metric noise** — a USD-denominated metric moves when the price moves; a reserve-denominated one does
  not. Alarm on the derived number and you will fire on volatility and miss a real drain.

Counter-measurements: aggregate per entity across all venues · measure the underlying quantity, not the derived
one · baseline against a trailing floor (so a re-add cannot reset it) · read the indirection slot and print
UNMEASURED when it cannot be read.

### 5 · Transfer

A precision measured on the author's curated population does not transfer to the population the product serves.
For a per-call service: an input outside the labelled set must come back explicitly *unmeasured*, and the test is
a bounded call count (draw N samples from a list you already hold; assert N/N carry either labelled evidence or
`unmeasured`).

## Counter-measurement bank — cheap, runnable before the build

| the claim | the measurement |
|---|---|
| "this detector is precise" | retrospective over a labelled corpus you already own; count fires before each label |
| "the gate is reachable" | arithmetic on the proposal's own numbers; weeks-to-gate stated |
| "the error path is handled" | four stubs: empty-200, refused, hang, bad schema → non-zero, and zero clean/safe/ok tokens |
| "the adversary cannot evade it" | name the evasion; then a fixture that performs it and must fail the check |
| "it generalises" | N out-of-population inputs, each either labelled or explicitly unmeasured |
| "the page cannot go stale" | two-run proof: clean run silent; page edited after its data's `generated_at` → red |
| "the numbers are consistent" | recompute each derived figure from the raw fields the proposal quotes |

## Review skeleton

```markdown
# Peer review — <proposal title> (author's, reviewed by <seat>)
**Verdict:** CHALLENGE | AGREE | UNMEASURABLE

## What I checked instead of trusting
| claim in the proposal | what the box says |

## 1..5 — one section per attack that lands
**The claim.** **Why it can be false.** **Counter-measurement** (command, cost, pass condition).

## What would flip me to AGREE
1–3 changes, each cheap and named.

## What I would keep as written
```

## Judgement calls that keep the review honest

- **A defect in the author's numbers is a finding, not a gotcha.** Report the measurement and the delta; do not
  editorialise about carelessness.
- **Do not stack attacks that share one root cause.** Five symptoms of one design error is one section with five
  examples.
- **If the proposal is basically sound, say AGREE and list the two things to watch.** A reviewer who never agrees
  is as useless as one who never challenges.
- **UNMEASURABLE is a real verdict** when the proposal's claims cannot be tested with what exists. Say what would
  make them testable instead of converting a missing measurement into a challenge.
