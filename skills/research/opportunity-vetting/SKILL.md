---
name: opportunity-vetting
description: "Use when vetting an opportunity or reviving an old build."
version: 1.0.0
author: gentech
license: MIT
tags: [opportunity, verification, curriculum, funding, career, vetting]
metadata:
  hermes:
    tags: [opportunity, verification, curriculum, funding, career, vetting]
    related_skills: [link-research-summary, career-application-execution, model-routing]
---

# Opportunity vetting

Jordan forwards money offers, fellowships, curricula, grants, tool launches and job leads constantly. The job
is **not** to summarise them — it is to say whether they are real, whether they fit, and what the honest gate
is. Four always-on rules, then the procedure.

## When to Use

- Jordan forwards a funding offer, fellowship, grant, accelerator or prize.
- Jordan shares a curriculum, course, roadmap or skill list and asks what to do with it.
- Jordan shares a job posting, or asks you to pull up roles (entry-level, remote).
- Jordan asks *"is this real?"*, *"should we do this?"* or *"how long would this take me?"* about any of the
  above.
- A tool or rail launch is shared and the question is whether to adopt, park, or ignore it.
- An old build is being **revived** for a programme that once accepted contributions — then the question is
  whether that programme still exists and still pays, not whether the code compiles.

**Not for:** extracting a link's contents (that is `link-research-summary`) or drafting and submitting the
application once the decision is made (that is `career-application-execution`).

## The always-on rules

### 1. Verify the counterparty before recommending — a no-strings money offer has two possible parents

