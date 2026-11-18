---
name: public-endpoint-diagnosis
description: "Use when a public endpoint is down, TLS-broken or wrongly public."
category: devops
version: 1.0.0
author: Hermes curator
license: MIT
tags: [dns, tls, cloudflare, traefik, nginx, reverse-proxy, reachability, diagnosis]
metadata:
  hermes:
    tags: [dns, tls, cloudflare, traefik, nginx, reverse-proxy, reachability, diagnosis]
---

# Public endpoint diagnosis

A public URL is unreachable or TLS-failing. The expensive mistake is not fixing it — it is **misattributing
it**: reporting that the fix is blocked on someone else's box when the box is your own, or fixing one host
when the fault is on every host of a class.

## When to Use

- A public hostname returns `http=000`, a TLS verification error (`tls_verify=18`, `certificate is not valid
  for any names`), or a 404 on every route.
- An API gateway, webhook, or paid endpoint that no external client can reach.
- Several hostnames fail at once under one domain.
- Before reporting that access to a host or IP is blocked on a third party.

## Procedure

### 1. Establish the pattern before debugging one endpoint

When more than one hostname fails, do not debug the one you were asked about. Resolve every subdomain of the
domain and group them by the IPs behind them:

```bash
for h in example.com www.example.com api.example.com mcp.example.com demo.example.com; do
  printf '%-28s ' "$h"; getent hosts "$h" | awk '{print $1}' | tr '\n' ' '; echo
done
```

- Hosts on **Cloudflare anycast ranges** (`104.x`, `172.67.x`, `2606:4700::`) are **proxied** — Cloudflare
  terminates TLS, so they answer 200 no matter what certificate the origin holds.
- Hosts on your **origin IP** are **DNS-only** — they reach the origin directly and need a valid certificate
  AND a router *per hostname*. This is where the failure appears.

**The tell that it is systemic rather than endpoint-specific:** every DNS-only host fails identically while
every proxied host works. That means no valid origin certificate exists for *any* directly-served name — so
the fix is one change for the whole set, and the blast radius includes non-API properties (demo sites, static
pages, arcade pages), not just the service you were asked about. **Enumerate the DNS-only set and report it**;
fixing only the reported host leaves the others down.

### 2. Read the certificate as a statement about routing, not validity

An origin serving `CN=TRAEFIK DEFAULT CERT` (issuer the same) is not presenting an expired certificate — it
is presenting the reverse proxy's *fallback* certificate, which is what it serves when **no router matches
the hostname**. Requests then fall through to the default handler and 404.

> **Read it as "this origin has no route for this name", not "TLS is broken".** Diagnosing it as a cert or
key problem sends you to renew something that is not the fault.

```bash
curl -sI https://api.example.com/status                       # http code + tls_verify
curl -skv https://api.example.com 2>&1 | grep -E 'subject|issuer|HTTP/'
curl -sk  -o /dev/null -w '%{http_code}\n' https://api.example.com/status   # -k to see past the fallback cert
```

### 3. Confirm the origin is yours before assigning the fix to anyone

**A service on a public IP you cannot see locally is very often on the host you are running on**, one layer
above your own namespace — a reverse proxy, a systemd unit, or a sibling container. Check identity first:

```bash
curl -s https://api.ipify.org   # your EGRESS IP — the HOST's public IP, not the container's
getent hosts <that-IP>          # reverse DNS names the provider
cat /etc/resolv.conf            # 127.0.0.11 => Docker's embedded resolver => you are inside a container
ls /proc/1/cgroup               # confirms the container boundary
```

If a failing hostname resolves to **your own egress IP**, the service is on your host — reachable by whoever
holds host access, and the fix belongs to your infrastructure. **Establish this before writing that a fix is
blocked on a box you cannot reach.**

**Corollary — not seeing the process is expected, not evidence of a different machine.** From inside a
container there is no `docker` socket, no listener on the host's ports, and no `traefik`/`nginx` process — a
host-level reverse proxy is simply outside the namespace. Absence of the process is not absence of the host.

