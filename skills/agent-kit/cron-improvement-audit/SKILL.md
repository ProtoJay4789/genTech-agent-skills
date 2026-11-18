---
name: cron-improvement-audit
description: "Use when auditing cron jobs for IMPROVEMENT rather than repair — 'is this still the best way?'. A repair audit asks whether a job is broken; this one asks whether the job is still worth running, still shaped right, and still using the right mode. Fleet-wide, per-ring, iron-sharpening-iron."
tags: [cron, audit, improvement, fleet-standard, agent-kit, efficiency]
trigger: "When asked to audit cron jobs for improvement, when a ring's jobs feel stale/extravagant/duplicated, or on a scheduled fleet-wide cron review. NOT for a job that is simply failing — that is cron-health-standard."
related_skills:
  - ../cron-health-standard/SKILL.md      # is the job WATCHED? (repair)
  - ../cron-truth-layer/SKILL.md           # is the job's DATA true?
  - ../../devops/cron-delivery-audit/SKILL.md
  - ../../model-configuration-management/  # cost per job
version: 1.0.0
author: Gentech
---

# Cron Improvement Audit — "is this still the best way?"

**A repair audit asks: is it broken?** It fires when something is wrong, and it ends when the thing
works again. **An improvement audit asks a question a repair audit can never ask: would we build
this the same way today?** A job can pass every health check — green, on time, delivering — and
still be the wrong job, at the wrong cadence, in the wrong mode, costing 50× what it needs to.

**Nobody runs this audit by accident.** Nothing is broken, so nothing prompts it. That is exactly
why it has to be scheduled, and why it is run by the ring that owns the jobs: the author is the
only one who knows what the job was FOR.

---

## The rule

**Every job answers eight questions. "Unchanged" is a valid, expected answer for most.**

| # | Axis | The question | The improvement |
|---|---|---|---|
| 1 | **NECESSITY** | Would we build this today? Does anyone still read it? | **RETIRE.** A job whose output nobody reads is a diary, not a monitor. |
| 2 | **MODE** | Is it in the cheapest mode that does the job? | `no_agent` for fixed output · `monitor_script`/`monitor_url` to gate an LLM job · `continuity` for digests · `context_from` to chain |
| 3 | **CADENCE** | Is the frequency justified by how fast the input changes? | Slower for slow inputs. Silence-gated for anything that mostly repeats. |
| 4 | **NOISE** | Does it speak when nothing changed? | Silence-gate on TRANSITIONS (membership), not VALUES. One message per distinct problem. |
| 5 | **OVERLAP** | Does another ring run the same job? | **Consolidate on SCOPE, never on name** — one job, N books. |
| 6 | **INTENT** | Is its purpose declared, machine-readably? | Add the `by_id` entry to the intent registry IN THE SAME CHANGE. |
| 7 | **DELIVERY** | Is the target explicit and right? Do failures reach a human? | Explicit `platform:chat_id`. Set `failure_deliver` deliberately — never swallow silently. |
| 8 | **COST** | Is it pinned to a model more expensive than its work? | Route simple jobs to the cheap tier; leave reasoning jobs on a reasoning model. |

**A job that is green and cheap and necessary gets "unchanged" — and that is the majority. The
audit's value is in the two or three that are not.**

### Two audit questions the eight axes imply but do not ask

**① "What ends this job?"** — a bounded-purpose job (announce a transition, watch until a condition clears,
run once after a migration) **must name its exit condition AND have a working path to it.** Measured: a watch
built to announce one transition and then retire itself fired **once**, then ran **720 more times over 30 days**
because its kill switch had two independent fatal defects hidden by `|| true`: it read the job id from an env var
the job never set, **and** it passed a flag the pause command does not accept. **An exit condition that only
exists in prose is not an exit condition.** Audit test: for every job whose name or prompt says *watch · until ·
once · then goes silent*, run the retire branch against a throwaway job id and confirm the listing shows it
paused. **A one-shot that cannot end is how a fleet fills with zombies, and every one of them reports healthy.**

**② "Does the body obey the delta it announces?"** — silence-gating a REPORT is only half the fix. Measured: a
job was converted to delta reporting and its first version printed `· 1 CHANGED` in the header **and then listed
all 14 rows anyway** — the announcement was true and the body contradicted it, which is the same repetition
wearing a new header. **When a job reports a delta, every row-printing loop must filter through the same
changed-set predicate** (one helper, applied to the outbound list, the inbound list, the courtesy list and the
conversations list). Prove it by perturbing one row: the header must say 1 **and the body must print 1**. Keep a
count of the steady rows (`23 unchanged — not repeated below`) so the reader knows coverage was not reduced.
**A header count that disagrees with the row count is the defect; the delta itself is fine.**

