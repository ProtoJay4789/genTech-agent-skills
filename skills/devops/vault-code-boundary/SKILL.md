---
name: vault-code-boundary
description: Use when code or logs sit in the vault, not notes.
---

# The brain is for notes. Code lives in a repo. Enforced by a checker, not by intent.

**Jordan, 2026-11-04:** *"Any type of live code should go on GitHub to the repo assigned to the code, because
that way it keeps Obsidian sync from not blowing up."*

He is right, and the measurement is unambiguous: **every top-level project under `10-Labs/` has no `.git` at
all**, and the vault is the only place that code exists. That is why sync carries binary blobs, why the tree grew
to 334 MB, and why one folder alone (`cdp-settle/node_modules`) was 152 MB of files Obsidian had to replicate.

## The rule, in one line

> **Code and its build output live in a git repo. The vault holds the note that points at it — and nothing else.**

## The boundary, by file class (not by folder name)

| class | examples | where it belongs |
|---|---|---|
| **live code** | `.py .js .mjs .ts .sol .go .rs`, `Dockerfile`, `requirements.txt`, `package.json` | **git repo** — the one assigned to that project |
| **build output / dependencies** | `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `*.log` | **never tracked anywhere** — `npm ci` / rebuild |
| **note** | `.md`, images, PDFs, small JSON *read by a human note* | **vault** (Obsidian sync) |
| **runtime data read by a live service** | `defi-data.json`, `travel-jordan.json`, keys' public IDs | vault **only if** the service reads it there — otherwise move it with the code and update the path |

## What this means for the repo that currently has no home

**`10-Labs/x402-gateway/` is the case in point.** ~90 files, 52 of them code (`server.py` 192 KB), no `.git`, and
the container runs it from this path by bind mount (`-v …/x402-gateway:/app`). So:

1. **Do not move the folder.** The live container mounts this exact path — a move takes the paid API down.
2. **Put a git repo around it in place** (`git init`, `.gitignore` for `logs/`, `__pycache__`, `*.log`,
   `deployed-snapshot-*`), then push to `Gentech-Labs/programmable-money-x402` (or a new `gentech-x402-gateway`).
3. **Then** the vault stops being the source of truth for that code: the repo is. The vault keeps
   `10-Labs/x402-gateway/README.md` (or a `POINTER.md`) naming the repo and the mount path.
4. Only after a verified clone elsewhere could the container be re-pointed — and that is a separate, deliberate
   change with a rollback, not part of a tidy-up.

**Never move code out of a running mount on the strength of a rule.** The rule says where new things go; it does
not authorise cutting a live wire.

## ⚠️ A RENAME is a MOVE — measure the contents and the references first

**An org-chart change is not a reason to rename a directory.** "Department X took over that lane, so rename its
folder to X" conflates *who owns the work* with *what the folder holds* — and the contents usually disagree.

**Measure in this order, and stop if any step surprises you:**

1. **File count per subtree.** The largest child may be infrastructure rather than the department being named.
   Measured on one "labs" folder: of ~2,200 files, one subtree was the fleet's **skills tree** and another was a
   **production service** — neither of them educational, both of them load-bearing for every other seat.
   **Handing that folder to the incoming owner is a change of CUSTODY, not a label.**
2. **Live reference sites** — `grep -rlE '(^|[^0-9A-Za-z_-])<folder>/'` over the script trees, cron scripts, routing
   docs and system notes. **Anchor the pattern**; an unanchored substring matches `110-Labs/`. Measured: one folder
   was named in **73 live files**, 47 of them for the service alone.
3. **Mounted or executed paths.** A folder a container mounts or a service imports **cannot be renamed at all** —
   the same red line as moving code out of a mount, wearing a cheaper-looking hat.
4. **Empty-dir count at ALL depths, not empty top-level folders.** The two numbers differ by roughly 3×
   (47 vs 158 on the folder above; 2,671 vault-wide). And **never positional-skip the walk by substring** — filtering
   out paths containing `/.obsidian` also filters out the vault ROOT, and the walk then reports **zero** empty dirs,
   which reads exactly like a clean tree. Check by path SEGMENTS (`set(rel.split(os.sep)) & {".git", ".obsidian"}`).

**When the folder is a junk drawer wearing a department's name, the defect is that NOBODY OWNS IT.** Renaming the
drawer after the new tenant does not tidy it — it puts the new tenant's name on the old mess.

- **Name a custodian per subtree, not per folder** — the biggest child usually belongs to the fleet (HQ), not to any
  one lane. Ownership here means *"you decide what stays, and you notice when it rots"*.
- **Ask the seat who would inherit it, and let "none" be a valid answer.** A lane owner declining the folder is the
  finding that settles the question; re-allocating someone's work without asking is how a fleet stops trusting its
  own routing. Do not edit or claim another seat's material on their behalf.
- **Separate the LANE from the CONTENTS in whatever you write down.** "The function moved to X" and "the files belong
  to Y" are different statements, and only stating both stops the next reader from merging them.
- **Then triage the stubs.** Empty folders are not a loss to delete; keeping dozens makes the handful of real
  subtrees hard to see.

## Enforcement — the classifier, not the honour system

Run `scripts/vault-structure.py --code` (added to the 04:00 maintenance). For each top-level project folder it
reports:

- code files vs note files, and the dominant class
- whether a `.git` exists
- whether any live process references the path (`grep` of the script tree)
- **verdict: `REPO-BACKED` · `NEEDS-REPO` · `MOUNTED-LIVE (do not move)` · `NOTES-ONLY`**

`MOUNTED-LIVE` is the important verdict: it means a running container or service reads that path, so the answer is
"create a repo around it in place", never "move it".

## The three questions before moving anything out of the brain

1. **Does anything execute from this path right now?** (`ps`, `docker inspect` mounts, cron commands, script imports)
2. **Is there a verified second copy?** A push upstream that you have re-cloned and diffed — not "it should be on
   GitHub".
3. **Can it be regenerated?** `node_modules` and `dist` yes; a 192 KB `server.py` with three years of production
   fixes no.

Two "no" answers mean: create the repo first, move later, or never.

## Operational data is a THIRD class — and it is the one that fills the sync quota

The table above splits the tree into code and notes. **The class that actually breaks Obsidian Sync sits between
them: operational data that a live service writes and reads.**

| example | why it does not belong in the vault |
|---|---|
| service traffic/payment logs (`*.jsonl`) | written continuously, read by revenue/ledger scripts, never read as a note |
| settlement ledgers, reconcile state | machine output; grows without bound |
| multi-MB reference dumps fetched by a script | regenerable, and enormous in a synced tree |
| `*.log`, `*.bak`, build snapshots | no reader at all |

**Operational data is not a note, and "a script reads it" is not a reason to keep it in the brain.** The test is
*synced to a human's other devices* — a log nobody will ever open on a laptop pays rent on every device forever.

**The move, in order — and the order matters:**

1. **Move, never delete.** The data is load-bearing; a deleted log is lost revenue history.
2. **Repoint every consumer in the same change.** Grep the whole script tree for the old path *including every
   seat's copy* (the same script is usually vendored per profile), back each file up, then patch. Then
   **re-run one consumer end to end** and confirm it still reads real rows — a repointed path that silently
   falls back to an empty file reads exactly like "no revenue today".
3. **Leave the pointer OUTSIDE the directory you emptied.** A `README.md` written *into* the moved directory
   becomes the one file the next sweep moves out — and the job then reports `✅ moved 1 file` for a fix it did
   not perform. Write the pointer beside the folder, or not at all.
4. **Count what actually moved** by difference (`files before − files after`), never by the mover's own report:
   `mv -n` silently skips existing targets and prints only what it moved, so a summary built from its output
   under-reports.

**Deletions DO propagate while uploads are blocked — the thing that keeps the cap full is the WRITER, not the
account.** Measured: 46.41 MB of media removed → the deletions reached the remote (file-by-file in the sync
log) → **uploads still failed**, on a 6 KB markdown file. The vault was not over-full from history; it was
over-full **because a live service kept writing its log inside the vault**, so every sync started above the cap
again. **Deleting files cannot outrun a writer.** The decisive move was repointing the writer
(`X402_TRAFFIC_DIR` at a mounted path) — after that, deletions landed and uploads resumed in the same run.

- **Find the writer before you delete anything.** `grep` the service source for the path it opens. A file
deleted inside a running service is recreated on the next write, so a delete-only fix has an unbounded number
of rounds.
- **Point the writer at a MOUNTED path, never a host path that merely looks right.** An env var naming
  `/opt/data/<dir>` inside a container creates that directory in the **writable layer** — the data vanishes at
  the next recreate, i.e. the bug relocated somewhere harder to see. Mount it (`-v host:/logs`) and make the
  variable name the mount (`X402_TRAFFIC_DIR=/logs`).
- **Verify UPLOADS, not just deletions.** `ob` exits 0 while failing; read the log for `Upload complete` /
  `Fully synced`, or run an independent verifier that reports `verified: true`. A deletion count is evidence
  about files, never about the cap.
- **Do not escalate to "the account cap is the blocker" on a failed upload alone.** The message reads
  `Vault limit exceeded` — a **per-vault** cap — and the per-vault accounting is not measurable from the
  client (no `ob usage`). Chasing the account-level number costs a round-trip with the user and produces no
  action; **the writer is the answer that can be acted on.**

### A duplicate subtree is a TIME CAPSULE, not a copy — and sync can bring it back

**A "duplicate" folder inside the vault is usually a snapshot from before your most recent moves, and it is
frequently the only surviving copy of what those moves took out.** Diff it against the CURRENT tree for orphans
before deleting a single file.

**It can also return after you delete it.** Sync is bidirectional: a local delete is a *proposal*, and a remote
that still holds the tree re-materialises it. Measured: a duplicate subtree was removed as "2,536 empty
directories", and came back as **7,166 files / 137 MB** once sync resumed — because the server had always held
real content beneath those directories.

**The orphan diff, in this order:**

1. **Count files, don't trust the label.** "Empty skeleton" was true of the directories and false of the data.
2. **For every file, resolve an alternative home:** the same relative path in the canonical tree, or the external
   store that absorbed it. Anything with no home is an **orphan** and is what you would lose.
3. **Restore orphans to their proper class before deleting the tree** — notes to the canonical vault path, media
   to the out-of-vault store, per the class table above. Verify each copy by size *and* hash.
4. **Only then remove the tree**, and re-run the orphan check expecting `0`.

Measured on that same subtree: of 5,967 files, **5,852 had twins and 115 were orphans** — 105 of them media that
had already been moved out to the store, and 10 real notes including a seat's own memory files. **A blind
delete would have destroyed a colleague's memory notes while reporting a tidy-up of duplicates.**

- **Deleting the local tree is not deleting the remote one.** Confirm the deletions propagated (the sync log
  prints them file by file) or the tree returns on the next pass and the work reads as never having happened.
- **The size you reclaim is on the REMOTE, not the disk you measured.** Re-check the sync size after propagation;
  a local `du` drop proves nothing about the quota.

## Dual transport — the vault pushed to a private repo is the durable answer

**When the sync vendor is the single point of failure, the brain needs a second, independent copy that no
subscription can switch off.** The shape that works: **Obsidian Sync as the interactive transport, a private
text-only git mirror as the durable backup.**

**It is a PUSH-ONLY mirror — the red line below still holds.** Obsidian and git must not both write the tree.
The mirror commits and pushes what is already on disk; nothing ever pulls into the vault.

**It costs nothing to keep current because the push is cheap and the tree changes slowly** — commit on a timer,
refuse to commit when nothing changed, and stay silent when there is nothing to say.

**Compliance and the pre-push gate are not optional here** — media in a timer-driven mirror is the exact shape
that suspends accounts. The rules, the staged-file gate, the secret scan, and the API verification live in
`github-account-compliance` (§9 MIRROR REPOS); a working end-to-end recipe is in
`references/git-mirror-transport.md`.

**Do not describe a mirror as "sync" and do not tell anyone the vault is "backed up" until the remote tree has
been read back.** Push reported, tree verified, two different claims.

## Red lines

- **Never `git pull` the vault.** Obsidian Sync and git are two writers on one tree — the vault transport protocol
  exists because that produced 842 phantom deletions. Push with git, sync with Obsidian.
- **Never commit a dependency tree to either place.** It is the single largest cause of sync pain and it is always
  reproducible.
- **Never let a rule delete a sole copy.** A file that exists in one place is not waste, whatever class it is in.
