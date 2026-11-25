# Syncing a build queue to a Hermes kanban board

Concrete mechanics for the one-direction rule in `SKILL.md` ("the mirror must be an inert render").
The board is **not** an inert render — it is an executor. Everything below assumes you have already
verified the dispatcher is off.

---

## 0 · Verify the actuator BEFORE creating the first task

Creating a card is not a write to a list; it is a request for work. Check, in this order:

```bash
hermes config get kanban.dispatch_in_gateway   # default TRUE — the gateway spawns workers
hermes config get kanban.auto_decompose        # default TRUE — triage cards get an aux-LLM split
hermes config get kanban.dispatch_interval_seconds   # default 60
grep -n 'kanban' /opt/hermes/hermes_cli/config_defaults.py | head
```

Signs the dispatcher is live:

```bash
pgrep -af kanban_worker_client      # one process per running task, parent = the gateway pid
```

To hold a board without editing code:

```bash
hermes config set kanban.dispatch_in_gateway false
hermes config set kanban.auto_decompose false
```

A `--dry-run` that prints "would create N" is **not** a safety check for this — the danger is in the
create, not in the count. Prove the executor is off first, then create one task, then inspect it
before bulk-loading.

**Verify the STOP by the process count, not by the config value.** `hermes config set` printing
`✓ Set …`, and `hermes config get` echoing `false`, both prove the FILE changed — the dispatcher holds
its own view and acts on a tick. The check is:

```bash
pgrep -cf 'hermes_cli[.]kanban_worker_client'   # bracket the dot: a bare pattern matches YOUR shell
```

**A zero worker count is not yet proof of anything.** `dispatch_in_gateway` is read at **gateway start
only**; a running gateway keeps ticking with the old value in memory, so the count drops to 0 between
ticks and climbs straight back. Measured: config set to `false`, workers 8 → 0 → 8 again minutes later,
with `hermes config get` reporting `false` the whole time.

**Two ways to actually stop it, in order of durability:**

1. **Restart the gateway** — the only action that makes the file value real. It cannot be done from
   inside the gateway process; it is a host action for the operator.
2. **Until then, leave nothing dispatchable** — a ticket is only claimable from `ready` (and from
   `review` while `review_dispatch` is on). Park the fleet, then prove the board has no claimable card:

```bash
# the state that means STOPPED, measured in the DB rather than the CLI
sqlite3 kanban.db "select status,count(*) from tasks group by 1"   # ready=0, running=0, workers=0
```

Config false + a human told to restart + zero claimable cards is a stopped fleet. Config false alone
is a note to the next reader.

---

## 0b · Two ways a "cleanup" restarts the fleet

**Archiving a child is a completion event, and children wake their parents.** A decomposed root prints
*"Root will wake when all children complete"* — so archiving 37 orphan children promoted their parents to
`ready` and the dispatcher spawned workers for them immediately. Park the parents **before** archiving
their children, or the cleanup is a launch.

**A refused `block` is usually safety, not failure.** `cannot block <id>` on a card that is `todo` with
unfinished parents is correct: a dependency-waiting card cannot be claimed until its parent completes, so
it needs no parking. Leave it and say so; do not reach for the DB to force it.

**Never `pkill -f <pattern>` with the pattern in your own command line** — the shell command that runs it
contains the string, so it matches itself and dies (exit `-15`, and the state read you queued after it
never runs). Bracket one character (`'kanban_worker[ ]client'`, `'hermes_cli[.]kanban_worker_client'`) so
the pattern cannot match its own invocation.

---

## 0c · Make the sync INCAPABLE of dispatching (the durable fix)

A sync that relies on `dispatch_in_gateway: false` being remembered is one config reset away from
launching a workforce. Two changes make the board structurally inert:

1. **Create every card with `--triage`.** `ready` means *run this now*; `triage` does not dispatch, and
   with `kanban.auto_decompose: false` nothing touches it. Promotion out of triage (`promote` /
   `unblock`) is the approval gate — one verb, visible on the board.
2. **`hermes config set kanban.dispatch_profiles "[]"`** — the shipped per-home claim allowlist: *"Set =
   fail-closed (an empty list claims nothing)"*. It refuses at **claim** time, so it does not depend on
   the gateway having started with a particular file.

With both, an accidental bulk sync produces a pile of parked cards, not eight workers.

### The control probe — prove the loop is inert, not just that nothing happened

Zero workers proves nothing when no card is claimable: **idle and disabled look identical.**

```bash
# 1. create a card the dangerous way on purpose: ready, no triage
TID=$(hermes kanban --board <slug> create 'PROBE — safe to ignore' \
        --body 'dispatch liveness control' --created-by dispatch-probe \
        | grep -o 't_[0-9a-f]*' | head -1)
sleep 90

# 2. read the DB, not the CLI
sqlite3 <db> "select status from tasks where id='$TID'"              # still 'ready'
sqlite3 <db> "select count(*) from task_runs where task_id='$TID'"   # 0
pgrep -cf 'hermes_cli[.]kanban_worker_client'                        # 0

# 3. archive it
hermes kanban --board <slug> archive "$TID"
```

