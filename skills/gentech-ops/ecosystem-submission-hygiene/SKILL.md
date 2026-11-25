---
name: ecosystem-submission-hygiene
description: Use when submitting or withdrawing a listing PR.
version: 1.1.0
author: Gentech
license: MIT
trigger: "Before opening, refreshing, withdrawing or re-filing any PR to an external repo or directory — and when an outbound PR backlog has gone silent."
---

# Ecosystem submission hygiene — one entry, one PR, one claim set

**Origin:** 2026-11-04. 52 open GenTech PRs across 40 repos: **12 of them duplicates** (one repo held four),
**11 carried facts that had stopped being true**, and the whole batch was silent 21–135 days. Nobody answered
because one account had flooded seven repos. This skill is the rule set that prevents that.

## Rule zero — does this repo accept OUTSIDE work at all?

**Read the contribution policy before planning any submission, and read it again before promising a fix.**
Repos split into three shapes, and the shape decides whether the deliverable is a PR, an issue, or nothing:

- **Invites PRs** — a `CONTRIBUTING` that says so, often with a neutrality condition (*"keep these docs a
  neutral resource, no branded content beyond links"*). Submit here; this is the only shape where a PR is
  the right artefact.
- **Refuses external PRs outright** — a marquee repo can state plainly that it does not accept outside code
  and asks instead for **bug reports, reproductions, root-cause analysis and design discussion**. Publishing
  a PR here is wasted work that also looks like not having read the rules. **The lane is analysis, not code** —
  and analysis requires that you actually run the thing, so check the binary/skill is installed before you
  offer an opinion about its behaviour.
- **Silent** — no policy at all. Then the merge-latency evidence
  (`references/repo-acceptance-scoring.md`) is the best available proxy for whether outside work lands.

```bash
curl -sL -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/contents/docs/contributing.md" | jq -r .content | base64 -d
# probe a few conventional paths: CONTRIBUTING.md, docs/contributing.md, .github/CONTRIBUTING.md
```

**A docs repo is the highest-trust surface available and the most under-used.** Contributing a neutral,
unbranded fix to the standard you build on reads as engineering; adding your name to someone's `awesome-*`
list reads as advertising — and the first is merged in about a day where the second decays for months.

## The three rules, in priority order

### 1 · ONE ENTRY = ONE PR, FOREVER
Before opening any PR to a directory, search first:

```bash
gh search prs --author @me --repo <owner>/<repo> --state open --limit 20
# or without gh:
curl -s -H "Authorization: Bearer $TOK" \
  "https://api.github.com/search/issues?q=repo:<owner>/<repo>+author:<login>+type:pr+is:open"
```

**If any PR from us is open against that repo, you do not open a second one.** You either push a commit to the
existing branch or comment on it. A list owner who sees three PRs from one account closes the batch — measured,
not theorised.

**Run that search BEFORE planning the submission, not before opening it.** A plan that says *"submit to
<directory>"* is derived from a list of DOORS we could knock on, and it carries no knowledge of which doors we
already knocked on. An open PR from months ago is invisible from the door's side and looks identical to a repo
we have never approached — so the first step of any "get listed on X" task is the open-PR search, and the
plan changes if it returns a row.

**A duplicate is a debt, not a backlog item.** Withdraw duplicates *before* any ping, because:
- closing a duplicate sends **no notification** to the maintainer (silently absorbed),
- pinging while siblings sit open is the single most common reason a whole batch gets closed,
- and the numbers get sane again, so the next report is readable.

### 2 · A CLAIM MUST BE READ FROM THE LIVE SURFACE, AT WRITE TIME
Never write a count, a chain list, an endpoint list or a tool count from memory, a README, an old note, or another
PR. Read the machine-readable source in the same breath as you write the prose:

```bash
curl -s https://api.gentechlabs.net/.well-known/x402 | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['resources']),'resources'); print(list(d['notServable']))"
curl -s https://api.gentechlabs.net/status | python3 -m json.tool
```

**Then quote those numbers, and only those.** On 2026-11-04 eleven PRs still said "16 endpoints" / "15+ tools" /
"12 paid endpoints" while the manifest said **10** and named five services `notServable`. A submission that
overstates is worse than no submission: it builds a reputation for inflation, then meets a buyer who can count.

**Also: link the production domain, never a staging subdomain.** Three PRs pointed at
`gentech-x402-gateway.<user>.workers.dev` while the live surface was `api.gentechlabs.net`.

### 2b · THE DEMO MUST EXECUTE — a placeholder is a failed submission, not a style choice

**Origin:** 2026-11-09. A catalogue submission carried a complete `catalog.json` with every required field —
`schemaVersion`, `slug`, `provider`, `demo`, `setup`, `install` — and sat 75 days with zero review. The
difference against the PR that merged in a day was not the schema. **It was that theirs was runnable `curl`**
and ours called `signPayment(payment, WALLET)` — a function that does not exist — and sent
`'Payment-Response': 'base64-encoded-response'`, a literal string where a signature belongs.

- **Run every command in the demo before you commit it.** Not read it — execute it, and paste the real output
  into your own notes. `curl /health` → 200; a paid route → 402; decode the challenge header → full JSON. **A
  demo whose commands you have not executed is a claim about a stranger's environment**, and it is the first
  thing a reviewer tries.
- **No invented symbols in sample code.** A helper the reader must implement is a prerequisite, not a demo.
  Use the protocol's own reference client (`npx @x402/fetch <url>`) for the hard half and show the wire format
  so the reader can verify what they are being asked to pay.
- **Header and field names must come from a live response, captured in the same pass as the write.** A demo
  that names `Payment-Signature` when the server emits and expects `payment-signature` is unverifiable — and
  the mismatch is invisible from inside, because both spellings look right.
- **Ship the asset the catalogue renders.** `"logo": null` next to a merged neighbour's `logo.svg` reads as an
  unfinished submission even when every textual field is correct.
- **A submission that lingers in a repo with a one-day merge median is evidence about the SUBMISSION, not the
  repo.** Do not escalate, re-ping, or blame the maintainer: diff your PR against the last two merged ones and
  find the convention you missed. "They could not verify us" and "they did not want us" have opposite remedies
  and only the diff tells them apart.

> How to score a candidate repo on its own closed-PR history before spending a submission (median merge days,
> external merge ratio, dead-repo detection): `references/repo-acceptance-scoring.md`.

### 3 · A PR THAT CANNOT MERGE DOES NOT GET A PING
Check `mergeable_state` before writing anything:

```bash
curl -s -H "Authorization: Bearer $TOK" https://api.github.com/repos/<owner>/<repo>/pulls/<n> \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['mergeable_state'], d['changed_files'], d['additions'], d['deletions'])"
```

- `dirty` → **rebase first.** A courtesy ping on a conflicting PR reads as "we did not check our own work."
  But **rebasing a months-old listing PR is a RE-SUBMISSION, not a marker resolution** — the upstream README
  has moved, so the entry may now belong in a different section, need a different format, or duplicate one a
  maintainer added:
  1. Re-read the CURRENT README's section list and the two or three entries around yours; write the entry
     against today's neighbours, not against the version the PR was opened on.
  2. Branch from `upstream/main` and re-add the line, rather than trying to satisfy old conflict markers — the
     resulting diff must be **exactly one added line** (`git diff --stat upstream/main`), with no deletions and
     no whitespace/line-ending churn.
  3. **Rewrite the PR body so it describes the line you are actually adding.** A body still describing the old
     section, the old count or the old links is a factual error a reviewer reads before the diff.
  4. Push to the branch the PR already points at so the PR updates in place; then re-read the PR (not the push
     output) for `mergeable`, the head label and the rendered diff.
  - **A fork can be renamed after the PR was opened.** Pushing to the old URL succeeds through GitHub's
    redirect and still updates the PR — so a green push is not evidence the ref is where you think. Confirm
    from the PR object (`head.label`, `head.repo.full_name`) and from the diff, never from the push output.
- `clean` → refresh the claim text and ping.
- `unknown` → GitHub is still computing; wait and re-read, do not guess.

## The withdrawal protocol (measured, 2026-11-04)

```python
PATCH /repos/{owner}/{repo}/pulls/{n}   body: {"state": "closed"}
```

- **Closing sends no notification.** Comment first only if the maintainer needs a reason — then comment, then
  close. A one-line "consolidating our submissions, our duplication not yours" is enough once.
- **Never close the PR that carries the best current text.** Keep the one that is newest, cleanest, and least wrong.
- **Verify after:** re-run the open-PR search and assert `total_count` dropped by exactly the number closed, and
  that no repo holds more than one open PR from us.

```bash
curl -s -H "Authorization: Bearer $TOK" \
  "https://api.github.com/search/issues?q=author:<login>+type:pr+is:open&per_page=100" \
  | python3 -c "
import json,sys,collections
d=json.load(sys.stdin); g=collections.Counter(p['repository_url'].split('/repos/')[1] for p in d['items'])
print(d['total_count'],'open |', {k:v for k,v in g.items() if v>1} or 'no duplicates ✅')"
```

## What to do when a backlog has already gone quiet

1. **Group by repo.** Duplicates first — withdraw, silently.
2. **Audit every patch for stale facts**, mechanically:
   ```bash
   curl -s -H "Authorization: Bearer $TOK" https://api.github.com/repos/<o>/<r>/pulls/<n>/files
   # then grep the '+' lines for counts, domains, and names of retired services
   ```
3. **Split the backlog by KIND before ranking it — the three kinds have three different remedies.**
   - **Directory listing** (an entry added to an awesome-list, a catalogue, a README table): if it is stale and
     unmerged, its value has already expired. **Withdraw or re-file; never re-ping** — a re-ping asks a maintainer
     to reconsider content that was true months ago.
   - **Protocol / code fix** (a header name, an address normalisation, a spec-compliance patch): correct work that
     a maintainer merges when reminded. **One polite re-ping each**, and repeat fixes across sibling repos can be
     batched into a single message rather than one per repo.
   - **A conversation** (a maintainer replied and nobody answered us): the highest-value row in any backlog, and
     the one most likely to be invisible — see the filter trap below.

   **The "silent PR" filter has a blind spot that inverts the priority ranking.** A report that counts only PRs
   with `comments == 0` cannot distinguish *nobody ever opened it* from *somebody answered us and we never
   replied* — both print as silence, while the second is the worse reputation outcome and the only one with a
   live counterparty. **Emit two buckets** (`comments == 0` → unopened; `comments > 0` and still open → waiting
   on a decision) and rank the second one first.

   **Label every row with the SENDING identity, not just the author.** The author of an outbound PR is constant
   while the fork it is sent from is not, so "which account did this go out as" cannot be inferred from the PR
   body: read it from the head fork
   (`GET /repos/{repo}/pulls/{n}` → `head.repo.owner.login`) for the rows you are already reporting, and print
   it beside each one. Before re-pinging or replying, confirm the account you are about to write from is the one
   the thread expects.

   **`comments > 0` is not a conversation until you exclude the BOTS.** Review robots, linters and status
   commenters post on their own, and their comment flips a dead PR into the "waiting on a decision" bucket —
   so the highest-priority row of the report can be a thread no human has ever opened. Measured: three rows
   reported as answered were one review-status bot (`<reviewer>-heimdall`-style) and one spam post; the real
   count of human replies was zero. Count only comments where `user.type != "Bot"` and the login does not end
   in `[bot]`, and print both counts (`3 comments · 0 human`) so the reader can see what the verdict rests on.

   **Before promising to fix a PR, confirm the account can still PUSH to its head fork.** `GET
   /repos/{owner}/{repo}` returns a `permissions` block; `push: false` with `pull: true` on the head repo means
   the branch is frozen to us — the PR can never be repaired, by us or by a future session, and every plan to
   "push a corrected commit" silently cannot happen. Measured: a listing PR sat 75 days because its head lived
   in a read-only fork while its twin in a fork we own had been closed. **A PR you cannot push to is not a
   backlog item, it is a re-file**: branch fresh from the CURRENT upstream `main` (`compare/main...<fork>:<branch>`
   → `behind_by` in the hundreds means the fork is a museum piece, and a merge of that branch carries every
   intervening change), commit the two files, open a new PR that names the old one as superseded, and close the
   ones you own.

4. **A fourth kind exists and it changes the goal: the REPO ITSELF is dormant.** Check `pushed_at` against the
   PR's `created_at` and against today. A repo whose last push **predates your PR** has nobody tending it, so
   *a merge is not the realistic outcome* and asking for one wastes the one message you will get. Measured: a
   PR sat 118 days with zero comments and zero reviews inside a repo last pushed nine days **before** it was
   opened — unread, not rejected, and unmergeable in practice.

   **When the repo is dormant, write for a READER, not a reviewer — and ask for a conversation, not a merge.**
   The shape that works:
   - **Open with a correction against your own material.** Diff your PR's claims against your live manifest in
     the same pass and, if the PR is closer to true than the manifest, **say so.** A correction that costs you
     something is the only opening that reads as honest in a repo nobody trusts to be read.
   - **Offer something they need instead of asking for approval.** A live surface they can test against, with
     the property that makes it useful named plainly (real paid calls, verifiable on chain, limits and a kill
     switch to exercise) beats "please merge".
   - **Make silence explicitly acceptable** (*"if this repo is dormant, no action needed"*). Without that line
     the note demands a reply from someone who has stopped reading, and it becomes a nag by default.
   - **Confirm the permission class before composing.** `permissions: {pull: true, push: false}` on their repo
     means issue comments are available and branch pushes are not — the message must fit what you can actually
     do, and a plan that assumes a push is a plan that cannot execute.
   - **Verify the comment LANDED by re-reading the thread**, not by the 201: fetch the comments list and assert
     one by our login exists. A POST that returns an id is a claim about the API.

5. **Rank survivors by "does this bring a customer",** not by age. A messaged x402 directory beats a 120-day-old
   awesome-list entry nobody reads.
6. **Ping a maximum of three, by hand, with a named decision.** 52 comments is spam; 3 is a person.
7. **Record the decision to ping inside the PR text itself** — offer the rebase, state the corrected number, and
   give the maintainer an easy close. A PR that is easy to close gets closed; one that is hard to close gets ignored.

## Hosted listings with an OWNER/APPROVAL split — write the update CALL correctly

The approval state machine (`draft` → `pending` → `approved` → `declined`, and the trap that unpublishing a
pending record returns it to draft) belongs to **`discovery-and-listing` → "A submitted listing has a STATE
MACHINE"**. Read that first: on an owner-controlled listing, `isPublished: true` with `approved: false` is
the normal *submitted* state and the publish switch is already on.

What belongs here is the part that costs a rejected write or a lost queue position — **how to compose the
update call:**

- **Omit the state field entirely** on a field edit. Only fields present in the body change; re-sending
  `isPublished: true` on an unrelated update is a needless write against live review state.
- **Array fields REPLACE, they do not append.** Sending `teamMembers` / `products` / `revenueSources` with one
  new entry deletes the rest. Always re-send the full array including existing entries.
- **Nested objects do not follow the prose.** A field documented as "links" may require
  `[{"type": "github", "url": "…"}]`, not a list of strings. A `400 Validation error … expected object,
  received string` is the schema telling you the shape the docs never printed — read the error's `path`
  (`teamMembers[0].links[0]`) and fix that exact element. A 400 writes nothing, so retry is clean.
- **Snapshot the full record to a file before the first write**, so any change is reversible.
- **Verify by RE-READ, and check the approval state survived.** A 200 means the request parsed. Re-fetch and
  assert all three: the new values are present, the fields you did not name are untouched, and
  `reviewStatus` / `isPublished` / `approved` are exactly what they were. Queue position is the one thing
  you cannot get back.
- **State the unverifiable part honestly.** While a listing is unapproved there is no public page, so the API
  confirms the *field*, never the rendered card or its badge. Say that instead of implying it looks right.

## Maintaining a live listing — a dead endpoint in a listing costs more than an absent one

**Getting listed is the easy half. A listing that outlives the endpoint it describes becomes a self-inflicted
injury:** the directory's own monitor keeps polling the dead path, and it grades your entry against the failures
it sees. Measured on one directory: a paid route retired in a host wipe stayed in the catalogue, their probe hit
it **~1,230 times in 2.7 days** from ~30 user agents, and the entry's status read `degraded` while the
compliance score was `A` and uptime `100%` — a contradiction only the stale rows explained.

### Measure the directory's own record before writing any correction

Most catalogues expose a public read endpoint. Query it for your brand and diff its fields against your live
manifest — the delta IS the correction payload, and it is more accurate than anything you would write from
memory:

```
GET {directory}/api/v1/services?search=<brand>
  → endpoint_count · networks[] · status · verified · compliance grade · uptime · description
```

Expect the record to be wrong in several fields at once (a count, a rail list, and prose naming services that no
longer exist) — a catalogue only learns what you tell it, so every field drifts independently.

### The server side must say GONE, not NOT-FOUND

**410 `service_retired` is the answer that stops a monitor; 404 `service_not_found` keeps it coming.** A 404 reads
as *this seller's link is broken*, which invites retry and depresses a grade; 410 reads as *deliberately gone*.
Return a body naming the replacement surface (`live_services: …/.well-known/x402`), not just a status code.

- **The retired set must be reachable by every name the router can form.** A path segment can map through an alias
  table to a third name (`deals` → `deal_tracker_native`), so a set that lists the manifest keys still misses the
  route at runtime. Enumerate the aliases, not just the service names.
- **A comment asserting "these routes answer 410" is a claim, not a fact.** When the constant beside it disagrees
  with the comment, the comment is what is wrong — and the set is what ships. Grep both, then hit each route live
  and assert the status; a route that still answers 404 after a "fix" means the lookup key differs from the one
  you edited.

### There is usually no self-serve edit — corrections go through the SUBMIT form

Most directories offer `new service` and `new facilitator` and nothing else, so a correction is a fresh
submission carrying the corrected record:

1. **Diff first** (above), and put the delta in the form: corrected endpoint list, corrected networks, rewritten
   description with the dead services removed.
2. **Say it is a correction in the notes field**, naming what was withdrawn and why (*"two endpoints previously
   listed are retired and now answer HTTP 410; count is N not M"*). A reviewer can act on that; an unexplained
   duplicate cannot.
3. **Follow the redirect for the receipt.** The POST commonly answers **303** with an empty body — that is
   success, and following it lands on a *pending review* page. An empty body is not a failure.
4. **Re-read the public record afterwards.** The count will not move until review; report "submitted, pending"
   rather than implying it is fixed. Then re-check on a later run and quote the number that changed.

**And fix both halves.** Correcting the listing without the server answering 410 leaves the probes running;
answering 410 without the correction leaves the dead paths advertised for the next buyer to find.

## Red lines

- **Never auto-post.** Drafting is safe; publishing under our name is a decision. This repo's own history proves it:
  an agent posting at machine speed is how you get 52 open PRs and 12 duplicates.
- **Never claim a merge, a reply or an acknowledgement that did not happen.** Silence is data.
- **Never re-open a withdrawn PR to "refresh" it.** Open a new one only after confirming the repo has none open.

## Compliance-audit mode — the business use (Jordan, 2026-11-04)

When we audit *someone else's* submission for them (the compliance service), the same three rules become three
findings, and this is the checklist that makes the audit worth paying for:

| finding | how you prove it | severity |
|---|---|---|
| **duplicate submissions** | group their open PRs by repo; >1 is a finding | high — it is why they are ignored |
| **claims that no longer match their live surface** | diff every count/domain/endpoint in their PR against their own `/.well-known` or `/status` | high — it is reputation, and it is provable |
| **unmergeable PRs left pinging** | `mergeable_state == dirty` | medium — reads as carelessness |
| **retired services still advertised** | their docs name services their status page marks down | high — it is a false promise |
| **a listed endpoint that now answers 404/410** | fetch every path in their listing and check the status; a 404 where 410 belongs is the same defect as an absent withdrawal | high — it is why a catalogue monitor keeps probing them |
| **no decision recorded in the PR** | no "please close if not a fit" / no response path | low — but it is why it stalls |

**The deliverable is a table like the one above, with each row quoting the live URL and the exact stale line.** Not
advice — evidence. That is the whole product.
