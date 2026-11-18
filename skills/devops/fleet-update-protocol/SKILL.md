---
name: fleet-update-protocol
description: "Use when a fleet-wide engine update is prepped or audited."
version: 1.0.0
author: gentech
category: devops
tags: [update, fleet, changelog, triage, checkpoint, audit, drift, hermes]
---

# Fleet Update Protocol

Coordinating an engine update across a multi-seat fleet. **Related but distinct:** `safe-update-restart`
owns the restart *mechanics* (unit topology, launch args, verification checklist); `hermes-update-assessment`
owns the changelog-filtering *lens* for a single consumer. This skill owns the **fleet coordination**: who
reads what, in what order, and what is audited afterwards.

## The governing idea

**An engine update is not only a risk to audit — it is a delivery of features to read for.** One commit range
carries work suited to a content lane and work suited to a capital lane. A fleet that only audits for
breakage halves the value of every update.

## PHASE 1 — PREP

**1. Fetch the changelog ONCE, centrally.** Write a digest with two parts: the upgrade notes as **RISKS**, and
**a block per department** as raw material. No seat re-fetches or re-parses the same page.

Measure the real gap with the compare API against **our own tag**:
```bash
curl -s -H 'Accept: application/vnd.github+json' \
  https://api.github.com/repos/<org>/<repo>/compare/<our-tag>...<target-tag>
```
- ⚠️ **Our release tag usually does NOT match the version string we report.** A build reporting `v0.21.5`
  published under tag `v2026.9.24`; comparing against `v0.21.5` returns `Not Found`. Read the tag list — do
  not conclude the repo is unreachable when only the tag name is different.
- ⚠️ **Never quote the release's own headline count as our gap.** A release body describes the range *since
  the previous major* ("~24,200 commits since v0.21.0"); our actual jump is the compare number and can be
  roughly half. Quote the measured gap.
- The compare's `ahead_by` is the number that matters. `files` is page-limited (300) — never sum it and call
  it the diff size.

**2. Every seat TRIAGES the digest through its OWN lens** — *"what in this update helps MY lane, and what
should we adopt?"* — and **files it to the brain BEFORE the swap.**
**Why before:** a restart wipes memory and the brain survives. Triage written after the wipe is worthless;
**the wipe is the forcing function that makes the read happen at all.**

**3. Require a decline list.** A triage that adopts everything is not a triage. Each seat names what it is
**not** taking and why. Real output from one run: a seat refused the language catalog, onboarding and the
plugin catalog as out-of-lane, and re-classified an upstream *feature* (reasoning replayed by default) as a
**cost** on its long turns rather than a gift. That judgement is the deliverable — not coverage.

**4. Expect the lenses to disagree — that is the signal.** One changelog produced three non-overlapping
findings: the content lane found the interactive-takeover feature that unblocked its whole automation wall;
the capital lane found reasoning replayed across compaction; HQ found the fixed-prompt token cut that lands
on the most expensive line item. None was visible to the others.

**5. Checkpoint: finish-or-park → save/log → VERIFY by reading back → ACK.** Dispatch the ask to
`01-HANDOFFS/gentech-to-<seat>/` **and** wake with a peer DM. Every ACK must state: what was finished ·
what was parked **and where to resume** · the seat's top 1–3 department findings · that it was **filed** (not
"sent") · **what it was verified against** (a measurement, not a memory) · that it is **NOT** a restart
authorization. Only when all seats ACK does the swap run.

## PHASE 1.4 — a VERIFIED backup, taken before the window opens

**A recreate is the one operation that can lose everything the fleet knows, so the backup is part of the prep,
not an afterthought in the runbook.** Two rules decide whether it is a backup at all:

- **Use the database's own backup call, never `cp`, on a live SQLite file.** `sqlite3 <src>` → `con.backup(out)`
  (or `VACUUM INTO`) takes a consistent snapshot under the writer's lock; copying the file while a session is
  writing can capture a torn page set that opens fine and is silently wrong. Per-seat `state.db` is a live DB as
  long as any gateway is running.
- **Prove it by opening it, not by its size.** For each copy: count tables and run `pragma integrity_check`; a
  file that is the right number of megabytes and fails to open is the worst possible artefact, because the size
  is the part a hurried reader checks. Record the integrity result and the byte count side by side.