---

## The axis after YIELD: CONFORMANCE — does the job fail HONESTLY?

**A job can be necessary, cheap, silent and yield-producing and still be a liar** — because when its source
refuses it, it reports a finding instead of an unknown. **"0 dead links" and "GitHub throttled me" print the same
number.** That is the same defect class as a missing file reading as zero, and only an audit asks about it while
the job is green.

**The conformance question, per job: if its source refused it, would the output say "could not look" or would it
report a finding?** Three protections answer it — **identify** (an identifying `User-Agent` where a network is
involved), **boundary** (403/429 is a refusal, not a transient to retry), **unknown** (the words that say we could
not see).

**WHICH jobs need them is decided by what a job READS** — the A/B/C tiering and its graduation rule are defined once,
in `cron-health-standard` §10; do not restate the table here. **This audit's job is to ask the question while every
job is still green**, and to record which tier each job sits in so a job that quietly grows a network call is
visible as a tier change rather than discovered as a false finding.

**Two failure directions, and only one of them gets checked by accident:**

- **Tier C is the point of the exercise.** A rule applied to every job is mostly theatre; adding a UA and a throttle
guard to a backup job changes nothing and dilutes the standard until nobody enforces it. **Leave C alone, and say
in the report that you left it alone** — otherwise a later pass "finishes the roll-out" by decorating jobs that
were already honest.
- **Prove the failing direction or the guard is decoration.** For every guard added, feed it the input that must be
refused: force the timeout, stub the 429, delete the file. A guard only ever tested on the happy path is a wish.

> Measurement recipe, the wrapper trap, and the instrument pitfalls that make a conformance audit report false
gaps: `references/conformance-tiers.md`.

---

## The axis the eight questions miss: YIELD

For any job whose purpose is to **produce an action** — find a lead, spot a stuck developer, catch a listing
that broke, surface an opportunity — recall is not the metric. **Count the chain end to end:**

```
found  →  acted on  →  sent  →  answered
```

**Measured: a lead-finder ran nine times, surfaced three real issues, and produced ZERO replies.** Every run was
correct; the filter was good; the tier gate suppressed noise properly. **And the job had never once done the thing
it was built for**, because its last step was "print a notification to the human". **Recall of 3/3 and yield of 0/3 is
a zero-value job with an excellent instrument inside it.**

**A job whose output is a nudge sits one step short of its purpose, and that step is the expensive one.** The nudge
costs the user attention every day and converts only if they do the last step by hand — which they will not, at
scale, at 11pm.

**The fix is to move the last step INTO the job as a draft, not to add more finding.**

- **Emit the artifact, not the pointer**: the paragraph that would be sent, the command that would be run, the PR
  body — `` `CANDIDATE REPLY: <draft>` `` or `` `NO ACTION — <why>` ``. **A job that says "no action" out loud is
  better than one that silently omits the row**, because silence reads as "couldn't check" when the truth is
  "checked, nothing to say".
- **The human keeps the send.** Drafting is the automatable half; acting under a person's name is not. Say so in the
  prompt so a future session does not "helpfully" post.
- **Wire the delivery to a RETRYING sender, and exclude seats that cannot receive.** A footer that says *"nudge by
  DM when this list is non-empty"* nudge-nothing; the band must call the spooling sender so a busy seat queues
  instead of dropping, and seats with **no registered channel** must be excluded in code — otherwise the job reports
  silence it structurally caused (`agent-to-agent-messaging` → the escalation-queue section).
- **Never template one remedy onto every match.** Measured: a draft generator reused a single `what worked for us`
  sentence across unrelated failures, producing exactly the generic reply the job's own footer warned gets filtered.
  **Key the remedy to the specific claim** and, when no remedy exists for a match, print that instead of borrowing
  one.
- **Before claiming a match, check the evidence is the SAME failure, not an adjacent one.** "We hit something like
  this" is not evidence; a related-but-different defect written up as first-hand experience is the fastest way to
  lose the audience the job exists to reach.

**Audit question to add for lead/outreach/opportunity jobs: what is the send rate, and what is the reply rate?** A
job with findings and no sends is not a pipeline, it is a reading list with a cron attached.

---

## The axis after YIELD: FIXABILITY — does each finding name the hand that unblocks it?

**A finding with no owner is a diary entry.** Measured: the identical set of issues was reported on five
consecutive days and nothing changed — not because anyone disagreed, but because the report never said whose
they were. **Every number was accurate and the job had zero effect.** That is the same disease as a lead-finder
with no send: correct instrument, no last step.

