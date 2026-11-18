---
name: public-repo-lifecycle
description: "Use when publishing to or pruning a public GitHub repo."
category: git
version: 1.0.0
author: Gentech
license: MIT
tags: [github, publishing, deletion, forks, compliance, resume]
---

# Public Repo Lifecycle — what may go out, what may come down

## When to Use
- A repo is about to get a **remote** — anything published is a public claim.
- A repo is being curated as a **portfolio / resume surface** a stranger will land on.
- Large repos or **forks are being pruned** from a bloated account.
- You are **mirroring content into a visible account** and deciding which copy is canonical.

For the API-rate-limit and account-flagging rules that also apply here, see
`agent-kit/github-account-compliance`.

## Before a remote exists — MEASURE, then create it
A repo is measured *before* it gets a remote, because everything published is a claim on a public page.
- **A NAME MATCH IS NOT A PROJECT MATCH — read the repo's file tree before you push into it.** Pushing a
  local directory into `owner/<same-name>` because the names agree is how one project overwrites another.
  Measured: a vault folder and an existing repo shared a name, and the repo was **Rust** (`Cargo.toml`,
  `src/`) while the folder was **Python** (`server.py`, deploy scripts) — two different products, one
  filename. **`GET /repos/{owner}/{repo}/contents/` first and compare the shape** (language, top-level
  entries, presence of *your* entry point). If it differs, create a new name; never "push over" — a force
  push is the only way this ends well and it never is.
- **Decide the audience before the first push: public if another builder could use it, private if it only
  makes sense with our keys.** The two benefits are separable and do not need to ship together — a private
  repo already buys the thing that matters most (**a second copy with history**, instead of a service
  living only in a synced note folder), while the reputation half can wait for one read-through. Publish
  when a stranger could clone it and run it; that means a README and a working demo, because **published
  is not findable** and a bare public repo is worse than a private one.
- **Size**, **count of binary/media files**, and **secret-shaped filenames** — in that order.
- **Scan the CONTENT of anything template-named, not just the name.** A file called something like a
  password-gate template is usually inert, but the check is cheap and the failure is unbounded.
- **Exclude build artifacts** (`__pycache__`, `*.pyc`, editor droppings) rather than committing them.
- A file excluded from the working tree is still **in history** if it was ever committed — removing it
  later requires a rewrite, so the decision belongs before the first push.

## Writing to a repo you do not own outright — read the permissions first

**`GET /repos/{owner}/{repo}` carries a `permissions` object. Read it before planning any content write,** because
every failure below disguises itself as something else:

- **`push: false` makes a write fail as `404 Not Found`** — the same body a missing path returns. Nothing in the
  response says "no permission", so the natural reading is "wrong filename" and you hunt a file that is right there.
  The content read (`GET .../contents/x`) succeeding while the write 404s is the tell: **read works, write is refused.**
- **Fork → commit on the fork → open the PR** is the pull-only path, and it is the honest one: it leaves the merge
  with the owner. `POST /repos/{owner}/{repo}/forks`, wait for the fork to populate, `PUT` onto the fork's branch,
  then `POST /repos/{owner}/{repo}/pulls` with `head: "<you>:<branch>"`.
- **The default branch is not always `main`.** Pass `default_branch` from the repo payload, never a remembered
  `main`: a write aimed at a `master` repo returns **`Branch main not found`**, which reads like a permissions
  error and is not one.
