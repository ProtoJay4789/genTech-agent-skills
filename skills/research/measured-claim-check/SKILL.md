---
name: measured-claim-check
description: "Use when a claim asserts a trend, forecast, or market fact."
category: research
version: 1.0.0
author: Hermes curator
license: MIT
tags: [research, macro, verification, markets, provenance, claims]
related_skills: [claim-provenance, market-data-feed-selection, crypto-price-fetch, link-research-summary]
metadata:
  hermes:
    tags: [research, macro, verification, markets, provenance, claims]
    related_skills: [claim-provenance, market-data-feed-selection, crypto-price-fetch, link-research-summary]
---

# Measured claim check

## When to use

Load this when a claim arrives and is expected to become a decision — a forwarded tweet or headline, a
macro assertion in conversation ("the dollar is weakening", "rates are coming down"), a bank's TAM or
price forecast, an "X is Y" market statement.

**The job is not to agree or disagree. It is to find which part of the claim is measurable, measure it,
and say plainly which part is not.** An assertion that survives two minutes of arithmetic is worth
keeping; one that does not was a vibe wearing a number.

## Procedure

1. **Write the claim down in its own words, split into its parts.** Most compound claims smuggle three
   different assertions into one sentence. See the decomposition below — do this before touching a tool.
2. **Check our own book first.** If the claim points at a name, is it already on the watch list? Was the
   thesis already recorded? See "Confirmation is not an edge" below.
3. **Pick a measurable proxy, preferring a keyless source.** You rarely need the exact index the claim
   names. A basket you can build beats an index you cannot fetch.
4. **Choose the window deliberately, and say which one you used.** A 12-month window and a 25-year window
   test opposite things (below).
5. **Report the number with its method in the same sentence**, and flag any range or precision honestly.
6. **Name what you could NOT measure.** Never let a partial measurement read as a complete one.
7. **Give a verdict that is actionable**: keep / hold / change nothing, and why. "Interesting" is not a
   verdict.

## The three-claim decomposition — the core move

A claim like *"the dollar is weakening, so a currency transition is coming"* is three claims wearing one
coat. They have different evidence and different timelines:

| Part | The claim | What tests it |
|---|---|---|
| **Long-run trend** | share is drifting down | multi-decade series; express per-year |
| **Recent fact** | it *is* weakening now | last 12 months of price vs a basket |
| **Future event** | a successor arrives soon | does the successor hold *accumulating* share? |

**They can all point in different directions at once, and usually do.** A slow trend down, a recent move
up, and no successor at scale is a perfectly coherent state — and it means *"the trend is real"* and
*"this is happening soon"* are not the same sentence.

- **Test the recent-fact part with a price.** It is usually the part the user actually cares about and the
  part most likely to be wrong.
- **A long-run trend quoted as a rate is far more useful than as a level.** "Down from >70% to 56.7%"
  sounds alarming; "~0.6pp per year, and the last two quarters moved in opposite directions" is the same
  data and tells you what to expect next quarter.
- **For a "transition" or "soon" claim, go straight to the successor.** A transition requires a replacement
  *accumulating* share. If the replacement is at ~2%, there is no transition on any near timeline no matter
  how convincing the incumbent's problems are. Say it that way.

### Structural claims — "the trend is breaking" is a fourth kind, and it has a definition

A claim that a market has **broken its structure** / is "headed down" is not a forecast and not a price
assertion. It is a claim about *sequence*, and sequence has a testable definition:

| Part | What it asserts | What tests it |
|---|---|---|
| **Severity** | "pulling back more than normal" | % off the window high, drawn from several coins |
| **Structure** | "the uptrend is breaking" | higher-lows: has a LOWER LOW printed / the last swing low been lost? |
| **Direction** | "down, not down-then-up" | *not measurable* — say so; the first two bound it |

