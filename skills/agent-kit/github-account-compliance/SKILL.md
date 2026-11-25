---
name: github-account-compliance
description: "Use BEFORE any GitHub API write (repo create, PATCH, fork, PR, comment, delete) or any burst of API reads. Hard STOP rules that keep our GitHub account un-flagged. Load this whenever GitHub work is about to happen."
version: 1.0.0
author: Gentech
tags: [github, api, compliance, rate-limit, flagging, safety]
---

# GitHub Account Compliance — the hard rules

**Load this before ANY GitHub API work.** These are not guidelines. Violating them risks the
whole account (repos, Pages, hackathon submissions, portfolio) going dark.

## ⚠️ Know WHICH budget you are spending — measured, 2026-11-03

**The old "60 requests/hour" line was the ANONYMOUS limit, not ours.** Corrected after Treasury flagged it and
`GET /rate_limit` was measured on our token the same day:

```
core         limit=5000   ← our authenticated REST ceiling
search       limit=30     ← PER MINUTE. The binding constraint.
graphql      limit=5000
code_search  limit=10     ← PER MINUTE
```

**60/hour is what an unauthenticated caller gets.** Quoting it as ours caused two opposite errors: treating a
generous core budget as scarce, and treating search as free.

**What that means in practice — the cap is per endpoint class, not just per task:**

| class | real limit | what burns it |
|---|---|---|
| **search** | **30 / minute** | `api.github.com/search/*` — a 6-query loop is 20% of a minute's allowance, and a *retry loop* exhausts it |
| **core** | 5,000 / hour | normal reads — genuinely plentiful |
| **code_search** | 10 / minute | `search/code` specifically |

**So: a "find repos" task is search-heavy and hits the per-minute ceiling long before the hourly one.** Batch and
cache search results; never re-run a failed query set "to see if it works now" (that is what I did on 2026-11-03).

**Free quota check — the only one that costs nothing:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/rate_limit
```
It does **not** count against the budget. Use it instead of `check_quota()` from a helper file that does not exist.

## 🛑 The STOP rules (absolute)

1. **403 / 429 = STOP. Immediately.**
   Stop every API call. Do not retry. Do not "just check one more thing". Do not switch to curl
   to see if it works better. Retrying through a block is **the** documented way accounts get flagged.
   Report what you were doing, then wait for the next cycle (or the reset time).

2. **No bursts. Ever.**
   Space **every write 3+ seconds apart**. No loops that fire N writes back-to-back. A tight burst of
   ~40 writes is what tripped our account on 2026-09-16.

3. **No ad-hoc repo creation. No mass forking.**
   Repo churn is GitHub's #1 flag trigger. Repo creation goes through the scheduler
   (`github-rate-limit-scheduler`) or an explicit Jordan decision — never improvised mid-task.

4. **Hard cap: ~30 API calls per task** (unless a written cap in the task says otherwise).
   Note the count when you're done. If the task needs more, batch/cache it or split it across cycles.

5. **Use a padded, counted call path — never raw calls in a loop.**
   ⚠️ **The helper this rule used to name (`/opt/data/profiles/gentech/scripts/github_api.py`) DOES NOT   <!-- ⚠️ ABSENT (verified 2026-11-17): this tool is not present on this host. Do not assume it runs. See build-queue #108. -->
   EXIST** on the post-wipe box — verified 2026-10-27 by `find / -name github_api.py`. Do not send an agent
   looking for it.
   **The compliant path today is `scripts/github-compliance-sweep.py`**, which carries its own per-account
   token handling, a **3s inter-call spacing** and a hard **40 API calls per account per run** cap, and reads
   bytes over git (zero API) instead of the API. For a one-off call, use `curl` against a single endpoint,
   count it against your budget, and space it — **do not reintroduce a burst.**

6. **git for bytes, web for scanning.**
   `git push/pull/clone/fetch` costs **zero** API quota. Reading `github.com` pages via `web_extract`
   costs **zero** API calls. Move data with git; read with the web — not the API.

7. **Never touch the GraphQL / search quotas casually.**
   GraphQL is a separate tiny budget (`gh repo create`, `gh pr create` use it). Search burns the
   secondary limit fast. Use REST and the helper instead.

## Pre-flight checklist (run this in your head before the first call)

- [ ] Am I about to make **more than ~5 writes**? → slow down to 3s spacing, or queue them.
- [ ] Am I **creating a repo / forking**? → STOP, route via the scheduler, not ad-hoc.
- [ ] Am I **in a loop**? → it must be capped, cached, and spaced.
- [ ] Have I checked quota? → `curl -s -H "Authorization: token $T" https://api.github.com/rate_limit | grep -o '"remaining":[0-9]*'` — **`/rate_limit` does not count against the budget**, so this is the one free read.
- [ ] If I get a 403/429 → **stop and report**. No retries.

