---
name: agent-load-path-audit
description: "Use when auditing what an agent loads at session start."
version: 1.0.0
author: Gentech
license: MIT
tags: [startup, context, memory, skills, wake-up, audit, verification]
metadata:
  hermes:
    tags: [startup, context, memory, skills, wake-up, audit, verification]
    related_skills: [wake-up-protocol, session-hygiene, memory]
---

# Agent Load-Path Audit

An agent's rules are only as good as what reaches its context. This skill is the **audit** of that path,
not the routine: the wake procedures tell you what to READ, this one tells you how to verify that
anything reads it at all — and which layer is silently failing.

## When to use

- An agent seems to have "forgotten" its identity, rules, or routing.
- After a migration, host wipe, or a long gap between sessions.
- When asked directly: *"do you actually load the rules/skills/brain we set?"* — answer with measurements,
  not reassurance.
- Before trusting a wake-up procedure someone wrote, and before blaming an agent for ignoring one.

## The load-path map — what actually arrives

For a normal session, exactly three things are in context before the first turn:

| arrives automatically | does NOT arrive |
|---|---|
| the seat's own `MEMORY.md` + `USER.md` | **skill bodies** — only name + description; a body appears only when `skill_view` is called |
| the skill list (names + descriptions; a couple hundred skills ≈ 5k tokens) | **the knowledge vault / second brain** — nothing auto-loads it; routing to it is a deliberate act |
| the system prompt / base identity | **any session-start procedure that is itself a skill** — it does not run itself |

Two corollaries that decide most of these investigations:

- **A long session can also DROP skill bodies it had already loaded** (they resurface as a
  `[SKILL_PRUNED]` marker). Re-load a skill before acting on it rather than trusting recall.
- **"It is in the vault" and "the agent knows it" are different claims.** Unwritten knowledge is not
  merely unavailable, it is invisible — nothing reports its absence.

## The audit, layer by layer

Measure each of these; each one caught a real defect when run for the first time.

**1. Identity file — size and content, against the expected version.** A file that *exists* proves nothing.
An identity file whose body is the vendor's generic default prompt is a stub, not an identity; compare its
size and content against the recovered/known-good version rather than confirming that the path exists.

**2. Every generated context file — mtime first.** A file described as "regenerated nightly" is only fresh
if the job that regenerates it still exists. Check both: if the generator is gone, the file ages silently
and **a stale copy reads exactly like a current one**. Treat anything older than its stated period as absent.

**3. The procedure's own paths — test each one before following the steps.** Grep the wake procedure for
every path it tells you to read and confirm each resolves in the CURRENT layout. Procedures outlive the
filesystems they were written on: a layout migration leaves them pointing at trees that no longer exist,
and an agent that follows the steps hits missing files at every one.

**4. The trigger — the document is not the invocation.** A procedure that says it runs "automatically on
every session" is automatic only if its **separate trigger package** is installed. Verify the package
(e.g. that an auto-wake skill and its marker file exist) rather than reading the claim. If the trigger is
missing, nothing runs it — not a restart, not a new session, not a compaction.

**5. The memory files — read them as RULES, not as notes.** They load into every single turn. Scan them
for statements that are no longer true; see the failure class below, which is the most expensive defect in
this whole area.

**6. Supporting scripts the procedure calls.** Any helper the procedure names (a context-save generator, a
watcher) must be present; if a generator is gone, say what the durable artifact is and produce it by hand.
A bridge/capture is a FILE, not the script that writes it.

**7. The LIVE session's stored prompt — the rule you wrote is not the rule it runs.** Identity and context
files are snapshotted into `system_prompts` and referenced from `sessions.system_prompt_hash`; the row the
agent actually runs is that stored prompt, not the file on disk.

- **An edit to `SOUL.md` changes nothing for a running session until its prompt is rebuilt:**
  `hermes sessions refresh-prompts -p <seat> --session <sid>` — history is kept, one prompt-cache miss, and
  **the rebuild lands on that session's NEXT turn**, so checking before a turn shows the old prompt and is
  not evidence the rebuild failed.
