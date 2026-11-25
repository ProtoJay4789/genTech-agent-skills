# Curated publication from a private corpus

The recipe behind the rules in SKILL.md → *Publishing a curated subset of a private corpus*.
Written from a real build: a 7,261-file private vault → a ~40-file public "portfolio brain".

---

## 1 · Why the copy-and-sanitize shape fails

Run the category census first, then read the numbers as evidence *against* filtering:

```python
CATS = {
  'personal_finance': r'\b(salary|net worth|mortgage|401k|balance|invoice)\b',
  'identity':         r'\b(ssn|date of birth|passport|driver.s licen[cs]e)\b',
  'credential':       r'(sk_live|ghp_|xox[baprs]-|BEGIN [A-Z ]*PRIVATE KEY)',
  'employment':       r'\b(employer|recruiter|offer letter|severance)\b',
  'relationship':     r'\b(wife|husband|son|daughter|birthday|anniversary)\b',
  'address_and_travel': r'\b(ohio|cincinnati|[A-Z]{3} [A-Z][a-z]{2} \d{1,2}|booking ref)\b',
}
```

Three conclusions, all measured:

- **Over-match is the norm.** `address_and_travel` hits almost every runbook in a finance repo, because
  every one of them names a flight, an airport code or a state. `personal_finance` flags vendor notes that
  merely mention invoices.
- **A denylist can never prove a negative.** Deleting everything a filter catches leaves you able to say
  "nothing I searched for is present" — which is a statement about the filter, not about safety. Same defect
  as reading a capped sample and reporting the total.
- **A copy also drifts.** Two trees, one private, one public, and the public one is stale by the second week
  with nothing marking which is true.

So the artifact is not a copy. It is a **build output**: one direction, small allowlist, provably clean,
regenerable.

---

## 2 · Gate 1 — the allowlist

A checked-in file of corpus-relative paths, grouped by what the section IS (standards / coordination /
architecture), so a reviewer reads a table of intent rather than a list of filenames:

```
# portfolio-brain.allowlist
[standards]
ROUTING.md
START-HERE.md
FLEET-BRIEF.md
standing-rule-restart-checkpoint.md

[coordination]
01-HANDOFFS/INBOX/README.md

[architecture]
10-Labs/SOUL.md
```

Rules the loader enforces:

- **`.md` only**, resolved **relative to the corpus root** — reject absolute paths and `..` outright, so an
  allowlist entry cannot reach outside the tree.
- **A veto list applied even to allowed paths**, as a second lock: a treasury folder, an HQ folder, a journal,
  a career folder, `secrets/`, `backups/`, and any `.env` / `.key` / `.token`. An allowlist entry that names a
  vetoed folder is a mistake, and the build should say so rather than quietly publishing it.
- **A missing allowlisted file is a build failure**, not a warning — a tree that silently shrinks is how a
  public repo loses its coordination section without anyone noticing.

---

## 3 · Gate 2 — the refusal patterns (any hit = no build)

Self-test this table before the first real run, in both directions. This is the version that shipped:

| class | pattern | must fire | must NOT fire |
|---|---|---|---|
| hex private key | `\b0x[0-9a-fA-F]{64}\b` | assigned 64-hex | a 40-hex address, a tx hash in prose |
| GitHub token | `\bgh[pousr]_[A-Za-z0-9]{20,}` | `ghp_…` | the word "token" |
| PEM | `-----BEGIN [A-Z ]*PRIVATE KEY-----` | header | a doc explaining what one is |
| Stripe live | `\bsk_live_[A-Za-z0-9]{16,}` | key | `sk_live` inside a pattern table |
| JWT | `\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}` | real JWT | base64 prose |
| email | `\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b` | a person's address | — (accept the noise; it is PII) |
| card | `\b(?:\d{16}|\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}|\d{4}[ -]\d{6}[ -]\d{5})\b` | 4111 1111 1111 1111 | `2026-11-20 to 2026-11-27`, chat id `<telegram-group-id>` |
| SSN | `\b\d{3}-\d{2}-\d{4}\b` | 123-45-6789 | a date range |

**The card row is the lesson.** The first version used `\b(?:\d[ -]*?){13,16}\b`, which matches any 13–16 digit
run with optional separators — so it ate a date range and a Telegram chat id and refused two perfectly clean
files. A refusing gate that produces false positives on ordinary prose is a gate the operator turns off, and
then the real hit ships. Narrow the pattern to shapes only a card can be; a real card has no other separator
pattern than 16-contiguous / 4-4-4-4 / 4-6-5.

**Print the self-test result, not just pass/fail:** `8 caught, 4 clean` is a receipt that the matcher runs at
all. A gate whose only output is silence is indistinguishable from a gate that never executed.

---

## 4 · Gate 3 — the human review (informs, never blocks)

A second script scans the *built output* for things a pattern cannot settle, and returns **0 regardless**:

```python
NEEDS_A_PERSON = [
    r'\b(myia|dadrian|vanito|venito|wife|husband|son|daughter|mom|dad)\b',
    r'\b(birthday|anniversary|home address|cincinnati|ohio)\b',
    r'\b(employer|recruiter|severance|offer letter)\b',
    r'(NEVER|never) (call|fund|send|publish)',   # standing rules written ABOUT a person
]
```

- Print `file:line: text` and a total (`9 lines in 8 files`), then exit 0.
- **Do not decide.** A line like a standing rule about a family member is fine in a private brain and wrong
  in a public one — only the owner can make that call.
- **Do not block.** A blocking review step gets commented out under time pressure; an informative one gets read.
- The human's read is the publication gate. Write that in the build script's own header comment, so the next
  agent reading the code cannot mistake script success for permission to publish.

---

## 5 · Sequence, end to end

```bash
python3 scripts/<name>-build.py --check     # gate 1 + gate 2 only, no write
python3 scripts/<name>-build.py             # render to a LOCAL cache path
python3 scripts/<name>-review.py            # gate 3: flagged lines, exit 0
# human reads the flagged lines, approves the file list
# only then: copy/tag/push, and re-scan the SERVED BYTES afterwards
```

- **Render locally first, always.** A cache path is not publication — it is the thing the human reads.
- After publishing, re-run the secret scan against the **published URL** (`curl` each file, grep the bodies),
  not the local tree, with a positive control (a URL that must 200) and a negative control (a path that must 404).
- **State what is NOT published and why.** "Zero treasury, zero career, zero family, zero credentials, zero
  health" is the useful headline; it tells the reader the boundary was chosen, not exhausted.

---

## 6 · What a public artifact of a private corpus should contain

The method, not the notes. The reader cannot use a copy of your backlog; they can use the coordination shape:
how handoffs carry an agreement block, how a completion must carry evidence, how a skill library promotes
from core to a seat, how a guard refuses instead of warning. Those are publishable because they are already
written as standards — files whose whole content is the rule.

**And name the honest cost to the user up front:** the build is cheap, the review is not, and the artifact
carries their name. Build it before the application it is meant to support, never alongside.
