---
name: cloudflare-zone-operations
description: "Use when editing or debugging a Cloudflare zone."
category: devops
version: 1.0.0
author: Hermes curator
license: MIT
tags: [cloudflare, dns, workers, edge, tokens, tunnels, proxied, devops]
metadata:
  hermes:
    tags: [cloudflare, dns, workers, edge, tokens, tunnels, proxied, devops]
    related_skills: [public-endpoint-diagnosis, x402-api-compliance, service-health-monitoring]
---

# Cloudflare zone operations

Changing or debugging a Cloudflare-fronted domain: DNS records, the `proxied` flag, Worker routes, edge
rules, API tokens, and tunnels.

**The expensive mistake in this class is misattribution** — measuring a real symptom *on the origin* (a
fallback certificate, 404 on every route) and concluding the fix belongs there, when the cause is one field
of edge config that needs no origin access at all. **Measure the symptom where it appears; attribute the
cause from the edge config.**

## When to use

- A hostname on the zone is unreachable, TLS-failing, or 404s on every route.
- Enabling/disabling the orange cloud, or adding/editing a DNS record.
- A Worker route exists but appears not to run, or a Worker returns `error code: 1003`.
- Minting, verifying, or scoping a Cloudflare API token.
- Standing up a Cloudflare Tunnel.

## Rule 1 — the `proxied` flag decides whether the edge is in the path AT ALL

An **unproxied** (grey-cloud) record bypasses Cloudflare completely: **Worker routes, WAF rules, redirect
rules, and caching do not apply**, because the request never reaches the edge.

- **A route that exists in the zone is NOT evidence that it runs.** Check the flag on the record too.
- **Two hostnames on the SAME origin IP can behave differently** — one proxied (the edge answers, TLS is
  fine), one DNS-only (it reaches the origin and fails). Grouping by resolved IP alone will therefore *miss*
  the fault.
- **The tell that finds it: a single hostname whose `proxied` flag differs from every working sibling.**
- Conversely: if a Worker route is *supposed* to serve a hostname, the fix for that broken hostname may be to
  turn the orange cloud **ON**, not off. Read the intent before flipping anything.

## Rule 2 — diagnose from the zone config, not from resolution

Resolution says where a name *points*; the record attributes say how it is served. Pull the config before
changing anything, and assert after.

```python
# bearer token read from its mode-600 file inside the script — never interpolated into a shell command line
GET /accounts                                              -> account_id, and proof the token works
GET /zones?name=example.com                                -> zone_id
GET /zones/{zone_id}/dns_records?per_page=100              -> type,name,content,proxied,proxiable,id
GET /zones/{zone_id}/workers/routes                        -> pattern -> script
GET /accounts/{account_id}/workers/scripts
```

Diff `proxied` across all records of the domain; list the Worker routes and ask whether one is *meant* to
handle the failing hostname.

## Rule 3 — the token prefix decides the verify endpoint

Cloudflare's scannable credential formats carry a class prefix, and the prefix changes which endpoint is
authoritative:

| Prefix | Credential | Verify at |
|---|---|---|
| `cfat_` | **Account** API token | `/accounts/{account_id}/tokens/verify` |
| `cfut_` | **User** API token | `/user/tokens/verify` |
| `cfk_` | Global API key | (not a token) |

> **A valid `cfat_` token returns `401 Invalid API Token` at `/user/tokens/verify`** — a false negative, not a
> bad credential. **Read the prefix before declaring a token dead**, or you will tell the user their working
> token is broken.

A token that lists accounts (`GET /accounts` → 200) is working, and that call also yields the account id.
Probe capabilities before planning work rather than assuming scope:
`GET /accounts/{id}/cfd_tunnel` (Tunnel:Edit) · `GET /zones/{id}/dns_records` (DNS:Edit) ·
`GET /zones/{id}/workers/routes` (route list).

## Rule 4 — apply, then read back

```python
PATCH /zones/{zone_id}/dns_records/{record_id}   {"proxied": true}
GET   /zones/{zone_id}/dns_records/{record_id}   # assert the field actually changed
```

