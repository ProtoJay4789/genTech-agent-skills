---
name: portfolio-deployment
description: Deploy the GenTech sites to Cloudflare Pages.
---

# GenTech website deployment — Cloudflare Pages

**The live estate is six Cloudflare Pages projects, deployed with `wrangler`. GitHub Pages is NOT the deploy
path any more, and the repo this file used to name does not exist.**

| project | domain |
|---|---|
| `gentechlabs` | gentechlabs.net (+ www) |
| `gentech-services` | services.gentechlabs.net |
| `gentech-demo` | demo.gentechlabs.net |
| `gentech-portfolio` | portfolio.gentechlabs.net (index + roadmap) |
| `gentech-milestones` | milestones.gentechlabs.net (index + career/career-old/defi) |
| `gentech-hub` | **hub.gentechlabs.net** + gentech-hub.pages.dev — DeFi/, Gaming/, Travel/ subtrees |

**⚠️ `gentechlabs.github.io` DOES NOT SERVE — but the repo still EXISTS** (measured: `private: true`, `has_pages: false`,
pushable, and it holds real files such as `DeFi/defi-data-jordan.json`). **Do not describe it as deleted and do not
conclude a push failed:** the push succeeds and nothing is ever published, which is the more dangerous state because
every tool reports success. All repo/clone/`gh-pages`/raw.githubusercontent paths below describe that dead target.
The resume is served from the VPS (`gentechlabs.net/resume.pdf` and `/resume.html`), not from Pages.

## The one deploy path: `wrangler`, from the deploy tree

```bash
cd /opt/data/deploy/<project>
export CLOUDFLARE_API_TOKEN=$(cat /opt/data/shared-secrets/cloudflare.token)
export CLOUDFLARE_ACCOUNT_ID=$(python3 -c "import json;print(json.load(open('/opt/data/shared-secrets/cloudflare.ids.json'))['account_id'])")
/opt/data/wrangler-cli/node_modules/.bin/wrangler pages deploy . --project-name=<project> --branch=main --commit-dirty=true
```

**⚠️ Verify the path before believing this file.** An earlier version of this section named
`10-Labs/web-sites-source/deploy-sites.sh` and `10-Labs/web-sites-source/<project>/`; **neither exists.** The live
deploy tree is **`/opt/data/deploy/<project>/`**. A skill that names a script which is not there sends the next
reader into `bash: no such file` and then into a hand-rolled workaround — so when a documented path is missing,
**fix this file in the same sitting** rather than quietly routing around it.

Credentials the CLI needs: `CLOUDFLARE_API_TOKEN` from `/opt/data/shared-secrets/cloudflare.token` and
`CLOUDFLARE_ACCOUNT_ID` from `cloudflare.ids.json` (key `account_id`).

**The deploy tree IS the source of truth for what is live.** Edit there, then deploy the whole tree — source and
deploy input being the same directory is the property that stops a half-published site recurring.

## A custom domain may ALREADY be attached — probe it before trying to add it

`wrangler pages domain add` **does not exist in the vendored CLI**: it prints the global help and exits 0, which
reads as success. Use the API instead:

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACC/pages/projects/<project>/domains" \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' --data '{"name":"<host>"}'
```

**HTTP 400 `You have already added this custom domain` is a PASS, not a failure.** The domain was attached and
nothing had ever been pointed at it. Go straight to probing the host:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<host>/         # want 200
curl -s -o /dev/null -w '%{http_code}\n' https://<host>/zz-nope  # want 404
```

**Every verify URL points at the DOMAIN, never the `*.pages.dev` preview name.** The preview name is not a URL a
customer would ever see, so a verifier aimed at it can pass while the branded host is dead — and the preview
subdomain changes on every deploy (`<hash>.project.pages.dev`), so it is not even stable enough to link.

## A live site nobody links to is not published

**The deploy is the second-to-last step; the front-door link is the last one.** A project can serve perfectly on
its own domain for months with **zero inbound links** — `grep -c` the served front page for the host before
calling the work done, and add the card in the same sitting as the deploy:

```bash
curl -sL "https://<main-site>/?cb=$(date +%s)" -o /tmp/front.html
wc -c < /tmp/front.html; grep -c '<new-host>' /tmp/front.html      # 0 = nobody can find it
```

