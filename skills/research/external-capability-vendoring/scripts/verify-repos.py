#!/usr/bin/env python3
"""verify-repos.py — verify candidate repos against the REAL GitHub core API.

    python3 verify-repos.py owner/repo [owner/repo ...]
    python3 verify-repos.py --file candidates.txt

Prints stars, licence (spdx_id), last push and archived flag per repo — the facts that decide adoption and the
ones a search snippet does not carry. Reads the token from GITHUB_TOKEN, else the first existing
profiles/*/secrets/github-token, and NEVER prints it.

Why the core API and not search: the search endpoint can refuse an account outright (`422 ... "User flagged as
spammy"`) while the core API keeps working — and `rate_limit` reporting the anonymous 60/hr bucket is the tell
that the token was ignored. A refusal here is reported as a GATE, never as "repo not found".
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

PROFILES = pathlib.Path("/opt/data/profiles")
UA = "gentech-capability-verification"


def token() -> str | None:
    env = os.environ.get("GITHUB_TOKEN")
    if env and env.strip():
        return env.strip()
    for p in sorted(PROFILES.glob("*/secrets/github-token")):
        try:
            v = p.read_text().strip()
            if v:
                return v
        except OSError:
            continue
    return None  # anonymous: still works, lower limits


def api(path: str):
    h = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    t = token()
    if t:
        h["Authorization"] = f"Bearer {t}"
    req = urllib.request.Request("https://api.github.com" + path, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "replace")
    except Exception as e:  # network-level
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    argv = sys.argv[1:]
    args = [a for a in argv if not a.startswith("--") and not a.endswith(".txt")]
    if "--file" in argv:
        idx = argv.index("--file")
        path = argv[idx + 1]
        args += [l.strip() for l in pathlib.Path(path).read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
    if not args:
        print(__doc__)
        return 2

    st, rl = api("/rate_limit")
    if isinstance(rl, dict):
        core = rl.get("resources", {}).get("core", {})
        anon = core.get("limit") == 60
        print(f"# auth={'token' if token() else 'ANONYMOUS'}  core {core.get('remaining')}/{core.get('limit')}"
              f"  {'(anonymous bucket = token ignored)' if anon else '(ok)'}")

    verdicts = []
    for repo in args:
        st, d = api(f"/repos/{repo}")
        if isinstance(d, str):
            print(f"  {repo:45s} HTTP {st} {d[:90]}")
            verdicts.append((repo, "UNVERIFIED — gate, not an empty result"))
            continue
        lic = (d.get("license") or {}).get("spdx_id")
        gate = "decline: NO LICENCE" if not lic or lic == "NOASSERTION" else f"licence {lic}"
        print(f"  {repo:45s} {d.get('stargazers_count'):>6}*  {str(lic):12s} "
              f"pushed={(d.get('pushed_at') or '')[:10]}  size={d.get('size')}KB  archived={d.get('archived')}")
        verdicts.append((repo, gate))

    print("\n# gate summary")
    for repo, v in verdicts:
        print(f"  {repo:45s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
