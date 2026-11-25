---
name: obsidian-sync-fix
description: "Use when 'ob sync' says no config found."
version: 1.0.0
author: Gentech (HQ)
tags: [obsidian, sync, handoff, config, xdg]
---

# Obsidian Sync Fix — $HOME/XDG config path

> **⚠️ CORRECTED 2026-10-29 (HQ).** This skill taught **`/root/...` paths, which no longer exist** — they died
> with the 2026-10-12 wipe, and `Pixel` (its original author) is a **retired seat**. An agent following the old
> text ran `ob` against a path it could not see and concluded *"the brain is empty"* while standing in a **915 MB**
> vault. **Every path below is now the real one, measured on the box.**
> Full audit: `00-System/brain-transport-audit-2026-10-29.md`

## When to Use
- `ob sync` / `ob sync-status` says **"No sync configuration found"** even though config exists on disk.
- Handoffs written to the vault aren't reaching other agents (they read via Obsidian sync, not git).
- `ob sync-list-local` shows "No vaults configured" but `/opt/data/home/.config/obsidian-headless/sync/` has a vault folder.

## Root Cause
The `ob` CLI resolves its config dir from `$HOME` (or `XDG_CONFIG_HOME`). On this host, `$HOME` is the **profile home** (`/opt/data/profiles/<seat>/home`), NOT the host root. So `ob` looks in the wrong place and can't see the real config at `/opt/data/home/.config/obsidian-headless/`.

## The Fix — always set XDG_CONFIG_HOME
```bash
XDG_CONFIG_HOME=/opt/data/home/.config ob sync --path /opt/data/.obsidian-vault
```

## ⚠️ First question: is ANYTHING running the sync at all?

**`ob sync` working when you type it is not the same as the vault being synced.** Check for a scheduled
job before debugging the sync itself:

```bash
# does any cron actually invoke it?
python3 -c "import json;d=json.load(open('/opt/data/profiles/<seat>/cron/jobs.json'));\
print([j.get('name') for j in (d if isinstance(d,list) else d.get('jobs',[])) if 'sync' in str(j).lower()])"
# empty list = nothing syncs this vault, on a vault four seats share
```

**A script that works and is never called is the same outage as a script that fails, except nobody is
alerted.** If nothing schedules it, the fix is the schedule, not the config.

## ⚠️ Judge the sync on OUTPUT, never on exit code

**`ob sync` exits 0 whether or not it actually synced.** Exit 0 means the command ran.

```bash
out="$(ob sync --path /opt/data/.obsidian-vault 2>&1)"; rc=$?
# success requires BOTH: rc == 0 AND the literal string "Fully synced"
case "$out" in *"Fully synced"*) ;; *) echo "UNKNOWN — not synced: $out"; exit 2;; esac
```

Treat anything that is not `Fully synced` as **UNKNOWN, not success**. A cron that trusts the exit code
reports health forever while the vault drifts.

**Related trap:** a sync that prints `Fully synced` and uploads NOTHING is also indistinguishable from a
remote that is empty or misconfigured. Track whether anything moved across runs — a long streak of
"success" with zero uploads is a signal, not calm.

## ⚠️ Dot-prefixed files NEVER sync

Measured: a file at `00-HQ/.sync-probe.md` produced `Fully synced` with **no upload line at all**. The
identical content at `00-HQ/sync-probe-visible.md` uploaded immediately (`Uploading file … Upload
complete`).

**Rule: nothing that must survive may start with a dot.** A hidden file in the vault is silently absent
from every other seat, and the sync will never complain about it.

## Verify config is visible
```bash
XDG_CONFIG_HOME=/opt/data/home/.config ob sync-list-local
# Should show the Gentech vault, Path: /opt/data/.obsidian-vault
# The id as of 2026-10-01 is: e2c92dacc2d71cc70e7e8d315741b4cb
# If the id DIFFERS, the vault was RELINKED — that is not a failure. The Path and the
# vault name are the check; the id is the value. A hard-coded id here is what made this
# step impossible to pass once the remote was recreated (the superseded id and host are
# recorded, labelled, in the obsidian-sync runbook's WITHDRAWN banner — deliberately not
# repeated here, so that a literal audit of this file does not have to special-case it),
# and a check that cannot pass is worse than no check, because it teaches the reader to skip it.
```

## Verify a handoff actually reached Obsidian cloud
Run the sync, then grep the output for your file:
```bash
XDG_CONFIG_HOME=/opt/data/home/.config ob sync --path /opt/data/.obsidian-vault 2>&1 | grep -iE "Upload complete <your-file>|Fully synced"
```
`Upload complete <file>` = delivered to Obsidian cloud (the channel other agents read).

## "Sync failed: Error: Vault limit exceeded" — the quota, not the config

Different failure, same symptom (handoffs stop arriving): `ob` connects fine, then dies on upload.

