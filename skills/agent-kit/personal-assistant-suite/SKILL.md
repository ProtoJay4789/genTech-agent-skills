---
name: personal-assistant-suite
description: "Use when a fleet needs one human-facing report job."
category: agent-kit
version: 1.0.0
author: Gentech
license: MIT
tags: [cron, reporting, digest, multi-agent, noise, consigliere]
---

# Personal Assistant Suite — the single human-facing voice

The fleet's reporting layer: N silent collectors + ONE consumer job that produces the single report the
human reads. Load this when building, repairing or reviewing that job.

## When to use
- A fleet of agents produces more internal traffic than the human actually reads.
- The human asks for "a summary of what the agents are doing", a morning brief, or a digest.
- You are repairing or rebuilding the reporting layer after it was lost.

## The architecture (two halves, different jobs)
- **Collectors** gather data and stay silent — `deliver=local`, zero human noise. They exist to produce
  data, not to be read. A collector that pings the human is the bug this pattern removes.
- **The consumer is the ONLY voice.** It reasons over the collectors' latest output at fire time and
  produces one report.
- **Adding intelligence must not add a ping.** A new data source slots in as one more collector plus a
  line in the consumer — never as a new job that messages the human.
- Chain them with the cron engine's "inject another job's last output" feature so the consumer reads
  *fresh* data rather than a file written yesterday.

## The governing bar — what earns the human's attention
**Transit is not news.** An agent sending another agent a note is the system working, and there is always
traffic — so a traffic digest is a list of filenames that tells the reader nothing.

An item earns attention ONLY if it is:
- **(a) addressed to the human** — a note in their inbox lane, a direct question, an item in their queue
- **(b) stuck / blocked / failing** — a handoff past its window, a job erroring, an endpoint down,
  a watcher that has stopped firing
- **(c) a decision only they can make** — money movement, a public release, a legal or account action,
  an approval gate
- **(d) a deadline inside 72h**

If none are true: say so in ONE line, or output nothing. **Never enumerate handoffs, file names, or
"X messaged Y". Never report work in progress.** Report only what is DONE, STUCK or DECIDED.

### The owner line — every report ends by naming who must act

**A list of items with no owner line leaves the human to work out whether any of it was addressed to
them**, and the answer they reach is usually "was I supposed to approve something?" — which means the
report failed while every line in it was accurate.

- **End with an explicit line:** `NEEDS <HUMAN>: nothing. No approval is pending.` — or the named decision
  plus its options. "Nothing needs you" is a complete report, not a missing one.
- **Never leave the decision surface implicit.** If an item needs a choice, state the choice and the two or
  three ways it could go; if none does, say none does. A reader should never have to infer their own
  involvement from a count.

### "Waiting on us" is a claim you have to read the thread for

**Last-speaker is not the same question as "they asked us something".** A thread whose last word belongs to
the other party can be a question — or a concession, an apology, a withdrawal, or a thank-you, none of
which need a decision from anyone.

- **Read the last body before marking anything owed.** Two verdicts: **OWED** (a question or blocker sits
  with us) and **COURTESY** (a close line is enough). Measured: a thread reported as open for a day
  contained nothing but the other party conceding two errors and withdrawing their request.
- **Quote their words and the timestamp, not the comment count.** "4 comments, last from @them" sends the
  reader off to look; "they said: '<one line>' at <time>" is the briefing.
- **State the change, not the total.** A backlog reported at the same N every run trains the reader to
  skip it. Report `delta 0` and the oldest item, or report nothing.

### An AGE is not a reason — check whether anything ever ASKS that seat

"Seat X is N days behind" is the most misleading sentence a report can contain, because it silently
asserts a cause. A handoff is a file write that notifies nobody: if no scheduled job on that seat reads
its inbox, the seat is not late, it was **never asked** — and the human reading "behind" concludes a
colleague is lazy when the seat was never wired.

**Before attributing a backlog to a seat, read its cron and count its readers:**

```python
import json
for seat in SEATS:
    j = json.load(open(f"/opt/data/profiles/{seat}/cron/jobs.json"))["jobs"]
    on = [x for x in j if x.get("enabled")]
    readers = [x for x in on if any(k in (x.get("name") or "").lower()
                                    for k in ("inbox", "ack", "handoff"))]
    print(f"{seat}: {len(j)} jobs, {len(on)} enabled, {len(readers)} inbox readers")
```

