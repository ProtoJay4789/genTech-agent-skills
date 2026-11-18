---
name: web-deployment
description: Deploy HTML dashboards, demo suites, and subdomain pages to the VPS — including nginx config, portfolio linking, and DNS setup
category: gentech-ops
version: 1.0.0
author: Gentech
tags: [deployment, vps, nginx, subdomain, portfolio, demo, dns]
trigger: "When shipping a new dashboard, demo page, or product hub that needs to go live on gentechlabs.net. When adding a new subdomain. When updating the portfolio site."
---

# Web Deployment

## Purpose
Deploy new HTML pages, dashboards, and demo suites to the VPS, set up subdomains, and link everything from the portfolio site. One workflow for getting products live.

## Site Routing Rule (Jordan-approved Aug 16, 2026) — THE canonical routing decision

There are THREE public surfaces. Route every piece of content to exactly ONE of them, like the other routing layers (model routing, etc.). Never let them drift into overlap.

| Content type | Goes to |
|---|---|
| Company narrative, problems, roadmap, AAE stack, API services, case studies | **Main site** `gentechlabs.net` (`index.html`) |
| Personal work history, career, skills, experience, open-source PRs, connect | **Portfolio** `portfolio.gentechlabs.net` + `gentechlabs.net/portfolio/` (same `/var/www/portfolio/index.html`) |
| Live, working, touchable artifacts (demos, videos, endpoints, dashboards) | **Demo site** `gentechlabs.net/demo.html` |
| Internal ops (Mess Hall, vault health, considerations, cron counts, agent online-status, 24/7 ops detail) | **Vault only — NEVER public** |
| Token/support/ecosystem promotion (AAE Token, $TREASURY) | **Not on any public surface** |

**The rule in one line:** *Main site = the story. Portfolio = the person. Demo site = the proof. Internal = never public.*

**Portfolio audit performed Aug 16, 2026** — stripped the portfolio down to: header, stats (Repos/PRs Shipped/API Endpoints/Marketplaces — NOT cron jobs), Two-Agent Ops (framed as differentiator, not internal detail), About, The GenTech Journey, Open Source, Tech Stack, Connect, footer. Removed: V4 intro banner, Core Projects (→ demo/main), AAE Stack (dupe of main), 24/7 Agent Ops, API Services, Hackathons (stale), Agent Stack, Mess Hall, Support Ecosystem (token), One-Liner Deploy. Backup at `index.html.pre-audit-backup`.

**Pitfall — the portfolio is served at TWO URLs:** `portfolio.gentechlabs.net` (own nginx server block) AND `gentechlabs.net/portfolio/` (alias to the same `/var/www/portfolio/index.html`). Both point at the one file. Edit that file and both update. `/root/portfolio/` is a SEPARATE, older repo that is NOT the deployed source — do not confuse them.

## A page describing a GENERATED system must be GENERATED from that system

**A marketing page and the API it markets drift apart silently, and the page always drifts in the
flattering direction.** Measured: the public site was last deployed **four months earlier** and advertised
**16 endpoints across three product lines** — Games, Movies, Intel — while the API served **9
crypto/DeFi services**. **All three example routes on the page returned `404`.** Prices were 5–10× stale
and included a figure the API had never charged.

**Nothing in the system flagged it.** The page loaded, rendered, and looked maintained. A developer who
read it and tried the API hit a dead end, and the failure was attributed to the market rather than to
the front door.

**The rule: when a page lists services, prices, endpoints, or counts that a machine already knows, build
the page FROM that machine.**

- **Fetch the machine-readable inventory at build time** (`/.well-known/<manifest>`, an OpenAPI doc, a
  registry JSON) and render the list from it. Never hand-type a price or a count that exists in a file.
- **Render the WITHHELD set too, with the reason the system itself gives.** An honest *"not available
  right now — <reason>"* block is what makes the page accurate; silently omitting the gaps is what makes
  it a lie by the next release.
- **Take the code example from a real route.** A hero snippet pointing at a path that does not exist is
  the single most expensive sentence on a developer-facing page, because it converts interest into a 404.
- **Regenerate on every deploy** so the page cannot be stale by construction. A generator that runs is
  worth more than a review process that is supposed to run.
- **Cross-check the page against the inventory as a scheduled check** (the same surface-agreement probe
  that compares your other published surfaces). If the site is not in that check, it is the surface that
  will be wrong.

**⚠️ Preserve the live page before regenerating.** When a Pages project has no git source, the live URL is
the only copy: `curl -s https://<domain>/ -o backup/index.html` and hash it. Then edit the preserved file
and redeploy it — a regenerate-from-scratch deploy blanks anything the generator does not know about.

**Symptom to watch for:** *"we have traffic but no customers."* Before blaming the market, open your own
homepage and call the example it prints. **A front door that 404s its own instructions explains
non-conversion without any market theory at all.**

**Reference implementation:** `profiles/<seat>/scripts/site-rebuild.py` — fetches the live manifest, rebuilds
the services tab (cards, prices, real route templates, withheld-with-reason block), rewrites the hero example
to a route that exists, and supports `--dry-run`. Read it before writing another generator; the pattern
(preserve live page → regenerate one section by locating its delimiter → verify every claim against the
manifest → deploy via wrangler) transfers to any page that lists machine-known facts.

## Deployment Workflow

### Step 0: Determine the ORIGIN before choosing a workflow

The steps below describe the **nginx/VPS** path. **Do not assume it is the path that serves your domain.**
Measured: `gentechlabs.net` and `www` are custom domains on a **Cloudflare Pages** project, and **18 zone
records pointing at the VPS origin all returned one identical 404** — the nginx path was writing to a server
that was not serving those names.

```bash
# one query decides which workflow you are in
token=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token)
curl -s -H "Authorization: Bearer $token" https://api.cloudflare.com/client/v4/accounts \
  | jq -r '.result[0].id' > /tmp/acc
curl -s -H "Authorization: Bearer $token" \
  "https://api.cloudflare.com/client/v4/accounts/$(cat /tmp/acc)/pages/projects" \
  | jq -r '.result[] | "\(.name) domains=\(.domains) last=\(.latest_deployment.created_on)"'
```

- **The name is a Pages custom domain** → use **`references/cloudflare-pages-deployment.md`**. Skip Steps 1–2.
- **The name resolves to the VPS origin and nginx holds the vhost** → Steps 1–2 below.
- **Unsure** → curl the name and hash the body (Step 3). The hash tells you whether anything you wrote is
  actually being served; the DNS record alone does not.

