---
name: fleet-provider-key-rotation
description: "Use when rotating a provider key across the fleet."
category: security
version: 1.0.0
author: Gentech
license: MIT
tags: [credentials, rotation, providers, fleet, cutover, secrets]
metadata:
  hermes:
    tags: [credentials, rotation, providers, fleet, cutover, secrets]
    related_skills: [secret-handling-in-chat, agent-credential-architecture, key-custody-and-recovery, model-configuration-management]
---

# Fleet Provider Key Rotation

Replacing an inference-provider credential across a multi-profile Hermes install. The hard part is
not the write — it is **not declaring victory from a probe that never exercised the credential**,
and then pointing every seat at a rail that is actually dead.

## When This Applies

- A provider API key leaked, was revoked, or was rotated upstream.
- The user hands over a replacement key and asks to move the fleet.
- Switching the fleet onto a provider, or back onto one it previously used.

## Procedure — in this order

### 1. Inventory every place the credential lives

Before writing anything, find all copies. There are three distinct kinds, and they are not the same:

- **`.env` files** — one at the install root plus one per profile. These are the credential.
- **`auth.json` credential pool** — entries are usually `source: env:VAR`, i.e. a **pointer** to the
  `.env`, not a stored copy. A pointer means there is nothing to scrub in the store; the `.env` IS
  the value. Confirm the `source` field before planning a scrub step.
- **Backups and dotfile copies** — `.env.bak-*`, `.env.*managed*`, exported snapshots. The export
  guard drops credential files by **exact filename** and scrubs known text suffixes; a renamed
  backup (`.env.bak-managed`) matches neither and **ships unscrubbed**. Grep for the variable name
  across backup dirs, not just for `.env`.

### 1b · When the credential is MISSING rather than being rotated

Same inventory, opposite conclusion. When a key the documentation says is configured cannot be found, the question is not "where do I write it" but "did it ever exist, and what happened to it".

- **Docs outlive secrets.** A reference file stating *"`CDP_API_KEY_ID` and `CDP_API_KEY_SECRET` are both present in `.env`"* stays true-looking forever. Treat every such sentence as a **claim about a past date** and re-verify it against the filesystem before repeating it to the user. Measured: a key documented as present, with the service settling through it, was absent from every `.env` on disk *including four rotated backups* — and the stale sentence is why one party said "it's missing" while the other correctly remembered providing it. Both were right about different months.
- **Search in this order and report the list:** live `.env` per profile → rotated `.env.bak-*` copies → the session/message store (`state.db`, full text) → key-shaped regex (`organizations/<uuid>/apiKeys/<uuid>`, base64 secret lengths) → shell history and logs → `/root`, `/etc`, systemd units → repo and vault notes → dependency trees and vendor template files.
- **A variable NAME is not a key.** Vendor example files ship `CDP_API_KEY_ID=` with an empty value, and docs mention the name hundreds of times. A hit only counts if it carries a value of the right *shape*; an empty assignment is a template.
- **Do not resurrect a stale value.** A format-valid key can still be revoked — this skill's own probe exists because a `401` reads like a code bug. If the credential has to come from the vendor portal anyway, **rotate rather than restore**.
- **Record the absence the moment you find it.** One line in the credential log: what is missing, what it blocks, what releases it. Zeros in a `.env` plus silence in the notes is exactly how the same search gets paid for twice.
- **Say which verdict you can prove.** "It is absent now, after searching X, Y, Z" is provable. "It never existed" is not — name the possibility you cannot exclude (a deleted chat, an upstream revocation) instead of asserting one.

### 2. Write the new key to every `.env`

Update in place if the variable exists; append if it does not. Verify by **count and masked tail**
per file — never print a value:

```bash
for f in .env profiles/*/.env; do
  grep -c '^PROVIDER_API_KEY=' "$f" 2>/dev/null | sed "s|^|$f: |"
done
```

### 3. Live-test the new key BEFORE pointing the fleet at it

This is the step that matters. A key that fails here must never reach a seat.

