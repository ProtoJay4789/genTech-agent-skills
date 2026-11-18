# Cloudflare Pages deployment — the working procedure, and the traps

**Use this when a page must go live on a `*.gentechlabs.net` hostname.** The apex (`gentechlabs.net`,
`www`) is a **Cloudflare Pages** project, not the VPS webroot — so the nginx/scp path in the parent skill
may write to an origin that is not serving the domain. **Determine the origin first** (parent skill,
"Pitfall — the public domain is served by Cloudflare Pages"), then use this procedure.

---

## 1 · Deploy — use `wrangler`, never hand-roll the API

```bash
cd "$SITE_DIR"                                  # index.html + the other pages, flat
export CLOUDFLARE_API_TOKEN=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token | tr -d '\n\r ')
export CLOUDFLARE_ACCOUNT_ID=<account_id>       # from GET /accounts
npx --yes wrangler@latest pages deploy . --project-name=<project> --branch=main --commit-dirty=true
```

**⚠️ Do NOT hand-roll the direct-upload API.** A hand-built multipart `POST` to
`/accounts/{acc}/pages/projects/{project}/deployments` — manifest as a literal form field, each file keyed
by its sha256 — **returns `success:true` with `environment=production` and then the project serves
HTTP 500 on every path.** The upload is malformed in a way the API does not report; the project simply
fails to serve. `wrangler` handles the manifest correctly and worked on the first attempt after the
hand-rolled version had failed repeatedly.

**`--branch=main` is what makes it a PRODUCTION deployment.** A custom domain serves production. A preview
deployment of identical assets will never appear on the domain, no matter how green the upload looked.

---

## 2 · New project + custom subdomain, end to end

All of this is doable from an agent session — the `cfat_` token carries **proven write scope** for Pages
projects and zone DNS. Do not send the user to the Cloudflare dashboard for it.

```bash
TOKEN=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token | tr -d '\n\r ')
ACC=<account_id>; ZONE=<zone_id>; PROJ=<project>; SUB=<sub>

# 1. create the project (production_branch is REQUIRED — a bare name is rejected)
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects" \
  --data '{"name":"'"$PROJ"'","production_branch":"main"}'

# 2. deploy with wrangler (section 1)

# 3. bind the custom domain
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/domains" \
  --data '{"name":"'"$SUB"'.gentechlabs.net"}'

# 4. create the DNS record — CNAME, PROXIED, pointing at the project's pages.dev
#    this is exactly how the apex is wired:  gentechlabs.net -> gentechlabs.pages.dev, proxied
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" \
  --data '{"type":"CNAME","name":"'"$SUB"'","content":"'"$PROJ"'.pages.dev","proxied":true,"ttl":1}'
```

**Proxied (orange) is mandatory for a Pages custom domain** — Cloudflare must terminate and route it. This
differs from an A record to a VPS origin, where grey/DNS-only is a legitimate choice.

---

## 3 · Verify — by CONTENT HASH, never by status code

**A Pages project catch-alls by default: a path that does not exist returns `200`.** So `curl -sI` proves
nothing here. Hash, and include a control that MUST differ:

```bash
LOCAL=$(sha256sum "$SITE_DIR/index.html" | cut -d' ' -f1)
SERVED=$(curl -sL "https://$SUB.gentechlabs.net/index.html" | sha256sum | cut -d' ' -f1)
[ "$LOCAL" = "$SERVED" ] && echo "MATCH" || echo "NOT SERVED"
# control: a path that cannot exist must return different bytes (it will still be HTTP 200)
curl -sL "https://$SUB.gentechlabs.net/does-not-exist-98765.html" | sha256sum
```

---

## 4 · The traps, in the order they bite

### A bound domain reporting `active` can still serve nothing
If the project returns 500 (or refuses) while the domain reads `active`, **DELETE the binding then re-POST
it**. That re-drives provisioning: the status goes to `initializing`, then `active` again — and this time it
serves. Measured: the first binding sat at `active` and served 500s; the re-bind fixed it.

### A proxied CNAME answers DNS queries as A/AAAA, never as CNAME
Querying `type=CNAME` against a proxied record returns an **empty answer** and looks like a missing record.
**Query `A` instead.** `Status=0` **with no Answer** on `type=A` is the real "not propagated" signal.

