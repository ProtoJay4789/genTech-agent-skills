---
name: verification-probe-execution
description: "Use when a probe batch must produce measured numbers."
version: 1.0.0
author: Gentech
license: MIT
tags: [verification, probes, measurement, unattended, evidence, coverage]
metadata:
  hermes:
    tags: [verification, probes, measurement, unattended, evidence, coverage]
    related_skills: [proving-a-negative, claim-provenance, verify-after-every-action, checkpoint-ack]
trigger: "Before running any multi-step evidence batch — a checkpoint ACK census, a seat/health audit, a drift scan, a pre-change survey — i.e. whenever the deliverable is a set of measured numbers produced by commands."
---

# Verification Probe Execution — batches that actually run, numbers that carry their limits

This skill owns the **mechanics** of gathering measured numbers: how to write a batch so it executes on a
surface where nobody can approve anything, how to report what it could not see, and how to leave the
instrument behind as an artifact. The **doctrine** lives in its own homes and is not restated here:
`proving-a-negative` (what an absence claim is worth), `claim-provenance` (every claim carries its
instrument). This one is about the batch itself.

## When to use

- A checkpoint ACK, a seat census, a health or drift audit, a pre-change impact survey — any task whose
  output is a set of numbers someone else will plan around.
- Any probe with more than about three steps, or one that walks many subjects (processes, profiles,
  files, records).
- Any probe that must run where no human is present to approve a command.

## Rule 1 — Write the probe as a FILE; never type it as one long command line

A multi-step probe typed inline (a `for … do … done` with a redirect or a pipe inside the body) is exactly
the shape static pre-execution analysis cannot resolve, so the whole line is held for approval. On an
unattended run — cron, a checkpoint, any no-user-present surface — there is nobody to approve it, so **the
probe never runs and the report gets written from what you already believed.** The two steps that work in
every session, attended or not:

