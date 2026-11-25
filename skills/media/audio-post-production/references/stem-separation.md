# Stem separation — audio-separator over htdemucs / BS-RoFormer / Spleeter

Depth for the separation leg. Load it when a **mixed** track has to be broken into vocals and instrumental
before tuning, converting or re-mixing. One CLI (`audio-separator`) wraps all three model families.

## Install and run (works on CPU, measured)

```bash
# once, into a PERSISTENT venv (see the venv section of SKILL.md — never cache/scratch, which is pruned)
/opt/data/bin/uv pip install --python <venv>/bin/python "audio-separator[cpu]"

# run: output names are <track>_(Vocals|Drums|Bass|Other)_htdemucs.flac, written to the CWD
cd <workdir> && <venv>/bin/audio-separator input.mp3 -m htdemucs.yaml
```

**Measured on 4 vCPU / no GPU:** a 91.6 s stereo song separated in **5 min 50 s** — about 3.8× slower than
realtime, comfortably better than the 10–15 min/track that CPU benchmarks usually quote. Four full-length
stems; vocals typically around −21 dB RMS on a vocal-forward track.

## Always verify the stems are real before using them

A silent **Other** stem is normal. A silent **Vocals** stem means separation failed and everything downstream
is worthless — so check, rather than discovering it after a 40-minute conversion.

```bash
for f in *_htdemucs.flac; do printf "%-45s " "$f";
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" | tr -d '\n'
  ffmpeg -hide_banner -i "$f" -af astats=metadata=1:reset=0 -f null - 2>&1 \
    | grep -m1 "RMS level dB" | awk '{print "  RMS",$NF,"dB"}'
done
```

## Model choice

| Model | Avg SDR (MUSDB18-HQ) | Use it when |
|---|---|---|
| **htdemucs** (Demucs v4) | ~9.0 dB | **default** — the production choice on CPU |
| **BS-RoFormer** | 9.80 dB | quality matters more than time; slower, memory-hungry, weights scattered across community releases |
| **Spleeter** | ~5.9 dB (vocals) | only on very weak hardware where speed is everything — "watery" vocals |

## Feeding a separation into a pitch/timbre tool

Use the **Vocals** stem, convert to 44.1 kHz mono WAV, and take the loudest window if you trim. A converted or
re-mixed result must be laid back over the same instrumental stem, otherwise the timing will not line up —
see `fit_vocal.py` in SKILL.md for the alignment step.
