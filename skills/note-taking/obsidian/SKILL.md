---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
version: 1.0.0
author: Teknium (teknium1), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Obsidian, Notes, Markdown, Vault]
    related_skills: []
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `${HERMES_HOME:-~/.hermes}/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Sync the vault

If the vault is synced by Obsidian's headless client (`ob`), two rules decide whether a sync
verdict means anything.

### Judge the sync on its OUTPUT, never on its exit code

`ob sync` exits 0 whether it synced, found nothing to do, or could not reach the server. The only
evidence is the string it prints.

```bash
out=$(ob sync --path "$VAULT" 2>&1); rc=$?
case "$out" in
  *"Fully synced"*) echo synced ;;
  *) echo "UNKNOWN: rc=$rc"; printf '%s\n' "$out" | sed -n '1,10p' ;;
esac
```

Require `Fully synced` explicitly, and print the run's own output on anything else — a sync that
failed silently is worse than one that failed loudly. Record what moved (`Uploading` /
`Downloading` / `Deleting` lines) so the history can tell "nothing to do" from "configured at the
wrong remote".

**A sync that reports success while moving nothing for many consecutive runs is suspect**, not
calm: that is the shape of a config pointing at an empty vault. Track a consecutive-idle count and
speak when it grows.

### A tool can DECLINE to run and still exit 0 — read the refusal, not the code

`ob sync` refuses to start in two different ways, and **both exit 0**. Match the refusal text before the
`Fully synced` match, or the case falls through to a verdict you did not measure.

**① Wrong working directory — `No sync configuration found for <path>`.** A bare `ob sync` run from
anywhere other than the vault's own directory has no config to read, prints that line, and exits 0.
**Always pass `--path "$VAULT"` or `cd` into the vault first** — and if a sync has been "passing" while
nothing moved, check the cwd before you check the account. A caller that treats exit 0 as synced will
report a healthy transport for a vault it never contacted.

**② Another instance holds the vault — `Another sync instance is already running for this vault.`**
The exit code is identical to a successful sync, and **your write did not travel on your call** — it rides
on whatever the holding instance does, on its own schedule (typically a cron sync every few minutes).

- **Match the lock line explicitly** and treat it as `DEFERRED`, never `synced`. Check it before the
  `Fully synced` match, or the case falls through to a verdict you did not measure.
- **Do not fight the lock** — killing the holder to make your call win trades a working scheduler for
  a single urgent write.
- **Say which one you got.** "My write is on disk and verified; the sync reported another instance
  running, so I cannot claim `Fully synced` from here" is the honest sentence. Claiming a sync you
  did not observe is the same defect as quoting a number you did not measure.
- **If the write must land now**, verify it from the other side (read the file back after the next
  scheduled cycle, or compare content on a second host) rather than re-invoking in a loop.

### Paths the transport SKIPS — and why that makes a handoff undeliverable

**Three kinds of path never leave the host**, and the client reports `Fully synced` regardless:

1. **dot-prefixed** paths (measured below);
2. **folders listed in the client's own exclusion config** — `ob sync-config --excluded-folders` — which is a
   *policy* set, not a bug. Read it before assuming a folder travels:
   ```bash
   ob sync-status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['excludedFolders'])"
   ```
3. **file TYPES excluded** via `--file-types` (audio, video, pdf, images) — a `.md` travels while the `.wav`
   beside it silently does not.

**`--excluded-folders` takes FOLDERS, not files.** You cannot exclude one noisy note; you must move it into a
folder that is excluded, or stop rewriting it.

**The consequence that costs a delivery: never point another seat at a path the transport skips.** A handoff
that says *"copy the block from `<vault>/10-Labs/skills-distribution/…`"* is undeliverable when that folder is
in the exclusion list — the reader finds nothing and has no way to tell "excluded" from "you did not write it".
**Inline the content into the handoff note itself**, which always travels. Test before sending: is the path I am
citing inside an excluded folder or dot-prefixed? If yes, paste the bytes instead of naming the path.

**A policy exclusion is also why a canon never reaches a remote seat.** If the distribution folder is excluded,
then editing CORE delivers to the seats on this host and to nobody else — and the local sync will report
success the whole time.

### Dot-prefixed paths are NOT synced

Measured: a file at `<vault>/00-HQ/.sync-probe.md` produced `Fully synced` with **no upload**; the
identical content at `<vault>/00-HQ/sync-probe-visible.md` uploaded immediately. Hidden/dot-prefixed
paths are excluded.

**Consequence: never rely on a dotfile being present in the remote vault.** If another seat (or
another machine) must see it, it cannot start with a dot — and when testing whether sync works,
probe with a VISIBLE filename, or the test will confirm success while proving nothing.

**This bites hardest on redirect and marker notes.** A `.redirect.md` left in a folder after a move is
excluded from sync, so the file explaining the move to every other host is exactly the one that never
arrives — and on that machine the retired folder still looks live and empty, ready for a writer to file
into. Name signposts visibly (`_MOVED.md`, `README.md`) or the retirement only lands on one host.

### Sync is not a file operation — schedule it and verify it

A vault shared by several agents that is never synced is several brains drifting apart, with the
newest knowledge in whichever host wrote it last. A sync script that exists but is called by no
schedule is the same as no sync at all — check for a scheduled job, not for the script.

### A SECOND lane is a BACKUP, not a merge partner — and a pull is only safe when the primary is DEAD

**Two writers on one working tree corrupt it. That is why `git pull` into a synced vault is forbidden.** But a
backup that is never read is an archive, not a restore path — so "if sync breaks, use the backup" has a
condition, and stating it is the difference between a policy and a trap.

**The rule: pull from the backup lane only onto a tree the primary is not writing.** A live primary is what makes
a pull destructive; a dead one is what makes it safe.

| primary state | what the backup is | how to use it |
|---|---|---|
| **working** | archive / history | **do not pull it into any tree the sync client writes.** Read it where it lives. |
| **dead** (sync refused, host lost, no writer active) | **a restore source** | clone it fresh and let it *be* the vault |

- **Write the condition down beside the backup's own rules, not in a chat message.** An operator who reads "go to
the second brain" without the qualifier will pull it while sync is healthy — reproducing the exact corruption
the no-pull rule exists to prevent.
- **Keep the lanes distinguishable in the report.** "The backup is current" and "the primary works" are two
facts, and a green backup must never be reported as a fixed sync.
- **Fall back on the same run that detects the failure, and name the cause in three classes:** *transient* (retry,
stay on the primary), *our fault* (bad config, expired credential — fix it here, stay on the primary), *the
account* (a cap or a lapsed plan — the owner's decision; the backup carries the brain meanwhile). "Sync failed"
with no class is the same useless sentence as a monitor that only says "down".
- **A restored primary is worth one line.** Silence is right for a healthy sync; a recovered one closes a loop
the operator opened.
- **Never let a fallback lane silently become the default.** Primary/backup is a choice, not a convenience — and
the fleet is usually unaffected anyway, because seats sharing one filesystem need no sync between them at all
(only the off-box copies freeze).

## Media does not live in a notes vault — stage it, never delete it

**A notes vault is the brain; it is not a media library.** Pictures, audio and video inside a synced vault cost
quota on every plan, inflate every backup, and are charged against the same ceiling the notes need.

**Rule: upload → verify → only then prune. Never move first and upload second.**

Why the order is the whole safety property: **a bidirectional sync propagates DELETIONS to every device.** The
moment a file leaves the vault, the client deletes it from the remote and from every synced laptop and phone.
If the destination copy does not exist yet — or exists but is unverified — the move has destroyed the only
copies while calling itself a backup.

**Three states, and there is no fourth:**

| state | where the bytes are | meaning |
|---|---|---|
| **IN VAULT** | the vault (+ remote) | violation — media in the notes lane |
| **STAGED** | a directory OUTSIDE the vault, same host | safe: out of the notes lane, queued, still on disk |
| **IN ARCHIVE** | the external store, VERIFIED | done — staging may be pruned |

- **Give the queue its own list file** carrying those states, and rewrite its section each run rather than
  appending (an appended queue grows four times a day and stops being read).
- **Say per row when the destination does not exist yet** (`not yet — destination unconfigured`) instead of
  implying the file moved. A queue that reads as handled because it is written down is the failure it exists
  to prevent.
- **Check references before moving any media file.** Measured on one vault: of 70 media files, **47 were
  referenced** by pages and notes — avatars, emblems, deliverable stills. Moving those "fixes" the quota by
  breaking the page that embeds them. Grep each basename across `.md`/`.html`/`.json` first, and treat a
  referenced file as a pair: **the file moves AND the link is updated.** Auto-stage only the unreferenced ones;
  refuse the rest with that reason.
- **Never delete to make room.** The remedy is always *move out and queue*, never *delete*.

### A storage cap is charged on ACCUMULATION, not on the local present

When a sync refuses with a limit/quota error, local tidying does **not** clear it — and this matters because
pruning is the intuitive first move.

- **Uploads are refused BEFORE deletions get a turn.** The client attempts the first changed file, the server
  rejects it, and the run aborts — so the deletions your pruning queued never travel. Moving ~48 MB out of the
  vault changed the remote total by zero bytes.
- **Empty directories are not weight.** Removing a 2,536-directory empty skeleton of a former duplicate vault
  deleted thousands of records and freed **0 bytes**. Worth doing for clarity; not a quota fix.
- **The charge is a property of the account's history at that moment.** A local state database can show zero
  deleted-retained records and the account can still be over — the charge lives on the provider's side.
- **Measure what the REMOTE holds before proposing anything.** Where the client keeps a state database, sum the
  live file sizes per path; that is the number being charged. Then decide.
- **Do not reorganise a vault to satisfy a limit you are not hitting.** If notes are a small fraction of the
  stated plan and sync still refuses, the problem is the account — an expired plan, a second vault, or
  accumulation. Check the plan and the remote total *before* moving a single file, and say which of the three
  causes the evidence points at.
- **An auth failure and a quota failure look nothing alike, and the difference is testable.** If the client can
  still list remote vaults and read the account name, the credential is valid and reachability is proven — so a
  refusal to sync is a policy/cap answer, not a login problem. Re-authenticating cannot fix a cap; say so
  instead of swapping credentials hopefully.

### Renaming a directory that scripts hardcode: rename the target, symlink the old name

Renaming a vault directory is a trap when scripts hold its absolute path. Measured: **66 files** referenced one
vault path.

- **Count the consumers first:** `grep -rl '<abs-path>' --include='*.py' --include='*.sh' <tree> | wc -l`.
  More than a couple means do not rename-and-edit.
- **Move the real directory to the new name, then leave a SYMLINK at the old path.** Every hardcoded reference
  keeps resolving with zero code edits, and the change is instantly reversible.
- **Verify through the OLD path, not the new one** — that is what the consumers use. Walk the tree and count
  files, then run one real consumer (recall, search, or a listing script) and confirm it reads.
- **The symlinked path is now load-bearing.** Record it where the next reader will look, or a later "clean up the
  stale symlink" deletes the fleet's vault path.
- **A remote-side display name is usually not renameable from a headless client** — the CLI exposes conflict
  strategy, exclusions, file types and device name, not a rename. State which half you changed and which is the
  human's to do.

## Writing notes a human will actually read

**The standard: could this be read once, on a phone, without re-reading a sentence?** A note that fails
that is not finished, however accurate it is. An unread note is worth nothing.

This governs every note written into a shared brain: handoffs, research, completions entries, HQ notes.
The full page lives in the vault at `00-System/WRITING-RULES.md`; these are the rules that apply to every
note, so they belong here too.

- **The first line is a sentence, not a summary object.** "Forge was right — our checker was counting
  real answers as silence." beats "FORGE. ACK. CHECKER BLIND. FIXED." Evidence comes after the finding.
- **One claim per line.** Four or five bullets beat one paragraph with nine clauses. If a line needs a
  second separator to stay understandable, it was two lines.
- **Budget the length.** A completions entry is a verdict plus a pointer: ~1,100 characters, ceiling
  1,800 — link the note, never paste the investigation into the log.
- **Format for the smallest screen in use.** Bullets and labelled lines; tables only in research notes,
  never in chat. Bold one thing per line, not every other word. No all-caps emphasis. No `·` used as a
  sentence joiner — it renders as noise.
- **Read it once, top to bottom, BEFORE saving.** Ten seconds. Check the pairs a spellchecker cannot
  catch: their/there, its/it's, then/than, lose/loose, affect/effect, you're/your.
- **Quoted speech from the user is verbatim.** Never correct it, never tidy it.
- **Name the artifact** the note produced or measured. A claim with no pointer cannot be checked later,
  and an unchecked claim becomes a myth.
- **In a hurry? mark it** `**Status:** quick note — not proofread`. That is honest; passing a rushed note
  off as finished is the failure this section exists to prevent.

### Run the mechanical check before the note lands

```bash
python3 /opt/data/scripts/brain-proof.py <file.md>      # one note
python3 /opt/data/scripts/brain-proof.py --recent 3     # everything touched in 3 days
```

Catches what a hurried writer misses: broken tables, real-word typos, doubled words, a missing `# Title`,
and completions entries over budget. Exit 1 means findings, 2 means it could not check.