`success: true` is not a config change until you read it back. Then **probe the live hostname** — the API
cannot tell you whether the endpoint serves.

## Rule 5 — "TLS restored" is not "endpoint restored"

Enabling the edge restores the certificate and starts applying edge config. It does **not** bring back a
backend. Report the two claims separately, each with its own probe:

- what was **fixed and verified** — the field, the read-back, the new `tls_verify` value
- what is **still down and why, measured** — closed ports, a looping route — never a shrug
- who owns each remainder, and whether it needs host access

A valid certificate in front of a dead backend is still a dead endpoint.

### Before planning a "restart", prove the thing exists

**A backend can be ABSENT rather than stopped** — never deployed, or dropped in a migration — and then
"restart the service" is not a fix, it is a guess that burns the user's minutes at a prompt. Four probes, run
in this order on a host you have access to, settle it:

```bash
systemctl list-units --all --no-pager | grep -Ei '<service-a>|<service-b>'   # any unit?
docker ps -a --format '{{.Names}} | {{.Status}} | {{.Ports}}'                # any container, incl. Exited?
ss -ltnp                                                                     # any listener on the ports?
find / -maxdepth 5 -iname '*<service>*' -not -path '/proc/*' 2>/dev/null     # does the CODE exist?
```

**No unit + no container + no listener + no code = a deploy, not a restart.** Say that plainly, and move the
work to a build queue instead of holding a user at a root prompt — a migration story is confirmed by the
**last-login stamp** on the prompt, which dates the last time anyone touched the box.

**When the code survives only in a recovery snapshot or a repository, treat recovery as part of the work and
be exact about scope:** restore what exists, **name precisely which pieces are missing**, and check the org's
repos before committing to a rebuild. "Two of four recovered, and the missing two are not in any repo" is a
usable status; "the services are down" is not.

## Rule 6 — Worker routes intercept, and their failure modes imitate origin faults

A matching Worker route takes precedence over the origin — **but only for proxied traffic.** Three traps make
a Worker look like a broken origin or a broken edge:

- **Catch-all redirect loop.** A Worker that proxies to a bare origin IP on :80 receives the origin's
  HTTP→HTTPS **301**; `fetch` follows redirects by default, so it lands back on the zone's own proxied
  hostname, re-enters Cloudflare, and trips the loop guard → **`error code: 1003`**.
- **Bare-IP subrequest refused.** A Worker that `fetch`es `http://<ip>:<port>/…` — with no hostname in the
  URL — is refused by the edge itself with the **same `1003`**, and the origin is never contacted. The fix is
  the opposite shape: keep the hostname in the URL and pin the address with
  `cf: { resolveOverride: <ip> }`. **Distinguish this from the loop before editing anything** — no origin
  log, no 301 to observe, and `redirect: "manual"` does not help.
- **Workers cannot set the `Host` header on a fetch** — `headers.set("Host", …)` is silently dropped, so a
  Worker reaching an origin by IP speaks the wrong virtual host.
- **Closed backend ports read as an outage.** Enumerate the ports the Worker actually proxies to, not just
  80/443.

Full detail, the confirmation commands, and the correct proxy shape: **`references/worker-proxy-patterns.md`**.

> **`error code: 1003` has two opposite causes** — a proxied record whose path is blocked by the edge, or an
> unproxied record that should have been served by a Worker. Same symptom, opposite fixes. **Confirm which
> before changing DNS.**

## Rule 7 — a Cloudflare Tunnel is not automatically the answer

A tunnel is a second path to the same backends and adds a credential to manage. **Match the fix to the
architecture that already exists:** if the zone already has Worker routes for the hostname, repair those
rather than layering a tunnel over the top. Reach for a tunnel when there is no existing edge path and no
inbound-port option.

## Rule 8 — a Pages custom domain can be BOUND and INACTIVE at once

A Cloudflare Pages project can hold a custom-domain binding whose status is `deactivated`: it appears in
the project's own domain list and serves nothing. **A hostname that 404s on every path while already
listed in the project's domains is not "never deployed" — it is a binding that is not live.**

