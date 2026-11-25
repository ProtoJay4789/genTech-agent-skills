#!/usr/bin/env python3
"""dept-reflect.py — each seat grades ITS OWN department, on numbers, run to run.

Jordan, 2026-11-18: *"we could ask agents about the current cron jobs that they run in their
departments… and get a self-reflection of that, see what we can improve, do better."*

WHY THIS IS NOT self-reflect.py
    self-reflect.py is HQ-only and asks CONFIGURATION questions about the whole fleet (are the
    fallbacks metered, do the skills agree, does every cron name a model). It grades the seats from
    outside. Nobody grades their own department.

    This runs ON the seat, reads ONLY that seat's own tree, and answers the questions that matter
    for its own work. Treasury's questions are about money being real. Arthur's are about learners
    getting answers. Proto J's are about the content ledger. HQ's are about the fleet.

WHY A SCORECARD AGAIN
    Same reason as self-reflect: a reflection written fresh each run is an essay, and you cannot
    tell improvement from a change of mood. Every probe is a number or a yes/no, the result is
    stored, and each run prints WHAT MOVED. A department that improves silently still gets credit.

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
import subprocess
import sys
from datetime import datetime, timezone

PROFILE = os.environ.get("DEPT_PROFILE") or os.path.basename(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = f"/opt/data/profiles/{PROFILE}"
JOBS = f"{ROOT}/cron/jobs.json"
BASELINE = f"{ROOT}/cache/dept-reflect-baseline.json"


def _jobs() -> list:
    try:
        d = json.load(open(JOBS))
        return d if isinstance(d, list) else d.get("jobs", [])
    except (OSError, json.JSONDecodeError):
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Probes. Every one must be answerable from files on THIS seat, and must return
# (ok: bool, measured: number|str, note: str). No probe may read another seat.
# ─────────────────────────────────────────────────────────────────────────────

def probe_cron_health():
    """Are this seat's jobs actually running clean?

    A job whose last run errored is not "mostly fine" — it is a job that did not do its work.
    Reported as a count so a day with 3 failures cannot look the same as a day with 0.
    """
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
    """Can this seat still LEARN? Measured in characters left, not percent.

    Arthur forgot a conversation on 2026-11-18. That is what a full memory file looks like from
    the outside: writes are refused and the seat stops accumulating what it is told. Headroom is
    the single number that predicts it, so it is probed directly.
    """
    worst = None
    for name in ("MEMORY.md", "USER.md"):
        p = f"{ROOT}/memories/{name}"
        try:
            size = os.path.getsize(p)
        except OSError:
            continue
        left = 3200 - size if name == "MEMORY.md" else 1800 - size
        if worst is None or left < worst[1]:
            worst = (name, left)
    if worst is None:
        return False, 0, "no memory files readable"
    # 200 chars is under two durable facts — below that the seat cannot record what it learns.
    return (worst[1] >= 200), worst[1], f"{worst[0]} has {worst[1]} chars left"


def probe_scripts_runnable():
    """Does every script this seat's cron references actually exist?

    The flow defect (2026-11-18) was a named handler that did not exist. The same shape recurs at
    the cron layer: a jobs.json entry pointing at a deleted script still reports enabled.
    """
    jobs = _jobs()
    missing = []
    for j in jobs:
        s = (j.get("script") or "").strip()
        if not s:
            continue
        if not os.path.exists(f"{ROOT}/scripts/{s}") and not os.path.exists(f"/opt/data/scripts/{s}"):
            missing.append(s)
    return (len(missing) == 0), len(missing), (
        f"{len(missing)} missing script(s)" + (f": {missing[:3]}" if missing else ""))


def probe_delivery():
    """Do this seat's jobs deliver somewhere that exists?

    A job that runs and reports into a room the bot cannot see is indistinguishable from a job
    that works — until someone asks why nothing was said.
    """
    jobs = _jobs()
    if not jobs:
        return False, 0, "no cron jobs on this seat"
    unset = [j.get("id") for j in jobs
             if j.get("enabled") and not (j.get("deliver") or j.get("delivery") or j.get("deliver_to"))]
    return (len(unset) == 0), len(unset), f"{len(unset)} enabled job(s) with no delivery target"


GENERIC = [
    ("01_cron_health", probe_cron_health),
    ("02_cron_enabled", probe_cron_enabled),
    ("03_memory_headroom", probe_memory_headroom),
    ("04_scripts_runnable", probe_scripts_runnable),
    ("05_delivery_set", probe_delivery),
]


def run(name_filter: str | None = None):
    rows = []
    for name, fn in GENERIC:
        try:
            ok, val, note = fn()
        except Exception as e:                                    # noqa: BLE001
            rows.append((name, False, None, f"PROBE ERROR {type(e).__name__}: {e}"[:120]))
            continue
        rows.append((name, ok, val, note))
    return rows


def load_baseline() -> dict:
    try:
        return json.load(open(BASELINE))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    argv = sys.argv[1:]
    quiet = "--quiet" in argv
    as_json = "--json" in argv
    save = "--save" in argv

    rows = run()
    if not rows:
        print("no probes", file=sys.stderr)
        return 3

    base = load_baseline()
    moved = []
    for name, ok, val, note in rows:
        prev = base.get(name, {}).get("value")
        if isinstance(val, (int, float)) and isinstance(prev, (int, float)):
            if val != prev:
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
            arrow = "⬆️" if verdict == "better" else "⬇️"
            print(f"   {arrow} {name}: {prev} → {cur}")

    if save:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        json.dump({n: {"ok": o, "value": v} for n, o, v, _t in rows}, open(BASELINE, "w"), indent=1)

    if failing:
        return 2
    if any(v == "worse" for *_x, v in moved):
        return 2
    return 0


def _better(name: str, cur, prev) -> bool:
    """All generic probes score lower-is-better except headroom and nothing else."""
    if name == "03_memory_headroom":
        return cur > prev
    return cur < prev


if __name__ == "__main__":
    sys.exit(main())
