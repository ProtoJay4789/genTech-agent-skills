#!/usr/bin/env python3
"""Queue router — READ-ONLY. Shows what department routing would do; changes nothing.

Why: Jordan, 2026-11-01 — *"let Gentech decide who should work on what project based on their department and
what's relevant to them. That way nobody has too much on their plate."*

That decision needs a `department` field the build queue does not have (0 of 102 items as measured
2026-11-01). This script infers one from `owner` so the distribution can be SEEN before anyone edits a
canonical file with 102 live items.

Rules it obeys:
- **Read-only.** It opens `build_queue.json` for reading and never writes it. There is no --apply flag.
- **Inference is labelled as inference.** Counts here are a starting point for a human to re-sort, not a
  verdict — `hq` is a dumping ground for everything owned by a machine rather than a domain.
- **Uncountable is reported as uncountable.** Items with no owner are listed, not silently bucketed.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

QUEUE = pathlib.Path("/opt/data/.obsidian-vault/scripts/build_queue.json")

# `owner` uses nine spellings across the 102 items. Two of them are the same department:
# gentech-treasury (30) and treasury (9). Collapsing them is the point.
OWNER_TO_DEPT = {
    "gentech-treasury": "treasury",
    "treasury": "treasury",
    "entertainment": "entertainment",
    "labs": "labs",
    "edu": "edu",
    "arcade": "arcade",
    # machine owners are NOT a department — they are "runs on this host"
    "gentech": "hq",
    "forge": "hq",
    "protojay": "hq",
    "unassigned": "hq",
    "none": "hq",
}
DEPARTMENTS = ("edu", "treasury", "arcade", "entertainment", "labs", "hq")
OPEN = ("pending", "in_progress", "blocked")


def load() -> list[dict]:
    d = json.loads(QUEUE.read_text())
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, list):
                return v
        return []
    return d


def dept_of(item: dict) -> tuple[str, bool]:
    """(department, was_inferred). An explicit `department` field always wins."""
    explicit = item.get("department")
    if explicit:
        e = str(explicit).strip().lower()
        if e in DEPARTMENTS:
            return e, False
        return "hq", True                      # unknown value — surfaced, never silently accepted
    owner = str(item.get("owner") or item.get("assigned_to") or "none").strip().lower()
    return OWNER_TO_DEPT.get(owner, "hq"), True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="(default) print the distribution, change nothing")
    ap.add_argument("--all", action="store_true", help="include closed/shipped items")
    a = ap.parse_args()

    items = load()
    rows = items if a.all else [i for i in items if i.get("status") in OPEN]

    per_dept = collections.defaultdict(lambda: {"n": 0, "owners": collections.Counter(), "ids": []})
    unknown_dept = 0
    no_owner = []
    for i in rows:
        d, inferred = dept_of(i)
        if inferred and not i.get("owner") and not i.get("assigned_to"):
            no_owner.append(i.get("id"))
        explicit = str(i.get("department") or "").strip().lower()
        if explicit and explicit not in DEPARTMENTS:
            unknown_dept += 1
        per_dept[d]["n"] += 1
        owner = str(i.get("owner") or i.get("assigned_to") or "none")
        per_dept[d]["owners"][owner] += 1
        per_dept[d]["ids"].append(i.get("id"))

    print(f"  {'department':14s} {'open':>5s}   owner-mix")
    print(f"  {'-'*14} {'-'*5}   {'-'*40}")
    for d in DEPARTMENTS:
        v = per_dept.get(d)
        if not v:
            continue
        mix = ", ".join(f"{k} {c}" for k, c in v["owners"].most_common())
        print(f"  {d:14s} {v['n']:5d}   {mix}")

    total = sum(v["n"] for v in per_dept.values())
    print(f"\n  {'TOTAL':14s} {total:5d}   ({'all' if a.all else 'open'} items)")

    print("\n  ── what is NOT trustworthy yet ──")
    print(f"  items needing a human re-sort (defaulted to hq): {per_dept.get('hq', {'n': 0})['n']}")
    if no_owner:
        print(f"  items with NO owner at all: {len(no_owner)} → {no_owner[:8]}")
    if unknown_dept:
        print(f"  items with an INVALID department value: {unknown_dept}")
    print("  (hq is a dumping ground for machine owners, not a real department — re-sort before trusting)")
    print("\n  READ-ONLY: nothing was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
