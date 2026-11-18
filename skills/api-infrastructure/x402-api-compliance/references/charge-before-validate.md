# Charge-before-validate — never issue a payment challenge for something you cannot serve

> Companion to `v2-payment-challenge.md` (which covers challenges that look right but cannot be paid).
> This one covers the mirror defect: a challenge that is **payable** for work that will never be delivered.

## The failure

An x402 gateway issues a well-formed 402 challenge **first** and proxies to the backend **after settlement**.
Any path that reaches the challenge handler therefore becomes payable — including paths no backend can answer.
The buyer pays, the proxy returns `404`, and value moves with no delivery.

Two shapes, same code path:

- **Unknown service segment** — usually already fixed by an explicit deliverability check (`service_not_found`).
- **Known service, nonsense leaf** — the survivor: `/v1/nft/nope-xyz`, `/v1/gas/nope-xyz`, `/v1/nft/search/nope`.
  The service exists, so the deliverability check passes; nothing validated the leaf.

If a service declares **no `{params}`** in its manifest endpoint, a naive validator has nothing to check and lets
the whole tail through. That is the hole.

## Detection — three curls, from the public URL

```bash
for p in /v1/not-a-service-xyz /v1/<service>/nope-xyz /v1/<service>/<real-leaf>; do
  printf '%-34s ' "$p"; curl -s -o /dev/null -m 12 -w '%{http_code}\n' "https://<host>$p"
done
# expect 404 · 404 · 402      a 402 in the middle IS the defect
```

Run it per service family — the defect is per-route, because each service declares a different endpoint shape.

## The fix — validate the LEAF, not just the service

Derive a **static leaf prefix** from the declared endpoint template, then require the incoming path to match it:

```python
def static_leaf_prefix(endpoint: str) -> list:
    """brace-free segments a service declares after /v1/<service>/"""
    pre   = (endpoint or "").split("?")[0]
    parts = [p for p in pre.split("/") if p]
    if parts and parts[0] == "v1": parts = parts[1:]
    if parts:                        parts = parts[1:]      # drop the service segment
    out = []
    for seg in parts:
        if seg.startswith("{") and seg.endswith("}"): break  # params start here
        out.append(seg)
    return out
```

- `/v1/defender/classify/{chainId}/{token}` → `['classify']`
- `/v1/nft/search` → `['search']`
- `/v1/market/price/{symbol}` → `['price']`

Gate the challenge on it:

```python
if prefix and segs[:len(prefix)] != prefix:                    # wrong leaf
    return reject("unexpected_subpath", segs[:len(prefix)])
if prefix and not param_names and len(segs) > len(prefix):     # right leaf, junk below
    return reject("extra_subpath", segs[len(prefix):])
```

**Routing aliases need their own allow-list — skipping them reopens the hole.** A key like `*_native` (or an
OKX alias) resolves to a manifest service but serves a *different* path, so validating it against its parent's
leaf rejects its own legitimate route — and skipping it entirely leaves exactly that route charging for nonsense.
Both wrong answers were shipped in turn: the skip version let `/v1/<alias-svc>/nope-xyz` return a payable 402
after the main fix was deployed.

**Enumerate the alias map BEFORE writing the validator** — aliases are invisible in the manifest, so a
manifest-driven fix silently misses them:

```bash
grep -n 'URL_TO_SERVICE\s*=\|_ALIASES\s*=\|_native"' server.py | head -20
```

Every public segment that maps to a *different* service key is a row the matrix must cover. A route whose key
ends in `_native` (or any alias suffix) is exactly where a leaf-prefix rule goes blind.

```python
# measured from the alias backend's own routes, not inferred
_NATIVE_SUBPATHS = {"gas_oracle_native": {"gas", "ethereum", "base", "polygon", ...}}

if service_key.endswith("_native"):
    allowed = _NATIVE_SUBPATHS.get(service_key)
    if allowed is not None and segs and segs[0] not in allowed:
        return reject("unexpected_native_subpath", segs[0])
    if allowed is not None:
        return ""            # validated above; nothing further to check
```