- **Two shapes, two different reports.** *Busy and deaf* (many jobs, none reads mail) → "no inbox reader";
  *no jobs at all* → "this seat has no schedule to read anything, and no working pattern to copy". A
  report that cannot tell these apart from ordinary lateness is reporting a mood, not a state.
- **One direct ask is the control.** Send the seat a real request and time the reply. A fast substantive
  answer proves the channel is healthy and the trigger is missing — say exactly that.
- **Never let the reporter write another seat's acknowledgement.** An ACK must come from the agent that
  owns the row, or it is a forged receipt. A reporter may only *list* what is missing.

### An age claim about an EXTERNAL system must be tested in the present

"Broken for N days" is a claim about the current state, not a historical one, and the row it came from
may describe a state that was already fixed. Measured: a report carried a multi-day outage that had in
fact been closed days earlier — the source row was stale, and the human was being sent to repair
something already repaired.

- **One probe before repeating an age.** Hit the live surface and read the present. If the present
  contradicts the row, **correct the row, then report the correction** — including that you had repeated
  it — or the stale claim survives in the place the next reader trusts most.
- **A peer's correction outranks your report.** When the seat you accused replies with evidence that the
  thing is fixed, verify *their* claim against the live surface, then publish their version. Retracting a
  stale row is worth more than defending a well-formatted one.

### A report's MECHANISM is a guess even when its numbers are measured

