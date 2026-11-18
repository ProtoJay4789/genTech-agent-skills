#!/usr/bin/env python3
"""Classify skill drift by DIRECTION before any reconcile runs.

WHY: a bulk sync to "clear" a drift count overwrites whichever side is newer, and in a fleet that
learns the seat is usually newer. This prints the four buckets so a human (or a --reconcile mode)
can act only on the unambiguous ones.

    python3 classify-skill-drift.py --core <skills-distribution> --seats-dir /opt/data/profiles --dry

Bucket meanings and actions:
    seat-ahead   PROMOTE  (seat -> core)      seat content differs and is newer, or holds a file core lacks
    core-ahead   SYNC     (core -> seat)      core content differs and is newer
    both-changed REPORT ONLY                  differing files on both sides, each newer than its pair
    missing      SYNC                         skill absent downstream

Exit codes: 0 = classified (prints a table), 2 = both-changed found (a human decision exists).
`--dry` is the default; this script NEVER writes. Reconcile belongs in the caller, per bucket.
"""

import argparse
import hashlib
import os
import sys

SKIP_PARTS = (".git", "__pycache__")


def _files(root: str) -> dict:
    out = {}
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            if name.startswith(".") or ".bak-" in name:
                continue  # backups must never be compared as content
            path = os.path.join(dirpath, name)
            out[os.path.relpath(path, root)] = path
    return out


def _digest(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def classify(core: str, seat_dir: str) -> dict:
    core_files, seat_files = _files(core), _files(seat_dir)
    differing = [f for f in core_files
                 if f in seat_files and _digest(core_files[f]) != _digest(seat_files[f])]
    only_core = [f for f in core_files if f not in seat_files]
    only_seat = [f for f in seat_files if f not in core_files]

    if not differing and not only_core and not only_seat:
        return {"bucket": "identical"}

    core_newer = any(_mtime(core_files[f]) > _mtime(seat_files[f]) for f in differing)
    seat_newer = any(_mtime(seat_files[f]) > _mtime(core_files[f]) for f in differing)

    if core_newer and seat_newer:
        return {"bucket": "both-changed", "differing": differing,
                "only_core": only_core, "only_seat": only_seat}
    if only_seat or (seat_newer and not core_newer):
        return {"bucket": "seat-ahead", "only_seat": only_seat, "only_core": only_core}
    if core_newer or only_core:
        return {"bucket": "core-ahead", "only_core": only_core, "only_seat": only_seat}
    return {"bucket": "core-ahead", "only_core": only_core, "only_seat": only_seat}


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify skill drift by direction (read-only).")
    ap.add_argument("--core", required=True, help="skills-distribution root")
    ap.add_argument("--seats-dir", default="/opt/data/profiles")
    ap.add_argument("--seat", action="append", help="limit to these seats (repeatable)")
    ap.add_argument("--dry", action="store_true", help="accepted for clarity; this never writes")
    ap.add_argument("--show", type=int, default=3, help="examples to print per bucket")
    a = ap.parse_args()

    if not os.path.isdir(a.core):
        print(f"UNKNOWN: core not found: {a.core}", file=sys.stderr)
        return 2

    skills = []
    for category in sorted(os.listdir(a.core)):
        cdir = os.path.join(a.core, category)
        if not os.path.isdir(cdir):
            continue
        for name in sorted(os.listdir(cdir)):
            sdir = os.path.join(cdir, name)
            if os.path.isfile(os.path.join(sdir, "SKILL.md")):
                skills.append(os.path.relpath(sdir, a.core))

    seats = a.seat or sorted(d for d in os.listdir(a.seats_dir)
                             if os.path.isdir(os.path.join(a.seats_dir, d, "skills")))
    totals = {"seat-ahead": 0, "core-ahead": 0, "both-changed": 0, "missing": 0}
    ambiguous = []

    for seat in seats:
        base = os.path.join(a.seats_dir, seat, "skills")
        counts = {k: 0 for k in totals}
        examples = {k: [] for k in totals}
        for rel in skills:
            dst = os.path.join(base, rel)
            if not os.path.isdir(dst):
                counts["missing"] += 1
                continue
            res = classify(os.path.join(a.core, rel), dst)
            bucket = res["bucket"]
            if bucket == "identical":
                continue
            counts[bucket] += 1
            if len(examples[bucket]) < a.show:
                examples[bucket].append(rel)
            if bucket == "both-changed":
                ambiguous.append(f"{seat}:{rel}")
        print(f"{seat:<18} core-ahead={counts['core-ahead']:<3} seat-ahead={counts['seat-ahead']:<3} "
              f"both-changed={counts['both-changed']:<3} missing={counts['missing']}")
        for bucket in ("seat-ahead", "both-changed", "core-ahead"):
            for rel in examples[bucket]:
                print(f"    {bucket:<13} {rel}")
        for k in totals:
            totals[k] += counts[k]

    print(f"\nTOTAL core-ahead={totals['core-ahead']} seat-ahead={totals['seat-ahead']} "
          f"both-changed={totals['both-changed']} missing={totals['missing']}")
    print("\nAction order: PROMOTE every seat-ahead, then SYNC every core-ahead, then re-classify.")
    if ambiguous:
        print(f"\n⚠️ {len(ambiguous)} both-changed — a HUMAN decides; do not pick the newer mtime.")
        for item in ambiguous[:10]:
            print(f"    {item}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
