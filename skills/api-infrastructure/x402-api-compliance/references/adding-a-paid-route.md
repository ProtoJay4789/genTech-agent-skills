# Adding a paid route to the live gateway

**The gateway has THREE gates between an edit and a sellable route. Editing one of them restarts to nothing.**
This file is the order, the exact files, and the failure signature that tells you which gate refused.

---

## The order (do all four, then restart once)

**1 · The manifest the gateway actually SERVES.**

```
10-Labs/x402-gateway/x402-bazaar-live-repriced.json     ← the served one
10-Labs/x402-gateway/x402-bazaar.json                   ← the source; NOT what /well-known returns
```

**Check which is live before editing:** fetch `https://<host>/.well-known/x402-bazaar` and count
`services`. The served file carries `notServable` / `notServableNote` and `resource_template`; the source
does not. **If the live `services` count and your edit disagree, you edited the wrong file** — a service
count that does not move after a restart is the proof, and it costs no second restart to check.

**2 · The readiness inventory** — `10-Labs/x402-gateway/readiness-state.json`, a `routes` map keyed by the
**route SEGMENT** (`price`, `gas`, `market`, `flow`), each `{backend, servable, verdict, detail,
policy_blocked}`. Recompute `routes_servable` / `routes_total` / `tally` when you add or flip one, or the
file contradicts itself.

**3 · Deliverability** — `_service_is_deliverable()` is `service_key in BACKEND_ROUTES`. A route served
inside the gateway has no backend, so **add its key to `NATIVE_SERVICES`**, or the guard answers 404/410
BEFORE any challenge and the route can never be reached.

**4 · Readiness probe** — `_route_is_servable()` live-probes a backend port. For a native service it has
nothing to connect to, resolves UNKNOWN and — correctly, fail-closed — refuses with 503 forever.
**Short-circuit `NATIVE_SERVICES` at the top of `_route_is_servable()`** with
`(True, "native in-gateway (no backend to probe)")`. This is not a relaxation: a native route cannot be up
in one place and down in another, which is the failure the probe exists for.

---

## Serve it from ONE funnel

`_route_to_backend()` is the single fan-in for every paid path (x402 proof, MPP credential, human key,
OKX alias). **Intercept the native route at the top of that function** and return a `JSONResponse` — do not
patch each call site, and do not return a bare dict (Starlette answers a dict with a 500 *after* settlement).

Return the rule alongside the number: thresholds, `as_of`, the source, and the settling caveat. A buyer's
agent that cannot recompute the label has to trust it, which is the opposite of the product.

---

## Read the data from a public hostname, not the vault

The gateway runs in its own container. `/opt/data` is not part of its contract, and a route that works only
because two containers happen to share a volume breaks on the next recreate. Fetch the published file over
HTTPS from the hostname we control, cache it in-process, and answer **503 when the source is down — never a
number invented locally.**

---

## Converge the copy with the thing it sells

A route described one way and built another is a false advertisement. When the shape changes, update every
surface in the same pass: the manifest entry, the panel that names the route, the price, and the example
call. **Grep the route name across the deployed tree after changing it** — the page that advertises
`POST /v1/market/etf-flow` while the gateway serves `GET /v1/flow/etf/{symbol}` is a page a buyer will
follow into a 404.

---

## Verification that is evidence

```bash
curl -s https://<host>/health                                  # services count MUST have moved
curl -s -o /dev/null -w '%{http_code}' .../v1/<route>/<param>  # 402 = advertised and payable
curl -s -o /dev/null -w '%{http_code}' .../v1/<route>/nope     # 404 BEFORE payment = shape guard works
```

**A 200 on `/health` proves liveness and nothing about the route.** The discriminating checks are: the
service count moved, the new path issues a **402 with the right price and payTo**, an invalid sub-path
**refuses before money moves**, and an unknown symbol answers **404 with the list of what exists** rather
than an empty object.

---

## Failure signatures, decoded

| Response | Which gate refused |
|---|---|
| `503 service_temporarily_unavailable … absent from the readiness inventory` | gate 2 — no readiness entry for the segment |
| `404`/`410` before any challenge on a path you just added | gate 3 — not in `NATIVE_SERVICES` / `BACKEND_ROUTES` |
| `503` with a READY readiness entry and a healthy handler | gate 4 — the live probe cannot see a native service |
| `200 /health` with an unchanged service count after a restart | you edited a manifest the gateway does not load |
| `500` after a settled payment | a handler returned a dict, not a response |
