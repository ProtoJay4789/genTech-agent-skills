# Jobs won by contribution, not application

Some employers run no application funnel at all and say so in writing: you earn the role by shipping a reviewed
change in public. The channel is real and queryable through the GitHub API, but only on the right surface.

## Four surfaces, ranked by yield

| Surface | Query | Yield |
|---|---|---|
| Bounty programme on one repo | `repo:OWNER/NAME is:issue is:open label:"Help Wanted"` | **highest** — curated, priced, actively reviewed |
| Ecosystem bounty labels | `is:issue is:open label:bounty` · `label:"💎 Bounty"` | high volume (thousands), needs a repo-quality gate |
| Hiring-labelled issues | `is:issue is:open label:hiring` | low — largely HR-farm posts with applicant spam |
| Body phrase search | `"open a pull request" "instead of"` | **unusable** — see below |

**Why body-phrase search fails:** a phrase query matches any text that happens to contain the words. One such
query returned **23,194** open issues, dominated by game servers, guild banks and bot projects. The ratio is
roughly 1,000:1 and the good results are not recoverable by paging. **Phrasing is a human cue; labels and repo
identity are the machine cues.** Do not build a feature on phrase matching.

## Read the payout path before reading the work

A bounty programme's own `CONTRIBUTING` (or an equivalent contributor guide) is the authoritative document. Read
it first and extract four facts:

1. **How payment is routed.** Commonly through a freelance platform, which means an account, an identity check
   and a tax form before any money moves. Some guides state explicitly that an unverified payout account risks
   non-payment — quote that back rather than describing the step as a formality.
2. **The proposal gate.** The common pattern is: a bot posts an opening proposal, a human proposes, and **no PR
   may be opened until a proposal is accepted**. This means the first hours are always unpaid and may produce
   nothing. Say so before he commits.
3. **Whether the price is in the title.** Programmes frequently encode it as `[$250] …`. Parse it from the
   title; a missing price means unpaid work.
4. **Whether the target repo accepts outside contributors at all** — some publish a guide and still restrict
   merges to staff.

## Selecting a first bounty

A first bounty should be chosen so the **artifact** does the arguing, not the resume:

- **Domain he can already demonstrate.** A model-routing, evaluation-harness or multimodal-testing bounty is
  winnable from existing work; a language or framework he has not shipped is a learning project wearing a
  bounty label.
- **Repo quality signals:** stars, recent commit activity, whether issues are actually being reviewed and paid
  (closed-and-labelled issues are the evidence), and how long proposals sit unanswered.
- **Scope honesty:** a bounty is 2–6 hours of unpriced work with a real chance of rejection. Compare that
  explicitly against the cost of a normal application, and do not present the channel as a shortcut.

## Availability lives in the COMMENT THREAD, never in `assignee`

An issue showing `assignee: null` can already have two claimants and two open PRs. This market asserts a claim in
prose, so the field the API makes obvious is the one that proves nothing.

Fetch the last ~30 comments of every shortlisted issue and treat any of these as **CLAIMED**:

- `/claim` — boundary-anchored, so a word like "claims handling" does not match
- `claiming`, "I'm taking this", "I have implemented"
- "PR opened" / "PR submitted", or a `github.com/<owner>/<repo>/pull/<n>` URL
- "deliverables submitted" — including **the payable-in-one-day farms**, which are claimed instantly

A plain question ("is this still open?") is not a claim. A thread you could not read is **UNVERIFIED**, never
"open" — say which one you have. Keep claimed issues in the report with the claimant named instead of dropping
them silently, or the filter becomes as untrustworthy as the board it reads.

**This is the check that must run before you name a bounty to him.** A well-matched issue recommended without a
comment read is a recommendation that may have been dead for a day.

## The credibility gate is a hard reject, not a lower score

The highest-volume "bounty" repos are farms: no licence, days old, hundreds of priced issues, near-zero stars.
A price in a title is a claim; these fields are the only evidence anyone intends to pay.

| Signal | Verdict |
|---|---|
| No `LICENSE` | **reject** — the contribution may not even be usable, and it is the strongest farm tell |
| Younger than ~30 days AND under ~50★ | **reject** — the payer cannot be verified |
| Under ~25★ | **reject** — no visible reputation to hold a payer to account |
| 1,000★+ | bonus — the PR becomes an employer-visible artifact, which is the real return |
| 25+ comments | penalty — contested |
| Untouched for months | **reject** — nobody is paying attention |

Rank credibility **above** fit. An issue that matches his evidence perfectly in a repo that may not pay is worse
than a plain issue in a repo that visibly does.

## The window beats the fit

Bounty queues clear in hours. The best-matching issues go to repo regulars who live on the issue feed — one
person can claim an entire org's board in a sitting. Therefore:

- **Recent and quiet beats relevant and busy.** A small unclaimed ticket outranks a large one with three open PRs.
- **A daily sweep is always late.** Recommending a well-matched issue claimed yesterday costs more trust than
  reporting nothing; say "nothing worth bidding today" when that is the truth.
- **The instrument that could work is a watcher** — new issues since the last run, silent unless it is credible,
  in his lane and unclaimed. A broader 24/7 sweep just delivers the farms faster.

## Before reporting the channel empty, widen the vocabulary

One query returning nothing is a query artifact until proven otherwise. Re-run across several label vocabularies
and phrasings and report the count per query. Zero from eight vocabularies is a measured negative; zero from one
is a guess wearing a finding's clothes.

Scanner implementation — filters, scoring, rejection reasons, report shape — lives in `freelance-marketplace-operations`
→ `references/github-bounty-claims.md`. The rules above are the decision; that file is the tool.

## Setting expectations

- **The expected outcome of a first attempt is a rejected proposal, not money.** Competition is public and
  includes people who have completed hundreds of these. He should know the odds before he starts, because a
  silent rejection on a first attempt otherwise reads as a verdict on his ability.
- **The durable return is the public PR and the reviewer relationship**, not the payout. That is also why the
  channel suits someone whose strongest evidence is invisible on a resume: a reviewer can read the diff.
- **Do not let the channel displace the application volume.** A bounty is a slow, uncertain ticket; parallel
  applications are the measurable funnel. Keep the response-rate loop running.

## Verification notes

- The GitHub search API works authenticated on the seats that hold a token; unauthenticated search is rate
  limited to the point of uselessness, and a stale "search is blocked" belief is regularly wrong — re-probe
  before reporting a restriction.
- Authentication is required for label queries at volume; filters like `repo:`, `label:` and `is:` are what make
  the result set bounded.
