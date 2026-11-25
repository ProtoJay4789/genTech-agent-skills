---
name: use-what-we-have
description: "Use before building or claiming something is missing."
version: 1.0.0
author: gentech
license: MIT
tags: [doctrine, reuse, inventory, brain, preflight, fleet]
metadata:
  hermes:
    tags: [doctrine, reuse, inventory, brain, preflight, fleet]
    related_skills: [pre-change-impact-assessment, proving-a-negative, name-resolution]
---

# Use what we already have

**Jordan's directive, 2026-10-24, verbatim:**
> *"Before considering doing certain moves or doing certain things, why not consider what we have internally
> already, whether that be tools, skills, behaviors, check the brain… just more proactiveness."*

**Before you build, buy, adopt, or declare something missing — check whether it already exists.**

## When to Use

- About to write a new script, skill, tool, or service.
- About to say **"we don't have X"** or **"there's no code for this."**
- About to adopt a third-party thing to solve a problem.
- Evaluating a launch, rail, grant, or opportunity someone forwarded.
- About to **ask the user a question** they may already have answered.
- Any time the plan starts with *"we should build…"*

## The rule, in one line

**Inventory first, act second — and the inventory is a SEARCH, not a memory.**

## The five places to look, in order

| # | Where | What you are looking for |
|---|---|---|
| **1** | **The runtime/engine** (Hermes itself) | **A shipped feature that already does the job — check before building infrastructure** |
| **2** | **Skills** (`skills/`, CORE tree) | An existing procedure for this exact job |
| **3** | **Tools & scripts** (`scripts/`, `services/`) | Existing code that already does it |
| **4** | **The brain** (the vault) | **Prior research, prior verdicts, prior decisions — including decisions to STOP** |
| **5** | **The fleet** | Another seat may already own this lane |
| **6** | **The DEPLOYED estate** | **A live deployment that left no local trace — ask the platform, not the filesystem** |
| **7** | **The SHARED tree outside any profile** (`/opt/data/scripts/`, `/opt/data/skills/`) | **A fleet-canonical instrument. A profile-scoped search will NEVER find it.** |

**Place 7 is the one that manufactures a duplicate that looks original.** `/opt/data/scripts/` is where a
fleet-wide instrument lives so every seat runs the same code; `/opt/data/profiles/<seat>/scripts/` is where a
per-seat wrapper lives. **A search rooted at your own profile returns only the wrappers**, so the canonical tool
is invisible and the rebuild looks like a genuine gap.

```bash
# the shared tree FIRST when the subject is fleet-wide
ls -1 /opt/data/scripts/ | grep -i '<topic>'
grep -rn 'answer\|purpose\|WHY THIS EXISTS' /opt/data/scripts/*.py | head -20
# then your own profile, which holds wrappers rather than instruments
ls -1 <profile>/scripts/ <profile>/tools/ | grep -i '<topic>'
# then every seat's cron for a job that already runs it
for p in /opt/data/profiles/*/cron/jobs.json; do python3 -c "import json,sys;d=json.load(open('$p'));j=d if isinstance(d,list) else d.get('jobs',[]);print('$p',[x.get('name') for x in j if isinstance(x,dict)])" ; done | grep -i '<topic>'
```

**Measured:** a memory-trimming tool was written from scratch after grepping the seat's own `tools/` and
`scripts/`, which held no such thing. **The fleet already owned one** in the shared tree — measuring every
profile, reading each seat's configured caps, and running twice a day from another seat's cron. The rebuild
duplicated a working instrument and, worse, re-implemented a *design the fleet had deliberately abandoned* (see
the next rule). **The search root was the defect, not the search.**

**The brain is the one that gets skipped most, and it is the most expensive to skip — but the ENGINE is the
one that costs the most to miss, because missing it means hand-building infrastructure that already exists.**
**And place 6 is the one that manufactures false absences: a local tree can be empty while the product is
live in front of customers.**

## The engine is inventory too — check what the runtime already ships

**Before designing a mechanism, ask what the runtime provides.** The framework underneath an agent is a
first-class inventory item, and its feature set grows: what was absent when a workaround was built may be a
supported feature now.

```bash
hermes --help                     # the command surface — read it, do not recall it
hermes <command> --help           # every verb and its flags
```

