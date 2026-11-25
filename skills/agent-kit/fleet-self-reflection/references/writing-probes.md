# Writing probes that can be trusted

A probe is a check that returns `(ok, detail)` and feeds a score. A self-reflection is only as good
as the probes underneath it, and probes have their own failure class: **they produce a plausible
number that grades the wrong thing.**

Every rule below was hit while building the seven-probe scorecard, and every one was caught by
running it rather than reading it.

---

## 1 · The verdict must come from the SAME NUMBER you print

A probe that returns `ok=True` while its own detail reads `0/30` scores a deliberate fault as healthy.
That is not a rounding error; it is a green check that means nothing, sitting in the report that
exists to eliminate exactly those.

```python
# ❌ reads as healthy at 0 of 30 — the fault IS the zero
explicit = sum(1 for j in jobs if j.get("model"))
return True, f"{explicit}/{len(jobs)} name their own model"

# ✅ the verdict is derived from the quantity the detail reports
return (explicit > 0), f"{explicit}/{len(jobs)} name their own model (rest inherit)"
```

**The test for every probe you write: *what value makes my detail say zero while my verdict says
true?*** If such a value exists, the probe is decorative. This is the same question as "what would
make this print a confident PASS while the thing it guards is broken?" — apply it per probe, not per
report.

---

## 2 · Bound every block parser, or it counts the NEXT block too

In an indentation-structured config, a block is **the lines with leading whitespace**. Any pattern
that lets `\s` match a newline at column zero is unbounded, and will run straight into the next
top-level key.

```python
# ❌ `\s+.*\n` matches a BLANK line, so the block continues past its own key
re.search(r"(?ms)^fallback_providers:\s*\n((?:\s+-.*\n|\s+.*\n)*)", txt)

# ✅ indented lines only — the block ends at the first column-zero key
re.search(r"(?m)^fallback_providers:[ \t]*\n((?:[ \t]+.*\n)+)", txt)
```

**The failure shape it produced:** one config was counted three times — `default,default,default` —
because the over-extended block contained three provider lines from unrelated sections. The count was
inflated, and the label repeated, which is how the bug became visible at all.

**When a count exceeds the size of the set it is counting, the parser is wrong before the data is.**
Cross-check every count against a denominator you know independently: `len(PROFILES)`, `len(SEATS)`,
the number of files you walked. A count larger than its universe is proof of a parsing defect, not a
discovery.

---

## 3 · Get the LABEL from the path with one helper

A probe that names which file failed is only useful if the names are right. Deriving the label inline
produces collisions that look like findings.

```python
# ❌ '/opt/data/config.yaml' -> 'data'; and every seat path has to be special-cased
os.path.basename(os.path.dirname(p))

# ✅ one helper, so the default and the seats are always distinguishable
def _plabel(path: str) -> str:
    parent = os.path.basename(os.path.dirname(path))
    return "default" if parent == "data" else parent
```

**A label that repeats is a parser bug wearing a finding's clothes.** Before reporting "three profiles
have this fault", check the three labels are distinct.

---

## 4 · Prove ONE probe can go GREEN before trusting any that are RED

A probe that cannot be made to pass is indistinguishable from one that is always red — and an
always-red probe is ignored in exactly the same way as a silent one. **Both failure directions ruin
the report.**

The cheapest possible proof, done once per probe:

1. Take one real instance of the fault in one file (not a fixture — a live config).
2. Fix only that instance.
3. Re-run: the count must decrement **and that file must disappear from the list**.
4. Restore the file.
5. Re-run: the count must return and the file must reappear.

```
5 profile(s): default,gentech,arthur,gentech-treasury,protojay
4 profile(s): default,gentech,gentech-treasury,protojay      ← arthur fixed, arthur gone
5 profile(s): default,gentech,arthur,gentech-treasury,protojay  ← restored
```

**Assert both directions, and assert the identity as well as the number.** A count that moves while
the wrong name leaves the list means the probe is grading something else.

---

## 5 · Store a baseline and report what MOVED

