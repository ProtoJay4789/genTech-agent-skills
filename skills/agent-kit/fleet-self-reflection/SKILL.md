---
name: fleet-self-reflection
description: Use when asked if everything works, or for a self-audit or coworker reflection.
---

# Fleet self-reflection

**Jordan, 2026-11-01:** *"Anytime I ask a question like this, when I ask if everything is working and if
everything is connected, we're doing what is called a self-reflection… we should create a skill out of
this so we know what we're looking for as far as the audit for ourselves."*

A self-reflection is **not** a status report. A status report says what we did. A self-reflection
**measures our own configuration against what it is supposed to be, and names what is broken.**

**The rule that makes it honest: every finding is a measurement, not an impression.** If you cannot
measure it, say `UNMEASURED` and say what would measure it — never `looks fine`.

---

## Why this exists (the evidence)

Run 2026-11-01, this audit found four real faults that no cron was watching:

1. **`stt.provider: nous`** — not a valid provider. Every seat inherited it, so **every voice note on
every seat failed silently** for weeks. `hermes config set` accepted the bogus value; the validator is
not a check.
2. **`image_gen.provider: nous`** — same bug, unnoticed. `FAL_KEY` was commented out in `.env`, so
**image generation had no working provider at all**; sessions fell back to hand-written scripts.
3. **`fallback_providers: nous` on all five configs** — the metered rail was armed as a **silent**
fallback. Measured drain: **1,227,576,788 cache-read tokens on the metered lane**, 98% of it from one
long-lived session that kept being re-read. Nobody decided to spend it.
4. **29 of 29 cron jobs inherit the seat model** — mechanical jobs (backups, list audits, sync checks)
run at the same tier as reasoning work. Not a bug, an unfilled decision.

**Common shape: a plausible-looking config value that resolves to nothing, fails silently, and no
check exists to notice.** That is what this skill hunts.

---

## The audit — run all of it, in this order

### 0 · Read what the LAST pass already measured, before measuring anything

**The cheapest evidence in any audit is the note the previous pass left behind — and it is the thing
most reliably skipped.** A probe tool written weeks ago usually carries the answer in its own
docstring, because whoever wrote it measured the number to justify writing it.

Measured on ourselves: a question was re-derived from raw logs for the better part of a session
("how many callers knocked and how many paid?"), while the script that had analysed exactly that
data contained the figure in its opening comment — alongside a second finding nobody had read: a named
gap in the feature, stated as *"that step is NOT built here and named as a gap rather than faked."*

**So, before auditing a domain:**

```bash
ls -t <that area's scripts and notes> | head -20     # the NEWEST artifacts hold the newest findings
head -40 <the newest script>                          # docstrings carry measured numbers
```

- **A prior pass's number is evidence, not truth.** Read its date and method before reusing it — a
  stale measurement is a claim like any other.
- **A docstring that names its own gap has already delivered a finding.** Quote it in the report
  instead of rediscovering it, and credit it as known work rather than presenting it as new.
- **When the prior number and your fresh number disagree, neither is automatically right.** That
  disagreement is the audit's most valuable output; find the method difference before picking one.
- **⚠️ Re-deriving a known number is worse than wasted time — it reads as discovery.** A report that
  presents a two-week-old measurement as a new finding tells the reader the estate is less understood
  than it is, and it hides the fact that the earlier finding was never acted on.

### 1 · Provider and model resolution (the silent-failure layer)

```bash
cd /opt/data
for p in /opt/data/config.yaml /opt/data/profiles/*/config.yaml; do
  echo "--- $p"
  grep -A4 '^model:' "$p" | head -5
  grep -A5 '^fallback_providers:' "$p" | head -6
done
```

**Check every value against the schema, not against intuition.** Valid providers live in
`/opt/hermes/hermes_cli/config_defaults.py` — read the list, do not recall it.

- ⚠️ **An invalid provider resolves to nothing and fails SILENTLY.** `hermes config set` will accept any
  string. **The validator is not a check; the schema is.**
- ⚠️ **A metered fallback is a spend decision nobody makes.** Check `fallback_providers` on every seat;
  a metered provider there can drain a balance invisibly on any hiccup.
- ⚠️ **Grade the MODEL, not the provider name.** A metered provider carrying a `:free` model cannot run
  up a bill. Flagging it anyway is the keyword-as-fact error this audit exists to catch, and it
  produces a permanent red light — which is ignored exactly like a permanent green one. Only
  `provider in METERED and not model.endswith(':free')` is a spend finding.

#### Editing config is not the same as changing it

**The running process OWNS keys like `fallback_providers`, and it will write its own copy back over a
hand edit.** This is the single most expensive lesson in the skill: a regex removal validated as
`0 armed` on all five configs came back armed — with a **new** entry appended — minutes later, each
file left with a `config.yaml.bak-<key>-<timestamp>` beside it. `DEFAULT_CONFIG` for that key is `[]`,
so a schema merge cannot explain it: an owner normalised the key and re-persisted it.

**The general rule: before editing a config key by text, ask whether a command owns it.** If
`hermes <thing> list|add|remove|clear` exists for that key, the text edit is the wrong instrument and
losing the race is not a matter of timing — it is guaranteed. `ls *.bak-*` beside a config is the
tell that something else writes that file.

**Use the command that owns the key, never a text edit.**

```bash
# ✅ owner path — the write survives, and it reports the file it touched
HERMES_HOME=/opt/data/profiles/<seat> hermes config set fallback_providers '[{"provider":"…","model":"…:free"}]'
HERMES_HOME=/opt/data              hermes config set fallback_providers '[…]'   # default profile

# ✅ and read the chain back through the same owner
hermes fallback list
```

**⚠️ `HERMES_PROFILE` is NOT the profile selector for `hermes config`.** Setting it produces writes that
all land in the *same* config while reporting different intents — four invocations, four different
seat names echoed, one file actually written. **`HERMES_HOME` is the variable**, and the reliable
confirmation is the path printed by `config set`, not the variable you set.