### 4. Fix paths, in order of cost

**Re-proxying alone does NOT restore TLS — it only does so if the zone's SSL mode accepts the origin
cert.** Treat these as two independent fixes, because a proxy change without the SSL-mode change converts
one failure into another (`000` → `526`) and the host stays down.

1. **Re-proxy the DNS-only hostnames through Cloudflare** (orange cloud). This is necessary for every
   directly-served host, and it matches whatever already works for the proxied siblings — but on its own it
   only moves the request in front of Cloudflare.
2. **Make Cloudflare accept the origin certificate.** Read the zone's SSL mode and decide deliberately:
   ```bash
   curl -s -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE/settings/ssl"   # off|flexible|full|strict
   ```
   - **`strict` + a fallback origin cert = 526** (Cloudflare refuses to talk to the origin). Either set the
     mode to **`full`** — Cloudflare still encrypts, it just stops requiring a cert the origin does not have;
     the pragmatic default for an origin on a private IP — or issue a real certificate at the origin so
     `strict` can pass. **State which you chose and why**: `full` is a deliberate trade of origin-identity
     validation for reachability, and it is one call to reverse.
3. **Then confirm the origin actually ROUTES those names** (step 5b) — DNS and TLS being right does not mean a
   backend exists.

```bash
# The better long-term fix, when you have host access rather than only an API token:
certbot certonly --standalone --non-interactive --agree-tos --expand \
  -m admin@example.com -d example.com -d api.example.com -d demo.example.com
```

**Order matters: reachability outranks discoverability.** While an endpoint is unreachable, no amount of
listing, indexing, marketplace registration, or catalogue placement pays off — a perfect listing only leads a
buyer to a 404. Fix the door before buying advertisement for it.

### 5. Prove the fix with a client-shaped probe

Define done as the forged-client condition, not your own relaxed probe:

- `tls_verify=0` with **no** `-k`
- the canonical status/health route returns 200 behind a valid certificate
- a probe carrying the identity and headers a real client sends, not a bare `curl`

### 5b. Ask the origin directly, with a Host header, to separate "no route" from "backend down"

Once DNS and TLS are correct, a remaining failure is almost always at the origin's routing layer. Send the
request straight at the origin IP with each hostname in a `Host` header and read the code as a routing fact:

```bash
for h in example.com api.example.com demo.example.com; do
  printf '%-28s ' "$h"
  curl -sk -o /dev/null -w '%{http_code}\n' --max-time 12 -H "Host: $h" https://<ORIGIN-IP>/
done
```

| Code | Meaning |
|---|---|
| **404** | The proxy is UP but has **no router/backend for that hostname** — config missing, or the service is not running. |
| **502 / 503** | A router exists but its backend is down — a *different* fix. |
| **200 / 301** | The service is genuinely serving. |

**Report these layers separately.** "DNS and TLS are fixed; the origin has no route for these names" is an
actionable, correctly-scoped verdict, and it is a materially different claim from "the endpoint is fixed".
`-k` is correct *here*: this probe is about routing, and the certificate question was settled in step 2.

### 5c. When an edge function fronts the host (Worker / edge proxy)

A hostname can be routed to an **edge function** instead of the origin. Check the route table before blaming the
origin — the Workers estate accumulates routes nobody remembers adding:

```bash
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/workers/routes"    # pattern -> script
```

Two failure modes are unique to this layer, both measured:

