---
name: company-meeting
description: "Use when the fleet reviews itself as a company."
version: 1.1.0
author: Gentech
license: MIT
tags: [fleet, governance, self-reflect, peer-review, meeting, delegation, hq]
metadata:
  hermes:
    tags: [fleet, governance, self-reflect, peer-review, meeting, delegation, hq]
    related_skills: [fleet-self-reflection, cron-health-standard, cron-improvement-audit, councilman]
---

# The Company Meeting

## When to Use

- The weekly fleet review is due, or you are chairing it for the first time.
- A seat has filed a proposal and needs a peer challenge before HQ can green-light it.
- You are about to green-light, push back on, or adjudicate a seat's proposal.
- You are walking a seat's lane and need the questions, the recording rule, or the follow-up reads.
- **Not for** a single department's internal verdict — that is the treasury's council, a different room.

**Jordan, 2026-11-17:** *"Treasury has the council meeting. We could have the company meeting… The skill should be
called The Company Meeting just to keep that professional name, and within inside the skill we'll list the details
where self-reflect comes in."*

**The names are deliberate and they are different jobs:**

| | **Council** (Treasury's) | **Company Meeting** (the fleet's) |
|---|---|---|
| who | the treasury's own read on a shared claim | **every seat, one agenda** |
| answers | *"what should we do about this?"* | *"how is each department doing, and what needs a decision?"* |
| output | a verdict | **a record + green lights** |

**`fleet-self-reflection` is the ENGINE. This skill is the MEETING** — the cadence, the agenda, the peer review,
and the record. **Do not restate that skill here; load it.**

---

## The operating model (Jordan's words, and they are the whole design)

> *"At the end of the day, we're just a delegation layer, right? We only wanna interfere if we need to, like if an
> agent goes down or something. But we hear what they say, and we give them feedback and the green light to add."*

**HQ is a delegation layer, not a manager.** The seat owns its lane and proposes; **HQ hears, grades, and
green-lights.** HQ interferes only when:
- a seat **did not answer** (a finding, not a retry loop), or
- a measurement is **red** and the seat did not name it.

**Everything else: the seat's call is the call.**

---

## Intent 0 · SHARED FACTS — read `00-HQ/shared-facts.md` before answering anything

**Jordan, 2026-11-17:** *"You guys may not have the latest update on everything. I may come here in GenTech HQ,
tell you my work schedule, but that doesn't mean Arthur knows my work schedule, or Treasury knows."*

**The gap: a fact told to HQ reaches ONE seat.** So **every meeting opens by reading the shared-facts file**, and
**every seat's answer is checked against it.**

- **A seat that contradicts a row has found either a stale row or a real change.** Both are findings; neither is
  a mistake to be corrected.
- **A seat that learned a fleet-wide fact from Jordan writes the row in the same turn it learned it.** The
  failure is never *"nobody wrote it down"* — it is *"everyone thought someone else did."*
- **Facts change by UPDATE, never by append.** The log lives in the note that records the decision.

---

## The agenda — three intents, in this order

**A meeting that asks everything gets a survey. Three questions get answers** (measured 2026-11-17 — the first
run produced four real faults and three usable instrument proposals from three seats).

1. **DEPARTMENT — cron and instruments.** *Name ONE job not earning its slot, and the measurement that proves it.*
   Then: *one instrument you would build that nobody asked you for, with the test that would prove it works.*
2. **STRATEGY — what is next in your lane, and what blocks it.** The blocker gets an owner tag
   (`NEEDS-JORDAN` / `NEEDS-HOST` / `UPSTREAM` / `FIXABLE-NOW`), per `cron-improvement-audit`.
3. **OPEN — one thing you would build or change that nobody has asked you for.** *This is the intent that produces
   the ideas nobody thought to request.* **It is not optional and it is not last for being least.**

**The rule stated in the ask, every time:**
> *Name measurements, not feelings. If you cannot measure it, say `UNMEASURED` and what would measure it.
> No suggestion without a test attached.*

---

## The peer review — **the three-process idea Jordan brought from his job**

**Jordan, 2026-11-17:** *"At my job we have three different processes for checking quality, so when you guys speak
to each other about this stuff we no longer have a single point of failure."*

```
AUTHOR     writes the proposal     knows what they MEANT
PEER       reads it cold           sees what they WROTE — and is told to attack it
HQ         green-lights            with both reads on the record
```

**Measured proof it works, 2026-11-17 — three catches, none by the author:**
- **Proto J** found a dead `ELEVENLABS_SELF_ID` retire branch in **HQ's own** cron job
- **Treasury** found its watchdog had **no subject** — invisible from HQ's vantage
- **Arthur**: *"`last_status: ok` is the script's exit, not a delivery receipt"* — one sentence that changed how
  three other jobs were verified that night
