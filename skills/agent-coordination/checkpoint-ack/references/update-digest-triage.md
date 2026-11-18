# Pre-swap department sweep, and the acceptance test after

The generic half lives in `measurement-recipe.md`. This file is the half that depends on **your own lane** —
the things that break because of what *you* run, not because of what the fleet runs.

Run it **before** the window and write the result into the triage note. Then run the acceptance test **after**
the swap and compare against what you recorded, so "it came back" is a measurement rather than a hope.

## 1. Runtime major-version jump — scan YOUR scripts, don't extrapolate from one

An update can move the managed Python (or Node, or Go) runtime under you.

```bash
python3 -V                                    # the runtime you are ON now
for f in <your entrypoints>; do
  echo "-- $(basename "$f"): $(wc -l < "$f") lines | \
        $(grep -cE 'distutils|pkg_resources|^import imp$|utcnow\(|get_event_loop|collections\.(Mapping|Callable|Iterable)' "$f") hits"
done
```

- **Scan every entrypoint, not the biggest one.** A clean 800-line engine and a dirty 30-line wrapper is the
  normal outcome; reporting "scripts are fine" from one file is not a scan.
- **`datetime.utcnow()` is the classic hit**: deprecated, still present, and it writes a **naive** timestamp —
  a correctness smell in a lane whose product is honest numbers.
- **Record a baseline RUN, not just a parse.** `--selftest` / `--status` / the gate script's rc, captured while
  the old runtime is still up. That baseline is the only thing that makes the post-swap comparison meaningful.
- **Do not fix engine code inside the checkpoint window.** A two-line compat fix is not restart-blocking, and an
  unreviewed edit during a freeze is exactly the scope creep the window forbids. Park it with the import line,
  the call, and what "done" looks like.

## 2. Data-retention defaults that flip ON

A new default that *deletes* things (pruned sessions, expired caches, rotated logs) is the one class where
"nothing to do" needs proof.

```bash
# session ages + pin state, run as a FILE, not with -c (see the inline-interpreter pitfall in SKILL.md)
python3 cache/scratch/session_probe.py
```

Report **the oldest record, its age, and the count over the threshold** — plus how many records are pinned. "No
records older than the threshold" is a measurement; "we don't think anything is old" is not. Say which one you
actually have.

## 3. Commands the update REMOVED

Grep for the removed command across everything you own — your scripts, your pack data, the shared config tree:

```bash
grep -rn "<removed-command>" <your-scripts> <shared-config-dir> | head
```

**Report the count and where it came back zero.** For a seat whose job is distribution or scheduling, the
removed sync/scheduler verb is the highest-severity item in the digest, and "checked, 0 hits" is worth more
than silence — it is the item a reader would most expect to have bitten you.

## 4. Renamed tools — count call sites, then ignore them until after the window

Old names usually keep working for a release. So: **count, don't rewrite.**

```bash
for t in "old_name(" "other_old("; do echo -n "$t -> "; grep -rn --include=SKILL.md -F "$t" <your-skills> | wc -l; done
grep -rn --include=SKILL.md -cE 'new_name|other_new' <your-skills> | awk -F: '{s+=$2} END {print s}'
```

A number in the tens is a post-swap shelf-hygiene task with a defined done-state (grep returns 0); it is never a
reason to hold the restart. Editing dozens of call sites during a freeze is how a window acquires a new bug.

## 5. The service shape you must be able to compare against

Record before the swap, compare after:

```bash
ls /run/service/                      # service names, verbatim
sed -n '1,20p' /run/service/<your-service>/run     # your launch line, exactly
pgrep -af 'gateway|your-process'      # pids + full argv
ss -ltnp 2>/dev/null | grep <port>    # or read /proc/net/tcp and resolve the inode to a pid
```

**Two numbers that get conflated:** the count of supervised services and the count of processes holding a
listener. "One multiplex process" and "N supervised services" can both be true, and a migration that reshapes
one may not touch the other. Report both, and name which entry point is yours — if your own service name
disappears after the swap, your seat is unreachable regardless of what else came back up.

## 6. Plugins, extensions and anything the update MOVED to a catalog

```bash
ls <profile>/plugins 2>/dev/null | tr '\n' ' '    # empty is a finding: nothing to migrate
```

An empty directory is a **complete answer** ("nothing to migrate"), not an unchecked box. Say it that way.

## 7. Acceptance test after the swap

Run in this order and diff against the baseline from step 1:

1. runtime version;
2. your strongest invariant — the one that must never print a plausible-but-fabricated number
   (`UNMEASURED`, not `0%`), plus the full selftest;
3. any gate that must not leak a secret — confirm it still prints the *source of* the key and never the value;
4. the service shape from step 5;
5. the inventory count you last recorded (registered items, skills, jobs) — and if it moved, say by how much and
   whether the change is explained;
6. the usage/quota gate before vs after, if the release touched prompt size or replay behaviour.

**A check that cannot fail is not a check.** Every line above must have a value it was not allowed to return.
