---
name: agent-credential-architecture
description: "Use when deciding where a credential should live."
category: security
version: 1.0.0
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [security, credentials, agents, secret-management, custody, brokers]
    related_skills: [secret-handling-in-chat, key-custody-and-recovery]
---

# Agent Credential Architecture

## When to Use

- A credential needs a home and you must choose the mechanism — password manager vs broker vs threshold custody.
- An agent needs to call an authenticated API and you must decide how it authenticates.
- Someone proposes "let's just use a password manager for everything", or "let's put the wallet key in the vault".
- A secrets/broker tool is under evaluation and you must judge whether it buys the guarantee it claims.
- A pasted secret needs follow-through: rotation, plus the mechanism that stops the same paste recurring.

Where a secret should live is a **per-credential decision**, and it is the decision that gets skipped. Beginners
ask "which password manager?" before asking "is a password manager even the right rail for this thing?" Ask the
rail question first, for each credential individually.

The three-rail model below is the whole skill; the rest is why each boundary sits where it does.

Related: `secret-handling-in-chat` (what to do the moment a raw value arrives in a message),
`key-custody-and-recovery` (surviving a host wipe). This skill decides *which mechanism*.

## Step 1 — sort every credential onto one of three rails

Do this as an inventory, not case by case in the middle of a task. Write the table out; it is short.

| Rail | What belongs on it | Mechanism |
|---|---|---|
| **1. The human's own credentials** | logins, personal accounts, the human's own copy of any key | **A real password manager** (1Password / Bitwarden) or paper. Never a notes app — a notes app is cloud-synced plaintext, so one account compromise is the whole exposure. |
| **2. Agent service credentials** | API keys the agent uses to make requests: LLM providers, Git hosting, market data, search, RPC, media APIs | **A credential broker** — the agent holds a *placeholder*, the broker injects the real value on the outbound request. See `references/agent-vault.md`. |
| **3. Money keys** | wallet private keys, signer material, any key that can move funds | **Threshold custody** (e.g. a 2-of-3 Safe with the agent holding one signer) plus a sharded keystore. Never rails 1 or 2. |

The two mistakes to catch: putting a **wallet key in a password manager** (its cloud sync *is* the "one account
compromise and the wallet is gone" problem), and putting an **agent service key in a password manager** (see the
next rule — the agent needs the value in-process, which a password manager cannot safely provide).

## Hermes ships one mechanism per rail natively — check before you build or buy

The platform already provides a mechanism for each of the two non-money rails, so "which password
manager?" is usually the wrong first question:

| mechanism | rail | what it does | what it does NOT do |
|---|---|---|---|
| `hermes secrets bitwarden\|onepassword` | **2** — agent API keys | pulls keys from the provider **at process startup** instead of reading `.env`; `token` validates a new one before storing, `sync` reports what changed | does not hide values from the process — the agent still holds them |
| `hermes egress` (iron-proxy) | **2** — agent API keys, stronger | TLS-intercepting egress proxy swaps a **placeholder token** for the real credential on the outbound request — the agent's environment never contains the value | only covers traffic that leaves through the proxy; local signing never touches it |
| `hermes auth` | 2 — **provider/inference** keys | pooled credentials, rotation on exhaustion, cooldown/refresh per provider | provider credentials only — not service keys like ElevenLabs or CDP |
| `hermes vault` | **1** — logins | local encrypted store the agent reaches through **handles**; values are injected server-side on the exact origin | **values never enter the conversation, so it cannot serve an API key the agent must send in a header** |

**Enumerate the platform before building or buying anything.** `hermes --help | grep -iE 'secret|auth|egress|vault'` answers in one line what a custom
credential store would take a day to rebuild. Measured: a fleet ran plaintext `.env` copies for months while three
native mechanisms sat unused, and the user had to ask "does Hermes already have this?" before anyone looked. **The
answer to "let's build a secret keeper" starts with the platform's own inventory, not with a design.**

**`hermes vault` is the wrong tool for an agent API key, and structurally so** — the same shape as the
broker/wallet-key mismatch below: its entire design is that the value never reaches the agent, and a key
the agent must attach to a request is precisely a value the agent needs. Use `hermes secrets` (or a
broker) for rail 2.

