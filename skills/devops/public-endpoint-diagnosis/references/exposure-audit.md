# Exposure audit — finding what is publicly reachable, and containing it without breaking the front door

The inverse of this skill's main direction. Same tools, opposite question: not "why can't the world reach
this?" but **"what can the world reach that should be private?"**

## When to use

- "Is anything of ours open to the internet?" / "are we exposed?"
- After any fast deploy, hackathon build, or container stood up by hand.
- Before claiming a perimeter exists — a WAF, a rate limiter, or an "only the proxy is public" assumption.

## 1 · Read the real bind table, never the config

```bash
sudo ss -ltnp | grep -v '127.0.0.1' | grep -v '\[::1\]'
```

Decode the local address, not the app's documentation:

| shown as | meaning |
|---|---|
| `127.0.0.1:<p>` | private — correct for a backend behind a proxy |
| `0.0.0.0:<p>` | every interface, including the public one |
| `*:<p>` | every interface, v4 and v6 |
| `100.x%tailscale0:<p>` | overlay only — private if the tailnet is |
| `[::]:<p>` | v6 wildcard, usually paired with `0.0.0.0` |

Two kinds of `users:(())` line need different handling:

- **`docker-proxy`** → a *published* port (`-p`). The fix is in the run args or compose file.
- **the application itself** (`python3`, `node`, the binary) → the app is bound to the host interface:
  either a host process or a **host-networked container**. Identify before proposing anything:
  ```bash
  sudo tr '\0' ' ' < /proc/<pid>/cmdline; echo
  sudo readlink /proc/<pid>/cwd
  docker ps --format '{{.Names}}\t{{.Status}}'
  docker inspect <container> --format '{{.HostConfig.NetworkMode}}'
  ```
  `NetworkMode=host` with no `com.docker.compose.project` label means somebody ran `docker run --network host`
  by hand: there is no compose file to edit and no env var you can add without recreating the container.

## 2 · Prove reachability from OUTSIDE, with a negative control

A probe from the host — or from a container on the same host — to the host's public IP is hairpin traffic. It
proves the bind, not that the internet can get there. Use an external fetcher:

```bash
curl -s -m 20 "https://r.jina.ai/http://<public-ip>:<port>/health"
```

**The negative control is what makes the verdict honest:** probe a wildcard port and a loopback-bound port
from the same external vantage. Wildcard answers and loopback times out → the finding is real and
port-specific. Both answer → the fetcher is not reaching what you think it is.

**Header comparison is the cleanest proof of a bypass**, on the same route:

```bash
curl -sI https://<hostname>/health | grep -i '^server'    # server: cloudflare
curl -sI http://<ip>:<port>/health   | grep -i '^server'  # server: <the app's own banner>
```

Same application, two doors — and the controlled one is now optional. Say that, because it is the sentence
that lands: **every edge control applies only to callers who use the hostname.**

## 3 · Ask what the exposed surface gives away

`/health`, `/status`, `/api/health`, `/api/status`, `/.well-known/*` are frequently unauthenticated and name a
**version, a commit, a backend map, and which components are down**. That is reconnaissance, and it is often
worse than the port itself — it tells a scanner exactly what it is looking at and where the weak parts are.
Read those routes from the outside and quote the body.

Also count what the surface *claims* versus what runs: an unauthenticated status body advertising a service
count larger than the live catalogue is a false promise published to anyone who asks.

## 4 · Contain without breaking the front door

When something on the same host dials the exposed port (a reverse proxy, an edge worker, a gateway), a
port-wide deny can take the **public** hostname down with it. Scope the rule by ingress interface instead:

```bash
ip -br addr show | grep -v ' lo '            # confirm the external interface name

iptables -I INPUT -i eth0 -p tcp --dport <p> -j DROP
apt-get install -y iptables-persistent >/dev/null 2>&1; netfilter-persistent save
```