**For anything the CLI does not name, read the feature index rather than concluding a feature is absent:**
the docs publish a generated one-line-per-feature index that maps a question to the page answering it.
**A negative answer about the engine is never safe from memory** — check the index or `--help` first.

**Measured:** a fleet hand-built a file-based multi-agent handoff mesh — lanes, watchers, ACKs, sweeps —
while the runtime already shipped a durable multi-agent task board. The board had been **initialised months
earlier and left with zero rows**: the feature was present, known enough to install, and forgotten. Every
fragility in the hand-rolled mesh (no durable ACK, work lost on restart, a handoff that evaporates) was a
property the shipped feature already solved.

- **Before debugging a hard problem in home-grown infrastructure, list the runtime's own commands.** One
  `--help` pass is cheaper than the audit that finds the gap later.
- **A stale setup is a signal, not a dead end.** Finding a half-configured artifact (an empty database, an
  unused config) means someone started down this road — read what is in it and why it stopped, before either
  adopting or discarding it.
- **Check the shipped feature's LIMITS as carefully as its features.** A capability that is single-host, or
  single-profile, may cover part of the fleet and none of the rest — say which seats it actually reaches
  instead of adopting it wholesale.

## A symptom that invites a mechanism redesign IS a build — inventory before you design

**When the user reports misbehaviour — "messages get skipped", "this doesn't queue", "the list is out of
sync" — the instinct is to design a better mechanism. That design is a build, and it is inventory-gated like
any other**, even though nothing in the request says "build". The engine answer is usually already shipped and
sometimes already correct.

- **Read the runtime's own source for the function the symptom maps to, before describing any mechanism.** The
docstring of the call that handles the case states what the behaviour actually is, in one sentence.
- **A shipped behaviour that turns out to be correct is the better finding.** "The transport is fine; I was
  mis-handling your message" is a real answer, and it is cheaper and truer than new infrastructure — say it
  plainly instead of defending the design you were about to propose.
- **Check the feature's live STATE, not just its configuration.** A toolset enabled in config with a database
  that holds **zero** rows is a feature that was installed and never used — that gap *is* the finding, and it
  is worth more than the mechanism you were about to write.
- **Prove it end to end on the real thing before recommending it.** Create one row, read it back, remove it.
  A configured-but-unused feature is a hypothesis until an artifact moves through it.

## ⚠️ An UPDATE invalidates your inventory — re-check the engine on a cadence

**The engine ships updates, and this fleet updates on a weekly cadence.** So *"we checked and it isn't
supported"* has a **shelf life measured in weeks, not forever.** A negative about the engine is a **dated**
claim: the answer can flip without anything on our side changing.

**The rule: after any engine update, re-run the engine pass on the things you previously worked around.**

```bash
hermes --version                                 # what are we actually running?
cat <vault>/00-HQ/UPDATE-AVAILABLE.md 2>/dev/null # is a newer image published?
curl -s https://hermes-agent.nousresearch.com/docs/llms.txt | grep -i "<your problem>"
hermes <command> --help                          # re-read the surface, do not recall it
```

**Search the feature index by the PROBLEM, not by the feature name you imagined.** You are looking for
something that does the job, and it may be named nothing like what you would have called it.

**Measured, one session, 2026-10-31 — three built-in features found only because someone asked "isn't there
something built in for this?" three separate times:**

| The problem we were hand-solving | What the engine already shipped | Cost of not looking |
|---|---|---|
| coordinating work across seats, durable ACKs | **Kanban** — durable board, atomic claims, survives restart | a hand-rolled file mesh with no durable ACK |
| reaching every agent from one desktop | **Multi-connection desktop** — many gateways side by side | we believed it was impossible |
| a session running on weeks-stale memory | **`/heartbeat` · `/goal` · `/loop`** | we built a monitor to watch the rot |

**All three were found in one afternoon, by asking — and all three had been available the whole time.**

### ⚠️ And know WHAT you cannot have, so you stop rebuilding it

The engine deliberately keeps **session-shape controls human-side.** Verify before you plan around the gap:

| Primitive | Kind | Agent-settable? |
|---|---|---|
| `hermes cron`, `delegate_task`, Kanban | standing job / work queue | **✅ yes** |
| memory writes, skills, vault notes | durable record | **✅ yes** |
| **`/new`** — fresh context | session control | **❌ human** |
| **`/heartbeat`, `/goal`, `/loop`** | session control | **❌ human** |

