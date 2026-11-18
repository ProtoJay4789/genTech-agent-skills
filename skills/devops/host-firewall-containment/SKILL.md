---
name: host-firewall-containment
description: Use when closing a port or proving it closed.
version: 1.0.0
author: gentech
license: MIT
metadata:
  hermes:
    tags: [firewall, iptables, docker, exposure, verification]
    related_skills: [verification-vantage, public-endpoint-diagnosis]
---

# Closing a port, and proving it — three port kinds, one verification rule

## When to Use

- A listener is bound to `0.0.0.0` and should not be public.
- You are asked to close a port, lock down a dashboard, or stop a bypass.
- You must prove a port is closed, or prove a firewall change did not break the front door.
- An `INPUT`/`DOCKER-USER` rule was applied but the port still answers.

**Origin:** 2026-11-04. Two publicly exposed ports on the GenTech VPS: an x402 gateway (host-networked, `0.0.0.0:8090`) and the Hermes dashboard (Docker-published, `0.0.0.0:32771`). The first `iptables` attempt closed one and silently did nothing to the other, and every in-host probe reported `200` while the rules were live.

## 1 · Identify which KIND of listener you have — this decides the mechanism

| `ss -ltnp` shows | kind | which rule works |
|---|---|---|
| `python3,pid=…` on `0.0.0.0:N` | **host-networked** app or container | `iptables -I INPUT -i eth0 -p tcp --dport N -j DROP` |
| `docker-proxy,pid=…` on `0.0.0.0:N` | **Docker-published** port | `iptables -I DOCKER-USER -i eth0 -p tcp --dport <CONTAINER_PORT> -j DROP` |
| `tailscaled` on `100.x.x.x` | tailnet-only | already private — do not touch |

Get the container port before writing anything:

```bash
docker inspect <container> --format '{{json .HostConfig.PortBindings}}'
```

## 2 · The two traps that make a fix look done when it isn't

**Trap A — `INPUT --dport` cannot see a published port.** Docker's `nat` PREROUTING rewrites destination **and port** (host `32771` → container `4860`) *before* the filter chain runs. A rule matching `--dport 32771` in INPUT is accepted, sits in the chain, and matches nothing.

**Trap B — `nat -j DROP` is refused.** `iptables -t nat … -j DROP` → *"The nat table is not intended for filtering"*. nat rewrites; it does not filter. Do not retry it with `-t raw` either (only NOTRACK is valid there). Use `DOCKER-USER`.

## 3 · ⚠️ The verification rule: only an EXTERNAL vantage proves a port closed

**A probe from the host itself hairpins over `lo`.** Traffic addressed to the host's own public IP does not traverse `eth0`, so `-i eth0` rules never see it — and neither does any local test. Measured: both ports returned `200` from inside the host while the DROP rules were live.

**Use an external fetcher**, and cache-bust it:

```bash
curl -s -m 30 "https://r.jina.ai/http://<IP>:<PORT>/<path>?cb=$(date +%s)" | head -c 200
# TimeoutError / 422  = closed ✅      rendered content = STILL OPEN ⚠️
```

Prove BOTH directions every time:

```bash
curl -s -o /dev/null -m 8  -w 'raw  -> %{http_code}\n' http://<IP>:<PORT>/health    # must fail
curl -s -o /dev/null -m 15 -w 'app  -> %{http_code}\n' https://<PUBLIC_HOST>/health # must stay 200
```

**A firewall rule you have not verified from outside the host is a wish.**

## 4 · Persistence has an ordering trap of its own

