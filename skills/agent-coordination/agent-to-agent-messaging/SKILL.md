---
name: agent-to-agent-messaging
description: "Use when one agent must reach another agent — pick the path, prove it landed, and never report a wake that never happened. Covers peer DM, peer run, the vault handoff, and the local twin."
category: agent-coordination
version: 1.5.0
author: Gentech
tags: [communication, agents, peer, handoff, mesh, fleet]
related_skills:
  - group-handoff-mesh
  - handoff-mesh
  - fleet-consult
---

# Reaching another agent

**One rule above all: the vault is the RECORD, a message channel is only a WAKE — and a wake that
never landed must never be reported as a wake.** A DM that failed silently is worse than no DM,
because the sender believes the work moved.

## The four paths

| path | what it is | use it for |
|---|---|---|
| `hermes peer dm <peer>[/<seat>] "<msg>"` | cross-machine delivery into the target's canonical chat; **blocks** for the reply | a quick answer, a checkpoint before a restart |
| `hermes peer run <peer> --idempotency-key <key>` | fire-and-forget; returns `run_<id>` immediately, stable key makes a retry a no-op | long work you must not block on |
| `01-HANDOFFS/<from>-to-<to>/<YYYY-MM-DD>.md` | durable, survives a machine being off, read by the digest/scanner | **everything that matters** |
| `hermes -p <profile> chat --query-file <f> --oneshot` | the **local twin** — runs a real turn as that seat on this box | the peer path is dark |

## Step −1 — establish WHICH "DM" is meant before diagnosing anything

**Two unrelated mechanisms carry the name, and answering the wrong one wastes a whole turn.**

| what the human may mean | mechanism | what breaks it |
|---|---|---|
| **agent-to-agent peer DM** | `hermes peer dm fleet/<seat>` → the multiplex gateway → a turn in that seat (`platform=local user=api-peer`) | no registered peer, no key, no listener |
| **a Telegram message into another bot's room** | the platform, not us | **a bot can only see groups it was added to — bots cannot DM or read across rooms at all** |

**Measure the room membership per bot instead of inferring it** (read-only, one call each):

```bash
curl -s "https://api.telegram.org/bot$TOKEN/getChat?chat_id=<group>"   # ok:true = member, "chat not found" = not
```

Measured: each seat's bot was a member of exactly one group and returned `chat not found` for every other, so
"HQ's bot never appears in EDU" was not a messaging defect — the bot was never added there. **When the human says "the
groups should be able to DM each other", they usually mean the first row: separate rooms, agent-to-agent reach,**
and it is already the better design (one wake per address, no cross-talk, no token storm). **Say which mechanism you
measured before proposing a fix**, or you will spend the turn debugging rooms that were never supposed to talk.

## Step 0 — MEASURE the path before you rely on it

A peer DM fails in two very different ways and they look nothing alike: the peer *refusing* (you get
a reply) and **nothing listening at all** (an instant `[Errno 111] Connection refused`). Only the
first is information.

```bash
ss -ltnp | grep -E ':(864[0-9])'          # any listener at all?
hermes peer list                            # what URL + port are registered?
```

**Nothing listening is NOT the peer refusing, and it is NOT "the agent is busy".** Do not retry, do
not read silence as consent, and do not let a restart depend on an ACK that could never have arrived.

Measured state, re-measure it rather than trusting this line: after the multiplex convergence (one
gateway process serves every profile) the four per-profile api_servers are **gone** — `:8642`–`:8645`
refuse instantly — because a secondary profile never gets its own `api_server`; the default's adapter
is what serves `/p/<profile>/` **mirrors**. Repair = one bind on the default profile + per-seat peer
URLs + **per-seat keys**, and it is **gateway-affecting: checkpoint ACKs from every VPS seat first**.
Never take it alone.

## Step 1 — write the durable copy FIRST, then wake

Vault note first (the source of truth), wake second. If the wake dies, the record survives; if the
machine was off, the note is still there in the morning.

## Step 2 — wake, and read the RESULT, not the return code

- `peer dm` prints the peer's reply. An instant connection error = **failed wake**.
- `peer run` returns an id that must be polled to completion; "started" is not "delivered".
- The local twin prints the seat's turn. **It can be interrupted mid-turn** — if it stops partway,
  whatever it had already written to disk is real and anything it had not finished is not. Say so.

### Compose the message in a FILE — never inline a multi-line body

A multi-line message passed straight into a shell command is where a wake dies before it is sent: any
`(`, `)`, backtick or `$` in the prose is parsed by `bash`, the command never runs, and what comes back is a
**syntax error** rather than anything about the peer.

```bash
# body → file first, then let the shell read it
cat > /tmp/msg.txt <<'EOF'
...the message, punctuation and all...
EOF
hermes peer dm fleet/<seat> "$(cat /tmp/msg.txt)"
```

- **Quote it as `"$(cat …)"`, not `$(cat …)`** — unquoted collapses the newlines into one run-on line.
- **Use a quoted heredoc delimiter (`<<'EOF'`)** so `$` and backticks in the prose survive literally.
- **This applies when the body is built in Python and passed to `terminal()`.** Write it to a file first
  and pass `"$(cat /tmp/msg.txt)"`; building the string in Python and interpolating it into the shell
  command reproduces exactly the failure above, and the error names bash, not the peer.
- The same applies to `--query-file` for the local twin: write the file, pass the path.

**A syntax error tells you nothing about the peer — verify the command PARSES before reading silence as a
failed wake.**

### An interrupted send is UNKNOWN, not failed — check before re-sending

If the tool call carrying a DM is interrupted (timeout, orphan recovery), the message **may already have
landed**. Re-sending blind double-wakes the seat and manufactures two turns of work on one request:

1. read the far seat's own log for an `api_<id>` session around the send time (Step 3);
2. re-send only when that check shows nothing.