**A slash command is not callable by an agent, and no tool wraps it.** So a *propagation* problem (a fact a
running session must know) is solved by **delivering a turn** — a DM, a message, a cron that speaks — and
**never** by trying to restart someone else's context. Design the workaround on the right side of that line,
and say which side it is on when you propose it.

### The credential surface is the one most often rebuilt by hand

**Before building any "secret keeper", inventory the engine's own credential commands.** Jordan's rule, stated
before a keeper was designed: *"before we build one, let's see what tools we have built into Hermes."* The engine
shipped three tiers, and the fleet was using none of them:

| Shipped | Verb | What it solves |
|---|---|---|
| external secret manager | `hermes secrets {bitwarden,onepassword} {setup,status,token,sync}` | pulls credentials at process start instead of storing them in `.env`; `sync` reports what changed, `token` **validates before storing** |
| pooled provider credentials | `hermes auth {add,list,priority,refresh,status}` | rotates provider keys on exhaustion — the reason inference never has the drift problem |
| credential injection | `hermes egress {install,setup,start,status,reload}` | an egress proxy swaps a token for the real key, so the agent **never holds** the credential |

**The generalisable move:** when the problem is "secrets are unmanaged", the engine answer is a *command family*,
not a blank page. Read it before writing a `secret-set.py` — and if a bespoke tool is still justified, say which
shipped feature was rejected and why (offline host, provider not supported, needs a mount the engine cannot see).

## A dependency named in a README is not a dependency you are missing — PROBE it

**A requirements list describes what the code needs. It says nothing about whether you already have it.**

Measured: a verifier module sat unused for weeks because its own README required *"a backend exposing
token-level logprobs"*, and that sentence was read as a blocker. One request per candidate model on the
subscription **already in place** showed **two returned full logprobs and two returned `200` with the field
absent**. The capability was already owned; the blocker was a sentence nobody had tested.

**The cost of that error is not the delay — it is that it sends the user shopping for infrastructure they
already pay for.** A blocker you have not probed is an impression, and it spends their money.

**The probe is one call per candidate, and it classifies the RESPONSE, not the status:**

```python
body = {"model": m, "messages": [
    {"role": "user", "content": "reply with one word"}],
    "max_tokens": 8, "logprobs": True, "top_logprobs": 3}
#  field present        -> CAPABLE
#  200, field absent    -> NOT capable (the parameter was silently ignored, not an error)
#  error                -> unavailable / wrong model id
```

**Three rules:**

1. **Probe the capability, not the provider name.** Two models on the *same* rail differed on the same
   request. *"Our provider doesn't do X"* is a guess about every model underneath it.
2. **A `200` with the requested field absent is a NO.** APIs routinely ignore unknown parameters. Reading
   "no error" as "supported" is the same mistake as reading a status code as a business event.
3. **Name the exact call that would settle the blocker, then run it.** If you cannot write that call, you
   do not have a blocker — you have a hypothesis, and it is not allowed to cost the user anything yet.

**Expect the failure message to blame the wrong thing.** A missing per-request header can return
`400 {"type":"MissingSessionID"}`, which reads exactly like an auth or model-name problem. When a call
fails, **diff the request against the one that worked** (headers, body shape, parameters) before
theorising about credentials.

### And check the DEGRADED path — a graceful fallback can hide a dead dependency

**A library that substitutes a neutral value when its backend is missing will look like it is working.**
Measured: the same verifier returns `0.5 / 0.5` for every comparison when no logprob backend is reachable —
indistinguishable from *"these two candidates are equal"*.

**A result exactly equal to the fallback constant is a failure wearing a verdict's clothes.**

- **A smoke test must FAIL on the fallback value, not pass.** `if a == 0.5 and b == 0.5: FAIL("degraded")`.
- **Prove it discriminates, not merely that it responds.** Feed one clearly-good and one clearly-bad
  input and assert the scores separate. A tool returning the same number for both has told you nothing.
- **Also assert the direction.** A live backend that *prefers the worse answer* is a different defect
  from a degraded one, and folding both into "ran without error" loses the distinction.
- **Carry the backend that answered in the result** (`model_used`, `degraded`) so a neutral-looking
  answer stays traceable to its cause later.

## The DEPLOYED estate is inventory too — the filesystem cannot see a live site

