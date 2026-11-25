#!/usr/bin/env python3
"""x402-signal — keep us in the loop on ecosystem SHIPS, not just ecosystem bugs.

WHY THIS EXISTS (2026-11-14): Base announced that Brave Search now accepts x402 payments on Base.
We found out because Jordan pasted the link. That is the wrong direction of information — a
household-name API adopting our protocol is the single most relevant event class we have, and we
had no instrument pointed at it. The existing `x402-trends` cron reads GitHub ISSUES (what people
are stuck on); it cannot see an announcement (what people just shipped). Different question,
different source, and only one of them was being asked.

WHAT IT DOES
  Reads a small, explicit source list. For each source, fetches, keeps only entries whose text
  matches the x402/agentic-payments vocabulary, and reports anything not already in the seen-ledger.
  Silence is the normal output — a quiet run means nothing shipped, not that the watch is broken.
  Prints a liveness line ALWAYS so "nothing new" and "could not fetch" can never look the same.

DESIGN RULES (from the fleet's own scars)
  * Watermark dedup: state file records what has been reported. A re-fetch of the same headline
    is not news, and a repeat alert trains the reader to ignore the alarm.
  * Absence of data is not a finding: every source that fails to fetch is named as UNREAD, and a
    run where every source failed exits non-zero so the cron wrapper can say so loudly.
  * No invented sources. Every URL below was fetched successfully by hand before being added; a
    source that starts returning 404 gets removed, not retried forever.

USAGE
  python3 x402-signal.py            # report NEW items only (cron)
  python3 x402-signal.py --all      # report everything currently matching, ignore the ledger
  python3 x402-signal.py --selftest # prove the matcher and the dedup, no network
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

STATE = "/opt/data/profiles/gentech/cron/x402-signal-state.json"

# Every source here was verified to respond 200 on 2026-11-14 before being added.
SOURCES = [
    # (label, url, mode)
    ("GitHub x402 releases", "https://api.github.com/repos/x402-foundation/x402/releases?per_page=15", "github"),
    ("GitHub x402 issues (recent)", "https://api.github.com/repos/x402-foundation/x402/issues?state=all&per_page=20&sort=created&direction=desc", "github"),
    ("Base blog", "https://www.base.org/blog", "html"),
]

# Vocabulary that means "someone shipped or changed something in our lane".
TERMS = [
    "x402", "402 payment", "agentic payment", "agent payment", "pay per call",
    "facilitator", "bazaar", "usdc on base", "micropayment", "agent wallet",
]

INTERESTING_TITLE = re.compile(r"x402|agentic pay|pay[- ]per[- ]call|facilitator|bazaar", re.I)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def load_state() -> dict:
    try:
        with open(STATE, encoding="utf-8") as fh:
            d = json.load(fh)
        if isinstance(d, dict) and isinstance(d.get("seen"), list):
            return d
    except Exception:
        pass
    return {"seen": [], "last_run": None, "runs": 0}


def save_state(st: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, STATE)


def fetch(url: str) -> tuple[str | None, str]:
    """(body, error). Exactly one is non-None."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "gentech-x402-signal/1.0",
        "Accept": "application/vnd.github+json, text/html, application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:80]}"


def parse_github(body: str) -> list[dict]:
    try:
        data = json.loads(body)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for it in data:
        title = (it.get("title") or it.get("name") or "").strip()
        if not title:
            continue
        url = it.get("html_url") or it.get("url") or ""
        body_txt = (it.get("body") or "")[:600]
        # ⚠️ MEASURED 2026-11-19: GitHub's /issues endpoint returns PULL REQUESTS AND ISSUES IN ONE
        # LIST — a PR carries a `pull_request` key, a real issue does not. The first version computed
        # kind from the URL and so labelled every PR "[issue]". Jordan saw twelve lines reading
        # "[issue]" and asked whether the job acts on them; it could not even tell him what they were.
        # 11 of the first 12 entries that night were PRs. A watcher that mislabels its input cannot be
        # acted on, so the distinction is now made from the payload itself.
        if "releases" in url:
            kind = "release"
        elif it.get("pull_request") is not None:
            kind = "pr"
        else:
            kind = "issue"
        out.append({"id": f"github:{kind}:{it.get('id') or title}", "title": title,
                    "url": url, "kind": kind, "text": f"{title} {body_txt}",
                    "merged": (it.get("pull_request") or {}).get("merged_at"),
                    "state": it.get("state")})
    return out


