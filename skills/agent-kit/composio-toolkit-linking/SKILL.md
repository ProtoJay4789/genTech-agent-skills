---
name: composio-toolkit-linking
description: "Use when an agent must act through a Composio toolkit."
version: 1.0.0
author: arthur
license: MIT
metadata:
  hermes:
    tags: [composio, integrations, oauth, files, google-drive, cli]
    related_skills: [agent-tool-contracts, secret-handling-in-chat, host-access-delegation]
---

# Composio — reaching an app your tool catalog does not expose

Composio can act on hundreds of apps (Drive, Gmail, Slack, GitHub) even when the agent's own connector
catalog shows none of them. The catalog is **your tool wiring**; Composio is **the platform**. Do not
report one as the other.

## When to Use

- A task needs an app (Google Drive, Gmail, Sheets…) that is not in the connector list.
- A user asks you to read or write something in an account they own.
- You previously concluded "the capability is missing" — verify that first (see rule 1).

## Rule 1 — a 401 is not a 404

Before declaring a capability absent, probe the API with a deliberately bogus key:

```
GET https://backend.composio.dev/api/v3/toolkits?search=googledrive
x-api-key: bogus-probe-key
```

- **401 `APIKey_InvalidAPIKey`** → the endpoint and toolkit exist; only auth is missing.
- **404** → the route genuinely is not there.

A missing entry in your connector catalog means nothing about the platform. This exact confusion cost an
hour and a wrong answer to the user.

### Three failure states, three different fixes — and they look the same in a report

A toolkit link can be down for three unrelated reasons. Naming the wrong one sends the user to fix the
wrong thing:

| HTTP | meaning | who fixes it |
|---|---|---|
| **404** | the route does not exist | nobody — wrong path |
| **410** `no longer available… upgrade to v3` | **we are calling a retired API version** | us — change the endpoint |
| **401** `APIKey_InvalidAPIKey` | the credential is dead or revoked | the user — reissue the key |
| **503** `DEPLOYMENT_PAUSED` / “deployment is currently unavailable” | **the vendor's own service is down** | nobody here — report the vendor outage, do not propose a rotation |

**A vendor outage is not a credential finding.** When the platform's own endpoint is returning 5xx, a
fresh key changes nothing and asking the user to mint one wastes their round trip. Probe the bare
host once — `curl -o /dev/null -w '%{http_code}' https://<vendor>` — and if that is 503 too, say the
service is down and stop. The distinction the report must carry: **“your key is revoked”** and **“their
service is paused”** send the user to two different places, and only one of them is theirs to fix.**

A retired version, a revoked key and a paused deployment can all be true in any combination.** They
stack, and fixing one leaves the integration just as dead as before — so resolve them in order
(version → vendor liveness → credential) and re-probe after each, rather than re-running the same
`curl` and reading the same 401.

**A retired version and a revoked key stack.** Both can be true at once, and fixing either alone leaves
the integration dead. Probe v3 *after* any version fix, or the retry looks identical to the first
failure.

```bash
KEY=$(cat /opt/data/shared-secrets/composio_api_key)
curl -s -o /dev/null -w "v1 %{http_code}\n" -H "x-api-key: $KEY" https://backend.composio.dev/api/v1/connectedAccounts
curl -s -o /dev/null -w "v3 %{http_code}\n" -H "x-api-key: $KEY" https://backend.composio.dev/api/v3/connected_accounts
```

**`/api/v1/connectedAccounts` is retired (410). Live discovery is `/api/v3/connected_accounts`.** Any
script, cron or note still pointing at v1 is broken regardless of the credential.

### A key file on disk is not a live integration

Finding `shared-secrets/composio_api_key` proves a credential was **installed once**, not that it works
and not that the toolkit is still linked. Report the three facts separately:

1. the key file exists (and its length, never its value)
2. the key **authenticates** — a real call, not a grep
3. a **connected account is ACTIVE** for the toolkit you need

A dead-but-present key is the most misleading state: every local check says "configured", and the
answer to "do we have access?" is no. Say "we lost it, here is the evidence" rather than "we should
have it somewhere".