- **Treasury** opened its own proposal by **contradicting HQ's claim** that the rug watcher was gone

**The brain already carried the pattern before the mechanism existed** —
`00-HQ/council-minutes/2026-09-30.md`: *"**Independent cross-check, not the author's test**"* — written after a
checker and its file **agreed with each other and both were wrong.**

### How to run the review without it becoming a rubber stamp

1. **The reviewer is never the author.** No exceptions, no self-review with a second hat on.
2. **Ask for the failure, not the opinion.** The prompt is *"find the measurement that would make this claim
   false"* — **never** *"does this look good"*, which produces agreement and teaches nothing.
3. **The verdict is one of three:** `CHALLENGE` (with the counter-measurement) · `AGREE` (with what was checked)
   · `UNMEASURABLE` (and what would measure it).
4. **A CHALLENGE without a counter-measurement is a question, not a veto.** HQ must answer it in the record —
   silence on a challenge is how peer review becomes theatre.
5. **HQ publishes the peer's read verbatim next to the proposal.** A meeting where the challenge is summarised
   away is a meeting where nobody challenges twice.

### HQ adjudicates — the third process is not a relay

**Relaying a peer's verdict makes two processes, not three.** HQ's read must be **its own measurement**, and the
record must show all three separately: what the author claimed, what the peer challenged, what HQ measured.

1. **Verify the reviewer before you adopt or reject the review.** Re-run its load-bearing numbers yourself. Mark
   each one *reproduced* / *not reproduced* — and publish that line, because a peer whose numbers are never
   checked is a second author.
2. **When you contradict someone's number, reproduce THEIR call, not an equivalent one.** Same endpoint, same
   params, same header. Two valid endpoints can disagree (a search route and an id route over the same object
   return different cardinalities); publishing that disagreement as a contradiction is your error, not theirs.
3. **Uphold a CHALLENGE by naming the changes required, not by restating the objection.** Numbered, each with
   the measurement that would satisfy it — an author cannot act on *"this is unfalsifiable."*
4. **Accept some of the proposal explicitly.** A verdict with no accepted items reads as a veto, and the author
   stops proposing. Name what survives untouched, so the revision is scoped.
5. **A verdict is `UPHELD` / `PARTIAL` / `REJECTED` on the RECORD, with the required changes listed.** Nothing
   ships between challenge and revision; the owning seat revises and answers the peer in the same file.

### A gate must be able to open

**When a proposal's evidence bar is a count of future events, compute how long the count takes to arrive.**
- **A bar that cannot be reached in the stated period is not a gate, it is a retirement with extra steps.**
- **A ceiling whose denominator is undefined is not a measurement** — if the number moves 2× depending on which
  population you count, it was a sentence. Demand the denominator before accepting the rate.
- **The counter-measurement is usually a retrospective run over data already on disk.** Ask for it before asking
  for calendar time: an afternoon over a labelled historical set beats a quarter of waiting.

---

## The record — the Mess Hall

**One file per week:** `11-Mess Hall/self-reflect/YYYY-WW.md`, **in the seats' own words, with their numbers.**

**Why there and not HQ's own folder:** `11-Mess Hall/` is *considerations* — decisions waiting to be made.
**The meeting turns it into a list of ideas rather than a pile of notes**, and the PA suite reads it.

**The maintenance rule Jordan set — "once it gets old, it's out of here":**
- **A new week is a NEW FILE.** Old weeks are read, never extended.
- **A suggestion with no action for a month is either dropped or promoted to the build queue.** It does not
  accumulate.
- The index line lives in `11-Mess Hall/considerations.md`.

---

## What the meeting does NOT do

- **It does not change routing, swap models, or disable providers.** `fleet-self-reflection`: *"This skill
  measures; Jordan decides."*
- **It does not fix what it finds, in the same pass.** A meeting that edits its own subject cannot be reviewed.
  HQ green-lights; the owning seat acts.
- **It does not speak when nothing happened.** A quiet week produces a file and **no message** — the Silence
  Standard. **A meeting that always reports cannot report an anomaly.**
- **It does not audit another seat's lane from the outside.** Ask the owner. The owner's answer is the finding;
  HQ's inference is a hypothesis.

---

## The cadence

| | |
|---|---|
| **when** | **Monday morning, after the Sunday council** — the meeting reads the week the council just closed, and lands before the new week starts |
| **who** | every seat; HQ chairs |
| **delivery** | file to `11-Mess Hall/self-reflect/`; **chat only if a seat did not answer or a probe went red** |
| **escalation** | ACK in the session it is read · answer within 2 days · escalate on day 3 (the Colleague Rule) |

