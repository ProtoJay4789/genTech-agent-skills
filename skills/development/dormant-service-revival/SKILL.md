---
name: dormant-service-revival
description: "Use when a service won't run — revive it, don't rebuild."
category: development
version: 1.0.0
author: Hermes curator
license: MIT
tags: [service, revival, import-errors, data-driven, migration, debugging]
metadata:
  hermes:
    tags: [service, revival, import-errors, data-driven, migration, debugging]
    related_skills: [lost-artifact-recovery, source-of-truth-verification, verify-after-every-action]
---

# Reviving a dormant service

A service whose code is on disk but which does not run. Two jobs, in this order: **make it run**, then
**make it extensible without touching its engine**.

**The expensive mistake in this class is planning a rewrite from a symptom.** "It doesn't start" reads
like deep damage and usually is not. **Read the first exception before you scope any rebuild** — a service
that has been dead for months is very often one line away from serving.

## When to use

- A service, API, or script exists on disk and has never run on this host, or stopped running.
- Someone asks "can we start on this now?" about a service that is already written.
- You are about to estimate a rebuild of something that exists.

## 1. Import it before you rebuild it

Run the import (or the start command) and **read the first exception**. Do not infer the fault from the
feature list or from how long the service has been dormant.

```bash
<venv>/bin/python3 -c "from api.server import app; print('import OK')"
```

A single missing name, a single bad path, or a single absent env var is the common answer. **Scope the fix
from the traceback, not from the symptom** — the traceback names the file and the line, and it is the only
cheap source of truth available before the service runs.

## 2. A hardcoded absolute path from a previous layout is the classic fault

**Symptom:** `ModuleNotFoundError` for a module that demonstrably exists somewhere on disk.

**Mechanism:** the service was written against a path layout that has since moved (a host migration, a
different deployment root, a renamed data tree, a restored snapshot). The code is fine; the path is a
ghost. It hardcodes an absolute root, so it fails identically everywhere the layout differs — including
in the same repository that contains the module.

**Check the top of the entry file for absolute roots before anything else** — this is where layout
assumptions live:

```python
_ENGINE_DIR = "/root/vaults/..."   # <- a root that does not exist on this host
sys.path.insert(0, _ENGINE_DIR)
```

