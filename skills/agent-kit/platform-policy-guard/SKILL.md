---
name: platform-policy-guard
description: "Use BEFORE any state-changing action on a third-party platform — git push, repo create, a listing or submission. Measures the real limits and REFUSES on a hard breach, keeps a dated snapshot of each platform's terms, and speaks when the terms move. Fails closed."
version: 1.0.0
author: Gentech
tags: [policy, compliance, github, platform-terms, gates, fail-closed]
---

# Platform Policy Guard — terms as a gate, not a warning that scrolls

**The failure this exists to prevent, in one line:** on 2026-09-16 GitHub suspended the account for
AUP §9 with a 1.8 GB, 299-media-file repository used as a backup. The rule was public, quotable and
findable. **Nobody was watching** — and every local check we had was a warning, not a gate.

Two things were missing, and this skill is both:

1. **A verifiable record of what each platform's terms say** — with the source URL, the date it was
   read, and a content hash, so a policy claim is *checkable* rather than remembered.
2. **A pre-flight that refuses.** Measured against the limit *before* the action, exiting non-zero
   so the action does not proceed.

## Load this when

- a `git push`, `git commit` intended for a remote, or a `gh repo create` is about to happen
- a listing, submission, or publication is about to go to the MCP Registry, 8004scan, Circle's
  Agent Marketplace, an x402 directory, or any new platform we just joined
- anyone (human or agent) asks *"are we allowed to do this?"* about a platform
- the monthly terms watch reports a change

## The command that matters

```bash
S=/opt/data/.obsidian-vault/10-Labs/skills-distribution/agent-kit/platform-policy-guard/scripts/policy-guard.py

python3 $S preflight --platform github --action push --repo /opt/data/.obsidian-vault
```

Read the verdict line, not the exit code alone:

| exit | verdict | what you do |
|---|---|---|
| **0** | `PASS` / `unchanged` / `ACKNOWLEDGED` | proceed |
| **1** | `REFUSE` / `CHANGED` | **stop.** Fix the measured cause, or read the changed terms. Do not proceed on a warning. |
| **2** | `UNKNOWN` | **stop.** Could not measure or could not read. This is *not* a pass — it never is. |

**Never route around a non-zero exit.** If the guard is wrong, fix the guard and say so; a bypass
that is not written down is the 2026-09-16 posture again.

## What it measures on `--action push`

