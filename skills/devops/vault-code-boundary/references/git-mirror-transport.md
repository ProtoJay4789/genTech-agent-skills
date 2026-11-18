# Git mirror transport — a private repo as the vault's durable second copy

**Use when**: the sync vendor is down, capped, or is the only copy of the brain; or when a docs/notes tree needs a
versioned backup that no subscription can switch off.

**Shape**: one-way, **push only**. The tree is committed and pushed on a timer; nothing is ever pulled into it.
A tree with two writers (a sync client and a git working copy) produces phantom deletions — do not create that.

---

## 1 · Prepare the tree before the first commit

```bash
cd <tree>
ls -la .gitignore          # READ IT FIRST — it may already encode a prior suspension's rules
```

If a hardened `.gitignore` already exists (media extensions, `node_modules`, `*.jsonl`, machine output), **extend
it** rather than replacing it — and mark the appended block so a later reader can tell new rules from original:

```gitignore
# ── MIRROR ADDITIONS ── credentials and local state only
.env
.env.*
*.env
*.pem
*.key
*.p12
*.pfx
id_rsa*
*credentials*.json
*secret*.json
*.sqlite
*.sqlite3
*.db
*.db-wal
node_modules/
__pycache__/
*.pyc
.DS_Store
sync-probe*.md
```

## 2 · Secret scan on CONTENT, before the first push

```bash
# provider shapes — these are the ones that matter
grep -rlE 'sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xoxb-[0-9]{8,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----' .
```

**Read every hit in context; do not let a count decide.** Known-safe false positives:

| hit | why it is safe |
|---|---|
| a filename containing `secret` / `credential` / `token` | it is a **note about** secrets |
| `AKIA…` in a security/audit note | AWS's own **published documentation** key |
| `0x<64 hex>` in an EVM note | **storage slot** or **transaction hash**, not a private key |
| twelve lowercase words in a row | English prose; the phrase heuristic fires on sentences |
| `-e PRIVATE_KEY=…` inside a README/code fence | an example invocation |

What must stop the push: a real token in an assignment, a `.env` that is not ignored, a key file.

## 3 · Create the repo (private) and make the first commit

```bash
# create via API or gh — PRIVATE, and this is an explicit-owner decision, not a reflex (account-compliance R3)
git init -q
git config user.email "<owner>@…"; git config user.name "<mirror bot>"
git config core.quotepath false; git config gc.auto 0
git add -A
```

**Review the staged set BEFORE committing** — this is the last cheap moment to catch a binary:

```bash
files=$(git diff --cached --name-only | wc -l)
bytes=$(git diff --cached --name-only | xargs -d'\n' du -cb 2>/dev/null | tail -1 | cut -f1)
media=$(git diff --cached --name-only | grep -icE '\.(png|jpe?g|gif|webp|mp4|mov|mp3|wav|pdf|zip)$')
big=$(git diff --cached --name-only | while IFS= read -r f; do [ -f "$f" ] && [ $(stat -c %s "$f") -gt 10485760 ] && echo "$f"; done)
```

Then commit and push. **Keep the token out of the command line and out of the remote URL you leave behind** —
re-add the remote from the secret file inside the push script each run, so no credential is persisted in
`.git/config` in a form a stray `git remote -v` would print.

## 4 · The push script's shape

Order matters. Every step below is a guard that must refuse **before** the transfer:

```
cd <tree>                              || exit 0     # missing tree = report, not crash
[ token file exists ]                  || exit 0     # no credential = no push, say so
[ -d .git ]                            || exit 0     # not initialised = say so
git add -A
git diff --cached --quiet && exit 0                   # NOTHING CHANGED → silent success (this is normal)
  ├─ media staged?          → REFUSE, print the files, git reset -q, exit 0
  ├─ file > ~40 MB?         → REFUSE, print, reset, exit 0
  └─ .git > ~200 MB?        → REFUSE, "binaries are being tracked"
git remote add origin <url with token from secret file>
git commit -q -m "mirror <timestamp> — N file(s)"    || report commit failure
timeout 300 git push -q origin main                  || report PUSH FAILED (the tree is NOT backed up)
verify: GET /repos/<o>/<r>/git/trees/main?recursive=1 → assert count, no media, no secrets
```

**Exit 0 on every path.** A findings-reporting mirror that exits non-zero is logged as a broken job, and the
next reader learns to ignore it — the same trap every checker in this fleet has hit.

## 5 · Verify from the API, not from git

```bash
curl -s -H "Authorization: Bearer $T" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1" | python3 -c "
import json,sys
blobs=[x['path'] for x in json.load(sys.stdin)['tree'] if x['type']=='blob']
print('files :', len(blobs))
print('media :', sum(1 for p in blobs if p.lower().endswith(('.png','.jpg','.mp4','.mp3','.pdf','.zip'))))
print('probe :', any('probe' in p for p in blobs))"
```

| symptom | truth |
|---|---|
| `git push` printed success | a **claim** — not delivery |
| repo API `size: 0 KB` right after push | GitHub's **asynchronous** counter lagging; the tree read is authoritative |
| tree read returns the expected blobs | **evidence** — safe to say "the mirror has it" |
| push failed | say **"the tree is not backed up"** — never soften it to "sync issue" |

## 6 · Schedule it

**Hourly, not every ten minutes, and commit only on change.** A timer that pushes empty commits is "excessive
automated bulk activity" under GitHub's AUP §4 — the same section that contributed to a prior suspension.
`hermes cron create "40 * * * *" --name "…" --script <script>.sh --no-agent --deliver origin` — the schedule is
**positional**; there is no `--schedule` flag.

Deliver to origin only on problem. A mirror that reports "pushed 3 files" every hour is noise the human learns to
skip, and skipping it is how a failed push goes unnoticed for a day.

## Pitfalls

- **Never `git pull` a synced tree.** Push only. Two writers on one tree produce phantom deletions.
- **Never `git add -f` media "just this once".** The force flag exists to bypass the only guard you have.
- **Do not count moved/committed files from the tool's own output.** Compute the delta before/after; `mv -n` and
  filtered pipelines both under-report.
- **Do not write the "where did it go" pointer inside the directory you emptied** — it becomes the next run's one
  movable file, and the job then reports a fix it did not perform.
- **Do not claim the account is fine because a repo create returned 200.** Authenticated reads show the owner's
  view; see `github-account-compliance` on public-visibility claims.
- **A mirror is not a sync client.** The human's laptop does not get current from this alone — it needs a pull
  path (a git plugin/checkout, or a read-only `rsync` of the live tree). Say which, and say plainly that the
  mirror protects the data without restoring interactive editing on their machine.