```bash
python3 - <<'PY'
import json, urllib.request, urllib.error
k = open('/path/to/new.key').read().strip()
body = json.dumps({"model": "<a-model-from-the-catalog>",
                   "messages": [{"role": "user", "content": "say ok"}],
                   "max_tokens": 8}).encode()
req = urllib.request.Request("<base_url>/chat/completions", data=body, headers={
    "Authorization": f"Bearer {k}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
})
try:
    r = urllib.request.urlopen(req, timeout=25); print("HTTP", r.status)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:200].decode('utf-8', 'ignore'))
PY
```

`scripts/probe-provider-key.py` does this with the false-negative guards built in — prefer it over
hand-writing the probe.

### 4. Verify each profile's provider config

Each profile's `config.yaml` carries its own `model:` block. Confirm `provider` and `base_url` per
profile — do not assume a change at the root cascaded.

### 5. Wire the fallback chain in YAML, not via the CLI

`hermes fallback add` is an **interactive picker** — it cannot be driven from a script or a
non-interactive session. Write the block directly into each `config.yaml`:

```yaml
fallback_providers:
  - provider: <backup-provider>
    model: <backup-model>
    base_url: <backup-base-url>
```

A fallback that is byte-identical to the primary is a retry, not a fallback — verify it differs in
provider, model, or base_url. After writing, confirm with `hermes fallback list`.

### 6. Redact the transcript copies you created

If the key ever appeared inline in a shell command or heredoc during this work, those copies landed
in `state.db`. Scan and redact:

```bash
python3 profiles/<seat>/scripts/redact-secret.py --file /path/to/new.key --yes
```

Then re-scan every profile's `state.db` for the literal and report the residual count. **Zero is the
only acceptable answer.**

### 7. Verify per-seat with a live one-shot

```bash
for p in seat1 seat2; do
  timeout 75 hermes -p "$p" -z "Reply with exactly: SEAT_OK" \
    --provider <provider> -m <model> 2>&1 | tail -2
done
```

A seat that answers proves the credential, the config, and the plugin wiring together.

### 8. Sweep the old key from backups

A revoked key in a backup is a dead key waiting to be found. Replace it with a placeholder in every
backup and dotfile copy, then confirm no copy remains.

## Pitfalls

- **A `403` with `error code: 1010` from a Cloudflare-fronted provider is a bot-signature block,
  not an auth rejection.** It fires on the default `urllib`/`curl` User-Agent while the key is
  still valid. Re-probe with a real browser User-Agent: if the same key returns `200` with a UA and
  `403/1010` without one, **the key is LIVE** — the "dead key" verdict was an artifact of your
  probe. Never report a provider credential as revoked on a 1010.
- **A `200` from `GET /models` is not an auth test.** Model lists are commonly served
  **unauthenticated** — a full catalog can come back with no key at all. Only a `POST` to the chat
  endpoint exercises the credential. Use the chat call as the acceptance test.
- **A provider may require a per-request session header.** Some gateways route on a session id and
  return `400 MissingSessionID` for a bare `POST` — which reads like a malformed request but is a
  routing requirement, and the key is fine. Send a unique session header in raw probes; the Hermes
  provider plugin injects its own automatically, so a key that "fails" a bare curl can still be
  perfectly good in the fleet. Treat a 400 naming a required header as **inconclusive**, not as a
  dead credential.
- **A shorter key-shaped literal found by a log/DB scan may just be a truncated copy of the key you
  already know.** Loggers truncate long tokens. Before declaring a *second* credential, hash
  successive prefixes of the known key and compare against the literal's hash — a match means it is
  one credential, not two.
- **Do not scrub a value out of the credential store when the pool entry is an env pointer.**
  `source: env:VAR` means the store holds no secret; the scrub belongs in the `.env` and its backups.
- **Do not assume the fallback survived the cutover.** Fallback entries are separate from the primary
  block and are easy to leave pointing at the provider you just moved off.

## Related

- `direct-model-api-calls` — the Cloudflare 1010 fix and direct-call patterns.
- `secret-handling-in-chat` — what to do the moment a raw key arrives in a message.
- `agent-credential-architecture` — *where* a credential should live (the rail model).
- `model-configuration-management` — provider/model/fallback configuration.
