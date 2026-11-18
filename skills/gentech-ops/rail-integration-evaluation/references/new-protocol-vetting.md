# Vetting a new protocol before building on it

Use when a protocol, SDK or program has just launched and the question is *"can we build on this, and is it worth
it?"*. Every probe below is read-only, needs no key and no capital, and answers a question the announcement cannot.

The order matters: **deployed → how busy → how much of the object graph exists → has anyone built on it → is the
API stable enough to depend on.**

## 1 · Prove deployed, and distinguish deployed from announced

Solana program (upgradeable loader):

```python
rpc("getAccountInfo", [PROGRAM_ID, {"encoding": "base64"}])["result"]["value"]
# -> executable: True, owner: BPFLoaderUpgradeab1e11111..., data: 36 bytes
```

36 bytes is the **program account**, not the code: `u32 tag (4) + 32-byte programdata address`.
Decode bytes 4:36, base58-encode it, then read that account:

```python
pda = rpc("getAccountInfo", [programdata_addr, {"encoding": "base64"}])["result"]["value"]
raw = base64.b64decode(pda["data"][0])
len(raw)                     # deployed program bytes
int.from_bytes(raw[4:12], "little")   # last upgrade SLOT
rpc("getBlockTime", [slot])["result"] # -> wall-clock of the upgrade
```

**Why the upgrade slot decides the story:** a program upgraded *days before* its SDK reached npm is a team shipping
the program first and the tooling after. An SDK published before the program was ever deployed is a launch post
with nothing behind it. State the two dates side by side.

EVM equivalent: `eth_getCode` returns the runtime bytecode; `0x` means no contract at all. A docs table is a
claim, bytecode is proof.

## 2 · Activity rate — measure the WINDOW before dividing

```python
sigs = rpc("getSignaturesForAddress", [PROGRAM_ID, {"limit": 1000}])["result"]
ts = [s["blockTime"] for s in sigs if s.get("blockTime")]
span_h = (max(ts) - min(ts)) / 3600
```

- `span_h > 0` → `rate = len(sigs) / span_h`. Report it with the span.
- `span_h == 0` → **all 1000 signatures landed inside one second bucket.** That is not `514,286 tx/hour`, it is
  "busier than this instrument can resolve". Say so; do not publish the division.

**This is the single easiest way to produce a confident wrong adoption number**, and it happens on exactly the
comparison you most want to draw (new program vs incumbent).

## 3 · Adoption SHAPE — bucket by day

```python
from collections import Counter
import datetime
Counter(datetime.datetime.fromtimestamp(s["blockTime"], datetime.UTC).strftime("%m-%d") for s in sigs)
```

A deploy spike, a quiet test trickle, then a listing burst are three phases; the daily histogram tells you which
one you are looking at, and whether the newest day is still climbing or already decaying.

## 4 · Object census without an IDL — count by account size

```python
all_acc = rpc("getProgramAccounts", [PROGRAM_ID, {"encoding": "base64",
                                                 "dataSlice": {"offset": 0, "length": 0}}])["result"]
Counter(a["account"]["space"] for a in all_acc)
```

`dataSlice` of length 0 keeps the response small — you get every account's **size** without any of its data.

- The dominant size is usually the per-user slot (e.g. 1,848 × 128 bytes).
- A small distinct size is usually the main object (e.g. 9 × 272 bytes = pools).
- **The histogram is a market-size reading.** Nine pools is a beta; four figures is a market. Report the counts, not
the impression.

## 5 · Has anyone built on it — search the ID, not the name

```
GET /search/repositories?q=<PROGRAM_ID>
```

Name searches return homonyms and unrelated projects with the same word. The **program/contract ID is unique**, so
a zero result there means literally no indexed repository references it.

**Report the zero as two facts, not one:** nobody has integrated yet (so there is no audience to sell to today),
and the integration window is still open (so a partner is grateful for the first credible one). Those point in
opposite directions depending on whether the product is consumer-facing or partner-facing — say which reading you
recommend and why.

## 6 · Is the API stable enough to depend on

Cheap signals, all from the registry:

```
GET https://registry.npmjs.org/<pkg>     # release count + per-version publish timestamps
get repo commits                          # who is committing, and what they are fixing
```

- **N releases in the first 72 hours** = the API is still moving. A wrapper written today is disposable.
- **Commits are the vendor fixing its own bugs** (`fix/<bounds>`, `fix/<parity>`) = healthy, early.
- **The durable asset is the account/IDL knowledge, not the client wrapper.** Build the reader against the
  **exported IDL**, treat every offset as discovery rather than a constant, and record the SDK version the code was
  written against so a drift is loud instead of silently wrong.

## 7 · Read the commercial surface, not just the technical one

Scan the launch docs for the words that decide revenue: `referral`, `integrator fee`, `revenue share`, `partner`.

- A **referral / integrator bps on routed volume** is the only lane that earns without holding a position or
  signing anything — it fits a no-write-path treasury rule exactly.
- It needs an **agreement**, which takes longer than the code. Request it while the ecosystem is empty.
- A partner-config product (launchpad-style) has two dependencies you do not control; price that as a
  conversation, not a build.

## Reporting shape

```
deployed:      <bytes>, loader, last upgrade <date>
sdk:           <version>, first publish <date>, <N> releases in 72h, <stars> stars
integrations:  <N> repos reference the program ID
objects:       <N> accounts, <N> pool-shaped
activity:      <N> sigs over <span>h = <rate>/h  (or "window too short to resolve")
verdict:       <build | watch | not a rail> + the ONE number that decides it
zero-capital lane: <referral share, if any> — needs <who> to agree
```

**Never let the announcement supply the adoption number.** The announcement supplies capability; only the chain
supplies demand.