**Re-deploying a site to add one link is a whole-tree deploy too** — ship the tree, then confirm the security
headers still respond (`_headers` is consumed as config and never appears in the deployment `files` list, so its
survival is only visible in response headers).

## ⚠️ Do not hand-roll the Pages upload API

A manual multipart POST to `/accounts/{id}/pages/projects/{name}/deployments` **recorded the correct sha256 in
the manifest and then served HTTP 500 on every hostname — twice — while reporting success.** Rolling back to the
previous deployment restored service in seconds each time, which is the only reason it was survivable.

**Use the vendor CLI.** Wrangler handles the upload protocol, costs nothing to run, and is vendored at
`/opt/data/wrangler-cli/node_modules/.bin/wrangler`.

## ⚠️ A single-file deploy silently deletes `_headers` (and every other file)

Direct Upload replaces the whole deployment. Shipping only `index.html` **removed the security headers**
(`x-frame-options`, `x-content-type-options`, `referrer-policy`, `x-xss-protection`) that a `_headers` file had
been setting — and nothing errored.

**Before deploying a project, list what the current deployment contains and ship all of it:**

```python
# the deployment object's `files` field is the manifest of what is live
GET /accounts/{account_id}/pages/projects/{project}/deployments/{id}
```

A `_headers` / `_redirects` / `404.html` file does **not** appear in `files` (Pages consumes it as config, it is
not served) — so absence from that list is **not** evidence it is absent from the deployment. Capture the
response headers before a deploy and diff them after; that is the only cheap check.

## ⚠️ A successful push to a target that does not serve is not a publish

Check the target's own capability before trusting any push path:

```bash
curl -s -H "Authorization: Bearer $TOK" https://api.github.com/repos/<owner>/<repo> \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print('private:',d.get('private'),'has_pages:',d.get('has_pages'))"
curl -s -o /dev/null -w '%{http_code}\n' https://<the-host-it-claims-to-publish-to>/   # 404 on everything = dead
```

A repo with `private: true, has_pages: false` **accepts every commit and serves nothing.** The push tool reports
success because the push succeeded; the site is empty because nothing was ever published.

**The failure hides behind a plausible excuse.** A verify step that polls the public URL and, after N tries,
prints *"pushed but not verified — CDN lag or a stale build"* turns a permanently wrong host into a transient.
**When a verify is still failing on its third consecutive run, the target is wrong, not slow — the message must
say that, and the verify URL must DEFAULT to the URL the transport actually serves** so a caller who forgets the
flag cannot get a silent pass on a publish nobody can see.

## ⚠️ One page can fetch from three different hosts — grep the served HTML

A dashboard can deploy correctly and still show year-old data, because **the page itself** pulls its JSON from
somewhere else. Measured on the DeFi hub: the HTML was live on one host, its data files were pushed by a script to
a second host that did not serve, and three `fetch()` calls read a third host's raw GitHub URL — **three different
answers to "where does this page get its data", none of them the same.** Every part looked fine in isolation,
which is why it survived for months.

```bash
curl -sL https://<host>/<page> -o /tmp/served.html
wc -c < /tmp/served.html                                  # 0 bytes = the fetch failed, not 'no refs'
grep -oE 'fetch\(.[^,)]{0,60}' /tmp/served.html | head    # where it really reads from
grep -c 'raw.githubusercontent.com' /tmp/served.html      # must be 0 on a self-contained site
```

**Fix: same-origin relative paths (`./data.json`), with the data files shipped in the same deploy tree as the
page.** A page that reads its own origin cannot be stale relative to itself, needs no CORS, and has one host to
break instead of three.

**⚠️ `curl -s` returning 0 bytes is not "no external references" — it is a failed fetch.** A bare `grep -c` on an
empty file prints `0` and reads as a pass. Capture the byte count in the same command and use `-L`.

## ⚠️ A page must not advertise a route, price or feature that does not exist

**Marketing copy is a claim, and it ships with the deploy.** A panel was published naming
`POST /v1/market/etf-flow` — an endpoint that was never built — for a week before anyone noticed. A
visitor who tries it gets a 404 and concludes the product is broken, which is a worse outcome than not
advertising it at all.