**Prefer sharing by SOURCE over sharing by COPY.** Hand-copying one key into N seats' files makes N
versions of the truth: rotate once and the stale copies keep working until one is revoked, with no error
to reveal which seat is behind. A startup pull from a single source has one value by construction. **If
you find several byte-identical copies already, that is the symptom, not a working convention** — say so
rather than treating the copy pattern as the established practice.

**And a shared set must carry per-entry VALIDITY — sharing propagates a DEAD credential exactly as fast
as a live one.** One source of truth is only an improvement if the value is real; a single dead value
distributed to N seats is *N broken seats*, and worse than the copy pattern it replaced, because now the
outage lands everywhere at once and every seat has grounds to believe it is installed. **A shared
credential set with no validity column multiplies failure instead of capability.** So: probe on population,
record the result beside each entry, and give the read path a check mode that exits non-zero while
anything is broken. Write the mechanism so the *second* reader can see the state without re-probing — the
manifest is the record.

**The generalised trap: an aggregate that consolidates values consolidates outages.** Any move toward a
single source (one file, one broker, one env) needs a *health* signal on that source for the same reason it
needs a backup — consolidation removes the accident that saved you when one copy was broken and another
was not.

**For a seat on a DIFFERENT machine, a shared directory is not available, and the sync tree is not a
transport.** A vault/brain that syncs through a third party cannot be un-sent: deleting the note removes
your copy, not theirs, and provider-side version history may retain it. Two rules follow. First, **if a
credential must reach an off-host seat and no provider-side manager is in place, hand it over and then
ROTATE it** — that is the only form in which "once they have it" becomes true, because what lingers is
dead. Second, **prefer the provider's own manager** (rail 1 or `hermes secrets`) over any file-sync path;
the sync tree's guarantee is delivery, never recall.

## Why a broker can never hold wallet keys — the load-bearing reason

**A broker's entire mechanism is: inject the secret into an outbound HTTP request.**

A wallet private key **never goes outbound** — it signs locally. There is no request to inject it into, so the
abstraction simply does not apply. This is **structural, not a market gap**: if someone asks "why has nobody built
a DeFi version of this?", the answer is that the shape of the problem forbids it, not that the tooling is missing.

Corollary: **never put a proxy in a signing path.** It adds a new place to steal the key while bounding nothing,
because the key is used locally either way. When the request is "agents should handle passwords", the answer is a
broker for rail 2 and threshold custody for rail 3 — not one mechanism stretched over both.

State the limitation rather than implying a broker covers everything. A user who believes the broker is total
will not build the threshold custody they actually need.

## Rules

- **Broker the credentials, threshold the keys.** Two rails, two mechanisms, no overlap.
- **The agent must never be able to read the value.** If the brokered agent's environment contains the real
  secret, the deployment is broken no matter what else is configured.
- **A broker on the same host as the agent is a tidy-up, not a security boundary.** Same-host buys rotation,
  per-agent revocation, request logging and egress allowlisting — all real — and buys *nothing* against an agent
  that compromises the shared host. Say which one you deployed.
- **The broker's master password is a new single point of failure.** If it lives in one place on one host, the
  wipe has been rebuilt with a nicer name. Give it its own restore story (shard it) *before* it holds anything real.
- **Introduce rail-2 credentials one class at a time**, starting with a read-only key that has no write scope and
  no funds attached.
- **Never broker a token your own control plane depends on** (e.g. a messaging gateway token). It *is* HTTP, but
  brokering it makes every inbound and outbound message depend on the broker being up — an availability risk
  traded for a security gain that the same-host caveat may have already voided.
- **A per-seat key file is not isolation when the seats share a host and uid.** Several agent seats on one box
  can read each other's `profiles/<seat>/secrets/`; a file-per-seat layout gives the *appearance* of separation
  while every seat can read every other's value. Real separation needs a **provider-side** boundary — one key,
  account, or quota per seat — not a directory. Until that exists, **declare the provenance** of any credential
  that is not the seat's own (name the cross-seat path and call it the last resort) so a later reader can see the
  true blast radius, and log per-seat key distribution as an **open ownership item** rather than a solved one. A
  silent shared fallback is the failure: it makes one seat's usage, after the fact, indistinguishable from the
  others'.

