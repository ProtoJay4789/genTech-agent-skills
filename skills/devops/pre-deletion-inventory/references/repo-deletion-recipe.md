# Retiring a repo or fork — the copy-paste ladder

Run every rung, then act. Nothing here is destructive on its own.

## Setup

```bash
export GIT_ASKPASS=<helper>      # a helper, not a token in the URL
export GIT_TERMINAL_PROMPT=0
export GIT_TOKFILE=<tokenfile>   # EXPORT it: an inline launcher passes env itself and hides this
mkdir -p <work>/{refs,contents,exports}
```

## Rung 1 — metadata pass (near-free)

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/repos/<owner>/<repo> \
  | jq '{full_name, fork, parent: .parent.full_name, size, default_branch, pushed_at, private}'
```

- `size` is **packed git-object size including history** — not the working tree.
- `fork` + `parent.full_name` separate *a copy of someone else's work* from *content we own*.
- Nothing here tells you what is inside. It sets the search order only.

## Rung 2 — every ref (the rung that is usually skipped)

```bash
git ls-remote --heads https://github.com/<fork>.git | awk '{print $2}' | sed 's|refs/heads/||'

git ls-remote https://github.com/<fork>.git   | awk '{print $1}' | sort -u > refs/fork.sha
git ls-remote https://github.com/<parent>.git | awk '{print $1}' | sort -u > refs/parent.sha
comm -23 refs/fork.sha refs/parent.sha          # object IDs the fork has and upstream does not
```

Branch **names** are the fastest authorship signal: a fork inherits upstream's branches at fork time, so a
name referring to your own project/product/feature can only have been created afterwards.

A SHA unique to the fork has two causes that look identical — upstream rebased or force-pushed away an
inherited commit (not ours), or a branch authored in the fork (ours). The branch name, then the commit author
identity on that branch, settles it.

Check the contribution surface too, before deleting a fork:

```bash
curl -s -H "Authorization: token $TOKEN" 'https://api.github.com/repos/<fork>/pulls?state=open&per_page=50'
```

Deleting a fork closes its side of a live pull request. An open PR is work in flight, not a copy.

## Rung 3 — contents, normalised

```bash
git clone --quiet https://github.com/<owner>/<repo>.git contents/<repo>
tar -C contents/<repo> --exclude=.git -czf contents/<repo>.tar.gz .
sha256sum contents/<repo>.tar.gz
```

Diff against the live counterpart **with the shared prefix stripped**, or the comparison is meaningless:

```bash
(cd contents/<repo>/<nested-root> && find . -name '*.md' -printf '%P\n' | sort) > contents/theirs.txt
(cd <live-root>                   && find . -name '*.md' -printf '%P\n' | sort) > contents/ours.txt
comm -23 contents/theirs.txt contents/ours.txt    # there, not here
```

Then **sample the sizes of the "only there" files before believing the count.** Eighteen snapshots of one
archive read as eighteen thousand findings and are one finding about a schedule.

## Rung 4 — export, with provenance

```bash
git clone --filter=blob:none --single-branch --branch <BR> \
    https://github.com/<owner>/<repo>.git exports/<repo>-<BR>
git -C exports/<repo>-<BR> log --format='%H|%ae|%cI|%s' > exports/<repo>-<BR>-commits.txt
git -C exports/<repo>-<BR> archive --format=tar.gz -o exports/<repo>-<BR>.tar.gz HEAD
sha256sum exports/<repo>-<BR>.tar.gz
```

Store branch, tip SHA, commit log and archive together. A bare tarball and a tail of a conversation are both
unusable a month later; provenance is the difference between a recovery and a mystery.

## Rung 5 — delete, paced, verified

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE \
  -H "Authorization: token $TOKEN" https://api.github.com/repos/<owner>/<repo>
sleep 5
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: token $TOKEN" https://api.github.com/repos/<owner>/<repo>    # expect 404
```

Log one row per retire: `name, measured MB, DELETE status, verify status, exported? (path)`. The ledger is
what makes the reclaimed total a measurement instead of a claim.

## When a compliance sweep and a recovery need collide

1. **Preserve** the artifact locally (rungs 3/4) — this satisfies recovery immediately and costs no policy.
2. **Extract** what is unique into the live system, where it belongs and where it will be backed up.
3. **Only then** treat the remote artifact as a policy item and act on the classified list.

Doing 3 before 1 is the failure this recipe exists to prevent, because the compliance workflow is the one
under time pressure and the one holding a stated reason to proceed.
