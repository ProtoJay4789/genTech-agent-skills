#!/usr/bin/env python3
"""Content-shape sweep for key material. Reports STRUCTURE only - never prints a value.

Why this exists: a sweep that selects candidates by FILENAME cannot find a key whose name is not
suggestive (deployer, rail-keys, bot-wallet, celo-rail-key). This selects on value SHAPE instead.

Usage:
    sweep-key-material.py ROOT [ROOT ...]        # report hits

Exit codes: 0 = no hits, 1 = hits found, 2 = nothing readable (coverage failure, NOT a clean result).
"""
import os
import re
import sys

# Anchored so common false positives do not fire: a 64-hex inside a longer run, or one that is
# part of a 0x-address, is not a raw private key on its own.
RAW_HEX = re.compile(r"(?<![0-9a-fA-Fx])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
PEM = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")
# 12 or 24 lowercase words separated by spaces - the mnemonic shape, not prose.
MNEMONIC = re.compile(r"\b(?:[a-z]{3,8}\s+){11,23}[a-z]{3,8}\b")
SECRET_ASSIGN = re.compile(
    r"(?i)(private[_-]?key|secret|mnemonic|seed[_-]?phrase|passphrase)\s*[:=]\s*\S{16,}"
)

SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".tgz", ".bz2", ".xz", ".woff", ".woff2", ".ttf", ".otf", ".mp3",
    ".mp4", ".mov", ".wav", ".splat", ".pack", ".idx", ".so", ".dylib", ".pyc",
}
SKIP_DIR = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}
MAX_BYTES = 2_000_000

# A hit in a file that also talks about keys is stronger; a lone 64-hex is weaker. Report both,
# ranked - never discard, because the weak signal is sometimes the finding.
KEY_CONTEXT = re.compile(r"(?i)(private|secret|mnemonic|seed|passphrase|key|custody|wallet)")


def iter_text_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SKIP_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield path


def classify(path):
    try:
        with open(path, "r", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return None
    kinds = []
    if PEM.search(text):
        kinds.append("PEM-PRIVATE-KEY")
    if RAW_HEX.search(text):
        kinds.append("RAW-64HEX")
    if MNEMONIC.search(text):
        kinds.append("MNEMONIC-SHAPE")
    if SECRET_ASSIGN.search(text):
        kinds.append("SECRET-ASSIGNMENT")
    if not kinds:
        return None
    return kinds, bool(KEY_CONTEXT.search(text))


def main(argv):
    roots = [a for a in argv if not a.startswith("--")]
    if not roots:
        print(__doc__)
        return 2
    scanned = 0
    hits = []
    for root in roots:
        if not os.path.isdir(root):
            print(f"  UNREADABLE (not a directory): {root}", file=sys.stderr)
            continue
        for path in iter_text_files(root):
            scanned += 1
            found = classify(path)
            if found:
                kinds, ctx = found
                hits.append((path, kinds, ctx))

    print(f"\nfiles scanned : {scanned}")
    print("criterion     : CONTENT SHAPES - bare 64-hex, PEM 'BEGIN ... PRIVATE KEY', mnemonic shape, secret assignment")
    if scanned == 0:
        print("\n!! NOTHING WAS READ - this is a COVERAGE FAILURE, not a clean result.")
        return 2
    if not hits:
        print("\nno hits. This negative covers the CONTENT-SHAPE field only.")
        print("Falsify it: plant a 64-hex line in a file under these roots and confirm this goes RED.")
        return 0
    print(f"\n{len(hits)} file(s) with key-shaped content (values NOT printed):\n")
    for path, kinds, ctx in sorted(hits, key=lambda h: (not h[2], h[0])):
        strength = "STRONG (key context nearby)" if ctx else "weak (shape only - check context)"
        print(f"  [{strength}] {path}")
        print(f"      kinds: {', '.join(kinds)}")
    print("\nNext: classify each WITHOUT printing the value; derive the address from any candidate key")
    print("and compare to its stored address; check live balance before calling it benign.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
