# Proving a probe can fail

A monitor with an untested red path is a claim. The red path is the one that never runs in production
until the night it matters — so it must be executed on purpose, against a fixture, before the probe is
trusted.

**The shape: fixture → sabotage → assert RED → assert GREEN → delete.** Both directions, every time.

---

## 1. Make the script pointable at a throwaway root

A probe that hardcodes its own profile cannot be tested without touching live state. Give it one override:

```python
PROFILE = os.environ.get("<TOOL>_PROFILE") or os.path.basename(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = f"/opt/data/profiles/{PROFILE}"
```

Then a test builds `profiles/_probe-fixture-ok` and `profiles/_probe-fixture-bad`, runs the **real script**
with the env var set, and reads its machine-readable output. Never fork the probe's logic into the test — a
test that reimplements the check proves the reimplementation works.

```python
subprocess.run([sys.executable, PROBE, "--json"], capture_output=True, text=True,
               env=dict(os.environ, <TOOL>_PROFILE=fixture), timeout=60)
```

## 2. Build the fixture to satisfy everything you are NOT testing

**A fixture that fails for the wrong reason passes a lazy test and proves nothing.** Measured: a fixture
declared a script name it never created, so the "runnable scripts" probe fired RED in the *healthy*
scenario — the assertion on the intended probe would still have passed if it had been written loosely.

So when building a fixture:

- create every file the untested probes look for (scripts, memory files, state dirs, databases);
- populate the columns every probe reads, including the boring ones — a job with no `next_run_at` is a
different finding from a job with a dead delivery;
- run it once and **read the whole output**, not just the line you care about. Unexpected reds mean the
fixture is lying, not that the probe is wrong.

## 3. Assert RED on the sabotaged scenario, and name the check

```python
state = {p["name"]: p["ok"] for p in doc["probes"]}
for name in ("01_cron_health", "02_cron_enabled", "05_delivery_set"):
    if state.get(name, True):
        fails.append(f"sabotaged fixture stayed GREEN on {name}")
if rc != 2:
    fails.append(f"sabotaged fixture exited {rc}, expected the findings code")
```

- **Assert the specific probe, by name.** "It exited non-zero" is satisfied by any bug in any probe.
- **Assert the note names the offender.** A red that cannot say *which* job failed is a red nobody can act on.
- **One sabotage per defect class**, not one big broken fixture: a single fixture with four faults proves the
  probes fire, not which one reads which field.

## 4. Assert GREEN on the clean scenario — including the exclusion rules

The clean fixture is where the false-positive rules are pinned. Put in it exactly the states that a careless
probe misreads:

- a **completed one-shot** (`enabled: false`, `state: completed`) — must be invisible to any "disabled" count;
- a job whose **frozen final status** is stale — must not be graded forever;
- a job with **no run history at all** — unmeasured, not a miss;
- a job that ran and **legitimately delivered nothing** (`suppressed`) — silence is not failure.

If the clean scenario goes red, the defect is in the probe's exclusions, and this is the only place it is ever
caught cheaply.

## 5. Clean up, and say you did

The test removes its own fixtures and prints that it did. Assert the scratch paths are gone:

```bash
ls -d /opt/data/profiles/_probe-fixture-* 2>/dev/null   # must be empty
```

A fixture left behind becomes a real profile that every fleet-wide scan then reads, grades, and reports on.

## 6. Wire the exit code honestly

`0` all assertions pass · `1` an assertion failed · `3` could not run. **A test that exits 0 because it could
not read its own output is the same defect as the monitor it is testing** — which is why the parse of the
machine-readable output is itself asserted, and a parse failure is a `1`, never a skip.

## Common defects this catches

| symptom | real cause |
|---|---|
| a probe that has never once been red | the red case was never executed |
| red on a healthy fixture | the fixture is incomplete, or the probe grades retired state |
| green on a sabotaged fixture | the probe reads config, not outcome |
| `json.loads()` fails on `--json` | a human verdict was printed to stdout alongside the JSON |
| assertion passes whatever the probe does | the test asserted only the exit code |
