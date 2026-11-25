#!/usr/bin/env python3
"""Sweep Seed-VC singing conversion over diffusion steps x inference-cfg-rate and score each run.

WHY THIS EXISTS
    A likeness score is easy to report from a run outside the model's documented quality range, and
    that turns a settings choice into a fake ceiling. This makes the sweep one command and produces
    numbers directly comparable to the earlier baseline.

MEASURED CONSTRAINTS BAKED IN (do not "simplify" these away)
  * inference.py accepts ONLY --inference-cfg-rate on the SVC path. --similarity-cfg-rate and
    --intelligibility-cfg-rate belong to inference_v2.py, a DIFFERENT model (22.05 kHz voice/accent
    conversion, hubert-bsqvae-small). Passing them here is an argument error.
  * inference.py slices the reference to ref_audio[:sr*25] -> only the first 25 s are used.
  * inference.py wants an INT for --semi-tone-shift. Passing -9.0 fails with
    "invalid int value: '-9.0'", so whole numbers are formatted as integers here.
  * PITCH COMES FROM THE SOURCE, NOT THE REFERENCE. --f0-condition True keeps the source melody's
    register and borrows only timbre from the reference, so a low-register reference cannot pull a
    high melody down. To hear the person in the register they actually sang, shift the SOURCE:
    12*log2(ref_median_f0 / source_median_f0). Measured: a 126 Hz sung reference against a 223 Hz
    source needed -9 st, which moved the output from 208.9 Hz to 131.6 Hz (91.2% below 160 Hz vs the
    reference's 91.1%) and held melody contour at 0.956.
  * Seed-VC writes the output file only once, at the very end, so a timeout that fires mid-run leaves
    NOTHING on disk. Leave generous headroom per cell.
  * RUNTIME IS OVERHEAD-DOMINATED, NOT LINEAR IN STEPS. Measured: 4 steps took 679 s on a 20 s clip
    while a 12-step run of the same pair finished faster. Do NOT budget ~23 s * steps * chunks -- time
    one short run on an idle box and multiply by CELLS, not by an assumed per-step figure.
  * THERE IS A STEP FLOOR. Measured on one pair with one scorer: unconverted source 0.6493, 4 steps
    0.6242 (BELOW the source -- the conversion damaged identity), 12 steps 0.7022. The README's "4-10
    for fastest inference" is a LATENCY band, not a cheap quality band. Hence the MIN_STEPS guard.
  * f0-condition MUST be True for singing, and auto-f0-adjust MUST be False (it drifts on sung audio).
  * Always score with resemblyzer cosine vs the reference. A score is only comparable to a baseline
    measured on the SAME reference file: one speaker's sung vs spoken reference differs by ~0.07, so
    re-score the OLD artefact with this same function (--score-only) before calling a new number
    better or worse, and never carry a baseline across references.
  * A PITCH-SHIFTED OUTPUT BREAKS fit_vocal.py's xcorr alignment (corr drops ~0.195 -> 0.080 and it
    returns a confident nonsense offset). Not this script's job, but do not mix a shifted vocal with
    an xcorr-aligned one and assume the placement is right.

USAGE
    export SEEDVC=/opt/data/profiles/<seat>/tools/seed-vc
    export SVC_PY=/opt/data/profiles/<seat>/venvs/svc/bin/python
    $SVC_PY svc_sweep.py --source melody_vocal.wav --reference sung_25s.wav \
        --steps 12,35,40 --cfg 0.7,1.0,1.3

    Put the person in their own register:
    $SVC_PY svc_sweep.py --source melody_vocal.wav --reference sung_25s.wav \
        --steps 12 --semi-tone-shift -9

    Prove the harness on a CONFIG YOU WILL KEEP (>=12 steps) against a 20-30 s excerpt -- cutting the
    step count to save time measures a broken setting, not a cheap version of a good one. Then run the
    real grid in the background with notify. Do not sit on it in the foreground.
"""
import argparse
import json
import os
import subprocess
import sys
import time

SEEDVC = os.environ.get("SEEDVC", "")
PY = os.environ.get("SVC_PY", sys.executable)
MIN_STEPS = 12

def _snapshot(*names):
    """Resolve a checkpoint/config inside the HF snapshot dir (the hash dir varies per download)."""
    base = os.path.join(SEEDVC, "checkpoints", "models--Plachta--Seed-VC", "snapshots")
    for hashdir in sorted(os.listdir(base)):
        for n in names:
            p = os.path.join(base, hashdir, n)
            if os.path.exists(p):
                return p
    raise SystemExit(f"could not find {names} under {base}")

CKPT = _snapshot("DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth") if SEEDVC else ""
CFG = _snapshot("config_dit_mel_seed_uvit_whisper_base_f0_44k.yml") if SEEDVC else ""


def _intish(x):
    """inference.py parses --semi-tone-shift as int; '-9.0' is rejected outright."""
    f = float(x)
    return str(int(f)) if f.is_integer() else str(f)