**Two faults stack here, and fixing either one alone leaves the site down:**

1. the Pages custom domain is bound but not `active`;
2. the DNS record for the hostname still points at the **old origin** — a bare A record to a host that no
   longer serves it — instead of the Pages target.

```python
GET    /accounts/{account_id}/pages/projects/{project}/domains          # status per domain
POST   /accounts/{account_id}/pages/projects/{project}/domains          # {"name": "<host>"} -> add
DELETE /accounts/{account_id}/pages/projects/{project}/domains/{host}   # then re-POST to re-initialise
PATCH  /zones/{zone_id}/dns_records/{record_id}                         # -> CNAME <project>.pages.dev, proxied
```

A domain stuck `deactivated` frequently re-initialises only when **removed and re-added**. **Capture the
old DNS values before rewriting them** — a flattened CNAME at the apex is fine, but the rollback is only
free if you wrote it down first.

**Binding a custom domain does NOT freeze the content.** A later deploy to the same project replaces what
is served, so "is this deployment stale?" is a follow-up, never a prerequisite. **Restore the binding now
and review the content after** — a live host serving an older build beats a 404 while you deliberate.

### A Pages SPA fallback answers EVERY path — including the machine-readable ones

**A single-page-app deployment serves its `index.html` for any path it has no file for, and it does so with
`200 OK`.** So a discovery document an agent fetches by convention — `/.well-known/x402`,
`/.well-known/agent-card.json`, `/.well-known/mcp.json`, `/openapi.json`, `/llms.txt` — comes back as
**`200 text/html`** carrying the website. **A fake 200 is worse than a 404: a 404 is an honest "not here",
while a 200 carrying HTML is an answer that lies.** The damage is silent — a registry or client parses
nothing, renders blanks, and reports no error on either side.

- **Test the CONTENT, not the status.** `http=200` plus a byte count is exactly what a status-only check
  reads as healthy. Assert `content-type` and parse the body.
- **The tell:** every unrelated path returns the *same byte length* — that is one file answering all of them.

**Fix it surgically with a Worker bound by ZONE ROUTE** rather than rewriting or moving the site: create a
Worker that proxies only those paths to the origin that serves them properly, and add one route per path
family. **Measured: a zone route DOES take precedence over a Pages custom domain**, so the website keeps
serving everything else untouched and needs no change at all.

```
<host>/.well-known/*        -> <proxy worker>
<host>/openapi.json         -> <proxy worker>
<host>/llms.txt             -> <proxy worker>
```

Rules for that proxy worker:

- **Pass `content-type` through VERBATIM.** A `.json` arriving as `text/html` is the defect being fixed.
- **Proxy every method, not just GET** — a JSON-RPC or POST surface on one of those paths must not be
  reduced to read-only. Let the origin's own answer (including its `405`) be the truth.
- **A path the origin lacks returns the origin's own 404 — never the website, never invented content.**
- **Cache assets (`max-age=60`) and cache errors not at all.** A cached 404 that outlives the fix is its own
  trap, and an unreachable origin answers `502` with a note rather than a substitute page.
- **Zone routes go live without the `workers.dev` subdomain toggle** — that POST is only needed to expose a
  script at `<name>.<subdomain>.workers.dev`.
- **Close the conventional paths the origin does not have.** A 404 for `/.well-known/agent-card.json` is a
  discovery miss you can simply fix by serving a real descriptor from the proxy — but only invent content
  you can stand behind.

## Rule 9 — auditing a whole zone: the API gives configuration, never intent

Asked *"which of these do we no longer need?"*, the zone API answers **configuration** completely and
**intent** not at all. Enumerate, probe, classify — but resolve "unneeded" against the architecture record,
never against a status code.

```python
GET /zones/{zone_id}/dns_records?per_page=100   # type,name,content,proxied -> the full configured set
GET /zones/{zone_id}/workers/routes             # pattern -> script         -> what the edge intercepts
```

