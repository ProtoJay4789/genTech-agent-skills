# Marker-manifest guard — catching a silent revert of a co-written file

Recipe for §3c. A code file with more than one writer is rewritten whole by whoever touches it next, so a
patch is replaced rather than merged: no conflict, no diff, no error, and a fresh `mtime` that looks like a
normal edit. A digest tells you it changed; it cannot tell you what was lost.

## Shape

Two artifacts beside the guarded file:

```
<seat>/cache/<name>-guard.json           # accepted baseline: digest + surviving marker labels
<seat>/scripts/<name>-guard.py          # check / accept / --selftest
```

Manifest, written only by `accept`:

```json
{
  "accepted_at": "<ISO>",
  "by": "<seat>",
  "scripts/thing.py": {
    "sha256": "<hex>",
    "present": ["<label>", "<label>"],
    "missing": [],
    "bytes": 15556
  }
}
```

Markers are `(label, needle)` pairs. The **label** is what a human reads when the behaviour is gone
(`"delivery probe reads run-level delivery_outcome"`); the **needle** is a short substring that only exists
while the behaviour does (`"_DELIVERED"`).

## The three verdicts

| digest | markers | verdict | exit |
|---|---|---|---|
| matches | all present | intact | 0 |
| differs | one or more GONE | **REVERTED** — name each missing label | 2 |
| differs | all present | changed-but-intact — ask for `accept` | 0 (with message) |
| no manifest | — | UNMEASURED, tell the reader to run `accept` | 3 |

Two rules that make it honest:

- **`accept` refuses** when any marker in the current scan is missing. Without this, one command ratifies the
  loss and the guard certifies the regression as the new standard.
- **Changed-but-intact must be a message, not silence.** Otherwise a legitimate edit is indistinguishable
  from a revert the next time somebody checks.

## Picking markers

Good needle: a function or constant name that only exists because of the fix (`_DELIVERED`,
`ran but delivered nowhere`, `file=sys.stderr if as_json`).

Bad needle: a word from a docstring or comment, or anything that survives the behaviour being deleted. A
needle that is also in the comment proving nothing is the classic way to build a guard that can never fire.

**Verify each marker by deletion** — remove the behaviour, confirm the label reports GONE, restore. One
pass over all markers catches the ones that are decoration.

## Selftest (must live with the guard)

Build two throwaway roots and drive the real entry point:

1. clean file → `accept` → `check` is GREEN.
2. sabotage one behaviour (string-replace the needle's line) → `check` exits 2 **and names that label**.
3. `accept` on the sabotaged file **refuses** (non-zero).
4. clean file + a harmless appended comment → `check` reports changed-but-intact, not silent.

Drive it by importing or invoking the real script with a root override (`os.environ.get("X_ROOT", <live>)`),
never by re-implementing the comparison in the test.

## Wiring it so it can actually be heard

Run the guard from the **caller** — the cron wrapper or the launch script — before the main output, and make
the red branch print even when the job is in `--quiet` mode:

```sh
GUARD=$("$PY" "$DIR/<name>-guard.py" check 2>&1); GRC=$?
if [ "$GRC" -eq 2 ]; then
  printf '%s\n' "$GUARD"
  printf '⚠️ GUARD RED — <file> lost a load-bearing behaviour; the output below is suspect.\n'
fi
```

**A guard that shares the silence of the thing it guards buys nothing.** A silent-when-healthy monitor is
exactly the job whose regression nobody hears, so the guard must be the one component in that path that
refuses to be quiet.

Exit 3 (no manifest) should say so once and continue — a missing baseline is unmeasured, not a regression.

## End-to-end proof, then restore

1. Sabotage the **live** file exactly as the real revert happened.
2. Run through the real entry point (the wrapper, at the real path, from a neutral working directory).
3. Confirm the loud report fires.
4. Restore from the pre-sabotage copy and confirm the digest is back to the baseline value.

Step 3 through a scratch copy proves the comparison; only step 2 proves the wiring.

## Keep the governance list SHORT

Govern files whose silent regression would be invisible — a monitor's probes, a gate's predicates, a
classifier's rules. A manifest over every script in a seat is a maintenance tax that will be disabled the
first time it cries about a harmless reformat.