⚠️ **A checker that fires on correct prose teaches writers to ignore it.** This one's first version
flagged 20 of 91 real notes and nearly every hit was wrong: `their own` is correct English, `97 loose
files` uses the adjective. Only patterns wrong in *essentially every* usage belong in such a list — and
the way to find out is to run the checker against a corpus of notes that are already known good, not
against a fixture you wrote to make it pass.

⚠️ **Count cells, not pipes.** A `|` inside a table cell splits the row and invents a column, so a cell
holding `<path\\|url>` or `wallet. \\| next` must be escaped. Two real rows in a build queue were silently
broken this way and read as if a sentence had been cut in half.

### Before you write: are you the WRITER for that folder?

**One folder, one writer; everyone else reads.** Divergence between two copies of the same note is not a
discipline failure — it is two seats both believing they may edit the same file, neither able to see the
other. Check the ownership map (`00-System/FOLDER-RULES.md`) before creating or editing a note outside your
own lane. **Anything with two writers converges on one path and stays there** — if you need a change in
someone else's folder, request it or file your own note.

Reading is unrestricted, and a seat that teaches from the vault should read MORE, not less — memory files,
personal notes, decisions. What reading does not licence is a silent correction: if a fact you are about to
rely on is wrong, say so to the owner, because the note you quietly fixed is now a third version.

