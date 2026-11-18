# Validate the PATH before you issue the challenge

A gateway that settles **before** it proxies will happily take money for a resource no backend can serve.
The buyer pays, the backend 404s, and from the seller's side it looks like a failed customer instead of a
broken door. This is the path-level twin of "never sell what you can't deliver" — same rule, different axis:
the *service* can exist while the *path* cannot.

## The defect, precisely

```
/v1/definitely-not-a-real-service-xyz   → 404  service_not_found        ✅ correct
/v1/nft/nope-xyz                        → 402  full payable challenge   ⚠️
/v1/gas/nope-xyz                        → 402  full payable challenge   ⚠️
```

Typical cause: path validation is keyed on **declared parameters** in the service's manifest endpoint.

```python
names = _path_param_names(cfg["endpoint"])     # ['address'] for /v1/defi/lp/{address}
if not names:
    return ""                                  # ← anything below the service segment is accepted
```

Every service whose endpoint declares **no** `{param}` — a fixed leaf like `/v1/nft/search` or `/v1/gas/gas`
— therefore accepts an arbitrary tail. The service segment is validated; the leaf never is.

## The fix — a service serves its declared leaf and nothing else

Derive the brace-free segments the endpoint declares after `/v1/<service>/`, then require the incoming path to
match them:

```python
def _static_leaf_prefix(template: str) -> list:
    """/v1/defender/classify/{chainId}/{token} -> ['classify'] ; /v1/nft/search -> ['search']"""
    pre = (template or "").split("?")[0]
    parts = [p for p in pre.split("/") if p]
    if parts and parts[0] == "v1":
        parts = parts[1:]
    if parts:
        parts = parts[1:]                      # drop the service segment itself
    out = []
    for seg in parts:
        if seg.startswith("{") and seg.endswith("}"):
            break                              # stop at the first parameter
        out.append(seg)
    return out
```

Then, inside the sub-path check, before any 402 is built:

```python
prefix = _static_leaf_prefix(cfg.get("endpoint") or "")
if prefix and segs[:len(prefix)] != prefix:
    return "unexpected_subpath:" + "/".join(segs[:len(prefix)])
if prefix and not names and len(segs) > len(prefix):
    return "extra_subpath:" + "/".join(segs[len(prefix):])
```

- **`unexpected_subpath`** — wrong leaf (`/v1/nft/nope-xyz`).
- **`extra_subpath`** — right leaf, junk below it (`/v1/nft/search/nope`). The first rule alone misses this:
  the prefix matched and there were no params to validate, so the tail slid through.
- **Skip routing aliases** (a `*_native` key that borrows its price from another manifest entry, an `okx`
  alias). Their served path deliberately differs from the endpoint they inherit, so the prefix rule
  false-positives on them. Gate the check on `not service_key.endswith("_native")` or an explicit alias flag.

Both errors must return **404 before payment**, not after. A challenge is an advertisement.

## Test it without the app's dependencies

The gateway container has runtime deps the agent host usually lacks (`fastapi`, `httpx`), so a full import is
not available for testing. Execute **the patched functions themselves**, read straight out of the source by
AST, against the **real manifest** — a fixture proves nothing here:

```python
import ast, json
tree = ast.parse(open("server.py").read())
want = {"_static_leaf_prefix", "_svc_cfg", "_subpath_rejection", "_path_param_names"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
ns = {"SERVICES": json.load(open("x402.json"))["services"], "re": re, "_TEMPLATE_RE": re.compile(r"\{[^}]*\}")}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "<f>", "exec"), ns)
```

Then run a **two-sided matrix** and require both halves:

| side | expectation |
|---|---|
| every declared endpoint, concretised (`{address}` → a real address, `{symbol}` → a real ticker) | **allowed**, 0 false rejections |
| a nonsense tail under each service (wrong leaf, and right-leaf-plus-junk) | **rejected**, 0 misses |

Print the per-case verdict, not a total. The first version of this fix passed the "wrong leaf" cases and
**still let `/v1/nft/search/nope` through** — the matrix caught it; reading the diff would not have.

## Acceptance — from outside, after one restart

Touching `server.py` changes a bind-mounted file; the running process keeps serving the old code until it
restarts. One restart, then measure the **pair** for each service:

| path | expected |
|---|---|
| `/v1/<service>/nope-xyz` | **404** (was 402) |
| `/v1/<service>/<real leaf>` | **402**, unchanged |

A firewall rule protecting the gateway survives the restart if it lives in `rules.v4`; state that after a
deploy so "the port is still closed" is not assumed.

Keep a timestamped copy of the pre-change file and print the rollback command
(`cp <file>.bak-<stamp> <file> && docker restart <container>`) **before** asking for the restart. On a
paid path, the operator needs the undo in the same message as the change.

## Related

- `references/v2-payment-challenge.md` — the five field defects that make a challenge unpayable.
- The Worker-side equivalent of this rule (pre-flight the fetch, never sell what you can't deliver).
- Scope of the defect matters for the report: buyers reached the paywall and were refused by *us*, which is
  not the same finding as "no demand" — never fold a broken door into a demand conclusion.
