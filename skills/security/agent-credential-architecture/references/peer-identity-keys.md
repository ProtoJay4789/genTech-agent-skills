# Peer identity keys — minting and publishing a seat's own key

The peer-mesh registry (`roster.json` in the shared tree) is an **allowlist**: it maps a seat's issuer string to
the public hex of the key it signs with. Getting a key into it is a credential operation with a shared-file write,
which is where the two failure modes live — a private half that gets synced, and a publish that wipes the registry.

## Shape

| half | where | rule |
|---|---|---|
| **private** | `profiles/<seat>/secrets/peer-mesh/<seat>.ed25519`, mode `600` | **outside** any synced or tree-managed folder. A VCS/note sync replicates every file it can see, including a backup you forgot you made. |
| **public** | merged into the shared registry as `<issuer>/<seat>` → hex | safe to publish; it is the thing that lets peers verify you |

The issuer string is structured (`<caip-namespace>:<chain-id>:<contract>:<token-id>/<seat>`); **read it out of the
registry or the derivation output — never retype it.** A single wrong digit produces a valid-looking identity that
no peer can verify.

## Procedure

1. **Prove the path guard before generating anything.** Call the keygen's guard twice, in this order:
   - a path **inside the synced tree** → must be **REFUSED**;
   - the intended `profiles/<seat>/secrets/...` path → must be **ALLOWED**.
   A guard whose root is a default that does not exist on this host passes *everything*; see
   `guard-verification` §1c. Only the refusal is evidence.
2. **Back up the registry first**, to a path **outside** the synced tree, named with a UTC stamp.
3. **Mint only your own seat's key.** Another seat's identity is theirs to mint and theirs to publish — publishing
   on their behalf puts a key the fleet cannot attribute into the allowlist.
4. **Publish by MERGING into the parsed document, never by calling the writer.** A
   `publish_roster()`-shaped helper typically writes only `{updated_at, keys}` — so calling it with one entry
   **drops every other member's key and every note/prune field** and still reports success. Parse the file, set
   your one entry, bump `updated_at`, write the merged object back.
5. **Read back and diff.** Your entry present; every other entry **byte-identical**; note and prune fields
   preserved; print the key count. "It is in the roster now" is an unverified claim until a fresh parse says so.
6. **Scan the synced tree for the private material, and report a VERDICT only** —
   `files containing private key material: NONE`. Never echo the value, a fragment, or a match line; a scan that
   prints what it found has published the secret it was checking for.
7. **Confirm the hygiene:** the backup sits outside the synced tree, and no `.bak-*` remains inside it.

## Pitfalls

- **A whole-document writer is a whole-document delete.** Any registry, roster or ledger whose publish function
  rewrites the file from a partial in-memory structure turns a one-seat update into a fleet-wide loss. Grep the
  writer's body for what it constructs before calling it.
- **Deriving an address from a private key: read the key from stdin.** Command-line arguments are world-readable via
  `ps` on a shared host. A five-line helper that reads stdin and prints only the address costs nothing and removes
  the exposure permanently; `argv` does not.
- **A retired seat's entry is a routing invitation.** Prune it when the seat retires and record that the prune was
  deliberate, so a later reader does not re-add it while tidying.
- **Handoffs have described this registry from memory and been wrong in the direction of "absent".** When a peer
  says a key is not published, parse the file before believing it or agreeing — the cached figure is the one that
  disagrees with reality, and the disagreement is invisible unless someone re-reads.
