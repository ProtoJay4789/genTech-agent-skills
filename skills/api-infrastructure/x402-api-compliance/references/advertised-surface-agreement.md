# Advertised surfaces must describe ONE inventory

A service is advertised in several places at once: a discovery manifest, a marketplace/bazaar document, an
MCP `tools/list`, a registry metadata file, an **OpenAPI spec**, and a **plaintext agent-facing summary
(`llms.txt`)**, plus whatever third parties index from those. **Each is a separate place a count can be wrong,
and third parties inherit the error** — an external bazaar's listing count drifts whenever our published
document changes, so "their number" is really "our number, delayed".

**Enumerate surfaces by TYPE, not by memory.** The structured ones — manifest, bazaar document, tool list,
registry metadata — are the ones you remember, because you built them as objects and they have obvious
schemas. **The plaintext and spec-derived ones are the ones you forget, and they are the ones catalogues read
first:** `llms.txt` is trivial to fetch and parse, and an OpenAPI `paths` map is the canonical service list
for a whole class of crawlers. Filtering four structured surfaces while leaving `llms.txt` and `openapi.json`
untouched produces a **passing audit script and a public overstatement at the same time** — the audit passes
because it checks the four it knows about.

**So: grep the server for every generator that emits a service list — including the ones that emit prose and
the ones that emit a spec — and hold each one against the servable set.** A generator that loops over the
service manifest is a surface; so is one that builds `paths`, and so is one that writes bullet points.

**A staged fix is not a live fix.** After editing a generator, the running process still serves the old bytes
until it restarts. Say so explicitly rather than implying the fix landed: re-fetch the live surface and
compare it, and when the restart is not yours to run, **state both numbers — what is staged and what is still
being served — so nobody mistakes a compiling module for a corrected response.**

## Scalar summary fields drift even when the service set agrees

The `services` map can be perfectly aligned across every surface while the **document's own summary
fields** are months stale — because they are scalars typed by hand, not entries generated from the set.

Measured on one manifest whose service list was correct and gated:

| field | served | truth |
|---|---|---|
| `updated_at` | ~7 weeks old | the file had changed repeatedly since |
| `price_range_usd` | `[0.005, 0.05]` | the real floor had dropped to `0.001` |
| `payment.network` | bare slugs (`base`, `avalanche`, …) | every live challenge emitted **CAIP-2** ids |

**Nothing flagged any of it.** A surface-agreement checker that compares service *names* reports green on
all three. **A price range is the field an agent filters on** — a stale floor is a silent "too expensive,
skip", which is worse than a wrong name because the caller never gets far enough to see the service.

### Derive summary fields at publish time, never type them

`price_range`, counts, `updated_at`, and the accepted-network list are all **functions of the set**. Compute
them where the document is built — at import, or in the generator — so they cannot disagree with what is
being sold:

```python
sellable = {k: v for k, v in services.items() if servable(k)}
prices   = [float(v["priceUsd"]) for v in sellable.values()]
doc["payment"]["price_range_usd"] = [min(prices), max(prices)]
doc["updated_at"] = now_iso()          # the file is changing; say so
```

### ⚠️ Derive from the SUBSET the claim covers

**A range promises "you can buy in this band". Including an entry nobody can buy makes it a false promise.**

Measured: the first correction computed the range over **all** entries and produced `[0.001, 0.25]` — the
`0.25` belonging to a route that was **withheld and unservable**. The honest range was `[0.001, 0.05]`,
over the sellable subset only. **The same applies to a count, a total, or an average: a summary of the
catalogue must summarise the part of the catalogue that applies.**

### ⚠️ Name networks the way the challenge names them

If the discovery document says `base` and the `402` says `eip155:8453`, every client carries a second
mapping it did not ask for — and one that silently fails to match. **Publish the identifier form the
challenge actually emits (CAIP-2), and add a label map beside it** (`{"eip155:8453": "base"}`) so a human
reading the doc is not decoding hex.