**Run the first one by hand.** The questions are new and they will misfire somewhere — and a meeting that has never
been chaired should not be scheduled before it has been read once by a human. *(Measured: the first manual run is
what produced the four findings above; an unattended first run would have shipped the same questions unchecked.)*

**Open the DEPARTMENT intent with the seat's own INSTRUMENT output, not with its recollection.** Where a seat runs a
department reflection, its last scorecard is the evidence base and the meeting asks what to do about it. The
operator's question is *"are the jobs working, what needs to change, what needs fixing"* — a seat answering that
from memory is guessing at numbers it could have read, and the guess will be flattering.

**Keep the instrument and the meeting as two different jobs on two different cadences.** The instrument runs often,
is a script, costs nothing, and grades one seat against a stored baseline. The meeting runs weekly, is a
conversation, and decides. **Collapsing them produces a meeting that is a status report, or a probe that thinks it
has authority to change policy.**

---

## What goes in the report, every week

```
THE COMPANY MEETING — week NN

DEPARTMENT   (per seat) one job not earning its slot + the number · one unasked instrument + its test
STRATEGY     (per seat) next step · blocker · owner tag
OPEN         (per seat) one idea nobody requested

PEER REVIEW  proposal · reviewer · verdict (CHALLENGE/AGREE/UNMEASURABLE) · the counter-measurement
GREEN LIGHTS approved / ask-Jordan / refused — with the one reason
JORDAN'S     the things only he can do, each with its release condition
```

**Every line carries a number or an owner.** A meeting minute that says *"improve X"* is a wish with a timestamp.

---

## After the green light — promoting is not delivering

**A green light ends HQ's decision. It does not end HQ's job.** The seat acts, reports *"done and verified"* — and
that report is about **one seat**. When the thing shipped is a skill, a script or a cron standard, it has to exist
**everywhere** before it is done.

```
seat promotes to CORE  ->  CORE holds the new rule  ->  every OTHER seat still runs its old copy
```

**Measured:** a seat promoted a guard to CORE and reported it verified. It was — **on its own seat and in CORE.**
Three of the four seats were still running the previous version, byte-for-byte, and one of them was HQ's. Every
verification the author ran passed, because the author only ever ran it where it had been installed.

**So the closing move on any fleet-wide change is four reads, not one:**

```bash
# 1. does every SEAT carry the new rule? (not just the author, not just CORE)
for p in <seats>; do
  printf '%-18s %s\n' "$p" "$(grep -c '<a string unique to the new rule>' profiles/$p/skills/<path>/SKILL.md)"
done
# 2. run the instrument FROM YOUR OWN SEAT, not by reading their transcript
python3 profiles/<your-seat>/skills/<path>/<the-script>; echo "exit=$?"
```

- **Run it from your own copy.** A seat's pasted output proves its copy behaves; yours may not have the file at
  all. The independent run is the finding, and it costs one command.
- **A count of `0` on a seat is not "no drift" — it is "this seat cannot do the thing".** Treat a missing rule as a
  delivery failure, never as a variant.
- **Check presence at the depth skills actually live, or you will report an installed skill as absent.** Skills sit
  at `skills/<category>/<name>/SKILL.md`, so `ls profiles/<seat>/skills/<name>` finds nothing for anything nested one
  level down — a false "not installed" that reads exactly like a real gap. Use
  `find profiles/<seat>/skills -name SKILL.md -path '*/<name>/*'`, and confirm the load path rather than the directory.
- **This test applies to the meeting's own format first.** A seat that cannot load THIS skill is answering a
  questionnaire it has no format for, and will answer in prose instead of the three intents. Install it on every
  seat and prove the load before the first scheduled meeting fires.
- **After the sync, re-run the instrument on the real input and require the NEW exit code.** Presence in a file
  is not behaviour; the guard has to fire where it lives.
- **`TOTAL DRIFT: N` from a fleet-wide checker is not a work list of N items.** It counts per-seat copy
  differences, and most are legitimate divergence. Ask the promote tool what it would actually change — it
  reports a handful, and only those are the work.

**A rule that exists on the seat that wrote it and nowhere else is not a fleet standard. It is one agent's habit
with a shared file path.**

---

## The WALK — the part a meeting cannot do

**Jordan, 2026-11-17, on Holman Plating (Dayton, Ohio):** *"The CEO would walk around and pretty much greet
everybody and speak with everybody, and I thought that was amazing, something I wanna implement."*

**A meeting collects reports. A walk GOES AND SEES.** The difference is not ceremony:

