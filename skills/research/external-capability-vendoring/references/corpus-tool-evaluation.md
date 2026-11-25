# Measuring a corpus tool (graph / wiki / knowledge / code-map) against our own material

A repo's README describes what it does to *a* corpus. This is how to find out what it does to **ours**, cheaply
and without contaminating the brain. Applies to knowledge-graph builders, wiki analysers, codebase mappers,
second-brain tools, embedding/retrieval indexes — anything that reads a directory tree.

## 0. Preconditions, not enthusiasm

Read the tool's detector first. Most of these tools have an implicit input contract — a manifest, an index
file, a schema file, a `raw/` layer, a particular link syntax. Answer each condition for our corpus before you
spend anything:

```bash
ls <corpus>/index.md <corpus>/log.md <corpus>/raw 2>&1 | head
find <corpus> -name '*.md' | wc -l
```

A missing precondition is a **migration cost**, and it is part of the verdict. Do not quietly hand-build the
missing file and then report the happy path as if the corpus had met the contract.

## 1. Copy, then point the tool at the copy

These tools write working state into the directory you give them (`.ua/`, `.cache/`, an index, a manifest).

```bash
mkdir -p scratch/tool-test
cp -r <corpus>/<subtree-a> scratch/tool-test/
cp -r <corpus>/<subtree-b> scratch/tool-test/
```

A representative subtree is enough — two or three top-level folders, a thousand-plus notes. The numbers
reproduce at full scale; the mess does not.

## 2. Run only the deterministic phase

Serious tools split a **free parser** from **paid model calls**. Find the parser and run it alone.

```bash
python3 <skill>/parse-*.py scratch/tool-test
```

Read its output as a checklist: `articles / sources / topics / wikilinks (unresolved)` and any `warnings`
array. Seconds, zero tokens, and it already decides most of the question.

## 3. Break the edges down by TYPE — a total edge count is meaningless

The headline "N edges" hides which edges are *knowledge* and which are just the folder tree.

```python
import json
from collections import Counter
m = json.load(open("scratch/tool-test/.ua/intermediate/scan-manifest.json"))
print(Counter(e["type"] for e in m["edges"]))
```

If every edge is a structural type (`categorized_under`, `contains`, `in_directory`) then the tool has
reproduced your directory listing as a graph. It will look impressive and teach nothing. **Only content-derived
edge types** (`related`, `references`, `depends_on`, `cites`) carry meaning.

## 4. Sample the detections — always

Open 5–10 of whatever it claims to have found, and compare with the source file.

```python
print(json.dumps(m.get("warnings", [])[:10], indent=1))
```

Expect false positives from **fenced code blocks and inline snippets**: a regex character class written
`[[:space:]]` inside documentation parses as a wiki link; the literal token `[[wikilinks]]` inside a note
*about* wikilinks parses as another. A 100% unresolved rate is the tell.

Cross-check the raw mechanism yourself, so you know whether the corpus or the tool is at fault:

```bash
for f in $(find <corpus> -name '*.md'); do grep -c '\[\[' "$f"; done | paste -sd+ | bc
find <corpus> -name '*.md' | wc -l
```

A low links-per-file ratio means **we never built the edges the tool reads** — verdict: borrow the renderer,
and author the links deliberately in one contained corpus. It is not a tool defect.

## 5. Category scan — decide the shelf before the quality

Count the vocabulary of the job you actually need:

```bash
for w in mastery quiz assess 'spaced repetition' evidence measure curriculum prerequisite; do
  printf '%-20s %s\n' "$w" "$(grep -ic "$w" README.md)"
done
```

All zeros means it does not model learners, levels or evidence: it is a **delivery surface**, not an engine.
Say that in one sentence and stop arguing about quality — the category decides the seam.

## 6. The verdict shape to write down

1. **What it is, verified** — licence, activity (`pushed_at`), size, and whether it ships in a format we can load
   (a `SKILL.md` package is directly relevant to us; a browser-only app is not).
2. **What it did to our corpus** — the measured numbers, including the drop/error rate.
3. **What it cannot do** — the vocabulary it lacks, stated as a boundary, not an insult.
4. **The seam it fits** — renderer/pack, never the engine; and the containment (one pack, one experiment).
5. **The cost of the LLM phases** — quote the project's own warning; the deterministic phase is free, so
   measure before spending.
6. **Whatever it proves about US** — a graph tool finding nothing is usually a statement about our corpus
   (untyped links, no frontmatter), and that is the durable finding worth filing.

File the write-up where the domain lives (the vault folder for that subject), not in the chat, and link it from
whatever skill governs the domain.
