# Reaching a service across an overlay network (tailnet / VPN → host → container)

When a service must be reachable from **another machine** over a private overlay (Tailscale, WireGuard, a
LAN), the path has **three independent layers**, and each one can be the reason it does not work:

```
PEER (another machine)
  └── overlay network        is the peer's node online and is the target node up?
        └── HOST listener    does the host accept on that address, and forward it anywhere?
              └── CONTAINER  is the service bound to an interface the HOST can reach?
```

**Map all three before changing ANY of them.** Diagnosing one at a time produces a sequence of confident,
wrong fixes: "bring up the overlay" is not the fix if the host proxies to a port nothing inside the
container listens on, and widening the container bind is not the fix if the peer cannot see the node.

## The defect that looks like a working proxy

**A container on a bridge has its OWN `127.0.0.1`.** The host's loopback is a different namespace. So a
host-level forward aimed at loopback — `tailscale serve --tcp=8642 tcp://127.0.0.1:8642`, a systemd socket
proxy, an SSH `-L` — **proxies to the HOST's loopback, where nothing is listening.**

Measured: the forward reported success and listed the tailnet address it was serving on, while every
connection through it returned `000`. The service was healthy the whole time — it was simply in another
network namespace, bound to the container's own loopback.

**Tell: the forward's own output is green and the served address still refuses.** A forward is a claim about
where traffic GOES, never evidence that anything is there. Bind facts must be read from the kernel.

## Read the ACTUAL bind from the kernel, not from a probe or a default

A connect probe tells you one address failed; it does not tell you what is bound. `/proc/net/tcp` does.

```bash
# 1. find the listener row for the port (hex, lowercase, no 0x)
python3 - <<'PY'
for line in open('/proc/net/tcp'):
    p = line.split()
    if len(p) > 3 and p[1].endswith(':21C2'):        # :21C2 == port 8642
        hexip, port = p[1].split(':')
        ip = '.'.join(str(b) for b in reversed(bytes.fromhex(hexip)))
        st = p[3]                                     # 0A == LISTEN
        print(f'{ip}:{int(port,16)}  state={st}  inode={p[9]}')
PY
```

**Decoding:** `0100007F` = `127.0.0.1` (loopback only) · `00000000` = all interfaces · anything else is that
address. State `0A` is LISTEN. **A single `0100007F` row is proof the service is unreachable from outside its
namespace**, whatever any config file says.

**Find the owning process by socket inode** — this names the profile/instance, which matters when several run
at once:

```bash
n=<inode from above>
for p in /proc/[0-9]*; do
  for fd in $p/fd/*; do
    [ -e "$fd" ] || continue
    [ "$(readlink "$fd" 2>/dev/null)" = "socket:[$n]" ] && {
      echo "pid $(basename $p): $(tr '\0' ' ' < $p/cmdline | cut -c1-120)"
      tr '\0' '\n' < $p/environ | grep '^HERMES_HOME='
    }
  done
done 2>/dev/null
```

**⚠️ Connecting to `0.0.0.0:<port>` proves nothing** — on Linux that resolves to loopback, so it "succeeds"
whenever loopback does. It is not evidence of a wildcard bind. Use `/proc/net/tcp`.

## Where the bind is configured

Read the resolution order from the code before editing configuration — the constant is not always the
answer. For the Hermes api_server (the multiplexer's single listener):

```python
host = extra.get("host", os.getenv("API_SERVER_HOST", DEFAULT_HOST))   # DEFAULT_HOST = "127.0.0.1"
```

So `platforms.api_server.host` in `config.yaml` wins over the env var, and the env var over the compiled
default. **`config.yaml` is the right home for it** — it is a *setting*, not a secret (secrets belong in
`.env`). Write it with the tool, not by hand:

```bash
HERMES_HOME=<default-profile-dir> hermes config set platforms.api_server.host 0.0.0.0
HERMES_HOME=<default-profile-dir> hermes config get platforms.api_server.host   # read it back
```

The explicit `HERMES_HOME` matters: run without it and the write lands in whichever profile your shell
resolves — **not the listener's**. Snapshot the file first and confirm the profile you did not mean to touch
is unchanged.

**A bind change needs a restart of the listener's process; a config WRITE does not.** So the write is safe to
do while the service is live — but say which process must restart, and name what else restarts with it.

## Choosing the bind, and the two fragility layers

- **Binding `0.0.0.0` inside a bridge-networked container is not a public exposure.** A Docker bridge
  (`172.16.x.x/24`) is not publicly routable; the only thing that makes the port reachable from outside is the
  host forward, which is deliberate. **Say the reasoning out loud when recommending it** — "wildcard bind"
  reads as reckless otherwise.
- **Prefer exposing via the host forward over binding the overlay IP directly.** A bind pinned to the overlay
  address (a) fails to start if the overlay daemon is not up yet, taking the whole service down at boot, and
  (b) breaks silently when the overlay address changes. A loopback bind plus a host forward has neither
  failure mode.
- **⚠️ Two addresses can move underneath you: the overlay IP and the container's bridge IP.** An overlay node
  that is re-registered gets a NEW address (measured: it changed on reinstall, invalidating every config that
  hardcoded the old one). **Use the overlay's MagicDNS NAME, not the IP** — a name follows the node; an IP must
  be re-discovered and every consumer updated. For the bridge address, expect it to change on container
  recreate and re-check it after one.

## Diagnosing the peer side

On the far machine, three readings separate "node down" from "path wrong":

```bash
tailscale status            # is the TARGET node listed, and does it say offline + "last seen"?
ping <target-address>       # 100% loss => the node is not on the overlay at all
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 8 http://<name>:<port>/<path>
```

**Expected codes, and they are not interchangeable:** `000` = nothing answered (transport) · **`401` =
reached it and it wants credentials — this is SUCCESS for a reachability test** · `200` = reached it.
**State the expected code up front**, because a test whose pass condition is unstated gets read as a failure.

## Reported flow when the last leg was not yet proven

This file was distilled from a diagnosis that was completed and kernel-verified up to the bind, where the
remaining step was the listener restart (owned by the user, on the host). **State which legs were PROVEN and
which are the diagnosed next step** rather than presenting the whole chain as validated:

- ✅ proven: the container's `127.0.0.1` is not the host's; the listener binds loopback only (kernel-read);
  the host forward aimed at loopback therefore had nothing to reach; the overlay name resolves.
- ⏳ next step, reasoned from the above: widen the container bind, restart the listener, point the host forward
  at the container's **bridge** address, then re-probe for `401`.

**A diagnosis is a deliverable even when the repair has not run.** Say which half you have.