| | **The Meeting** | **The Walk** |
|---|---|---|
| direction | seats report **up** to HQ | HQ goes **down** to the seat |
| question | *"how is your department doing?"* | *"what are you working on right now, and what's in your way?"* |
| input | answers to three intents | **the seat's actual current state**, not a summary of it |
| failure it catches | a lane that stopped earning its slot | **a seat that is busy, honest, and building the wrong thing** |
| cadence | weekly, on the record | **irregular, unannounced** |

### Why an unannounced walk finds what a scheduled meeting cannot

**A seat preparing for a meeting reports what it thinks you want.** That is not dishonesty — it is what anyone
does when they know the question in advance. **The walk has no agenda, so there is nothing to prepare.**

**Three things only the walk catches (each observed in one night, 2026-11-17):**
- **Proto J had a broken command menu and had not noticed** — it surfaced only because I asked an open question
- **Treasury's watchdog had no subject** — invisible from HQ's vantage, obvious from inside the lane
- **A seat's real blocker is usually smaller than its report** — *"I need capital"* becomes *"I need 25 USDC and a
  bin width"* the moment you ask a person, not a form

### How HQ walks (the rules)

1. **Arrive with nothing to assign.** A walk that ends in a task is a supervision visit, and the next one is
   prepared for. **Ask, listen, leave.**
2. **Ask about the PRESENT, not the period.** *"What are you working on right now?"* — not *"what did you
   accomplish this week?"* The second produces a summary; the first produces the truth.
3. **Ask what is in the way.** A seat will not volunteer a blocker it thinks is its own fault. **"What's in your
   way?"** gives it permission.
4. **Walk to the seat, not the report.** Read the seat's own log/output first so the visit is informed — **but do
   not arrive quoting it.** A walk that opens with a correction is an audit wearing a friendly hat.
5. **Write down what you heard, in their words, the same day.** A walk nobody records is a nice conversation.
6. **Do not walk the same lane twice in a row.** A walk becomes a special inspection when it only happens after
   something goes wrong.

### The line this must not cross

**The walk is a courtesy, not a checkpoint.** If HQ only visits when a number is red, the walk *becomes* the red
number, and every seat learns to dread the visit. **Visit the healthy lanes too — especially the quiet ones.**
A silent seat is the one most likely to be stuck, because being stuck and being quiet look identical from HQ.

**And a seat is not a person on a factory floor: it will answer any question you ask, at any hour, with perfect
patience.** That removes the social cost that made the Holman walk work — **nobody is embarrassed to be visited.**
So the walk must supply the thing the office supplied for free: **HQ must actually go, on a schedule nobody
announces, or it will simply never happen.** A cron cannot walk. **The chair of the meeting must.**

### The Walk feeds the Meeting — the loop, and where it lives

**The walk is not a competing ritual; it is the meeting's INPUT.** Jordan's correction, and it is the right shape:
*the CEO walks all week; the weekly meeting asks whether what was said on those walks is working.*

```
WALK (unannounced, several per week)  ->  a durable log  ->  the daily PA suite  ->  COMPANY MEETING (weekly)
   finds the file path                    the corpus        Jordan sees it daily     asks: did it move?
```

- **The walk belongs to the PA suite, not to a cron.** It is something the chair does *while already talking to a
  seat* — bundling it into the same daily instrument that reports correspondence is what makes it happen.
- **Log each visit the moment it ends:** the seat, what was heard in their words, what they named as in the way,
  and anything they wanted seen. **A visit the log does not hold did not happen** — the weekly meeting has nothing
  to carry forward.
- **The meeting reads two separate numbers and never sums them:** what is still **open** (a concern no later
  visit closed) and what was **never revisited** (nobody walked that seat again). *Different questions, same rule
  as any two counters in an audit.*
- **A closed item needs an explicit close.** Matching a later visit's "this resolves X" against the original
  concern must be case-, space- and punctuation-insensitive — a human retyping a reference will never match
  byte-for-byte, and a silent non-match leaves a closed concern listed as open forever.
- **An unreadable log is `exit 2`, never silence.** Silence means "nothing open"; a corrupt log that reports
  silence is the worst available answer.
- **And the honest limit stays attached to the number:** *never revisited* proves nobody walked that seat again.
  It does **not** prove the concern was solved, and the report must say so in the same breath.

**Why the log is worth keeping even when it looks like bookkeeping:** four departments, the same three questions,
week after week, with the answers and their outcomes dated — that is a corpus of what actually blocked real work
on real days. **It cannot be synthesised, and nothing else in the vault records it.**

**The instrument, its CLI and the four close-matching cases:** `references/walk-instrument.md`.
