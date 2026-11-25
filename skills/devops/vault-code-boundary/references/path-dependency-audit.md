# Path-dependency audit — what actually reads this folder

Use before moving, archiving or absorbing a folder tree. Output: a per-entry count of **live** references, which
is the only evidence that decides machinery vs records vs archive.

## 1 · Inventory the tree (counts, bytes, dates)

```bash
L=/opt/data/.obsidian-vault/10-Labs
ls -1 "$L" | wc -l                                   # total entries
find "$L" -maxdepth 1 -type d | wc -l                # includes $L itself — subtract 1
find "$L" -maxdepth 1 -type f | wc -l
for e in "$L"/*; do
  n=$(find "$e" -type f 2>/dev/null | wc -l)
  b=$(du -sb "$e" | cut -f1)
  printf '%-7s %-10s %s %s\n' "$n" "$b" "$(stat -c %y "$e" | cut -c1-10)" "$(basename "$e")"
done | sort -k1,1nr
```

Keep the result as JSON next to the run so the sender's numbers can be checked against a fixed list later.

## 2 · Count references, and filter the noise first

Search for the **literal path**, not the bare folder name:

```bash
rg -o -H --no-heading -F "10-Labs/<entry>" <roots> | sed 's|.*10-Labs/||' | sort | uniq -c | sort -rn
```

Roots that count as *live*: each seat's `profiles/*/scripts/`, every `profiles/*/cron/jobs.json`, the shared
`scripts/` tree, and `00-System/agent-profiles/`. Roots that must be excluded or they drown the signal:
`**/cache/**`, `**/10-Archive/**`, `**/_archive/**`, `**/archive/**`, `**/.curator_backups/**`, and — the big one —
**bulk manifests / merge logs**, which list every path in the vault and turned 14,928 matches into a "everything is
referenced" answer (four manifest files alone produced 11,666 of them).

**A grep over the whole vault answers a different question.** Vault notes citing a path are *navigation*; live code
reading it is a *dependency*. Report the two separately, and move on the dependency count.

## 3 · Read the hit, not just the count

A count of 4 can mean four `sys.path.insert` lines (hard dependency) or one comment and three prose mentions (no
dependency at all). Classify each:

| hit looks like | verdict |
|---|---|
| `sys.path.insert`, `import`, a file opened for read/write, a cron `script`/`command`, a mount, a service `ExecStart` | **hard — do not move** |
| a path inside a docstring, a comment, or a printed instruction | soft — safe to move, fix the text |
| a path under `/root/...` or another host's tree | stale — it is already broken; do not treat it as protection |

## 4 · Before the move

1. Manifest (entry · files · bytes · why) written first, old → new for every row.
2. One dated parent for a sweep; `du -sb` before and after.
3. Every hard-dependency path either stays or gets its reader updated **in the same pass, by the same author**.
4. Verify the reader resolves the new path. If its library is missing on this host, stub it:

```python
# stub module on PYTHONPATH, then run the script's module body to print its resolved constants
import runpy, sys
sys.argv = ["tool.py", "relative-input.md"]
g = runpy.run_path("/path/to/tool.py", run_name="probe")
print(g["_DEFAULT_DIR"], g["SRC"].exists(), g["SRC"].stat().st_size)
```

That proves **path resolution only**. Report "path proven, output not rendered" — a stub renderer produces no
artifact and claiming otherwise is the same class as a fabricated number.

## 5 · Verify after the move

```bash
ls -1 <new dir> | wc -l                       # equals the pre-move count
ls <new dir> | sed 's/\.\(md\|pdf\|json\)$//' | sort | uniq -c | awk '$1!=2'   # spot unpaired source/output pairs
[ -d <old dir> ] && echo "LEFTOVER" || echo "old path clean"
grep -rn "<old path>" <live code roots> | grep -v '/cache/'   # any hit left = a reader still points there
```