**These are separate claims and the first does NOT imply the second.** A deep drawdown that stays above the
previous swing low is a **big pullback with the higher-low sequence intact** — mechanically, a rally from 50
to 80 falling to 57 is **−29%** and structurally *unbroken*, because 57 > 50. Report the two numbers side by
side rather than merging them into one verdict; merged, neither is falsifiable. When the structure claim
*does* fail, the honest answer is "you are right about the depth and wrong about the break", or vice versa.

**Deliver a tripwire, not a verdict.** The useful output of this check is the number that would settle it
next time — the most recent confirmed swing low per asset — so the claim stops being re-argued and starts
being watched. "Broken" then means price closed below a stated level, which anyone can check.

**And test the test before you report it — a structural detector can be convincingly wrong in the
NEGATIVE direction, which is the direction that contradicts the user.** Measured: a first detector compared
the minimum of the window's first half against its second. Fed a rally from 50 to 80 collapsing to 57 —
price through every recent low — it returned **"no lower low"**. The mechanism: the rally's *origin* sits
inside the window, so the first half's minimum is the floor, and price must give back the **entire rally**
before the test fires. On live data it would have answered a genuine break with *"no break — still rising
lows"*, delivered as a correction. It was **blind at exactly the moment it existed for**, and only a
synthetic series caught it. Detect **swing lows** (confirmed local minima), not window minima; compare the
latest swing against the *previous swing*, and test the whole thing on constructed series where you know the
answer — including one that is a big drawdown but NOT a break.

## Attribution claims — "this news caused the move" is settled by timestamps, not plausibility

A claim that a release or headline **caused** a market move is measurable, and it is the most commonly
asserted and least often checked claim in the class. Plausibility is not evidence: a hot inflation number
does make assets fall, so the story always sounds right. Test it anyway — four steps.

1. **Measure the move AT the instant.** Pull bars around the release time and compare the hours before with
the hours after. The test is concrete: **was the tape flat beforehand, and does the break begin INSIDE the
release bar on above-average volume?** The volume is the corroborating half — a move with no volume is
drift wearing a headline. A break that starts hours *earlier* falsifies the attribution outright.
2. **Correct the press framing when it disagrees with the tape.** Live-blog headlines are filed *before* the
event and phrase the move as happening "ahead of" the number. The bars decide. Say which one you checked —
and expect to correct a headline, because this is where they are habitually wrong.
3. **Separate the TRIGGER from the DRIVER.** One release explains the session it lands in, not a multi-week
structural move. If a breakdown predates the release by weeks, the correct sentence is that the print
**confirms a driver already in motion** and is the **continuation, not the origin** — the person who said it
is right about the news and right about the reaction, and is describing the trigger as if it were the cause.
Name the driver with its own dated evidence (prior meetings, futures pricing, other released data) so it is
not absorbed by the single headline.
4. **Read the COMPOSITION of the number, not just its level.** A headline that "came in hot" can be one
component doing the work — a single commodity, an energy shock — which changes what it implies. A
supply-driven print is not answered by a demand-side policy response, and saying so is the finding.

**Both halves can be true at once, and saying so is the answer.** "The number is real AND the reaction is
time-stamped to it AND it did not cause the multi-week decline" is a coherent, useful result. A single
verdict would lose whichever part you dropped.

**End on the number that resolves it next time** — a level to watch rather than a re-argument. An attribution
claim that changes no position is still worth settling, because it tells you which story the market is
trading.

## Before the CAUSE, measure the SCOPE

**"Why did X dump — did we get bad news?" is unanswered until you know whether X moved ALONE.** A
crypto-specific event leaves equities untouched and gold unbought; a macro de-risking takes the whole risk
complex down and crypto is just the highest-beta leg. **Compare the session across `SPY`/`QQQ`, `GLD`, `TLT`
and `VIXY` before hunting a headline** — an index that fell further than the coin, with gold and bonds bid,
is a rotation, not a crypto story. Then state the cause as inference unless you ran the timestamp test above.

**And a round number is not a level.** Asked *"what happens if we break $X"*, name the nearest MEASURED level
and the gap to it, or say there is none — never describe a false floor. Note separately that a breakout which
fails invalidates the low it was built on, not the high it failed to hold.

