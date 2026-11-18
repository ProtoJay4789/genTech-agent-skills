# Worker proxy patterns — traps and the correct shape

Depth for Rule 6 of the parent skill. A Cloudflare Worker that proxies to origin backends has three failure
modes that masquerade as something else entirely.

## 1. The catch-all redirect loop (`error code: 1003`)

The classic shape — and it is wrong:

```js
const VPS_IP = "203.0.113.10";

async function proxyToVPS(request, targetHost, targetPort) {
  const url = new URL(request.url);
  const targetUrl = `http://${VPS_IP}:${targetPort}${url.pathname}${url.search}`;
  const proxyReq = new Request(targetUrl, { method: request.method, headers: request.headers });
  proxyReq.headers.set("Host", targetHost);        // <-- silently dropped by the Workers runtime
  return fetch(proxyReq);                           // <-- follows redirects by default
}
```

**What actually happens:** the request reaches the origin by IP; the origin's reverse proxy sees an HTTP
request and answers its standard HTTP→HTTPS **301** to the *hostname*; `fetch` follows it; that hostname is
proxied on the same zone; the request re-enters Cloudflare's edge; the loop guard fires and returns
`error code: 1003` with `server: cloudflare` and a short text body.

**Confirm it — never guess:**

```bash
curl -s -o /dev/null -w '%{redirect_url}\n' http://<origin-ip>/<path> -H 'Host: <host>'
# a Location pointing at https://<host>/<path> is the loop
```

A route answered *inside the Worker* (a local `/health`) will look perfectly healthy while every proxied path
returns 1003 — which is why a partial 200 misleads.

**Correct shapes:**

```js
// (a) fetch the origin hostname over HTTPS — no Host override needed, no redirect to follow
const r = await fetch(`https://${originHost}${url.pathname}${url.search}`, { method: request.method });

// (b) or fetch by IP only when the origin speaks the right vhost and does not redirect
const r = await fetch(`http://${originIp}:${backendPort}${url.pathname}${url.search}`, {
  redirect: "manual",   // never let a proxy follow an origin redirect into the public hostname
});
```

Set `redirect: "manual"` on any Worker fetch that targets your own zone — following it is the bug.

## 2. `Host` is a forbidden header in a Worker fetch

`proxyReq.headers.set("Host", …)` does not error; it is dropped. So a Worker reaching an origin **by IP**
speaks whatever vhost the origin infers from the address — the default server, a wrong certificate, a 404.

Consequences to check for: a wrong vhost answering, a fallback certificate, or `/` returning some other
property's page. If the origin needs virtual-host routing, **fetch the hostname, not the IP.**

## 3. Closed backend ports read as a service outage

The Worker's route table may map paths to internal ports. If those listeners are down, the proxy target
refuses the connection — which presents as "the API is broken" rather than "a process is not running."

**Enumerate the ports the Worker names, not just 80/443:**

```bash
for p in 8080 8082 8084 8088; do
  (echo > /dev/tcp/<origin-ip>/$p) 2>/dev/null && echo "$p OPEN" || echo "$p closed"
done
```

Then separate the two failure classes cleanly: **a route with no listener** (host/ops work) versus **a route
that loops** (a Worker code fix). They need different owners, so report them separately.

## Reading a deployed Worker's source

The script is downloadable through the API — useful for confirming what a route actually does rather than
inferring from behaviour:

```python
GET /accounts/{account_id}/workers/scripts/{script_name}
```

Returns `multipart/form-data`; split on the boundary and take the part carrying the JS to get the source.

## Reporting a Worker-fronted hostname

Keep the claims independent so a partial fix is not read as a whole one:

- **edge restored** — flag applied and read back, `tls_verify=0`
- **service restored** — the real routes return their expected status through the edge
- **still broken** — per route: no listener, or looping; and who owns each

Do not fold "the handshake works now" into "the API is back."
