# Refreshing a frozen memory snapshot — the levers, and what each one actually does

Hermes injects `MEMORY.md`/`USER.md` into the system prompt as a snapshot at session start and never
refreshes it mid-session (prompt-cache preservation). On a messaging platform a session can live for
weeks, so a seat keeps writing facts it cannot read. The only fix is a **new session for that chat**.

## What each lever does

| lever | reaches the chat's session? | notes |
|---|---|---|
| user sends `/new` in the chat | **yes** | ends the old row with `end_reason='session_reset'`, sets `is_fresh_reset` |
| `hermes sessions …` (list/archive/prune/repair) | **no** | store maintenance only; there is no `new`/`reset` subcommand |
| `hermes peer dm fleet/<seat>` | **no** | runs a turn under that seat's `api_server` routing key |
| `hermes -p <seat> chat --oneshot` | **no** | same: a fresh api session, the Telegram session is untouched |
| gateway restart | **no** | routing index is persisted; sessions resume |
| your own CLI message posted into the chat | **only if one can be sent at all** | `hermes send -t <platform>:<chat>` is the only route by which you could trigger the reset yourself — check `hermes send --list <platform>` first. Measured once in this container: no channels discovered, and `-t telegram:<chat>` failed `Chat not found` |
| write `suspended=true` into the routing index | **yes, on the chat's next message** | the engine's own force-new path (see below) |

**The measured trap:** after a peer DM a seat looks awake — it replies, it runs tools, its log is busy —
while the chat whose memory you meant to refresh is still the old row. "The seat answered me" and "the
seat's chat has a new session" are different claims with different proofs.

## The routing index

One table, one row per live chat, in the **default** profile's store (`/opt/data/state.db` in this
container) — not in the seat's own `state.db`, which holds only that seat's session/transcript rows.

```sql
-- shape
SELECT scope, session_key, entry_json, updated_at FROM gateway_routing;
-- scope is the sessions dir, e.g. '/opt/data/sessions'
-- session_key: agent:<profile>:<platform>:<chat_type>:<chat_id>:<user_id>
-- entry_json: the serialised SessionEntry (session_id, created_at, suspended, resume_pending,
--             is_fresh_reset, active_turn_token, active_turn_started_at, origin, prompt_pin, ...)
```

Semantics, read from the engine's own source (`gateway/session.py`, `get_or_create_session()`):

- **`suspended=True`** → next access creates a **new `session_id`** (`auto_reset_reason='suspended'`).
- **`resume_pending=True`** → next access **keeps the existing `session_id`** (crash recovery: the seat
  continues on the same transcript). This is why clearing `active_turn_token` / `active_turn_started_at`
  matters — `recover_interrupted_turns()` promotes a leftover marker to `resume_pending`, which would
  undo the suspension you just set.
- Priority order is `suspended` → `resume_pending` → `updated_at`, so `suspended` wins.

## Procedure (operator-initiated refresh)

1. **Snapshot the store first**: copy `state.db` to `backups/state.db.pre-refresh-<UTC>`.
2. Read the row for the target key and confirm which `session_id` it points at (that is the frozen one).
3. In the `entry_json`: drop `active_turn_token` and `active_turn_started_at`, set `suspended=true`,
   `auto_reset_reason='suspended'`, `resume_pending=false`; write it back to the same key.
4. **Verify by the chat's next message, not by the write.** A confirmed refresh = a NEW row (or new
   `entry_json.session_id`) for that key, and the old `sessions` row ending with
   `end_reason='session_reset'` immediately before it.
5. Tell the user what will happen on their next message in that chat (a fresh start, not lost work —
   the transcript is retained in the store).

## Honesty rules

- **Say which step you actually completed.** A routing-index write is not a refresh until a new session
  row exists. Until then: "suspended, awaiting the chat's next message" — never "refreshed".
- **The engine resets on the next inbound message, so an idle seat stays frozen** until something is sent
  to it. If the chat is silent for a day, the refresh has not happened yet.
- **Never edit another profile's routing state as a side effect of unrelated work.** One target key at a
  time, backed up, verified — several seats share one index, and a wrong key resets a conversation
  somebody was mid-task in.
