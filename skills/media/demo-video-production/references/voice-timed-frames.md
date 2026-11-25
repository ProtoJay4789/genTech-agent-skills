# Voice-timed frames — the picture follows the narration

Use when a demo video carries a voiceover and the runtime is fixed ("make it 60 seconds"). The failure this
prevents: frames rendered to a guessed timeline, one long TTS clip stretched to fit, and a narrator describing
a screen that has already moved on.

## Order of operations (this order is the whole trick)

```
script → split per frame → synthesise each → ffprobe each → frame duration := clip duration
       → render frames → concat video → concat audio → mux -shortest → verify 3 channels
```

## 1. Split the script per frame

One paragraph per frame, spoken as a complete thought. Word budget for a 60s slot at ~1.2–1.3× speed is
**150–160 words** — write to that, then measure, do not guess. Each frame's text also becomes its on-screen
caption and its claims-sheet row, so one paragraph per fact keeps all three in step.

## 2. Synthesise each section separately

- Use `text_to_speech` per section with the `speed` parameter. Pick a speed that lands the natural read near
the target (edge-class voices default slow; **1.25 is a sane first try** for a demo cadence).
- Do NOT synthesise one long clip and stretch it afterwards — a single `atempo=1.3` on 79s of speech sounds
  rushed everywhere, while 1.25 plus a 1.03 correction is inaudible.
- Keep the per-frame clips; they are also the segment list for the audio concat.

## 3. Measure, then fit

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 sec0.ogg
```

Sum the durations. If the total is off the slot, apply ONE uniform factor to every clip so relative pacing
survives:

```bash
ffmpeg -y -i sec0.ogg -filter:a "atempo=1.0311" -ac 1 -ar 48000 a0.wav
```

Re-measure the fitted clips — these are now the frame durations. Expect float noise of a few hundredths;
`-shortest` at mux time absorbs it and `ffprobe` on the output should read the target exactly.

## 4. Render one frame per duration

Text goes to a FILE, never inline (`textfile=`), because drawtext parsing fails at render time on `:`, `%`
and bare `/`:

```bash
ffmpeg -y -f lavfi -i "color=c=0x0d1117:s=1280x720:d=${DUR}:r=24" \
  -vf "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf:textfile=/tmp/t0_0.txt:fontcolor=0xe6edf3:fontsize=24:x=64:y=120" \
  -t "$DUR" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -r 24 v0.mp4
```

A push-in on the money frame: `scale=iw*1.06:ih*1.06` then `zoompan=z='min(1+0.0009*in,1.06)':d=1:s=1280x720:fps=24`
prefixed to the drawtext chain.

## 5. Concat separately, then mux

```bash
ffmpeg -y -f concat -safe 0 -i video_list.txt -c copy silent.mp4
ffmpeg -y -f concat -safe 0 -i audio_list.txt -c copy voice.wav
ffmpeg -y -i silent.mp4 -i voice.wav -c:v copy -c:a aac -b:a 128k -shortest out.mp4
```

Never `-c copy` a concat of MP3s straight into the final file: non-monotonic DTS. WAV intermediate, AAC at mux.

## 6. Verify three channels — all three, and say which you checked

| channel | command | pass looks like |
|---|---|---|
| duration | `ffprobe -show_entries format=duration` | exactly the target (`60.000000`) |
| audio alive | `ffmpeg -i out.mp4 -af volumedetect -f null /dev/null` | `mean_volume` around −20 dB, `max_volume` near −2 dB |
| pixels | `ffmpeg -ss <t> -frames:v 1 f.png` + `vision_analyze` | every claim-bearing line transcribed verbatim |

**A mux can succeed with a silent or truncated audio track**, so `mean_volume` is not optional — omit it and
"the video renders" becomes a claim about the container, not about whether anyone speaks.

## The SLOW read (explanatory narration) — fit by cutting copy, never by speeding up

When the brief says *"speak slowly, we're explaining"*, the fit direction INVERTS. A deliberate read with
`eleven_multilingual_v2` on a cloned voice lands at roughly **115–125 words per minute** — a 60s slot then holds
**~145–160 words, not 200**. Two consequences:

- **Do not raise `speed` to make the words fit.** A clone pushed to 1.25–1.3 stops sounding like an explanation
  and starts sounding like a disclaimer being read at gunpoint. **Cut words instead**, then apply a factor that
  *slows* (0.90–0.97) for the final polish — slowing is inaudible, speeding is not.
- **One idea per sentence beats one comma-chained paragraph.** Measured on the same copy: a paragraph of three
  comma-joined clauses came back at **15.5s and 17.6s** where the slot allowed 12, while the identical content
  split into short sentences landed at **9–11s**. The voice inserts its own pause at every comma, so a
  comma-dense script silently *adds* runtime that no tempo correction can remove without deleting the pauses
  the slow read exists for.

Both fixes belong in the SCRIPT, which is re-editable in seconds; a rendered frame is not.

## Landing the slot EXACTLY, with air at both ends

Summing measured clips almost never equals the target. Do not chase the remainder with a fractional tempo —
give each clip a fixed tail of silence, concat, then pad/trim/fade the joined track to the exact figure:

```bash
# per clip: light trailing pad only (this is the breath between sections)
ffmpeg -y -loglevel error -i s0.mp3 -af "silenceremove=start_periods=1:start_silence=0.08:start_threshold=-45dB,\
areverse,silenceremove=start_periods=1:start_silence=0.15:start_threshold=-45dB,areverse,atempo=0.97,apad=pad_dur=0.30" \
  -ar 48000 -ac 1 f0.wav

