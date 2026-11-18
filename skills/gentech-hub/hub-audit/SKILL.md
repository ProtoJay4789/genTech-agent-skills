---
name: hub-audit
description: "Audit GenTech hubs for stale data, broken HTML, and live data issues. Prevents GitHub Pages build failures and ensures dashboards stay fresh."
version: 1.12.0
author: gentech
tags: [gentech, hub, audit, dashboard, github-pages, html, validation]
---

# Hub Audit — Validate GenTech Hubs

**Purpose:** Audit all GenTech hubs (Jordan's and Vanito's) for data freshness, HTML integrity, and live data connectivity. Catches issues before they break pages.

## The Problem

- **Static hubs go stale** — No live data feeds, hardcoded HTML only
- **Broken HTML** — Unclosed tags, truncated JavaScript cause build failures
- **Missing data files** — Hub references JSON that doesn't exist
- **GitHub Pages failures** — "Build failed" emails from broken syntax
- **Stale timestamps** — Data never updates, shows old prices/stats

## The Solution

Systematic audit of all hub files:
1. Tag balance check (div, script, other elements)
2. Data source detection (fetch vs hardcoded)
3. Timestamp verification (lastUpdated fields)
4. External URL validation (404s, CORS)
5. File modification date review

## Audit Workflow

### Step 1: Find All Hubs

```bash
# Find HTML hub files (VPS deployment)
ls -la /var/www/gentechlabs/*.html
# Find hub data files
ls -la /var/www/gentechlabs/hub-vanita-data.json 2>/dev/null
```

**Expected files (VPS — deployed at `/var/www/gentechlabs/`):**
- `/var/www/gentechlabs/hub.html` — Main landing page
- `/var/www/gentechlabs/jordan.html` — Jordan's hub
- `/var/www/gentechlabs/vanito.html` — Vanito's hub (served at vanito.gentechlabs.net)
- `/var/www/gentechlabs/hub/data/` — Legacy hub system per-person JSON
- `/var/www/gentechlabs/hub-vanito-data.json` — JS-fetched data for vanito.html music tab

### Step 2: Check Tag Balance + File Permissions

```bash
# Check div tags (must be balanced)
grep -c '<div' /var/www/gentechlabs/vanito.html
grep -c '</div>' /var/www/gentechlabs/vanito.html

# Check script tags
grep -c '<script' /var/www/gentechlabs/vanito.html
grep -c '</script>' /var/www/gentechlabs/vanito.html

# Check fetch() calls (live data vs static)
grep -n 'fetch(' /var/www/gentechlabs/vanito.html

# ⚠️ CRITICAL: Check data file permissions
# Files created as root default to 600 — nginx reads as www-data
# A 403 Forbidden on a data file looks identical to a 404 to JS
for f in /var/www/gentechlabs/*.json /var/www/gentechlabs/hub/*.json; do
  [ -f "$f" ] && ls -la "$f" | awk '{print $1, $NF}'
done
# Expected: -rw-r--r-- (644) for all data files
```

**If unbalanced:** HTML syntax error → GitHub Pages will fail.

### Step 3: Detect Data Sources

```bash
# Search for fetch() calls (live data)
grep -n 'fetch(' /var/www/gentechlabs/vanito.html

# Check JS for expected data JSON
grep -n "\.json'" /var/www/gentechlabs/vanito.html

# ⚠️ CRITICAL: a page can have BOTH a fetch AND a frozen literal that wins
# Match an object literal whose values are numbers — the signature of a snapshot
awk '/<script/,/<\/script>/' <page>.html | grep -nE 'const [A-Za-z_]+ = \{[^}]*[a-z]+: *-?[0-9]'
```

**Classification:**
- ✅ **Live hub** — Has `fetch()` + `cache: 'no-store'`
- ⚠️ **Static hub** — No fetch calls, hardcoded only
- 🔴 **FROZEN SNAPSHOT** — has `fetch()` *and* a numeric literal object. **The fetch is decoration; the page renders the literal.** This reads as a live hub to every check that greps for `fetch(`.

**A hardcoded position object is the worst case, because it was TRUE when written.** Measured: a tracker
carried `const position = {avaxAmount: 2.19, rangeMin: 6.65, currentPrice: 6.71, ...}` beside a live price
fetch. The page rendered a position that had stopped existing, with a timestamp-free confidence — the same
defect class as quoting a six-week-old balance as current, and invisible to a "does it fetch?" audit.

**The fix is not to update the numbers — it is to delete the literal.** Every figure must arrive from one
generated JSON carrying its own read time, and the page must render nothing rather than a memory:

```javascript
let position = null;                       // no default: a default IS the bug
async function load() {
  const d = await (await fetch('live.json?t=' + Date.now(), {cache:'no-store'})).json();
  if (!d.trusted) throw new Error(d.warnings?.[0] || 'value unverified');
  return d;                                // d.position === null is a REAL answer: nobody read a wallet
}
```

- **`null` for "not read" is a finding; `0` is a different claim.** Keep `position`, `fees` and any
  claimable-amount field `null` when the source cannot produce them — a `0.00` there reads as "you earned
  nothing", which is an assertion the instrument never made.
- **Stamp the read, print the source.** `Live · read <time> · <source> · cross-checked (drift n%)` — a
  number whose age is visible cannot be mistaken for a current one.
- **A cross-check that disagrees must BLOCK the render, not warn inside it.** Beyond ~2% drift between a
  derived value and an independent feed, show the unavailable state — an on-page warning next to a confident
  number loses to the number.

### Step 4: Verify Data Freshness

```bash
# Fetch live data file and check timestamp
curl -s https://raw.githubusercontent.com/.../data.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('lastUpdated', 'NO TIMESTAMP'))"
```

**Freshness check:**
- ✅ Timestamp from today → fresh
- ⚠️ Timestamp > 7 days old → stale
- ❌ No timestamp field → unknown (may never update)

### Step 5: Test External URLs

```bash
# Check if data URLs return 200
curl -I https://api.dexscreener.com/...

# Check CORS errors
curl -s -H "Origin: https://gentechlabs.net" https://api.dexscreener.com/...
```

