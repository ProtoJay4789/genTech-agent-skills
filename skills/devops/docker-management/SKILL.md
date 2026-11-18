---
name: docker-management
description: Manage Docker containers, images, volumes, networks, and Compose stacks — lifecycle ops, debugging, cleanup, and Dockerfile optimization.
version: 1.0.0
author: sprmn24
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [docker, containers, devops, infrastructure, compose, images, volumes, networks, debugging]
    category: devops
    requires_toolsets: [terminal]
---

# Docker Management

Manage Docker containers, images, volumes, networks, and Compose stacks using standard Docker CLI commands. No additional dependencies beyond Docker itself.

## When to Use

- Run, stop, restart, remove, or inspect containers
- Build, pull, push, tag, or clean up Docker images
- Work with Docker Compose (multi-service stacks)
- Manage volumes or networks
- Debug a crashing container or analyze logs
- Check Docker disk usage or free up space
- Review or optimize a Dockerfile

## Prerequisites

- Docker Engine installed and running
- User added to the `docker` group (or use `sudo`)
- Docker Compose v2 (included with modern Docker installations)

Quick check:

```bash
docker --version && docker compose version
```

## Quick Reference

| Task | Command |
|------|---------|
| Run container (background) | `docker run -d --name NAME IMAGE` |
| Stop + remove | `docker stop NAME && docker rm NAME` |
| View logs (follow) | `docker logs --tail 50 -f NAME` |
| Shell into container | `docker exec -it NAME /bin/sh` |
| List all containers | `docker ps -a` |
| Build image | `docker build -t TAG .` |
| Compose up | `docker compose up -d` |
| Compose down | `docker compose down` |
| Disk usage | `docker system df` |
| Cleanup dangling | `docker image prune && docker container prune` |

## Procedure

### 1. Identify the domain

Figure out which area the request falls into:

- **Container lifecycle** → run, stop, start, restart, rm, pause/unpause
- **Container interaction** → exec, cp, logs, inspect, stats
- **Image management** → build, pull, push, tag, rmi, save/load
- **Docker Compose** → up, down, ps, logs, exec, build, config
- **Volumes & networks** → create, inspect, rm, prune, connect
- **Troubleshooting** → log analysis, exit codes, resource issues

### 2. Container operations

**Run a new container:**

```bash
# Detached service with port mapping
docker run -d --name web -p 8080:80 nginx

# With environment variables
docker run -d -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=mydb --name db postgres:16

# With persistent data (named volume)
docker run -d -v pgdata:/var/lib/postgresql/data --name db postgres:16

# For development (bind mount source code)
docker run -d -v $(pwd)/src:/app/src -p 3000:3000 --name dev my-app

# Interactive debugging (auto-remove on exit)
docker run -it --rm ubuntu:22.04 /bin/bash

# With resource limits and restart policy
docker run -d --memory=512m --cpus=1.5 --restart=unless-stopped --name app my-app
```

Key flags: `-d` detached, `-it` interactive+tty, `--rm` auto-remove, `-p` port (host:container), `-e` env var, `-v` volume, `--name` name, `--restart` restart policy.

**Manage running containers:**

```bash
docker ps                        # running containers
docker ps -a                     # all (including stopped)
docker stop NAME                 # graceful stop
docker start NAME                # start stopped container
docker restart NAME              # stop + start
docker rm NAME                   # remove stopped container
docker rm -f NAME                # force remove running container
docker container prune           # remove ALL stopped containers
```

**Interact with containers:**

```bash
docker exec -it NAME /bin/sh          # shell access (use /bin/bash if available)
docker exec NAME env                   # view environment variables
docker exec -u root NAME apt update    # run as specific user
docker logs --tail 100 -f NAME         # follow last 100 lines
docker logs --since 2h NAME            # logs from last 2 hours
docker cp NAME:/path/file ./local      # copy file from container
docker cp ./file NAME:/path/           # copy file to container
docker inspect NAME                    # full container details (JSON)
docker stats --no-stream               # resource usage snapshot
docker top NAME                        # running processes
```

### 3. Image management

```bash
# Build
docker build -t my-app:latest .
docker build -t my-app:prod -f Dockerfile.prod .
docker build --no-cache -t my-app .              # clean rebuild
DOCKER_BUILDKIT=1 docker build -t my-app .       # faster with BuildKit

# Pull and push
docker pull node:20-alpine
docker login ghcr.io
docker tag my-app:latest registry/my-app:v1.0
docker push registry/my-app:v1.0

# Inspect
docker images                          # list local images
docker history IMAGE                   # see layers
docker inspect IMAGE                   # full details

# Cleanup
docker image prune                     # remove dangling (untagged) images
docker image prune -a                  # remove ALL unused images (careful!)
docker image prune -a --filter "until=168h"   # unused images older than 7 days
```