The count in a report is usually honest; the **explanation attached to it** is written prose, and it is
where a report goes wrong without looking wrong. A confident structural theory ("that lane is a naming
artifact, an agent writing to itself"; "no watcher owns that directory"; "the store mislabels what it
holds") reads as an established fact beside a real number, so the reader acts on it.

- **Verify the mechanism against the artifact before acting, especially when the fix is a rename or a
  delete.** Measured: a lane named `<sender>-to-<target>` was reported as a doubled-prefix bug because the
  target's own name began with the sender's name. It was the **correct** name — the note in it had been
  answered in the return lane — and renaming it would have orphaned seven notes. A plausible-sounding
  diagnosis is more dangerous than a wrong count, because the count invites a check and the diagnosis
  invites an edit.
- **A reporter can be right about the symptom and wrong about the cause in the same paragraph.** Split
  them: keep the measurement, discard the story until you have reproduced it.
- **Say you corrected it.** When a report's mechanism is disproved, record the correction where the next
  run will read it — otherwise the same invented cause is regenerated nightly from the same inputs.

## The verdict — an opinion, or it is an unfinished sentence
A list of facts is a clerk; a recommendation is an adviser. **Every item carries a verdict tag:**
- `[GO]` — you would do it; give the one reason it is worth doing.
- `[NO-GO]` — you would not; give the one reason, and be willing to be wrong out loud.
- `[HOLD]` — not yet; name the SINGLE fact that would flip it.
- `[YOURS]` — only the human can act; give the exact action (the click, the form, the words).

Line shape: `• <what it is> · <file cited> → [ACT NOW|TODAY|SKIPPABLE] [VERDICT] — <your reason>`

- **No fence-sitting.** Banned: "consider", "you may want to", "it might be worth", "no action needed
  at this time". `[HOLD]` without naming what would flip it is a hiding place, not a verdict.
- You are allowed to be wrong. You are not allowed to be vague.
- Verdicts obey the same honesty rules as everything else: cite the file, never invent urgency, never
  manufacture a conflict to look useful.
- If two items conflict, say which one you would do first.

## Modes, picked by slot
Derive the mode from the current UTC hour at run time; never use the wrong mode's format.
1. **MORNING BRIEF** — the one slot the human reads first (≤2500 chars): what needs them today, each with
   its verdict line · what completed overnight with NO return note, and what broke · today's agenda
   (deadlines due, human-gated items, one-shot jobs firing today). Close with ONE personal take: what you
   would do first and why. If the desk is clean, say that in one line and stop.
2. **CHECK-IN** — recurring daytime slots; the exceptions-only pass. **If nothing clears the bar, output
   NOTHING AT ALL — zero bytes, exit 0.** Not a one-line reassurance, not `Quiet — nothing needs you.`
   Jordan named this explicitly: *"if there's nothing to report, it probably shouldn't run. It should be
   silent, right? So that way, every two hours, I'm not just getting blasted."* **An always-present line
   is what makes the report unreadable**, because the reader has no baseline of quiet to contrast with —
   and a job that always speaks cannot report an anomaly. No verdict line on a quiet report; there is
   nothing to have an opinion about.

   **The one exception is a DIGEST slot with a number** (a queue depth, a spend total, a conversion rate):
   there, *nothing changed* IS the information, and the slot may speak every day — briefly, and with the
   number. A digest must say in its own header that it is a digest and why; an unconditional report with
   no such sentence is a defect, not an exemption. Test: *would a week of quiet hide information the human
   explicitly asked for?* Yes → digest. No → silence.
3. **DAY WRAP** — the last slots (≤1500 chars): what got COMPLETED today, grouped by seat (read the
   *return* notes, not the outbound traffic) · open blockers · anything the human worked on that got no
   return note, flagged by name and stated as nobody-closed-it. Open items carry verdicts; shipped items
   do not.

## Schedule to the human's real window, not to the clock

**Quiet hours are only half the availability picture.** A human who works shifts has a second blocked
window that changes at short notice — and a brief that asks for a decision inside it produces an item
nobody acts on, which then gets reported as pending for days.

- **Keep a standing availability note and read it before scheduling** anything that expects a reply.
  Record short-notice changes the same turn they are mentioned — dated, with what they displace.
- **When in doubt, put human-gated work after the end of their working day** and say why. Late is
  recoverable; ignored is not.
- **Switch the mode, not just the volume, during a blocked window.** A brief that lands while the human
  is at work should REPORT and HOLD. Asking for a decision there is how a good item gets buried and then
  re-asked for days.
- **An item re-asked three times is a scheduling defect, not a reminder.** If the same owner-action has
  appeared in three briefs, it is competing with nothing — make it the only thing in the first open
  window and say so.

### Cadence is about NOT MISSING THINGS; placement is about them being ACTIONABLE

Jordan asked for a multi-hourly report for one reason: *"so that it's less likely for me to miss something
that we were just talking about."* That is a **memory** requirement, and it is satisfied by density. It is
**not** satisfied by density alone — five of six runs landing inside his shift produced five reports he
could not act on.

- **Set the rhythm from what the human forgets, then place it against their real window.** Every 2–3 hours
  is right for a conversational fleet; a two-hour gap that lands at 09:30 and 11:30 while they are at work
  is two reports spent for nothing.
- **Put the reads where the human is:** one before the working day (the overnight digest, read once with
  coffee), then the slots after they are home, when a decision can actually be taken.
- **Mid-shift runs become detection, not delivery** — they may run, and must be silent unless something is
  genuinely urgent. This is the silence gate doing the placement work (see `silence-gated-monitors`).
- **Never assume a quiet reply window is disinterest.** During known work hours silence is not disagreement;
  the queue is where an item waits, not a repeated question in chat.
- **Two job families are deliberately exempt from this placement and the human says which.** Anything about
  live money and inbound correspondence — the paid-API revenue/conversion lane and the GitHub inbox — stays
  running through the day, because "I need to know what's going on" and "I wanna know who's talking, who's
  inboxing" are not questions that wait for evening. Ask once, record the exemption, and do not quietly move
  those jobs into a tidy window.

### End with ONE thing, or say there is nothing — never a ranked list and no conclusion

**A list of forty accurate items with no conclusion is homework.** The single highest-value line in the whole
report is the closing one: *if you only do one thing, do THIS — and here is why.* One item, one reason.

- **The reason must be a measured consequence**, not a priority adjective ("most important" is not a reason;
  "it is the only item blocking the next deploy" is).
- **If you cannot justify one, that is itself the finding** — say there is nothing worth doing today and
  stop. Manufacturing a top item to fill the slot is inventing urgency to look useful.
- **Rank across owners, not within them.** The reader wants the first move, not a per-seat leaderboard.

## When the human says "put it in my queue"

**Write it at the TOP of the queue file, never the bottom.** A long-lived queue runs to thousands of
lines; anything appended sits below the fold of every reader, including the brief that is supposed to
surface it.

- **Lead with the exact command or click**, copy-pasteable, plus a **done-test** — what the reader should
  see afterwards that proves it worked.
- **State what breaks if it waits, and what does NOT.** An item dressed as an emergency when it isn't
  teaches the reader to discount urgency, and the next real one gets skipped.
- **Say when the fix is already staged.** If the code is on disk but needs a process restart, name the
  file, its timestamp, and the single command — "patched but not live" is the state that gets forgotten,
  and naming it is the difference between a ten-second job and a lost one.
- **Do the verification yourself and keep the reminder on the human.** The queue exists so they remember
  to run the command; you get no reminder value from asking them to report back.
- **⚠️ Make the done-test include a CONTROL that must still pass.** A verification list of only "these
  should now be 404" cannot detect a fix that went too far — add the one live path that must keep
  working and say so in the row (`expect 404 · 404 · **402** ← control: if this stops challenging, the
  change went one step too far`). A check that cannot go red in either direction is decoration.
- **Never leave a date in a standing row's title.** "TODAY — <a date that has passed>" is read as *today*
  by every reader, including the one who wrote it, so the row silently stops meaning anything. Measured:
  a command row still headed with a date four days old sat at the top of the queue while the work it
  described had grown (a second, larger fix was staged behind the same restart). **Re-date the row or
  strip the date, and re-read its body in the same pass** — a stale heading almost always hides a stale
  body, and the body is what the human acts on.
- **A reminder for a human-blocked command must repeat until it is retired.** A one-shot reminder fires
  into a workday and is gone; schedule it to ask again daily, and **say in the message that it will** —
  then retire it explicitly once the human confirms the command ran. Better an acknowledged nag than a
  single reminder that vanished under a shift.

### A health-checker that WRITES the queue owns a BOUNDED section

**Standing instruction for this fleet:** a doctor/health job must **fix what it can on its own**, and route only
what needs the human into their list. A findings-only checker that names no owner is the shape this replaces.

When such a job writes the queue, give it one marker heading and rewrite that span:

```
## 🩺 ENGINE & HOST — health items (auto, rewritten each run)
_Last run <stamp> — replaced, not appended._
```

- **Rewrite, never append.** At 4 runs/day a 3-item queue becomes a 12-item one by lunchtime, and every copy
  carries fresh unchecked boxes that read as OPEN TASKS.
- **Implementation:** partition the file on the marker, find the next `\n## ` after it, replace exactly that
  span; write via temp file + `os.replace` so a crash cannot truncate the queue. Every other section must stay
  byte-identical.
- **Prove idempotency, do not assume it:** run twice, assert the marker count stays **1**, and `diff` the set of
  other `## ` headings — the only difference should be the new section appearing.
- **Route only what no agent may do:** a command needing a stopped service, an interactive wizard, a legal or
  account action. Anything fixable gets fixed silently; anything fixable-and-routed is a wasted row.
- **Report what was FIXED this run in the same section**, above the open items. Without it the human cannot tell
  progress from stagnation, and a section that only ever lists debt stops being read.
- **Do not let the fixer claim a fix it did not perform.** Measured: a self-fix pass wrote its own pointer note
  *inside* the directory it had just emptied, so the next run "moved 1 file" and reported a repair that did not
  happen. Put the pointer outside the swept path, and make the pass silent when there is nothing to move.

## Read fresh every run
**The shared brain is the source of truth — never the job's own memory.** Re-read the lanes at fire time.
If a report can be produced without reading anything, it is a hallucination with a schedule.

## Pitfalls
- **Reporting per-job instead of per-fleet.** N jobs each messaging the human = N pings and a reader who
  stops reading. One voice.
- **Inventing urgency to look useful.** A quiet day is reported by saying NOTHING — the job working
  correctly produces no message at all.
- **A legend or "how to read this" line printed on every run.** Measured: a bundled report printed its
  `[note]` explanation of the section tags *outside* the collected blocks, so a run with zero findings still
  delivered a paragraph six times a day. Guard the whole emit path — if no section produced output, `exit 0`
  **before** any prose — and verify with a clean run that the byte count is 0. Diagnostics belong in the log;
  silence belongs on the wire.
- **Reporting transport instead of state.** "A sent B a note" is not news.
- **Claiming an action that did not happen.** If the messaging/wake channel is down, file the note in the
  durable lane and SAY YOU FILED IT. Never report a wake, a DM or a message that did not land — verify the
  channel before describing it as a delivery path.
- **An ORIGIN record is not a DESTINATION.** A delivery-origin payload (platform, chat id, chat type, user id,
  profile, message ids) states where a message CAME FROM. It holds no bot chat, no reply-to address and no
  route. Record it as data, leave `deliver` exactly as configured, and keep any reference to it in the job's
  instructions rather than re-keying the job's routing fields. When something asks for a reply destination the
  payload cannot supply, **name the measured gap** — never synthesise one from the fields that happen to be
  present. A guessed destination is worse than a missing one: correctly-formatted text lands in the wrong room
  and nothing errors.
- **Reading a stale generated summary as current state.** Check the summary's age, and that the job which
  regenerates it still exists, before trusting it.
- **Length creep.** The caps are per-mode. A briefing nobody finishes is not a briefing.
- **Writing the report BACK INTO a list the job itself reads.** A reporting job that appends its own
  briefs into the human's queue turns that queue into a diary: the file grows without bound (measured
  at several times its useful size) and, worse, each write-back carries fresh unchecked boxes — so
  every log entry reads as an OPEN TASK to the next reader, and to the brief itself. Keep reports in
  the report lane and the queue in the queue; never let the consumer be a producer of the thing it
  parses.