1. write the probe to a file (`<profile>/cache/scratch/probe-<topic>.py`, or the skill's own `scripts/`);
2. run it as `python3 <that file>` through the terminal.

It executes in one call, survives a timeout, and **the file is left behind as the instrument** — which is
what lets a later session re-run the identical probe instead of re-deriving one.

## Rule 2 — Read-only by construction, and accumulate as you go

- A probe **never writes to the system it measures.** No restarts, no fixes, no "while I'm here" edits —
  repairing the thing you are measuring destroys the measurement.
- For a batch over many items, **append each item's result to a JSON/CSV in the workspace and aggregate from
  the file at the end.** Progress then survives a timeout, and the count is computed rather than recalled.
- Keep probe scratch under the profile's scratch dir: it is ephemeral by design, so it never appears in a
  later census as work in flight.

## Rule 3 — Count the subjects you could NOT read, and print `readable/total`

Any probe that walks per-subject (one file per process, one entry per store, one directory per account)
**fails partially**, and a bare zero silently promotes the unreadable remainder into evidence.

- Guard every per-subject read and count the failures; print them **on the same line as the count**:
  `seen=45 readable=19 unreadable=26 carriers=0`.
- "0 processes carry the key" is a claim about 45 processes. "45 seen, 19 readable, 0 of the 45 seen carry
  it" is a measurement a reader can attack.
- A probe that dies on the first `EACCES` returns nothing at all, which reads to the next reader exactly like
  a clean population. Never let one unreadable subject abort the batch.
- The same holds for a directory you could not list: **an unreadable subject is UNKNOWN, never clean.**
- **A crash is not a finding — import each check lazily so one missing dependency cannot kill the batch.** A
  checker whose top-level `import` of a sibling module fails exits non-zero before it reads anything, and the run
  then reads exactly like a red result on the thing you asked about. Measured: a two-check probe died on an
  import, so the *other* check — which would have passed — never ran, and the report said the whole surface was
  broken. Do the import inside the per-check function, catch `ImportError` as its own outcome, and keep going.
- **A false RED costs as much as a false GREEN.** A green light is trusted until it hides something; a red light
  is acted on immediately, so a crash mislabelled as FAILURE sends the repair at the wrong layer. When the
  instrument cannot reach its data, the honest output is `COULD NOT MEASURE` with the reason, not `FAILED`.

## Rule 4 — Label the verdict you actually have

Keep **three** distinct sentences available and pick honestly: **verified** (the instrument covered the
population) vs **consistent, not verified** (the readable subset agrees and the rest could not be opened) vs
**could not measure** (the instrument never reached the data — a missing file, a failed import, an unreachable
endpoint). A missing file and a failed read produce the same empty screen, so say which one you saw — "file
absent" and "the read raised EACCES" are different findings — and never let a crash borrow the word *failed*,
which is a claim about the subject rather than about the instrument.

**Give the three outcomes three exit codes** so a caller can tell them apart without parsing prose:
`0` = ran and is clean · `1` = ran and found a defect · `2` = could not measure. A checker that returns `1`
for its own inability to run is the single most expensive shape here, because every scheduled consumer of it
will page someone about a fault that does not exist.

## Rule 5 — Split a composite claim, and name the artifact each half lives in

A claim about "the config" (or "the setting", "the key", "the value") names a **logical setting, not a
file**: fleet-level settings can live in a root or gateway config or a shared fleet file, while each seat
carries its own copy. So:

- Measure **your own artifact**, then report **per half**: "key present in this seat's `.env` ✓ / the `tts`
  block absent from this seat's `config.yaml` ✗ — **refuted for this seat**; the root config would settle
  the fleet-wide half."
- One seat's copy never proves a fleet-wide claim false — and it never disproves the half that does hold. A
  single verdict on a two-part claim is wrong in one direction whichever way you give it.
- Say the depth of the check: a byte-level read is not a parse. Never upgrade one into the other.

## Rule 6 — Stamp, append, and verify the record you leave

- **Read the stamp back against the file's own mtime** and correct it. A header a minute ahead of its own
  mtime is a small inconsistency in a document whose whole value is that its numbers agree.
- **Appending to a large append-only ledger:** the file tool truncates long lines, so you cannot anchor a
  targeted edit on a multi-megabyte record's tail, and a whole-file write would rewrite the ledger. Append
  with a two-line script (`open(path, "a")`) guarded by an **idempotency marker** — check the line is not
  already present before writing — so a re-run cannot double-post.
- **Verify after writing:** digest + size + mtime, and a `grep -c` on a distinctive marker inside the file
  you just wrote. "I wrote it" is a claim; the readback is the evidence.

## Rule 7 — Silence is not an empty result

A held command, a timeout, or a probe that failed before printing its header produces **no output**, which
is character-identical to a verified clean result. Before reading silence, confirm the instrument executed:
check the exit code, require a header/first line, and print a count of subjects walked. A run that never
started and a run that found nothing must not share an output shape.

## Rule 8 — Prove the instrument can FAIL, and measure the EFFECT, not the channel

Two defects make a probe lie in the same direction: it reports clean, and the reader believes it.

- **A probe that has only ever reported success is a constant with a name.** Before trusting a clean run,
  point the probe at a subject that *must* fail — a name that does not exist, a path that is not there — and
  confirm it reports the failure. An instrument unable to produce the negative makes its positive meaningless.
- **A channel's empty response is not evidence about the far side — measure the far side's own artefact.**
  When the question is "did X reach Y, and did Y act?", the request's return value is only one signal and it is
  the weak one: an empty reply is character-identical to a failed delivery. Take a **second, independent**
  signal from Y's own record — its log file's mtime/size advancing, a session row appearing, a file it wrote —
  and classify on the PAIR:

  | channel replied | far-side artefact advanced | verdict |
  |---|---|---|
  | yes | — | delivered |
  | no | yes | **delivered, unreported** — the channel lost the reply, not the message |
  | no | no | failed |

  The middle row is why this rule exists. A healthy transport that drops its own reply gets reported as an
  outage, and the repair is then aimed at the wrong layer. Measured: three of three wakes landed and the client
  printed nothing — an outcome already written up as both a timeout and an auth failure, neither of which was
  happening. **Give the middle state its own name** (here `silent_ok`) so it can never be silently folded into
  either neighbour.
- **A timeout reported by the far side is not a latency finding.** Read both ends' windows before blaming the
  clock: a receiver-side orphan timer can sit an order of magnitude below the caller's own timeout, so a slow
  subject and a dead one produce the identical sentence. When a probe reports "timed out", suspect the path or
  the credential first.
- **Validate a parser against a known answer before reporting its output as a finding.** A parse bug and a real
  gap are indistinguishable in a results table; the retraction costs more than the check.
- **Check the QUERIES themselves for degeneracy: independent hypotheses must not return the same number.**
  A search-backed census runs N different questions; if three or more of them return an **identical total**, the
  queries have collapsed into one generic match — that is a broken instrument, not a finding. Measured: six
  distinct failure-mode hypotheses each returned `29,573`, because the URLs were built with hand-rolled
  `.replace()` chains instead of a real encoder, so the distinctive terms were mangled away. **Build query URLs
  with `urllib.parse.quote(q, safe='')`, never a `.replace()` chain**, and prefer a few **quoted phrase** queries
  over parenthesised OR-groups, which degrade silently on the same endpoints. Ship the guard with the probe:
  count how many hypotheses share a total and **refuse to print a ranking** when three or more tie, with the
  reason stated — a degenerate batch that prints a sorted table is worse than one that prints nothing, because
  the table looks like research.
- **Rank a frequency census by SPECIFICITY, not volume, and say so in the output.** A broad query's total is
  contaminated by whoever generates the most text (bots, bulk-issue repos, syndicated digests); a narrow query's
  handful of hits are the people actually stuck. Measured: a loose phrase matched **1,934** issues of mixed
  provenance while a specific error string matched **2** — the 2 named real, unfixed pain, and the 1,934 could
  not be attributed to any one cause. Print both columns (`total` and `open in newest N`) and let the small,
  sharp number carry the conclusion.

## Rule 9 — A shell pipeline rewrites both the VALUE and the exit status

Two mechanics of `|` cost real conclusions in one session, in opposite directions: a number that was never
there, and a failure that was read as a success.

**`awk` with `printf` and no newline CONCATENATES across input lines.** A per-file field print glues every
record's value into one string:

```bash
ls -la /opt/data/profiles/*/state.db-wal | awk '{printf "%.0f", $5/1048576}'   # 649 47 25 9 -> "64947259"
```

Rendered as `2548649 MB` — a number large enough to look catastrophic and specific enough to be believed.
**Put a newline in the format** (`printf "%.0f\n"`), or accumulate and print once in `END`, or use `stat`
per file. Any figure produced by `printf` over multiple records is suspect until you see **how many lines
came out** — one line from N records is the bug.

**`$?` after a pipe belongs to the LAST stage.** `cmd | tail -5; echo "exit=$?"` reports `tail`'s status, so a
probe exiting `2` reads as `0`:

```bash
out=$(python3 probe.py 2>&1 | tail -5); echo "exit=$?"      # WRONG — tail's status
```

This produced the exact inversion this skill exists to prevent: a correctly-failing verifier was declared
"lying" and a genuine finding was nearly dismissed. Use `set -o pipefail`, read `${PIPESTATUS[0]}`, or run
the instrument unpiped and truncate the output afterwards. **Before accusing an instrument of dishonesty,
confirm you read ITS status and ITS number** — the pipe is the first suspect, not the script.

**The same rule covers counts the tool announces.** `mv -print`, `rsync --stats`, `find … -exec … -print`
report what the command *chose to act on*, not what changed. Count the state before and after and print the
difference.

## Pitfalls

- **Reporting a bare zero from a partly unreadable probe.** The single most believable false negative — it
  looks like diligence. Print the split (Rule 3).
- **Typing the batch inline on an unattended surface.** The command is held, nothing runs, and the report is
  composed from memory. Write the file (Rule 1).
- **Reading a requester's claims as your own measurements.** Re-measure each claim about your seat and say
  measured / refuted, with the number that settles it — never echoed back as fact.
- **Treating "the batch ran" as "the numbers are good."** A probe that executed proves nothing if it could
  not have seen the thing you asked about.
- **Letting a probe crash on the first permission error.** One unreadable subject ends the batch and the
  report looks clean.
- **A stamp that disagrees with its own mtime**, and a record appended without an idempotency marker.
- **Leaving the probe only in the session.** A batch that exists nowhere on disk cannot be re-run, so its
  numbers can never be re-checked.
- **Reading a piped command's output and exit status as the command's own.** `cmd | tail` reports the last
  stage's status, and `awk '{printf}'` without `\n` concatenates every record into one value. Both produce a
  confident, specific, wrong number — see Rule 9.
- **Declaring the instrument broken before reading its actual exit code.** "The verifier says success while
  the thing failed" is a strong accusation; check for a pipe, a subshell, or a masked status first.

## Support files

- `scripts/seat_probe.py` — a read-only seat census (held work, artifacts by bytes + mtime, session-DB
  integrity, cron summary, environ census **with its readability split**, md5 of any extra artifacts).
  Assembled from probes exercised in practice; its parts are known-good but the assembled file has not been
  run end to end, so **dry-run it once** (`python3 scripts/seat_probe.py <profile_dir>`) before you rely on
  its output for a report.
