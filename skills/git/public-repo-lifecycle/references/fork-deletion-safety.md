# Fork deletion safety — the test battery

## Commands, in order

```bash
# 1. default-branch divergence from the parent (necessary, not sufficient)
#    compare API: <parent>:<default> ... <fork-owner>:<default>
#    read .status and .ahead_by — ahead_by 0 does NOT mean safe

# 2. branch names that exist only in the fork
ssh_url_or_local=$(git -C "$FORK_DIR" remote get-url origin)
git -C "$FORK_DIR" ls-remote --heads origin | awk '{print $2}' | sed 's#refs/heads/##' | sort > /tmp/fork_heads
#    any name absent from the parent's heads carries our work

# 3. every ref's SHA vs the parent's refs — OVER-REPORTS (a branch merely behind also differs)
git -C "$FORK_DIR" for-each-ref --format='%(objectname) %(refname)' > /tmp/fork_refs

# 4. AUTHORSHIP ACROSS ALL REFS — the decisive test
git -C "$FORK_DIR" log --all --format='%ae' | sort -u
#    grep that against our known commit identities; any hit = NOT deletable yet
```

**Why test 4 is the one that matters:** tests 1–3 all said "safe" on a fork that held a real unmerged bug
fix with no pull request anywhere. Authorship over every ref was the only signal that caught it.

## Does a pull request already preserve it?
A fork's deletion does **not** destroy a commit that has a PR: the host keeps `refs/pull/<N>/head`
upstream. So before deleting, check whether any commit is reachable from a PR:

```
GET /repos/{parent_owner}/{parent_repo}/commits/{sha}/pulls
```

- **Non-empty** → the work survives the fork's deletion; deletion is safe on that basis alone.
- **Empty** → the commit exists **only** in the fork. Export before anything is touched.

The PR may be closed and unmerged and the ref still lives — closed is not the same as gone. Absence of a
*merged* PR is not evidence the work is unrepresented.

## Export before delete (the irreversible step)
```bash
git -C "$FORK_DIR" bundle create "$OUT/$(basename "$FORK_DIR").bundle" --all
tar -czf "$OUT/$(basename "$FORK_DIR")-branches.tar.gz" -C "$FORK_DIR" .
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"
```
Store the checksums with the artifacts. An export nobody can verify is a rumour that the work is safe.

## After each deletion — read it back
- The delete should succeed, then a **readback must confirm it is gone**. A success response plus a
  still-readable repo is a false receipt, and the true state is what a later reader sees.
- **Count what you actually removed and state it** against the total you set out to remove. A declared
  total ("1.44 GB across 7 forks") is an assertion: verify the arithmetic and the list.
