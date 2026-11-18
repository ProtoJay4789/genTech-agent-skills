---
name: github
description: "GitHub via gh CLI: PRs, issues, reviews, repos, auth."
version: 2.0.0
author: Ben Barclay (benbarclay), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, gh, git, pull-requests, issues, code-review, repos, auth, ci]
    category: software-development
    related_skills: [codebase-inspection, requesting-code-review]
---

# GitHub

Work GitHub end to end with the `gh` CLI (REST fallback where noted): auth,
issues, the PR lifecycle, issue-to-PR delivery, code review, and repo
management. This skill consolidates six former skills; each workflow lives
complete in its reference file — ALWAYS read the matching reference before
starting that workflow, the body below only routes.

## Routing

| Task | Read first |
|---|---|
| Auth broken / new machine / token or SSH setup / gh login | `references/auth.md` |
| Create, triage, label, assign, close issues | `references/issues.md` |
| Branch, commit, open PR, watch CI, merge | `references/pr-workflow.md` |
| Carry an ISSUE to a verified PR (full delivery loop) | `references/issue-to-pr.md` |
| Review someone's PR: diffs, inline comments, verdict | `references/code-review.md` |
| Clone/create/fork repos, remotes, releases | `references/repo-management.md` |

Supporting assets: `scripts/gh-env.sh` + `scripts/git-credential-token.py`
(auth helpers), `templates/` (PR bodies, bug report, feature request),
`references/ci-troubleshooting.md`, `references/conventional-commits.md`,
`references/github-api-cheatsheet.md`, `references/review-output-template.md`.

## Core discipline (applies to every workflow)

- Preflight once per session: `gh auth status` — if it fails, go to
  `references/auth.md` before anything else.
- Prefer `gh` over raw REST; drop to `gh api` only for endpoints the
  porcelain lacks (the cheatsheet lists them).
- Never report CI green without checking `gh pr checks` yourself; never
  claim merged without verifying `state,mergedAt`.
- Read full context before writing: `gh issue view --comments` /
  `gh pr view --comments` — decisions live in threads, not titles.
- **A comment COUNT is not an unanswered thread.** `comments: 1` may be *our own* reply. Before
  answering anything inbound, read who spoke **last** and whether that speaker is us. Replying to a
  thread we already answered adds a duplicate to a public record and tells the other party we do not
  read our own history. If the earlier answer is now stale, **correct it in a follow-up** and say what
  changed — do not restate the whole thing.
- **Keep inbound and outbound as two separate queues, and never merge them.**
  *Inbound* = issues/PRs **others** opened **on our repos** → waiting on **us**. *Outbound* = PRs
  **we** opened **on other people's repos** → waiting on **them**. They need opposite actions, so a
  single "no reply" number mixing both is unactionable. Filter each explicitly
  (`?state=open` then compare `user.login` against the authenticated account).
- **An unmerged PR older than a few weeks is dead, not pending.** A maintainer who has not responded
  in months is not coming back to it; leaving it open costs nothing and gains nothing. Triage by
  whether the target repo has moved at all since we opened it, not by how much we want the listing.
- Sweep for duplicates before creating anything:
  `gh pr list --search` / `gh issue list --search`.

## Verification

- The workflow's own reference file defines done for that task.
- Cross-cutting: every claim about remote state (CI, merge, release,
  issue state) is backed by a fresh `gh` read, never memory.
