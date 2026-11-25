# Consolidation audit — measuring what is actually in a skill

The four measurements that turn "these look similar" into a merge list with byte counts. Run all four
before proposing any cut; each one has overturned a plausible-looking plan.

## 1 · Job identity: compare INSTRUMENTS, not prose

Two descriptions can share every keyword and two headings lists can share almost nothing, in both
directions. The reliable signal is what the text tells an agent to **run**:

```python
import re
def instruments(text):
    return (set(re.findall(r'\b([a-z0-9][a-z0-9_\-]{2,40}\.(?:py|sh))\b', text)),
            set(re.findall(r'state/([a-z0-9_\-]+\.json)', text)))
```

**Same job = same instrument set** — overlapping tool/script names, the same reader script, the same
config file. Measured pair: two LP-monitoring skills shared **6 tools, one script and one state file**
while their H2 headings overlapped on **two generic words** (`implementation`, `pitfalls`). The heading
diff said "different"; the instruments said "one job, two vintages". **Instruments win.**

A different instrument set with a similar topic is two jobs: a router that names skills and a procedure
that runs tools are not one procedure, however much vocabulary they share.

## 2 · History share: bytes under dated / incident headings

```python
hist = 0
for line in text.splitlines(True):
    if re.match(r'^#{1,4} ', line):
        cur = bool(re.search(r'20\d\d-\d\d|case|history|log|incident|post[- ]mortem', line.lower()))
    if cur: hist += len(line.encode())
```

Typical result on a shelf that "feels full of history": **2-7% of bytes**, 0% on some files. So "move the
history to the vault" is usually a real but small win — do not build the whole plan on it.

## 3 · Stale-procedure share: sections naming an instrument that is not there

This is where the weight usually is. Resolve every referenced instrument against the profile the skill
loads into, then against the whole host, to separate *gone* from *lives elsewhere*:

```python
idx = {f for root, _, files in os.walk('/opt/data') for f in files}   # one walk, then set membership
absent  = [r for r in refs if not glob.glob(f'{profile}/**/{r}', recursive=True)]
nowhere = [r for r in absent if r not in idx]
elsewhere = [r for r in absent if r in idx]        # vault / recovery snapshot — not runnable here
```

Measured on four large skills in one lane: **38-44% of each file** sat in sections naming an instrument
absent from the seat — 303 distinct missing instruments, **132 existing nowhere on the box**, 171 only in
the vault or an old recovery snapshot. The skills described the pre-wipe generation of tools while the
seat ran a different set. **That, not history, is the balloon.**

Attribute the bytes per section so the cut is quantified, not asserted:

```python
for block in re.split(r'\n(?=#{1,4} )', text):
    if set(re.findall(r'\b([a-z0-9][a-z0-9_\-]{2,40}\.(?:py|sh))\b', block)) & set(absent):
        stale += len(block.encode())
```

## 4 · The clean skill is the template, not the victim

Find the skill in the slice whose references all resolve. Measured: one 8-reference skill with **zero
missing** instruments, in a lane where its neighbours were at 38-44% stale. **That is the target shape for
the rewrite** — point the merge at it, and leave it alone. A merge that consumes its cleanest member has
removed the example the next rewrite should copy.

## Turning it into the answer the owner wants

Report per candidate as **(a) merges I would make, (b) bytes saved each** (measured for deletions,
labelled *estimate* for rewrites), **(c) what I refuse to merge and why.** Never present a total saving
without saying which lines were measured and which were projected.

**Refuse the umbrella-absorbs-everything merge even when it is the biggest single win.** An "one skill to
rule them all" whose trigger fires on every task in the domain is the defect, not the fix: split it into a
thin router plus `references/`, and keep the procedure where it is already correct.