**Tag every finding with the hand that releases it, then compute the verdict:**

| tag | meaning |
|---|---|
| `FIXABLE-NOW` | the repair command handles this class — name which |
| `NEEDS-HOST` | requires an action outside the job's own privileges (stop the process that owns a file, rebuild an image) |
| `NEEDS-<owner>` | an interactive step only that person can take |
| `UPSTREAM` | nothing local persists; the fix ships in a later release |
| `UNCLASSIFIED` | read it before assuming a fix exists |

Then print `VERDICT: N of M fixable by this job as configured`, **computed by classifying the findings that
actually appeared**, never asserted from memory. That one line converts a five-day loop into a decision:
either a fix is available, or the job is honestly a "your hands" report.

### Classification is the diagnosis — the job must still ACT and ROUTE

A report that ends at `N of M fixable` leaves both halves undone, and the same findings come back tomorrow.
**Run the fixable half yourself, then hand the rest to its owner in a place that persists:**

- **`FIXABLE-*` → do it, then say what you did.** Report the fix as `✅ FIXED — <what changed> (<quantity>)`
  in the same output, and **prove it by the finding count dropping** (a sweep that removes one doctor issue
turns `5 issue(s)` into `4`). A self-fix that reports success while the count is unchanged did nothing.
- **Never delete during a self-fix.** Move operational data out of a synced/scanned tree, repoint every
  consumer, and verify by **listing the destination**, not by the mover's exit code. A vault or repo that
  silently loses a directory is worse than one that never had it.
- **Keep the self-fix idempotent and silent when there is nothing to do.** The second run of a bloat sweep
  must print nothing about bloat — otherwise the job reports a standing emergency forever and readers learn
  to skip the section that matters.
- **`NEEDS-*` → write it to the owner's QUEUE, never only to the chat.** A message scrolls away; the queue is
  where the next session and the human both look. One bounded section per job, **rewritten each run, never
  appended**: four runs a day at append-rate turns a 3-item queue into a 12-item one by lunchtime, and a
  queue nobody can act on is the same failure as a monitor nobody reads.
- **Prove the rewrite is bounded:** run twice, assert the section marker count stays at 1, and `diff` the
  **set of `##` headings** before/after — only the owned section may change. Every other section must be
  byte-identical, or the job is quietly editing somebody else's work.
- **Route only what no agent may do** — actions under a person's identity, interactive wizards, account/plan
  decisions, host commands that need privileges the job lacks. Anything an agent can do belongs in the
  self-fix half, not on the human's list.
- **Give each routed item its release condition**, not just its symptom: "needs the process that owns the
  file to be stopped" tells the reader which window to book; "WAL is large" does not.

**Decide fixability by reading the repair tool's own source, not its name.** A `--fix` flag existing does not
mean it can act on today's findings. Measured across three classes in one doctor tool: one branch **refused
while a live process held the file** it would repair (fails closed by design), one issue class had **no fix
branch at all**, and a third was documented in code as **never locally fixable** because the next update
reinstalls the pinned versions. **A repair command's flag is a capability, not a promise** — and the refusal
messages are often the most honest documentation in the tool.

**A repair command that rewrites configuration unattended is a decision, not a default.** `--fix` paths
commonly call a non-interactive config migration. On a multi-seat host with hand-tuned config, that is how a
`model.default` or a provider line disappears at 3am — a worse failure than the one being repaired. **Report
the fixable classes, ask, and if it is enabled take a config backup in the same job.**

**Anti-pattern: turning on `--fix` because it exists.** It repairs what it recognises and is silent about the
rest, so the job starts looking productive while the findings that actually matter are untouched.

---

## The second product: the register of what the job could NOT match

**A job that matches findings against a known table has two outputs, and it usually ships one.** The matches become
replies; **the non-matches are discarded** — and the non-matches are the only place the job can learn something it
did not already know. "No evidence of ours — do not reply" is a refusal that carries information: *this failure mode
exists in the wild and we have never met it.*

**Ship it as a durable register, not a line in the log.** `REGISTER.md` beside the job's output: one row per
unmatched mode with **first seen · times seen · do we have evidence**. That file answers the question a later
session cannot answer from any log — *what should we learn next* — and it grows on its own, at zero cost, because
the job was already reading those issues.

Rules that make it honest:

- **Name the SHAPE of an unmatched item, never "unknown".** A bucket called `UNCLASSIFIED` with a count is a shrug;
  a label (`version/dialect interop`, `settlement/facilitator`, `auth/402 shape`) is a hypothesis a human can act on.
  Keep an explicit `unclassified` bucket for the residue so nothing is silently dropped.