```
[..] New file <path>
[..] Uploading file <path>
[..] Sync error: {}
Sync failed: Error: Vault limit exceeded.
```

**Diagnose — does not require guessing:**
```bash
# last time it worked (the quota tripped after this)
grep "Fully synced" "$XDG_CONFIG_HOME/obsidian-headless/sync/<vaultId>/sync.log" | tail -3
# why it failed — ⚠️ NOT from sync.log. Measured: the log records `Sync error: {}` and NOTHING else.
# `grep -c 'Vault limit exceeded' sync.log` returns 0 while every run is failing with exactly that.
# The message reaches STDOUT only — capture the command's own output, not the log:
ob sync --path /opt/data/.obsidian-vault 2>&1 | grep -iE 'limit exceeded|Sync failed'
# what is actually consuming quota: files UNDER the per-file ceiling
find . -path ./.git -prune -o -type f -size -5000k -print0 | xargs -0 stat -c%s | awk '{s+=$1} END {printf "%.0f MB\n", s/1048576}'
```

**Key facts that decide the fix:**
- Files **over** 5 MB are *skipped by design* — they never count against quota. So a vault that looks
  huge may have a small sync bill; measure with `-size -5000k`, not `du -sh`.
- Quota is consumed by **file count and version churn**, not just bytes. A vendored `node_modules`
  (tens of thousands of small files) is the classic silent eater — it should never sit in a synced vault.
- **`Sync error: {}` is an empty object — and the reason NEVER reaches the log.** The `Sync failed: Error: …`
  line exists on **stdout** only. Measured: `grep -c 'Vault limit exceeded' sync.log` → **0** on a vault that
  had been refused on every run for a day. **So this file cannot be used to diagnose the cause**; it only
  proves *that* an attempt failed. Run the command and read its output.
- **When a tool's log elides its own reason, detect failure by the SHAPE of the attempt, never by searching
  for the message.** In this log the shape is unambiguous: split on `Starting sync:`, take the last block, and
  require `Uploading file <p>` followed by `Sync error:` with no completion after it. **A probe grepping for
  the reason gets "no failure" forever** — the failure mode that makes a monitor report clean while the thing
  it guards is down. Bound it by recency (only count a failure inside the last few hours) so an old failure
  is not reported as a current one, and prove all three cases before trusting it: healthy → no block,
  upload-and-error → block, old failure outside the window → no block.

**It is a fleet/account decision, not a seat-level edit.** Deleting peer media or vendored trees to buy
quota headroom is a call Jordan owns; report the measurements and the cheapest options, delete nothing.

**⚠️ A local prune alone does NOT clear `Vault limit exceeded` — because a WRITER refills what you delete.**
Measured: 47.6 MB of logs moved out (209 MB → 162 MB on disk) and the next run still answered
`Vault limit exceeded`. **The cap is accounted on the REMOTE vault**, so shrinking the local tree changes
nothing until the remote reconciles — and it will not reconcile a quota it is already over.

**But "pruning never helps" is the wrong conclusion, and one session was spent on it.** The prune failed
because a live service was **still writing its log file inside the vault**, so every sync started above the
cap again. **Deleting files cannot outrun a writer.** The sequence that actually clears it, in this order:

1. **Find the writer** — `grep` the service source for the path it opens (`X402_TRAFFIC_DIR`, a log dir
   constant). A deleted file inside a running service is recreated on the next write, so delete-only fixes
   have an unbounded number of rounds.
2. **Repoint the writer at a MOUNTED path**, then recreate/restart it. An env var naming `/opt/data/<dir>`
   inside a container creates that directory in the **writable layer** — the data vanishes at the next
   recreate, i.e. the bug relocated somewhere harder to see. Mount it (`-v host:/logs`) and let the variable
   name the mount (`=/logs`).
3. **Now prune**, and let the deletions propagate.
4. **Verify UPLOADS, not deletions** — `Upload complete` / `Fully synced`, or an independent verifier
   returning `verified: true`. A deletion count is evidence about files, never about the cap.

Measured end to end on the second attempt: writer repointed → deletions drained → **`Fully synced`, zero
limit errors, verifier `verified: true`**. So the honest report is *"cap cleared"* only when uploads actually
resume; until then it is *"headroom bought; cap still applies."*

- **Still worth doing once**, because operational data (traffic logs, payment ledgers, multi-MB dumps) has no
  business in a synced notes vault: it inflates every seat's local tree and every backup. Move it out, repoint
  the consumers, leave a pointer **outside** the moved directory.
- **Do not report that as "sync fixed."** Report it as "vault bloat removed; cap unchanged; the cap is the
  account". The two are separate findings with separate owners, and conflating them is how the real blocker
  gets marked resolved.
- **Instrument defects found while diagnosing this are still real fixes** — a sync verifier that judged success
  on the exit code alone, or a consumer reading a log path that no longer exists, is broken regardless of the
  quota.