**A local directory search proves what is on disk, not what is serving.** Pages projects, Workers, DNS
records, storage buckets and deployed functions live on a platform, and a project deployed from another
machine, an older laptop, or a dashboard click leaves **no local artifact at all.**

Measured: a plan was announced to build and deploy a hub because the pages existed only as vault files and
"nothing is on the domain yet". Enumerating the account showed the hub **already live** with real traffic —
several Pages projects and dozens of Workers, one of them serving the exact personal dashboard the plan was
about to rebuild, and already referencing a data file by the very name about to be written. The deployment
path existed, was working, and needed an update rather than a build.

**Ask the platform before you write the plan:**

```bash
# Cloudflare — the resource lists are the inventory
curl -s -H "Authorization: Bearer $CF" "https://api.cloudflare.com/client/v4/zones?per_page=50"
curl -s -H "Authorization: Bearer $CF" "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records?per_page=100"
curl -s -H "Authorization: Bearer $CF" "https://api.cloudflare.com/client/v4/accounts/$ACCT/pages/projects"
curl -s -H "Authorization: Bearer $CF" "https://api.cloudflare.com/client/v4/accounts/$ACCT/workers/scripts"
```

- **`dns_records` is a catalogue of intentions, not of contents.** A hostname with a record can still be
  serving `404`; a hostname with no record can be the one that matters. Read both the record set and a real
  request per name.
- **A DIRECTORY `404` is not an absence — probe the artifact URL.** Static hosts serve no index for a folder
  unless one was written, so `https://host/DeFi/` returning `404` says nothing about `DeFi/panel.html` sitting
  there. Measured: that directory `404` was read as "the page is not live" while the page itself answered
  `200` one path segment deeper — one command away from building a second copy of a working dashboard.
  List the deploy tree (`ls deploy/<site>/<area>/`), then fetch each **file** URL, not its parent folder.
- **A redirect is a live page.** Static hosts commonly answer `308` and land on an extensionless route
  (`/page.html → /page`), so a bare status check reads as broken. Follow it: `curl -sL -o /dev/null -w
  '%{http_code} %{url_effective}'`.
- **"Deployed" and "routed" are two different states.** A project can be live on its platform subdomain while
  its custom domain answers `404`. Check the custom names you actually publish, not only the default one.
- **Then diff, and prefer update over rebuild.** A live target turns the job from *create a home* into
  *update what is there* — which is smaller, safer, and preserves whatever the running version already gets
  right.
- **Never overwrite a live deployment blind.** If the deployed artifact cannot be listed, the update is a
  gamble: a missing file breaks a page that worked a minute ago. Read the current file list first, then push
  an addition rather than a replacement.

## The credential is not the capability — and a refusal from the API is often your URI's shape

**A credential is proven by the action it enables, never by an introspection endpoint or by a `404` that
really meant "wrong path".**

Two refusals that read like *"this token cannot do that"* and were not:

| What came back | What it actually meant |
|---|---|
| `user/tokens/verify` → `Invalid API Token` | **scoped/account-owned tokens fail introspection while working fine.** The zone list answered normally in the same breath |
| `pages/projects` → `10404 No route for that URI` | **the path was missing `/accounts/<id>/`**, not the permission. The account-scoped path answered on the first try |

**Before reporting "we lack the permission", check the URI SHAPE against the API's own resource hierarchy**
(zone-scoped vs account-scoped), and prove the capability by calling the resource you intend to use. A
permission verdict delivered from the wrong URL sends the user to re-issue a credential they already hold.

## Why this exists — the measured cost of skipping step 3

Five wrong conclusions in one session, **every one refutable by a file already on disk:**

| Claim | What the brain already held |
|---|---|
| `agent-credit-score` is *"the one asset nobody else has"* | The vault folder holds **one `thumbnail.html`, 16 KB, no code** |
| The bridges are *"unwired"* | The scripts are **absent entirely** — the claim came from a stale summary line |
| *"Nobody does cross-protocol allocation"* | **A prior verdict on Yield Yak was already written** — plus the competitor's own site |
| The `~$0.20` funding gap blocks liquidation | Two **unrelated** gaps chained; the real figure was ~$2, and on a different chain |
| *"The drift checker has a blind spot"* | The checker **worked**; the output list was sliced at six |

**Every one was a missing search, not a missing fact.** The information existed. The *look* did not happen.

## Make it checkable — "be proactive" is not a rule