"$50K, no equity, no strings, 10-minute application" is either a genuine programme or a **data harvest**, and
the announcement cannot tell you which. **Do not recommend it until all three hold:**
1. **Named people who exist** — founders with real public profiles (a personal site, a LinkedIn history).
2. **Independently checkable advisors** — institutions verifiable *without* trusting the page (a university
   profile, a firm's people page).
3. **A track record with visible outcomes** — at least one *prior* programme that ran to completion with
   **named winners**, not "winners announced" as text.

**Read the fee-free tells the right way:** they ask for a *portfolio*, not payment, credentials, or a wallet.
Absence of a payment ask is evidence; presence of one is a stop.

### 1b. An inbound offer you never asked for is a FRAUD question, not a fit question

A recruiting email is not an opportunity until you establish that the job exists. The fraud shape is
stable and cheap to test — **five measurements, any one of which ends it:**

1. **Did the candidate actually apply?** Query the application registry, not memory. An interview offer for
   an application that does not exist is the whole answer. (An unsolicited "we saw your profile" offer on a
   lane the user has never worked is the same finding with a friendlier sentence.)
2. **How old is the sending domain?** `curl -s "https://rdap.verisign.com/com/v1/domain/<domain>"` → the
   `registration` event. A firm hiring across timezones does not run on a months-old domain with a one-year
   registration, and **an obscure registrar in a different jurisdiction from the claimed HQ is corroboration**.
3. **Does the business it claims to be have a careers page?** Fetch the site and count `career|job|jobs|team`.
   Zero hits on a site that sells courses, coaching or "community" is decisive: they sell advice, they do not
   run a desk.
4. **Does the named person exist?** Grep the site, and the web, for the sender's name and title. A Head of HR
   who appears nowhere is a persona.
5. **What is the channel?** *"The interview will be conducted via text"* plus a **Telegram/WhatsApp handle
   instead of a company address** is the confession, not a convenience: it moves the conversation onto a
   platform that keeps no records and cannot be subpoenaed.

Secondary tells that cost nothing to notice: a generic salutation with no name, BCC-to-self (a mail-merge
blast), and a role that does not match the business model.

**State the script, not just the verdict.** The victim's protection is recognising step two before they reach
it: warm chat → a "trial" or "test trade" on a platform the sender controls → **a small first withdrawal that
works** (the credibility purchase) → a fee, a tax, a minimum balance, or "fund the account to unlock profits" →
the deposit is gone with no counterparty and no regulator.

**Two rules for the response itself:**
- **Never tell the user to reply "not interested".** A reply confirms a live address and a reading human. The
  instruction is: don't engage, mark spam, block the domain.
- **Do not log it in the application funnel.** A fake application poisons callback statistics that other
  decisions are priced against. File it as its own vetting record instead.

### 1c. A lead your OWN pipeline emitted is still a claim — verify it at the employer's board

A row coming out of your scanner is **not** evidence the job exists. Aggregators syndicate, repost and keep
closed reqs up; a job page that answers `200` may be a tombstone. Verify before recommending — cheapest check
first.

1. **Does the employer have an ATS board? Query it directly and match the title.** An aggregator row is a
   copy; the employer's board is the source. This one call settles most cases:

```bash
curl -s "https://boards-api.greenhouse.io/v1/boards/<token>/jobs" \
  | python3 -c "import json,sys,re; [print(j['title'],'|',j['location']['name'],'|',j['updated_at'],'|',j['absolute_url']) for j in json.load(sys.stdin)['jobs'] if re.search(r'<title>',j['title'],re.I)]"
curl -s "https://api.lever.co/v0/postings/<token>?mode=json"
curl -s "https://api.ashbyhq.com/posting-api/job-board/<token>"
```

2. **HTTP 200 is not liveness.** A Greenhouse job URL answers `200` for a closed req. Read the API record —
   `first_published`, `updated_at`, and body length. No API record for the id is the tombstone signal, not a
   fetch failure.
3. **A company with no ATS whose only action is a company-wide form is a funnel, not a requisition.** If the
   careers page leads to one generic Typeform/Google Form and no role-specific application, no posted job
   exists — it is a talent-pool catch-all, and the "opening" may have no headcount behind it.
4. **The same JD under multiple "employers" at an hourly rate is a data-labelling funnel.** Identical
   responsibilities, near-identical wording, `$N/hr` contract, "portfolio required" → AI-training or
   annotation work wearing an engineering title. Before recommending, search a distinctive sentence from the
   description and see whether it reappears under another company name.
5. **An aggregator's pay figure is the aggregator's claim.** When the only compensation evidence lives on the
   feed and the employer page states none, mark it unverified in the same line and never quote it as a band.

**Report which items verified and which did not, with the check that settled each.** *"Six of seven live, one
  does not verify"* is the useful sentence. *"All verified"* derived from status codes alone is the exact
  failure this rule exists to prevent — and expect the most attractive-looking lead to be the one that fails,
  because an aggregator title is optimised to be clicked.

### 2. The ARTIFACT RULE — an item is complete only when it produces a public artifact with a receipt

A repo, a live URL, a measured number. **Never a completed module, certificate, or course.** Jordan's record
is scored on what he built, and a curriculum's finish line must not be presented as a credential.

### 3. Two clocks — never let one stand for the other

- **Artifact time** — hours to produce the deliverable ÷ his actual weekly pace. A *build budget*.
- **Readiness time** — time until he is hireable. The widely-quoted "6 months to FDE" assumes an
  *experienced developer*; sources converge on **18–24 months** without a production-engineering background.

When asked "how long will this take me?", quote the artifact number **and** the readiness number in the same
breath. A build-hours figure standing alone reads as a promise of employability — false precision, and the
exact failure this rule exists to stop.

### 4. Grade before endorsing, and name the gate

Never present an unverified or mis-gated lead as a win. Two shapes recur:
- **Grade a curriculum against what we already run** — mark every item **shipped / partial / genuine gap**.
  Published curricula are written for someone with *no artifacts*, so a large share of the items are things
already running in production. **Adopt such a curriculum as an interview MAP (the vocabulary a case study
probes), never as a syllabus to work through.**
- **A live posting is not an eligible posting.** "Right title, wrong gate" is the common outcome — a
  years-gated or on-site role among remote-first ones. Say so plainly instead of dressing it as a hit.

**Never sequence learning before applying.** The skill lane runs in the *background*; applications start in
week one. Waiting for a curriculum optimizes against an *assumed* bar, and windows close faster than
certificates get earned.

### 5. The earning question is a MECHANISM question — points are not pay

A programme that rewards in **points, XP, credits or "allocation"** is not paying a builder, and no amount of
leaderboard changes that. Read the vendor's own disclaimer **verbatim** and quote it: the recurring text is
*"points have no monetary value, are not an investment, and provide no right or expectation of profit or
redemption"*. A third-party tracker's "earn up to N% of fees / of the points your work generates" is
**UNMEASURED** until it appears on the vendor's own page — aggregators paraphrase launch copy and outlive the
terms they described.

**So the earning mechanism gets named, or the answer is UNMEASURED — never inferred.** The four mechanisms,
most to least real: (1) a payment per deployment or usage, with published terms; (2) a grant with a named
decision process; (3) a conversion of accrued points to a token whose terms are **published**; (4) points whose
conversion is "at our discretion / TBA" — category (4) is not pay, however large the stated pool.

**Verdict vocabulary for a revival, and there are only three:** `REVIVE` / `ARCHIVE AS TEACHING` / `RETIRE`.
Each carries the measurement behind it and **revisit gates that are all checkable** (vendor mainnet live · a
published points→token conversion · a documented payment per deployment, usage or accepted contribution).
ARCHIVE is a complete outcome: the artifact becomes courseware, not a debt.

## The procedure

1. **Read at source, not from the announcement.** Fetch the actual page. If the source is a platform that
   blocks automated reading, **say which claim you could not verify** and name the single question that would
   settle it — never present a match as a confirmed tag.
2. **Ask what it actually is before analysing.** A product, a rail, a curriculum, a job lead and a money
   offer get different work. Getting this wrong wastes the whole pass.
3. **Verify the counterparty** (rule 1) for anything involving money, data, or his name.
4. **Grade it against our stack** (rule 4) and state the gap honestly — including when the gap is on our side.
5. **Answer the timeline question with two clocks** (rule 3) if asked.
6. **Wire the finding to the vault** — brief, queue item, or both. An analysis that changes no file did not
   finish. Offer the next concrete step (draft it, wire it, park it) rather than a menu.

## Pitfalls

- **Do not draw a negative from a probe you have not proved complete.** Absence from a subset is not absence.
  The same shape as declaring a provider dead from one failed chat call when its catalog endpoint answers
  `200`: probe the broad endpoint first, and only a broad failure means the thing is gone.
- **A documented value is not a measured one.** An identifier or figure repeated across enough documents
  starts to look verified. Put it through the API before building on it.
- **Don't explain the obvious.** When the topic is already familiar, skip the architecture explainer and lead
  with the verdict and the gate.
- **The counterparty's own claims are not evidence.** "Winners announced" as text is marketing; a named
  winner on a live page is a record.
- **A surviving API name is not compatibility.** Namespace calls still appearing in a vendor's reference docs say
  nothing about whether the *pattern* is still sanctioned. Read the doctrine page (consensus model, validation
  rules, "which approach to use") and compare it to what the old code does — code that imports cleanly can be an
  exact instance of the anti-pattern the current docs name. Compatibility is three separate reads: the
  dependency pin resolves, the API surface exists, the doctrine is unchanged.
- **An artifact's own header is a claim, not a record.** "Part of <Vendor> <X> Programme" must be checked
  against the vendor's *current* org or portal rather than trusted: programmes get renamed (a template bank
  becomes a points portal), repos disappear, and the submission route moves from "open a PR" to "a steward
  reviews you" — which changes the acceptance rate the plan is priced against. Search the vendor org for the
  surface name; a zero-result search is itself the finding.
- **A pre-launch network has no customers.** Deploying to a testnet or pre-mainnet chain is a **demo of someone
  else's protocol**, never a revenue line. Say which one it is before scoping a build, and never let "we
  deployed" stand in for "we can earn".

## Related

- `link-research-summary` — link extraction and fetch mechanics (user-owned).
- `career-application-execution` — application drafting and submission (user-owned).
- `model-routing` — provider/rail changes and the fallback chain (user-owned).