> Full procedure, the cross-asset reading table, the failed-breakout worked example and the reporting shape:
> `references/selloff-scope-and-levels.md`.

## Institutional and policy claims — "who decides" is measurable, and the obvious axis is usually the wrong one

A question like *"what happens to our market if the government changes hands?"* is not a forecast and not
a price claim. It is a claim about **who holds the pen**, and that has a method.

### Map the decision-holders — never score the body

**The tempting build is a composite index over every member (a "crypto friendliness score" across 535
people). Do not build it.** It is unverifiable, it is wrong in exactly the seats that matter, and no reader
can check a number that averages 535 opinions. **Name the people who actually decide and quote their record:**

- the committee chairs and ranking members with jurisdiction over the thing,
- the agency head writing the operative rules,
- the named analysts the sell-side quotes, with the quote.

**A handful of named people with quoted evidence beats a composite over a whole body**, because every line of
it can be checked by the person reading it. State the method in the artefact: *"named chairs and ranking
members only; every opinion carries its source; anything unverified is marked."*

### A posture is not a prediction, and a party label is not a policy

**Do not map "pro-crypto" / "anti-crypto" onto parties and stop.** The live fault line almost always cuts
across the obvious axis, and finding it is the whole value of the exercise. **Ask who GAINS from a
restriction, not who is friendly.** Measured: the sharpest live risk to a stablecoin reserve was not
hostile-to-crypto legislators at all — it was **banks plus progressive legislators aligned against platforms
paying interest on stablecoins**. The people who had killed the industry's own bill were the natural allies of
the people who wanted the yield banned. **"Hostile to your bill" and "hostile to your position" are different
claims, and the second is the one that matters.**

### Watch the instrument that has stages — not the bill that has none

**A dead bill is not watchable; a rulemaking is.** Once legislation fails, the operative rulebook moves to
agency rulemaking with dated, observable stages:

> OIRA clearance → NPRM published → comment open → comment close → final rule

Record each stage with its date, and mark unobserved stages as **not yet observed** rather than assumed. A
bill that failed a vote and expires with a Congress has no stages to watch — saying *"we are tracking it"* is
then a claim with no observable.

### Called is not certified, and a projected result is not a result

**"Projected", "called" and "certified" are three different claims**, and the last is the one that will
embarrass you if a recount moves a single seat. Write the strength of the result into the sentence, and keep
outcome counts separate from *counting* counts — a live tracker showing seats-yet-uncalled is not a result.

**And when a market read is available, read it rather than predicting it.** A widely-expected reaction is a
hypothesis: measured on this class, crypto did **not** sell off on a political outcome the whole street had
labelled bearish — the fear had been about a different sector entirely, and the tape was higher within twelve
hours. **Report what the market did, not what it was supposed to do**, and treat the failed consensus call as
the finding.

### Timing: a policy file is stale in weeks, an instrument file is stale in quarters

**Give every policy artefact an `as_of`, and re-date it before it is quoted for a decision.** Individual
votes are final; market reactions and committee line-ups are not. **Anything that is UNVERIFIED must stay
labelled UNVERIFIED** — a jurisdiction watch seeded with plausible-sounding instrument names is worse than an
empty one, because someone will act on it.

## Confirmation is not an edge

If the claim's followers reach for names your list already holds, that is a **confirmation of the selection
and adds no information**. Say so explicitly rather than presenting it as a discovery.

> A thesis the crowd has just discovered is not an edge; it is a crowd.

The next question is always: **does our exposure actually match what the claim is about?**

- A forecast about a *market* is not a forecast about the *ticker* people use as a proxy for it. Separate
  "the platform's governance token" from "the tokenised asset itself" — those are different bets, and only
  one of them is the thing the headline describes.
- Check the positions: the two exposures are often at *opposite* ends of their range at the same moment. If
  they are, that contrast is the answer, not a footnote.

## The headline is a claim with its own verb — check it against the body before anything else

