# The kanban board — command surface and the workflows worth having

Depth for the "board is an execution surface" section of SKILL.md. Read that section first: the safety
rules (triage-by-default, empty claim allowlist, `block` not `reclaim`, stimulus probe) are prerequisites,
not alternatives.

## The model

| object | meaning |
|---|---|
| **board** | one per workstream. `hermes kanban boards create <slug>`; select with `--board <slug>` |
| **task** | a card: title, body, assignee, status, dependencies, workspace, model override, completion contract |
| **status** | `triage` → `ready` → `running` → `done` / `blocked` / `review` / `archived`. `todo` = waiting on a parent |
| **run** | one worker execution of a task (`task_runs`): status, worker pid, heartbeat, outcome, summary |
| **comment** | the thread a human and a worker talk on. This is the additive-note channel |
| **event** | machine log per task (heartbeats, blocks, promotions) |

State lives in SQLite at `kanban/boards/<slug>/kanban.db`. **Read it read-only when you need the truth:**

```python
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
con.execute("select status,count(*) from tasks group by 1")
con.execute("select id,status,assignee from tasks where status in ('ready','running')")
```

The CLI is a view; the DB is the state. A CLI call that exits 0 with empty output is a **silent read
failure**, not an empty board — and an empty-looking board is what duplicates every card on the next sync.

## Commands, grouped by job

**Create and shape**

```
create <title> [--body|--body-file] [--assignee P] [--triage] [--priority N]
              [--parent ID ...] [--project] [--skill S ...] [--workspace|--branch]
              [--model|--provider] [--max-runtime] [--max-retries] [--goal] [--goal-max-turns]
              [--completion-contract TEXT] [--idempotency-key K] [--created-by WHO]
specify [<task_id>|--all]      # an LLM writes the real spec for a triage card
decompose <task_id>            # split one card into children (needs the aux model)
edit <task_id>                 # amend title/body
promote <task_id>              # triage -> ready. THE APPROVAL GATE
```

**Move state**

```
claim / reclaim / reassign      # reclaim RETURNS THE CARD TO CLAIMABLE — it restarts work, it does not stop it
block <id> [--ids ...] [--kind capability|dependency|needs_input|transient] <reason...>
unblock <id>                   # re-arms; repeat same-kind blocks route to triage to break loops
schedule <id> <reason...>      # defer with a timing note
tail / log / runs / heartbeat  # what a worker is actually doing
complete <id>                  # terminal, with a result
archive <id>                   # out of the working set, kept for the record
```

**Review and evidence**

```
request-review <id>   / request-changes <id> / reopen-review <id>   # review as a STATE
attach <id> <path>    / attachments / attach-rm                     # evidence pinned to the card
comment <id> <text>                                                # additive note, delivered mid-run
```

**Multi-worker shapes**

```
swarm                          # Kanban Swarm v1: parallel workers -> verifier -> synthesizer
link <parent> <child>          # dependency; child waits in todo, auto-promotes when parent finishes
dispatch [--dry-run] [--max N] # manual dispatch pass
   daemon / watch              # run the dispatcher outside the gateway
stats / diagnostics / gc / repair
```

**Notifications**

```
notify-subscribe <id> / notify-list / notify-unsubscribe   # push on complete/block, instead of polling
```

## Config knobs that decide whether the board is safe

| key | default | set it to |
|---|---|---|
| `kanban.dispatch_in_gateway` | **true** | `false` unless you intend unattended workers |
| `kanban.auto_decompose` | **true** | `false` — otherwise triage spawns LLM children |
| `kanban.auto_decompose_per_tick` | 3 | bounds the burst if you re-enable decomposition |
| `kanban.dispatch_profiles` | `None` (any) | `[]` — fail-closed claim list, claims nothing |
| `kanban.review_dispatch` | true | `false` if reviews are human-only |
| `kanban.max_in_progress` | None → memory-derived | set an explicit int to bound the fleet |
| `kanban.dispatch_interval_seconds` | 60 | raise it if a tick can outrun your approval |

Set these with `hermes config set kanban.<key> <value>`; **the running gateway only picks them up at
start**, so a restart is part of the change, not a follow-up.

## Workflow 1 — queue → triage → specify → promote (the safe pipeline)

