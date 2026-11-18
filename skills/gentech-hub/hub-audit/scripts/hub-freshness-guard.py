#!/usr/bin/env python3
"""hub-freshness-guard.py — is a dashboard's data TRUE, or merely reachable?

WHY THIS EXISTS (and why it is in a skill's scripts/, not one seat's profile)
  A hub whose fetches 404 shows dashes; someone goes looking. A hub whose fetches work but whose payload is
  months old looks FINE and is quoted as today. The first fault announces itself, the second does not — so the
  age of every feed has to be an asserted fact, on a schedule, not something a human notices later.

THREE ASSERTIONS PER SOURCE
  (a) the payload PARSES                     invalid JSON is a fault, not a number (conflict-marked files!)
  (b) `lastUpdated` is under the stale bound
  (c) an unreadable source prints UNKNOWN   — never 0, never "clean", never silence

EXIT CODES (the guard's own contract — for humans and for scripts)
  0  every source is fresh
  1  at least one source is STALE or ARCHIVED      (a finding — speak it)
  2  at least one source could not be read/parsed  (UNKNOWN — louder than a finding)
  3  bad usage

⚠️ WHEN YOU SCHEDULE THIS, PUT IT BEHIND A WRAPPER. A cron runner reads non-zero as "the job FAILED", so
   passing rc 1/2 through records a failure on every run and trains the operator to mute it. Wrapper contract:
   rc 0 -> exit 0 silent · rc 1|2 -> write state, print, exit 0 · anything else -> exit loud. The guard stays
   honest for humans; the job stays honest for the scheduler.

USAGE
  hub-freshness-guard.py [--json] [--selftest] [--stale-days 3] [--archive-days 30]
  Edit SOURCES below (or import classify() into your own harness — the judgement is a pure function).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request

# ── configure ─────────────────────────────────────────────────────────────────────────────────────────────
# (name, url, required). Keep one entry per feed the page actually renders. A feed on a DIFFERENT origin than
# the page is a second failure mode — same-origin data in the deploy tree removes it.
BASE = "https://example.github.io"
SOURCES = [
    ("feed_a", f"{BASE}/data/a.json", True),
    ("feed_b", f"{BASE}/data/b.json", True),
]
UA = "hub-freshness-guard/1.0 (+identify-yourself; freshness only)"  # an identifying UA is part of a probe
TIMEOUT = 25


def fetch(url: str, timeout: int = TIMEOUT) -> tuple[bytes | None, str]:
    """Return (body, error). A network failure is an ERROR, never an empty body."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), ""
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"network: {getattr(e, 'reason', e)}"
    except Exception as e:  # noqa: BLE001 — anything else is still "could not look"
        return None, f"{type(e).__name__}: {e}"