## Installing a credential into a container you cannot recreate

A running container's environment is **immutable**. `docker run --env` / `--env-file` are creation-time flags, so adding a variable to a hand-started container (no compose file, no unit) means **recreating it** — which drops every dependent service for as long as the recreate takes. When that container is itself fronting live products, "just add the env var" is not an option you can take at 5pm.

**The pattern: read the credential from a FILE at startup, with env vars taking precedence.**

```python
def _credentials():
    k = os.getenv("X_API_KEY", "")
    if k:
        return k                    # an operator who set the var meant it
    for path in ("/opt/data/.x.env",                # the container's own volume — preferred   <!-- ⚠️ NOT PRESENT (checked 2026-11-17): this file does not exist on this seat. Do not assume it; verify before relying on it. -->
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), ".x.env")):
        if not os.path.exists(path):
            continue
        vals = dict(line.split("=", 1) for line in open(path)
                    if "=" in line and not line.strip().startswith("#"))
        print(f"credentials loaded from {path}")   # the only proof the file was read
        return vals.get("X_API_KEY", "").strip()
    return ""
```

Installing it then costs **a file plus a restart**, no rebuild. Four rules that keep it honest:

- **Put the file on a mounted volume, not in a notes/sync tree.** A secret inside anything that syncs to third-party storage is a secret you cannot un-send. Use the container's own data volume; treat the app directory as a fallback and say out loud that it depends on hidden files not being synced.
- **Search order in code = your stated priority.** Env wins over file, and say so in the docstring, or two operators will each believe the other's value is live.
- **Deliver it without argv or shell history:** `docker exec -i <c> sh -c 'umask 077; cat > /path/.x.env'`, paste the lines on stdin, Ctrl-D. A value in an `export` line is in `ps` and in `.bash_history` forever.
- **Verify by a log line that names the path.** "Started fine" is not "read the credential" — the service will start happily with none. Print `credentials loaded from <path>` and grep the logs for it; absence means the file is in the wrong place or unreadable.
- **Shape-check the value before accepting a file.** A loader that trusts any readable file will use a placeholder and
  surface a *format* error that reads like a bad credential. Decode and reject what cannot be real, then fall through
  to the next path:
  ```python
  if len(base64.b64decode(sec + "=" * (-len(sec) % 4))) != 64:   # not an ed25519 secret
      print(f"WARN: {path} skipped — not a credential"); continue
  ```
- **A key can be valid and still be read by nothing.** After installing, grep the codebase for a *consumer* of the
  variable. A credential wired to no reader is a file, not a capability — and it will be reported as "configured" by
  every inventory while opening no door.

**And never take the dev bypass to make the error go away.** A verifier that refuses with *"simulation disabled: <SECRET> not configured"* is refusing correctly. Setting that secret enables an HMAC path that accepts proofs **without any settlement** — the service then reports payments that never moved a coin. A missing production credential must be fixed with a production credential; the bypass is not a smaller version of the same thing, it is the opposite of it.

## The falsifiable test — run this before trusting any broker

Ask the brokered agent to **print its environment**. Expect the **placeholder** (e.g. `__provider_api_key__`).

**If a real value comes back, the deployment is wrong and nothing else about it matters.** This is the one
non-negotiable acceptance test, and it is cheap enough to run on every config change.

Two supporting checks: the outbound call must still *succeed* through the proxy (substitution works, not just
blocking), and the request log must show the call (provenance, so a later "did it go through?" has an answer).

## Verifying a third-party broker before you run it

A broker sits in the credential path, so it is the highest-trust binary in the stack. Do not run one on the
strength of its README:

1. **Verify the artifact** — match the release checksum against the published checksums file, or use the build
   provenance attestation (`gh attestation verify <archive> --repo <owner>/<repo>`). Do this before executing.
2. **Check the licence boundary** — many projects keep premium code in a separate directory under a different
   licence, so "open source" may not describe the feature you want.
