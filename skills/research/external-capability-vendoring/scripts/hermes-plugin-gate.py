#!/usr/bin/env python3
"""hermes-plugin-gate — does OUR installed engine actually load this plugin?

WHY THIS EXISTS
  A plugin's README states a minimum platform version, and that claim is usually numbered against a
  DIFFERENT versioning scheme than the engine reports (a product marketing version like "1.70" versus an
  engine semver like "0.22.6"). Comparing them is not a comparison — so the compatibility question gets
  answered by guessing, and the guess becomes the reason not to test at all.

  The platform can answer it directly. Its loader has a discovery predicate and an import path; both are
  ordinary Python you can call against a cloned checkout in scratch. Run this BEFORE writing a gate verdict.

WHAT IT CHECKS (in order, each independent)
  1  discovery   — the engine's own predicate accepts the directory as a memory provider
  2  import      — the package imports the way the loader imports it (synthetic parent namespace)
  3  contract    — the provider class subclasses the engine's own MemoryProvider
  4  runtime     — every hook shells out to some helper; can that helper START?
  5  selftest    — does the plugin's own health/doctor check TEST anything, or only look for files?

  Steps 1-3 are code, and they pass or fail cleanly. Steps 4-5 are where adoptions actually die: a provider
  that registers perfectly and cannot serve one request, and a health check that reports ok while it cannot.

USAGE
  python3 hermes-plugin-gate.py /path/to/cloned-plugin            # steps 1-3 + runtime scan + health probe
  python3 hermes-plugin-gate.py /path/to/cloned-plugin --no-health

  Exit 0 = registers and looks runnable. Exit 1 = it does not register. Exit 2 = registers but is not usable.
  A non-zero exit is a FINDING here, not an instrument failure — the distinction is in the message.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import types

NS = "_hermes_user_memory"   # the synthetic parent namespace the loader registers for user plugins


def engine_root() -> pathlib.Path:
    for p in ("/opt/hermes",):
        if pathlib.Path(p).is_dir():
            return pathlib.Path(p)
    raise SystemExit("hermes-plugin-gate: no engine root found (expected /opt/hermes)")


def check_discovery(root: pathlib.Path, plugin: pathlib.Path):
    """Use the engine's own predicate. Never re-implement the heuristic — that tests your copy of the rule."""
    sys.path.insert(0, str(root))
    from plugins import memory as mem  # noqa: E402
    text_hit = mem._is_memory_provider_dir(plugin)
    ast_hit = mem._defines_memory_provider(plugin)
    return text_hit, ast_hit


def check_import(root: pathlib.Path, plugin: pathlib.Path):
    sys.path.insert(0, str(root))
    pkg = types.ModuleType(NS)
    pkg.__path__ = []
    sys.modules[NS] = pkg
    name = "gate_probe"
    spec = importlib.util.spec_from_file_location(
        f"{NS}.{name}", plugin / "__init__.py", submodule_search_locations=[str(plugin)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{NS}.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def check_contract(root: pathlib.Path, mod):
    from agent.memory_provider import MemoryProvider  # noqa: E402
    found = [(n, o) for n, o in vars(mod).items()
             if isinstance(o, type) and issubclass(o, MemoryProvider) and o is not MemoryProvider]
    return found


def scan_runtime(plugin: pathlib.Path):
    """Every hook routes through SOME subprocess. Find out which, and whether it can start."""
    bins, wrappers = set(), []
    for py in plugin.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(errors="replace", encoding="utf-8-sig"))
        except (SyntaxError, ValueError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 300:
                s = node.value
                if "command -v " in s:
                    bins.add(s.split("command -v ")[1].split()[0].strip("'\""))
    for cand in sorted(plugin.glob("scripts/*")):
        try:
            head = cand.read_text(errors="replace", encoding="utf-8-sig")[:400]
        except OSError:
            continue
        if head.startswith("#!") and "bash" in head.split("\n")[0]:
            wrappers.append(cand)
    return sorted(bins), wrappers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin")
    ap.add_argument("--no-health", action="store_true")
    a = ap.parse_args()

    plugin = pathlib.Path(a.plugin).resolve()
    if not (plugin / "__init__.py").exists():
        print(f"NOT A PLUGIN DIR — no __init__.py at {plugin}")
        return 1
    root = engine_root()

    print(f"engine   : {root}")
    print(f"plugin   : {plugin}")
    manifest = plugin / "plugin.yaml"
    if manifest.exists():
        print("manifest : " + " ".join(
            l.strip() for l in manifest.read_text(errors="replace").splitlines()[:3]))

    text_hit, ast_hit = check_discovery(root, plugin)
    print(f"\n1 discovery: text-heuristic={text_hit} ast-parse={ast_hit}")
    if not (text_hit or ast_hit):
        print("  FAIL — the engine will not see this as a memory provider.")
        return 1
    if text_hit and not ast_hit:
        print("  NOTE — discovery rests ONLY on the text heuristic (a class name appearing in __init__.py).")
        print("         It works today; a future engine that drops the heuristic drops this plugin. Say so.")

    try:
        mod = check_import(root, plugin)
    except Exception as e:
        print(f"\n2 import   : FAILED {type(e).__name__}: {str(e)[:200]}")
        return 1
    print("\n2 import   : OK")

    found = check_contract(root, mod)
    print(f"3 contract : {len(found)} MemoryProvider subclass(es) {[n for n, _ in found]}")
    if not found:
        print("  FAIL — imports, but exposes nothing the engine can register.")
        return 1

    bins, wrappers = scan_runtime(plugin)
    print(f"\n4 runtime  : wrappers={[w.name for w in wrappers]}")
    missing = [b for b in bins if shutil.which(b) is None]
    print(f"  required on PATH: {bins or '(none declared)'}")
    print(f"  MISSING          : {missing or '(none)'}")
    for w in wrappers:
        try:
            r = subprocess.run([str(w), "--version"], capture_output=True, text=True, timeout=60)
            first = (r.stdout + r.stderr).strip().splitlines()[:1]
            print(f"  {w.name} --version -> rc={r.returncode} {first}")
        except Exception as e:
            print(f"  {w.name} --version -> {type(e).__name__}: {str(e)[:80]}")
    if missing:
        print("  NOT USABLE YET — the hooks shell out through these; install or decline. "
              "A user-space runtime installs into a scratch prefix without root.")

    if not a.no_health and hasattr(mod, "health"):
        try:
            h = mod.health()
            print(f"\n5 selftest : health() -> {json.dumps(h)[:400]}")
            print("  READ THE KEYS IT CHECKS. If it only asserts that FILES EXIST, its ok:true says nothing")
            print("  about whether the plugin can serve a request — that is a false green, whatever it prints.")
            return 2 if missing else 0
        except Exception as e:
            print(f"\n5 selftest : health() raised {type(e).__name__}: {str(e)[:160]}")

    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
