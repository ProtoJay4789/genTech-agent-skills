# Running a backend as a container behind a label-driven proxy (Traefik)

Use when a host-level reverse proxy discovers its routes **by Docker label only** — its only mounts are
`/var/run/docker.sock` plus cert volumes, so it has **no file provider** and cannot see a host process on any
port. "Run it as a systemd service" produces a listener nothing can route to.

## 1. Read the proxy's own configuration first — it decides the label set

```bash
docker inspect <proxy-container> --format '{{json .Args}}'
docker inspect <proxy-container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

Read these three out of the args, because each one changes the command you are about to write:

| Arg | Consequence |
|---|---|
| `--providers.docker.exposedbydefault=false` | A container gets **no route unless it opts in** — it must carry `traefik.enable=true`. This single flag is why a running container can be completely invisible. |
| `--entrypoints.websecure.address=:443` | The entrypoint name to attach the router to (mirror the working router's `entrypoints` value). |
| `--certificatesresolvers.<name>...` | The `tls.certresolver` value; mirror it so the proxy issues the cert itself. |

**Then read a router that already WORKS and mirror its labels exactly** — do not compose the label set from
memory or from documentation:

```bash
docker inspect <a-working-container> \
  --format '{{range $k,$v := .Config.Labels}}{{$k}}={{$v}}{{"\n"}}{{end}}' | grep -i traefik
```

## 2. Resolve the host path to the code before writing anything

**The path inside your container is not the host's path.** A `-v` written with the in-container path mounts an
empty directory and the service starts against nothing (or fails outright):

```bash
docker inspect <app-container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

Use the **SOURCE** side. Verify it exists on the host with an `ls` of the actual entrypoint file before
running — not the directory.

## 3. The run command

```bash
NET=$(docker inspect <proxy-container> --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' | head -1)
docker rm -f <name> 2>/dev/null
docker run -d --name <name> --restart unless-stopped --network "$NET" \
  --user <owner-uid>:<owner-gid> \
  -v <HOST-SOURCE-PATH>:/app -w /app \
  --entrypoint <interpreter> \
  --label traefik.enable=true \
  --label 'traefik.http.routers.<router>.rule=Host("api.example.com")' \
  --label traefik.http.routers.<router>.entrypoints=<entrypoint> \
  --label traefik.http.routers.<router>.tls.certresolver=<resolver> \
  --label traefik.http.services.<svc>.loadbalancer.server.port=<APP-BIND-PORT> \
  <image> <entrypoint-script>
```

Four deliberate choices, each with a failure it prevents:

- **`--entrypoint <interpreter>`** — **overrides a container image's init/entrypoint** (s6, tini, a shell
  wrapper) which otherwise swallows your command and starts the image's default process instead. Passing the
  script as a bare argument to a wrapped image is the quietest way to get a container that runs, logs nothing
  useful, and serves nothing.
- **Quoting the rule with `"` not backticks** — see the pitfall below.
- **`loadbalancer.server.port` must equal the port the app actually binds**, read from its own source. If the
  app binds `0.0.0.0:8090`, this is `8090`. A mismatch is a `502` with a healthy container.
- **`--user` matched to the mounted files' owner** — otherwise any state the service writes lands
  **root-owned** in a data volume that everything else runs as an unprivileged uid. Read the ownership off the
  file (`ls -la` on the entrypoint) and match it.
- **No `-p` flag** — the proxy reaches the container over the Docker network (or the host net). Publishing the
  port is unnecessary and adds a second, unauthenticated path to the same service.

## 4. Verify the ORIGIN directly before touching the edge

Do not test the public hostname yet — an edge function may still be sitting in front of it. Send the request at
the origin IP with the real `Host` header, **and include a nonsense hostname as a control**:

```bash
for h in api.example.com nonsense-not-a-route.invalid; do
  printf '%-32s ' "$h"
  curl -sk -o /dev/null -w '%{http_code}\n' --max-time 12 -H "Host: $h" https://<ORIGIN-IP>/
done
```

The control is what makes the result trustworthy: the real host must return the service's answer and the
nonsense host must return **`404`**. If both return the same code, the router is not doing the routing and you
are reading a default handler. **Without the control, a `200` proves only that something answered.**

## 5. Cut over the edge in this order — each step is reversible until the last

1. **Back up the route table** before deleting anything:
   ```bash
   curl -s -H "Authorization: Bearer $CF_TOKEN" \
     "https://api.cloudflare.com/client/v4/zones/$ZONE/workers/routes" > routes-backup.json
   ```
