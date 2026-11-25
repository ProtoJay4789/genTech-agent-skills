#!/usr/bin/env python3
"""policy-guard — platform terms and limits as something that can FAIL.

The GitHub suspension of 2026-09-16 was not caused by ignorance. AUP §9 was
public, quotable and findable. It was caused by nobody watching, and by every
local check being a *warning* rather than a *gate*.

This tool is the gate. It does three things and refuses to fake any of them:

  snapshot    Read each platform's terms, record the source URL, the date it was
              read, and a content hash. Compare against the last snapshot and
              speak when the text moved. If it cannot read a page it says
              UNKNOWN — silence is never consent.

  preflight   Measure the real facts of the action about to be taken (repo .git
              size, tracked media, largest tracked file, push cadence) and
              compare them to the recorded limits. A breached HARD limit exits 1
              and the action must not proceed. A hard limit that CANNOT be
              measured from here also exits 1 — unless a human acknowledges that
              exact limit id with --ack, which is recorded in the output.

              Actions: push (measure a repo), repo-create, publish (a listing or
              submission — nothing local to measure, so every hard limit must be
              acknowledged by id).

  status      What we have actually read, and when. Unread platforms are listed
              as unread, not omitted.

EXIT CODES (every subcommand):
  0  PASS / unchanged / acknowledged
  1  REFUSE / terms changed — do not proceed until a human has read this
  2  UNKNOWN — could not measure or could not read. NOT a pass. Fails closed.

Stdlib only. No third-party packages.
"""

import argparse
import difflib
import hashlib
import html as html_mod
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

EXIT_PASS, EXIT_REFUSE, EXIT_UNKNOWN = 0, 1, 2
MIB = 1024 * 1024
DEFAULT_STATE = "/opt/data/.obsidian-vault/00-HQ/policy-snapshots"
DEFAULT_REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "platforms", "registry.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) gentech-policy-guard/1.0"

# Extension-based. The aggregate bound (.git size) is what catches the rest —
# a media file renamed to .dat is still counted by repo_git_size.
MEDIA_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".ico", ".svgz",
    ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v",
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".aiff",
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz",
    ".pdf", ".onnx", ".pt", ".pth", ".safetensors", ".ckpt", ".bin", ".model",
    ".sqlite", ".db", ".mp4a", ".psd", ".ai", ".blend1",
}


class GuardError(Exception):
    """A condition that must never be silently swallowed."""


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(msg=""):
    print(msg)


def unknown(msg):
    say(f"UNKNOWN  {msg}")
    return EXIT_UNKNOWN