Report it as unknown rather than picking whichever answer is convenient.

### A timeout is the SENDER failing, not the message being lost — queue it, keyed by content

`peer dm` blocks until the far seat finishes a whole agent turn, so a timeout says **nothing** about delivery.
Measured on one probe run: one seat replied in 26s, a second in 13.7s, a third exceeded 45s — and the third was
plainly alive (its own log showed a turn in progress). **A busy seat does not refuse the message; it makes the
sender wait for it.** Treating that wait as "never sent" produces the duplicate: a retry that delivers a second
copy of a request that already landed.

**So make retry safe by construction — spool the send, don't repeat it:**

1. **Send with a bounded wait.** On success, done — nothing is queued.
2. **On timeout, write the message to a durable spool file** (`state/dm-spool.jsonl`) instead of retrying inline,
   and print `QUEUED attempt 1` — a visible state, not silence.
3. **Key every spool entry by a hash of its CONTENT**, and flush under that key. A flush that has already
   delivered cannot deliver again, so the spool is safe to run on a schedule and safe to run twice.
4. **Flush from a cron** (every ~20 min) rather than from the blocked turn — the queue drains without a session
   holding it open.
5. **After N attempts mark the entry `STUCK` and LEAVE IT ON DISK.** A message nobody could deliver is
   information; deleting it turns an outage into a gap nobody can audit.
6. **Prove it on the failing path before trusting it:** force a 1-second timeout, confirm the entry is QUEUED,
   run the flush, confirm delivered and the spool empty. A queue you have only ever seen stay empty is not a
   queue.

**The diagnostic order that prevents the duplicate:** before re-sending anything, read the far seat's own log
for a turn around the send time (Step 3). "Timed out" and "did not arrive" are different findings and only one
of them justifies sending again.

## Step 3 — PROVE the message landed in the target's own artefacts

Not by assuming the channel worked. Look for: a reply note in your lane, a file the target touched,
a session/transcript entry. **If nothing shows, the honest statement is "the wake failed"** — never
"they have been notified".

**⚠️ A printed reply is not proof of delivery.** `peer dm` echoes whatever came back, and an echo, a
stale cached turn, or your own text returned by a proxy all look identical to a real answer. The
receipt is the **far seat's own log**:

```bash
tail -c 4000 /opt/data/profiles/<seat>/logs/agent.log | grep -E 'api_|Turn ended'
```

A new `api_<id>` session entry with `Turn ended: reason=text_response` timestamped around your send
**is** the delivery — it proves the far agent opened a turn and finished one. Its absence is a failed
wake no matter what the command printed, and on a shared filesystem that log is readable without
touching the peer.

**⚠️ `sessions` is NOT the receipt — delivery reuses the far seat's EXISTING session, so a landed DM adds no
new session row.** This skill says that three sections above, and the operational consequence is easy to miss:
query the session table, find nothing new, and every delivered message reports as undelivered. The row a real
turn leaves is in the **`messages`** table — scan it by content and recency:

```bash
sqlite3 "file:/opt/data/profiles/<seat>/state.db?mode=ro" \
  "select id, substr(session_id,1,24), role, substr(content,1,120) from messages order by id desc limit 10"
```

- An inbound `user` row carrying your prose, or a `tool` row whose text contains the far seat's work on your
  request, is the receipt — and it will sit inside a session that may be weeks old.
- **A timeout plus work done downstream is a SENDER-side reporting error, not a delivery failure.** Measured:
  two sends returned nothing at all, the session check found no new session and the wake was reported as
  probably-failed — while the recipient had read it, done the work and filed a return handoff, exactly as the
  `messages` row would have shown. **So the order is: send → on timeout scan `messages` → also check the
  recipient's RETURN lane (`01-HANDOFFS/<seat>-to-<you>/`) → only then consider a re-send.** Reading the
  return lane before re-sending is what catches this class, because the proof of delivery is often the work
  that came back rather than anything the sender saw.
- Report it as *"delivered — proved by the far seat's message log and its reply; the DM itself returned no
  output"*. Never "not delivered", and never a second send.

Two cheaper corroborations, useful when the log is rotated away: the seat's `state.db`
`session_model_usage` shows a model call at that minute, and a fleet-wide sweep of that table shows
which seats have gone quiet for longer than their normal cadence.

## A wake is NOT a refresh — and a DM cannot fix a stale brain

**A delivered peer DM is a turn inside the recipient's EXISTING session. It does not open a new one.**
Measured: a probe DM to another seat returned a reply, and the far seat's own `state.db` gained no new session
row — the turn landed in a session opened **~2.5 weeks earlier**, and the seat said so itself when asked
(the newest id in its store was still the old one, with only `message_count` moving).

Why that matters more than it sounds: Hermes injects `MEMORY.md` / `USER.md` into the system prompt as a
**frozen snapshot at session start**. So a seat can be woken, answer you promptly, and still be reasoning from
memory that is weeks old.

- **Waking and refreshing are two different problems.** A wake = a message arrives. A refresh = a new
  session (**`/new`**, a human action inside that seat's own chat). **Never report a DM as having refreshed a
  seat.** But there is a **third option between them**: `hermes sessions refresh-prompts -p <seat> --session <sid>`
  rebuilds that session's stored system prompt from current sources **on its next turn** — history and session id
  kept, one prompt-cache miss. **That clears the stale-memory blindness WITHOUT a new session.** It is
  **asynchronous**: the request is accepted now and applied later, so report *"refresh requested — applies on its
  next turn (not yet observed)"*, and treat the **changed `sessions.system_prompt_hash`** in that seat's
  `state.db` as the only proof it landed. A seat that never takes a turn keeps the request queued forever — a
  silent seat is a different fault from a stale one.
- **Report them as two verdicts** — "woke: yes (reply + far-seat log entry) · refreshed: no (same session, N days
  old), refresh requested" — one line, and it stops the most common false comfort in the fleet.
