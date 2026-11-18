#!/usr/bin/env python3
"""Make ONE real x402 payment against a URL and report what happened.

Purpose: prove the paid path end-to-end. A 402 alone proves nothing — the only
question that matters is whether a client can construct a payment that the
facilitator verifies and settles.

The key is read from a file and never printed.

Usage:
    python3 x402-paid-call.py <url> [keyfile] [network]

Requires: pip install "x402[evm]" requests
"""
import sys

import requests
from eth_account import Account
from x402 import x402ClientConfig, SchemeRegistration
from x402.http.clients import wrapRequestsWithPaymentFromConfig
from x402.mechanisms.evm.exact import ExactEvmScheme

url = sys.argv[1]
keyfile = sys.argv[2] if len(sys.argv) > 2 else "/opt/data/.blockrun/.session"
network = sys.argv[3] if len(sys.argv) > 3 else "eip155:8453"

raw = open(keyfile).read().strip()
if not raw.startswith("0x"):
    raw = "0x" + raw
acct = Account.from_key(raw)
print("  payer  :", acct.address)

config = x402ClientConfig(
    schemes=[SchemeRegistration(network=network, client=ExactEvmScheme(signer=acct))]
)
session = wrapRequestsWithPaymentFromConfig(requests.Session(), config)
r = session.get(url, timeout=180)

print("  status :", r.status_code)
print("  ctype  :", r.headers.get("content-type"))
pr = r.headers.get("payment-response") or r.headers.get("x-payment-response")
print("  PAYMENT-RESPONSE:", (pr[:120] + "…") if pr else "(none)")
print("  body   :", r.text[:400].replace("\n", " "))

if r.status_code != 200:
    print("\n  ⚠️  A non-200 here means the challenge is unpayable or the settlement failed.")
    print("      Bisect the requirements object — see references/v2-challenge-correctness.md")
    sys.exit(2)
