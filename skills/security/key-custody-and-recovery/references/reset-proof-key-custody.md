# Reset-proof key custody — implementation

Reference implementation used by the GenTech treasury seat. Read the custody rules in SKILL.md first;
this file is the depth.

## Tool

`profiles/gentech-treasury/tools/treasury_keystore.py`, run on
`profiles/gentech-treasury/venvs/treasury-venv` (venv built with `uv`; needs `eth-account` and
`cryptography`). No `age` or `gpg` on the box — the crypto is the Python libs.

| command | what it does |
|---|---|
| `init --names a,b --out DIR` | generates EVM keypairs, one AES-256-GCM bundle, 3 passphrase shards. Refuses to overwrite an existing bundle without `--force`, because re-init strands the old keys |
| `show --out DIR` | prints recorded addresses + bundle sha256 — **no secrets** |
| `selfcheck --out DIR` | drills all three 2-shard combinations against the recorded addresses, and asserts a single shard opens nothing |
| `restore --shard F1 --shard F2 [--dump-dir D]` | rebuilds the passphrase, decrypts, derives each address, prints `MATCH`/`MISMATCH`, then `RESTORE DRILL: PASS|FAIL` |
| `publish --vault DIR` | copies **ciphertext + public index only** into the vault; refuses if a shard-like file is already in that directory |
| `seal --out DIR [--confirm]` | deletes the on-host shards — refuses without `--confirm`, because before the off-host copy exists that destroys the only copy |

## Layout the invariants imply

```
ciphertext  ->  may live on the host, and is published into the vault (the one off-host channel)
passphrase  ->  split 2-of-3 (Shamir); shards go somewhere that is NOT this host and NOT the vault
wallets     ->  generated only after the drill passes; funded last
```

When the vault's own transport is the only off-host leg, it is the right place for the **ciphertext** and
exactly the wrong place for the shards — putting them beside the bundle collapses two factors into one
directory. Enforce that separation **in code** (the publish step refuses on a shard-like filename), not
by convention, because conventions drift and a directory listing does not.

## Build notes

- Private keys are never written to disk in plaintext: AES-256-GCM with an scrypt-derived key. Two keys
  make a bundle of a few hundred bytes.
- Shamir over GF(2^8) with the AES polynomial `0x11b`; reconstruct by Lagrange interpolation at x=0. The
  standard library has no modular inverse over that field — square-and-multiply to `a^254` works.
- Use a **random per-bundle passphrase** so a leaked shard pair cannot be replayed against a later keystore.
- Guard destructive verbs (`init` over an existing bundle, `seal`) with an explicit refusal path and a
  distinct non-zero exit. A tool that silently overwrites a keystore is a key-loss machine.

## Expected drill output

```
shards (1,2) -> PASS      shards (1,3) -> PASS      shards (2,3) -> PASS
single shard breathes on its own -> PASS (it does not)
SELFCHECK: PASS
```

Quote this before funding. A drill that was never run is not evidence.

## Where the ciphertext copy actually travels (audited, not assumed)

Listing a host-backup archive built by the agent's own product gave, in one measurement:

| path in the archive | entries | reading |
|---|---|---|
| the synced vault's `*-keys.enc` | 2 | ✅ ciphertext **is** carried |
| the synced vault's `*-keystore.json` | 2 | ✅ addresses + hashes carried |
| `shards/` | **0** | ✅ **correct — the means are NOT carried** |
| the working key directory outside the product home | **0** | ⚠️ **not** carried — the vault copy is the only one in the archive |
| the recovery manifest | 0 | timing only, if written after the run started |

**The rule that table encodes: the archive takes the ciphertext and leaves the shards, so it can live
anywhere.** But the fourth row is the trap — an agent product's backup is **not** a keystore backup, and it
covers the key material only because the synced vault happens to sit inside the product home. Keep the
publish step running, or the archive silently carries a stale bundle.

## The human step is the critical path

Until **two shards are physically somewhere that is not this host**, the keystore protects against
corruption and operator error but **not** against a host reset. Hand it over as paths plus destinations:

1. copy shard 1 and shard 2 to two *different* off-host places (phone, USB, hardware-wallet backup);
2. put shard 3 somewhere separate again;
3. only then `seal --confirm`, so "ciphertext here, key not-here" becomes true rather than aspirational.

If the shards are still on the host after a session, say so plainly in the report. That sentence is the
difference between a protection and a claim about one.

**Generate the shard-destination table; do not remember it.** A recovery manifest written by the publish
step — addresses, bundle hash, the destination of each numbered shard, and the restore command with its
pinned interpreter — turns *"we hold a backup"* into *"here is what opens it and where each piece lives"*.
A restorer after a wipe has files and no memory; ciphertext without instructions is not a recovery path.
