# Session & memory monitoring — verified against the live schema

Every command here was run against a real Hermes deployment and returns what it claims. If a
path or column name below disagrees with the host, **the host wins** — re-derive with
`PRAGMA table_info(sessions)` before trusting an old copy of this file.

## Where the truth lives

| Thing | Path |
|---|---|
| Session + message store, per seat | `/opt/data/profiles/<seat>/state.db` (table `sessions`) |
| Memory / user profile | `/opt/data/profiles/<seat>/memories/MEMORY.md`, `USER.md` |
| Agent activity log | `/opt/data/profiles/<seat>/logs/agent.log` |
| Gateway in/out + resets | `/opt/data/profiles/<seat>/logs/gateway.log` |

⚠️ There is **no** `sessions/sessions.sqlite3` and no `memory_entries` table in this engine.
Queries built for those fail as "no such file" / "no such table" and can be misread as "no
sessions" — a false clean. Read the schema first.

## Is a seat's memory snapshot FROZEN, and for how long?

Hermes injects MEMORY.md/USER.md as a snapshot **at session start** and never refreshes it. On a
messaging platform the session never ends on its own, so the age of the live session **is** the
age of the memory the agent is working from.

```python
import sqlite3, datetime, sys
seat = sys.argv[1]
con = sqlite3.connect(f"file:/opt/data/profiles/{seat}/state.db?mode=ro", uri=True)
r = con.execute("""SELECT id, started_at, message_count, last_activity_at
                    FROM sessions WHERE source='telegram' AND ended_at IS NULL
                    ORDER BY started_at DESC LIMIT 1""").fetchone()
print(r[0], datetime.datetime.fromtimestamp(float(r[1]), datetime.UTC), r[2], "msgs")
print("frozen days:", round((datetime.datetime.now(datetime.UTC).timestamp()-float(r[1]))/86400, 1))
```

Emit **UNKNOWN, never a silent zero**, when the row is missing. A seat you cannot measure is the
finding, not the absence of one.

## Did a `/new` actually LAND? (the only reliable proof)

A reset is a *state change in the DB*, not a guess from a log:

```python
# closed sessions and why
con.execute("SELECT id, started_at, ended_at, end_reason FROM sessions "
            "WHERE source='telegram' AND ended_at IS NOT NULL "
            "ORDER BY ended_at DESC LIMIT 3")
# sessions opened today
con.execute("SELECT id, source, started_at FROM sessions WHERE started_at > ?", (midnight,))
```

- **Landed** = an old `source='telegram'` row with `end_reason='session_reset'`, whose `ended_at`
  immediately precedes a **new** telegram row `started_at`. Two rows, one handoff.
- **Did not land** = no new telegram row at all, and the old one still open. The bot never received
  the command — the room/gateway is the problem, not the user's typing.
- **Also check the gateway log** for `Invalidated run generation … (session_reset)` — it prints at
  the instant the reset is accepted and is the closest thing to a receipt.

⚠️ **NEVER infer a reset from the newest/most-frequent session id in `agent.log`.** Right after a
reset the *old* id still fills the log tail, so a mode-of-ids heuristic keeps reporting the dead
session and the seat looks frozen when it is not (measured: reported 23.4d stale minutes after a
successful reset). A heuristic that reads a log is a hypothesis; the `sessions` table is the record.

## Memory capacity, in the unit the limiter uses

Budgets are **characters**, not bytes. A UTF-8 arrow or em-dash costs more bytes than chars, so
`wc -c` overstates usage:

```bash
wc -m /opt/data/profiles/<seat>/memories/MEMORY.md   # -m = characters
```

Health target is headroom, not "not yet rejected": at 98–99% of budget a new fact is refused at
write time, silently, so a seat at the wall is one lesson away from being unable to remember it.
Report `chars / budget`, `headroom`, and `entries` per seat — and treat a seat with no archive
pointer in its memory as unable to cut safely when it hits the wall.

## Bloat and compression

```python
con.execute("SELECT id, message_count, tool_call_count, started_at, last_activity_at "
            "FROM sessions WHERE source='telegram' AND ended_at IS NULL "
            "ORDER BY message_count DESC LIMIT 10")
```

Signal to suggest `/new`: a live session past ~25 messages **or** any session whose memory
snapshot is older than the newest `MEMORY.md` mtime — the second one always matters, the first is
a comfort threshold.