**Before deploying copy that names an endpoint, a price or a capability, hit that exact URL:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://api.example.net/v1/the/route   # 402/200 = exists; 404 = fiction
```

**Then re-read the deployed page and compare the string to the route that actually answers** — the
method, the path shape and the price all drift independently. When the route changes, the copy is part
of the change, in the same sitting.

## ⚠️ A catch-all makes every link check meaningless — probe nonsense first

A Pages project with no `404.html` returns **the homepage with HTTP 200 for every unknown path** — including a
URL invented for the test. Every "all links 200" verdict against such a site is hollow, and it hides the fact
that a deep path was never published.

```bash
# a real 404 answers differently from a catch-all
curl -s -o /dev/null -w '%{http_code}' https://<host>/zz-no-such-page
curl -s https://<host>/zz-no-such-page | wc -c      # identical byte count to / means catch-all
```

**Symptom to recognise:** every path returns the same size. Confirm by comparing the body against `/`.
**Fix:** ship a `404.html` per project — it is the only way the site can distinguish a working link from a
broken one.

## Verifying a deploy — both directions, always

```bash
curl -s -o /dev/null -w '%{http_code}' https://<host>/            # real page -> 200
curl -s -o /dev/null -w '%{http_code}' https://<host>/zz-nope    # nonsense -> 404
```

**Content check, not just status.** Cloudflare injects ~367 bytes of script into served HTML, so compare the
preserved source against the served body with a tolerance, or hash the source and compare a slice — never assume
`served_bytes == source_bytes`.

### ⚠️ A 200 on an HTML file proves the FILE is served, not that the PAGE shows anything

**A JS-rendered page answers 200 with correct HTML and correct JSON behind it and still displays garbage.**
Two measured failures on one panel, both invisible to status codes:

- **Guessed field names render as dashes.** The table asked for `change_24h` / `returns`; the provider returns
  `change_pct_24h` / `roi_7d` / `roi_1m` / `ytd`. Every cell printed `—`, which reads as *"no data published"*
  when it actually means *"I asked for a key that does not exist."* A dash in a finance table is a lie about
  the market.
- **Units are not inferable from the number.** The provider returns **fractions** (`0.0256`). Printing them with
  a `%` suffix showed `+0.03%` for a 2.56% move — wrong by 100×, and it looked entirely plausible.

**So read the RENDERED page, not the source and not the status:**

```python
rows = js("""(() => {const o=[];document.querySelectorAll('table tbody tr').forEach(tr=>
  o.push([...tr.children].map(td=>td.innerText.trim()).join(' | ')));return o.join('\\n')})()""")