**Restoring it takes two independent steps, and the second is not optional:** reissue the key on the
platform, *then* re-authorise the connected account — Composio holds the upstream OAuth grant, so a
new key alone restores nothing. Say that up front so the user is not surprised by a second round trip.

## Procedure

### 1. Install the CLI (inspect the script first)

```bash
curl -fsSL https://composio.dev/install -o composio-install.sh
# read it: it should fetch from GitHub releases and verify checksums; no sudo, no data POSTs
COMPOSIO_QUIET=1 COMPOSIO_INSTALL_DIR="$HOME/.composio" sh composio-install.sh
```

**Rootless hosts usually lack `unzip`** and the installer hard-requires it
(`unzip -oqd DIR FILE`). Write a shim that satisfies that call instead of asking for root:

```sh
#!/bin/sh
# ~/.local/bin/unzip — extraction only, via Python
 dir=""; archive=""; prev=""
for a in "$@"; do
  case "$a" in
    -*) case "$a" in *d*) prev="d" ;; *) prev="" ;; esac ;;
    *)  if [ "$prev" = "d" ]; then dir="$a"; prev=""; else archive="$a"; fi ;;
  esac
done
exec python3 -c 'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$archive" "${dir:-.}"
```

Then `PATH="$HOME/.local/bin:$PATH"` for the install.

### 2. Authenticate — browser flow, never an agent identity

```bash
composio login --no-wait --yes     # prints a URL; exits without opening a browser
composio login --poll              # completes it once the human clicks
```

- **The pending session expires in MINUTES.** Across a chat round-trip it will often be dead. Generate the
  link and have the human click inside the same minute; expect to retry two or three times.
- **`composio login --agent` exists and must not be used when a human is present.** It creates a throwaway
  Composio account, so the work lands in an identity that is not the user's. The CLI's own hint says so.
- An API key is optional and durable: `composio login --user-api-key "$(cat secrets/composio_api_key)"`.
- Verify identity before proceeding: `composio whoami` → `{"account_type":"human","email":…}`.

### 3. Link the toolkit (OAuth consent is the human's, not yours)

```bash
composio link googledrive --no-browser --no-wait
# → {"status":"pending","redirect_url":"https://connect.composio.dev/link/…","connected_account_id":"ca_…"}
```

Hand the URL to the human, then confirm it turned real:

```bash
composio connections list    # want status ACTIVE, not INITIALIZING or EXPIRED
```

`INITIALIZING` = waiting on their click. `EXPIRED` = the link died; generate another. Leave dead entries
alone unless removal is trivially scriptable — `connections remove` is interactive-only.

**Every `link` call creates a NEW pending connection.** A call that blocks or times out still leaves an entry
behind, so a host with no browser produces a second `INITIALIZING` account each time it is retried. Call
`link --no-browser --no-wait` **once**, hand over the URL, and then poll `connections list` — do not re-link
while one is already pending. Removal is interactive, so that clutter is effectively permanent.

### 4. Find, inspect, then execute

```bash
composio search "upload a file to google drive"        # returns slugs
composio execute GOOGLEDRIVE_UPLOAD_FILE --get-schema  # read the real field names
composio execute GOOGLEDRIVE_UPLOAD_FILE -d '{"file_to_upload":"/abs/path/file.pdf"}'
```

**`--file <path>` appears in `--help` but fails with "Invalid JSON input"** — pass the path inside the `-d`
JSON under the schema's own file field instead of using the flag.

**Schema key names are CamelCase per API, not snake_case** — `fileId`, not `file_id`. Passing the wrong
name returns a validation error listing the correct keys; read it rather than guessing twice.

**Replacing a file's contents is a different tool from uploading one.** A corrected local file uploaded again
creates a *second* remote copy with a new id, so the link already handed to the user keeps serving the old
content. Update in place instead:

```bash
composio execute GOOGLEDRIVE_UPLOAD_UPDATE_FILE \
  -d '{"fileId":"<existing id>","file_to_upload":"/abs/path/file.pdf"}'
```

