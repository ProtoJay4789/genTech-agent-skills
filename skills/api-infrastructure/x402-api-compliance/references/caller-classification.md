# Classifying callers: a roster, not a bucket

Aggregate classes ("discovery=9744 · self=1176 · other=455") cannot be sold to, disqualified, or fixed.
A roster — one row per caller with a verdict **and the evidence that produced it** — can.

## The discrimination rule

**The user-agent is a claim. Path breadth is evidence.**

- A **buyer** reads one resource and pays → few distinct paths, one resource.
- A **walker** enumerates the catalogue → many paths per caller, always 402, never pays.

So classify by *shape* first and let the UA only break ties. A caller that walked 13 paths is a crawler
regardless of what its UA claims, and a bare `curl` that touched exactly one path is **not** a crawler by
name — it is unproven.

## Verdict set

| verdict | test |
|---|---|
| `SELF` | UA or path names one of our own probes/settles |
| `MONITOR` | UA self-identifies as liveness/uptime/index (`x402-list`, `carbonmonitor`, `station`, `crawler`, `probe`, `census`, `checker`, `verifier`, `liveness` …) |
| `RUNTIME` | generic HTTP client (curl/axios/undici/deno/python-*/node) **that walked 5+ paths** |
| `SCANNER` | browser-string UA hitting `.env`, `.git`, `wp-*`, `xmlrpc`, credentials/terraform paths |
| `WALKER` | unnamed UA that walked 5+ paths |
| `CANDIDATE` | not ours, not named, not a scanner, **and it met a price challenge** |
| `FREE-ONLY` | never met a price challenge — it browsed the free surface and left |
| `NO-UA` | no user-agent at all: unidentifiable by definition |

**`CANDIDATE` requires having reached a 402.** A caller that only touched free surfaces never met the
paywall and cannot be evidence about demand — it is the *positioning* question (does the free surface
point at a paid route?), not the demand question.

## What each bucket means commercially

- **MONITOR** — proof the catalogue is discoverable, never a customer. Not a leak.
- **FREE-ONLY** — read the docs, never saw a price. Fix the path from free surface → paid route.
- **CANDIDATE** — reached the paywall. **The only bucket where a sale could have happened.** If these
  are numerous and none settle, test the payment path (`payment-path-proof.md`) before concluding
  nobody wanted to buy: "no demand" and "strangers cannot pay us" look identical from inside our own log.

## Output shape

Write the roster to JSON (per-caller rows with first/last seen, knocks, served, distinct paths, verdict,
reason) so it can be diffed between runs. Print a verdict tally plus the top rows by activity, then list
the `CANDIDATE`s **by name** — that short list is the only actionable output the report produces.

## Pitfall: the ledger rotates

A caller roster over "7 days" is only as long as the ledger's retention. Read every rotated generation
and print the actual coverage — see `cron-truth-layer` for the general rule.
