# The silent verifier fallback — a door that refuses every payer and says nothing useful

## The failure

An x402 seller's payment verifier usually has two modes: a real facilitator call, and a **simulation** mode used in
development. If the verifier is configured to pick a mode automatically and the facilitator credentials are missing,
it can land in simulation **in production** — where it examines the proof, decides the settlement is not real, and
refuses *every* payer.

The dangerous properties, all observed together:

- **The refusal is well-formed.** The client gets a correct `402 payment_proof_invalid` with a reason string. Nothing
  looks broken from the outside; it looks like the buyer's proof is wrong. Repeated across every rail, it reads as
  "the market is not buying".
- **The reason never names the missing component.** It describes the proof, not the misconfiguration — so the seller
  debugs their client for days.
- **The seller's own reputation is intact and useless.** Discovery surfaces answer 200, the challenge is valid,
  balances are readable. Every public metric is green while revenue is structurally zero.

## Rules

1. **Never make the door look open with a placeholder.** Setting a shared secret, a dummy key, or any "just to make
   it run" value converts a visible outage into fabricated revenue. A closed door that says why is always better than
   a door that reports sales it did not make.
2. **Fail loudly, naming the cause.** The refusal body for a misconfigured verifier should name the host it could not
   reach and the exact env var that is absent. A generic `invalid proof` is a bug in its own right.
3. **Refuse to start, or refuse to advertise.** If verification cannot run, either exit at boot or withhold the paid
   routes from the challenge — do not serve a payable challenge you cannot settle.
4. **Prove the door from outside, with a real client, on a real route.** Config reading is not proof; a 200 from
   `/health` is not proof. The only proof is a client that signs, a settlement that appears on chain, and the data
   arriving afterwards. Then check the payer's balance moved by the quoted amount and no more.
5. **Record the result even when it is zero.** "0 paid calls, 0.000000 USDC received" is a measurement. It is the
   number that tells the next session the door was tested rather than assumed.

## Diagnosis order (each step is cheap; do them in this order)

```
1. Decode a live 402 and read the verifier's mode out of the server config/env.
2. Ask the running process what credentials it actually holds — not what the .env file says.
   A value present in a file is not a value present in the process.
3. Send a deliberately malformed proof and read the REASON string, not just the status code.
   "simulation disabled" / "not configured" is a configuration finding; "bad signature" is a client finding.
4. Only then touch credentials — and when a credential is genuinely lost, record the loss at the moment it is
   discovered, with the date, so nobody searches for it twice.
```

## The generalisation

Any system with an auto-selected "safe" mode will eventually select it in production. The mode must be **explicit,
not inferred**, and its refusal must be **diagnostic, not generic** — otherwise the failure is indistinguishable from
the business simply having no customers, which is the one conclusion nobody re-tests.
