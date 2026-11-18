# Rebasing a published mirror onto its working tree

The case: a repo is already public and still meant to be current, but development happens elsewhere (a synced
vault, a private tree, another seat). Every push is therefore a **sync across a boundary** — and the boundary is
where both the security exposure and the lying-README live.

## Procedure

**1. Clone the published copy and measure the gap. Do not push first.**

```bash
git clone -q "https://x-access-token:$TOKEN@github.com/<owner>/<repo>.git" /tmp/clone
cd /tmp/clone && git ls-files | wc -l          # what IS published
```

Then compare against the source tree by **set** and by **content**:

```python
core = {str(p.relative_to(core_root)) for p in core_root.rglob("*") if p.is_file()}
repo = set(subprocess.run(["git","ls-files"],capture_output=True,text=True).stdout.split())
missing, extra = sorted(core-repo), sorted(repo-core)
# and for the intersection, compare sha256 — a shared FILENAME says nothing about shared CONTENT
```

**Report `missing` / `changed` / `only-in-repo` counts before writing anything.** That number is the finding.

**2. Build the payload in a scratch directory, not in the clone.** Copy the source tree in, drop `.git`, and
write the ignore file in the same step:

```
__pycache__/
*.pyc
.env
*.log
cache/
# per-learner / per-user local state, not engine content
data/<progress>.json
```

**3. Secret-scan the payload before `git add`, and require ZERO hits.** Scan content, not filenames, and allow
obvious placeholders only:

```python
pats = [r"ck_[A-Za-z0-9]{10,}", r"sk_[A-Za-z0-9]{16,}", r"ghp_[A-Za-z0-9]{20,}",
        r"xox[baprs]-[A-Za-z0-9\-]{10,}",
        r"[A-Za-z0-9_\-]{32,}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{20,}",   # JWT
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"]
```

Skip matches containing `your_`, `<`, `>`, `xxx`, `example`, `placeholder`, `redacted`. A hit that survives that
filter stops the push.

**4. Commit with the gap in the message.** "Sync N days from <source>" plus the file-level deltas. A commit that
says only "update" erases the only evidence of how stale the public claim had been.

**5. Verify FROM GitHub, never from your own git.** `git push` exiting 0 and `git log` in the clone both prove
only that your local repo believes something.

```bash
# the repo's own clock moved
curl -s -H "Authorization: token $T" https://api.github.com/repos/<owner>/<repo> | jq '.pushed_at,.size'

# the CONTENT matches the source, byte for byte, fetched anonymously
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>" | sha256sum   # == sha256sum <source>/<path>

# excluded state is genuinely absent
curl -s -o /dev/null -w '%{http_code}' "https://raw.githubusercontent.com/.../data/<progress>.json"   # expect 404
```

Check 4–5 representative files including at least one **new** and one **modified**; a push that landed nothing
but a README still returns 200 on everything that already existed.

**6. Delete the clone.** If the token was embedded in a remote URL it now lives in `.git/config` on disk; removing
the directory is part of the job, not tidiness.

## Rules that belong to this class

- **Counts in the commit, not adjectives.** "25 files missing, 9 diverged, biggest 46 KB → 54 KB" is auditable;
"brought up to date" is not.
- **A repo whose description claims a capability the code no longer matches is a public misstatement.** When the
mirror is a portfolio surface, the description is part of the sync.
- **Pushing to `main` directly is a permissions question, not a technical one.** If the principal said this
department owns the repo, push; otherwise open a branch and say why. Record which it was.
- **A grant of "you may work in this repo" is not a grant to change who else can reach it.** Adding
collaborators, widening token scope, or handing out access is a fleet-level decision that belongs to whoever
owns the credentials — raise it, do not do it.
