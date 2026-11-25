# Choosing a voice by measured noise floor

A synthesised voice carries whatever the source recording carried. For a **clone**, that includes the room: a fan,
a fridge, a laptop, traffic. The listener hears it as "cheap", and no post-processing removes it — a constant is
part of the signal, so normalising raises the voice and the hum together.

**Measure the floor before you build anything.** One sentence per candidate, identical settings, then score.

## The probe

```python
import subprocess, array, math

def snr_db(path):
    """Peak over the inter-phrase floor, in dB, from a decoded PCM stream."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw)
    frame = 320                      # 20 ms at 16 kHz
    n = len(a) // frame
    en = sorted(sum(abs(x) for x in a[i*frame:(i+1)*frame]) / frame for i in range(n))
    floor = en[int(len(en) * 0.10)]  # quietest tenth == the noise between phrases
    peak  = en[int(len(en) * 0.99)]
    return floor, peak, 20 * math.log10(max(peak, 1) / max(floor, 1e-9))
```

**Why the quietest tenth and not `volumedetect`'s `min_volume`:** `min_volume` is one sample and is dominated by
digital silence inside a synthesized pause. The 10th percentile of frame energy lands on the *residual* level in
pauses, which is what a listener hears as room tone.

**Synthesise with a long gap in the text** (`"Sentence one.          Sentence two."`) so the probe has real pauses
to measure — a continuous read leaves no inter-phrase floor to find, and every voice then scores the same.

## How to read the score

| SNR | verdict | use |
|---|---|---|
| ≥ 55 dB | clean | any scripted content |
| 45–55 dB | usable | fine for narration; a hair of texture |
| 35–45 dB | audible floor | acceptable only if the voice is irreplaceable |
| < 35 dB | unusable | the hum competes with the words; do not ship |

**Also compare raw peak level, not SNR alone.** A quiet voice can post a poor SNR purely for being quiet
(peak ~3,000 vs ~12,000 on the same sentence) — that is a gain problem, fixable, not a room problem.

## What the numbers imply about the catalogue

- **Pre-made / library voices are studio recordings** — they measure clean and cost the same.
- **Clones inherit their source.** A clone below ~35 dB is a clone of a bad capture, not a bad model.
- **Professional (marketplace) voices vary** — some are as noisy as a home recording.
- **One bad clone does not condemn the others**: on the account measured, 8 of 12 clones were below 35 dB while
the operator's own clone sat at 58.5 dB, i.e. clean.

## The fix, in order

1. **Swap the voice first.** Re-render the same script; nothing else changes if the script was already measured.
2. **Compare the FINISHED tracks, not the probes.** Re-run the same probe on the muxed MP4: one pair measured
   30.4 dB before and 51.5 dB after the swap, which is the only number that describes what a viewer hears.
3. **Only then consider the clone.** Retrain from a clean capture. Deleting the voice destroys the evidence of a
   bad recording without repairing it.
4. **Probe the source next time.** Two minutes on a test sentence beats a re-cut of a finished video.

## Making an A/B cheap

Take the voice id from an env var (`VOICE_ID`, `VOICE_NAME`) rather than a literal, so a second candidate is one
command and no code edit — and keep the frame timings derived from the *new* clip durations, never reused from the
first render.
