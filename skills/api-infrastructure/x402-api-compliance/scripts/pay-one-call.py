#!/usr/bin/env python3
"""Pay ONE x402 call and return the settlement receipt — the end-to-end proof a rail actually works.

WHY: a 402 challenge proves the door exists, not that money can pass through it. The only proof that a rail
is live is a signed payment that SETTLES and whose transaction hash the chain agrees with.

WHAT IT DOES
  1. GET the resource, read the 402 challenge.
  2. Enforce a spend policy LOCALLY before anything signs: this rail only, and a hard per-call ceiling.
  3. Sign, send, read `PAYMENT-RESPONSE`, base64-decode it, print `settled` + tx hash.

USAGE
  pay-one-call.py https://api.example/paid/route [--dry-run]

DEPENDENCIES (a throwaway venv is fine — do NOT install into the service container)
  python3 -m venv .payenv && .payenv/bin/pip install 'x402[evm]' httpx

PITFALLS BAKED IN (each one cost a debugging round)
  * The SDK returns a typed object, not a dict: `resp.get(...)` returns None silently and reports
    `settled: false` on a REAL settlement. Normalise with `dict(vars(obj))` before reading fields.
  * The receipt header arrives LOWERCASE (`payment-response`). A case-sensitive key lookup misses it.
  * A 200 with no receipt is not a sale — require success OR a transaction hash, and never accept an
    unconfirmed settlement as paid.
  * Send the SIGNED header dict the SDK returns (`encode_payment_signature_header`), not a string.
"""
from __future__ import annotations

import base64
import json
import os
import sys

import httpx
from eth_account import Account
from x402 import max_amount, prefer_network, x402ClientSync
from x402.http import decode_payment_response_header, x402HTTPClientSync
from x402.mechanisms.evm.exact import ExactEvmClientScheme  # exact-EVM scheme lives in .exact, not the package root
from x402.mechanisms.evm.signers import EthAccountSigner

# ── POLICY: set these for your estate; refuse rather than negotiate ───────────────────────────────────
RAIL = os.environ.get("PAY_RAIL", "eip155:8453")            # CAIP-2 network we are willing to pay on
MAX_ATOMIC = int(os.environ.get("PAY_MAX_ATOMIC", "20000"))  # hard per-call ceiling, token base units
SECRET = os.environ.get("PAY_WALLET_SECRET", "")             # path to a JSON file holding "private_key"


def _key() -> str:
    if not SECRET or not os.path.exists(SECRET):
        sys.exit(f"No wallet secret at {SECRET!r} — set PAY_WALLET_SECRET to a 600 file with a JSON private_key.")
    return json.load(open(SECRET))["private_key"].strip()


def main(url: str, dry_run: bool) -> int:
    acct = Account.from_key(_key())
    client = x402ClientSync()
    client.register(RAIL, ExactEvmClientScheme(EthAccountSigner(acct)))
    client.register_policy(prefer_network(RAIL))
    client.register_policy(max_amount(MAX_ATOMIC))
    http = x402HTTPClientSync(client)

    with httpx.Client(timeout=60) as hc:
        first = hc.get(url)
        if first.status_code != 402:
            print(f"{first.status_code} (not a paywall) {url}", file=sys.stderr)
            return 4
        challenge = http.get_payment_required_response(lambda n: first.headers.get(n), first.text)
        chosen = challenge.accepts[0]
        rail, amount = getattr(chosen, "network", None), int(getattr(chosen, "amount", 0))
        if rail != RAIL:
            print(f"policy refused: challenge led with {rail}, we pay {RAIL} only", file=sys.stderr)
            return 2
        if amount > MAX_ATOMIC:
            print(f"policy refused: {amount} atomic > cap {MAX_ATOMIC}", file=sys.stderr)
            return 2

        payload = client.create_payment_payload(challenge)
        if dry_run:
            print(json.dumps({"url": url, "dry_run": True, "rail": rail,
                              "amount_atomic": amount, "payer": acct.address}))
            return 0

        r2 = hc.get(url, headers=http.encode_payment_signature_header(payload))
        hdr = {k.lower(): v for k, v in r2.headers.items()}
        receipt = hdr.get("payment-response") or hdr.get("x-payment-response") or ""
        settle = {}
        if receipt:
            try:
                obj = decode_payment_response_header(receipt)
            except Exception:
                obj = None
            if obj is None:
                try:
                    obj = json.loads(base64.b64decode(receipt + "=" * (-len(receipt) % 4)))
                except Exception:
                    obj = {}
            # typed object -> dict, because .get() on an object returns None without raising
            settle = obj if isinstance(obj, dict) else dict(vars(obj))

        tx = settle.get("transaction") or settle.get("tx") or settle.get("txHash") or ""
        out = {"url": url, "status": r2.status_code, "settled": bool(settle.get("success")),
               "tx": tx or None, "network": settle.get("network"),
               "payer": acct.address, "amount_atomic": amount}
        print(json.dumps(out))
        return 0 if (out["settled"] or tx) else 3


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(args[0], "--dry-run" in sys.argv))