1. **`error code: 1003` (a 17-byte plain-text body) = a Worker subrequest to a RAW IP.** Cloudflare rejects
   `fetch("http://1.2.3.4:port/path")` from a Worker with *Direct IP Access Not Allowed*. The Worker looks
   healthy in the dashboard and may never have been modified — it was deployed broken and stayed broken, which
   is why nothing flags it. **Fix: keep the hostname and pin the IP instead.**
   ```js
   const req = new Request(`http://${targetHost}:${port}${path}`, {
     method, headers, body,
     cf: { resolveOverride: ORIGIN_IP },     // hostname preserved, IP pinned
   });
   ```
   `resolveOverride` is the documented pattern; rewriting the URL to a bare IP brings `1003` straight back.
   **Before deploying that fix, confirm a listener exists on the target port** — a fix onto a dead port turns a
   loud `403` into a quiet `502`, which is strictly worse, because a `403` at least tells the truth.

2. **A `/health` answered by the edge function itself is a decoy.** The Worker commonly hardcodes its own
   health response — measured: a host returned `200 {"status":"ok","service":"<proxy-name>"}` on `/health`
   while **every real endpoint returned `403`**. That route never reaches an origin, so it cannot detect an
   outage. > **A smoke alarm wired to its own battery.** Any monitor that checks only `/health` reports healthy
   straight through a total outage. **Read the body and check the service name is the BACKEND's, not the
   proxy's** — a plausible-looking `{"status":"ok"}` is exactly what makes this survive undetected.

**Verify with a real service path, never the health route.** On a paid endpoint the correct unauthenticated
answer is `402` (payment required) — a `403`, `200`, or `000` there is a finding.

### 5d. Identify catch-alls before trusting any 200

A host answering 200 on an API-looking path may be a single-page app returning one HTML shell for everything.
Compare a real path against a nonsense one — **identical bytes, or `text/html` on a route that should return
JSON, means catch-all, and every 200 from that host is noise:**

```bash
for p in /health /definitely-not-a-real-path-xyz123 /v1/<real-service>/; do
  curl -s -o /dev/null -w '%{http_code} %{content_type}\n' --max-time 10 "http://$HOST$p"
 done
```

This catches the trap in both directions: a local port serving an SPA reads as a working gateway until you
notice it is `text/html` on a JSON route, and a nonsense path returning 200 exposes a fallback that would
otherwise pass a status sweep.

**Cheapest catch-all detector: compare CONTENT LENGTH across the paths that are supposed to differ.** One
request per path, and identical byte counts across unrelated documents is proof they are the same document:

```bash
for p in /jordan.html /vanito.html /hub.html /DeFi/data.json; do
  curl -s -o /dev/null -w "$p %{http_code} %{content_type} %{size_download}\n" --max-time 10 "$SITE$p"
done
```

Measured: four unrelated pages and a JSON data file all returned **200, `text/html`, 18149 bytes** — the host
was serving its index page for every path, so five "OK"s were one page and the whole personal-site surface was
down. **A status sweep would have printed five greens.** Assert the CONTENT TYPE the path owes (`application/json`
for a data file) and the size differing where documents differ; a 200 with the wrong type is a redirect into a
fallback, not a hit.

**And never repair a dead URL by repointing it at a host you have not proven serves that artifact.** Moving a
reference from a broken host to a working-looking one turns a *visible* failure into a **silent fake success** —
the consumer's own content check then runs against the fallback page and reports whatever the fallback happens
to contain. Measured: a script that read `…/DeFi/<tenant>.json` from a dead host was "fixed" by pointing it at the
live domain, which answered `200 text/html` with the homepage; the check was left comparing an HTML document
against a JSON expectation, in a deployment nobody would look at again. **Confirm with the exact request the
consumer makes** (`curl` the new URL, assert the content type and one known key) before the reference is changed —
and if the destination genuinely lacks the path, the honest state is "the destination must be built first", not a
redirect.

### 5e. When the proxy is host-level, establish whether the SERVING STACK still exists — restart vs reinstall

**The application code surviving is not evidence the service can be started.** Three facts decide the *shape*
of the fix, and none of them is visible from inside your container. Read them in one pass, because each one
changes the answer:

**① Does the service's unit exist at all?** Services started by systemd live in `/etc/systemd/system/` —
**outside any application data volume** — so a host container-recreate destroys the units while the code under
`/opt/...` survives intact. Ask before you propose a restart:

```bash
systemctl list-unit-files | grep -i <name>      # EMPTY => the units are gone
systemctl status <name> --no-pager | head -5    # "could not be found" => reinstall, not restart
```

**"Restart vs reinstall" is the first thing to establish.** Proposing a restart for a service whose unit no
longer exists spends the pass and reads as confident while being impossible. (Contrast the scope bogey: a
unit legitimately absent from *system* scope at `--user` scope — settle that from the process's own cgroup
before believing the negative.)

**② How does the proxy learn its routes? The mechanism decides whether your intended fix is possible at all.**

```bash
docker inspect <proxy-container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