**If 404/CORS:** Data fetch will fail, dashboard shows nothing.

### Step 6: Check File Modifications

```bash
ls -lh /var/www/gentechlabs/hub*.html /var/www/gentechlabs/jordan.html /var/www/gentechlabs/vanito.html
```

**Recent = good:** Modified within last 30 days means active maintenance.

### Step 7: Check GitHub Actions Build Status

After deploying a hub update, verify GitHub Pages actually rebuilt:

```
GH_TOKEN=$(gh auth token 2>/dev/null)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/actions/runs?per_page=3&event=push" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('workflow_runs', []):
    print(f\"{r['head_commit']['message'][:50]:50s} {r['status']:12s}\")
"
```

If the most recent commit's status is `completed` + `success`, Pages is up to date.
If `in_progress` or `pending`, wait and re-check.
If `cancelled`, a newer commit superseded it — check the next one.

## Common Issues

### Issue 0: GitHub Merge Conflicts in JSON Data Files

**Symptom:** Hub fails to load, console shows "JSON.parse error" or "Unexpected token <".

**Detection:**
```bash
# Check for merge conflict markers (specific file)
grep -n "<<<<<<< Updated upstream" DeFi/defi-data.json

# Check ALL JSON files in the repo for markers (catches cross-contamination)
find . -name '*.json' -exec sh -c 'c=$(grep -c "<<<<<<< \|=======\|>>>>>>>" "$1" 2>/dev/null); [ "$c" -gt 0 ] && echo "🔴 $1 ($c markers)"' _ {} \;

# Verify JSON is valid
curl -s "https://raw.githubusercontent.com/.../defi-data.json" | python3 -m json.tool
# If error: Expecting value: line 1 column 1 (char 0) → file is corrupted
```

**Root Cause:** Git merge/rebase on another machine left unresolved conflicts pushed to `origin/main`.

**Two Cases:**

**Case A — Clean commit exists on remote:** The corrupted file is one of several commits. Restore from the last clean commit.
```
1. git log --oneline -135 | grep -v "auto: on-chain position update" | head -5
2. git reset --hard e363dc89
3. git show e363dc89:DeFi/defi-data.json > DeFi/defi-data.json
4. git push origin main --force-with-lease
```

**Case B — Remote HEAD is the corrupted commit:** No clean commit to restore from. Use a clean local copy (vault) as source of truth.
```
1. git fetch origin
2. git reset --hard origin/main            # Match remote exactly
3. cp ${VAULT_DIR}/defi-data.json DeFi/defi-data.json  # Vault is clean
4. python3 -m json.tool DeFi/defi-data.json  # Verify valid
5. git commit -m "fix: Repair defi-data.json (N merge conflict markers)"
6. git push origin main
```

**Real-world case (Jul 12, 2026):** POE2 build sync pushed defi-data.json with 57 merge conflict markers to origin/main. Hub Nightly Sync diverged locally and could not rebase. Used Case B: reset to origin/main, restore from vault, commit repair, push. Replaced 456 corrupted lines with 20 clean lines.

**Verification after fix:**
```bash
curl -s "https://raw.githubusercontent.com/GentechLabs/gentechlabs.github.io/main/DeFi/defi-data.json" | python3 -m json.tool > /dev/null && echo "VALID" || echo "CORRUPTED"
```

**Prevention:** Add a post-rebase conflict marker scan to the sync script's push pipeline (see `cron-truth-layer` Anti-Pattern 9 — Sequence Vulnerability). The `sanitize_json_text()` function auto-strips markers before they reach the remote.

**Reference:** `references/github-merge-conflict-resolution.md` — Complete resolution guide and prevention tips.

### Issue 1: Missing Hub Data Files

**Symptom:** Dashboard shows "Failed to load data" or empty sections. Console shows 404 error for data file.

**Detection:**
```bash
# Check if data file exists on GitHub
curl -I "https://raw.githubusercontent.com/.../hub-vanito-data.json"
# Output: HTTP/1.1 404 Not Found
```

**Root Cause:** Hub HTML references JSON data file that was never created or pushed to GitHub.

**Fix:**
1. Create placeholder JSON file with minimal structure (lastUpdated, name, avatar, tagline, status, projects[], stats{})
2. Commit and push to GitHub: `git add hub-vanito-data.json && git commit -m "feat: Add placeholder data file" && git push origin main`
3. Verify file is accessible: `curl -s "https://raw.githubusercontent.com/.../hub-vanito-data.json" | python3 -m json.tool`

**Template:**
```json
{
  "lastUpdated": "2026-07-01T16:30:00.000Z",
  "name": "Vanito",
  "avatar": "Vanito",
  "tagline": "PoE2 Warrior",
  "steamId": "76561198132811363",
  "status": "Active",
  "projects": [],
  "stats": { "level": 0, "builds": 0, "gold": 0 }
}
```

**Reference:** `references/missing-hub-data-files.md` — ⚠️ *not written.* That path is named in this doc but exists on no seat and has never been in git. The creation guide the pointer promises is the JSON template directly above plus the Issue-1 steps below — read those; do not go looking for the file.

### Issue 2: Static Hub (No Live Data)

**Symptom:** Hub shows static values, never updates.

**Detection:** No `fetch()` calls, no `DATA_URL` constant.

**Fix:**
1. Create JSON data file with timestamps
2. Add `fetch()` with cache-busting
3. Use `cache: 'no-store'` option

**Example:**
```html
<script>
const DATA_URL = 'https://raw.githubusercontent.com/.../data.json';

async function loadData() {
    const resp = await fetch(DATA_URL + '?' + Date.now(), { cache: 'no-store' });
    const data = await resp.json();
    // render data
}
</script>
```

### Issue 8: Missing Data File Causes JS JSON Parse Error (Not Direct 404)

**Symptom:** Feature tab shows "Error loading [feature]" but page itself loads fine. Browser console shows `SyntaxError: Unexpected token '<', "<html>... is not valid JSON`. No 404 visible to the user.

**Root cause:** JS `fetch('data.json')` resolves to a URL where the file doesn't exist. Nginx returns a 404 HTML page. The fetch promise resolves successfully (connection worked), but `response.json()` fails because the body is HTML, not JSON. The catch block renders the generic error message — the 404 is hidden from the user.