**Fix it so it survives the next move:** resolve relative to the file, with an env override for a
genuinely different layout. Never replace one hardcoded root with another.

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.environ.get("<SERVICE>_DIR", "/opt/data/.obsidian-vault/10-Labs/<engine>")
```

## 2a. A path that RESOLVES is not a path that WORKS — freshness-gate every input

**The most dangerous revival is the one that runs perfectly.** Section 2 covers a path that does not
exist: it raises, and a traceback names it. The harder class is a path that still resolves **to a file
nobody has updated since the service died.** There is no error, no warning, and the output looks exactly
like a working service — because every line of code did work.

A lens that scored market structure put a dead feed's number into its verdict as **strongly bullish**. The
file existed, its mtime was weeks old but recent enough to pass a glance, and **the timestamp inside the
file was months older than its mtime**. The service was not broken. It was confidently wrong.

**Rules for any revived component that reads a data file:**

1. **Assume every input is as old as the service until measured.** Revival restores CODE; it does not
   restore the data that code was pointed at. Check each source's age before you report anything it says.
2. **Gate on BOTH clocks: the file's mtime AND the timestamp the file carries inside it.** They fail
   independently, and mtime is the one that lies — `touch`, a copy, a sync or a restore all refresh mtime
   while the payload stays last quarter's. A document carrying its own `generated_at` should be judged by
   that field first.
3. **A stale or missing input degrades to UNMEASURED — never to zero.** A zero silently votes for
   whichever side the lens is scoring, so a dead feed becomes an argument rather than an absence. Print
   the age you measured and the limit you applied, so the reader can see the gate fired.
4. **Never let an absence look like agreement.** If a component is designed to speak only on disagreement,
   then "the input was unreadable" and "the input agreed" produce the same silence. Report them as two
   states: `UNTESTED` and `no dissent`. Collapsing them turns the component into a rubber stamp.
5. **Prefer the live source you already maintain over reviving the dead feed the service was written for.**
   Repointing an old lens at a current data file is usually a smaller change than resurrecting its
   original feed, and it makes the revival agree with the rest of the system by construction.
6. **Re-verify the output against an independent measurement before trusting the revived verdict.** A
   service that starts is not a service that is right; the first run of restored code is a hypothesis.

**Corollary for reading revived output:** when restored code disagrees with what you measured
independently, suspect the code's inputs before you suspect your measurement — the code has been asleep
while the world moved.

## 3. Prove it runs the way production will — no path hack

**A fix that requires an env var or `PYTHONPATH` on every invocation is not a fix; it is a note-to-self you
will forget.** After editing, start the service with a **clean environment** — explicitly strip the variable
you used while debugging — and confirm it comes up:

```bash
env -u PYTHONPATH <venv>/bin/python3 -m uvicorn api.server:app --host 127.0.0.1 --port <port>
```

If it only runs with the hack, the fix is incomplete.

## 4. Extensibility: a SUBJECT is a file, never an engine edit

When the service carries a hardcoded list or an `if title == ...` ladder, **every future addition edits
core logic** — and each edit can break the ones before it. Move the content into a data file and read it:

```python
items = _load_json("catalogue.json").get("items", [])
```

- **Adding a subject = adding an entry to a file.** No code change, no regression risk, and a non-author
  can do it.
- **A missing or malformed data file yields an empty collection, never an exception** — the service keeps
  serving and the catalogue degrades to empty.
- **Sort data-driven output deterministically** (by date, then name) so response order does not depend on
  file order.
- **Require the reasoning field, not just the verdict.** A data-driven entry that answers with a bare value
  invites fabricated entries; make the entry carry its own justification so a bad one is visible on sight.

## 5. Lookup keys need normalization AND an alias map

The same entity arrives spelled many ways. Normalize both the stored keys and the query, then map known
variants:

```python
def _normalize(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
```

Aliases go in the data or a small map beside it — `"gta 6"`, `"gta vi"`, `"grand theft auto vi"` all
resolving to one key. **Never rely on the caller spelling it the way you stored it.**

## 6. An unmatched key returns UNKNOWN — never a guess

**A lookup that invents an answer to look complete is worse than one that reports it has nothing.** When
nothing matches, return an explicit unknown verdict with low confidence and say what input would produce
one. A guessed verdict is indistinguishable from a real one to the caller, and it is the single most
damaging thing this class of service can do.

## 7. Verify the negative path, not just the happy one

Test the miss explicitly — an unmatched key must return the honest UNKNOWN, and the data-driven path must
return the seeded entry — **before** reporting the service revived. A check that only ever exercises the
path you just seeded proves nothing about the one that fails.

## 8. Stopping it: verify the PORT, not the process

Two traps, both producing a false "clean":

- **Killing the parent does not kill the worker.** A dev server spawns a child that keeps serving after the
  parent is signalled. Re-probe the **port** — a free port is the only proof:
  ```bash
  curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 http://127.0.0.1:<port>/health   # 000 = nothing listening
  ```
- **Grepping `ps` for a service name matches your own shell command.** An innocent check reports "N
  processes still alive" against itself. Bracket the first character (`[u]vicorn`) and confirm with the port
  probe rather than trusting the count.
- **`pkill -f <pattern>` matches your own command line — and kills your shell.** The pattern appears in
  the command performing the kill, so the kill is applied to itself first; the session dies with a
  SIGTERM and it looks like an external shutdown. **Filter on the process NAME/`comm`, never a bare
  pattern**, and exclude the current shell:
  ```bash
  for pid in $(ps -eo pid,comm,args --no-headers | awk '$2=="python3" && /<unique-marker>/ {print $1}'); do
      kill "$pid"
  done
  ```
  Confirm with the port probe afterwards — a clean process list is not proof the port is free.

**A test instance you leave listening is litter on a shared host** — stop it and prove it stopped.

## 9. A front door is not its backends — the whole-fleet case

**A healthy gateway, proxy, or API front door proves nothing about the services behind it.** Before
concluding anything about a service layer, separate the two:

- A **price challenge / auth challenge / 402 / 401 / handshake** is issued by the *front door*, before
  any backend is contacted. It is an advertisement, not a health signal.
- A **health endpoint on the front door** reports on the front door.
- The only evidence a backend exists is a probe that reaches **its own process** — a TCP connect to its
  port, then a real request.

**Symptom that should trigger this section:** every route prices/promises correctly, the gateway's own
status page says healthy, and *nothing* is listening on any backend port — on the host **and** inside the
front door's container.

### 9a. Find the PORT AUTHORITY before writing a launcher

The **gateway's route table is the authority, not the service sources.** Service sources drift, and two
services can declare the *same* port after independent edits — a launcher built from the sources then
starts both, one silently shadows the other, and both report "started fine".

```bash
grep -n -A40 'BACKEND_ROUTES = {' <gateway>/server.py    # the authority
```

Pin the port **explicitly on the command line** so a source's drifted default cannot move a service.

### 9b. Find out how the front door is networked before choosing a fix

Do not theorise about *why* loopback stopped resolving — **read the network mode**:

```bash
docker inspect <front-door-container> --format '{{.HostConfig.NetworkMode}}'
```

- `host` — the container's `127.0.0.1` **is** the host's loopback. A gateway calling `127.0.0.1:<port>`
  reaches host-level services directly, and a *host* port scan is a valid probe.
- `bridge` — `127.0.0.1` inside is the container itself; host services need a shared namespace
  (`--network container:<name>`) or an addressable name.

**A port refusal on the host AND in the container means the services are simply not running.**
"Networking changed" cannot explain a host-side refusal — if the services existed on the host, the host
probe would have answered. State *"they are absent"* and stop asserting a cause you have not measured.

### 9c. Prefer an image that already has the dependencies

When the host interpreter lacks the service stack (`fastapi`, `uvicorn`, …) **do not install into the
agent's own environment first.** If the front door runs that stack, its image already has it:

```bash
docker run --rm --entrypoint python3 <front-door-image> -c 'import fastapi,uvicorn,httpx; print("OK")'
```

Run each backend as a container from that image, with the front door's network mode, mounting the service
source read-only. This avoids installing packages, avoids editing a vendor image that gets replaced on
update, and avoids the shared-namespace coupling that orphans sidecars when the front door is recreated.

```bash
docker run -d --name <svc> --network host -v <src-dir>:/svc:ro -w /svc \
  --entrypoint python3 <image> -m uvicorn <module>:app --host 127.0.0.1 --port <port>
```

**⚠️ `python3 -m uvicorn` is the reliable entry** — it pins host and port, so the launcher is the
authority rather than each source's `__main__` block.

### 9d. Preflight every source before launching any

Three defects make a service look broken when the *command* was wrong:

- **\(app\) must exist at module level.** `grep -c '^app *= *FastAPI(' <src>` — `uvicorn mod:app` needs it.
- **Package-relative imports need the package path.** A module doing `from . import sibling` must be run
  as `pkg.module:app` with the working directory at the package's **parent**, not `module:app`.
- **A data-dir default may point at a dead root.** `grep -n 'os.environ.get' <src>` — a default like
  `/root/vaults/...` that no longer exists starts fine and then writes nowhere or raises on first write.
  Set it explicitly via the env var the source already reads.

### 9e. Prove ONE, then the rest, then the whole set

Start a single service, curl its own health, confirm real JSON — **then** launch the rest, **then** loop
over every port. A launcher proven on one service and guessed for nine is a batch of nine unknowns.

### 9f. Two caveats to state, not bury

- **Provenance.** Sources recovered from a public mirror are a **functional** restore, not a production
  blessing — commits are not pinned and the code is unaudited. Say so; do not let a green health check
  imply more than it proves.
- **Terms can stop a service the code cannot.** A backend may depend on a third party whose terms forbid
  your use. A service is only as sellable as *every* upstream it calls — so audit upstreams **per source,
  not per service**, and expect a multi-source service to be partially usable.

**The durable fix is a readiness gate at the front door:** it must refuse to issue a price challenge for
a backend that is not up, so a dormant service can never again be advertised to a paying caller. See
`verification-vantage` for the fail-closed gate rules.

## Pitfalls

- **Scoping a rebuild from a symptom.** "Never worked" and "won't start" are cheap to diagnose and
  expensive to assume. The first exception is the cheapest evidence in this class.
- **Trusting a revival because it runs.** Restored code pointed at a dead feed produces a confident,
  clean, wrong answer with no error anywhere. Freshness-gate every input (mtime AND the file's own
  internal timestamp) and degrade to UNMEASURED, never to zero, before reporting what it says.
- **Reading a component's silence as agreement.** An unreadable input and a agreeing input both produce
  silence in a speak-only-on-disagreement design; report `UNTESTED` and `no dissent` as different states.
- **Replacing one hardcoded path with another.** The next layout move breaks it again; resolve relative
  with an override.
- **Accepting a fix that needs a debugging flag to work.** Prove it under a clean environment before
  calling it done.
- **Editing the engine to add a subject.** That is how a service with three subjects becomes one nobody
  dares touch.
- **Reporting "clean" from a process list.** Verify by port, and bracket your own grep.
- **Treating the front door's health as the backend's health.** A challenge response or a gateway status
  page is generated *before* any backend is contacted. Only a probe that reaches the backend's own port
  is evidence it exists; every route can price perfectly while nothing is listening anywhere.
- **Building the launcher from the service sources.** Ports drift and two services can claim the same one.
  The gateway's route table is the authority — pin the port on the command line.
- **Asserting a networking cause without measuring it.** Read the container's network mode before blaming
  connectivity, and remember a host-side refusal cannot be explained by container networking at all.
- **Installing the service stack into the agent's own environment first.** If the front door runs that
  stack, its image already has it — run from there and leave the agent's environment alone.

## Related

- `lost-artifact-recovery` — when the code is genuinely gone rather than merely unrunnable.
- `source-of-truth-verification` — confirm which copy is authoritative before editing it.
- `verify-after-every-action` — read the state back after every change.
- `verification-vantage` — a check may only be trusted for the question it actually asks; the fail-closed
  readiness gate that keeps an unservable service from being advertised.
