# One source of truth for secrets across seats on ONE host

**Use when** several agent seats share a machine and filesystem, and the same credential currently
lives as N hand-copied files. This is the *same-host* implementation of "prefer sharing by SOURCE over
sharing by COPY". When seats are on **different** machines, this does not apply — use a provider-side
manager, or hand over then rotate (see SKILL.md).

**What it buys:** one value by construction, so a rotation is one write and no seat is silently stale.
**What it does NOT buy:** isolation. Seats sharing a host and uid can read each other's files regardless
of layout — see the per-seat-isolation rule in SKILL.md.

## Layout

```
<shared-root>/            mode 700  — one source of truth
  <secret-name>           mode 600  — the values
  .manifest.json          size + sha256 + source + VALIDITY per entry
  resolve                 the one way any seat reads a secret

profiles/<seat>/secrets/<name>   -> symlink to <shared-root>/<name>
```

**Symlinks matter.** They keep every existing path working — nothing that already reads
`profiles/<seat>/secrets/<name>` needs editing. Replacing files with a moved target is a breaking change
nobody asked for; a symlink is not.

## Procedure

1. **Snapshot first** — this touches files four+ writers share. `tar czf` each seat's `secrets/` to a path
   **outside** the secrets tree (a sibling backup inside it becomes a phantom entry, exactly as in the
   skill-shelf rules).
2. **Build an explicit share / hold list before copying anything.** Verify every entry against the rail
   rules in SKILL.md — API keys share, **money keys never do**, logins go to the login rail.
3. **Populate from the richest copy**, then `chmod 600` each file. Do not assume the newest file is the
   best one; pick by content, and record which seat it came from in the manifest.
4. **Replace per-seat files with symlinks.** Skip paths already symlinked so a re-run is idempotent.
5. **Verify by resolution, not by existence:** for each secret, read it through every seat's path and
   assert the set of hashes is a single value. `N/N resolve identically` is the acceptance test; "the file
   exists" is not.
6. **Probe and record validity** on population, and re-probe on any rotation. See the probe rules in
   SKILL.md — capability endpoint, never `/verify`.
7. **Confirm the hold list is still held** by counting copies of the excluded items. A sharing pass that
   quietly swept a wallet key in is the failure that matters most.

## The `resolve` helper

One reader, so a layout change is one edit and every caller keeps working.

```sh
resolve <name>     # print the value (stdout)
resolve --check    # probe known-broken entries; exit non-zero if any
resolve --list     # names + validity, never values
```

**Design points that are load-bearing:**
- `--check` must **exit non-zero** when anything is broken, so it composes into other tooling as a gate.
- `--list` must **never print a value** — it is the safe thing to paste into a report.
- The helper should **own the secret names**, so callers never hard-code a path.
- Prove the exit codes **both ways** before trusting them: a known-broken state exits non-zero *with a
  message*, a known-good state exits zero. A guard that exits non-zero by raising looks identical to one
  that failed cleanly — see the crash-as-pass pitfall in SKILL.md.
- Default to printing a value to stdout and nothing else — never a log line, never a banner. Values on
  stdout end up in transcripts; anything noisy on stdout gets them there too.

## Rotation

Rotate by writing the ONE file, then re-probe and update the manifest. Do not touch the per-seat paths —
that they are symlinks is what makes this a one-step operation. **If a rotation ever requires editing more
than one file, the sources were not consolidated and the copy-drift is still live.**

## Migrating away

This layout is an interim, not a destination: it has no per-seat access control, so it trades isolation
for consistency. Leaving it means moving to a provider-side manager (`hermes secrets` or a broker) whose
boundary is the provider's, not a directory. **Say which property you gained and which you gave up**
whenever you describe this deployment — "shared" here is convenience, not a security boundary.
