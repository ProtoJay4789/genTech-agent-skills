# Creating a repo and importing a directory — no `gh`, no local clone

For a seat whose credentials are an HTTP token in a `600` file and which has **no `gh`, no `git` remote
helper, and no writable parent filesystem**. Every step below is REST; the content never touches a working
tree, so there is no `.git` to leave behind and nothing to accidentally commit later.

Substitute `$TOKEN` from the file (`TOKEN=$(cat .../secrets/github-token-<account>)`). Never echo it.

## 1 · Create the repo (JSON body from a FILE)

```bash
cat > /tmp/gh/body.json <<'JSON'
{"name":"<repo>","description":"…","private":true}
JSON

curl -sL -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/vnd.github+json' \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/gh/body.json \
  https://api.github.com/user/repos
```

**Pass the body as a file, not an inline string.** An inline `-d '{"name":…}'` assembled in a shell/Python
wrapper failed with `{"message":"Body should be a JSON object"}` — a quoting artefact, not a schema error,
and it reads exactly like a malformed request. `--data-binary @file` removes the quoting layer entirely.

Confirm the answer: `full_name`, `private`, and `message: null`.

## 2 · A brand-new repo is EMPTY, and the git-data API refuses it

```
POST /repos/{r}/git/blobs → 409 {"message":"Git Repository is empty."}
PUT  /repos/{r}/contents/README.md
```

- **`409 Git Repository is empty` is a STATE, not a permission problem** (and the `permissions` block on the
  repo still reads `admin: true`). Do not start debugging the token or the account type.
- **`PUT /contents/<path>` works on an empty repo** and creates the first commit and branch. Seed one small
  file with it (`README.md`), then the blob/tree/commit/ref endpoints all unlock.
- A **404** on `/contents/...` for a repo that exists is the same family of misread: check whether the repo
  is empty before concluding anything about access.

## 3 · Push the tree in ONE commit

```
for each file:  POST /repos/{r}/git/blobs   {"content": <base64>, "encoding": "base64"}   -> sha
POST /repos/{r}/git/trees   {"base_tree": <head sha>, "tree": [{path, mode:"100644", type:"blob", sha}]}
POST /repos/{r}/git/commits {"message": …, "tree": <tree sha>, "parents": [<head sha>]}
PATCH /repos/{r}/git/refs/heads/main  {"sha": <commit sha>, "force": true}
```

Two practical notes:

- **Build the file list in code and skip exclusions there** — that is what makes "the secret was never sent"
  true rather than "the secret was gitignored". Filter by filename, by directory, and by size before the
  bytes are read.
- **Batch in a loop, not one call per hand.** ~100 blobs of a small tree complete in well under a minute;
  the rate-limit binder is search (30/min), not the git-data endpoints (5,000/hr core).

## 4 · Verify the TREE, not the repo metadata

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/$R/git/trees/main?recursive=1" | grep -o '"path": "[^"]*"'
```

Assert three things, and quote them in the report:

1. **the file count** on `main` matches what you intended to send;
2. **the entry point is present** (`server.py`, `package.json`, whatever the project actually starts with);
3. **no path matches a secret** (`api_keys`, `.env`, `*.pem`, `*token*`) — grep the fetched list, do not
   assume the exclusion worked.

**`size: 0` on the repo object right after a successful push does not mean the push failed.** GitHub
recomputes that field asynchronously; a repo can report `0 KB` while `git/trees?recursive=1` lists every
file. Read the tree for content, the repo object only for existence, visibility and default branch.

## 5 · Finish the packaging before calling it published

A repo with no README, no description and no runnable demo is a **second copy**, not a published project —
which is exactly the half of the benefit a private repo is supposed to buy. Decide which halves you are
claiming:

| claim | what proves it |
|---|---|
| "a second copy with history exists" | tree listing + commit sha |
| "another builder could use it" | README + working demo + a stranger can clone it |

Say which one you delivered. Publishing without the second is normal and fine — calling it published is not.
