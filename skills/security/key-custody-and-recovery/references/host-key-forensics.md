# Host-side key forensics — where a key can still be after a wipe

Companion to the custody rules in SKILL.md. Use when a wallet's key is missing and the question is *"can it
still be recovered, or is it a write-off?"* — the answer is decided by a search that reports its denominator,
plus three host locations the agent cannot reach and must name instead of hand-waving about.

---

## Order of work — cheapest and widest first

1. **Derivation sweep of the readable estate** (below).
2. **Docker inventory** — images, dead containers, volumes.
3. **Name what is outside the agent's reach** and hand over exact commands.

Do not start at step 3. "Ask the human to look in /root" is the last resort, not the plan, and it returns no
numbers.

---

## The derivation sweep, and the trap in its own output

Scan every TEXT file for a 64-hex run, derive each to an address, compare to the target. Never a filename
pattern, never a grep for the word `key` — a live key has been found in a file whose name matched no pattern.

**Report three numbers, never one:** files scanned · distinct addresses derived · matches for the target.

**⚠️ The derived-address count is inflated by HASHES, and saying so is part of reporting it honestly.**
Every sha256 in the tree parses as a private key and derives a perfectly valid address. A sweep of a
200k-file estate reported *172,046 distinct addresses* whose top hits were Tcl encoding tables and JSON
manifests — digests, not keys. So the sentence to say is:

> *"Among every 64-hex string on this host — keys and hashes alike — not one derives to the target."*

That is a strong, bounded negative. *"172,046 keys exist"* is a false alarm, and *"I found nothing"* is
not a measurement.

**⚠️ A random token can derive as a key too.** An `API_SERVER_KEY`-style 64-hex secret derives to a valid
address and looks exactly like a hit. Before reporting "key material found in <file>", read the VARIABLE
NAME the string is assigned to. A random hex token is not a wallet key, and announcing one as such starts a
false incident.

**A zero needs a positive control.** If the sweep cannot derive anything at all (missing `eth_account`, a
read error), it reports the same zero as a genuinely clean tree. Confirm the tool can produce addresses from
one known-good fixture before trusting the zero.

---

## Docker: what a deleted container leaves behind

A container's data outlives it in three places, in increasing order of yield:

```bash
docker images --format '{{.Repository}}:{{.Tag}}  {{.ID}}  {{.Size}}'
docker ps -a   --format '{{.Names}}  {{.Image}}  {{.CreatedAt}}  {{.Status}}'
docker volume ls
```

- **An image is code, not data.** A rollback tag from an unrelated update holds no user keys, and checking it
  is not a recovery path. Say so rather than leaving it on the list of hopes.
- **Anonymous volumes are where a deleted container's home directory goes.** `docker volume ls` prints opaque
  hashes; nothing is named, so nothing is obvious. A volume that holds `SOUL.md`, `config.yaml`, `.env`,
  `cron/`, or `state.db` at its root is an agent profile.

### Telling a LIVE agent from an orphan — mtime, not hope

```bash
mp=$(docker volume inspect <vol> --format '{{.Mountpoint}}')
find "$mp" -type f -newermt '-90 minutes' | wc -l
```

**`cp -a` PRESERVES mtimes.** So after copying a volume into a readable tree, a file dated minutes ago dates
the ORIGINAL, not your copy. That is how you distinguish an abandoned remnant from a **running agent whose
identity may not be in your roster** — and the second one is a finding about cost and access, not about keys.

**Consequences, in the order they matter:**

1. **An orphan cannot hold a pre-wipe key** if it is writing right now — check liveness BEFORE sweeping it,
   or you spend a pass on the wrong object.
2. **A copied live profile carries live credentials.** Copy read-only (`:ro`), and **delete the copy in the
   same session** — it will contain `API_SERVER_KEY` and channel tokens. A root-written copy may be
   undeletable by the agent's uid; hand the owner the exact `rm -rf` path rather than leaving it in place.
3. **Live-but-unknown containers belong in the report** even when the key hunt succeeds elsewhere.

---

## Encrypted bundles that guard the WRONG address

Finding `*.enc` bundles with Shamir shards beside them is not a recovery. **Read the keystore index and
compare the address it declares to the address you actually want.**

If the index names the post-wipe *generated* address (nonce 0, empty) while the funded wallet is a different
address, then: **the machinery works perfectly and protects nothing you need.** That is evidence the keystore
minted a replacement instead of restoring a recorded key — a mechanism defect, not a data loss.

**The guard to install:** a keystore must REFUSE to generate for a tenant whose recorded address it holds no
key for, and name the missing key. Two checks make it real — point it at a consistent store (must pass) and
at a mismatched recorded address (must fail). A guard only exercised on the happy path is untested.

---

## Closing out: retirement beats a fourth search

After a sweep with denominators and an inventory that finds nothing, the honest output is **RETIRED —
UNRECOVERABLE — DO NOT FUND**, recorded with:

- **balances read at retirement** (so the record states what was left, not merely that it is gone),
- **the reason measured**, with the denominators,
- **instruction files corrected and history files left alone** — a dated ledger naming the old address is
  evidence of a past spend; rewriting it destroys the record. Edit skills, configs and scripts; annotate
dated notes with a status banner *after* the first heading.

**A funded-looking address is more dangerous than an empty one.** Empty needs no rule. A wallet holding a
visible balance invites someone to "test" it — which is why the do-not-fund line is the load-bearing part of
the retirement record.