**A corollary that invalidates whole verifications:** any "each config parses / each config has X"
check run with the wrong selector is measuring one file N times. Read the path back from the tool's
own output before believing a per-profile result.

**And a hand edit is not live until a restart.** Until the gateway reloads, the scorecard is grading
**files** while the fleet runs the **old** config. State that plainly in every report: staged, not
applied. The measurement that matters is the one taken *after* the restart.

### 2 · Prove the spending lane, from the ledger

```bash
sqlite3 "file:/opt/data/profiles/<seat>/state.db?mode=ro" \
  "SELECT billing_provider, COUNT(*), SUM(cache_read_tokens) FROM session_model_usage GROUP BY billing_provider;"
```

**`billing_provider` is the truth about who charged you.** Report the split per seat. If a metered
provider appears, get the dates:

```sql
SELECT date(first_seen,'unixepoch') d, COUNT(*), SUM(cache_read_tokens)
FROM session_model_usage WHERE billing_provider='<metered>' GROUP BY d ORDER BY d DESC;
```

⚠️ **A session's rows can be split across providers** — a provider flip mid-session leaves old calls on
the old lane. **A single huge day means one long session, not a runaway job.** Check `session_id`
before blaming a cron.

**⚠️ `estimated_cost_usd` is a price list; `actual_cost_usd` is a charge. Report both.** A lane can read
as an enormous drain in tokens and still have cost **$0.00 actual**, because the model on it is a
subscription tier or `:free`. Before writing the word "billing", print the money columns per seat:

```sql
SELECT billing_provider, SUM(estimated_cost_usd), SUM(actual_cost_usd), cost_status
FROM session_model_usage GROUP BY billing_provider;
```

**A `billing_provider` label is an attribution, not an invoice.** The ledger names whichever rail answered;
it does not establish that the rail charged. When the estimated total is single-digit dollars and every
`actual_cost_usd` is `0.00` with `cost_status=estimated`, the correct finding is **"labelled, not charged"** —
and the action is to close the latent path, not to escalate a spend. **Reporting a token count as money is
the same keyword-as-fact error as reporting a provider name as a capability.**

### 3 · Per-tool config blocks: present ≠ working

For each tool family (`stt`, `image_gen`, `video_gen`, vision/auxiliary), confirm **both**:

- the config **loads** — `load_config()` returning `None` for a block means it is not in the schema and
  the tool is reading nothing
- a **credential exists and is uncommented** — `grep '^KEY=' .env`, not `grep 'KEY' .env`

```bash
# WRONG — matches the commented line and reports a credential that does not exist
grep -q 'FAL_KEY' /opt/data/.env && echo "present"

# RIGHT
grep -q '^FAL_KEY=' /opt/data/.env && echo "present" || echo "ABSENT (or commented)"
```

⚠️ **`image_gen` and `video_gen` are not top-level schema keys.** A `provider:` line under them is
inert. Providers are chosen by credential + plugin, not by that line. **Verify by checking which
`plugins/image_gen/*` directories exist and which have keys.**

#### The inverse: a tool REPORTED missing is not a tool that is missing

**A preflight warning is a claim about a ledger, not about the world.** When a CLI prints something
like `install out of sync (ffmpeg: not installed or outdated; node: …; ripgrep: …)` on **every**
invocation — including `--help` — treat it as bookkeeping drift until a capability test says otherwise.

**The test is one command per tool, not a reinstall:**

```bash
command -v <tool> && <tool> --version | head -1     # present and runnable?
```

**The tool that matters gets a REAL exercise, not a version string** — for `ffmpeg`, transcribe one
audio file and assert exit 0 with plausible text. That single call retires the whole warning.

**Why the ledger disagrees:** a package manager only vouches for what *it* installed. Tools baked into
the image under the product's own `tools/` tree are on `PATH` and fully functional while absent from
`<data>/tools/facts.json`, so `drift()` returns them as "not installed or outdated" forever. The
remedy in the message ("rebuild the artifact") means **a host-side image rebuild** — a production
change to fix a cosmetic line.

- **A warning that prints on every command has no information content.** It cannot distinguish the day
the thing actually breaks, so it trains the reader to ignore the one that can.
- **Never reinstall, and never escalate, to silence a warning** until a capability test has failed.
- **Record it as a known cosmetic warning** with the evidence (versions + one real exercise), so the
  next audit does not re-investigate it as a fault. That note is the entire deliverable.

#### A credential that EXISTS is not a credential that WORKS

**A key file on disk proves nothing.** An uncommented, correctly-shaped, mode-600 credential survived
weeks after the vendor had revoked it, and the wiring notes beside it still read "Drive is live".
**Before installing a credential — and before ever reporting that access exists — spend one call
proving the API accepts it.** A dead key sitting in a file looks exactly like access.

**The discriminator that actually settles "is it dead or just under-scoped":**

| pattern across the API surface | verdict |
|---|---|
| **uniformly rejected** — every endpoint returns the same auth error | the value is invalid/revoked; no scope or header will fix it |
| **accepted somewhere, forbidden elsewhere** | the key is valid but lacks a permission — fix the scope, not the key |

Test several endpoints before concluding: the auth surface is where a scope bug shows up as green on
`/toolkits` and red on the endpoint you wanted. **Uniform rejection is the only evidence that the
value itself is wrong.**

**Use a control key.** Send one obviously fake value and one empty header alongside the real one:

- real key and fake key return the **same** error → the server is matching values; the key is dead
- real key returns `invalid` while empty returns **`no auth provided`** → the header is correct and
the rejection is about the value, not the wiring
- empty header returns the role/permission error → **the header name is wrong**, fix that before
anything else