def sha256(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


# ---------------------------------------------------------------- registry


def load_registry(path):
    if not os.path.exists(path):
        raise GuardError(f"registry not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            reg = json.load(fh)
        except json.JSONDecodeError as exc:
            raise GuardError(f"registry is not valid JSON: {exc}")
    platforms = reg.get("platforms") or {}
    if not platforms:
        # An empty container makes every per-key validator pass. Refuse the whole
        # run rather than report health for a registry nobody loaded.
        raise GuardError("registry contains ZERO platforms — refusing to report health")
    return reg


# ---------------------------------------------------------------- fetching / text


_TAG = re.compile(r"<[^>]+>")
_DROP = re.compile(r"<(script|style|svg|nav|header|footer)\b.*?</\1>", re.I | re.S)


def normalize_html(raw):
    """Reduce a page to comparable prose. Nav/script/style are dropped so that a
    chrome change does not read as a policy change — but anything left is hashed
    verbatim, so a real edit can never hide."""
    text = _DROP.sub(" ", raw)
    text = _TAG.sub(" ", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch(url, timeout=25):
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                raw = body.decode(charset, "replace")
            except LookupError:
                raw = body.decode("utf-8", "replace")
            return {"ok": True, "http": resp.status, "bytes": len(body), "raw": raw}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "http": exc.code, "bytes": 0, "raw": "",
                "error": f"HTTP {exc.code}"}
    except Exception as exc:  # transport, DNS, TLS, timeout
        return {"ok": False, "http": 0, "bytes": 0, "raw": "",
                "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------- git measurement


def _run(args, cwd=None):
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180)
    return proc.returncode, proc.stdout, proc.stderr


def _git_dir_mib(repo):
    gd = os.path.join(repo, ".git")
    if os.path.isfile(gd):
        with open(gd, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.read().strip()
        if line.startswith("gitdir:"):
            target = line.split(":", 1)[1].strip()
            gd = target if os.path.isabs(target) else os.path.join(repo, target)
    rc, out, _ = _run(["git", "-C", repo, "rev-parse", "--is-bare-repository"])
    if rc == 0 and out.strip() == "true":
        gd = repo
    if not os.path.isdir(gd):
        raise GuardError(f"no .git directory found for {repo}")
    total = 0
    for root, _dirs, files in os.walk(gd):
        for name in files:
            path = os.path.join(root, name)
            try:
                total += os.path.getsize(path)
            except OSError:
                continue
    return total / MIB


def measure_repo(repo):
    """Measure the facts a push would expose. Raises GuardError — never returns a
    half-filled dict that a caller could mistake for a clean result."""
    if not os.path.isdir(repo):
        raise GuardError(f"repo path does not exist: {repo}")
    rc, _out, err = _run(["git", "-C", repo, "rev-parse", "--git-dir"])
    if rc != 0:
        raise GuardError(f"not a git repository: {repo} ({err.strip()[:120]})")

    m = {"repo": os.path.abspath(repo), "git_dir_mib": round(_git_dir_mib(repo), 2)}

    rc, out, err = _run(["git", "-C", repo, "ls-tree", "-r", "-l", "-z", "--full-tree", "HEAD"])
    entries = []
    if rc == 0:
        for chunk in out.split("\0"):
            if not chunk:
                continue
            try:
                meta, path = chunk.split("\t", 1)
            except ValueError:
                continue
            parts = meta.split()
            if len(parts) < 4:
                continue
            try:
                size = int(parts[3])
            except ValueError:
                continue  # submodule / tree
            entries.append((path, size))
    else:
        # No HEAD (empty repo) — fall back to the index, and say so rather than
        # reporting zero files as if the repository were empty on purpose.
        rc2, out2, _ = _run(["git", "-C", repo, "ls-files", "-z"])
        if rc2 == 0:
            for path in out2.split("\0"):
                if path:
                    try:
                        entries.append((path, os.path.getsize(os.path.join(repo, path))))
                    except OSError:
                        entries.append((path, 0))
            m["measured_from"] = "index (no HEAD)"
        else:
            raise GuardError(f"could not list tracked files in {repo}")

    media = [(p, s) for p, s in entries if os.path.splitext(p)[1].lower() in MEDIA_EXTS]
    largest = max(entries, key=lambda x: x[1]) if entries else ("", 0)

    m["tracked_files"] = len(entries)
    m["tracked_media_files"] = len(media)
    m["tracked_media_mib"] = round(sum(s for _p, s in media) / MIB, 2)
    m["media_sample"] = [p for p, _s in sorted(media, key=lambda x: -x[1])[:10]]
    m["largest_tracked_file_mib"] = round(largest[1] / MIB, 3)
    m["largest_tracked_file"] = largest[0]
    m["measured_from"] = m.get("measured_from", "HEAD")

    rc, out, _ = _run(["git", "-C", repo, "log", "--since=24.hours", "--format=%an%x09%s"])
    lines = [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []
    m["commits_last_24h"] = len(lines)
    m["committers_24h"] = sorted({ln.split("\t", 1)[0] for ln in lines})
    m["commit_subjects_24h"] = [ln.split("\t", 1)[-1] for ln in lines[:5]]

    rc, out, _ = _run(["git", "-C", repo, "rev-parse", "--short", "HEAD"])
    m["head"] = out.strip() if rc == 0 else "(none)"
    return m


# ---------------------------------------------------------------- snapshot


def snapshot_path(state_dir, platform):
    return os.path.join(state_dir, f"{platform}.json")


def build_snapshot(platform, entry):
    snap = {
        "schema": 1,
        "platform": platform,
        "display": entry.get("display", platform),
        "read_at": now_iso(),
        "terms": [],
    }
    for term in entry.get("terms") or []:
        rec = {
            "id": term["id"],
            "title": term.get("title", term["id"]),
            "url": term["url"],
            "kind": term.get("kind", "terms"),
        }
        got = fetch(term["url"])
        if not got["ok"]:
            rec.update({"status": "unreadable", "error": got.get("error", "fetch failed"),
                        "http": got.get("http", 0)})
        else:
            text = normalize_html(got["raw"])
            if len(text) < 200:
                # A page that fetched but carries no prose is not a readable
                # policy page (JS shell, block page, redirect stub).
                rec.update({"status": "unreadable", "http": got["http"],
                            "error": f"only {len(text)} chars of prose after normalization — cannot verify content"})
            else:
                rec.update({
                    "status": "ok",
                    "http": got["http"],
                    "bytes": got["bytes"],
                    "chars": len(text),
                    "raw_sha256": sha256(got["raw"]),
                    "text_sha256": sha256(text),
                    "snippet": text[:600],
                })
        snap["terms"].append(rec)
    return snap


def cmd_snapshot(args):
    reg = load_registry(args.registry)
    platforms = reg["platforms"]
    targets = list(platforms) if args.all else [args.platform]
    rc_worst = EXIT_PASS
    changed_any = False
    compared_any = False
    uncovered = []

    for pid in targets:
        if pid not in platforms:
            say(f"UNKNOWN  platform '{pid}' is not in the registry")
            rc_worst = max(rc_worst, EXIT_UNKNOWN)
            continue
        entry = platforms[pid]
        if not entry.get("terms"):
            if args.allow_unread:
                # Recorded coverage gap, not a new failure. The verdict below still
                # counts it as NOT COVERED so a reader cannot mistake exit 0 for
                # "every platform was read".
                uncovered.append(pid)
                say(f"NOT COVERED  {pid}: registry records ZERO terms sources — never read.")
                if entry.get("candidates"):
                    say("             probed candidates on record:")
                    for cand in entry["candidates"]:
                        say(f"               {cand.get('http')}  {cand['url']}  — {cand.get('note','')}")
                continue
            say(f"UNKNOWN  {pid}: registry records ZERO terms sources — nothing to read.")
            say("         This is the honest state: we have not read this platform's terms.")
            if entry.get("candidates"):
                say("         Probed candidates on record:")
                for cand in entry["candidates"]:
                    say(f"           {cand.get('http')}  {cand['url']}  — {cand.get('note','')}")
            rc_worst = max(rc_worst, EXIT_UNKNOWN)
            continue

        snap = build_snapshot(pid, entry)
        path = snapshot_path(args.state, pid)
        previous = None
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    previous = json.load(fh)
            except json.JSONDecodeError:
                previous = None

        diffs = diff_snapshots(previous, snap)
        say(f"── {pid} ({entry.get('display', pid)}) — read {snap['read_at']}")
        for term in snap["terms"]:
            if term["status"] != "ok":
                say(f"   🔴 {term['title']}: UNREADABLE — {term['error']}")
                say(f"      {term['url']}")
                rc_worst = max(rc_worst, EXIT_UNKNOWN)
            else:
                say(f"   ✅ {term['title']} — {term['chars']} chars, sha {term['text_sha256'][:12]}")

        if previous is None:
            say("   first snapshot for this platform (no baseline to compare)")
        elif diffs["changed"]:
            compared_any = True
            changed_any = True
            say("   ⚠️  TERMS CHANGED since the last snapshot — read the source before relying on it:")
            for item in diffs["changed"]:
                say(f"      · {item['title']}  {item['url']}")
        elif diffs["unreadable"]:
            compared_any = True
            say("   ⚠️  comparison INCOMPLETE — a page was unreadable this run or last, so"
                " 'unchanged' cannot be claimed")
            rc_worst = max(rc_worst, EXIT_UNKNOWN)
        else:
            compared_any = True
            say("   unchanged since last snapshot")

        if args.update:
            os.makedirs(args.state, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(snap, fh, indent=2)
                fh.write("\n")
            say(f"   written: {path}")

        if changed_any:
            rc_worst = max(rc_worst, EXIT_REFUSE)

    tail = (f" · NOT COVERED: {', '.join(uncovered)} "
            f"({len(uncovered)} platform(s) never read — this is a gap, not a pass)") if uncovered else ""
    if changed_any:
        say(f"\nVERDICT: CHANGED — a human must read the diff before this platform is relied on.{tail}")
    elif rc_worst == EXIT_UNKNOWN:
        say(f"\nVERDICT: UNKNOWN — not every page could be read. This is not 'unchanged'.{tail}")
    elif not compared_any:
        say(f"\nVERDICT: BASELINE — first snapshot written. Nothing has been compared yet,"
            f" so this is NOT a claim that the terms are unchanged.{tail}")
    else:
        say(f"\nVERDICT: unchanged where read.{tail}")
    return rc_worst


def diff_snapshots(previous, current):
    out = {"changed": [], "unreadable": [], "added": [], "removed": []}
    if not previous:
        return out
    prev = {t["id"]: t for t in previous.get("terms", [])}
    cur = {t["id"]: t for t in current.get("terms", [])}
    for tid, t in cur.items():
        if tid not in prev:
            out["added"].append(t)
            continue
        if t.get("status") != "ok" or prev[tid].get("status") != "ok":
            out["unreadable"].append(t)
            continue
        if t["text_sha256"] != prev[tid].get("text_sha256"):
            out["changed"].append(t)
    for tid, t in prev.items():
        if tid not in cur:
            out["removed"].append(t)
    return out


# ---------------------------------------------------------------- preflight


def snapshot_age_days(snap):
    try:
        read = datetime.strptime(snap["read_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        return None
    return (datetime.now(timezone.utc) - read).total_seconds() / 86400.0


def cmd_preflight(args):
    reg = load_registry(args.registry)
    platforms = reg["platforms"]

    if args.platform not in platforms:
        return unknown(f"platform '{args.platform}' has no registry entry — no limits are on record")
    entry = platforms[args.platform]

    # 1. Has anyone actually read this platform's terms?
    path = snapshot_path(args.state, args.platform)
    if not os.path.exists(path):
        return unknown(
            f"{args.platform}: terms have NEVER been read (no snapshot at {path}). "
            "Silence is not consent — run `policy-guard snapshot` first.")
    with open(path, "r", encoding="utf-8") as fh:
        snap = json.load(fh)

    unreadable = [t for t in snap.get("terms", []) if t.get("status") != "ok"]
    if unreadable:
        return unknown(
            f"{args.platform}: {len(unreadable)} terms page(s) unreadable in the last snapshot "
            f"({', '.join(t['title'] for t in unreadable)}). Terms we cannot read are terms we cannot rely on.")

    age = snapshot_age_days(snap)
    if age is None:
        return unknown(f"{args.platform}: snapshot has no parseable read_at — cannot judge freshness")
    if age > args.max_age_days:
        return unknown(
            f"{args.platform}: terms snapshot is {age:.0f} days old (limit {args.max_age_days}). "
            "Re-run `policy-guard snapshot --update`.")

    # 2. Measure the action.
    say(f"── preflight · {args.platform} · action={args.action} · terms read {snap['read_at']} ({age:.0f}d ago)")
    m = {}
    if args.action == "push":
        if not args.repo:
            return unknown("action 'push' requires --repo")
        try:
            m = measure_repo(args.repo)
        except GuardError as exc:
            return unknown(f"could not measure the repository: {exc}")
        say(f"   repo        {m['repo']}  @ {m['head']}")
        say(f"   .git        {m['git_dir_mib']:.2f} MiB")
        say(f"   tracked     {m['tracked_files']} files; media {m['tracked_media_files']}"
            f" / {m['tracked_media_mib']:.2f} MiB")
        say(f"   largest     {m['largest_tracked_file_mib']:.3f} MiB  {m['largest_tracked_file']}")
        say(f"   last 24h    {m['commits_last_24h']} commit(s)"
            + (f" by {', '.join(m['committers_24h'])}" if m["committers_24h"] else ""))
        if m["media_sample"]:
            for p in m["media_sample"][:5]:
                say(f"      media → {p}")
    elif args.action == "repo-create":
        say("   repo        n/a (action creates a new repo; nothing is in it yet)")
    elif args.action == "publish":
        say("   action      publish — a listing or submission to this platform; there is no")
        say("               local artifact to measure, so every limit must be acknowledged by id")
    else:
        return unknown(f"unknown action '{args.action}'")

    # 3. Evaluate.
    acked = {x.strip() for x in (args.ack or "").split(",") if x.strip()}
    breaches, warnings, unmeasured, evaluated = [], [], [], []
    for lim in entry.get("limits") or []:
        measure = lim.get("measure")
        if not measure or measure not in m:
            # Either the registry declares no machine-checkable measure for it, or
            # this action cannot expose it. Both mean: we cannot prove it here.
            unmeasured.append(lim)
            continue
        actual = m[measure]
        evaluated.append(lim)
        fired = actual > lim["value"] if lim.get("op", ">") == ">" else actual < lim["value"]
        if not fired:
            continue
        line = {
            "limit": lim, "actual": actual,
            "detail": f"{lim['id']}: {actual} {lim['unit']} vs limit {lim['value']} {lim['unit']}",
        }
        (breaches if lim.get("severity") == "hard" else warnings).append(line)

    # A hard limit we cannot measure is NOT a pass. It is a refusal unless a human
    # has acknowledged that specific limit by id for this run — which is the whole
    # difference between "we checked" and "we scrolled past a warning".
    for lim in unmeasured:
        if lim.get("severity") == "hard" and lim["id"] not in acked:
            breaches.append({
                "limit": lim, "actual": None,
                "detail": (f"{lim['id']}: hard limit is not machine-checkable from here "
                           f"and has not been acknowledged (--ack {lim['id']})"),
            })
    acked_shown = [lim for lim in unmeasured if lim["id"] in acked]

    if warnings:
        say("")
        for item in warnings:
            lim = item["limit"]
            say(f"   ⚠️  WARN  {item['detail']}")
            if lim.get("rule_ref"):
                say(f"      rule: {lim['rule_ref']}")

    if unmeasured:
        say("")
        for lim in unmeasured:
            if lim["id"] in acked:
                tail = "acknowledged for this run by the operator"
            elif lim.get("severity") == "hard":
                tail = f"BLOCKS — acknowledge with --ack {lim['id']} once you have read it"
            else:
                tail = "not counted as a pass; not blocking"
            say(f"   ◻️  NOT MACHINE-CHECKABLE  {lim['id']} — {tail}")

    for um in entry.get("unmeasured") or []:
        say(f"   ◻️  NOT MEASURED  {um['id']} — {um['why']}")

    if breaches:
        say("")
        for item in breaches:
            lim = item["limit"]
            say(f"   🛑 REFUSE  {item['detail']}  [{lim.get('enforced_by','platform')}]")
            if lim.get("quote"):
                say(f"      “{lim['quote']}”")
            if lim.get("source"):
                src = next((t for t in entry["terms"] if t["id"] == lim["source"]), None)
                if src:
                    say(f"      source: {src['url']}")
            if lim.get("rule_ref"):
                say(f"      rule: {lim['rule_ref']}")
        say(f"\nVERDICT: REFUSE — {len(breaches)} hard limit(s) not satisfied. Do not proceed.")
        return EXIT_REFUSE

    if not evaluated:
        if acked_shown:
            say("")
            say(f"VERDICT: ACKNOWLEDGED — 0 limits were machine-checkable for action "
                f"'{args.action}'; {len(acked_shown)} hard limit(s) confirmed by hand this run: "
                f"{', '.join(lim['id'] for lim in acked_shown)}.")
            say("         This is a recorded human acknowledgement, not a measurement.")
            return EXIT_PASS
        return unknown("no limit could be evaluated against this action — refusing to call that a pass")

    say(f"\nVERDICT: PASS — {len(evaluated)} limit(s) evaluated, none breached."
        + (f" {len(acked_shown)} further hard limit(s) acknowledged by hand." if acked_shown else ""))
    return EXIT_PASS


# ---------------------------------------------------------------- status / compare


def cmd_status(args):
    reg = load_registry(args.registry)
    say(f"{'PLATFORM':<18} {'TERMS':<11} {'LIMITS':<7} {'LAST READ':<22} AGE")
    unread = 0
    for pid, entry in reg["platforms"].items():
        n_terms = len(entry.get("terms") or [])
        n_limits = len(entry.get("limits") or [])
        path = snapshot_path(args.state, pid)
        if not os.path.exists(path):
            say(f"{pid:<18} {'NEVER READ' if n_terms else 'none found':<11} {n_limits:<7} {'—':<22} —")
            unread += 1
            continue
        with open(path, "r", encoding="utf-8") as fh:
            snap = json.load(fh)
        age = snapshot_age_days(snap)
        bad = sum(1 for t in snap.get("terms", []) if t.get("status") != "ok")
        state = f"{len(snap.get('terms', []))} ok" if not bad else f"{bad} UNREADABLE"
        say(f"{pid:<18} {state:<11} {n_limits:<7} {snap.get('read_at','—'):<22} {age:.0f}d")
    if unread:
        say(f"\n{unread} platform(s) with no verified terms snapshot. preflight will refuse them (exit 2).")
    return EXIT_PASS


def cmd_compare(args):
    """Offline comparison of two normalized texts — used by the selftest to prove
    change detection without depending on a live page moving."""
    def load(p):
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return normalize_html(fh.read())
    a, b = load(args.a), load(args.b)
    if sha256(a) == sha256(b):
        say("SAME — normalized content is identical")
        return EXIT_PASS
    say("CHANGED — normalized content differs")
    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), "before", "after", lineterm="", n=1))
    for line in diff[:40]:
        say(f"   {line}")
    return EXIT_REFUSE


# ---------------------------------------------------------------- selftest


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=120)


def _init_repo(path):
    os.makedirs(path, exist_ok=True)
    _git(["init", "-q"], path)
    _git(["config", "user.email", "selftest@local"], path)
    _git(["config", "user.name", "selftest"], path)
    return path


def _commit(path, files):
    for name, content in files.items():
        full = os.path.join(path, name)
        os.makedirs(os.path.dirname(full) or path, exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(full, mode) as fh:
            fh.write(content)
    _git(["add", "-A"], path)
    _git(["commit", "-q", "-m", "fixture"], path)


def cmd_selftest(args):
    """Prove BOTH directions, and prove the RIGHT limit fired — not merely that
    something exited non-zero. A guard whose refusal is not attributable is
    indistinguishable from a guard that refuses everything."""
    here = os.path.dirname(os.path.abspath(__file__))
    me = os.path.abspath(__file__)
    results = []

    def run(argv, expect, label, expect_text=None):
        proc = subprocess.run([sys.executable, me] + argv, capture_output=True, text=True)
        blob = proc.stdout + proc.stderr
        ok = proc.returncode == expect
        if ok and expect_text and expect_text not in blob:
            ok = False
        results.append((ok, label, expect, proc.returncode))
        say(f"   {'PASS' if ok else 'FAIL'}  {label}  (exit {proc.returncode}, expected {expect})")
        if not ok:
            if expect_text and expect_text not in blob:
                say(f"         | expected the refusal to name '{expect_text}' and it did not")
            for line in blob.strip().splitlines()[-6:]:
                say(f"         | {line}")
        return ok

    with tempfile.TemporaryDirectory() as tmp:
        reg_src = os.path.abspath(os.path.join(here, "..", "platforms", "registry.json"))
        with open(reg_src, "r", encoding="utf-8") as fh:
            reg = json.load(fh)

        def variant(name, git_mib, largest_mib):
            """Two registries, so each refusal isolates ONE limit and the clean
            fixture passes both. A tiny .git threshold applied globally would
            fail the clean repo too and prove nothing."""
            v = json.loads(json.dumps(reg))
            for lim in v["platforms"]["github"]["limits"]:
                if lim.get("measure") == "git_dir_mib":
                    lim["value"] = git_mib
                if lim.get("measure") == "largest_tracked_file_mib":
                    lim["value"] = largest_mib
            path = os.path.join(tmp, f"{name}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(v, fh)
            return path

        # reg1 exercises the per-file and media limits; 1 GB stays at its real value.
        test_reg_path = variant("reg1", 1024, 0.05)
        # reg2 exercises the aggregate .git bound with a threshold a few-KB
        # fixture can actually cross.
        fat_reg_path = variant("reg2", 0.5, 100)
        gh = reg["platforms"]["github"]

        empty_reg_path = os.path.join(tmp, "empty.json")
        with open(empty_reg_path, "w", encoding="utf-8") as fh:
            json.dump({"schema": 1, "platforms": {}}, fh)

        state = os.path.join(tmp, "state")
        os.makedirs(state, exist_ok=True)

        # 1. empty registry must FATAL, never report health
        run(["--registry", empty_reg_path, "status"], EXIT_UNKNOWN, "empty registry refuses to report health")

        # 2. no snapshot → preflight UNKNOWN (fail closed on silence)
        clean = _init_repo(os.path.join(tmp, "clean"))
        _commit(clean, {"README.md": "# clean\n", "main.py": "print('ok')\n"})
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", clean],
            EXIT_UNKNOWN, "no terms snapshot -> UNKNOWN, never PASS")

        # 3. write a fresh synthetic snapshot, then the same repo must PASS
        snap = {"schema": 1, "platform": "github", "display": "GitHub", "read_at": now_iso(),
                "terms": [{"id": t["id"], "title": t.get("title"), "url": t["url"],
                           "status": "ok", "text_sha256": "x" * 64, "chars": 500}
                          for t in gh["terms"]]}
        with open(os.path.join(state, "github.json"), "w", encoding="utf-8") as fh:
            json.dump(snap, fh)
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", clean],
            EXIT_PASS, "clean repo -> PASS")

        # 4. tracked media → REFUSE, and the refusal must NAME tracked_media
        media = _init_repo(os.path.join(tmp, "media"))
        _commit(media, {"README.md": "# media\n", "art/cover.png": b"\x89PNG\r\n\x1a\n" + b"\0" * 512})
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", media],
            EXIT_REFUSE, "tracked media -> REFUSE", expect_text="tracked_media")

        # 5. oversized single file → REFUSE via the per-file limit. Use .txt so
        # the media rule does not also fire — the refusal must be attributable.
        big = _init_repo(os.path.join(tmp, "big"))
        _commit(big, {"README.md": "# big\n", "notes.txt": "a" * (200 * 1024)})
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", big],
            EXIT_REFUSE, "oversized file -> REFUSE", expect_text="file_size_block")

        # 5b. aggregate .git size → REFUSE. Incompressible blobs so the
        # aggregate bound is genuinely crossed (400 KB of 'x' would deflate to nothing).
        fat = _init_repo(os.path.join(tmp, "fat"))
        for i in range(3):
            _commit(fat, {"README.md": f"# fat {i}\n", "data.txt": os.urandom(400 * 1024)})
        run(["--registry", fat_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", fat],
            EXIT_REFUSE, "aggregate .git over the bound -> REFUSE", expect_text="repo_git_size")

        # 6. a repo path that does not exist must be UNKNOWN, never PASS
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", os.path.join(tmp, "nope")],
            EXIT_UNKNOWN, "missing repo -> UNKNOWN")

        # 7. a directory that is not a git repo must be UNKNOWN, never PASS
        notgit = os.path.join(tmp, "notgit")
        os.makedirs(notgit, exist_ok=True)
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "push", "--repo", notgit],
            EXIT_UNKNOWN, "non-git directory -> UNKNOWN")

        # 8. stale snapshot → UNKNOWN
        stale = json.loads(json.dumps(snap))
        stale["read_at"] = "2020-01-01T00:00:00Z"
        stale_state = os.path.join(tmp, "stale")
        os.makedirs(stale_state, exist_ok=True)
        with open(os.path.join(stale_state, "github.json"), "w", encoding="utf-8") as fh:
            json.dump(stale, fh)
        run(["--registry", test_reg_path, "--state", stale_state, "preflight",
             "--platform", "github", "--action", "push", "--repo", clean],
            EXIT_UNKNOWN, "stale snapshot -> UNKNOWN")

        # 9. an unreadable term in the snapshot → UNKNOWN (cannot rely on it)
        badsnap = json.loads(json.dumps(snap))
        badsnap["terms"][0]["status"] = "unreadable"
        bstate = os.path.join(tmp, "bad")
        os.makedirs(bstate, exist_ok=True)
        with open(os.path.join(bstate, "github.json"), "w", encoding="utf-8") as fh:
            json.dump(badsnap, fh)
        run(["--registry", test_reg_path, "--state", bstate, "preflight",
             "--platform", "github", "--action", "push", "--repo", clean],
            EXIT_UNKNOWN, "unreadable terms in snapshot -> UNKNOWN")

        # 10. change detection, both directions, offline
        a = os.path.join(tmp, "a.html")
        b = os.path.join(tmp, "b.html")
        c = os.path.join(tmp, "c.html")
        for path, body in ((a, "<html><body><p>Clause 9: no backup.</p></body></html>"),
                           (b, "<html><body><p>Clause 9: no backup.</p></body></html>"),
                           (c, "<html><body><p>Clause 9: backups are now permitted.</p></body></html>")):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        run(["compare", a, b], EXIT_PASS, "identical terms text -> SAME")
        run(["compare", a, c], EXIT_REFUSE, "edited terms text -> CHANGED")

        # 11. a platform whose terms were never recorded must be UNKNOWN
        run(["--registry", test_reg_path, "--state", state, "snapshot", "--platform", "8004scan"],
            EXIT_UNKNOWN, "platform with no terms source -> UNKNOWN")

        # 12. publish action, no acknowledgement: nothing is machine-checkable for a
        # listing, so every hard limit must block until a human names it.
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "publish"],
            EXIT_REFUSE, "publish without --ack -> REFUSE",
            expect_text="repo_git_size: hard limit is not machine-checkable")

        # 13. the same action with the hard limits acknowledged by id -> PASS,
        # and the verdict must say it is an acknowledgement, not a measurement.
        hard_ids = [l["id"] for l in gh["limits"] if l.get("severity") == "hard"]
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "publish", "--ack", ",".join(hard_ids)],
            EXIT_PASS, "publish with every hard limit acknowledged -> ACKNOWLEDGED",
            expect_text="ACKNOWLEDGED")

        # 14. acknowledging ONE limit must not acknowledge the rest — the gate has to
        # be per-limit, or a single --ack becomes a blanket waiver.
        run(["--registry", test_reg_path, "--state", state, "preflight",
             "--platform", "github", "--action", "publish", "--ack", hard_ids[0]],
            EXIT_REFUSE, "acknowledging one limit does not waive the others",
            expect_text="tracked_media: hard limit is not machine-checkable")

        # 15. a platform with terms on record but ZERO limits -> UNKNOWN. An empty
        # limits list makes every per-limit check vacuously pass; that is the
        # "healthy because nobody looked" failure this tool exists to prevent.
        nolim_path = os.path.join(tmp, "nolim.json")
        v = json.loads(json.dumps(reg))
        v["platforms"]["cloudflare"]["limits"] = []
        with open(nolim_path, "w", encoding="utf-8") as fh:
            json.dump(v, fh)
        cf_state = os.path.join(tmp, "cfstate")
        os.makedirs(cf_state, exist_ok=True)
        cf_snap = {"schema": 1, "platform": "cloudflare", "display": "Cloudflare",
                   "read_at": now_iso(),
                   "terms": [{"id": t["id"], "title": t.get("title"), "url": t["url"],
                              "status": "ok", "text_sha256": "y" * 64, "chars": 900}
                             for t in reg["platforms"]["cloudflare"]["terms"]]}
        with open(os.path.join(cf_state, "cloudflare.json"), "w", encoding="utf-8") as fh:
            json.dump(cf_snap, fh)
        run(["--registry", nolim_path, "--state", cf_state, "preflight",
             "--platform", "cloudflare", "--action", "publish"],
            EXIT_UNKNOWN, "platform with zero recorded limits -> UNKNOWN, never PASS")

        # 16. --allow-unread tolerates a RECORDED gap but must still name it, so a
        # watcher can distinguish "changed" (exit 1) from "never read" (reported).
        run(["--registry", test_reg_path, "--state", state, "snapshot",
             "--platform", "8004scan", "--allow-unread"],
            EXIT_PASS, "--allow-unread tolerates a recorded gap", expect_text="NOT COVERED")

    passed = sum(1 for ok, *_ in results if ok)
    say(f"\nSELFTEST: {passed}/{len(results)} cases behaved as required")
    if passed != len(results):
        say("SELFTEST FAILED — the guard does not hold in the direction it exists to hold.")
        return EXIT_UNKNOWN
    return EXIT_PASS