**A real search has a command, a result, and a stopping condition.**

```bash
# Before asserting "we don't have X":
grep -ril "<the thing>" /opt/data/.obsidian-vault --include="*.md" | head
grep -ril "<the thing>" /opt/data/services /opt/data/scripts 2>/dev/null | head
ls -1 /opt/data/profiles/*/skills/**/*<topic>* 2>/dev/null | head
```

**Stated as a claim anyone can attack:**
- ✅ *"I searched the vault for `credit` + `score`, `scripts/` for a scorer, and both trees for the skill —
  the only artefacts are a thumbnail and a README."* — falsifiable.
- ❌ *"We don't really have anything for that."* — an impression wearing a finding's clothes.

## ⚠️ You search for the name of the thing you are about to build — not for the record that exists

**The most common false absence is not a bad search. It is a search for the name of the NEW file, which by
definition did not exist yesterday.** Measured twice in one night: a seat building `post-log.py` searched
`*post-log*` and declared "no post record" while a `post-log.csv` with three real publications sat in the vault
— its new ledger opened at `published 0`; and a live-path grep for a monitor's vocabulary returned zero, so HQ
reported the job "gone" while two working artifacts sat in the recovery snapshot.

1. **Search for the RECORD and the BEHAVIOUR, never for your planned filename** — the concept, the columns you
   would expect (`url`, `published`, `posted`), and the suffix (`*.csv`, `*.jsonl`).
2. **Search every ROOT, including archive and recovery trees** (`recovered-*`, `10-Archive/`, `_archive/`).
3. **A new record that starts at ZERO beside an existing one is a REGRESSION, not progress.** Print the existing
   rows and state the delta before creating a ledger, register or index.
4. **Grep the VENDOR / DATA-SOURCE name across `scripts/` before writing any client.** Integrations are named
   after the third party, not after the feature: a new `flow-desk`/`client.py` will not match, but
   `ls scripts/*<vendor>*` and `grep -ril '<vendor>' scripts/` find the client that already talks to it.
   Measured: a second API client was written for a provider whose working, live-verified client had sat in
   `scripts/` for two days — the vendor-name grep would have returned it in one line.

**Depth — the four other ways a negative gets invented (wrong namespace, truncated slice, stale status table,
remembered path): `references/false-absence-searches.md`.**

## The stop condition — when you may say "it doesn't exist"

**A negative needs a COMPLETE probe. Absence from a subset is not absence.**

- Search the **whole** relevant source, not the first page, the first directory, or the first `[:N]` slice.
- **Check every namespace** — a 404 from one (a user account, an org, a target) is not a negative about the others.
- **Read the tool's own output code** before concluding a tool missed something. A truncated list renders
  exactly like a complete one.
- **A stale summary is not a source.** If a document says a file exists, **open the file.**
- **Search by FILENAME across the tree ROOT, not by the path you remember.** A correct filename under a
  parent you mis-remembered produces a clean, confident "missing". Measured: council channel art was
  reported absent from `Design-Assets/x402-council/`; the files were real, at
  `10-Labs/Design-Assets/x402-council/` — one path segment away. `find <root> -name '<file>'` is the probe;
  the remembered path is the hypothesis.
- **A document's own status table is a DATED measurement, not current state.** Inheriting a row from a plan
  re-publishes an old absence as a present-tense fact. Measured: "`06-Content` has zero files" came from a
  table measured two weeks earlier; the folder held eleven files. Re-run the row before repeating it, and
  when you correct one, mark the table superseded rather than deleting it — the old row is the evidence the
  thing was later built.

## A question on the user's list is not an unanswered question

**Before you put a question back to the user, search the brain for the answer.** An item survives on a queue
because it was **filed**, not because it is **unresolved** — the record may already hold the verdict, and the
item may be waiting on something else entirely (an action, not information).

**Measured:** a question about a benefits/voucher rule was handed back to the user as a five-minute task —
and the brain already held the *verified wording* plus a recorded plan built on it. The user's correction was
to look first. **Re-asking a resolved question teaches the user that their queue is noise**, which is the
opposite of what a queue is for, and it costs the trust that makes the queue read at all.

**The check is the same inventory grep as any other step 3:** search the vault for the subject *before*
writing the question. If the record holds a verdict, **report the verdict and what actually remains open**
(often nothing, or one genuinely new detail) instead of re-opening the whole question. And when a question
does survive, make the *remainder* explicit — "we settled X yesterday; the open piece is Y" — so the user can
see their own work was not ignored.