Probe every hostname for **status AND body**, then bucket:

| bucket | evidence |
|---|---|
| serving | 2xx **and** a body that is the expected content |
| broken | a route exists but the app answers 404 — Worker deployed, app not |
| dead | an A/CNAME to an origin answering 404/5xx — the record is real, the backend is gone |
| no DNS | named in docs, absent from the API — nothing to delete here; fix the references |
| phantom route | a Worker route with **no DNS record** — it can never fire |
| orphan script | deployed in the account, **no route attached** — it can never receive a request |

**Deployed is not routed, and the gap is invisible code.** `GET /accounts/{id}/workers/scripts` lists what
*exists*; `GET /zones/{id}/workers/routes` lists what can *receive*. **Diff the two sets.** An unrouted
function fails **silently** — no 404, no error, no edge log — so anything depending on it (a payment callback,
a webhook, a facilitator) simply never arrives and nothing reports why. Measured: **23 scripts against 10
routes**, leaving 13 unreachable functions that read as live assets in every inventory. Report the orphan set,
and treat each one as **preserve-before-delete** — it may hold the only copy of its code, exactly like any
other unbacked artifact.

**Two checks that change the verdict:**

- **Wildcard detection.** Before reading a 404 as per-host meaning, confirm there is no `*` record. With a
  wildcard every 404 is the catch-all and says nothing about that hostname.
- **CNAME takeover.** A record pointing at `*.workers.dev` (or any provider hostname) whose target has been
  **deleted** is claimable by anyone. Fetch the target and confirm it answers rather than returning *worker
  not found*, **before** reporting the zone clean. This is the one finding in a zone audit that is a
  security incident rather than a hygiene item.

**A record that 404s is not a record nobody wants** — an approved architecture named 8 hostnames a liveness
sweep had marked obsolete. Full recipe: **`references/zone-record-audit.md`**.

**Status code is not health.** A Worker answering `200` with `{"error":"Not found"}` in the body looks
perfectly healthy to a status-only check and serves nothing. Read the body.

## Rule 10 — prove a WRITE capability with a throwaway resource, and prove the cleanup

Some capability questions **cannot** be answered by reading. *Can this token deploy?* is the archetype: a
read-only audit correctly refuses to answer it, so the question hangs and blocks every plan that depends on it.
**When the answer re-routes the whole plan, spend one mutating probe — on a name that is obviously disposable
— and prove both halves:**

```python
PUT    /accounts/{id}/workers/scripts/<probe-name>   # 1. create the throwaway
GET    /accounts/{id}/workers/scripts                # 2. read it BACK from the collection
DELETE /accounts/{id}/workers/scripts/<probe-name>   # 3. delete
GET    /accounts/{id}/workers/scripts                # 4. read back again, assert absent
```

**`success: true` on the write is not existence, and a probe that leaves a resource behind is not a probe** —
it is litter in an account you are auditing. Report all four results, not the verdict alone. If creation is
refused, say so plainly: *nothing was created and nothing needs cleanup* — the capability question is answered
either way, and cleanly.

## Rule 11 — to debug a live Worker you did not write, deploy a COPY that tells you the error

A handler wrapped in a framework error handler answers a bare `500 Internal Server Error` and logs the real
reason somewhere you may not be able to read. **Do not infer the cause, and do not redeploy over the
production script.** Pull the source, patch a copy, and let the code tell you:

1. **Download the deployed source.** `GET /accounts/{id}/workers/scripts/{name}/content` answers
   `method_not_allowed` for a **module-format** worker — that is an API-shape error, not a dead script. The
   module download is `.../content/v2`, which returns **multipart**; split the parts and write each file under
   its `Content-Disposition` filename.
2. **Patch only the error branch** so it returns the message and the first few stack frames.
3. **Deploy under a NEW name.** The production script keeps serving untouched; the copy is one DELETE away
   from gone.
4. **Bundles importing node builtins need `compatibility_flags: ["nodejs_compat"]`** in the upload metadata.
   Without it the deploy is rejected with `No such module "node:stream"` — a missing flag, not a broken bundle.
