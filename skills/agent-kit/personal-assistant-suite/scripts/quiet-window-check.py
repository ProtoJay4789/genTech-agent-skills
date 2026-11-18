#!/usr/bin/env python3
"""quiet-window-check — prove no cron job DELIVERS to a human inside quiet hours.

Quiet hours govern DELIVERY, not execution: overnight maintenance must still RUN.

The subtle failure this catches: `deliver=local` silences a job's normal output, but engine
failure/interruption notices follow `deliver` when `failure_deliver` is unset — so a job that is
"silent on success, speaks on failure" still pings at 3am on a bad night. Both are flagged.

The window is half-open [start, wake): the wake-up job sits at the end and is the night's single
voice, reading the state files the silent jobs wrote.

Usage:
  python3 quiet-window-check.py                       # defaults: 03:00-10:30 UTC, 24h
  python3 quiet-window-check.py --window 03:00-10:30 --hours 24
  python3 quiet-window-check.py --profiles-dir /opt/data/profiles

Exit: 0 clean - 1 violations - 2 no readable job files.
"""
import argparse
import datetime
import glob
import json
import os
import sys


NAMES = ("name", "job_id", "id")


def field(spec, lo, hi):
    """Expand one cron field ('*', 'a,b', 'a-b', '*/n', 'a-b/n') into a set of ints."""
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
            rng = (range(lo, hi + 1) if base == "*"
                   else range(int(base.split("-")[0]), int(base.split("-")[-1]) + 1))
            out |= {x for x in rng if (x - lo) % step == 0}
        elif "-" in part:
            a, b = part.split("-")
            out |= set(range(int(a), int(b) + 1))
        elif part == "*":
            out |= set(range(lo, hi + 1))
        else:
            out.add(int(part))
    return out


def fires(expr, start, hours):
    """Fires of a 5-field cron expression in [start, start+hours)."""
    f = expr.split()
    if len(f) != 5:
        return []
    mi, hh, dom, mon, dow = f
    M, H = field(mi, 0, 59), field(hh, 0, 23)
    D, W = field(dom, 1, 31), field(dow, 0, 6)
    end = start + datetime.timedelta(hours=hours)
    out, day = [], start.date()
    while datetime.datetime.combine(day, datetime.time(0), tzinfo=datetime.UTC) < end:
        if dom == "*" or day.day in D:
            for h in sorted(H):
                for m in sorted(M):
                    t = datetime.datetime.combine(day, datetime.time(h, m), tzinfo=datetime.UTC)
                    if start <= t < end and (dow == "*" or day.weekday() in {(w + 6) % 7 for w in W}):
                        out.append(t)
        day += datetime.timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", default="/opt/data/profiles")
    ap.add_argument("--window", default="03:00-10:30", help="UTC start-wake, half-open [start, wake)")
    ap.add_argument("--hours", type=int, default=24)
    a = ap.parse_args()

    def mins(s):
        h, m = s.split(":")
        return int(h) * 60 + int(m)

    lo, hi = (mins(x) for x in a.window.split("-"))
    now = datetime.datetime.now(datetime.UTC).replace(second=0, microsecond=0)
    rows, violations, unreadable, scanned = [], [], [], 0

    for path in sorted(glob.glob(os.path.join(a.profiles_dir, "*", "cron", "jobs.json"))):
        who = path.split(os.sep)[-3]
        try:
            data = json.load(open(path))
        except (OSError, ValueError) as e:
            unreadable.append(f"{who}: unreadable ({e})")
            continue
        for j in data.get("jobs", []):
            if not j.get("enabled", True):
                continue
            scanned += 1
            name = next((j.get(k) for k in NAMES if j.get(k)), "<unnamed>")
            sched = j.get("schedule") or {}
            if not isinstance(sched, dict) or sched.get("kind") != "cron":
                unreadable.append(f"{who}/{name}: non-cron schedule - review by hand")
                continue
            fs = fires(sched.get("expr", ""), now, a.hours)
            for t in fs:
                m = t.hour * 60 + t.minute
                if not (lo <= m < hi):
                    continue
                if j.get("deliver") != "local":
                    violations.append(f"{who}/{name} fires {t:%H:%M}Z -> deliver={j.get('deliver')}")
                elif not j.get("failure_deliver"):
                    violations.append(
                        f"{who}/{name} fires {t:%H:%M}Z -> deliver=local but failure_deliver unset "
                        f"(failure notices follow deliver; set it to local)")
            if fs:
                rows.append((min(fs), who, name, j.get("deliver"), len(fs)))

    print(f"quiet window (UTC, half-open): {a.window}   jobs scanned: {scanned}   next {a.hours}h")
    print(f"VIOLATIONS: {len(violations)}")
    for v in violations:
        print("  !", v)
    for u in unreadable:
        print("  ?", u)
    print("fire table (earliest first):")
    for t, who, name, dv, n in sorted(rows):
        print(f"  {t:%H:%MZ}  {who:16} {str(name)[:44]:46} deliver={dv:7} ({n} fires)")
    if unreadable and not rows:
        return 2
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
