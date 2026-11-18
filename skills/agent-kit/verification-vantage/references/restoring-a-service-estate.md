# Restoring a service estate behind a front door

**Use when a gateway/proxy/front door is up and healthy but the services behind it are
absent — the front door prices or routes fine, and nothing answers.**

## The shape of the symptom

The front door is *not* the problem, and its health is what hides the problem. It answers
auth challenges, price tags and route matches **before** it contacts anything upstream.
So every check aimed at the front door passes while the estate is empty.

**First move: stop testing the front door. Find its upstream map and test behind it.**

---

## Step 1 — Read the upstream map from the CODE, and treat it as the port authority

The front door's own route table is the authority for host:port, **not the service
sources' own defaults.** Measured case: two services both declared the *same* port in
their source while the route table correctly placed them one apart. A launcher generated
from the source files would have produced a silent collision — both "start fine", one
shadows the other, and every health check on the shadowed port answers from the wrong
process.

```bash
# pull the map out of the front door's source
grep -n -A20 'BACKEND_ROUTES\s*=' path/to/server.py
```

**Write the map down as data before touching anything.** It is the contract you are
restoring to.

## Step 2 — Establish where the front door DIALS FROM

This decides the entire topology, and it is one command against the container:

```bash
docker inspect <front-door-container> --format '{{.HostConfig.NetworkMode}}'
```

- **`host`** → the front door's `127.0.0.1` **IS the host's loopback**. Upstream services
  must listen on the host's loopback. A *different* container cannot reach it; a probe run
  from another container will honestly report `NOT_READY` for every live service.
- **`bridge`** → loopback is private to the container; upstreams need either a shared
  network namespace (`--network container:<front-door>`) or the map rewritten to DNS names.

> **Do NOT infer this from a symptom.** "The container moved to bridged networking, so
> `127.0.0.1` stopped meaning the host" is a plausible story that survives until measured.
> Run the inspect. In the measured case the mode was `host` and the story was simply
> false — the services were not running, which was the whole explanation.

## Step 3 — Borrow the image that already has the dependencies

Before installing anything, check whether an image on the box already carries the stack:

```bash
docker run --rm --entrypoint python3 <image> -c 'import fastapi, uvicorn, httpx; print("OK")'
```

**`--entrypoint` is required** — without it the image's own entrypoint runs instead of
your command, and the probe hangs rather than erroring, which reads as "the image is
broken".

If the front door's image carries the stack, **run the services as containers from that
same image.** That avoids a dependency install entirely, keeps them version-matched to the
front door, and (with `--network host`) puts their loopback exactly where the map expects.

## Step 4 — Start one, verify it, then the rest

**One service, then look at it.** A batch start turns one wrong assumption into N failures
to untangle.

```bash
docker run -d --name svc-<name> --network host \
  -v <source-dir>:/svc -w /svc --entrypoint python3 <image> \
  -m uvicorn <module>:app --host 127.0.0.1 --port <port-from-the-map>

curl -s http://127.0.0.1:<port>/v1/health; echo
```

**Assert on the body, not the port.** `{"status":"ok","service":"<name>"}` is the
signal; an open port is not.

### Invocation pitfalls, each of which looks like a broken service

- **PACKAGE vs MODULE.** A service in a directory with an `__init__.py`, or one using
  relative imports (`from . import x`), must be run as a package from its PARENT dir:
  `-w /svc-parent -m uvicorn api.server:app`. Running it as a bare module raises an import
  error that reads as a code defect.
- **Pin host and port on the command line.** Do not let the source's own default decide;
  the map is the authority (Step 1).
- **Dead default paths inside the service.** Old service sources commonly default a data
  directory to a path from a previous host layout (a `/root/...` or a home path that no
  longer exists). The service then starts cleanly, writes nowhere, and answers health
  checks. **Grep each source for absolute defaults and set them explicitly by env** — a
  service that runs and silently loses its data is worse than one that refuses to start.
- **Bind loopback, not `0.0.0.0`,** unless the service is meant to be public. With
  `--network host`, `0.0.0.0` publishes it on the host.

## Step 5 — Pin the lifetime, at the same time as everything else

```bash
for c in svc-a svc-b ...; do docker update --restart unless-stopped "$c"; done
```

A service started by hand dies on reboot while any state file describing it still says
`READY` — the front door then keeps selling a dead route. **Restart policy and the gate
are one change, not two.**

## Step 6 — Gate the ADVERTISEMENT, from the same inventory

Everything above makes the estate *work*; the gate makes it *honest*. Before the front
door issues any challenge for a route, it must know the upstream answers — and anything
policy-blocked (licence, upstream objection, no source recoverable) must be refused **even
though its process is up**, because entitlement is not health.

See the parent skill's "Adding a gate to a live path" for the gate itself. Two rules that
belong to this step:

- **Order the checks: policy → liveness → cache.** A live process must never override a
  terms decision.
- **Generate every published catalogue from the same inventory the gate reads**, so a
  service that cannot be served cannot be advertised, and the withheld ones are listed
  *with their reasons*.

---

## Why a file next to a bind-mounted source is the only safe state path

When the gate or the front door must read a generated file, put it **beside the source
file that is bind-mounted into the container.** A path relative to that file resolves to
the *same file* on both sides by construction.

Measured failure: the container's `/opt/data` was a **Docker volume**, not the host tree of
the same name. State written from the host landed on a different filesystem than the
container read, so the container found nothing, failed closed, and refused every route —
while the operator believed the services were up. **A fix that looks like success.**

```bash
# what the container actually mounts — do this before choosing a path
docker inspect <container> --format '{{range .Mounts}}{{.Source}} => {{.Destination}}{{"\n"}}{{end}}'
```

The host path for a container's directory is rarely the same string. Read the mounts; do
not assume the names match.

---

## The honest limits to state when reporting a restore

- **Health is not correctness.** A `200` on `/v1/health` proves the app answers. It does
  not prove a paid route returns real data rather than a placeholder, stale fixture, or a
  valid-looking document for the wrong subject.
- **Recovered source is not vetted source.** Code recovered from a public mirror has
  unpinned provenance; calling a restore "verified" without saying that is a claim you
  have not earned.
- **Count what you can serve, not what you intended to.** "N of M routes servable, and here
  is why each of the rest is not" is the report. A single number that flattens the
  different refusal reasons loses the information the next reader needs.