## Why these exist (the mechanism)

GitHub flags accounts for automated/inauthentic activity and secondary rate-limit abuse
(Acceptable Use §4). The triggers:

- **Bulk content creation**: >80 content-generating requests/min, >500/hr (repos, releases,
  issues, PRs, comments). Repo churn is the #1 flag.
- **Concurrent requests**: >100 simultaneous REST+GraphQL.
- **Per-endpoint bursts**: >900 points/min (a POST/PUT/DELETE costs 5 points; GET costs 1).
- **Secondary-limit cooldown**: 403/429 → stop ALL calls. Continuing = integration ban.

When an account is flagged it can return **404 on web + API while `git ls-remote` still works**,
and stored tokens read as **invalid**. That's the signature — the repos are fine, the account is
hidden. The fix is owner-only (unflag appeal), cannot be done by an agent.

## Case study — 2026-09-16 (why this skill exists)

While "improving the GitHub profile", an agent fired ~40 unspaced API writes, **created a repo
ad-hoc**, hit the rate limit, and **kept probing** — then the account went 404 on web+API.
Every one of the four STOP rules was broken. Full write-up:
`00-HQ/incident-github-account-404-2026-09-16.md`.

**The lesson is not "be careful." It's: these rules must be in front of you at the moment of action.**
That is why this skill is loaded on GitHub work rather than filed in a handoff somewhere.

## Two tokens are two ACCOUNTS — resolve the identity BEFORE every write

A write does not just change a repo; **it speaks in someone's name.** Owning two token files is not two keys
to one door, and treating them as interchangeable produces both failure modes at once:

```
<token A>  → GET /user → ProtoJay4789   push ✓ ProtoJay4789/*   push ✓ Gentech-Labs/*
<token B>  → GET /user → GentechLabs    push ✓ GentechLabs/*    push ✗ Gentech-Labs/*
```

Note the owner names: **`GentechLabs` and `Gentech-Labs` differ by one hyphen and are different owners**, with
completely opposite permissions. A comment posted on an org repo with the personal token does not merely
fail — where it succeeds elsewhere it reads as *the person* speaking for the company, which nobody authorised.

**Pre-flight, every write, all three steps:**

```bash
# 1 · who is this token?
curl -s -H "Authorization: token $T" https://api.github.com/user | jq -r .login
# 2 · may it write HERE?  (the gate, asked of the API, not assumed from the owner's name)
curl -s -H "Authorization: token $T" https://api.github.com/repos/<owner>/<repo> | jq -r .permissions.push
# 3 · then write, spaced, against the budget in this file
```

- **Map owner → token in code, not in your head.** One dict, keyed by the repo owner, so the identity is a
  property of the call. A module-level `TOKEN = …` is a single-voice design that silently answers as the wrong
  account the first time it is used outside its original repo.
- **A permission preflight must be able to FAIL.** Ask GitHub; cache per repo; refuse before attempting. A
  comment that 403s after a perfect-looking draft wastes the turn, and a successful write as the wrong account
  is worse than the 403.
- **Never let a bare chat/user id stand in for an identity.** The same reflex applies everywhere: a target, a
  sender or a token must be qualified by its system.

## Speaking to strangers: inbound is ours, outbound is not

**The line is ownership of the repo, not the direction of the message.** A PR *from* a stranger *into* our repo
is a customer question and answering it is the maintainer's job. A PR *from* us *into* someone else's repo is a
contribution, and it stays human — their rules, their reputation, one open contribution at a time.

- **Gate a reply tool on the repo owner**, as a hard refusal that names the reason, not a prompt instruction.
- **Gate it on the claim, too.** A reply that states a fact ("we support X", "it's live", "$N/month") must
  carry a line from something we publish; otherwise escalate it to a human with the draft attached. A bot that
  invents a capability to a customer is a fabricated receipt pointed outward.
