# Validate the PATH before you quote a PRICE

A gateway that settles first and proxies second inverts the only order the customer can
observe. If the challenge is issued before the request is proven servable, a buyer pays and
receives a 404: **value moves, delivery does not.** Anyone enumerating paths (scanners, indexers,
listing monitors) will find every one of these holes and pay into one.

## The rule

**Resolve the incoming path to a real route AND its parameters before emitting a 402.** If it
cannot be served, answer 404 with a reason. A price challenge is an advertisement; never
advertise what you cannot deliver.

## Where the defect actually hides

The service segment is usually validated — `/v1/definitely-not-a-real-service` answers
`service_not_found`. The bug lives one level **below** it:

| request | naive result | why |
|---|---|---|
| `/v1/<svc>/<wrong-leaf>` | 402 payable | only the service segment was checked |
| `/v1/<svc>/<right-leaf>/<junk>` | 402 payable | leaf matched, no params to validate, tail accepted |
| `/v1/<svc>/<param-looking junk>` | 402 payable, then 500/404 | param shape never checked against the declared type |

The trap is structural: a validator written as `if not declared_params: return ""` (nothing to
check → no rejection) passes **everything** for every parameterless service. Those are usually
the cheapest, most-enumerated routes, so this is the highest-traffic hole in the catalogue.

## Implementation shape

Derive the leaf from the service's own manifest endpoint — never a second hand-maintained list:

```python
def static_leaf_prefix(endpoint: str) -> list[str]:
    """Brace-free path segments declared after /v1/<service>/, stops at the first {param}.
    '/v1/defender/classify/{chainId}/{token}' -> ['classify']
    '/v1/nft/search'                          -> ['search']
    ''''"""
    parts = [p for p in (endpoint or "").split("?")[0].split("/") if p]
    if parts and parts[0] == "v1":
        parts = parts[1:]
    if parts:
        parts = parts[1:]                     # drop the service segment itself
    out = []
    for seg in parts:
        if seg.startswith("{") and seg.endswith("}"):
            break
        out.append(seg)
    return out
```

Then two rejections, and keep them **separately named** so the reason is readable in logs and the
verdict is testable:

- `unexpected_subpath:<seg>` — the path does not start with the declared leaf.
- `extra_subpath:<tail>` — the leaf matched, the service declares **no** parameters, and there is
  more path below it.

```python
prefix = static_leaf_prefix(cfg["endpoint"])
if prefix and segs[:len(prefix)] != prefix:
    return f"unexpected_subpath:{'/'.join(segs[:len(prefix)])}"
if prefix and not declared_params and len(segs) > len(prefix):
    return f"extra_subpath:{'/'.join(segs[len(prefix):])}"
```

**Exempt routing aliases** (`*_native` and similar) whose served path deliberately differs from
the manifest endpoint they borrow a price from — otherwise the fix takes a working route offline.

## Preserve the deliberate non-defects

Two paths look wrong and are not. Check them before adding rejection logic, or the fix breaks
shipped routes that exist for a reason:

- **Bare service root** (`/v1/<svc>`) — must challenge, not 307-redirect. A client that preflights
  `advertised resource == challenging route` fails on a redirect, and that failure is silent.
- **Collection root** (`/v1/defi/lp`) — answer with a non-payable discovery document (200), not a
  challenge and not a 404. Crawlers read 404 as an outage.

## Test it without the app's dependencies installed

The agent container frequently lacks the gateway's own deps (`fastapi`, `httpx`), so importing the
module to test is not available. Extract the patched functions from the file by AST and run them
against the real manifest — that exercises the shipped code, not a re-implementation:

```python
import ast, json
tree = ast.parse(open("server.py").read())
want = {"_static_leaf_prefix", "_svc_cfg", "_subpath_rejection", "_path_param_names"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
ns = {"SERVICES": json.load(open("x402.json"))["services"], "re": re,
      "_TEMPLATE_RE": re.compile(r"\{[^}]*\}"), "_PARAM_SHAPES": {}}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "<f>", "exec"), ns)
```

**Run a full matrix, in both directions, and require zero on each:**

| direction | cases | required |
|---|---|---|
| must ALLOW | every service's own endpoint, concretised from its template | false rejections = **0** |
| must REJECT | wrong leaf, right leaf + junk tail, malformed param, per service | missed = **0** |

A one-sided test is worthless here: a validator that rejects everything passes the second row and
takes the whole catalogue down. The first matrix run of this pattern missed `right-leaf + junk`
(`/v1/nft/search/nope`) — the matrix found it, eyeballing the diff did not.

## Acceptance, from outside

Deploy needs a restart, so state the five probes up front and run them after:

```bash
for p in /v1/nft/nope-xyz /v1/gas/nope-xyz; do   # expect 404
  curl -s -o /dev/null -w "$p %{http_code}\n" "https://<public-host>$p"; done
for p in /v1/nft/search /v1/gas/gas /v1/market/price/ETH; do   # expect 402
  curl -s -o /dev/null -w "$p %{http_code}\n" "https://<public-host>$p"; done
```

Keep the pre-patch file as a named backup and hand over the one-line rollback with the deploy:
`cp server.py.bak-<reason> server.py && <restart>`. **A money-path change shipped without a named
rollback command is a change the owner cannot undo at the moment it matters.**

## Why this outranks most other defects

While the paywall is verified-enforced, this is the first thing a genuinely paying buyer
encounters: an agent that paid and got nothing does not file a bug report, it leaves and tells its
operator. Fix it **before** opening or repairing the payment path, never after — the repair is what
finally lets these requests convert into real money lost.
