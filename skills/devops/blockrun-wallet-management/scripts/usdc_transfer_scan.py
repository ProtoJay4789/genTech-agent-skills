#!/usr/bin/env python3
"""usdc_transfer_scan.py — USDC Transfer history for one address on Base, with RPC fallback.

Answers: is this wallet LIVE (has it paid?), is the balance explained, and when did the money move.
Chunks at 900 blocks because a provider cut eth_getLogs from 2,000 to 1,000 — a 1,999 span errors on
EVERY chunk with -32614, which reads as "no transfers" if the error is swallowed.

Usage:  usdc_transfer_scan.py <0xaddress> [blocks=1200]
Never prints key material; takes a public address only.
"""
import datetime
import json
import subprocess
import sys

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RPCS = ["https://mainnet.base.org", "https://base.llamarpc.com",
        "https://base-rpc.publicnode.com", "https://1rpc.io/base", "https://base.drpc.org"]
CHUNK = 900


def rpc(payload):
    body = json.dumps(payload)
    for url in RPCS:
        p = subprocess.run(["curl", "-s", "--max-time", "25", "-H", "Content-Type: application/json",
                            "-d", body, url], capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
        except Exception:
            continue
        if "result" in d:
            return d["result"]
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    addr = sys.argv[1]
    blocks = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    pad = "0x" + "0" * 24 + addr[2:].lower()

    head = rpc({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1})
    if head is None:
        print("UNMEASURED: no RPC answered (an unreadable chain is not an empty wallet)")
        return 2
    head = int(head, 16)
    start = max(0, head - blocks)

    rows = []
    cur = start
    while cur <= head:
        end = min(cur + CHUNK - 1, head)
        for direction, topics in (("OUT", [TRANSFER, pad]), ("IN", [TRANSFER, None, pad])):
            logs = rpc({"jsonrpc": "2.0", "method": "eth_getLogs", "params": [{
                "address": USDC, "fromBlock": hex(cur), "toBlock": hex(end), "topics": topics}], "id": 1})
            if logs is None:
                print(f"  WARNING chunk {cur}..{end} {direction}: RPC failed — result incomplete, not zero")
                continue
            for lg in logs:
                rows.append({
                    "dir": direction,
                    "usdc": int(lg["data"], 16) / 1e6,
                    "other": "0x" + (lg["topics"][2] if direction == "OUT" else lg["topics"][1])[-40:],
                    "block": int(lg["blockNumber"], 16),
                    "tx": lg["transactionHash"],
                })
        cur = end + 1

    stamps = {}
    for b in sorted({r["block"] for r in rows}):
        blk = rpc({"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [hex(b), False], "id": 1})
        if blk:
            stamps[b] = int(blk["timestamp"], 16)

    rows.sort(key=lambda r: r["block"])
    print(f"USDC transfers touching {addr} in blocks {start}..{head}: {len(rows)}")
    for r in rows:
        t = datetime.datetime.fromtimestamp(stamps.get(r["block"], 0), datetime.UTC).strftime("%Y-%m-%d %H:%M:%SZ")
        print(f"  {t}  {r['dir']:3s} {r['usdc']:.6f}  other={r['other']}  tx={r['tx'][:18]}…")

    out_total = sum(r["usdc"] for r in rows if r["dir"] == "OUT")
    in_total = sum(r["usdc"] for r in rows if r["dir"] == "IN")
    print(f"\nOUT {out_total:.6f}  IN {in_total:.6f}  net {in_total - out_total:+.6f}")
    print("CHECK: this net must equal the current balance minus whatever moved before this window.")
    print("       If it does not close, you are looking at the wrong address or a second token.")
    print("       Any OUT entry proves the wallet is live; a wallet that only receives is the stranded candidate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
