#!/usr/bin/env python3
"""Transcribe voice-note audio with faster-whisper, decoding via ffmpeg.

Why not let faster-whisper open the file itself: its decode_audio() calls
av.open(..., metadata_errors=...) which raises TypeError on some av builds.
Decoding to float32 via ffmpeg sidesteps the bundled decoder entirely and does
not depend on version pinning.

Usage:
    python3 transcribe-voice-note.py <audio> [<audio> ...]

Notes:
  - Model downloads on first use (~150 MB for base.en) and is cached in
    ~/.cache/whisper.
  - Works on .ogg/.opus (Telegram voice notes), .mp3, .m4a, .wav — anything
    ffmpeg can read.
  - Prints each file's transcript under a === header. "(no speech detected)"
    is a real result, not an error.
"""
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

MODEL = os.environ.get("WHISPER_MODEL", "base.en")


def load_audio(path: str, rate: int = 16000) -> np.ndarray:
    """Decode any audio ffmpeg understands to mono float32 at 16 kHz."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-f", "s16le", "-ac", "1", "-ar", str(rate), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 2

    model = WhisperModel(
        MODEL, device="cpu", compute_type="int8",
        download_root=os.path.expanduser("~/.cache/whisper"),
    )

    failures = 0
    for path in paths:
        print(f"\n=== {os.path.basename(path)} ===")
        if not os.path.exists(path):
            print(f"MISSING: {path}")
            failures += 1
            continue
        try:
            segments, _ = model.transcribe(load_audio(path), beam_size=5)
            text = " ".join(s.text.strip() for s in segments).strip()
            print(text if text else "(no speech detected)")
        except Exception as exc:  # noqa: BLE001 - report, never swallow
            print(f"FAILED: {type(exc).__name__}: {exc}")
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