```python
con = sqlite3.connect(src); out = sqlite3.connect(dst)
con.backup(out); out.close(); con.close()
# then, per file: table count + `pragma integrity_check` == 'ok'
```

**Back up the CONFIG the recreate needs to reproduce, not only the data:**

- `cron/jobs.json` (the job set is not in `state.db`), and any state the jobs read.
- The **`docker inspect` essentials** — `.Config.Image`, `.Mounts`, `.HostConfig.PortBindings`, `.Config.Env`,
  `.HostConfig.RestartPolicy.Name`. A recreate that loses the bind mount comes back as a fresh install with an
  empty brain, and no backup of the brain helps if the new container never mounts it.
- Credential **file names and modes**, never their contents.

- **Put the backup outside the tree the swap replaces.** A path inside the container being recreated may be
  exactly what disappears; a directory under the bind mount survives, and so does anything on the host.
- **State the headroom for the new image** in the same breath (`df -h`), so the pull cannot fail for a reason the
  operator discovers halfway through.

## PHASE 1.5 — WATCH (know a new image exists without going looking)

The phases above coordinate a swap you have *already decided* to make — they do nothing to tell you a newer
engine was **published**. That discovery gap is how a fleet runs months behind without knowing. Close it
with a stamp watcher that fires only on change:

- **The honest version source is the IMAGE's build stamp, not a source file:**
  `docker run --rm --entrypoint /bin/cat <image> /opt/hermes/install-stamp.json` → read `baseVersion`.
- ⚠️ **Never read `hermes_cli/__init__.py` for the version.** As of v0.22.x that file holds a **lazy**
  `__version__` (no literal) and a **stale `__release_date__`** — it reported the SAME release date as the
  running engine against a genuinely newer image, and sent the run to a **false STOP**. The install stamp
  is the only honest source.
- ⚠️ **Never read the version with `docker run --rm <image> --version`** — the image's ENTRYPOINT is the s6
  init, so it swallows the flag and **starts the whole gateway** (its own throwaway volume, sitting in the
  terminal). Use `--entrypoint /bin/cat` on the stamp.
- Compare against the running container's stamp; wake the coordinator **only when `baseVersion`/`commit`
  differs**. **Silence-gated** — a watcher that reports "no change" every day trains the reader to ignore it.
- The watcher needs host Docker access → run it as a **no-agent cron or a host action**, never from inside a
  seat. `scripts/image-watch.sh` is the ready form.
- ⚠️ **A watcher that runs on the HOST must locate the bind-mount SOURCE, not the container path.** The
  script is authored while looking at `/opt/data` (inside the container) but executes where that path does
  not exist — so it silently probes nothing and reports "no change" forever. Resolve the host side from
  the running container's own mount (`docker inspect <c> --format '{{range .Mounts}}…'`), then fall back
  to a known path. **A path that does not exist and a probe that found nothing print the same thing** —
  so make the script fail LOUDLY when it cannot locate its tree, rather than exiting quiet.
- **You do not need Docker — or the host — to learn a published image's version.** When the seat cannot
  reach the Docker socket and the host is not yours, read the build stamp straight out of the *registry*
  over HTTPS: anonymous pull token → manifest → the layer whose history entry wrote the stamp → extract it
  from the tar. Full recipe and pitfalls: `references/registry-image-introspection.md`. **This is the
  docker-free form of the same check, and it is how "is this update actually real?" gets answered from
  inside a container** — the question the WATCH phase exists to answer.

## PHASE 2 — THE SWAP

Usually a host action, not an agent action. On a published-image install `hermes update` **refuses** outright
(no `.git`, not writable) — the swap is a container recreate. Mechanics: the `safe-update-restart` skill, and
for the container-specific order its `container-update-protocol` reference file.

**When several seats live in ONE container, the "fleet update" is a single compose action — resist designing
a propagation scheme for it.** Measured topology: one container, one image, one bind mount, and `s6`
supervising a gateway slot per seat plus a default slot and the dashboard. So:

```
cd <compose project dir>
docker compose pull
docker compose up -d
```

