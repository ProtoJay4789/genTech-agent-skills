---
name: drive-file-transfer
description: Use when an agent must push files from the VPS/workstation to Google Drive, or pull them back. Covers the Composio path (agent file transfer), the rclone path (bulk), and the one hard rule — the vault never goes to Drive.
---

# Drive file transfer (agent → Google Drive)

**The rule that outranks everything here — and it is narrower than "never":**

> **The NOTES never move to Drive. The MEDIA does.**

`${VAULT_DIR}` holds credentials, tokens and handoffs; it is the brain, and its text belongs in the notes
lane (Obsidian, mirrored to a private git repo). **Copies of credentials on a third party's servers are ones
we can never fully recall.**

But a notes vault is not a photo library, and a storage cap counts bytes. **The standing policy: pictures,
music and video live in a Drive project folder, not in the vault.** Drive is the *media brain*; Obsidian is
the *notes brain*; git is the *code brain*. A note about a song belongs in Obsidian — the song belongs here.

| content | home |
|---|---|
| notes, handoffs, decisions, config | vault → notes lane |
| code, scripts, source trees | git repo |
| images, audio, video, PDFs, big data dumps | **Drive project folder** |
| credentials, tokens, seeds | **nowhere third-party. Ever.** |

So "never send the vault to Drive" means **never mirror the whole tree, and never ship a secret** — it does
**not** mean media has to stay in the vault. A blanket refusal here now contradicts the house policy and
would block a migration the operator asked for.

### ⚠️ Moving media OUT of the vault: the ORDER is the safety property

Where the vault syncs bidirectionally (Obsidian Sync), **a file that leaves the vault is deleted from the
server and from every device the human owns.** A routine that relocates first and uploads second destroys
the only other copies while calling itself a backup. The order is not negotiable:

```
1 · upload to Drive            (copy only — deletes nothing anywhere)
2 · VERIFY every file          (size + count; `rclone check <stage> <dest>`)
3 · only then may anything be pruned — and NOT automatically
```

- **Never prune in the same step as the upload.** Deletion propagates to devices the agent cannot see, so it
  stays a human decision even when the copy verified cleanly. Print the exact paths and stop.
- **A staging directory on the same host is not a backup.** Until the Drive copy verifies, "moved out of the
  vault" means "deleted from every device, still on one disk" — and if sync is alive it is *already* deleting.
- **Audit references before moving any media.** Grep each basename across `*.html`, `*.md`, `*.json`: measured
  on one vault, **44 of 64 media files were referenced** by pages (avatars, emblems, deliverable stills) and
  only 20 were unreferenced. Move the unreferenced set by default; referenced media moves as a **pair** — file
  to Drive *and* the page's link updated. A sweep that takes both silently fixes the quota by breaking the site.
- **Record every staged file with explicit states** — *in vault / staged / verified in Drive* — in a list you
  REWRITE each run rather than append. A staging directory with no record becomes an undocumented second
  dumping ground within a week, and a queue nobody counts reads as handled.
- **Name the transport gate before promising the move.** No credential means the honest report is "the
  pipeline is built and refuses to move anything" plus the one-time authorisation step — never a half-move.
  An `rclone` remote with an empty `token =` fails with `empty token found - please run rclone config reconnect`;
  a remote configured but never authorised has *never* worked, whatever the config file suggests.

## ⚠️ Preflight — prove the lane is alive BEFORE planning around it