- Mounts include a **config file or directory** (a file provider) → the proxy can route to an arbitrary
  host/port; add a config entry.
- Mounts are **only `/var/run/docker.sock`** (plus cert volumes) → the proxy discovers backends **exclusively as
  Docker containers, via labels**. **It cannot route to a host process on any port.** In that case "run it as a
  systemd service" produces a listener nothing can reach; the backend has to run as a **container carrying the
  same label set the working routers use**. Check the labels of a router that *does* work and mirror them.
  **Concrete recipe — label set, quoting traps, entrypoint override, and the ordered route cutover:
  `references/container-behind-traefik.md`.**

**③ The host's path to the code is not your container's path.** A unit file or `docker run` written with the
path you see from inside points at nothing:

```bash
docker inspect <app-container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

Use the **SOURCE** side. Measured: a path under `/opt/data/...` that resolves perfectly inside the container
**did not exist at all on the host**, so the obvious `ExecStart` would have failed at load.

> **Rule: before proposing any fix to a service behind a host-level proxy, answer three questions in one
> pass — does the unit exist, how does the proxy route, and what is the host path to the code? Each answer
> changes the shape of the fix, and getting any of them wrong produces a plan that cannot work.**

**The reframe this produces:** when the code survives and the serving stack does not, the task is not a
*repair* — it is **standing the service back up from scratch**. Say so plainly. "There is no restore to do,
only a fix" is a materially different (and better) status than the failed restart you were first asked about,
and naming it stops the next reader from re-running the same three dead-end restarts.

### 6 · The inverse direction — an exposure audit

The same vantage work answers the opposite question: **what of ours is reachable when it should not be?**
`ss` lists the real binds, `/proc/<pid>/{cmdline,cwd}` names the process, and an external fetcher proves
reachability — a probe from the host to its own public IP is hairpin traffic and proves nothing about the
internet. The trap: a port-wide deny can take a *working* front door down when something on the same host
dials that port, so containment must be scoped to the ingress interface. Full procedure, the interface-scoped
`iptables` rule with its persistence gap, and the decision table for the permanent fix (loopback bind vs
bridge migration, and why host networking is often a real constraint): `references/exposure-audit.md`.

## Pitfalls

- **A publish target that 404s EVERY path is not propagating — it is not serving.** A successful push proves the
  WRITE, never the hosting. Measured: a data pipeline generated a file, pushed it, then verified against
  `https://<org>.github.io/<path>` — which returned `404` for every path including the repo root. The API settled
  it in one call: the repo exists, is **private**, and `has_pages: false`. The verify branch that read the 404 as
  *"pushed but public JSON does not show it yet — CDN lag or a stale build"* had been reporting a permanently dead
  host as a transient, so the pipeline looked healthy for months. **Diagnose in this order, before touching
  anything:** (1) `GET /repos/<owner>/<repo>` and read `private` + `has_pages`; (2) `GET
  /repos/<owner>/<repo>/contents/<path>?ref=<branch>` — if the file is THERE, the write works and the fault is
  purely hosting; (3) only then probe the public URL. **Never let a 404 be classified as lag** — lag is a
  hypothesis that expires on its own; a disabled Pages config never does. Note also that **a private repo cannot
  serve Pages without a paid plan**, so "just enable it" may not be available.
- **Two publishes, one dead — name which one is real before repointing.** When the org site 404s and a
  **personal-account** site under the same project serves the same paths, you do not have an outage: you have two
  publish destinations and only one of them is live. Measured: the pipeline pushed to the org repo (Pages off)
  while the reachable site was an individual's `*.github.io` still serving a file from **98 days earlier**. Fixing
  the push target and fixing the reader's host are two different changes with different owners; say which host is
  authoritative before either is edited, or the repoint publishes into the void a second time.