**Diagnosis chain:**
```bash
# 1. Does the file exist on the server?
ls -la /var/www/gentechlabs/hub-vanito-data.json

# 2. What content-type is nginx returning?
curl -sI "https://vanito.gentechlabs.net/hub-vanito-data.json" | grep -i content-type
# text/html = 404 error page. application/json = correct.

# 3. Check nginx access log for the actual HTTP status
tail -n 20 /var/log/nginx/*.access.log 2>/dev/null | grep "data.json"
```

**Fix — Two parts:**

**Part A — Create the data file** with valid JSON matching the JS expected schema (check `fetch()` call in the HTML for the expected structure).

**Part B — Fix file permissions** — files created as root default to 600, but nginx reads as www-data:
```bash
chmod 644 /var/www/gentechlabs/hub-vanito-data.json
chown www-data:www-data /var/www/gentechlabs/hub-vanito-data.json
```

**Verification:** `curl -s "https://example.com/data.json" | python3 -m json.tool` should return valid JSON with `content-type: application/json`.

**Prevention:** Any data file served by nginx must be 644 + www-data. After creating, always check content-type header before assuming the file is accessible.

**Real-world case (Jul 25, 2026):** Vanito's hub music tab showed "Error loading music". The JS fetched `hub-vanito-data.json` which didn't exist on the VPS. Fixed by creating the file and setting correct permissions.

### Issue 9: Unclosed HTML Tags

**Symptom:** GitHub Pages build fails with "Unclosed tag" error.

**Detection:** Unbalanced div/script tags.

**Fix:** Add missing closing tags. Use `grep` to find where the opening tag has no closing match.

### Issue 10: Data Pushed to Pages Repo But VPS Webroot Never Updated (NEW — Sep 3, 2026)

**Symptom:** Sync pipeline reports success (repo commit + push all green), raw.githubusercontent.com serves fresh data, but the LIVE site (`gentechlabs.net/defi-data.json`) still serves weeks-old data.

**Root cause:** `gentechlabs.net` and `vanito.gentechlabs.net` are served by **nginx on the VPS from a plain webroot** (`/var/www/gentechlabs/`) — NOT from a git checkout, NOT from GitHub Pages. Pushing to the Pages repo only updates GitHub; nothing copies the fresh JSON into the webroot. The pipeline was verifying the wrong target.

**Deployment topology (three targets, verify the SERVING one):**
```
vault source → Pages repo (github) → [NOT SERVING for gentechlabs.net]
                                  └→ VPS webroot /var/www/gentechlabs/ ← nginx serves THIS
```

**Detection:**
```bash
# Compare webroot vs repo copy directly:
diff <(python3 -c "import json; print(json.load(open('/var/www/gentechlabs/defi-data.json'))['lastUpdated'])") \
     <(python3 -c "import json; print(json.load(open('(GitHub repo, not on this host: gentechlabs.github.io/)DeFi/defi-data.json'))['lastUpdated'])")
# Also confirm the webroot is NOT a git checkout:
cd /var/www/gentechlabs && git rev-parse --is-inside-work-tree 2>/dev/null || echo "plain webroot — push does NOT update it"
```

**Fix — add a webroot deploy step after the push step:**
```python
# Step 5.5: Deploy to VPS webroot (nginx serves /var/www/gentechlabs)
import shutil
shutil.copy2(f"{REPO_PATH}/DeFi/defi-data.json", "/var/www/gentechlabs/defi-data.json")
os.chmod("/var/www/gentechlabs/defi-data.json", 0o644)
```

**Real-world case (Sep 3, 2026):** defi-data.json served Aug 11 data on Sep 3 (23 days stale) despite the sync script "working" — the script pushed to the Pages repo but never touched `/var/www/gentechlabs/`. Fixed by adding the webroot copy step; live site verified fresh within one run. Note: the Pages repo's remote already points at GentechLabs (`gentechlabs.github.io`) — the legacy folder name `/root/ProtoJay4789.github.io` is just a local directory name, not the deploy target.

**Lesson: an audit must trace data to the SERVING target.** A pipeline can be green end-to-end (vault fresh, repo pushed, CDN reachable) while the user sees stale data. Always finish with: fetch the live URL a real browser would hit and compare `lastUpdated` against the source.

### Issue 3: Broken Data URL

**Symptom:** Dashboard shows "Failed to load data" or empty sections.

**Detection:** `curl -I` returns 404, or browser console shows CORS error.

**Fix:**
- Correct the URL path
- Add CORS headers if using custom API
- Use `no-cache` query string to bypass CDN caching

### Issue 4: Stale Timestamp

**Symptom:** Dashboard shows prices from weeks ago.

**Detection:** `lastUpdated` field is old or missing.

**Fix:**
- Update data pipeline to write current timestamp
- Add cron job to refresh data daily
- Add age indicator on dashboard (e.g., "Updated 2h ago")

### Issue 5: Live Verification False Failure (SHA-Specific URL)

**Symptom:** Hub sync script reports "Live verification: HTTP 404" for a defi-data.json URL, but the data file is valid and GitHub Pages responds 200.

**Root cause:** The verification function used the local `git rev-parse HEAD` SHA to build a `raw.githubusercontent.com/{sha}/path` URL. If the local commit was never pushed (push failed, rebase conflict), the SHA doesn't exist on GitHub → 404. The function reported this as a data issue when it was actually a deployment gap.

**Fix — Fallback URL chain:** Try the SHA-specific URL first (cache-busting), then fall back to the `main` branch ref. This way a failed push doesn't cascade into a false 404 alarm.

```python
def verify_live():
    """Verify with URL fallback chain."""
    # 1. Try SHA-specific URL (cache-busting, accurate for just-pushed commits)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], ...).stdout.strip()
    if sha:
        urls_to_try.append(
            f"https://raw.githubusercontent.com/user/repo/{sha}/path/data.json"
        )
    # 2. Fall back to stable branch ref
    urls_to_try.append(
        "https://raw.githubusercontent.com/user/repo/main/path/data.json"
    )

    for url in urls_to_try:
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            # Validate required sections...
            if all_sections_present:
                return True, []
            return False, missing
        except Exception:
            continue
    return False, ["All verification URLs failed"]
```