### Audit them explicitly

Fetch the discovery document and the live `402` together and assert three things: the range brackets the
prices actually advertised, the network ids in the doc equal the `network` values in `accepts[]`, and
`updated_at` is not older than the newest change you know you shipped. **Then remember the restart rule
above — an edited summary is staged, not served, until the process reloads the manifest.**

## The rule

> **Advertise only what you can serve, and advertise the SAME thing everywhere.**

Every surface must list exactly the services the runtime readiness gate calls servable, and any surface that
carries a withheld set must carry the **same** withheld set **with reasons**. A surface that advertises a
service it cannot deliver is the same defect as a dead link, only harder to notice because the document
validates.

## One predicate, several surfaces

**Do not re-implement "is this servable?" per surface.** Each copy is a chance to disagree, and the copies
drift the moment one is edited. Find the single function the payment path already uses and call it from every
advertising path.

**Prefer the PRECOMPUTED state over a live probe on advertising paths.** A readiness function that
TCP/HTTP-probes each service is correct for a request that is about to charge, and **wrong for a discovery
document an agent fetches casually** — one probe per advertised service adds tens of seconds to the response.
Read the state file the gate already writes (it is what the registry metadata is generated from, so the two
agree by construction), and cache it in-process for a few seconds.

**Fail CLOSED when the gate is unreadable** — the same way the paid route does. If you cannot establish that
a service is servable, do not advertise it.

## Withhold, do not delete

A service you cannot serve should leave the primary list and appear **under a separate key, with its reason**
(`notServable: {service: {reason: …}}` plus a one-line note). Silently dropping it reads as "we never had
that capability"; advertising it reads as "we do". **A reader must see the GAP rather than infer completeness.**
The same applies to a tool list: withhold from `tools`, and name the withheld ones in the response so an agent
does not spend a call discovering a `503`.

## Pitfall — the manifest key is not the backend key

**Two namespaces that look alike will be treated as one, and the answer is silently wrong.** A manifest holds
**service** keys (`gas_oracle`, `deal_tracker`); the routing table holds **backend** keys
(`gas_oracle_native`, `deal_tracker_native`). A readiness lookup against the routing table therefore returns
"not servable" for a perfectly healthy service — and an advertising filter built on it **withholds a working
service**, which is the opposite of the intended fix and looks like a successful cleanup.

Resolve in this order, most explicit first:

1. the key itself, when it is already a backend key;
2. `<key>_native`;
3. the **URL segment** of the service's own published endpoint, mapped through the same alias table the paid
   route uses — so the answer cannot disagree with what a caller actually hits.

**A URL built from the service KEY is a related trap.** If the internal name differs from the published
segment (a tool called `store` published at `/v1/gas/gas`), any code that constructs a URL as
`/v1/{service_key}` addresses a segment the gateway cannot resolve and returns "service not found" — while
the service is listed, healthy, and reported ready. **Build internal calls from the PUBLISHED path, never
from the key**, and a listed-but-404 tool becomes impossible.

## A service that is GONE must answer `404`, not `503`

Withholding it from the lists is only half the fix. The route itself is still reachable by anything that kept a
URL — crawlers, catalogues, an agent's cached discovery — and the status code it answers there is a claim about
our state.

- **`503` says "temporarily unavailable, try later".** That is the honest code for a service whose backend is
down and will be back: it tells a client to retry, and it tells a conformance suite the run was inconclusive.
- **A service with no backend left must `404`** (or `410` Gone). Returning `503` for something that will never
  return promises a repair that is not coming, and every retry loop, health check and conformance report treats
  it as **our outage**.

**Measured cost of getting this wrong:** a public conformance crawler logged 680 `503`s against a gateway whose
withdrawn services no longer had any backend at all — the list was already correct, and the paths still told the
world the gateway was broken. Removing the dead entries from the routing table (so the same "not deliverable"
branch that answers `404` for an unknown segment answers these) stopped the accumulation without touching a
single advertised surface.

