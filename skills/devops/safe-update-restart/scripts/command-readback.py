#!/usr/bin/env python3
"""command-readback — refuse to hand a human a command that is not complete.

WHY: a `docker run` handed over as a skeleton with `...` for the image and volume args was pasted
verbatim. Docker read `...` as the IMAGE NAME -> `invalid reference format`. Because the line ABOVE it
was `docker rm -f <svc>`, and that had already SUCCEEDED, the service went from running to absent with
no replacement. The instruction punished the reader who followed it exactly -- which is the correct way
to follow a pasted command.

THE RULES THIS ENFORCES
  1. A command handed to a human must already be runnable: no ellipsis, no <placeholder>, no bare $VAR
     the reader must fill in.
  2. A DESTRUCTIVE verb must not precede a CONSTRUCTIVE one in the same command. `rm` then `run` is a
     one-step outage; the safe shape is build-under-a-temp-name -> verify -> swap.

USAGE
  python3 command-readback.py --file cmd.txt      # a runbook; scans only fenced code blocks
  echo '<command>' | python3 command-readback.py  # a single block
  python3 command-readback.py --selftest          # 9 cases, both directions

EXIT
  0  clean, safe to hand over
  1  a blocking defect found (message says which, and what to do)
  2  could not read input -- UNKNOWN, not clean
"""
from __future__ import annotations

import argparse
import re
import sys

# An ellipsis used as an ARGUMENT (standing alone as a token), not inside prose or a numeric range.
ELLIPSIS = [
    (re.compile(r"(^|\s)\.\.\.(\s|$)", re.M), "bare `...` used as an argument"),
    (re.compile(r"(^|\s)…(\s|$)", re.M), "bare `…` used as an argument"),
]
# Angle-bracket placeholders a reader is expected to substitute. Excludes shell redirection and HTML tags.
PLACEHOLDER = [
    (re.compile(r"(?<![\w>])<([a-z][a-z0-9 _-]{1,30})>(?![\w<])", re.I),
     "`<placeholder>` the reader must fill in"),
]
BARE_VAR = re.compile(r"(?<!\\)\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")

DESTRUCTIVE = re.compile(r"\bdocker\s+(rm|kill|stop)\b|\brm\s+-[rf]|\bmv\s+\S+\s+/dev/null", re.I)
CONSTRUCTIVE = re.compile(r"\bdocker\s+(run|start|create)\b|\bdocker\s+compose\s+up", re.I)

# Words legitimate in angle brackets that are markup, not placeholders.
ALLOW = {"head", "html", "body", "div", "span", "br", "p", "a", "code", "pre",
         "strong", "em", "table", "tr", "td", "th", "title", "style", "script"}


def check(text: str) -> list[tuple[str, str]]:
    """Return [(severity, message)] where severity is 'FAIL' or 'WARN'."""
    out: list[tuple[str, str]] = []
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]

    for i, ln in enumerate(lines, 1):
        for rx, msg in ELLIPSIS:
            if rx.search(ln):
                out.append(("FAIL", f"line {i}: {msg} — docker/shell reads it as an argument. "
                                    f"Supply the real value or do not hand this over."))
        for rx, msg in PLACEHOLDER:
            for m in rx.finditer(ln):
                if m.group(1).strip().lower() in ALLOW:
                    continue
                out.append(("FAIL", f"line {i}: {msg} -> `{m.group(0)}`. "
                                    f"An unsubstituted placeholder runs, and does the wrong thing."))
        for m in BARE_VAR.finditer(ln):
            name = m.group(1)
            if name in {"HOME", "PATH", "USER", "PWD", "SHELL", "TMPDIR", "?"}:
                continue
            if re.search(rf"\b{re.escape(name)}\s*=", text):
                continue
            out.append(("WARN", f"line {i}: `${name}` is used but never set in this command — "
                                f"if it is empty the command still runs, silently wrong."))

    body = "\n".join(lines)
    d = DESTRUCTIVE.search(body)
    c = CONSTRUCTIVE.search(body)
    if d and c and body.find(d.group(0)) < body.find(c.group(0)):
        out.append(("FAIL",
                    f"destructive step (`{d.group(0).strip()}`) comes BEFORE the constructive one "
                    f"(`{c.group(0).strip()}`). If the second fails, the first has already happened. "
                    f"Build under a temporary name, verify, then swap."))
    return out


def selftest() -> int:
    cases = [
        ("bare ellipsis after rm -f (the real outage)", """docker rm -f svc
docker run -d --name svc -e X=/y ...""", 2),
        ("clean, complete command", """docker run -d --name svc --restart unless-stopped \\
  -v /host/app:/app -e X=/logs img:latest server.py""", 0),
        ("placeholder the reader must fill", "docker run -d --name app <image> server.py", 1),
        ("remove-then-build is the outage", """docker rm -f svc
docker run -d --name svc img:latest server.py""", 1),
        ("constructive only is fine", "docker run -d --name svc img:latest server.py", 0),
        ("build-then-verify-then-swap is fine", """docker run -d --name svc-new img:latest server.py
docker exec svc-new curl -sf localhost:8090/robots.txt
docker rm -f svc && docker rename svc-new svc""", 0),
        ("html tags are not placeholders", "echo '<div class=\"x\">hi</div>' > /tmp/a.html", 0),
        ("unset variable is a warning", "docker run -d --name svc $IMAGE", 0),
        ("variable set above is accepted", "IMAGE=img:latest\ndocker run -d --name svc $IMAGE", 0),
    ]
    bad = 0
    for name, text, want in cases:
        fails = [f for f in check(text) if f[0] == "FAIL"]
        ok = len(fails) == want
        print(f"  {'OK  ' if ok else 'FAIL'} {name:<44} expected {want} FAIL, got {len(fails)}")
        if not ok:
            bad += 1
            for sev, msg in check(text):
                print(f"        -> {sev}: {msg[:104]}")
    print(f"\n  {len(cases)-bad}/{len(cases)} selftest cases pass")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.file:
        try:
            text = open(a.file, encoding="utf-8").read()
        except Exception as e:  # noqa: BLE001
            print(f"CANNOT READ {a.file}: {type(e).__name__} — UNKNOWN, not clean", file=sys.stderr)
            return 2
    else:
        if sys.stdin.isatty():
            print("no input: pipe a command in, or pass --file", file=sys.stderr)
            return 2
        text = sys.stdin.read()

    if not text.strip():
        print("EMPTY input — UNKNOWN, not clean", file=sys.stderr)
        return 2

    # A MARKDOWN FILE IS NOT A COMMAND. Flagging angle brackets in prose trains the reader to ignore
    # the gate. If fenced code blocks exist, scan ONLY those.
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    if blocks:
        text = "\n".join(blocks)
        if not text.strip():
            print("fenced blocks present but empty — UNKNOWN, not clean", file=sys.stderr)
            return 2

    findings = check(text)
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]

    for sev, msg in findings:
        print(f"  {sev}: {msg}")

    if fails or (a.strict and warns):
        print(f"\n  🔴 DO NOT HAND THIS OVER — {len(fails)} blocking defect(s).")
        return 1
    if warns:
        print(f"\n  🟠 passes, with {len(warns)} warning(s) — a human should still read it.")
        return 0
    print("  ✅ clean — runnable as written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
