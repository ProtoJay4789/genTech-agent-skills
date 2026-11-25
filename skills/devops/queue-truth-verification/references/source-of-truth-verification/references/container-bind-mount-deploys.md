# Deploying into a container that serves a bind-mounted file

For when a running container serves a file that lives on YOUR side of the filesystem — a manifest, a
config, a public document. Four attempts can fail here while every check says the edit is correct.

## The sequence, in order

### 1. Find what the container actually reads

```bash
docker exec <ctr> grep '<basename>' /proc/self/mountinfo
```

`mountinfo` names the **host source path** and the mount flags. `/proc/mounts` shows only the device
(`/dev/sda1`), which tells you nothing about which host file it is.

Read the line's shape:

```
1536 1508 8:1 /docker/<stack>/data/.obsidian-vault/.../public-copy/x402-bazaar
          /var/www/site/.well-known/x402-bazaar ro,relatime - ext4 /dev/sda1 ...
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ host source         ^^ read-only mount
```

- **No line at all** → it is an ordinary file in the container layer, and `docker cp` works normally.
- **A line with `ro`** → `docker cp` can never replace it (see step 2).

Distinct from `docker ps` mounts: `docker ps` lists directory binds, not single-file binds, so a
single-file mount is invisible there.

### 2. Know that `docker cp` lies on a read-only bound file

```
Successfully copied 8.39kB (transferred 10.2kB) to ctr:/var/www/.../x402-bazaar
Error response from daemon: RemoveAll x402-bazaar: device or resource busy
```

Both lines are about the same operation. Docker's `cp` removes the destination before writing; the
`ro` bind refuses the removal; **the success line is printed anyway and the served bytes never move.**
`device or resource busy` is the truthful line.

Also: **`docker cp` runs on the HOST.** A container path like `/opt/data/...` is not a host path — the
host path comes from step 1. Passing the container's bind target as the source is the other way this
fails with `lstat ... no such file or directory`.

### 3. Write the HOST file IN PLACE

Because the mount is bound to an **inode**, not to a path:

- plain `open(path, 'w')`, truncate-and-write, or `cp` over the destination → **same inode**, container
  sees the new bytes on its next read (and on restart for anything cached at import).
- temp-file + `os.replace` / `mv` / editor "safe write" → **new inode**, the container stays bound to
  the dead one, and the restart serves stale content with no error anywhere.

```python
ino_before = os.stat(p).st_ino
with open(p, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
assert os.stat(p).st_ino == ino_before, "write replaced the inode — the mount is now stale"
```

**Verify with the inode, never with the copy message.** Equal inode before/after is the proof; a
`Successfully copied` line is not.

### 4. Restart only if the process reads at import

A server that does `MANIFEST = json.load(open(PATH))` at module import holds the old bytes until the
process restarts. A server that opens per request needs no restart. Check which, and say which —
"deployed" for an import-time read that has not been restarted is a claim about the file, not the
service.

### 5. Confirm through the container, not from your side

```bash
docker exec <ctr> python3 -c "import json;d=json.load(open('/served/path'));print(d['key'])"
```

Your side and the container's side can disagree for a minute after a mount change. The prose above is
the container's view of the file; the public endpoint is the container's view after any filter.

## Why a structural diff of the live payload points at the WRONG file

If the handler filters or reshapes at request time, the live document is a **projection**, so matching
it against a file selects whichever file happens to match after filtering. Measured: the served payload
held 9 services while the file being served held 14 — the five withheld ones were dropped in the
handler. The payload matched a decoy copy that held 9, and two rounds of "fix verified on disk" went
into files with no reader.

**The mount table is evidence; a payload match is a coincidence.**

## Checklist before any bind-mounted deploy

1. `docker exec <ctr> grep '<basename>' /proc/self/mountinfo` → host source + flags
2. Is the mount `ro`? If yes, `docker cp` is not a write path at all
3. Write the host file **in place**; assert `st_ino` unchanged
4. Restart only if the read happens at import — and check the process, not the docs
5. Verify through the container (`docker exec ... cat <served path>`) and then on the public surface
