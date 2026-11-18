#!/usr/bin/env python3
"""Minimal `unzip` shim for hosts without the real binary.

WHY: vendor install scripts (`curl -fsSL https://<vendor>/install | sh`) ship CLI bundles as zip and
shell out to `unzip`. When it is missing they fail at extraction with `unzip is required` — or worse,
with a confusing `FileNotFoundError` from whatever stub happens to be on PATH. Installing the real
package usually needs root, which a container agent does not have; a Python zipfile shim does the job.

USAGE
    mkdir -p /opt/data/tools/bin
    cp unzip-shim.py /opt/data/tools/bin/unzip && chmod +x /opt/data/tools/bin/unzip
    export PATH=/opt/data/tools/bin:$PATH      # must precede the installer
    curl -fsSL <vendor>/install | sh

⚠️ COMBINED SHORT FLAGS ARE THE TRAP. Installers routinely pass `-oqd <dir>` in one token, not
`-o -q -d <dir>`. A shim that only understands a bare `-d` treats `-oqd` as the archive name and dies
with `No such file or directory: '-oqd'`. Handle the combined form.
"""
from __future__ import annotations

import sys
import zipfile


def parse(argv: list[str]) -> tuple[str, str | None]:
    """Return (archive, dest) from unzip-style args, including combined short flags."""
    archive: str | None = None
    dest: str | None = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            i += 1
            continue
        if a.startswith("-") and a not in ("-", ""):
            flags = a[1:]
            if "d" in flags:
                # -d <dir> or a combined form like -oqd <dir>
                if i + 1 >= len(argv):
                    sys.exit("unzip shim: -d requires a directory")
                dest = argv[i + 1]
                i += 2
                continue
            i += 1  # -o, -q, -f, -n … nothing to do
            continue
        if archive is None:
            archive = a
        i += 1
    if archive is None:
        sys.exit("unzip shim: no archive given")
    return archive, dest


def main() -> int:
    archive, dest = parse(sys.argv[1:])
    try:
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest or ".")
    except FileNotFoundError:
        sys.exit(f"unzip shim: archive not found: {archive}")
    except zipfile.BadZipFile:
        sys.exit(f"unzip shim: not a zip archive: {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