print(rows)          # every cell must hold a number, not '—'
print(js("document.body.innerText")[:600])   # the cards, the labels, the units
capture_screenshot()  # then vision_analyze it: layout, cut-off cards, dashes
```

**A dash where a number belongs, or a percentage that is 100× off, is the failure signature.** Confirm the field
names and the unit against one real payload before writing the renderer, then re-read the rendered output after
the deploy.

### ⚠️ The edge caches the HTML — prove you are looking at the new file

After a redeploy the browser can still serve the previous HTML, so a "still broken" verdict may be a cached copy
of the bug you already fixed. Prove which file you are reading before diagnosing it:

```bash
TS=$(date +%s); URL="https://<host>/<page>?cb=$TS"
curl -sL "$URL" -o /tmp/served.html -w '%{http_code} %{size_download}\n'
wc -c < /tmp/served.html; wc -c < /opt/data/deploy/<project>/<page>     # must match
```

**⚠️ `"...?cb=$(date +%s)"` inside SINGLE quotes is not expanded** — the literal string goes to the server, the
fetch returns `000`, and the output file still holds the *previous* body, so a byte comparison against it is
meaningless. Compute the query value first, then interpolate. In the browser, use a unique query key per load
(`?fresh=<epoch>`); the same URL twice can return the cached render.

## Cloudflare's API token is valid even when `verify` says otherwise

`GET /user/tokens/verify` can return **`success:false` / `Invalid API Token` while DNS, Workers and Pages reads
all work**. Treat a failed verify as UNKNOWN about permissions, not as "the token is dead" — the working check is
the resource call you actually need.

---

# HISTORICAL — the GitHub Pages era (superseded, kept for diagnosis only)

**Everything below this line describes a deployment target that no longer exists.** It remains useful only for
recognising the old failure modes if someone revives a GitHub Pages path.

## FIRST: verify the substrate before you plan a file move

**A deploy plan that assumes a working copy and one canonical version of a file is a plan built on two
claims nobody measured.** Check both before touching anything:

```bash
git -C <documented-clone-path> remote -v      # does the clone exist ON THIS HOST?
curl -s "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/branches" | grep '"name"'
```

- **A documented clone path is a claim with a lifetime.** A clone under a host home directory dies with
  that directory; the skill and the plan keep naming it long after. If there is no clone, the work is an
  API/clone-from-scratch job, and saying so up front beats discovering it mid-edit.
- **The repo carries more than one live branch, and they are NOT copies of each other.** `main` and
  `gh-pages` routinely diverge in both content and size for the same filename. **Read every branch before
  editing**, and name the branch you are changing: a rename committed to one branch does not change the
  other, and both may be served. Compare them without a clone or a token:
  `curl -s https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path> | wc -c`.
- **Committed is not published.** The Pages builder lags, and a stale build serves the cached root page
  while returning **404 for files that are committed**. So a 404 on a deep URL is not proof the file is
  absent — check the git tree (API `contents/?ref=<branch>`) before concluding either way, and never
  report "live" or "missing" off the served URL alone.
- **Check the DESTINATION NAME before renaming onto it.** The obvious new name is often already taken by
  something that must not be overwritten — the family convention may reserve it. Enumerate the target path
  on **every** branch first; a rename that silently replaces the owner's page is worse than a blocked task.

## ⚠️ HISTORICAL (Aug 3, 2026): personal-account Pages block — VPS was then the only target

**GitHub Pages is permanently broken for ProtoJay4789 (personal account).** The account has an infrastructure-level restriction that prevents Pages from ever deploying — 0 builds in history, Actions disabled at account level, the settings option removed from the UI. **Do NOT attempt to fix GitHub Pages.** The VPS is the permanent home.

**Confirmed Aug 3, 2026:** Even switching to legacy `gh-pages` branch mode and pushing a trigger commit does NOT deploy — the Pages build queue shows 0 builds ever. `POST /pages/builds` returns "queued" but the build never executes. The account is flagged at the infrastructure level. The VPS at `portfolio.gentechlabs.net` is the only working deployment target.

### Live Portfolio

- **URL:** `https://portfolio.gentechlabs.net/` (HTTPS, Let's Encrypt cert)
- **Also at:** `https://gentechlabs.net/portfolio/` (nginx alias)
- **Server path:** `/var/www/portfolio/index.html` on `root@2.24.195.196`
- **DNS:** `portfolio.gentechlabs.net` → `2.24.195.196` (Cloudflare DNS-only, gray cloud)

### Deploy Command

```bash
# 1. Get latest from gh-pages branch (authenticated)
TOKEN=$(grep 'oauth_token:' ${PROFILE_DIR}/home/.config/gh/hosts.yml | head -1 | awk '{print $2}' | tr -d '"')
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://raw.githubusercontent.com/GentechLabs/gentechlabs.github.io/gh-pages/index.html" \
  > /tmp/portfolio-latest.html

# 2. Push to VPS
scp -o StrictHostKeyChecking=no /tmp/portfolio-latest.html root@2.24.195.196:/var/www/portfolio/index.html

# 3. Verify
curl -s http://portfolio.gentechlabs.net/ | grep -c "x402"
curl -sk https://portfolio.gentechlabs.net/ | grep -c "x402"
```

### Backup Pattern

Before overwriting on VPS, SSH in and backup:
```bash
ssh root@2.24.195.196 "cp /var/www/portfolio/index.html /var/www/portfolio/index.html.bak$(date +%s)"
```

### GitHub Repo Status

The repo at `/root/repos/ProtoJay4789.github.io/` is a **secondary mirror only** — it holds the source but cannot deploy. The `gh-pages` branch has correct content (verified via authenticated raw.githubusercontent.com), but GitHub will never serve it. The old vault path `${VAULT_DIR}/github/ProtoJay4789.github.io/` no longer exists.

### Full Diagnosis Reference

See `references/account-level-pages-block-diagnosis.md` for the complete diagnostic sequence, symptoms, and what does/doesn't work.

---

Deploy content from vault (`${VAULT_DIR}/`) to portfolio website (`${VAULT_DIR}/github/gentechlabs.github.io/`).

---

## Trigger Conditions

When the user asks to:
- "Ship" or "deploy" content to the portfolio
- "Add to the portfolio site"
- "Update the portfolio"
- "Deploy [content] to portfolio"