- **Frequency is a signal, so count it per DAY, and recompute — never add.** A register that adds today's count to
  the stored total on every invocation doubles when the job is re-run or backfilled, and a doubled number is
  indistinguishable from a trend. Store `seen-by-day.json` (date → mode → n) and derive totals and first-seen from
  it, so any number of runs in one day is idempotent. Prove it by running twice and diffing the register.
- **The consumer must not report its own blindness as a finding.** A trends pass over records that carry no text
  (URLs only, an empty dump) can only produce `UNCLASSIFIED` rows — measured, that printed *36 new failure modes*
  on the first run, all of them the absence of a title field. **When nothing is classifiable, print `UNKNOWN` and
  name the cause**, exactly as the primary job must.
- **A downstream consumer is a reason to make the dump UNCONDITIONAL.** An `--json <path>` flag that nobody passes
  leaves the reader with nothing to read; have the job write its dump every run (`backups/<job>-latest.json`) and
  say in the header that a consumer depends on it. **A flag exists for humans; a file exists for jobs.**
- **The register and the evidence table must agree.** When evidence for a mode is acquired, its row moves into the
  matcher's `EVIDENCE` table AND its register line flips to "have evidence" in the same change — otherwise the
  register slowly fills with lessons already learned, which reads as a backlog that is not there.

---

## The modes (what "the right mode" means)

These exist and are cheap. **A ring that uses none of them is probably over-running the LLM.**

| Mode | Use it when | Cost |
|---|---|---|
| `no_agent: true` | The script IS the job; stdout is the answer. Fixed format, no reasoning. | **zero LLM** |
| `monitor_script` / `monitor_url` | A cheap check can decide whether the agent needs to run at all. Identical output to last tick → **the agent is skipped entirely.** | zero LLM on no-change |
| `continuity: true` | The job should see its OWN last output — digests, incremental scouts, anything that must not repeat itself. | one LLM run |
| `context_from: [ids]` | Job B needs job A's result. **This is how jobs chain ("sync together").** | one LLM run |
| `attach_to_session: true` | The output should be repliable, not fire-and-forget. | one LLM run |

**Rule: an LLM job with a deterministic input is almost always a `no_agent` job that was written
before anyone measured the cost.** Check before you keep paying for it.

---

## How a ring runs it (the protocol)

1. **List your own ring's jobs.** `hermes -p <profile> cron list`. Read the raw `jobs.json` too —
   the CLI hides mode fields.
2. **Answer the eight axes for each job.** Most are "unchanged". Write the exceptions down.
3. **For each exception, state the change in one line**: job → axis → proposed change → why.
4. **Do NOT change anything during the audit.** An audit that edits what it audits cannot be
   reviewed. Propose; the ring's owner approves; then apply.
5. **Append your findings to the shared file** (see below) — *not* a reply in your own seat. A
   finding that lives only in a session log is a finding nobody can audit.
6. **One ACK line.** The findings are the deliverable; the ACK just says you filed them.

### The shared file (append-only, all rings write to ONE file)

`01-HANDOFFS/cron-improvement-audit/<date>-findings.md` — the vault path, so every ring can read
every other ring's proposals and the fleet sees its own duplication. **Append, never rewrite**
another ring's section.

**Report format per job** (one line each; `—` if unchanged so the exceptions stand out):

```
<profile> · <job name> (<id>) · <axis> · <current → proposed> · <why, one clause>
```

### The fleet-level findings (only the auditor writes these)

Step 3 is where the audit earns its name: **the cross-ring view is something no single ring can
see.** The auditor looks for:

- **Duplication** — the same job in two rings (consolidate on scope).
- **Orphans** — a ring with jobs for a seat that no longer exists.
- **Mode deserts** — a whole ring using none of the cheap modes.
- **Capability gaps** — the fleet declared a capability (a standard, a tool) and no ring uses it.
  *Check this against the standard's own recorded baseline, not against memory.*

---

## Anti-patterns

- **Auditing only for breakage and calling it an audit.** That is the repair audit. This one exists
  for the jobs that are working fine and shouldn't be.
- **Editing during the audit.** Propose, then apply. An audit that mutates its subject cannot be
  reviewed by anyone else.
- **Reporting "all jobs healthy" as the outcome.** Health is the other audit's question. This
  audit's outcome is a list of proposed changes, and "none" is only credible if the eight axes
  were actually answered.
- **Trusting memory about what was built.** Check the live fleet. The last time this was done by
  memory, a fleet believed it ran capabilities that zero jobs used.
- **A ring auditing another ring's jobs.** Ownership is what makes the "what was this FOR" answer
  trustworthy.