- **Read the stored TEXT, never the hash.** A new `system_prompt_hash` proves a rebuild happened; only the
  section string proves the rule is inside it. Grep the newest `system_prompts` row for the heading you
  added (`.lower().count("english")`, `"non-negotiable" in p`).
- **A stored prompt missing exactly one section of a file that contains it is a stale snapshot, not a
  filter.** Diff the newest prompt text against the file on disk (`difflib.SequenceMatcher`) and read which
  side is behind — then check the file's mtime against the session's `started_at`. Concluding "the loader
  drops this section" from that diff is a wrong theory about a clock.
- Recipe, read-only, no agent tool needed:
  `sqlite3 profiles/<seat>/state.db "select system_prompt_hash from sessions order by started_at desc limit 1"`
  then `select prompt from system_prompts where hash like '<prefix>%'` and grep it.

**8. Drift symptoms — measure per seat before naming a cause.** When one seat misbehaves and the others do
not (wording, tone, language), count the symptom in each seat's OWN message store — e.g. regex the CJK range
`[\u4e00-\u9fff]` over each profile's recent `assistant` messages in `state.db`. When N−1 seats on the same
model return 0 and one returns 13, **the model is not the variable and the config diff is**. A per-seat count
turns "it sometimes does X" into a named seat, a named window, and a before/after you can re-run.

## Measure USE, not just load — the tool mix is a log readout, not an opinion

"Are the agents actually using the skills and tools we gave them?" is answerable in one pass from each
seat's `logs/agent.log`, and the answer is usually three different answers per tool class:

```bash
# per seat: what actually ran, ranked (the completion marker, not the word)
grep -oE '(\w+) completed \(' logs/agent.log | sed 's/ completed (//' | sort | uniq -c | sort -rn | head -14
```

- **Count the COMPLETION marker, never the bare tool name.** A tool's name appears in prompts, skill
  bodies and error text; `grep -c skill_view` counted a *higher* number than the real calls because it was
  matching prose. `skill_view completed (` is the invocation.
- **State the window.** The log covers one session's lifetime (or whatever rotation is configured), so report
  "N calls over these dates", never a bare count that reads as all-time.
- **Report the mix as a ratio, and interpret each class separately.** A high `skill_view` share with a low
  `web_search` share is not one story: skills loading often means the index is doing its job, while a near-zero
  web count means either the answers come from measured commands (good) or the destinations block this host
  (a gap, not a habit) — say which, because the same number supports both readings.
- **The per-turn cost of the shelf is the INDEX, not the library:** `sum(len(name) + len(description))` over
  every skill ≈ what is injected before the first turn. Quote that number, not the total bytes of all
  `SKILL.md` files (which load only on demand) — and not the count, which says nothing about cost.
- **Cross-seat comparison needs the same window per seat**, and a quiet seat is not a broken one: the newest
  seat will show a fraction of the calls. Rank by rate, not by total.

## Failure classes (each with its rule)

**A rule that loads but is WRONG is worse than a rule that is missing.** A stale memory entry is injected
into every turn and quietly steers every answer, and it reads exactly as confident as a correct one.
*Fix it the turn you find it.* Never leave a known-false entry for a later review — "later" is thousands of
turns of bad steering.

**Stale generated context presents as live.** Any auto-generated summary needs a freshness gate and its
own measurement timestamp; without one, age is unobservable at the point of use. Prefer durable sources
when the summary is old, and say that you did.

**A missing trigger is indistinguishable from a lazy agent.** Before concluding a seat ignored a procedure,
check whether anything invokes it. "Never ran" and "ran and was ignored" need different fixes.

**Rote path references rot silently.** A procedure with dead paths fails at step 1 and looks like the agent
refusing to work. Test paths, then fix the procedure — not the agent.

**Loaded-then-pruned bodies.** After a long session, re-load the skill instead of trusting that a body is
still in context.