5. **A new script's `workers.dev` route is DISABLED by default**, so every call returns **`error code: 1042`**
   until you enable it — one POST, no redeploy:
   ```bash
   curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/scripts/$NAME/subdomain" \
     -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" -d '{"enabled":true}'
   ```
   **Compare against a known-good script on the same account before concluding anything account-wide:** one
   200 and one 1042 side by side proves it is per-script. A 1042 does **not** justify rebuilding on a VPS —
   that turns a ten-second toggle into a migration.
6. **Read the error, then delete the copy and read the collection back** to prove it is absent.
7. **The upload content-type decides the SYNTAX, and the wrong one fails as `415`, not as a syntax error.**
   `PUT /accounts/{id}/workers/scripts/{name}` accepts `application/javascript`, `text/javascript` or
   `multipart/form-data` — **`application/javascript+module` is refused with `415`.** Under
   `application/javascript` the body is parsed as **service-worker** syntax, so a module body
   (`export default { fetch }`) is invalid there: wrap it as
   `addEventListener("fetch", e => e.respondWith(handle(e.request)))`, or use the multipart/metadata
   route for true module format (with `compatibility_flags` — see item 4).
8. **`node --check` the artifact before uploading, and read the upload's own status afterwards.** A
   duplicate `let` declaration comes back from the API as a bare `HTTP 400 / code 10021 "Identifier … has
   already been declared"`, which reads like an upload problem and is a syntax one — one local second
   instead of a round trip. **And a REJECTED upload leaves the PREVIOUS version serving:** every probe
   afterwards measures the old build, and if the old build also answers in the shape you expect, those
   probes read as success for the wrong artifact. **A 4xx on the upload invalidates everything measured
   after it.**

This also settles a capability question cheaply: deploying a harmless new script proves write access without
touching anything that serves.

## Rule 12 — a 500 on EVERY route is one startup failure, not N broken handlers

When a service is up (`/health`, `/pricing`, discovery docs all answer) but **every** functional endpoint
returns `500`, do not debug the endpoints. **A uniform status across unrelated handlers is a shared
initialisation failure** — config load, credential/key load, or a dependency client refusing to construct.
Reproduce one call, read the one exception, fix the one cause.

**The corollary for payment gates:** an `x402` gateway that throws during payment-layer initialisation
returns `500` and **never issues the `402` challenge at all**. Callers report "payments don't settle" /
"the facilitator rejects us" when the server never asked for money. **Check that a paid route returns `402`,
not just that the service is alive** — a healthy `/health` beside a `500` on every paid path is the exact
shape of a payment rail that has never worked.

**The most common cause is arithmetic, not code: an EMPTY network intersection.** A gateway declaring only
mainnet chains, pointed at a facilitator that serves only testnets, cannot construct a single supported
payment kind — so the payment layer refuses to initialise and every paid route `500`s. Settle it with one
probe before reading any gateway source:

```bash
curl -s https://<facilitator>/supported      # the kinds it will actually settle
```

Diff those `network` values against the chains the gateway advertises. **Zero overlap = zero payments**, no
matter how correct the rest of the gateway is — the failure is the match, not the implementation. Probe
results drift, so re-read them rather than trusting a table.

**The same probe proves the free path.** A testnet-only facilitator is the right tool for a full
`402`→pay→settle proof *before* buying mainnet credentials — debug the handshake with no money at risk, then
repoint at a mainnet facilitator once the mechanism is known good.

**Two follow-ups that change the fix.** ① **Read one handler body** — a route returning a placeholder
(`c.json({ success: true, data: "X results" })`) is a STUB, and repairing the facilitator buys nothing;
the job is then to build the product, not fix the rail. "Protocol compliant" and "delivers real data"
are different tests. ② **Confirm the published surface IS this deployment** — one product can exist
twice (a container estate behind an API hostname, and an edge/Worker estate under a `*.workers.dev`
URL), and a listing may point at either, so a fix applied to the wrong estate reaches no buyer. Triage
both, plus facilitator-auth credential shapes, in the `x402-api-compliance` skill's
`gateway-failure-diagnosis` reference file.