**A title is a compressed assertion, and compression is where claims get upgraded.** Compare the verb in the
headline to the verb in the reporting underneath it, and to the primary source, before spending a single tool call
on the substance.

Measured shape: a video titled *"<Person> Accepts: Return as CEO"* whose own transcript said *"is **considering** a
comeback"* and *"the board said **no formal process** has been initiated"* — and whose attributed source additionally
reported the board approaching an **outside successor**. The title's verb was two steps ahead of every source in the
piece: *considering* → *accepts* → *returns*. The body was honest; the headline was not, and the headline is what
travels.

- **Extract the operative verb and rank it.** *rumoured < reported < considering < agreed < signed < effective*.
  A claim is only as strong as its weakest stated step, and a headline that jumps a rung is a different claim.
- **Quote the body's verb back, with its attribution** (*"the FT reports he is **considering**"*), and name the gap
  between that and the title explicitly. Do not silently adopt either.
- **Look for the counter-fact in the same reporting.** A piece that also says a successor is being approached points
  the *opposite* way; the omission of that line is usually the difference between analysis and advocacy.
- **State what would settle it**, and prefer a dated primary artefact — a filing, a press release, a named officer —
  over any number of outlets restating one wire story. *"No source says he accepted"* is a finding; *"nobody has
  denied it"* is not.

**Compression widens the NOUN too, and the noun decides whether it applies to you at all.** The verb ladder
catches *considering → accepts*; the noun phrase catches *"traditional markets" → "derivatives markets"* and
*"perpetuals" → "perpetual contracts on energy commodities only"*. Measured: a viral post announced that an agency
would discuss *"24/7 trading in traditional markets"*; the agency's own release said **"derivatives markets"**, and
the request-for-comment underneath scoped its perpetual half to **physically delivered or storable energy
commodities**. Two widenings, and the second one decides the answer — an energy-perp framework creates **no** route
for an equity perp, which was the only part we cared about.

- **Read the primary document's TITLE and scope line and quote the exact noun phrase.** A sub-heading is often the
  most honest sentence in the whole release.
- **Check the jurisdiction boundary.** Different agencies own different instruments: a derivatives regulator's view
  of "markets" does not reach securities, so an adjacent regulator's interest in a *neighbouring* asset class is
  **not a door** into ours. Say which agency, and which instrument, before implying anything opens.
- **Check the STATUS of the process.** A roundtable is not a rule; an agenda with no published speakers is not even
  a roundtable yet. "Will discuss" is the weakest verb in the class — rank it below "proposed" and far below
  "adopted".
- **Check whether the input window is still open before proposing to contribute.** Measured: the comment period had
  closed **months** before the announcement circulated, with the count already published. "We should comment" is
  advice that cannot be followed, and it reads as competence until someone checks the date.
- **Check who the event is FOR.** An industry roundtable taking speaker nominations is not a public-comment channel;
  confusing the two turns a press release into a plan of action.

**Then ask whether it moved anything.** An announcement that changes no measurable input is worth reporting as
**priced already / not priced yet**, with the number that shows it — a flat close on the day a story broke is the
answer, not a footnote.

## Recency: a search index is not a wire

**A search result is true when it was WRITTEN and may be false when you READ it.** Every result carries a
publish date; compare it to the claim's date before using it to adjudicate anything. **A result published
before the claim cannot refute the claim** — it can only describe the earlier state.

Measured shape, and it is the one that embarrasses you: a body publicly refuses a decision for days, then
reverses it in a single announcement. Search for the question afterwards and **the top results are all the
refusal** — high-ranking, well-indexed, carefully argued. Every one is accurate. Together they describe a
world that no longer exists, and you will quote them as the current state and tell the user their breaking
news is wrong.

- **When the user reports something hours old that contradicts your search, "my index is stale" is the FIRST
  hypothesis, not the last.** Recency lag is the default explanation for a fresh contradiction, and treating
  the user's report as the claim to be falsified inverts the burden for no reason.
- **Go to the issuing body's own feed before contradicting anything.** A company newsroom, a regulator's
  release page, an exchange announcement — one fetch settles it. An aggregator restating a wire story is
  never the primary artefact, and a press release is.
