# Settlement receipts — "verified" is not "delivered", and neither is "sold"

An x402 gateway answers three different questions, and they are routinely collapsed into one:

| question | who can answer it | what the answer looks like |
|---|---|---|
| **Can they pay?** | your 402 body | a well-formed v2 challenge |
| **Did they pay?** | the facilitator's settle response | a settlement id / tx hash |
| **Did they get the good?** | your own response path | a 200 body that actually carries the payload |

**A traffic log usually records the first and the third, and calls the result "revenue".** Audit the schema
before believing any total built on it.

## The measured failure shape

A gateway logging 48,309 rows, of which **15 served a 200 — and 0 carried a transaction hash, anywhere in the
file.** Every served row read `stat=verified`, `rail=eip155:8453`, `tx=None`, `why=None`. So:

- **"Did they pay?" had evidence** — `stat=verified`, the verifier's verdict on the payment payload.
- **"What did we get for it?" had none.** No tx, no settlement id, no join key back to the chain.

Nothing errored, and the log looked complete. **A status field is a statement about what your code decided;
only a settlement identifier is a statement about what happened in the world.**

**Why it happens:** `stat` is written where verification happens, early. **The tx hash only exists after the
settle step succeeds**, and if the log writer runs before that, or is called from the challenge path, the field
ships `null` forever and no test notices — the schema permits null, the rows are otherwise correct.

## Audit recipe — run it before quoting any revenue figure

```python
rows = [json.loads(l) for l in open(LOG) if l.startswith("{")]
served = [r for r in rows if str(r.get("s")) == "200"]
print("served:", len(served), "with tx:", sum(1 for r in served if r.get("tx")))
print("5xx with no reason:", sum(1 for r in rows if str(r.get("s"))[:1] == "5" and not r.get("why")))
```

Three numbers decide whether the log is usable as revenue evidence:

1. **served rows with a non-null tx** — the only rows you can reconcile against the chain.
2. **the join** — take one tx out of the log, look it up on-chain, and confirm the `Transfer` to `payTo`.
   **If the join cannot be performed at all, say so; do not substitute a count of 200s.**
3. **non-2xx rows carrying no `why`** — a failure with no recorded cause cannot be diagnosed after the fact.
   Measured: 22 × HTTP 503 on one route, all `why=None`, all undiagnosable an hour later.

## The rules

- **Write the settlement id on the DELIVERED row, not just on the settle call.** If the writer runs before
  settlement completes, move it after — an id recorded in a different record than the 200 cannot be joined.
- **Make `tx` a required field on a 200.** A null on a served row means "we do not know that they paid" — a
  different and much louder state than `paid`. Never let null render as falsy success.
- **A boolean is not a receipt.** `verified: true` should carry the facilitator's own identifier beside it, or
  the claim is unfalsifiable after the fact.
- **Log a reason on every non-2xx**, from the exception that produced it. An empty `why` is the difference
  between a diagnosable outage and a mystery.
- **Never count 200s as sales.** A free route, a health probe, and a paid route all return 200. The sale is the
  settled transfer, and only the chain (or the facilitator's settlement record) can assert it.
- **State the join's absence explicitly** in any revenue report: *"N served, M with a settlement tx; the M rows
  are the only ones reconciled against the chain."* That sentence is honest at any M, including zero.

## Test the negative

Delete or blank the `tx` on a served row and confirm the audit's headline changes. **An audit that reads the
same whether or not the join is possible is not auditing the join** — it is counting rows and calling it
reconciliation.