**If the vendor ships a CLI, it outranks your curl.** `composio login --user-api-key …` returning
"Invalid or revoked user API key" is one call and settles what five header permutations only hint at.
Reach for the vendor's own client early rather than reconstructing its auth from HTTP codes.

**Check whether the VENDOR is down before blaming the credential.** A `503`/`DEPLOYMENT_PAUSED` from a
provider endpoint is not our key, not our IP, and not our request — confirm the service is up (and
say so in the report) before proposing a rotation the user cannot perform.

**When the tool cannot be fixed, still deliver the half that does not depend on it.** Access being
blocked rarely blocks the whole task: local copies, backups and staging material are usually already
on disk. Split the work into "what needs the blocked path" and "what does not", do the second now,
and ask the one question that unblocks the first (here: *does the destination agent read from this
host, or its own machine?*) — that answer changes the whole plan and costs nothing to obtain.

### 4 · Cron cost: tokens, not model names

```python
scripted = sum(1 for j in jobs if j.get("no_agent"))   # 0 tokens, model field irrelevant
llm      = len(jobs) - scripted                        # these are the ones that cost
```

**The metric is the script-only ratio, not `inherited/total`.** A job with `no_agent: true` never calls
a model, so its model field means nothing and it costs nothing regardless of what it says. **Scoring
"N of M jobs name their own model" manufactures a red light over a fleet that is already ideal** — and
a red light nobody can turn off is ignored exactly like a silent one.

**The defect worth finding is narrower: a job whose PROMPT is an instruction to run one command, but
which still pays a model to type it.** Their prompts announce themselves — `Script-only job: …`,
`Run: python3 …`, `Run this exactly once: python3 …`. Converting them is free money and removes a
model from the failure path: set `no_agent: true`, `script: <file>`, and keep the old prompt as
documentation. **Verify the script's contract first** — silent-on-success, a real print path, and a
`0/2/3` exit code — or the conversion turns a summary into raw noise. **And check what the cron layer
does with that code: a non-zero exit is recorded as `error`, so a script that exits `2` on findings turns
every real finding into a crashed job.** Wrap the conversion so findings exit `0` (§11).

**Check the THIRD state before converting — instrument failure — because the other two can both look
right.** Measured across five wrappers in one pass: each printed `… INSTRUMENT FAILED …` when its
subprocess broke and then fell through to `exit 0`, and one never captured the exit code at all.
Silent-on-success ✅, prints-on-findings ✅, **and a broken tool reported as a clean run.** Those jobs
delivered to `local`, so the printed alarm went to a file nothing reads — the exit code was the only
channel reaching cron health, and it was the one lying. **A wrapper's failure branch exits `3`; the print
is for the reader, the code is for the monitoring.**

**Run each candidate and read all three, rather than reading the source and hoping:** exit `0` with
**zero** lines is the pass shape, exit `0` with lines is a finding worth reading, and a non-zero on
healthy input is a defect in the script you are about to promote.

