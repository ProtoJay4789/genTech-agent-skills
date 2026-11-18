---
name: fleet-update-container
description: "Update a Hermes agent running as a Docker container (s6 init, published image, host bind mount). The container-correct companion to safe-update-restart: why `hermes update` refuses in-container, how to read the real version from the image's install stamp, the boot trap that false-flags lost ports, and the four-phase prep→watch→swap→settle-audit sequence. Use when the agent runs from an image, not a git checkout."
version: 1.0.0
author: Gentech
tags: [update, docker, container, s6, image, hermes, deployment, verification, safety]
license: MIT
---

# Fleet Update — Container Edition

## When to Use
- **Your agent runs as a Docker container**, not a bare-metal install — you have no writable
  `/opt/hermes`, no `systemd`, and `/opt/data` is a host bind mount.
- You are about to follow `safe-update-restart` and the commands look wrong for your box.
- You want to know **whether a newer image even exists** before touching anything.

> **Read `safe-update-restart` first — then come here.** That skill owns the *general* restart doctrine.
> This one owns the **container-specific facts**, and several of that skill's commands **do not work
> in a container**. If your box is bare metal (you can `cd /usr/local/lib/hermes-agent` and it has a
> `.git`), use `safe-update-restart` and stop here.

---

## The one thing to understand first

**In a container, the engine IS the image.** On bare metal a restart reloads a process. In a container
an update is a **container recreate** — a new image is pulled and the container is rebuilt on it.
That changes the whole shape:

- **Your state survives by design** — it lives on a bind mount (`/opt/data`), which the recreate does
  NOT touch. `/` is the overlay layer that *is* replaced.
- **The engine cannot be patched** — `/opt/hermes/.venv` is baked into the image. A new engine means a
  new image, always.
- **The update is a HOST action** — an agent inside the container cannot do it. It cannot reach the
  Docker socket (uid 10000, denied), cannot write the install tree, and `hermes update` **refuses
  outright** (published image, no `.git`, not writable).

---

## Five assumptions that break in a container

| # | The bare-metal command | What actually happens in a container |
|---|---|---|
| 1 | `hermes update --yes` | **Refuses.** Published image — no working tree to pull into. Not a permissions bug. |
| 2 | `cd /usr/local/lib/hermes-agent` | Doesn't exist. Install is `/opt/hermes`, read-only to you. |
| 3 | `systemctl is-active ...` | **No systemd.** Services are **s6**: `s6-svstat /run/service/<name>`, list with `ls /run/service`. |
| 4 | state in `~/.hermes`, backup to `/root/...` | `/root` is unreadable; state is the **bind mount `/opt/data`**. |
| 5 | "run the update" is your action | It's the **host operator's** action — `docker compose up -d --force-recreate`. |

---

## THE FOUR PHASES

```
PREP  →  WATCH  →  SWAP  →  SETTLE-AUDIT
(agents)  (cron)   (host)   (agent, ~90s after)
```

**PREP** — the coordinator fetches the changelog once, each seat triages it through its own lane,
finishes or parks at a named resume point, saves and logs, then ACKs. **Only when all seats ACK does
the swap run.** An ACK covers ONE event and expires with its window — it is NOT a standing
authorization.

**WATCH** — a cron that detects a newly published image. See "Knowing an update exists" below. Silent
unless something changed, so it never trains you to ignore it.

**SWAP** — the host operator's hands. See "The swap" below.

**SETTLE-AUDIT** — the agent runs the audit against the pre-swap baseline ~90s after the recreate.
**A swap with no settled audit is not a finished update.**

---

## Knowing an update exists — the honest version source

**⚠️ NEVER read the version from `hermes_cli/__init__.py`.** As of v0.22.x that file holds a **lazy**
`__version__` and a **stale `__release_date__`** — even in a newer build. Measured 2026-10-21: reading
it reported the *same date as the running container* and would have sent us to a **false STOP.**

**The authoritative source is the image's install stamp:**

```bash
docker run --rm --entrypoint /bin/cat <YOUR_IMAGE> /opt/hermes/install-stamp.json
```
It prints `"baseVersion"`, the commit, and the build time. **Compare `baseVersion` to the running
container's stamp.** Newer → an update exists. Same → silence.

