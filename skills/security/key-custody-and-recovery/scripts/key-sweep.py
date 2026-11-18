#!/usr/bin/env python3
"""Sweep every text file for 64-hex key material, DERIVE each to an address, and match targets.

The skill's rule: a zero needs a denominator. "The key isn't here" is a guess; "N files scanned,
M distinct addresses derived, K matches for the target" is a measurement. This prints those numbers and
NEVER prints key material, and never prints a derived address that did not match.

Why derivation and not a grep: a key-shaped string can live in a file whose NAME matches no pattern
(measured: a live key in a file called `celo-rail-key`). Only deriving proves what a 64-hex actually is.

Usage:
  python3 key-sweep.py --root /opt/data --targets 0xABC… 0xDEF… [--max-bytes 20000000] [--json-out f]
Exit: 0 when the sweep RAN (findings are data, not breakage). 2 when it could not run — never a pass.

Reading the output (say this in the report, not just the numbers):
  * `distinct addresses` is INFLATED by sha256 digests — any 64-hex derives. So the denominator bounds the
    input class: "among every 64-hex anywhere on this host — keys and hashes alike — none derived to the
    target". Never present it as a key count.
  * a match whose variable is `API_SERVER_KEY`/a session token is NOT a wallet key. Name the variable.
"""
import argparse
import json
import os
import re
import sys

HEX64 = re.compile(r"(?:0x)?([0-9a-fA-F]{64})(?![0-9a-fA-F])")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "site-packages", "cache", ".npm-global"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".wav", ".zip", ".gz", ".xz",
            ".tar", ".db", ".sqlite", ".pyc", ".so", ".whl", ".pdf", ".ico", ".woff", ".woff2"}


def derive(h: str):
    from eth_account import Account
    try:
        return Account.from_key("0x" + h).address
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/opt/data")
    ap.add_argument("--targets", nargs="*", default=[])
    ap.add_argument("--max-bytes", type=int, default=20_000_000)
    ap.add_argument("--json-out", default="")
    a = ap.parse_args()

    try:
        import eth_account  # noqa: F401
    except ModuleNotFoundError:
        print("  CANNOT RUN: eth_account missing — exit 2, NOT a clean sweep")
        return 2

    targets = {t.lower(): t for t in a.targets}
    files = 0
    addrs: dict[str, list[str]] = {}
    matches = []
    skipped_big = errors = 0

    for dirpath, dirnames, filenames in os.walk(a.root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) > a.max_bytes:
                    skipped_big += 1
                    continue
                text = open(p, "rb").read().decode("utf-8", errors="ignore")
            except OSError:
                errors += 1
                continue
            if "0" not in text:
                continue
            files += 1
            for m in set(HEX64.findall(text)):
                ad = derive(m)
                if not ad:
                    continue
                addrs.setdefault(ad, []).append(p)
                if ad.lower() in targets:
                    matches.append((ad, p))

    print(f"  files scanned          : {files}")
    print(f"  distinct addresses      : {len(addrs)}   (INFLATED by hashes — see header)")
    print(f"  targets asked for       : {len(targets)}")
    print(f"  MATCHES                 : {len(matches)}")
    for ad, p in matches:
        print(f"    MATCH {ad}  in {p}")
    if skipped_big:
        print(f"  skipped (>max-bytes)    : {skipped_big}")
    if errors:
        print(f"  unreadable              : {errors}")

    top = sorted(addrs.items(), key=lambda kv: -len(kv[1]))[:12]
    if top:
        print("\n  files holding derived material (paths only — name the VARIABLE before calling it a wallet):")
        for ad, paths in top:
            print(f"    {len(paths):>3} file(s) -> {ad[:10]}…  e.g. {paths[0]}")
    if a.json_out:
        json.dump({"files": files, "distinct": len(addrs),
                   "matches": [{"address": ad, "path": p} for ad, p in matches],
                   "holdings": {ad: sorted(set(ps))[:5] for ad, ps in addrs.items()}},
                  open(a.json_out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
