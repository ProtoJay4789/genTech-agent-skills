# Container Update Protocol — the engine IS the image

When a Hermes seat runs as a **Docker container on a published image** (not a git checkout), the update
mechanics differ from bare metal in five ways that change the whole procedure. Measured on a host-provider
image (`ghcr.io/<provider>/...:latest`), not upstream. **The parent SKILL.md's `hermes update` / `systemctl`
/ `/root/.hermes` steps do NOT apply here — this file replaces them.**

## The five differences

| Bare-metal assumption | Container truth |
|---|---|
| `hermes update` applies | **It refuses.** `/opt/hermes` is a published image — no `.git`, not writable by the seat's uid. There is no working tree to pull into. |
| You own the venv | `/opt/hermes/.venv` is baked into the image. A new engine means a **new image**, not a patch. |
| `systemctl` manages services | No systemd. Services are **s6**: `s6-svstat /run/service/<name>`, `ls /run/service`. |
| State lives in `~/.hermes` | State is a **host bind mount** → `/opt/data`. `/` is the overlay the recreate replaces; `/opt/data` survives by design. |
| The update is the agent's action | The update is a **host action**. The seat runs uid 10000 and has no Docker socket → **an agent cannot perform the swap.** |

## Procedure

**0. Know which image you're on.** `docker inspect <c> --format '{{.Config.Image}}'` is the only authority.
Pull what the box is RUNNING — a provider's own build, not `nousresearch/...:latest`. Pulling upstream swaps
*distributions*, not just versions.

**0.5 Does an update exist? Ask the REGISTRY, not PyPI.** Inside the container there is no `git fetch`, so the
only honest question is "what tags has the registry published since my build?".

```bash
hermes --version                      # installed, e.g. v0.22.6 (2026.9.24) upstream f0d94882
curl -s "https://hub.docker.com/v2/repositories/<owner>/<repo>/tags?page_size=8&ordering=last_updated" \
 | python3 -c "import sys,json;[print(t['name'],t['last_updated']) for t in json.load(sys.stdin)['results']]"
```

- ⚠️ **PyPI is the wrong index — `hermes-agent` there is a DIFFERENT project.** It published `0.19.0` while the
  engine was running `v0.22.6`; comparing the two reports the fleet as *three versions ahead* and hides a real
  release published the day before. **Never resolve "is there an update" from a package index the install never
  came from** — check the registry the image actually lives in.
- **`-desktop` / `rc.*` tags are not the seat's rail.** Read the tag that matches the running image's
  distribution, and report the published timestamp so the operator can judge "how new is new".

**1. Snapshot for rollback.**
```bash
docker exec <c> /opt/hermes/.venv/bin/hermes backup -q -l pre-<new>
```

**2. Pull, then read the image's build stamp BEFORE recreating.**
```bash
docker pull <image>
docker run --rm --entrypoint /bin/cat <image> /opt/hermes/install-stamp.json
docker image inspect <image> --format 'created = {{.Created}}'
```
- ⚠️ **The naive `docker run --rm <image> --version` is a trap** — the image's ENTRYPOINT is the s6 init, so
  it swallows the flag and **starts the whole gateway** (its own throwaway volume, sitting in the terminal).
  Use `--entrypoint /bin/cat` on the stamp.
- ⚠️ **Do NOT read `hermes_cli/__init__.py` for the version** — it holds a lazy `__version__` and a **stale
  `__release_date__`**, so it reports the SAME release date as the running engine against a genuinely newer
  image and sends the run to a false STOP. The stamp's `baseVersion` is the only honest source.

**Decision gate:** stamp `baseVersion` newer than the running engine → proceed. Same → **STOP**; no update
exists and recreating only restarts the same engine.

**3. Record what the compose file does NOT hold, then recreate.**
- **Launch args** — a lost `--host/--port` silently drops the dashboard to `127.0.0.1`. Check
  `docker inspect <c> --format '{{.Config.Cmd}}'`; an EMPTY cmd means there is nothing to lose.
- **The binds** — the `/opt/data` bind mount is why state survives.
```bash
docker compose -f <compose> up -d --force-recreate
```

**4. Settle, THEN audit.** Wait for the gateway to show `up` (~60–90s), then:
```bash
docker exec <c> python3 <vault>/scripts/post-swap-audit.py --diff
```

## Two changes, two windows

**A version jump and a config change are two variables — never put both in one restart.** When a rail/provider
change is already staged and unproven, a plain restart proves the config against the code that was already
running; a recreate proves the new code against everything at once. If it breaks, you cannot say which change
did it.

- **Order:** restart for the config → verify the new provider is actually the one serving → *then* schedule the
  image swap in its own window, with its own backup and its own rollback tag.
- **A newly published image is not a reason to hurry it.** Report the age of the release in the answer ("published
  17 hours ago") and recommend the swap as a separate, planned step when a live config change is mid-flight.
- **Keep a rollback tag before and after the swap** (`docker tag <current-image> <repo>:rollback-<old-version>`).
  The tag is the entire recovery; without it the only way back is a re-pull you no longer control.

## Pitfalls

- ❌ **Reading the audit within ~60s of `up -d`** — it FALSE-flags `PORTS LOST` and a missing pid while
  services are still binding. **Wait until the gateway shows `up`.** A port "lost" inside the first minute is
  a boot artifact, not a regression.
- ❌ **Running `hermes update`.** It refuses in-container — that is by design, not a permissions bug to work
  around.
- ❌ **Assuming the running image == upstream.** Read `.Config.Image` first; the provider's build is a
  different distribution.
- ❌ **A silent watcher DM is not proof the seat got it.** The vault file is the delivery of record; the DM is
  only a wake.
- ❌ **Answering "are we updated?" with "no" because a restart was pending.** A pending restart is a *config*
  reload; the version question is answered by the running build vs the registry. They are different answers and
  conflating them tells the operator the engine is current when it is a release behind.
