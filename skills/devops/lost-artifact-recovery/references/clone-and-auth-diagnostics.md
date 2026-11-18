# Clone and Auth Diagnostics

For the moment a recovery clone fails and you must decide what that means. A failed clone has several causes
that look identical from the caller's side, and only a control separates them.

## The ladder — cheapest first, stop at the first "fine"

```bash
# 1. Are git and the network fine at all? Clone a STRANGER's well-known repo.
git clone --depth 1 https://github.com/octocat/Hello-World.git /tmp/ctrl
#    WORKS  → git + network are fine. The problem is OUR path or OUR credential.
#    FAILS  → the problem is the environment, not the repo.
```

If the control works, the remaining causes are, in order of likelihood:

1. **Wrong namespace.** Repos can be owned by a **user** or an **org**, and the names often differ by one
   character (a hyphen is the classic). Both forms return the *same* clean `404` — a wrong owner name is
   indistinguishable from a deleted repo.
2. **Wrong credential / wrong header format.** See below.
3. **A genuine flag, or a private repo you cannot see.** Last, and only after 1 and 2 are excluded.

## Never reconstruct the namespace from prose

Read it off data you already have. `GET /user/repos` returns per repo:

- `owner.login` — the authoritative owner string
- `full_name` — `owner/name`, authoritative casing
- `clone_url` — the exact URL to use

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "https://api.github.com/user/repos?per_page=100&sort=updated" \
  | python3 -c "import json,sys; [print(r['full_name'], r['clone_url']) for r in json.load(sys.stdin)]"
```

**Print these verbatim into the clone command.** Do not retype the owner from memory or from a different note
— the whole failure mode is a one-character difference that reads as data loss.

## Header formats — git-over-HTTPS is not the REST API

The API accepts `Authorization: Bearer <token>`. **git-over-HTTPS does not reliably** — it wants Basic:

```bash
umask 077
B64=$(printf 'x-access-token:%s' "$(cat "$TOKFILE")" | base64 -w0)
printf '[http "https://github.com/"]\n\textraHeader = "Authorization: Basic %s"\n' "$B64" > /tmp/gcfg
chmod 600 /tmp/gcfg
GIT_CONFIG_GLOBAL=/tmp/gcfg git clone --depth 1 <url> <dest>
rm -f /tmp/gcfg
```

A `Bearer` header here fails and looks exactly like an invalid token. **Before concluding a token is dead,
re-issue the request in the format the tool expects** — a format error and a dead credential are
indistinguishable from the error text alone.

## Keep the credential out of `argv` and out of output

- **Never** pass a token as a command-line argument: the process list is readable on many systems.
- Prefer a config file read by the tool (`GIT_CONFIG_GLOBAL`, a `curl -K` header file), created `600` and
  deleted in the same command.
- **Print prefixes and metadata, never values:** byte count, first few characters, mtime, and permissions are
  enough to identify which copy you tested.
- Report **which path** you tested. "The token is dead" without the path is unreproducible.

## Red herrings this ladder exists to prevent

- **`remote: Repository not found`** on a repo the API lists → check the namespace *before* anything else.
- **An anonymous `404` where a control returns `200`** → commonly read as "our account is hidden/flagged". It
  has several mundane causes, namespace first. Do not write an incident note from one `404`.
- **A fresh clone's mtimes are all identical** → that is the clone time, not the content date. Never use mtime
  to order versions across a clone boundary.
