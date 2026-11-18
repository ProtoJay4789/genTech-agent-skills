#!/usr/bin/env python3
"""x402 surface sweep — enumerate every hostname and find any real 402.

A valid /.well-known/x402 proves a service DESCRIBES payment; only a 402 proves it
RAISES it. If nothing 402s anywhere, the paid surface is either unmapped (we have not
probed the documented resource paths) or drifted (the discovery doc advertises payment
the handler never collects). One pass distinguishes them.

Usage:
  ./x402-surface-sweep.py --domain gentechlabs.net api defi lp fleet search feedback
  ./x402-surface-sweep.py --domain example.com --paths /v1/price/ETH,/v1/pools api
  HOSTS="api.example.com b.example.com" ./x402-surface-sweep.py

Exit: 0 = at least one 402 found  |  10 = hosts live but NOTHING charges
      2 = nothing answered (check DNS before concluding anything about the rail)
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_PATHS = ["/health", "/.well-known/x402", "/openapi.json", "/pricing", "/"]


def probe(url, n=4000, timeout=12):
    req = urllib.request.Request(
        url, headers={"User-Agent": "GenTechLabs/1.0 x402-surface-sweep"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(n).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(n).decode("utf-8", "replace")
    except Exception as e:  # DNS, TLS, timeout — all "did not answer"
        return 0, type(e).__name__


def full_host(name, domain):
    if "." in name or not domain:
        return name
    return f"{name}.{domain}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hosts", nargs="*", help="short names (api, defi) or full hostnames")
    ap.add_argument("--domain", default=os.environ.get("SWEEP_DOMAIN", ""))
    ap.add_argument("--paths", default=",".join(DEFAULT_PATHS))
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    hosts = a.hosts or os.environ.get("HOSTS", "").split()
    if not hosts:
        ap.error("give hostnames on the command line or via HOSTS=")
    hosts = [full_host(h, a.domain) for h in hosts]
    paths = [p for p in a.paths.split(",") if p]

    jobs = [(h, p) for h in hosts for p in paths]
    res = {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        outs = ex.map(lambda j: probe(f"https://{j[0]}{j[1]}"), jobs)
        for (h, p), out in zip(jobs, outs):
            res.setdefault(h, {})[p] = out

    w = max(len(h) for h in hosts) + 2
    print(f"{'host':<{w}}" + "".join(f"{p:<24}" for p in paths))
    print("-" * (w + 24 * len(paths)))
    for h in hosts:
        row = "".join(
            f"{str(res.get(h, {}).get(p, (0, ''))[0]):<24}" for p in paths
        )
        print(f"{h:<{w}}{row}")

    print("\n=== discovery docs (a 200 here does NOT mean the host charges) ===")
    for h in hosts:
        code, body = res.get(h, {}).get("/.well-known/x402", (0, ""))
        try:
            doc = json.loads(body)
            acc = doc.get("accepts")
            n = len(acc) if isinstance(acc, list) else None
        except Exception:
            doc, n = None, None
        if code == 200 and doc is not None and n is not None:
            print(
                f"  {h:<{w}} x402Version={doc.get('x402Version')}"
                f"  accepts={n}  version={doc.get('version')}"
            )
        elif code == 200:
            print(f"  {h:<{w}} 200 but not a discovery doc")
        else:
            print(f"  {h:<{w}} {code if code else 'no answer'}")

    charged = [
        (h, p)
        for h in hosts
        for p, (c, _) in res.get(h, {}).items()
        if c == 402
    ]
    live = [h for h in hosts if any(c for c, _ in res.get(h, {}).values())]

    print("\n=== verdict ===")
    if charged:
        print("  402s found — the rail charges:")
        for h, p in charged:
            print(f"    {h}{p}")
        return 0
    if live:
        print(f"  {len(live)} host(s) answer; NOTHING returns a 402.")
        print("  Two causes, distinguishable: (a) we have not probed the DOCUMENTED")
        print("  resource paths, or (b) the discovery doc advertises payment the handler")
        print("  does not collect. Read each host's /openapi.json + /pricing, then re-probe")
        print("  those exact paths via --paths: a declared paid resource answering 200")
        print("  proves (b) — doc/code drift.")
        return 10
    print("  No host answered — check DNS before concluding anything about the rail.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
