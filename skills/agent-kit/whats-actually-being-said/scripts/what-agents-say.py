#!/usr/bin/env python3
"""what-they-say.py — the PA's answer to "what are the agents actually saying?"

WHY THIS EXISTS (Jordan, 2026-11-24)
    "The personal assistant was also supposed to let me know what we need to be doing, what's important and who's
    working on what ... I'll know the agents are communicating when I check the brain, but the personal assistant
    will let me know what they're ACTUALLY SAYING."

    The vault tells him a note exists. It cannot tell him the seat disagreed with it, found the measurement wrong,
    or shipped something and said so in passing. That sentence lives in the seat's own conversation, in
    profiles/<seat>/state.db, and nothing was reading it.

WHAT IT READS, AND WHY IT IS SAFE
    Read-only SQLite (`mode=ro`) over each seat's `messages` table. It never opens a seat's session for writing and
    never calls a model — the cost is a local query, not a turn of context.

WHAT IT SKIPS, ON PURPOSE
    * its own reports TO the fleet ("**Treasury** (`seat`) · session …"), wake probes, cron deliveries and internal
      notifications — those are on the record already, and quoting them back to Jordan is the noise this job exists
      to remove;
    * anything under 80 characters, and any message with no sentence in it.

OUTPUT
    Per seat: what it said that a stranger could act on, capped, with the timestamp. Silent when a seat said nothing
    worth quoting — a seat with nothing to say is not an error.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import time

PROFILES = os.environ.get("HERMES_PROFILES", "/opt/data/profiles")
SEATS = tuple(sorted(d for d in os.listdir(PROFILES)
                     if os.path.exists(os.path.join(PROFILES, d, "state.db"))))
LABEL = {}

# Our own outbound reports, wake probes, and machine notices — never quoted back as conversation.
NOISE = re.compile(
    r"(?i)^(\*\*[a-z][\w \-]*(\([^)]*\))?\*\*\s*·|wake probe|cron(?:job)? response|\[internal|background process|"
    r"session `|probe \d+ answered)")

# A sentence worth quoting carries one of these: it is a claim, a decision, a correction, or work stated plainly.
SIGNAL = re.compile(
    r"(?i)\b(measured|the number|correction|wrong|fixed|shipped|shipping|blocked|can't|cannot|"
    r"recommend|decided|decision|built|deployed|found|evidence|turns out|actually|refuse|declined)\b")


def epoch(ts) -> float | None:
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return None
    return t / 1000 if t > 1e11 else t


def quotes(seat: str, hours: float, per_seat: int = 3) -> list[tuple[str, str]]:
    p = os.path.join(PROFILES, seat, "state.db")
    if not os.path.exists(p):
        return []
    cutoff = time.time() - hours * 3600
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "select content, timestamp from messages where role='assistant' "
            "and content is not null and length(content) > 80 order by rowid desc limit 600").fetchall()
    except Exception as exc:  # noqa: BLE001
        print(f"[say] {LABEL.get(seat) or seat}: could not read ({type(exc).__name__})", file=sys.stderr)
        return []

    out, seen = [], set()
    for r in rows:
        t = epoch(r["timestamp"])
        if not t or t < cutoff:
            continue
        txt = " ".join((r["content"] or "").split())
        if NOISE.match(txt) or not SIGNAL.search(txt):
            continue
        # one quote per conversation-shape: dedupe on the first 60 chars so a retried message appears once
        key = txt[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        # keep the first two sentences — the claim, not the whole report
        parts = re.split(r"(?<=[.!?])\s+", txt)
        snippet = " ".join(parts[:2])[:400]
        out.append((time.strftime("%m-%d %H:%MZ", time.gmtime(t)), snippet))
        if len(out) >= per_seat:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=20.0, help="how far back to read (default 20h)")
    ap.add_argument("--per-seat", type=int, default=3, help="max quotes per seat")
    ap.add_argument("--exclude", default=os.environ.get("SAY_EXCLUDE", ""),
                    help="comma-separated seats to skip (e.g. the reader's own seat)")
    a = ap.parse_args()

    skip = {x.strip() for x in a.exclude.split(",") if x.strip()}
    any_out = False
    for seat in SEATS:
        if seat in skip:
            continue
        q = quotes(seat, a.hours, a.per_seat)
        if not q:
            continue
        any_out = True
        print(f"[say] {LABEL.get(seat) or seat} — what they said since {int(a.hours)}h ago:")
        for when, snippet in q:
            print(f"[say]   {when}  {snippet}")
    if not any_out:
        print(f"[say] nothing quotable from the seats in the last {int(a.hours)}h "
              f"(a quiet fleet is not a fault; the notes are in the brain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