**Workaround while the quota is full:** git push still works. On the VPS all seats read the same
on-disk tree, so a peer on the same host still sees the file — but a **desktop seat (Forge) is cut off**,
since Obsidian is its only channel. Say which machines are affected rather than calling it "delivered".

**⚠️ The client-side levers are exclusions ONLY — and they do not rescue a remote that is already full.**
`ob sync-config` exposes `--excluded-folders "a,b,c"` and `--file-types ""`. Use exclusions to stop a
**future** problem — vendored trees, operational logs, multi-MB deliverables have no business in a synced
notes vault — but measured on an over-quota remote, excluding four heavy folders changed nothing: the error
is about what the remote already holds, not about what this run proposes to add. Do not present exclusions
as the fix for a blocked account.

**`--file-types` is NOT a lever on this client — do not reach for it to shrink a cap.** Measured: the flag
neither cleared nor changed anything (`sync-status` still printed the same classes), and the per-vault
`config.json` has **no `allowTypes` key at all** — only `ignoreFolders`, `conflictStrategy`, `deviceName`,
encryption fields. Attachment classes are an **account-side** setting, so "turn off image/audio/pdf/video to
save space" is not available to an agent here. Exclusions are the whole self-serve surface.

**Diagnostic discriminator — an over-quota remote and a broken client fail at different moments:**
```
Uploading file Treasury/…/scoreboard.md        <- it got as far as a transfer
Sync error: Error: Vault limit exceeded.       <- then the account refused it
```
A cap is hit **mid-transfer**, after `Uploading` appears. A config/path fault fails **before** any transfer
at all ("No sync configuration found"). Which line you see tells you which owner the problem has.

**`ob sync-status` / `sync-config` report configuration only — but the STATE DB exposes what the remote holds.**

The CLI has no usage command; do not hunt for one. What it does keep is a per-vault SQLite database that records
**the server's own file table**, and that is the measurement:

```bash
DB="$XDG_CONFIG_HOME/obsidian-headless/sync/<vaultId>/state.db"
python3 - "$DB" <<'PY'
import sqlite3, json, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True, timeout=10)
live_b = live_n = del_b = del_n = 0
for path, data in c.execute("select path,data from server_files"):
    d = json.loads(data)                      # {"size":…, "deleted":…, "hash":…, "mtime":…}
    s = d.get("size") or 0
    if d.get("deleted"): del_b += s; del_n += 1
    else:                live_b += s; live_n += 1
print(f"LIVE {live_n} files {live_b/1048576:.1f} MB · DELETED-RETAINED {del_n} files {del_b/1048576:.1f} MB")
PY
```

- **`meta` holds the account's own operation counter — and it is the REVISION accumulator, not a byte count.**
  `select value from meta where key='version'` returned **95,340** on a vault whose live payload was ~114 MB.
  That figure is total sync operations recorded server-side, and **it does not fall when files are deleted** —
  so on a capped account "free some bytes" targets the wrong variable. Print it next to the byte total; when
  bytes are a tenth of the stated plan and operations are in the tens of thousands, the cap is counting
  **history**, and only the human can act on that (prune version history in the app, or find a second vault).
  Do not propose a local tidy-up against a limit the local tree is not hitting.
- **`ignoreFolders` is not retroactive: it stops NEW syncs, it does not evict what already synced.**
  Measured: the per-vault `config.json` listed four `ignoreFolders`, and those four prefixes still held
  **2,293 files / 26.4 MB on the remote**. So an exclusion added today buys nothing today — it prevents the
  folder growing, not the space being returned. Say that before someone adds exclusions and re-measures.
- **Open read-only (`?mode=ro`).** The sync daemon holds the database; a read-write handle fails or blocks.
- **`server_files` is the remote's view** — one row per path, `data` a JSON blob. Group it by top-level folder
  and by extension to find what the cap is actually counting. Measured on one vault: **79.4 MB of a 130.6 MB
  remote was media** (photos, avatars, deliverable PNGs) while the notes were the small half. That number is
  the whole decision — a notes vault is not full, a vault carrying images is.
- **`deleted = true` rows are the accumulation a local walk can never show you.** Zero of them is also a
  finding: nothing is being retained, so the cap sits on present bytes and the only lever is removing present
  bytes.
- **A "duplicate" path set is not automatically wasted bytes.** A stale prefix held **2,535 mirrored paths**
  that looked like pure reclaimable headroom; every one was a **0.0 MB folder record**. Sum the sizes before
  proposing a delete — a path count is not a byte count, and a headline built on one is a false promise.
- **When the user remembers "two vaults", check the vault LIST before hunting a folder.** `ob sync-list-remote` is
  authoritative and cheap: it prints every vault on the account with its id and region. One entry there means there
  is no second vault, however strongly the symptom suggests one — and a second entry is a real duplicate worth
  reporting as such. Do not start deleting things on the strength of a remembered duplicate.
