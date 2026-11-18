# Restoring a lane from a recovery tree

A **lane** is an entry script plus the sibling modules it imports. Recovering the script alone does not
recover the lane — and every failure below shows up as a bug in the script while actually being a
mismatch in the set. Work the steps in order; each one prevents the next step's symptom.

## 1. Locate every copy, and choose by GENERATION

```bash
# every copy on the box (exclude package caches, which hold thousands of unrelated names)
find /opt/data -name 'regime_classifier.py' -not -path '*/cache/uv/*' 2>/dev/null

# which copy actually satisfies the caller's import?  grep the FUNCTION, not the filename
for f in $(find /opt/data -name 'regime_classifier.py' -not -path '*/cache/uv/*'); do
  printf '%-80s %s\n' "$f" "$(grep -c 'def run_btc_classification' "$f")"
done
```

**Take the whole set from the same directory as the entry script.** Sibling modules carry the API of
their generation: same filename, different signature. A set assembled across directories fails on
`ImportError` (missing name) or `TypeError: unexpected keyword argument` — never on data.

```bash
# read the entry script's imports first, then stage exactly those
D=<the directory the entry script came from>
for f in <entry>.py <sibling1>.py <sibling2>.py; do cp "$D/$f" "tools/$f"; done
```

## 2. Repoint pre-wipe absolute paths — AFTER the last copy

A recovered script typically carries absolute paths from the machine it last ran on. Make them
**env-overridable** so a test can inject a scratch root instead of the live one:

```python
# was: STATE_DIR = "/root/.hermes/scripts"
STATE_DIR = os.environ.get(
    "STEWARD_STATE_DIR",
    os.path.join(os.environ.get("HERMES_PROFILE_DIR", "<profile dir>"), "state"),
)
```

- **Grep EVERY file in the set, not just the entry script.** The path lived in the entry script *and*
in a sibling that writes a price-history file. Fixing one and re-running produces a `PermissionError`
from a file you did not open — which reads like a new problem.
- **Re-grep after staging:** `grep -rn '/root/' tools/` and assert only comments remain. A staged copy
  CAN revert a patch you already applied; staging must come first, patching second.
- **Do not reach for `expanduser()` or a hardcoded home** — a profile-scoped `HOME` resolves it to the
  wrong tree. An explicit env var with a correct default is the form that survives both.

## 3. `.get(k, default)` — the default does not apply to a present-but-None key

```python
summary = {"avax_price": None}          # the fetch failed and stored None
summary.get("avax_price", 0)            # -> None  (the key EXISTS, so the default never fires)
f"{summary.get('avax_price', 0):.2f}"   # TypeError: unsupported format string passed to NoneType

summary.get("avax_price") or 0          # -> 0     (null-coalescing — this is the fix)
```

Find the whole class in one pass, and mind the quoting — a regex written for bare identifiers silently
matches nothing when the keys are quoted strings:

```python
pat = re.compile(r"\.get\((\s*['\"][^'\"]+['\"]),\s*([0-9.]+)\)")
s = pat.sub(lambda m: f".get({m.group(1)}) or {m.group(2)}", s)
```

**Assert the rewrite count, not just that the file changed** — a regex that matches nothing still
reports success. Print the number of substitutions.

**Then fix the report, not only the crash.** `0` for an unknown price is a failed read rendered as a
confident value — the same defect as the crash in a friendlier costume. Render the unknown AS unknown:

```python
f"   AVAX: {('$%.2f' % summary['avax_price']) if summary.get('avax_price') else 'UNMEASURED (all sources failed)'}"
```

## 4. Run it, and read PER-STAGE status — the exit code is not a verdict

An entry script that wraps each stage in its own `try/except` records the failure in its state file and
**still exits 0**. A run with every stage dead looks clean if you only read `$?`.

```bash
venvs/<venv>/bin/python tools/<entry>.py > /tmp/run.out 2>&1; echo "exit=$?"

python3 -c "
import json; d=json.load(open('state/<entry>.json'))
for k,v in d.get('pipeline',{}).items():
    e=v.get('error') if isinstance(v,dict) else None
    print(f'{k:10} status={v.get(\"status\") if isinstance(v,dict) else \"?\"}  {str(e)[:80] if e else \"\"}')
"
```

**Require every stage `ok`.** A stage reporting `status=error` under an exit code of 0 is a lane that is
not restored, and reporting it as restored is the failure this whole skill exists to prevent.

## 5. Prove determinism, then push and verify from the REMOTE

```bash
# deterministic? diff excluding the only legitimate difference — the timestamp
venvs/<venv>/bin/python tools/<entry>.py > /tmp/r1.txt 2>&1; sleep 1
venvs/<venv>/bin/python tools/<entry>.py > /tmp/r2.txt 2>&1
diff <(grep -v timestamp /tmp/r1.txt) <(grep -v timestamp /tmp/r2.txt) && echo "deterministic"

# push, then prove it from the remote — not from the exit code
git ls-remote --heads origin                     # READ the branch; memory gets this wrong
git push origin HEAD:<branch>
git ls-remote origin refs/heads/<branch> | cut -f1   # must equal:  git rev-parse HEAD
git ls-tree --name-only origin/<branch> <dir>/        # the new files must appear
```

- **`git clone` refuses a non-empty directory.** Clone into a fresh path and stage AFTER — creating the
target first (`mkdir -p $R/tools`) makes the clone fail while the staging that follows still appears to
succeed.
- **Never leave a status-bearing command upstream of a pipe with `&&` after it** — see
  `verify-after-every-action`: the pipeline's status is the last command's.
