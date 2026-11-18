#!/usr/bin/env python3
"""freshness-guard.py — is the data TRUE, or merely reachable?

WHY: repointing a broken fetch at the right URL is the easy half. Behind a correct URL the payload can be
months old, and a page full of old numbers reads as live while a page full of dashes reads as broken. This
asserts the second half: each source PARSES, each source carries an internal timestamp, and each is young
enough to be served.

RULES IT ENFORCES
  · parsed but no internal timestamp        -> NO_TIMESTAMP (never FRESH; mtime lies)
  · conflict markers / bad JSON            -> INVALID (never hand-merge a data file; republish it)
  · fetch failed / timeout                 -> UNKNOWN with a null age (never 0 days, never "clean")
  · UNKNOWN outranks STALE in the exit code (not knowing is louder than knowing it is old)

EXIT CODES: 0 all fresh · 1 stale/archived · 2 could-not-read/parse · 3 bad usage

USAGE
  freshness-guard.py SOURCES.json [--stale-days 3] [--archive-days 30] [--json] [--selftest]
  SOURCES.json = [{"name": "defi", "url": "https://host/data.json"}, ...]

WIRE IT TO A SCHEDULE or it is decoration: a guard nothing runs is a file, and a stale feed reported as
healthy because the fetch succeeded is the exact defect this exists to catch.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import sys
import urllib.error
import urllib.request

UA = "gentech-freshness-guard/1.0 (+ops@example.com)"  # identifying UA: anonymous clients draw 403s
TIMEOUT = 25


def fetch(url: str, timeout: int = TIMEOUT) -> tuple[bytes | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), ""
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"network: {getattr(e, 'reason', e)}"
    except Exception as e:  # noqa: BLE001 — anything is still "could not look"
        return None, f"{type(e).__name__}: {e}"


def find_stamp(obj, depth: int = 0):
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for k in ("lastUpdated", "last_updated", "as_of", "updated_at", "generated_at"):
            if isinstance(obj.get(k), str):
                return obj[k]
        for v in obj.values():
            if (got := find_stamp(v, depth + 1)):
                return got
    elif isinstance(obj, list):
        for v in obj[:5]:
            if (got := find_stamp(v, depth + 1)):
                return got
    return None


def classify(name, body, err, now, stale_days, archive_days) -> dict:
    """Pure: bytes + clock -> one row. No printing, so the selftest can drive it."""
    row = {"source": name, "state": "UNKNOWN", "age_days": None, "stamp": None,
           "detail": err or "", "bytes": len(body) if body else 0}
    if body is None:
        row["detail"] = err or "could not read"
        return row
    try:
        payload = json.loads(body)
    except Exception as e:  # noqa: BLE001
        row.update(state="INVALID", detail=f"not valid JSON: {str(e)[:90]}")
        return row
    stamp = find_stamp(payload)
    if not stamp:
        row.update(state="NO_TIMESTAMP", detail="parsed, carries no internal timestamp")
        return row
    try:
        ts = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        row.update(state="NO_TIMESTAMP", detail=f"unparseable stamp {stamp!r}")
        return row
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    age = (now - ts.astimezone(dt.timezone.utc)).total_seconds() / 86400.0
    row.update(age_days=round(age, 1), stamp=ts.strftime("%Y-%m-%d"))
    row["state"] = "ARCHIVED" if age > archive_days else ("STALE" if age > stale_days else "FRESH")
    return row


def overall(rows) -> int:
    """UNKNOWN/INVALID/NO_TIMESTAMP outrank STALE — not knowing is the louder fault."""
    states = {r["state"] for r in rows}
    if states & {"UNKNOWN", "INVALID", "NO_TIMESTAMP"}:
        return 2
    if states & {"STALE", "ARCHIVED"}:
        return 1
    return 0


def render(rows, now, stale_days=3, archive_days=30) -> str:
    icon = {"FRESH": "OK  ", "STALE": "STALE", "ARCHIVED": "ARCH",
            "INVALID": "INV ", "UNKNOWN": "UNK ", "NO_TIMESTAMP": "NOST"}
    out = [f"FRESHNESS — checked {now.strftime('%Y-%m-%d %H:%MZ')} (stale >{stale_days}d, archived >{archive_days}d)"]
    for r in rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "age unknown"
        tail = f" · {r['detail']}" if r["detail"] else ""
        out.append(f"  {icon.get(r['state'], '?')} {r['source']:<12} {r['state']:<12} "
                   f"{r['stamp'] or '—':<10} {age:<11}{tail}")
    code = overall(rows)
    out.append({0: "  OK — every source parses and is inside the freshness window.",
                1: "  FINDING — reachable but OLD. Do not report it as live.",
                2: "  UNKNOWN — could not read/parse at least one source. This is NOT healthy."}[code])
    return "\n".join(out)


def selftest() -> int:
    now = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    rows = []

    def chk(name, ok):
        rows.append((name, bool(ok)))

    fresh = json.dumps({"lastUpdated": "2025-12-31T12:00:00Z"}).encode()
    old = json.dumps({"lastUpdated": "2025-09-01T00:00:00Z"}).encode()
    stale = json.dumps({"lastUpdated": "2025-12-25T00:00:00Z"}).encode()
    conflicted = b'{\n<<<<<<< Updated upstream\n "lastUpdated": "2025-12-01T00:00:00Z"\n=======\n>>>>>>> Stashed changes\n}'
    chk("fresh payload is FRESH", classify("t", fresh, "", now, 3, 30)["state"] == "FRESH")
    chk("120-day-old payload is ARCHIVED, never healthy", classify("t", old, "", now, 3, 30)["state"] == "ARCHIVED")
    chk("7-day-old payload is STALE", classify("t", stale, "", now, 3, 30)["state"] == "STALE")
    r = classify("t", conflicted, "", now, 3, 30)
    chk("conflict-marker JSON is INVALID with no age", r["state"] == "INVALID" and r["age_days"] is None)
    r = classify("t", None, "network: timeout", now, 3, 30)
    chk("failed fetch is UNKNOWN with no age (never 0)", r["state"] == "UNKNOWN" and r["age_days"] is None)
    chk("parsed-with-no-stamp is NO_TIMESTAMP, not FRESH",
        classify("t", b'{"a": 1}', "", now, 3, 30)["state"] == "NO_TIMESTAMP")
    chk("UNKNOWN outranks STALE in the exit code",
        overall([classify("a", old, "", now, 3, 30), classify("b", None, "HTTP 404", now, 3, 30)]) == 2)
    chk("all fresh exits 0", overall([classify("a", fresh, "", now, 3, 30)]) == 0)
    chk("nested stamp is found",
        classify("t", json.dumps({"payload": {"lastUpdated": "2025-12-31T00:00:00Z"}}).encode(), "", now, 3, 30)["state"] == "FRESH")
    chk("report never says OK for a bad source", "OK —" not in render([classify("t", conflicted, "", now, 3, 30)], now))

    for n, ok in rows:
        print(f"  {'GREEN' if ok else 'RED  '}  {n}")
    bad = [n for n, ok in rows if not ok]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} pass" + (f" — FAILING: {bad}" if bad else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="?", help="JSON file: [{'name':..,'url':..}, ...]")
    ap.add_argument("--stale-days", type=float, default=3)
    ap.add_argument("--archive-days", type=float, default=30)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.sources:
        print("ERROR: need a SOURCES.json (or --selftest)", file=sys.stderr)
        return 3
    now = dt.datetime.now(dt.timezone.utc)
    srcs = json.load(open(a.sources, encoding="utf-8"))
    rows = [classify(s["name"], *fetch(s["url"]), now, a.stale_days, a.archive_days) for s in srcs]
    if a.json:
        print(json.dumps({"checked": now.isoformat(), "exit": overall(rows), "sources": rows}, indent=1))
    else:
        print(render(rows, now, a.stale_days, a.archive_days))
    return overall(rows)


if __name__ == "__main__":
    sys.exit(main())
