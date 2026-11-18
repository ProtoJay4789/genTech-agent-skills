# Estate probes — measuring declarations against behaviour

Read-only probes. Substitute `P=/opt/data/profiles/<seat>` and `<STORE>` for the estate you are
auditing. Run multi-line probes from a scratch file with `python3 <file>`: it survives a timeout, is
re-runnable verbatim when a number moves, and keeps quoting out of the shell.

---

## 1 — Live enumeration, WITH the timestamp

The read time is part of the measurement. Print it in the same output as the count so a later reader can
reprove it.

```bash
date -u '+measured at %Y-%m-%d %H:%M:%S UTC'
cat <STORE>    # raw store, not the CLI summary: the CLI hides mode fields
```

Per ring, print the total, the enabled count and the mode fields. **Re-run this at the END of the audit**
and report any delta: another owner editing the store mid-read is normal, and a silent re-number is
indistinguishable from an error.

---

## 2 — Registry coverage ratio (a declaration vs live ids)

```python
# rows that match NOTHING are the finding
live = {job["id"] for every profile's cron/jobs.json}
reg  = json.load(open(REGISTRY))["by_id"]
print("live:", len(live), "| registry rows:", len(reg))
print("covered:", len(live & set(reg)))              # report THIS as a ratio
print("registry rows matching no live id:", len(set(reg) - live))
```

Report `covered / live` ("0 of 13"). A registry with rows but zero coverage is a fossil — its rows explain
history and triage nothing. Never quote its row count as the size of the estate.

---

## 3 — Wiring check (existence is not deployment)

```bash
grep -rl '<tool-name>' /opt/data/scripts /opt/data/profiles/*/scripts /opt/data/profiles/*/cron 2>/dev/null
```

Then confirm at least one job's `script` or prompt names it. **Empty output = unwired.** Report
"restored, not wired" and cite the check. A file with today's mtime is the prime suspect: a restore is not
a deployment, and a capability table that counts it is reporting an intention.

---

## 4 — Silence counting from the run record (the grep trap)

Each job's runs are recorded at `<profile>/cron/output/<job id>/<timestamp>.md`. A silence-gated job's
body carries a status line saying it was silent; a job that spoke has a non-trivial body.

**The trap:** counting with the literal label returns zero even when every run was silent, because the
label is written with markdown emphasis around the word (`**Status:** silent (empty output)`) — so
`grep 'Status: silent'` matches 0 files and a report of "0 of 36 silent" is exactly inverted.

```bash
grep -l 'silent' <output-dir>/* | wc -l      # silent runs
ls -1 <output-dir> | wc -l                   # total runs
```

Before trusting ANY counting pattern, run it against one file you already know is non-silent. Zero from a
pattern that cannot match is the most expensive kind of zero.

Then read the minority: the run that spoke is usually the finding you want (a real transition), and it is
how you tell a correct gate from a broken one.

---

## 5 — Delivery-consumer trace (before calling a job silent)

```bash
head -20 <profile>/scripts/<wrapper>.sh     # 1. the wrapper's own header states the contract
# 2. does a CONSUMER name the artefact? grep each job's prompt for the state path
# 3. the artefact itself
ls -la <the state file>
```

A `deliver=local` job with a documented contract, a live state file on disk, and an enabled consumer
whose prompt names that path is **working as designed** — the finding is not the local delivery.

**Then read the failure branch of the wrapper.** The pattern that matters:

```sh
out="$(...)"; rc=$?
if [ $rc -ne 0 ]; then echo "FAILED"; exit $rc; fi   # <-- exits BEFORE the evidence is written
printf '%s\n' "$vout" > "$VERIFYLOG"                # <-- the consumer reads this file
```

On a hard failure the consumer reads the **previous run's PASS**. Propose writing the state/heartbeat on
the failure path too (or a failure sentinel the consumer checks), and set `failure_deliver` explicitly —
`null` is unset, not a decision.

---

## 6 — Per-field capability census (declare the depth)

```python
counts = {f: sum(1 for j in jobs if j.get(f)) for f in
          ("no_agent", "continuity", "context_from", "monitor_script", "monitor_url", "attach_to_session")}
```

Report every count as **field-level** unless you also read the scripts. Then state the two consequences
that keep the number honest:

- jobs that gate *inside* their script (empty stdout, state-file-only writes) are invisible to this count;
- in an all-`no_agent` ring there is no LLM for a gate to skip, so the field's zero costs nothing and
  adding it would buy declaration only.

---

## 7 — Filing and verifying in a shared document

```bash
F=<shared findings file>
stat -c '%s B | mtime=%y' "$F"; md5sum "$F"
grep -c '<other owner heading>' "$F"     # their section still intact
grep -c '<my ACK line>' "$F"              # mine present and findable
```

Append to your own section only. Verify the other owners' sections and your own line before you report
that you filed — the file is the deliverable, and a clobbered sibling section is a worse outcome than a
finding not filed.
