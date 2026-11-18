# Paywall failure modes the logs cannot show

Two opposites, one symptom: **zero revenue with plenty of traffic.**

| mode | what the buyer experiences | what the logs say |
|---|---|---|
| **A · the door cannot accept** | valid challenge, valid proof, `402 payment_proof_invalid` | lots of 402s, zero 200s on paid routes |
| **B · the door accepts for nothing** | pays, settles, then receives a `404` from a backend | a settled payment and a served error — looks like a sale |

Both are invisible from traffic counts alone. Neither is a demand problem, and reading one as the other is how a
broken paywall gets reported as "no market".

---

## A · Proving the door can take money at all

**Do not infer this from logs.** Send a real paid request with a real x402 client from a funded wallet — one that
is not the receiving wallet — and read the response body verbatim. That single call separates "nobody wants it"
from "nobody can buy it".

```bash
python3 scripts/x402-paid-call.py "https://<host>/v1/<paid-route>" /path/to/.session
# 200 + data        -> the path works; zero sales is then a demand question
# 402 + a reason    -> READ THE REASON: a refusal naming a missing variable is a config defect, not a payment failure
```

Run it against **several** paid routes, not one — a per-route bug and a fleet-wide one look identical otherwise.

### The specific defect: `auto` verify mode falling back to a verifier that fails closed

A common shape: `PAYMENT_VERIFY_MODE` defaults to `auto` → try the real facilitator (CDP/Coinbase) **if a key
exists**, else fall back to a *simulation* verifier → the simulation verifier refuses when its HMAC secret is
unset (a correct guard, added so a deployment cannot silently accept forged proofs). Net effect: one missing
environment variable turns **"not configured for production" into "we take no money"**, silently, for every
buyer, without ever raising an error anywhere else.

Diagnosis order — measure, then read the flag:

```bash
# 1 · the behaviour (client call above) — this is the evidence
# 2 · does the container even have the credentials the code believes in?
docker exec <gateway-container> env | grep -c '^CDP_'      # 0 = no verifier can ever succeed
grep -rl 'CDP_API_KEY_ID' /root /etc 2>/dev/null           # is a key on the host at all?
```

### ⚠️ The wrong fix, named so nobody takes it

**Never set the simulation HMAC secret to "make payments work".** It validates *simulated* proofs — the paywall
starts returning 200 for payments that never moved a cent, and every revenue report after that is fiction. The
honest fixes, in order:

1. Put the real facilitator credentials where the verifier runs (env of the process, or a mounted env file).
2. If the credentials do not exist yet, force the strict mode (`PAYMENT_VERIFY_MODE=cdp`) so every buyer gets a
   **named** failure instead of a mystery — loud beats silent, and it stops the estate pretending to be open.
3. Never make the simulation path the production path.

**Verify no money moved** when the attempt was refused — read the payer's balance before and after and say the
number. A refusal that moved funds is a different, much worse defect.

---

## B · Charge-before-validate: a payable challenge for a resource that cannot be served

A gateway that **settles first and proxies second** will happily issue a full payment challenge for a path no
backend can answer. The buyer pays and receives the backend's `404`. Value moves; delivery does not.

Two levels, and the shallow fix only handles one:

1. **Unknown service** (`/v1/<not-a-service>`) — reject with `404` before any challenge. Most gateways get this.
2. **Known service, unservable sub-path** (`/v1/<service>/nonsense`, a template left unsubstituted, a malformed
   parameter) — **this is the one that survives.** A validator that only checks services returns "fine" because
   the service is real, and the leaf is never inspected.

### Fix — validate the leaf against what the service declares

```python
def _static_leaf_prefix(template: str) -> list:
    """brace-free path segments a service declares after /v1/<service>/
    '/v1/defender/classify/{chainId}/{token}' -> ['classify'];  '/v1/nft/search' -> ['search'] """
    parts = [p for p in (template or "").split("?")[0].split("/") if p]
    if parts and parts[0] == "v1": parts = parts[1:]
    if parts: parts = parts[1:]
    out = []
    for seg in parts:
        if seg.startswith("{") and seg.endswith("}"): break
        out.append(seg)
    return out

# inside the pre-challenge validator, for every non-alias service:
prefix = _static_leaf_prefix(cfg.get("endpoint") or "")
if prefix and segs[:len(prefix)] != prefix:
    return f"unexpected_subpath:{'/'.join(segs[:len(prefix)])}"
if prefix and not declared_params and len(segs) > len(prefix):
    return f"extra_subpath:{'/'.join(segs[len(prefix):])}"      # right leaf, junk below it
```

- **Skip routing aliases** (`foo_native`, OKX/product-vhost aliases) — their served path deliberately differs from
  the manifest endpoint they borrow a price from, and a leaf check would reject a valid route.
- **Return `404` with a reason**, never a 402: `{"error": "unservable_subpath", "reason": "..."}`. A crawler that
  enumerates paths reads a challenged 402 as "payable resource" and a 404 as "no resource" — which is the truth.

### Test it as a matrix, in both directions

```
MUST NOT REJECT  → every declared endpoint, concretised with a real sample value  (count them all)
MUST REJECT      → nonsense leaf, right-leaf-plus-junk, malformed param, unknown service
```

Report **false_rejections** and **missed** as two numbers. A one-directional test passes a validator that rejects
nothing, and the first version of this fix let `/v1/<service>/<leaf>/junk` through because the prefix matched and
there were no declared params — the matrix caught it, the diff did not.

**Deploy order for a live gateway:** edit → execute the patched functions against the **real manifest** (AST-extract
them if the full app cannot be imported in the agent's environment) → restart → re-run the matrix over HTTP from
**outside** the host → keep the one-line rollback (`cp server.py.bak-<tag> server.py && docker restart <c>`).

---

## The reporting consequence

A zero under a heading that implies a sale is a claim, not a measurement. When writing this up, distinguish three
things explicitly, because they lead to different work:

- **0 settled payments** — nobody bought.
- **N refused attempts** — buyers tried and *we* said no (config defect, mode A).
- **N settled-but-undelivered** — buyers paid and got nothing (mode B).

Only the first is a market question. The other two are bugs, and a report that blends them costs a quarter of
misreading.
