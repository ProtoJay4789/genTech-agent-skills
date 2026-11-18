# Behaviour vs source — probing what a job actually does

Companion to the `The behaviour-inference class` rule in SKILL.md. Read this when an audit is making claims
about **runtime behaviour** (`this prints every run`, `this guard fires`, `this branch never runs`) rather than
about artifacts on disk.

## Why a static read is a hypothesis

A behaviour claim cites code, which makes it *look* like verification. It is not: it is the tool's reading of
the code. Measured, one audit produced **four false violations in a single sitting** against correct code — a
header-only read, two failed multi-line regexes, thin wrappers judged instead of their targets, and an 18-line
shim treated as a program. Every one was reported as a defect.

**A real defect is stable under better instruments. A parser artefact moves with the parser.** If findings keep
changing as you improve the parser while the artifacts never change, you are measuring the parser.

## The probe: run it twice, count bytes

For a question like *"does this job stay quiet when it has nothing to say?"*, the property IS an observation.

```python
import subprocess, sys

def probe(path, timeout=240):
    cmd = ["sh", path] if path.endswith(".sh") else [sys.executable, path]
    def once():
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd="/opt/data")
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            return 124, "TIMEOUT"
    rc1, out1 = once()          # the first run may legitimately report — it establishes state
    rc2, out2 = once()          # second run, nothing changed
    if not out2.strip():
        v = "SILENT"            # the property holds
    elif out1.strip() == out2.strip():
        v = "REPEATS-UNCHANGED"  # talks, and says the same thing twice — the real finding
    else:
        v = "CHANGES-EACH-RUN"   # it has something real and varying to say
    return {"script": path, "bytes1": len(out1), "bytes2": len(out2), "verdict": v}
```

**`REPEATS-UNCHANGED` is the finding.** Identical bytes on consecutive runs means the job is re-announcing a
condition nobody asked to hear twice.

**Safety:** only probe scripts that are read-only — state readers, linters, link checkers, report generators.
Never a job that writes a vault, calls a paid API, or moves money. Hard timeout on every run. An allowlist in
code is cheaper than a careful thought at the time and it survives the session.

## Following indirection — the wrong-file traps

Four false verdicts, four different wrong files:

| the artifact | why auditing it measures nothing | what to do |
|---|---|---|
| `exec python3 /path/real.py "$@"` | 3 lines; the logic is elsewhere | resolve the path, audit that |
| `runpy.run_path(CANONICAL)` | the shim is the pointer | parse `CANONICAL = "..."` |
| an 18-line shim with a long docstring | passes any `len(lines) > N` test | ask: does it FORWARD and print nothing itself? |
| a script whose gate is in the body | the docstring never mentions it | look for the exit, not the vocabulary |

```python
forward = bool(re.search(r"\b(exec|run_path|subprocess\.(run|call|check_output))\b", body))
prints = bool(re.search(r"^\s*(print\(|echo )", body, re.M))
if forward and not prints:
    path = follow_the_pointer(body)      # a wrapper, not a program
```

## Finding the gate without a clever regex

A gate is an exit under a condition. Shell and Python bodies are indented and the shapes vary, so a single
multi-line pattern fails silently and reports correct code as broken. Walk the lines instead:

```python
def has_gate(body: str) -> bool:
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if not re.search(r"(sys\.exit\(0\)|return 0|exit 0)\s*$", line.strip()):
            continue
        indent = len(line) - len(line.lstrip())
        for j in range(i - 1, max(-1, i - 25), -1):
            prev = lines[j]
            if prev.strip() and not prev.strip().startswith("#"):
                pind = len(prev) - len(prev.lstrip())
                if pind < indent:
                    return bool(re.match(r"\s*(if|elif)\b", prev))
    return False
```

## Let the probe override the parser

Maintain one instrument, not two opinions:

- static `VIOLATION` + probe `SILENT` → `PROBE-SAYS-SILENT` (do not act)
- static `VIOLATION` + probe `REPEATS-UNCHANGED` → `VIOLATION-REPEATS` (act)
- probe `UNKNOWN` (could not run) → never `clean`

**Print the downgrades.** A scan that silently drops its own hits leaves the next reader unable to tell which
of its verdicts are load-bearing.