# the joined track: pad, hard trim to the slot, fade the last clause, normalise to broadcast
ffmpeg -y -i joined.wav -af "apad=pad_dur=1.2,atrim=0:60,afade=t=out:st=59.3:d=0.7,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -ar 48000 -ac 1 vo60.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 vo60.wav   # must read 60.000000
```

`loudnorm` is why the level reads sane on playback: without it a clean TTS track sits near −24 dB mean and
the mix sounds quiet beside every other video on the platform.

**Trim silence to remove dead air, not to tighten the read.** `silenceremove` with start+reverse-tail passes
only touches head and tail of each clip. Running it through the body of a clip (`stop_periods=-1`,
`stop_duration` longer than the ordinary pause) eats the deliberate pauses the slow read was written to
include, and the result measures shorter while sounding *happier* and less clear.

## Gate the RENDER on its own claims — refusing to build beats noticing afterwards

A renderer that prints what it put on screen is a transcript; a renderer that **checks the numbers first
and exits non-zero when one has drifted** is an instrument. Put the contract in the script:

```python
def verify_claims() -> dict:          # read the live surface at render time, never from a note
    ...                               # manifest count, tool list bytes, a probe's exit code

def check(facts) -> list[str]:        # one line per number that appears on screen
    return [...]                      # non-empty => REFUSING TO RENDER, exit 2
```

- **Every on-screen figure gets a check, not just the headline ones.** The frame that says "0 findings" over
  an API that has since gained a finding is the worst artifact this pipeline can produce, because it is
  evidence of the exact discipline it is lying about.
- **Refuse, do not warn.** A warning at build time has no reader; a missing MP4 is impossible to miss.
- **Keep an explicit `--no-verify` escape that prints its own unverified status**, so a deliberate draft is
  possible and is labelled as one.

## A frame that states a NUMBER and then a LIST must be counted against itself

**Read the still and count the items.** Measured: a frame read *"our own audit was wrong four times"* over a
list of **three** assumptions — the most quotable line in the video, off by one, and invisible to `ffprobe`,
to the render's exit code, and to a diff of the script. The fix belongs in the copy: make the count and the
enumeration agree, or drop the count.

- **Prefer enumerating without a count** ("we were wrong about the shape, the price, the status code and the
  parameter") — it cannot drift when a fifth item is added.
- **Two scopes, one quoted.** A payload's array and its whole envelope are different measurements (e.g. a
  tool list that is 5,958 bytes as an array and 7,130 bytes as the response). Decide which number the guard
  watches, then quote THAT one everywhere, and name the scope on screen if both appear.

## Pitfalls

- **Frame durations guessed instead of measured** — the drift is cumulative and invisible until the last frame.
- **`atempo` outside 0.5–2.0** — chain two filters (`atempo=1.5,atempo=1.5`) rather than asking for 2.25.
- **Reading the script back instead of the pixels.** The transcript file is your intent; the render is the
  artifact. Extract stills and transcribe them; check for right-edge clipping while you are there.
- **A duplicate segment hides behind a correct total.** Hash every synthesised clip (`sha256sum`) before you
  render frames: two different sections returning identical bytes means one sentence plays twice, the other
  never plays, and the runtime still lands on target. See `elevenlabs-voice-generation` for the synthesis-side
  check.
- **Timing the close card to the word "thirty cents"** — leave the last frame a second of air after the final
  clause, or the file ends mid-syllable once `-shortest` trims.
