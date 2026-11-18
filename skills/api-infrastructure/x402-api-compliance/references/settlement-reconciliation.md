# Settlement reconciliation without an indexer

Answering *who paid us, on which rail, for what* — from the chain, with no paid block indexer and no
range scan. Use when a payment log records that money moved but not which transaction, or when a
reconciliation job keeps dying on public RPC throttling.

## The primitive is the RECEIPT, not the log range

`eth_getLogs` over months of blocks is not viable on public RPC: Base endpoints cap the range at
50,000 blocks **and** throttle sustained scans — a run can complete zero chunks in minutes. A paid
indexer replaces the scan, but it is not required:

```
payment log (tx hash) -> eth_getTransactionReceipt (one call per hash) -> decode ERC-20 Transfer
```

`eth_getTransactionReceipt` is a single free, unmetered call. One call per settlement, forever.
Decode the transfer:

- `topics[0] == 0xddf252ad…23b3ef` (Transfer)
- payer = `0x` + `topics[1][-40:]` · recipient = `0x` + `topics[2][-40:]`
- amount = `int(log["data"], 16)`, scaled by the token's decimals
- read `blockNumber` and `status` (`0x1` = success) from the receipt itself

**But this only works if the hash was kept.** A gateway that marks a payment `verified` without
persisting the settlement hash can never answer the question — the fix is at the WRITE, not the
reconciler. Extract the hash from the settle response in every shape it arrives (dict key
`transaction` / `tx_hash` / `transactionHash`, object attribute of the same names, or a bare `0x…`
returned as the reason string), and persist it beside the verdict.

**Absent must stay absent.** Write `"tx": null` when the rail returned no hash; never default it to
`0x0` or an empty string, or "we have no hash" becomes indistinguishable from "the hash is empty"
and every count downstream inherits the ambiguity.

## Verify the KEY before blaming the plan

Etherscan V2 keys are **per-chain gated**, not per-account. The same key answers:

```
chainid=1     -> {"status":"1","message":"OK","result":"…"}
chainid=8453  -> {"status":"0","message":"NOTOK",
                  "result":"Free API access is not supported for this chain. Please upgrade your api plan…"}
```

So a free key that "does not work" is usually a free key being asked for a chain its tier excludes.
**Probe chainid=1 first** — a valid answer there proves the key, and the 8453 refusal is then a
pricing decision, not a credential defect. Do not buy a plan before checking whether the receipt
path makes the indexer unnecessary (it usually does).

Legacy endpoints are also gone: `api.<explorer>.org/api` (V1) now answers *"You are using a
deprecated V1 endpoint, switch to Etherscan API V2"* — a message that reads like a key error and is
not.

## Fail-loud rules (a reconciler that reports zero is worse than none)

| condition | required behaviour |
|---|---|
| no payment log file | print `UNKNOWN — not 'zero payments'`, exit non-zero |
| log exists, no hashes yet | say "nothing to reconcile yet" — do not print 0 settlements as a result |
| RPC silent for a hash after retries | report that hash **UNRECONCILED**, exit non-zero; never omit it |
| receipt `status=0` | record `reverted`, `verified:false` |
| no Transfer to our payTo in the receipt | record as **not a settlement** — do not count the tx |
| re-run | dedupe by tx on append; the ledger must not double |

Print the verified row as JSON so the artefact is auditable: `tx`, `block`, `rail`, `path`, `status`,
`verified`, `payer`, `payTo`, `token`, `amount_raw`, `amount`.

## Public RPC quirks

**Send a User-Agent.** Public Base RPCs answer `403 Forbidden` to the default Python `urllib` agent.
The same endpoint answers normally over `curl` or with any UA set — so a bare `urllib.request`
reconciler reports "no RPC" on a healthy endpoint. Always set `headers={"User-Agent": "<name>/<version>"}`.

Keep a preference-ordered endpoint list per rail and retry each twice before declaring a hash
unreconciled; throttling is intermittent and a second endpoint usually answers.

## State the limits in the output

The reconciler sees only hashes it was given, so it **cannot discover unlogged payments** — say so.
And when the same address is both the treasury and the settle-test wallet, a verified row proves a
payment happened but not that a customer made it; a per-service payTo or a memo closes that gap, and
it is a product decision rather than a bug to hide.
