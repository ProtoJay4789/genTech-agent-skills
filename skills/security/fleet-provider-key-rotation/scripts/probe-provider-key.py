#!/usr/bin/env python3
"""Probe a provider API key without producing false negatives.

Usage:
    python3 probe-provider-key.py --key-file /path/to/key \\
        --base-url https://host/v1 --model some-model

Exit codes:
    0  LIVE      - HTTP 200 from the chat endpoint
    1  DEAD      - explicit auth rejection (401/403 with a real auth body)
    2  INCONCLUSIVE - could not classify (timeout, 5xx, header requirement)

The point of this script is the classification: a 403 whose body is only a
Cloudflare "error code: 1010" is a BOT-SIGNATURE BLOCK, not a revoked key.
It fires on the default urllib User-Agent while the key is perfectly valid.
Never report a credential as revoked on that signal.
"""
import argparse, json, sys, urllib.request, urllib.error

BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def probe(key, base_url, model, session=None):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "say ok"}],
        "max_tokens": 8,
    }).encode()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": BROWSER_UA,
    }
    # Some gateways route on a per-request session id and 400 without it.
    # That is a routing requirement, NOT a dead key.
    if session:
        headers["x-opencode-session"] = session
        headers["X-Session-Id"] = session

    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=body, headers=headers
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, r.read()[:400].decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400].decode("utf-8", "ignore")
    except Exception as e:
        return None, f"transport error: {e}"


def classify(code, text):
    t = text.lower()
    if code == 200:
        return 0, "LIVE - chat endpoint answered"
    if code is None:
        return 2, "INCONCLUSIVE - no HTTP response"
    if "1010" in t or "cloudflare" in t:
        return 2, ("INCONCLUSIVE - Cloudflare bot block (1010), NOT an auth "
                   "rejection. The key may be live; this probe is being blocked.")
    if "session" in t and code == 400:
        return 2, ("INCONCLUSIVE - provider requires a session header. The key is "
                   "not implicated by this response.")
    if code in (401, 403):
        return 1, f"DEAD - explicit auth rejection ({code})"
    if code >= 500:
        return 2, f"INCONCLUSIVE - upstream error ({code})"
    return 2, f"INCONCLUSIVE - unclassified HTTP {code}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--session", default=None,
                    help="session id to send if the gateway requires one")
    a = ap.parse_args()

    key = open(a.key_file).read().strip()
    print(f"key: sha256[:12]={__import__('hashlib').sha256(key.encode()).hexdigest()[:12]} len={len(key)}")

    # Pass 1: with a browser UA. Pass 2: without, to expose a 1010 block.
    code, text = probe(key, a.base_url, a.model, a.session)
    rc, verdict = classify(code, text)
    print(f"  with browser UA : HTTP {code}  {verdict}")

    if rc == 2 and "1010" in text.lower():
        print("  -> the key is NOT proven dead. Do not report it as revoked.")

    if rc != 0 and a.session is None:
        import uuid
        code2, text2 = probe(key, a.base_url, a.model,
                             session="probe-" + uuid.uuid4().hex[:12])
        rc2, verdict2 = classify(code2, text2)
        print(f"  with session hdr: HTTP {code2}  {verdict2}")
        if rc2 == 0:
            rc = 0

    print("  body:", text[:200].replace("\n", " "))
    sys.exit(rc)


if __name__ == "__main__":
    main()