- **What a "duplicate" usually is: an empty skeleton inside the ONE vault.** Measured: a `Gentech/` tree of
  **2,536 directories and zero files**, apparent size 0, left behind by an earlier re-link. It is safe to remove
  (`find Gentech -depth -type d -empty -delete` — directories only, so nothing can be lost), and it is worth
  removing: the deletion queue finally ran (`Deleting remote folder Gentech/...` for ~4 minutes, 11,082 → 8,546
  server records). **But it freed 0 bytes and did not clear the cap** — say so in the same breath, because "I deleted
  the duplicate" reads as "the problem is fixed" and it is not.
- **⚠️ The same-named tree can also be a FULL duplicate — and a bidirectional sync downloads it back.**
  Measured on a later pass: the subtree that had been an empty skeleton returned as **7,166 paths / 137 MB** on
  the remote, because deleting only the *empty directories* left the remote's real files authoritative and the
  next sync restored them locally. **An empty local copy is not evidence the remote is empty.** Treat a
  same-named subtree as unknown until measured — and rescue before removing:

  ```
  1 · walk the duplicate; for each file, does the SAME relative path exist in the vault root?
  2 · NO twin → it is UNIQUE. Copy it to its canonical home (media → the off-vault store, notes → root)
  3 · re-walk and require UNIQUE == 0 — the orphan count is the gate, not a spot check
  4 · only then remove the tree, and let sync drain the deletions
  ```

  A duplicate of this kind is not junk: it is a **frozen snapshot of an earlier tree**, so it holds files the
  root no longer has — media already moved off-vault, archived handoffs, another seat's memory notes.
  **Removing it without the diff destroys exactly the files that exist nowhere else.** And unlike the empty
  skeleton, this one *is* real reclaimable weight, so the two cases must be measured apart before either is
  called "the duplicate".
- **Grep code for the path before removing it** (`obsidian-vault/Gentech/` across `scripts/` and `profiles/`): an
  empty directory has no files, but a consumer can still name it as a path.
