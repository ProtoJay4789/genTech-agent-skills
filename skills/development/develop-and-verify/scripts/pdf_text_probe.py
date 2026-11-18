#!/usr/bin/env python3
"""Prove what a generated PDF actually SAYS — read its own text layer, no external tools.

Why this exists: a PDF renderer prints a success message, and a success message is not the document.
The failures this catches, both real:

  1. **The renderer never read the input you gave it.** A script with a hardcoded source AND output path
     re-rendered the old document and printed `OK · 5,229 B`. The tell was a byte count IDENTICAL to the
     previous render — new content cannot produce the same bytes. Always compare size and mtime against
     the expectation, and probe for a phrase that ONLY the new content can contain.
  2. **The claim in the prose is not in the file.** A document said `fine-tuned` after the wording was
     corrected to something honest. Substring probes on the text layer catch a stale copy still being
     shipped (including the one already uploaded elsewhere).

Usage:
    pdf_text_probe.py FILE.pdf "phrase that must be present" [--absent "phrase that must be gone"]
    pdf_text_probe.py FILE.pdf --dump          # print the whole extracted text layer

Exit codes: 0 = every assertion held · 1 = an assertion failed · 2 = no text layer readable.

Method: inflate each `stream`, pull the `(...) Tj` show-text operators out of the content stream, and
join them. Enough for a text-first document produced by any normal PDF writer. This is a PROBE, not a
converter: it will not lay out columns or reproduce reading order for a scanned/image-only PDF — and an
image-only PDF returning almost no text is itself the finding (an ATS cannot read it either).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import zlib


STRING_OPS = re.compile(rb"\((?:[^()\\]|\\.)*\)\s*Tj")


def text_layer(pdf: pathlib.Path) -> str:
    raw = pdf.read_bytes()
    runs: list[str] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            body = zlib.decompress(m.group(1))
        except zlib.error:
            continue                    # not a Flate stream (font, image); skip it
        for op in STRING_OPS.findall(body):
            s = op[1:op.rfind(b")")].decode("latin-1", errors="ignore")
            runs.append(s.replace("\\(", "(").replace("\\)", ")"))
    return " ".join(runs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("must", nargs="*", help="phrases that must be PRESENT")
    ap.add_argument("--absent", nargs="*", default=[], help="phrases that must be ABSENT")
    ap.add_argument("--dump", action="store_true", help="print the extracted text layer")
    a = ap.parse_args()

    p = pathlib.Path(a.pdf)
    if not p.exists():
        print(f"  \U0001F534 no such file: {p}")
        return 2

    blob = text_layer(p)
    print(f"  {p.name}: {p.stat().st_size:,} B \u00b7 {len(blob):,} chars of text layer")

    if a.dump:
        print(blob)

    if not blob.strip():
        print("  \U0001F534 NO TEXT LAYER \u2014 image-only or unreadable; a parser sees nothing either")
        return 2

    failed = 0
    for phrase in a.must:
        ok = phrase in blob
        failed += 0 if ok else 1
        print(f"   {'\u2705 present ' if ok else '\U0001F534 MISSING '} {phrase!r}")
    for phrase in a.absent:
        ok = phrase not in blob
        failed += 0 if ok else 1
        print(f"   {'\u2705 absent  ' if ok else '\U0001F534 STILL THERE '} {phrase!r}")

    if not a.must and not a.absent and not a.dump:
        print("  (no assertions given \u2014 pass phrases, or --dump)")

    print(f"  {'ALL ASSERTIONS HELD' if failed == 0 else str(failed) + ' ASSERTION(S) FAILED'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
