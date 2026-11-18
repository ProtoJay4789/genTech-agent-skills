# Paid bounties — vetting a repo before spending an evening in it

A bounty is a paid piece of work published as an issue. The work is real, the money is usually real, and
the failure mode is **spending six unpaid hours on something already finished**. This file is the decision
depth for the `💰 Paid Bounties` section of SKILL.md.

## Discovery — which queries carry signal, and which are noise

Label search is the only workable discovery surface. Body-phrase search is not:

| Query class | Example | Verdict |
|---|---|---|
| Priced-issue labels | `is:issue is:open label:bounty`, `label:"Help Wanted"`, `label:"💎 Bounty"` | ✅ |
| Platform labels | `label:"Algora Bounty"` | ✅ (may legitimately return 0) |
| Body phrasing | `"open a pull request" "instead of"` | ❌ ~20,000 false positives (game servers, guild banks) |

The phrase "apply by contributing" is a **human** signal, not a machine one. Never build a scanner on
prose. Also expect **label vocabulary to fragment** — a market-wide sweep needs several query spellings,
and a single query returning 0 is not evidence the market is empty until the alternates are also tried.

## Credibility gate — the most important filter, and it must be a HARD REJECT

The tell of a bounty farm is a repo that cannot plausibly honour a payout:

- **No licence** → reject outright. Work in an unlicensed repo may not even be usable by the contributor,
  and no serious payer ships without one.
- **Young and small** (created days ago, near-zero stars) with many priced issues → reject. A five-day-old
  repo with 74 priced issues is a funnel, not an employer.
- **Very low stars** (< ~25) → reject. There is no visible reputation to hold a payer to account.

Accepting a farm price is worse than reporting nothing: the headline number is large, so it wins on any
score that rewards price, and it costs the most hours of anything on the list.

## Price handling

- **Parse the price from the TITLE, not the body.** Bodies discuss other amounts and the title is the
  repo's own stated figure.
- **UNSTATED is not zero and not "unknown value"** — rank it below a stated price but never render it as $0.
- **A price is a claim, not a receipt.** Nothing in the API proves anyone will pay. Say that out loud when
  recommending one.
- Reward units are often **tokens or points, not currency** (`N TOKEN`, `N points`). Value is unmeasured
  unless a market for the unit was checked — do not convert it to dollars in your head.

## Claim state — `assignee` is not how this economy works

**The API's `assignee` field proves nothing.** Bounty economies claim by **commenting** — `/claim`, "I'm
working on this", "I have implemented", "PR opened" plus a PR link. `assignee: null` and "open" in the
issue list are both compatible with work that finished yesterday.

Detect on the comment thread of every shortlisted issue:

- literal `/claim`, the word "claiming", "I'm taking this", "I have implemented"
- a `github.com/<owner>/<repo>/pull/<n>` URL, or "PR opened"/"PR submitted"
- a claim bot posting on the payer's behalf (`<org>-pbc[bot]` style) — a bot `/claim` means the issue is
  **live and speakable**, since Algora-style bots post availability on behalf of the repo
- an **empty thread** is not a claim — do NOT reject it; report it as the quietest, least contested shape

Reject a claimed issue **with the evidence line attached** (`who: which signal`), and keep it visible in a
separate excluded list. An exclusion nobody can audit is indistinguishable from a bug.

## The availability window — fit is the wrong ranking basis for a newcomer

**Best-fitting bounties are claimed within hours by people who live on that repo's issue feed.** Same-day
claim rates are normal; a day-old strong match is usually gone. Consequences for the ranking:

- **Weight recency and low comment count above lane fit** for a first attempt. A modest unclaimed ticket
  beats a large prize with three open PRs under it.
- **Few comments = little competition**; a busy thread on a young issue usually means claimed or argued over.
- **A high-value issue with many comments is the biggest trap on the board** — it looks like the prize and
  it is the one most likely to be contested or already done.
- **Being early needs a watcher, not a search.** A daily scan of the whole market is structurally late.
  The only instrument that beats the regulars reads issues *created since the last run* and speaks only
  when one is credible, in-lane and unclaimed — silence otherwise.

## Work-shape filters — what looks like engineering and is not

Reject these by name, they score deceptively well on keyword match:

- **Engagement / quiz farms** — "answer the N linked question(s)", "why did you choose us", "register in
  the ecosystem", "star the repo". They pay cents per unit for content, not engineering.
- **Content and design** — blog posts, copy, logos, Figma work.
- **Wrong-language work** — a ticket whose PRs are native Go/Rust in the repo's own package tree.
- **Deep specialist tickets** in a high-star repo: excellent portfolio material, wrong *first* bounty
  because they cannot be won quickly.

**A language mention is a floor, not evidence.** Every bounty in a given ecosystem is Python or TypeScript,
so "python" in the body discriminates nothing — let a language token confirm a lane match, never create
one. The same for short tokens generally: an unbounded `ci` matches *favicon*, *special*, *efficiency*.

## Reading the issue correctly

- **Run reject rules against the TITLE only.** A body that mentions a platform ("reproduces on iOS") gets
  filtered out of an issue that is about a web surface. **A false reject hides real work; a fair
  off-lane rejection is an honest answer.** Lane scoring may still read the body — a false lane hit costs
  a rank, not the issue.
- **Re-read each surfaced issue from the API before printing it.** Search indexes lag; the list result is
  not proof the issue is still open.
- **An unreadable thread is `UNVERIFIED`, not open.** Print that status explicitly when the comment fetch
  fails rather than defaulting to available.
- **Match the ticket against artifacts that exist.** The winnable bounties are the ones whose acceptance
  criteria *describe work already shipped* — the PR is then a port of a proven mechanism, not a research
  project. Say which artifact matches, or decline the recommendation.

## Pitfalls

- ❌ Recommending from the artifact without checking its state — the same defect as citing a job posting
  without checking it is still listed. Availability is decided in the thread, not in the listing.
- ❌ Reporting "no bounties available" off one narrow query. Enumerate the label spellings first.
- ❌ Treating "no price" as "unpaid, skip" — many real bounties state the reward in a linked doc.
- ❌ Presenting the top-scoring item as a recommendation when its thread is busy and its price is
  unstated. Rank and recommendation are different sentences.

## Reference implementation

`profiles/arthur/scripts/bounty-scanner.py` — label discovery, credibility gate, title-only rejection,
lane scoring with language-as-confirmation, comment-thread claim detection, and a `--selftest` whose
fixtures are real comments and real repo records. Reuse its **filter order** when rebuilding elsewhere:
reject first, score second, verify claims last.
