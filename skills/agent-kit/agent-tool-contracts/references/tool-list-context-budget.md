# Tool-list context budget — what an agent pays to find you

Depth for `agent-tool-contracts` §7. Measured on a real MCP server we sell through, not on a sample.

## The numbers that frame every decision here

| surface | tools | payload | ≈ tokens |
|---|---|---|---|
| our server, before | 11 | 9,188 b | 2,297 |
| our server, after trimming | 11 | 5,880 b | 1,470 |
| a 2,500-endpoint API via two Code Mode tools | 2 | ~4,000 b | ~1,000 |

The comparison that matters is **per endpoint**, not per server: ten routes costing 2.3× a 2,500-route API is a
discovery tax nobody pays knowingly — they simply never load you.

## Where the bytes actually go

Measure the split before trimming, or you will trim the wrong half:

```python
import json
raw = json.dumps({"tools": tools})
schema_b   = sum(len(json.dumps(t["inputSchema"])) for t in tools)
desc_b     = sum(len(t["description"]) for t in tools)
annot_b    = sum(len(json.dumps(t.get("annotations") or {})) for t in tools)
print(len(raw), schema_b, desc_b, annot_b)
```

On ours: schemas 4,496 b (the contract — keep), descriptions 1,642 ch (ours — cut), annotations 95 b × 11
(machine-read — keep). The single biggest line item was **one sentence repeated on all 11 tools**.

## The trimming recipe

1. **One line per tool in the list.** Price + the shortest true clause. Prefer the field already written for
   search (`bazaarDescription`-style) over the catalogue paragraph.
2. **A shared parameter's long description moves to the free catalogue response.** Short hint stays in the
   schema so the tool is still callable from the list alone.
3. **Never let a cut produce a fragment.** Sentence → clause → word boundary → strip dangling `e.g`, `i.e`,
   `(`, `such as`, trailing comma. A hint that reads broken is worse than the paragraph it replaced.
4. **Re-verify the contract after trimming**, mechanically, because names can survive while a schema quietly
   loses its shape:

```python
bad = []
for t in tools:
    s = t["inputSchema"]
    if s.get("type") != "object" or "properties" not in s: bad.append(t["name"]+":schema")
    if "examples" not in s: bad.append(t["name"]+":examples")
    if not (t.get("annotations") or {}).get("readOnlyHint"): bad.append(t["name"]+":annotations")
    if not t.get("title") or not t.get("description"): bad.append(t["name"]+":title/desc")
```

## Measuring it honestly when the list is filtered by a readiness gate

A server that withholds unservable routes serves a DIFFERENT tool count from a scratch box that cannot reach its
backends — so a naive before/after on a scratch port compares 11 tools against 2 and reports a 70% saving that
did not happen. **Force the gate to the live servable set and measure the same population both times:**

```python
LIVE = {"route_a", "route_b", ...}
m._route_is_servable = lambda k: (True, None) if k in LIVE else (False, "withheld")
tools, withheld = m._mcp_tools()
```

## The budget guard (so prose cannot creep back)

Add the byte count to whatever already validates the published surfaces, with a ceiling that leaves room for a
service or two and no room for a paragraph per tool:

```python
r = post_json(f"{API}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
b = len(json.dumps(r))
if b > 7000:
    problems.append(f"tools/list is {b} bytes, over budget — prose belongs in the free catalogue tool")
```

**Name-comparison checks cannot catch this.** A guard that asks "is every service listed" stays green while the
list doubles in size, which is exactly the regression that costs every future agent. Measure bytes, not names.

## When the per-tool shape stops scaling at all

Past roughly twenty routes, the fixed-footprint shape wins: two tools (`search` over the spec, `execute` for
code in a sandbox), with the spec never entering the model's context. The design problem is not `search` — it is
that `execute` running scripts against *paid* routes needs payment to happen inside the sandbox through the
caller's own client. Keep the cheap-list version until the route count makes it the binding cost.
