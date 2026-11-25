#!/usr/bin/env python3
"""
x402 PRESENCE CHECK — are we actually listed everywhere we should be?

READ-ONLY. Verifies our presence across every discovery surface we know of, and reports
DRIFT against a stored baseline rather than just restating the current state.

WHY THIS EXISTS (Jordan, 2026-10-30): "we need verification it's hitting everywhere we are
currently." The week produced four separate cases of a surface describing us wrongly — 10 of 14
services invisible in CDP's Bazaar, a listing we believed was live that was DELISTED, an
undercount on x402-list, and a registry entry that overstated PayAPI. Every one was found by
hand, late. This makes it automatic.

⚠️ THE RULE IT ENFORCES: absence from a list is a fact about the LIST until you control both
sides. A surface that drops us is news; a surface that never had us is a gap. Both are reported,
and they are reported differently.

EXIT CONTRACT (Hermes script-only cron — never use 1 for findings):
  0 + non-empty stdout -> delivered verbatim (news: drift detected, or a surface unreadable-but-noted)
  0 + empty stdout     -> silent tick (everything matches the baseline)
  2                    -> UNKNOWN: a REQUIRED surface could not be read. Never report "quiet"
                          when the instrument is blind — that is the failure this fleet keeps
                          re-learning.

BASELINE: profiles/gentech/state/x402-presence-baseline.json (NOT the gateway's logs/ dir — that is
root-owned and unwritable by uid 10000). First run writes it and SPEAKS (so the baseline is
visible in the log); later runs compare against it. Drops alarm; gains are reported as news and
become the new baseline.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request          # the chain read below needs it; without this the surface reported
                               # NameError and silently fell back to "unreadable" — which is exactly the
                               # kind of quiet failure this check exists to catch, in itself.

PAYTO = "0x7ebff188f2Eba16518C02864589b1403a5d1296a"
# ⚠️ NOT the gateway's logs/ dir: the container runs as ROOT, so
# 10-Labs/x402-gateway/logs/ is root-owned and uid 10000 cannot write there (measured
# 2026-10-30: PermissionError on the first run of this script). Reading traffic.jsonl from
# there still works — it is world-readable — but anything WE write lives in our own state dir.
BASE_DIR = "/opt/data/profiles/gentech/state"
BASELINE = os.path.join(BASE_DIR, "x402-presence-baseline.json")

# ⚠️ DECLARED WITHDRAWALS — routes we chose to stop selling, with the reason.
#
# WHY THIS EXISTS, measured 2026-11-19: `flow` was withheld from the gateway (native route, no
# `_flow_payload` handler — it issued a payable 402 and the call raised NameError → 500). Withholding it
# correctly removed it from every surface, and this job then reported two 🔴 DROPPED lines. Both were
# true and both were noise: the monitor counts APPEARANCES, so it cannot tell a deliberate withdrawal
# from a broken listing.
#
# The cost of leaving that alone is alarm fatigue: a nightly red for something we chose is how a reader
# learns to ignore the channel — the same failure as a dietician printing "NO RULE FIRED" twice a day.
# So a route we removed ON PURPOSE is declared here, and its absence is reported in the same breath as
# the count (a quiet, factual line) instead of as a 🔴 drop. A drop that is NOT declared still shouts.
#
# RULE: add an entry only when the withdrawal is intentional AND the reason is known. An unexplained
# drop must never be declared away — that would turn the alarm off precisely where it is needed.
DECLARED_WITHDRAWN = {
    "flow": "withheld 2026-11-19 — native route had no handler (_flow_payload); paid calls 500'd after settlement",
}

# Which SURFACES are expected to shrink when a route is withdrawn. Matching on a surface's prose
# `note` field does not work (measured: no note contains "flow"), so the expectation is declared
# against the surface key instead — explicit, greppable, and impossible to satisfy by accident.
WITHDRAWAL_AFFECTS_SURFACES = {"own_manifest", "own_mcp"}

# Every surface we expect to be on. `required` = if we cannot read it, the check is UNKNOWN.
SURFACES = [
    {
        "key": "cdp_bazaar", "name": "CDP Bazaar (merchant lookup)", "required": True,
        "url": f"https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo={PAYTO}&limit=50",
        "expect": "count>0", "note": "feeding CDP APIs + Bazaar MCP + Bedrock AgentCore + agentic.market",
    },
    {
        "key": "payai_bazaar", "name": "PayAI facilitator Bazaar", "required": True,
        "url": f"https://facilitator.payai.network/discovery/resources?payTo={PAYTO}",
        "expect": "count>0", "note": "the facilitator our settles go through",
    },
    {
        "key": "x402_list", "name": "x402-list.com", "required": True,
        "url": "https://x402-list.com/api/v1/services?q=gentech",
        "expect": "count>0", "note": "grades us; currently undercounts endpoints",
    },
    {
        "key": "payapi_market", "name": "payapi.market", "required": False,
        "url": "https://payapi.market/api/agent/search?q=gentech",
        "expect": "any", "note": "KNOWN DELISTED — a non-zero count here is news, not a failure",
    },
    {
        "key": "own_manifest", "name": "our /.well-known/x402-bazaar", "required": True,
        "url": "https://api.gentechlabs.net/.well-known/x402-bazaar",
        "expect": "services", "note": "the surface WE control — must always name our services",
    },
    {
        "key": "first_customer", "name": "first CUSTOMER settlement", "required": False,
        "kind": "local", "expect": "any",
        "note": ("the one number no catalogue can give us. Counts settled payments whose PAYER is not one of "
                 "our own wallets — resolved from the CHAIN, because the gateway log carries `tx` but no "
                 "payer. required=False on purpose: being at 0 is not a defect, it is the truth."),
    },
    {
        "key": "own_mcp", "name": "our /mcp tool list", "required": True,
        "url": "https://api.gentechlabs.net/mcp", "method": "POST",
        "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        "expect": "tools", "note": "MCP tools are separately indexable in the Bazaar",
    },
]


def fetch(spec: dict, timeout: int = 30) -> tuple[object, str | None]:
    """Returns (parsed_or_None, error)."""
    cmd = ["curl", "-sL", "--max-time", str(timeout),
             "-H", "User-Agent: gentech-cron/1.0 (+https://gentechlabs.net)"]
    if spec.get("method") == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/json",
                "-H", "Accept: application/json", "-d", json.dumps(spec["body"])]
    cmd.append(spec["url"])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10).stdout
        return json.loads(out), None
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:80]}"


# Our own wallets. A payment FROM any of these proves the path works; it is NOT a customer.
SELF_WALLETS = {
    "0x6021ec630e031dbf60d2e96b76b76be2dec899f1",   # buyer/settle-test
}
# The gateway writes its logs next to its OWN server.py (`_TRAFFIC_DIR = dirname(__file__)/logs`).
# ⚠️ MEASURED 2026-11-15: I moved a copy out of the vault to save sync quota, then read THAT copy and
# concluded the log was frozen — while the container had recreated the directory in the vault and was
# writing there. The first sale of the company was invisible to the watcher built to find it. Read the
# path the WRITER uses; fall back only if it is absent.
PAYLOGS = [
    "/opt/data/.obsidian-vault/10-Labs/x402-gateway/logs/payments.jsonl",
    "/opt/data/x402-gateway-logs/payments.jsonl",
]
_RPC = "https://mainnet.base.org"
_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"   # USDC on Base (the address our 402 advertises, verified)


def _chain_payer(tx: str) -> str | None:
    """tx hash -> the address that sent the USDC. The CHAIN is the authority on who paid."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt",
                       "params": [tx]}).encode()
    req = urllib.request.Request(_RPC, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "presence"})
    try:
        rc = json.load(urllib.request.urlopen(req, timeout=20)).get("result")
    except Exception:
        return None
    if not rc:
        return None
    for lg in rc.get("logs", []):
        if lg.get("address", "").lower() == _USDC.lower() and lg["topics"][0].startswith("0xddf252ad"):
            return ("0x" + lg["topics"][1][-40:]).lower()
    return None