---

## Portfolio Site Structure

**Key file:** `index.html` (main portfolio page)

**Sections:** (in order, with `id=` attributes)
- `sec-about` - About section
- `sec-journey` - Journey section
- `sec-projects` - Projects section
- `sec-stack` - AAE Stack section
- `sec-apis` - API Services section
- `sec-casestudies` - Case Studies section

**Navigation requires updates in 4 places when adding a section:**
1. Bottom nav bar (around line 1350) - adds a nav button
2. Settings modal options (around line 850) - adds a settings option
3. Section mapping in JS (around line 1364) - adds to `map` object
4. Scroll spy array in JS (around line 1378) - adds to `sections` array

---

## Deploying Standalone Pages to Subdirectories

Not all deployments modify `index.html`. Sometimes you deploy a new standalone page to a subdirectory (e.g., `DeFi/defi-dashboard.html`).

### Correct File Path

The portfolio repo root is at:
`${VAULT_DIR}/github/gentechlabs.github.io/`

A file at `repo-root/DeFi/defi-dashboard.html` in the tree must be written to:
- `${VAULT_DIR}/github/gentechlabs.github.io/DeFi/defi-dashboard.html`

**Do NOT write from the vault root** (e.g., `${VAULT_DIR}/DeFi/defi-dashboard.html`) — git will see the file at path `github/gentechlabs.github.io/DeFi/defi-dashboard.html` which GitHub Pages will not serve.

### Verify Correct Path After Adding

```bash
cd ${VAULT_DIR}/github/gentechlabs.github.io
git ls-tree HEAD DeFi/defi-dashboard.html
# Expected: DeFi/defi-dashboard.html
# Wrong:    github/gentechlabs.github.io/DeFi/defi-dashboard.html
```

### Fallback: GitHub API When Git Push Is Blocked

The vault's working tree (untracked files from ongoing sessions) frequently blocks `git checkout`, `git stash`, and `git pull`. When standard git deployment fails:

**For existing files (update):**
```bash
GH_TOKEN=$(gh auth token 2>/dev/null)
# Get current SHA
SHA=$(curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/contents/DeFi/file.html" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
# Base64 encode new content
B64=$(base64 -w0 /path/to/new/file.html)
# Update via PUT
curl -s -X PUT -H "Authorization: token $GH_TOKEN" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json; print(json.dumps({'message':'Update file','content':'$B64','sha':'$SHA'}))")" \
  "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/contents/DeFi/file.html"
```

**For new files:** Omit `sha` from the JSON payload.

### CDN Propagation

After deployment:
- **raw.githubusercontent.com** updates within ~30s (CDN cache: 5 min max-age)
- **GitHub Pages CDN** (protojay4789.github.io) takes 2-5 min to rebuild and flush cache
- **Git blob API** is the only uncached definitive source

### Build Type: "workflow" vs Default

This repo uses **"workflow" build type** (GitHub Actions), NOT the default Pages builder. This means:

1. **You CANNOT trigger a manual rebuild** via `POST /pages/builds` — the API returns 403 "The repository does not have a GitHub Pages site" even though Pages IS configured
2. **You MUST push a commit** (even empty with `--allow-empty`) to trigger a rebuild
3. The API-based file update (PUT `/contents/path`) creates a commit and DOES trigger an Actions run automatically

### Checking Build Progress

After deployment, check GitHub Actions for build status:

```
GH_TOKEN=$(gh auth token 2>/dev/null)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/actions/runs?per_page=3&event=push" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('workflow_runs', []):
    print(f\"{r['head_commit']['message'][:50]:50s} {r['status']:12s} {r['conclusion'] or '...':10s}\")
"
```

Status: `completed` = done, `in_progress` = building, `pending` = queued.
Conclusion: `success` = deployed, `cancelled` = superseded, `failure` = build broke.

### Verifying Deployed Content (Four Levels)

**Level 1 — Git tree (file at correct repo-relative path):**
```
cd ${VAULT_DIR}/github/gentechlabs.github.io
git ls-tree HEAD DeFi/file.html
# Expected: DeFi/file.html
# Wrong:    github/gentechlabs.github.io/DeFi/file.html
```

**Level 2 — Git blob (content confirmed, UNCACHED — definitive):**
```
GH_TOKEN=$(gh auth token 2>/dev/null)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/git/blobs/<SHA>" | \
  python3 -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode()[:200])"
```

