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

### The fourth failure state: platform CONNECTED, toolkit UNLINKED — and it answers zero, not an error

**A toolkit that was never linked does not fail. It returns an empty result set**, which is
indistinguishable from "this account genuinely has none". Measured: a Sheets search returned zero results for
every query while the SAME Google account listed the very file being searched for through Drive — one toolkit
linked, the other not, both reporting success.

- **Before reporting an empty result, prove the toolkit is linked for the account you are calling.**
  `composio connections list`, filtered to the toolkit AND the alias/`ca_` id used in the call. `ACTIVE` for
  `googledrive` says nothing about `googlesheets`.
- **Prove the rail with a known-present object.** Search for something you know exists before you search for
  what you want. A query returning zero on an item you can name is a LINKAGE finding, not a data finding.
- **Each product is its own toolkit and its own consent** — Drive, Gmail, Sheets, Calendar, Docs. Linking one
  is not linking the family, so "Google is connected" is wrong in the most expensive direction: it reads as
  done and sends nobody back to finish it.
- **Say which world you are in.** "The account holds no such file" and "Sheets is not linked, so I cannot see
  anything" lead to opposite next actions. Returning a calm blank for the second is the failure this whole
  skill exists to prevent — an absence you did not measure is not an absence.

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
composio login --no-wait --yes --no-skill-install   # prints a URL; exits without opening a browser
# hand the URL to the human, then:
composio login --poll                               # completes once they click; polls ~10 min
```

**⚠️ A rejected API key is NOT a reason to ask the user for another key.** Measured: a key the user had
just created was refused by REST (`APIKey_InvalidAPIKey`, three endpoints, both header styles) and by the
CLI (`Invalid or revoked user API key`) — and the fix had nothing to do with keys. A browser login
succeeded immediately on the same host, resolved the organization, and `whoami` returned a real human
identity. **A browser session supersedes the key entirely:** it carries the human's own identity and
selects the org, which is what an org-scoped key rejection usually is. Ask for a new key only after a
browser login has ALSO failed — otherwise you spend the user's round trip on the wrong object, and the
"your key is dead" verdict you stated with confidence turns out to have been a scope or org story you
told twice.

- `--no-skill-install` avoids the Claude-plugin step, which fails on any host without a coding agent.
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

**A second account on the SAME toolkit requires `--alias`** — the CLI refuses the link without it
("Required when creating an additional account for the same toolkit/auth config"). The alias is also how
you address the right account later, so make it say which one:

```bash
composio link gmail --alias second-google --no-browser --no-wait
```

**The consent screen silently re-authorises whichever account the browser is already signed into.**
Linking a second Google account from a browser session that is logged into the first yields a second
`ACTIVE` connection pointing at the SAME mailbox — and two `ACTIVE` rows cannot tell you that. Tell the
user to open a private window or choose "Use another account" *before* they click, and afterwards prove
the accounts are actually different by executing a read on each connection and comparing the returned
data. Counting `ACTIVE` rows is not a check; it is the appearance of one.

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

**Never derive a tool slug from a name pattern — the tool set is not guessable.** A slug invented to mirror a
REST verb (`GMAIL_MODIFY_MESSAGE`, modelled on the real `GMAIL_ADD_LABEL_TO_EMAIL`) does not exist, and the
failure is charged PER CALL: a 55-message batch spent 55 round trips learning one missing name, all of them
reporting the same "Tool not found". Discover the slug instead —

```bash
composio search "modify labels on gmail messages"   # take the slug it returns
```

— and expect the real verb to be the plural batch form (`GMAIL_BATCH_MODIFY_MESSAGES`, camelCase fields, many
ids per call). **A wrong slug is the cheapest mistake to make and the most expensive to repeat.**

**`composio execute <slug> --help` is NOT the tool's schema.** It prints the CLI's own generic `execute` help
and reads as authoritative while telling you nothing about the tool's parameters. The schema is
`--get-schema`. Measured: `--help` was read twice in one session and both times the answer was about
`--parallel` and `--data`, not about the tool.

**A large result is spilled to a file, not returned inline.** `composio execute` answers with
`{"successful":true,"storedInFile":true,"outputFilePath":"…/TOOL_OUTPUT_….json"}` once the payload is
big — measured: 142 KB for a three-message Gmail fetch. Parse `outputFilePath` and pull the fields you
need. Reporting the execute response itself hands the user a path where they asked for data.

**The spilled file wraps the payload AGAIN — read `["data"]`, not the file root.** The file is itself
`{"successful":true,"data":{"messages":[…]}}`, so `json.load(f)["messages"]` is `None`, which is
indistinguishable from a genuinely empty result. Measured: that mis-read reported "0 inbox messages" for
a mailbox holding 8,857. Unwrap every result the same way — CLI stdout → `outputFilePath` → `["data"]` →
the collection — and treat `successful:false` or a missing key as the ONLY evidence of "no data".
Writing `list(d.get("messages") or [])` against the wrong level silently converts a parse bug into a
finding, which is the most expensive kind of wrong answer.

**A broad query fails with "payload too large" instead of returning a page.** Adding `max_results` makes
it worse. Pass `verbose:false` (measured ~75% smaller) and narrow with a `query` filter; the error text
names this remedy. Only treat the failure as data-missing if the same call fails after that.

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

**Two ACTIVE connections to the same toolkit are not proof of two accounts.** Linking a second Google
account from a browser already signed into the first silently re-authorises the SAME mailbox: both rows
read `ACTIVE`, both have distinct `ca_…` ids, and the only way to tell is to ask each one who it is.

```bash
composio execute GMAIL_GET_PROFILE --account <alias|word_id|ca_id> -d '{}'
```

Compare `emailAddress`, `historyId` and `messagesTotal` — identical values mean one mailbox under two
connections. Do this before reporting a second account as linked; a distinct id proves nothing.

A successful upload response is not proof the file is there, correct or complete. Read it back and compare:

```bash
composio execute GOOGLEDRIVE_GET_FILE_METADATA -d '{"fileId":"<id>","fields":"id,name,size,mimeType,createdTime,webViewLink"}'
```

Check the returned `size` against the local file byte count. **Only then report success.**

**Verify the effect in the user's own units, not the API's.** A batch of accepted writes is a receipt for
the calls, not for the outcome: removing a label from messages that never carried it succeeds and changes
nothing measurable. After any bulk mutation, re-run the query the user would run and report before/after.

**Never silently exceed the scope the user approved.** If the real count comes out materially larger than
the number you got a "go" for, stop and say so with the evidence before running it — a reversal of the
same action at 3× the size is still not the action that was authorised. Cheap, reversible operations do
not exempt you: the approval was for a quantity, and the quantity changed.

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

- **The installer ends on a `💥 Error` that is not a failed install.** Measured 2026-11-19 on a host with no
  coding agent installed: the CLI installs, then the optional plugin step tries to spawn `claude` and prints
  `💥 Error • ENOEXEC,unknown error, posix_spawn 'claude'` followed by `agent plugin setup failed`. The binary
  is fine — verify `composio --version` (0.6.2 at the time) before re-running anything. The suggested retry
  (`composio setup --target auto --yes`) only relates to the plugin step, not to whether you can use the CLI.
- **Confirm a dead key with BOTH surfaces before asking for another.** The REST probe and the CLI disagree in
  ways that matter: `composio login --user-api-key "$KEY"` answers `Invalid or revoked user API key`, while
  REST v3 answers `APIKey_InvalidAPIKey`. Two independent systems agreeing is a credential verdict you can
  state with confidence; one alone is still worth a second probe.
- **Key LENGTH is not a truncation test on this platform.** Measured: every stored key on the host was 23
  chars and cached doc examples ranged 13-21, so a 23-char `ck_…` key is the normal shape. Do not tell the
  user their key was cut off — check the error text, which echoes the key masked (`ck_**-sni`) and therefore
  proves the full value arrived.
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
- **Zero results is not zero data until the toolkit is proven linked.** An unlinked toolkit returns an empty
  set rather than an error, so a clean blank is the one answer that must never be reported without a
  `connections list` check — and a per-toolkit check, never a per-provider one.
- **Rate your own report.** "It uploaded" from the tool's response is a claim; from a metadata read-back it
  is a receipt.

## Related

- `references/gmail-tool-operations.md` — Gmail at volume: payload unwrapping, opaque label ids, batch
  archive semantics, why there is no unsubscribe action, and the bulk-delete safety walls.
- `agent-tool-contracts` — the same boundary discipline for tools that take generated arguments.
- `secret-handling-in-chat` — the paste-redaction protocol used above.
- `host-access-delegation` — when the missing thing is root, not a credential.