LOCAL = {"first_customer": lambda: measure_customers()}


def measure_customers() -> dict:
    """Settled payments whose payer is NOT us. 0 is a legitimate answer and must read as 0, not as 'unknown'."""
    path = next((p for p in PAYLOGS if os.path.exists(p)), None)
    if not path:
        return {"ok": False, "error": "no payments log found — customer count is UNKNOWN, not zero"}
    settled = []
    try:
        for line in open(path, errors="ignore"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("ok") is True and d.get("tx"):
                settled.append(d["tx"])
    except Exception as e:
        return {"ok": False, "error": f"log unreadable: {type(e).__name__}"}
    settled = settled[-40:]                       # bounded: this runs on a schedule, not as an indexer
    payers = {}
    for tx in settled:
        payers[tx] = _chain_payer(tx)
    self_n = sum(1 for v in payers.values() if v in SELF_WALLETS)
    cust = {t: v for t, v in payers.items() if v and v not in SELF_WALLETS}
    unres = [t for t, v in payers.items() if v is None]
    return {"ok": True, "count": len(cust), "self_settlements": self_n,
            "unresolved": len(unres),
            "note": (f"{len(cust)} customer · {self_n} our own · {len(unres)} unresolved"
                     if settled else "no settled payments recorded")}


def measure(spec: dict) -> dict:
    """Extract the comparable figure from a surface's response."""
    # Local surfaces have no URL to fetch — they read our own state. Dispatch BEFORE fetch(), or a surface
    # that is not an HTTP endpoint raises KeyError('url') and takes the whole check down with it.
    if spec.get("kind") == "local":
        try:
            return LOCAL.get(spec["key"], lambda: {"ok": False, "error": "no local extractor"})()
        except Exception as e:
            return {"ok": False, "error": f"local: {type(e).__name__}: {str(e)[:70]}"}
    d, err = fetch(spec)
    if err or d is None:
        return {"ok": False, "error": err or "unparseable"}
    try:
        k = spec["key"]
        if k in ("cdp_bazaar", "payai_bazaar"):
            items = d.get("items") or d.get("resources") or []
            ours = [i for i in items if PAYTO.lower() in json.dumps(i).lower()]
            return {"ok": True, "count": len(ours)}
        if k == "x402_list":
            x = (d.get("data") or [{}])[0] if isinstance(d.get("data"), list) else {}
            return {"ok": True, "count": 1 if x else 0,
                    "status": x.get("status"), "endpoints": x.get("endpoint_count"),
                    "verified": x.get("verified")}
        if k == "payapi_market":
            return {"ok": True, "count": int(d.get("count") or 0), "searched": d.get("searched")}
        if k == "own_manifest":
            svcs = d.get("services") or {}
            return {"ok": True, "count": len(svcs) if isinstance(svcs, (list, dict)) else 0}
        if k == "first_customer":
            return measure_customers()
        if k == "own_mcp":
            tools = ((d.get("result") or {}).get("tools")) or []
            return {"ok": True, "count": len(tools)}
    except Exception as e:
        return {"ok": False, "error": f"parse: {type(e).__name__}: {str(e)[:70]}"}
    return {"ok": False, "error": "no extractor"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true",
                    help="also print the standing state when nothing changed (silence is the DEFAULT, "
                         "because this runs as a cron: 0 + empty stdout = silent tick)")
    ap.add_argument("--reset-baseline", action="store_true")
    args = ap.parse_args()

    os.makedirs(BASE_DIR, exist_ok=True)
    prev = {}
    if os.path.exists(BASELINE) and not args.reset_baseline:
        try:
            prev = json.load(open(BASELINE))
        except Exception:
            prev = {}

    now = {"at": int(time.time()), "surfaces": {}}
    blind = []
    news = []

    for spec in SURFACES:
        m = measure(spec)
        now["surfaces"][spec["key"]] = m
        if not m.get("ok"):
            if spec["required"]:
                blind.append(f"{spec['name']} — {m.get('error')}")
            else:
                news.append(f"⏭ {spec['name']}: unreadable ({m.get('error')}) — not required")
            continue
        p = (prev.get("surfaces") or {}).get(spec["key"])
        if p is None:
            # first sighting of this surface — say where we stand, do not call it drift
            extra = ""
            if spec["key"] == "x402_list":
                extra = f" · status={m.get('status')} · endpoints={m.get('endpoints')}"
            news.append(f"• {spec['name']}: {m['count']}{extra}  (first measurement)")
            continue
        if m["count"] < (p.get("count") or 0):
            # A drop inside a declared withdrawal is EXPECTED. Name the route and the reason so the
            # reader can still audit it, but do not raise an alarm we already answered by hand —
            # an alarm that fires for chosen behaviour teaches the reader to ignore the channel.
            lost = (p.get("count") or 0) - m["count"]
            if spec["key"] in WITHDRAWAL_AFFECTS_SURFACES and lost <= len(DECLARED_WITHDRAWN):
                for r, why in DECLARED_WITHDRAWN.items():
                    news.append(f"⏸ {spec['name']}: {r} withdrawn by policy "
                                f"({p.get('count')} → {m['count']}) — {why}")
            else:
                news.append(f"🔴 {spec['name']}: DROPPED {p.get('count')} → {m['count']}  ← was listed, now is not")
        elif m["count"] > (p.get("count") or 0):
            news.append(f"🟢 {spec['name']}: GREW {p.get('count')} → {m['count']}")
        if spec["key"] == "x402_list" and m.get("status") != p.get("status"):
            news.append(f"⚠️ {spec['name']}: status {p.get('status')} → {m.get('status')}")

    # A required surface we cannot read is UNKNOWN, never "quiet".
    if blind:
        print("⚠️ x402 presence UNKNOWN — a required surface could not be read:")
        for b in blind:
            print(f"   • {b}")
        print("   Not reporting 'all present': a blind check is not a clean one.")
        json.dump(now, open(BASELINE, "w"), indent=1)
        return 2

    json.dump(now, open(BASELINE, "w"), indent=1)

    if not news:
        if not args.verbose:
            return 0        # silent tick — the cron contract's "quiet" path
        total = sum((now["surfaces"].get(s["key"]) or {}).get("count", 0) for s in SURFACES)
        print(f"📡 x402 presence — no change ({len(SURFACES)} surfaces, {total} entries total)")
        return 0

    print(f"📡 x402 presence — {len(news)} change(s) · {time.strftime('%Y-%m-%d %H:%MZ', time.gmtime())}")
    for n in news:
        print(f"   {n}")
    for s in SURFACES:
        m = now["surfaces"].get(s["key"]) or {}
        if m.get("ok"):
            extra = ""
            if s["key"] == "x402_list":
                extra = f" · status={m.get('status')} · endpoints={m.get('endpoints')}"
            print(f"   from: {s['name']:34s} {m['count']}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