- **Verify the PR's DIFF, not the create response.** A `201` proves a PR object exists; `Accept:
  application/vnd.github.v3.diff` on `/pulls/{n}` proves what it changes. One line changed should read as one
  line changed.

### After scrubbing a secret from a committed file, prove it two ways

Fetch the file back and assert **zero matches of the key's shape** (`0x[0-9a-fA-F]{64}` for an EVM key) — a
re-read, not a glance at the commit response. **And confirm the warning survived:** if the edit removed the
`never fund <address>` note along with the value, you deleted the only thing standing between a reader and funding
a burned address. Replacing the line with a placeholder plus the warning is the shape that works.

Say both facts in the report: **gone from the branch head**, and **still in history** — the scrub is hygiene, the
rotation is the fix.

## Publishing rules (a public repo is a claim)
- **A dead link is worse than no link.** Every advertised URL should be tested: a README that says "Live"
  beside a 404 is the first thing a reviewer checks, and it invalidates the rest of the page. If a
  discovery endpoint, demo or listing is gone, remove the line — do not leave it aspirational.
- **THE FIRST LINE DECIDES WHO KEEPS READING — lead with the layer your reader needs, then name who should stop.**
  A dev tool's README that opens with its most exotic capability reads as a product for that one audience, and every
  other reader bounces before reaching the parts that would have helped them. Measured: a kit whose first line sold
  payment rails and market data was read as a DeFi project — so a recipient with no DeFi work never saw the memory,
  handoff and maintenance material underneath, which was the useful half for them. The fix is structural, not tonal:
  **state the layers up front in a small table (what it is · who it is for · what it needs), mark which layer is
  optional and what it requires (wallet, chain, API key), and write one sentence telling the wrong reader to stop
  reading.** "Skip the rest if this isn't your job" converts a confusing product into a filter — and it is the
  cheapest way to make a broad tool land with a narrow reader.
- **A HAND-TYPED COUNT DRIFTS — PUBLISH THE POINTER, NOT THE NUMBER.** A count in a public README
  describes an artifact that changes on a different schedule from the sentence describing it, so the
  sentence is true on the day it is written and quietly false afterwards, with nothing in the file to
  signal that it moved. Measured across three surfaces in one pass: an org profile advertising a skills
  repo as "175 skills" whose tree held **7**; a kit README claiming "12 chains" against a manifest
  advertising **6 settlement rails**; a site badge saying 16 against **9** served. **Each had been true
  once** — which is why none was caught by whoever wrote it, and why a reader who checks one stops
  trusting the rest of the page.
  The durable form is a claim the reader can RESOLVE against the source — *"the repo is authoritative"*,
  *"see the live manifest"* — plus, where a number is genuinely wanted, the one measured today with its
  as-of. **When one count conflates reach with capability (12 chains readable vs 6 rails settleable),
  split it into two claims** rather than publishing the flattering one. And when you fix one number,
  grep the same file for every other: they drifted together, because one hand maintained them together.
- **Never publish a personal address as a project address.** A personal wallet published as "the project
  wallet" links every personal on-chain action to the org, permanently. Keep operational/treasury
  addresses only.
- **A PAYOUT ADDRESS IN A PUBLISHED FILE IS A DEFAULT, AND A DEFAULT ROUTES MONEY.** An address written
  into a README table, a skill file or an example config is read by an installer as *the thing to use* — it
  cannot tell "the vendor's collection address" from "replace this before running". Then a payment path that
  runs without configuration sends a stranger's funds to whoever wrote the file. That is wrong in every
  direction, including the author's: it makes your address a trap.
  **Three rules, in order:** (1) **scan the whole tree for the address SHAPE**, not the file a reviewer
  happened to quote — an address family (`[1-9A-HJ-NP-Za-km-z]{32,44}` base58, `0x[a-fA-F0-9]{40}`) will
  appear in the most-copied table as well as the doc that explains it, and a one-file fix leaves the table;
  (2) **delete it rather than parameterising it, unless the variable is actually read** — documenting
  `PAY_TO` in a repo whose code reads nothing produces a second defect (a claim with no reader) in place of
  the first; verify with a grep for the variable across the source, and if nothing consumes it, say *"no
  address ships here and nothing reads one"* instead; (3) **verify on the BRANCH through the contents API**
  (`GET /contents/<path>?ref=<branch>`), because `raw.githubusercontent.com` **lags the commit** — a reviewer
  reading the old text is reporting a clock difference, not a failed fix, and both sides can be right.
  Distinguish a real address from a benign shape match: a token mint, a program id or an explorer example is
  not a payout target — classify the hit before you claim it is one.
- **Commit as a person, not a robot.** A history signed by tooling accounts is the automated-account
  shape that gets accounts flagged. Author commits under the human identity.
- **Don't advertise a link the reader cannot open.** Measure public visibility logged out; an owner's view
  of their own repo proves nothing about what a stranger sees.
- **When you mirror content into a visible account, make the visible copy canonical** and rewrite every
  install path, badge and clone URL to that account in the same pass. Half-rewritten paths across two
  accounts is the exact fragmentation that makes a working product look broken.

## Publishing a repo AS A HANDOFF to someone else

A repo built so another person can clone it and read it is a different job from a portfolio. The
question stops being "does this flatter us" and becomes **"does anything in here belong to someone who
is not the recipient?"**

- **The test is OWNERSHIP, not keywords.** A term-scrub — replacing the names you remember with
  `<omitted>` — is not a content audit. Measured: a package went public after a scrub, and the finding
  that mattered came from a second pass that asked, file by file, *whose is this* — it surfaced an
  account registry and Steam IDs belonging to a **different household** inside a skill everyone assumed
  was generic. Nothing about the filenames said so; they read as ordinary notes.
- **Enumerate by path, then open every file and classify it.** Files carrying other people's identifiers
  (account registries, hardware IDs, addresses, household details) are exactly the ones a scrub misses,
  because the scrub searches for what its author remembers rather than for what the recipient is not.
- **Ship the recipient's material written for them — not your copy with holes punched in it.** A skill
  full of `<omitted>` breaks the first time the recipient's agent follows it: it will run a command
  against a path that was never theirs. **A short clean rewrite beats nine placeholdered files** — and
  when the source files were your own internal procedures in the first place, the rewrite is the only
  honest option.
- **A private repo link is not a delivery.** GitHub answers **404, not 403**, to anyone without access,
  so a link sent to a non-collaborator looks like a deleted repository and the user reports *"your link
  is broken."* Either add the collaborator (and verify the invite actually landed) or send an archive
  file that needs no account. Say which one you did — "I sent the link" is not the same claim as "they
  can open it."
- **A temporary-public repo still has to survive being indexed.** "We'll delete it tonight" does not
  un-copy what a crawler already took, and a delete-from-head leaves the bytes in history. **If the
  content is personal, strip it before the flip, not after.**

## Pruning — the decisive test is AUTHORSHIP, not similarity
Fork cleanup is the cheapest large win on a bloated account and it is **irreversible**. A fork can hold
commits no upstream has ever seen, so "it looks like a copy" is not proof of anything.

**Order of tests, each catching what the previous one misses:**
1. **Default-branch divergence from the parent.** Zero is necessary and *not sufficient*.
2. **Branch names against the parent's refs** — a branch that exists only in the fork carries our work.
3. **Every ref's SHA against the parent's** — *over-reports*: a branch that is merely **behind** the parent
   also differs from its current tip, so a clean fork can look like it has hundreds of "own" refs.
4. **Authorship across ALL refs** (log every ref, filter for our commit identities). **This is the only
   decisive test** — it is what stops the deletion of a genuine unmerged fix.

Commands, the PR-survival check, and the export-before-delete recipe: `references/fork-deletion-safety.md`.

Creating a repo and importing a directory into it **without `gh` and without a local `git` clone** — the
seed-then-blob sequence, and the secret check that follows: `references/empty-repo-bulk-push.md`.

**Pace the deletions.** A burst of deletes is the same traffic shape that gets an account flagged, so
remove a few, verify each one landed (delete succeeds, then a readback confirms it is gone), and only then
continue. A delete that returned success but left the repo readable is a false receipt.

## ⚠️ Exposure found on a repo that is ALREADY public

**Different problem from publishing, and it has its own order. The trigger is usually a red X on some
unrelated CI job** — you open the repo to fix the workflow and find the contents are the emergency.

**Rule: when a failure sends you into a repo, audit what the repo IS before fixing the job.** A
failing `deploy-pages` job is a symptom that the repo was never meant to be a website; the finding
that matters may be sitting in the file tree. The failing job costs nothing to leave broken for a day.

### Containment order

```
1  ENUMERATE the whole tree anonymously   → the attacker's view, no token
2  FILTER by suspicious path patterns    → .env, secret, credential, token, .key, .pem, wallet, seed
3  CONFIRM by fetching each anonymously  → 200 + key-shaped content = live exposure
4  DELETE from the branch head           → verify each returns 404 on a CACHE-BUSTED anonymous GET
5  FLIP visibility                       → private, verify anonymous 404
6  CHECK HISTORY                         → a head delete is not a removal
7  ROTATE                                → every value that was in those files
```

**Do steps 1–3 before saying the word "leak" out loud, and do step 4 before debating whether it is
one.** A file that returns `200` with no credential to anyone who asks is not a risk assessment, it is
a fact.

```bash
# enumerate as a stranger
curl -s "https://api.github.com/repos/$R/git/trees/main?recursive=1" | grep -o '"path": "[^"]*"'

