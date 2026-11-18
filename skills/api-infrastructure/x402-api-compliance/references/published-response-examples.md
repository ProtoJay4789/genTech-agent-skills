# Published response examples — a false one costs a payment

The 402's `extensions.bazaar.info.output` block is documentation a buyer's agent reads **before** it pays.
`output.example` is the part it plans a parser from. Treat it as a contract, not as decoration.

## The rule

**Publish an example ONLY if it was captured from a real response. Otherwise publish none.**
`output.example` is optional in the bazaar schema (`required: ["type"]`), so omitting it costs nothing but a
little guidance — while shipping a wrong one costs the buyer a payment and the seller a customer.

An agent given **no** shape parses defensively. An agent given a **false** shape parses confidently and breaks on
the 200. That asymmetry is the whole argument.

## The tell: identical examples across services

The failure is not usually a single bad example — it is **one example copy-pasted into every service's
challenge**. If `market price`, `agents search`, `wallet portfolio` and `defender classify` all advertise the same
`output.example`, at least three of them are lying, because no four APIs return the same object.

How to check, on the live gateway, not in the source:

```
for r in /v1/market/price/ETH /v1/agents/search /v1/wallet/portfolio/<addr> /v1/defender/classify/8453/<token>; do
  curl -s "https://<host>$r" | python3 -c "import json,sys;print(json.load(sys.stdin)['extensions']['bazaar']['info']['output'].get('example'))"
done
```

Identical output across all four = a hardcoded block. One distinct example each = real.

## Why this class survives so long: the fix is applied one field too narrow

The 402 challenge has two shape-describing fields, `input` and `output`. When `input` was de-hardcoded (every
service had been publishing the same `pathParams: {"address": …}`), the fix landed on `input` and `output` kept
its hardcoded example — often **directly underneath the comment explaining why hardcoding it was wrong**. When you
fix a hardcoded descriptor, grep the whole challenge builder for every other field that describes per-service
shape, or you ship half the fix and a comment claiming it is done.

## The honest fallback

```python
def _output_spec(service_name: str) -> dict:
    return {"type": "json",
            "description": (f"JSON result from {service_name}. No response example is published: "
                            "parse defensively and read the 200 body's own fields.")}
```

Say in the description that the omission is deliberate, so the next reviewer does not "restore" the example.

## How to get real examples (the correct end state)

A seller at scale publishes a **captured** sample — a full JSON body from an actual call, per service. To do this
you need one successful response per service, which means either backend access from the machine doing the work
or a paid call. Two traps:

- **Backends bound to `127.0.0.1` on the host are not reachable from a containerised agent seat** — connection
  refused, which looks like a dead backend. Confirm from where the challenge is actually built before planning
  a capture.
- **Never hand-write the shape from the service description.** A plausible object invented from a description is
  exactly the defect this file exists to prevent, one layer down.

## Verification before deploy

1. Every probed service returns 402 with `accepts` non-empty and **no** `example` key (or a distinct real one).
2. The `output` block still validates against the schema shipped beside it in the same extension.
3. The existing template/route regression suite passes on a local instance, not just the changed file.
4. **Re-read the LIVE endpoint after the restart.** Editing the file is not deploying it: a gateway in another
   container caches its code at start, so measuring production after the edit is how you discover the change has
   not shipped. A pre-deploy "verified" claim with production still serving the old block is a false receipt.