- **Calling a restored service fixed because it answers.** Reachability and correctness are separate verdicts: a
  service whose config/data file lives outside the mount that survived starts cleanly, serves `200`, and
  advertises **nothing** (`services: 0`), because a bare `except FileNotFoundError` swallowed the miss. **Find the
  content counter and assert it is non-zero** — a health route returning `200` says nothing about whether the
  service has anything to serve. Full recipe: `references/container-behind-traefik.md` §6.
- **Trusting env-var-configured behaviour after a rebuild.** Configuration that comes from environment variables
  reverts to the app's **defaults**, and a default is frequently a degraded fallback (one rail, one provider, one
  region) that reports success. **Read the app's `os.getenv` calls and its `_DEFAULT_*` constants, then set what
  you need explicitly** — a silent fallback is indistinguishable from a correct configuration, which is why it
  survives review.
- **Reading `error code: 1003` as a DNS, TLS, or certificate fault.** It is an **edge-layer subrequest refusal**:
  the origin may be perfectly reachable and the Worker simply cannot call it by IP. Checking DNS and certs first
  burns the pass on layers that are fine.
- **Trusting a `/health` that a proxy answers itself.** The route may never touch a backend. Confirm the service
  name in the body, or probe a real service path, before calling a host healthy.
- **Calling a host up on a 200 from a path you chose.** A 200 proves nothing until you know the host is not a
  catch-all (step 5d). Prefer a path whose expected answer you can state in advance — for a paid API, `402`.
- **Probing the origin's ports from inside your own container.** `127.0.0.1` is *your* namespace; the host's
  listeners are invisible there and every port reads as closed. Reaching the host by its public IP works even
  when `127.0.0.1` does not — the two are not the same vantage, and only one of them is the internet's.
- **A host-level forward aimed at `127.0.0.1` cannot reach a bridged container.** The container's loopback is a
  DIFFERENT namespace from the host's, so a forward (`tailscale serve`, a socket proxy, an SSH `-L`) pointing at
  loopback proxies to the host's own loopback — where nothing is listening. **The forward reports success and
  lists the address it is serving on while every connection through it returns `000`.** A forward is a claim
  about where traffic GOES, never evidence anything is there. **Read the real bind from `/proc/net/tcp`, not
  from a probe or a config default** — `0100007F` = loopback only, `00000000` = all interfaces, `0A` = LISTEN
  (recipe, decoding table, and the socket-inode→PID lookup: `references/overlay-network-reachability.md`).
- **Connecting to `0.0.0.0:<port>` as a evidence of a wildcard bind.** On Linux that address resolves to
  loopback, so the probe *succeeds* whenever loopback does and proves nothing about the bind.
- **Reading a green `list-unit-files`-style absence as "the service is broken" rather than "the units are
  gone".** Units live outside the data volume and die with a host recreate while the code survives — so
  `could not be found` means REINSTALL, and the whole class of "we tried to restart it and nothing happened"
  reports traces back here. Establish restart-vs-reinstall before proposing a fix.
- **Proposing to run a backend as a host process when the proxy discovers routes by Docker label only.** If
  the proxy's only mount is the docker socket, it has no file provider and cannot see a host port at all. The
  fix that looks simplest (a systemd unit) produces a service nothing can route to — read the proxy's mounts
  before choosing the shape of the fix.
- **Assuming the container's paths exist on the host.** A unit or container written with the in-container path
  fails at load. Resolve the mount SOURCE side and write the fix against that.
- **Assuming a proxy flip fixes TLS.** It fixes *where the request goes*, not *whether Cloudflare trusts the
  origin*. Under `ssl mode: strict` an origin serving a fallback cert turns `000` into **`526`** and the host
  is exactly as down. Read the SSL mode in the same pass as the DNS records.
- **Reading `526` as a DNS or certificate-renewal problem.** `526` is specifically *Cloudflare could not
  validate the origin* — a Cloudflare↔origin trust question, i.e. a zone SSL-mode setting, not a record or an
  expiry.