- **A silent lane is a third, separate signal.** "No vault write in N days" says the seat is not *reading*; it
  does not say the wake failed, and a wake does not fix it. Say which of the three you measured.

### Measure a seat's session age yourself, instead of asking it

Two reads on the shared filesystem, no message needed:

```python
# 1 · the routing index tells you WHICH session the seat is on right now
#     session_key form: agent:<seat>:<platform>:<chat_type>:<chat_id>:<user_id>
#     gateway_routing(scope, session_key, entry_json, updated_at)  → json.loads(entry_json)['session_id']
# 2 · the sessions table tells you WHEN that session started and last moved
#     sessions(id, source, started_at, last_activity_at, message_count)  ← started_at is the freeze time
```

Compare `started_at` against `memories/MEMORY.md`'s mtime: **the gap is how much the seat has written that it
cannot see.** That number is the finding — not the fact that it answered.

## Step 4 — record it, including the failure

In the return note: what was sent, by which path, whether it landed, and the error **verbatim** when
it did not. The next reader must be able to tell a delivered message from an attempted one.

## Step 5 — ANNOUNCE the exchange to the human (Jordan, 2026-10-17)

Jordan's rule, verbatim: *"a better idea would be for agents to just say something and let me know that
they received a DM and what they responded with. I think that will work out better when you guys are
communicating. So that way I can see that you guys got the message and you respond or say something and
you let me know what you're doing in response."*

**WHY the watcher was the wrong shape:** the vault handoff is **SILENT**. A file write notifies nobody,
so the human sees only the residue of an exchange, never the exchange. A watcher was built to bridge
that gap and it is now dead — and the gap is better closed by the agents themselves.

**The rule: when you receive a DM from another agent, say so in the group — what you received and what
you answered.** Both halves, in the channel Jordan reads. That makes every agent-to-agent exchange
auditable by him without opening a file.

**Shape it, or it becomes the noise the watcher was:**

- **One short line per exchange** — received / answered / what happens next.
- **Only when a DM was actually received.** A routine vault file-drop needs no announcement; the file is
  already the record. Announcing those would reproduce the noise.
- **A receipt with no answer yet is still worth one line** ("received X, working on it"). The receipt is
  the thing he is asking to see — silence about it is the blind spot this rule exists to close.
- **The sender announces its side too** when the reply comes back, so the pair of lines tells the story.

**Precondition, now MET — re-measure rather than trust either state.** The rail came back: `hermes peer
list` reports one registered peer, **`fleet`**, at `http://127.0.0.1:8642` with a key set, and
`hermes peer dm fleet/<seat> "…"` returns the far seat's reply. **The working form is the peer name plus
the seat as a suffix (`fleet/arthur`); a bare seat name (`peer dm arthur`) resolves nothing**, because
`fleet` is the single registered peer and the seat is its routing suffix. `/health` on `:8642` answers
`200`. An earlier revision of this section declared the rail dark and told the reader not to announce —
that was true when measured and is false now. **Re-run Step 0 before repeating either claim.**

## When a path is DOWN — the fleet fallback (adopted 2026-09-30)

A single channel must never be the failure point. **The vault handoff is the delivery; the DM is only
the accelerator.** When Step 0 shows the wake path is dark, the sender still:

1. **files the vault handoff** — the record is written regardless of whether a channel exists;
2. **states in the record that the wake FAILED** — the error verbatim, never "they were notified";
3. **does NOT wait** — no blocking on a channel that cannot answer.

**A restart never *gates* on a channel that cannot answer — but a dark channel is NOT consent.** The
gate is failed *to the seat that owns it* (Jordan), never read as an ACK. **Gating ≠ proceeding.** An
ACK that could not have arrived must not be waited for **and must not be assumed** — those are two
different mistakes and both are forbidden.

> Boundary this rule must NOT be allowed to mean: *"dark channel ⇒ proceed."* It never does. A
> measured-dark path escalates; it does not authorise.

**A DOORBELL IS NOT A LANE — and Hermes already ships a better doorbell than ours.** Telegram does
not carry bot-to-bot traffic, which is why the wake had to be built at all. Hermes's group routing
(`exclusive_bot_mentions`, `bots_require_mention` — see `telegram-group-routing`) is built for that
traffic, but it only works where two bots can SEE the same room. Measured: no fleet seat shares a
room with another, so there is nothing to route and nothing to gain. Two corollaries:

- **Do not borrow the routing knobs to replace the peer DM.** A mention has no receipt, no run id and
  no delivery proof — the peer DM still exits with a status and prints a reply.
- **`peer run` + `peer status` close the last gap in our own wake.** `peer run --idempotency-key`
  returns `run_<id>` without blocking, and `peer status <peer> <run_id>` reads the outcome later. That
  is the honest "long-polled and it landed" shape — prefer it over a blocking `peer dm` on any turn
  that can hang, and over a fire-and-forget send that was never checked.

## A checker that PRINTS a nudge has not sent one — wire the escalation to the queue

**"Nudge by DM when this list is non-empty" in a report's footer is a to-do for a human, not a duty the fleet
performs.** The list looks actioned because it is loud; nothing was sent. Measured: an SLA checker printed red
`ESCALATE` rows for weeks while silently nudging nobody.

**So make the checker's escalation band call the retry-safe sender directly** (`peer-dm.py` in this fleet: bounded
wait → spool keyed by content hash → cron flush every ~20 min → `STUCK` after N attempts stays on disk). Then an
overdue note becomes a queued message instead of a line in a report, and the report states the path it took:

```
📬 NUDGED — 0 sent · 1 queued for retry
```

**"0 sent · 1 queued" is the honest success shape.** A checker that can only report `sent` is either lying or has
never met a busy seat.

**Exclude seats by CAPABILITY, computed in code — never by importance, and never by hand-maintained list:**