**Prove the conversion ON DISK, not from the tool's reply.** `hermes cron edit <id> --no-agent --script
<file>` echoes `Mode: no-agent`, but the record is `no_agent: true` plus a resolving `script:` in that
seat's `jobs.json` — read it back, because the reply is a claim about intent. Then `hermes cron run <id>`
proves the new mode executes — **but it bypasses the scheduler and leaves `last_run: None`**, so report
the conversion as verified-in-mode, never as verified-in-schedule. The scheduled run is a separate proof
you still owe.

**⚠️ Match the prompt SHAPE, not the word.** A job that *mentions* a script ("the script output is the
live report — treat it as fact") is doing judgement **on** script output and should keep its model.
Only a prompt that opens with the instruction, or is short + one command + asks for no analysis,
counts. Same keyword-as-fact error this file exists to catch.

**Report which LLM jobs remain and why each one reasons.** Three that genuinely need a model is a
healthy fleet, not a gap.

#### A job whose output nobody reads is not running — it is producing

**"Is there a cron job running that is no longer serving its purpose?" cannot be answered by listing jobs.
It is answered by tracing each job's OUTPUT to a CONSUMER.**

Measured on ourselves: a weekly sweep ran correctly, scored its input, and printed a shortlist to stdout.
The meeting it existed to stock read the board and its own minutes — **and never opened the sweep.** Every
run succeeded. The feature was inert for its entire life, and no health check could see it, because the job
was never broken.

**So for each job, name the artifact it writes and then name who opens it:**

```bash
grep -rl "<the artifact path or format the job writes>" <the tree those consumers live in>
```

- **stdout is not a consumer.** Under `no_agent`, stdout is a chat message and nothing more — it is read
  once by a human and never by a program. **A producer that only prints has no consumer.**
- **A file nothing greps for is the same as stdout**, with more disk. Search for the path, not for the intent.
- **The consumer is usually the thing the user described as the point.** If Jordan says a step exists *"to
  give the council time to prepare"*, then grep the council's own code for that file — if it is absent, the
  intended consumer was never wired and the pipeline is two halves.
- **Fix it by wiring the consumer, not by improving the producer.** Adding retries, better scoring or a
  richer report to a job nobody reads is effort spent on the wrong end.
- **Then make the absence LOUD.** A consumer that finds no input must print *"no input on file this week"* —
  a silent skip is indistinguishable from a healthy quiet run.

**Do not change routing; routing is Jordan's to set.** Say which jobs would benefit and wait.

### 5 · The brain's own records

- Four lists: age, size, live/done/blocked, parseable
- Ideas: ids present, bullets joined to a record
- Completions registry vs append log — are shipped items reaching the queryable record

### 6 · External surfaces agree

Every published surface must give the same inventory. **Counting the wrong thing is worse than not
counting** — check the structure before reporting a number.

**⚠️ And check it as the audience, not as yourself.** Your own authenticated view is the most
flattering vantage you own: a private repo returns `200` to its owner and `404` to everyone else, and
an unauthenticated fetch is the only request that answers *"can they actually see it?"*

```bash
git_repo=ProtoJay4789/vanito-hermes-agent
curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/$git_repo   # 404 = private
curl -s -o /dev/null -w "%{http_code}" https://github.com/$git_repo             # 200 = public
curl -s "https://raw.githubusercontent.com/$git_repo/main/<path>"               # no auth header
```

**A visibility flag in an API response is the API agreeing with you, not the world's view.** One
unauthenticated request per published surface settles it, and it is also the cheapest way to catch
content that should not have been published — see `claim-provenance` on auditing for the reader's
vantage rather than your own.

### 7 · Identity files — is every seat actually running ITS instructions?

**A seat behaving wrong is usually a seat with no orders, not a seat ignoring orders.** Measure the
identity file's **size and content**, not just its presence:

```bash
wc -c /opt/data/profiles/*/SOUL.md
head -3 /opt/data/profiles/<seat>/SOUL.md     # does it name the seat, or start "You are Hermes Agent"?
```

**⚠️ A SOUL.md that opens with the stock Hermes prompt text is the default, not a seat** — the file
exists, differs from every other seat (so the private-set hash check reads healthy), loads cleanly, and
gives the agent no role, no group, no fleet protocol and no ACK requirement. It is the config-layer
version of the same bug this whole audit hunts: **a plausible value that resolves to something
generic and fails silently.**

**A wide spread is the tell.** Identity files are deliberately private and never synced, so sizes
should vary with the seat's job — but a spread of an order of magnitude means at least one seat was
never written, not that it has a leaner personality. Confirm by reading the smallest, not by assuming.

### 8 · The EXEMPTION audit — what is each monitor forbidden to report?

**A monitor that is working correctly and a monitor that has been told to ignore the fault produce the
same output: silence.** So the audit question is never "did the job run?" (it did, and it exited 0). It
is **"what is this job not allowed to tell me?"**

Measured on ourselves: a backend-liveness job ran every four hours for a night and reported
`silent — empty output` on every run. **It was right every time.** Three backends were down and all
three sat in the same hardcoded dict:

```python
OUT_OF_SERVICE = {
    "score":     "router :8087 not started",
    "route":     "router :8087 not started",
    "providers": "router :8087 not started",
}
```

The router had never been started at all. **A service that was never started is a hole, not a
decision** — but it was written down as one, months earlier, and never revisited.

**The rule:**

> **Every allowlist / out-of-service / known-issue entry MUST carry an OWNER and an EXPIRY. Past its
expiry it alerts like any other fault.** A permanent exemption is a blindfold with a written note.

**Why it fails silently and permanently:** the list only grows. Each addition is locally reasonable
(*"we know about that one, stop nagging"*), and the aggregate is a monitor that cannot report the exact
class of outage it was built for. **Nothing in the system ever says "this excuse is now stale."**

**Run it as a probe, not a reading:**

1. **List the exemptions.** `grep -n -A20 'OUT_OF_SERVICE\|KNOWN_DOWN\|IGNORE\|SUPPRESS\|ALLOWLIST' <script>`
2. **For each entry, ask when it was written and whether the condition is still TRUE.** An entry whose
   stated reason is *"not started"* / *"temporarily blocked"* / *"waiting on X"* is a claim about the
   past. Verify it against the live system.
3. **Diff the excuse list against the live failure set.** Any entry that is BOTH excused and still
   failing is either a decision that needs an owner, or a hole that has been hidden.
4. **Prove the monitor can still go red.** Break something it is not excused from and confirm it speaks.
   A monitor whose only remaining subjects are healthy is indistinguishable from a dead one.

**Same family, different shape:** the stale-`READY` state file, the `|| true` on a probe, the quiet-hours
mask, and a `try/except: pass` around the check. **A gate that fails OPEN when its input goes stale is not
a gate.** Ask of every suppression: *if this source of truth stops being true, does the system fail closed
or open?*

### 9 · The COWORKER reflection — ask the seats, because they are the workers

**Jordan, 2026-11-10:** *"ask agents their opinion on how things are working. Since agents are the workers,
we should look into a coworker reflection or an agentic reflection."*

**Sections 1–8 audit the ESTATE — configs, cron, credentials, surfaces. That is the machinery. It cannot
see the waste that lives in the work itself:** a handoff sent twice, a probe that asks "are you there?",
a task a weaker model flattens. **Only the seat that did the turn knows it cost a turn for nothing.**

**Run it after the mechanical audit, and never instead of it.** The two answer different questions: *is
the estate correctly configured* and *is the work worth the turns we pay for it*.

#### How to ask — the shape that produced usable answers

One message per seat, **short, numbered, English, with a line limit**. Measured 2026-11-10 across three
seats, this returned specific, non-generic answers on the first try:

```
HQ here — one question, answer short.
1) Which model do you currently run?
2) Name ONE task in your lane where a different model would do better, and why.
3) Any one thing you'd change about how we work. Reply in English, six lines max.
```

- **Ask for ONE task, not a category.** "What's inefficient?" gets an essay; "name ONE task" gets a name
  and a reason.
- **Ask what they RUN, not what they think of the fleet.** A seat knows its own config and its own waste.
- **Six lines max is load-bearing.** Long answers get summarised into platitudes; short ones stay specific.
- **Follow up on the cut-off.** A truncated reply is normal; one short second DM ("you answered 2, give me
  the rest of 2 and your answer to 3") recovers it and costs far less than re-asking everything.

#### What their answers are worth — and what they are not

**Three seats answered 2026-11-10, and all three skipped the model question to name process waste:**
duplicate handoffs re-sent to a seat that had already filed an answer; bare wake probes ("reply with your
seat name and session id") costing a full model turn each while carrying no payload; long verdict notes
written by a fast model that flattens sourced claims.

- **A seat's opinion about its own waste is HIGH-VALUE.** It is a first-person account of a cost nobody
  else can see, and it is verifiable — every claim above was checked against cron config, the probe script
  and the session ledger before being acted on.
- **A seat's opinion about a MODEL is a HYPOTHESIS, not a finding.** Three agents believing a bigger model
  writes better receipts is a good reason to run a test and no reason to switch a default. **Same rule as
  every other claim in this file: measure it.**
- **A seat's opinion about another seat is out of scope.** Ask each about its own lane; cross-seat
  complaints are routing, and routing is Jordan's.
- **Never ask a seat what it would like to be given to do.** That is a wish list, not a reflection. Ask what
  costs it a turn for nothing.

#### Convert an answer into a test before acting

| the seat said | the evidence it goes behind |
|---|---|
| "we re-send handoffs" | grep the return lane for the same slug — `dispatch-guard.py <seat> <slug>` |
| "wake probes cost turns" | read the probe's message text and its run count; if the payload is only "prove you exist", it is a tax |
| "a faster model flattens my writing" | **UNMEASURED until run**: same prompt, same input, both models, compare sourced-claim counts |

**A coworker reflection that ends in action without a measurement is a survey, not a reflection.**

### 10 · The TEAM-LEADER reflection — three axes, and the leader is one of them

**A self-reflection that only audits the estate is an inspector's report. The standing standard is three
axes, and the third one is the reason the other two improve:**

| axis | the question | what answers it |
|---|---|---|
| **Department** | is my own domain correctly configured and running? | sections 1–8 — config, cron, credentials, surfaces |
| **Self as leader** | am I running this lane well, or merely keeping it alive? | the turn-cost and handoff evidence in section 9 |
| **The orchestrator** | *"what can I do to help you?"* | the inputs the seat lacks — access, a ruling, a credential, a decision |

**Ask the third axis explicitly, in every pass, and never skip it as rhetorical.** Jordan's framing:
*"Because I'm the orchestrator, what can I do to help you?"* — it is a request for a specific, answerable
ask, and a report that ends without one leaves the human's half of the work unnamed.

- **Distinguish the orchestrator axis from a wish list.** *"What would you like to be given to do"* is
  out of scope, as section 9 says. *"What input are you missing that makes your lane slow or blocked"* is
  in scope and actionable — a missing credential, an unanswered routing question, a decision nobody made.
  Ask for the **input**, not for the assignment.
- **Answer it about yourself even when nobody asks you.** A leader report that lists only the department's
  faults is incomplete; name the one thing in your own conduct you would change, measured if you can.
  *"I edited skills twice this session and deepened the seats-vs-CORE drift"* is a self-assessment;
  *"I think I'm doing well"* is not.
- **A department finding and a leadership finding are different repairs.** One is a config change or a
  script fix; the other is a change to how the lane is run. Filing the second as the first produces a
  fixed mechanism and an unchanged habit.

#### Track who ANSWERS, not only who is correct

**An agent that is never wrong and never replies is a worse teammate than one that is occasionally wrong
and always answers.** Acknowledgment is a measurable behaviour, and it decays silently because nothing in
the system asks about it.

- **Keep the count per seat: handoffs received, ACKed, answered, and ignored** — read from the handoff
  tree, not from memory. A seat's reply is evidence; a seat's silence on a handoff addressed to it is the
  finding.
- **Name the seat and the artifact.** *"3 of 9 handoffs to that seat have no reply in the thread"* is
  actionable; *"communication could improve"* is not.
- **Feed it back as a private, specific observation, not a public score.** The purpose is a reply, not a
  ranking.
- **Include yourself.** If HQ sent handoffs with no named owner or no deadline and got no answer, the
  defect is HQ's — a vague handoff that gets no reply is the sender's problem, not the recipient's.

### 11 · The per-seat department reflection — each seat grades ITSELF

**Sections 1–10 are run FROM HQ, on the estate. That is inspection, and it has a blind spot: no seat ever grades
its own work.** The distinction matters — *"ask agents about the current cron jobs they run in their
departments… get a self-reflection of that."* A seat that is only ever graded from outside has no way to notice
its own decay between audits.

**Build it as a script that runs ON the seat and reads ONLY that seat's own tree.** Two properties make it
work:

- **Derive the profile from the file's own path**, not an argument:
  `os.path.basename(os.path.dirname(os.path.dirname(__file__)))` resolves `profiles/<seat>/scripts/…` to
  `<seat>`. One binary, installed on every seat, no per-seat variant to drift. An argument a caller can get wrong
  is a wrong reading waiting to happen.
- **Same scorecard design as the rest of this file** — numeric probes, a stored baseline, print what MOVED,
  silent when healthy. A per-seat essay is worth less than a number comparable to last week.

#### ⚠️ The WRAPPER is a second copy of that decision, and it silently re-points every seat

**Deriving the seat from the file's own path is correct and it is still not enough, because the cron
wrapper is a separate script that hardcodes a path.** Measured: four seats' `dept-reflect.sh` wrappers were
**md5-identical**, and every one of them named `/opt/data/profiles/gentech/scripts/dept-reflect.py`. The
`.py` resolved its own path faithfully — so Treasury's job graded **Gentech's** department, printed the
score under Treasury's name, and returned a verdict about the wrong seat. Four reflections, one subject.

**Whatever derives the seat must derive it at the LAST layer before execution, from the path that is
actually running.** In the wrapper, resolve from the wrapper's own location, never from a literal:

```sh
SEAT=$(basename "$(dirname "$(dirname "$0")")")   # profiles/<seat>/scripts/dept-reflect.sh -> <seat>
OUT=$(python3 "/opt/data/profiles/$SEAT/scripts/dept-reflect.py" "$@" 2>&1)
```

**Verify by the seat name printed in the first line, not by "the file exists on all four seats".** Four
identical hashes across seats is the tell when paths are hardcoded; four DIFFERENT printed seat names is
the proof it is fixed. **A shared CORE copy makes this worse, not better: one file naming one seat is
correct in CORE and wrong in every seat it is copied to.**

#### Exit `2` is a FINDING, and the cron layer records it as a CRASH

**A `no_agent` job treats any non-zero exit as `last_status: error`, and the cron-health probe counts that
as a broken job.** So a probe that correctly exits `2` for "measured, found something" — the contract in
`references/writing-probes.md` §6 — makes every run that finds anything look like a crash, permanently.
Measured: three seats reported `error` on every reflection while the reflections were working perfectly.
The findings were never reported *as findings*, so the one thing the job exists to say was invisible.

**The boundary rule: the cron health signal means "the measurement ran", never "the department has work
to do".** Convert at the wrapper, keep the distinction, keep a broken instrument loud:

```sh
printf '%s\n' "$OUT"
[ "$RC" -eq 2 ] && exit 0     # findings are a SUCCESSFUL measurement
[ "$RC" -eq 3 ] && exit 3     # could not measure — must stay red
exit "$RC"
```

**And because the wrapper now swallows the code, the verdict must be in STDOUT or it is lost.** Print
`⚠️ FINDINGS: 3 probe(s) failed — 01_cron_health, 03_memory_headroom` before the script returns 2. **A
wrapper that converts findings to success WITHOUT a printed verdict builds a monitor that cannot go
red** — the exact failure this file hunts, introduced by the fix for a different one.

**Test by running the wrapper by hand on each seat and reading BOTH the printed seat name and the exit
code.** That one command proves both bugs are gone. `hermes cron run <id>` can refuse a job that belongs
to another seat's registry ("job not found"), so the scheduled run is the confirmation, not the test.

#### A job that has NEVER once reported success has never been proven to run end-to-end

**"It errors, but the output looks right" is not reassurance** — the output was written before the failure,
or truncated at it. A permanent `error` means **this path has never completed**, and every green-looking line
it produced came from a code path that did not reach its end. So: **treat a never-successful job as
UNMEASURED, not as working-with-cosmetic-noise**, and re-run it in a state where success is possible before
trusting a single line it emitted.

The tell that this has been happening for weeks: `last_status` is `error` on **every** run while its printed
output reads plausibly. That combination is the fingerprint of a contract bug (exit code, missing verdict
line, a swallowed exception after the print), not of an intermittent fault — an intermittent fault produces
*some* successes.
- **A finding about a never-successful job outranks every finding the job carries**, because the job's own
  subject matter is unverified while it has never completed.
- **Do not re-baseline a never-successful instrument.** Its stored baseline is from a run that never finished;
  saving over it makes the first honest run look like a regression.

**The probe set that earns its keep (each is one file read, no model, no network):**

| probe | measure | why it is the one that matters |
|---|---|---|
| **memory headroom** | `cap − len(text)` in **chars**, signed, both files | negative = writes already refused; this is what "forgot yesterday" looks like from inside. ⚠️ Subtracting BYTES from a char cap over-reports by ~2% and invents a file that is already over |
| cron health | jobs whose `last_status` is not `ok` | a job that errored did not do its work |
| cron enabled | count disabled | a disabled job looks like coverage and is not |
| script existence | every `script:` referenced by a job resolves on disk | the same "declared but never implemented" class as a route with no handler |
| delivery target | enabled jobs with no deliver target | a report with nowhere to go reads as a healthy silent run |

- **Make the pass condition a FLOOR, not a percentage.** `headroom ≥ 200 chars` (≈ two durable facts). A probe
  that only asks "is it above 85%?" cannot express "this file is already over its cap and refusing writes".
- **Measure in the ENFORCER's unit, not the shell's.** `wc -c` gives bytes; the memory cap counts `len()` of the
  joined string. A probe that subtracts bytes from a char cap reports a file at **−31 when it had +99 free**, and
  the next hour is spent trimming a file that never refused a write. Read the enforcing code before believing the
  arithmetic.
- **Prove each profile is a SEAT before grading it.** `glob('profiles/*')` returns directories, not seats: a
  leftover test artifact with a `SOUL.md`, an empty `memories/` and **no `config.yaml`** was graded and reported as
  a finding. Require `config.yaml` — an instrument that grades clutter manufactures output that reads like a fault.
- **A seat with no cron jobs is a FAILURE of that probe, not `n/a`.** Zero automation on a working seat is the
  finding — it means nothing accumulates there between human requests.

**Automation density is uneven, and the thinnest seat is the one that fails silently.** Measured across four
seats: **49 / 19 / 3 / 0** cron jobs. The seat that had just been reported as *forgetting a conversation* was
near the bottom of that list — almost nothing was watching it, and the one probe that would have caught the
cause (memory headroom) did not exist there. **Report the per-seat job count beside the probe results**; it
explains why two seats running the same code produce different experiences.

**Schedule it for after the workday, not during it.** The files a seat grades change only when work happens, so
a mid-day run reports a half-finished day and needs a second run to see the real one. Late afternoon, before any
quiet window, gives one run that reflects the actual day. `no_agent` + a script means zero model cost, so
cadence is a scheduling choice rather than a spend decision — and silent-when-healthy keeps it from becoming
heartbeat noise.

**Ship the script into the shared CORE tree, not only into each seat.** A per-seat instrument that lives only on
the seats is lost in the rebuild that most needs it to run afterwards.

**And when you repair a wrapper by hand on the seats, reconcile it against the canonical copy shipped with this
skill (`scripts/dept-reflect.sh`) before calling it done.** A hand-typed fix is nearly always the weaker variant —
it drops `set -u` and the missing-file guard, so all four seats run a version the next rebuild will silently
replace. **Fix once in the canonical file, then copy that file to every seat**; four identical hashes are correct
here, because the seat is resolved at runtime and the bytes should not differ.

#### ⚠️ Unequal hashes are the MIRROR defect: the upgrade landed on one seat

**Identical hashes are only the correct end state once every copy is the current one.** A wrapper that gains a
capability on the seat its owner happens to be sitting in keeps its older, thinner form everywhere else — and
nothing looks broken, because each seat still runs a wrapper, still exits `0`, and still prints something.

Measured: one seat's memory wrapper was **2,199 bytes** (measure + propose + ACT) while the other three were
**231 bytes** (measure only), so the step that actually changed anything existed on exactly one seat, and three
seats kept printing proposals with no actor attached. Every report read healthy.

```sh
md5sum profiles/*/scripts/<wrapper>.sh; wc -c profiles/*/scripts/<wrapper>.sh
grep -n '<the call that only the new copy makes>' profiles/*/scripts/<wrapper>.sh
```

- **A large SIZE GAP between copies of a file that should be identical is a shipped capability, not a variant.**
  Identical hashes are the tell when paths are hardcoded; a 10× size gap is the tell when one copy was upgraded and
  the rest were not. Both are bugs, in opposite directions.
- **Verify by BEHAVIOUR after copying** — the step now happens on each seat — not by the hash alone. Four matching
  hashes prove the bytes agree, not that the behaviour was ever exercised on a seat you were not sitting in.
- **When a fleet-wide script takes a `--profile` filter, remember its default is every seat.** A wrapper that runs it
  with no argument already covered the fleet, which is exactly how a seat-local defect hides: the output looks
  complete and the one seat whose owner was awake is the one that got fixed.

---

## Reporting

**Verdict first, then a scorecard, then the one thing to fix.**

**Every line that reports a fault ends in an ACTION or an OWNER.** A finding phrased only as *"the seat needs to
choose"* reads as all-clear — measured, that exact sentence printed twice a day while three files sat at 96–98%
and nobody acted. *"ACTION: consolidate BY HAND — merge same-topic entries, push detail to the archive"* is the
same finding and gets done. **A report that names no action gets no action.**

```
✅ working      what was measured and how
🔴 broken       what is wrong, the evidence, and what it costs
⚠️ unmeasured   what could not be checked, and what would check it
```

### The scorecard is a stored artifact, not a paragraph

**A self-reflection written fresh each time is an essay.** It can be eloquent and useless, because the
reader cannot tell improvement from a change of mood. Persist the probe results and print what
**moved**: `⬆️ improved since last baseline` / `⬇️ REGRESSED since last baseline`, by probe name.
**A regression line is the single most valuable output and it only exists if the previous run was
stored.** Save a baseline only once the probes are correct — saving a buggy run makes the next honest
run look like a regression, which teaches the reader to ignore the one signal worth having.

**⚠️ But a metric that goes red again after an all-clear is not always a regression — sometimes the
process keeps genuinely happening, and the report must say which.** Measured: a `seats_vs_core` probe read
`0 files differ`, and 24 minutes later read `5 files differ` again. Nothing had broken — other seats had
**learned** in between and written the new rule into their own copies. Two rules follow:

- **Report the MECHANISM, not just the delta.** `⬇️ REGRESSED` is only true if something got worse. When
the differing artifacts are *larger* and contain coherent new content, the correct line is *"drift returned
because three seats learned after the last sync — promote-then-sync, not revert."*
- **Fix in the direction the evidence points.** Overwriting the larger copy to make the number green
deletes exactly what the fleet just learned. **The bigger artifact is almost always the newer knowledge.**
- **A recurring red on one metric is a finding about the process, not a broken probe.** Do not retire the
  probe because it keeps firing; it is reporting something that keeps happening.

#### ⚠️ A reflection nobody scheduled is not a practice — check the SCHEDULER before the probes

**The script existing is the declaration; a cron entry is the behaviour.** Measured on ourselves: a
self-reflection script was written, committed and correct — and referenced by **zero** jobs across every
seat's `jobs.json`. It ran only when a human asked, so for over two weeks the fleet's self-assessment was
whatever someone remembered to request. That is the exact defect this skill hunts, one level up: **a
capability that resolves to nothing and fails silently.**

```bash
# the reflection is PERMANENT when a job names it
for f in /opt/data/cron/jobs.json /opt/data/profiles/*/cron/jobs.json; do
  echo "--- $f"; grep -c 'self-reflect\|self_reflect' "$f" 2>/dev/null || echo 0
done
```

- **Zero references is the FIRST finding of the pass, not a footnote.** Report *"the mechanism exists and
  nothing runs it"* before reporting a single probe result, because an unscheduled probe's results are a
  one-off measurement of a system nobody is watching.
- **Run it by hand anyway** — the manual run is what produces the scorecard — but never let a manual run
  stand in for a schedule. Hand-running is proof the probe works, not proof the practice exists.
- **Then decide the cadence with the owner, and say which you chose.** On-request only, a weekly job, or
  continuous-in-conversation are three different commitments; the fleet does not get to pick silently.
  Continuous has a cost worth naming: it competes for the same context as the work itself.

#### The DEPARTMENT WALK — three fixed questions, per-department material

**The per-seat probe grades the machinery; it does not say whether the department is doing its job.**
Jordan's distinction: *"it's pretty much saying 'hey, is our cron job working?'… it needs to be more
department-focused… almost like the CEO walk — what are we working on, what are we improving, where are we
going next."* Both belong; they answer different questions and neither replaces the other.

**Three fixed questions. The material behind each one is per department, and that is the whole design:**

| question | answered from | never from |
|---|---|---|
| **what are we working on** | that department's own handoff lane this week, plus inbound replies | a fleet-wide "recent activity" list |
| **what did we improve** | its own appended completions **and** a measured delta | an impression, or another seat's wins |
| **where are we going next** | the question that department is judged on | a generic "continue improving" |

**The cron state rides under "what did we improve" as EVIDENCE, not as the subject.** `crons: 15/16 · 0 not ok`
is one line of a department report; it is not the report. A walk whose entire body is cron health is an
infrastructure probe wearing a department's name.

**Encode "where next" as a per-department DOCTRINE TABLE in the code, not as a prompt instruction** — HQ: the
delegation layer (who is blocked, who has not replied, what waits on Jordan); a learning department: what
lesson is built, what is graded, what the learner still cannot do; a capital department: what is deployed,
what is idle, what the venue gate forbids; a broadcast department: which channels carry our services, which
are dead, what post is owed. **A prompt that says "reflect on your department" returns an essay; a table
returns four different, comparable reports from one binary.**

⚠️ **CROSS-CREDIT IS THE FIRST BUG IN EVERY DEPARTMENT WALK, and it is invisible because every report looks
full.** A single fleet-wide `…-completions.md` read for everybody makes all N walks print the *same*
improvement list — the learning seat credited with gateway work, the social seat with the queue migration.
**A walk that reports another department's work as its own improvement is worse than no walk: it is a false
attribution in the shape of a report.** Filter each line to those that name this department (and to lines
that name *nobody* else); **an empty list is the honest answer for a department that shipped nothing**, and
printing it is the finding.

**A department reads its own row in the fleet's shared lists before it reports.** Build queue, the human's
queue, pending, completed — the four lists already say what this department owes and what it is blocked on;
a walk that ignores them reports only what the seat remembered to write in its own lane.

**Three runnable scripts carry this skill; run them before hand-writing anything new.**

**A canonical copy of the per-seat instrument ships with this skill at `scripts/dept-reflect.py`** — copy it
onto a seat that lacks it (and into CORE) rather than rewriting it, so every seat measures with the same probes
and the same floor. **Its cron wrapper ships as `scripts/dept-reflect.sh` and must be copied too** — the wrapper
is where the seat path is resolved and where a findings-exit becomes a success, so a seat that gets the `.py`
without the wrapper re-inherits both bugs.

```bash
cd /opt/data
python3 profiles/<seat>/scripts/self-reflect.py            # HQ-only: estate config vs baseline
python3 profiles/<seat>/scripts/self-reflect.py --save     # store this run as the new baseline
python3 profiles/<seat>/scripts/tool-liveness.py           # EXERCISE the tools (exit 0/2/3)
python3 profiles/<seat>/scripts/dept-reflect.py            # ON the seat: its OWN department (§11)
python3 profiles/<seat>/scripts/dept-reflect.py --save      # store its baseline
sh      profiles/<seat>/scripts/dept-reflect.sh             # cron wrapper, silent when healthy
```

**`tool-liveness.py` is the one that would have caught every fault in this file's evidence section.**
It calls the STT provider, validates providers against the schema, flags billable fallbacks, and
reports a missing image key as `FAIL` — never `fine`. **A tool that is configured but dead produces
the same report as one that works: nothing. Exercise, do not read config.**

**Writing or fixing a probe? Read `references/writing-probes.md` first.** It carries the ways a probe
grades the wrong thing — verdict from the same number you print, bounded block parsers, label
collisions, proving one probe can go green, the stored baseline, the 0/2/3 contract, the distribution
probe class that drift checks systematically miss, **the User-Agent that makes a probe measure its own
blocking instead of the target**, and **the derived ratio above 100% that proves the classifier is
wrong**.

**Rules:**
- **Never report `fine` from absence of evidence.** A check that did not run is `UNMEASURED`.
- **A keyword match is not a fact.** `grep` for a word, then read the line.
- **Report the cost of each fault in the currency that applies** — tokens on a metered lane, silent
  failure of a user-facing feature, or a wrong number someone would act on.
- **Do not change routing, do not swap models, do not disable providers without asking.** This skill
  measures; Jordan decides.

## What to fix immediately vs. report

| finding | action |
|---|---|
| invalid provider value | **fix now** — it is silently broken, no decision needed |
| commented-out / missing credential | **report** — needs a key Jordan may have to supply |
| credential present but the API rejects it | **report with the error and the discriminator** — a file is not access; only the owner can mint a new one |
| vendor endpoint returning 5xx / paused | **not a credential finding** — say the vendor is down; do not propose a rotation |
| metered fallback armed | **report with the measured drain** — this is a spend decision |
| metered provider with a `:free` model | **not a finding** — it cannot bill; say so and move on |
| crons paying a model to run one command | **convert to `no_agent`** — free, and it removes a model from the failure path |
| crons that reason on script output | **not a finding** — that is the job working as designed |
| a preflight warning that prints on EVERY command | **not a finding until a capability test fails** — exercise the tool, record the drift, do not reinstall |
| surface disagreement | **fix the one that is wrong**, after checking the structure |
| a config change verified only by re-reading the file | **not verified** — read it back through the owning command, then confirm again after a restart |
| a metered label with `actual_cost_usd = 0.00` | **not a spend finding** — report the label, close the latent path, do not escalate a charge that never happened |
| a job whose output nothing downstream reads | **wire the consumer or retire the job** — a producer with no consumer is a feature that has never run |
| a monitor excused by a permanent out-of-service entry | **verify the excuse is still true, then give it an owner and an expiry** — a silent monitor and a correct one look identical |
| a probe job that reports `error` every run while its output reads correctly | **the exit code, not the job** — a findings exit is recorded as a crash; convert `2`→`0` at the wrapper and print the verdict |
| a wrapper that prints an alarm and exits `0` | **fix the failure branch to exit `3`** — a printed alarm with no code is invisible to health monitoring, and these jobs deliver to a file nobody opens |
| a job whose `last_status` is `delivery_failed` | **report it apart from `error`** — the work happened and nobody heard it; that is a transport fault, not a broken job |
| a per-seat instrument whose result is identical on every seat | **read the wrapper, not the script** — a hardcoded path re-points every seat at one seat |