| measure | limit (GitHub, as recorded) | severity |
|---|---|---|
| `largest_tracked_file_mib` | > 100 MiB blocked by GitHub, > 50 MiB warns | hard / soft |
| `git_dir_mib` | > 1024 MiB (our own R3 line, from GitHub's "ideally < 1 GB") | hard |
| `tracked_media_files` | > 0 — **any** media, not "under 50 MB" (our R1) | hard |
| `commits_last_24h` | > 1 → warn, and it prints the committer names so a human can judge automation (R4) | soft |

**Why the aggregate bound is the one that matters.** The 2026-09-16 repository never tripped a
per-file limit — the largest file was 31.4 MiB. The exposure was **aggregate**: 1.8 GB of mostly
media, pushed automatically, serving as our backup. A check that only reads the 50/100 MiB rule
would have called that repository compliant. This is measured, not asserted:
`preflight --repo /opt/data/recovered-github-2026-10-15/gentech-vault` → `REFUSE` on
`tracked_media`; `--repo /opt/data/.obsidian-vault` → `PASS`.

**A timer-driven mirror trips the cadence WARN by construction — read it as a design question, not a
breach.** A scheduled job that commits and pushes on a timer will always exceed "1 commit/24h", so the
warning is guaranteed on every run and a reader who treats it as noise will also miss the real case it was
written for (an agent pushing on a loop). When it fires, ask two things and answer both: **is the committer
a scheduler or an agent** (the verdict prints the names precisely so you can tell), and **does the mirror
commit content or noise** — a push cadence matching the schedule is fine; a cadence far above it means
something other than the timer is writing. Do not silence the warning to clear the report; change the
schedule, or record why the cadence is intended.


## When a limit cannot be measured — `--ack`, named per limit

Some limits are real and not computable from a local repo: Circle's *"may suspend, remove, or
decline to list any Endpoint at any time in its sole discretion"*; the MCP Registry's moderation
rule; GitHub §9's *"significantly excessive in relation to other users"*.

A hard limit that cannot be measured is **not a pass**. `preflight` REFUSES it until the operator
names that exact id:

```bash
python3 $S preflight --platform circle --action publish \
        --ack listing_discretion,third_party_flowdown
```

Acknowledging one id never waives another — the self-test proves that direction
(`acknowledging one limit does not waive the others`). The verdict says `ACKNOWLEDGED`, and says
it is *a recorded human acknowledgement, not a measurement*.

## Snapshot — what "we have read the terms" is allowed to mean

```bash
python3 $S snapshot --all --update --allow-unread   # read, hash, diff, write
python3 $S status                                    # coverage + age, per platform
```

Each term page is stored with: `url`, `read_at`, `http`, `bytes`, `raw_sha256`, `text_sha256`,
`chars`, and a 600-char `snippet`. Nav/script/style are stripped before hashing so a chrome change
does not read as a policy change; everything left is hashed verbatim so a real edit cannot hide.

State lives in `00-HQ/policy-snapshots/<platform>.json` — in the vault, so every seat on this host
reads the same record and `git log` is the audit trail.

**`--allow-unread` is not a permission slip.** It tolerates a platform the registry has *never*
read (a recorded gap, printed as `NOT COVERED`), so a scheduled watcher can use exit 1 to mean
"the terms moved". A read that **fails** still exits 2.

## The registry — `platforms/registry.json`

One entry per platform: what we depend on there, `terms[]` (id, title, url, `url_state`),
`limits[]` (`measure`/`op`/`value`/`severity`/`enforced_by`/`source`/`quote`/`rule_ref`), and
`candidates[]` for pages we probed and could not use (with the HTTP code, so the next reader does
not repeat the search).

**Adding a platform — the only correct order:**

1. Locate the *real* terms URL. Not the marketing page, not the API landing page. Probe it and
   record the HTTP code. A 404 is a finding — write it down.
2. Add the entry with `terms[]` and **at least one `limits[]` row**. A platform with zero limits is
   reported `UNKNOWN` forever, by design: an empty limits list makes every check vacuously pass.
3. Quote the platform's own words in `quote`. Never paraphrase a policy into a limit.
4. `snapshot --platform <id> --update` to write the first baseline.
5. `status` — it must appear with a date, or you have not read it.

**Never record a limit you have not read.** The registry is the thing a future agent will trust.

## Invariants — each one is proved by `selftest`, not asserted

```bash
python3 $S selftest     # 18 cases, exits 0 only if every direction holds
```

- empty registry → fatal, never "healthy"
- no snapshot → `UNKNOWN` (silence is not consent)
- tracked media → `REFUSE`, and the refusal **names `tracked_media`** (a refusal that cannot be
  attributed is indistinguishable from a guard that refuses everything)
- oversized file → `REFUSE` via `file_size_block`; aggregate `.git` → `REFUSE` via `repo_git_size`
  (incompressible fixture, because 400 KB of the letter `x` deflates to nothing)
- missing repo path / non-git directory → `UNKNOWN`, never `PASS`
- stale snapshot (> `--max-age-days`, default 90) → `UNKNOWN`
- an unreadable term in the snapshot → `UNKNOWN`
- identical text → `SAME`, edited text → `CHANGED` (offline, so the test does not depend on a live
  page moving)
- a platform with terms but zero limits → `UNKNOWN`

## Standing practice

- **Before the action** — `preflight`. Monthly, or on any policy notice — `snapshot --all --update`.
- **If a SCHEDULED job does the pushing, the gate goes INSIDE that job.** "Before the action" enforced by a
  human's habit is not a gate: a timer fires whether or not anyone remembered to check. Measured — a mirror
  cron committed and pushed a 32-file batch (including an incident report) with no preflight in the loop,
  and the four numbers were only read afterwards. A push cron must call `preflight` first and **skip the push
  on a non-zero exit**, logging the verdict line so the run is auditable.
- **Point it at the repo the job actually pushes**, and quote the measured numbers in the log line
  (`.git` size · tracked media · largest file · commits/24h). A verdict with no numbers is an opinion the
  next reader has to re-earn.
- The snapshot watch is scheduled (`policy-terms-watch.sh`, monthly). It speaks only when the terms
  changed or a page became unreadable; silence means *unchanged where read* — and it always prints
  the platforms it has never read, because a coverage gap is not a pass.
- The 90-day freshness bound means an un-refreshed snapshot stops being usable. That is deliberate:
  a stale terms record is a memory, not a measurement.

## What this cannot do (stated so nobody assumes it)

- It cannot see **history**: media deleted from `HEAD` still lives in `.git`. The aggregate bound
  (`git_dir_mib`) is the proxy.
- It cannot see **account shape** (which identity holds what) — that is
  `agent-kit/github-account-compliance` R6.
- It cannot see **third-party flow-down**: publishing through Circle means inheriting a provider's
  terms we have not read. Recorded as a hard, unmeasurable limit on purpose.
- It does not push, commit, or publish. It only decides whether you may.

## Upstream — this is a Hermes feature request, not just an internal tool

Jordan's framing (2026-09-19): *"maybe this is a feature we can talk to Tiki about, because maybe
people want to run agencies with Hermes but Hermes might make mistakes from time to time."*
That is the general case: **every operator running an agent fleet against third-party platforms
inherits this failure mode**, and the useful thing to hand upstream is not a suggestion but a
reproducible case —

> An agent fleet pushed a 1.8 GB media-laden repository to GitHub as a backup for months. The rule
> (AUP §9) was public and quotable; the per-file limits were never breached; the account was
> suspended anyway. The measurement that would have caught it is four numbers (`.git` size, tracked
> media count, largest tracked file, push cadence) and none of them are in the agent's context.
> Ask: platform terms as a first-class, dated, hash-checked source in the agent's kit, plus a
> pre-tool-call gate that REFUSES on a hard limit instead of warning.