**Why not just use `main` always:** SHA-specific URLs bypass CDN caches — important for verifying fresh pushes. The fallback ensures the verification still works when the SHA URL fails.

**Real-world case (Jul 12, 2026):** hub-sync-nightly.py used only SHA-specific URL. When git push failed (divergent remote with 26 commits), `verify_live()` returned 404 for the unpushed SHA. Fixed by adding `main` branch fallback.

### Issue 6: Deployed Content Stale on GitHub Pages (CDN Cache)

**Symptom:** New content confirmed via raw.githubusercontent.com or Git blob API, but GitHub Pages still shows old version.

**Root cause:** Pages uses CDN caching (2-5 min typical) + GitHub Actions build queue.

**Diagnosis:**
1. Check blob content (definitive, no cache): `curl -s -H "Authorization: token $GH_TOKEN" "https://api.github.com/repos/GentechLabs/gentechlabs.github.io/git/blobs/<SHA>" | python3 -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode()[:200])"`
2. Check Actions build status (see Step 7 above)
3. If build completed successfully but Pages still stale → CDN propagation (wait 2-5 min)

**Prevention in hub dashboards:** Add a `lastUpdated` timestamp rendered from the JSON data file rather than relying on the page serving timestamp. Users see when data was refreshed, not when the page was deployed.

### Issue 7: raw.githubusercontent.com Returns 404 for main Branch (CDN Gap)

**Symptom:** `curl -I "https://raw.githubusercontent.com/owner/repo/main/path/file.json"` returns HTTP 404, but the file is confirmed valid via the GitHub API and the Actions build completed successfully.

**Root cause:** `raw.githubusercontent.com` is a separate CDN from the GitHub API and GitHub Pages. It can return 404 for files that exist on the `main` branch when:
- The CDN edge node hasn't picked up the latest commit (cache propagation delay)
- The file path is case-sensitive and doesn't match (e.g., `DeFi/` vs `defi/`)
- The raw CDN has a transient outage for a specific repo/branch combination

**Real-world case (Jul 21, 2026):** Hub Nightly Sync pushed `DeFi/defi-data.json` to `ProtoJay4789.github.io` (commit `370e3248`, valid JSON, 15/15 sections, Actions build completed with `success`). But `raw.githubusercontent.com/ProtoJay4789/ProtoJay4789.github.io/main/DeFi/defi-data.json` returned 404. The GitHub API confirmed the blob was valid (13,595 bytes, all sections present). The raw CDN was simply not serving the file.

**Diagnosis — Three-layer verification chain:**

```bash
# Layer 1: raw.githubusercontent.com (fastest, but unreliable)
curl -sI "https://raw.githubusercontent.com/owner/repo/main/path/file.json"
# -> 404 does NOT mean the file is missing

# Layer 2: GitHub API blob content (definitive, no cache)
GH_TOKEN=$(cat /path/to/token)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/owner/repo/contents/path/file.json?ref=main" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Size: {d.get(\"size\")}, SHA: {d.get(\"sha\")[:12]}')"
# -> If this returns valid data, the file IS on GitHub

# Layer 3: GitHub Actions build status (confirms deploy ran)
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/owner/repo/actions/runs?per_page=3&event=push" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('workflow_runs', []):
    msg = r.get('head_commit', {}).get('message', '?')[:60]
    print(f'{msg:60s} {r[\"status\"]:12s} {r[\"conclusion\"] or \"-\":12s}')
"
# -> If latest commit shows completed + success, data is deployed
```

**Fix — Use GitHub API as authoritative source, not raw CDN:**

When verifying data after a push, use this priority:
1. **GitHub API blob content** (definitive, no cache) — check file exists and is valid JSON
2. **GitHub Actions build status** — confirm deploy ran for the expected commit
3. **raw.githubusercontent.com** — best-effort, treat 404 as "CDN not propagated" not "data missing"

```python
def verify_data_on_github(repo_owner, repo_name, path, token):
    """Verify data exists on GitHub via API (not raw CDN)."""
    import urllib.request, json

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}?ref=main"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    })
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())

    # Decode base64 content and validate JSON
    import base64
    content = base64.b64decode(data["content"]).decode()
    parsed = json.loads(content)
    return parsed, data["sha"]
```

**Key insight:** `raw.githubusercontent.com` 404 is NOT evidence of a data problem. It is a CDN propagation issue. The GitHub API is the authoritative source. Always use the API for verification, not the raw CDN.

**Prevention in hub sync scripts:** Add a GitHub API verification step as the primary check, with raw CDN as a best-effort secondary. Never report "data missing" based on raw CDN 404 alone.

## Auditing a PRODUCT-LISTING page — a rendered card is not a working product

A marketing/hub page that names products is making **capability claims**, and the audit question is not
"does the card render" but **"is there a thing behind it."** The two are unrelated: a card is a few
`<div>`s, and it renders identically whether the product is live, blocked, unfinished, or never existed.

**Procedure — every card gets one of three verdicts, traced to an artifact:**

1. **Enumerate the cards** from the served HTML (not the source you assume is deployed).
2. **Find what each names** — an endpoint path, a service name, a skill, a file. A card with no address of
   any kind is already `UNPROVEN`.
3. **Probe the address.** Endpoint → call it and read the body. Local artifact → does anything *route* to it?
   Skill → does the directory hold runnable code, or only markdown references?
4. **Record `WORKING` / `NOT LIVE (reason)` / `NO BACKEND`.** "The page mentions it" is not a verdict.

Measured on one four-card gaming tab: **zero of four worked** — an advertised endpoint answered `404
service_not_found`, one product's skill directory held **eleven markdown reference files and no code**, one
was a local HTML file with no route to it, and one was a folder of JSON no endpoint reads. Every card was
markup-complete and the tab rendered perfectly.