- **Make it idempotent** — key a state file on the message text so a scheduled job cannot post the same reply
  every morning.
- **Answer the OPENING MESSAGE when there are no comments.** A thread with zero comments carries its question
  in the issue/PR body; reading only the comments feed returns empty and reports "cannot read the thread",
  which is a much more alarming claim than "nobody has replied yet".
- **Publish the merge decision, don't make it.** Classify such a thread as needing a human, draft it, and say
  so; merging a stranger's work into a company catalogue is a publication decision.

## A "200" on your own content proves nothing about public visibility

**An authenticated call shows the OWNER's view — and the owner always sees their own flagged/hidden
account.** So "I called the API with our token and got 200" is not evidence the account is publicly
healthy; it is the *expected* behaviour of a hidden one.

**Rule:** for any PUBLIC-visibility question (is our repo/issue/profile visible to outsiders?), measure
**logged out**, or with a second account. Authenticated results may be reported only as
"visible-to-owner", never as "public".

Symptom this explains: anon `404` on every artifact we author, while controls (someone else's repo) return
`200` in the same batch, and auth `200` on our own. That split is *content-scoped*, not caller-scoped — so
it is not rate limiting, which is applied to the caller and returns `403`, not `404`.

## Stale credential files — test the LIVE one, or you will call a valid credential "invalid"

**⚠️ This is a FLEET pattern, not a GitHub one. Two instances in one week.**

Before concluding ANY credential is dead, **enumerate every copy on the box and test each one**:

```bash
find / -name "hosts.yml" -o -name "*composio*key*" -o -name "*.env" 2>/dev/null | head
```

Then test each candidate against a cheap authenticated endpoint and report **which path** you tested.

| Instance | Live copy | Stale copy | Symptom of reading the stale one |
|---|---|---|---|
| GitHub (2026-09-18) | `~/.config/gh/hosts.yml` | `~/.hermes/profiles/<p>/home/.config/gh/hosts.yml` (Aug 31) | declared a working token "invalid" → wrote it into an incident note |
| Composio (2026-09-19) | `COMPOSIO_API_KEY` in the profile `.env` (`ak_`, 23 ch) | `/root/composio-key.txt` (`COMPOSIO…`, 40 ch) | 401 `Invalid API key` → declared Drive blocked (it was live) |

**Never generalise from one file to "the credential".** A dead token and a restricted/hidden account
look identical from outside — so testing the wrong file manufactures a problem that does not exist, while
the real one stays available.

### GitHub-specific detail

There is a **live** credential file and at least one **stale** copy:

- LIVE: `~/.config/gh/hosts.yml`
- STALE: `~/.hermes/profiles/<profile>/home/.config/gh/hosts.yml` (older; silently `401`s)

Reading the stale one produced a false "our token has been invalidated" conclusion that went into an
incident note. **Before concluding a credential is dead:**

1. List every candidate file (`find` for `hosts.yml`) and compare mtimes.
2. Test each one against `GET /user` (`200` + the expected `login` = alive).
3. Report which path was tested. Never generalise from one file to "the token".

Note the direction of the risk: a dead token and a hidden account look similar from outside. Testing the
wrong file manufactures a credential problem that does not exist — which is why this belongs in the
pre-flight, next to the quota check.

## A dead `secrets/github-token` shadows the live `gh` credential — and `check_quota` hides it

*(HISTORICAL — the helper below no longer exists on this box; the lesson still applies, the path does not.)*

`scripts/github_api.py` resolved its token from `${PROFILE_DIR}/secrets/github-token` **before** falling back to
`gh auth token`. Those two credentials can **diverge** (measured 2026-09-18: secrets file → **401 Bad credentials**,
live `gh` token → **200 `GentechLabs`**), and then every `gh_get` / `check_quota` call fails 401 while `gh api`
works perfectly.

**The trap:** `check_quota("core")` reports **`0/0`** when the token is rejected — it reads as *"quota exhausted"*,
not *"bad credential"*, so a blocked script looks like a rate limit.

**Rule:** when the helper 401s but `gh api user` returns our login, the helper's **credential is stale** — the API
is fine. Test each credential's file with its own `GET /user` call; never generalise from one source. (This is the
reverse direction of the Aug-2 case, where `gh` reported the token invalid while the secrets file still worked.)
Fix by replacing the file's contents — `pr-submission-rules` → `references/token-death-recovery.md`.

