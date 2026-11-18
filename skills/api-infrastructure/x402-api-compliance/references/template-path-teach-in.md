# Template paths and catalogue crawlers — teach the caller, never charge it

A parameterised route (`/v1/defi/lp/{address}`) is advertised as a **template**. Catalogues and
conformance probes read that template and many of them **call it literally** — `:address`,
`{address}`, `:solana_address`. When your server answers the literal template with a bare **404**, the
directory records `paywall {ok:false, status:404}` against your origin and a buyer never sees a price.

**Measure it before theorising.** Classify your 404s by kind, not by path:

| kind | what it means |
|---|---|
| `:address` / `{address}` / `:solana_address` in the path | a crawler using a **stale cached** copy of your spec |
| `[object Object]` | a broken JS client serialised its argument |
| `.env`, `/.git`, `/wp-` | attack probe, not a buyer |
| a path that used to exist | retired route |
| `/robots.txt` | crawler etiquette |

One defect can dominate the total. If a single kind is most of your 404s, the fix is not more routes —
it is one response shape.

## The three wrong answers, and the right one

| answer | verdict |
|---|---|
| **404** | tells an agent nothing it can act on. The resource exists; only the parameter is missing. |
| **402 with `accepts`** | **catastrophic.** A payable challenge for a path that cannot serve means a buyer can pay for nothing. Charge-before-validate. |
| **silent price default** | same class — it invents a price for an undefined resource. |
| **402 `parameter_required`, no `accepts`** | **correct.** Machine-actionable, unpayable, and the agent can retry correctly. |

```json
{
  "error": "parameter_required",
  "reason": "unsubstituted_template",
  "service": "defi_lp_analytics",
  "detail": "This path is a TEMPLATE, not a resource. The service exists and is chargeable —
             substitute a real value for the parameter and call again. No payment is requested.",
  "retry_with": "/v1/defi/lp/0x7ebff188f2Eba16518C02864589b1403a5d1296a",
  "accepts_params": ["address"],
  "retry_example_source": "manifest",
  "discovery": "https://<host>/.well-known/x402"
}
```

**Carry `accepts` nowhere in that body.** The absence is the safety property, not a style choice.

## Build `retry_with` from the manifest, not from a hardcoded example

A hardcoded EVM `0x…` is a **confident wrong answer** for any service that also accepts Solana base58
(or is Solana-only). Prefer, in this order:

1. the manifest's own `examples[]` for that service (already a real, chain-correct path);
2. the concrete URL discovery already publishes;
3. the template with a **shape placeholder** (`<evm-0x-address-or-solana-base58>`), never a fake address.

Label which one you used (`retry_example_source`) — a later reader can then tell a manifest example from
a derived guess.

## Proof: assert BOTH directions, or the suite passes on the catastrophe

| case | expect | must |
|---|---|---|
| template `:address` | 402 | `accepts` **absent** |
| template `{address}` | 402 | `accepts` **absent** |
| real EVM address | 402 | `accepts` **present** |
| real Solana address | 402 | `accepts` **present** |
| retired route | 410 | no challenge |
| `/robots.txt` | 200 | — |

A check that only asserts "no 404 any more" passes when templates become **payable**. Test the refusing
direction explicitly, and re-run the suite against a tree with an **empty manifest** — see the
empty-container rule in `develop-and-verify`; with no manifest the guard goes inert and templates start
receiving valid challenges.

## Two adjacent fixes that belong in the same pass

- **Never publish a literal template on your own index/root.** `"/v1/{service}/{path}"` in a JSON
  endpoint map teaches a crawler exactly the shape you cannot serve. Publish derived **concrete** paths
  instead — and filter them through the same deliverability + retired-route predicate as the challenge,
  or you re-advertise dead routes from your own front door.
- **`robots.txt` must exist** and should explain the convention in the file itself:
  *a 402 with `accepts` is a PRICE, not an error; a 402 with `error: parameter_required` means your path
  was a template — follow `retry_with`.* Crawlers that cannot read robots may throttle themselves, and an
  agent that gets 404 there has learned nothing.

## Retired ≠ missing

A route you deliberately removed answers **410 Gone** with a pointer to live discovery — not 404 and not
503. 404 reads as "this seller is broken" and invites endless retries; 503 reads as an outage and drags a
directory listing to DEGRADED. 410 is the machine-readable "stop asking".
