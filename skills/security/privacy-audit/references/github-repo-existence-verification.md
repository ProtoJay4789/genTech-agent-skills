# Is this GitHub repo deleted, gated, or misnamed?

**A 404 from GitHub is not proof of absence — it is proof of no access.** GitHub deliberately returns
404 instead of 403 for repos a credential cannot administer, so it never confirms that a private or
gated repo exists. Three different situations render as the identical 404:

| Verdict | Signature | What it means for an exposure finding |
|---|---|---|
| **Genuinely deleted** | anonymous raw fetch 404 **and** token API 404 **and** the owner path gone | finding is closed |
| **Exists, no access** | token API 200 on the repo, 404 on `/settings` | you lack admin — the owner's hand is required, exposure stays open |
| **Wrong namespace** | the URL's owner does not hold the repo | the link is dead, the repo is not — find the real owner |

## The ladder — run all four, in order, before writing "deleted" or "hidden"

```bash
T=$(cat <path to token> | tr -d '\n\r ')
OWNER=<owner>; REPO=<repo>; FILE=<path in repo>; BRANCH=<branch>

# 1. what a stranger sees — no auth, no cache
curl -sL -o /dev/null -w 'raw  anonymous      %{http_code}\n' \
  "https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH/$FILE"

# 2. does the repo exist at all? (private repos answer 200 to an authorized token)
curl -s -o /tmp/r.json -w 'repo API          %{http_code}\n' \
  -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO"

# 3. can THIS credential administer it? (404 here is the access-hiding 404)
curl -s -o /dev/null -w 'settings page     %{http_code}\n' \
  "https://github.com/$OWNER/$REPO/settings"

# 4. is the owner an ORG or a PERSONAL USER?
curl -s -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/orgs/$OWNER" | head -c 300; echo
```

Step 4 is the one people skip. `GET /orgs/<name>` returns `login` / `type: Organization` /
`public_repos` for an organization, and `{"message":"Not Found"}` for a personal user account — a
personal account is not an org endpoint and never will be.

## The namespace trap — two spellings, two owners

Owner names that differ only in punctuation are different accounts. Measured: an organization spelled
with a hyphen and a personal user spelled without it owned a repo of the same name — the org README
linked to the **org** path and returned 404, while the file the README meant to advertise was served
publicly from the **personal** account, key included.

Consequences that matter for an exposure audit:

- **"The org copy is deleted" is not "the leak is closed."** The org and the personal account are two
  locations. The distinct-secrets rule already says one key in two places is one finding with two
  locations; a same-named repo under two owners is the same situation.
- **"The link 404s" is not "the repo is gone."** A dead link in a README is a broken-link finding, not
  an acquittal. Fetch the file by the path that resolves.
- **Name the ACCOUNT in the finding**, not just the repo — `owner/repo` where owner is the real owner.
  Otherwise the next reader searches the wrong namespace and reports a live leak as closed.

## Approval is not access

When only the repo owner can delete, the exposure stays open until the deletion is *measured*. An
authorization to delete is a decision; a `DELETE /repos/<owner>/<repo>` returning **403 "Must have admin
rights to Repository"** is the proof that the blocker is the hand and not the permission.

Report it as **open**, name the exact owner-only action required, and keep it open until a fresh
**anonymous** fetch of the file itself returns 404. Do not accept "I approved it" or "it should be
gone" as closure — both read as closed while the bytes are still served.

Also worth checking before declaring a repo hidden: a deleted repo does not leave its siblings dead. If
`README.md`, `foundry.toml`, or any other file in the same repo still returns 200 anonymously, the repo
is live and the 404 came from somewhere else — most often the access-hiding path or the wrong owner.

## Why this matters more than a status code

A 404 read as "already handled" removes the item from the queue. The exposure then persists for months
while every subsequent report says it was closed — the same failure as a check that cannot go red, but
inverted: a red result read as green. **The verdict must come from a measurement that can distinguish the
three causes, and the only such measurement is all four steps.**