def find_last_updated(obj, depth: int = 0):
    """First `lastUpdated` anywhere in the payload — the stamp is often nested one level down."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for k in ("lastUpdated", "last_updated", "_lastUpdated"):
            if isinstance(obj.get(k), str):
                return obj[k]
        for v in obj.values():
            got = find_last_updated(v, depth + 1)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj[:5]:
            got = find_last_updated(v, depth + 1)
            if got:
                return got
    return None


def parse_ts(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def classify(name: str, body: bytes | None, err: str, now: dt.datetime,
             stale_days: float, archive_days: float, required: bool = True) -> dict:
    """The whole judgement as a PURE function of (bytes, clock) — so it can be tested without a network."""
    row = {"source": name, "state": "UNKNOWN", "age_days": None, "last_updated": None,
           "detail": err or "", "required": required, "bytes": len(body) if body else 0}
    if body is None:
        row["detail"] = err or "could not read"
        return row
    try:
        payload = json.loads(body)
    except Exception as e:  # noqa: BLE001
        row["state"] = "INVALID"
        row["detail"] = f"source is not valid JSON: {str(e)[:90]}"
        return row
    stamp = find_last_updated(payload)
    if not stamp:
        row["state"] = "NO_TIMESTAMP"
        row["detail"] = "parsed, but carries no lastUpdated — age cannot be stated"
        return row
    ts = parse_ts(stamp)
    if ts is None:
        row["state"] = "NO_TIMESTAMP"
        row["detail"] = f"unparseable lastUpdated {stamp!r}"
        return row
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    age = (now - ts.astimezone(dt.timezone.utc)).total_seconds() / 86400.0
    row["age_days"] = round(age, 1)
    row["last_updated"] = ts.astimezone(dt.timezone.utc).strftime("%Y-%m-%d")
    if age > archive_days:
        row["state"] = "ARCHIVED"
    elif age > stale_days:
        row["state"] = "STALE"
    else:
        row["state"] = "FRESH"
    return row


def overall(rows: list[dict]) -> int:
    """UNKNOWN outranks STALE: not knowing is louder than knowing it is old."""
    states = {r["state"] for r in rows}
    if states & {"UNKNOWN", "INVALID", "NO_TIMESTAMP"}:
        return 2
    if states & {"STALE", "ARCHIVED"}:
        return 1
    return 0


def render(rows: list[dict], now: dt.datetime) -> str:
    icon = {"FRESH": "OK  ", "STALE": "STALE", "ARCHIVED": "ARCHIVED",
            "INVALID": "INVALID", "UNKNOWN": "UNKNOWN", "NO_TIMESTAMP": "NO-TS"}
    lines = [f"HUB FRESHNESS — checked {now.strftime('%Y-%m-%d %H:%MZ')} (stale >3d, archived >30d)"]
    for r in rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "age unknown"
        tail = f" · {r['detail']}" if r["detail"] else ""
        lines.append(f"  {icon.get(r['state'], '?'):<9} {r['source']:<10} {r['last_updated'] or '—':<10} {age:<11}{tail}")
    code = overall(rows)
    if code == 2:
        lines.append("  UNKNOWN — could not read/parse at least one source. This is NOT a healthy page.")
    elif code == 1:
        lines.append("  FINDING — reachable but old. Do not report it as live.")
    else:
        lines.append("  OK — every source parses and is inside the stale bound.")
    return "\n".join(lines)


def cmd_selftest() -> int:
    now = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc)
    results = []

    def check(name, ok):
        results.append((name, bool(ok)))

    fresh = json.dumps({"lastUpdated": "2025-12-31T20:00:00Z", "x": 1}).encode()
    old = json.dumps({"lastUpdated": "2025-10-01T00:00:00Z"}).encode()
    stale = json.dumps({"lastUpdated": "2025-12-25T00:00:00Z"}).encode()
    rot = b'{\n<<<<<<< Updated upstream\n "lastUpdated": "2025-10-01T00:00:00Z"\n=======\n>>>>>>> Stashed changes\n}'

    check("a fresh payload classifies FRESH", classify("t", fresh, "", now, 3, 30)["state"] == "FRESH")
    check("90-day-old data is ARCHIVED, never healthy", classify("t", old, "", now, 3, 30)["state"] == "ARCHIVED")
    check("7-day-old data is STALE", classify("t", stale, "", now, 3, 30)["state"] == "STALE")
    r = classify("t", rot, "", now, 3, 30)
    check("conflict-marker JSON is INVALID with no age", r["state"] == "INVALID" and r["age_days"] is None)
    r = classify("t", None, "network: timed out", now, 3, 30)
    check("a failed fetch is UNKNOWN with no age (never 0)", r["state"] == "UNKNOWN" and r["age_days"] is None)
    check("parsed-with-no-timestamp is NOT fresh", classify("t", b'{"x": 1}', "", now, 3, 30)["state"] == "NO_TIMESTAMP")
    check("UNKNOWN outranks STALE in the exit code",
          overall([classify("a", old, "", now, 3, 30), classify("b", None, "HTTP 404", now, 3, 30)]) == 2)
    check("all-fresh exits 0", overall([classify("a", fresh, "", now, 3, 30)]) == 0)
    check("one archived exits 1", overall([classify("a", old, "", now, 3, 30)]) == 1)
    nested = json.dumps({"payload": {"lastUpdated": "2025-12-31T00:00:00Z"}}).encode()
    check("nested lastUpdated is found", classify("t", nested, "", now, 3, 30)["state"] == "FRESH")
    check("an identifying User-Agent is set", "freshness" in UA and len(UA) > 10)
    txt = render([classify("rot", rot, "", now, 3, 30)], now)
    check("the report never prints OK for a bad source", "INVALID" in txt and "OK — every source" not in txt)

    for n, ok in results:
        print(f"  {'GREEN' if ok else 'RED  '}  {n}")
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} pass" + (f" — FAILING: {bad}" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stale-days", type=float, default=3)
    ap.add_argument("--archive-days", type=float, default=30)
    a = ap.parse_args()
    if a.selftest:
        return cmd_selftest()

    now = dt.datetime.now(dt.timezone.utc)
    rows = [classify(n, *fetch(u), now, a.stale_days, a.archive_days, req) for n, u, req in SOURCES]
    print(json.dumps({"checked": now.isoformat(), "exit": overall(rows), "sources": rows}, indent=1)
          if a.json else render(rows, now))
    return overall(rows)


if __name__ == "__main__":
    sys.exit(main())
