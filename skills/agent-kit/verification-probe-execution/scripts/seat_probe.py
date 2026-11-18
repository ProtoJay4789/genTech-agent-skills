#!/usr/bin/env python3
"""Read-only seat census for an evidence batch (checkpoint ACK, seat/health audit).

Usage:
    python3 seat_probe.py [PROFILE_DIR] [extra_artifact ...]

Defaults to $HERMES_PROFILE_DIR, else /opt/data/profiles/gentech. Extra paths are reported with size,
mtime and md5 for digest proof.

Prints: UTC stamp; held-work census; artifacts by bytes + mtime; secrets/keystores COUNT only;
session-DB integrity + session count; cron jobs with next fire; the environ census WITH its
readability split; md5 of any extra artifacts.

Read-only: writes nothing, restarts nothing. Anything it cannot open is printed as UNREADABLE or as
an explicit seen/readable/unreadable split -- never silently as zero.

Assembled from individually exercised probes; dry-run it once before trusting its output.
Set PROBE_ENV_KEYS to change the env names probed (comma separated).
"""
import glob
import hashlib
import json
import os
import sqlite3
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HERMES_PROFILE_DIR", "/opt/data/profiles/gentech")
EXTRA = sys.argv[2:]
SKIP = {"cache", ".curator_backups", "sandboxes", "sessions", "home", "logs", "audio_cache", "image_cache"}
KEYS = [k.strip() for k in os.environ.get("PROBE_ENV_KEYS", "ELEVENLABS_API_KEY").split(",") if k.strip()]


def utc(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


def walk(root, maxdepth=3):
    """Yield (dirpath, dirnames, filenames) up to maxdepth, skipping bulk dirs."""
    root = os.path.abspath(root)
    for dp, dn, fn in os.walk(root):
        if dp[len(root):].count(os.sep) >= maxdepth:
            dn[:] = []
        dn[:] = [d for d in dn if d not in SKIP]
        yield dp, dn, fn


print("== seat census ==")
print("profile :", P)
print("now     :", utc(time.time()))

print("\n-- held work (a bounce destroys only what is in memory) --")
pj = os.path.join(P, "processes.json")
if os.path.exists(pj):
    try:
        print("processes.json : %s (%d B)" % (open(pj).read().strip() or "(empty)", os.path.getsize(pj)))
    except Exception as e:
        print("processes.json : UNREADABLE (%s) -> unknown, not 0" % e)
else:
    print("processes.json : ABSENT -> 0 tracked processes (file not present, not a broken read)")

for name in ("pending", "plans"):
    d = os.path.join(P, name)
    if not os.path.isdir(d):
        print("%-15s: ABSENT -> 0 queued writes" % name)
        continue
    files = [os.path.join(dp, f) for dp, _, fn in walk(d) for f in fn]
    if not files:
        print("%-15s: present, 0 files" % name)
        continue
    mt = sorted(os.path.getmtime(f) for f in files)
    print("%-15s: %d file(s) UNAPPLIED | oldest %s | newest %s"
          % (name, len(files), utc(mt[0]), utc(mt[-1])))

strays = [os.path.join(dp, f) for dp, _, fn in walk(P)
          for f in fn if f.endswith((".wip", ".tmp", ".partial", ".swp"))]
print("stray partials : %d %s" % (len(strays), strays[:5]))
gits = [os.path.join(dp, d) for dp, dn, _ in walk(P) for d in dn if d == ".git"]
print("worktree       : %s" % (gits[:3] if gits else
                                "no .git under the profile -> no uncommitted branch to lose"))

print("\n-- artifacts (bytes + mtime) --")
for rel in ("config.yaml", ".env", "cron/jobs.json", "state.db", "state.db-wal", "state.db-shm",
            "memories/MEMORY.md", "memories/USER.md"):
    fp = os.path.join(P, rel)
    try:
        st = os.stat(fp)
        print("%-20s: %12d B | mtime %s" % (rel, st.st_size, utc(st.st_mtime)))
    except FileNotFoundError:
        print("%-20s: ABSENT" % rel)
    except Exception as e:
        print("%-20s: UNREADABLE (%s)" % (rel, e))

for name in ("secrets", "keystores"):
    d = os.path.join(P, name)
    try:
        print("%-20s: %d entr(ies) (count only - never print names)" % (name + "/", len(os.listdir(d))))
    except FileNotFoundError:
        print("%-20s: ABSENT -> 0" % (name + "/"))
    except Exception as e:
        print("%-20s: UNREADABLE (%s) -> unknown, not 0" % (name + "/", e))

print("\n-- session DB (read-only URI, no writer lock) --")
db = os.path.join(P, "state.db")
if os.path.exists(db):
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
        print("quick_check :", c.execute("pragma quick_check").fetchone()[0])
        print("sessions    :", c.execute("select count(*) from sessions").fetchone()[0])
        c.close()
    except Exception as e:
        print("DB check    : FAILED (%s) -> report the failure; do not infer integrity" % e)
else:
    print("state.db    : ABSENT")

print("\n-- cron --")
try:
    d = json.load(open(os.path.join(P, "cron", "jobs.json")))
    jobs = d.get("jobs", d) if isinstance(d, dict) else d
    jobs = list(jobs.values()) if isinstance(jobs, dict) else jobs
    print("jobs: %d | enabled: %d" % (len(jobs), len([j for j in jobs if j.get("enabled")])))
    for j in jobs:
        s = j.get("schedule") or {}
        nxt = (j.get("next_run") or j.get("next_fire") or j.get("next_run_at")
               or s.get("expr") or s.get("display"))
        print("  - %s | enabled=%s | last=%s | next=%s"
              % (j.get("name"), j.get("enabled"), j.get("last_status"), nxt))
except Exception as e:
    print("jobs.json   : UNREADABLE (%s) -> unknown, not 'no jobs'" % e)

print("\n-- environ census (PARTIAL by nature: another user's /proc/<pid>/environ is unreadable) --")
seen = readable = carriers = 0
pids = []
for p in glob.glob("/proc/[0-9]*/environ"):
    seen += 1
    try:
        data = open(p, "rb").read().decode("utf8", "replace")
    except Exception:
        continue
    readable += 1
    names = {l.split("=", 1)[0] for l in data.split("\x00") if "=" in l}
    if names & set(KEYS):
        carriers += 1
        pids.append(p.split("/")[2])
print("probe keys : %s" % ",".join(KEYS))
print("seen=%d readable=%d unreadable=%d carriers=%d %s"
      % (seen, readable, seen - readable, carriers, pids))
print("-> report the split; a bare '0 carriers' is a false negative when unreadable > 0")

if EXTRA:
    print("\n-- extra artifacts (digest proof) --")
    for fp in EXTRA:
        try:
            h = hashlib.md5()
            with open(fp, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            st = os.stat(fp)
            print("%s | %d B | mtime %s | %s" % (h.hexdigest(), st.st_size, utc(st.st_mtime), fp))
        except Exception as e:
            print("UNREADABLE (%s): %s" % (e, fp))

print("\nEvery number above was measured now. Unreadable subjects are unknown, never clean.")
