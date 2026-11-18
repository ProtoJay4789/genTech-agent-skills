# Reading a file out of a remote container image — without Docker

**When:** you need a fact that lives INSIDE a published image (its version stamp, its bundled config) and
you cannot run `docker pull` — typically because you are inside a container whose Docker socket is denied
and the host is not yours to touch.

**Why not just ask the image:** `docker run --rm <image> --version` is a trap — the image's ENTRYPOINT is
its init system, so the flag is swallowed and a full service starts. And `docker inspect` shows *labels*,
which may be **inherited from a base image and name a different product entirely** (measured: an image
whose labels described the base image's catalog feature, not the payload). **Labels are not the payload.**

## The recipe (GHCR, anonymous, read-only)

```python
import json, io, tarfile, urllib.request

repo = "<owner>/<name>"
ACC  = ",".join(["application/vnd.oci.image.index.v1+json",
                 "application/vnd.docker.distribution.manifest.list.v2+json",
                 "application/vnd.docker.distribution.manifest.v2+json",
                 "application/vnd.oci.image.manifest.v1+json"])

tok = get(f"https://ghcr.io/token?scope=repository:{repo}:pull")["token"]   # anonymous pull token
H   = {"Authorization": f"Bearer {tok}", "Accept": ACC}

idx = get(f"https://ghcr.io/v2/{repo}/manifests/latest", H)
amd = next(x for x in idx["manifests"]                    # multi-arch index -> pick a platform
           if (x.get("platform") or {}).get("architecture") == "amd64")
man  = get(f"https://ghcr.io/v2/{repo}/manifests/{amd['digest']}", H)
layers = man["layers"]
hist   = get(f"https://ghcr.io/v2/{repo}/blobs/{man['config']['digest']}", H)["history"]

# -- the key move: history maps to layers 1:1 --
# every history entry WITHOUT empty_layer consumes exactly one layer, in order. So created_by
# tells you WHICH layer wrote a file -- and that layer is usually tiny.
li, target = 0, None
for h in hist:
    if h.get("empty_layer"):
        continue
    if "<path fragment of the file you want>" in (h.get("created_by") or ""):
        target = layers[li]
    li += 1

# -- fetch ONLY that layer and pull the file out of the tar --
raw = get_bytes(f"https://ghcr.io/v2/{repo}/blobs/{target['digest']}", H)
tf  = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
for nm in tf.getnames():
    if nm.lstrip("./").endswith("/<filename>"):
        print(tf.extractfile(nm).read().decode())
```

## Why this beats pulling

- **Bytes.** A version stamp lives in a layer of a few KB; the image is often >1 GB. Fetch the small
  layer, ignore the rest.
- **No Docker.** Pure HTTPS + `tarfile`. Runs from inside a seat.
- **Re-runnable.** Safe to run on a schedule as a change watcher.

## Pitfalls

- **Use the history->layer mapping; do not blind-scan layers for the file.** Scanning works, but it can
  land on a *stale earlier copy* — a file copied early in the build and overwritten later. **The highest
  layer index that contains the file wins.**
- **`created_by` strings are truncated** for some build steps; match on the path fragment you care about,
  never the whole command line.
- **Do not depend on the `Docker-Content-Digest` response header** — it is not reliably exposed through a
  plain urllib call. Read the digest from the manifest body.
- **Distinguish "read it, and it says the same version" from "I could not read it."** Those are opposite
  answers (no-update vs failed-probe) and must never print the same thing. Make the failure path loud.
