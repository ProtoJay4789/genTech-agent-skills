# Reading transfer LOGS on Base — which RPC serves it, and the empty-success trap

For counting on-chain inflows (API revenue, settlement totals, payTo credits). Companion to
`onchain-token-address-verification.md` (which checks the ADDRESS is live) — this one covers actually
QUERYING it. **Re-probe before relying on the table; public endpoints change without notice.**

## The headline: balance reads work everywhere, log queries do not

`eth_call` `balanceOf` and `eth_getBalance` are served by essentially every public endpoint, **including a
historical read pinned to a block**. `eth_getLogs` is gated, capped, or refused on most of them. So:

- **Prefer a balance-delta computation over a log scan when either would answer the question.** It is one
  call, works on every RPC, and needs no window arithmetic.
- **When you do need per-transfer detail, treat RPC capability as a first-class dependency** and pick the
  endpoint deliberately — not whichever URL happens to be first in a list.

## Measured capability (Base mainnet)

| Endpoint | `eth_getLogs` | Cap / behaviour |
|---|---|---|
| `mainnet.base.org` | refused | returns a JSON-RPC error (`-32011 request limit reached`); does NOT serve logs at all |
| `base-rpc.publicnode.com` | served | 50,000-block window cap |
| `base.drpc.org` | capped | 10,000-block cap |
| `1rpc.io/base` | capped | 50-block cap (unusable for backfills) |
| `base.llamarpc.com` | no | HTTP 525 |
| `base.blockpi.network` | no | key required |

Takeaway: a multi-RPC fallback list gives you **resilience for balances and none for logs** — one usable
endpoint means one point of failure, and a "it worked yesterday" query can silently become empty.

## The trap: an over-range query returns EMPTY, not an error

**A window wider than the endpoint's cap does not always raise. It can return a well-formed empty result —
indistinguishable from "no matching transfers", and therefore a false zero on a money figure.** This has no
failure signature: no error object, no timeout, no permission denied. Same class as an ignored query filter
that returns the default page, and the same class as any probe whose refusal looks like a clean result.

**Two defences, both required:**

1. **Bound and chunk.** Never issue an unbounded or `latest`-to-genesis range. Walk backward in windows at or
   under the smallest cap you may hit, and **return UNKNOWN if ANY window fails** — never sum the readable
   windows and present that as the total. A partial sum is the most believable wrong number available here.
2. **Control the empty.** Before reporting a zero, re-run a bounded window you KNOW contains a hit. If the
   bounded query finds it and the wide one did not, the wide one was refused, not empty.

```python
# Backward walk in bounded windows; refuse to report a partial total.
LOG_CHUNK = 50_000            # at or below the tightest cap you may encounter
rows, cursor = [], head
while cursor > oldest:
    lo = max(oldest, cursor - LOG_CHUNK)
    logs = rpc("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(cursor),
                                "address": TOKEN, "topics": [TRANSFER, None, topic_to]}])
    if logs is None:
        return rows, False     # UNKNOWN — do not present this as the total
    rows += decode(logs)
    cursor = lo - 1
return rows, True
```

## Cross-check with an independent instrument

Sum the decoded transfers and compare against the token balance delta over the same span — `balanceOf(payTo)`
read at the head block versus at `head - days x blocks_per_day`. `eth_call` with an explicit `blockNumber` is
served by every endpoint tested, so this second instrument is always available.

**When the two agree, that is the evidence. When they disagree, one instrument is wrong — investigate rather
than picking the flattering number.** Agreement is also what catches a silent cap: a log scan that truncated
will not match the delta.

## Also worth knowing

- **The `from` address of a settled x402 payment is the FACILITATOR's relayer, not the buyer.** Settlement uses
  a gasless authorization (`AuthorizationUsed` + `Transfer` in the same receipt) submitted by the facilitator,
  so the buyer's own `nonce` stays `0`. Filtering receipts by "the buyer sent it" finds nothing and reads as a
  failed payment.
- **To attribute a payment to a SERVICE, read it from the gateway, not the chain.** The chain carries the
  amount, never which route was bought. A response-status ledger on the gateway gives knocks (402) and served
  (200) per PATH — that is where per-service attribution lives.
- **Exclude your own test traffic explicitly and print the exclusion.** Self-settlements are real transfers and
  will inflate a customer-revenue figure unless the sender addresses are filtered and the filtered amount is
  stated inline.
