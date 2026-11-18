# Conformance tiers — the measurement recipe

Companion to the CONFORMANCE section of `cron-improvement-audit`. This is how to *measure* which jobs read
something outside the host, and the three instrument defects that will make the report wrong if you do not
know them.

## 1 · Resolve every job to the file that ACTUALLY runs — first, always

**Half a mature fleet's cron "scripts" are two-line wrappers.** `<job>.sh` calls `/opt/data/scripts/<job>.py`,
or `x.sh` calls `y.py`. A grep of the wrapper answers a question about the wrapper.

Measured consequence: a naive pass counted **8** jobs reading the network; following the wrappers found **14**.
The six missing ones were exactly the jobs whose guards had never been checked.

```python
# follow a tiny wrapper to its canonical target before judging it
if len(txt.split("\n")) < 40:
    for target in re.findall(r"(/opt/data/[\w./-]+\.py)", txt):
        if os.path.exists(target):
            path, txt = target, open(target).read()
            break
```

**A checker that does not do this under-reports network jobs and over-reports "no UNKNOWN handling"** — both
false, both delivered with confidence.

## 2 · Classify on source shape, never on job name

```
network?  api.<vendor>  |  urllib.request  |  requests.(get|post)  |  subprocess.run(["curl", …])
local?    open(  |  Path(  |  glob  |  sqlite3  |  json.load
shell?    subprocess.run(["docker"…] or any system probe
```

A job named "…watch" may read only a state file; a job named "…digest" may call three APIs. **The name describes
the purpose; the imports describe the failure modes.** Tier from the imports.

## 3 · Vocabulary: the instrument must know the synonyms

**A check that says `ABSTAIN` or `UNMEASURED` has done the right thing** even if it never types `UNKNOWN`.
Measured: a job printing `ABSTAIN — lane UNMEASURED` was reported as a gap purely because of the word it chose —
the instrument accused the better-written job.

```
UNKNOWN | NOT RUN | INCOMPLETE | ABSTAIN | UNMEASURED | could not | cannot | unavailable
```

**Fix the instrument before you "fix" the code.** A false gap costs the same trust as a miss, and it teaches the
reader to skim the report.

## 4 · A guard inherited through an import is a guard

`job.py` that calls `gh_guard.gh_get()` sends whatever User-Agent `gh_guard` sets. A per-file grep says the job
sends none. **Follow `import <transport>` one level and check the transport** — otherwise every job routed through
the shared helper is reported as unprotected, which is the opposite of true.

## 5 · Attribution and the two things this audit cannot see

- **A shared token has no per-caller usage.** GitHub reports remaining quota for the token, not for the job. So a
  conformance report can say *"the budget is thin"* but never *"this job spent it"*. **The honest attribution is
  a line in the job's own handoff** (`Spent: ~N core, M searches`), not a dashboard.
- **A throttle has two meanings and they need different words.** *"The gateway said this service is down"* and
  *"the gateway did not answer"* are both `UNKNOWN`, and only one of them is a fault. If a monitor collapses them,
  the operator chases a backend that was never broken.

## 6 · The failure this audit is for, stated once

```
failed read  →  empty value  →  compared against expectation  →  reported as a finding
```

Measured instance: a site-sync job set `live = ""` when a fetch threw, compared it to local, and called the page
**drifted** — and its `--apply` mode would then redeploy a page that was never wrong. **A write triggered by a
failed read.** The fix is one word in the classifier: `UNVERIFIED` is not `DRIFT`.

**When you find this shape, look for the write path.** A monitor that mislabels is annoying; a reconciler that
mislabels *and then acts* is the expensive version.

## 7 · The instrument can mismeasure its OWN work

The defects above are about the job misreading its subject. These are about **you misreading the job** — and they
all produce a confident, wrong number rather than an error.

- **A pipeline reports the LAST stage's status, not the script's.** `script.py | tail -5; echo $?` prints
  `tail`'s exit code. Measured: a verifier that correctly exited **2** was reported as `exit=0` because `tail`
  succeeded — i.e. a working guard was written up as a silent failure. Capture the status immediately after the
  command (`out=$(cmd); rc=$?`), or read `${PIPESTATUS[0]}` in bash. **When an instrument's verdict and your
  measurement disagree, suspect the measurement.**
- **`ls -la <many files> | awk '{printf …}'` concatenates across records.** `printf` without `\n` emits no
  separator, so four WAL sizes became the single string `2548649 MB`. Use `stat -c %s` per file and take the max,
  or print with an explicit newline.
- **Count a move by what is GONE, never by what the mover announced.** `mv -n … -print | wc -l` silently skips
  targets that already exist, so it under-reported **2 against 9 actually moved**. List the directory before and
  after and subtract; then list the destination as proof.
- **Never write a pointer file into the directory you just emptied.** It becomes the next run's "moved 1 file"
  — a fix the job did not perform, reported as a fresh one. Put the pointer one level up, outside the swept path,
  and say why in a comment so a later editor does not "tidy" it back in.
- **Idempotency is a test, not an intention:** run the job twice and diff the artifact (marker count `1`→`1`, every
  other heading unchanged). A sweep that shrinks correctly on run 1 and claims work on run 2 is not idempotent.