# confirm one finding, cache-busted — raw.githubusercontent serves stale content
curl -s -H 'Cache-Control: no-cache' "https://raw.githubusercontent.com/$R/main/$P?cb=$(date +%s)" \
  -w '\n%{http_code}'
```

### Deleting from the head is not deleting

**`GET /repos/{r}/commits?path=<file>` answers whether the content is still recoverable.** It almost
always is. Say both facts in the same report — *gone from `main`* and *still in history* — because a
reader who hears only the first believes the exposure is closed.

```bash
curl -s "https://api.github.com/repos/$R/commits?path=HQ/config/api-key.env&per_page=5"
# non-empty → the bytes are still resolvable from a commit SHA
```

**Flipping private is the fastest real containment** (it takes one PATCH, and it also stops the
crawlers) — but it is containment, not remediation. **The only true close is rotating every value,
because a public window means the content was already copied; "we deleted it" is a claim about a
branch head.**

### A repo that mirrors something private needs a decision, not a cleanup

**If enumeration finds a working copy of an internal tree — handoffs, agent config, project strategy —
the repo's *purpose* is the finding.** Ask whether it should be public at all before curating its
contents. Cleaning one file out of a mirror leaves the mirror.

**And judge the exposure by content, never by name.** Credential-shaped filenames are the easy hits;
the dangerous ones read like ordinary notes. Fetch and inspect rather than trusting the path.

### Flipping private has DOWNSTREAM READERS — repoint them in the same pass

**Before the `PATCH private:true`, grep every surface that prints the repo's URL: the vault, the site,
CVs, DM templates, application tables.** A private repo answers **404 to a stranger**, so every
*"portfolio: <url>"* line silently becomes a dead link — and some of those documents have already
left your hands (a CV, a submitted form, a DM), where you cannot fix them.

- Measured: flipping a repo that held a vault mirror was the correct call, and it 404'd its Pages URL —
  while **three job documents still told employers to visit it**. The flip was right; leaving the
  references was the defect. Grep first, repoint in the same pass, and say what was repointed.
- **Repoint to a surface that resolves without an account** — a public org page, a live API's
  `/openapi.json`, a demo — not to another private repo (see *"a private repo link is not a delivery"*).
- **The Pages API may refuse: `422 Deactivating GitHub pages for this repository is not allowed`.**
  Flipping visibility closes Pages by consequence, so that is the reliable containment when the Pages
  endpoint says no — do not spend the session arguing with it.
- **Verify as a stranger, then re-grep:** repo API 404 · `raw.githubusercontent` 404 · the site 404 ·
  and zero live occurrences of the old URL left in the docs you searched.

### Report the containment, not the story

Give the user: what was readable, how many, the verification method, what is now closed, and **what is
still open** (history, rotation, the repo's existence). **Do not print the secret values** — a report
that quotes the key has re-created the exposure in a new place, including chat logs and backups.

## Deleting a repo outright — archive first, then prove both 404s

A delete is irreversible and the user often names one repo while a dead initiative owns **two**.

1. **Inventory before anything: list the tree and keep the SOURCE, not the build.** Fetch every blob whose path is
   not vendored or generated (`lib/`, `node_modules/`, `out/`, `cache/`, `dist/`) into a folder outside the repo, and
   write a short `README-ARCHIVE.md` naming why it was deleted, what was kept, and anything that must never be used
   again (a burned address, a dead deploy target). **A contracts repo can be 900 files of which 24 are yours** —
   archiving the vendored tree makes the archive unreadable and pointless.
2. **Verify the archive before the delete, by count and by the files that matter** — not by "the copy succeeded".
3. **`DELETE /repos/{owner}/{repo}` returns `204`; then read back twice** — the API path and the public URL, both
   `404`. A delete that returned success is a receipt for the request, not for the absence.
4. **Enumerate siblings of the same dead initiative and say which you removed.** Measured: the repo named was one of
   two carrying the same abandoned hackathon (one pushed that week, one silent for months); deleting the named one
   and *reporting the sibling by name without touching it* was the right scope, and the user then confirmed it.
   **Deleting more than you were asked is not thoroughness** — it is an unrecoverable action on something the user
   never decided.
5. **A delete breaks INBOUND links, and nothing tells you — so check them in the same session.** The repo's own
   404 is expected; the damage is the pages that still advertise it. Measured: the org profile README linked a
   deleted repo, and the front page carried a dead project link for hours until a scheduled link check flagged it.
   **Search every surface that names repos** (org profile `profile/README.md`, docs, listings, CV/portfolio files,
   DM templates) for the repo slug, remove or repoint each hit, then **run the link checker** rather than trusting
   the edit — it reads the live page, not your copy of it.

## Pitfalls
- **Deleting on `ahead_by == 0` alone.** It misses author-named branches entirely — the failure is silent
  and the work is unrecoverable.
- **Treating a fork's own ref list as proof of unique work.** See test 3: being behind manufactures the
  same signal as being ahead.
- **Publishing before measuring.** A remote makes the content live; a secret in the first commit is in
  history forever.
- **Judging public visibility from an authenticated call.** Owner-visible ≠ publicly visible.
