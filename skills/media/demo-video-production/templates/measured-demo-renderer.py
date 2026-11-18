#!/usr/bin/env python3
"""measured-demo-renderer.py — terminal-style demo video from REAL output.

Copy and replace the frames in main(). Every line must be a command you ran or a value you read;
if it cannot be measured, it does not go in the video.

WHY textfile= — MEASURED: inline drawtext `text=` aborts the render on `%`, a bare `/`, or `:`, with
`Nothing was written into output file` + `libx264 ... return code -22`. It fails at RENDER time, so one bad
line kills a video whose earlier frames already rendered. Backslash escaping is unreliable because the
filtergraph is parsed twice; textfile has no escaping at all.

USAGE
  python3 measured-demo-renderer.py out.mp4
Needs: ffmpeg + ffprobe + a monospace TTF (check `fc-list` for DejaVu).
"""
import os, shutil, subprocess, sys, tempfile

W, H, FPS = 1280, 720, 24
BG    = "0x0d1117"
FG    = "0xe6edf3"
DIM   = "0x8b949e"
GREEN = "0x3fb950"
BLUE  = "0x58a6ff"
AMBER = "0xd29922"
MONO  = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def frame(lines, out, dur, tmp, idx):
    """lines: (text, colour, size, bold, y). Each text goes to its own file - no escaping."""
    filters = []
    for j, (text, colour, size, bold, y) in enumerate(lines):
        if not text.strip():
            continue
        tf = os.path.join(tmp, f"t{idx}_{j}.txt")
        with open(tf, "w", encoding="utf-8") as f:
            f.write(text)
        filters.append(
            f"drawtext=fontfile={MONOB if bold else MONO}:textfile={tf}"
            f":fontcolor={colour}:fontsize={size}:x=64:y={y}:line_spacing=8")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
           "-i", f"color=c={BG}:s={W}x{H}:d={dur}:r={FPS}",
           "-vf", ",".join(filters), "-t", str(dur),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", "-r", str(FPS), out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"frame {idx} failed:\n{r.stderr[-800:]}")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "demo.mp4"
    tmp = tempfile.mkdtemp(prefix="demo-")
    segs = []

    def add(lines, dur):
        p = os.path.join(tmp, f"f{len(segs):03d}.mp4")
        frame(lines, p, dur, tmp, len(segs))
        segs.append(p)

    # ---- replace everything below with measured facts ----
    add([("Product Name", BLUE, 64, True, 250),
         ("one line on what it is", FG, 34, False, 340),
         ("the mechanism, three words", DIM, 26, False, 400)], 4)

    add([("$ the exact command that was run", GREEN, 26, True, 90),
         ("the actual output, verbatim, wrapped by hand", FG, 24, False, 150)], 5)

    # HONESTY FRAME - keep it. Numbers only, no hedging.
    add([("what is true today", AMBER, 30, True, 110),
         ("N callers in 7 days", FG, 28, False, 190),
         ("all of them crawlers", DIM, 26, False, 240),
         ("0 paid calls so far", FG, 28, False, 300)], 6)

    add([("the address", BLUE, 52, True, 260),
         ("what the buyer does, in three words", FG, 30, False, 340)], 5)
    # ---- end of frames ----

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", out],
                         capture_output=True, text=True).stdout.strip()
    print(f"wrote {out}  ({float(dur):.1f}s, {os.path.getsize(out)} bytes)")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