**⚠️ The naive `docker run --rm IMAGE --version` is a trap.** The image's ENTRYPOINT is the **s6 init**,
so `--version` is *swallowed* and the whole gateway service **starts** — a second gateway, its own
throwaway volume, sitting in your terminal until Ctrl+C. Always use `--entrypoint /bin/cat`.

---

## ⚠️ A RESTART IS NOT AN UPDATE — and the agent cannot do either

**Two different actions get confused constantly:**

| Ask | What it does | Who can run it |
|---|---|---|
| **restart** | new process, **same image** — reloads config (provider, model, hooks) | host shell |
| **update** | pull image + recreate — **changes the engine version** | host shell |

**Never answer "restart" with an update command, or vice versa.** A restart after a provider change picks
up the new provider; it will not move you to a newer version.

**And an agent inside the gateway CANNOT bounce it.** Measured 2026-11-17: the lifecycle command is
**blocked by a tool guard** — *"cannot restart or stop the gateway from inside the gateway process…
SIGTERM propagates to child processes."* The guard is correct: the script dies before it finishes, and
on a multiplexer it takes every seat down with it. **Do not retry it, do not route around it — hand the
operator a host command.**

**Corollary for a multiplexer host:** one gateway process serves every profile
(`http://127.0.0.1:8642/p/<profile>/v1`) over s6 services named `gateway-<seat>`. **A restart bounces
all seats at once** — which is usually what you want when a fleet-wide config changed.

## ⚠️ FIND THE CONTAINER NAME — DO NOT GUESS IT

**A compose-created container is `<project>-<service>-<n>`, so the stack directory name is NOT the
container name.** Measured 2026-11-17: the host path is `/docker/hermes-agent-wxt5/data`, the obvious
guess `hermes-agent-wxt5` **does not exist**, and the real name was
**`hermes-agent-wxt5-hermes-agent-1`**. The operator ran the guessed name three times and got
`No such container` three times.

```bash
docker ps --format '{{.Names}}\t{{.Image}}'
```

**Read the name off that output and paste it — never construct it.** While you are there, confirm the
image: **pull what the box RUNS.** Do not bounce sibling containers that merely share the name prefix
(an x402 gateway, a floor of `gt-*` services) unless that is the thing you were asked to restart.

## The swap

### 0 — Know which image you are actually on
```bash
docker inspect <CONTAINER> --format 'image={{.Config.Image}}'
```
**Pull the image the box is RUNNING.** It may be your host provider's own build
(`ghcr.io/<provider>/hvps-hermes-agent:latest`), not `nousresearch/hermes-agent:latest`. Pulling
upstream would **swap distributions**, not update the engine.

### 0b — ⚠️ THE IMAGE YOU TEST IS NOT THE IMAGE COMPOSE DEPLOYS (measured 2026-11-17)

**`docker compose pull` fetches the image named in the compose file — never the tag you pulled by hand.**
Measured: the pre-flight pulled and booted `nousresearch/hermes-agent:v0.23.2`, tagged the running image
for rollback, and took a full backup. The operator then ran `docker compose pull && docker compose
up -d` — and compose resolved **its own** `image:` line, a provider build
(`ghcr.io/<provider>/hvps-hermes-agent:latest`), landing the fleet on **v0.23.1**. **The entire
pre-flight was spent on an image that was never deployed, and the version that shipped had never been
booted.**

**Read the compose file's `image:` line BEFORE any pull or throwaway test, and if it differs from the
tag you intend to ship, that is the decision to surface — not a detail to discover afterwards.**

```bash
grep -nE '^\s*image:' <compose-file>        # what compose WILL deploy
docker inspect <CONTAINER> --format '{{.Config.Image}}'   # what is running now
```

**Two consequences that cost real time:**

- **An override is a distribution change, not an update.** Pointing compose at upstream replaces the
  provider's build; the provider's wrapper (entrypoint, env, dashboard wiring) goes with it.
- **Verify the CAPABILITY you upgraded for, not the version string.** The reason for this update was a
  new subcommand; after the swap, `hermes <cmd> --help` answered *"'check' is not a hermes command"* —
  a correct-install, correct-version, wrong-outcome result. **A version number that matches your target
  proves nothing if the feature you moved for is absent.**

### 1 — Snapshot first
```bash
docker exec <CONTAINER> /opt/hermes/.venv/bin/hermes backup -q -l pre-v<new>
```

