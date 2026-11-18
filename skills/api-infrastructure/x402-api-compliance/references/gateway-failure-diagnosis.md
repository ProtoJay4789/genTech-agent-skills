# Gateway failure diagnosis — the parts Rule 12 does not cover

**The core diagnostic lives in `cloudflare-zone-operations` → "a 500 on EVERY route is one
startup failure" (Rule 12): a uniform 500 across unrelated handlers is a shared initialisation
failure, and the most common cause is an EMPTY network intersection between the chains a gateway
advertises and the networks its facilitator will settle.** Read that first; it is not repeated here.

This file carries what that rule does not: how to tell three different faults apart when they all
surface as the same status code, and what to do about each.

## 1. Free routes 200 / every paid route 500

That split is the cheap localiser. The payment layer wraps exactly the paid routes, so a clean
division means the fault is in the payment layer and **no handler body has ever run**. Do not
report "the service is down" — the fixes are unrelated.

## 2. Stub routes — compliant, and still selling nothing

A deployment can pass every compliance check and return `500`-free placeholders once fixed:

```js
app.get("/api/x", (c) => c.json({ success: true, data: "X results" }))   // a string, not a result
```

**Read one handler body BEFORE promising a fix.** If the routes are stubs, repairing the
facilitator buys nothing — the job is to build the product behind the routes. "It is protocol
compliant" and "it delivers real data" are separate tests, and only the second one is a product.

## 3. A facilitator that refuses your credentials

A mainnet facilitator usually demands auth, and a stored key can be the wrong *shape* for it —
a plain-string legacy secret where the service expects a signed JWT / Ed25519 JSON. Try each form
before promising a config change:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -u "$ID:$SECRET"        "$FACILITATOR/supported"
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $ID" "$FACILITATOR/supported"
curl -s -o /dev/null -w '%{http_code}\n' -H "X-API-Key: $ID:$SECRET" "$FACILITATOR/supported"
```

**All three 401 means re-pointing the facilitator is a build, not a one-line edit** — say that
before the user plans around a five-minute fix.

## 4. Fix options, in preference order

1. **Publish the endpoint that already works.** If another deployment of the same product prices
   correctly, repoint the published listing at it. Cheapest, and it stops the bleeding in the
   surface a buyer actually reaches.
2. **Repoint the facilitator** to one that serves the deployment's networks — only once the
   credentials are proven (section 3).
3. **Reconfigure the networks** to what the facilitator serves — usually testnets, i.e. no revenue.
4. **Retire the deployment** and remove it from listings. Better than leaving a listed surface
   that 500s. A stub estate is often not worth rebuilding — decide that deliberately.

## 5. Check the last-modified date before you speak about exposure

A stale modified-date on a broken public surface means the breakage is **old and public**, not a
fresh casualty of the incident you are investigating. That changes the sentence you give the user
about how long the defect has been live.

## 6. Two estates: the surface you fix may not be the surface you publish

**The most expensive version of this bug is auditing the wrong deployment.** A product can exist
twice — a container estate behind an API hostname, and an edge/Worker estate under a
`*.workers.dev` URL — and the published listing may point at either.

**Before auditing, read your OWN published entry and probe each URL in it for FUNCTION, not for
status.** Three live links at `200` can still include one whose every functional route fails. Then
enumerate the estate the entry points at and compare it against the one you have been repairing:
if they differ, every fix you made was to a surface no buyer reaches.

```bash
# which estate does the listing actually send people to?
grep -oE 'https?://[^ )|]+' <your-published-entry>
# then probe the routes, not the roots
for r in /health /pricing <a paid route>; do printf '%-22s ' "$r"; curl -s -o /dev/null -w 'http=%{http_code}\n' "$BASE$r"; done
```

**And treat your own published claims as claims.** Count the endpoints and the deployments your
entry asserts and check both against the API and the gateway's own documents — a listing that
overstates the estate is the same defect as a listing that links to a dead one.

## 7. The discovery surface and the delivery path must share ONE inventory

**An agent's first call is a listing, not a request.** An MCP `tools/list`, an OpenAPI document, a
manifest, a directory entry — each is a set of promises about routes that have to resolve. Two
faults come from letting the listing and the delivery path drift apart, and a status check on the
root shows you neither.

**a) A listed name that does not resolve to a route.** A handler that builds its call URL from a
service's internal KEY rather than its PUBLISHED path will fail for exactly the services whose key
differs from their public segment — and pass for every service where the two coincide, which is why
it survives review. Measured: one entry in fifteen 404'd this way while its siblings were fine.

```bash
# CALL every entry; do not merely list it
for t in $(curl -s -X POST "$BASE/mcp" -H 'content-type: application/json' \
           -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
           | jq -r '.result.tools[].name'); do
  printf '%-24s ' "$t"
  curl -s -X POST "$BASE/mcp" -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$t\",\"arguments\":{}}}" \
    | jq -r '(.result.content[0].text | fromjson | .http_status) // "no http_status"'
done
```

- **Derive the call URL from the field you PUBLISH** (the manifest endpoint's own path), never from
  an internal identifier — then a rename cannot silently orphan the surface.
- Only two outcomes are honest: **a payment challenge, or a not-servable refusal.** A third status is
  a resolved-but-wrong answer that no listing check will ever reveal.
- A tool list that wraps an upstream status inside a JSON-RPC `200` is honest but easy to misread:
  read the WRAPPED status, not the transport one.

**b) One surface withholds what another still advertises.** If the metadata generator filters
unservable services out *with reasons* while the tool list still enumerates them, an agent spends a
call on a promise one document kept and another dropped. **Filter every discovery surface from the
same readiness state**; where a surface cannot be filtered, say so where the two are compared.

**Cross-reference:** for the edge-deployment half of this — which facilitators actually settle
mainnet, the Worker deploy traps, and giving an edge estate its own traffic ledger — see
`cloudflare-worker-x402-gateway.md` in this same directory.
