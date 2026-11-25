# Singing voice conversion on CPU — measured state and install recipe

Depth for the SVC leg of the pipeline. Install, runtime cost and first measured output quality are below.

## Why SVC, not TTS

TTS synthesises speech from text. SVC **rewrites the timbre of a melody that already exists** — notes in,
notes out, different voice. There is no prompt that makes a speech model sing, and style/expressiveness
settings move speech emphasis, not pitch (measured: raising `style` made a clone *flatter*).

Therefore the order is fixed: **generate the melody first, convert the timbre second.** Never the reverse.

## Candidates, ranked for a no-GPU host

| Project | Why / why not |
|---|---|
| **Seed-VC** (`Plachtaa/seed-vc`) | Zero-shot — converts from a ~20 s reference, **no per-voice training**. The only viable route without a GPU |
| **RVC** (`RVC-Project/Retrieval-based-Voice-Conversion-WebUI`) | Best-known consumer tool, but it *trains* — not possible on CPU |
| **so-vits-svc** (`svc-develop-team/so-vits-svc`) | Singing specialist, proven, stale since 2023 |
| **Applio** (`IAHispano/Applio`) | Friendlier RVC packaging, actively maintained |

If zero-shot quality disappoints *at the recommended settings*, the upgrade is **one rented GPU hour to train
RVC**, then CPU inference forever after. Training is the batch job; inference is cheap. That is the honest
fallback — but it comes **after** the free parameter sweep and a sung reference, not instead of them.

## Install (proven)

```bash
# 1. Clone — it is NOT a pip-installable project (no pyproject.toml / setup.py)
git clone --depth 1 https://github.com/Plachtaa/seed-vc.git /opt/data/profiles/<seat>/tools/seed-vc

# 2. Separate venv, CPU torch. DO NOT install its requirements.txt:
#    it pins torch nightly + cu126, which is wrong for a CPU box and huge.
/opt/data/bin/uv venv --python 3.11 /opt/data/profiles/<seat>/venvs/svc
/opt/data/bin/uv pip install --python svc/bin/python \
  torch==2.4.0 torchaudio==2.4.0 torchvision==0.19.0 \
  --index-url https://download.pytorch.org/whl/cpu
/opt/data/bin/uv pip install --python svc/bin/python \
  "numpy==1.26.4" "scipy==1.13.1" "librosa==0.10.2" "transformers==4.46.3" \
  munch einops descript-audio-codec resemblyzer pydub soundfile hydra-core pyyaml python-dotenv \
  "setuptools==80.9.0"
```

**Verified imports:** `torch 2.4.0+cpu`, `torchaudio 2.4.0`, `transformers 4.46.3`, `librosa 0.10.2`,
`numpy 1.26.4`, `dac`, `resemblyzer`, `webrtcvad`.

Two traps:
- `descript-audio-codec` imports as **`dac`** — a check for `descript_audio_codec` is a false negative.
- `webrtcvad` (via resemblyzer) needs the `setuptools==80.9.0` pin for `pkg_resources`.

## Running it

```bash
cd <seed-vc> && <venv>/bin/python inference.py \
  --source <isolated melody.wav> \
  --target <20 s reference of the person.wav> \
  --output <outdir> \
  --diffusion-steps 35 --f0-condition True --auto-f0-adjust False \
  --inference-cfg-rate 1.0 --fp16 False
```

- **`--diffusion-steps`: use 30–50 for anything you will judge by ear or quote a number from.** The project's
own README defaults to 25 and recommends **30–50 specifically for singing voice conversion**; 4–10 is its
"fastest inference" band. Do not adopt 12 as a house default — it samples below the documented quality range,
so a score measured there is a low-quality draw, not the model's ceiling. Use a low step count **only** as an
explicit speed proof on a throwaway excerpt, and label it as such.
- **`--inference-cfg-rate`** (default 0.7) is the ONLY classifier-free-guidance flag on `inference.py`, and the
  one that trades target-likeness against source fidelity. Sweep it (0.4 / 0.7 / 1.0 / 1.3) before concluding
  anything about likeness.