**What this proves about the failure mode:** an outage that is invisible in the discovery documents can still be
the loudest thing about the service, because **the paths outlive the listings**. Audit both — the advertised set
*and* the status code each withdrawn path returns — and keep the live-route check beside it: after removing dead
routes, confirm a healthy sibling still issues its `402`, because a routing-table edit that is too broad turns a
working service into a 404 and looks identical in the logs.

## `paths` is a list of CALLABLE routes — a template is not a route

An OpenAPI `paths` map is read by a whole class of crawlers as **the enumeration of endpoints to call**: they
fetch the spec, then request every key verbatim. So each key is a promise that a `GET` to it does something
meaningful. **A parameterized entry (`/v1/price/{address}`) is a route SHAPE, not a route** — the crawler
substitutes nothing or substitutes junk, and every such call is a guaranteed `404` that lands in the logs as
**our** outage.

Measured shape: a single discovery crawler generated roughly **six template `404`s for every one legitimate
call** over a few days — thousands of them — while the gateway was behaving perfectly. The routes were
correct; **the advertisement was the defect**, and it was invisible in every count that mattered because a
`404` on a path nobody can call looks identical to a path that broke.

- **Keep `paths` to concrete, callable entries only.** Publish the parameterized form beside the concrete
  entry as an extension (`x-resource-template`), so a machine can learn the shape and a crawler has nothing
  bogus to call.
- **⚠️ An `x-` extension placed as a SIBLING key of `paths` becomes a path.** Crawlers enumerate keys and do
  not respect the extension convention there, so the extension itself turns into a `404` route — you have
  moved the bug, not fixed it. Extensions belong on the **operation object** (beside `get`/`post`), never at
  the `paths` level.
- **Fix all surfaces that derive from the same generator at once.** A `_concrete_url()` fix applied to the
  well-known manifests does not reach `openapi.json` if it builds `paths` on a separate code path — that is
  exactly how a spec keeps advertising templates after every other surface was corrected.
- **Expect a lag, and measure it.** Crawler `404`s continue for as long as third parties hold the cached spec.
  Report the fix by **the rate falling at a timestamp**, not by the spec being edited.

## Build the audit, or the drift returns

Alignment done by hand drifts. Ship a checker that reads the runtime truth, fetches every surface, and fails
loudly:

- compare each surface's set against the servable set — report **missing** (servable but unadvertised) and
  **advertised-but-unservable** separately, they need different fixes;
- compare every surface's withheld set against the gate's;
- **an unreadable surface reports UNREADABLE, never zero** — a failed read rendered as `0` is how a blind
  check passes;
- exit `0` on agreement and `2` on disagreement, **never 1**, and print nothing on agreement so it can run as
  a silent scheduled monitor.

**Two bugs the checker will have on its first run, both of which produce phantom findings:**

- **Alias routes read as services.** A route table may list both `price` and `market` for one service. Count
  a route with no service of its own as an ALIAS of the service that has one — otherwise it appears as a
  service missing from every surface, and you go hunting for a real gap that does not exist.
- **A parse that assumes one document shape.** The withheld inventory may be a list on one surface and a dict
  on another. Tolerate both, and skip entries that are not dicts, rather than raising where nobody looks.

## Also check the counts you do not control

A third-party index is a *derived* number. When it disagrees, establish which direction the error flows before
editing anything: if our published document is right, the index will converge on its own; if ours is wrong,
the index is faithfully republishing a lie. **Record the derived number and the date you read it** — a bazaar
listing dropping from one count to another is a change signal, not a rounding difference.

And when a third party reports our absence from their catalogue, **check whether the URL they measured is even
ours.** A well-meaning monitor baselining `someone-else.example/mcp` and reporting "your tools" produces a
finding about the wrong system, and the useful fact in it is that we are absent from a directory that matters.