```
for each open queue row:
    kanban create <name> --body <row body + gate + queue id marker> --assignee <seat> --triage
# nothing runs. A human (or a scheduled review job) decides:
    kanban specify <id>      # optional: turn the rough card into a real spec
    kanban promote <id>      # the approval gate — now it can be claimed
```

- **Carry the queue id in the body** (`bq:<id>`) so the board is joinable back to the record and the sync
  can dedupe by reading markers rather than trusting `--idempotency-key`.
- **Only open rows cross.** Closed items belong in the record, not on a work board you filter before
  every look.
- **A blocked row keeps its gate and release condition in the card body.** A card that says "blocked"
  with no release condition is a shrug with a status.

## Workflow 2 — a completion contract answers "what counts as done"

An append-only log of "shipped" lines cannot tell anyone whether the thing is true. A card can carry the
test:

```
kanban create 'Route X serves real data' --completion-contract '<the observable state that must hold>'
```

The contract is the difference between *someone wrote a line* and *the promised state was checked*. Use it
for anything whose completion a reader might doubt — which is most things worth tracking.

## Workflow 3 — review as a state, not a comment

`request-review` moves the card into a review lane a reviewer can claim; `request-changes` sends it back
with the reason. That makes "done" mean *reviewed and accepted*, and keeps the judgement visible instead
to buried in a chat thread. Pair it with `attach` for the evidence the reviewer is meant to read.

## Pitfalls, all measured

1. **`--board` goes BEFORE the verb.** `kanban --board <slug> ls --json` parses; `kanban ls --board <slug>
   --json` does not.
2. **Strip the CLI banner before parsing.** stdout can carry a version/notice line ahead of the payload;
   slice from the first `[` (a list payload) rather than the first `{`, which throws away the wrapper.
3. **`--idempotency-key` does not dedupe.** Same key twice = two cards, same id printed both times.
4. **`reclaim`/`release` re-arms the work.** To stop a running fleet: block the cards first, then stop the
   worker processes. Doing it in the other order re-creates them within seconds.
5. **A blocked card's children stay in `todo` and are safe.** They cannot be claimed until the parent
   finishes, so a parked parent parks its subtree — no separate cleanup needed.
6. **`--triage` + `auto_decompose: false` is the inert parking lot.** Either one alone is not enough.
7. **Dumping the board into one giant sync is how a fleet wakes up.** Batch with `--limit`, inspect the
   first few cards, and only widen once you have seen one land in the state you intended.
8. **A worker's write-back to a JSON record will re-serialise it.** Enforce the queue's splice rule on the
   write-back path, and prove a re-serialisation by comparing parsed rows field-by-field and printing the
   changed count.
9. **Stopping workers: never `pkill -f <literal-that-you-just-typed>`.** The pattern matches the invoking
   shell's own command line, so the kill takes out the tool call that issued it and you learn nothing about
   whether the workers died. Bracket one character so the pattern cannot match itself:

   ```bash
   pgrep -f 'hermes_cli[.]kanban_worker_client'      # count, self-safe
   pgrep -f 'hermes_cli[.]kanban_worker_client' | xargs -r kill   # then kill by PID
   pgrep -c -f 'hermes_cli[.]kanban_worker_client'   # verify 0
   ```

   Confirm the gateway PID is still alive afterwards — workers are children of the gateway, but they are
   separate processes, and the gateway is what you wanted to keep.
10. **Archiving the children of a decomposed parent RE-ARMS it.** Completing a parent's dependency set
   promotes the root to `ready` on the next tick, and a live dispatcher claims it immediately — so
   *cleanup is a stimulus*. Block the parent FIRST, then archive its children; otherwise the tidy-up you
   performed to reduce noise starts new workers.
11. **`block`'s reason is POSITIONAL; `--reason` does not exist.** The bulk shape is
   `block <id> --ids <more ids...> --kind needs_input "<reason>"`. Passing `--reason` fails as
   *unrecognized arguments* and the whole batch does nothing — which reads like "the cards refused to
   block" rather than "the flag is wrong". `archive` likewise needs `--board <slug>` before the verb.
12. **A ready card that nothing claims is the only proof the dispatcher is off.** A count of zero workers
   after a restart proves nothing on its own: with no claimable cards a live dispatcher is idle and looks
   identical. Create the stimulus, wait past one tick, assert no worker and no `task_runs` row, then
   archive the card. State the limit honestly — that probe proves the dispatcher is not running; it does
   not prove a config allowlist that no dispatcher has yet had to honour.