### A state file the ENGINE reads is not a note the BRAIN has

**If behaviour is driven by a JSON/YAML file, the vault must carry a prose twin that names the file as
the authority.** Otherwise every agent reasoning over the vault is reasoning from an old note, and the
human experiences it as "the brain is not being updated" while the machine is behaving perfectly.

Measured: the learning engine resolved its track correctly from `active-track.json`, and a grep of all
47 notes in that subject's folder for the track name, the config filename, and the current milestone
returned **zero hits**. The state existed only inside a skill pack. Nobody could have read it.

Give the twin a fixed name and a fixed shape (`<FOLDER>/CURRENT-STATE.md`):

- **the value in force** — one line, not a history;
- **who ruled it and when** — a ruling with no author is indistinguishable from a leftover;
- **the authority order** — which file wins, stated so a reader never has to guess ("if this note and
  `active-track.json` disagree, the file wins and this note is wrong");
- **what is explicitly OVERRULED**, quoted — a stale contradiction in a neighbouring config is the most
  expensive thing in the folder, because it reads as current;
- **what is deliberately not decided** — the open questions, so the next reader does not relitigate.

**Rule of thumb: a change nobody can read about did not happen.** When any mechanism changes state,
write the twin in the same session as the change — a JSON edit with no note is a change only the
machine remembers.

### A doc on the LOAD PATH must be checked for age, and for dead paths

A note nobody opens is merely unused. **A note every seat is told to read on wake-up and which is months
old is actively harmful** — it loads without error, so it lies in exactly the voice of authority.

- **Stale is silent.** There is no runtime signal, no warning, no broken link. A protocol file named as
  *"the single most important on wake-up"* can sit a month untouched while every seat trusts it. **Check
  `mtime` before you trust a doc whose only virtue is that the instructions say to.**
- **Say the age out loud when you load it.** "This says X, and it was last written N days ago" is the
  honest form; quoting a stale file as current is the failure.
- **Wire every doc you add to the load path into a staleness check in the same change.** A map with no
  producer watching its age decays into fiction, and the decay is invisible until someone acts on it.
- **Verify every path a navigation doc names actually resolves.** Onboarding docs accumulate dead
  references as the tree moves, and a reader following them literally hits two or three 404s before it
  reaches anything useful — it learns the map is unreliable and stops using it. **Rewrite the dead path
  and record it as a pitfall**; a doc that sends readers to files that no longer exist is worse than no doc.
- **Measure the map against the tree, not against memory.** The list of "files that must never go stale"
  is worth writing down, because it is short and checkable — and the ones near the top are usually the
  ones that have gone longest without a writer.

### A folder is a name until it has a writer

**Creating a lane does not create the behaviour.** A folder with a README and no author produces nothing,
and it will show up in every audit as an empty room whose owner booked it and never came.

Before declaring a lane real, name three things in its README:

1. **who writes to it** — a named seat, and the schedule or trigger that makes them write;
2. **what belongs** — the four or five artifact kinds, so a writer can decide without asking;
3. **what does NOT belong** — the things that will otherwise drift in. A lane that accepts everything
   becomes a filing cabinet, and the audit will report it as "nobody reads this".

**And state the honest starting position in the folder itself**, not in a handoff where it will be
forgotten: if the named writer has no job that touches the folder yet, write that down. A README that
claims a live lane the fleet does not run is a lie that the next audit inherits.

Test to apply before filing a lane as done: **can I name the first three things that will be written
here, and by whom?** If not, it is a folder, not a lane.

### Repairing a folder that already went wrong

Use `references/vault-consolidation.md` for the full procedure: audit → triage → back up outside the vault
→ merge field-by-field → redirect → verify with the consumer. It carries the two findings that decide
whether a merge is safe: **a path match must anchor** (`HQ/` otherwise matches inside `00-HQ/`), and **the
newest content is not always in the canonical folder** — readers resolve a path, and a path can point at
the stale copy. It also carries the rule for **renaming** a live folder: measure the contents and the
anchored reference count first, separate "the lane moved" from "the contents are theirs", and assign
custody by asking the claimant seats rather than reading it off the new name. Check the folder drift with
`python3 /opt/data/scripts/audit-folders.py`.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