- **`--similarity-cfg-rate` / `--intelligibility-cfg-rate` DO NOT EXIST on `inference.py`.** They belong to
  `inference_v2.py`, which drives a *different model*: V2 voice/accent conversion (22.05 kHz,
  `hubert-bsqvae-small`), built to suppress source-speaker traits — not the singing model. Passing them here
  is an argument error, not a tuning choice. **Confirm against `<venv>/bin/python inference.py --help`**, never
  the README, which documents both entrypoints in one block.
- **`--fp16 False` is mandatory on CPU.** The default is True and will fail or silently degrade.
- **`--f0-condition True`** selects the singing model (44 kHz f0, RMVPE pitch extractor) and preserves the
  source melody. Without it you get the speech model and the tune is lost.
- **`--auto-f0-adjust False`** — auto adjust causes pitch drift on sung material; only useful speech-to-speech.
- **`--semi-tone-shift`** (int, default 0) — pitches the **SOURCE melody** before conversion, and is the only
  lever on the output's register (see the register section below). It is parsed as an **int**: `-9.0` fails
  with `invalid int value: '-9.0'`, so format whole numbers as integers.
- Checkpoints (~1.5 GB+) download from `Plachta/Seed-VC` on first run, plus RMVPE from
  `lj1995/VoiceConversionWebUI`; they cache under `<seed-vc>/checkpoints`.

## Measured cost on 4 vCPU / no GPU — and why the obvious formula is wrong

**Do not budget `~N s × steps × chunks`.** That arithmetic was recorded here once and it is wrong: cost is
**overhead-dominated**, not step-dominated. Measured, same 20 s pair: a **4-step** run took **679 s**, while a
**12-step** run of the identical pair finished *faster* — three times the steps in less wall time. The fixed
cost is model load, Whisper, f0 extraction and BigVGAN; the steps are a small increment on top.

So:

- **Time one short run and multiply by CELLS, not by an assumed per-step figure.** Check `/proc/loadavg`
  first — a saturated 4-core box inflates the number several-fold (the 679 s above was taken at load **4.87**).
- **Cut the DURATION for the first proof, never the step count.** A 20–30 s excerpt at 35 steps is the right
  first proof; a 20 s excerpt at 4 steps proves only that the harness runs (see the floor below).
- Full length stays a deliberately long background job, and Seed-VC writes its output **once, at the very
  end** — so an interrupted run leaves an empty directory.

**The output file is written once, at the very end.** An interrupted run leaves an empty output directory.
Verify with `ls -la <outdir>` before reporting anything, and remember a `| tail` pipeline reports `tail`'s
exit code (0) for a killed job.

## Measured output quality — first real run, and why zero-shot is the weakest configuration

20 s of isolated generated vocal → 20 s of the person *speaking*, `--f0-condition True`, 12 steps, CPU:

| Metric | Value | Read |
|---|---|---|
| Wall time | **8 min 0 s** for 20 s of audio (two passes) | ~59× realtime |
| Melody contour correlation | **0.707** | tune kept, not note-exact |
| Median pitch shift | **−0.07 st** | f0-conditioning held; no global drift |
| Median f0 | 139.1 Hz → **122.3 Hz** | in the target's register — **but see the warning: this is NOT evidence of likeness** |
| Speaker similarity vs target ref (resemblyzer cosine) | **0.702**, from **0.650** unconverted | closer, not him |
| Voiced frames | 778 / 3999 (19 %) | output is breathy/sparse |

### The measured step floor — and why "landed in their register" proves nothing

Three outputs, one pair, one scorer:

| Output | Similarity |
|---|---|
| Unconverted source | 0.6493 |
| **4 diffusion steps** | **0.6242 — BELOW the source** |
| 12 diffusion steps | 0.7022 |

Below the floor the conversion scores **under the untouched source**: the model damages identity instead of
transferring it. The README's *"use 4–10 for fastest inference"* is therefore a **latency** band, not a cheap
quality band — a low-step probe is legitimate for proving the harness runs and worthless as a quality read.
`scripts/svc_sweep.py` refuses `<12` steps for exactly this reason (`--allow-low-steps` re-benchmarks the floor).