- **A fact-check headline is evidence the claim was VIRAL, not that it was FALSE.** Never cite one as proof of
  falsity without opening it. The existence of "fact check: was X true?" tells you X spread widely; it says
  nothing about which way the answer went, and the article is usually about a *different* version of the claim.
- **Check what the primary document says beyond the headline claim.** A reinstatement release that also
  discloses an ongoing investigation is a materially different fact pattern from a clean reversal, and only
  the primary source carries it.
- **When you are wrong, correct it loudly and name the mechanism.** State the source and timestamp you used,
  say plainly what you got wrong, and name the rule that failed — not "I apologise" but "I read a dated index
  as current state, and here is what I will check first next time." A quiet correction reads as two answers.
- **Do not let the standing posture harden.** The habit of checking primary sources is right; the habit of
  assuming a startling claim is false, because startling claims are often false, will eventually be wrong in
  public. Verify, do not disbelieve by default — they are different operations and only one of them is yours.

## Precision honesty

- **Report the quantity in the unit THE READER DECIDES IN — a raw token/byte/count is not actionable.**
  The reader will convert it themselves, silently, by guessing the rate, and they will guess wrong in the
  direction that flatters the number. Measured: a wallet holding was reported as **"~26 CELO"** with no
  quote-currency figure; the reader took **26 for dollars** and reasoned about it — while the value at
  $0.0841/token was **$2.20**, a **12x overstatement**. The token count was correct and the report was
  still wrong, because the decision ("is this worth moving?") is made in the quote currency.
  **Convert before reporting and print both, with the rate's source and time:**
  `26.14 CELO ≈ $2.20 (at $0.0841, <source>, <time>)`. Cross-check the rate against a second,
  independent source before it carries a currency symbol.
- **Where a unit is AMBIGUOUS, the ambiguity is the defect.** A ticker that reads like an amount, bytes vs
  MiB, a count vs a rate, per-day vs per-year, a percentage of a pool vs of a position — the reader cannot
  tell an ambiguous unit from a wrong number, and will supply their own reading.
- **A published percentage with no stated PERIOD is not quotable — decline it out loud.** The same figure can be
  a since-inception return, an annualised yield or a trailing-week payout, and the three differ by orders of
  magnitude. Measured: a vendor page listed **6.94% · 6.18% · 4.14%** beside four portfolio products with **no
  period anywhere on the page**; quoting any of them as "the yield" would have invented the most decision-relevant
  fact. The correct output names the number, says the period is unstated, and does not rank or compare them.
  **This is the same refusal as an un-cross-checked APY** — a figure whose denominator the publisher withheld is a
  marketing asset, not a measurement.
- **Never render a real value as zero — format by magnitude.** A formatter that divides by 1e6 and always prints
  "M" turns a genuine **$37,816** book into **"$0M"**, on exactly the small positions where the number is the
  whole question — measured, that hit **10 of 13** tracked markets, every thin one. Rounding a number to zero is
  the same defect as reporting UNKNOWN as UP: the value existed and the card said it didn't. Use adaptive units
  (`$10.6M` / `$37K` / `$812`) and keep an explicit `$0` for a genuine zero, so "small" and "empty" never share
  a rendering.
- **When you notice you shipped a raw unit, correct it in place and say that you corrected it.** Do not
  let the next message quietly switch units as if the first had been right — a silent unit change reads as
  two different measurements of the same thing.
- **A range presented as a forecast is a direction, not a prediction.** A stated `$3T–$10T` is a **3.3×
  spread** — report the multiplier, because it converts a precise-looking number back into what it is.
- **Name the carve-out.** "almost entirely a valuation effect", "driven by price, not by flows" — the
  qualifier is frequently more informative than the headline figure, and the source usually says it.
- **A forecast about an industry is not a return available to a participant.** Scale framing ("$3T market",
  "$1B TVL") describes the size of a pool, not the yield to one person in it.
