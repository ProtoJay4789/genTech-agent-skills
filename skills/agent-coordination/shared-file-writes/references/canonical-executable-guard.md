# Canonical-executable guard — prove WHICH file actually runs

The marker-manifest guard (`references/marker-manifest-guard.md`) catches a **content** regression. This one
catches a **routing** fault: several seats edit or own a copy, and the copy that runs is not the one being edited.
The failure is silent by construction — both files exist, both are valid, and the wrapper decides.

## When it is needed

- A script under a shared path (`/opt/data/scripts/...`) is exec'd by more than one seat's wrapper.
- A seat has (or might have) its own copy under `profiles/<seat>/...` that a wrapper could point at.
- You are about to edit a file that another seat also runs on a schedule.

## Shape — a `--canonical-check` mode on the script itself

Put the check in the artifact, not in a separate doc, so it travels with every copy:

```python
def canonical_check() -> int:
    canon = "/opt/data/scripts/<name>.py"
    here  = os.path.realpath(__file__)
    mine  = hashlib.md5(open(here, "rb").read()).hexdigest()
    print(f"CANONICAL {canon}\nRUNNING   {here}\nMD5       {mine[:12]}  ({os.path.getsize(here):,} B)")
    if here != os.path.realpath(canon):
        return 3                      # running a copy, not the canonical file
    rc = 0
    for w in sorted(glob.glob("/opt/data/profiles/*/scripts/*-<job>.sh" )):
        execs = canon in open(w, encoding="utf-8", errors="ignore").read()
        print(f"  {'OK ' if execs else 'BAD'} {w}")
        rc = max(rc, 0 if execs else 2)
    for fork in sorted(glob.glob("/opt/data/profiles/*/skills/**/<name>.py", recursive=True)):
        h = hashlib.md5(open(fork, "rb").read()).hexdigest()
        rc = max(rc, 0 if h == mine else 3)
    return rc
```

Exit codes that mean different things, so a wrapper can act on them:

| verdict | meaning | action |
|---|---|---|
| 0 | every wrapper execs the canonical path, no divergent fork | proceed |
| 2 | **a wrapper execs something else** — the edit you are about to make lands in a file that never runs | stop, fix the wrapper first |
| 3 | **a byte-divergent copy exists on a seat** — a fork, or the artifact you read is not the one running | name the fork before editing |

## Marker in the header, naming the contract

The file's own header is the only doc a seat reads when it opens the file to edit:

```
# ⚠️ FLEET-SHARED FILE — ONE CANONICAL COPY, N WRAPPERS. Read this before editing.
#   Canonical path : <abs path>
#   Exec'd by      : profiles/{a,b,c}/scripts/<job>.sh  (thin wrappers, `exec python3 <canonical>`)
#   A copy under profiles/<seat>/... is NOT this scanner — it is a FORK, and a fork that runs
#   instead of this file is invisible to every other seat.
#   Verify: python3 <canonical> --canonical-check
```

The precedent worth quoting in it: a shared wrapper whose path was hardcoded to one seat meant three seats
ran another department's instrument and printed it as their own — the fix was to resolve the seat from the
invocation path, and the marker exists so nobody re-hardcodes it.

## Order of operations

1. `--canonical-check` **before** the edit — a fork discovered afterwards invalidates the work.
2. Back up with a digest: `cp -a f f.bak && md5sum f f.bak` (two identical lines is the receipt).
3. Edit the **canonical** file only.
4. `--canonical-check` **after** the edit — catches a wrapper that was moved mid-pass, and confirms the seats
   you think run this actually do.

## Pitfalls

- **A repo-wide `grep` for the old hardcoded path still hits — inside the comment that documents the fix.**
  Counting occurrences is not reading the executed line; grep the line that assigns/execs, or the guard will
  report a bug that was fixed.
- **The wrapper count is the finding.** Two seats is not "the fleet"; enumerate every wrapper and print each verdict
  so a missing one is visible rather than assumed.
- **A copy under a cache/scratch path is a test artifact, not a fork** — exclude those from exit 3, or every
  scratch copy trips the guard and it gets ignored.
- **The guard must run from the artifact's own directory context**; `__file__` under a symlinked or relative
  invocation resolves differently, so compare `os.path.realpath` on both sides.
