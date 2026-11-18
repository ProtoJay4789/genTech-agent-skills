---
name: hermes-dashboard-auth
description: "Use when the dashboard login must be set up or fails."
trigger: "Setting up dashboard username/password auth, a public bind shows a sign-in page you cannot satisfy, or credentials that 'should work' return Invalid credentials."
tags: [hermes, dashboard, auth, docker, s6, config]
version: 1.0.0
author: Gentech
---

# Hermes Dashboard Auth

## The precedence trap: the container's ENVIRONMENT beats `.env`

The bundled provider (`plugins/dashboard_auth/basic`) resolves each setting env-first, then config:

```
HERMES_DASHBOARD_BASIC_AUTH_USERNAME      (env)  ->  dashboard.basic_auth.username   (config)
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD      (env, plaintext, hashed in-memory)
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH (env)  ->  dashboard.basic_auth.password_hash
HERMES_DASHBOARD_BASIC_AUTH_SECRET        (env)  ->  per-process random key if unset
```

In a Docker/s6 install the container environment is injected at launch (via
`/run/s6/container_environment/`, populated by the host's `docker run -e` / compose / env file).
That layer **wins over anything written to `/opt/data/.env` or `config.yaml`**.

**Writing auth keys into `.env` while the container already supplies them does nothing — and can
LOCK EVERYONE OUT.** Measured 2026-10-12: the container supplied `USERNAME=hermes` +
`PASSWORD=<32 chars>`; adding `USERNAME=<new>` + `PASSWORD_HASH` to `.env` changed only the
username the process loaded (dotenv overlays it) while the container's `PASSWORD` still forced
`hash_password(container_password)` to override the hash. Result: a **mismatched pair** — the new
username with the old password's hash. Neither credential worked. Fix: remove the `.env` keys so
the container env governs both halves again; login then returned 200 with 3 session cookies.

**Rule: never set one half of a credential pair in a layer that the other half isn't in.**

## Diagnosing

1. Which username is live **now** (not from an old log line):
   `tr '\0' '\n' < /proc/$(pgrep -f 'dashboar[d] --host' | head -1)/environ | cut -d= -f1 | grep AUTH`
   — `/proc/<pid>/environ` shows the launch env and does NOT show variables dotenv set later, so
   the two sources are distinguishable.
2. What the provider registered: the plugin logs
   `dashboard-auth-basic: registered password provider (username=X)` — **check the timestamp**; an
   old line is not evidence about the current process.
3. The env layer itself: `ls /run/s6/container_environment/` (readable even when root-owned) and
   `/opt/hermes/docker/s6-rc.d/dashboard/run` (the service definition).

## Verifying — a login, not a registration

`GET /api/auth/providers` returning `200` with a provider proves only that *something* registered.
Prove the credential with an actual login POST:

- Endpoint is **`POST /auth/password-login`** — NOT `/api/auth/...`. `_GATE_PUBLIC_PREFIXES`
  bypasses `/auth/password-login`, `/login`, `/api/auth/providers`; everything else under `/api/`
  is gated, so a POST to `/api/auth/password-login` returns the middleware's 401
  `{"reason":"no_cookie"}` (a gate rejection) rather than the handler's `Invalid credentials`
  (a real verdict). **Those two 401s mean opposite things — read the body.**
- Body: `{"provider":"basic","username":U,"password":P,"next":""}`. Success = `200` + 3
  `Set-Cookie`; then `GET /api/auth/me` with the cookie jar must stop returning 401.
- Always send the wrong password too, and confirm it still fails. A test that only tries the good
  password cannot tell a working login from a gate that lets everything through.
- Keep the password out of the command line — `curl --data @file` or read it inside Python. The
  command string lands in the transcript.

## Fixing it properly

The container env is root-owned (`drwxr-xr-x root root`) while the agent is uid 10000, so the agent
**cannot** change it from inside. Two honest options:

- **Use the configured credential as-is**: read the username from
  `/run/s6/container_environment/HERMES_DASHBOARD_BASIC_AUTH_USERNAME` and the password from the
  sibling `..._PASSWORD` file (or the host env file that fed the container). Verify with a login POST
  before handing it over.
- **Use different credentials**: set `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` + `_PASSWORD` in the
  container's environment **on the host**, then recreate the container. Nothing inside the container
  can do this.

Set `HERMES_DASHBOARD_BASIC_AUTH_SECRET` too: with it unset the plugin generates a random signing
key per process, so **every restart logs the user out**.

## Pitfalls

- A public bind always requires an auth provider (the June 2026 hardening): `--insecure` is a no-op
  and no longer bypasses the gate.
- `hermes dashboard --stop` / `--status` exist; the dashboard child runs as the agent user, so it can
  be restarted by PID. **Never `pkill -f '<pattern>'` when the pattern appears in your own command
  line** — the shell running it matches and kills itself (use `pgrep -af 'dashboar[d] --host'`, the
  bracket trick, then kill by PID).
- Do not conclude "no credential exists" from a sign-in page: a public bind renders one whether or
  not an auth provider is registered.