### 4. Docker Compose

```bash
# Start/stop
docker compose up -d                   # start all services detached
docker compose up -d --build           # rebuild images before starting
docker compose down                    # stop and remove containers
docker compose down -v                 # also remove volumes (DESTROYS DATA)

# Monitoring
docker compose ps                      # list services
docker compose logs -f api             # follow logs for specific service
docker compose logs --tail 50          # last 50 lines all services

# Interaction
docker compose exec api /bin/sh        # shell into running service
docker compose run --rm api npm test   # one-off command (new container)
docker compose restart api             # restart specific service

# Validation
docker compose config                  # validate and view resolved config
```

**Minimal compose.yml example:**

```yaml
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      # Password comes from the POSTGRES_PASSWORD secret, not the URL
      - DATABASE_URL=postgres://mydb_user@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### 5. Volumes and networks

```bash
# Volumes
docker volume ls                       # list volumes
docker volume create mydata            # create named volume
docker volume inspect mydata           # details (mount point, etc.)
docker volume rm mydata                # remove (fails if in use)
docker volume prune                    # remove unused volumes

# Networks
docker network ls                      # list networks
docker network create mynet            # create bridge network
docker network inspect mynet           # details (connected containers)
docker network connect mynet NAME      # attach container to network
docker network disconnect mynet NAME   # detach container
docker network rm mynet                # remove network
docker network prune                   # remove unused networks
```

### 6. Debugging reachability — in this order

When one container cannot reach another, or a host process cannot reach a container, **measure in this
order before changing anything**. Each step rules out a whole class of cause, and guessing at the wrong
one wastes the most time:

```bash
# 1. Which network is each side actually on?
docker inspect A --format '{{.HostConfig.NetworkMode}}'
docker inspect B --format '{{.HostConfig.NetworkMode}}'
#    host        -> its 127.0.0.1 is the HOST loopback
#    container:X -> shares X's network namespace (so X's 127.0.0.1 is shared)
#    bridge/custom -> its own loopback; reach peers by NAME on a shared user-defined network

# 2. Do they even see the same FILES? (mounts are per-container, and a matching
#    PATH does not mean a matching filesystem — one may be a volume, the other a bind mount)
docker inspect A --format '{{range .Mounts}}{{.Source}} => {{.Destination}}{{println}}{{end}}'

# 3. Is anything actually listening on the port?
docker exec A sh -c 'command -v ss >/dev/null && ss -lntp || netstat -lntp'   # inside
ss -lntp | grep ':PORT'                                                       # on the host
```

**A listener bound to `127.0.0.1` is reachable only from its OWN network namespace.** If two containers
must share a loopback file/port, share the namespace (`--network container:<name>`) or use `--network host`
on both. A service on the *host* and a container on a bridge network cannot see each other through
`127.0.0.1` no matter which port is published.

**For any service more than one container depends on, also check the restart policy** — a container with
no policy is gone after a reboot, and the mismatch between its lifetime and the lifetime of whatever
*reports* on it is silent:

```bash
docker inspect NAME --format '{{.HostConfig.RestartPolicy.Name}}'   # expect unless-stopped|always
```

**Starting a stack of services that must share an existing container's loopback.** When several
services have to answer the `127.0.0.1:<port>` map that an already-running container dials, in order:

1. **Read the CONSUMER's route/config table first — the port map belongs to the consumer, never to
   the services.** Two services can each declare the same default port in their own source and both
   start "fine", one silently unreachable. The consumer's table is the only authority; a launcher
   built from the services' own defaults produces a collision that looks like a healthy start.
2. **Reuse an image that already has the runtime dependencies** rather than installing onto the host.
   The consumer's own image usually has them by definition — it is running the consumer.
3. **Match the consumer's network mode.** If the consumer is `--network host`, run the services
   `--network host` too: their loopback is then the same loopback the consumer dials, with no
   sidecar-to-container namespace coupling that orphans when the consumer is recreated.
4. **Pin host and port explicitly on the command line** (`--host 127.0.0.1 --port N`). A service's
   internal default for either is a hint, not a contract.
5. **`--restart unless-stopped` at creation time**, not later — a stack started by hand vanishes on
   reboot while anything reporting on it keeps saying it is up.
6. **Override the entrypoint when the image declares one.** `docker run IMAGE <cmd>` runs `<cmd>` as
   *arguments to the image's ENTRYPOINT*, not as the process you asked for — with a
   `python3`-style entrypoint that can hang with no output. Use `--entrypoint <binary>`.
7. **Verify with one request per port, run from the same namespace as the consumer** (see §6 step 1).
   A stack verified from a different container reports every service down.

**Check the service's own hardcoded defaults before trusting a start.** Recovered or vendored code
routinely defaults a data/config directory to an absolute path that does not exist on this host; the
service starts perfectly and silently reads/writes nowhere. Override it explicitly (env var) and say
which path you set, rather than discovering it when the data is gone.

### 7. Disk usage and cleanup

Always start with a diagnostic before cleaning:

```bash
# Check what's using space
docker system df                       # summary
docker system df -v                    # detailed breakdown

