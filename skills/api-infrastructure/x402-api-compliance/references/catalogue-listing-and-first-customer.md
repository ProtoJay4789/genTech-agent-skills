# Catalogue listing: getting indexed, staying indexed, and counting real customers

A paid API can be protocol-correct, settle real money, and still be invisible to every buyer because it is not
in the catalogue buyers query. This file is the operational sequence: prove the settlement, prove the listing,
then prove a *customer* (not a self-payment).

## The admission gate is a settlement, not a registration

There is no signup endpoint. A facilitator catalogues a resource **after a settlement for that endpoint
completes**, reading which resource was bought from `paymentPayload.resource` in the settlement payload.

- **Indexing runs on `settle`, not on `verify` alone.** Field reports exist claiming verify is sufficient;
treat settle as the reliable path and verify as an optimisation to *test*, never to budget on.
- A settlement that omits `paymentPayload.resource` moves money and registers nothing. Check that field before
  spending anything on a "trigger a listing" attempt — see `references/client-side-signing-compatibility.md`.
- Settling through facilitator A does not list you in facilitator B's index. Settlement routing and discovery
  are separate products; if the catalogue you want is another party's, the settlement usually has to be theirs.

## Three independent proofs, in this order

A single green check is a claim. Run all three, because each can pass while another fails.

1. **Facilitator receipt.** Decode the base64 `payment-response` header (read case-insensitively). It must carry
   `success: true`, a `transaction`, and a `payer`.
2. **The chain, not the receipt.** `eth_getTransactionReceipt` on that hash → `status: 0x1`, then find the token's
   `Transfer` log and assert **amount, from, to** against the addresses you expect. A receipt is a facilitator
   opinion; the block is the event.
3. **The catalogue.** Query discovery by *search*, not by paging.

## Never conclude "not listed" from page 1 of the catalogue

Catalogues hold tens of thousands of resources. Page 1 of the paginated catalogue will not contain you, and an
offer that sorts low never appears there at all.

- Use the **semantic search** endpoint (`discovery/search?query=<your service name>`). That is what an agent
  with a need actually calls, and it is the honest test of discoverability.
- **Distrust a merchant/filter lookup that returns a full page.** If a `?payTo=…` (or similar) query returns the
  same 100 unfiltered rows regardless of the parameter, the parameter is being ignored — the endpoint accepted
  your syntax and silently dropped your filter. Verify the filter *filtered*: compare returned count against the
  count that match your own address. A zero result from an ignored filter is not evidence of absence.
- Catalogue access comes in several modes; test the one your buyer's client uses. A JSON discovery endpoint may
  answer `405` to `GET` because it speaks MCP over `POST` — a 405 means the path exists, not that it is broken.

## Staying listed is a separate problem from getting listed

Indexes apply a **recency window**: a resource with no activity for roughly a month is dropped from results.
That means a listing you earned can silently disappear while every endpoint stays healthy and no error is
raised — the failure mode is indistinguishable from "nothing to report".

- Monitor listing count, and alert on a **drop to zero**, not on an error. An absence of errors is not presence.
- Re-check by search after any window longer than the recency period, or after a period with no traffic.

## A 200 on a paid route is NOT a sale

This is the label that hides revenue gaps for weeks. Split the response classes before reporting anything:

| signal | meaning |
|---|---|
| request carries a **payment signature header** | a genuine payment attempt — the only population that can become income |
| 402 then nothing | was quoted, did not attempt — a viewer, not a buyer |
| 2xx **without** a payment header | free, cached, keyed, or index/docs traffic — never a sale |

- Count **payment-attempt headers**, not 2xx responses. An endpoint serving a public index, manifest, docs page
  or MCP handshake returns 2xx all day and will dominate any naive count.
- When reporting income, state the attempt count separately from the served count. `quoted / attempted /
settled` is the only triple that cannot flatter itself.

## Counting customers when the log has no payer field

An API's own log often records status, route and transaction hash but **not who paid**. Do not infer a customer
from a transaction existing.

- Keep a set of **your own wallets** and exclude them explicitly. A self-payment proves the rail works; it is
  the documented admission procedure, not demand.
- Resolve the payer from the **chain** (`Transfer.from` on the settlement tx), not from the log. The chain is the
authority on who paid.
- Read settlement logs from the path the writer actually uses. A logger that derives its directory from its own
  module location will recreate and write to that directory even if you relocate a copy — reading the relocated
  copy yields a file that looks frozen at the moment of the move, and hides every settlement after it.

## Report the milestone without inflating it

"First sale" is only true when the payer is not you. Say which it was: a self-payment opens the door, a
third-party payer is revenue. Writing the first as the second makes every later number untrustworthy.
