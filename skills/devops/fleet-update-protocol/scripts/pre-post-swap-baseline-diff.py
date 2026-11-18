#!/usr/bin/env python3
"""
pre-post-swap-baseline-diff.py — capture a host's shape BEFORE a change, diff it AFTER.

  --capture   record the baseline (run BEFORE the swap, while the old box is still up)
  --diff      re-probe and print, per check, whether anything moved

Read-only probes + one JSON file. Never writes to live state.

WHY THIS IS A SCRIPT AND NOT A CHECKLIST: a post-change check with no pre-change reference
proves nothing — "here is what it looks like now" cannot distinguish drift from intended
migration. And the pitfall it was built around: volatile fields (uptime, durations, ages)
drift between ANY two reads, so comparing them raw reports "changed" on every run, and a
check that is red when nothing happened trains the reader to skip it.

Adjust PROBE() for the host you are on; the capture/diff/normalise skeleton is the reusable
part. Env overrides: BASELINE_JSON, HERMES, S6.
"""
import argparse, hashlib, json, os, pathlib, re, subprocess, sys, glob

BASE = pathlib.Path(os.environ.get("BASELINE_JSON", "/opt/data/backups/pre-swap-baseline.json"))
HERMES = os.environ.get("HERMES", "/opt/hermes/.venv/bin/hermes")
S6 = os.environ.get("S6", "/package/admin/s6/command")


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception as e:                                   # noqa: BLE001
        return f"(probe failed: {e.__class__.__name__})"


def fingerprint(p):
    """Hash a file so a config edit shows as a changed digest, not a diff dump."""
    try:
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]
    except Exception:                                        # noqa: BLE001
        return "(absent)"


VOLATILE = re.compile(r"\s+\d+\s+seconds?\s*$")     # the drift this script exists to neutralise


def probe():
    st = {}
    st["version"] = sh(f"{HERMES} --version 2>&1 | head -1")

    # LAYOUT + per-slot STATE. Normalise the drifting uptime off the state string: compare
    # state + pid, keep the raw value separately for the human.
    slots, raw = {}, {}
    for d in sorted(glob.glob("/run/service/*/")):
        name = os.path.basename(d.rstrip("/"))
        line = sh(f"{S6}/s6-svstat {d} 2>/dev/null")
        slots[name] = VOLATILE.sub("", line).strip() or "(unreadable)"
        raw[name] = line or "(unreadable)"
    st["slots"], st["raw_uptimes"] = slots, raw
    st["slot_names"] = sorted(slots.keys())

    # PROCESS IDENTITY — an unchanged pid after a swap means the swap did not take effect,
    # however green everything else looks.
    pidfile = pathlib.Path("/opt/data/gateway.pid")
    st["gateway_pid"] = pidfile.read_text().strip() if pidfile.exists() else "(absent)"

    # LISTENING SURFACES — a change here is a regression, not a feature.
    st["listening"] = sorted({l.split()[3].rsplit(":", 1)[-1]
                              for l in sh("cat /proc/net/tcp /proc/net/tcp6 2>/dev/null").splitlines()[1:]
                              if l.split()[3].endswith("0A")})

    # COUNTS
    st["agent_logs"] = len(glob.glob("/opt/data/profiles/*/logs/agent.log"))
    st["skill_dirs"] = len(glob.glob("/opt/data/skills/*/"))

    # THE MOUNT PROOF: persistent state must sit on its own mount, not on the layer a recreate
    # replaces. Without it, "our data survived" is a claim, not a measurement.
    st["mount"] = sh("findmnt -no SOURCE,FSTYPE /opt/data 2>/dev/null") or sh("grep ' /opt/data ' /proc/mounts")
    st["root_fs"] = sh("findmnt -no FSTYPE / 2>/dev/null") or "(unknown)"

    st["fingerprints"] = {p: fingerprint(p) for p in
                          ("/opt/data/config.yaml", "/opt/hermes/docker-compose.yml")}
    return st


def diff(old, new):
    lines, flags = [], []

    def chk(tag, a, b, ok, bad, expect_change=False):
        if a == b:
            lines.append(f"  [{tag:<16}] {bad if expect_change else ok}")
            if expect_change:                       # unchanged where change was EXPECTED = alarm
                flags.append(tag)
        else:
            lines.append(f"  [{tag:<16}] {bad}\n      was: {a}\n      now: {b}")
            if not expect_change:
                flags.append(tag)

    # version + pid are EXPECTED to move across a swap — an unchanged one is the alarm.
    chk("ENGINE", old["version"], new["version"],
        f"{new['version']}  ⚠️ UNCHANGED — did the swap actually happen?",
        f"{old['version']} → {new['version']}", expect_change=True)
    chk("GATEWAY PID", old["gateway_pid"], new["gateway_pid"],
        "UNCHANGED — the gateway may not have restarted",
        f"{old['gateway_pid']} → {new['gateway_pid']}", expect_change=True)

    # layout: a mismatch is a FINDING, not automatically a fault — topology changes are
    # sometimes the POINT of the upgrade. Report it; let the human classify it.
    if old["slot_names"] == new["slot_names"]:
        lines.append(f"  [SERVICE LAYOUT ] identical ({len(old['slot_names'])} slots)")
    else:
        added = sorted(set(new["slot_names"]) - set(old["slot_names"]))
        gone = sorted(set(old["slot_names"]) - set(new["slot_names"]))
        lines.append(f"  [SERVICE LAYOUT ] CHANGED — +{added} −{gone}")
        flags.append("SERVICE LAYOUT")

    moved = [n for n in sorted(set(old["slots"]) & set(new["slots"]))
             if old["slots"][n] != new["slots"][n]]
    for n in moved:
        lines.append(f"  [SLOT STATE     ] {n}: {old['slots'][n]} → {new['slots'][n]}")
        flags.append("SLOT STATE")
    if not moved:
        lines.append("  [SLOT STATE     ] all states unchanged ✅  (uptime drift excluded by design)")

    # surfaces must MATCH — a change here is a regression.
    chk("PORTS", old["listening"], new["listening"], f"{new['listening']} ✅", "no longer listening")
    chk("SKILL DIRS", old["skill_dirs"], new["skill_dirs"], f"{new['skill_dirs']} ✅", "count changed")
    chk("AGENT LOGS", old["agent_logs"], new["agent_logs"], f"{new['agent_logs']} ✅", "count changed")

    same = old["mount"] == new["mount"]
    lines.append(f"  [STATE MOUNT    ] /opt/data {'unchanged' if same else 'CHANGED'} "
                 f"{new['mount']}  (root fs: {new['root_fs']})")
    if not same:
        flags.append("STATE MOUNT")

    return lines, flags


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--diff", action="store_true")
    a = ap.parse_args()

    if a.capture:
        st = probe()
        BASE.parent.mkdir(parents=True, exist_ok=True)
        BASE.write_text(json.dumps(st, indent=2))
        print(f"  baseline captured → {BASE}\n    version     : {st['version']}")
        print(f"    slots       : {len(st['slot_names'])}")
        print(f"    gateway pid : {st['gateway_pid']}")
        print(f"    listening   : {st['listening']}")
        print(f"    /opt/data   : {st['mount']}")
        sys.exit(0)

    if not BASE.exists():
        print("  no baseline — run --capture BEFORE the change, not after")
        sys.exit(1)

    old, new = json.loads(BASE.read_text()), probe()
    print("════════ POST-SWAP AUDIT — did anything of OURS move? ════════")
    lines, flags = diff(old, new)
    print("\n".join(lines))
    print(f"\n  {len(lines)} checks · {len(flags)} needing a read")
    sys.exit(0)