3. **Check the release maturity** — a project that calls itself preview will change its API under you.
4. **Run it on a throwaway dir with a throwaway master password**, confirm it serves and its CLI talks to it,
   then **stop it**. Proving it starts is not proving it brokers — record which of the two you established.

## Pitfalls

- Do NOT recommend a password manager for a credential an agent must use programmatically — the agent needs the
  value in-process, which is the exact thing the manager exists to prevent.
- Do NOT let "nobody has built a solution for X" pass as a market gap without checking whether the shape of X
  forbids it. Wallet keys are the canonical case.
- Do NOT claim a broker removes exfiltration risk when it shares a host with the agent.
- Do NOT skip the env-print test because the server started and the CLI connected. Those prove installation, not
  brokering.
- Do NOT collapse rails 2 and 3 into one tool for simplicity. They fail in different ways and are recovered
  differently.
- **A secrets file holding a REDACTED value is worse than no file** — it makes the credential look
  installed, so no seat reports the gap. Symptom: a real-looking prefix and suffix with the middle masked,
  at a length too short for that provider. Confirm against what the API says — a 401 that echoes a *tail*
  absent from your file proves the file is not what was sent. **Flag it loudly on sight: every reader of
  that file has been trusting a decoration.**
- **A provider's key CLASSES are not interchangeable, and the wrong class fails exactly like a dead key.**
  Check the prefix against the API surface you are calling before declaring a credential invalid — one
  provider issues separate keys for its agent-facing and consumer-facing APIs, and the consumer key
  returns 401 from the agent API.
- **Search every seat's `secrets/` and every `.env` before reporting a credential absent.** Seats on one
  host can read each other's secret dirs (rule above), so "not in my profile and not in the fleet `.env`"
  is not "not on this host" — the value may be sitting in another seat's directory, and reporting it
  missing sends the user to re-issue one they already supplied.
- **Probe CAPABILITY on a real endpoint, never a `/verify` or introspection route.** A token can return
  `401 Invalid` from the provider's own verify endpoint while serving real calls successfully, which makes
  a working credential look dead — and the probe then sends you to re-issue something that was fine. Call
  an endpoint that does the actual work (list the account's resources); treat the verify route as a
  diagnostic hint at most. **The mirror rule also holds:** a `200` from a verify route is not proof the
  *right* credential is installed, so confirm which account/class answered, not just that something did.
- **A guard that exits non-zero by CRASHING reads exactly like a guard that failed cleanly.** When adding
  a check mode that signals with an exit code, read its *output* once before trusting the code: an
  unhandled exception and a real verdict both exit non-zero, and a traceback in the log is the only tell.
  Prove it both ways — a known-broken state must exit non-zero *with a message*, and a known-good state
  must exit zero. A one-sided proof lets a crash pass as a pass.
- **A dead credential can be documented and still be in use.** Recorded deaths carry a removal instruction
  that nobody executes; the value then survives and — once a shared set exists — gets re-propagated to
  every seat. **When a source-of-truth doc says a credential should be removed, remove it in the same pass,
  with a backup**; a documented-but-present secret is worse than an undocumented one, because the record
  makes the next reader believe it is handled.
- **A vendor-managed OAuth key is a single point of failure for the whole capability, and only the vendor
  can restore it.** When an integration brokers a third party's OAuth on your behalf, the grant lives with
  the vendor: a rotated or revoked key takes every dependent function with it, the fix requires an account
  action you may not be able to perform, and nothing on your side can recover it. Measured: an entire
  file-transfer capability died this way and the only remedy was "the owner mints a new key in their
  dashboard." **When the choice exists, prefer a credential the owner controls end-to-end** — a first-party
  OAuth client with its own stored token — over a vendor's managed set, and say which one you deployed.
  The failure mode also has a tell worth recognising early: the wiring notes still say "live", the key
  file is present and well-formed, and the only evidence of death is a uniform rejection from the API.

## References

- `references/shared-source-on-one-host.md` — the same-host single-source layout: shared root + per-seat
  symlinks, manifest with a validity column, the `resolve` helper contract, and the rotation step.
- `references/agent-vault.md` — Agent Vault (Infisical) concretes: ports, placeholder substitution, object model,
  agent-mode environment variables, and the staged adoption plan.