### A fresh subdomain may not resolve from THIS container while the edge serves it fine
The local resolver **negative-cached the NXDOMAIN** from before the record existed, and that cache outlives
the record by its TTL. **Do not conclude the deploy failed.** Isolate DNS from serving by addressing the
edge directly:

```bash
IP=$(curl -s -H 'accept: application/dns-json' \
  'https://cloudflare-dns.com/dns-query?name=<sub>.gentechlabs.net&type=A' | jq -r '.Answer[0].data')
curl -sL --resolve <sub>.gentechlabs.net:443:$IP https://<sub>.gentechlabs.net/index.html | sha256sum
```

An edge-IP fetch returning the right bytes proves **the deploy, the binding, and the edge are all correct,
and only name resolution is pending.** Report it as exactly that — *"live at `<project>.pages.dev`, verified
by content; the custom subdomain is routing correctly and negative-cached locally"* — never as "not live".

### The `.pages.dev` URL 308-redirects once a custom domain is attached
A `308` with `location: /` is **not** a failure — it is the project redirecting to its custom domain. Follow
it. And note that until the custom domain resolves, that redirect leads somewhere unreachable, so the
project can look entirely broken when it is not.

### Preserve the live copy before ANY redeploy
**A Pages deploy REPLACES the site contents.** If the currently-served page's source is not in a repo you
hold, **the live URL is the only copy**:
```bash
curl -s https://gentechlabs.net/ -o "$BACKUP_DIR/index.html" && sha256sum "$BACKUP_DIR/index.html"
```
**Then include that preserved file in the new deployment**, or a redeploy blanks the front door. Measured:
the apex landing page had **no source on disk** — one stale deployment was the only copy in existence.

### A pre-existing `A` record on the name silently BEATS the Pages binding

Attaching the custom domain and deploying successfully does **not** mean the name reaches Pages. **If the
name already holds an `A` record pointing at the VPS origin, that record keeps answering** — the hostname
resolves, looks configured, and serves the *origin's* 404 while the Pages project behind it is perfectly
healthy. Measured: `hub.gentechlabs.net` held `A → 2.24.195.196` (proxied) and served the same byte-identical
404 as the rest of the hollow-hostname set, while a freshly-deployed `gentech-hub.pages.dev` was serving the
real hub the whole time.

**Diagnose the record TYPE before deploying, not after:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?name=$SUB.gentechlabs.net" \
  | jq -r '.result[] | "\(.type) \(.name) -> \(.content) proxied=\(.proxied)"'
```
A `CNAME → <project>.pages.dev` is correct. An `A` at the VPS IP is the trap.

**Fix = REPLACE, and the order matters — delete first, then create.** A CNAME cannot coexist with another
record type on the same name, so creating it without removing the `A` conflicts or fails:
```bash
# 1. delete the stale A (id from the query above)
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records/$AID"
# 2. create the proxied CNAME -> <project>.pages.dev   (section 2, step 4)
# 3. READ IT BACK — a write that returned success is not a write that landed
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?name=$SUB.gentechlabs.net" \
  | jq -r '.result[] | "\(.type) \(.name) -> \(.content) proxied=\(.proxied)"'
```
**The read-back is the verification** — it reports the type that is actually live, not the one you meant to
create. Then re-run the content-hash check (section 3) against the custom name; the name resolving is not
the same event as the name serving your bytes.

---

## 5 · Auditing an existing zone — what to check before adding anything

```bash
# the authoritative map: what points where
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?per_page=100" \
  | jq -r '.result[] | "\(.type) \(.name) -> \(.content) proxied=\(.proxied)"'
```

**A DNS record is a CLAIM that a service exists.** A zone accumulates records pointing at origins that no
longer answer — every one advertises something that isn't there.

- **Hash the bodies across all hostnames before drawing per-host conclusions.** Measured: **18 hostnames
  returned byte-identical `404 page not found` (19 bytes, same hash)** — that is **ONE** answer being
  served for 18 names, not 18 broken services. A count of "N broken" derived from N identical responses is
  wrong by an order of magnitude.
- **A 404 at `/` is NOT evidence a service is broken.** An API worker with explicit routes correctly 404s at
the root while serving real payloads at `/health` and `/.well-known/x402`. **Probe the path the service
  actually claims.**
- **A record pointing at a reserved documentation address (e.g. `192.0.2.1`) is worse than a dead one** — it
  looks configured. Grep the zone for reserved ranges.
- **Never bulk-delete records to "clean up".** The record is often the only surviving pointer to where the
  content lived. **Diagnose the origin first** (does the host still hold the files?), then **reroute** if the
  content survives or **erase** if it is truly gone.

---

## 6 · `_headers` and `_redirects` are DEPLOYED CONFIG — a partial deploy silently deletes them

Two special files are **consumed by Pages, never served as routes**:

- `_headers` — response headers applied per path (`X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, CSP, `Access-Control-Allow-Origin`).
- `_redirects` — redirect and rewrite rules.

