# The Kanban bridge — putting the file-based lists onto a durable board

Why this file exists: the queue is a FILE (intent + history). A file cannot hold **state** — who claimed
it, whether it is running, who commented mid-run. The kanban board can, and it survives a restart that
loses the agent's context window. This is how to join them without creating a third copy that drifts.

---

## 1. What the lists actually are (measured, not remembered)

| # | list | path | what it is |
|---|---|---|---|
| 1 | Jordan's queue | `HQ/jordan-queue.md` | only a human can act; one section per lead |
| 2 | build queue | `00-HQ/build-queue/build_queue.json` | the canonical record we can act on |
| 2b | `queue.md` | `00-HQ/build-queue/queue.md` | a **render** of the JSON — not a second list |
| 3 | pending | `00-HQ/pending-list.md` | **includes blocked**; every row names its gate + release condition |
| 4 | completed | `00-HQ/completion-registry.json` | harvested shipments |
| 4b | `completed-list.md` | `00-HQ/completed-list.md` | a **render** of #4, last 7 days |
| 5 | thinking lists | `09-Green Room/ideas.md` · `11-Mess Hall/considerations.md` | ideas and decisions, not tasks |

**A render is not a list.** Any file whose header says `GENERATED … do not hand-edit` must never be
edited by hand and must never be counted as an independent source. Two renders in this set exist only
because the JSON is unreadable to a human at a glance — that is the whole of their job.

**A count is not a measure of work.** `completed-list.md` prints a large "N completed in the last 7 days"
figure that is a count of **log lines harvested from per-seat `*-completions.md` files**, not N units of
delivered work — and the registry's own `description` field says so and points the reader at the seat
files instead. Read the `source_list` breakdown before quoting any total, and never print the harvest
count as an achievement.

**Terminal rows accumulate.** The canonical queue can carry its own finished rows (`shipped`, `closed`,
`dropped`, `superseded`, `cancelled`) even though this skill says completed items should be removed.
Count the open subset before building anything on top of it, and treat the finished rows as archive.

---

## 2. The board

- Canonical DB: **`/opt/data/kanban.db`** · board slug `default` · the `kanban` toolset is enabled in the
  profile config. `hermes kanban init` is idempotent; `hermes kanban boards list` shows the current board.
- A board that has been configured but holds **zero tasks** is not "set up" — check `tasks` in the DB before
  claiming the fleet has a task board.

Verbs that matter for a bridge:

```bash
hermes kanban create "<title>" --body-file <path> --assignee <profile> \
       --idempotency-key <stable-key> --completion-contract "<what done means>"
hermes kanban comment <task-id> "<mid-run note>"     # lands as an ADDITIVE note, not an interrupt
hermes kanban context <task-id>                      # exactly what the worker will see
hermes kanban ls | show <id> | assign | block | unblock | complete | archive
hermes kanban dispatch --dry-run                     # preview spawns; then --max N
hermes kanban daemon | watch | stats | runs | tail
```

`--idempotency-key` is the whole reason a sync is safe: re-running the importer with the same key per
queue item creates nothing new. **Use the queue item's own id as the key** — a name is a claim, an id is
the identity, and a renamed item must not become a second task.

`kanban comment` is the durable form of "here is more detail while you work": the worker receives it as
*"New note on your kanban task — take it into account for the work you're doing right now"*. A chat message
mid-turn is delivered the same way by the harness (`steer`), but it does **not** survive a restart; a
comment does.

---

## 3. The bridge — one direction, open rows only

```
build_queue.json ──(idempotency-key = item id)──► kanban task
   the record                                      who / when / state
                                                       │
                            complete ─────────────────►│
                                                       ▼
                              back to build_queue.json status
                              + a completion entry WITH proof
```

Rules that keep it honest:

1. **Only open rows cross** (`pending` / `in_progress` / `blocked`). Dragging the archive onto the board
   turns it into a graveyard you filter before every look.
2. **Carry the queue id in the task body**, not only in the idempotency key — a human reading the board must
   be able to find the row it came from.
3. **Blocked rows keep their gate.** Put the gate and its release condition in the body: a board row that
   says only "blocked" is a shrug, and the same rule applies here as in `pending-list.md`.
4. **Write back only on completion**, and write the proof with it. A board that closes tasks without a
   proof field becomes the next unverifiable completion count.
5. **Never make the board the only copy of anything the queue also holds.** The board is the execution
   surface; the JSON stays the system of record until someone decides otherwise.
6. **Do not put ideas or considerations on the work board.** A half-formed idea in a task row is noise you
   filter forever; mature it first and promote it into a task as a deliberate act.

---

## 4. Pitfalls

- **A configured board is not a running board.** Zero tasks for weeks looks identical to a working system
  from the CLI's help output. Query the DB.
- **`hermes kanban` has no `import` command.** Import is a script you write against the CLI or the SQLite
  file; check the verb list before designing around one that does not exist.
- **Verify the board end to end before recommending it** — create one throwaway task, comment on it, read
  `context`, then archive it. A board whose comment path is broken is a board that silently drops the
  mid-run notes you built it for.
- **Every earlier surface must be re-pointed in the same change.** If a new manifest or sync file wins the
  read order for a route, the old one becomes a decoy that silently ignores edits. The same is true of
  these lists: retire `queue.md` as a hand-written surface when the board renders it, or you have created
  the drift you set out to remove.