- **Trusting a token-introspection endpoint's refusal as proof the token is dead.** Cloudflare's
  `/user/tokens/verify` answers `{"code":1000,"message":"Invalid API Token"}` for **scoped/account-owned
  tokens that work perfectly** on their scoped endpoints. Verify a credential by calling the resource it is
  meant to reach (list zones, list DNS records) — an introspection endpoint that does not apply to the token
  type reports a false negative, and acting on it means re-asking the user for a credential you already hold.
- **Reporting a fault as someone else's before checking your own egress IP.** The most expensive error in this
  class: it hands the user a blocker that is not theirs and moves the fix to a queue it was never in. Run the
  identity check in step 3 first.
- **Fixing only the hostname you were asked about.** When every DNS-only host presents the same fallback cert,
  the fault is a missing certificate/router for the whole set. Report the full set and fix it once.
- **Reading a fallback certificate as a certificate problem.** `TRAEFIK DEFAULT CERT` means no router matched
  the hostname — the same signal as an nginx default server. It is a routing symptom, and renewing the cert
  changes nothing.
- **Probing with `-k` and calling the endpoint up.** Bypassing verification hides exactly the defect you were
  called to find. `-k` is for reading the diagnostic detail, never for the verdict.
- **A `000` on a timeout sized below real latency reads as "dead peer" when it may only mean "slow".** Poll a
  second time before escalating a reachability verdict from one probe.
- **Treating a proxied sibling's 200 as proof the origin is healthy.** Cloudflare answers from the edge; a
  proxied 200 says nothing about the origin's certificate, router, or service. Test the origin path separately.
- **Reading `http=200` as "the endpoint is up" when an edge Worker (or any proxy) sits in front of it.** An
  edge function can answer **200 with an ERROR BODY** — measured: a Worker-fronted host returned
  `http=200` and a 21-byte body of `{"error":"Not found"}`. A status sweep that records only the code
  reported it as the single healthy surface in a list of dead ones. **A status code is not a health check
  when something programmable answers first** — capture and read the first bytes of the body in the same
  sweep, and judge by content, not code.
- **Assuming a missing hostname is a DNS-ONLY hostname.** Those are two different faults with two different
  fixes: a DNS-only record resolves to the origin and fails at TLS (`000`), while a hostname with **no record
  at all** returns **NXDOMAIN** and never reaches anything. Probe with a public resolver and read the status —
  `Status=0` with answers vs `Status=3` (NXDOMAIN) — rather than inferring from the HTTP code, since **both
  present as `http=000`** and the HTTP probe cannot tell you which you have.
  ```bash
  curl -s -H 'accept: application/dns-json' \
    'https://1.1.1.1/dns-query?name=api.example.com&type=A'   # Status:0=exists  Status:3=NXDOMAIN
  ```
  **Check for absent records in the same pass as the DNS-only set** — an enumeration that reads only the
  records that exist will silently omit the names that need creating, which are usually the most-referenced
  ones (they were missed precisely because nothing pointed at them).

- **Reading a record's VALUE as the host's behaviour.** A proxied record's `A`/`AAAA` is a **proxy anchor, not
  the address clients reach** — and when an edge Worker route exists for the pattern, the proxy never forwards
  to it at all. Measured: a hostname whose `A` record pointed at **`192.0.2.1` (RFC 5737 TEST-NET, an address
  that cannot host anything)** was declared dead — but it served `200` with a real 6,564-byte page, because a
  Worker route answered before the origin. **The record says where the proxy points; only a request says what
  answers.** One `curl -sI` settles it, and it cost a retraction to learn. The mirror error is equally cheap
  to avoid: confirm a *missing* name with a resolver (`getent hosts` / `socket.gethostbyname` → NXDOMAIN) rather
  than reporting it as "the host returned 000" — no record and a dead origin are different findings.