**A deployment replaces the ENTIRE project contents.** So deploying only `index.html` **removes `_headers`**,
and the site keeps serving pages with **no security headers at all** — no error, no warning, nothing in the
response that looks wrong. Measured: the header set was present before a one-file deploy and absent after it.

**You cannot detect these files by probing for them.** `GET /_headers` is not a route, so on a catch-all
project it returns the **homepage with 200** — identical to the probe for any missing path. **The probe
proves nothing.** The only reliable tells are:

1. **Read the response headers BEFORE you deploy** and treat non-default ones as evidence of a `_headers`
   file:
   ```bash
   curl -sI https://<domain>/ | tr -d '\r' | sort > /tmp/h_before.txt
   ```
   `X-Frame-Options` / `X-XSS-Protection` / a `Referrer-Policy` are **not** Pages defaults — their presence
   means a config file exists.
2. **Ship a reconstructed `_headers` in the same deployment** that reproduces the observed set, then re-read
   the headers afterwards and diff against `/tmp/h_before.txt`.

```
/*
  X-Frame-Options: SAMEORIGIN
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: same-origin
```

**`GET /deployments/{id}` returns a `files` map of exactly what the deployment recorded** — the fastest way
to see what a deploy did or did not include:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/deployments" | jq -r '.result[0].id'
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/deployments/$DEP" | jq '.result.files'
```
Note `_headers` does **not** appear in `files` (it is config, not a served asset) — so a `files` map showing
only `/index.html` is **not** proof that `_headers` is absent, and vice versa.

---

## 7 · Rollback — the recovery move when a deploy breaks production

**A broken deploy is not a debugging session on a live site.** Roll back first, diagnose second.

```bash
# 1. list deployments, newest first — identify the last KNOWN-GOOD id
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/deployments" \
  | jq -r '.result[] | "\(.id) \(.created_on) \(.latest_stage.status)"'

# 2. roll back to it
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/deployments/$GOOD_ID/rollback"

# 3. verify by status AND content before doing anything else
curl -sSL -o /tmp/live.html -w 'http=%{http_code} bytes=%{size_download}\n' https://<domain>/
```

Measured: rollback restored a **500-ing production site to 200 in about 4 seconds**, twice in one session.
`latest_stage.status=success` on the broken deployment is **not** evidence it serves — status describes the
upload pipeline, not the runtime.

---

## 8 · Kill the catch-all: ship a `404.html`

A Pages project answers **every unknown path with `200` and the homepage**, which makes every link check
meaningless and hides broken links from visitors and from your own probes.

**Adding a `404.html` at the deployment root makes unknown paths return a real `404` with that page.** Pages
picks it up automatically — no config, no route.

```bash
# 1. write 404.html (plain HTML, styled to match the site) into the deploy directory
# 2. deploy it WITH the site — never alone
npx --yes wrangler pages deploy . --project-name=<project> --branch=main --commit-dirty=true
# 3. prove the catch-all is gone: the fake path must now differ in BOTH status and body
curl -sL -o /dev/null -w '%{http_code}\n' https://<domain>/does-not-exist-98765   # expect 404
curl -sL -o /dev/null -w '%{http_code}\n' https://<domain>/                        # expect 200
```

**Do this before trusting any link audit.** On a catch-all host, `200` on every URL is the default answer and
carries no information; once `404.html` exists, a `200` starts meaning something again.

---

## 9 · Why this was invisible for months

A deploy skill verified with `curl -sI "https://<domain>/{page}.html"` → *"should return HTTP/2 200"*.
**Measured: a path that does not exist returns `HTTP/2 200`.** A successful deploy and a failed one were
indistinguishable, so the apex served one stale page for four months and neither the deploy step nor its
verification could tell. **A check that cannot go red is not a check** — and on a catch-all host, a status
code is not a verification.