**Level 3 — Browser snapshot (visual, may be cached):**
Navigate URL, check `<title>` in the returned snapshot.

**Level 4 — Raw URL (cache-busting):**
```
curl -s "https://raw.githubusercontent.com/GentechLabs/gentechlabs.github.io/main/DeFi/file.html?cb=$(date +%s)" | grep '<title>'
```

### Multi-File Dashboard Deployments

When a dashboard loads data from multiple JSON files (rainbow, rotation, macro), deploy ALL files in the same batch. The dashboard shows fallback/loading until every file exists on the remote.

**Preferred order:**
1. Create all data files locally first (within the repo tree)
2. Push content (HTML) + data files (JSON) in a single API batch
3. Verify ALL raw URLs return 200
4. Check GitHub Actions for the final build to complete

## Deployment Workflow

### 1. Read Content from Vault

```python
# Read the source content (e.g., case studies, one-pager)
with open('${VAULT_DIR}/00-HQ/case-studies.md', 'r') as f:
    content = f.read()
```

### 2. Generate Matching HTML

The portfolio uses specific styling:
- Section wrapper: `<div id="sec-NAME" style="margin-top: 18px;">`
- Section title: `<div class="section-title">🔥 Title</div>`
- Cards: `<div class="card project-card">` with `card-header`, `project-tech`, `card-desc`
- Status badges: `<span class="status-badge status-live"><span class="status-dot"></span> Live</span>`
- Tags: `<span class="tag tag-blue|cyan|green">Label</span>`

**Copy an existing section as a template** and adapt the content.

### 3. Find Insertion Point

Use search to find markers:

```python
# Read portfolio HTML
with open('${VAULT_DIR}/github/gentechlabs.github.io/index.html', 'r') as f:
    html = f.read()

# Find insertion point (e.g., after "Browse All APIs →")
insert_marker = '<a href="https://gentechlabs.net" target="_blank" class="link-btn">🧪 Browse All APIs →</a>'
next_section = '<!-- ═══ NEXT_SECTION ═══ -->'

if insert_marker in html and next_section in html:
    # Insert between them
    updated = html.replace(insert_marker + '\n\n' + next_section,
                          insert_marker + '\n\n' + new_section + '\n' + next_section)
```

### 4. Update Navigation (4 places)

**Bottom nav:** Add button after last existing nav item

```html
<button class="nav-item" onclick="scrollToSection('sec-NAME')">
  <span class="icon">🔥</span>
  <span>Title</span>
</button>
```

**Settings modal:** Add option after last existing option

```html
<button class="settings-option" onclick="scrollToSection('sec-NAME');closeSettings()">
  <span style="font-size:1.3em;">🔥</span>
  <div><strong>Title</strong><br><span style="font-size:0.8em; color:var(--dim);">Subtitle</span></div>
</button>
```

**JavaScript section mapping:** Add to `map` object

```javascript
const map = {
  'sec-about': 0,
  'sec-journey': 1,
  'sec-projects': 2,
  'sec-stack': 3,
  'sec-apis': 4,
  'sec-NAME': 5  // Add this
};
```

**JavaScript scroll spy:** Add to `sections` array

```javascript
const sections = ['sec-about', 'sec-journey', 'sec-projects', 'sec-stack', 'sec-apis', 'sec-NAME'];
```

### 5. Use execute_code for Multi-Location Changes

Do NOT use `patch` for multi-location updates. Use `execute_code`:

```python
# More reliable for replacing multiple occurrences
content = content.replace(old_pattern, new_pattern)
# Write back
with open('index.html', 'w') as f:
    f.write(content)
```

### 6. Commit and Push

```bash
cd ${VAULT_DIR}/github/gentechlabs.github.io
git add index.html
git commit -m "Descriptive commit message"
git push
```

---

## Git Credential Status

**Vault repo** (`gentech-vault`):
- ✅ Credentials configured
- Pushes work fine via HTTPS

**Portfolio repo** (`gentechlabs.github.io`):
- ❌ May not have credentials configured
- Current remote: `https://github.com/GentechLabs/gentechlabs.github.io.git`
- Push fails with: `could not read Username`

**Fix options:**
1. User pushes manually from their machine
2. Configure credentials on VPS (SSH key or OAuth token)
3. Use personal access token in remote URL