# Targeted cleanup (safe)
docker container prune                 # stopped containers
docker image prune                     # dangling images
docker volume prune                    # unused volumes
docker network prune                   # unused networks

# Aggressive cleanup (confirm with user first!)
docker system prune                    # containers + images + networks
docker system prune -a                 # also unused images
docker system prune -a --volumes       # EVERYTHING — named volumes too
```

**Warning:** Never run `docker system prune -a --volumes` without confirming with the user. This removes named volumes with potentially important data.

### 8. Full Service Removal

When decommissioning a service entirely (not just stopping it), follow this order to reclaim all resources:

```bash
# Step 1: Identify everything
docker ps -a --filter "name=SERVICE" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"

# Step 2: Stop containers
docker stop $(docker ps -q --filter name=SERVICE)

# Step 3: Remove containers
docker rm $(docker ps -aq --filter name=SERVICE)

# Step 4: Remove associated volumes
docker volume ls --filter name=SERVICE -q | xargs -r docker volume rm

# Step 5: Remove images
docker images --format '{{.Repository}}:{{.Tag}}' | grep -i SERVICE | xargs -r docker rmi

# Step 6: Prune build cache (often 4-5GB)
docker builder prune -af

# Step 7: Remove project directories
rm -rf /root/SERVICE /root/repos/SERVICE-*

