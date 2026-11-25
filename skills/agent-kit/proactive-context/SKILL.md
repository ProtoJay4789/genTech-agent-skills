---
name: proactive-context
description: Proactive context saving — handoff notes, Mess Hall logging, memory management
category: core
---

# Proactive Context Saving

**Trigger:** When context is getting tight, when brainstorming, when ending a session.

## During Conversations

1. **Log ideas to Mess Hall** (`11-Mess Hall/`) during brainstorming — not just at the end
2. **Cross-reference** — note files, decisions, or threads that might be needed later
3. **Save as skill** if a workflow repeats — don't clutter memory with procedures

## Handoff Note Protocol

When ending a session or context is tight, write to `11-Mess Hall/YYYY-MM-DD-handoff.md`:

```markdown
# Session Handoff — [Date]

## Working On
- What we were doing when context ran out

## Decisions Made
- List of choices/decisions from the session

## Open Threads
- Things started but not finished

## Next Steps
- What to pick up on session resume

## Files Modified
- List of files that were changed
```

## Agent Activation via Peer Transport

Context is no longer a passive accumulate-then-prune problem. **`hermes peer dm`
spawns a real turn in the target agent** — the active-memory layer. Wake another
agent only when there's something to act on:

```bash
hermes -p <my-profile> peer dm <target> "Pick up the open handoff at <path> — <task>"
```

- Handoffs (vault) = durable record; peer DM = live wake-up that proves the
  agent acted (synchronous reply).
- Each profile needs a distinct `api_server.port` (gentech 8642, treasury 8643,
  gizmo 8644, pixel 8645) + a strong `API_SERVER_KEY`, then a gateway restart
  (from a separate shell — the gateway SIGTERMs children).
- **Bot Chat bloat pitfall:** a peer DM targets the canonical "Bot Chat" session,
  which doesn't auto-reset and can exceed the compressible context ceiling. Reset
  it when you see "Context length exceeded":
  `hermes -p <profile> sessions rename <id> "__archived-bot-chat"` then
  `hermes -p <profile> sessions archive --title "__archived-bot-chat" --yes`.
  Recoverable, nothing deleted.
- Full reference: `docs/peer-transport-and-activation.md`.

## Memory Bar Rule

Only show `[🧠 XX%]` when memory is 80-100% full. Don't show it below 80%.

## Session Start Protocol

1. Read latest Mess Hall file for context
2. Check `09-Green Room/ideas.md` and `11-Mess Hall/considerations.md`
3. Search sessions if user references something from before
4. Don't ask the user to repeat themselves — find it in the vault first

## Skill Over Memory

When discovering a repeatable workflow:
- **Memory** = facts (user preferences, environment details)
- **Skill** = behaviors (procedures, workflows, patterns)
- Save as skill if it'll be used again — skills persist better

## Mess Hall as Scratchpad

The Mess Hall (`11-Mess Hall/`) is for:
- Ideas being fleshed out
- Cross-references to check later
- "Things to think about" notes
- Mid-conversation observations
- Session handoff notes

Don't wait until end of session. Log as you go.

## Notes written WITHOUT an instruction — two tiers, and no third

"Log as you go" answers *when*. This answers *where*, and the distinction is the one that decides whether the
note outlives the session. Every note written on your own initiative goes to exactly one of two places:

| tier | lives in | contract |
|---|---|---|
| **DURABLE** | the vault (`00-HQ/`, `11-Mess Hall/`, the owning project folder) | indexed, discoverable by someone else, dated, current until superseded |
| **SCRATCH** | `profiles/<seat>/cache/scratch/` | disposable, never cited as evidence, assumes nobody else will read it |

**A note that is neither is the failure state**, and it is the common one: analysis written into a scratch file,
concluded from, quoted in a reply — and then left where no index points and no cleanup reaches. The conclusion has
no home, and the next session re-derives it from raw data, which is the expensive way to learn something we already
knew.

- **State the tier in the note's first line.** A one-line header (`# SCRATCH — not indexed` or a real vault title)
  makes the difference visible to whoever finds it later, including you.
- **Promote before you conclude.** The moment a scratch file's finding is used in a report, a decision, or a
  skill, the finding must be promoted to a durable note — the report is transient, the vault is the record.
- **Never cite a scratch path to the user as the record.** Give them the durable note; keep the scratch path for
  your own tool calls. A path under `cache/` reads as an artifact until the reader learns it is pruned.
- **Write → index → route → open.** A durable note with no pointer from the index does not exist for the next
  reader. Add the pointer in the same change, not "later".
- **Scratch has no expiry by default — give it one.** Directories under `cache/` that nothing prunes accumulate
  until someone audits them, and a stale scratch file that looks like analysis is worse than no file.

**The test for which tier:** *could someone else find this next week, and would they know whether it is still
current?* Yes → durable, and make both halves true. No → scratch, and say so at the top.
