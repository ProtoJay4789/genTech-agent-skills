# Narrated demo: TTS + ffmpeg recipe

Commands that produced a verified 60.00 s, 1280×720, H.264/AAC narrated explainer. Adapt numbers, keep the order.

## 1 · Picture first (silent, deterministic)

Build one still frame per beat, each with `drawtext … textfile=<path>` (never inline `text=`), then concat:

```python
cmd = ["ffmpeg","-y","-loglevel","error","-f","lavfi",
       "-i", f"color=c={BG}:s={W}x{H}:d={dur}:r={FPS}",
       "-vf", ",".join(filters), "-t", str(dur),
       "-c:v","libx264","-preset","veryfast","-crf","23",
       "-pix_fmt","yuv420p","-r",str(FPS), out]
```

```bash
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -c copy picture.mp4
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 picture.mp4
```

A slow push-in on the one money-shot frame: `scale=iw*1.06:ih*1.06,zoompan=z='min(1+0.0009*in,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=WxH:fps=FPS` before the drawtext filters.

## 2 · Voice segments (one per beat)

```bash
curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE?output_format=mp3_44100_128" \
  -H "xi-api-key: $KEY" -H "Content-Type: application/json" \
  -d '{"text":"…","model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.72,"similarity_boost":0.88,"style":0.15}}' \
  --output seg0.mp3
```

- `eleven_multilingual_v2` for cloned voices; turbo variants drift past ~30 s.
- Keep each segment ≤35 s. Measure with `ffprobe`; a 12 s cap per visual beat keeps sync easy.

## 3 · Stitch clean (do not `-c copy`)

```bash
ffmpeg -y -loglevel error -f concat -safe 0 -i voice.txt -c:a pcm_s16le -ar 44100 -ac 1 voice.wav
```

`-c copy` on MP3 segments emits *non-monotonic DTS* and leaves seams. Decode once, then mux.

## 4 · Mux to the picture length

```bash
ffmpeg -y -loglevel error -i picture.mp4 -i voice.wav \
  -filter_complex "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur=60[vo]" \
  -map 0:v -map "[vo]" -c:v copy -c:a aac -b:a 128k -shortest -movflags +faststart out.mp4
```

`apad=whole_dur=` the picture duration; `-shortest` then trims to the video. `-c:v copy` keeps the picture untouched.

**Fit an overrunning read without touching the picture** — measure the stitched voice first, then choose the tempo, so a long read never truncates mid-sentence:

```python
tempo = 1.0 if vd <= 58.6 else min(1.08, vd / 58.6)   # vd = ffprobe duration of voice.wav
f"[1:a]atempo={tempo:.3f},loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={seconds}[vo]"
```

Cap it near 1.08 — past that the read audibly speeds up, and the real fix is fewer words, not more tempo.

## 5 · Verification battery

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height -of default=nw=1 out.mp4
ffmpeg -hide_banner -i out.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
ffmpeg -hide_banner -i out.mp4 -af silencedetect=noise=-40dB:d=0.4 -f null - 2>&1 | grep silence_ | head
for t in 2 20 33 50 57; do ffmpeg -y -loglevel error -ss $t -i out.mp4 -frames:v 1 frame-$t.png; done
```

Then read at least the first, a middle, and the last frame with `vision_analyze`, asking for the text verbatim and whether anything is clipped. A pass here is the difference between "rendered" and "deliverable".

Healthy targets from a real render: mean_volume ≈ −17 dB, max_volume ≤ −1 dB, duration exact to the centisecond, speech ending ~3–4 s before the visual so the close card lands in silence.

## 6 · Insert a beat before a closing read — as MP3

A held silent beat before the final read lets the last number land and moves the close onto the close card. Build it from `anullsrc`, **encoded as MP3, not WAV**:

```bash
ffmpeg -y -loglevel error -f lavfi -i anullsrc=r=44100:cl=mono -t 2.5 -c:a libmp3lame -b:a 128k silence.mp3
```

List it in order among the TTS segments (`seg0..seg5, silence.mp3, seg6`), then stitch as usual.

**Trap, measured:** a WAV silence dropped into a concat list of MP3s fails to decode (`Invalid data found when processing input`) and the concat silently outputs the **same duration as before** — the beat quietly does not exist. Two tells: the decoder error in the concat output, and a stitched duration that did not move by the silence length. Check `ffprobe` after every splice.

## 7 · When a claim drifts after the render — re-cut, do not re-explain

Numbers on a live service move between render and upload. Keep a **verified-claims sheet** measured *after* the render (claim → verified value → ✅/⚠️), then:

- **Prefer a rounded floor for any number that will live for months** — *"over 1,200 distinct callers in seven days"* stays true; an exact count is a photograph that ages in a week.
- **Never round a bucket you did not measure.** If 354 of 8,790 responses are `other`, say *"a crawler, an indexer, or one of our own probes"* rather than folding them into a word you cannot defend.
- **Name the count you mean** when two counts exist (services advertised vs backends registered) — *"nine of the fourteen services we advertise"*, not a number that silently switches referent.
- **Take extra runtime from the lowest-value frames** (status dumps, boilerplate) — **never from the honesty/disclosure frame**, whose hold is the credibility of the piece.
- **Re-extract frames at the new timecodes after a re-time**: frame boundaries shift, so old screenshots no longer prove anything about the new cut.
- **Copy the final file out of `cache/scratch/`** into a durable media directory the same day; scratch is pruned, and a deliverable that lives only there is gone by the next session.

## Cost bookkeeping

Read `GET /v1/user/subscription` before and after and **report the meter, not the arithmetic** — a measured delta does not equal the script length (an 882-character read moved the counter by 397 in one build, for reasons the API does not expose). Give both numbers and call the delta unexplained rather than asserting a billing rule. Re-rendering the picture is free; re-generating voice is not.
