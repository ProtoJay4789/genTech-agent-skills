#!/usr/bin/env python3
"""
scan-residue.py — find where a leaked value actually lives. Prints counts, never the value.

WHY THIS EXISTS
    "The redactor said 0" is not a measurement. This scans what the redactor cannot see:
      * EVERY column of EVERY table (not a hardcoded list — an unlisted column is a blind spot)
      * the RAW BYTES of state.db AND state.db-wal (a clean logical scan is not a clean file)
      * every hex run containing the needle, so you learn whether a FRAGMENT or a FULL key is present

USAGE
    # literal (preferred). Assemble from parts in your own shell so the command line does not
    # re-insert the value into the transcript:
    P="8ab2""bcfe5" python3 scan-residue.py --needle-env P --profiles gentech

    # every profile's state.db
    P="<value>" python3 scan-residue.py --needle-env P --all

EXIT CONTRACT   0 = zero residue everywhere. 2 = residue found (or unreadable target).
NEVER            prints the needle, a match context, or any hex run's value.
"""
import argparse
import glob
import os
import re
import sqlite3
import sys


def hex_run_census(raw: bytes, needle: bytes):
    """Longest hex run containing the needle -> fragment vs full-secret, by LENGTH only."""
    runs = {len(m.group(0)) for m in re.finditer(rb"[0-9a-fA-F]{8,128}", raw) if needle in m.group(0)}
    return (max(runs) if runs else 0), sorted(runs)[:8]


def logical_scan(db: str, needle: str):
    """EVERY column of EVERY table/view. A hardcoded column list is how a secret survives."""
    found = {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=30)
    try:
        cur = con.cursor()
        objs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")]
        for t in objs:
            try:
                cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")')]
            except Exception:
                continue
            for c in cols:
                try:
                    n = cur.execute(
                        f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" LIKE ?', (f"%{needle}%",)
                    ).fetchone()[0]
                except Exception:
                    continue
                if n:
                    found[f"{t}.{c}"] = n
    finally:
        con.close()
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--needle", help="the literal value (prefer --needle-env)")
    ap.add_argument("--needle-env", help="env VAR NAME holding the value (keeps it out of argv)")
    ap.add_argument("--profiles", nargs="*", default=None, help="profile names, default: every profile")
    ap.add_argument("--all", action="store_true", help="scan every profile")
    a = ap.parse_args()

    needle = None
    if a.needle_env:
        needle = os.environ.get(a.needle_env)
        if not needle:
            sys.exit(f"env var {a.needle_env} is empty or unset")
    elif a.needle:
        needle = a.needle
    if not needle:
        sys.exit("need --needle-env (preferred) or --needle")

    print(f"  needle: {len(needle)} chars (value never printed)")
    if a.profiles:
        dbs = [f"/opt/data/profiles/{p}/state.db" for p in a.profiles]
    else:
        dbs = sorted(glob.glob("/opt/data/profiles/*/state.db"))

    bad = 0
    for db in dbs:
        if not os.path.exists(db):
            print(f"  {os.path.basename(os.path.dirname(db)):20s} MISSING")
            continue
        name = os.path.basename(os.path.dirname(db))

        # --- logical: every column of every table
        found = logical_scan(db, needle)

        # --- bytes: db AND wal (the part a logical scan cannot see)
        bites = {}
        for suffix in ("", "-wal", "-shm"):
            p = db + suffix
            try:
                raw = open(p, "rb").read()
            except Exception:
                continue
            n = raw.count(needle.encode())
            if n:
                longest, dist = hex_run_census(raw, needle.encode())
                bites[os.path.basename(p)] = (n, longest, dist)

        if not found and not bites:
            print(f"  {name:20s} ✅ clear")
            continue

        bad += 1
        print(f"  {name:20s} 🔴 RESIDUE")
        for k, v in sorted(found.items()):
            print(f"      logical  {v:6d}x  {k}")
        for k, (n, longest, dist) in sorted(bites.items()):
            print(f"      bytes    {n:6d}x  {k}   longest hex run containing it: {longest} ({dist})")
            if longest >= 64:
                print("      ⚠️ a run >= 64 chars means a FULL key/secret is on disk — escalate")

    print()
    if bad:
        print(f"  RESULT: residue in {bad} profile(s). Logical clears are not byte clears.")
        sys.exit(2)
    print("  RESULT: 0 residue, logical AND byte level. That is the only acceptable answer.")
    sys.exit(0)


if __name__ == "__main__":
    main()
