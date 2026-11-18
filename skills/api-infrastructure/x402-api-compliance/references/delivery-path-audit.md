# Delivery-path audit — is there anything behind the price list?

Use when a gateway/API advertises paid routes and you need to know whether it can actually
serve them. The price path answering is NOT evidence. Do this audit before promising uptime,
discoverability work, or a rating fix.

## 1 · Enumerate the backend addresses from the source, not from memory

The route map in the server file is the authority. Read it rather than recalling ports:

```bash
grep -n -A2 'BACKEND_ROUTES\|SERVICES *=' <server.py>
```

Every tuple's first element is the exact address the proxy will call (`http://127.0.0.1:<port>`
by default). Collect them; do not assume the set is small or contiguous.

## 2 · Probe from the network the gateway actually runs in

**Loopback inside a container is not loopback on the host.** In bridged or non-host networking,
`127.0.0.1` inside the container is the container itself. A host-run service is unreachable there
even when it is perfectly healthy. Probe from *both* vantage points before drawing a conclusion:

```bash
# inside the gateway container
docker exec <gateway> sh -c 'for p in <ports>; do printf "%s " $p; \
  curl -s -o /dev/null -w "%{http_code}\n" --max-time 3 http://127.0.0.1:$p/v1/health; done'

# and from the host's own namespace
for p in <ports>; do printf "%s " $p; \
  curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://127.0.0.1:$p/v1/health; done
```

`000` means nothing is listening on that port from that vantage — not "unhealthy", "absent".
Record which vantage produced which number; the pair is the finding.

## 3 · Check the process table before believing a networking story

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'
```

If the backends are neither in this list nor listening on the host, the problem is not
addressing — the services are gone, and no amount of route rewriting will help.

## 4 · Before calling it a rebuild, look for the sources

Search for each service by name across the vault and the data tree:

```bash
for n in <service names>; do find <roots> -maxdepth 5 -iname "*${n}*" \
  -not -path '*/node_modules/*' -not -path '*/.git/*' | head -3; done
```

Also check any pre-migration snapshot directory. Restore beats rebuild: a service whose source
survives is a deployment task, not a re-implementation.

## 5 · Translate paths before handing a user a command

A path you can read inside the container is usually NOT valid in the host shell. Resolve the
binding first — `/proc/self/mountinfo` names the host-side source — and give the user the host
path, or a `docker exec` form, never the container-internal path.

## 6 · What to report

Report the *pair* of measurements per port, and separate three findings that get conflated:

- **nothing listening** (a delivery failure — money can move with nothing delivered)
- **listening but erroring** (a service bug)
- **not running anywhere, source gone** (a rebuild decision for the owner, not a config fix)

If a status endpoint reports the backends as down, re-examine the assumption that it is lying.
A status page that says `down` while the price path answers `402` may simply be correct.
