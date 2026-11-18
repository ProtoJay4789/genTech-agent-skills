# Whole-file exposure in a public repo

A pattern sweep asks "does a secret appear inside these files?" That question misses the worse case: **an
entire credential file committed to a public repo.** No amount of content-regex discipline finds it if you
only scan files you already know about — the file's NAME is the finding.

## Enumerate as an anonymous visitor

```bash
# No token. No access the visitor lacks.
curl -s "https://api.github.com/repos/OWNER/REPO/git/trees/HEAD?recursive=1" \
  | grep -o '"path": *"[^"]*"' \
  | grep -iE '\.env|secret|credential|token|\.key|private|password|\.pem|wallet|seed|mnemonic|auth'
```

**⚠️ An owner-side recursive grep answers the wrong question.** Sweeping with your own token on your own
checkout tells you what *you* can see. The exposure is what an **anonymous** request can see. Fetch the tree
with no credential, then fetch each hit's raw bytes with no credential, and inspect the response body — that
is the vantage that matters.

**A repo that mirrors a private tree is worse than the sum of its files.** A working copy of a vault, a
backups directory, or a notes mirror publishes handoffs, strategies, memory files and household details in
one move — thousands of files, none individually suspicious. **Treat "this public repo contains a copy of
our private tree" as one critical finding about the repo, not N findings about N files**, and decide repo
visibility before file cleanup.

## Remediation order that actually closes

1. **Make the repo private first.** One PATCH, reversible, stops the exposure while you work. Cleanup on a
   still-public repo is a race you are losing.
2. **Delete the files** — `DELETE /contents/<path>` with the blob sha.
3. **Verify with a cache-busted ANONYMOUS GET.** `raw.githubusercontent.com` serves a cached 200 for a file
   that is already deleted; a plain re-read is not evidence. Append a cache-buster plus
   `Cache-Control: no-cache` and require **404**. Verify as the anonymous visitor, never with the token that
   deleted it.
4. **Prove what is still recoverable, and say so.** Deletion removes the file from the branch head only:
   ```bash
   curl -s -H "Authorization: Bearer $TOK" \
     "https://api.github.com/repos/OWNER/REPO/commits?path=PATH" | jq 'length'
   ```
   Non-zero means the value is still in history. **Report it as still exposed** — private-plus-history is
   much better than public, but it is not closed. History rewrite or **rotation** is the only real close,
   and rotation is the cheaper one.
5. **Never report "removed" from a delete response.** The receipt is a fresh anonymous 404 plus a stated
   history count.

## The audit artifact is a leak vector

A scanner that writes the value it found into its own report has recreated the exposure in a second place —
and if that report lives in a synced folder or a committed directory, it is now distributed.

- **Report `file:line` and the variable NAME; never the value.**
- If a tool has already emitted values, **redact the artifacts in place** — `[REDACTED-SECRET]`, location
  kept so the finding still means something — then verify zero remaining values before archiving anywhere.
- **A recurring scanner needs a retention policy from day one.** Count files and total size before the
  folder becomes unbounded; a nightly report generator with no ceiling becomes one of the larger things you
  own, and it is regenerable output, not records.

## A short public window is still an exposure

"It was only public for twenty minutes" is not a mitigation: public repos are crawled within minutes, and
forks, caches and search indexes do not follow a visibility flip back. **Once a credential file has been
public for any interval, treat it as burned — rotation, not deletion, is the fix.**

## Related

- `references/github-repo-existence-verification.md` — a 404 is three different verdicts; the ladder to run
  before writing "deleted" or "hidden".
- `references/live-secret-leak-scan.md` — proving a hit is a LIVE value, not a placeholder.
