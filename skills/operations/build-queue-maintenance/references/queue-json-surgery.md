# Queue JSON surgery — the scanner and the splice

Working code for editing selected rows of `build_queue.json` without re-serialising the file.
Every approach here was arrived at by breaking the file first; the failure list is in SKILL.md.

## Why splice at all

A whole-file re-dump is only safe if the serializer round-trips the current bytes. Prove it before writing:

```python
raw = open(QUEUE, encoding="utf-8").read()
probe = json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + "\n"
print("round-trips:", probe == raw, len(probe), len(raw))
```

`indent=1` is correct for the **whole list** (row braces at one space, keys at two). A **standalone row
object** dumped on its own needs `indent=2` to put its keys at two spaces. Mixing these up is what makes a
46-row edit look like a 1,100-line one.

## Scan: string-aware brace walker

```python
def object_spans(text: str):
    """Yield (start, end_exclusive) for each TOP-LEVEL object in a JSON array.

    Braces inside string literals are ignored, and nested objects stay inside their
    parent's span, so a row containing a `checkin` block resolves correctly.
    """
    in_str = esc = False
    starts: list[int] = []
    for idx, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            starts.append(idx)
        elif ch == "}" and starts:
            st = starts.pop()
            if not starts:                 # outermost object closed
                yield st, idx + 1
```

Then key each span by its id **as it appears in the file text**:

```python
blocks = []
for st, en in object_spans(raw):
    seg = raw[st:en]
    mid = re.search(r'^  "id": (.+?),$', seg, re.M)
    blocks.append((st, en, mid.group(1).strip() if mid else None))
pos = {bid: (s, e) for s, e, bid in blocks if bid}
```

## Comparing ids across a mixed-type queue

ids are `15` (int), `"rev-3"` (quoted string) and `"#106"` (unquoted string). The span key holds the raw
text *including* the quotes, so compare on the JSON-quoted form:

```python
key = json.dumps(row["id"])       # 15 -> '15' ; "rev-3" -> '"rev-3"'
if key not in pos:
    raise SystemExit(f"no span for {row['id']} — refusing to write")
```

A row can also carry **no `id` key at all** (only `_orig_id`). It cannot be a target — skip it rather than
failing the count check.

## Splice: one forward pass

```python
edits = []                                   # (start, end, replacement)
for rid in changed_ids:
    row = by_id[rid]
    s, e = pos[json.dumps(row["id"])]
    block = json.dumps(row, indent=2, ensure_ascii=False)   # standalone object
    edits.append((s, e, block))              # span ends AT the brace; comma stays outside

out, cursor = [], 0
for s, e, replacement in sorted(edits, key=lambda t: t[0]):
    if s < cursor:
        raise SystemExit(f"overlapping spans at {s}-{e} — refusing to write")
    out += [raw[cursor:s], replacement]
    cursor = e
out.append(raw[cursor:])
open(QUEUE, "w", encoding="utf-8").write("".join(out))
```

**Forward, ascending — not backwards.** Walking backwards and accumulating `raw[e:cursor]` slices is easy to
get subtly wrong (the first version of this spliced text from the wrong side and produced a file that failed
to parse at line 306). The forward cursor has one invariant and one failure mode.

## Adding rows: append at the anchor, never re-dump

Adding a row is not the splicing problem above — it is simpler, and a whole-file write is the trap.
Measured on a **two-row addition**: `json.dump(rows, ...)` over the loaded list produced **419 insertions /
381 deletions**, and the diff had to be reverted and redone. Appending to the raw text produced **40
insertions / 2 deletions** for the same change.

The anchor is the last row's closing brace; everything after it is the line `]`.

```python
raw = open(QUEUE, encoding="utf-8").read().rstrip()
assert raw.endswith("]"), "queue does not end with ] — refusing"
anchor = raw.rindex("\n }") + 3          # just past the final row's "}"

def as_row(obj):
    # the file's shape: object brace at ONE space, keys at TWO
    return "\n".join(" " + ln for ln in
                     json.dumps(obj, indent=1, ensure_ascii=False).splitlines())

new_raw = raw[:anchor] + ",\n" + ",\n".join(as_row(o) for o in NEW) + "\n]\n"
json.loads(new_raw)                      # must parse BEFORE it goes anywhere
open(QUEUE, "w", encoding="utf-8").write(new_raw)
```

**`json.dumps(obj, indent=1)` then ONE leading space on every line** is what reproduces the file's shape —
brace at one space, keys at two. Do not reason it out from the indent number: indentation that is *valid
JSON* can still be a different shape from the file, and a shape mismatch is invisible until someone reads the
diff. Prefixing only the lines after the first leaves the brace at column 0 and the keys one level too deep;
both parse, both are wrong.

**Assert the id is not already present before appending.** A duplicate id does not raise — the queue then
carries two rows answering to the same number, and every id-keyed lookup afterwards returns whichever one the
parser happened to see first.

## Verify from disk

```python
back = json.load(open(QUEUE))
assert len(back) == len(rows), "row count changed — restore from snapshot"

OPEN = {"pending", "blocked", "in_progress", "open", "needs-evidence"}
def ok(r):
    g = (r.get("gate") or "").strip()
    rc = (r.get("release_condition") or "").strip()
    return bool(g) and (bool(rc) or bool(re.search("releas", g, re.I)))

open_rows = [r for r in back if r.get("status") in OPEN]
print(f"open {len(open_rows)} · fully gated {sum(1 for r in open_rows if ok(r))}")
```

Then prove no collateral damage: load the pre-edit copy and the post-edit file, compare row by row, and
assert the set of changed ids equals the set you intended.

```python
changed = {str(y["id"]) for x, y in zip(before, after) if x != y}
assert changed == targets, changed ^ targets
```

## Run the queue's own readers afterwards

A parse proves the file loads; it does not prove the reporters still work. Run each of them and check the
exit code:

- `build-queue-reconcile.sh`
- `queue-digest.sh`

A digest that fails or silently reports zero is the signal that a field it reads changed shape.