- **Report the measurement and what it implies** — the number does not decide whether a user's photos should
  leave their other devices. **The policy question is now answered** for this fleet: media belongs in a
  **cloud drive project folder, not in the vault** ("pictures and video back up should be for Google drive in a
  project folder"). A notes vault is the brain; it is not a photo library, and images are what a storage cap
  actually counts. See `### Moving media OUT — the ordering is the safety property` below.
- **⚠️ The standing rule has TWO prohibitions, not one: media enters NEITHER sync surface.** Not the vault
  (quota) and **not the git mirror either** — the mirror is a rate-limited surface, and pushing media into it
  trades a storage cap for an API cap. **Until a real external offload exists, the VPS is the home**: one
  directory outside the vault, with a `_MANIFEST.json` of `sha256` + size for every file. Verified copies on
  that host are **not a backup** — say so in the same sentence, every time.
- **File the offload as a PENDING item, not an open task.** It is waiting on a human action (an OAuth in a
  browser, a credential that does not exist yet), so it belongs in the pending list **with its gate and its
  release condition written out** — what must become true for it to move. An open task list that carries a
  blocked item re-reports it as overdue forever; the gate is the reason it is not moving, and stating it is
  what makes the silence honest.

### Moving media OUT — the ordering is the safety property

**Obsidian Sync is bidirectional, so a file that leaves the vault is DELETED from the server and from every one
of the human's devices.** A routine that relocates first and uploads second destroys the only other copies
while calling itself a backup. The order is not a preference:

```
1 · upload to the external store        (copy only — deletes nothing anywhere)
2 · VERIFY file-by-file on both sides   (size + count; `rclone check <local> <dest>`)
3 · only then may anything be pruned from the vault — and NOT automatically
```

- **Never prune in the same step as the upload.** Deletion propagates to devices the agent cannot see, so it is
  a human decision even when the copy verified cleanly. Print the exact paths and stop.
- **The verify step is the whole gate.** A copy that has not been checked is a second untrustworthy copy; a
  failed verify must abort the prune loudly, not proceed with a warning.
- **Audit references before moving anything — and count LOADERS, not mentions.** Measured on one vault: of 64
  media files, **44 were referenced by pages and notes** and **20 were unreferenced**, which made the unreferenced
  set look like the only movable slice. **A basename grep is the wrong instrument for this**: run over a notes
  corpus it matches the inventory note that lists every filename, and every session checkpoint that ever quoted a
  path. Re-measured on a later batch, the same basename test reported **47 of 47 referenced**; tightening it to
  "does a file that actually LOADS assets point at this path" returned **8**, and three of those eight were
  checkpoints — recordings, not consumers. **Treating a mention as a reference makes every asset permanently
  undeletable**, so the conservative-looking rule is the one that stalls the job forever.

  | match type | example | movable? |
  |---|---|---|
  | **loader** | `icons/icon-192.png` inside `manifest.json` or a dashboard `.html` | **no — keep** |
  | **inventory** | the media-queue note listing every filename | yes |
  | **transcript** | a checkpoint or completions log quoting a path | yes |

  Require the **path tail** (last two segments) rather than the bare basename, search only file types that
  consume it (`.html`, `.json`, `.py`), and exclude inventory/checkpoint/completions files **by name**. Keep an
  explicit `KEEP` set of what a live page loads and assert it survived the pass. **PWA icons are the classic
  near-miss** — an icon a `manifest.json` names is load-bearing even when it looks like incidental artwork.
- **A staging directory on the same host is not a backup.** Until the external copy verifies, "moved out of the
  vault" means "deleted from every device, still on one disk".
- **Name the transport gate before promising a move.** If the external store has no credential (a `rclone`
  remote with an empty `token =`, no OAuth ever completed), the honest report is *the pipeline is built and
  refuses to move anything* plus the one-time authorisation step — never a half-move.
- **rclone's shared Google client_id is being retired during 2026** (its own stderr says so); a durable setup
  needs the operator's own client_id. Say that at authorisation time rather than after it breaks.
- **Staging a batch can shift the failure without fixing it — report which happened.** Measured: after moving
  the unreferenced media out of the vault, the next run stopped aborting on the first upload and started
  **deleting** remote files instead; the server payload fell (130.6 → 122.5 MB). Then the cap returned on the
  next upload. So a staging sweep **buys headroom and unblocks the deletion queue** — it does not clear the
  account's limit. Say "sync advanced from refusing uploads to draining deletions; cap still applies", never
  "sync fixed".
- **A staged file with no record is a misplaced file.** The staging directory becomes a second undocumented
  dumping ground within a week unless every moved file is written to a list with explicit states —
  *in the vault / staged / verified in the external store* — so a reader can tell "not lost" from "forgotten".
  Rewrite that section each run rather than appending (four runs a day must not quadruple it), and have the
  nightly check print **queue depth and age**. The state that matters is *waiting*, and a queue nobody counts
  reads as handled.
- **Default the sweep to unreferenced files only, and say why the rest stayed.** Referenced media moves as a
  pair — the file to the external store, and the page's link updated — which is a different, larger change.
  A tool that silently takes both fixes the quota by breaking the site.

### Back to the cap — a saturated remote still deletes, and the vendor may also just be down

**Deletes and uploads fail differently — do not promise pruning as the escape.** Measured: `Deleting remote
file …` lines appear in `sync.log` from *inside* the capped window while the same runs abort on `Uploading
file …`. A saturated remote still accepts deletions, but the client reaches the upload first and stops, so
freeing space self-serve is unreliable. Say that instead of "delete some files and retry".

**⚠️ THE THIRD CAUSE: the vendor is down. Nothing client-side fixes it.**
`Vault limit exceeded` and a config-path fault are both *our* side. A third failure produces the same symptom
(handoffs stop arriving) and is entirely theirs: **the Obsidian Sync account reports its own servers overloaded,
or a login/API call fails without a quota message.** No config change, no exclusion, no prune, and no retry loop
addresses it — and repeatedly hammering a struggling sync backend is how a soft outage becomes an account flag.

**Symptom taxonomy — which line tells you which owner:**

| what you see | owner | action |
|---|---|---|
| `No sync configuration found` | config path (`$HOME` / `XDG_CONFIG_HOME`) | fix the path |
| `Uploading file …` then `Sync error: Vault limit exceeded` | the **account** (remote is over cap) | quota decision, not code |
| login/API says **overloaded / unavailable**, no quota wording | the **vendor** | stop retrying; switch transport |

**Prove the TOKEN before blaming it — account reads and sync auth are different failures.** A quota error and
an expired login both stop handoffs, and they are cheap to separate:

```bash
ob login            # "Logged in as <name> (email)"  → token VALID
ob sync-list-remote # lists the vault             → authenticated read WORKS
```

If both succeed while `ob sync` fails, **the credential is fine and re-authenticating will not fix it.** Say so
plainly when the user offers "maybe we just need to log in again" — it is a reasonable guess and it deserves a
measurement, not a silent agreement or a blind `ob logout && ob login` that risks the working token for nothing.

**⚠️ An ACTIVE, PAID subscription does not mean the cap is a billing lapse.** Measured: the user checked the
vendor's site and the plan was valid for weeks; `Vault limit exceeded` continued on every attempt. So **do not
tell a user their plan probably lapsed** — that is a guess dressed as a diagnosis, and it sends them to a page
that tells them what they already know. Report instead: token valid (measured), service reachable (measured),
cap enforced by the server at a specific byte count (measured), and that the two remaining explanations are
**another device's vault consuming the same allowance** or **accumulation held in their account that no client
read can see**. Then name the one test that splits those, rather than guessing between them.

**Grep the CLIENT for the error string — its absence is the proof it came from the server.** One command
localises the owner without any account access:

```bash
f=$(readlink -f "$(command -v ob)"); grep -c 'Vault limit exceeded' "$f"   # 0 → not our code
```

Zero hits means the message is a verbatim server reply: the request was **sent, authenticated and answered**.
That single fact rules out the config path, an unreachable network and a dead token all at once, and it is the
cheapest answer to "maybe we just need to log in again". (Contrast: `No sync configuration found` *is* the
client speaking, so that one is ours.)

**Do the plan arithmetic before proposing any surgery.** If the user states their plan ("we only have 1 GB for
notes"), compute what the vault *should* cost against it and print the percentage. Measured on one vault:
notes + non-media totalled **~96 MB of a 1 GB plan — 9%** — while the server refused uploads at 130.6 MB.
A payload sitting at a tenth of the stated allowance is **not limited by that allowance**, so every local
tidy-up is aimed at the wrong variable. Say that out loud instead of reorganising the vault to satisfy a limit
it is not hitting, and keep the plan check and the cap investigation as two separate questions.

**When it is the vendor, the answer is a second transport, not a repair.** Do not spend the session debugging a
service you cannot see. Establish the durable copy — a push-only, private, text-only git mirror of the vault —
and say clearly what it does and does not restore:

- **It protects the data** and gives version history that no subscription can switch off.
- **It does not give the human's laptop interactive editing back.** That needs a pull path (a git
  plugin/checkout, or a read-only `rsync` of the live tree) — name which, and say the mirror alone is not it.
- **The fleet is not down.** All seats on one host read the same on-disk tree, so an agent-to-agent outage is
  only real for **seats on other machines** (a desktop seat whose only channel is Obsidian).

**The response to a sync error has three steps, in this order — never reordered, never collapsed:**

1. **TRY.** One failure is not a verdict; measure it. Two or three consecutive attempts distinguish a blip
   from a condition, and they are cheap.
2. **INVESTIGATE, THEN TELL THE USER — naming which of the three causes it is** (path / account / vendor, per
   the taxonomy table). "Sync failed" alone is not a report; it is the same empty sentence a monitor sends
   forever while nothing is owned. Never swap transports silently: the user must not believe the primary
   works because the backup did.
3. **GO TO THE BACKUP IMMEDIATELY** — on the same run that detected the failure, not at the next scheduled
   mirror tick and not only if an agent remembers.

**Then state the one rule that makes the backup usable, because it contradicts the note that governs it:**

> **A backup that is never pulled is an archive. A pull into a tree the primary is writing is corruption.**

So the backup is a **restore source in exactly one situation: the primary is dead and nothing else is writing
the tree.**

| primary state | what the mirror is | how to use it |
|---|---|---|
| **working** | backup / archive | read it in the browser. **Do not pull it into a synced tree.** |
| **dead** | restore source — the second brain | clone it fresh and let it *be* the vault |

A working primary makes a pull destructive; a dead one makes it safe. **State which world you are in before
touching a clone** — the dual-writer corruption this guards against is documented and expensive.

Recipe: load `vault-code-boundary` and read its `git-mirror-transport` reference. Compliance gate:
`github-account-compliance` → §9 MIRROR REPOS.

**`ob` also needs `HOME`, not just `XDG_CONFIG_HOME`.** `export HOME=/opt/data/home` is what makes
`ob sync-list-local` and `ob login` resolve the real config; a profile home (`/opt/data/profiles/<seat>/home`)
leaves `ob` reporting no vault at all. Setting only `XDG_CONFIG_HOME` inside a script can hide this, because the
script works while an interactive `ob` invocation does not.

**And `ob sync` needs `--path`: without it, the SAME "No sync configuration found" message appears and it means
nothing about the config.** The CLI resolves the vault from the working directory when no `--path` is given, so
running `ob sync` from `/opt/data` reports no configuration while the vault sits one directory away and is
perfectly configured. **This is the cheapest of the causes and the easiest to misread as the expensive one.**

```bash
ob sync                                  # from an unrelated cwd → "No sync configuration found" (false alarm)
ob sync --path /opt/data/.obsidian-vault # the invocation the working cron actually uses
```

- **Copy the working cron's exact argv** (`grep -n 'subprocess\|[OB' <verifier>`) instead of typing the command
  from memory — a hand-written `ob sync` differing by one flag reports a failure that is not there.
- **Before concluding "sync is unconfigured", confirm you passed `--path` AND set `HOME`.** Two invocation
  mistakes produce the identical string as a genuinely missing config, and only one of the three is a problem.
- **A monitor that runs `ob sync` without `--path` reports a sync outage that does not exist** — and because the
  client exits 0 and logs `Sync error: {}`, every downstream consumer reads it as a real transport failure. When a
  gate says handoffs are BLOCKED on sync, reproduce the gate's OWN argv before investigating the account: the
  cheapest explanation is a missing `--path`, not a full remote.

## ⚠️ Two vault directories under `sync/` — the RETIRED one's log looks authoritative

**A re-bind leaves the old vault's directory in place, and its `sync.log` stops dead at the re-bind moment.** A
consumer that hardcodes the old id (a verifier, an SLA gate, a heartbeat check) then reads a frozen file and
reports a week-long outage while the live vault is syncing every hour.
**Measured:** two directories under `obsidian-headless/sync/` (`config.json` created 15 Nov and 17 Nov), both
naming `vaultPath: /opt/data/.obsidian-vault`; the older log's last line was `Disconnected from server` from the
17th, the newer log showed `Fully synced` minutes ago and `Upload complete` for a file written seconds before.

**Rule: resolve the ACTIVE vault, never a stored id.**

```bash
SYNC="$XDG_CONFIG_HOME/obsidian-headless/sync"
ACTIVE=$(ls -t "$SYNC"/*/config.json | head -1 | xargs dirname)     # newest config.json wins
python3 -c "import json,sys;d=json.load(open('$ACTIVE/config.json'));print(d['vaultId'],d['vaultPath'])"
```

- **A log older than 2 hours is `UNKNOWN`, not `healthy` and not `blocked`.** Age the file (`date -r`), then say
  which it is. A monitor that reads a stale log manufactures confidence — the opposite of its job.
- **Both directories can name the SAME `vaultPath`.** The path is not the discriminator; the mtimes are.
- **Prove liveness with a visible probe, not a status string:** write `00-HQ/sync-probe-visible.md` (never a
  dot-file), sync, then `grep 'sync-probe-visible' "$ACTIVE/sync.log"` for `Upload complete`. That is the only
  evidence the carrier end-to-end works, and it takes ten seconds.

## ⚠️ Excluded folders are a DELIVERY hole, not just a quota lever

**A handoff that tells a remote seat to read a file inside an excluded folder is not a delivery** — the file exists
here, the sync says `Fully synced`, and the reader's copy never receives it.

```bash
ob sync-status --path /opt/data/.obsidian-vault | grep -i excluded
```

**Read that list before writing any instruction of the form "the text is in `<path>`".** Measured on this fleet the
exclusions include `10-Labs/skills-distribution` and `10-Labs/hermes-memory` — i.e. **the skills CORE and the memory
mirror are deliberately outside the sync**, so a seat on another machine has never received them however healthy
the sync looks.

- **Inline the content** in the handoff itself when it lives in an excluded folder. A path you cannot see from the
  reader's side is not a delivery, and the failure is silent in both directions: the writer sees `Fully synced` and
  the reader sees nothing to open.
- **Same-host seats are unaffected** (they read the one filesystem); **a desktop seat on another machine is the one
  that loses it.** State which machines the note actually reaches rather than calling it delivered.
- **`--file-types` and `--excluded-folders` are also not retroactive** — see the quota section: exclusions stop NEW
  syncs, they do not evict or backfill.

## Renaming the vault path — count the hardcoded references BEFORE the `mv`

A vault directory is named in script constants, cron wrappers and config files, so a bare `mv` breaks every
consumer at once while looking like a cosmetic change.

```bash
# 1 · how big is the blast radius? (measured: 66 files in one fleet, incl. cron scripts)
grep -rl '/opt/data/.obsidian-vault' --include='*.py' --include='*.sh' /opt/data/scripts /opt/data/profiles | wc -l
# 2 · move the real directory, leave a symlink at the old name
mv /opt/data/.obsidian-vault /opt/data/.obsidian-vault
ln -sfn /opt/data/.obsidian-vault /opt/data/.obsidian-vault
```

**Symlink, not a bulk sed:** a rename is cosmetic, and the blast radius is everything. The symlink keeps all 66
absolute paths resolving with **zero code edits**; the real directory carries the correct name.

**Verify THROUGH THE OLD PATH** — that is what the scripts use, and a listing on the new name proves nothing
about it:

```bash
ls /opt/data/.obsidian-vault/00-HQ | wc -l                  # old path still resolves
python3 -c "import os;print(sum(len(f) for _,_,f in os.walk('/opt/data/.obsidian-vault')))"  # real walk
git -C /opt/data/.obsidian-vault log --oneline -1              # mirror lane intact
ob sync-status --path /opt/data/.obsidian-vault | head -4    # sync still finds the vault
```

- **`readlink -f` is the one-line proof** that the old path is a symlink and where it points.
- **Name the device too:** `ob sync-config --path <vault> --device-name "GenTech Brain (VPS)"` — that is the
  string the human sees in sync version history, and it is separately renameable.
- **The REMOTE vault name is NOT renameable from this client.** `ob sync-config` exposes conflict strategy,
  exclusions, file types and configs — no name flag — and `vaultName` appears only inside the stored
  `config.json`. Renaming the remote is an **Obsidian app / account-site** action. Say that explicitly rather
  than reporting the rename as complete while `sync-list-remote` still prints the old name.
- **Do not rename while the vault is mid-sync or a deletion queue is draining** — wait for the run to finish,
  or the next run reports `Another sync instance is already running` and you will read it as a failure.

## Re-pointing to a DIFFERENT remote vault — `Vault not found` with a healthy local tree

**Symptom: every read and write works, the note count is right, and nothing propagates.** The remote vault was
replaced (recreated, renamed at the account level, or moved to a new sync vault) and the local copy is still
bound to the OLD id.

```
Sync failed: Error: Failed to authenticate: Vault not found.
```

**Read the two ids before touching anything — this is a binding problem, not a credentials problem:**

```bash
ob sync-status          # "Vault: <name> (<id>)"  ← what this machine is BOUND to
ob sync-list-remote     # the ids the ACCOUNT actually has  ← authoritative
ob sync-list-local      # what is registered here
```

Different id in `sync-status` vs `sync-list-remote` = the local copy points at a vault that no longer exists.
**`ob login` will not fix it and neither will re-authentication** — the token is fine, the target is gone.

### Re-bind, and run it as the OWNING unix user

```bash
# from the HOST, into the container that owns the vault:
docker exec -u root  <container> rm -rf /opt/data/home/.config/obsidian-headless/sync/<NEW_VAULT_ID>
docker exec -it -u hermes <container> bash -lc 'cd <vault> && \
  HOME=/opt/data/home PATH=/opt/data/.npm-global/bin:$PATH \
  ob sync-setup --vault <NEW_VAULT_ID> --path <vault> --device-name "<device>"'
```

- **`ob` lives in the CONTAINER, not on the host.** On the host shell it is simply `command not found`; the
  binary is at the profile's npm global path inside the container. Say this before handing anyone a command.
- **`-u <owner>` is not optional.** Run as `root` and the setup writes
  `~/.config/obsidian-headless/sync/<id>/` as **root, mode 700**; the agent (a non-root uid) then fails with
  `EACCES: permission denied, open '…/config.json'` on every retry, and cannot even delete the directory to
  recover because it cannot list a 700 root-owned child. Root has to remove it first.
- **`wrangler`-style traps apply: `--vault` takes the ID, not the name.** Names are ambiguous after a rename.
- **Take a snapshot before binding bidirectional to a vault that may hold other content** — `ob sync-setup`
  itself warns that local notes will be MERGED with the remote and that the most recent version wins per note.
  A `tar` of the vault costs a minute; an unrecoverable merge does not.
- **Verify with a COUNT and a BINDING, not with the word `Fully synced`:** compare note count before and after
  (`find . -name '*.md' -not -path './.git/*' | wc -l`) and confirm `sync-status` prints the NEW id. A bind can
  be configured correctly and still have moved nothing yet.
- **`Another sync instance is already running for this vault` is not a failure.** An interrupted or
  timed-out `ob sync` holds the lock; check `ps aux | grep '[o]b sync'` and let it finish rather than killing it
  mid-upload. Killing a drain halfway leaves the remote and local disagreeing with no message about it.

## Pitfalls
- **`.git` inside the sync root is NOT quota weight — do not report it as such.** The dot-prefix rule above
  applies to directories too, so the vault's own history never leaves the machine. Measured: a 111 MB `.git`
  sat inside a vault whose remote refused uploads, and naming it as a contributor sends the human to prune
  something the server never received. When measuring what the remote holds, prune `.git` from the walk
  (`find . -path ./.git -prune`) — that is a measurement correction, not a size reduction.
- **git push vault is NOT the delivery channel for handoffs.** Other agents (Forge) read via Obsidian sync. A file committed+git-pushed but not Obsidian-synced is NOT delivered.
- The sync can be slow on first run (it reconciles the whole vault, including node_modules). Run with a generous timeout (180s+).
- `ob sync` is one-shot; use `--continuous` only if you want a daemon. For handoffs, run it after writing each handoff.
- The config lives at `/opt/data/home/.config/obsidian-headless/sync/<vaultId>/config.json` — as of 2026-10-01 vaultId `e2c92dacc2d71cc70e7e8d315741b4cb`, vault "Gentech", host `sync-72.obsidian.md`. **The id AND the host move together when the remote vault is recreated** — the previous pair is recorded, labelled as superseded, in the obsidian-sync runbook's WITHDRAWN banner, and is deliberately not repeated here; read both live with `ob sync-list-local` rather than trusting the pair written here.

## Verification
- [ ] `XDG_CONFIG_HOME=/opt/data/home/.config ob sync-list-local` shows the Gentech vault.
- [ ] After writing a handoff, `ob sync` output shows `Upload complete <file>`.
- [ ] Other agents can see the handoff in their Obsidian-synced vault.
