---
name: spa-data-extraction
description: "Use when a JS-heavy site defeats form-driven browsing."
category: web
version: 1.0.0
author: Gentech
license: MIT
tags: [browser, spa, extraction, automation, data]
metadata:
  hermes:
    tags: [browser, spa, extraction, automation, data]
    related_skills: [browser-to-api, blocked-page-recovery]
---

# Extracting Data from JS-Heavy Sites

Read a JS-heavy site by **URL query** first, escalate to search snippets, and capture traffic only as
a last resort. Most sites people conclude "the browser can't do" answer a plain query outright.

## When to use

- A site's UI resists automation — autocompletes, date pickers, multi-step widgets.
- A headless browser read "times out", hangs, or returns an empty page.
- You need repeated readings of the same kind of page (prices, listings, dashboards).
- Someone has already concluded *"the browser can't do this site"* — that conclusion is usually wrong.

## The escalation ladder — go in order, escalate ONLY on failure

| Rung | Method | Cost |
|---|---|---|
| **0** | Construct the URL query and read the rendered text | seconds, one call |
| **1** | `web_search` snippets (aggregators echo real values in their descriptions) | seconds, cheap |
| **2** | `browser-trace` capture + `browser-to-api` to derive a callable surface | minutes, heavy |

**Do not start at rung 2 because a widget resisted.** Most of these sites answer rung 0 outright.

## Rung 0 — the URL query

**What gets misdiagnosed as "the browser can't do this site" is usually the *form*, not the site.**
Typing into autocompletes and clicking date pickers is what times out. The URL-parameterised query on
the same host returns immediately, server-rendered. **Retry the URL, not the interaction.**

1. Work out the natural-language search the UI would have made.
2. URL-encode the whole request into the site's query parameter — origin, destination, ISO date,
   and the mode (`one way` / `round trip`). Put the *entire* ask in the query string.
3. Load it, settle briefly, and print `document.body.innerText`.

```python
q = urllib.parse.quote("Flights from CVG to CEB on 2027-01-20 one way")
new_tab(f"https://www.google.com/travel/flights?q={q}&curr=USD&hl=en")
wait_for_load(); time.sleep(6)
print(js("document.body.innerText")[:4000])   # the data is TEXT, not an image
```

The `curr=` / `hl=` style parameters pin currency and language — set them explicitly so readings are
comparable across runs instead of drifting with the caller's locale.

### Read text, not pixels

Work from `document.body.innerText` (or targeted `js()` DOM reads). Screenshots cost a round trip,
need vision, and cannot be grepped or diffed. Text output is skimmable, storable, and comparable
run-to-run — which matters most when the point is to detect *change*.

### Permalinks are readings, not searches

A shared link with an opaque id (`…/s/<id>`) encodes one specific query. Decode it to the itinerary
it actually represents (route, date, cabin, passenger count) **before** treating its price as a
comparable data point — and never diff it against a general search result.

## A virtualised list renders a SUBSET — and the subset looks complete

Lazy-loaded lists (saved places, infinite scroll, virtual tables) mount **only the visible window** and
recycle nodes as you move. `document.body.innerText` then returns a tidy, well-formed ~20 rows while the
page's own header says **"71 places"**. Nothing errors, nothing is truncated mid-word, and the extract
looks exactly like a complete list.

**Always compare the parsed count against the population the page itself states.** The header is the
denominator you cannot get from the DOM: `20 parsed · header says 71`. If those disagree, you have a
window, not the list — say so, never "I read your list".

**Programmatic scrolling does not wake the loader.** Measured, all of these left the count at 20:
`el.scrollTop = el.scrollHeight`, an incremental `scrollTop += 260` loop, `window.scrollTo`, a synthetic
`KeyboardEvent('End')`, and dispatching wheel events at the container. These lists gate the next page on
**genuine user-gesture** events, so an automated read has a hard ceiling at the first window. Do not
spend a dozen iterations discovering this one shape at a time — try one programmatic scroll, see the
count not move, and stop.

**Check for the FIELD you need before designing around the page.** The rendered card often exposes only
name / rating / category while the coordinates sit in the map layer or behind a per-item click. A list
you can *read* but cannot *place* supports no distance, no "what's near me", no pin — so confirming the
header and the row text is not confirmation the integration is possible. Name the missing field in the
first report, not after the product is built on it.

**The escape is the service's own EXPORT, not more scraping.** A shared link returning 200 and rendering
without a login wall proves **access**, not **extractability** — two different claims, and the second is
the one your product needs. Look for the product's export format first (KML, GeoJSON, CSV, a Takeout
bundle), describe the two-click path to produce it, and parse the FILE: a file carries the full
population with exact coordinates, is stable across runs, and carries no scraping exposure. When the user
reports the export is unavailable, the honest answer is "then the page is a partial view and we build
the list from names instead" — measured: two place-name lookups out of three failed against open geo data,
so say plainly how much a name-only approach can deliver before the user spends an evening typing names.

## Pitfalls

1. **Form-driving is the trap.** If a browser attempt fails, the fix is a different *URL*, not a
   fourth attempt at the same widget. Retry the interaction at most once, then change approach.
2. **Never present an outlier as a real alternative.** When one page shows two wildly different
   numbers for the same thing (a normal fare and a 20x fare for the identical itinerary), the outlier
   is a bad bucket or a stale render. State which figure you are quoting and why.
3. **A value that vanished has not necessarily sold out.** Buckets release and refresh — re-run the
   query before reporting something gone. Say "re-checked, still gone" rather than assuming.
4. **Re-query before concluding, and quote the page's own verdict when it offers one.** Many sites
   print an explicit assessment ("prices are currently low / typical / high"). That line is the
   site's own read, it is what the user will see, and it settles buy-now-vs-wait better than inference.
5. **Do not fabricate a reading to fill a gap.** If every rung fails, report the blocker and the exact
   error — a plausible-looking number is worse than an honest gap, because it gets acted on.

## Composing with siblings

- `browser-to-api` — rung 2. Derives an OpenAPI surface from a `browser-trace` capture when no URL
  query will do.
- `blocked-page-recovery` — a *different* failure mode. That one is for access **denied**
  (403/429/WAF/paywall); this one is access **granted** but the UI undriveable. Check which you have
  before choosing a remedy.