- **Test for a catch-all BEFORE you trust a single link on the host.** A wildcard site returns `200` and the
  same bytes for paths that never existed, so a link audit of it reports every URL healthy. Compare a nonsense
  sibling's **byte count**, and if it matches the real page, say the link audit is void — see
  `verification-vantage` → *A wildcard router answers 200 for paths that do not exist*.
- **Audit the CLAIM across tabs, not just within one.** The same product can be declared *"Not live — blocked
  by policy"* on one tab and sold as a shipping product on another. One page carrying two opposite statements
  about one thing is a finding in its own right, and it is invisible to any audit that reads one section.
- **An advertised request example is a claim that must be re-run.** If the page shows `GET /v1/…` with a
  sample response, execute it. A 404 under a published example is worse than no example — it is a documented
  promise the system breaks on contact.
- **Find the SOURCE before you edit the artifact.** A deploy can be a managed project (Pages/Workers) whose
  source is not on this host. Patching the deployed file directly **works today and is overwritten by the
  next deploy from the real source** — so name which of the two you are doing, and if the source is missing,
  that gap is the finding to report, not a detail to route around.
- **Taking a product OFF a page is not killing the project.** Move it to an explicit *In development* block
  that states its real state — the same discipline as *UNKNOWN, never 0*: the reader must be able to tell
  "not built yet" from "removed" and from "broken". Deleting the card silently destroys the only record that
  the work was ever intended.

## Audit Report Template

