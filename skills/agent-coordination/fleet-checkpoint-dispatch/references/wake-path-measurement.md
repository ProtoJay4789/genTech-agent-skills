# Measuring the wake rail before a dispatch

The wake path's state CHANGES, so measure it every dispatch and trust no note about it — including this
one. Both states have been observed on this fleet.

## The measurement

```bash
# 1. What is registered, and at what URL/port?
hermes peer list

# 2. Is anything actually listening?  `ss` is frequently absent in a container, so an `ss`-based
#    check returns EMPTY and reads as death. Use /proc/net/tcp instead: state `0A` == LISTEN.
python3 - <<'PY'
for line in open('/proc/net/tcp').read().splitlines()[1:]:
    f = line.split()
    if len(f) > 3 and f[3] == '0A':
        port = int(f[1].split(':')[1], 16)
        if 8600 <= port <= 8700:
            print('LISTEN', port)
PY
```

## Reading the two states

| state | what you see | what it means |
|---|---|---|
| DOWN | `hermes peer list` → *"No peers registered"* | nothing to announce; the vault file is the delivery |
| UP | a peer registered (e.g. `fleet http://127.0.0.1:8642 …`) **and** a port LISTENING | dispatch over it, and prove the reply |

**`:8642` is the multiplexer itself** after a gateway convergence — that is the port to LOOK FOR, not
evidence of death. Only a live probe (registered peer + listening port + a reply from a named seat) tells
you the rail is up. A dark report may be a blind test, not a dead service: confirm the server before
believing the client.

## Sending, and capping the block

`peer dm` BLOCKS until the reply, so cap it — and read the real results as described in SKILL.md:

```bash
timeout 150 hermes peer dm "fleet/<seat>" "<one-line pointer to the checkpoint file>" \
  > /tmp/dm-<seat>.out 2> /tmp/dm-<seat>.err
rc=$?
printf 'rc=%s bytes=%s\n' "$rc" "$(wc -c < /tmp/dm-<seat>.out)"
```

`rc=124` means `timeout` cut off a live turn (the seat may still have acted). A `bytes=0` with `rc=0` is
UNPROVEN. Neither is a refusal, and neither is a delivery.

## Fallback when the rail is dark

File the record anyway, state in it that the wake FAILED with the error verbatim, and do not block on a
channel that cannot answer. A wake that never landed must never be reported as a wake — but a dark channel
is still not consent, so the gate stays with the human.
