---
name: blocked-page-recovery
description: "Use when a fetch fails: 403/429, paywall, WAF, bot wall."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Archives, Wayback, Paywall, WAF, Fallback]
    related_skills: [grounded-citations]
---

# Blocked-Page Recovery

When a page won't fetch — 403/429, Cloudflare "Just a moment...", a paywall,
or a bot-detection interstitial — don't give up and don't loop on the same
URL. Third-party services often hold a **copy** of the page. Work down this
ladder, cheapest first.

## The ladder

```
1. Wayback Machine  — archive.org "available" API  (snapshot + timestamp)
2. archive.today    — domain rotation: archive.ph → .md → .li → .is
3. Jina Reader      — only if JINA_API_KEY is set  (live server-side render)
4. API-first pivot  — look for /api/, /graphql, .json, or RSS on the same host
5. Real browser     — browser tool as the last, most expensive resort
```

Run it in one shot with the bundled script:

```bash
python3 scripts/recover_page.py "https://example.com/blocked-article" --json
```

The script tries each route in order, validates every body (see "Fake
successes" below), and prints the first genuine hit with its provenance.

## Provenance discipline (non-negotiable)

Every recovered copy carries a provenance you MUST preserve when citing:

| Route | Provenance | How to cite |
|-------|-----------|-------------|
| Wayback / archive.today | `snapshot` | Cite WITH the snapshot date: "as archived 2026-08-06". Never present a snapshot as the live page — it may be stale. |
| Jina Reader | `live` | Server-side re-render of the live page; cite normally. |
| Live fetch / browser | `live` | Cite normally. |

If the user needs *current* data (prices, availability, breaking news), a
snapshot is context, not an answer — say so explicitly and note its age.

## Manual routes

### 1. Wayback Machine (best provenance, try first)

```bash
# Discovery: returns closest snapshot URL + timestamp as JSON
curl -sL "https://archive.org/wayback/available?url={URL}"
# Then fetch archived_snapshots.closest.url
```

For enumerating many snapshots (or recovering deleted pages), the CDX index:

```bash
curl -sL "https://web.archive.org/cdx/search/cdx?url={URL}&output=json&limit=10"
```

CDX intermittently returns 503 under load — if it does, fall back to the
`available` API; don't retry-hammer it.

Works for: any publicly crawled URL. Fails for: robots-blocked sites,
never-crawled URLs, JS-only SPAs (snapshots don't render).

### 2. archive.today (paywalls, deleted content)

User-submitted archives — often has paywalled news articles Wayback lacks.
Rate-limits aggressively (429) and rotates domains, so iterate:

```bash
for d in archive.ph archive.md archive.li archive.is; do
  curl -sL --max-time 20 "https://$d/newest/{URL}" -o ~/.hermes/cache/scratch/page.html \
    -w "%{http_code}" && break
done
```

**Validate the body, not the status code** — a 429 still ships several KB of
rate-limit HTML that looks like a success to a size check alone.

### 3. Jina Reader (requires JINA_API_KEY)

`r.jina.ai` re-renders the live page in a real browser server-side and
returns markdown. Anonymous access is dead — measured 2026-11-24 it answers
**HTTP 403** with a JSON body
`{"code":403,"name":"AbuseAlleviationError","message":"Anonymous access to
domain … blocked until <timestamp> due to previous abuse"}`. That body is
**not HTML and not an error page** — a naive caller parses it as the fetched
page, matches nothing, and reports "fetch failed" with no clue why. Check the
status code before the body, and treat a 403-with-JSON as "route unavailable",
never as content. A key is required:

```bash
curl -s -H "Authorization: Bearer $JINA_API_KEY" "https://r.jina.ai/{URL}"
```

Handles JS SPAs that archives can't. Skip this route entirely when the env
var is unset.

### 4. API-first pivot

WAFs protect the HTML surface far more aggressively than the data endpoints
behind it. After 2-3 blocked attempts on a site, stop fighting the HTML and
look for:

- `/api/...`, `/graphql`, or `.json` variants of the page URL
- An RSS/Atom feed (`/feed`, `/rss`, `<link rel="alternate">` in any copy
  you did recover)
- A sitemap (`/sitemap.xml`) revealing canonical URLs that may not be gated

## Fake successes — routes that LIE

These return HTTP 200 with a plausible body that is NOT the page. The script
rejects them automatically; reject them manually too:

- **Google Cache is dead** (since mid-2024). `webcache.googleusercontent.com`
  returns 200 + tens of KB, but it's a Google Search interstitial with a JS
  redirect, not a cache. Never use it.
- **AMP caches** (`*.cdn.ampproject.org`) mostly return a ~300-byte
  `<title>Redirecting</title>` meta-refresh stub pointing back at the
  original (blocked) URL. Treating that as success creates a fetch loop.
- **Rate-limit bodies**: archive.today 429 pages are multi-KB HTML. Check for
  the target's actual content (title words, expected strings), not just size.
- **Hollow same-size 200s**: a blocked data surface can return **HTTP 200 with
  nearly the same byte count as the real page and none of the data** (measured
  on Google Flights: 1.90 MB hollow vs 2.02 MB rich, zero price tokens, and
  the word "captcha" in the body). A byte floor cannot reject it. Assert on
  CONTENT the page must carry — a price token, a row count, a known phrase —
  and give the response a NAME ("hollow / no fare block"), because an unnamed
  failure is unreportable.

### Retrying a hollow wall: rotate the endpoint, slow down

- **Rotate the endpoint, not just the user agent.** Measured: while
  `www.google.com?gl=US` served hollow back-to-back, `www.google.co.uk` served
  the same route rich at the same moment. A second host or locale is a
  different gate.
- **Before quoting a rotated reading, prove product equivalence.** Pin the
  params that define the product (`curr=USD`, locale) on every endpoint, and
  confirm the number and window match across them; a point-of-sale change can
  silently change the price, which is worse than a failed fetch.
- **The block is rate-based, so retries can deepen it.** Back-to-back attempts
  (even 3/6/10 s apart) turn a short block into tens of minutes; a 60 s and
  then 120 s idle probe both stayed hollow. Retry a few times with growing
  gaps, then STOP and report loudly. Schedule one run a day, not a hammer.
- **Corollary for monitors:** "no data" must never render as "no change". A
  fetch layer that returns `""` on failure and a report layer that returns `""`
  on no-alert is a silent outage generator. Emit a named failure line instead.

Detection heuristics the script applies: body under a per-route byte floor;
meta-refresh/JS-redirect stubs whose target is the original host; interstitial
titles ("Just a moment", "Redirecting", "Google Search", "Attention Required").

## Proxy relays: don't

Generic "web proxy" relays are man-in-the-middle by construction. Never send
cookies or Authorization headers through one, and don't use them for anything
the user will rely on — provenance is unverifiable. Prefer archives, which at
least timestamp their copies.