A scorecard re-written from scratch each run cannot distinguish improvement from a change of mood.
Persist the results and diff them.

```json
{ "baseline_at": "…", "score": "2/7", "results": { "01_stt_provider_valid": {"ok": true, "detail": "5/5 valid"}, … } }
```

Print `⬆️ improved since last baseline` and `⬇️ REGRESSED since last baseline`, listing probe names —
not prose. **A regression line is the single most valuable output a scorecard produces**, and it only
exists if the previous run was stored.

**Save the baseline only after the probes are correct.** Saving a buggy run as the baseline makes the
next honest run look like a regression (it will report `⬇️ REGRESSED` for a probe you just repaired),
which teaches the reader to ignore the one signal worth having.

---

## 6 · A probe that shells out keeps the 0/2/3 contract

Probes that invoke another script inherit its exit codes. Keep them distinguishable:

- `0` — measured, and it passed
- `2` — measured, and it found something
- `3` — **could not measure** (`UNKNOWN`)

A probe that returns `0` because the subprocess crashed has converted blindness into a clean bill.
Treat a missing script, a non-zero-unexpected code, or a timeout as `UNKNOWN` with the reason attached
— and never fold `UNKNOWN` into the passing count.

### The wrapper is where the contract is most often lost

**A wrapper written to make findings exit 0 will, if nobody looks, also make FAILURE exit 0** — because
both branches usually close with the same trailing `exit 0`. Measured on five wrappers in one sweep:
every one printed `… INSTRUMENT FAILED …` plus an explanation and then fell through to success, and one
never captured `$?` at all. The alarm text was correct and the exit code contradicted it.

**Why the code is the half that matters:** those jobs delivered to `local`, so the printed alarm landed in
an output file nobody opens. **The exit code is the only signal that reaches health reporting.**

```sh
if [ "$rc" -ne 0 ]; then
  printf 'X — INSTRUMENT FAILED  %s\n%s\n' "$(date -u '+%Y-%m-%d %H:%MZ')" "$out"
  exit 3          # ✅ visible to cron health
fi
case "$out" in *"gaps: 0"*) : ;; *) printf '%s\n' "$out" ;; esac   # findings → print, fall to 0
exit 0
```

- **Check `$?` FIRST, before matching on the output.** A wrapper that only pattern-matches `$out` cannot
  tell an empty success from a crashed run that printed nothing.
- **Audit all three states per wrapper**: clean (0, no output), findings (0, output), instrument broken (3).
  One missing the third is a monitor that cannot go red — the failure this file exists to catch,
  introduced by the fix for a different one.
- **`unreadable` is not `clean`.** A probe that returns success when it could not open its input reports
  its own blindness as a pass; that is `3`, always.

---

## 7 · A probe that fetches your own public hostname must send a real User-Agent

**The default library UA is blocked at the edge, and the resulting error describes the endpoint, not
the probe.** Measured: `urllib` with its stock `Python-urllib/3.x` UA got **HTTP 403** from Cloudflare
on our own domain, while `curl/8.x` got **200** on the same URL from the same machine, seconds apart.

The probe reported *"COULD NOT READ the manifest"* — which reads as **the endpoint is broken**, when
the truth was **we were refused at the edge**. A future reader would have chased the service.

```python
# ❌ measures the client's UA policy, not the target
urllib.request.urlopen(url)

# ✅ a real UA + Accept, and the probe now measures the thing it names
req = urllib.request.Request(url, headers={
    "User-Agent": "<product>/1.0 (+https://your-domain)",
    "Accept": "application/json",
})
urllib.request.urlopen(req, timeout=20)
```

**The general rule: when a probe fails, first ask whether it reached the application at all.**
`403` and `429` are **edge** answers — WAF, bot policy, rate limit — not capability answers. Only a
`4xx`/`5xx` from the application itself is evidence about the application. **A probe that cannot
distinguish "blocked" from "broken" will report the wrong one forever.**