- **a seat with no registered peer** — an ACK is *structurally impossible*, so nudging asks for something that
  cannot arrive. Excluding it is not leniency; it is the difference between measuring silence and measuring a
  missing doorbell.
- **the sending seat itself** — a seat does not DM itself about its own notes.

**And when a checker measures a structural silence, suspend the clock IN THE ARTIFACT.** Append a short block to
the note itself saying the ACK cannot arrive, why, and who owns the follow-up — otherwise the next run, and the
next reader, see the same red row and re-derive the same false accusation.

**Give every checker a `--no-nudge` flag, defaulting to send.** A checker that messages the fleet on every
invocation cannot be run by hand while debugging, so it gets run less, and the one time it matters it is stale.
**Dry-run with it first, then run the real path once** — and if the send path was never exercised, you have
shipped a `sent` claim with no evidence behind it.

## Acknowledgement is a SEPARATE duty from delivery — and it is measurable

Delivery is "did the message land". Acknowledgement is "did the receiving seat read it and say what it
did about it". A fleet can be good at the first and near-zero on the second, and the two failures look
nothing alike: **silence, not dishonesty.**

Measured in one pass: **12 recent inbound handoffs across five seats, 0 carrying an `## Agreement` block**,
while **0 were "acknowledged without evidence"**. So nobody was faking agreement — nobody was answering at
all. Report those two numbers separately or the conclusion is wrong in both directions.

**The duty has TWO beats, and the first one is the one the fleet skips:**

1. **`## Receipt` on OPEN** — a one-row block in the handoff itself, giving the seat, the timestamp, what
   you are doing about it, and a **`by` date**. This is a read receipt *with a promise*, and it is not an
   agreement: it never closes the note, and the checker strips it before asking "is this answered?" so
   the word `received` cannot satisfy the agreement matcher.
   - **A Receipt DOES close a DIRECTIVE — but only when it states an OUTCOME.** A restart checkpoint is an
     order (*finish, log, verify, then ACK*); it has nothing to agree TO, and its closure lane is the receipt
     the receiving seat writes back (`READY` / `NOT READY — mid-<task>` / `NO ACTION NEEDED`). A briefing that
     only ASKS for agreement cannot escape on a stray receipt. So teach the checker the difference rather than
     treating every receipt alike: recognise it as a closure only when the note states a required action
     (an imperative at line start — must / finish / write / run / reply / ACK / hold) **and** the receipt
     names an outcome. Otherwise it stays a promise.
   - **Test both directions before shipping the rule**, or one of them silently inverts: `ORDER + Receipt`
     → closed · `BRIEFING + bare Receipt` → still counted · `BRIEFING + Agreement` → closed. A checker that
     accepts a receipt from anyone stops asking its question; one that refuses it from an order reports a
     five-day-old completed checkpoint as new debt, and a false accusation trains the reader to skip the report.
2. **`## Agreement` on COMPLETION** — the block below, unchanged.

**Why the receipt exists:** with only one artifact, *"read and working"* and *"nobody opened it"* both
report as "silent", which is the single most common false impression in the fleet. Measured on the day
this was added: 17 `## Agreement` blocks existed and exactly **1** `## Receipt`. The checker therefore now
reports three states — **unread** (nobody opened it), **promised and missed** (`by` date passed, no
answer), **answered** — and the middle one is the state a human colleague never needs asked about twice.

**The duty:** every handoff ends with an `## Agreement` table — one row per seat that must agree — and a
seat that reads it writes `acknowledged` **plus an evidence line naming what it did about it**. A read
receipt is not agreement; a status word with no evidence is reported as *unproven*, which is worse than
`pending` because it hides the work.

- **Clear your own INBOX before diagnosing anyone else's.** In the pass above, four notes had sat in the
  *asking* seat's own inbox for up to eight days — the loudest complainer was the worst offender. Measure
  per-seat counts first; the finding is usually not where the question was aimed.
- **Cheap measurement, no messaging needed** (shared filesystem):
  `for seat in INBOX/*/; do n=$(find "$seat" -name '*.md' -mtime -14 | wc -l); a=$(grep -l '^## Agreement' "$seat"/*.md 2>/dev/null | wc -l); echo "$seat $n new / $a acked"; done`
- **Acknowledge at the SOURCE, not in chat.** The block goes in the note, so the next reader and the
  sign-off scanner both see it. Announcing the ACK in group chat alone leaves the artifact silent — the
  same defect the announcement rule was written to fix, one layer down.
- **Answering slowly is still answering.** Age the pending rows (2-day floor) and report worst-first;
  never let a stale row read as agreement by falling out of the window.
- **A format has a START DATE — count from it, or the backlog is permanent.** When `## Agreement`
  becomes mandatory, every note written before that date lacks one, so a flat "uncovered notes" counter is
  overwhelmingly **migration debt, not silence** — and reporting it nightly as pending trains the reader
  to skip the number. Cut the counter at the convention date and report the older set once, as legacy.
- **Never backfill acknowledgements to clear the count.** Writing `acknowledged` rows onto notes that
  were answered before anyone asked for a block is a **forged receipt** — the exact object the block
  exists to prevent, and worse than an honest gap because it is indistinguishable from real agreement.

### When the checker and reality disagree, suspect the CHECKER's resolution step

A fleet can look like it is ignoring everything while the work was done and answered. Measured: a
checker reported **10 handoffs unacknowledged**, and four of them had been picked up and answered — two
of those answered *by us*, in a lane the checker never searched. The defect was entirely in how the
acknowledgement was **located**.

- **ACK IN PLACE — write the `## Agreement` block into the HANDOFF FILE ITSELF**, not only into a
  return-lane note. It is the only acknowledgement location with **no resolution step**: no lane
  naming, no alias table, no date window, no "which of our many directories counts as the reply".
