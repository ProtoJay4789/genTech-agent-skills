# Probe design for settling a claim *about your own seat*

A checkpoint usually arrives carrying claims about your box — "your config was migrated", "the key is set on
all seats", "nothing is running". The ACK must settle each one with a probe **whose pattern can tell the two
states apart**. This file is the pattern library. Substitute `P=/opt/data/profiles/<seat>`.

---

## 1 — The probe must be able to fail

The classic error is a pattern loose enough that it agrees with whatever the claim already says. If a
substring match cannot return "absent", it is not a verification — it is a rubber stamp with a number on it.

| claim shape | the pattern that CAN fail | the pattern that cannot |
|---|---|---|
| "the credential/flag is set" | `grep -cE '^[[:space:]]*KEY='` (live assignment) | `grep -ci KEY` — counts commented placeholders and help text |
| "the key is set on every seat" | one live count per file, printed as a table | `grep -ci` per file, which reads the same on all of them |
| "N jobs are scheduled" | the metric the claim means: all rows vs `enabled: true` vs actually running | reading `N` off a listing |
| "the file is X bytes" | `stat -c %s` | `len(open(p).read())` — codepoints, not bytes |
| "the block is in the config" | a byte-level read of your own copy, quoted verbatim | assuming a loader would have picked it up |

**Always report the split, not the hit count.** Live vs commented is the finding; "2 mentions" is not.

```bash
for f in /opt/data/.env $P/.env /opt/data/profiles/*/.env; do
  printf '%-55s live=%s commented=%s\n' "$f" \
    "$(grep -cE '^[[:space:]]*ELEVENLABS_API_KEY=' "$f" 2>/dev/null)" \
    "$(grep -cE '^[[:space:]]*#.*ELEVENLABS_API_KEY' "$f" 2>/dev/null)"
done
```

Also **inspect the shape of the matching lines, values redacted**, before drawing a conclusion: a
commented `# KEY=` placeholder and a `# … set GROQ_API_KEY, … or KEY above` help line both match a loose
grep and mean the opposite of what a naive count suggests.

```bash
grep -in 'ELEVENLABS_API_KEY' "$P/.env" | sed -E 's/(sk_[A-Za-z0-9]+)//g' | cut -c1-120
```

---

## 2 — Scope the refutation: one seat is not the fleet

Your probe reads **your files**. When a claim is true somewhere and false on your seat, say both halves in
one line: *"false on my seat (0 live) ; the file that does hold it is X's — flagged, not settled for the
others I cannot read."* Asserting a fleet-wide refutation from one seat's file is the same overreach as
repeating the original claim.

Likewise when a **rationale** (not a fact) is being used to justify the event: a factual claim about your
config can be **refuted for your seat** while the *reason for the event* still stands for structural
reasons the sender measured. Refute the claim; do not silently relitigate the decision.

---

## 3 — Attribute an unexplained change before reporting it

Between two checkpoints, another writer can edit *your* config, `.env`, cron store or memory:

- match **size + mtime** against sibling profiles — identical size **and** mtime on several seats means a
  single fleet-wide sweep, not a targeted edit of you;
- then read **your own copy** and name what changed (`config.yaml` gained a `fallback_providers` block);
- report it as a named delta: who (inferred), when (mtime), what (the block), and the fact that you did not
  do it.

```bash
stat -c '%n %s %y' $P/config.yaml /opt/data/profiles/*/config.yaml      # same mtime+size => one writer
```

A census delta you cannot attribute reads as an anomaly and buries the deltas that matter. If the writer
emptied something you were relying on — a cron store, a queue — say plainly what it means for the next
reader ("a job I expect to re-check this next cycle no longer exists"), rather than only quoting the new
size.

---

## 4 — State the depth of every check, every time

"Byte-level read, not a parse" — because a loader may ignore a block the bytes plainly contain, and the
claim you are settling is about behaviour. Never upgrade a depth: a read is not a parse, a count is not a
schedule, and "the file says so" is not "the process is using it".

---

## 5 — Quote the instrument with the verdict

A refutation earns its place by carrying: the claim, **your** two numbers side by side, the file path, and
size + mtime (digest where it will not move). "Refuted" with no instrument is an opinion, and it will be
treated as one.