**A documented path is not a working path.** This skill previously said "verified live" about a
Composio connection that was later revoked, and a session that trusted the note lost the better part
of an hour to a dead key. **Run this before anything else here:**

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  "https://backend.composio.dev/api/v3/connected_accounts" -H "x-api-key: $COMPOSIO_API_KEY"
```

**Read the number, then read the error body — the code alone will mislead you:**

| result | meaning |
|---|---|
| `200` with a `googledrive` account in the list | the lane is up — proceed |
| `410` | the endpoint version is retired; move to the version the docs name now |
| `401` `…InvalidAPIKey` **on every endpoint tried** | the key itself is dead or revoked — no header or path will fix it |
| `401` accepted on one endpoint, forbidden on another | the key is valid but **under-scoped** — fix permissions, not the key |
| `5xx` / `DEPLOYMENT_PAUSED` | the vendor is down — not our credential, and not something a rotation fixes |

**Send a control alongside the real key:** one obviously fake value and one empty header. If the real
key and the fake key return the *same* error, the server is matching values and the key is dead. If
empty returns a *different* error (`NoAuthProvided`), the header name is right and the rejection is
about the value.

**If the vendor ships a CLI, it outranks your curl.** `composio login --user-api-key <key>` answers
"is this key good" in one call, in the vendor's own words. Reach for it early instead of reconstructing
auth from HTTP codes.

## Path A — Composio (agent file transfer)

**Composio-managed OAuth — no Google Cloud project needed. Only use this once the preflight above
returns 200 and shows a live `googledrive` account.**

**Credential:** `COMPOSIO_API_KEY` in `${PROFILE_DIR}/.env` (never inline in config — config
gets committed, `.env` doesn't). Store the canonical copy at `${SHARED_SECRETS}/composio_api_key`
(mode 600) and reference it; a key pasted through chat should be installed there, not re-pasted.

**Connection:** `user_id=gentech`, connected account `ca_e3m5YNqM4MRB` (googledrive). Check it any time:

**⚠️ That id is a record of what once existed, not proof it is live** — see *Open items* below, where
this credential is dead. Re-run the preflight before relying on Path A; a connected-account id in a
skill file is exactly the kind of stale evidence this skill's own preflight section exists to catch.

```bash
curl -sS "https://backend.composio.dev/api/v3/connected_accounts" -H "x-api-key: $COMPOSIO_API_KEY"
```

**Run a tool** — `user_id` is REQUIRED alongside `connected_account_id`, or you get
`ActionExecute_ConnectedAccountEntityIdRequired`:

```bash
curl -sS -X POST \
  "https://backend.composio.dev/api/v3/tools/execute/GOOGLEDRIVE_CREATE_FOLDER" \
  -H "x-api-key: $COMPOSIO_API_KEY" -H "Content-Type: application/json" \
  -d '{"connected_account_id":"ca_e3m5YNqM4MRB","user_id":"gentech",
       "arguments":{"folder_name":"Folder Name"}}'
```

**Tool slugs that matter:** `GOOGLEDRIVE_CREATE_FOLDER` (takes `folder_name`, **not** `name`),
`GOOGLEDRIVE_CREATE_FILE_FROM_TEXT`, `GOOGLEDRIVE_UPLOAD_FILE`, `GOOGLEDRIVE_LIST_FILES`,
`GOOGLEDRIVE_GOOGLE_DRIVE_DELETE_FOLDER_OR_FILE_ACTION` (there is **no** `DELETE_FILE` slug).
**Delete arg is `fileId`** (verified 2026-09-14) — `GOOGLEDRIVE_GOOGLE_DRIVE_DELETE_FOLDER_OR_FILE_ACTION`
takes `{"fileId": "<id>"}`; both `id`/`item_id` and the bare `DELETE_FILE`/`GOOGLEDRIVE_DELETE` slugs
404 or "missing field". Move/rename slug is `GOOGLEDRIVE_MOVE_FILE` (takes `fileId`).

### 📎 BINARY files (PDF, PNG, MP4) — three steps, proven 2026-09-14

`CREATE_FILE_FROM_TEXT` is **text only**. Binaries need the staging flow:

```python
from composio import Composio
import hashlib, httpx
c = Composio(api_key=COMPOSIO_API_KEY)
data = open(path, "rb").read()
md5  = hashlib.md5(data).hexdigest()

# 1. presign — returns .key (the s3key) and .new_presigned_url
resp = c.client.files.create_presigned_url(
    filename="x.pdf", md5=md5, mimetype="application/pdf",
    tool_slug="GOOGLEDRIVE_UPLOAD_FILE", toolkit_slug="googledrive")

