---
name: agent-graph-orchestration
description: "Use when wiring a multi-agent graph (LangGraph or similar)."
version: 1.0.0
author: arthur
license: MIT
metadata:
  hermes:
    tags: [orchestration, langgraph, state, parallel, retry, fail-closed]
    related_skills: [agent-tool-contracts, falsifiable-tests, develop-and-verify, multi-agent-build-queue]
---

# Agent graph orchestration — state that survives parallel branches

Wiring two or more agents into a graph (LangGraph, or any stateful runner). The failure mode is never the
model: it is the state schema, the join, and the retry counter.

**Governing rule: a graph must be provably unable to hang, unable to run a node twice by accident, and
unable to hide a branch that failed.** Each of those is a state-schema decision, not a code review finding.

## When to Use

- Building a graph of agents/nodes (research → write, fan-out → join, supervisor → workers).
- Adding a second or third parallel branch to an existing graph.
- A node sometimes runs twice, the graph never terminates, or a failed branch silently disappears.
- Writing the handover doc for a graph someone else will run.

## Procedure

### 1. Declare the state with a reducer on EVERY key that can be written concurrently

Start here, not with the nodes. Any key two nodes can touch in the same step needs
`Annotated[..., reducer]`:

```python
from typing import Annotated, TypedDict
import operator

def _last(old, new):                    # explicit last-write-wins
    return new if new is not None else old

def _merge(acc: dict, new: dict) -> dict:
    out = dict(acc or {}); out.update(new or {}); return out

class S(TypedDict, total=False):
    trace:    Annotated[list, operator.add]   # append-only audit of every step
    findings: Annotated[dict, _merge]         # both branches write here
    attempts: Annotated[dict, _merge]         # retry counters, per branch
    status:   Annotated[str, _last]
```

**Never make a step counter a plain `int`.** Two parallel nodes incrementing it raises before your code
ever runs.

### 2. Give each branch its own retry counter, stored in STATE

The router reads the counter every pass, so it cannot live in a closure — a closure resets per invocation
and the graph loops forever.

```python
def route_branch(branch):
    def route(state):
        findings = state.get("findings") or {}
        attempts = state.get("attempts") or {}
        if branch not in findings and attempts.get(branch, 0) < MAX_ATTEMPTS:
            return f"research_{branch}"        # RETRY the same node
        ...
    return route
```

### 3. Make the join a STATE CONDITION, not an edge count

Correct join: a node fires when **every** branch is settled (produced a result **or** exhausted its attempts).

```python
settled = all((b in findings) or (attempts.get(b, 0) >= MAX_ATTEMPTS) for b in branches)
if not settled: return {"trace": ["writer#waiting"]}
if state.get("draft"): return {"trace": ["writer#skipped"]}
```

And route a not-yet-settled branch to `END` for **its path only** — not through the join — or it terminates the
graph while the other branch is still working.

### 4. Put a hard ceiling in the graph, not in the caller

A `guard` node after the join aborts when `len(trace) > MAX_ITERATIONS`. An orchestration bug then becomes a
stopped run with an explicit status, not a bill and a hung process.

### 5. Prove recovery by injecting faults, not by describing them

Ship the fault injector with the graph and assert outcomes in the same script:

| scenario | injection | must prove |
|---|---|---|
| happy | none | all branches present, `status=complete` |
| transient | a branch fails once | **retried**, then completes; `attempts[branch]==2` |
| permanent | a branch fails always | other branch **still present**, gap recorded, terminates fast |

Assert each as a boolean and print a verdict table; exit non-zero if any fails. A graph whose recovery was
never exercised has not been tested.

### 6. Make the failure visible in the OUTPUT, not just the state

The writer must mark the gap in the artifact itself:

```
## Branch B — FAILED
> INCOMPLETE — branches B failed after 2 attempt(s). The draft uses what exists and marks the gap.
```

**Hand a model a failed branch and it will invent its contents.** The gap marker is what stops a downstream
LLM from hallucinating over a missing input.

### 7. Handover doc: run command, exit-code contract, and what is NOT proven

State: the run command and its dependencies, the runtime, that **exit code is the signal** (`0` all checks,
`1` any failed), the graph diagram, the node table, and a short *"what is not proven"* section. That last
section is the difference between a demo and an artifact.

## Pitfalls

- **`InvalidUpdateError: At key 'X': Can receive only one value per step`.** Two nodes wrote a plain key in one
  superstep. Fix by reducing **every** shared key — reducing only the key that failed first just moves the
  error to the next one (`status` after `iterations` is the same bug renamed).
- **A join by edge count runs the join node once PER branch.** With branches settling in different steps the
trace reads `writer, guard, writer, guard`: the writer runs twice, and two outputs race to overwrite each
  other. Harmless for a template, double the cost for a model call. Gate on state, and make a second
  invocation a no-op that records why (`writer#skipped`).
- **A premature route ends the graph early.** If the not-yet-settled path is routed through the join, that path
  reaches `END` and the run finishes before the remaining branch reports. Send it to `END` directly.
- **A retry counter in a closure resets every invocation** → infinite loop. It must be in state.
- **A retry budget with no ceiling elsewhere still spins** if the router can route back without consulting the
  count. Two independent bounds: per-branch attempts and a global step ceiling.
- **Asserting "parallel" without measuring it.** Two branches in one superstep is concurrency of *structure*;
  it is not a speed result. On a sub-second run there is nothing to measure — do not cite a latency win you
  never measured.
- **Deterministic nodes make a passing run repeatable.** For orchestration tests, keep retrieval/templating
  deterministic and swap the model in behind a flag. A non-deterministic branch makes a green run
  unreproducible and hides which change fixed it.
- **No checkpointing means a crash loses state.** If the run matters, wire a persistent saver; if you did not,
  say so in the handover rather than implying resumability.

## Related

- `agent-tool-contracts` — the boundary for a single tool call; this is the boundary for a graph of them.
- `falsifiable-tests` — proving a guard goes red for the right reason.
- `multi-agent-build-queue` — coordination across seats, which is a different problem from a graph.