## When you find it, EXTEND it — do not write the sibling

**Finding the existing implementation only solves half the problem. The other half is resisting the urge to write
a better one beside it.** A new module that re-implements an old one's job (a transport, a guard, a formatter) is
the same defect as building from scratch, one step later — and it is worse, because now two things claim the same
authority and nobody declared which wins.

**Measured:** a compliance module was written with its own HTTP transport beside an existing guarded client that
already had budget checks and throttle handling. Both worked. Neither was wrong on the day. The older one wins by
accident the first time a caller imports it, and from then on every fix has to be made twice and silently does not
apply where it is not.

**The shape that survives: a FAÇADE.** New rules live in a thin module that re-exports the existing one and adds
only what was missing:

```python
_guard = _load_existing()          # import the established implementation, do not re-implement it
def get(path):                     # re-export its behaviour
    return _guard.get(path)
def write(...):                    # add ONLY the new rule
    ...
```

- **One transport, one place to fix.** If a second copy exists, deleting it is the fix — not syncing it.
- **Say which one is authoritative** in the module docstring, so the next agent imports the right thing without
  reading two files.
- **A rule duplicated across two implementations is a rule you no longer have** — you have two opinions, and the
  one that runs is whichever the caller happened to import.

**The check before writing a new helper: does something already perform this exact job? If yes, the new file is
probably a patch, not a module.**

### A refused overwrite IS the inventory check firing — read the file, do not work around it

**When a write is refused because the target already exists, that refusal is the cheapest inventory result you
will ever get: it names the thing you were about to rebuild.** The reflex is to route around it — pick a new
filename, write to a scratch path, add a suffix. Every one of those turns a caught duplicate into a live one.

**Read the existing file instead, and expect it to be better than your draft.** Measured: a cost model was
about to be written for the third time; the refused overwrite pointed at the file, and it already held the same
arithmetic *plus* the operator's own recorded rule for when the answer should be WAIT — a rule the draft did not
know existed and would have contradicted. The draft was not a worse tool, it was a tool missing the one thing
that made the existing one trustworthy.

**How to read the refusal:**

1. **`read_file` the target, whole.** Not the head — the header docstring is where the tool states the question
   it answers and the decisions it refuses.
2. **Look for the NEGATIVE clauses.** `does NOT`, `never`, `deliberately` — those are verdicts from a previous
   session and they outrank your idea for the same reason a written protocol does.
3. **Then choose: EXTEND, MERGE, or a genuinely new instrument.** Writing beside it is only correct when the
   existing tool answers a *different question*; say which, in one sentence, before you create anything.
4. **If you do write a second file, name the authoritative one** in both docstrings, so the next agent imports
   the right thing without reading two files.

**A guard that stops you is not an obstacle between you and the work. It is the work, arriving early.**

### Before adding an INSTRUMENT, list the QUESTIONS the existing ones answer

**Monitors, checkers and reporters are the worst place to skip the inventory**, because two of them can do
overlapping work while sharing not one word of their names. A filename grep finds nothing; the fleet looks
covered and is double-covered.

**The move: read each existing instrument's own header docstring, not its filename.** A good monitor states
the question it answers in its first paragraph — that sentence *is* its contract, and it is greppable.

```bash
# what question does each existing job answer?
grep -rn 'answer\|question\|Purpose\|purpose\|Header' <scripts-dir>/*.py | grep -i 'answer\|purpose' | head -20
```

**Measured:** a new every-6-hours watcher was built for "are we listed, and has a stranger paid?" while an
existing presence check **already owned the first half** — its own header named the exact failure it existed
to catch. The duplicate was invisible because neither name contained the other's words. The existing job had
also been working correctly the whole time; the new one added one genuine surface and 90% redundant polling.

**The one-sentence test, before writing any instrument:** write the sentence *"this job answers: ___"*.
If an existing instrument's header contains that sentence, **it owns the question** — extend it, do not
create a rival.

### ⚠️ "We deliberately do NOT do X" in an existing header is a DECISION, not a gap

**A docstring that names an abandoned behaviour is the most expensive sentence to skip, because it reads like
an absence and is actually a verdict.** When an instrument says *"the original did X and was replaced because
X destroyed something"*, **rebuilding X is not an improvement — it is a regression with a clean conscience.**