**A rule that lives in one seat's prose is absent everywhere it was not retyped.** Per-seat identity files
are independent copies, so a fleet-wide rule written into `SOUL.md` exists only on the seats someone edited
by hand — a seat provisioned later inherits nothing, and the resulting behaviour reads as a model defect.
When you find a seat missing such a rule, **do not fix only that seat**: encode the invariant as a CHECK that
names every seat missing it (walk `profiles/*/config.yaml` as the seat population, regex the required
sentence), schedule it, and prove it with a throwaway fixture seat carrying no rule — created, flagged by
name, deleted, silent again. A rule you cannot enumerate is a hope.

**A rule that must fire on an UNBIDDEN observation cannot live only in a skill.** Skill bodies load when
something MATCHES their trigger; a rule shaped *"whenever you happen to see someone else's repository, do X"*
has no trigger phrase, so a skill carrying it is never loaded at the moment it is needed. **Placement decides
whether a rule fires:**

| the rule is… | lives in | because |
|---|---|---|
| always-on conduct, gates, "never/always X" | the seat's `SOUL.md` → its always-loaded rules section | injected every turn, needs no trigger |
| a procedure for a recognised task | a skill body | loads on its trigger, keeps the prompt small |
| both | the RULE in `SOUL.md`, the DEPTH in the skill | the prompt stays cheap and the rule still fires |

**Pushing one rule fleet-wide — order matters, and the copy you edit is not always the one you think:**

1. **Find the canonical copy first, and do not assume it is the newest.** A "shared core" tree can be STALER
   than a seat's own copy if a seat was edited without promoting up. Measured: the core held an older, shorter
   revision of a skill while the seat held the longer current one, so the core had to be refreshed FROM the
   seat — not the reverse. **Grep the core for the very rule you just added; zero hits means the canon is behind**
   and any "synced to all seats" claim built on it is false.
2. **Write it once, in one canonical wording**, then copy that exact text everywhere. Retyping per seat drifts
   the wording, and a checker that greps for the original then names compliant seats as missing it.
3. **Add the standing rule to every seat's always-loaded section** — `SOUL.md` → its rules list. A seat without
   that heading has an equivalent ("the lines that do not move", non-negotiables); extend that rather than
   inventing a second list beside it.
4. **Refresh prompts:** `hermes sessions refresh-prompts -p <seat>` with no `--session` refreshes EVERY session
   in the profile and reports the count. The rebuild lands on the next turn, so checking before a turn is not
   evidence that it failed.
5. **Prove it by ASKING, not by grepping.** A grep of `SOUL.md` proves the file says it. Ask the seat a cold,
   narrow question and require the answer to reproduce the rule's substance unaided. **That is the only check
   that distinguishes a rule in a file from a rule in an agent** — and it is cheap: one turn per seat.

**A fact that was true on ANOTHER seat.** The tell is a stored rule containing another profile's path
(`/profiles/<other-seat>/scripts/`, another seat's `secrets/`, another seat's cron dir): it loads every turn
and points at files that do not exist for the reader. When copying a procedure between seats, rewrite every
path for the destination seat and re-measure any number in it — a borrowed rate limit or directory count is
a measurement of the seat it came from. Flag these rather than asserting: a checker can name the mismatch,
only the owning seat can confirm what its own value is.

## Reporting

State the result as measured, per layer, with what was checked — plus the ONE gate that blocks the rest.
"Partly, and the parts that fail are X and Y" beats either reassurance or a survey of possibilities. If the
natural home for a fix is a skill you do not own, say so and recommend adoption rather than silently
editing around it.

## Related

The wake routine itself (what to read, in what order) and session hygiene (when to save and start fresh) are
separate PROCEDURE skills. This skill audits whether they can work; if one of them carries wrong paths or
an unverifiable trigger, correct it in place — and if it is user-owned, report the defect and recommend
`hermes curator adopt <name>` instead of appending an "update" note underneath it.

**Absorbed:** `agent-context-load-audit` — its full body and references now live at `references/agent-context-load-audit/agent-context-load-audit.md`. Do NOT re-create `agent-context-load-audit` as its own skill: it is this one.
