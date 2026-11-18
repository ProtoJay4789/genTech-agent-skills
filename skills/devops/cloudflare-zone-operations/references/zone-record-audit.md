# Zone record audit — enumerate, probe, classify

Use when asked which hostnames/records on a zone are still needed. Read-only until the owner names a prune
set. Rule 9 in SKILL.md is the summary; this is the runnable pass.

## 1. Build the candidate list from the vault, not from memory

```bash
# every hostname the brain mentions, most-referenced first
grep -rhoE '([a-z0-9-]+\.)+example\.com' --include='*.md' --include='*.html' --include='*.json' . \
 | sed -E 's/^([a-z0-9.-]+)\.example\.com$/\1/' | sort | uniq -c | sort -rn
```

- **Allow for noise.** Doc examples and probe names (a literal `-probe`, a scratch hostname) appear in this
  list and are not real subdomains. The API in step 2 is what settles it.
- **A hostname that appears only in docs and nowhere in the API is a phantom** — the fix is the reference,
  not a DNS delete.

## 2. Pull the authoritative config

```python
GET /zones?name=example.com                    -> zone_id
GET /zones/{zone_id}/dns_records?per_page=100  -> type,name,content,proxied,id
GET /zones/{zone_id}/workers/routes            -> pattern -> script
```

Bucket the A/CNAME targets: origin IP versus a provider hostname (`*.pages.dev`, `*.workers.dev`).

## 3. Probe every hostname for status AND body

```python
req = urllib.request.Request(f"https://{host}/", headers={"User-Agent": "audit"})
with urllib.request.urlopen(req, timeout=10) as r:
    code = r.status
    body = r.read(4000).decode("utf-8", "ignore")
```

Record `code`, a title/body fingerprint, and for JSON endpoints the first bytes of the body. Thread it
(12 workers is plenty) so 40 hostnames cost one timeout, not forty.

**Do not stop at the status code.** Observed in one zone: a Worker returned **`200`** with
`{"error":"Not found"}` — a status-only sweep scored it "serving", and it was serving nothing.

## 4. Two safety checks

- **Wildcard.** A `*` record makes every 404 the catch-all. Confirm none exists before attributing a 404 to
  a specific hostname.
- **Takeover.** For every CNAME to a provider hostname, fetch the target directly. If the target has been
  deleted, the record is claimable by a third party — report it as a security finding with its own severity,
  not as a broken site.

## 5. File the result BEFORE naming a prune list

The output is a status table, not a verdict. Any hostname named in an approved architecture note, spec, or
build-queue entry is **down, not dead** — its record is the plan. Only hostnames in no intent record are
deletion candidates, and the owner names that set.

Report per bucket with the count and the probe used, e.g. *"37 hostnames probed: 2 serving, 6 broken, 18
reachable-but-404, 8 no-DNS, 1 phantom route; 0 wildcard; 8/8 CNAME targets alive, so no takeover risk."*