2. **Read the origin certificate** the proxy now presents for that hostname (the proxy usually issues it
   itself via the resolver).
3. **Read the zone's SSL mode** — decide *before* removing the edge function whether the origin cert must be
   valid, because removing a Worker under `strict` can turn a loud failure into a different one.
4. **Delete the edge route** (`DELETE .../workers/routes/<id>`) and **read back the route table** to confirm it
   is gone rather than trusting the delete response.
5. **Re-verify every real endpoint as a client** — a bare `curl` on `/health` is not the test. Send the headers
   a real client sends and assert the correct **unauthenticated** code for a paid API:
   ```
   402 = serving correctly      403 = still walled      502 = wrong port or backend down
   ```
   Enumerate the full endpoint list, count successes and failures, and report the counts.

## 6. The service can come back REACHABLE AND WRONG — check content, not just reachability

A restored service frequently returns correct-looking HTTP while serving **nothing**, because its *content* lives
outside the mount that survived. Two mechanisms, both silent, both measured:

### (a) A config/data file the app reads is not in the container

**Read the app's OWN source for the path it opens, then confirm that path exists in the container.** The mount
u suppose you need is often not the one the code reads:

```bash
grep -nE 'PATH *=|_PATH *=|\.json"|\.json\x27' <entrypoint>.py | head        # what does it actually open?  
docker exec <name> ls -la <that-path>                                        # does it exist in there?
```

Measured: a gateway read `MANIFEST_PATH = /var/www/<site>/.well-known/<file>`, the container had **no
`/var/www` mount at all**, the `open()` raised, and a bare `except (FileNotFoundError, ...)` set the catalogue
to `{}`. The service started cleanly, logged nothing, served `200`, and advertised **`services: 0`** while a
complete multi-service manifest sat on disk under the mounted directory. **Mount the file at the literal path
the code names, read-only:**

```bash
  -v <HOST>/public-copy/<file>:/var/www/<site>/.well-known/<file>:ro
```

> **A service that survives a rebuild can come back EMPTY and look healthy.** Find the *content counter* — a
> `services: N`, a `records: N`, a catalogue length — and assert it is non-zero. `/health` returning `200`
> says nothing about whether the service has anything to serve.

### (b) Env-var-driven config silently falls back to a default

**A service configured by environment variables comes back with its DEFAULTS after a rebuild.** Read the
source for the default before trusting what it advertises:

```bash
grep -nE 'os\.getenv\(|_DEFAULT_|getenv\(.*,' <entrypoint>.py | head -20
```

Measured: `_DEFAULT_<SETTING> = "<one-value>"` plus per-option defaults of `""`, and the resolver dropped any
option whose value was empty — so with no env set the service **silently degraded to a single fallback option**
and reported success. The default was never a deliberate choice; it was the fallback path.

**Rule: enumerate every env var the app reads, and set the ones you need explicitly in the run command.** A
silent fallback is indistinguishable from a correct configuration — that is exactly what makes it survive
review.

### (c) Assert the two lists AGREE

When the service both *advertises* capabilities and *offers* them per-request (a catalogue and a challenge, a
manifest and an endpoint), **read both and compare them.** Measured: the manifest declared five networks and the
live challenge offered one — a directory reading the manifest would tell a client to pay on a rail the challenge
never mentions. **A declared list and an offered list that disagree is a finding, and it is invisible if you
check only one side.**

## Pitfalls

- **Backticks in a Traefik rule are destroyed by chat and terminal pasting.** The rule language requires a
  quoted literal — `Host(\`api.example.com\`)` — and an unquoted `Host(api.example.com)` is **invalid**: the
  proxy silently ignores the router and nothing routes, exactly like a config that was never applied. **Write
  it with double quotes** — `Host("api.example.com")` — which is equally valid and survives the paste.
- **A healthy container is not a routed one.** Check the proxy actually produced the router (or that the
  origin probe in step 4 answers with a 404 control), never just that the container is `Up`.
- **Assuming a systemd unit will be seen by a label-driven proxy.** If the proxy's only mount is the docker
  socket, a host process is unreachable regardless of which port it listens on.
- **Resolving the network to `host` by taking "the first" of several.** Auto-detecting the proxy's network is
  fine only when the proxy and the new container really share it — a proxy already on the host network reaches
  a host-networked container on `127.0.0.1`, which is correct here but is an accident worth recording rather
  than a pattern to copy blind.
- **Deleting the edge route before proving the origin answers.** The Worker may be the only thing answering
  anything on that hostname; removing it first can turn a loud failure into a total one.