# 2. push the bytes
httpx.put(resp.new_presigned_url, content=data,
          headers={"Content-Type": "application/pdf"}, timeout=120)

# 3. attach it
c.tools.execute(slug="GOOGLEDRIVE_UPLOAD_FILE",
    arguments={"file_to_upload": {"name": "x.pdf", "mimetype": "application/pdf",
                                  "s3key": resp.key},
               "folder_to_upload_to": FOLDER_ID},
    connected_account_id=ACCT, user_id="gentech",
    dangerously_skip_version_check=True)
```

**⚠️ `files` lives on the INNER client: `c.client.files`, not `c.files`.** Checking `dir(c)`
and concluding "no file API" is **wrong** — that mistake was made once already. Look inside
`c.client`.

### 🔍 THE STEP THAT WAS MISSING — check the source before concluding "it doesn't exist"

**Jordan, 2026-09-14:** *"this only happened because I gave you the information for Composio,
but you didn't think — let me check out their GitHub first, let me look at their docs first
before I do this, to make sure to verify everything is in order."*

**Rule: "I looked and didn't find it" is NOT "it doesn't exist."**

Before reporting any capability as missing, do these **in order** — cheap, and each one is
seconds:

1. **The vendor's docs** — search them directly, don't skim:
   `https://docs.composio.dev/api/knowledge-search?q=<your question>`
2. **The vendor's GitHub** — search the code, not just the README:
   `gh api "search/code?q=repo:ComposioHQ/composio+<term>" --jq .total_count`
3. **One level deeper in the client** — `dir(c)` is not the whole object. Check `c.client`,
   sub-resources, and `inspect.signature` on anything promising.
4. **Then** conclude. A negative finding is a claim like any other and carries the same
   burden of proof.

**Why it matters here specifically:** this cost an hour and nearly produced a bug report
against a healthy 30k-star project. **A false negative reported outward is worse than a
missing feature — it spends someone else's time on our oversight.**


**Pitfall — argument names are not guessable.** `CREATE_FOLDER` takes `folder_name`, **not**
`name`. **Read the error and use what it names** — don't retry the same guess.

**Always read back.** A `successful: true` is the API's claim; `GOOGLEDRIVE_LIST_FILES` is the
proof. Verify with a listing before reporting success.

### ✅ The route that actually lands — CLI browser login, then execute a tool directly

Proven end-to-end: install → browser login → link `googledrive` → upload a binary → **verify by read-back**.

```bash
curl -fsSL https://composio.dev/install | sh     # inspect the script before running it
umask 077; echo "$KEY" > "${SHARED_SECRETS}/composio_api_key"   # only if using the key route
export PATH="$HOME/.composio:$PATH"
composio login --no-wait --yes      # prints https://dashboard.composio.dev/?cliKey=...
#   human opens it and authenticates, then:
composio login --poll
composio whoami                     # proves identity + org before anything else
composio link googledrive --no-browser --no-wait   # prints connect.composio.dev/link/...
composio connections list           # INITIALIZING -> ACTIVE
composio execute GOOGLEDRIVE_UPLOAD_FILE -d '{"file_to_upload":"/abs/path/file.pdf"}'
composio execute GOOGLEDRIVE_GET_FILE_METADATA -d '{"fileId":"<id>","fields":"id,name,size,mimeType,modifiedTime"}'
```

**⚠️ The login and link URLs expire in MINUTES, and a chat round-trip spends most of the window.** Paste the
URL and have the human click immediately; a link that waits for a reply silently expires, and you then
diagnose a "broken login" that is only a slow loop. If it expires twice, stop racing the clock — mint a
durable key, or treat the browser flow as a same-minute operation.

**⚠️ `--file` alone fails validation** (`Invalid JSON input`); pass arguments as JSON with `-d`.

**⚠️ Argument keys are camelCase, and the rejection names the correct one** — `fileId`, not `file_id`.
Read the error: it lists the allowed top-level keys. Do not retry the same guess.