- **Derive the reply lane from the TARGET, and handle the self-pair.** The reply to a note from A to B
  is written by B in `B-to-A`. When a note is addressed to you *by someone else*, the reply lands in
  **their** lane (`them-to-you`), so a lookup that only tries `you-to-you` finds nothing. Any resolver
  that collapses two names into one must be tested with a note from a *third* party.
- **Separate "misaddressed" from "unacknowledged".** A target that is a folder, an alias or a retired
  seat cannot answer, so reporting it as someone's silence puts a human on the wrong task. Give it its
  own bucket and its own line: re-route or close it, do not chase it.
- **A note can carry MORE THAN ONE `## Agreement` block, and the second one is the ACK.** Append-only is
  the contract, so a seat that later accepts must not edit the original table — it appends its own block
  below. **A parser that reads only the FIRST block makes every appended ACK invisible**, and the row it
  completes keeps counting as pending. Scan all blocks; a later block overrides an earlier one per seat.
- **Markdown puts the colon BEFORE the closing asterisks.** `**Seat:** X` does not match `seat\**\s*:`,
  which expects the asterisks first and silently finds nothing, so a "fixed" matcher still reports the
  ack missing. Match `seat\s*\**\s*:` and test the pattern against real bytes before declaring it fixed.
- **A flag that accepts input and produces nothing is worse than no flag.** A `--json PATH` that is
  declared, documented and never written looks implemented, so nobody checks it. **Exercise every
  documented flag once and assert its output exists**, and put the FULL rows (path, seat, age, evidence)
  in it — counts were never what the caller needed.
- **Re-run your own false positive as the control after the fix.** The sample you just explained is the
  only proof the change moved the number for the right reason — and expect more than one pass: a
  broadening that fixes one shape can break another.
- **A BROADCAST lane is invisible to a per-seat checker — so its agreements are never chased.** A checker that
  enumerates `INBOX/<target>/` (one folder per seat) sees nothing in `01-HANDOFFS/<from>-to-fleet/` or any other
  fan-out lane, so a note asking three seats to agree produces answers that no report will ever count. Two rules
  follow: **when the ask matters, also drop a copy in each `INBOX/<seat>/`** (or write the per-seat notes), because
  only that lane is measured; and **widen the checker to the fan-out lanes** rather than assuming a broadcast is
  read just because it is loud. Verify by planting one note in the broadcast lane and confirming whether the run
  counts it.
- **Ask several seats at once with a shape that makes a REFUSAL easy.** When handing out ownership, ask *"is any
  of this yours, and will you keep it tidy? yes / no is a valid answer"* — a seat that owns none of it otherwise
  answers politely and vaguely, and politeness is indistinguishable from a claim. The seats that decline give the
  most useful replies in the exchange, usually with a correction to your premise inside them (they are reading the
  same filesystem, so their counts are a second instrument — check theirs before defending yours).

## Delivery is not DUTY — check whether any job ever ASKS the seat

**Before diagnosing "that seat never answers", establish that anything ever asks it.** A handoff is a
**silent file write**: it notifies nobody. So a seat can be perfectly healthy, answer a DM in seconds,
and still ignore every handoff for weeks — because no scheduled job on that seat reads its inbox.

**Measure it in one pass per seat** (the shared filesystem means no messaging needed):

```python
import json, glob, re
# ⚠️ WORD BOUNDARIES, not substrings. A bare `"ack" in name` reports `data-backup-nightly` as a mail
# reader, because "ack" sits inside "backup" — a probe that miscounts trains you to fix the wrong seat.
PAT = re.compile(r"\b(inbox|handoff|handoffs|ack|acknowledg\w*)\b", re.I)
for prof in sorted(glob.glob("/opt/data/profiles/*/cron/jobs.json")):
    seat = prof.split("/")[4]      # ⚠️ index 4 = <seat>; index 3 is the literal "profiles"
    j = json.load(open(prof))["jobs"]
    on = [x for x in j if x.get("enabled", True)]
    readers = [x.get("name") for x in on
               if PAT.search((x.get("name") or "") + " " + (x.get("prompt") or "")[:4000])]
    print(f"{seat}: {len(j)} jobs, {len(on)} enabled, {len(readers)} inbox readers")
```

**Print the seat names and sanity-check one against a seat you know exists** before believing the counts:
both mistakes above produce a plausible-looking table, and the wrong table is the one that gets reported.

**The three shapes this exposes, and they need different fixes:**

- **Busy and deaf** — many jobs, none that read mail. Looks healthy on every dashboard; the "backlog"
  attributed to it is an unwired seat, not lateness. Fix: add the reader.
- **No jobs at all** — zero cron entries. There is **no working schedule pattern to copy**, so a new
  job must be tested rather than assumed to fire. Say so instead of shipping it as working.
- **Only one seat wired** — the common real answer. The fleet's acknowledgement rate then describes HQ's
  own cron, not the fleet's discipline, and every pending row will be on the unwired seats.

**The counter-test is the proof, and it is cheap:** send the seat one real request and time the answer.
A fast, substantive reply settles it — **the channel is fine, the trigger is missing.** Report that
distinction explicitly, because "3.8 days behind" and "nothing has ever asked it" sound identical in a
summary and mean opposite things about who should act.

- **Report who was ASKED, not who is late.** An aged row is a statement about silence, not about
  capacity. Where the cause is a missing reader, name that.
- **Never let a reporter or a PA write another seat's acknowledgement.** An ACK must come from the agent
  that owns the row, or it is a **forged receipt**. A reporter may only *list* what is missing.
- **A backlog AGE is not an outage.** Before repeating "N days broken", test the present: a note can
  describe a state that has since been fixed. One request against the live surface settles it — and if
  the answer contradicts the row, correct the row and say you had repeated it.
