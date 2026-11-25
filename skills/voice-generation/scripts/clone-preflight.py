#!/usr/bin/env python3
"""
clone-preflight.py — is a recording good enough to clone a voice from?

A clone inherits the room it was captured in, and no post-processing removes a constant: `loudnorm` only makes
the room louder. Measure the SOURCE before spending money on the clone.

WHAT IT MEASURES
  floor      mean amplitude of the quietest 10% of 20 ms frames — the room between phrases, not the voice
  peak       99th-percentile frame amplitude — how loud the loudest speech is
  SNR        peak/floor in dB — the single number that predicts "sounds like a fan/AC/hum"
  clip%      share of samples at full scale — irreversible, auto-REJECT
  dc         mean sample value — DC offset means a bad converter or mis-wired input, auto-REJECT
  silence    longest continuous quiet stretch — no natural pauses usually means one take with noise underneath

THRESHOLDS (stated so they can be argued with)
  SNR >= 45 dB GOOD · 35-45 MARGINAL (denoise, then re-measure) · < 35 REJECT (re-record)

USAGE
  clone-preflight.py recording.wav [more.wav ...]
  clone-preflight.py --dir /path/to/voice-samples

Exit 0 = nothing rejected · 2 = at least one REJECT · 3 = nothing to measure.
"""
from __future__ import annotations

import argparse
import array
import glob
import math
import os
import subprocess
import sys

FLOOR_PCT, PEAK_PCT = 0.10, 0.99
FRAME = 320           # 20 ms at 16 kHz
GOOD, MARGINAL = 45.0, 35.0


def pcm(path: str) -> array.array:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h")
    a.frombytes(raw)
    return a


def analyse(path: str) -> dict:
    a = pcm(path)
    if len(a) < 16000:                                  # under a second is not a sample
        return {"error": "shorter than 1 s"}
    n = len(a) // FRAME
    frames = [a[i * FRAME:(i + 1) * FRAME] for i in range(n)]
    energy = sorted(sum(abs(x) for x in f) / FRAME for f in frames)
    floor = energy[int(len(energy) * FLOOR_PCT)]
    peak = energy[int(len(energy) * PEAK_PCT)]
    snr = 20 * math.log10(max(peak, 1) / max(floor, 1e-9))
    clipped = sum(1 for x in a if abs(x) >= 32700) / len(a)
    dc = (sum(a) / len(a)) / 32768.0
    thr = max(floor * 3, 50)
    longest = run = 0
    for f in frames:
        if sum(abs(x) for x in f) / FRAME <= thr:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return {"seconds": len(a) / 16000, "floor": floor, "peak": peak, "snr": snr,
            "clipped": clipped, "dc": dc, "longest_pause": longest * FRAME / 16000}


def verdict(r: dict) -> tuple[str, str]:
    if "error" in r:
        return "REJECT", r["error"]
    if r["clipped"] > 0.001:
        return "REJECT", f"clipping {r['clipped']*100:.2f}% of samples — irreversible"
    if abs(r["dc"]) > 0.005:
        return "REJECT", f"DC offset {r['dc']:+.3f} — fix the capture chain"
    if r["snr"] >= GOOD:
        return "GOOD", "clone it"
    if r["snr"] >= MARGINAL:
        return "MARGINAL", "clone only after denoise, then re-measure"
    return "REJECT", f"SNR {r['snr']:.1f} dB — the room is louder than it should be; re-record"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", help="scan every audio file in this directory")
    a = ap.parse_args()
    files = list(a.files) or []
    if a.dir:
        for ext in ("*.wav", "*.mp3", "*.m4a", "*.flac", "*.ogg"):
            files += sorted(glob.glob(os.path.join(a.dir, ext)))
    if not files:
        print("  nothing to measure — pass files or --dir")
        return 3

    bad = 0
    print(f"  {'verdict':10} {'SNR':>6}  {'file':44} floor   peak   pause  notes")
    for f in files:
        r = analyse(f)
        v, why = verdict(r)
        if v == "REJECT":
            bad += 1
        if "error" in r:
            print(f"  {v:10} {'--':>6}  {os.path.basename(f)[:44]:44} {why}")
            continue
        print(f"  {v:10} {r['snr']:6.1f}  {os.path.basename(f)[:44]:44} "
              f"{r['floor']:5.0f} {r['peak']:6.0f} {r['longest_pause']:5.2f}s  {why}")
    print(f"\n  {len(files)} file(s) · {bad} reject · threshold: SNR >= {GOOD:.0f} dB to clone")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
