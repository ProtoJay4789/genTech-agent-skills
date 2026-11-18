# Discovery-surface audit

You publish one inventory (services, prices, chains) through many doors. Every door is a separate
claim, and they fail independently — so an audit that checks one of them has checked almost nothing.

## The surfaces, and the failure each one has

| surface | what it is for | the failure that hides there |
|---|---|---|
| `/.well-known/x402` | capability manifest | templated `endpoint` values; hand-written counts |
| `/.well-known/x402-bazaar` | full catalogue + prices | withheld services still listed; stale `updated` |
| `/.well-known/agent-card.json` | agent identity | a `payTo`/chain that no longer settles |
| `/openapi.json` | machine enumeration contract | **templates published as callable paths** |
| `/status` | liveness/inventory | lists every configured service, not every servable one |
| `llms.txt` / `llms-full.txt` | agent-facing index | a curated subset mistaken for the whole corpus |
| public README / catalogue repo | human + crawler entry | prose counts; a service you removed |
| `/mcp` `tools/list` | tool discovery | a tool per withheld service |

## Procedure

**1 · Fetch every surface and keep the raw bytes.** A surface you did not fetch is a surface you did
not audit. Fetch with a normal UA; a discovery document that only renders for browsers is itself a
defect.

```bash
for p in /.well-known/x402 /.well-known/x402-bazaar \
         /.well-known/agent-card.json /openapi.json /status; do
  curl -s -o "surf$(echo $p | tr '/.' '__').json" -w "%{http_code} $p\n" "$BASE$p"
done
```

**2 · Count the inventory on each, and compare to the live set — not to each other.** Two surfaces
agreeing is not evidence if both are hardcoded.

```python
live = set(manifest["services"])                    # the servable set
for name, doc in surfaces.items():
    assert set(doc["services"]) <= live, f"{name} advertises non-servable services: {set(doc['services']) - live}"
```

**3 · Grep every surface for template braces.** Any `{param}` a machine can read as a URL is a link
it may follow.

```bash
for f in surf_*.json; do
  printf '%-28s ' "$f"; grep -o '"[^"]*{[a-zA-Z][^"]*"' "$f" | wc -l
done
```

Braces are legitimate in a documented *template* field. They are a defect anywhere a reader treats
the value as callable — and always a defect under an OpenAPI `paths` key.

**4 · For OpenAPI, split `paths` into concrete and templated and count both.**

```python
paths = spec["paths"]
templated = [p for p in paths if "{" in p]
concrete  = [p for p in paths if "{" not in p]
print(f"{len(concrete)} callable · {len(templated)} templated (MUST NOT be paths)")
```

Anything in `templated` will be requested literally by an enumerating crawler. If it must be
published, move it to `x-resource-template` on the concrete operation.

**5 · Probe a template the way a crawler would, and read the STATUS SEMANTICS.**

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/v1/thing/%7Bid%7D"
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/v1/thing/{id}"
```

A `404` here is *correct behaviour* (refuse, charge nothing) and simultaneously *proof of an advertised
defect*. Both are true: never report the route as broken, and never leave the advertisement in place.
A `402` on a template is worse — it means you are willing to sell a URL nobody can fill in.

**6 · Check the counts in prose against the arrays beside them.**

```bash
curl -s "$BASE/openapi.json" | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['description'])" \
  | grep -oiE '[0-9]+ (chains|services|endpoints|rails)'
```

Every hit is a hand-written number. Compare it to the generated field, and to what actually settles —
*configured* and *settling* are two facts and must be stated separately.

**7 · Re-fetch the public URL after deploying a fix.** A change that needs a restart is not deployed
until the surface shows it. Grep for the stale claim rather than checking for `200`.

## Reading a crawler's log to find which surface it uses

Before fixing anything, confirm which document the caller actually reads. Group the caller's requests
by path and status:

```python
calls = [r for r in rows if crawler_ua in (r.get("ua") or "").lower()]
Counter(r["p"] for r in calls).most_common(10)
```

A caller that fetches **one** document and then hits every path in it is telling you exactly which
surface to fix. A caller hitting many documents is doing discovery as intended and its 4xx are its own
noise. Distinguish the two before writing a fix.

Also compare its **concrete** hits against its **template** hits for the same service: the ratio shows
whether the concrete form is even visible to it. If it calls the template far more often, the template
is what your spec is emphasising.

## Honest limits to state in the audit

- **Unverified until deployed.** Re-crawl behaviour after a spec change is a prediction; say so.
- **Probe callers are not customers.** A monitor/crawler hitting a route says nothing about demand.
- **Archive depth caps the negative.** A window beyond the endpoint's available history fails
  per-chunk; count failed chunks and refuse to report a total while any remain.
- **A surface you only read as HTML has not been audited.** Fetch the machine form.