- **Never round a hard number into agreement.** If the data contradicts the premise, say the premise is
  wrong, cite the number, and move on. Agreement because the user said it is worth nothing.

## A published series has a DATE, an ORDER and a LENGTH — verify all three before you quote it

Two silent failures dominate public statistical APIs. Neither returns an error; both return plausible numbers.

- **Check the ORDER of the rows before you pick "latest".** The BLS public API returns observations
  **newest first**. A probe that sorted ascending and took row 0 reported **October 2023** as the current shelf
  price — a correct number from the wrong year, which survives review because nothing about it looks wrong.
  Sort explicitly on `(year, month)` with a stated direction, and never trust the response order.
- **Check what the AGGREGATE parameter actually did.** The World Bank CPI endpoint accepts `country=all`; with
  it, a per-country loop returned the **same figure for twelve different economies**. Treat a unanimous result
  across independent sources as a **data error, not a finding** — twelve countries do not share a CPI. Fix:
  one country per request, and print the country name beside the value so the bug is visible.
- **Print the as-of period next to every value, and read it out.** Annual series lag years (World Bank CPI's
  newest full year was two behind); monthly series lag a month. **A correct number from the wrong period is
  worse than an error, because it survives review.** Never describe a lagging series as a nowcast — say
  "history, not current" in the same line.
- **A stalled source is COULD NOT READ, never the last value you saw.** Rate-limited statistical APIs stall
  mid-loop; a country that did not answer must print as unread, not silently vanish from a table that still
  looks complete.
- **Cross-check one value by hand before looping.** Pull a single well-known series first and confirm it
  matches a published figure you already know. One confirmed value tells you the order, the units and the
  aggregate behaviour before you spend twelve calls learning it the hard way.
- **A period average needs N x periodicity bars — assert the count, do not assume the endpoint gave you enough.**
  Measured: a "200-week" average computed over 1,000 *daily* bars is a 143-week average, and it printed
  **$77,746** where the true 200-week figure from 375 *weekly* bars was **$68,373** — a 14% error in the one
  number a "is it below the long-term mean" question turns on. The bar count was correct for the request and
  wrong for the label. **Fetch the N bars at the periodicity the name implies, or fetch N x periodicity daily
  bars, and print `len(series)` beside the result** so the label can be checked against the input. A moving
  average is defined by its window; an endpoint silently truncated at 1,000 rows redefines it.

## Reusable keyless measurements

You can measure a macro premise without any paid feed:

```python
# Currency basket — a free, keyless FX timeseries (build the basket, do not chase a DXY quote)
# https://api.frankfurter.app/<start>..<end>?from=USD&to=EUR,JPY,GBP,CHF
# Equal-weight the moves. USD/EUR +3.5%, USD/JPY +4.0%, ... -> basket +2.8% = dollar STRENGTHENED.

# Hard-asset cross-check — the market's own vote on the same premise
# https://coins.llama.fi/chart/coingecko:tether-gold?span=61&period=1d   (keyless, ~0.1s)
# Endpoint caps at span=61: ~60 completed days plus today's still-forming point.
```

- **Mind the direction convention.** In `USD/EUR`, a *rising* number means EUR per USD rose, i.e. the dollar
  **strengthened**. State the sign convention in the reply or the reader will invert your conclusion.
- **Prefer a basket over a single pair.** One currency can move for its own reasons; four assert something
  about the dollar.
- **Reserve-share and flow statistics are not price statistics.** Quote them from the official source (IMF
  COFER, BIS turnover) and give the release period — they are quarterly, not live.

## Grading a claim later — the rules that keep a scoreboard from becoming an advertisement

Checking a claim once is an argument. **Grading it at a date is an instrument**, and the instrument is only
worth reading if the verdict is mechanical. These rules exist because every shortcut here flatters whoever
is doing the scoring.

1. **Write the falsification test at entry, not at resolution.** "What would make this wrong" must be recorded
   with a number and a date in the same line as the claim. A test written after the outcome is visible is not a
   test, it is a rationalisation, and it will always fit.