- **A protocol nobody is awake for is not a protocol.** Writing the duty down a third time changes
  nothing; the seat needs a scheduled job that opens its inbox. Fix the trigger first, then the format.

## A peer-less seat's delivery IS the vault sync — a broken sync looks exactly like negligence

**This skill's four paths all assume the vault replicates. For a seat with no registered peer, the vault
IS the only path — so if sync is broken, that seat receives nothing and every report will blame the seat.**

Measured: an SLA checker escalated a peer-less desktop seat as `SILENT` and `OVERDUE` — six notes, up to six
days, no `## Receipt` on any of them. The seat had not gone quiet; **its inbox had stopped arriving.** Its own
last written note was **nine days earlier** and explained the cause from inside: it was reading a *stale clone*
of the vault and could not see files that existed in the live tree. Meanwhile the sync log on our side read
`Connection successful` on every run while every upload died:

```
Connection successful. Detecting changes...
Uploading file <note>.md
Sync error: Error: Vault limit exceeded.
Disconnected from server
```

- **`Connection successful` is not a delivery proof.** A bidirectional sync connects, *detects*, then fails the
  write. Check that an upload **completed**, or that the far side can see a file you just wrote — never that the
  socket opened.
- **Resolve the ACTIVE sync state directory by mtime — never hardcode a vault id.** Re-creating a vault mints a new
  id and a new `sync/<vaultId>/` directory; the old one stays on disk, frozen, and every tool pointed at it keeps
  reading a dead log forever. Measured: a checker hardcoded the retired vault's path and reported "transport down
  six days" while a probe file uploaded in the same minute. Pick `max(glob(sync/*/sync.log), key=mtime)`, print the
  resolved id and the log's age, and return `UNKNOWN` (not healthy) when the freshest log is itself stale. Same rule
  for any state file keyed by an id the system can regenerate.
- **The sync client lives in the container, not the host shell.** Run it as
  `docker exec -it <container> sh -lc 'XDG_CONFIG_HOME=/opt/data/home/.config <ob-path> sync --path <vault>'` —
  without `XDG_CONFIG_HOME` it answers "No sync configuration found" and exits 0, which reads as success.
- **A probe file is the only end-to-end proof, and it must not start with a dot.** Write a visible file, sync, then
  confirm `Upload complete <path>` in the live log; dot-prefixed paths are excluded by the client and produce
  "Fully synced" with no upload.
- **Deletes propagate even when uploads are refused.** The failure is asymmetric, so the far seat sees a brain
  that shrinks and never grows — the most confusing possible signal, and one that reads as "my colleagues
  stopped writing to me."
- **A seat whose only channel is the vault cannot be late.** Before reporting any peer-less seat as silent,
  overdue or unresponsive, **verify the transport delivers** (write a probe file, confirm it appears remotely).
  `SILENT` and `UNDELIVERABLE` are different findings with opposite owners, and the fix for the second is ours.
- **Say which one you measured.** "Six notes undelivered, transport down since <date>, seat not at fault" — a
  report that only prints `ESCALATE` sends a human to chase a colleague who never received the request.
- **TWO sync configs on the same vault path are a loaded gun — remove the retired one.** Re-creating a vault
  leaves the old `sync/<vaultId>/` directory on disk with the *same* `vaultPath`, and the client chooses between
  them by its own order rather than by freshness. Consumers then read a dead log while the live one looks fine;
  worse, if the active config is ever lost the client silently reconnects the retired vault and pushes current
  notes into a dead brain — with no error, because the old remote still exists. Procedure: confirm the active id
  from what the sync itself prints (`Vault: <name> (<id>)`), back the retired directory up **outside** the sync
  root (tar it, then list the archive to prove it is not empty), delete only that directory, write a visible
  probe file and confirm `Upload complete` in the surviving log, then re-run every resolver and assert it reports
  exactly one config.
- **A seat's own last note often names the cause.** Read the newest thing it wrote before asserting anything
  about its diligence; a seat reporting that it is reading a stale copy of the brain is a transport alarm
  wearing the clothes of a complaint.
- **Suspend the clock in the artifact.** When the SLA row is a transport fault, append a block to the note saying
  the ACK cannot arrive, why, and who owns the fix — otherwise the next run re-derives the same false accusation.
- **Your own outbound lane being current proves NOTHING about the far side.** Measured: one seat's inbound lane was
  written minutes earlier while four of its outbound lanes had not moved in 3–7 days. **Delivery to a vault-only
  seat is evidenced by notes IT authored, never by notes you uploaded** — check every return lane's newest mtime
  (`ls -t 01-HANDOFFS/<seat>-to-*/ | head -1`) side by side with yours, and report the gap in days. Uploading is a
  claim about your half of a bidirectional channel.
- **Two of those lanes going quiet at different times is the useful signal.** All four quiet since one date = the
  machine is off or its client is unbound. Quiet only on the reply lanes = it receives and does not write. Same
  symptom, opposite owners; measure the spread before asking a human to act.

### Better than annotating the artifact: make the suspension MEASURED, so it un-suspends itself

**A hand-written note saying "the ACK cannot arrive" is a permanent exemption.** It is correct on the day it is
written and silently wrong the day the transport recovers — the same failure family as a hardcoded seat list
that outlives its reason. Suspend the clock in **code, from a live probe**, and let it lift on its own.

- **Probe the CHANNEL, never the seat.** Derive the blocked set each run from one check of the delivery path
  (for a vault-only seat: does the **last** sync attempt end in an upload error, **inside a recency window**?),
  and compute the affected rows from that answer. The seat name never appears in the logic.
- **Print the gate AND the release condition on every blocked row.** *"🚧 BLOCKED (3) — undeliverable, NOT late"*
  followed by the measured failure and what would release it. A row that says only "blocked" is a shrug the next
  reader cannot act on.
