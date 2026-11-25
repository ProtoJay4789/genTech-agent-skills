#!/usr/bin/env python3
"""dept-reflect.py — each seat grades ITS OWN department, on numbers, run to run.

Distinct from self-reflect.py, which is HQ-only and asks CONFIGURATION questions about the whole
fleet (graded from outside). This runs ON the seat, reads ONLY that seat's own tree, and answers
the questions that matter for its own work.

WHY A SCORECARD
    A reflection written fresh each run is an essay, and you cannot tell improvement from a change
    of mood. Every probe is a number or a yes/no, the result is stored, and each run prints WHAT
    MOVED. A department that improves silently still gets credit.

SILENCE STANDARD
    --quiet prints nothing when nothing regressed and nothing fails. A daily "all clear" is the
    heartbeat that trains a reader to ignore the channel.

USAGE
    dept-reflect.py            measure, compare to baseline, print what moved
    dept-reflect.py --save     measure AND store as the new baseline
    dept-reflect.py --json     machine-readable
    dept-reflect.py --quiet    print nothing when healthy (for cron)

EXIT  0 no regression · 2 at least one probe failed or got worse · 3 could not measure
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Derive the seat from THIS file's path (profiles/<seat>/scripts/...), never from an argument:
# an argument a caller can get wrong is a wrong reading waiting to happen.
PROFILE = os.environ.get("DEPT_PROFILE") or os.path.basename(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = f"/opt/data/profiles/{PROFILE}"
JOBS = f"{ROOT}/cron/jobs.json"
BASELINE = f"{ROOT}/cache/dept-reflect-baseline.json"

CAPS = {"MEMORY.md": 3200, "USER.md": 1800}   # read these from config if the seat differs
HEADROOM_FLOOR = 200                          # ≈ two durable facts


def _jobs() -> list:
    try:
        d = json.load(open(JOBS))
        return d if isinstance(d, list) else d.get("jobs", [])
    except (OSError, json.JSONDecodeError):
        return []


def probe_cron_health():
    """A job whose last run errored is not "mostly fine" — it did not do its work."""
    jobs = _jobs()
    if not jobs:
        return False, 0, "no cron jobs on this seat"
    bad = [j.get("id") for j in jobs if j.get("last_status") not in (None, "ok")]
    return (len(bad) == 0), len(bad), f"{len(bad)} failed of {len(jobs)}"


def probe_cron_enabled():
    """A disabled job is a silent decision — it looks like coverage and isn't."""
    jobs = _jobs()
    if not jobs:
        return False, 0, "no cron jobs on this seat"
    off = [j.get("id") for j in jobs if not j.get("enabled")]
    return (len(off) == 0), len(off), f"{len(off)} disabled of {len(jobs)}"


def probe_memory_headroom():
    """Can this seat still LEARN? Measured in characters left, SIGNED, not percent.

    A file can be PAST its cap; from that moment every write is refused with no signal. That is
    what "the agent forgot yesterday" looks like from the inside, so headroom is probed directly
    and a NEGATIVE reading is a failure, not a rounding artifact.
    """
    worst = None
    for name, cap in CAPS.items():
        p = f"{ROOT}/memories/{name}"
        try:
            left = cap - os.path.getsize(p)
        except OSError:
            continue
        if worst is None or left < worst[1]:
            worst = (name, left)
    if worst is None:
        return False, 0, "no memory files readable"
    return (worst[1] >= HEADROOM_FLOOR), worst[1], f"{worst[0]} has {worst[1]} chars left"


def probe_scripts_runnable():
    """Does every script this seat's cron references actually exist?

    Same class as a route declared in a manifest whose handler was never written: the entry
    reports enabled while the thing it names does not exist.
    """
    missing = []
    for j in _jobs():
        s = (j.get("script") or "").strip()
        if not s:
            continue
        if not os.path.exists(f"{ROOT}/scripts/{s}") and not os.path.exists(f"/opt/data/scripts/{s}"):
            missing.append(s)
    return (len(missing) == 0), len(missing), (
        f"{len(missing)} missing script(s)" + (f": {missing[:3]}" if missing else ""))


def probe_delivery():
    """A job that reports into nowhere is indistinguishable from one that works."""
    jobs = _jobs()
    if not jobs:
        return False, 0, "no cron jobs on this seat"
    unset = [j.get("id") for j in jobs
             if j.get("enabled") and not (j.get("deliver") or j.get("delivery") or j.get("deliver_to"))]
    return (len(unset) == 0), len(unset), f"{len(unset)} enabled job(s) with no delivery target"


PROBES = [
    ("01_cron_health", probe_cron_health),
    ("02_cron_enabled", probe_cron_enabled),
    ("03_memory_headroom", probe_memory_headroom),
    ("04_scripts_runnable", probe_scripts_runnable),
    ("05_delivery_set", probe_delivery),
]


def _better(name: str, cur, prev) -> bool:
    """Every probe scores lower-is-better except headroom, which is higher-is-better."""
    if name == "03_memory_headroom":
        return cur > prev
    return cur < prev


def main() -> int:
    argv = sys.argv[1:]
    quiet, as_json, save = "--quiet" in argv, "--json" in argv, "--save" in argv

    rows = []
    for name, fn in PROBES:
        try:
            ok, val, note = fn()
        except Exception as e:                                    # noqa: BLE001
            ok, val, note = False, None, f"PROBE ERROR {type(e).__name__}: {e}"[:120]
        rows.append((name, ok, val, note))

    try:
        base = json.load(open(BASELINE))
    except (OSError, json.JSONDecodeError):
        base = {}

    moved = []
    for name, _ok, val, _note in rows:
        prev = base.get(name, {}).get("value")
        if isinstance(val, (int, float)) and isinstance(prev, (int, float)) and val != prev:
            moved.append((name, prev, val, "better" if _better(name, val, prev) else "worse"))

    failing = [r for r in rows if not r[1]]
    if as_json:
        print(json.dumps({
            "profile": PROFILE,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "probes": [{"name": n, "ok": o, "value": v, "note": t} for n, o, v, t in rows],
            "moved": moved,
        }, indent=1))
    elif not (quiet and not failing and not moved):
        passed = sum(1 for r in rows if r[1])
        print(f"🔍 {PROFILE} — department self-reflection · {passed}/{len(rows)} passing · "
              f"{datetime.now(timezone.utc):%Y-%m-%d %H:%MZ}")
        for name, ok, _val, note in rows:
            print(f"   {'✅' if ok else '🔴'} {name:22} {note}")
        for name, prev, cur, verdict in moved:
            print(f"   {'⬆️' if verdict == 'better' else '⬇️'} {name}: {prev} → {cur}")

    if save:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        json.dump({n: {"ok": o, "value": v} for n, o, v, _t in rows}, open(BASELINE, "w"), indent=1)

    if failing:
        # ⚠️ PRINT THE VERDICT BEFORE RETURNING 2 — the wrapper swallows this exit code, so stdout is
        # the only signal that reaches a human. Without this line the shipped pair builds a monitor that
        # cannot go red: wrapper turns 2 into success, .py says nothing, and a broken department reports
        # clean. Measured on four seats: every run logged `error` for weeks while the scorecard it never
        # printed held the findings. Suppressed under --json so machine output stays parseable.
        if not as_json:
            print(f"⚠️ FINDINGS: {len(failing)} probe(s) failed — "
                  f"{', '.join(r[0] for r in failing)}")
        return 2
    if any(v == "worse" for *_x, v in moved):
        if not as_json:
            print("⚠️ REGRESSED: " + ", ".join(n for n, _p, _c, v in moved if v == "worse"))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