### 2 — Pull, then read the stamp BEFORE recreating
```bash
docker pull <YOUR_IMAGE>
docker run --rm --entrypoint /bin/cat <YOUR_IMAGE> /opt/hermes/install-stamp.json
docker image inspect <YOUR_IMAGE> --format 'created = {{.Created}}'
```
Still the same version → **STOP.** There is no update; recreating only restarts the same engine.

### 3 — Capture what the compose file does NOT hold
```bash
docker inspect <CONTAINER> --format '{{.Config.Cmd}}'
```
If that prints `[]`, there are no launch args to lose and the recreate is safe. If it prints args
(e.g. dashboard `--host 0.0.0.0 --port 4860 --no-open`), **record them** — lose them and the dashboard
silently drops to `127.0.0.1` and becomes unreachable.

### 4 — Recreate
```bash
docker compose -f <compose-file> up -d --force-recreate
```

---

## ⚠️ THE BOOT TRAP — do not read the audit yet

**Measured 2026-10-21:** the settle-audit run ~4 seconds after `up -d` **FALSE-flagged**
`PORTS LOST: ['4860','8642']` and a missing gateway pid. Services were still binding. Ninety seconds
later: everything listening. **A port "lost" inside the first minute is a boot artifact, not a
finding.** Wait until the gateway shows `up` (`s6-svstat`) AND both ports answer — ~60s minimum —
before you believe any port reading.

---

## The settle-audit

```bash
docker exec <CONTAINER> python3 <audit-script> --diff
```
It diffs live state against the pre-swap baseline and prints, per check, **whether anything of yours
moved** — version, gateway pid, platforms, ports, config fingerprints, skill count, cron count, the
`/opt/data` mount. Capture the baseline **while the old container is still up**; a post-swap check with
no pre-swap reference proves nothing.

**Expect the s6 layout to change** on some upgrades — per-profile gateways folding into a multiplexer.
That's intended migration, not breakage. **File the delta** — what moved, what didn't, what you are
re-adapting. A swap with no delta filed is not complete.

---

## Pitfalls

- ❌ **Running `hermes update` in-container.** It refuses. Don't read the refusal as a broken install.
- ❌ **Reading the version from `hermes_cli/__init__.py`.** Lazy + stale. Use `install-stamp.json`.
- ❌ **`docker run --rm IMAGE --version`.** The s6 entrypoint eats the flag and starts a gateway.
- ❌ **Reading the audit within 60s of the recreate.** False "ports lost". Wait for the gateway up.
- ❌ **Pulling upstream instead of your own image.** Different distribution — you run the provider's build.
- ❌ **Testing a tag compose will not deploy.** `docker compose pull` resolves the `image:` line; a
  hand-pulled tag is a rehearsal for a different play. Read the line first.
- ❌ **Checking the version to confirm the update worked.** Check the **feature** you updated for — a
  correct version with a missing capability is the quiet failure mode.
- ❌ **Assuming an agent can run the swap.** uid 10000, no Docker socket, no writable install tree.
  **The swap is a host operator action.**
- ❌ **Skipping the pre-swap baseline.** "It's up" is not the question. The question is *what moved that
  we did not ask to move.*
- ❌ **Letting a silent DM stand in for an ACK.** A silent DM is not a failed delivery — verify by the
  seat's own activity and the file on disk. The vault is the delivery of record; the DM is only a wake.

---

## Verification
- **After a RESTART (config change), prove the new setting from the RUNNING process, not the file.**
  The file already said the new provider; that was never the question. Read the agent's own next
turn: `grep 'conversation turn' <profile>/logs/agent.log | tail -3` shows
  `model=… provider=…` — **the agent's own inference calls are the proof**, because they are the
  process actually using the rail. Also grep the same window for `fallback|403|1010` = 0 hits.
  **A config that says the right thing and a process that has not restarted is the failure mode this
  check exists to catch.**
- `install-stamp.json` `baseVersion` in the new container **changed** to the target.
- Gateway is `up` (s6) with a **new pid**; every platform `connected`.
- Both expected ports answer (dashboard + api).
- `/opt/data` mount unchanged; skill count, cron count, platforms all match baseline.
- The delta is filed and the rollback snapshot is recorded.

---

*Companion to `safe-update-restart`. Authored from a measured v0.21.5 → v0.22.2 container swap,
2026-10-21. The kit's `safe-update-restart` is the bare-metal procedure; this is the container one.*