**Do NOT:** Hardcode tokens in scripts. Use environment variables or user configuration.

---

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using `patch` for multi-location changes | Only first occurrence replaced, navigation broken | Use `execute_code` with Python string replacement |
| Missing one of 4 navigation updates | Section exists but can't scroll to it or no settings option | Check all 4: bottom nav, settings, JS map, JS sections array |
| Not matching portfolio CSS style | Content looks out of place | Copy existing section as template, use same class names |
| Assuming credentials are configured | Push fails with auth error | Check credentials first, have user push manually if missing |
| Gitignore exception ordering | New media files (mp4, png) not pushed because gitignore denies them | Place exception (`!pattern`) AFTER the blanket deny (`**/*.ext`). Later gitignore rules override earlier ones, so deny-first, then allow. |
| **Wrong repo-relative path for subdirectory pages** | GitHub Pages returns 404 or old content | Verify with `git ls-tree HEAD path/to/file` — file must be at path relative to repo root, not nested under vault structure |
| **git push blocked by vault working tree** | `git checkout` aborts with "untracked files would be overwritten" | Use GitHub API fallback — don't try to force through vault interference |
| **CDN shows stale content after deploy** | raw.githubusercontent.com correct, GitHub Pages shows old version | Wait 2-5 min for Pages build. Verify via Git blob API for definitive status |
| **Private repo blocks GitHub Pages** | All URLs return 404, raw.githubusercontent.com also 404 without auth | Check repo visibility: `curl -s -o /dev/null -w "%{http_code}" "https://github.com/OWNER/REPO"` — 404 = private. Fix: make repo public, or deploy via Cloudflare Worker proxy using the PAT |
| **Actions disabled at account level (PERMANENT)** | Workflow dispatch returns 422 "Actions has been disabled for this user", no workflow runs appear. Pages builds queue but never execute (0 builds ever). Even legacy gh-pages branch won't deploy. The user confirmed the Actions settings option has been **removed** from their personal account settings entirely. | **This is permanent and unfixable.** Do NOT suggest re-enabling Actions or creating new workflows. The VPS at `portfolio.gentechlabs.net` is the only working deployment target. See `references/account-level-pages-block-diagnosis.md` for the full diagnostic sequence. |
| **CDN caches old private-repo 404** | After making repo public, raw.githubusercontent.com still returns 404 for hours | The CDN edge caches the "private repo" response aggressively. Use the GitHub API with auth (`curl -H "Authorization: token $PAT"`) to verify files exist. For immediate access, serve from VPS instead. |
| **gh-pages orphan branch doesn't trigger legacy build** | Pushing a gh-pages branch with all files doesn't deploy — Pages build queue shows 0 builds ever | The account-level Actions block prevents even legacy (non-workflow) Pages builds from executing. The `POST /pages/builds` API returns "queued" but the build never runs. Only fix is resolving the account-level Actions block or using VPS fallback. |
| **Pages build_type mismatch** | Pages configured but site returns 404 after push | Check `build_type` in Pages API response. If `"legacy"`, the default Pages builder is active but the workflow file expects `"workflow"` mode. Switch via `PUT /pages` with `{"build_type":"workflow"}`. If the PUT returns empty, the switch may have already been applied — re-check with GET. |
| **Pages status is null** | Pages API returns `"status": null` even though `has_pages: true` | Null status means Pages is configured but hasn't completed its first build yet. Push a commit or trigger a workflow dispatch to kick off the initial deployment. |
| **Repo flipped private→public→private kills Pages** | After flipping back to private, `has_pages` becomes `false` and Pages is deactivated | Re-flip to public, then re-enable Pages via `POST /pages` with `{"source":{"branch":"main","path":"/"}}`. Then switch build_type to `"workflow"` via `PUT /pages` with `{"build_type":"workflow"}`. Push a commit to trigger the first build. |

---

## Verification Checklist

After deployment:
- [ ] File pushed to VPS via SCP
- [ ] Backup created on VPS (`index.html.bak*`)
- [ ] `curl -s http://portfolio.gentechlabs.net/` returns HTTP 200
- [ ] `curl -sk https://portfolio.gentechlabs.net/` returns HTTP 200
- [ ] Content verified (e.g., `grep -c "x402"` or check for expected text)
- [ ] GitHub repo `gh-pages` branch updated (secondary mirror, for source control only)