## ⚠️ The fleet WRITE gate is NOT DEPLOYED (verified 2026-10-27, re-verified 2026-11-17)

**This section describes machinery that is currently absent. Read it before assuming you are paced.**

- `/opt/data/profiles/gentech/scripts/github-write-gate.py` — **absent.**
- **⚠️ RE-VERIFIED 2026-11-17 — the READ half now exists, and it is not a write gate.** Do not mistake it:
  `/opt/data/profiles/gentech/scripts/gh_guard.py` provides **`gh_get()` only** — spacing, `Retry-After` /
  `X-RateLimit-Reset` waiting, and a budget floor that reports UNKNOWN. **It has NO write entry point**, and it is
  imported by `github-inbox-check.py` and `github-secret-audit.py` — both read-only jobs. **So the paragraph below
  is still TRUE: nothing paces our writes.** **The fix, if it is ever built, is `gh_write()` beside `gh_get()` in
  that same file — not a second script that a reader is told to look for and cannot find.**
- **The vault IS now a git repo** (`/opt/data/.obsidian-vault/.git`), created as a **private text-only
  mirror** to `ProtoJay4789/gentech-brain` — so "the pre-push hook in the vault repo" finally has a real
  home. **The gate script above is still absent**; what enforces the rules today is the mirror job's own
  pre-push gate (`brain-mirror.sh`, see §9 below), not the hook. Do not assume the shared gate exists just
  because the repo now does.
- A recovered copy survives at
  `/opt/data/recovered-github-2026-10-15/gentech-vault/scripts/github-write-gate.py` (9,160 b, syntax OK,
  no state file). **It is a recovery artifact, not a running guard.**

**Consequence, stated plainly: nothing enforces write pacing right now.** Until the gate is restored and a
hook is installed in whichever repo actually pushes, **the pacing is manual and it is yours**: one writer at a
 time, 3+ seconds between writes, ≤30 API calls per task. **The 2026-09-16 flag came from an unpaced burst;
the guard that prevents a repeat is missing, not merely idle.**

The rest of this section documents the intended design, kept so a restore has a target:

### Design (to restore)

`/opt/data/profiles/gentech/scripts/github-write-gate.py`, enforced by `.git/hooks/pre-push` in the vault
repo. One writer at a time, 25 s minimum spacing, **20 writes per rolling hour** across ALL
profiles (state: `/opt/data/profiles/gentech/state/github-write-gate.json`, shared box-wide — the risk is
the ACCOUNT's total write shape, not one profile's).

- Check `status` before a push you care about: it prints `remaining` / `used_last_hour`.
- On saturation it prints `GITHUB-GATE: deferred (push) — budget saturated, retry next tick`
  and exits 3. **That is the gate working, not an error.**
- A caller is only held `MAX_WAIT_S = 120 s`; longer and it defers rather than blocking a
  cron forever. A retry therefore succeeds once the OLDEST write in the window has aged
  enough for the computed wait to drop under 120 s — read the oldest `ts` from the state
  file and retry at `oldest + 3600 - 120`.
- **Do NOT set `GITHUB_GATE_BYPASS=1` for convenience.** Unpaced pushes are the lane that
  got the account flagged; a saturated budget is usually our own agents pushing, and
  bypassing recreates exactly the burst shape being prevented. Emergencies only — and say
  so in the log.
- **A deferred push loses no work** — the commit is safe on disk; only the push waits.
- A rejected push when local is AHEAD and nothing is incoming is usually this gate, NOT a
  conflict. Check `status` before assuming a rebase is needed.

## The monthly recheck — measured, not assumed (Jordan, 2026-10-27)

**Jordan, after the reinstatement:** *"let's go through the compliance and maybe we could update the
compliance to where we recheck it maybe once a month… I don't want to get banned again."*

**Job `7a89d0a2fc79` — "GitHub Compliance monthly recheck (read-only)", `0 14 1 * *` (1st, 10am ET),
`no_agent: true`, deliver → HQ.** Runs `scripts/github-compliance-monthly.py`.

