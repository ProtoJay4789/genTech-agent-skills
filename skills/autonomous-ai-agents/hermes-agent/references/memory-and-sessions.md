# Memory & Sessions

**Load when:** a seat forgets something it just saved, memory is near its cap, an agent "feels
dumber", or you are deciding where a durable fact belongs.

## The two stores

| File | Holds | Limit |
|---|---|---|
| `$HERMES_HOME/memories/MEMORY.md` | the agent's own notes — environment, conventions, lessons | 2,200 chars |
| `$HERMES_HOME/memories/USER.md` | the user profile — identity, preferences, expectations | 1,375 chars |

Both are **per profile**: `profiles/<name>/memories/`. A CLI session in the default profile and a bot
on another profile do **not** share notes.

**Never point two processes at one Hermes home.** Memory writes are automatic and load back at session
start, so two writers compound each other's entries into state neither of them (nor the user) authored.
If two agents need shared memory, that is an external memory provider — not a shared home.

## ⚠️ The frozen snapshot — the rule that costs the most

Memory is injected into the system prompt **once, at session start**, and that block **never changes
mid-session**. Writes persist to disk immediately; the *injected* copy does not update until the next
session starts. This is deliberate — it preserves the LLM's prefix cache.

**Consequences, and they are large on a gateway:**

- A mid-session save is **real and confirmed** (tool responses show live state) but **invisible to the
  session that made it**. The value still works inside the current conversation; it becomes
  systematically available only from the next session onward.
- **On a messaging platform a session can run for weeks.** Gateway chats deliberately survive restarts,
  gateway crashes and reboots, so "frozen for weeks" is the *normal* state, not an edge case. A seat can
  be answering from a snapshot older than everything it has learned since.
- **The fix is a session boundary, and on a gateway that boundary is the human's to create.** Run `/new`
  at natural boundaries — a finished task, a change of topic, **the start of a day**. Each boundary is
  when memory pays off: the agent re-reads the updated snapshot, starts from a cheap short context, and
  reaches for `session_search` only when it needs history. On the CLI this is automatic (every
  invocation is a new session); on a gateway **nothing triggers it**.
- **Fresh memory is invisible to every OTHER already-running session too.** A broadcast to the fleet
  does not reach an awake seat. The durable channel is a file; the wake-up is a restart or a DM — and a
  seat that never restarts never re-reads.

### What an agent can and cannot do about it

`/new`, `/heartbeat`, `/goal` (Persistent Goals) and `/loop` are **all slash commands** — session-shape
controls deliberately reserved for the human. An agent **cannot** set one for itself or for another seat,
no matter what it claims, and no built-in refresh mechanism exists or can exist (the freeze is what keeps
the cache valid). What an agent *can* schedule: `cron`, subagent delegation, and Kanban. So a seat cannot
un-freeze itself — un-freezing is either the human's `/new` or an inbound turn.

### The injected block is frozen; the conversation is not

A **delivered message reaches the live session immediately.** A DM, a cron delivery, any inbound turn
arrives as a *new user message* and is read at once, even when the memory block beside it is days old.
That makes a **delta DM a real propagation channel for facts — not just a doorbell.** Send the *change*
("X is now Y, superseding Z"), not "you have a handoff": the sentence itself is what crosses the freeze.
Limits: it costs one turn per fact, and it only reaches a session somebody actually addresses — so the
durable record is still the file.

**`/new` and a delta DM fix different failures.** `/new` fixes **bloat** (a context too large, a snapshot
too old to be cheap); a delta DM fixes **staleness** (a snapshot that predates the facts). Neither
substitutes for the other — a seat can be on a cheap fresh context and still be wrong, or correctly
informed inside a 20-day session that is burning tokens.

**Measure the freeze before theorising about it:**

```bash
# the live session is the id the seat is currently logging under
grep -oE '\[(20[0-9]{4}_[0-9]{6}_[a-f0-9]+)\]' profiles/<seat>/logs/agent.log | tail -1
# its start time and size, from the session store (column names vary — read PRAGMA table_info first)
sqlite3 profiles/<seat>/state.db \
  "SELECT id, started_at, message_count FROM sessions WHERE id='<that id>'"
# and when memory actually changed on disk
stat -c '%y %n' profiles/<seat>/memories/MEMORY.md
```

**A memory file modified LATER than the live session's `started_at` is proof the seat cannot see it.**
Report that as a measured number — "frozen for N days" — not as an impression.