`pull` only fetches (the running fleet keeps answering); `up -d` is the swap, and the supervisor brings every
slot back on the new image **together**. There is nothing to propagate between seats: **skills, memory and
config live in the profile tree; the engine version lives in the image.** Copying one seat's profile to
another moves configuration, never the engine. A user asking "can the others update off the coordinator?" is
asking for a fleet-wide recreate, which is what this already is — say so instead of building a second
mechanism. Confirm the topology rather than assuming it: `docker inspect <c> --format '{{.Config.Image}}'`
plus the supervised slot list (`ps -eo args | grep s6-supervise`).

## PHASE 3 — POST-SWAP SYSTEM AUDIT

Not "does it work" — **"did anything of OURS move?"** Diff against the pre-swap record:

1. the **service/layout shape**
2. every profile still serves; a live message lands
3. the **peer rail still answers** (`hermes peer dm`) — the rail's front door is the api_server, and a
   recreate is exactly when its key/host posture can change
4. launch args survived — a lost `--host/--port` silently drops a dashboard to `127.0.0.1`
5. cron still fires (one job lands)
6. **every default that flipped silently** per the upgrade notes, confirmed at its ACTUAL value here
7. our own customizations that touch a changed surface
8. the **token posture — both directions**: prompt trimming saves, replayed reasoning costs. Measure; never
   assume either.
Then **file the delta** — what moved, what didn't, what we are re-adapting.

## Rules that cost time to learn

- **A checklist published in the digest is not a check performed.** The six pre-swap items (is a retired
  config key set anywhere, does any script call a removed command, what are the process ids and launch args)
  are **absence probes** and process probes — a search that must return nothing, and a live process list — they read as done because they sit in a tidy list, and the ACK
  that follows them is a lie if nobody ran them. Ship the checklist as **commands**, run every line in the
  same window, and paste the output into the ACK. The coordinator must run its OWN checks before it can
  accept anyone else's.
- **The dispatch is a record too — stamp it from the clock, never from a plan.** `date -u` at write time and
  reconcile the stamp to the file's mtime afterwards, **in every copy** (each seat's lane gets its own copy,
  so one wrong stamp is four wrong records, and the seats cite it). A stamp that reads later than the mtime
  cannot be true, and a `~HH:MM` estimate is exactly how that happens.
- **Record the shape BEFORE you change it — and make it true of the LAYOUT, not just the PROCESS.**
  `multiplex_profiles: true` was set with a single gateway process running, while the service tree *still*
  carried five gateway slots (one default + one per seat) alongside the orchestrator and dashboard. So "we
  already run one gateway per machine" was **true of the process and false of the layout** — and the
  fold-into-multiplex was exactly what the upgrade touched. Without the pre-swap record, post-swap drift is
  indistinguishable from intended migration.
- **A silent wake is not a failed delivery — check the lane, not the reply.** In one run every seat's peer
  DM returned nothing or timed out (exit 124) while all seats had already filed their ACKs. Verify delivery
  by the seat's own activity and the file on disk, never by the reply. And never report a wake that did not
  land.
- **An ACK covers ONE event and expires with its window.** A swap that slips needs a fresh round — do not
  carry ACKs forward.
- **Checkpoint asks must demand a FINISH, not a save.** Read the returns for **named resume points**; a
  parked item with no resume file is a loss with a timestamp — send it back before the swap.
- **A seat may legitimately return "nothing was in flight."** The rule tightens what an ACK *means*; it does
  not invent work to save.
- **Grade the returns, do not just collect them.** Three seats can all answer in the right shape and still
  differ hugely in evidence quality — the strong ones give digests and read their own files back, the weak
  ones restate the request.
- **Normalise volatile fields OUT of the post-swap comparison — a check that is red when nothing happened
  is a check the reader learns to skip.** Uptime counters, durations, ages and timestamps drift between ANY
  two reads, so diffing them raw reports "changed" on every single run and buries the one line that matters.
  Compare **state + pid only**; keep the raw value beside it for the human. This is what stops a real
  regression from being waved through as more noise. **The same principle governs WHEN you read, not just
  WHAT you compare:** an audit run seconds after a recreate FALSE-flags `PORTS LOST` and a missing pid while
  services are still binding — a port "lost" inside the first minute is a boot artifact, not a regression.
  **Read the audit only after the gateway shows `up`.**