Then read the metadata back and confirm `size` equals the new local byte count and `modifiedTime` moved. **The
user's shared link is the artifact — if it still shows the old bytes, the fix did not land where it matters.**

### 5. Verify by read-back, never by the write response

A successful upload response is not proof the file is there, correct or complete. Read it back and compare:

```bash
composio execute GOOGLEDRIVE_GET_FILE_METADATA -d '{"fileId":"<id>","fields":"id,name,size,mimeType,createdTime,webViewLink"}'
```

Check the returned `size` against the local file byte count. **Only then report success.**

## Before asking for a new key: is there a first-party path ALREADY on the host?

**A broker credential is a single point of failure.** Every hop through a platform that holds the
upstream OAuth grant means one vendor decision — a revocation, a paid-tier change, a paused deployment
— silently removes access to an account the user still fully controls. When the broker route is
blocked, **check the host for a first-party client before asking the user to fix the broker.**

**What to look for, in one pass:**

```bash
python3 -c "import googleapiclient, google.oauth2, google_auth_oauthlib; print('client libs OK')"
find /opt/data/.obsidian-vault/10-Labs/skills-distribution -ipath '*google-workspace*' -name '*.py'
```

**A bundled provider skill normally ships its own non-interactive auth flow**, and it is designed to be
driven *by the agent* — `--check`, `--client-secret <path>`, `--auth-url`, `--auth-code <code>`. That
means the whole setup is: the user downloads one OAuth client JSON from the provider's console, you
run four commands, they click a link once. **No broker, no third-party grant, no revocable key in
someone else's dashboard.**

**Say the trade honestly when recommending it:** a first-party token is *more* setup and *less* likely
to vanish. The failure mode that killed the broker route cannot recur, because nobody else holds the
grant.

**Order of preference when an app must be reached:**

1. the agent's own connector catalog (if the app is listed)
2. the app's provider skill + first-party OAuth — durable, self-owned
3. a broker platform like Composio — fastest to wire, most fragile in operation

**Pursuing (3) first is reasonable once. Rebuilding it after it has already expired once is not** —
that is the moment to move down the list, and to say why.

## Pitfalls

- **Do not claim a platform cannot do something because your catalog omits it.** Probe for 401 vs 404.
- **Do not use `--agent` login with a human present** — you would authorise the wrong identity.
- **Never type a password or approve OAuth yourself.** The consent click belongs to the account owner.
- **Secrets pasted in chat:** seal to `secrets/<name>` at mode 600, delete the message, scan the vault for
  residual copies, never echo the value. Do it before anything else.
- **Uniform rejection across every endpoint means the key is DEAD, not under-scoped.** Modern APIs issue
  least-privilege keys, so the tempting diagnosis for a 401 is "this key lacks a permission" — and that
  sends the user to add a scope, which cannot fix a revoked credential. **A scoped key is accepted
  somewhere and forbidden elsewhere; a dead key is refused everywhere, identically.** Probe several
  unrelated read endpoints before asking for anything: measured, seven endpoints across three hosts all
  returned the same `APIKey_InvalidAPIKey`, while an empty header produced a *different* error
  (`NoAuthProvided`) — which proves the key was parsed and rejected rather than unrecognised. **Identical
  failure at every address is a credential verdict; a mixed pass/fail pattern is a scope verdict.**
  Different remedies (reissue vs. re-scope), so quoting the wrong one costs the user a round trip.
- **A rejected key is not always a truncated key.** If the same 23-character string arrives twice, it is
  invalid, not mis-copied — say so instead of asking for it a third time.
- **Scope to the ask.** Linking Drive does not mean touching Gmail.
- **Rate your own report.** "It uploaded" from the tool's response is a claim; from a metadata read-back it
  is a receipt.

## Related

- `agent-tool-contracts` — the same boundary discipline for tools that take generated arguments.
- `secret-handling-in-chat` — the paste-redaction protocol used above.
- `host-access-delegation` — when the missing thing is root, not a credential.
