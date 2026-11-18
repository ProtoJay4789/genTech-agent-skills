#!/usr/bin/env python3
"""Pay ONE x402 call against a gateway, on one rail, from a payer key held in a file.

The point is not the payment — it is the PROOF: a 200 whose `PAYMENT-RESPONSE` carries a transaction hash you can
check on chain. A 402 challenge proves the gateway quotes a price; only an accepted proof proves the door opens.

Setup (once, in a scratch venv — no root needed):

    python3 -m venv .payenv && .payenv/bin/pip install 'x402[evm]' httpx

Usage:

    .payenv/bin/python x402-paid-call.py <url> --key-file <.key> [--dry-run] [--cap 20000] [--rail eip155:8453]

Rules this script enforces so the caller does not have to remember them:
  * the per-call ceiling is a CLIENT POLICY, checked before signing — not a comment;
  * `--dry-run` prints {rail, amount, payer} and sends NOTHING (a price you did not expect is noticed here);
  * the key is read from a file inside the process and never printed or put on a command line;
  * the receipt is normalised from the SDK's OBJECT to a dict before any field is read (the bug that reports
    `settled: false` on a real settlement: `.get()` on a dataclass returns None without raising).

Exit: 0 paid (or dry-run ok) · 2 refused by policy/usage · 3 payment failed · 4 endpoint not payable.
"""
from __future__ import annotations

import base64
import json
import sys

import httpx
from eth_account import Account
from x402 import max_amount, prefer_network, x402ClientSync
from x402.http import x402HTTPClientSync
from x402.mechanisms.evm.exact import ExactEvmClientScheme
from x402.mechanisms.evm.signers import EthAccountSigner


def arg(name: str, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def main() -> int:
    url = next((a for a in sys.argv[1:] if a.startswith("http")), None)
    key_file = arg("--key-file")
    if not url or not key_file:
        print(__doc__, file=sys.stderr)
        return 2
    dry = "--dry-run" in sys.argv
    cap = int(arg("--cap", "20000"))                 # atomic units (USDC = 6 decimals)
    rail = arg("--rail", "eip155:8453")

    # Accept either a raw hex key file or a JSON object holding it.
    raw = open(key_file).read().strip()
    if raw.startswith("{"):
        raw = json.loads(raw).get("private_key", "")
    acct = Account.from_key(raw)

    client = x402ClientSync()
    client.register(rail, ExactEvmClientScheme(EthAccountSigner(acct)))
    client.register_policy(prefer_network(rail))
    client.register_policy(max_amount(cap))            # enforced, not advisory
    http = x402HTTPClientSync(client)

    with httpx.Client(timeout=60) as hc:
        first = hc.get(url)
        if first.status_code != 402:
            print(f"{first.status_code} (not a paywall) {url}", file=sys.stderr)
            return 4
        challenge = http.get_payment_required_response(lambda n: first.headers.get(n), first.text)
        chosen = challenge.accepts[0]
        got_rail = getattr(chosen, "network", None)
        amount = int(getattr(chosen, "amount", 0))
        if got_rail != rail:
            print(f"policy refused: challenge led with {got_rail}, we pay {rail} only", file=sys.stderr)
            return 2
        if amount > cap:
            print(f"policy refused: {amount} atomic > cap {cap}", file=sys.stderr)
            return 2

        payload = client.create_payment_payload(challenge)
        if dry:
            print(json.dumps({"url": url, "dry_run": True, "rail": got_rail,
                              "amount_atomic": amount, "usd": amount / 1e6,
                              "payer": acct.address}))
            return 0

        r2 = hc.get(url, headers=http.encode_payment_signature_header(payload))
        hdr = {k.lower(): v for k, v in r2.headers.items()}      # the wire sends `payment-response`
        receipt = hdr.get("payment-response") or hdr.get("x-payment-response") or ""
        settle: dict = {}
        if receipt:
            try:
                from x402.http import decode_payment_response_header
                _s = decode_payment_response_header(receipt)
            except Exception:
                _s = None
            if _s is None:
                try:
                    _s = json.loads(base64.b64decode(receipt + "=" * (-len(receipt) % 4)))
                except Exception:
                    _s = {}
            # OBJECT -> dict. Skipping this is how a real settlement is reported as settled:false.
            settle = _s if isinstance(_s, dict) else dict(vars(_s))

        tx = ""
        if isinstance(settle, dict):
            tx = settle.get("transaction") or settle.get("tx_hash") or settle.get("txHash") or ""
        out = {"url": url, "status": r2.status_code,
               "settled": bool(isinstance(settle, dict) and settle.get("success")),
               "tx": tx or None,
               "network": (settle or {}).get("network") if isinstance(settle, dict) else None,
               "payer": acct.address, "amount_usd": amount / 1e6,
               "receipt_present": bool(receipt)}
        print(json.dumps(out))
        # Print the raw header length on a miss so "no receipt" and "unreadable receipt" stay distinguishable.
        if not receipt:
            print(f"no PAYMENT-RESPONSE header on a {r2.status_code} response", file=sys.stderr)
        return 0 if (out["settled"] or tx) else 3


if __name__ == "__main__":
    sys.exit(main())
