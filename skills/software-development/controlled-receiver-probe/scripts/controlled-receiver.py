#!/usr/bin/env python3
"""controlled-receiver.py — a receiver you control, so you can see EXACTLY what a client sends.

Why this exists: when a client and a server disagree about auth/routing, reading the client's source is
slower and more ambiguous than capturing the real request. This stands up a tiny HTTP server, logs every
request (method, path+query, header NAMES, body) with SECRETS FINGERPRINTED rather than printed, and
answers 200 so the client proceeds to whatever it does next.

Usage:
  python3 controlled-receiver.py [--port 8899] [--once] [--exit-after 20]

  --once        stop after the first request (handy for a single WAKING call)
  --exit-after  seconds to listen before exiting (default 20)

Then point the CLIENT at it THROUGH THE CLIENT'S OWN REGISTRATION PATH (never a hand-typed equivalent),
invoke the client, and read the log this prints on exit.

Never prints a secret value: a Bearer/JWT/API-key header is shown as <N chars, sha256:xxxxxxxx>.
"""
import argparse, hashlib, http.server, socketserver, sys, threading, time

CAPTURED = []
SECRET_HEADERS = ("authorization", "x-api-key", "api-key", "x-auth-token", "cookie")
ONCE = False

def fingerprint(value):
    return f"<{len(value)} chars, sha256:{hashlib.sha256(value.encode()).hexdigest()[:12]}>"

def render(name, value):
    return fingerprint(value) if name.lower() in SECRET_HEADERS else value

class Handler(http.server.BaseHTTPRequestHandler):
    def _record(self, body=b""):
        headers = {k: render(k, v) for k, v in self.headers.items()}
        CAPTURED.append({
            "method": self.command,
            "path": self.path,
            "headers": headers,
            "body": body.decode(errors="ignore")[:2000],
            "ua": self.headers.get("User-Agent"),
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
        if ONCE:
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def do_GET(self):
        self._record()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self._record(self.rfile.read(n) if n else b"")

    do_PUT = do_PATCH = do_DELETE = do_POST

    def log_message(self, *a):  # silence the default stderr chatter
        pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--exit-after", type=float, default=20.0)
    args = ap.parse_args()
    ONCE = args.once

    srv = socketserver.TCPServer(("127.0.0.1", args.port), Handler)
    srv.allow_reuse_address = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"receiver listening on http://127.0.0.1:{args.port} — point the client at it now", flush=True)

    deadline = time.time() + args.exit_after
    while time.time() < deadline and not (ONCE and CAPTURED):
        time.sleep(0.2)
    srv.shutdown()

    print("\n=== captured requests ===")
    if not CAPTURED:
        print("  NONE — the client never reached this receiver. That is itself the finding:")
        print("  the request went somewhere else, so the fault is the DESTINATION, not the credential.")
    for i, rec in enumerate(CAPTURED, 1):
        print(f"\n[{i}] {rec['method']} {rec['path']}")
        for k, v in rec["headers"].items():
            print(f"      {k}: {v}")
        if rec["body"]:
            print(f"      body: {rec['body']}")
    sys.exit(0 if CAPTURED else 3)
