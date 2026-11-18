# Recovering a wiped container's estate — enumerate, don't assume

A container wipe destroys the filesystem, not the archive. Everything ever pushed survived. The failure
mode is not "the data is gone" — it is **nobody looked in the right place**, because everyone trusted a
hand-written list of "our repos" instead of enumerating.

## Rule 1 — enumerate the whole account before concluding anything is lost

```bash
TOK=$(cat <profile>/secrets/github-token)
curl -s -H "Authorization: Bearer $TOK" "https://api.github.com/user/repos?per_page=100&affiliation=owner&sort=pushed"
```

A curated list of "the repos we own" **is how repos go missing for weeks.** Enumerate every time.

## Rule 2 — inspect file trees WITHOUT cloning

Recursive trees cost one API call per repo and no disk:

```bash
curl -s -H "Authorization: Bearer $TOK" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1" \
  | python3 -c "import json,sys; [print(x['path']) for x in json.load(sys.stdin)['tree'] if x['type']=='blob']"
```

This finds the one file you need in a 157 MB repo without downloading 157 MB. **Pattern-match the paths
for the categories that matter, then clone only what the tree justifies.** Sweep a whole account this way
in one pass; clone selectively.

## Rule 3 — two categories to search, and they answer different questions

- **Key-shaped** (`keystore|shard|mnemonic|passphrase|private-key|\.enc$|custody|wallet.*\.key`) —
  answers "can we recover the money?" Expect **false positives**: skill docs *about* wallet management,
  test fixtures, `node_modules` internals. Resolve every hit before claiming either answer.
- **State/doctrine-shaped** (`cron/jobs\.json|MEMORY\.md|state/|SKILL\.md|hub\.html|tenants\.json`) —
  answers "what did this system know and do?" This is where the real recoveries hide.

## Rule 4 — know what a backup actually captured before trusting it

**Read the backup script.** A "nightly backup" is only evidence for what it enumerates. One that copies
memories, skills, config, SOUL and cron does **not** hold a key stored elsewhere, and no amount of output
inspection will reveal that — only the script will.

## Rule 5 — a name-pattern sweep proves presence, not absence

Sweeping file *paths* finds things with telling names. It cannot prove a valuable file has no value.
At current HEAD it also misses anything deleted in an earlier commit. **State both limits when you
report a negative.** "No keys found" from a path sweep is strong evidence; "nothing else valuable
exists" is not.

## Rule 6 — clone mechanics that fail in misleading ways

- `x-access-token:<TOK>@github.com/...` for git. `Bearer` works only on the API — a `Bearer` git URL
  fails like an auth error.
- **Check the branch**: `git ls-remote --heads origin`. Assuming `master` when it is `main` produces a
  push failure that reads like a permissions problem.
- **Never pre-create the clone destination** — `mkdir` then `git clone` fails with "destination path
  already exists and is not empty."
- **`| tail && echo pushed` masks a failed push.** Verify by reading the remote back:
  `git ls-remote origin refs/heads/<branch>` and compare shas.

## Rule 7 — the archive is not a substitute for custody

Recovering code and doctrine is not recovering keys. **Keys that lived only inside the host are gone,
and no repo sweep changes that.** Say which category each recovered thing is in, so nobody mistakes a
restored estate for a restored wallet.