def score(converted, reference):
    """Speaker similarity, same metric as the recorded baseline."""
    import numpy as np
    from resemblyzer import VoiceEncoder, preprocess_wav

    enc = VoiceEncoder("cpu")
    a = enc.embed_utterance(preprocess_wav(reference))
    b = enc.embed_utterance(preprocess_wav(converted))
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def convert(source, target, outdir, steps, cfg_rate, timeout_s, semi_tone=0.0):
    os.makedirs(outdir, exist_ok=True)
    before = {f for f in os.listdir(outdir) if f.endswith(".wav")}
    cmd = [PY, "inference.py", "--source", source, "--target", target, "--output", outdir,
           "--diffusion-steps", str(steps), "--inference-cfg-rate", str(cfg_rate),
           "--f0-condition", "True", "--auto-f0-adjust", "False",
           "--semi-tone-shift", _intish(semi_tone),
           "--fp16", "False", "--checkpoint", CKPT, "--config", CFG]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=SEEDVC, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        # The job leaves nothing behind; do not report this as a score of zero.
        return None, time.time() - t0, "TIMEOUT (no output written by design)"
    elapsed = time.time() - t0
    if p.returncode != 0:
        tail = (p.stderr or "").strip().splitlines()
        return None, elapsed, f"FAIL rc={p.returncode}: {tail[-1][:200] if tail else 'no stderr'}"
    new = [f for f in os.listdir(outdir) if f.endswith(".wav") and f not in before]
    if not new:
        return None, elapsed, "rc=0 but no new wav — verify the artefact, the exit code lies"
    return os.path.join(outdir, max(new, key=lambda f: os.path.getmtime(os.path.join(outdir, f)))), elapsed, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="isolated melody/vocal to convert")
    ap.add_argument("--reference", required=True, help="target voice; ONLY the first 25 s are used")
    ap.add_argument("--outdir", default="./svc_sweep")
    ap.add_argument("--steps", default="35,40", help="comma-separated diffusion steps (30-50 for singing)")
    ap.add_argument("--cfg", default="0.7,1.0,1.3", help="comma-separated --inference-cfg-rate values")
    ap.add_argument("--semi-tone-shift", type=float, default=0.0,
                    help="shift the SOURCE melody by N semitones before conversion (negative = lower). Use "
                         "when the melody sits outside the reference's register: f0-condition keeps the "
                         "SOURCE pitch, so this is the only way to hear the person in the register they "
                         "actually sang. Compute it as 12*log2(ref_median / source_median).")
    ap.add_argument("--baseline", type=float, default=None,
                    help="prior score to compare against. It MUST have been measured on THIS SAME --reference "
                         "file: one speaker's sung and spoken references differ by ~0.07, so a carried-over "
                         "baseline prints a delta that is the scorer, not the model. Leave unset and prove "
                         "the baseline with --score-only instead.")
    ap.add_argument("--timeout", type=int, default=2400, help="per-run cap; Seed-VC writes nothing on timeout")
    ap.add_argument("--allow-low-steps", action="store_true",
                    help="permit <12 steps (measured to score BELOW the unconverted source) — floor re-benchmark only")
    ap.add_argument("--score-only", metavar="WAV",
                    help="skip conversion; just score an existing wav against --reference (use to prove baseline reproducibility)")
    args = ap.parse_args()

    # Prove the metric before comparing anything to it.
    if args.score_only:
        print(json.dumps({"wav": args.score_only,
                          "similarity": round(score(args.score_only, args.reference), 4)}))
        return 0

    if not SEEDVC:
        raise SystemExit("set SEEDVC to the seed-vc checkout")

    steps_list = [int(s) for s in args.steps.split(",")]
    if min(steps_list) < MIN_STEPS and not args.allow_low_steps:
        raise SystemExit(
            f"REFUSED: steps {min(steps_list)} < {MIN_STEPS}. Measured: 4 steps = 0.6242 vs an unconverted "
            f"source of 0.6493 — below the floor the conversion makes the take LESS like the person. "
            f"Cut the excerpt duration instead of the steps, or pass --allow-low-steps to re-benchmark the floor."
        )

    results = []
    for steps in steps_list:
        for cfg in (float(c) for c in args.cfg.split(",")):
            st = args.semi_tone_shift
            tag = f"steps{steps}_cfg{cfg}" + (f"_st{st:+g}" if st else "")
            print(f"\n=== {tag} ===", flush=True)
            wav, secs, status = convert(args.source, args.reference,
                                        os.path.join(args.outdir, tag), steps, cfg, args.timeout,
                                        semi_tone=st)
            row = {"tag": tag, "steps": steps, "cfg_rate": cfg, "semi_tone_shift": st,
                   "seconds": round(secs, 1), "status": status}
            if wav:
                try:
                    row["similarity"] = round(score(wav, args.reference), 4)
                except Exception as e:  # noqa: BLE001 - a scoring failure is a result, not a crash
                    row["score_error"] = str(e)[:200]
                row["wav"] = wav
            results.append(row)
            print(json.dumps(row), flush=True)
            # Write after EVERY run so a later timeout cannot erase the earlier numbers.
            with open(os.path.join(args.outdir, "sweep-results.json"), "w") as f:
                json.dump(results, f, indent=2)

    scored = [r for r in results if r.get("similarity")]
    if not scored:
        print("no scored runs — read the statuses above; do not report a ceiling")
        return 1
    best = max(scored, key=lambda r: r["similarity"])
    if args.baseline is None:
        print(f"\nbest: {best['tag']} -> {best['similarity']}  (no --baseline given: score the old artefact "
              f"with --score-only against THIS same reference before claiming an improvement)")
    else:
        print(f"\nbest: {best['tag']} -> {best['similarity']} (baseline {args.baseline}, "
              f"delta {best['similarity'] - args.baseline:+.3f})")
    if best["similarity"] < 0.75:
        print("below the 0.75-0.85 same-speaker band quoted for *speech* corpora; against a sung reference "
              "do not restate that band as the target -- a trained model remains the lever for likeness")
    return 0


if __name__ == "__main__":
    sys.exit(main())
