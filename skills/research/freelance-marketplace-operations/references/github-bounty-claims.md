# GitHub issue bounties — scanner design and vetting filters

Paid GitHub issues are a real hiring channel (some employers pay per-merged-PR instead of interviewing) and a bad
default hunting ground. This file is the **tool** — discovery surfaces, filters, thresholds, scoring and report
shape for a bounty scanner.

The **decision** — whether to bid, how to pick a first bounty, what to tell the user about odds — lives in
`career-application-execution` → `references/contribution-hiring-channel.md`. When a rule changes, change it in the
file that owns it and leave the other pointing at it; two copies of one threshold drift and the scanner then
contradicts the advice.

## Discovery surfaces, in order of yield

| Surface | Query | Verdict |
|---|---|---|
| Repo-managed bounty programs | `is:issue is:open label:"Help Wanted"` + the repo's own CONTRIBUTING | ✅ best — named process, named price in the title |
| Bounty label ecosystem | `is:issue is:open label:bounty`, `label:"💎 Bounty"`, `label:"Algora Bounty"` | ✅ but farm-dominated; requires the credibility gate |
| `label:hiring` issues | `is:issue is:open label:hiring` | ⚠️ low yield — HR-farm repos and "I'm interested" comment spam |
| Body-phrase matching | e.g. `"open a pull request" "instead of"` | ❌ **never** — a phrase in a body matches guild banks, game servers and bots at roughly 1000:1 noise |

Body-phrase search is a *human* signal, not a machine one. Do not build a scanner on it.

## Credibility gate — a hard reject, not a scoring penalty

A price is a claim. These fields are the only evidence anyone intends to pay.

| Signal | Rule | Why |
|---|---|---|
| No `LICENSE` | **reject** | the contribution may not even be usable, and it is the strongest farm tell |
| Repo < 30 days old AND < 50★ | **reject** | cannot verify the payer exists; farms appear fully-formed |
| < 25★ | **reject** | no visible reputation to hold a payer to account |
| ≥ 1,000★ | bonus | the PR is an employer-visible artifact, which is the actual return |
| ≥ 25 comments | penalty | contested; someone is already in it |
| untouched > 120 days | **reject** | stale — the maintainer is not paying attention |

Measured shape of a farm: 0–15★, **no licence**, a handful of days old, and tens to hundreds of open issues with
prices in the titles. A generic `label:bounty` search returns these first. Filtrate them out before ranking, or the
report hands the user a stranger's unpaid work as an opportunity.

## Claim detection — where availability actually lives

`assignee` is meaningless on these boards: an issue shows `assignee: null` while two people have submitted PRs.
Availability is asserted in the comment thread. Fetch the last ~30 comments per shortlisted issue and treat any of
these as **CLAIMED**:

- `/claim` (boundary-anchored — a bare `claim` matches "claims handling")
- `claiming`, "I'm taking this", "I have implemented"
- "PR opened"/"PR submitted", or a `github.com/<owner>/<repo>/pull/<n>` URL
- "deliverables submitted"

A plain question ("is this still open?") is **not** a claim. Empty or unreadable thread is `UNVERIFIED`, never
"open" — print that distinction rather than defaulting to the optimistic reading.

Keep claimed issues visible in a separate section with the evidence line attached, rather than dropping them. Every
exclusion has to be auditable or the filter becomes as untrustworthy as the boards.

## Scoring rules that survived live runs

- **Price is read from the TITLE only.** Bodies pad and pad-style text yields false prices. A price present in the
  title counts; absence is `UNSTATED`, which ranks **below** a stated price and is never rendered as `$0` — the same
  rule as `UNMEASURED` in a milestone report.
- **Lane evidence must point at an artifact we can show.** Match the issue against existing work (evaluation
  harnesses, tool-calling contracts, model routing, retrieval, infra). If nothing matches, `OFF_LANE` is an honest
  answer and not an insult.
- **Language is a floor, not evidence.** Every bounty is Python or TypeScript, so a lone language mention
  discriminates nothing. Treat it as a small confirmation bonus, never as the thing that admits an issue. Watch for
  the failure mode where `"[$10] Add a favicon python"` scores as in-lane.
- **Rejection reads the TITLE only.** Bug reports routinely name other platforms in the body (a web-surface issue
  whose reproduction notes mention a mobile OS). Rejecting on body text hides real work; lane scoring may read the
  body because a false hit there costs a rank, not the issue.
- **Short tokens need word boundaries.** A two-letter alternation like `ci` matches `favicon`, `special` and
  `efficiency`, letting off-lane issues through. Same defect class as a country token matching a US state name.
- **Engagement farms exist** — "answer the N linked questions", "why did you choose us", "register in ecosystem",
  "star the repo". They pay cents per response, they are never engineering, and they will out-rank real work on
  every naive score.

## The economics: the window beats the fit

Bounty queues clear in **hours**, not days: the best-matching issues go to repo regulars who live on the issue feed,
and one person can claim an entire org's board. So a scanner run once a day is **always late**, and what a newcomer
can actually win is **recent and quiet**, not relevant and contested.

The durable instrument is a **watcher** — new issues only since the last run, silent unless credible + in-lane +
unclaimed all hold. Do **not** build a 24/7 sweep of the whole label space: the measured base rate is farms, and
speed only delivers them faster.

## Before reporting a channel empty, widen the vocabulary

A "nothing available" conclusion from one query set is a query artifact until proven otherwise. Re-run across
several label vocabularies and several search phrasings, and report the counts per query. `0` from eight
vocabularies is a measured negative; `0` from one is a guess wearing a finding's clothes.

## Report shape

State, in this order: issues examined · kept · rejected **by reason** (counts per rule) · then the shortlist with
score, repo scale, comment count, claim state, and the lane evidence. Finish with what the tool cannot claim: a
stated price proves nothing, `OFF_LANE` says nothing about the person, and no scanner can predict whether a
maintainer will accept.