## Rule 13 — a Worker's egress IPs are shared, and free public APIs throttle them

**A Worker calling a third-party API is not calling it from a neutral address.** It leaves from Cloudflare's
shared egress pool, and free data APIs rate-limit those pools aggressively. Measured on one day across three
independent providers: **each answered `200` from an ordinary host and `429` from the Worker.**

- **"The API works" verified from a shell is NOT evidence that the Worker can use it.** Probe the dependency
  *from the Worker* — a temporary self-test route or a shadow build — before wiring a route to it.
- **Treat a third-party dependency as a design decision, not a detail.** Prefer a keyed or clearly-generous
  tier for anything a revenue path depends on, and always retry `429`/`5xx` with backoff. Retry softens a
  throttle; it cannot be relied on to remove one.
- **Never let this reach a customer as a charged failure.** Where the Worker gates a payment, fetch the data
  **before** quoting the price and refuse with the reason and **no charge** if the upstream does not answer.
  A static "this data source exists" flag cannot see a throttle — only a live pre-flight can.
- **Exercise every outbound path before promoting the build**, and strip the self-test route afterwards
  (prove its path 404s). A debug route that survives promotion is a free hole in a paid surface.

## Credential handling

A Cloudflare API token is a revocable secret, and the `cfat_`/`cfut_` formats exist **precisely so DLP tools
can detect leaks** — Cloudflare scans for and auto-revokes leaked tokens. So: install to a mode-600 file,
delete the chat message if it arrived through chat, redact the transcript copies, then re-scan to zero. That
lowers exposure; **rotation is still the close.** Never echo the value, and never interpolate it into a shell
command line (that writes another copy into the transcript).

## Pitfalls

- **Changing DNS before reading the zone config.** One flag flip is cheap; flipping the wrong way drops a
  working hostname off the edge. Read `proxied` and the Worker routes first.
- **Concluding a token is invalid from one endpoint.** The prefix decides the verify endpoint — a `401` at the
  user endpoint means "wrong endpoint for this token class" far more often than "revoked".
- **Assuming a proxied sibling's 200 proves the origin is healthy.** A proxied 200 is answered from the edge
  and says nothing about the origin's certificate, router, or service.
- **Reporting a fix as complete at the handshake.** `tls_verify=0` is a claim about TLS, not about the
  service. Probe the real routes and state both results.
- **Treating a Worker route's existence as its execution.** Unproxied records never reach the edge, so the
  route is dead code — check the flag.
- **Concluding "never deployed" from a 404 on a hostname that is already in the Pages project's domain
  list.** A `deactivated` binding answers exactly like an absent site, so the rebuild looks justified. Read
  the domain status before redeploying anything.
- **Reading a `200` on a `/.well-known/*` or `/openapi.json` path as "the file is there".** On a
  single-page-app host the fallback answers every path with the site itself, so the file may not exist at
  all — and a status-only check reports it healthy. Assert `content-type`, and parse the body.
- **Correlating route patterns against DNS by splitting the pattern on `/`.** Patterns carry the scheme
  (`https://api.example.com/*`), so the split yields `https:` as the "host" and every record silently reports
  as missing. This produced a retracted finding — "the route exists but the DNS record does not" — that was
  purely an artefact of the parser. **Validate a parser against a case whose answer you already know before
  reporting its output as a finding**: a parse bug and a real gap are identical in a results table, and the
  retraction costs more than the check.
- **Fixing only the hostname you were asked about.** When several records share one misconfiguration,
  enumerate the affected set and report it; fixing one leaves the rest down.

## Related

- `public-endpoint-diagnosis` — reachability/TLS triage and origin-vs-edge attribution.
- `x402-api-compliance` — discovery-endpoint and marketplace concerns for an x402 gateway.
- `service-health-monitoring` — ongoing port/URL monitoring after the fix.
