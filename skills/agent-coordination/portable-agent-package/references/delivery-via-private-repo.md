# Delivering a package as a private repository

When the recipient cannot be reached by folder copy — different machine, different cloud, no shared
storage — a **private repo** is the fastest delivery: clone, copy, done. This file is the procedure and
the traps.

---

## 1 · Measure access before promising it

**A token that can read is not a token that can create.** Check the two things separately, before the
user has been told the delivery is arranged:

```bash
# who is this token, and what may it do?
curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/user | grep '"login"'
curl -s -D - -o /dev/null -H "Authorization: Bearer $TOKEN" https://api.github.com/user \
  | grep -i '^x-oauth-scopes'
```

- **Classic token** → the `x-oauth-scopes` header lists scopes. `repo` is required to create a private
  repo.
- **Fine-grained token** → the header is absent. Access is per-repository and a *new* repo is outside
  its grant; that is a refusal, not an outage.
- **No `gh` CLI installed is not a blocker.** The REST API does everything the CLI does; do not stall
  the delivery on installing tooling. Only install if the CLI genuinely saves work.

---

## 2 · Create it private — the flag is not the proof

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  -d '{"name":"<repo>","description":"<one line>","private":true,
       "has_issues":false,"has_wiki":false,"has_projects":false,"auto_init":false}' \
  https://api.github.com/user/repos
```

**`"private": true` in the response is the API agreeing with you, not the world's view.** The only
proof of privacy is an **anonymous** request being refused:

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>
# 404  → private, confirmed (unauthenticated)
# 200  → PUBLIC. Stop and fix before adding a single file.
```

**Do this check before the first upload.** A repo that is briefly public with credentials-adjacent
content in it cannot be un-exposed by deleting the file.

---

## 3 · Upload, then verify by reading the tree back

One `PUT .../contents/<path>` per file, base64 body, `message` describing the change:

```bash
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  --data @payload.json \
  "https://api.github.com/repos/<owner>/<repo>/contents/<path>"
```

**A 201 on each PUT is not the delivery.** Read the whole tree back and compare against what you meant
to send:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1"
```

**Check three things in that response:** the file count matches the source folder, no path is
unexpected, and `"truncated": false` — a truncated tree silently omits files from your own proof.

---

## 4 · ⚠️ Purge build artifacts before the first upload

The folder you packaged is almost never clean. **Filter before you enumerate**, not after the tree
comes back:

| artifact | where it hides |
|---|---|
| `*.bak`, `*.bak-*`, `*.orig` | beside the file that was edited |
| `*.bak-<key>-<timestamp>` | beside any config a tool rewrites |
| `.DS_Store`, `Thumbs.db` | anywhere a GUI touched it |
| `__pycache__/`, `*.pyc` | beside any imported module |

**A backup file beside a skill is a stale copy of that skill**, and once it is in the repo the
recipient has two versions with no way to tell which is current. It is the same class of mistake as
shipping a credential: easy to do, invisible in a file count, embarrassing to explain.

```python
files = [f for f in files
         if not re.search(r'(\.bak|\.orig|\.pyc|__pycache__|\.DS_Store)', f[0])]
