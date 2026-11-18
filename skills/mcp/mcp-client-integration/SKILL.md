---
name: mcp-client-integration
description: "Use when onboarding or debugging a remote MCP client."
tags: [mcp, oauth, pkce, integration, api, credentials]
trigger: "When a remote MCP server (or an OAuth-protected API) needs a credential the agent must obtain itself; when an MCP-backed service is deployed but failing; when calling tools/call against a hosted MCP endpoint by hand."
version: 1.0.0
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [mcp, oauth, pkce, integration, credentials]
    related_skills: [native-mcp, travel-planning]
---

# Remote MCP Client Integration

## When to Use

Being a credentialed client of someone else's MCP server — acquiring the token, calling it correctly
over Streamable HTTP, and diagnosing it when it breaks. Load this when:
- a remote MCP server (or an OAuth-protected API) needs a credential you must obtain yourself;
- an MCP-backed surface is deployed but failing, and the fault may be an upstream rather than code;
- you are calling `tools/call` by hand against a hosted MCP endpoint, for a Worker, cron, or script.

> For wiring an MCP server into Hermes' own config (`mcp_servers:` in `config.yaml`, tool prefixes,
transports), use the `native-mcp` skill. **This** skill is the client-side procedure for a server
Hermes is not managing — when you are the consumer, on behalf of a Worker, cron, or script.

## The onboarding procedure — in order

### 1. Read the server's auth posture before anything else
Probe the base endpoint with no credential. The status code tells you which procedure applies:
- `200` — open, no onboarding needed.
- **`401` — the endpoint is ALIVE and wants a credential.** This is the good outcome; proceed.
- `404` — the URL is wrong or that deployment is gone. Find the canonical URL before onboarding.

**A `401` is information, not failure.** Do not treat it as "unavailable" — the server is
reachable and the remaining work is only the credential.

### 2. Discover the OAuth metadata — never guess endpoints
Most MCP servers publish RFC 8414 metadata. Fetch it; do not invent paths:
```
GET <issuer>/.well-known/oauth-authorization-server
```
Read: `issuer`, `registration_endpoint`, `authorization_endpoint`, `token_endpoint`,
`scopes_supported`, `grant_types_supported`, `token_endpoint_auth_methods_supported`.

The consent screen is often NOT at a `/consent` path — it is commonly the
`authorization_endpoint` itself (e.g. a `/connect` page). Use what metadata says.

### 3. Register a client dynamically (RFC 7591) — no allowlist needed
`POST` JSON to `registration_endpoint`:
```json
{"client_name": "<Agent> <Product>",
 "redirect_uris": ["http://localhost:8899/callback"],
 "grant_types": ["authorization_code", "refresh_token"],
 "response_types": ["code"],
 "token_endpoint_auth_method": "none",
 "scope": "<only what you need>"}
```
`token_endpoint_auth_method: none` + a localhost redirect is the public-client shape, and it is
what most MCP servers accept for a single-user agent. Expect `201` with a `client_id`.

**The `redirect_uris` you register must match the redirect you actually send, byte for byte** —
including port. A mismatch is refused at the authorize step with a message that does not name the
redirect as the cause.

### 4. PKCE is usually mandatory — generate it up front
Many servers refuse an authorize request with no challenge, and the error names the fix:
*"PKCE is required: code_challenge with code_challenge_method=S256."* Skip the wasted round trip and
always send it:
```python
verifier  = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
```
Also send a `state` and verify it on the callback — a mismatch means the code is not yours.
**Persist `verifier` and `state` to a file before opening the consent URL**: each tool call is a
fresh interpreter, so an in-memory verifier is lost by the time the code comes back.

### 5. Stand up the local callback listener FIRST
On this host the browser and the agent share a filesystem, so `http://localhost:<port>/callback`
works and the whole flow can be driven without involving the user.
- Write a tiny `http.server` handler that writes the query params to a file and returns a short
  "you can close this tab" page. **Write params to a file, never to stdout** — a `code` is a
  credential.
- Start it in the background and self-test it with a dummy query before opening the consent URL.
- `chmod 600` the callback file.

### 6. Open the consent URL and approve
Build the authorize URL from metadata + `client_id` + `redirect_uri` + `scope` + `state` +
`code_challenge`. Then: navigate, read the page, **click the button whose label names your client**
("Connect to <Your App Name>"), and wait for the redirect to the localhost callback.

Do not assume consent needs an account, an email, or a card — read the page. Many are genuinely
one tap. Check for `error` alongside `code` in the callback params either way.