Corollary: when `curl` works and your code does not, **diff the request, not the environment.** UA and
headers first, TLS/proxy second, network last.

---

## 8 · A ratio above 100% proves the classifier is wrong, not that you had a good day

**A derived rate is two counts divided. If the numerator can contain events the denominator cannot,
the result can exceed 100% — and that number is a defect report, never a result.**

Measured: a conversion probe reported **461%** and **468%** on two routes — *more sales than quotes*.
Arithmetically impossible, therefore the classification was wrong. Both routes counted **HTTP 200 on a
bare route** as a completed sale. Those 200s were **collection-root signposts** —
`{"collection_root": true, "payable": false}` — served when a caller omits the required path parameter.
A crawler reading a signpost is not a customer.

```python
# ❌ status code treated as the event
if status == 200: served += 1

# ✅ the event is a 2xx on a path that actually carried a transaction
if status in (200, 202):
    if not path_after_prefix.strip('/'):   # bare route = signpost, not a sale
        signpost += 1
    else:
        served += 1
```

**Three rules that generalise:**

1. **A status code is a protocol outcome, not a business event.** `200` covers a sale, a signpost, a
   cached page, a health probe and a catch-all fallback. Classify on the SHAPE of the request (did it
   carry the required parameters?) as well as the response.
2. **Assert the denominator contains the numerator's universe, then check the arithmetic.** A rate above
   100%, a count above its own set size, or a share of a whole that exceeds the whole are all the same
   signal: **the two numbers are measuring different things.** Print the raw counts beside every rate so
   the impossibility is visible to the reader too.
3. **A category that silently absorbs traffic is worse than a wrong number.** The signposts were being
   counted as revenue for as long as the probe existed. **Give a non-event its own column**
   (`signpost`, `bot`, `self`, `unknown`) so it is subtracted from the story instead of inflating it.
   **A total that reconciles to its parts is the receipt; a total alone is a guess.**

---

## 9 · Separate FINDINGS from CONTEXT — a list in the output is not a fault

**A probe that counts every non-empty list it produces reports a healthy system as broken.** Measured: a
health instrument printed `findings 9` for folder structure when the real defect count was zero to one. Its
keys were doing three different jobs:

- `duplicates`, `dead_redirects` — **findings**: a human must act
- `similar_names`, `unreferenced`, `shells` — **context**: real observations that are usually fine
  (`00-HQ/` beside a legacy `HQ/` shares zero filenames; a 73-file `Entertainment/` is a folder, not a fault)

**Keep two key sets and count only one:**

```python
FINDING_KEYS  = ("duplicates", "dead_redirects")
ADVISORY_KEYS = ("similar_names", "unreferenced", "shells")
findings = sum(len(d.get(k, [])) for k in FINDING_KEYS)   # what the verdict reads
```

**A permanent red light and a permanent green one are ignored identically.** Advisory output may still be
printed — as context, under its own label — but it must not move the pass/fail number, and it should
escalate only on CHANGE against a stored high-water mark, never on mere presence. **A backlog that is
exactly where it should be is not news.** Same rule for anything phrased "N ideas in no handoff", "N files
unreferenced", "N files without a title": name the population, then ask whether existing is the defect or
only growing is.

---

## 10 · Scope the sweep — a finding about a BACKUP is not a finding

**An unscoped text sweep finds the system's own copies of itself.** Measured: a proofread check flagged
files under `backups/`, `memory-archive/`, `patches/`, `_repopulate-*` and a log, then reported "1,380
files lack a title" — a number that also over-counted vendored docs, redirect stubs and generated public
copies.

**Every text sweep needs an explicit SKIP list and a stated idea of what a human actually writes:**

```python
SKIP = ("/backups/", "/memory-archive/", "/completions-archive/", "/patches/",
        "/venvs/", "/node_modules/", "/.git/", "_repopulate-", "/logs/")
```

- **A generated or archived artifact is not authored text.** Grading it grades a copy of something you
  already grade, at a moment you cannot fix it.