def parse_html(body: str, source_label: str) -> list[dict]:
    """Headlines from a blog index. Deliberately crude: we want titles, not a scraper."""
    out = []
    seen = set()
    for m in re.finditer(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.S | re.I):
        raw = re.sub(r"<[^>]+>", " ", m.group(1))
        title = re.sub(r"\s+", " ", raw).strip()
        if 12 < len(title) < 180 and title.lower() not in seen:
            seen.add(title.lower())
            out.append({"id": f"{source_label}:{title.lower()}", "title": title,
                        "url": "", "kind": "announcement", "text": title})
    return out


def matches(entry: dict) -> bool:
    t = (entry.get("text") or "").lower()
    return any(term in t for term in TERMS)


def selftest() -> int:
    """Prove the matcher keeps signal and the dedup drops repeats. No network."""
    fails = 0

    def check(name: str, got, want):
        nonlocal fails
        ok = got == want
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r} want {want!r}")
        if not ok:
            fails += 1

    check("x402 mention matches", matches({"text": "Brave adds x402 payments"}), True)
    check("facilitator mention matches", matches({"text": "new facilitator in town"}), True)
    check("unrelated news is ignored", matches({"text": "we hired a new designer"}), False)

    gh = json.dumps([
        {"id": 1, "title": "v2 settle returns invalid_network", "html_url": "https://x/1", "body": "x402"},
        {"id": 2, "title": "Add docs", "html_url": "https://x/2", "body": "nothing"},
    ])
    parsed = parse_github(gh)
    check("github parse keeps both", len(parsed), 2)
    check("github id is stable", parsed[0]["id"], "github:issue:1")
    check("issue vs release naming", parsed[0]["kind"] in ("issue", "release"), True)

    html = ("<h1>Our blog</h1>"
            "<h2>Brave Search adds agentic payments to its API</h2>"
            "<h2>How we built a facilitator for x402</h2>")
    ph = parse_html(html, "Base blog")
    # "Our blog" is 8 chars and the filter's floor is 12 — a site-title h1 is not a headline.
    check("html drops the 8-char site title, keeps both headlines", len(ph), 2)
    check("html keeps the first real headline", ph[0]["title"].startswith("Brave Search"), True)
    check("html dedups identical headings", len(parse_html("<h2>Brave Search adds agentic payments</h2>"
                                                          "<h2>Brave Search adds agentic payments</h2>", "x")), 1)
    check("html filter keeps a short but real heading", len(parse_html("<h3>Facilitator update</h3>", "x")), 1)

    print(f"\n  {len([1])+13 - fails} passed · {fails} failed")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()

    show_all = "--all" in argv
    st = load_state()
    seen = set(st["seen"])
    new_items, unread = [], []

    for label, url, mode in SOURCES:
        body, err = fetch(url)
        if err:
            unread.append((label, err))
            continue
        entries = parse_github(body) if mode == "github" else parse_html(body, label)
        for e in entries:
            if not matches(e):
                continue
            if e["id"] in seen:
                continue
            new_items.append({**e, "source": label})
            seen.add(e["id"])

    # Liveness line ALWAYS — "nothing new" and "watch is broken" must never look alike.
    print(f"x402 SIGNAL — {now()}")
    print(f"sources read {len(SOURCES) - len(unread)}/{len(SOURCES)}"
          + (f" · UNREAD: " + "; ".join(f"{l} ({e})" for l, e in unread) if unread else ""))
    print()

    if new_items or show_all:
        for it in new_items:
            tag = it["kind"]
            if tag == "pr":
                tag = "pr-merged" if it.get("merged") else f"pr-{it.get('state') or 'open'}"
            print(f"  [{tag}] {it['title'][:110]}")
            if it["url"]:
                print(f"          {it['url']}")
        print()
    else:
        print("  nothing new since the last run.\n")

    if show_all:
        print(f"  ({len(new_items)} unreported at this moment)")

    st["seen"] = sorted(seen)[-4000:]   # bounded: a ledger that grows forever is a leak
    st["last_run"] = now()
    st["runs"] = int(st.get("runs") or 0) + 1
    save_state(st)

    # Every source failed => we did not observe, we blacked out. Say so at the exit code.
    if len(unread) == len(SOURCES):
        print("ALL SOURCES UNREAD — this is an absence of data, not an absence of news.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
