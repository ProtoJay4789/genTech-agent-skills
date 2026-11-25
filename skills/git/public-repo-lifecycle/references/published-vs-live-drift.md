# Published vs live — proving a public library is the one you run

A published copy of an internal library drifts silently: nothing links the two trees, no build fails, and
the difference is invisible to everyone except a stranger trying to install it. This is the check that makes
"the published copy is current" a measurement.

## Why the obvious check is wrong

`raw.githubusercontent.com` **serves stale content for minutes after a push**, so a fetch-based comparison
reports drift that does not exist and then reports clean before the commit is even readable. Compare **git blob
hashes through the tree API** instead — one call, uncached, and it scales to hundreds of files.

The local half needs no network: git's blob id is `sha1("blob <len>\0" + content)`.

```python
import hashlib
def git_blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()

# one call returns every blob id in the published branch
tree = GET(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
published = {e["path"]: e["sha"] for e in tree["tree"] if e["path"].endswith("/SKILL.md")}
```

Compare `published[repo_path]` against `git_blob_sha(live_file)`. A mismatch is a real difference; a fetch of
the same file proves only what the CDN thinks today.

## Three classes, three different fixes

| class | meaning | fix |
|---|---|---|
| **MISSING** | live, never published | a consumer cannot install it at all |
| **STALE** | published, differs from live | the public copy is wrong, and it is wrong under the right name |
| **ORPHAN** | published, no live twin | deleted upstream, renamed, or written for the repo on purpose |

**STALE is the dangerous one.** A skill that is 5–9× smaller than its live twin looks fine in a file listing —
same name, plausible content, and a reader has no way to know it predates months of work. Measured: four files
in a published kit were 11–21% of the live versions under identical names.

**Check ORPHANs for a rename before deleting.** A misspelled path (`ljf-` for `lfj-`) reads as a deletion
candidate; removing it without publishing the correct spelling quietly reduces the public library.

## Withheld is a decision, not drift

If part of the library is private on purpose, the checker must carry that list — otherwise every run reports
the same findings forever and the check becomes noise nobody reads.

```python
WITHHELD = {"skills/<private-category>/", ...}      # subtree prefixes, with a one-line reason each
PUBLIC_ONLY = {"skills/<cat>/<skill>/"}             # published on purpose, no live twin

def withheld(p):
    return any(p.startswith(w) for w in WITHHELD | PUBLIC_ONLY)
```

Subtract `withheld()` before computing MISSING **and** before computing ORPHAN. Keep the reason for each entry
**in the file**, because the next reader's instinct will be to "fix" a list they cannot see a rationale for.

## Exit codes, and the branch that quietly returns 0

```
0  in sync
1  drift found
2  could not measure (network / auth / wrong branch)  — never a quiet pass
```

**Compute the verdict once and return it from one place.** A printer with a `return 0` per output branch
(`--json` vs human) means adding a third branch silently defaults to green — measured: 298 findings printed and
exit status 0, because only the `--json` branch returned 1. A consumer reads the exit code, never the prose.

**A wrong branch name must be exit 2, not 0.** The tree API answers `404` for a branch that does not exist;
if the code catches that and treats an empty tree as "nothing published", the check passes on a typo.

## Falsify both directions before trusting it

```bash
# 1 · in sync must be SILENT (cron-shaped guards deliver stdout)
out=$(check.sh); [ -z "$out" ] && echo 'silent on clean ✅'

# 2 · a one-line change must speak
printf '\n<!-- probe -->\n' >> <live skill>/SKILL.md
check.sh            # must name the file and exit non-zero
<revert>
check.sh            # must be silent again, exit 0
```

A checker that has only ever been green has never been shown to bite.

## The cron wrapper (silent when in sync)

```bash
python3 "$SCRIPT" >"$OUT" 2>&1; rc=$?
case "$rc" in
  0) : ;;                                                    # say nothing
  1) echo "🔴 DRIFT — the published copy is not what we run"; cat "$OUT" ;;
  *) echo "⚠️ CHECK COULD NOT RUN"; echo "This is NOT a pass."; cat "$OUT" ;;
esac
exit 0        # the wrapper always succeeds; the MESSAGE carries the verdict
```

Register with `--no-agent` so stdout is delivered verbatim, weekly, and note in the job's record **when it
retires** (the check stops mattering if the library stops being published).

## The publish pass that keeps one generation

Publishing the missing files without refreshing the stale ones leaves **two generations of the same library in
one repo** — the exact defect the check exists to find. One pass: copy every live skill in a publish category,
refresh every already-published skill from live, remove the renames, then commit once.

Order that works:

1. Compute MISSING / STALE / ORPHAN from the API.
2. Copy live → clone for every STALE, and every MISSING whose category is publishable.
3. Resolve ORPHANs by name similarity before deleting any.
4. **Run the secret scan over the CLONE, not only the live tree** — the clone is what becomes public.
5. Commit with the counts in the message (`+N, refresh M, withheld W`) so history answers "when did this change".
6. Verify from the **published side** (tree API) against the expectation you told the user, not against the
   script's own log.
