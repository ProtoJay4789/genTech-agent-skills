# Traffic is not demand

Deciding whether to BUILD a route, add a rail, or rebuild a dead service. Use when a log shows a
route getting requests while revenue stays flat — the numbers look like demand and are usually
catalogue machinery.

## Classify the caller before you believe the count

A request is not a customer. Group the log by **user-agent** and by **status**, then read the shapes:

| shape | what it is | what it means |
|---|---|---|
| `*-catalog-health`, `*-probe`, `*-observer`, `*-trust-probe`, `AgentRank*`, uptime monitors | machine readers, usually self-identifying | they grade you; they never pay |
| high volume on ONE path, steady day after day, `404`/`503` | a catalogue advertising a path you no longer serve | **catalogue debt**, not demand |
| `402` then a retry on the SAME route with a payment header | a real buyer trying | the only traffic that can become revenue |
| `402` then a retry on a DIFFERENT route | a client that cannot sign your rail | a rail-compatibility defect, not absence of demand |

Measured: a retired trio of routes drew **~400 requests/day for ten days** — and every single caller
was a catalogue monitor or an uptime prober (`AgentRankProbe`, `*-catalog-health`, `*-probe`), with the
same route returning `404` then `503` because a stale catalogue still advertised it. **Three requested
routes, one real payer: zero.** Building them would have converted monthly `404`s into monthly `402`s
that nobody pays.

## The decision rule

**Build only for a caller that can pay.** If the only evidence is volume, the honest options are:

1. **Retire the path properly** — `410 Gone` plus a body pointing at the live inventory. Monitors can
   act on "deliberately gone" and stop; `404` makes them re-probe forever. See `receipts-and-error-codes.md`.
2. **Fix the catalogue that advertises it**, not the service — the paths are usually listed somewhere
   you control, and a refresh cycle removes them without a line of new code.
3. **Scope it as a product with a named buyer** — when there IS an argument (routing, aggregation,
   anything a real client asked for in a reply), that is a build with a business case, not a repair of
   a monitor's complaint.

## Say what it would and would not buy

A rebuild that satisfies crawlers buys **a cleaner grade**, not revenue. Name that distinction in the
report: *"this is an optics fix, not a product"* is a sentence the user can act on; "we should build it
because it gets traffic" is not. And when recommending retirement, give the two costs honestly — the
grade stays lower, and a service someone might have wanted is gone — then do the `410` so nobody keeps
asking.

## Pitfalls

- **A seven-day window hides a fixed incident.** A burst concentrated on two days (a restart, an
  outage) aggregates into a "sustained" weekly number. Histogram by day before quoting a rate.
- **`200` on a paid path is not a sale.** If the log has no payment field, a successful response may be
  a free surface or a cached page; only clipped receipts and settled hashes are revenue.
- **A monitor naming a path you never published is evidence about ITS catalogue**, not about your API —
  a `404` from a guessed path says nothing about what you serve.