- **A post-change check with no pre-change reference proves nothing.** "Here is what it looks like now" is
  not verification — capture the baseline *while the old box is still up*, or the post-swap diff cannot
  distinguish drift from intended migration. `scripts/pre-post-swap-baseline-diff.py` is the reusable form.
- **Count STABLE artefacts in the baseline, never every file in a directory.** Counting all files under a
  skills tree reported "+2 skills" after a clean recreate — they were two transient `.locks/*.lock` files
  created by merely READING a skill, plus a usage-ledger touch. A census that moves when nothing was edited
  manufactures drift on every swap. Count the meaningful unit (`SKILL.md`), and keep identity (names) beside
  the count so a later reader can tell *which* item appeared instead of only how many.
- **Measurement commands are read-only in EFFECT only — audit what they PRINT before running them.**
  A Step-0 probe run to find the container name (`env | grep -iE 'image|tag|hermes|docker|vnc'`) surfaced
  `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` straight into the transcript. **A secret's variable name need not
  resemble a secret — the pattern decides what leaks, not the value's sensitivity.** Check for a value's
  PRESENCE with a boolean or an exact-key test, never by piping a broad `env`/`printenv` through a filter.
  A credential that reaches the chat is a **rotation** event, not merely a redaction one — the chat copy
  outlives the DB row you scrub.
- **Where our own notes and the host's own config disagree, the host wins — and resolving that is step 0.**
  Our prep doc and the image's bundled compose template disagreed on both the container name and the image
  tag. The agent cannot see the host, so the runbook's FIRST step must be a read-only `docker inspect` that
  settles it. Bake the uncertainty into the runbook as an instruction; do not paper over it with a guess.
- **The image reference may not be the upstream one — pull what the box is RUNNING, not what the docs say.**
  `docker inspect <c> --format '{{.Config.Image}}'` is the only authority. A runbook that named
  `docker pull nousresearch/hermes-agent:latest` met a box running
  **`ghcr.io/hostinger/hvps-hermes-agent:latest`** — the host provider's own build. Pulling upstream would
  have **swapped distributions, not updated the engine**; the container would have come back on different
  software. Measure the reference before writing the pull line — a wrong one is not a failed update, it is a
  different product.
- **A runbook is executed by a HUMAN — make every command copy-paste safe.** Substitute every `<PLACEHOLDER>`
  with the measured value before sending; a literal `<CONTAINER>` pastes as a filename. Keep command blocks
  **pure ASCII**: a circled numeral or an em-dash inside one lands as
  `bash: $'\342\221\240': command not found`. Each one costs a round trip and teaches the operator the
  runbook cannot be trusted verbatim.
- **A command block carries COMMANDS ONLY — no annotations, no arrows, no "then wait" notes.** A block like
  `docker compose pull   → fetch the image` pastes `→ fetch the image` as arguments and dies with
  `no such service: →`; prose placed inside the fence is prose the shell will execute. Put every explanation
  **outside** the block, one command per line, and re-read the block as if you were pasting it blind before
  sending. When the operator comes back with a paste error, that is not a question — **resend the same block
  with the measured values substituted, in full**, rather than explaining what went wrong.
- **An image refresh is not always the same operation as an image upgrade — read the tag's SUFFIX before
  pulling.** Published images ship in classes distinguished by a tag suffix that changes the feature set,
  not just the version. Pulling the plain tag onto a host running a suffixed variant silently *removes*
  features (a screen/X stack the bots depended on stops starting). Probe the container for the class
  markers, keep any suffix you find, and when the choice is refresh-vs-change-class, **name both and let the
  operator pick** — they differ in blast radius, not in recency.

## References and scripts

- `references/fleet-update-run-worked-example.md` — a full measured run: the commit gap, the ACK returns, the
  department lenses, and the pre-swap findings that made the post-swap diff meaningful.
- `scripts/pre-post-swap-baseline-diff.py` — the Phase-3 audit as a runnable probe: `--capture` the shape
  BEFORE the swap, `--diff` it afterwards. It encodes the volatile-field normalisation above, so re-running
  it cleanly says *"nothing of ours moved"* instead of crying wolf.
- `scripts/image-watch.sh` — the Phase-1.5 WATCH probe. Pulls the image, reads its install stamp, and exits
  **10 only when the commit changed** (silent otherwise). Run it as a no-agent cron; it needs host Docker.