A card still `ready` with zero runs IS the proof: a live dispatcher reaps claimable cards within one

tick (60s default). Report it as *"config false, and a control card went unclaimed for 90s"* — the
second half is the measurement.

### Two parsing traps in the CLI output

- **Slice JSON from the first `[`, never the first `{`.** `ls --json` emits a list; slicing at `{` starts
  mid-object and the parse fails while looking like corrupt output. A banner line ("install out of
  sync…") often precedes the payload on the combined stream.
- **Treat `rc=0` with empty stdout as a READ FAILURE, not an empty board.** That silent mode duplicates
  the entire queue on the next run. Fall back to the DB read above.
- `--idempotency-key` stores the key and still creates a second card, re-printing the original task id —
  it *looks* deduped, which is why the body marker in §1 is the index instead.

---

## 1 · Idempotency: the CLI flag does not dedupe

`hermes kanban create --idempotency-key K` **stores** K; repeating the same K still creates a second
card (the same task id is printed, so it *looks* deduped). Do not build a sync on it.

**The working index: a marker in the body, read from the database.**

```python
import re, sqlite3
db = "/opt/data/kanban/boards/<slug>/kanban.db"
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
idx = {}
for tid, body in con.execute("select id, coalesce(body,'') from tasks"):
    for qid in re.findall(r"bq:([A-Za-z0-9._-]+)", body or ""):
        idx[qid] = tid
```

Every synced card starts its body with `bq:<queue-id>`, so a human reading the card and a script
reading the DB agree on the same key. Then `to_create = [i for i in open_items if str(i['id']) not in idx]`
and a re-run is a no-op — **prove it** by dry-running twice and showing `would create: 0`.

**Read the DB, not the CLI, as the authority.** `hermes kanban --board <slug> ls --json` can return
**rc=0 with empty stdout** when run under the gateway/cron process. That reads exactly like "the
board is empty" and will duplicate the whole queue on the next tick. The DB read has no such mode.

---

## 2 · Command shapes that actually work

```bash
# the board flag goes BEFORE the verb, not after it
hermes kanban --board gentech ls
hermes kanban --board gentech reclaim <task>
hermes kanban --board gentech block  <task> 'reason text'

# block: task_id then reason (positional). There is no --reason flag.
# bulk: first id positional, the rest via --ids
hermes kanban --board gentech block <id1> --ids <id2> <id3> --kind needs_input 'reason'
```

- Omitting `--board` makes the verb act on the **default** board — `reclaim` then answers
  `cannot reclaim <id> (not running or unknown id)` for a task that is plainly running.
- `block --kind` values: `dependency` (waits in todo, auto-promotes when parents finish), `needs_input`
  and `capability` (park for a human), `transient` (flaky). A repeat re-block of the same kind routes
  the card to triage to break unblock loops.
- **`reclaim` does not stop work, it requisitions more.** It releases the claim and puts the card back
  to `ready`, so the dispatcher spawns a fresh worker on the next tick. To STOP a fleet, `block`
  everything first; reclaim only to clear a stale lock you intend to reassign.

---

## 3 · What a synced card must carry

| field | why |
|---|---|
| `bq:<id>` as the first body line | the dedupe key, human- and machine-readable |
| owner + difficulty + queue status | a reader should not need the JSON to know whose card this is |
| the item's detail, truncated | the worker has no other context |
| **gate + release condition** for anything blocked | a card that says only "blocked" is a shrug |
| the vault path and queue id | the queue stays the system of record |

Closed statuses (`shipped`, `closed`, `dropped`, `rejected`, `superseded`, `cancelled`) must **never**
cross. A board that mirrors 118 rows including 52 finished ones is a graveyard every reader filters
before looking.

---

## 4 · Owner names are not profile names

Queue owners (`treasury`, `labs`, `forge`) are not assignable Hermes profiles. Map them explicitly and
map the unassignable ones to **no assignee** rather than letting `--assignee` invent one:

```python
OWNER_MAP = {"gentech": "gentech", "gentech-treasury": "gentech-treasury",
             "treasury": "gentech-treasury",      # old label, same seat
             "arthur": "arthur", "protojay": "protojay",
             "forge": None, "labs": None}        # desktop / retired — not assignable
```

---

## 5 · After a sync run, read what the workers did

```sql
select id, task_id, profile, status, outcome, substr(summary,1,300) from task_runs;
select task_id, author, substr(body,1,250) from task_comments;
select status, count(*) from tasks group by status;
```

`task_runs.summary` is the worker's own closing report and is the fastest read of what actually
happened. Cross-check any external side effect it claims **against the external system** (the GitHub
API, the live endpoint), never against the summary alone.

Worker-written files land in the vault as untracked changes: `git status` on the vault is the
inventory, and `git diff --numstat` separates cosmetic churn from real edits.