# ---------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="policy-guard",
        description="Platform terms and limits as a gate that refuses, not a warning that scrolls.")
    ap.add_argument("--registry", default=os.environ.get("POLICY_GUARD_REGISTRY", DEFAULT_REGISTRY))
    ap.add_argument("--state", default=os.environ.get("POLICY_GUARD_STATE", DEFAULT_STATE))
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot", help="read terms, record URL + date + hash, diff vs last")
    s.add_argument("--platform")
    s.add_argument("--all", action="store_true")
    s.add_argument("--update", action="store_true", help="write the new snapshot")
    s.add_argument("--allow-unread", action="store_true",
                   help="tolerate platforms the registry has never read (recorded gaps), "
                        "so a scheduled watcher can mean 'changed' with exit 1. A read that "
                        "FAILS still exits 2.")
    s.set_defaults(func=cmd_snapshot)

    s = sub.add_parser("preflight", help="measure an action and refuse on a hard breach")
    s.add_argument("--platform", required=True)
    s.add_argument("--action", required=True, choices=["push", "repo-create", "publish"])
    s.add_argument("--repo")
    s.add_argument("--ack", default="", help="comma-separated hard-limit ids a human has read and accepts")
    s.add_argument("--max-age-days", type=float, default=90.0)
    s.set_defaults(func=cmd_preflight)

    s = sub.add_parser("status", help="what we have read, and when")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("compare", help="offline SAME/CHANGED on two documents")
    s.add_argument("a")
    s.add_argument("b")
    s.set_defaults(func=cmd_compare)

    s = sub.add_parser("selftest", help="prove both directions")
    s.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    if args.cmd == "snapshot" and not args.platform and not args.all:
        ap.error("snapshot needs --platform <id> or --all")
    try:
        return args.func(args)
    except GuardError as exc:
        return unknown(str(exc))
    except BrokenPipeError:
        return EXIT_UNKNOWN


if __name__ == "__main__":
    sys.exit(main())