```bash
python3 …/scripts/github-compliance-monthly.py                 # sweep + report + speak on change
python3 …/scripts/github-compliance-monthly.py --quiet-unless-bad   # the cron form: silent when clean
python3 …/scripts/github-compliance-monthly.py --force-speak       # print the report now
python3 …/scripts/estate-audit.py --self-test                      # the selector's own controls
```

**It READS ONLY — it never pushes, so R4 is respected** (R4 forbids *pushes* on a timer, not reads).

**Silence doctrine** — proved by a six-case battery, not asserted:

| case | behaviour |
|---|---|
| first run (no baseline) | SPEAKS once — a job must never be silently blind |
| no change | SILENT, exit 0 — delivers nothing |
| any rule total up | SPEAKS, exit 1 |
| a total down (improvement) | SILENT — good news is not an alert |
| forced | SPEAKS |
| findings unreadable | exit **2 UNKNOWN**, never "healthy" |

**Baselines:** `backups/github-sweep/monthly-baseline.json` (previous run) · `findings.json` (per repo) ·
`COMPLIANCE-REPORT.md` (human-readable, per-rule totals + change column + repos to inspect).

**First measured run, 2026-10-27:** 227 repos — **R1 media in git: 1,458 across 82 repos** ·
**R2 git-as-backup: 101 across 17** · **R3 vendored: 16,324 across 32** · **R1/R5 secret-named files: 301
across 17** · 2 unmeasurable. **The account was reinstated one day earlier.**

**Known defect, fixed:** `github-compliance-sweep.py:236` unpacked 5 values from a `classify()` that returns
6, so **every `scan`/`all` run crashed** and `findings.json` was never regenerated after 2026-10-14.
**A measurement that crashes and is never scheduled is indistinguishable from a clean bill of health.**
When you touch a function's return arity, grep every call site — an unpack error at one caller broke the
whole sweep silently while `inventory` kept working.

## §9 MIRROR REPOS — the shape that got us suspended, and the four rules that prevent a repeat

**This account was suspended once for AUP §9 Excessive Bandwidth Use**: a 1.8 GB repository with 299 tracked
media files (872 MB), pushed automatically as "the fleet's backup". GitHub's own docs name that as the wrong
tool: *"Git is not designed to serve as a backup tool."* **Any repo that mirrors a working tree on a timer
re-creates that shape unless the rules below are enforced by code.**

**R1 · TEXT ONLY, enforced by a gate, not by `.gitignore` alone.**
`.gitignore` is a filter, and `git add -f` walks straight past it. Put a **pre-push check over the STAGED
set** that refuses the whole push if any media extension is present:

```bash
git add -A
media=$(git diff --cached --name-only | grep -icE '\.(png|jpe?g|gif|webp|bmp|tiff?|psd|mp4|mov|webm|mkv|mp3|wav|pdf|zip|tar\.gz|7z)$')
[ "$media" -gt 0 ] && { git diff --cached --name-only | grep -iE '\.(png|mp4|mp3|pdf)$' | head -5; git reset -q; exit 0; }
```

**Prove the gate by the failing direction** — force-stage a junk media file past `.gitignore`
(`printf 'x' > tree/should-not-sync.png; git add -f tree/should-not-sync.png`) and confirm the push is
**refused**. A guard only ever run on the happy path is a wish.

**R2 · SMALL, refused in code before it becomes a finding.** Refuse any staged file over ~40 MB and any
repo whose `.git` passes ~200 MB — both well inside GitHub's 50 MiB warn line, 100 MiB block, and 1 GB
guidance, so the refusal happens while it is still cheap to investigate. **Growth is the alarm**: a mirror
whose size climbs means binaries are being tracked, and the answer is to find them, not to raise the ceiling.

**R3 · NOT BULK.** Commit and push **at most once an hour**, and **commit nothing when nothing changed** —
`git diff --cached --quiet && exit 0`. A timer that pushes every ten minutes with empty commits is precisely
"excessive automated bulk activity" (§4). **Silence with no commit is the correct normal output**, not a
dead job.

**R4 · PRIVATE.** These are working trees, vaults and notes. Private is not a preference.

### Scan CONTENT before the first push — filename matches are noise

A filename grep for `*secret*` / `*token*` / `*.pem` returns mostly **notes ABOUT secrets**, and treating that
list as a blocker strands the push forever. **Scan the staged files' CONTENT for provider shapes instead:**

