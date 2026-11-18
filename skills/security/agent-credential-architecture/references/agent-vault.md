# Agent Vault (Infisical) — rail-2 concretes

Depth for the credential-broker rail. Verify these against the binary you actually download before relying on
them; the project describes itself as preview and its API is subject to change.

## What it is

An open-source HTTP credential proxy and vault. One binary that is **both server and CLI client**. Its own
stated purpose is eliminating **credential exfiltration** — the class where an agent is talked into leaking a
secret it holds, via prompt injection or otherwise.

Distinguish it from a password manager: a password manager answers *"where is the secret stored?"*; a broker
answers *"can the agent steal it at all?"*

## Architecture

| Port | Role |
|---|---|
| management port (default `14321`) | HTTP API + web UI, operator-facing |
| MITM port (default `14322`) | **the transparent proxy where credentials are injected** |

The agent is launched with the proxy environment (`HTTPS_PROXY` / `HTTP_PROXY` / `NO_PROXY`,
`NODE_USE_ENV_PROXY`) plus root-CA trust variables (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`,
`GIT_SSL_CAINFO`, `NODE_EXTRA_CA_CERTS`, `DENO_CERT`). That CA + proxy-env combination is what makes it
**interface-agnostic** — MCP, CLI, SDK and plain `curl` work unmodified, with no SDK integration.

Requests matching no configured service forward as plain proxy traffic by default; a vault can be flipped to a
strict deny policy so unmatched hosts are rejected outright rather than passed through. Default is permissive —
deny is an explicit choice, and it is the one that turns egress into a real boundary.

## Object model

```
vault -> credentials   (real values; a placeholder name maps to each)
      -> services      (rules: which host/endpoint is given which credential, and how)
      -> agents        (tokens; individually rotatable and revocable)
```

`run -- <command>` mints a **vault-scoped, time-bounded session** and executes the child. It names several
agent CLIs as first-class targets, `hermes` among them, so integration is not bespoke work.

**Two modes, and they differ in a way that matters to cron:**

- **Admin mode** — uses the on-disk session from an interactive login, mints a fresh session token for the
  child. A TTL flag is honoured here.
- **Agent mode** — unattended/containerized. Pre-supply the token, broker address and target vault as
  environment variables. The token is validated against the broker once before the child is executed. A TTL flag
  is **rejected** here because the token's lifetime is fixed at mint time.

**Unattended jobs (cron) therefore belong in agent mode** — they exist because there is no human to log in.

## Features worth choosing it for

| Feature | Value |
|---|---|
| Credential brokering | No real secret in the agent's process, so an injected instruction to print the environment yields a placeholder. |
| Egress filtering | Per-agent, per-service, per-endpoint allowlists — an agent limited to the endpoints it needs, not the internet. |
| Request logging | Every authenticated call is inspectable. This is an action log for free, which cron/audit doctrine usually asks for separately. |
| Revocation | Per-agent revoke/rotate without touching any other agent's access. Compare with editing a `.env` and hoping. |

Backends: local encrypted SQLite by default; PostgreSQL for multi-instance. Credential stores: a builtin store, or
an external secrets platform for **dynamic secrets** — short-lived credentials minted on demand instead of
long-lived strings. Dynamic secrets are the strongest form and belong in a later stage.

## The caveat that decides whether it works

Its own documentation is explicit that the broker is **meant to be deployed on a separate machine from the
agents**, so that agents cannot reach the broker's own storage by compromising a shared host.

**Same-host deployment is a tidy-up, not a security boundary.** Do not present it as one.

## Staged adoption plan

- **Stage 0 — inventory.** Sort every credential onto the three rails (parent skill). Pick the first migration
  candidate on purpose: **read-only, no write scope, no funds** (a market-data key is ideal).
- **Stage 1 — prove substitution on a second host.** Stand up the broker on a *different* machine, store one
  credential class, point **one low-stakes seat** at it, and run the env-print test from the parent skill. Gate on:
  placeholder visible, outbound call succeeds, request log shows the call.
- **Stage 2 — migrate the remaining read-only credentials**, then enable the strict deny policy so egress is a
  real boundary instead of a default.
- **Stage 3 — the money path stays out.** Wallet keys never enter it, at any stage.

Give the broker's master password its own restore story (shard it, store the shards off-host) before Stage 2.
Until then it is a new single point of failure wearing a security costume.

## Sibling projects

Agent credential brokers exist as a category, so do not conclude "none exist". Alongside Agent Vault the space
includes secrets managers shipping agent access SDKs with just-in-time access and human-in-the-loop approval, a
commercial MCP gateway that injects credentials so the agent never holds them, and a Linux-Foundation-hosted
gateway with the same shape. Evaluate on the two axes that decide it here: **does it keep the value out of the
agent's process**, and **can it be deployed off the agent's host**. A broker that fails either is not buying the
thing you came for.