### 7. Exchange the code, then store the token correctly
`POST` form-encoded to `token_endpoint`:
`grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, `code_verifier`.
Write the whole JSON response **mode 600** under the profile's `secrets/` directory.

**Never print a token, and never inline one in a shell command** — an inline secret becomes an
extra copy in the shell history and the session DB. Read it from the file inside the script.

**The access token is short-lived; the refresh token is the durable asset.** Bind the *refresh*
token into whatever consumes it, and refresh on use rather than caching an access token:
```
POST <token_endpoint>
  grant_type=refresh_token & refresh_token=… & client_id=…
```
A consumer that refreshes per call has no stale-token window and needs no renewal cron.

### 8. Verify with the real handshake, not a health check
A health endpoint proves nothing about auth. Run the actual MCP sequence:
`initialize` → `tools/list` → one real `tools/call`.
Count the tools `tools/list` returns and record them — the tool list IS the capability map.

## Calling it over Streamable HTTP

The client handshake, with the three quirks that cost the most time:
```
POST <mcp-url>   Content-Type: application/json
                 Accept: application/json, text/event-stream     <-- both, or you get a 4xx
                 Authorization: Bearer <token>
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18",
  "capabilities":{},"clientInfo":{"name":"<you>","version":"1.0"}}}
```

**Quirk 1 — the response may be SSE, not JSON.** A Streamable HTTP server can return the JSON-RPC
body wrapped in a server-sent event. `json.loads()` on it throws or yields nothing. Strip first:
```python
payload = raw.split("data: ", 1)[-1].strip() if "data: " in raw else raw
```

**Quirk 2 — stateless servers send no `mcp-session-id`.** The header is optional. If `initialize`
returns `200` with no session header, do **not** conclude the session failed — call `tools/list`
and `tools/call` without it. Only echo the header back when the server actually issued one.

**Quirk 3 — an MCP tool error is often in the body, not the status.** Some servers return HTTP
`200` with a JSON-RPC `error` object, or a `402`/`401` carrying the actionable text in
`WWW-Authenticate` or a JSON `how` array. Read the body before reporting a failure.

**Long-running tools return a search handle, not results.** Asynchronous tools (search, batch jobs)
return an id plus a `next_step`, and you poll a second tool until a completion marker disappears.
Do not treat the first response as the result set. Parse the id, poll, and only then read offers.

## Diagnosing a dead MCP-backed service

When something that fronts MCP servers starts failing, the fault is usually an **upstream**, not
the code. Work in this order:

1. **Probe every bound upstream URL independently, with no credential.** `404` = a deleted
deployment (the project may be alive while *your* deployment is gone — check the vendor's canonical
URL, it is often a totally different host). `401` = reachable but needs a credential you may not
hold. `200` on a health path = genuinely fine.
2. **Read the bindings, not the source.** A Worker's env bindings name each upstream URL — enumerate
them via the platform's settings endpoint. That list is the real dependency map.
3. **Match the error to the mechanism.** `500 {"error":"Unexpected end of JSON input"}` from an
aggregator means an upstream returned an **empty body** and `JSON.parse("")` threw. The message
names neither the upstream nor the cause — never chase it in the application code first.
4. **Check for a revoked token CLASS, not just an expired token.** A vendor can retire a whole
credential lane and revoke everything it ever issued. Re-reading the vendor's own docs frequently
turns up a dated revocation notice that explains a "suddenly broken" integration better than any
probe will.

### Prefer paying in a rail you actually hold
The fallback door for agent access is often a small one-off on-chain charge (`402` with a
`WWW-Authenticate: Payment` challenge). **Decode the challenge before quoting it to the user** — the
base64 `request` field carries amount, currency, chain id, and recipient. A challenge denominated
in a chain you have no funded wallet on is not a plan; it is a second gate. Report which rail it
wants and whether you hold it.

## Pitfalls

- **Do not paste a token, code, or verifier into chat or a command line** — write it to a mode-600
  file and have the consumer read the file. Redirect URIs and client ids are fine; secrets are not.
- **Register the exact redirect you will use.** A port or trailing-slash difference is refused at
  authorize time with a misleading message.
- **Persist PKCE state to disk before opening the consent URL** — a fresh interpreter per tool call
  loses in-memory state.
- **A truncated account/tenant id is the single most common platform error.** A display-shortened
  id yields a "could not route … perhaps your object identifier is invalid?" style error that reads
  like a permissions problem. Re-fetch the full id from the API and cache it.
- **A `success:false` from one endpoint of a platform does not mean the credential is dead.** Test
  the operation you actually need before concluding a token is useless, and before escalating to
  the user as a manual step.
- **`workers.dev` answering 404 says nothing about the route.** It is a separate enablement flag;
  always verify against the public hostname.
- **Health checks do not test auth.** A `/health` that returns `200` to a deliberately wrong
  credential proves only that the process is up.

## References

- `references/letsfg-travel-mcp.md` — worked example: the LetsFG travel MCP (endpoints, OAuth
  specifics, the tool groups, and how the credential is bound into a Worker).
