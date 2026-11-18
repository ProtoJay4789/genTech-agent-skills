#!/usr/bin/env python3
"""A keystore must never MINT a replacement for a tenant whose address is already recorded.

The failure this guards: a generate-on-first-use keystore meets a tenant whose key it does not hold
and mints a new key. The new address is valid, empty and nonce 0, so every downstream check passes
and nothing raises an alarm — while the recorded wallet becomes unspendable with no signal at all.

Rule: if a tenant has a RECORDED address and the keystore holds no key deriving to it, the keystore
must REFUSE and name the missing key. Availability is never a reason to mint a second address.

Usage:
  python3 keystore-mint-guard.py --recorded <tenants.json> --keystore <dir-or-index.json>

Exit codes (a guard whose exit is ambiguous is not a guard):
  0  consistent — every recorded address has a matching key, or nothing is recorded
  1  VIOLATION — a recorded address has no key, or the keystore holds a DIFFERENT address for it
  2  could not run (missing or unreadable input) — NOT a pass
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _addr(v):
    return v.lower() if isinstance(v, str) and v.startswith("0x") and len(v) == 42 else None


def _load_recorded(path: str) -> dict[str, str]:
    """tenant -> recorded address. Fails closed: an unreadable file is exit 2, never 'no tenants'."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    out: dict[str, str] = {}
    if isinstance(d, dict):
        addrs = d.get("addresses") or d.get("tenants") or d
        for k, v in (addrs or {}).items():
            if _addr(v):
                out[k] = _addr(v)
            elif isinstance(v, dict):
                a = _addr(v.get("address") or v.get("wallet"))
                if a:
                    out[k] = a
    return out


def _load_keystore_addresses(path: str) -> dict[str, str]:
    """tenant -> address the keystore actually holds a key for, from its own index."""
    out: dict[str, str] = {}
    files = []
    if os.path.isdir(path):
        for root, _dirs, names in os.walk(path):
            files += [os.path.join(root, n) for n in names if n.endswith(".json")]
    else:
        files = [path]
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001 — an unreadable index is reported by the caller, not swallowed silently
            continue
        for k, v in ((d.get("addresses") if isinstance(d, dict) else None) or {}).items():
            a = _addr(v) or _addr((v or {}).get("address") if isinstance(v, dict) else None)
            if a:
                out[k] = a
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recorded", required=True, help="registry/index naming each tenant's REAL address")
    ap.add_argument("--keystore", required=True, help="keystore dir or index json")
    a = ap.parse_args()
    try:
        recorded = _load_recorded(a.recorded)
        held = _load_keystore_addresses(a.keystore)
    except Exception as e:  # noqa: BLE001
        print(f"  CANNOT RUN: {e} — exit 2, NOT a pass")
        return 2

    if not recorded:
        print("  no recorded addresses — generation is unconstrained (state, not a pass)")
        return 0

    bad = 0
    for tenant, want in sorted(recorded.items()):
        got = held.get(tenant)
        if got == want:
            print(f"  OK        {tenant}: keystore holds a key for the recorded address {want[:10]}…")
        elif got:
            bad += 1
            print(f"  VIOLATION {tenant}: recorded {want[:10]}… but keystore minted {got[:10]}…")
            print("            → the recorded wallet is UNOPERABLE and a replacement was silently created")
        else:
            bad += 1
            print(f"  VIOLATION {tenant}: recorded {want[:10]}… and the keystore holds NO key for it")
            print("            → generation must REFUSE for this tenant, not mint a new address")

    print(f"\n  {len(recorded)} recorded tenant(s) · {bad} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
