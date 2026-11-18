# Facilitator endpoints — which hostname is real, and how to prove it

**The short version: `api.cdp.coinbase.com` is the production facilitator. Three other hostnames are
circulating in docs and bug reports and none of them resolve.** Integrators lose days to this because a
dead hostname and a rejected payment produce the same symptom from inside a server: *nothing settles.*

## The table — measure it, don't trust docs

| hostname | observed | meaning |
|---|---|---|
| `api.cdp.coinbase.com/platform/v2/x402/{verify,settle}` | **401** unauthenticated | **alive and auth-gated — this is the one** |
| `x402.org/facilitator/platform/v2/x402/{verify,settle}` | **404** | retired path; still quoted in older docs |
| `facilitator.cdp.coinbase.com` | **NXDOMAIN** (no A record) | *recommended as the fix* in several public issues — it does not exist |
| `x402-facilitator.cdp.coinbase.com` | **NXDOMAIN** | appears verbatim in at least one repo's `FACILITATOR_URL` |

Three dead hostnames, one live host, and **one of the dead ones is the remedy quoted inside the issue
about the other dead one.** That is the trap: following the fix moves an integrator from a 404 to a DNS
failure and looks like they mis-typed something.

```bash
for h in api.cdp.coinbase.com facilitator.cdp.coinbase.com x402-facilitator.cdp.coinbase.com; do
  printf '%-38s ' "$h"; python3 -c "import socket,sys;socket.gethostbyname(sys.argv[1]);print('resolves')" "$h" 2>/dev/null || echo 'NO A RECORD'
done
curl -s -o /dev/null -w '%{http_code}\n' https://api.cdp.coinbase.com/platform/v2/x402/supported   # 401 = alive
```

## Reading the response correctly

- **`401` on a facilitator path means the endpoint is ALIVE.** It is credential-gated, not broken. Never
  report 401 as "the facilitator is down" — that misreads a healthy auth wall as an outage, and it is the
  single most common false negative in this whole diagnostic.
- **`404` means the host answered but the path is gone** — a retired or wrong route, and the fix is the URL,
  not the credentials.
- **`000` / `gaierror` means DNS.** Distinguish this from everything else before touching config: no amount
  of correct key material makes an NXDOMAIN host answer.

## The silent-failure mode that hides this

A server whose verify path cannot reach the facilitator can fall back to a **simulation** verifier and then
refuse every payment with an error that never mentions the network — e.g. `payment_proof_invalid: simulation
disabled`. The buyer sees "your proof is invalid"; the truth is "this server has no facilitator".

- **Fail loudly and name the host.** A refusal that does not say *which endpoint was unreachable* will be
debugged from the buyer's side, in the wrong repo, for days.
- **Never "fix" it by enabling a simulation path in production.** That converts a broken door into a door
  that fabricates receipts.
- **Check the container's own environment before reading code** — the same gateway booted with and without
  its env file advertises a different number of rails, which looks like a code bug and is a deployment one.

## JWT / key details that cost time

- **`kid` accepts the bare UUID** from the portal; the `organizations/<uuid>/apiKeys/<uuid>` form is not
  required. Sign with the portal's value before assuming the format is wrong.
- **A key id and a wallet signing key are different credentials.** A wallet private key cannot authenticate
  to the facilitator, and an API key cannot sign a transfer. Verify which one the error is about.

## Turning this into a paid product signal

Reachability is a **conformance check**, not just a debugging step: a service can have a perfect 402 shape
and still be unsellable because its facilitator hostname is dead. Any audit of "can this endpoint take
money?" must include *the facilitator resolves and answers*, and must report the host it tested — otherwise
the report cannot distinguish a wrong endpoint from a wrong key.