---

## Example: Adding a New Section

```python
# 1. Generate HTML section
new_section = '''  <!-- ═══ NEW SECTION ═══ -->
  <div id="sec-new" style="margin-top: 18px;">
    <div class="section-title">🔥 New Section</div>
    <div class="card-desc" style="margin-bottom: 12px;">Description here.</div>

    <div class="card project-card">
      <div class="card-header">
        <span class="card-title">Item Title</span>
        <span class="status-badge status-live"><span class="status-dot"></span> Live</span>
      </div>
      <div class="project-tech">
        <span class="tag tag-blue">Tech</span>
        <span class="tag tag-cyan">Stack</span>
      </div>
      <div class="card-desc">Item description here.</div>
    </div>
  </div>'''

# 2. Insert at correct location
# 3. Update navigation (4 places)
# 4. Commit and push
```

---

## Related Infrastructure

### Portfolio Sync Script (`portfolio_sync.py`)

The portfolio has an automated daily health check at `scripts/portfolio_sync.py` (both profile and `/opt/data/profiles/gentech/scripts/` paths). It:
1. Pulls latest from `origin/main`
2. Reads canonical `data/projects.json`
3. Verifies consistency with `projects.json` and `index.html` (V4 — no inline JSON, so consistency is data:root only)
4. Syncs if needed and pushes

**The method signature for continuous work:** When deploying content, the sync script may overwrite your changes if it runs on its schedule after you. Always push your deployment changes, then let the health check confirm consistency on its next run. If the sync script detects a DRIFT and resets, it means your file paths were wrong (see file path pitfalls above).

### Cron Job

- **Name:** `Portfolio Health Check — Sync + Verify + Deploy`
- **Job ID:** `ce23c5df747b`
- **Schedule:** `15 12 * * *` (daily at 12:15 UTC / 8:15 AM ET)
- **Toolsets:** terminal, file
- **Script:** `portfolio_sync.py`

## Consistency Across Artifacts

**User preference:** When updating information like agent stack, deployed services, or pricing, ensure consistency across ALL public-facing artifacts. Do NOT update just one — update everywhere that information appears.

**Artifacts to keep in sync:**

| Artifact | Path | Purpose |
|----------|------|---------|
| Portfolio website | `github/gentechlabs.github.io/index.html` | Public showcase |
| One-pager | `00-HQ/gentech-one-pager.md` | Ecosystem introductions |
| Agent Kit v2 spec | `02-Labs/agent-kit/AGENT-KIT-V2-SPEC.md` | Product documentation |
| Build queue | `00-HQ/build-queue.md` | Internal roadmap |
| Audit reports | `Audits/*.md` | Verification evidence |

**When updating:**

1. Identify what changed (e.g., new model, new API, updated endpoint count)
2. Search across all artifacts for related mentions
3. Update every occurrence with the new information
4. Commit and push all changes together

**Example workflow:**

```python
# User says: "Update agent stack to include GLM-5.2"

# 1. Search for "agent stack" across vault
import os
for root, dirs, files in os.walk('${VAULT_DIR}'):
    for file in files:
        if file.endswith('.md') or file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            if 'agent stack' in content.lower():
                # Update this file
                updated = content.replace(old_stack, new_stack)
                with open(path, 'w') as f:
                    f.write(updated)

# 2. Commit all changes together
git add .
git commit -m "Update agent stack across all artifacts - add GLM-5.2"
git push
```

**Why this matters:** 
- User said "I wanted to make sure it's synced everywhere"
- Inconsistent information looks unprofessional
- Different docs saying different things confuses people
- Melinda, grant reviewers, and collaborators read multiple artifacts

---

## Related Files

- Portfolio site: `${VAULT_DIR}/github/gentechlabs.github.io/index.html`
- Vault content: `${VAULT_DIR}/00-HQ/*.md`
- Reference: See `references/portfolio-structure.md` for full CSS classes
- **Design strategy:** See `references/portfolio-design-strategy.md` for job-seeking vs founder showcase mode, section ordering, and content rules
- **Link delivery pattern:** See `web-deployment` skill's "Deliver the Link" section for the verified pattern (build first, verify, send link as its own message — never bury at end of status recap)

---

*Last updated: July 14, 2026 — Added standalone subdirectory deployment, GitHub API fallback, CDN propagation verification, path verification pitfalls*