- **Counting from the tool's narration instead of from state.** Two measured failures in one script: a
  multi-file `ls -la … | awk '{printf "%.0f", $5/1048576}'` **concatenated every size into one string**
  ("2548649 MB") because `printf` without a newline joins rows — print one line per file (`stat -c %s`), then
  `sort -rn | head -1`. And `mv -n … -print | wc -l` **under-reported** (9 files moved, "2") because `-n`
  silently skips existing targets — count `before_n − after_n` instead. **A number in a report comes from the
  state after the operation, never from the tool's account of what it intended.**
- **Asserting "identical / unchanged / duplicate" from matching file sizes.** Sizes repeat; content
  does not. Hash before claiming sameness (`md5sum`/`sha256sum`), and if you only compared sizes, say
  "same size". The same rule covers every staleness claim: cite the measurement, or downgrade the
  claim to exactly what you measured.
- **Parsing an overnight artifact without checking its age.** A verdict file that still reads PASS may
  be last week's. Check the producing file's mtime against the job's period — an unchanged verdict
  means the job did not run, and that is its own finding, not a healthy night.
- **Re-parsing a collector's artifact by hand because its `--json` flag is inert.** If the structured
  output you need does not appear, the flag is the bug — fix the collector to emit the payload (the
  full rows, not just counts, since counts were never what the caller lacked) instead of rebuilding its
  parser inside the report. A reporter that hand-parses races the collector's own parsing and drifts from
  it; the next schema change breaks one and not the other. **A flag is implemented when its output
  exists, not when it parses.**
- **Leaving the night's silenced failures ownerless.** When overnight jobs are quiet, the wake job is
  their only voice: it must name the seat that owns each failure, not just paste the error.

## Reference
- `references/collector-consumer-pattern.md` — the wiring: silent collectors, consumer chaining, delivery
  targets, and the silent-when-clean convention for scheduled jobs.
- `references/quiet-hours-and-overnight-state.md` — the window (23:00–06:30 ET = 03:00–10:30 UTC), the
  three-part silence rule (`deliver=local` is not enough — set `failure_deliver` too), the state-file
  handoff to the wake job, freshness-checking those files, and hand-editing `cron/jobs.json` safely.
- `scripts/quiet-window-check.py` — expands every enabled job's cron expression across all profiles and
  asserts zero human-facing deliveries inside the window (also flags local jobs that can still speak
  through an unset `failure_deliver`). Run it after any cron change.