```bash
grep -lE 'sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xoxb-[0-9]{8,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----' <each staged file>
```

**Expect and read the false positives rather than suppressing them** — a documentation repo legitimately
quotes AWS's own published example key, and an EVM note legitimately contains 64-hex **storage slots and
transaction hashes** (not private keys). Both are safe. What must never ship is a live credential, and the
way to tell is to **read the line in context**, not to count matches.

Also: a 12-word run of lowercase words is almost always English prose. **Do not "fix" a heuristic hit by
deleting the note.**

### Verify the push from the API, never from git's exit code

```bash
curl -s -H "Authorization: Bearer $T" "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1"
```

Read back the blob list and assert the things that matter: **count, no media, no credential file, and any
probe file actually gone.** `git push` reporting success is a claim; the tree read is evidence.

**⚠️ `size: 0 KB` on the repo API is not a failure** — GitHub's size field is an **asynchronous** counter
that lags the push. The **tree read** is the truth about what is in the repo; do not report a mirror as
empty because an eventually-consistent byte counter has not caught up.

### Reuse the existing `.gitignore` — it probably already encodes the suspension

A tree that was once pushed to GitHub usually still carries the hardened ignore file written after the
suspension (media extensions, `node_modules`, `*.jsonl`, machine output). **Read it before writing a new one.**
Append only the gaps — credentials and local state (`.env`, `*.pem`, `*.key`, `*.db`, probes) — and mark the
addition so a later reader knows which rules are original and which were appended.

## See also
- `devops/github-rate-limit-scheduler` — the budget-aware scheduler that owns repo_create/fork/PR ops
- `github/github-api-helper` — the helper's API surface and wiring pattern
- `software-development/open-code-review-cli` — `ocr`, the second-opinion reviewer (gated, cost-aware)

## Learned on arthur (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

### Authenticating the push — and leaving no token behind
Two failures happen *after* a successful `POST /user/repos`, and both read like auth problems when they
are something else. Budget the whole creation path as **three writes**: create (with the description
inline), the push itself (**zero API quota** — git moves bytes), and one `PUT .../topics`. Do not spend a
fourth call on a `PATCH` for the description you could have sent in the create payload.
1. **`src refspec main does not match any` is a BRANCH NAME error, not an auth error.** `git init` can
   still default to `master` while the remote expects `main`. Run `git branch -M main` before the first
   push. Reading it as an auth failure sends you hunting for a token problem that does not exist.
2. **`git -c http.extraheader="Authorization: Bearer $T" push` does NOT authenticate to GitHub over
   HTTPS.** Git still asks for a username and dies with `fatal: could not read Username for
   'https://github.com': No such device or address` in any non-interactive shell. **Use the token inside
   the remote URL for the push, then reset the remote to the clean URL in the same command** and assert
   the token is gone:
T=$(cat "$SECRETS/github-token-<account>" | tr -d '\n\r ')
git remote set-url origin "https://x-access-token:${T}@github.com/<owner>/<repo>.git"
GIT_TERMINAL_PROMPT=0 git push -u origin main      # fails loudly instead of hanging a cron
 git remote set-url origin "https://github.com/<owner>/<repo>.git"
grep -c "x-access-token" .git/config || echo "0 token refs remain"   # must print 0
   **The scrub is the point, not the push.** A token left in `.git/config` is a live credential on disk
   in a directory that gets copied, archived and (for a mirror job) re-pushed — so the last step of every
   token-authenticated push is proving the config is clean. `GIT_TERMINAL_PROMPT=0` matters for the same
   reason: an unprompted credential read blocks a scheduled job forever rather than failing it.
3. **Then verify visibility logged out** — the section above: an authenticated `200` is the owner's view,
   and it is the *expected* answer for a hidden account too.
- **`references/publishing-a-personal-repo.md`** — the PUBLIC, personal-account shape (the opposite of §9's
  private mirror): confirming which token belongs to which identity, creating with the description inline so
  the path costs three writes, the stranger-visibility battery, the third content scan for emails / home
  paths / wallet addresses that a credential-shaped grep misses, and what belongs in a tree that is
  effectively a job application. The push mechanic itself lives in §9 above — that file adds only what
  differs when the artifact is a portfolio rather than a backup.

