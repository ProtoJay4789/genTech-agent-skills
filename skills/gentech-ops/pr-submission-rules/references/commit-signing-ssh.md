# Commit signing from a headless node — SSH keys, no GPG, no root

**This SUPERSEDES the older note in the bot-trap table that said commit signing "cannot be automated from a
headless build node" and should be escalated as Tier 3 to the human.** That was wrong. Signing is fully
scriptable here with `ssh-keygen` + git's SSH signing support: no GPG, no root, no browser, no hardware token.

Only escalate when the key genuinely needs something you cannot unlock (a password-protected key, a hardware
token). Absent that, sign it here.

## Why it matters more than it looks

The CI comment that raises this is not a soft warning. In the same comment:

> "The team will not review this PR before ALL commits have been verified and it will be closed after 1 week
> of inactivity."

So an unsigned PR is not "slow" — it is a **one-week countdown to auto-close**, and it will be closed while
looking like it is simply waiting for review. That is why the signing state has to be read the day the PR
opens, not on a weekly sweep.

## Set up once per host

```bash
KEYDIR=~/.secrets/signing
mkdir -p "$KEYDIR" && chmod 700 "$KEYDIR"
ssh-keygen -t ed25519 -N '' -C "<label>@<domain>" -f "$KEYDIR/id_ed25519"
chmod 600 "$KEYDIR/id_ed25519"; chmod 644 "$KEYDIR/id_ed25519.pub"
```

## Configure the repo

```bash
git config gpg.format ssh
git config user.signingkey "$KEYDIR/id_ed25519"
git config commit.gpgsign true
```

## Sign the work

For a single existing commit (the usual case when CI flags a PR already open):

```bash
git commit --amend --no-edit -S
git push --force <fork-remote> <branch>:<branch>
```

A force-push is required — the commit hash changes, and the CI bot re-scans on push.

## Register the key — the endpoint is the trap

**`POST /user/keys` registers an AUTHENTICATION key. It does not make the key a SIGNING key.**

Registering there produces a commit that carries a real, valid signature while GitHub answers
`verified: false, reason: unknown_key`. Signing registration is a **separate** endpoint:

```bash
curl -s -X POST -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  -d "{\"title\":\"<label> signing key\",\"key\":\"$(cat $KEYDIR/id_ed25519.pub)\"}" \
  https://api.github.com/user/ssh_signing_keys
```

List what is already registered to avoid duplicates:

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/user/ssh_signing_keys   # signing keys
curl -s -H "Authorization: token $TOKEN" https://api.github.com/user/keys              # auth keys (different!)
```

## Verify from the side that decides

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/repos/<o>/<r>/commits/<sha> \
  | jq '.commit.verification | {verified, reason}'      # want: verified true, reason valid
```

## Two false alarms to expect

- **`git log --format=%G?` returns `N` and that is NOT a signing failure.** SSH signatures need
  `gpg.ssh.allowedSignersFile` before git will trust them locally. Configure it if you want local
  verification, or use `git verify-commit HEAD`; either way, **GitHub's `verification` block is the authority**
  because GitHub is what decides whether the PR is reviewable.
- **`reason: unknown_key` looks identical to a bad signature.** It is not — it means the signature is fine and
  the *key registration* is the wrong kind. Check `/user/ssh_signing_keys` before touching the commit again.

## Also confirm the author identity

Signing and authorship are separate checks. A signed commit whose author email is not verified against the
GitHub account still trips the CLA bot. Verify `git config user.email` is a GitHub-verified address before
committing, then sign.