### Step 1: Build the HTML Page — IN THE REPO, not the webroot
Build in the canonical repo (`/root/repos/gentechlabs.github.io/{path}`), commit + push, then `cp` to `/var/www/gentechlabs/` and `chown www-data:www-data`. **Never create pages only in the webroot** — webroot-only pages are orphans: invisible to git, lost on VPS rebuild, and one careless `cp` from being clobbered. Proven failure Sep 4, 2026: vanito.html's 87KB dashboard was overwritten from a wrong-source file that shared the name, and the original was unrecoverable; the sweep then found 11 more orphan pages (demo, portfolio, jordan, concept*, hub-backup, hub-launcher). Legacy orphans being fixed in place must be codified into the repo in the same pass. Use the dark theme (bg: #0a0e17, text: #e2e8f0, accent: #60a5fa) to match the existing suite.

### Step 2: Deploy to VPS
```bash
scp /var/www/gentechlabs/{name}.html root@2.24.195.196:/var/www/gentechlabs/
ssh root@2.24.195.196 "chown www-data:www-data /var/www/gentechlabs/{name}.html && chmod 644 /var/www/gentechlabs/{name}.html"
```

### Step 3: Verify by CONTENT — a status code proves nothing on this domain

```bash
# 1. Did the bytes change? Compare a hash, not a status code.
curl -s "https://gentechlabs.net/{name}.html" | sha256sum
sha256sum "$LOCAL_COPY_OF_{name}.html"        # the two hashes must MATCH

# 2. Sanity floor: the same fetch of a path that CANNOT exist must DIFFER.
curl -s "https://gentechlabs.net/{name}-does-not-exist-xyz.html" | sha256sum
```

**⚠️ `curl -sI` returning `HTTP/2 200` does NOT mean your page is live.** Measured on this host: **every**
path on `gentechlabs.net` — including a deliberately fake one — returns `HTTP/2 200` with byte-identical
content. A failed deploy and a successful one are indistinguishable by status code. **Only a content hash
distinguishes them.** If the fake-path hash equals your page's hash, **your page is not being served.**

**⚠️ Follow redirects and print the status before you hash.** Cloudflare Pages serves **clean URLs**: a
request for `/<name>.html` answers **`308` → `/<name>`**. `curl -s` without `-L` therefore returns **zero
bytes**, and the sha256 of an empty body is `e3b0c442…` — the same value for every path everywhere. A digest
comparison run that way either "matches" nothing or reads as *the page is empty*, and both look like a
finding about the deployment.

```bash
curl -sSL -o /tmp/live.html -w 'http=%{http_code} bytes=%{size_download} final=%{url_effective}\n' "$URL"
sha256sum /tmp/live.html
grep -oE '<title>[^<]*</title>' /tmp/live.html     # is this the page, or a catch-all?
```

Assert `http_code=200` **and** that `bytes` is the right order of magnitude before comparing hashes — a
`308`/`301` on that line means you are still holding a redirect, not the artifact. **A matched digest on an
empty body is the one comparison that fails for the wrong reason**, so the body check comes with it.

**This is the general rule, not a one-off:** *a check that cannot go red is not a check.* Any deploy
verification must include one input that SHOULD fail and be confirmed to fail, or it is a paragraph.

**Deploying a sub-page into a subdirectory of the hub (PROVEN Aug 2026).**
The gaming tracker pages (POE2, Helldivers 2) live in `Gaming/` under the hub root,
not as top-level `{name}.html`. nginx `location / { root /var/www/gentechlabs; }`
serves any subpath, so a file at `/var/www/gentechlabs/Gaming/helldivers2.html`
is live at `https://gentechlabs.net/Gaming/helldivers2.html`. Flow:
1. Build the HTML + a sibling `.json` data file in the canonical repo
   (`/root/repos/gentechlabs.github.io/<path>`).
2. `mkdir -p /var/www/gentechlabs/Gaming` and `cp` both files into it
   (no `chown` needed if you write as root and the site is read-only static).
3. Verify **by content, not by status** (see Step 3 above — a status code proves nothing
   on this domain, including for the sibling `.json`):
   - the page's sha256 must MATCH the local file's;
   - the `.json` must **parse as JSON** — fetch it and run `jq -e . >/dev/null`. On a
     catch-all host a missing `.json` still returns `HTTP 200` carrying the HTML
     fallback, so the page renders "could not load build data" while every status
     check is green. **Parsing is the test; 200 is not.**
4. Wire it into the live hub's relevant tab: add an `<a class="link-card">` to the
   `link-grid` in `/var/www/gentechlabs/hub.html`, then `curl` the hub and `grep`
   for the new label to confirm it's live.