**An alias absent from the table is left unchecked — say so.** A guessed set 404s real customers; a missing
check costs nothing we did not already have. The limit is stated, not hidden.

Do **not** touch the two deliberate exceptions: a **collection root** (`/v1/defi/lp`) serves a discovery document,
and a **bare service root** (`/v1/defi`) must challenge rather than 307 — that no-redirect behaviour exists
because clients preflight the advertised resource URL.

## Testing without deploying

The validator functions are pure: read them out of the source with `ast`, feed them the **real** manifest, run a
matrix. This catches what a diff review misses — a validator that rejects the shipped endpoints.

```python
import ast, json, re
src   = open("server.py").read()
nodes = [n for n in ast.parse(src).body
         if isinstance(n, ast.FunctionDef) and n.name in {"static_leaf_prefix", "subpath_rejection"}]
ns = {"SERVICES": json.load(open("manifest.json"))["services"], "re": re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "<f>", "exec"), ns)
```

**Acceptance matrix — both directions, every route:**

| case | expectation |
|---|---|
| each service's own declared endpoint, concretised | **allowed** — false rejections must be **0** |
| wrong leaf under a real service | rejected |
| right leaf plus a junk tail | rejected |
| **each routing alias's legitimate sub-paths** (e.g. `/<svc>/<chain>`) | **allowed** |
| **each routing alias's nonsense sub-path** | rejected |
| collection root (`/v1/defi/lp`) | allowed |
| bare service root (`/v1/defi`) | allowed |

A matrix that checks only the rejections passes while breaking every real route. **Assert zero false rejections
explicitly** — the first version of this validator still let `/v1/nft/search/nope` through, and only the matrix
said so.

**⚠️ Build the matrix from the LIVE manifest, never from the allow-lists your patch added.** A harness that
imports the patch's own constants inherits its blind spot: a version that skipped alias keys and *also* skipped
them in the test scored 10/10 green, then the live call returned the old payable 402 within a minute. Alias and
indirection rows are not optional — they are the rows that fail.

**And run the acceptance against the DEPLOYED service, not only the local functions.** The local matrix is a
hypothesis; the public curl is the experiment. After the deploy, also prove the running file is the patched one
(`cmp` live vs patched, and `cmp` live vs pre-patch must differ) — a clean restart of an unpatched file serves
old behaviour with new confidence.

## Order of operations

1. Validate **before** the challenge exists — that is the whole point; validation after settlement still collects
   the money and only changes the error text.
2. Keep any post-settlement validation too: the two gates catch different bugs.
3. Reject with an honest 404 body (`{"error": "unservable_subpath", "reason": …}`), never a payable challenge
   with a caveat buried in a description field.

## The mirror defect — charge-then-REDIRECT

Validating the path before the challenge is only half the ordering rule. The other half: **nothing may redirect the
buyer after settlement.** A gateway that settles first and proxies second will happily take the money and then emit
the proxy's `307` with an empty body:

```
/v1/<service>/<param>/   → 307, settled  ← paid, delivered nothing
/v1/<service>/<param>    → 200, settled  ← correct
```

Cause is almost always canonicalisation — a trailing slash, a case fold, a legacy alias — applied at the proxy instead
of at route resolution. **Normalise the request path before the challenge is issued**, so the path that gets priced is
the path that gets served. Two rules that follow:

- **Treat any 3xx after settlement as a delivery defect**, even when the receipt says `success:true` and the chain
  shows the transfer. The money moved; the product did not.
- **Never let a client "fix" it by following the redirect** — the retry is a second charge for one purchase.

Test **both spellings of every published URL** in the acceptance matrix. A matrix built only from the canonical paths
passes while every listing that ships a trailing slash charges and delivers nothing.

## Why it matters more than it looks

Agents enumerate paths; a crawler that finds a service prefix tries its leaves. So the population that hits this
defect is exactly the population that might have paid — each call converts a possible customer into an agent that
learned the endpoint takes money and returns nothing. The same principle covers a rail advertising a payTo address
that cannot receive: **a challenge is an advertisement; never advertise what you cannot deliver.**
