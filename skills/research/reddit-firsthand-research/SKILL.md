---
name: reddit-firsthand-research
description: "Use when Reddit threads are 403-blocked. Pull via .rss."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Research, Reddit, Scraping, WAF]
    related_skills: [blocked-page-recovery, grounded-citations]
---

# Reddit first-hand research when the site is blocked

## When to Use

- You need real Reddit threads (outcomes, reviews, testimonials) as evidence.
- Reddit HTML/JSON returns 403, or `web_extract` fails on Reddit URLs.
- Any subreddit, any thread ID — the `.rss` endpoint is universal.

Reddit blocks datacenter/cloud IPs hard: `www.reddit.com/...json` → 403,
`old.reddit.com` → 403, redlib/libreddit mirrors → Anubis/Cloudflare walls,
`web_extract` → "Failed to fetch". Do NOT burn time on those. One surface works.

## The one endpoint that works

```
https://www.reddit.com/r/<sub>/comments/<id>/.rss
```

Returns the **full post + every comment** as Atom XML (~15–90 KB), with author,
`<updated>` (ISO date), title, and comment body. Works with a normal desktop
User-Agent, no login. This is the whole trick.

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
curl -s -m 30 --compressed -A "$UA" \
  "https://www.reddit.com/r/AWSCertifications/comments/1lqqq8o/.rss" -o thread.xml -w "%{http_code}"
```

## Rate limiting — pace it

- Rapid requests → **429** (empty body). Back off 15–25 s between fetches.
- Batch **3–5 threads per shell call** with `sleep`, writing each to its own
  file, so a tool timeout does not lose progress. Resume by skipping files that
  already exist and are non-empty.
- A single `execute_code` cell times out (300 s) if you retry-hammer; prefer a
  `terminal` call with `timeout=500`+ and a plain bash loop.

## Parsing (stdlib only)

```python
import re, html
def parse(path):
    xml = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        a = re.search(r"<name>([^<]*)</name>", e)
        u = re.search(r"<updated>([^<]*)</updated>", e)
        cm = re.search(r"<content[^>]*>(.*?)</content>", e, re.S)
        body = re.sub(r"<[^>]+>", " ", cm.group(1)) if cm else ""
        body = re.sub(r"\s+", " ", html.unescape(body)).strip()
        out.append({"author": (a.group(1) if a else "?").replace("/u/",""),
                    "date": u.group(1)[:10] if u else "", "content": body})
    return out
```

## Finding thread IDs

You cannot search Reddit directly. Get IDs from a web search engine
(`web_search`) — snippets for `site:reddit.com r/<sub> <topic>` return the
`/comments/<id>/<slug>` URLs you need. Then fetch each via `.rss`.

## Triage large threads

Sort entries by `len(content)` descending — long comments are the first-hand
stories; short ones are jokes/bot boilerplate. Filter out `RemindMeBot`,
`AutoModerator`, and `submitted by` footers.

## Still blocked / gaps
- **YouTube transcripts**: also blocked from cloud IPs (`youtube-transcript-api`
  → RequestBlocked). No easy workaround without proxies.
- **archive.org wayback API**: rate-limits to 429 quickly.
- Prefer `.rss` over fighting `blocked-page-recovery` ladders for Reddit.