**Pitfall — a freshly-written HTML file returns HTTP 403 (nginx can't read it).**
When you create a page with `write_file` directly into `/var/www/gentechlabs/`, the file lands
with mode `600` (owner root only). nginx runs as `www-data`, so it cannot read the file and
returns **403 Forbidden** even though the file exists and the path is correct. This is distinct
from a 404 (wrong path) or a stale-cache issue. Fix:
```bash
chmod 644 /var/www/gentechlabs/{name}.html
# then verify
curl -s -o /dev/null -w "%{http_code}" "https://gentechlabs.net/{name}.html"   # expect 200
```
**Confirmed Aug 5, 2026:** `treasury-demo.html` returned 403 after `write_file`; `chmod 644`
flipped it to 200. Always `chmod 644` any file you write into the web root (the `scp`+`chown`
deploy path in Step 2 already does this — the gap is when you `write_file` directly). Check
permissions FIRST when a new page 403s: `ls -la /var/www/gentechlabs/{name}.html` — if it shows
`-rw-------`, that's the cause, not nginx config or Cloudflare.

**Pitfall — the public domain is served by Cloudflare Pages, NOT by the nginx webroot. Confirm which surface answers before trusting either.**
`gentechlabs.net` and `www.gentechlabs.net` are **custom domains on a Cloudflare Pages project named
`gentechlabs`** (subdomain `gentechlabs.pages.dev`), marked `verified=active`. The nginx path below
(`scp` → `/var/www/gentechlabs/`) writes to the VPS — **which may or may not be the origin actually serving
the domain.** Determine it before deploying:
```bash
# List the Pages projects and their custom domains (read-only):
token=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token)
acc=$(curl -s -H "Authorization: Bearer $token" https://api.cloudflare.com/client/v4/accounts | jq -r '.result[0].id')
curl -s -H "Authorization: Bearer $token" "https://api.cloudflare.com/client/v4/accounts/$acc/pages/projects" | jq -r '.result[] | "\(.name) \(.domains) last=\(.latest_deployment.created_on)"'
```
**A Pages project whose `latest_deployment.created_on` is far in the past is serving a stale snapshot** —
anything you add by another route is invisible to the public domain, no matter how green the "deploy" looked.

**⚠️ Before ANY Pages redeploy, preserve the live copy first.** A Pages deploy REPLACES the site contents.
If the deployed page's source is not in a repo you hold, the live URL is the ONLY copy:
```bash
curl -s https://gentechlabs.net/ -o "$BACKUP_DIR/index.html" && sha256sum "$BACKUP_DIR/index.html"
```
**Then include that preserved file in the new deployment** — otherwise a redeploy blanks the front door.

Same trap on the old advice "treat the VPS nginx copy as the source of truth for *is it live*": that is
only true if the VPS is the origin. **Verify the origin, then trust it.**

### Deploying to Cloudflare Pages

**Use `npx wrangler pages deploy`. Do NOT hand-roll the direct-upload API** — a hand-built multipart POST
reports `success` and `environment=production` and then the project **serves HTTP 500 on every path**.
**A bound domain reporting `active` can still serve nothing** (delete + re-POST the binding to re-drive it),
and **a fresh subdomain may not resolve from this container while the edge serves it fine** (negative-cached
NXDOMAIN — verify via `--resolve` to the edge IP and report only what that proves).

```bash
export CLOUDFLARE_API_TOKEN=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token | tr -d '\n\r ')
export CLOUDFLARE_ACCOUNT_ID=<account_id>
cd "$SITE_DIR" && npx --yes wrangler@latest pages deploy . \
  --project-name=<project> --branch=main --commit-dirty=true     # --branch=main == PRODUCTION
```

**A Pages project catch-alls — a missing path returns 200 — so the content-hash check in Step 3 is the only
test with any power.**

**⚠️ A deploy REPLACES the whole project, so deploying only `index.html` deletes `_headers` and
`_redirects` — the security headers vanish with no error.** Read the response headers before deploying
(`curl -sI`), reconstruct `_headers` if non-default ones are present, and ship it in the same deploy; then
diff the headers afterwards. **You cannot probe for these files** — `/_headers` is config, not a route, so on
a catch-all project it returns the homepage with 200 like any missing path.

**Ship a `404.html` at the deployment root to end the catch-all.** Pages serves it automatically for unknown
paths, turning a meaningless `200`-on-everything host into one where a `200` means something — do this before
trusting any link audit. **And when a deploy breaks production, roll back first and diagnose second:**
`POST /accounts/{acc}/pages/projects/{proj}/deployments/{known_good_id}/rollback` restored a 500-ing site to
200 in seconds. A broken deployment's `latest_stage.status=success` describes the upload, not the runtime.

### When no source exists, recover it from the catch-all — the deployment's own file map is the index

**A direct-upload Pages project with no repo has exactly one copy of its source: the live responses.** The same
catch-all that makes link checks useless is what makes recovery possible, because every path still returns its
own real file.

Enumerate the true paths first — do not guess them. The deployment object carries a **`files` map keyed by
absolute path**, and that map is the manifest of what it **uploaded**:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/$PROJ/deployments/$DEP" \
  | jq -r '.result.files | keys[]'
```
Then fetch each key from a hostname the project owns and hash it:

```bash
for p in $(curl -s ... | jq -r '.result.files | keys[]'); do
  mkdir -p "src/$(dirname \"$p\")" && curl -sSL "https://$HOST$p" -o "src/$p"
done
sha256sum src/*   # record it — this is the only identity these recovered files have
```

- **Recover the siblings, not just `index.html`.** A hub's tabs and their `.json` data files are separate paths
  in the same map; a project restored with only its front page renders a page of dead buttons.
- **⚠️ The map omits config files — a project showing only `/index.html` can still carry `_headers` and
  `_redirects`.** They are consumed by the platform, never served, so they never appear as paths. Measured: a
  deployment listed exactly one file while its responses carried four non-default security headers. **Never
  conclude "that is everything" from the map** — read the live response headers before rebuilding from it, or
  the recovery silently drops the security policy.
- **Verify the recovery before trusting it**: the map's values are content digests, so a re-fetch that matches
  its recorded digest is byte-exact. Use the digest as a comparison, never as a spec — the algorithm varies by
  uploader (`wrangler` and the raw API do not agree).
- **Then deploy FROM the recovered directory and keep it as the archive.** One directory that is both the
  source and the deploy input is what stops "there is no source" recurring.

### Verify response headers case-insensitively — a dict lookup on the wrong case reads as "deleted"

HTTP header names are case-insensitive and servers send them in whatever case they like. Measured: a deploy was
believed to have deleted four security headers because `dict(resp.headers).get("X-Frame-Options")` returned
`None`, while `curl -sI` showed the header present the entire time — and the "repair" deploy that followed was
unnecessary work against a file that had never been lost.

```bash
curl -sI -A '<ua>' "https://$HOST/" | tr -d '\r' \
  | grep -iE 'x-frame-options|x-content-type-options|referrer-policy|x-xss-protection'
```

- **Lowercase the keys before asserting absence** (`{k.lower(): v for k, v in resp.headers.items()}`), or read
  them with a case-insensitive grep. A case-sensitive dict is an instrument that cannot report the header.
- **Read headers off the method you actually serve with** — `HEAD` and `GET` can differ when a layer adds
  headers to only one.
- **"The header is gone" is a claim about a deletion.** Prove it with an instrument that cannot miss by case
  before telling anyone you removed something.

### Parsing a page for facts — anchor on the BLOCK, then hand-verify one case

**Proximity is not association.** Measured: a price audit read each `<h3>` and took the first `$x` within the
following characters — but the price badge sits **before** the heading inside each `<article class="card">`, so
every price was paired with the **next** card's name. That produced a specific, confident, entirely false report
that five prices were wrong and two were swapped, on a page where all nine were correct.

```python
# anchor on the repeating block, then read fields INSIDE it
for blk in re.findall(r'<article class="card">(.*?)</article>', html, re.S):
    name  = re.search(r'<h3>([^<]+)</h3>', blk)
    price = re.search(r'class="price">\$([\d.]+)', blk)
```

- **Extract per block, never per heading with a sliding window.** Field order inside a card is not stable across
  sections of the same page, so any window-based rule silently borrows its neighbour's value.
- **Print one block's raw HTML and check it by eye before reporting any number derived from the parse.** A
  single manual read catches the off-by-one that no amount of whole-parser auditing will.
- **A uniformly-wrong result is a parser bug, not a finding.** Every value differing is the signature of
  misfielded data; a real divergence is scattered. Treat "all of them are wrong" as evidence about the
  instrument first.
- **The same trap lives in the key map, not only the HTML.** A display name mapped to the wrong manifest key
  produces mismatches on exactly the rows that share a name. Verify the map against the source's own keys
  before comparing any values.

**Full procedure — project creation, the custom-domain + proxied-CNAME steps, the audit queries, and every
trap in the order it bites — is in `references/cloudflare-pages-deployment.md`.**


**Pitfall — pick a clean local test port.** Port 8095 is occupied by another
service that responds `{"detail":"Not Found"}` (a FastAPI-style responder), which
looks like a broken deploy when you curl it. Use an uncommon port (e.g. 8137) and
bind `127.0.0.1` for `python3 -m http.server` test servers, and confirm the server
actually started (its own `OSError: [Errno 98] Address already in use` traceback
tells you the port was taken).

**Pitfall — headless Chrome has a viewport floor; sub-500px screenshots may be crops, not true renders.**
When doing responsive visual QA with `google-chrome --headless --screenshot`, a requested
window width below ~500px can still produce a screenshot whose content was laid out at
~500px and then cropped to the requested width. This makes the page look like it has
right-edge overflow when it does not. Always add a control test (a tiny page that reports
its own `window.innerWidth`) to confirm the instrument is honest before chasing clipping
bugs. If the control shows `innerWidth = 500` for a 390px screenshot, the render floor is
cropping the image — the page itself is fine.

**Pitfall — verify CONTENT, not just HTTP 200 (Cloudflare stale cache).**
Aug 2, 2026: a replaced PDF kept serving the OLD file through Cloudflare
(`cf-cache-status: HIT`) even after the file on disk was correct. curl showed
200, but the bytes were the previous version — the user saw a 404 / wrong
content while the agent saw "200 OK". For binary/PDF/HTML replacements:
1. Download and check actual content: `pdftotext served.pdf - | grep -i 'expected title'`
   or `grep -oE '<title>[^<]*</title>'` on the served page.
2. Cache-buster forces Cloudflare revalidation: append `?v=20260802b` —
   if the busted URL shows new content, the edge was holding the old copy.
3. CF cache purge needs a token with **Cache Purge** permission — a zone-read
   token verifies (`/user/tokens/verify` → active) but returns 10000
   "Authentication error" on `POST /zones/{id}/purge_cache`. Don't fight it;
   use the cache-buster or serve the artifact from GitHub raw instead.
4. **Bulletproof fallback: host the artifact in the repo and link the raw URL**
   (`https://raw.githubusercontent.com/OWNER/REPO/main/path`) — no Cloudflare
   in the path, cannot serve stale content. Preferred for submission-critical
   files (hackathon deck PDFs, etc.).
5. Also verify the LOCAL disk copy matches what nginx serves: `curl -H "Host:
   gentechlabs.net" http://127.0.0.1/path` — if local is new but public is
   old, it's the CDN, not your deploy.

**Pitfall — platform extraction failures still have partial-data paths (Aug 30).**
A Facebook reel link failed full extraction (login wall), but `r.jina.ai` returned real
partial metadata (title, view counts, page info). Pattern: when a platform blocks full
extraction, take whatever partial data the probe DID return, then reconstruct the *topic*
via web research and deliver the substance — research the subject the link points at, not
just the link. "Cannot extract" is only the final answer when partial-data + topic
reconstruction both come up empty.

**Pitfall — same-name file from an old project.** Before linking a file that
"already exists" in the web root, check WHAT it is: `file {name}.pdf`,
`pdftotext` it, check the `<title>`. Aug 2, 2026: `arc-presentation.pdf` was
actually the previous TokenRiskOracle (Somnia) deck sitting in the directory
from an earlier hackathon — nearly got submitted to the wrong programme.
`ls -la` timestamps tell the story (old file predates the new HTML).

### Step 4: Set Up Subdomain (Optional)
If the page deserves its own subdomain (e.g., `yield.gentechlabs.net`, `arb.gentechlabs.net`, `demo.gentechlabs.net`):

Create nginx config on VPS:
```bash
ssh root@2.24.195.196 "cat > /etc/nginx/sites-enabled/{subdomain} << 'EOF'
server {
    listen 80;
    server_name {subdomain}.gentechlabs.net;
    root /var/www/gentechlabs;
    index {name}.html;
    location / { try_files \$uri \$uri/ =404; }
}
EOF
nginx -t && nginx -s reload"
```

Then add a DNS record in Cloudflare. **⚠️ CORRECTED — this IS manageable from an agent session.** The
`cfat_` token at `~/.hermes/profiles/gentech/secrets/cloudflare.token` has **proven write scope** for both
Pages projects and zone DNS records (a CNAME was created and served successfully). Do not tell the user to
log in to cloudflare.com for this; do it and verify it:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records" \
  --data '{"type":"A","name":"<sub>","content":"2.24.195.196","proxied":true,"ttl":1}'
```
**Proxied (orange) vs DNS-only (grey) is not a preference — it depends on what answers.** A record for a
**Cloudflare Pages** project **must be proxied** (Cloudflare has to terminate and route it). An A record to
the VPS origin can be either; grey is fine for a demo page, orange if you want Cloudflare's TLS and cache.

**Pitfall — a reservoir of "configured" records that serve nothing.** Before adding a new subdomain, audit
what already exists rather than assuming the name is free or that its neighbours work:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?per_page=100" | jq -r '.result[] | "\(.type) \(.name) -> \(.content) proxied=\(.proxied)"'
```
**A DNS record is a CLAIM that a service exists.** A zone can accumulate dozens of records pointing at an
origin that no longer answers — every one of them advertises something that isn't there. **Deleting a record
is destructive: the record is often the only surviving pointer to where the content was.** Diagnose the
origin first (does the host still hold the files?), then **reroute** if the content survives or **erase** if
it is truly gone. **Never bulk-delete records to "clean up" without checking the origin.**

**Pitfall — many hostnames answering byte-identically is ONE answer, not many results.** If N subdomains all
return the same status and the same body hash, they are not N broken services — they are N names hitting a
single default handler. Hash the bodies before drawing any per-host conclusion:
```bash
for h in $(...); do echo "$h $(curl -sL https://$h.gentechlabs.net/ | sha256sum | cut -c1-12)"; done | sort -k2
```
**And a 404 at `/` is NOT evidence a service is broken.** An API worker with explicit routes correctly 404s
at the root while serving real payloads at `/health` and `/.well-known/x402`. **Probe the path the service
actually claims, not `/`.**

**⚠️ The token file at `~/.hermes/profiles/gentech/secrets/cloudflare.token` is not dead — do not declare it
so.** It is a **`cfat_` (Account) API token**, and Account tokens return `401 Invalid API Token` at
`/user/tokens/verify`, which is a **false negative, not a bad credential.** Read the prefix before judging:

| prefix | type | correct verify endpoint |
|---|---|---|
| `cfat_` | Account API token | `/accounts/{account_id}/tokens/verify` (never `/user/...`) |
| `cfut_` | User API token | `/user/tokens/verify` |
| `cfk_` | Global API key | neither — it is not a token |

**Test it against `/accounts` instead**, which is the real proof and needs no prefix logic:
```bash
token=$(cat ~/.hermes/profiles/gentech/secrets/cloudflare.token)
curl -s -H "Authorization: Bearer $token" https://api.cloudflare.com/client/v4/accounts
# success:true + account list = the token is ALIVE and has account scope
```
**Measured working — read AND write.** Account read, Pages project read/create, deployment, and zone DNS
record create were all exercised successfully from an agent session. **Write scope is proven, so do the
work yourself rather than telling the user to log in.** *Reading succeeding says nothing about write scope*
— so the proof is the write, not the read: create something reversible and confirm it landed.

| Subdomain | Type | Value | Proxy Status |
|-----------|------|-------|-------------|
| `{subdomain}` *(nginx origin)* | A | `2.24.195.196` | either — grey for a demo page, orange for CF TLS/cache |
| `{subdomain}` *(**Pages** origin)* | **CNAME** | **`{project}.pages.dev`** | **orange (proxied) — mandatory** |

**Pick the row that matches the ORIGIN you verified, not the one that looks simpler.** An A record to the VPS
only works if nginx is actually serving that name; a Pages project needs the proxied CNAME. **Proxied vs
grey is a property of what answers, not a preference.**

**Pitfall — the subdomain is dead until the DNS record exists, and you can add it yourself.** Nginx config (or
a Pages binding) alone is not enough — without the DNS record the name returns NXDOMAIN. **Do NOT tell the user
to log in to Cloudflare; the `cfat_` token has proven zone-DNS write scope.** Create the record, then verify by
fetching the hostname and hashing the body (Step 3). If it does not resolve from this container, that is the
local negative cache, not a failed record — diagnose with `--resolve` to the edge IP before reporting anything.

**Pitfall — a name that already HAS a record can still serve the wrong thing: replace the record, do not just
add one.** A hostname whose record is the wrong TYPE for its origin keeps answering the default handler even
after you deploy the correct service — the binding is not the problem, the leftover record is. Measured: a
subdomain held an `A` → VPS IP while its working sibling held a `CNAME` → `<project>.pages.dev`; the sibling
served the site, the `A` served one hollow default page. **Diagnose by comparing records across the zone — a
working neighbour tells you the correct shape** — then delete the wrong record and create the right one:
```bash
# does a wrong-type record already exist?
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?type=A&name=<sub>.gentechlabs.net" \
  | jq -r '.result[0].id'          # non-empty → delete it, then POST the correct CNAME
```
**TWO records for one name can coexist and the stale one may win, so deleting is part of the fix, not
optional.** A record is destructive to remove — it is often the only surviving pointer to where the content
was, so confirm the origin first (does the target still hold the files?). **Then READ THE RECORD BACK** — a
create call returning `success` is a claim; the read-back is the receipt. Expect the custom-domain status to
sit at `pending`/`initializing` for a while after attaching a Pages domain; the site can serve correctly
before that status settles, so verify by content hash rather than waiting on it. **Full procedure:
`references/cloudflare-pages-deployment.md`.**

### Step 5: Link from Portfolio
Add a nav link to the portfolio site:
```bash
ssh root@2.24.195.196 "sed -i 's|<li><a href=\"#experience\">exp</a></li>|<li><a href=\"#experience\">exp</a></li>\n        <li><a href=\"https://{subdomain}.gentechlabs.net\">{label}</a></li>|' /var/www/portfolio/index.html"
```

Also add a project card in the `#projects` section with description, tech tags, and link. Use `sed` to insert directly after the `<div class="projects-grid">` opening tag, matching the existing card format:

```bash
ssh root@2.24.195.196 "sed -i '/<div class=\"projects-grid\">/a\\
      <div class=\"project-card\">\
        <span class=\"project-icon\">🌈</span>\
        <h3>Dashboard Name</h3>\
        <p class=\"project-desc\">Description of what it does.</p>\
        <div class=\"tech-tags\"><span class=\"tech-tag\">Tag1</span><span class=\"tech-tag\">Tag2</span></div>\
        <div class=\"impact-metric\">📈 Live dashboard</div>\
        <a href=\"https://{subdomain}.gentechlabs.net\" class=\"project-link\">Live Dashboard →</a>\
      </div>' /var/www/portfolio/index.html"
```

Verify with `grep -c '{subdomain}.gentechlabs' /var/www/portfolio/index.html` — should return a count of project cards added.

**Pitfall — sed inserts get collapsed into single-line entries without proper formatting.** The `sed` command above inserts newlines literally. After inserting, verify the output has proper line breaks by checking with `grep -A 10 '{subdomain}' /var/www/portfolio/index.html`. If entries are collapsed, the `\` line continuations in the `a\\` block need adjustment — each `\` at line end produces a newline in the output.

### Step 6: Link from Demo Hub
If the new page is part of the product suite, add a card to `demo.html` in the appropriate section (Payment Infrastructure, DeFi Intelligence, Agent Infrastructure, Technical Stack).

## Deliver the Link — Build First, Send ONLY the Link

**User-verified pain point (Aug 2, 2026):** "Every time you're working on
giving me the link, the message gets cut off short." Cause: inlining long
status + HTML content in the same message as the link; Telegram truncates at
~4000 chars and the URL at the end never arrives.

**The pattern for ANY deliverable link (deploy page, demo, PDF, deck):**
1. Build the artifact on the server first — all tool calls, invisible to chat.
2. Verify it's live (`curl -o /dev/null -w '%{http_code}'` AND content check).
3. Then send a SHORT message with the link front-and-center, nothing after:
```
Here's the deploy page, boss:

https://gentechlabs.net/arc-deploy.html

Connect MetaMask, sign, done.
```
4. Never bury a link at the end of a long status recap. Status recap = separate
   message; link = its own message.
5. Never paste HTML/JS into chat — host it and link it. (See `message-length-discipline`
   skill for the full char-limit discipline; this is the deployment-specific
   delivery rule.)

## Professional Dashboard Preview Pattern

When Jordan says "make the front end look professional" (e.g., DeFi treasury hub), the goal
is a *product* interface, not a read-only data dashboard. Build the preview as if a real
user will manage money through it. See `references/professional-dashboard-preview-pattern.md`
for the full recipe, cost model, and surface-distinction rule.

At minimum the preview should include:
- Sticky header with nav, tenant/user toggle, wallet chip, and live status dot.
- Capital hero: large balance, deployed/idle split, efficiency/badge row, and a progress bar.
- An **action row** with the buttons a user expects (Add funds, Rebalance, Withdraw, Pause)
  — marked clearly as "preview · actions are not wired" if the wiring isn't done yet.
- A 2×2 or 4-column metric grid with subtle dividers.
- Earnings card that compares the book's yield to a benchmark (e.g., "same capital as an
  X% staker").
- "What the machine is doing" panel: regime, resolved shape, transition state, lean, next
  check, and a one-sentence explanation.
- Chart as *data*: max-bin label, price bounds, spot-position ruler, and a legend.
- A data-trust strip: last-read timestamp, source, and ledger-vs-shape delta.

**Pitfall — don't conflate the chat surface with the management surface.** Telegram is where
a user *talks* to an agent; the hub is where they *manage* a treasury. If other people will
use the product, the hub is the product face and Telegram is the support channel. Build and
preview them as separate surfaces with separate jobs.

## Demo Suite Structure

The demo hub at `gentechlabs.net/demo.html` is organized into sections:

| Section | Content |
|---------|---------|
| **Payment Infrastructure** | x402 Gateway, Q402 Gasless, Agent Kit |
| **DeFi Intelligence** | Yield Rainbow, GTA Arb Monitor, Narrative Rotation |
| **Agent Infrastructure** | Self-Evolution Harness, Agent Credit Score, GenTech Smash |
| **Technical Stack** | AI Models, Blockchain, Infrastructure |

Each card has: icon, status badge (LIVE/PREVIEW/SOON), title, description, and link.

## Shipping a Hub With Its Dashboards — consolidation

**A personal hub is not one page, it is a page plus the dashboards its tabs link to.** Each tab renders a
**mini view** and carries a CTA (*"Open Full Map →"*, *"Open Full Farm →"*) pointing at the full page.
**Deploy the hub and its dashboards as ONE bundle** so the relative paths resolve — a hub deployed alone is
a confident-looking page of dead buttons.

```
<project>/index.html                 ← the hub
<project>/Travel/travel-dashboard.html
<project>/Gaming/poe2-dashboard.html
<project>/DeFi/defi-dashboard.html   ← shipped alongside, not linked to a vanished host
```

**Prefer RELATIVE paths inside the bundle.** A tab's `onclick` and its CTA frequently disagree — measured, a
tab opened a relative path while its "full" CTA used an absolute URL at a host that no longer existed.
Ship one convention (relative) and let the bundle make it true.

### Audit every outbound CTA before you ship — a rendered tab proves nothing about where it points
Fetch each destination and confirm it returns real content, not a catch-all page:
```bash
for u in $(grep -oE 'href="https?://[^"]+"' index.html | cut -d'"' -f2 | sort -u); do
  printf '%s %s\n' "$(curl -sL -o /dev/null -w '%{http_code}' --max-time 20 "$u")" "$u"
done
```
Measured: **every one** of a hub's four "Open Full" links pointed at a `*.github.io` host that returned
`404` with a **fixed-size body** — GitHub Pages' own 404 page, not the content. The mini views all rendered
correctly, which is exactly why the hub *felt* fine.

- **A path near-miss 404s silently.** A link said `Travels/` while the directory on disk was `Travel/`.
  Check every link's path against the **actual on-disk directory name** (plural vs singular is the common
  one) before deploying.
- **Verify destinations by body, not only status.** Our own catch-all host returns `200` for a missing
  path; a dead third-party host returns a real `404` with a generic body. In both cases **the body is the
test** — hash it or read the title.
- **When grepping for a dead hostname, grep the FULL hostname.** `grep -ci 'someuser'` matched a *repo name*
  (`.../OWNER/SomeUser.github.io/main/data.json`) inside a legitimate `raw.githubusercontent.com` data URL —
  four false "dead link" hits. Grep `someuser.github.io`, never the bare username fragment; usernames
  legitimately appear in repo names and data URLs.
- **Compare HASHES, never sizes.** `python` `len(str)` counts *characters*; `wc -c` counts *bytes*. Emoji,
  em-dashes and arrows are multi-byte, so the byte count runs higher by one per character. A size mismatch
  with an equal hash is an instrument artifact, **not** a failed deploy — check for multi-byte characters
  before concluding anything.
- **A dashboard its own live data sources.** A hub tab may `fetch()` live JSON from a repo. Check those URLs
  resolve too — a tab that renders with blank numbers passed every status check.

### A registry entry marked `active` with no URL is a lie
Dashboards are registered somewhere (`Dashboards/dashboard-registry.json`, a hub index, a README table).
**A status must be backed by a reachable address.** Measured: six dashboards all read `status=active` with
`deployed_url` empty — six claims, six dead ends. **Mark undeployed entries as such** (`registered-not-deployed`)
and give the live ones real URLs. An unreachable dashboard is not active, and a registry that says otherwise
sends the next reader to a 404.

### One surface, one source of truth
When the same roadmap/tracker exists as both a vault file and a deployed page, **they will diverge** —
measured, a deployed tracker still displayed a plan that had been withdrawn, with zero trace of the change.
Point at ONE canonical surface and retire the copy, rather than keeping two in sync by habit.

## Portfolio Site Details

- **Location:** `/var/www/portfolio/index.html` (NOT `/var/www/gentechlabs/portfolio/`)
- **Nginx config:** `location /portfolio/ { alias /var/www/portfolio/; }`
- **Nav links** are in the `<ul class="nav-links">` section
- **Project cards** are in the `<div class="projects-grid">` section
- **Tech tags** use `<span class="tech-tag">` with accent color
- **Impact metrics** use `<div class="impact-metric">`

## Publishing a DATA file to a public page — the pre-publish gate

A page that `fetch()`es a sibling JSON is only as safe as that JSON and only as true as its provenance.
Three gates, in this order, on every publish.

### 1 · Scan for identifiers, and publish MASKED

**A rebuild is not automatically an improvement: it can re-add what an earlier version deliberately
removed.** The common regression is a generator that emits both `wallet` and `wallet_masked` — the file
previously carried only the masked form, so the raw one is new exposure that no diff review catches
because the file looks *more* complete.

- **Publish the masked form only**, for current identifiers *and* historical ones (a superseded address is
  still a live pointer to a person).
- **Public contract addresses are not personal data.** Whitelist them explicitly — an allow-list entry is
  a deliberate decision you can audit later; an unlisted one that happens to pass is an accident.
- The reason to mask is not abstraction: **the chain supplies the balances, and the public page is what
  attaches them to a name.**

### 2 · A scanner must be falsifiable in BOTH directions

A pre-publish scanner has two failure modes and only one of them is loud.

- **Too loose** — it passes the raw address and the whole gate is decorative.
- **Too strict** — it flags every price (`34.17241044461`), every CSS shorthand (`0 0 600 150`) and every
  ISO date (`2026-11-01`) as a phone number. **A scanner that cries wolf on every number in a financial
  file gets switched off within a day, and then it protects nothing.**
- Narrow the pattern to an explicit shape (`+<country><digits>` or `(<area>) <number>`), and **report the
  hit count, not just pass/fail** — "75 hits" next to "CLEAN" is how you notice the heuristic is wrong.
- **Prove it fires**: scan one file you know contains a real identifier and confirm it flags it, before
  trusting the clean result on the file you are about to publish.

### 3 · SHA-matched write, then verify the served bytes

The contents API needs the **current blob sha**. A stale sha does not fail loudly — it overwrites whatever
else changed in that file. Read the sha immediately before the write, send it, and treat a 
`409`/`sha mismatch` as "someone else edited it", not as a transient error to retry blindly.

**A 2xx on the PUT is a claim; the re-fetch is the receipt.** Request the published URL with a cache-buster
and confirm the new bytes are actually served. On a catch-all host — where every path returns `200` — the
body is the only test.

### 4 · An end-to-end test must not leave its provenance on the live surface

Proving a pipeline works by running it against production is legitimate and often the only honest test.
**Leaving the test's output published is not.** If the run stamps its source (a minutes file, a run id, a
`-SELFTEST` name), the public page now cites a thing that does not exist — and it reads exactly like real
content.

- **Test against the real surface, then immediately republish the true state** — including the *absence*
  of a block when no real source exists yet. "No record yet" is an honest page; a record naming a deleted
  file is a fabrication.
- After restoring, **fetch the live surface and grep for the test token**. A successful restore you did not
  verify is the same class of claim as the artifact you just removed.

## Pitfalls

- **Portfolio is at `/var/www/portfolio/` NOT `/var/www/gentechlabs/portfolio/`** — different root. Always check nginx config before assuming path.
- **Subdomains need DNS records** — nginx config alone isn't enough. The user must add A records in Cloudflare DNS. Without DNS, the subdomain returns NXDOMAIN.
- **DNS-only subdomains** (grey cloud in Cloudflare) are fine for demo pages and internal dashboards — no user data, no forms, no sensitive info. If SSL/HTTPS is needed later, flip proxy to orange (proxied) and set up certbot on the VPS.
- **Nginx reload after config change** — always run `nginx -t` before `nginx -s reload` to catch syntax errors.
- **Conflicting server names** — if a subdomain is already defined in another config file, nginx will warn but still work. The first match wins.
- **Portfolio sed edits** — use exact match strings. The nav has specific indentation. Verify with grep after editing.
- **Cloudflare cache** — new pages may take a minute to appear. Use `curl -H "Cache-Control: no-cache"` to bypass.
- **Lesson pages must be proper HTML** — not plain markdown. Always wrap in a styled HTML template with DOCTYPE, head, body, and matching dark theme CSS. See `references/lesson-page-template.md` for the pattern.
- **`.gitignore` re-ignores media — force-add anything pages load (burned twice Sep 4).** A late `**/*.mp4` / `**/*.mp3` rule can override earlier negations, so `git add -A` silently skips files that sit in the working tree — Pages then 404s the asset (dead video/audio) with no commit error. Check with `git check-ignore -v <file>`, fix with `git add -f <file>`, and curl the live asset URL after push.
- **Webroot backup to GitHub — chunked pushes + release assets (proven Sep 4).** A single >1.2G git-over-HTTPS push dies silently (`send-pack: unexpected disconnect while reading sideband packet`) and may leave "Everything up-to-date" lies in the transcript — verify the remote SHA, never the push's exit text. Chunk the tree into ≤250MB commits, push each, and ship the tail as a GitHub release asset (2GB/file limit — different upload path, immune to the pack disconnect). Full suite snapshot: private repo `GentechLabs/gentech-webroot-backup`.
- **404 on existing file** — if nginx returns 404 for a file that exists with correct permissions (`www-data:www-data`, 644), the issue is likely a conflicting server_name in another config file. Run `nginx -T 2>&1 | grep -E "server_name|root |index "` to see all active server blocks. The `localhost` hostname won't match any server_name — always test with the proper `Host` header: `curl -sI -H "Host: gentechlabs.net" http://127.0.0.1/path`.
- **Mobile-only container** — the main site was originally `max-width: 480px` (phone column on desktop). When building new pages, use `max-width: 1100px` for responsive layout. Use `.card-grid` for 2-col tablet / 3-col desktop card layouts, and `.stack-grid` for multi-column stack displays.
- **Subdomain SSL certs can share the wildcard** — subdomains on the same VPS can reuse `/etc/letsencrypt/live/gentechlabs.net/fullchain.pem` in their nginx config. No need to run certbot for each one individually. Just reference the shared cert in the 443 server block.
- **Subdomains as AAE layer showcases** — each subdomain can represent a different AAE layer. Pattern: yield.gentechlabs.net = Layer 7 (Intelligence), narrative.gentechlabs.net = Layer 7 (Intelligence). The page header should include a badge row showing the layer number, status, and tech tags. Include a "Layer Context" card at the top explaining how this dashboard fits into the AAE stack.
- **Dashboard pages need market analysis sections** — when building a data dashboard, include a dynamic analysis section that interprets the current data for the user. Pattern: renderMarketAnalysis() function that reads the current data state and produces oversold/neutral/overbought analysis with recovery signals and user advice. The analysis should answer "when could the bear end?" and "how do I use this for my portfolio?"
- **Back-link on subdomain pages must go to the demo suite** — subdomain pages (yield, narrative, arb) should link back to `gentechlabs.net/demo.html` (not `gentechlabs.net` or an old hub page). Use `🏠 Home` as the link text, not `🏠 Hub` or `🏠 GenTech`.
- **Site content audit pattern** — when Jordan asks to audit the main site, the checklist is: remove personal hubs, gaming hubs, DeFi dashboards, Labs dead tabs, Mess Hall, Hackathon Track, Support/Token sections. Add: Problems We Solve, Roadmap, Case Studies. Update layer counts. Fix container width for desktop. Update bottom nav and settings modal to match new sections.
- **Subdomain as AAE layer showcase** — each subdomain can represent a different AAE layer. Pattern: yield.gentechlabs.net = Layer 7 (Intelligence), narrative.gentechlabs.net = Layer 7 (Intelligence). The page header should include a badge row showing the layer number, status, and tech tags. Include a "Layer Context" card at the top explaining how this dashboard fits into the AAE stack. Include a "Treasury Integration" card showing how the Agentic Treasury uses this data. The back-link should go to the demo suite, not the main site.

## VPS Maintenance — Disk Space Recovery

**Pattern proven Jul 28, 2026.** The VPS (193GB disk) fills up over time from logs, caches, and Docker artifacts. When Hostinger sends a "disk space almost full" alert, run this recovery sequence:

### Step 1: Diagnose
```bash
ssh root@2.24.195.196 "df -h / && echo '---' && du -sh /var/log/* /var/cache/* /root/.npm /root/.cache /var/lib/docker /tmp/* 2>/dev/null | sort -rh | head -15"
```

### Step 2: Clean Logs
```bash
# Vacuum journal to 500MB
journalctl --vacuum-size=500M

# Remove old rotated logs (keep current)
rm -f /var/log/syslog.1 /var/log/syslog.2.gz /var/log/syslog.3.gz /var/log/syslog.4.gz
rm -f /var/log/kern.log.1 /var/log/kern.log.2.gz /var/log/kern.log.3.gz /var/log/kern.log.4.gz
rm -f /var/log/dmesg.0 /var/log/dmesg.1.gz /var/log/dmesg.2.gz /var/log/dmesg.3.gz /var/log/dmesg.4.gz
```

### Step 3: Clean Caches
```bash
npm cache clean --force
pip cache purge
apt-get clean
```

### Step 4: Prune Docker
```bash
docker system prune -f
```

### Step 5: Clean Temp Files
```bash
rm -rf /tmp/*.mp4 /tmp/*.zip /tmp/node-* /tmp/kage-*
```

### Typical Recovery
| Source | Typical Size | 
|--------|-------------|
| Old syslog/journal | ~2GB |
| npm cache | ~2GB |
| pip cache | ~700MB |
| Docker unused images | ~10GB |
| Temp files | ~600MB |
| **Total recovered** | **~13-15GB** |

### Prevention
Set up a weekly cron for log cleanup:
```bash
# /etc/cron.weekly/clean-logs
#!/bin/bash
journalctl --vacuum-size=500M
find /var/log -name '*.gz' -mtime +7 -delete
find /var/log -name '*.1' -mtime +7 -delete
```

### Pitfalls
- **Don't delete current logs** — only rotated archives (`.1`, `.gz`). Current `syslog`, `kern.log`, `dmesg` are active.
- **Docker prune removes unused images** — running containers are unaffected. Safe to run anytime.
- **npm cache clean --force** is safe — it only removes cached packages, not installed ones.
- **Journal vacuum is safe** — it removes old archived journals, not current ones. The `--vacuum-size` flag keeps only the most recent entries up to that size.

## References

- `references/cloudflare-pages-deployment.md` — **the Pages deploy procedure end to end**: `wrangler` invocation, project creation + custom-domain binding + proxied CNAME, the negative-cache/`--resolve` diagnosis, and the zone-audit queries. Read before deploying anything to a `*.gentechlabs.net` hostname.
- `references/demo-suite-structure.md` — Full demo hub architecture and card patterns
- `references/site-content-architecture.md` — What belongs on the main domain vs subdomains. Read before deploying anything new.
- `references/github-pages-workflow-pitfalls.md` — Pages deploy workflow pitfalls + the Aug 30 repo-rename provision-limbo and VPS-mirror fix.
- `references/resume-hosting-pattern.md` — Always-current résumé/CV: vault source-of-truth → self-hosted URL → portfolio repo → Pages mirror, plus the 6-hour Resume Sync cron and content QA rules.
- `references/market-analysis-pattern.md` — Dynamic market analysis section for data dashboards. Three-state oversold/neutral/overbought analysis with recovery signals, user advice, 4-year cycle timing context, and dry powder (USDC/USDT market cap) tracking pattern.
- `references/professional-dashboard-preview-pattern.md` — Product-shaped preview for management surfaces (treasury hub, portfolio, agent ops): layout checklist, cost model, surface distinction, and headless-Chrome viewport-floor QA trap.
- `references/game-loadout-tracker-pattern.md` — Reusable per-game build/loadout tracker (POE2, Helldivers 2): JSON schema, themed page, hub wiring, growth loop, verify checklist.
- `scripts/backup-webroot-push.sh` — Chunked webroot backup pusher (≤250MB commits, SHA-verified per push) for the backup pitfall above.

## Missing references

Cited in this skill but **absent** — verified 2026-10-19 across CORE and all four seat trees.

Listed here instead of repointed at something similar: a wrong pointer is worse than a known gap.

- `references/lesson-page-template.md` — no copy exists on any seat; nearest real material (where known) is named in the citing passage.
- `references/demo-suite-structure.md` — no copy exists on any seat; nearest real material (where known) is named in the citing passage.