**The 4-step output also measured a median f0 of 128.5 Hz** — squarely inside the speaker's ~131 Hz register —
*while scoring below the source*. So register alignment and timbre identity are independent: **f0 proximity is
not evidence of likeness.** Similarity (resemblyzer cosine) is the metric; f0 is only a drift check.

**Prove the baseline reproduces before comparing to it.** Re-score the old artefact with the same scorer and
script — the recorded 0.702 re-scored as **0.7022**, and that reproducibility is what licenses calling a new
`0.62` worse rather than a different script. `svc_sweep.py --score-only <wav>` does this in one call.

**Verdict on this run: the chain worked, the likeness did not.** Same-speaker pairs typically score 0.75–0.85,
so 0.70 is "a cousin". Two structural causes were known — **zero-shot** (no per-voice training) and a
**speech→singing domain gap** (a sung line converted from a spoken reference). **The domain gap turned out to be
the binding one, and it is closed by the sung-reference run documented below** — so do not quote 0.70 as this
technique's ceiling. It was a wrong-domain reference measured below the documented step range.

### The score is reference-dependent — a sung reference is NOT comparable to a spoken one

The cosine measures output-vs-*reference*, so the reference file is part of the number. Measured, one speaker,
one scorer:

| Pair being compared | Cosine |
|---|---|
| The speaker's own **sung** take vs their **spoken** take (same human) | **0.656** |
| A converted output vs the spoken reference | **0.7022** |
| **The same** converted output vs the sung reference | **0.6292** |

Singing shifts the embedding by about as much as a mediocre conversion does. Rules that follow:

- **Never quote a similarity number without the reference file it was measured against.**
- **Never compare a new run to a baseline from a different reference** — that gap is the scorer, not the model.
  When the reference changes speech→singing, **re-measure the baseline** on the new reference before concluding
  anything about the new run.
- The "same-speaker 0.75–0.85" benchmark above comes from *speech* corpora — do not restate it as the target
  for a sung output scored against a spoken reference.

### Is the reference actually sung? Two numbers, not an impression

| Reference | Voiced frames | Median f0 |
|---|---|---|
| Spoken (20 s) | **19.8 %** | 131 Hz |
| Genuine sung take (65 s) | **57.8 %** | 126 Hz |

The **voiced-frame ratio** is the discriminator — it roughly triples when someone is genuinely singing rather
than talking near the tune. Duration and level are not: the good take peaked at only **0.176**, a quiet phone
recording, and was still the better reference. Compute with `librosa.pyin`, count finite f0 frames, and do this
**before** committing a grid to the file.

Measure this rather than judging by ear alone — `resemblyzer` is already in the SVC venv, and computing both
the target-vs-output and source-vs-output cosines is what makes the movement visible:

