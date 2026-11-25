#!/usr/bin/env python3
"""queue_patch_row.py — edit ONE build-queue row without re-encoding the file.

WHY THIS EXISTS
---------------
`json.dump()` over the whole queue rewrites every line: the file stores keys at two spaces, braces
at one, and a mix of literal em-dashes and \\uXXXX escapes that no single (indent, ensure_ascii) pair
reproduces. Measured, a 46-row pass written that way cost 4,341 changed lines; the same pass spliced
as raw text cost 871, and a single-row edit cost 7. The change is correct either way — only one of
them is reviewable.

So: locate the row's object span in the RAW TEXT, replace just that span, leave every other byte.

USAGE
    # preview (writes nothing)
    python3 queue_patch_row.py --path q.json --id '#112' --set-file fields.json --check

    # apply
    python3 queue_patch_row.py --path q.json --id '#112' --set-file fields.json

    # single field
    python3 queue_patch_row.py --path q.json --id 42 --set status=shipped

    # ALWAYS aim the first runs at a COPY (see SKILL.md: "Iterate on a COPY")

GUARDS (each one is a corrupted file that was paid for)
  * Braces are counted OUTSIDE string literals — a row's text may contain "{" (a URL template, an
    instruction), and counting it desynchronises the scan so one row is written over its neighbour.
  * The id is matched as JSON-EMITTED text, because ids are mixed-type: 15 (int), "rev-3" (quoted),
    "#106" (unquoted string). str() fails on the quoted ones.
  * A row may carry NO id at all (one superseded row has only _orig_id) — skipped, never matched.
  * Exactly ONE match is required; zero or two aborts.
  * The result is re-parsed BEFORE the write; a parse failure leaves the file untouched.
  * The span ends AT the closing brace, so the trailing comma stays outside it. Do not re-append it.
"""
from __future__ import annotations

import argparse
import json
import sys


def object_spans(text: str):
    """(start, end) of each top-level object, brace-counted outside of strings."""
    in_str = esc = False
    starts: list[int] = []
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            starts.append(i)
        elif ch == "}" and starts:
            st = starts.pop()
            if not starts:          # outermost object closed
                yield st, i + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="queue JSON (use a COPY while developing)")
    ap.add_argument("--id", required=True, help="row id exactly as it appears: 42, rev-3, #106")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="field to set; VALUE is parsed as JSON when it parses, else kept as text")
    ap.add_argument("--set-file", help="JSON object of fields to merge")
    ap.add_argument("--check", action="store_true", help="preview only, write nothing")
    a = ap.parse_args()

    raw = open(a.path, encoding="utf-8").read()
    rows = json.loads(raw)

    updates: dict = {}
    if a.set_file:
        updates.update(json.load(open(a.set_file, encoding="utf-8")))
    for spec in a.set:
        if "=" not in spec:
            return _die(f"bad --set {spec!r} (want key=value)")
        k, v = spec.split("=", 1)
        try:
            updates[k] = json.loads(v)
        except ValueError:
            updates[k] = v
    if not updates:
        return _die("nothing to set — pass --set or --set-file")

    hits = []
    for s, e in object_spans(raw):
        seg = raw[s:e]
        try:
            obj = json.loads(seg)
        except ValueError:
            continue
        # compare on the JSON-emitted id so int / quoted-string / bare-string all resolve
        if json.dumps(obj.get("id")) == json.dumps(a.id) or str(obj.get("id")) == a.id:
            hits.append((s, e, obj))
    if len(hits) != 1:
        return _die(f"expected exactly 1 row with id {a.id!r}, found {len(hits)} — refusing to write")

    s, e, obj = hits[0]
    before = {k: obj.get(k) for k in updates}
    obj.update(updates)

    if a.check:
        for k, v in updates.items():
            print(f"  would set {k}: {before[k]!r} -> {v!r}")
        print("  --check: nothing written")
        return 0

    # The span starts AT the row's opening brace; the brace's own leading spaces are outside
    # it and stay in raw[:s]. So the first emitted line must carry NO prefix, and every later
    # line must be shifted by the SAME amount as that brace — measured 2026-11-24: prefixing
    # every line by one space put keys at 3 while the file uses 4, so a one-row edit showed
    # up as a whole-row reformat.
    block = json.dumps(obj, indent=2, ensure_ascii=False)
    _line_start = raw.rfind("\n", 0, s) + 1
    _indent = " " * (s - _line_start)          # the brace's own column, e.g. 2
    _lines = block.splitlines()
    block = "\n".join([_lines[0]] + [_indent + ln for ln in _lines[1:]])
    new = raw[:s] + block + raw[e:]      # the trailing comma is outside the span — never re-append it

    parsed = json.loads(new)             # must parse BEFORE the write
    if len(parsed) != len(rows):
        return _die(f"row count changed {len(rows)} -> {len(parsed)} — refusing to write")

    with open(a.path, "w", encoding="utf-8") as fh:
        fh.write(new)

    print(f"updated {a.id}: {len(updates)} field(s)")
    for k, v in updates.items():
        print(f"  {k}: {str(before[k])[:60]!r} -> {str(v)[:60]!r}")
    return 0


def _die(msg: str) -> int:
    print(f"REFUSED — {msg}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