- **Design it to fail back OPEN.** When the probe says the channel is healthy, those same rows must return to
  their normal bands **on their own next run** — no edit, no remembered suppression, no one to remind.
- **Prove all three cases before trusting it:** healthy → **no block** · the real failure → **block** · a failure
  older than the window → **no block**. The third is the one that stops an old outage being reported as current,
  and it is the one usually left untested.
- **Recency is not optional, because the log is append-only.** An unbounded scan keeps re-reporting a fixed
  problem forever; bound it by hours since the last failure and state the window in the output.
- **A reachable seat that ignores you is still reported as ignoring you.** The band suppresses only seats whose
  channel is measurably down — that is the entire value of the distinction, and collapsing it back into
  "everything peer-less is excused" destroys it.

### A third bucket: the destination has NO MAILBOX AT ALL

**Transport health and destination existence are different questions, and a checker that only asks the first
will bill you for mail to an empty house.** A seat can be reachable in the roster and still have nowhere for a
note to land — no profile directory on this host (so no cron, no gateway) and no registered peer. For that
seat the vault is not a degraded channel, it is the only one, and it needs a human to boot the machine.

Measured: five notes escalated at such a seat over five days while its own newest authored note was the same
age — it had not gone quiet, nobody could read what we sent.

```bash
ls -d /opt/data/profiles/<seat>      # no directory = no mailbox on this host
hermes peer list                    # only `fleet` = no peer channel for that seat
```

- **Keep it SEPARATE from the transport-band.** `BLOCKED` means *the channel is down and will come back*;
  a no-mailbox seat means *the channel does not exist*. One releases itself on the next healthy sync, the other
  releases when a human opens the machine or the lane is retired as a live correspondent. Collapsing them makes
  a permanent condition read as a temporary one.
- **Report it as `NO READER` with its gate and release condition, and stop counting it as debt** in the headline
  number. The count a human reads must be the count of things a seat can actually answer.
- **Declare the set by hand, but prove it can lift.** A literal set of seats is correct here because it is a fact
  about the host, not a judgment about diligence — but assert the release path: empty the set, re-run the
  checker, and confirm those rows return to `ESCALATE`. A park you have never seen lift is indistinguishable
  from a permanently suppressed row.
- **Re-derive it whenever a seat is provisioned or retired** — this set is exactly the kind of literal that goes
  stale the moment the fleet changes shape.

## Related rules that bite here

- **A peer's claim is a claim.** Verify what they report before relaying it (`verify-after-every-action`).
  Asking for something and receiving an answer is not the same as the answer being true.
- **A peer's report on work you originated is a continuation, not a new ask** (`group-handoff-mesh`).
- **`peer dm` blocks until the reply** — never put it on a path that can hang a session you need.
- **Never leave another seat's in-flight edits to rot**: if their turn was interrupted, their
  uncommitted files are theirs. Do not commit them for them; name the state instead.

## Bringing a dark rail UP — the measured recipe

**Symptom:** `hermes peer list` → *"No peers registered"*, and `hermes peer dm <seat>` →
`401 Invalid gateway API key (API_SERVER_KEY)`. **Do not conclude the rail is dead** — measure the
server before believing the client. A dark report may be a blind test, not a dead service.

1. **The api_server may already be up and correct.** `ss` is frequently absent inside a container, so an
 `ss`-based port check returns *empty* and reads as death. Use `/proc/net/tcp` (`state 0A` = LISTEN).
 Confirm two-sided: `GET /v1/models` → `401` unauthenticated, `200` with `Authorization: Bearer <key>`.
2. **Find the key the server actually uses** — `API_SERVER_KEY` in the home of the gateway that owns the port.
3. **The common root cause (measured):** that key exists only in **one** profile's `.env`. The multiplex
 gateway then cannot authenticate **routing to a named profile**, so `peer dm <peer>/<seat>` 401s while
 `peer dm <peer>` (default profile) succeeds. **Fix:** put `API_SERVER_KEY` + `API_SERVER_ENABLED=true`
 in **every live seat's** `.env` (mode 600). **No gateway restart is required** — the running gateway
 reads the key per request.
4. **Register the peer in each seat's OWN list** (`hermes -p <seat> peer add …`), or a seat can only be
 reached and never reach.
5. **Prove it end to end** — a *reply from the far seat*, not a `200`.

**Pitfalls, measured — each cost real time:**

- `hermes peer add` reports *"key stored as `HERMES_PEER_<NAME>_KEY` in `~/.hermes/.env`"* but writes it
to the **active profile's** `.env`. Never trust the message; grep the file.
- The header must be `Authorization: Bearer`. A correct key sent as `X-API-Key` returns `401` anyway.
- To see what `peer dm` actually sends, register a **probe peer pointed at a receiver you control** and
dump the request. Faster and more certain than reading the client's source.
- The peer's front door may be a **non-seat profile** (here the default profile owns the port). Routing to
a *named* seat is what you want; a bare peer DM answers as the default profile and proves nothing.

- **The two-key trap — and how it was closed (2026-10-19).** Every seat's `.env` carries **both**
`API_SERVER_KEY` and `HERMES_PEER_<PEER>_KEY`. They once held **different values** while only **one** was
accepted by the single live listener (the multiplexer), so a client configured with the other got a silent
`401`. Measured then on `/p/gentech/v1/models`: no key `401` · `API_SERVER_KEY` `401` · peer key `200`.
**Now aligned** across all four seats — either value authenticates, and the retired orphan value returns
`401`. When a DM "didn't arrive", check **which credential the sender used** before blaming transport.
- **Do not assume a send-key / receive-key split.** Secondary profiles **do not bind their own port**, so
there is no second listener to authenticate against. I published that split theory and it was wrong; the
peer agent's correction was right. Re-measure the listener, don't reason from the variable names.
- **`/health` is NOT an auth check.** It answers `200` with no key AND with a deliberately wrong key, so a
  green health probe proves nothing about credentials. On the **peer gateway** use `/v1/models` (`401` bare,
  `200` authenticated) — that split is measured for THIS listener and does not generalise: some model providers
  answer `/v1/models` `200` with any bearer string and only refuse at completion time. **A listing endpoint is a
  routing answer, not an auth answer; only a real completion proves a rail.**