```

If they already went up, delete each with `DELETE .../contents/<path>` and the file's `sha`, then
re-read the tree to confirm the count dropped.

---

## 5 · ⚠️ A private repo on a free plan is visible to the OWNER ONLY

**This is the step that looks finished and is not.** The repo exists, is private, and contains
everything — and the recipient cannot open it, because a private repo on a free plan grants access to
exactly one account.

**So "private repo, only they can see it" is not achievable by visibility alone.** Someone must be
granted access:

1. **Repo → Settings → Collaborators → Add people → their username.** The owner does this; it is two
   clicks and it always works.
2. **API** — `PUT /repos/{owner}/{repo}/collaborators/{username}`. Works only if the token carries
   the right admin scope for org-owned repos and the username exists. **Do not promise this path:** it
   fails opaquely for outside collaborators and a half-finished invite is worse than none.

**Ask for the recipient's username in the same message where you report the repo is ready**, so the
handoff does not stall on a question nobody asked.

**Also true of a PRIVATE package regardless of transport:** a private repo is a delivery vehicle, not
an invitation. Say plainly whether the recipient can see it *right now*.

---

## 6 · Report

```
repo      <owner>/<name>   private: confirmed by anonymous 404
files     N (source had N) · total bytes
verified  git tree read back, not truncated
pending   <recipient> cannot see it until they are added as a collaborator
```

**What to say when the recipient still cannot open it:** state it in one line, name the single action
that fixes it, and do not bury it under the upload statistics. **A delivery nobody can open is not a
delivery — it is a draft.**

---

## 7 · ⚠️ When the recipient is an AGENT, public may be the correct answer — and it is irreversible

**An agent cannot clone a private repo without its own credential.** So "make it public so their agent
can just read it, then delete it tonight" is a legitimate plan, not a shortcut. It is also the only
delivery in this file that **cannot be undone**.

**Why "delete it tonight" does not undo it:** public repos are indexed and mirrored within minutes. A
crawler that read the file has already copied it, and that copy survives your delete. **Public is a
publication, not a visibility toggle.**

### Before flipping

**A term-scrub is not a content audit.** Removing the words you thought of (a name, a city, a family
detail) leaves everything you did not think of. The question that actually gates publication is:

> **Does every file in this package belong to the person it is FOR?**

Not *"does it contain words I searched for"*. Scan for **your own identity** with the same rigour you
scan for credentials — the sender's org and seat names, absolute paths into the sender's host, wallet
addresses, hostnames, account handles, other people's IDs, and internal repo names. **A skill shipped
that references the sender's infrastructure is the sender's skill, and it takes their layout with it.**

```python
OURS = {
  "seats/org":  r"(?i)\b(<name-a>|<name-b>|<org>)\b",
  "host paths": r"/opt/<stack>/|<private-dir>",
  "wallets":    r"0x[0-9a-fA-F]{40}",
  "hosts":      r"(?i)<your-domain>|<your-hostname>|<github-login>",
  "account ids": r"\b\d{17}\b",          # Steam/Discord-style snowflakes
  "personal":   r"(?i)\b(<names you were told>)\b",
}
```

**Expect the scan to hit files you did not write.** A package assembled from a backup of the
recipient's old skills can be 100% the sender's material — those skills were authored *during work on
the sender's stack*, so they carry the sender's hosts, paths, wallets and — worst case — a shared
household registry belonging to neither party.

### If the audit finds your own material

**Do not publish.** Revert to private immediately and re-verify with an anonymous request before doing
anything else — a half-second of public exposure is still exposure, and the revert is one API call:

```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" -H "Content-Type: application/json" \
  -d '{"private":true}' https://api.github.com/repos/<owner>/<repo>
curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>   # expect 404
```

**Then rewrite, do not strip.** Placeholdering (`<omitted>`, `<your-host>`) produces a skill that reads
as complete and breaks the first time it is followed — it instructs the reader to run commands against
paths that do not exist on their machine. **A rewritten skill with no reference to anyone's
infrastructure is correct; a redacted one is a trap that looks like a deliverable.**

### After flipping — verify from the stranger's vantage

**The token can see everything; the recipient sees only what is public.** Fetch every file
**anonymously** and scan that, because that is exactly what the recipient's agent will read:

```bash
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>"   # no auth header
```

- expect `200` on the browser URL with no token, and `200` on each raw file
- run the ownership scan against the downloaded text, not against the local folder — the two differ
  the moment a file failed to upload or an old version is still cached
- **report the scan result as the receipt**, not the file count

### What still needs the owner's word

**Deleting the repo deletes the only copy the recipient's agent read from.** So the close of a public
handoff is two facts, not one: *it is readable now*, and *deletion waits until they confirm they have
copied it*. Never delete on your own initiative at the end of the session — ask.