# Step 8: Verify cleanup
docker ps -a
docker system df
df -h /
```

**Why this order matters:**
- Stop before rm (can't remove running containers)
- Volumes before images (volumes hold persistent data like databases)
- Build cache separately — `docker system prune` doesn't always catch it
- Project directories last — Docker is the big space consumer

**Verified:** Jun 4, 2026 — Removed Multica (3 containers, 2 volumes, 2 images, 4.8GB build cache). Net result: ~2-3GB disk reclaimed.

### 9. Finding a container path's HOST path — and why `docker cp` to a bind mount lies

When you are working **inside** a container and need to hand a human a path to run commands on, do not
guess the host side. A container's `/opt/data` may be `/docker/<stack>/data`, `/srv/<app>`, or anything
else, and paths from old notes rot silently when a host is rebuilt.

**The marker technique — one file, one find, zero guessing:**

```bash
# inside the container
hostname > /opt/data/DISK-MARKER-$(hostname).txt
```

```bash
# on the host — prints the real prefix for every path you were about to hand over
sudo find / -name 'DISK-MARKER-*.txt' 2>/dev/null
# → /docker/hermes-agent-wxt5/data/DISK-MARKER-707cbca52aae.txt
```

The directory containing the marker is the host path of the container directory it was written to. Use
that prefix for every later instruction in the conversation, and delete the marker when done.

**A bind-mounted destination is not writable, and `docker cp` will not tell you.** Copying onto a path
that is a bind mount produces `Successfully copied 8.17kB` and then fails the follow-up steps:

```
chown: changing ownership of '/var/www/.../file': Read-only file system
docker exec ... chmod 600 ...                   → Read-only file system
```

**`Read-only file system` here is not a permissions problem — it is the mount telling you the file lives
on the host.** The write went to the container layer and will be discarded on the next restart; the
file the service actually reads is unchanged.

- **To change a bind-mounted file, write its HOST source** (find it with
  `docker inspect NAME --format '{{range .Mounts}}{{.Source}} => {{.Destination}}{{println}}{{end}}'`),
  then restart the container if the app reads it at import.
- **`docker cp` is for container-layer paths only.** On a bind mount it is a no-op dressed as a success.
- **The receipt is the file read back at its real path**, not the `docker cp` message. If you must prove
  it, `docker exec NAME cat <path> | head -c 200` and compare.
- **Watch the ownership you would have changed.** A bind-mounted file is often deliberately owned by a
  non-root in-container user at mode `600`; renaming or re-copying it as root can leave the service
  unable to read its own config while the container still reports `Up`.

**A container that is `Up` does not prove its mounts are valid.** Docker validates a bind-mount source at
container *creation*; it does not re-check an existing one. A source that later becomes a symlink, is
renamed, or is removed leaves the running container serving happily until the next `docker restart`,
which then fails with `mkdir <source>: file exists` (symlink) or `no such file or directory`. **If you
moved anything that might be a mount source, restart the container before declaring the move done.**

**Do not symlink-swap a mount source, and do not rename it at all — satisfy the rename at the consumer
layer instead.** A bind-mount source must be a real directory: Docker resolves the path and tries to create
what is missing, so a symlink is reported as `file exists` and the container will not start. When the real
reason for the rename is *presentation* (a nicer name on a dashboard, in a UI, in a chat channel), change
the name where a human reads it — a display name, a device label, a note — and leave the on-disk path alone.
The disk path is a contract shared by the mount, the app's config and every script that hardcodes it; a
rename breaks all of them at once, and the mount is only the loudest.

**If a directory name really must change, treat it as a code change:** grep every hardcoded reference first
(`grep -rl '<old-path>' --include='*.py' --include='*.sh'`), and expect the count to surprise you. A path
extracted at runtime through a config loader is a one-line edit; a literal baked into forty scripts is a
migration. **Verify the rename by running the consumers, not by listing the directory** — a script that
points at the vanished name fails at its next scheduled run, hours after you called it done.

## Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Container exits immediately | Main process finished or crashed | Check `docker logs NAME`, try `docker run -it --entrypoint /bin/sh IMAGE` |
| "port is already allocated" | Another process using that port | `docker ps` or `lsof -i :PORT` to find it |
| Two services both start OK, one is unreachable | Each was launched on the port its OWN source declared — the two defaults collided, and the second bind "succeeded" | Take the port map from the CONSUMER's route/config table, pin host+port explicitly per service, and stagger the starts so a clash reports against the right one |
| `docker run IMAGE <cmd>` hangs or does nothing | The image defines an ENTRYPOINT, so `<cmd>` was passed to it as arguments instead of being run | `docker run --entrypoint <binary> IMAGE <args>` |
| "no space left on device" | Docker disk full | `docker system df` then targeted prune |
| Can't connect to container | App binds to 127.0.0.1 inside container | App must bind to `0.0.0.0`, check `-p` mapping — **unless the container is `--network host`, in which case `127.0.0.1` inside IS the host loopback and binding to it is correct** |
| `127.0.0.1` inside the container doesn't reach the host | Bridge networking gives the container its own loopback | Read the mode before theorising: `docker inspect NAME --format '{{.HostConfig.NetworkMode}}'`. `host` = shares the host loopback; `container:<name>` = shares that container's namespace; anything else = its own |
| A file written on the host is invisible inside the container (or vice versa) | Same PATH, different filesystem — one side sees a named volume, the other a bind mount | Never assume two containers share a directory because the path matches. `docker inspect NAME --format '{{range .Mounts}}{{.Source}} => {{.Destination}}{{println}}{{end}}'`, and for a file two containers must both read, put it **beside the bind-mounted code** so a path relative to the script resolves to the same file on both sides |
| Everything worked, then a host reboot left the service gone | Container started without a restart policy (the default is `no`) | `docker inspect NAME --format '{{.HostConfig.RestartPolicy.Name}}'`. Start long-lived services with `--restart unless-stopped`, and treat a missing policy as a defect — anything that *tracks* the service's state (a monitor, a readiness file, a dashboard) will keep reporting it up after it is gone |
| Permission denied on volume | UID/GID mismatch host vs container | Use `--user $(id -u):$(id -g)` or fix permissions |
| Compose services can't reach each other | Wrong network or service name | Services use service name as hostname, check `docker compose config` |
| Build cache not working | Layer order wrong in Dockerfile | Put rarely-changing layers first (deps before source code) |
| Image too large | No multi-stage build, no .dockerignore | Use multi-stage builds, add `.dockerignore` |
| Systemd service still running after Docker removal | Service not disabled | `systemctl stop <svc> && systemctl disable <svc> && rm /etc/systemd/system/<svc>.service && systemctl daemon-reload` |
| Ollama models persist after binary removal | Models live in `~/.ollama/` not with binary | Remove `~/.ollama/` separately after stopping service |

## Verification

After any Docker operation, verify the result:

- **Container started?** → `docker ps` (check status is "Up")
- **Logs clean?** → `docker logs --tail 20 NAME` (no errors)
- **Port accessible?** → `curl -s http://localhost:PORT` or `docker port NAME`
- **Image built?** → `docker images | grep TAG`
- **Compose stack healthy?** → `docker compose ps` (all services "running" or "healthy")
- **Disk freed?** → `docker system df` (compare before/after)

## Dockerfile Optimization Tips

When reviewing or creating a Dockerfile, suggest these improvements:

1. **Multi-stage builds** — separate build environment from runtime to reduce final image size
2. **Layer ordering** — put dependencies before source code so changes don't invalidate cached layers
3. **Combine RUN commands** — fewer layers, smaller image
4. **Use .dockerignore** — exclude `node_modules`, `.git`, `__pycache__`, etc.
5. **Pin base image versions** — `node:20-alpine` not `node:latest`
6. **Run as non-root** — add `USER` instruction for security
7. **Use slim/alpine bases** — `python:3.12-slim` not `python:3.12`