```python
from resemblyzer import VoiceEncoder, preprocess_wav   # feed 16 kHz mono
import numpy as np
enc = VoiceEncoder("cpu")
cos = lambda a, b: float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

### 🎯 Measured: the sung reference is the whole game (same everything else)

Identical source melody, identical 12 steps, identical scorer. The **only** change was the reference file:
20 s of the person speaking → 65 s of the person singing.

| Metric | Spoken reference | **Sung reference** |
|---|---|---|
| Similarity vs its own reference | 0.7022 | **0.8472** |
| Similarity vs the *sung* reference (fair bar) | 0.6292 | **0.8472 — +0.218** |
| Unconverted source vs sung reference | 0.7156 | 0.7156 (the bar to beat) |
| Melody contour correlation | 0.707 | **0.968** |
| Median f0 | 139.1 → 122.3 Hz | 218.6 → 216.1 Hz (no drift) |
| Wall time | ~8 min | 29 min on a loaded 4-core box |

Read this table carefully, because three conclusions come off it and the third is the important one:

1. **0.8472 is inside the genuine same-speaker band (0.75–0.85)** — at the top of it, at 12 steps.
2. **It beats the unconverted source (0.7156) by +0.132**, so the conversion is doing real work and is not a
   passthrough that scores well because the source was already close.
3. **Still measured below the recommended 30–50 steps.** So the step sweep is *upside on top of* a passing
   result — it is not a precondition for one. A sung reference at deliberately cheap settings cleared the band;
   the reference was the binding constraint all along, not the step count and not the absence of a GPU.

**The transferable rule:** when zero-shot likeness disappoints, the first question is *what domain is the
reference in*, not *how much hardware do we need*. A person who has only ever spoken to us has no sung
reference, and that — not model choice — is usually the gap. One minute of their humming outperformed the case
for renting a GPU.

### Register comes from the SOURCE, not the reference — and it needs its own fix

`--f0-condition True` keeps the **source melody's pitch** and borrows only **timbre** from the reference. So a
low-register reference can never pull a high melody down. The symptom is unmistakable to the person listening:
their voice sliding from a comfortable low into a thin mid range, described as *"it went from my low-pitched
voice to my medium-pitched voice."* No amount of extra reference recording fixes it — the melody is the lever.

Diagnose with three medians and the sub-160 Hz share, which is cheap and conclusive:

| Clip | Median f0 | <160 Hz |
|---|---|---|
| person's sung reference | 126.4 Hz | 91.1 % |
| source melody (generated) | 222.9 Hz | 35.1 % |
| output, unshifted | 208.9 Hz | 41.6 % |
| **output, `--semi-tone-shift -9`** | **131.6 Hz** | **91.2 %** |

Compute the shift from the two medians — `12*log2(ref_median / source_median)` = −9.85 st, applied as −9.
The output's register distribution then matched the reference almost exactly (91.2 % vs 91.1 %), melody contour
held at **0.956**, and similarity nudged **0.8472 → 0.8516**.

- **Warn the person that the result will sound lower than the original recording** — that is the shift doing
  its job, and hearing it unbriefed reads as a bug. If it lands too low, the honest answer is a melody written
  in their range, not a larger shift (which starts to sound smeared).
- **⛔ The shift is a TRANSPOSE, so it must be applied to the whole arrangement.** Shifting the vocal alone
  leaves it a fixed interval below the backing track — measured as **9 semitones of pitch-class rotation** on a
  −9 st shift, which is dissonant by construction and unfixable in the mix. Shift the instrumental by the same
  ratio (`rubberband=pitch=0.5946:tempo=1.0` for −9 st; tempo preserved, so the grid survives, then verify the
  duration is unchanged) and mix at the vocal's offset. Rule, command and the "transposing is a fallback, not
  the plan" consequence: SKILL.md → *Register comes from the SOURCE melody*.
- **Do not confuse this with the timbre lever.** Reference quality and domain fix *who it sounds like*;
  `--semi-tone-shift` fixes *where it sits*. They are independent and both need checking before you deliver.
- **A shifted vocal breaks xcorr alignment downstream.** `fit_vocal.py` correlates the converted vocal against
the source it cannot match any more (corr 0.195 → 0.080) and returns a nonsense offset with no error. Align
against the *shifted* source, or let the script's low-correlation guard fall back to offset 0.

### ⚠️ This number was measured BELOW the model's documented range — treat it as a floor, not a ceiling

The 0.702 above came from a **12-step** run, while the project's README recommends **30–50 steps for singing
voice conversion**, and the guidance flag that actually exists on this script (`--inference-cfg-rate`) was
never swept. (The 0.8472 sung-reference run was *also* at 12 steps — so even the passing result is below the
documented range, which makes the ceiling claim weaker still.)
So that figure measures the model **handcuffed**, and any sentence of the form "the likeness gap is not a
setting I can tune" is unsupported by it. Stated as the rule:

> **A quality score produced outside the model's own documented operating range is not evidence about the
> model's limits — check the project README's recommended settings before you conclude a technique is exhausted.**

This is the highest-frequency way to talk yourself out of a working tool: run it at the fast settings, measure
the fast settings, and report the number as the tool's nature. Read the recommended-flags block of the README
as part of the task, not as an optimisation to get to later.

**What actually raises likeness, in order of leverage:**
1. **Sweep the documented quality parameters first** — free, and it is the only step that can be skipped by
   accident. Raise steps into the 30–50 band and sweep `--inference-cfg-rate` (0.4–1.3). Cost is time only,
   so prove it on a 20–30 s excerpt at a step count you will keep — measure the run rather than estimating it
   from a per-step figure. Do this **before** buying or renting anything, and before telling anyone the
   ceiling is reached.
2. **A sung reference** — a reference where the person actually holds notes closes the domain gap more than
   any flag can. Someone who has only ever spoken has no sung reference, which is the normal case; asking them
   for ~60 s of humming or one held line is cheaper than any GPU and usually the single biggest lever.
   **This is now measured, not assumed: it took 0.6292 → 0.8472 with every other variable held fixed, at 12
   steps.** Treat it as the primary fix for likeness. Do it *before* proposing hardware, and do it before
   concluding zero-shot cannot work.
3. **Train RVC** on 10+ min of the target voice, then infer on CPU forever after. Needs a GPU, so it is the
   *last* resort and never the opening suggestion. **Sung reference + step/CFG sweep reached the same-speaker
   band on CPU for $0**, so RVC is what you reach for when those two are already exhausted and the bar is still
   missed — not the default answer to "it doesn't sound enough like me".

## Preparing the two inputs

- **Source (melody):** separate the generated track first (`audio-separator`, htdemucs) and use the *Vocals*
  stem. Convert to 44.1 kHz mono WAV. Pick the loudest window if trimming.
- **Reference (timbre): MATCH THE DOMAIN — for a singing target, use a SUNG reference.** This is the single
  biggest lever in the whole pipeline (measured 0.6292 → 0.8472 with everything else fixed), and reaching for a
  spoken clip as the convenient default is what produces a "0.70, doesn't sound like them" result. Use ~20 s of
  the person actually holding notes; fall back to speech only when no sung take exists, and then say the result
  is a floor. Clean it to `highpass=f=60,lowpass=f=13000,loudnorm=I=-18:TP=-2`. Longer is not better — and here
  it is not even *possible*: `inference.py` slices `ref_audio[:sr * 25]`, so **only the first 25 seconds are ever
  used**, and the extra is dropped without a warning. Never ask for "60 s of you singing" expecting length to
  help; ask for the best material **inside the first 25 s** and say so in the request. A noisy reference poisons
  the timbre more than a short one starves it.

## The recording request — spec it exactly, then verify it landed

A sung reference is the highest-leverage free input, and it is also the only one that depends on a human
doing a performance. Two failure modes cost a whole session each time:

- **Never spec it as "60 seconds of you singing".** That request is already wrong twice: only the first 25 s
  are used, and a *length* target invites a low-energy take. Spec it as: **name the material, ask for the
  chorus or the most sustained phrase, and put it in the opening 25 seconds.** Sustained pitch is the whole
  point — accuracy on key is not; the model reads contour, not intonation quality. Say that, or the person
  rehearses for a standard that does not apply to them.
- **Verify the artefact before you run the sweep — VERIFY means go look for it, not wait for a promise.** A
  pasted lyric block or a transcript of what they sang is not a recording. **But a timed-out upload is not
  evidence of absence either:** the attachment is usually already saved at
  `profiles/<seat>/cache/audio/audio_*.ogg`. Enumerate that directory by mtime, `ffprobe` each duration, and
  **transcribe each candidate** (Scribe tags sung material `[singing]`) to learn which opaque hash is the take.
  Skipping this is how a session gets spent asking a person to re-perform a file already on disk. Confirm it is
  audio you can decode *then* start a run; discovering the input is missing three minutes into a 40-minute grid
  wastes the compute and, worse, teaches the user that reporting a failure looks the same as reporting a result.

The reference does not have to be the same song as the melody being converted — only the timbre transfers.
If the person has a preferred song, take it; it makes them more willing to perform, and willingness is the
input quality that no flag can substitute for.
