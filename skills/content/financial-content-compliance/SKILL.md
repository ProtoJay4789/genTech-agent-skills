---
name: financial-content-compliance
description: "Use when publishing finance content or disclaimers."
version: 1.0.0
author: protojay (SOCIAL seat)
license: MIT
tags: [compliance, finance, publishing, disclosure, youtube, sec, cftc, ftc, fca, disclaimers]
metadata:
  hermes:
    tags: [compliance, finance, publishing, disclosure, youtube, sec, cftc, ftc, fca, disclaimers]
    category: content
    related_skills: [grounded-citations, monetized-distribution-gates, claim-provenance, measured-claim-check, yt-package]
---

# Financial content compliance — what protects a publisher, and what is ritual

## When to Use

- You are about to publish content that discusses markets, positions, trades, prices or a financial product —
  a show, a clip, a thread, a newsletter, a caption.
- You are deciding whether to monetise it (ads, sponsor, affiliate, product) and need to know what that changes.
- Someone asks "do we need a disclaimer?" — which is usually the wrong question.
- You are drafting a script and want the shape checked before a voice is generated, or a claim about your own
  positions is about to go on screen.

**Not for:** whether a *market claim* is true (that is `measured-claim-check`), or whether a platform pays out
at all (`monetized-distribution-gates` covers the payout gates; this file covers the content rules).

## RULE ZERO — a disclaimer is a statement that must itself be true, not a shield

Liability turns on four things, and a disclaimer touches none of them directly:

| what decides it | question to answer in writing |
|---|---|
| **the kind of speech** | general publication, personal recommendation, or marketing of a product? |
| **your own interest** | do we hold, sell, or get paid for what we are describing? |
| **misleading-ness** | is every claim dated, sourced, and falsifiable? |
| **platform policy** | separate from law: can this content monetise at all? |

**"Not financial advice" is ritual.** If the content *is* advice, saying otherwise can be its own misleading
statement. What does legal work: **position disclosure, compensation disclosure, non-personalisation, a dated
as-of stamp, no guarantees, and no directed call to an individual.**

## Procedure

1. **Classify the speech before writing a word.** Publication = general circulation, non-personalised, no
   client relationship, no discretion over anyone's money. Recommendation = directed at a person ("you
   should"). Marketing = anything sold in the same breath. Write the classification into the brief — the
   script follows from it, not the reverse.
2. **Check the interest.** If the content names an asset we hold, a **spoken position card** is mandatory
   *before* the number: what we hold, size, last trade date, as-of stamp.
3. **Check the compensation.** Sponsor, affiliate, product, membership — disclosed **at the point of mention,
   in the same medium**, not in a description or footer.
4. **Write measurement, not prescription.** First person, past tense, dated, sourced. Every number carries an
   `as of <date> <time> UTC`.
5. **Lint the script mechanically before recording** (`scripts/script-lint.py`). A WARN is not a pass; it is a
   line someone must defend before the record button.
6. **Check platform policy as a separate gate.** Legally clean content can still be unmonetisable — see
   `references/platform-content-policy.md`. Decide revenue on that basis, not on view counts.
7. **State what you could not verify, then buy the lawyer's hour** — with four *classification* questions,
   never "review our disclaimer". Template at the end of this file.

## Always-on rules

- **No second-person prescription. Ever.** "We are waiting" is allowed; "you should buy" is not. The lint
  word list exists because this is the line between publishing and advising.
