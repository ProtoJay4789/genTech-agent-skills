# Verify a contract before you call it a stub

**Cost of getting this wrong: six days.** A real pool address was written off as a "196-byte stub" and every
pool-level number derived from it was treated as suspect until a screenshot forced a re-check.

## The error that caused it

`eth_getCode` returns HEX. A 97-byte contract renders as `0x` + **194 hex characters** = **196 characters**.
Reporting that as "196 bytes" turned a normal minimal proxy into an apparent placeholder.

**Always convert:** `bytes = (len(code) - 2) // 2`

**A small contract is not a broken contract.** 97-byte bodies starting `363d3d373d3d3d...` are EIP-1167-style
proxies. Follow the delegate: the implementation address is embedded in the bytecode and carries the real
logic (24,535 bytes in the case that mattered).

## Two instruments agreeing is not proof

The "stub" finding was confirmed by `eth_getLogs` returning 0 over a 20,000-block window. **Both were wrong.**
Public RPCs silently cap log ranges (~50 blocks) and answer an oversized span with an empty result and **no
error**. Zero logs therefore proved nothing about the pool.

**Rule: before concluding "this contract does nothing", prove the RPC can see something on the SAME chain in
the SAME window** — a busy token emitting logs in 50 blocks is the control.

## LFJ / Trader Joe Liquidity Book, verified 2026-10-30

WAVAX/USDC V2.2 — the real pool:

| | |
|---|---|
| proxy | `0x864d4e5ee7318e97483db7eb0912e09f161516ea` |
| implementation | `0x7a5b4e301fc2b148cefe57257a236eb845082797` (24,535 bytes, verified on the explorer) |
| `getActiveId()` | `0xdbe65edc` |
| `getReserves()` | `0x0902f1ac` |
| `getBin(uint24)` | `0x0abe9688` |
| `getBinStep()` | returns 10 (0.10% per bin) |

**Price from the active bin:** `(1 + binStep/10000)^(activeId − 2^23) × 10^(decX − decY)`
Verified to **−0.01%** against the aggregator. The `2^23` offset is mandatory; omitting it silently produces
plausible-looking wrong numbers.

**Get the ABI, never guess selectors.** The implementation is verified on Snowtrace:
`api.snowtrace.io/api?module=contract&action=getabi&address=<impl>`. Four guessed selectors cost an afternoon
and produced nothing. Confirm a derived selector by checking it reproduces one you already know works.

## Rate limits that lie

| endpoint | real behaviour |
|---|---|
| `api.avax.network` | 429s under sustained use; fall back to `avalanche-c-chain-rpc.publicnode.com` |
| YouTube RSS | returns **HTTP 404 / 500** on VALID channel IDs when rate-limited. **Retrying deepens the block**; ~5 min idle clears it. Treat 404/500 as THROTTLED, never as "channel deleted" |
| Kalshi | quotes live in `yes_bid_dollars` / `*_fp`; legacy `yes_bid`/`volume` fields still exist but return null. `status=active` → HTTP 400; use `status=open` |

**A rate-limit that returns 404 is indistinguishable from a deleted resource unless you test the same URL
later.** That is the general lesson: when an error code and a known-good resource disagree, suspect the
instrument before the object.