- **A `401` reads as "sent."** The sender sees no error unless it checks the HTTP status, so the message never
lands and surfaces later as *"I sent it but they didn't acknowledge."* Check the status code, not the exit
code — `curl` exits `0` on a `401`.
- **`peer dm` can hang 60–90s and then succeed.** Retry once before concluding failure; prefer `--json`.

## Handing a live credential to a peer seat — the only safe shapes

**A re-point that moves the URL but not the key is a ONE-CHANGE-TWO-VALUES bug, and both sides are blind to it.**
The registry says the lane moved; the far seat's `/health` returns 200; every authenticated call 401s. **So when a
peer endpoint changes, the credential moves in the SAME change or the lane is dark but looks healthy.** The receiving
seat cannot detect this alone — its only local signal is the 401, and a liveness check never produces one.

When the key must physically travel to another host:

1. **Write it to a path that git cannot ever see, and add the ignore rule BEFORE the file exists.**
   `00-System/peer-keys/*.key`, mode 600, with `00-System/peer-keys/*.key` in `.gitignore` created first. Verify
   with `git status --short --ignored` showing `!!` for the key and `??` for the README — a rule added afterwards
   cannot remove what a commit already captured.
2. **Never commit a key to a branch, even when the receiving seat asks for it as the convenient path.** Git
   history is permanent, so a key in history is a key that can never be revoked cleanly. Refuse that option and
   say why; offer the ignored-file pickup instead.
3. **Never paste it into chat.** A message becomes a forwarded message, and the seat that refused to take it that
   way was right to refuse.
4. **Ask for deletion on pickup, and delete your copy on their confirmation.** Reciprocal, stated in the note.
5. **Handing a shared fleet key to one more host is a ROTATION EVENT, not a copy** — note it at hand-off time,
   because "everyone has it now" is the moment it stops being scoped to one machine.
6. **The only proof is a keyed call** — `curl -H "Authorization: Bearer $KEY" …/v1/models` → 200. `/health`
   answers 200 to a wrong key and to no key, so it can never be the acceptance test.

## Learned on arthur (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

3. **Key every spool entry by a hash of its CONTENT.** That stops a duplicate ROW; **it does not stop a duplicate
   DELIVERY** — and the difference is the whole defect. A bounded wait that expires says only that the *sender*
   stopped waiting: the message may be sitting in the far seat's log already. Retrying it then delivers a second
   copy of a request that landed, and one probe run proved it — the same text arrived **three times** while the
   spool held one row and the content key never changed.
   - **Before any retry, look for the text in the target's own inbound log** (`/opt/data/profiles/<seat>/logs/
     gateway.log`, whitespace-normalised, first ~60 chars is enough) and on a hit mark the row **delivered** and
     drop it. Checking the spool is not delivery proof; the far seat's log is.
   - **A spool row that outlives a successful send is a guaranteed duplicate**, because nothing records "already
     arrived". So the flush must be able to answer *"did this land?"*, not just *"did my last attempt return?"*.
   holding it open. **Lock the read-modify-write** (`fcntl.flock` on the spool) around load→send→save: two flushes
   that overlap otherwise each load the same row and each deliver it, and an atomic `os.replace` does not help
   because the READ was stale, not the write.
6. **The spool belongs to the SENDER's profile** (`profiles/<sender>/state/dm-spool.jsonl`). One shared path means
   a message addressed to X is later retried BY X, TO itself — an inbound duplicate loop that looks like the
   recipient being spammed by a colleague. And **a default fallback to another seat's profile silently restores
   the loop** whenever the profile env var is unset, so resolve it from the running seat and prove it: print the
   resolved spool path beside the send.
7. **Prove it on the failing path before trusting it:** force a 1-second timeout, confirm the entry is QUEUED,
   queue. Then run **two flushes at once** and count the deliveries — one delivery is the pass, two is the bug
   above. **Test the WRITE path as well as the flush:** N concurrent enqueues should leave N rows, and a shortfall
   is a lost update on the load→append→save. Scale the concurrency until it either fails or you have real evidence
   it holds — a 60-attempt run passed clean on a writer that lost **half of 400**, so a gentle rate proves nothing.
   A flock probe is the cheapest liveness check: open the lock file non-blocking and expect `BlockingIOError`
   while a flush is in flight, which confirms the serialisation instead of assuming it.
### When you are the TARGET of a delivery probe, COUNT the copies and touch nothing
A concurrency test ("two flushes are racing, exactly ONE delivery is the pass") is measured on the receiving seat,
so the receiver's job is to be a passive counter, not a debugger:
- **Count deliveries of the identical text. Two copies is a FAIL, and the second copy arriving minutes after the
  first is the result, not a new question** — report the count, the content key, and the spool state, and stop.
  Re-diagnosing a probe that has already failed burns the run the probe exists to produce.
- **Never run the flush yourself while a probe is in flight.** You will manufacture the second copy and fail the
  test you were asked to observe. Reading `--status` and hashing the spool is safe; sending is not.
- **Check the spool's per-row state before concluding anything about delivery:** `attempts`, `last_attempt`,
  `last_reason`. A row sitting at `attempts=2` with `last_reason="no answer within 60s"` **while the text has
  already arrived** is the exact signature of the defect — the queue cannot see a delivery that only the
  receiver's log can prove.
- **A lock probe is the cheap liveness read:** open the lock file non-blocking; `BlockingIOError` means a flush
  holds it (serialisation working), `LOCK_EX` acquired means the path is idle. Report which you saw.