- **Prefer narrowing the population over widening the rule.** The instinct is a bigger sweep; the correct
  move is a stated scope. **A check that reports 1,380 defects and expects one fix is a check nobody runs
  twice.**
- **Accept the shapes authors actually use.** A file whose first line is a plain-text title HAS a title;
  requiring your own markup (`# `) invents a defect. The title check should pass on either.

---

## 11 · A text check must not reach across a line boundary

**`re.sub(r'"[^"]*"', ...)` applied to a whole document pairs an OPENING quote with the CLOSING quote of a
later line whenever that line holds an odd number of quotes — swallowing every word in between, then
"finding" doubled words inside the mangled remainder.** Measured: a doubled-word probe reported `the the`
on a line that reads correctly, and the chase cost an hour.

**The mechanism generalises to every check that masks spans before matching:** mask **per line**, and make
sure what the mask leaves behind cannot *create* the pattern you are hunting.

```python
# ❌ whole-body mask: an unterminated quote eats the next paragraph
body = re.sub(r'"[^"]*"', " ", body)

for _line in body.splitlines():
    _s = re.sub(r'"[^"]*"', "", _line)          # ✅ per line
    _s = re.sub(r"[ \t]{2,}", " ", _s).strip()   # ✅ collapse what the removal left behind
```

⚠️ **Removing a span leaves the spaces on BOTH sides of it, and two spaces are enough for a `word \s+
word` matcher to see a repeat that is not there.** Replace-with-one-space, replace-with-empty and
replace-with-a-sentinel all reproduce the artefact until the whitespace is collapsed. **Collapse first,
then judge.**

### When a finding contradicts the file, READ the file — do not edit it

**A probe's output is a claim; the file is the evidence.** Measured the hard way: three successive edits
were made to "fix" a typo that lived in the probe, not the note — one of them deleted a real paragraph,
and the "restore" was typed from memory instead of from git.

1. Print the exact line the probe names with `repr()` — control characters and stray whitespace become
   visible, and most phantoms die here.
2. Reproduce the match on that line alone, in the same code path the probe uses.
3. **Restore with `git checkout -- <file>`, never from memory.** A hand-typed restore is a new edit, not a
   revert.
4. If the probe was wrong, fix the probe and say so. **A file edited to satisfy a broken check is a
   regression wearing a repair's clothes.**

---

## The seven probes, as a starting set

A worked implementation lives at `profiles/<seat>/scripts/self-reflect.py`; read it before writing
another. The set is deliberately small and each one is a yes/no or a number:

| probe | question | fails when |
|---|---|---|
| `stt_provider_valid` | does every profile's provider exist in the schema's list? | a value resolves to nothing |
| `metered_fallback` | how many metered providers are armed as fallbacks? | a spend decision was never made |
| `image_provider` | is there an uncommented, usable key anywhere? | the tool has no lane at all |
| `seats_vs_core` | how many seat skills differ from the shared core? | a fix landed on one seat only |
| `cron_explicit_model` | how many jobs are script-only (0 tokens), and does any instructed-script job still pay a model? | a one-command job runs through an LLM |
| `tool_liveness` | did every tested tool answer a real call? | a tool is configured but dead |
| `signoff_pending` | are any seats still unsigned past the floor? | agreement is claimed, not given |
| `seat_identity` | does each seat's identity file name the seat, or open with the stock default? | the seat was never configured |

**One probe class is easy to forget: DISTRIBUTION.** Config probes ask "is this value valid?" and
miss "does every seat have one at all?" A private file that is never synced (an identity file, a
memory file, a `.env`) cannot be checked by drift — drift compares seats to each other, and a file
that is *absent in substance* on one seat still differs byte-wise from its siblings. Probe the
substance: for identity, that the file names its own seat; for a memory file, that it is not empty;
for a credential, that the value is uncommented and non-empty. **Difference proves nothing was
overwritten. It does not prove anything was written.**

**Add a probe only when it can be made to fail on demand.** A probe that has never been red is a
line of output, not a measurement.
