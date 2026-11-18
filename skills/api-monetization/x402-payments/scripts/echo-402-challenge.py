#!/usr/bin/env python3
"""Answer 402 with a requirement you control, and capture the client's signature.

This is the diagnostic that makes x402 debugging deterministic: it isolates
"can a client sign for this requirement?" from "does my server format it right?".

Run it, then point scripts/x402-paid-call.py at http://127.0.0.1:<port>/...
The captured PAYMENT-SIGNATURE lands in /tmp/captured-sig.txt (base64 JSON).
Decode it and POST {payload, accepted} to the facilitator's /verify.

Usage:
    python3 echo-402-challenge.py [port] [name] [version]
"""
import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8977
# Advertise the token's EIP-712 DOMAIN name, not its symbol. USDC is "USD Coin".
TOKEN_NAME = sys.argv[2] if len(sys.argv) > 2 else "USD Coin"
TOKEN_VERSION = sys.argv[3] if len(sys.argv) > 3 else "2"

REQ = {
    "scheme": "exact",
    "network": "eip155:8453",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x0000000000000000000000000000000000000001",  # replace before settling
    "amount": "1000",
    "maxAmountRequired": "1000",
    "resource": f"http://127.0.0.1:{PORT}/probe",
    "description": "challenge-capture probe",
    "mimeType": "application/json",
    "maxTimeoutSeconds": 60,
    "extra": {"name": TOKEN_NAME, "version": TOKEN_VERSION},
}
CHALLENGE = {
    "x402Version": 2,
    "resource": {"url": REQ["resource"], "description": REQ["description"],
                 "mimeType": "application/json"},
    "accepts": [REQ],
}

OUT = "/tmp/captured-sig.txt"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        sig = self.headers.get("PAYMENT-SIGNATURE") or self.headers.get("payment-signature")
        if not sig:
            body = json.dumps(CHALLENGE).encode()
            self.send_response(402)
            self.send_header("content-type", "application/json")
            self.send_header("PAYMENT-REQUIRED", base64.b64encode(body).decode())
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        with open(OUT, "w") as f:
            f.write(sig)
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


print(f"  probe on :{PORT}  name={TOKEN_NAME!r}  version={TOKEN_VERSION!r}", flush=True)
print(f"  captured signature → {OUT}", flush=True)
HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
