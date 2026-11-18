# Port containment — the rule depends on the port's OWNER

Companion to the exposure section of `verification-vantage`. Read the owner from `ss -ltnp` first; it decides
the rule. Getting it wrong produces a rule that is listed, looks applied, and matches nothing.

## Owner → mechanism → what actually closes it

| `ss -ltnp` shows | what it is | the port becomes reachable because | what closes it |
|---|---|---|---|
| `python3` on `0.0.0.0:<p>` | an app binding every interface itself | the app's own bind | fix the bind (see "switch as a file" below) — a firewall is the stopgap |
| `docker-proxy` on `0.0.0.0:<p>` | Docker publishing a container port | `nat` PREROUTING DNAT to the container | `DOCKER-USER` keyed on the **container** port, or change the publish |
| `traefik`/`nginx` on `*:80`,`*:443` | the intended front door | nothing — it is the door | leave it; route the app behind it |
| `tailscaled` on `100.x.x.x` | tailnet traffic | the tailnet | nothing — it is not internet-reachable |
| `sshd` on `0.0.0.0:22` | expected | — | key-only auth, not a firewall change |

## Why `INPUT --dport <host-port>` fails for published ports

```
packet arrives on eth0 -> raw -> mangle -> nat PREROUTING  (DNAT: dst=container-ip, dport=CONTAINER-port)
                                        -> routing decision -> FORWARD / INPUT
```
The INPUT chain never sees the host port. A rule matching it matches zero packets — forever, silently.

**Two rules that work instead:**

```bash
# A · post-DNAT, forwarded traffic — match the CONTAINER port
ss -ltnp | grep docker-proxy            # note the container's own port from `docker port <name>`
iptables -I DOCKER-USER -i eth0 -p tcp --dport <container-port> -j DROP

# B · remove the publish entirely (durable; needs a container recreate)
#   ports: "127.0.0.1:<host-port>:<container-port>"   # or "100.x.x.x:<host-port>:<container-port>"
```

`DOCKER-USER` is traversed after DNAT and before the container, so it is the correct hook for publish-level
filtering. It matches on the container port, not the host port.

## Why `-t nat -j DROP` cannot work

```
iptables -t nat -I PREROUTING -i eth0 -p tcp --dport <p> -j DROP
iptables v1.8.10 (nf_tables): The "nat" table is not intended for filtering, the use of DROP is therefore inhibited.
```
`nat` rewrites addresses; it does not make verdicts. Do not try to build a filter there.

## Host-networked apps: the `-i eth0` rule

```bash
ip -br addr show | grep -v ' lo '                     # confirm the external interface name
ss -ltnp | grep -v '127.0.0.1' | grep -v '\[::1\]'    # the real public surface, with owners
iptables -I INPUT -i eth0 -p tcp --dport <p> -j DROP
```

Safe for a host-networked app because a reverse proxy on the same host reaches it over `lo`, which the rule
does not touch. **Unprovable from inside the host** — see the hairpin note below.

## Verification — the two directions, and the one that lies

| check | proves |
|---|---|
| local `curl` to the public IP, before | nothing — hairpins over `lo` |
| local `curl` to the public IP, after | nothing — returns `200` even when the rule is correct |
| `iptables -L INPUT -n -v` → `0 packets` | **the rule has never matched** — treat as not applied |
| third-party fetcher, after | **the only proof of closure** |
| the public hostname still `200` | the rule did not break the front door |

```bash
# the falsifiable inside check: counters, not presence
iptables -L INPUT -n -v --line-numbers | head -8
```

**Hairpin, stated once:** a request from the host (or from a container on it) to the host's own public address
is routed over `lo`. It is not evidence of exposure, and it is not evidence of containment. Both questions need
an outsider.

## Persistence — the file that is actually read

| written to | restored at boot? |
|---|---|
| `/etc/iptables/rules.v4` via `netfilter-persistent save` | **yes** — this is the unit's source |
| `/etc/iptables.rules` (hand-written) | **no** — nothing reads it |
| `iptables-save > anywhere` and nothing else | **no** |

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
netfilter-persistent save
ls -la /etc/iptables/rules.v4 && grep -c DROP /etc/iptables/rules.v4
```

Two side effects to state **before** the operator runs it: the package **removes `ufw`** (harmless if inactive,
surprising if not), and its `debconf` prompt presents in a terminal as a **hang with a blinking cursor**.

## The switch-as-a-file trick (when an env var would force a recreate)

A hand-started or host-networked container cannot gain an env var without a recreate — which drops every service
depending on it. Make the switch a file read at start-up instead:

```python
def _bind_host(default="0.0.0.0"):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bind-host")
    try:
        if os.path.exists(p):
            v = (open(p).read() or "").strip()
            if v:
                return v
    except Exception as exc:
        print(f"WARN: .bind-host unreadable ({exc}); binding {default}")   # never fail to start
    return default

uvicorn.run(app, host=_bind_host(), port=PORT)
```

- **Default stays exactly what shipped today**, so deploying the code changes no behaviour.
- Switch = `echo 127.0.0.1 > .bind-host && docker restart <name>`; revert = `rm .bind-host && docker restart <name>`.
- **Test the function on all three branches** (no file / loopback / bridge IP) before handing it over — an
  exception on the start path turns a security fix into an outage.
- **Say what the retry costs**: if the public hostname breaks, the revert is one `rm` + restart, not a rebuild.

## What to hand the operator

One line at a time, with the blank/wrong answers named up front, and **a proof line whose output is the answer**:

```bash
ss -ltnp | grep -v '127.0.0.1' | grep -v '\[::1\]'        # the surface
```
Then the rule. Then:
```bash
iptables -L INPUT -n -v | head -8                          # counters = did it match
iptables-save > /etc/iptables/rules.v4                     # or: netfilter-persistent save
```