`iptables-save > /etc/iptables.rules` is inert — nothing reads that path. The correct pair is:

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
netfilter-persistent save                       # writes /etc/iptables/rules.v4
```

⚠️ Without `DEBIAN_FRONTEND=noninteractive`, the install **hangs on a debconf prompt** (a blinking cursor with no visible question — `Ctrl+C` is safe; rules already inserted stay). It also **removes `ufw`** as a dependency; say so, or the next session goes looking for a command that is gone.

⚠️ **Boot ordering:** `netfilter-persistent` restores *before* `docker.service` creates `DOCKER-USER`. A saved rule referencing a chain that does not exist yet can make `iptables-restore` **abort the whole file**, reopening the port and losing the INPUT rules too. **After any reboot, verify:**

```bash
iptables -L INPUT -n | grep -c 'dpt:<port>'
iptables -L DOCKER-USER -n | grep -c 'dpt:<container_port>'
```

Non-zero on both, or the restore failed.

**The fix for the ordering trap — a oneshot unit that runs after Docker.** This beats relying on
`rules.v4` for the `DOCKER-USER` rule, because it is idempotent and cannot be skipped by an aborted restore:

```bash
cat >/etc/systemd/system/docker-user-guard.service <<'EOF'
[Unit]
Description=Block external access to published container ports
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c '/usr/sbin/iptables -C DOCKER-USER -i eth0 -p tcp --dport <CONTAINER_PORT> -j DROP 2>/dev/null || /usr/sbin/iptables -I DOCKER-USER -i eth0 -p tcp --dport <CONTAINER_PORT> -j DROP'

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now docker-user-guard.service
```

**Prove the unit actually re-adds the rule** (do not trust `enable` alone): delete the rule, restart the unit,
and confirm it comes back — that is the boot path exercised without a reboot:

```bash
iptables -D DOCKER-USER -i eth0 -p tcp --dport <CONTAINER_PORT> -j DROP
iptables -L DOCKER-USER -n | grep -c 'dpt:<CONTAINER_PORT>'   # expect 0
systemctl restart docker-user-guard
iptables -L DOCKER-USER -n | grep -c 'dpt:<CONTAINER_PORT>'   # expect 1
```

⚠️ Duplicate rules from repeated manual inserts are harmless (`grep -c` going to 3 is fine); collapse them with a
`while [ "$(iptables -L INPUT -n | grep -c 'dpt:<port>')" -gt 1 ]; do iptables -D …; done` loop, then re-save.

## 5 · Closing a port you were using — hand the owner a replacement path first

If the port served a dashboard or admin UI, closing it locks the owner out. State the alternative *before* closing:

- **Tailnet** — `-i eth0` rules do not match traffic arriving on `tailscale0`, so `http://<tailnet-ip>:<port>` keeps working.
- **SSH tunnel** — `ssh -L <port>:127.0.0.1:<port> root@host`, then browse `localhost:<port>`. Loopback inside the host is unfiltered.

## 6 · The durable fix is always the bind, not the rule

The firewall is containment, not architecture:

- **Docker-published** → publish `127.0.0.1:<host_port>:<container_port>` in compose, `docker compose up -d`, then delete the DOCKER-USER rule.
  ⚠️ If that container *is the agent itself*, this restarts the session — schedule it, never mid-conversation.
- **Host-networked app** → make the bind address configurable and default it to loopback, then prove the front door still answers.
  ⚠️ **Do not bind loopback blind.** Check whether the reverse proxy dials the container IP or loopback first; if it dials the IP, a loopback bind takes the public hostname down. When the container was hand-started with `docker run` and an env var would force a recreate, **a file read at startup** is the switch that costs nothing to flip and nothing to revert.
- **App in front of local backends** → if it proxies `127.0.0.1:8000–8999`, it **cannot move to a bridge network without re-addressing every backend**. That constraint is why the `0.0.0.0` bind exists — say it out loud instead of prescribing a migration that breaks nine services.

## Red lines

- Never enable a host firewall package blind where Docker manages its own chains — an allow-list missing 22/80/443 locks the owner out of SSH. Prefer one surgical rule plus the provider's firewall panel.
- Never report a port closed on the strength of a local `curl`. Measure from outside, or say it is unverified.
- Never claim persistence without a post-reboot check or an explicit "not yet proven".