- **Three spoken statements replace the boilerplate** (spoken, in the video — a description-only disclosure
  fails both the FTC's in-video rule and Google's no-rollover rule):
  1. **Position** — *"We hold X, size Y, we have not traded since <date>. As of <stamp> UTC."* (flat: "We hold
     none of this.")
  2. **Payment** — *"Nobody paid us for this episode and we sell nothing in it"* — or the sponsor, by name, at
     the first mention of what is sold.
  3. **Purpose / non-personalisation** — *"a record of what we measured and did with our own money, not a
     recommendation for you, not tailored to you."*
- **Stop relying on:** "not financial advice", "educational purposes only", "do your own research", any
  footer-only block. Keep them if you like; never treat them as protection.
- **Never present an AI persona as a human expert on finances.** Platform policy refuses monetisation to
  exactly that shape (`references/platform-content-policy.md`). Name the voice as synthetic on screen, and
  attribute opinions to the human who holds them.
- **In a host-led format, the obligations follow the human voice — and the agent is a source, not a persona.**
  A human host consulting an attributed AI is **not** the "AI-generated persona presenting itself as a human
  expert" shape that platform policy refuses to monetise — **but only conditionally**: (a) the agent is attributed
  out loud **and** on screen at first appearance, (b) it never delivers advice, a call or an opinion, (c) the human
  carries all three disclosures in his own voice, in the body of the video. Drop any one in the edit and the
  protection goes with it. **And lint the host's lines too** — a second-person call from an identifiable person is
  closer to the regulated conduct than the same words in an agent voice.
- **"The council comes in from time to time" is an appearance, not a role.** (Jordan, 2026-11-02: *"I'll just be
  the talking point and the council will come in from time to time."*) A segment where an agent voice speaks must
  open by naming it aloud and on screen — *"this is the council's read, produced by our agents"* — and close back
  to the host. A recurring segment is exactly where attribution gets dropped in the edit, because it feels
  established after episode two. **It is never established; the audience is different every time.**
- **Capability claims about your own tooling must be literally true, per segment.** "Produced by this tooling"
  is a factual claim with enforcement history behind it — a false one is a fraud question, not a marketing
  question.
- **Never become a signals service.** "Signals" is the word that converts publishing into a prohibited
  category on ad platforms and into advisory territory under securities law.
- **Cite primary sources; write the gap plainly.** Law-firm summaries are pointers, not authority. When a
  primary page or statute settles it, quote it and date the retrieval. When only secondary coverage exists,
  say so (`grounded-citations`).
- **When the research contradicts your own earlier assumption, state the correction in the artifact.** A
  silent fix leaves the wrong version in circulation, and the next reader inherits it.

## Pitfalls — each with the mechanism

- **Answering only the question you were asked.** The policy that governs your format usually sits one heading
  away from the one you were sent to check — the automation clause and the AI-persona monetisation ban were on
  the same page. Read the neighbouring headings of the same primary document before you close the research.
- **Generalising one regulator's publisher exclusion to another.** The securities statute excludes the
  publisher of a *"bona fide newspaper, news magazine or business or financial publication of general and
  regular circulation"*; the commodity statute excludes the *"publisher or producer of any print or electronic
  data of general and regular dissemination"*. Similar idea, different words, different conditions, no shared
  case law. Quote the statute you are actually relying on.
- **Assuming disclosure is the safe side of every line.** Publishing your own book is safer on exactly one
  axis (publication vs advice). Without a position disclosure it becomes the touting fact pattern instead —
  the failure the big influencer enforcement cases turn on is **non-disclosure**, not a missing disclaimer.
- **Treating "we're a publisher" as covering the derivatives side.** That analysis runs on different
  definitions and a different, conditional carve-out; and taking other people's money is a separate prong from
  advising them. See `references/cftc-cta-cpo.md`.
- **Letting the title decide monetisation by accident.** Platforms publish profanity tiers for titles and
  thumbnails; a strong word in the title is a revenue decision, not a brand decision.
- **Putting the disclosure where the audience will not meet it.** Ad-platform rules and the FTC say the same
  thing in different words: visible without a click, in the video, not in the description or a link.
- **Quoting a policy as if it were enforcement.** Policy text tells you the rule, not how it is applied. Say
  which one you have, and say when no published decision tests your case.
- **Buying "disclaimer review" from a lawyer.** The disclaimer follows from the classification. Spend the hour
  on classification: publication vs marketing, where personalisation starts, which instrument classes are in
  scope, which jurisdictions you actually publish into.

## The four lawyer questions (use verbatim, fill the blanks)

1. Does selling <the product/kit> change this content from publication to marketing, and if so which lane do we
   choose to stay in?
2. Where exactly is the personalisation line — public Q&A? live chat? a paid group? answering one viewer?
3. Do descriptions of our own positions in <instrument classes> implicate the derivatives regime, given we are
   not compensated for advice?
4. We publish from <jurisdiction> to a global audience: what is the minimum so a viewer in <stricter
   jurisdiction> does not convert our publisher position into a regulated promotion there?

## References

- `references/sec-publisher-lane.md` — the adviser definition, the publisher exclusion, the case that reads it,
  and what makes a publication stop being "bona fide".
- `references/cftc-cta-cpo.md` — commodity-statute definitions (CTA, CPO), the conditional publisher carve-out,
  and the table that answers "does describing our own book cross the line?".
- `references/platform-content-policy.md` — platform monetisation (automation, AI personas, title profanity),
  ad-platform financial and prediction-market limits, FTC in-video disclosure, FCA social-media promotions.
- `scripts/script-lint.py` — the mechanical gate: blocks second-person prescription and certainty language,
  warns on trade verbs, requires the three statements plus an `as of` stamp.