```markdown
# Hub Audit Report — $(date)

| Hub | File | Last Modified | Data Status | Issues |
|-----|------|---------------|-------------|--------|
| Landing | hub.html | $(date) | ✅ STATIC | Links to Jordan, Vanito, Portfolio |
| Jordan | jordan.html | $(date) | ✅ STATIC | 4 tabs, no data fetches |
| Vanito | vanito.html | $(date) | ✅ LIVE | Music data: hub-vanito-data.json |

## Deployment Verification

- [ ] Raw content accessible via raw.githubusercontent.com
- [ ] Git blob content matches expected
- [ ] GitHub Actions build completed with `success`
- [ ] GitHub Pages serves correct content (after CDN propagation)
- [ ] VPS webroot copy (`/var/www/gentechlabs/*.json`) matches the repo copy — nginx serves the webroot, not GitHub (Issue 10)
- [ ] LIVE URL fetched (not pipeline output) and `lastUpdated` is fresh

## Issues Found

### Student Hub — Archived (first student departed Aug 2026)
- **Status:** ARCHIVED — first student departed Aug 2026; template removed. Method kept in 10-Labs/academy-playbook/orchestrator-playbook-distilled.md

## Recommendations

1. Deploy a student hub only when Jordan greenlights a new student
2. Add lastUpdated timestamps to all data files
3. Test data URLs weekly
```

## Fixing a dashboard that renders placeholders — the fix that lies better than the bug

A hub that shows `Connecting…`, `Loading…` and `—` in every field is the **honest** failure state: it looks
broken, so someone goes looking. The repair has a trap in it that is worse than the fault.

**Procedure, in this order:**

1. **Enumerate EVERY `fetch()` in the SERVED html, not just the ones that failed for you.** A page can carry
   four fetches all broken by the same stale constant; finding two and fixing two leaves two dead panels and
   reads as a partial fix. `grep -oE "fetch\('[^']+'" page.html | sort -u` and count them against the number
   of panels on the page.
2. **A `raw.githubusercontent.com` 404 can be a WRONG OWNER, not a CDN gap.** Before applying Issue 7, read
   the owner/repo in the URL and check the same path under every owner the fleet publishes from — a hub
   pinned to a repo that never held `DeFi/` 404s forever and no amount of cache-waiting fixes it. Distinguish
   the two: a CDN gap gives 404 on a path that exists under that owner (verify via the API, Issue 7 step 2);
   an owner drift gives 404 under one owner and **200 under another**.
3. **Before writing "fixed": every payload must PARSE and carry its own `lastUpdated` — and you must print
   the AGE of each feed.** An owner swap that makes the numbers appear is not a fix if the numbers are
   months old.

> **A dashboard full of old numbers is worse than a dashboard full of dashes.** Dashes announce a fault;
> current-looking figures with no age beside them are read as today's. "It is connecting again" and "it is
> telling the truth" are two different claims, and only the second one is worth shipping.

**So the freshness bar is part of the repair, not a nice-to-have.** Render, per feed, the source's own
`lastUpdated` and its age, from the payload rather than the deploy time. Two failure modes that look
identical from outside must read differently on the page: *feed unreachable* and *feed stale*.

- **A committed JSON carrying git conflict markers has no correct side — do not hand-merge it.** Nested or
  long-aged markers mean nobody resolved a stash; picking a branch manufactures a number. Report it as
  `source is not valid JSON`, keep the panel in its unavailable state, and have the generator REPUBLISH the
  file. Issue 0 covers resolution when a clean ancestor exists; when it does not, publishing nothing is the
  correct output.
- **A freshness bar that reads `Data: connecting…` at rest is decorative until its JS fills it.** Load the
  page and confirm the bar resolves to real ages; a bar that can only ever show "connecting" is the
  FROZEN SNAPSHOT class wearing a freshness label.
- **Render-clean is not markup-clean — the placeholder you overwrite at runtime comes back when the script
  fails.** A page can render zero `Loading...` strings and still carry them in the SERVED source, because the
  bar and the pair-info write over those nodes on success. If the fetch 404s or a line throws, the reader sees
  `Loading...` again and it reads as a slow page, not a broken one. **Start those nodes EMPTY and let the
  failure state be the explicit `UNKNOWN`/unavailable text** — then assert both: `grep -c 'Loading\.\.\.' served.html`
  is 0 **and** the render shows no placeholder.
- **Set the two thresholds once and name them on the page**: `>3 days = STALE` (a feed that skipped a cycle),
  `>30 days = ARCHIVED` (a feed nobody is writing). Two labels, not one — "old" collapses *the producer stopped*
  into *the producer is late*, and only one of those is a deploy problem.
- **Do not hand-write this check per session: `scripts/hub-freshness-guard.py` is the tested one.** It parses
  each feed, reads its own `lastUpdated`, prints `UNKNOWN` (never `0`) when a source cannot be read, exits
  `0 fresh / 1 stale-archived / 2 UNKNOWN`, and its `--selftest` (12 checks) plants the failures — an
  unparseable payload, a 90-day timestamp, an unreachable host, a missing timestamp. **A guard against staleness
  that a fetch failure scores as healthy is the same bug one level up**, which is why the UNKNOWN path has its
  own tests.

## Pitfalls

### Removing a DOM Node Without Its Writer Blanks the Page

When you delete a tile/row from a hub generator, delete the JS that writes to it **in the same
edit**. A writer left behind behaves one of two ways, and the difference is an outage:

- `document.getElementById("x").textContent = v` — **throws a TypeError on null**. Inside a single
  render pass this aborts **every field below it**, so the page goes blank rather than dropping one
  tile. The symptom looks like "the whole page is broken", not "a tile is missing".
- `const dset = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; }`
  — null-safe, silently no-ops, no harm.

**Check which form the writer uses BEFORE removing the node:** `grep -n 'getElementById("x")' <generator>`.
If it is the direct form, remove or guard it in the same change. Removing a node and leaving its
writer is how a tidy-up becomes an outage.

### A Card Emitted After the Container Closes Renders Full-Bleed

A block placed **after** the page wrapper's closing `</div>` is outside the max-width container.
It renders full-bleed and unaligned with every other card — this reads to the user as "the page
looks jumbled up", and it is a layout leak, not a style choice.

**Check:** count `<div` vs `</div>` (already in Step 2) **and** confirm the last card sits inside
the wrapper. Balanced div counts plus correct nesting order is the proof; balanced counts alone
can still hide a card in the wrong container.

### Verify a JS-Rendered Page by Running Its OWN Script (tag balance is not proof)

Tag balance proves the document **parses**. It does not prove the page **renders** — a shipped
script can throw on the first field and leave everything below it blank while the HTML is perfectly
valid.

To prove what a reader actually sees:

1. Slice the page's `<script>` **byte-for-byte out of the SERVED html** (never a re-implementation —
   a re-implementation proves only that your copy works).
2. Run it in node under a minimal DOM shim plus a `fetch` shim that reads the local data files.
3. Print the `textContent` of the element ids that matter.
4. **Run it twice**: once against the real payload, once against a deliberately degraded one (e.g.
   `{"status":"unknown"}`). One run alone proves nothing about the failure path.

`scripts/render-page-check.js` does this. `threw: None` plus the expected values is the proof.
A node that should have been removed reads `<unset>` — which is the assertion for the removal itself.

**A RED from this kind of harness is a claim about the HARNESS until proven otherwise.** The check
depends on a DOM shim, a `fetch` shim and a slice of the page's own source, and each of those is a
belief that can be wrong — so a failure sends you to fix the page when the fault is in the check.
Both bugs found while building one such harness were **its own**: a boundary marker that captured
prose instead of code, and a DOM stub that captured the FIRST definition and never saw the later
one. Before editing the page, re-read the harness: which exact bytes did it slice, and which stub
did it actually bind? Then confirm the harness can go RED on a real fault (run it against a
deliberately broken payload) — a check that has only ever been green is not evidence.

## Presentation Rules for Hub Pages

Standing preferences for what a hub page shows. These are about **emphasis**, not deletion.

- **Lead with the FLOW, not the stock.** The headline is what the position is EARNING over a period
  (a rate), not how much capital sits in the pool. A stock is the wrong headline for a book that
  churns.
- **Demote, never delete.** When a number stops being the headline, drop it lower on the page but
  keep it in the JSON payload, where it still drives decisions. Removing it from the view is not
  removing it from the system.
- **Do not surface the operator's idle admin gas float.** Wallet dust set aside for gas is not a
  position and not the reader's business. Show the autonomous **decision** (HOLD / act, and why),
  not the pocket change — the reader should come away knowing the system manages itself.
- **UNKNOWN, never 0.** Any read that cannot be produced renders `UNKNOWN` *with its reason*. A `0`
  means "measured, and it is genuinely zero". A `0` that means "could not read it" is the most
  repeated bug class in these hubs.
- **An honest zero must EXPLAIN itself — a bare `$0.00` is indistinguishable from a broken page.**
  The inverse of the rule above: where a zero is real (capital deployed but out of range, so nothing
  is being collected), print the zero *with its cause* — `WHY THIS IS $0.00 — the book is OUT OF
  RANGE, fully deployed and collecting nothing`. A reader cannot tell a true zero from a failed
  render, so a page that shows one without a reason trains them to distrust every number on it.
- **One RATE, several horizons — never several independently-computed numbers.** When a page shows
  earnings per day / week / month, derive all three from a SINGLE rate (multiply it out) and say in
  the card that they are the same rate at three spans. Three independent estimates can disagree with
  each other and with the goal shown beside them, and a reader who spots the contradiction stops
  trusting the whole page.
- **Reuse the rate that already drives the goal.** If a rank/target figure elsewhere on the page
  computes its own "per day", do not introduce a second source for the tiles — the page would then
  print two different per-day numbers. Where a genuinely different second source exists, carry it in
  the payload with its provenance rather than averaging two things that answer different questions.
- **Label an estimate as an estimate, in the artifact.** A figure projected from the deployed book is
  not realised income, and the tile must say *estimated* — the reader is who will otherwise quote it
  as settled. Pair it with the note that realised fees are the ledger's job.
- **A request to remove something from the PAGE is not a request to remove the FEATURE.** "Take the
  auto-compound out, I don't mean the feature, I mean on the page" is a display change: swap the
  tiles and the card, leave the mechanism and its payload fields untouched. Read the scope from the
  sentence — *on our pages* is a lens change, never a deletion — and say in the reply which of the
  two you did.
- **Put the picture at the top.** For a position/liquidity page the shape chart goes above the
  numeric tiles: what the money looks like first, the numbers underneath.
- **A LOSS IS NOT A DASHBOARD FEATURE — record it in the brain, never render it on someone's hub.**
  Jordan, on showing an unreachable position on a collaborator's page: *"it's gonna be a reminder of the
  money we lost, and my cousin is probably gonna ask me not to show that."* **A hub is a place a person
  opens; a memorial is not a hub.** This is a stronger instruction than *demote, never delete* — some
  content must leave the page entirely — and it is still **not deletion**: the record moves to the brain
  (`Treasury/orphaned-positions-record-*.md`) as a **recovery ledger**, framed by what can still be done
  rather than what was lost.
  - **Ask the owner, not the data.** Whether a fact belongs on a page is the subject's call when it is
    their money and their page. Present the option and the reason; do not decide by what is measurable.
  - **Reduce the page to forward-looking state.** The page keeps the pool, and its own error path carries
    one honest line — *"No active position tracked. This hub shows live positions only."* Verified by
    running the page's script: the sentence renders and **none of the old figures appear**.
  - **Distinguish the two absences in the record**: *gone from the chain* (nothing to track) vs *gone from
    reach* (trackable, key lost). Flattening them into one "lost" bucket loses the only fact that matters
    for a future recovery.
  - **No cron on a memorial.** Re-reading a position nobody can reach is motion, not information — read it
    when a recovery attempt makes it relevant.

### Don't Assume No News Is Good News
Just because the hub loads in browser doesn't mean it's correct. Check the actual data values and timestamps.

### GitHub Pages Cache Can Mislead
Adding `?Date.now()` isn't always enough. Use `cache: 'no-store'` option in fetch.

### Compression Can Timeout Long Sessions
This session used `/compress` which timed out due to context length. Not critical — just cleanup. Don't retry if not needed.

### MiMo-v2.5 Leaves Broken HTML
MiMo hits timeouts on long builds and leaves incomplete code. Use GLM-5.2 for all HTML/dashboard work to get complete patches.

### Stale Data With Zero Errors = Check the Producer Cron EXISTS
A data file weeks stale with NO failure logs usually means the sync script lost its cron job (consolidation drops orphaned jobs silently) — not that the script is broken. Check `hermes cron list | grep <script-name>` FIRST; a script with zero jobs runs never. Proven Sep 3, 2026: hub-sync-nightly.py had no job AND a rebase-cascade bug; re-wired as `22b2467ded55` (22:10 UTC nightly, no-agent) with `--failure-deliver telegram` so future breaks alert the principal instead of dying silently. While there, prefer merge `--strategy-option theirs` over rebase for fully-regenerated files (see cron-truth-layer Anti-Pattern 11).

### One Failed Probe ≠ Down (Cloudflare/IPv6 Flap)
A single curl returning 000/timeout can be a transient edge/IPv6 flap — the same URL connected fine over IPv6 seconds later (200 in 70ms). Before declaring a subdomain down: retest http AND https, and confirm the vhost exists in `nginx -T` server_name output. Escalate only on repeated failures.

**And before either: read the DNS zone, because a guessed hostname can never have existed.** `000` from a
subdomain you thought of is not a broken deploy — it is often NXDOMAIN. Query the zone's records directly
(`GET /zones/<id>/dns_records`) and compare against what the pages actually link to; the hub may live at a
different name than the one you assumed, and an agent that hands the user a guessed URL sends them to a blank
page and then diagnoses a deploy that was never involved. **Say which you measured: NO DNS RECORD (the name
never existed) vs RECORD PRESENT BUT NOT SERVING (a real outage).**

**A record's CONTENT is not the host's BEHAVIOUR — never call a hostname dead from its A record.** A zone full
of proxied names carries an anchor address that is not an origin at all (a proxy range, or an RFC 5737
`192.0.2.x` documentation address placed there on purpose). Reading `A → 192.0.2.1` and concluding "can never
reach a server" is measuring the wrong layer: with a Worker route or a Pages custom domain in front, the
request never touches that address. **Fetch the hostname before judging it** — `curl -sI` plus a real body
fetch is one second of work — and then look for a route that answers first (`/zones/<id>/workers/routes`).
Control: a nonsense sibling subdomain that returns nothing proves the name is not a wildcard, so a `200` on the
real one is a serving route, not a catch-all. The honest phrasing when it does serve is *"the record is an
anchor, the route serves; consistency only"* — not a fault, and not an outage.

## Integration with Gentech Ops

Run hub audit weekly as a cron job:

```bash
# cron: hub-audit-weekly.sh
# Runs every Sunday at 10 AM

echo "Hub Audit Report - $(date)" > /tmp/hub-audit-report.md

# Run all checks on VPS hub files
for hub in hub.html jordan.html vanito.html; do
    echo "Checking $hub" >> /tmp/hub-audit-report.md
    bash ${PROFILE_DIR}/skills/gentech-hub/hub-audit/scripts/check-hub-tags.sh "/var/www/gentechlabs/$hub" >> /tmp/hub-audit-report.md 2>/dev/null || echo "Tag check skipped" >> /tmp/hub-audit-report.md
    bash ${PROFILE_DIR}/skills/gentech-hub/hub-audit/scripts/check-hub-data.sh "/var/www/gentechlabs/$hub" >> /tmp/hub-audit-report.md 2>/dev/null || echo "Data check skipped" >> /tmp/hub-audit-report.md
done

# Check data file permissions
ls -la /var/www/gentechlabs/hub-vanita-data.json >> /tmp/hub-audit-report.md 2>/dev/null || echo "hub-vanita-data.json: MISSING" >> /tmp/hub-audit-report.md

mv /tmp/hub-audit-report.md ${VAULT_DIR}/11-Mess Hall/hub-audit-$(date +%Y%m%d).md
```

## Linked Files

**Scripts:**
- `scripts/check-hub-tags.sh` — Automated tag balance verification
- `scripts/check-hub-data.sh` — Data source validation and URL testing
- `scripts/render-page-check.js` — Run a hub page's OWN `<script>` under a DOM shim to prove it
  actually renders (healthy payload + degraded payload). Tag balance is not proof of rendering.
- `scripts/hub-freshness-guard.py` — Parse + age every feed, `UNKNOWN` (never `0`) when a source cannot be
  read, exit `0/1/2`, `--selftest` plants the failures. Schedule it behind a wrapper that turns a finding into
  exit 0 (see the exit-code note at the top of the file); a nonzero-on-finding guard is recorded as a failed job
  on every run and gets muted.

**References:**
- `references/github-pages-build-errors.md` — ⚠️ *not written* (named here and in `## References` below, but absent from every seat and from git). The build-failure patterns are the numbered Issues above and the Deployment Verification checklist.
- `references/github-merge-conflict-resolution.md` — How to fix merge conflicts in JSON data files on GitHub
- `references/missing-hub-data-files.md` — ⚠️ *not written* (see the inline JSON template in Issue 1).
- `references/personal-hub-link-pattern.md` — Link pattern for personal hubs (Christel, Vanito, others). Always use deployed GitHub Pages URLs, not raw GitHub markdown files.

Use these scripts for automated audits and quick checks.

## References

- `references/github-pages-build-errors.md` — ⚠️ *not written* (duplicate of the Linked Files pointer above; see the numbered Issues in this doc).
- `scripts/check-hub-tags.sh` — Tag balance verification script
- `scripts/check-hub-data.sh` — Data source validation script

## Version History

- **1.12.0** — Added **fixing a dashboard that renders placeholders**: enumerate every `fetch()` in the served
  html (not only the ones that failed); a raw-CDN 404 may be a WRONG OWNER rather than a CDN gap, and the two
  are distinguished by whether the path answers under a different owner; a repair is not done until each
  payload PARSES and its own `lastUpdated` age is printed. Added the governing rule — **a dashboard full of
  old numbers is worse than a dashboard full of dashes** — and made the per-feed freshness bar part of the
  repair. Added: do not hand-merge a long-aged conflict-marked JSON (republish it); a freshness bar stuck on
  `Data: connecting…` is decorative. Extended *One Failed Probe ≠ Down*: read the DNS zone first, because a
  guessed hostname can be NXDOMAIN rather than broken — report NO DNS RECORD and RECORD NOT SERVING as
  different findings.

- **1.11.0** — Added **auditing a PRODUCT-LISTING page**: a rendered card is not a working product. Every card
  gets `WORKING` / `NOT LIVE (reason)` / `NO BACKEND` traced to an artifact (endpoint probe, route, or runnable
  code); test for a catch-all before trusting any link on the host; audit the claim ACROSS tabs, since one page
  can declare a product blocked and sell it elsewhere; re-run any published request example; find the SOURCE
  before editing a deployed artifact; and move an unbuilt product to an explicit *In development* block rather
  than deleting the card.
- **1.10.0** — Step 3 gained the **FROZEN SNAPSHOT** class: a page can carry a `fetch()` *and* a numeric
  literal object, so a "does it fetch?" audit grades a dead page as live. Added the deletion-not-recomputation
  fix, `null`-vs-`0` discipline, and the rule that a disagreeing cross-check blocks the render rather than
  warning beside it. Presentation Rules gained **a loss is not a dashboard feature** — record it in the brain,
  ask the owner, reduce the page to forward-looking state, and distinguish *gone from the chain* from *gone
  from reach*.
- **1.9.1** (Council 2026-09-27) — The 1.9.0 material was authored on **gentech-treasury** and never reached the
  shared core, so three seats ran the older copy until the Council's drift gate caught it. **Promoted here
  byte-for-byte — no content changed.** The gate was green because every copy of this file is seat-agnostic: the
  divergence was invisible to anything but a file-by-file hash across all four seats.
- **1.9.0** — Presentation Rules extended for earnings/rate readouts: an honest zero must explain
  itself (a bare `$0.00` is indistinguishable from a broken page); one RATE across several horizons
  rather than several independently-computed numbers; reuse the rate that already drives the goal
  so the page cannot print two per-day figures; label a projection as *estimated* inside the
  artifact; and a request to remove something from the PAGE is a display change, never a feature
  removal. Added: a RED from the render harness is a claim about the HARNESS until proven
  otherwise (slice boundaries and DOM stubs were the two bugs that made it lie).
- **1.8.1** (Council 2026-09-26) — Corrected two dangling reference pointers:
  `references/github-pages-build-errors.md` and `references/missing-hub-data-files.md` were named in this
  doc (twice each) but existed on no seat and in no git revision. They are now marked *not written* with a
  pointer to the inline material that actually carries the guidance, instead of authoring files that would
  only duplicate the issue list and the Issue-1 JSON template. Found by the Council's reference-resolution
  check while promoting the 09-25 hub-audit pitfalls into the shared core.
- **1.8.0** — Added Pitfalls: removing a DOM node without its writer blanks the page (direct
  `getElementById().textContent` throws on null inside the single render pass; a `dset`-style
  null-guarded writer no-ops safely — check which form before removing). Added: a card emitted
  after the container closes renders full-bleed (div balance plus nesting order is the proof).
  Added: verify a JS-rendered page by running its OWN shipped script against a healthy AND a
  degraded payload — tag balance is not proof of rendering. Added `scripts/render-page-check.js`
  and a Presentation Rules section (lead with the flow not the stock; demote don't delete; never
  surface the idle gas float; UNKNOWN never 0; picture at the top).
- **1.7.0** (Sep 3, 2026) — Added pitfalls: stale-data-with-zero-errors → check producer cron exists (orphaned sync script pattern); single-probe flap ≠ down (IPv6/Cloudflare transient).
- **1.6.0** (Sep 3, 2026) — Added Issue 10 (webroot deploy gap: nginx webroot ≠ Pages repo; verify the SERVING target). Deployment Verification checklist extended.
- **1.5.1** (Jul 25, 2026) — Updated hub inventory: Christel removed, Academy student template added.
- **1.4.0** (Jul 21, 2026) — Added Issue 7 (raw.githubusercontent.com 404 CDN gap). Three-layer verification chain: GitHub API blob content (authoritative) > Actions build status > raw CDN (best-effort).
- **1.1.0** (July 1, 2026) — Added Issue 0 (merge conflict resolution) and Issue 1 (missing data files). Added reference docs for both issues.
- **1.0.0** (June 26, 2026) — Initial release. 3 hubs audited, static hubs identified.

---

*"Tough love for the agent economy."*