**Read the negative clauses, not only the positive ones.** A good header carries both: what the tool does, and
what it refuses to do and why. The refusal is usually the part someone learned the hard way.

**Measured:** a rebuild auto-trimmed a record by *score* — a numeric proxy for the position of an entry in the
file. The existing fleet instrument's own docstring said, in as many words, that it **never rewrites the file**
because *"the original trimmed by position … the cut lines are exactly the ones the agent would have kept"*.
The rebuild was that original, rewritten by someone who had not read the sentence. It then deleted
user-preference entries the fleet's written protocol listed as **never delete** — the exact failure the existing
design existed to prevent.

**Three checks before writing any tool that MODIFIES durable state:**

1. **Grep the existing instruments for `NEVER`, `does not`, `deliberately`, `refuses`.** Those lines are the
   design contract; violating one is not a feature.
2. **A rebuild that changes WHO decides is a different product**, not a better version. If the existing tool
   deliberately leaves a judgement to a human, an automated replacement has removed a human, not added speed.
3. **Diff your proposed deletion rule against the written protocol's protected categories** (preferences,
   corrections, identity, wallet rules). If your scoring can rank a protected category last, your scoring is
   the defect — a protection that a heuristic can outvote is not a protection.

**When you find a partial overlap, the answer is neither "keep both" nor "replace":**

1. **Merge the genuinely new surface INTO the owner** (one job, one question, one place to fix).
2. **RETIRE the copy** — delete its schedule *and* archive the script, so a second copy cannot quietly drift
   back into use. Deleting the cron while leaving the script runnable produces a future session that re-arms it.
3. **Say which one is authoritative** if any trace of the retired one remains.

**A half-duplicate is worse than a duplicate.** Two instruments answering adjacent questions diverge on the
first change to either, and then the fleet has two contradictory numbers and no rule for which is true.

**And a monitor's coverage is a claim like any other: "we already check that" needs the header read, not a
filename remembered.**

## Pitfalls

- **Treating prior work as settled because it is written down.** A documented value is not a measured one —
  **put it through the tool before building on it.** Prior research answers *"what we decided"*; it does not
  answer *"what is true now."* **Both are needed; the record comes first.**
- **Reading the decision and missing the reason.** Prior verdicts often carry a *"do not use X"* on grounds
  that no longer hold — and, just as often, grounds that still do. **Read the why, not only the what.**
- **Searching for the *solution* instead of the *problem*.** Search for what the thing DOES. The answer may
  live under a name you did not guess — which is why the search is by behaviour, not by title.
- **Skipping the inventory because the build is small.** Small builds are where the duplicate lives.
- **Inventory as a ritual.** A search you did not read the results of is not a search.

## Related

- `pre-change-impact-assessment` — the wider "before a big change" pass.
- `proving-a-negative` — how to state an absence honestly.
- `name-resolution` — verify the name before reasoning from it.

## Learned on gentech (merged 2026-11-24)

> Promoted verbatim from the seat that learned it. Kept separate on purpose: this is a second writer's evidence, not a rewrite of the section above.

## A task waiting on the USER is a claim about their state — check it before re-serving it
**The sibling of the question rule, and it costs the user's attention rather than yours.** An item in their
queue asserts *"you still have to do this."* If nobody has checked, it gets re-copied into every report and
hardens into fact.
**Measured:** "register with vendor X — needs your email and name" was carried on the pending list across two
reports, and it had already been done: the catalogue held **17 of our rows**. The registration had happened, the
name and email were used, and the only thing that survived was the note. The user had to ask *"didn't I already
give you that?"* — which is the whole cost.
- **Check the third party's own record, not our note about it.** A catalogue, account page or API answers
  *"is this done?"* in one call; the note answers only *"did someone once think it was needed?"*
- **A queue item that names an ACTION is verifiable; one that names a MISSING THING is not the same claim.**
  "Needs their email" is testable against their own listing; "needs better positioning" is not, and should not be
  filed in the same list.
- **When you find a queue item already done, say so and close it — do not silently drop it.** The record that a
  task was thought open and turned out closed is what stops it being re-filed next week.
- **The inverse also holds:** a task marked done by our own note is a claim about *our* side, and the same check
  decides it. Both directions are one lookup.

