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
`0/2/3` exit code — or the conversion turns a summary into raw noise.

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

---

## Reporting

**Verdict first, then a scorecard, then the one thing to fix.**

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

**Two runnable scripts carry this skill; run them before hand-writing anything new.**

```bash
cd /opt/data
python3 profiles/<seat>/scripts/self-reflect.py            # measure + diff vs the stored baseline
python3 profiles/<seat>/scripts/self-reflect.py --save     # store this run as the new baseline
python3 profiles/<seat>/scripts/tool-liveness.py           # EXERCISE the tools (exit 0/2/3)
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
