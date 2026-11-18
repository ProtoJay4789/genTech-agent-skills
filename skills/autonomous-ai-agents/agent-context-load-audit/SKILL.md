---
name: agent-context-load-audit
description: "Use when checking what an agent actually loads."
category: autonomous-ai-agents
trigger:
  - "do you actually load our rules"
  - "do you load the brain"
  - agent behaves generically after a rebuild
  - after a host migration or disaster recovery
  - after creating or cloning an agent profile
  - a house rule exists in writing but is never followed
  - fleet reports healthy but ignores its own conventions
version: 1.0.1
author: Hermes Curator
license: MIT
tags: [context, identity, memory, skills, audit, rebuild, multi-agent]
metadata:
  hermes:
    tags: [context, identity, memory, skills, audit, rebuild, multi-agent]
    related_skills: [agent-fleet-health-audit, handoff-mesh, wake-up-protocol]
---

# Agent Context Load Audit

## When to Use
- After ANY rebuild, host migration, disaster recovery, or profile clone
- When an agent behaves generically, or ignores house rules that are written down somewhere
- When asked directly: "do you actually load our rules / skills / brain?"
- Periodically, as a fleet check — this failure class is INVISIBLE to process health checks

## The distinction that makes this necessary
**"Exists on disk" is not "loads".** Every process can be green, every cron registered, every file
present — and the agent still injects no identity, no rules and no usable skill bodies. Silent
degradation emits no error, no crash and no log line, so it never appears in a health check. Audit the
load path as its own axis, separately from the process layer.

## Procedure

### 1. Name the layers, and which of them are always-on

| layer | when it loads | how it fails |
|---|---|---|
| identity file (the profile's `SOUL.md`) | every turn, injected as the system prompt | silently replaced by the stock/default prompt |
| memory files (`MEMORY.md`, `USER.md`) | every turn | stale or false entries, followed as rules |
| the skill LIST (names + descriptions) | every turn | — |
| skill BODIES | only when actually read | never read, or pruned mid-session by compaction |
| the knowledge base / vault | nothing, unless something routes to it | no automatic load at all |

Report per layer. "I load the brain" is a vague claim until you have said which layer, from which path,
and how you verified it.

### 2. Identity — is the real file injected, or the stock stub?

```bash
# a match means the generic prompt is what the agent is running on
if grep -q "You are Hermes Agent, built by Nous Research" "$PROFILE/SOUL.md"; then
  echo "STOCK STUB — no identity is loading"
else
  echo "real identity injected"
fi
```

- **A stub is the DEFAULT state** after a rebuild, restore or clone — not evidence that no identity
exists. The authored identity usually survives somewhere else (the knowledge base, a starter template,
another seat). **Search for it before authoring a replacement**, or you will ship a thinner identity
than the fleet already had.
- **Install direction:** copy the authored file over the profile's `SOUL.md`. Back up the stub first —
you are changing what loads on every single turn.
- **Truth-pass it during the install.** An authored identity outlives the host it was written on, so it
carries dead absolute paths and claims about machinery that has since changed. Correct what is provably
false; mark what you cannot verify as unverified. Then re-verify the file's bytes.
- **It takes effect at the NEXT session start** (the prompt is assembled then). Verify the file, never
the current turn's behaviour.
- **Check EVERY seat.** The event that reset one profile usually reset all of them — and a seat running
on the stub cannot report that it is on the stub.

### 3. Always-on files that are stale — the "auto-generated nightly" trap

A file documented as auto-generated is only as fresh as its generator. Check the generator still exists:
1. List the registered scheduled jobs and look for the one that claims to write the file.
2. If it is not registered, the file is **frozen at its last write** — report the age, with a timestamp.
3. If it is registered, compare the file's mtime against the claimed cadence.

A stale context file is worse than a missing one: it reads as current, so it silently steers decisions.

### 4. Skill bodies — present is not available

Only names and descriptions are always-on. A body must be **read** to be in play, and a body already
read can be dropped by context compaction mid-session. Before acting on a procedure you "already
loaded", confirm it is still in context — if a marker says the content was lost, re-read it before
relying on it.

### 5. The retrieval index — diff it against reality

A routing/index file that names folders or paths which no longer exist makes retrieval fail quietly: it
degrades to a full scan, or routes nowhere and reports nothing. Diff the index's entries against what
exists, and fix the index in place — an index that lies is worse than no index, because it is trusted.

### 6. Report the load state, not the file state

```
LOAD AUDIT (<as-of UTC>)
identity:  loaded | STUB — no identity injected        evidence: <path, bytes, check result>
memory:    <n>/<cap> per file | stale or false entries found and fixed: <list>
skills:    list loaded; bodies on demand; bodies that required re-reading: <list>
index:     <n> entries, <n> of them naming non-existent paths
seats:     checked <n>; <n> running on the stub
```

## Rules
- **"The file exists" is not "the file loads"; "the process runs" is not "the agent knows who it is."**
- **A rule that loads every turn and is WRONG is worse than a missing one, because it gets followed.**
  Fix it in place the instant it is found — never append a correction beneath the wrong sentence, never
  defer it to a later pass.
- **Verify the load, not the intent.** An identity file, a memory entry or an always-on index is
  *executed context*. Check its claims against the present environment before trusting them.
- **Nothing loads the knowledge base for you.** If the design is "load your slice, know the index",
  then the index must actually be read at wake — and the index itself must be true.
- **Absence of an error is not evidence of a load.** Every finding here has to come from reading the
  injected artefact, not from the absence of complaints.

## References
- `references/skills-distribution-contract.md` — one CORE, N seats: how a skill edit must travel
  (promote before sync), the guards a distribution tool needs, and why a seat-only skill is a
  contribution rather than garbage.