- **A RETIRED ROUTE MUST ANSWER `410 Gone`, NOT `404` — and never `402`.** `404` means *never existed*, so every
  catalogue and uptime prober that learned the path keeps re-asking forever and grades the host as broken;
  `410` means *it existed and is deliberately gone*, which is the only answer that tells a machine to stop.
  Measured: three retired paths drew ~400 requests a day from eight distinct monitors, every one of them a
  crawler rather than a buyer — the traffic was the *symptom of a 404*, not demand. And **never answer a paid route
  with `402` when you cannot serve it**: a challenge for a service with no backend is how a client pays for
  nothing. Answer `410` with a pointer to the live inventory, and keep the unknown-path branch at `404` so the
  two stay distinguishable.
- **Reading `401` as "the endpoint is down" — or `404` as "the host is fine".** The status code answers a
different question than reachability. On an auth-gated API, **`401` is the correct answer from a LIVE
service** — it resolved, it accepted the connection, and it refused an unauthenticated caller. `404` means the
host answered but has no route at that path. **`000` / a `gaierror` is the only code that means "dead"**, and it
has two causes that need different fixes (NXDOMAIN vs connection failure — probe DNS to tell them apart).
  A diagnosis that reports a 401 endpoint as "unreachable" sends someone to rebuild a service that is running.
- **Endorsing a replacement hostname you did not resolve.** Repair advice quoted from another issue or a doc page
  is a claim, not a fact: measured, three *different* supposedly-current facilitator hostnames were circulating
  in public threads and **two of them were NXDOMAIN**, one of them recommended as the fix inside the very issue
  about a dead hostname. Before repeating any host, run `getent hosts <host>` (or `socket.gethostbyname`) **and**
  one real request. A resolver miss is invisible to anyone reading the thread, and copying it forwards the outage.
  When several spellings of the same service exist, settle which one resolves **first**, then quote the full path.

- **Declaring a service "down" without asking whether anything is LISTENING.** `systemctl status <name>` answering
  *Unit not found* means only that systemd does not own it — a hand-started `nohup uvicorn … --port N` process is
  invisible to systemd while holding the port perfectly well. **Run `sudo ss -ltnp | grep -E ':(<port>|<peer ports>)'`
  first:** a listening entry with a live PID means the service is UP and misbehaving, which is a *different fix*
  from starting it. **The two error texts that settle it:** `ConnectionRefused` = nothing bound (start it);
  `TimeoutError` / `curl` exit `000` on a socket that `ss` shows as LISTEN = **bound but hung** (kill and restart
  it). Reporting the second as the first sends someone to "start" a process that is already running.
- **Blaming a cache for a failure the cache is only reporting.** An error string carrying `(cached)` invites the
  conclusion that a stale entry is the fault. **Read the TTL before believing it:** where a readiness probe caches
  for tens of seconds, `(cached)` describes the *note*, not the age of the fault, and the backend really is
  failing. Fix the dependency, not the cache.
- **Assuming a fleet of hand-started services is supervised.** Several backends answering on loopback ports, all
  started the same day with no unit and no container, means **a host reboot takes every one of them and nothing
  brings them back** — they then 503 one at a time as clients notice. **Map the whole set in one pass**
  (`ss -ltnp` for the listeners, `ps -o pid,lstart,cmd` for the start time) and write units with `Restart=always`
  rather than restarting the one that broke.

## Related

- `service-health-monitoring` — ongoing port/URL monitoring and alerting.
- `references/container-behind-traefik.md` — running a backend as a container behind a label-driven proxy:
  the label set, the quoting trap in rule syntax, the entrypoint override, the ordered edge cutover, and **why a
  restored service can come back reachable and EMPTY (config file outside the mount, env-var defaults)**.
- `references/overlay-network-reachability.md` — reaching a service across an **overlay network** (tailnet/VPN →
  host → container): the three layers to map before changing any, why a host forward to loopback cannot reach a
  bridged container, reading the real bind from `/proc/net/tcp`, choosing a bind that survives a daemon that is
  not up yet, and **why the overlay's DNS name beats its IP** (a re-registered node gets a new address).
- `x402-api-compliance` — gateway-specific discovery paths and the Cloudflare WAF / DNS-only SSL pitfall.