2. **Apply the test AS WRITTEN at resolution.** If the entry turns out to be under-specified ("closes below the
   levels callers named" — which levels?), you may substitute a defensible reading, but **state the substitution
   in the same record**: *"the entry never recorded the levels, so this was applied as 'no breakout — the month
   closed below its open'."* An undisclosed substitution is a different claim being graded.
3. **Never take a verdict on a technicality in your own favour.** When the narrow test and the claim's plain
   meaning diverge, score the plain meaning and disclose the divergence against yourself. Measured: a call about
   *"structure repairs"* had a literal test ("no higher low prints") that a **+0.19%** higher low technically
   satisfied — scoring it a hit would have been arithmetically correct and substantively false. The verdict went
   against its own author and said why. **A ledger that scores only other people is an advertisement; one that
   scores itself generously is the same thing with better manners.**
4. **DUE is not MISS.** Past the date with no measurement means *unmeasured*, and no verdict may be issued. Only
   a measurement decides. Keep *unmeasured* and *evidence packed, awaiting a human judgement* as **separate
   states** — they are reported differently on air and mean different things about the instrument.
5. **Withhold derived statistics below a stated sample floor.** A hit rate over three resolved calls is noise
   wearing a percentage; print the counts and *"withheld — n of 5"* instead. State the floor where the number
   would otherwise appear.
6. **A ratio that cannot be empty cannot be trusted.** The instrument must be able to publish *"0 resolved"*
   for weeks and still be doing its job. An episode or report that manufactures a hit rate from an empty sample
   has destroyed the only thing the scoreboard was for.
7. **A test that cannot resolve as written is VOID, not open forever** — and a VOID is excluded from the ratio,
   because it is neither a win nor a loss.

**The window belongs in the test.** "Bonds rallied" and "bonds didn't" can both be true of the same event
measured across the decision day versus the two sessions after it. **If a claim's test does not name its
measurement window, the entry is defective at birth** — add the window (which bars, which close, which
close-of-business) before the claim can be graded, and say so when the ambiguity is discovered late.

**Two-lane resolution, for judgement-bearing claims:** the machine-checkable half (price, filing, date, on-chain
fact) is resolved by a scheduled measurement with its receipt attached; the interpretive half ("dovish tone",
"the market liked it") is **flagged for the human** with the evidence packed and the verdict withheld. A cron
that grades tone is inventing a verdict, and a human asked to grade without the numbers is guessing.

## Pitfalls

- **Do not write the mechanism before running the case.** The *reason* a number behaves as it does is the
  part most often guessed backwards. Run the case, then describe it. (A range window that includes today's
  live candle *inflates to contain* the price — the opposite of the intuitive "compresses the range".)
- **Do not measure the part that is easy and report it as the whole claim.** A currency's 12-month move does
  not answer a question about a successor currency 10 years out.
- **Do not let a labeled gap become an implicit estimate.** "I could not get the 1-year figure" is a
  complete and honest report; a plausible-looking derived number is not.
- **Do not treat a source's own label as the finding.** "Capital out of reserves" is not "capital into
  another currency" — reserve managers diversifying out of reserves into gold is a different event from a
  reserve-currency transition, and the source often names the difference itself.
- **Do not present a verdict with no action.** End on keep / hold / change-nothing plus the reason. A claim
  that changes nothing is a legitimate result and should be filed as one, not dressed up.
- **File it where the measured work lives.** Extend the existing note on that topic rather than writing a
  fresh one; the numbers are what a future argument is against.

## Reporting shape that works

This shape was accepted on every claim raised:

1. What the claim actually says (source, timestamp, reach if given).
2. **What the crowd/thread says** — and whether any of them answers the question that was asked.
3. **The measured part**, with the window and the source named, in a compact key/value block.
4. The three-part decomposition, showing which parts fail.
5. **Where the claim still pays** — the actionable instrument, tied to a number we already watch.
6. **Verdict** + what was filed.
7. **The gap you could not measure**, stated last and plainly.
