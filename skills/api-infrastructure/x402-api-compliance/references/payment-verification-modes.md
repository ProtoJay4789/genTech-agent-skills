# Payment verification modes — why every buyer gets refused, and the fix that is a trap

## The mode ladder

A gateway that verifies and settles payment proofs usually selects behaviour from an env var
(`PAYMENT_VERIFY_MODE`) that defaults to `auto`:

| mode | behaviour | when it is right |
|---|---|---|
| `cdp` | verify + settle through the facilitator (Coinbase Developer Platform) | production, real money |
| `simulation` | HMAC-validate an `X-PAYMENT` header against a shared `GATEWAY_SECRET` | local dev, tests, never revenue |
| `auto` | try CDP **if a key exists**, else silently fall back to simulation | convenient, and the source of the failure below |

**The failure shape:** `auto` + no facilitator key ⇒ simulation ⇒ no `GATEWAY_SECRET` ⇒ **fail closed**.
Every caller holding a perfectly valid proof gets:

```
402 {"error": "payment_proof_invalid",
     "reason": "simulation disabled: GATEWAY_SECRET not configured"}
```

Failing closed is correct engineering — the guard exists so a deployment cannot silently accept forged
proofs. What is wrong is the fallback: **"not configured for production" becomes "we take no money",
silently, on every request.**

## ⚠️ The trap: do NOT set `GATEWAY_SECRET` to make it pass

Setting the secret turns the **simulation** verifier green. A simulated proof is not a settlement — nothing
moved on-chain. The estate would then start recording payments that never happened, and every revenue
report after that is fiction. **When an error message names an env var, ask which branch accepts it before
you provide it.**

The honest fixes, in order:

1. **Production verifier credentials inside the process that serves** — `CDP_API_KEY_ID`,
   `CDP_API_KEY_SECRET`, `CDP_API_KEY`. Restart, re-run the paid call, and quote the settlement hash.
2. **If the keys are not to hand:** force `PAYMENT_VERIFY_MODE=cdp` so the failure is *named* instead of
   mysterious, and stop any manifest or dashboard implying the service is purchasable.
3. **Never** leave `auto` in place while telling buyers the door is open.

## Diagnose it in this order

```bash
# 1. Is there a facilitator key inside the thing that actually serves?
docker exec <gateway-container> env | grep -c '^CDP_'      # 0 = the fallback is in play

# 2. Is a key anywhere else on the host? (a found file = a mount, not a new account)
grep -rl 'CDP_API_KEY_ID' /root /etc 2>/dev/null | head

# 3. Which mode does the code default to, and what proves the refusal?
grep -n 'PAYMENT_VERIFY_MODE\|GATEWAY_SECRET' server.py | head
```

Read the branch that produces the message before changing anything: the refusal string usually names the
exact variable, and the code around it tells you whether the fix is a credential or a code change.

## The paid-call test that reads as evidence

Run a **real x402 client** on the `exact` scheme, with a funded wallet that is **not** the `payTo` address,
against **three** paid routes. One bad path is a mistake; three identical refusals are a door.

- Print the **payer address**, the **status**, and the **body** — the body is where the reason lives.
- Settlement may be gasless (EIP-3009 `transferWithAuthorization` is submitted by the facilitator), so a
  zero-ETH balance is not automatically a blocker. Hold USDC first, then prove gas is needed before
  concluding it is.
- **Re-read the balance afterwards.** "Nothing moved" is a finding: it proves the attempt was refused
  before settlement rather than partially executed.
- Compare the payer to `payTo` in the challenge. Paying yourself proves the *client* works, not that a
  stranger can pay — label it `self` and never count it as demand.

## What a refusal invalidates downstream

**A zero-revenue metric measured through a refusing verifier is not demand data.** Every "candidate who hit
the paywall and left" is, in that state, a caller *we* turned away.

- `0` paid calls + a refusing verifier ⇒ **could not be bought** — never report it as "nobody wanted it".
- The demand question only becomes answerable once the door opens: re-read the caller roster afterwards.
  If candidates start settling, you had demand and a broken door; if they still leave, demand is the
  problem. **Before that the two are indistinguishable from inside your own logs.**

## Storage is not delivery — check the MOUNTS before calling a key missing

A credential can be correctly saved and still be **invisible to the process that serves**. Before concluding a
key was lost, rotated, or never provided, prove the path exists:

```bash
docker inspect <gateway-container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

If the file that holds the secret is not among the mounts, **there was never a route from store to process** —
that is a delivery gap, not a lost credential, and it explains a refusal that survives every re-paste. Fix the
delivery (mount, env-file, or a file under a mount that already exists), then re-test.

**Prefer a file inside an existing mount over recreating the container.** A hand-started, host-networked
container has no compose file and no `--env-file`, so adding an env var means recreating it — and everything
that depends on that process goes down with it. A dotfile read at start-up (`/app/.cdp.env`, or a path on an
already-mounted data volume) turns the change into *write file + restart*, and the revert into *delete file +
restart*.

## The loader must be called where the BRANCH is decided

A loader that lives inside the verify function is useless if the dispatch still reads the raw environment:

```python
# WRONG — the file-based credential is never consulted, so every request takes simulation
if os.getenv("CDP_API_KEY"):
    valid, reason = verify_proof_via_cdp(...)   # <- loads the file, never called
else:
    valid, reason = verify_proof_simulation(...)  # <- refuses with a GATEWAY_SECRET message

# RIGHT — one accessor, used at the decision point and inside the verifier
if load_credentials()[0]:
    ...
```

**Symptom to recognise:** the refusal still names the *simulation* secret after a correct credential file was
installed. That is not a bad key — it is a missed branch, and it will look like a credential problem forever if
you keep replacing the key.

**Shape-check what the loader returns.** An Ed25519 CDP secret is base64 of exactly **64 bytes**; a key ID is
`organizations/<uuid>/apiKeys/<uuid>` (a bare UUID is also accepted by the facilitator — measured, so do not
"repair" it into the long form). Anything else is a placeholder or the wrong paste: **skip that file and try the
next path** rather than handing it to the JWT signer, where it surfaces as an ASN.1/PEM framing error that reads
like a key problem and is not one.

## Prove the credential BEFORE touching the gateway

Do not deploy a code change to test a key. Mint the JWT yourself and call the facilitator's `/supported`:

```bash
# EdDSA JWT, kid = the key id, claims: sub/iss/aud/nbf/exp + uris: ["<METHOD> <host><path>"]
# then: GET https://api.cdp.coinbase.com/platform/v2/x402/supported
```

`200` = the credential is real and the JWT shape is right, so any remaining refusal is ours. `401` = the
credential itself, and no amount of code work will fix it. This single call separates "our gateway is broken"
from "our key is broken" in under a minute.

## Related

- `references/v2-payment-challenge.md` — the challenge field defects that make a proof unpayable.
- `references/advertised-surface-agreement.md` — do not advertise purchasability while this path refuses.