**Why this cannot break the proxy:** locally generated traffic to the host's own address rides `lo`; internet
traffic arrives on `eth0`. The rule kills the second and leaves the first.

**Verify both directions in one pass — never one alone:**

```bash
curl -s -o /dev/null -m 8  -w 'raw %{http_code}\n' http://<public-ip>:<port>/health   # must fail/time out
curl -s -o /dev/null -m 15 -w 'api %{http_code}\n' https://<hostname>/health          # must still be normal
```

- Revert is one `iptables -D INPUT -i eth0 -p tcp --dport <p> -j DROP`.
- ⚠️ `iptables -I` is **not persistent**. Without `netfilter-persistent save` the hole reopens at the next
  reboot, and nobody will be looking for it then.
- ⚠️ Do **not** `ufw enable` on a Docker host as a quick fix. Docker manages its own chains; an allow-list
  that omits 22/80/443 locks the owner out of their own machine.

## 5 · The permanent fix — decide from how the front door dials

**Read the proxy's route before choosing a fix:**

```bash
docker inspect <proxy-or-app> --format '{{json .Config.Labels}}' | tr ',' '\n' | grep -i <hostname>
# traefik.http.routers.<name>.rule=Host("api.example.com")
# traefik.http.services.<name>.loadbalancer.server.port=8090
```

That label pair states the proxy dials **the container on that port**. So binding the app to loopback breaks
the public hostname — *unless* the proxy is itself host-networked (its listeners then appear in the host's
`ss` with no `docker-proxy` in front, which is how you tell).

**❌ The textbook fix is often wrong here: enumerate localhost dependencies first.** A service that proxies to
backends on `127.0.0.1:<ports>` cannot move from host networking to a bridge — inside a bridge namespace those
addresses are the container itself, so every backend breaks at once. **Host networking is frequently a real
constraint, not carelessness**; say so instead of prescribing bridge migration as a five-minute change.

**Switching a hand-started container's bind.** An env var would require recreating a container that has no
compose file. A **file read at startup** gives the same switch for the cost of a restart:

```python
def _bind_host() -> str:
    default = "0.0.0.0"                     # unchanged until the file exists
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bind-host")
    if os.path.exists(p):
        v = (open(p).read() or "").strip()
        if v:
            return v
    return default
```

Change = write the file, restart. Revert = delete it, restart. **Test every branch of the switch by executing
the function** (no file, valid override, junk override) — a fallback path that references an unimported module
fails only when the override is bad or missing, which is precisely the moment you cannot afford it.

## Pitfalls

- **`0.0.0.0` in application code is a publish decision nobody made.** It is usually a literal in the `main`
  guard (`uvicorn.run(app, host="0.0.0.0")`), so there is no config to review and no owner to blame. Grep for
  the bind literal rather than assuming a deployment flag controls it.
- **Connecting to `0.0.0.0:<port>` is not evidence of a wildcard bind** — on Linux that address is loopback, so
  the probe succeeds whenever loopback does and proves nothing.
- **The second hole is usually the operator surface, not the product.** Dashboards and control planes published
  with a bare container port (`-p 4860`) land on a random host port on **every** interface. Rebind to
  `127.0.0.1:<port>:<container-port>`, or to the overlay address if it must be on the tailnet — and treat a
  control plane exposed with only a login form as the higher-severity finding, because it is the whole fleet
  behind one password.
- **Reporting a perimeter that was never swept.** "Cloudflare fronts us" is a claim about the hostname, not
  about the host. Only a bind table plus an external probe supports it.
- **Presenting the leak and its containment as one verdict.** "Publicly reachable" and "closed" are different
  states; only the second is proven, and only by both probes passing in the same pass.
- **Treating a provider firewall as a complete answer.** It is the right *immediate* containment, but the
  durable state is still a wildcard bind, and any change to the network path (a new interface, a container
  recreate, a firewall reset) reopens the door with no alarm attached.