**⚠️ Replacing a file's content: `GOOGLEDRIVE_UPLOAD_UPDATE_FILE` with the same `fileId`.** Re-uploading
under a new name leaves a stale duplicate — and the stale copy is the one already being shared.

**⚠️ Verify by read-back, always.** `successful: true` is the API's claim; a `size` from
`GET_FILE_METADATA` that equals the local byte count is the receipt. Report the link only after it matches.

**Host without `unzip` and without root:** the installer calls `unzip -oqd DIR FILE`. A ~15-line shell shim
that shells out to `python3 -c 'zipfile.ZipFile(a).extractall(d)'` satisfies it. The CLI is worth the shim —
it is the only path that reports authentication in the vendor's own words.

## Path C — our own Google OAuth (no third party in the middle)

**Preferred when it is available, because the failure mode that killed Path A cannot recur:** nobody
can revoke a credential they do not hold.

The bundled `productivity/google-workspace` skill ships everything but the client:
`google_api.py` (Drive/Gmail/Sheets client) and a **fully non-interactive `setup.py`** written to be
driven by an agent through terminal commands.

```bash
cd <skills>/productivity/google-workspace/scripts
python3 setup.py --check                        # exit 0 = authenticated, 1 = not
python3 setup.py --client-secret /path/to.json  # store the OAuth client (user supplies)
python3 setup.py --auth-url                     # print the URL for the user to open
python3 setup.py --auth-code <CODE>             # exchange the pasted code
python3 setup.py --check                        # verify
```

**What the user must do once, in a browser:** create a Google Cloud project → enable the Drive API →
OAuth consent screen (External, add themselves as a test user) → Credentials → **OAuth client ID →
Desktop app** → download the JSON.

**⚠️ A `client_secret.json` is a client credential, not a grant** — it cannot read anyone's Drive on
its own, and it still belongs in a mode-600 file rather than a chat message. The resulting
**refresh token** is the sensitive half: it never travels through chat at all.

**Status: the auth check runs and reports `NOT_AUTHENTICATED` on this box (no token yet).** The flow
above is the skill's own documented sequence; exercise it end-to-end once the client secret exists and
record the result here rather than assuming it.

## Path B — rclone (bulk moves, e.g. multi-GB)

Composio is for **files**; rclone is for **bulk**. Vanito's 4.4 GB handoff is a Path B job.
The media migration is a Path B job too — a vault's worth of images and clips is bulk by definition.
Secrets still never travel this way.

## Established folders

| Folder | ID | Use |
|---|---|---|
| GenTech - Vanito Handoff | `1VMA6WRGqSwrbUZkh5x1ur5ujU32pO6Dz` | Vanito's frozen work before he switches out (Oct) |

## Open items — current status

- **The API-KEY route is dead; the BROWSER route is alive.** A user API key (`ck_…`) returned
  `401 InvalidAPIKey` uniformly across endpoints and was rejected by name, unchanged, on a second paste —
  re-installing the same value cannot fix a revoked key. **`composio login --no-wait` → human clicks →
  `--poll` authenticated cleanly, `googledrive` linked `ACTIVE`, and a real upload was verified after.**
  **Never report "Composio is down" from a failed key alone** — try the browser flow before concluding.
- **Do not use the `--agent` login when a human is present.** It signs in with a throwaway agent account and
  attaches the files to an identity that is not theirs; the tool's own docs say not to.
- **A 401 is not a 404.** A bogus key returning `401` on a toolkit-listing endpoint proves the endpoint
  exists and only the credential is wrong — do not conclude the capability is unsupported.
- **Path C remains the durable fix** — our own OAuth client, no vendor in the middle, and nobody can revoke
  a credential they do not hold.
- Stale **Gmail** connections accumulate as `EXPIRED` entries beside the live one. They hold no access and
  removal is interactive-only, so leave them rather than fighting a prompt loop — but confirm the toolkit you
  actually need is `ACTIVE`, not merely present in the list.