## Memory does NOT auto-compact

A write that would exceed the limit **returns an error** — it does not silently drop or evict entries.
So a full memory is a **friction** problem, not data loss: the seat hits a wall and must spend a turn
consolidating before it can save anything.

Recovery is **one batch whose final result is under the limit** — the limit is checked only on the
batch result, so a single call can free space *and* add the new entry:

```json
{"target":"memory","operations":[
  {"action":"remove","old_text":"<stale entry>"},
  {"action":"patch","old_text":"<long span>","new_text":"<short span>"},
  {"action":"add","content":"<new fact>"}]}
```

- `patch` / `remove` match on a **short unique substring**; a span occurring more than once is rejected —
  add surrounding text.
- A `patch` that *lengthens* is bound by the limit too.
- There is no `replace` action. To rewrite one entry, pass the whole entry as `old_text`.
- Exact duplicates are rejected with a "no duplicate added" success.
- Entries are scanned for injection/exfiltration patterns and invisible Unicode before acceptance.
- **Batch is all-or-nothing.** If it refuses and names a shortfall, free that many chars in the SAME
  batch and retry once — do not loop one add at a time.

**Consolidate above ~80%** (the percentage is in the injected header). Do not let a seat sit at 99%:
whatever it learns next is the thing that gets refused.

**⚠️ Capacity is the SMALLER problem when the snapshot is frozen.** Consolidating a memory that no
running session will re-read is tidying a room with the lights off. Fix the boundary first.

## Where a durable fact belongs

| The fact | Home | Why |
|---|---|---|
| Applies to **every** session regardless of task; small | `memory` / `user` entry | injected always |
| **How to do a class of task** | a **skill** | loads only when relevant; does not compete for the 2,200-char budget |
| A path a **recurring job** needs every run | a skill, or the job's own script | same reason |
| "did we discuss X last week?" | `session_search` | unlimited, ~20ms, no LLM cost |
| Project conventions, commands, ports | `AGENTS.md` / `.hermes.md` in the project | belongs to the project, not the agent |
| Durable voice and personality | `SOUL.md` (a file the **user** edits) | memory never changes the persona |

Memory is a **pointer, not a library**: keep index lines and edit them in place as facts change. If
memory is filling, the overflow goes to the durable store (vault/skill), not to a bigger memory.

## "The agent feels dumber" — check in this order

Most cases are one specific, checkable cause, roughly in order of how often they are it:

1. **The session is on a different model than you think** — `/model`, `/status`. A plain model switch is
   session-only; a dashboard change applies to new sessions only.
2. **Context pressure** — `/usage`, `/context`; then `/compress` (keeps recent exchanges verbatim) or `/new`.
3. **Wrong detected context length** — the CLI startup line prints it; pin `model.context_length`.
4. **The frozen snapshot** — forgot something saved *this* session. By design; visible next session.
5. **Memory is bounded and curated** — a detail from last week is not there by design. Ask for a
   `session_search`; do not "fix" it by adding transcript.
6. **Skills or tools not loaded** — `/skills`, `/tools list`, `/context all`.
7. **Compression side-effects** — older detail was summarised away; `session_search` reaches the archived
   turns (compaction is non-destructive by default, `compression.in_place: true`).

## Commands

```bash
hermes memory status|setup|off|reset   # external provider; built-in memory is ALWAYS active
hermes journey list|show               # timeline of saved memory entries + skills over time
hermes sessions list|browse|rename
```

- Only **one** external provider active at a time; built-in memory runs alongside it, never replaced.
- `hermes memory reset` **erases** MEMORY.md and USER.md — treat as destructive.
- **Gating:** `write_approval: true` stages writes instead of applying them (`/memory pending`,
  `/memory approve all`); `skills.write_approval` does the same for skills. **On a gateway a staged write
  never reaches the file until approved** — check this before concluding a save "did not work".
- `memory.memory_enabled: false` (or `memory` in `agent.disabled_toolsets`) removes the tool entirely; a
  seat then cannot save at all, whatever it claims.
- A **config change to memory/compression keys on a running gateway takes effect on the next message** —
  no restart — but the injected SNAPSHOT still only refreshes at a session boundary.

## Pitfall

**"I've saved that to memory" is text, not evidence.** Memory persists only when the `memory` tool is
actually called. Weak tool-calling models produce the confirmation without the call. Verify by reading
the file — and if it keeps happening, the fix is a stronger model for setup, not more instructions.
