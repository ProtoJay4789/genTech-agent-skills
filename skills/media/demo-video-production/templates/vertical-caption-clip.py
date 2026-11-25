#!/usr/bin/env python3
"""Vertical caption clip: TTS voiceover + burned text beats -> 1080x1920 MP4.

Copy this file and edit CONFIG. Requires ffmpeg/ffprobe and an ElevenLabs key file.

Why the plate is generated in ffmpeg: image models render their own lettering, which
then collides with burned-in text. A lavfi gradient plate cannot contain text.

Verify after every render: extract a frame at each beat boundary and read the text
back (vision_analyze). Boundary frames are where overlap defects live.
"""
import json
import pathlib
import subprocess
import sys
import urllib.request

# ---------------------------------------------------------------- CONFIG
OUT_DIR = pathlib.Path("/path/to/scratch")
KEY_PATH = pathlib.Path("~/.hermes/secrets/elevenlabs_api_key").expanduser()
VOICE_ID = "<voice id>"
MODEL_ID = "eleven_multilingual_v2"

SCRIPT = "..."          # what the voice reads, plain words, short sentences
TITLE = "TITLE LINE"
SUBTITLE = "one line of context"
FOOTER = "SAMPLE — not live data"   # keep an honesty label on demos

# (label, [lines], colour hex, font size)
BEATS = [
    ("THEY SAID", ["the claim, quoted"], "0xE8B44A", 46),
    ("WHAT THAT MEANS", ["plain translation line one", "line two"], "0xE8B44A", 46),
    ("THE RECEIPT", ["what the data shows"], "0xE8B44A", 46),
    ("VERDICT", ["CONFIRMED — and here is why"], "0x3FBF6B", 56),
]

W, H, FPS = 1080, 1920, 30
GOLD, GREEN, RED, GREY = "0xE8B44A", "0x3FBF6B", "0xD9634A", "0x9AA0A8"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TITLE_END = 2.4          # seconds the title holds; beats start after this
Y0, STEP = 500, 250      # first beat y, vertical pitch between beats
BEAT_END_PAD = 0.07      # between() is inclusive both ends -> end a frame short
# ------------------------------------------------------------- /CONFIG


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("FAILED:", " ".join(cmd[:5]), "\n", p.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    return p.stdout


def dur_of(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", str(path)]).strip())


def esc(t):
    """drawtext chokes on these unescaped."""
    for a, b in (("\\", r"\\"), (":", r"\:"), (",", r"\,"), ("'", r"\'"), ("%", r"\%")):
        t = t.replace(a, b)
    return t


def tts(text, out):
    key = KEY_PATH.read_text().strip()
    body = json.dumps({
        "text": text, "model_id": MODEL_ID,
        "voice_settings": {"stability": 0.72, "similarity_boost": 0.85, "speed": 0.94},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", data=body,
        headers={"xi-api-key": key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        out.write_bytes(r.read())
    print(f"voice: {out.name} ({out.stat().st_size} bytes, {len(text)} chars)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw, clean = OUT_DIR / "vo-raw.mp3", OUT_DIR / "vo.mp3"
    out = OUT_DIR / "clip.mp4"

    tts(SCRIPT, raw)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
         "afftdn,acompressor=threshold=-20dB:ratio=4:attack=5:release=50,"
         "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(clean)])
    dur = dur_of(clean)
    slot = (dur - 0.6 - TITLE_END) / len(BEATS)
    print(f"audio {dur:.2f}s -> {slot:.2f}s per beat")

    f = [
        f"[0:v]format=rgba,noise=alls=5:allf=t,"
        f"drawbox=x=100:y=246:w=190:h=3:color={GOLD}@0.9:t=fill,vignette=PI/4[v0]",
        f"[v0]drawtext=fontfile={FONT_R}:text='{esc(FOOTER)}':"
        f"fontcolor={RED}@0.75:fontsize=24:x=100:y=1806[va]",
        f"[va]drawtext=fontfile={FONT_B}:text='{esc(TITLE)}':"
        f"fontcolor={GOLD}:fontsize=76:x=100:y=320:enable='lt(t,{TITLE_END})'[vb]",
        f"[vb]drawtext=fontfile={FONT_R}:text='{esc(SUBTITLE)}':"
        f"fontcolor=white@0.88:fontsize=36:x=100:y=418:enable='lt(t,{TITLE_END})'[vc]",
    ]
    chain = "[vc]"
    for i, (label, lines, colour, size) in enumerate(BEATS):
        start = TITLE_END + i * slot
        end = start + slot if i < len(BEATS) - 1 else dur
        y = Y0 + i * STEP
        win = f"enable='between(t,{start:.2f},{max(start, end - BEAT_END_PAD):.2f})'"
        f.append(f"{chain}drawtext=fontfile={FONT_R}:text='{esc(label)}':"
                 f"fontcolor={GREY}:fontsize=27:x=100:y={y}:{win}[b{i}0]")
        chain = f"[b{i}0]"
        for j, line in enumerate(lines):
            ly = y + 46 + j * int(size * 1.34)
            f.append(f"{chain}drawtext=fontfile={FONT_B}:text='{esc(line)}':"
                     f"fontcolor={colour}:fontsize={size}:x=100:y={ly}:{win}[b{i}{j + 1}]")
            chain = f"[b{i}{j + 1}]"

    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"gradients=s={W}x{H}:c0=0x090B0E:c1=0x1A2028:x0=0:y0=0:"
               f"x1={W}:y1={H}:d={dur:.2f}:r={FPS}",
         "-i", str(clean), "-filter_complex", ";".join(f),
         "-map", chain, "-map", "1:a",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)])

    print(run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_name,width,height:format=duration,size",
               "-of", "default=nw=1", str(out)]).strip())
    print(f"PATH {out}")
    print("NEXT: extract a frame at every beat start and read it back before shipping.")


if __name__ == "__main__":
    main()
