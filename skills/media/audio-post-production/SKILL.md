---
name: audio-post-production
description: "Use when generating songs or converting/autotuning a voice."
tags: [audio, music, autotune, blockrun, ffmpeg, pyworld, gentech-media, svc, stems]
---

# Audio Post-Production (Gentech Media)

## When to Use

Load this when the ask involves **sound as the deliverable**: generate a song or instrumental, put a voice on a
track, clone or convert a voice, make an existing vocal sing in someone else's timbre, auto-tune / pitch-correct
a take, separate stems, fit a vocal to a beat, or judge whether any of that is possible at all. Also load it
before *promising* any of the above — the top sections exist to stop a promise the pipeline cannot keep.

Not for: transcription/STT, video render, or a plain voice-note reply in chat.

**Branding: this is a Gentech Media capability, not "Vanito Productions".** (Jordan, 2026-11-13: the media
lane is Gentech's own — *"this is no longer Vanito Productions. The media skills we have should be renamed
to Gentech Media"*.) Vanito's own material — his songs, the KAGE/HIKARI/cold-crown cast, the personal
folder and the Drive tree — is **his**, preserved separately and untouched by Gentech Media work. Do not
label Gentech Media output under his brand, and do not move his archive into ours.

Two capabilities, both measured on this host:

| Job | Lane | Cost | Proof |
|---|---|---|---|
| Generate a song/instrumental | BlockRun `minimax/music-2.5+` | $0.199 + $0.001 tx | 94.7 s stereo MP3 rendered 2026-11-11 |
| Pitch-correct / auto-tune a vocal | local `pyworld` WORLD vocoder | free | mean pitch error 27.5 → 4.2 cents |
| Other audio FX (EQ, reverb, denoise, tempo, pitch-shift) | `ffmpeg` | free | has `rubberband`, `afftdn`, `loudnorm`, `atempo`, `acompressor` |

**Stem separation IS available** — `audio-separator` + `htdemucs` install and run on CPU here (see below).
The autotune still wants a **dry** vocal, because it locks onto whatever dominates the pitch in the file;
but you can now *manufacture* one: separate the mix, tune the vocal stem, mix back. Do not refuse a
"tune this mixed track" request on the grounds that separation is impossible.

Still genuinely unavailable: no `sox`, no `autotalent`, no audio-to-MIDI / melody extraction, no GPU.

## The voice question — what ElevenLabs can and cannot do (answer this before promising a song)

When the ask is *"make a song with MY voice"*, the honest answer has three parts and they are not
interchangeable:

1. **Cloning your voice: yes**, if the account has a free voice slot. It needs **30–60 s of clean, dry
   speech** — quiet room, normal voice, no music. Then `POST /v1/voices/add` (multipart, `files[]` + `name`).
2. **Your cloned voice SPEAKING over a beat: yes, and it is the deliverable that actually exists.** Rap flow,
   spoken-word hooks, intros, ad-libs. This is the real "my voice on a track" answer.
3. **Your cloned voice SINGING a melody: no.** ElevenLabs TTS is a speech model — it will not belt, sustain
   a note, or hold a tune. Melodic singing in someone's own timbre needs a **voice-conversion / SVS model**,
   which is a different class of tool, not a setting. Say this up front, not after they record.

Never let the model name make the promise: the music model generates **its own singer** from a text prompt,
so a $0.20 track is "a singer in that style", never "you singing". The cheap song lane cannot take a voice
clone as input.

### Check the account's real scope before promising a clone

```bash
K=/opt/data/profiles/<seat>/secrets/elevenlabs_api_key
curl -s -H "xi-api-key: $(cat $K)" https://api.elevenlabs.io/v1/user/subscription \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['tier'],d['character_count'],'/',d['character_limit'],'| voice_limit',d['voice_limit'])"
```

Read **tier**, **remaining characters** and **`voice_limit` vs the number of voices you already have** — that
last pair is what decides whether a new clone is possible. A custom-voice slot is the constraint, not the
credit balance.

### ⚠️ A clone named after a person is THAT person's voice — verify before you use it

A voice called `Jordan`, `Vanito`, `Christel` etc. is a clone of **that human**, not a persona the requester
owns. Before putting a named clone on anything:

```bash
curl -s -H "xi-api-key: $(cat $K)" https://api.elevenlabs.io/v1/voices/<voice_id> \
  | python3 -c "import sys,json;v=json.load(sys.stdin);print(v['name'],'|',v.get('category'));print((v.get('description') or '')[:160]);print([s.get('file_name') for s in (v.get('samples') or [])])"
```

The `description` and the sample **filenames** say whose voice it is and what it was made for. **Do not
assume a voice named after the person you are talking to is their own** — collaborators share a group, and
one of them may be using a voice named after a friend. If the requester asks "did I clone my voice?", answer
by enumerating the account (name + category + description + sample filename per voice) and saying plainly
which one, if any, is theirs. Getting this wrong attributes one person's voice to another.

## Song generation — BlockRun music lane

`minimax/music-2.5+`, ~$0.20 per track. Script `/opt/data/profiles/<seat>/scripts/blockrun-music.mjs`;
run it backgrounded (renders take 60–120 s) and `ffprobe` the result rather than trusting the request.

**It generates its own singer from a text prompt** — a track is "a singer in that style", never "you
singing". The lane cannot take a voice clone as input.

Async/payment/`duration_seconds` traps, the exact endpoint shapes and the free re-poll recovery:
`references/blockrun-music-lane.md` — read it before the first render, three of the four traps cost a run each.

## Auto-tune — real pitch correction, not a pitch-shift

Script: `/opt/data/profiles/protojay/scripts/autotune.py`

```bash
ffmpeg -i in.ogg -ar 44100 -ac 1 tmp.wav          # voice notes arrive as ogg/opus — decode first
.audiovenv/bin/python autotune.py tmp.wav out.wav --scale major --speed 0.15
.audiovenv/bin/python autotune.py tmp.wav hard.wav --scale major --speed 0.35   # T-Pain snap
```

How it works: `pw.harvest` f0 → quantize each frame to the nearest in-scale semitone → blend by
`--strength` → one-pole slew → `pw.synthesize` with the ORIGINAL CheapTrick envelope + D4C aperiodicity,
so timbre/identity is preserved and only pitch is rewritten. Key is auto-detected when `--key` is omitted.

### Measured settings (A4/C#5/E5/D5 phrase sung 27.5 cents off, mean abs error per note)

| `--speed` | mean cents off after | reads as |
|---|---|---|
| 0.05 | 13.1 | barely touched |
| 0.15 (default) | 10.3 | natural, in tune |
| 0.20 | ~10 | natural, in tune |
| 0.35 | 5–6 | tight |
| 0.50 | 4.2 | hard tune / robotic |

On a real spoken/sung Telegram voice note (8.3 s, 23.8 cents median off, only 32 % of frames within 15 cents):
`--speed 0.20` → 17.2 cents off (60 % of frames improved), `--speed 0.50` → 11.9 cents (67 % improved,
57 % of frames within 15 cents). **Speech does not quantize as cleanly as sustained singing** — say so;
the shift is audible but not studio-perfect on a talky take.

Report the numbers as the receipt (`median_cents_off_pitch_before/after`, key + confidence are printed as JSON).

## Auto-tune verification loop (do this, it caught a 100x bug)

**A pitch-shift bug silently produces a "working" file.** The first version blended the correction in
**cents** and re-applied it as `2**(x/1200)` — that is a semitone/cent mismatch, so the file came back
shifted by ~1/100 of what was asked and still reported a plausible-looking number. It survived a whole
deliverable before the numbers exposed it. Guard:

1. **Re-estimate f0 on the OUTPUT and compare to the input per frame** (`pw.harvest` on both):
   median cents-off must fall, and *frames improved* must clearly beat *frames worsened*.
   Anything near 50/50 means the shift is not landing. A correct run showed 60–67 % improved.
2. **Check the mean shift in semitones is not ≈ 0** (it should be small but nonzero): a ~0 shift while
   "median cents off" moves a little is the signature of a strength/unit error, not a working tuner.
3. Separate the ratio from the smoothing: correction is computed in **semitones** and applied as
   `2**(semi/12)`. Never mix cents and semitones in one expression.

## Can a cloned voice SING? No — and style settings do not fix it (measured 2026-11-13)

A common ask is "clone my voice, then make a song with it". The clone will **recite**, not sing. Do not
take this on faith — it was tested on a real clone (`Jordan`, `FQ7BD8hzBQ9rpKAoto8c`) three ways, measuring
pitch movement as the std of f0 in semitones over voiced frames:

| Rendition | Median f0 | Pitch movement (st, std) |
|---|---|---|
| The person's real speech | 131 Hz | **3.86** |
| `eleven_v3`, style 0.55 | 126 Hz | 3.50 |
| `eleven_multilingual_v2`, style 0.70 | 130 Hz | **2.75 — flatter** |

Two conclusions, both counter-intuitive:
1. **Raising `style` makes it flatter, not more melodic.** Style buys *speech* expressiveness (emphasis,
   attitude), not pitch movement. Do not burn renders sweeping style in search of singing.
2. **Auto-tuning a spoken clone cannot work.** Measured 24.3 → 25.6 cents off: pitch correction needs a
   melody to correct, and a monotone reading has none. If the user wants their clone auto-tuned, the melody
   has to come from somewhere else first.

**Say this up front, before the user records a sample for singing.** The honest deliverable from TTS is
spoken-word / rap flow over a beat, which is genuinely good. Melodic singing in someone's timbre is
**singing voice conversion**, and that is a different model:

```
1. melody from a generator   (MiniMax $0.20)  — a singer performs the notes
2. isolate that vocal        (audio-separator, free)
3. swap in the target timbre (Seed-VC zero-shot, free) — rewrites timbre, keeps the notes
4. auto-tune                 (autotune.py, free) — now there IS a melody
5. mix back                  (ffmpeg, free)
```

The architectural point to remember: **SVC does not synthesise singing — it rewrites the timbre of a
melody that already exists.** So generate the melody first, convert second. Never the reverse.

Install recipe, ranked model choices, the mandatory CPU flags (`--fp16 False`, `--f0-condition True`), the
measured **runtime cost (overhead-dominated, not per-step)** and the **first measured output quality**:
`references/singing-voice-conversion-cpu.md`.

### Never report a quality ceiling from a run outside the model's documented range

**Before saying a technique is exhausted, read that project's own recommended-flags block as part of the task.**
A model run at "fast" settings produces a low-quality sample, not a limit — and it is the easiest way to talk
yourself out of a working tool, because the number looks like a measurement rather than a choice.

Measured: a likeness score was reported as *"not a setting I can tune"* while the run used **12 steps** where
the project recommends **30–50 for singing**, and the one CFG flag that does exist had never been swept. The
honest finding was **"untested at the recommended settings"**, not "impossible".

**⚠️ Verify a flag exists on the script you will actually RUN — `--help` it; do not plan from the README.**
These projects ship several entrypoints over several *different* models, and the README documents all of them
in one block. `--similarity-cfg-rate` / `--intelligibility-cfg-rate` belong to `inference_v2.py` (22 kHz
voice/accent conversion); the 44 kHz **singing** script `inference.py` accepts only `--inference-cfg-rate`.
Grepping the README proves a flag exists *somewhere in the repo*, not in your run — promising a sweep on the
wrong script's flag sends the user to record audio for an experiment that cannot execute.

**Check the code for a hard input cap before asking anyone to record more of it.** `inference.py` slices
`ref_audio[:sr * 25]` — the reference is **silently truncated to 25 seconds**, so "send me 60 s" cannot help
by length. The lever is *what occupies the first 25 s*. Put that instruction in the request itself, or the
extra recording is wasted effort and the result looks like the model ignored it.

- **Correct a claim like this out loud, as your own error.** Do not quietly re-run and present the new number
  as if it had always been the plan; the user acted on the earlier claim.
- **Sweep the free documented parameters before proposing any spend** — new hardware, a rental, a paid API.
  The sweep is time, the alternative is money, and the user asked for the free one first.
- Full flag table, ranges and the corrected leverage order: `references/singing-voice-conversion-cpu.md`.
  `scripts/svc_sweep.py` runs the whole steps × CFG sweep and scores every result with resemblyzer, so a
  sweep is one command and the numbers are comparable to the earlier baseline. It also takes
  `--semi-tone-shift` (the register lever) and refuses `<12` steps.

### There is a measured step floor, and "landed in their register" is not "sounds like them"

Same pair, same scorer: **source 0.6493 · 4 steps 0.6242 · 12 steps 0.7022.** Below the floor the conversion
*scores under the untouched source* — it damages identity rather than transferring it, so a project's "use 4–10
for fastest inference" is a **latency** band, not a cheap quality band. `scripts/svc_sweep.py` refuses `<12`
steps (`--allow-low-steps` re-benchmarks the floor). A low-step probe proves the harness runs and nothing about
quality. Full table and the sung-vs-spoken diagnostics: `references/singing-voice-conversion-cpu.md`.

**Prove the baseline is reproducible before you compare to it.** Re-score the *old* artefact with the scorer
and script you are about to use — the recorded 0.702 re-scored as **0.7022**, and that is what licenses
calling a new `0.62` worse rather than a different script. `svc_sweep.py --score-only <wav>` does exactly this.
**Never carry a baseline across references.** 0.702 belongs to the *spoken*-reference runs; re-scored against
a sung reference the same artefact is 0.6292. Pass `--baseline` only from a number measured on the reference
you are actually sweeping against, or leave it off — the script no longer assumes one for this reason.

**Never cite f0 proximity as evidence of likeness.** A 4-step output measured a median f0 of **128.5 Hz** —
dead in a ~131 Hz target register — while scoring *below the source*. Register alignment and timbre identity
are independent; similarity is the metric and f0 is only a sanity check that the pitch did not drift.

### Register comes from the SOURCE melody, not the reference — shift the source

`--f0-condition True` takes **pitch from the source melody** and only **timbre from the reference**. So a
low-voiced reference can never pull a high melody down: the user hears their own timbre stuck on a song pitched
for someone else, and describes it precisely that way — *"it went from my low-pitched voice to my medium-pitched
voice."* No extra reference recording and no training fixes this. The **melody** is the lever.

Diagnose by comparing median f0 and the sub-160 Hz share across all three files:

| Clip | Median f0 | <160 Hz |
|---|---|---|
| person's sung reference | 126.4 Hz | 91.1 % |
| source melody | 222.9 Hz | 35.1 % |
| output, unshifted | 208.9 Hz | 41.6 % |
| **output, `--semi-tone-shift -9`** | **131.6 Hz** | **91.2 %** |

Compute the shift from the medians — `12*log2(ref_median / source_median)` gave −9.85 st, applied as −9.
Register distribution then matched the reference almost exactly (91.2 % vs 91.1 %), melody contour held at
**0.956**, similarity nudged **0.8472 → 0.8516**.

- **Say up front that the output will sound lower than the original recording** — that is the shift working.
  If it is too low, the honest next step is a melody genuinely written in their range, not a bigger shift.
- **`inference.py` wants an INT for `--semi-tone-shift`.** `-9.0` fails with `invalid int value: '-9.0'`;
  format whole numbers as integers.
- **⛔ Shift the BACKING TRACK by the same interval, or the deliverable is out of key — and no amount of
  mixing repairs it.** `--semi-tone-shift` moves the vocal **only**, but it is a *transpose*: it is only
  musically valid applied to the **whole arrangement**. A shifted vocal over an unshifted instrumental sits a
  fixed interval below the harmony — measured as **9 semitones of pitch-class rotation** on a −9 st shift, so
  the notes are wrong against the chords by construction. The person hears it immediately and reports it in
  exactly those words: *"too low and out of key."* Levelling, EQ and auto-tune cannot fix it, because the
  problem is not the mix.

  ```bash
  # ratio = 2**(st/12); -9 st -> 0.5946. rubberband shifts pitch and preserves tempo, so the grid survives.
  ffmpeg -y -i instrumental.wav -af "rubberband=pitch=0.5946:tempo=1.0" -ar 44100 -ac 1 inst_shifted.wav
  ffprobe -v error -show_entries format=duration -of csv=p=0 inst_shifted.wav   # must equal the original
  ```

  Then mix at the vocal's offset. `rubberband` is available as an ffmpeg filter here; `sox` is not.
- **Transposing is a fallback, never the plan.** Shifting a whole arrangement is coherent but it is a
  *transposed recording*, not a song written for that voice — and it still reads as *too low* to the person
  even when it is perfectly in key. When the register does not fit, make the **source melody** come out in the
  performer's key in the first place: prompt the music lane for that register, or pitch the source before
  separating stems. **Ask what range they actually sing in before transposing a song written for someone else.**
- **Pitch-shifting breaks fit-to-beat alignment** — see the correlation guard in the `fit_vocal.py` section.

**Before blaming the converter for gaps, breathiness or a choppy result, profile the SOURCE the same way.** Count
active 20 ms frames and the longest silent run on **both** files. Measured: an output at **11.1 % active frames
with a 5.06 s silent stretch** looked like model damage — the source had the *identical* 11.1 % and the same
5.06 s gap, so the sparsity was inherited from the excerpt, not introduced. Report an output defect as the
model's only when the input does not already show it; otherwise you hand the user a reason to distrust a working
pipeline.

**The similarity score is only meaningful against the reference you actually scored with — singing shifts the
embedding, so cross-reference comparisons are invalid.** Measured on one speaker: their *sung* voice and their
*spoken* voice score only **0.656** against each other, and the same converted output scored **0.7022 vs the
spoken reference but 0.6292 vs the sung one**. Two consequences: (1) quote a score only next to the reference
it came from, and never compare a new run to a baseline drawn from a different reference file — that is a
scorer difference masquerading as an improvement; (2) when the reference changes from speech to singing, the
baseline must be **re-measured**, not carried over.

**A sung reference closes the gap — this is measured, so treat it as the answer rather than a hope.** Identical
source melody, identical 12 steps, identical model; the only change was the reference (spoken → sung).
Similarity **0.7022 → 0.8472**, melody contour **0.707 → 0.968**, no f0 drift, and it beats the unconverted
source (**0.7156**) by **+0.132** so it is not a passthrough. Measured against the correct sung baseline of
0.6292 that is **+0.218**. **0.8472 sits inside the genuine same-speaker band.** A free sung take outperformed
the entire case for renting a GPU, and it was recorded by the user in one minute — so the standing order holds
and hardens: **better input before better hardware, and never present RVC training as the only road to
likeness.** Note it reached 0.8472 *still below* the recommended 30–50 steps, so the step sweep is upside on
top of this, not a precondition for it.

**Confirm a reference is actually sung before spending a grid on it.** Two cheap numbers separate a real
take from someone talking near the tune: **voiced-frame ratio** and **f0 spread in semitones**. A spoken
reference measured **19.8 % voiced** (median 131 Hz); a genuine sung take measured **57.8 % voiced, 2.83 st
of f0 spread at a 126 Hz median**. The **voiced-frame ratio is the discriminator** — it roughly triples — so
judge "is this singing" on that, not on duration or loudness. **Do not quote an f0-spread figure you measured
on only one of the two files**; a metric reported for both when it was computed for one is a fabricated
comparison, and it makes the discriminator vanish. (Peak level is meaningless here: a quiet phone recording at
0.176 peak is still a good reference.)

### Asking a human for a recording — prove the rig first, then confirm the file actually arrived

The input this pipeline needs most is a *person performing*, which is the one thing you cannot generate,
retry or scrape. Treat the request itself as part of the engineering.

- **Prove the harness end to end on assets you already hold BEFORE sending the spec.** Run one cheap config
  against the existing source/reference pair and confirm it scores. Asking someone to sing into an unproven
  rig spends their effort to discover a bug you could have found alone, and a wasted take is much more
  expensive than six minutes of CPU.
- **⛔ A failed download is NOT a missing file — search the inbound cache before you declare zero.** A
  timeout in the chat transport says nothing about disk: the attachment is usually already saved under
  `profiles/<seat>/cache/audio/audio_*.ogg` (and sometimes again under `cache/documents/native-inputs/<hash>/`).
  Declaring "nothing arrived" without looking makes you ask a human to re-perform something you already have,
  which is the most expensive mistake available in this workflow. Enumerate the cache, then identify each
  candidate — the filenames are opaque hashes:

  ```bash
  cd /opt/data/profiles/<seat>/cache/audio
  for f in *.ogg; do echo "$f $(stat -c %y "$f" | cut -d. -f1) $(ffprobe -v error \
    -show_entries format=duration -of csv=p=0 "$f")"; done | sort -k2
  ```

  **Transcribe each candidate to learn what it is** — this is how a take gets identified, and Scribe tags sung
  material explicitly as `[singing]`, which distinguishes it from the spoken coaching notes in the same cache:

  ```bash
  curl -s -X POST https://api.elevenlabs.io/v1/speech-to-text \
    -H "xi-api-key: $(cat /opt/data/profiles/<seat>/secrets/elevenlabs_api_key)" \
    -F "file=@audio_XXXX.ogg" -F "model_id=scribe_v1" | head -c 400
  ```

  If the person says "I sent it twice", **enumerate all takes and report which ones you found** rather than
  working from one and implying the rest never existed.
- **A pasted lyric, a transcript, or a *description* of the singing is still not the recording.** That part
  holds — a text block is not audio, and you cannot convert lyrics. But it is a claim about the *content*, not
  a licence to conclude the file is absent: check the cache first (above), and only then ask for the file.
- **Ask for audio as a file/document, not a voice bubble.** Voice notes arrive opus/48 kHz mono compressed;
  feeding codec artefacts into a timbre model means some of what you measure is the carrier, not the person.
  Accept a voice note as a fallback rather than losing the take, but ask for the file first.
- **If the person defers or is not in the mood, stop — do not coax.** A tired or unwilling take is a bad
  reference, and a bad reference makes you report the *input's* weakness as the model's ceiling. Write a
  resume note instead: the chosen material, the input constraints (which 25 s, what to sing), the exact
  command, and the baseline number to beat. Nothing is lost — the rig is built, and the recording is the only
  outstanding item.

## A converted vocal is melody-correct but NOT time-aligned — fit it before you mix

SVC preserves the tune, not the grid. Laying the raw output over the instrumental is a train wreck.
`profiles/<seat>/scripts/fit_vocal.py` does the four steps and prints a number for each:

```bash
<venv>/bin/python fit_vocal.py \
  --vocal converted.wav --source <original isolated vocal stem>.wav \
  --instrumental inst.wav --out fitted.wav \
  --autotune <path>/autotune.py --speed 0.35
```

1. **Streaming cross-correlation** for the offset, reading both files in 60 s chunks so long files never
   load whole. **Strip leading silence from BOTH signals before correlating** — the pad dominates the
   correlation and pins the answer at exactly `0.000 s`, which looks like a perfect alignment and is just
   the silence matching itself.
2. **Trim the mix window** to where the vocal actually lives, so lead padding never ships as dead air.
3. **Auto-tune** the aligned vocal.
4. **Mix** over the instrumental, peak-normalised, and report the window and peak.

**A low normalised correlation between a converted vocal and its source is EXPECTED** — the timbre was
deliberately replaced, so waveform similarity is low even when the alignment is right. Do not tune parameters
to raise that number. **But there is a floor below which the offset is simply wrong, and it errors loudly:
never.**

| Vocal | xcorr offset | normalised corr |
|---|---|---|
| unshifted | −0.001 s | 0.195 |
| `--semi-tone-shift -9` | **+6.454 s** | **0.080** |

Pitch-shifting decorrelates the vocal from the source it is being aligned against, so xcorr returns a
confident-looking nonsense lag and the vocal lands in the wrong place — a wrong answer with no error, which
is the worst failure shape in this pipeline. The script guards it: below `MIN_CORR = 0.12` it warns and falls
back to **offset 0** (conversion preserves timing; the unshifted run independently confirmed ~0), overridable
with `--allow-low-confidence`. **When you see the low-correlation warning, trust the fallback, not the lag.**
The proper fix is to align against the *pitch-shifted* source.

## What must leave this box (Jordan, standing)

Split by cost profile, not preference:

| Job | Where |
|---|---|
| RVC **training** of any voice | GPU host — impossible here |
| Conversion or separation on > ~40 s / > ~3 min of material | GPU host |
| Song generation, auto-tune, fit-to-beat, mixing, mastering, delivery | **stay local** |

A round trip through a desktop that may be asleep is worse than six minutes of local compute — do not offload
the cheap stages to feel tidy.

**Jordan's standing preference: do not lead with "rent a GPU".** When a local result disappoints, the order is
(1) sweep the free documented parameters, (2) ask for a better *input* (a sung reference instead of speech),
(3) use hardware we already own, (4) mention a rental last and explicitly as deferred. An SVC run on a rented
hour is under a dollar, but it was already declined once — offering it again as the headline answer reads as
not listening, and the free sweep had not been done.

**Proving a peer lane exists takes three probes, not one — and an echo reply is the weakest of them:**

```bash
ping -c 3 -W 2 <peer>                      # host's network stack is up        — proves NOTHING about the agent
for p in 22 8642 8646; do timeout 4 bash -c "echo > /dev/tcp/<peer>/$p" \
  2>/dev/null && echo "$p OPEN" || echo "$p closed"; done   # is anything listening
curl -s -o /dev/null -w '%{http_code}\n' http://<peer>:<port>/health            # does it serve
hermes peer list && hermes peer dm fleet/<seat> "probe"    # is the agent REGISTERED
```

**ICMP succeeding while every TCP port is closed means the machine is on and the service is not** — a
reachability ping is not a lane, and reporting "the host is up" as "we can use it" is exactly the confusion
to avoid. If the probe set does not all pass, say the lane does not exist and name what is missing (a key moved
by hand, `hermes peer add`, or someone at that desk running the agent).
**Filing a note into a folder nothing reads is not delivery.**

## Stem separation — `audio-separator` + htdemucs (works on CPU, measured)

Isolate a vocal from a mix before tuning, converting or re-mixing. Default model `htdemucs`; **verify the
Vocals stem is non-silent before using it** — a silent vocal means the separation failed and everything
downstream is worthless. Install command, measured throughput (91.6 s song in 5 min 50 s on 4 vCPU), the
stem-verification loop and the htdemucs / BS-RoFormer / Spleeter trade-off: `references/stem-separation.md`.

Model choice in one line: `htdemucs` is the default; `BS-RoFormer` (~9.8 vs ~9.0 dB SDR) is slower and
memory-hungry with scattered weights; `Spleeter` only wins on very weak hardware.

## Long CPU jobs — the exit code lies, so verify the artifact

Diffusion/neural audio jobs print only at the END, so an interrupted run leaves **nothing** on disk while
the wrapper still looks like it succeeded. Two traps, both hit in one session:

- `cmd 2>&1 | tail -8; echo EXIT=$?` reports **`tail`'s** status, not the job's. A killed run reads `exit 0`.
- An outer `timeout N cmd` returns 124/143 that the notification may surface as a normal exit.

**The only proof is the output file.** After any long run, `ls -la` the output directory and `ffprobe` the
expected file — before reporting success, and before re-running (a partial run may have produced something).

**Do not derive runtime by multiplying steps.** Measured: a **4-step** run took **679 s** on a 20 s clip,
while a **12-step** run of the same pair finished *faster* — the cost is dominated by fixed overhead (model
load, Whisper, f0 extraction, BigVGAN), not by step count. Time one short run on an idle box, check
`/proc/loadavg` first (a saturated 4-core box inflates it several-fold), then multiply by **cells**, never by
an assumed per-step figure. **Cut the excerpt duration for the first proof — never the step count.** Below
12 steps the conversion scores *worse than the unconverted source*, so a low-step probe proves the harness
runs and nothing at all about quality.

## Environment trap — the venv is not optional

The host `python3` is 3.14 from `/opt/hermes/.venv`, with **no pip and no numpy**. Do not try to install
into it. Build the working venv:

```bash
# A PERSISTENT path — NOT cache/scratch, which is pruned on idle and silently eats the venv.
mkdir -p /opt/data/profiles/<seat>/venvs && cd /opt/data/profiles/<seat>/venvs
/opt/data/bin/uv venv --python 3.11 audio
/opt/data/bin/uv pip install --python audio/bin/python numpy soundfile librosa pyworld "setuptools==80.9.0"
```

`pyworld` imports `pkg_resources`, which setuptools ≥81 removed — pin `setuptools==80.9.0` or the import
dies with `ModuleNotFoundError: No module named 'pkg_resources'`. `uv` lives at `/opt/data/bin/uv` (not on PATH).

**A venv built in the scratch dir does not survive.** `TMPDIR`/`cache/scratch` is pruned after ~24 h idle, so
a library installed there is gone by the next session and every script path into it breaks. Build audio venvs
under `profiles/<seat>/venvs/`. The same `setuptools<81` pin is needed by `webrtcvad` (pulled in by
`resemblyzer`), which fails identically — if a package imports and dies on `pkg_resources`, the fix is the pin,
not a reinstall.

**When an import check says a package is missing, confirm the module name before believing it.**
`descript-audio-codec` installs and imports as **`dac`** (`from dac.nn.quantize import VectorQuantize`); a
check for `descript_audio_codec` reports a false negative on a correctly installed package. Look at what the
consumer imports (`grep -rn "import" <project>/modules/*.py`) rather than guessing from the distribution name.

## Delivery

Send the audio as a MEDIA line in the reply that announces it. Add `[[audio_as_voice]]` only when the
artifact is meant to be listened to as a voice note; a song ships as an audio file. One MEDIA per message
when the audio is the point — two can arrive as nothing.

**A/B file recipe** — the effect must never be confusable with a volume change.

⛔ **Match on GATED loudness (EBU R128), never on `mean_volume`.** There are two separate ways to get this
wrong and both were measured on the same deliverable:

- **`loudnorm` applied blind is not an equaliser.** The same chain on both halves left them **7.6 dB apart**
  (−30.0 vs −22.4 dB mean) because integrated loudness does not converge over a few seconds.
- **`mean_volume` is the wrong target for any sparse clip — this is the one that ships broken audio.** It is
  carried by silence, so a take with a long gap reads as "matched" while the notes a human can actually hear
  sit **7.9 dB down** (−32.2 vs −24.3 dBFS over active frames). The user then reports exactly what is there:
  *"it's kind of quiet, I didn't hear anything on that."* A comparison built this way is not merely unfair —
  it is inaudible.

Measure **gated LUFS per half**, apply explicit gain, then **re-measure the shipped file**:

```bash
# integrated loudness; add -ss/-t BEFORE -i to measure a slice
lufs() { ffmpeg -i "$1" -af ebur128=framelog=quiet -f null - 2>&1 \
           | grep -E '^\s+I:' | tail -1 | grep -oE '\-?[0-9.]+'; }

target=-16
for f in a.wav b.wav; do
  m=$(lufs "$f")
  g=$(python3 -c "print(round($target - ($m),2))")
  ffmpeg -y -v error -i "$f" -af "volume=${g}dB" -ar 44100 -ac 1 "eq_$f"
done
ffmpeg -y -v error -i eq_a.wav -i gap.wav -i eq_b.wav \
  -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1[o]" -map "[o]" -b:a 192k ab.mp3
# VERIFY both halves of the FINISHED file — never trust the gains you computed
for ss in 0 <second-half-start>; do
  printf 't=%ss ' "$ss"
  ffmpeg -ss "$ss" -t <len> -i ab.mp3 -af ebur128=framelog=quiet -f null - 2>&1 | grep -E '^\s+I:'
done
```

**Accept a pair within ~0.2 LU and nothing wider.** Check the peak after gain and put a limiter before the
encode (`alimiter=limit=0.89:level=false`) — a quiet phone recording needs a large boost and will otherwise
clip. A sparse source also loses ~7 dB when summed with `amix`, which normalises by input count; use
`normalize=0` or apply the gain afterwards.

**The listening pass outranks every metric in this file.** On this workflow the user twice caught real defects
my numbers did not surface — an unfair-loudness A/B and a wrong-register output. Ship the audio so it can be
heard, state what to listen for, and treat their report of a defect as evidence, not opinion.

Telegram voice notes arrive as **opus/48 kHz/mono**; decode to 44.1 kHz mono WAV first. Deliver the raw
take as its own file too — a demo the user cannot compare against their own original proves nothing.
