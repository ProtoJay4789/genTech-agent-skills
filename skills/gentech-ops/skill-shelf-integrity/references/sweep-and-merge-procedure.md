# Sweep and merge — procedure

Concrete steps for the two operations in `SKILL.md`. Paths are this host's: CORE is
`/opt/data/skills`; seats are `/opt/data/profiles/<seat>/skills`.

## A. Adopting a CORE shelf change

1. **Read the handoff for the trap list**, then check which trees exist before touching one.
2. **Diff the survivor** (Rule 1). Save the unique-line count per file; anything above zero is content
   to promote up, not to overwrite.
3. **Confirm the absorbed bodies are preserved** in CORE and are byte-identical to the seat copies
   (`md5sum`). Record the hashes in the report — a delete without a hash is a claim, not a proof.
4. **Tar the seat copies** before deleting anything.
5. **Copy the survivors down.** `cp -a "$CORE/<skill>/." "$SEAT/<skill>/"` is a merge-copy; it cannot
   drop files the seat has, but it also cannot restore a file CORE never had — that is what the diff
   was for. (`rsync` may be absent on this host; `cp -a` needs no substitute tool.)
6. **Delete the absorbed directories**, then prove four things: the survivors' hashes match CORE, the
   absorbed dirs are gone, no `SKILL.md` sits under any `references/`, and the enabled count arithmetic
   holds.
7. **Repoint stale citations, not scope vocabulary.** A permissions row that mentions a skill name is
   data. Grep for the absorbed names and classify each hit: a path pointer gets repointed, a table row
   does not. A `references/` scanner will not catch a dangling skill name, so this pass is manual.

Report shape: what was restored, what was deleted **with hashes**, the index arithmetic, and any gap
found in CORE itself (a skill the handoff says was promoted but is missing from CORE is a real finding —
say so rather than silently sourcing it from a peer).

## B. Sweeping dangling `references/` citations

```bash
python3 /opt/data/scripts/skill-ref-audit.py --root <tree>   # exit 0 clean / 1 findings / 2 absent
python3 /opt/data/scripts/skill-ref-audit.py --root <tree> --json
python3 /opt/data/scripts/skill-ref-audit.py --root <tree> --orphans   # exist, cited by nobody
```

It reports: `dangling` (skill-relative, absent, undeclared — fails), `cross-missing` (a named
skill/vault path that does not exist — fails), `declared` (absent but named under
`## Missing references` — passes), `external` (repo/URL paths — passes), `traps` (a `SKILL.md` inside
`references/` — fails).

### Classify every finding before fixing any

For each cited path, in this order:

1. Does the **same skill path** hold it in another tree? → restore.
2. Does the line name an owning skill whose directory holds it? → the citation is already correct;
   this is a checker false positive, not a defect. Fix the checker, not the file.
3. Is the citation part of a longer repository or vault path that exists? → external, leave it.
4. Is the base wrong but the artifact real and identifiable? → correct the base, and flag it in the
   report as a judgement call.
5. Otherwise → declare under `## Missing references`, listing the path, the fleet-wide search that
   found nothing, and the nearest real material where you actually verified one exists.

**Declaration block** — keep it factual, no speculation:

```markdown
## Missing references

Cited in this skill but **absent** — verified <date> across CORE and all seat trees.

Listed here instead of repointed at something similar: a wrong pointer is worse than a known gap.

- `references/<name>.md` — <no copy on any seat | the citing line names <skill>, which is not on the
  shelf>; <nearest real material, and why it is a different artifact>.
```

### Reading the result

- **Undeclared dangling = 0** is the passing state. A shelf with 27 declared gaps and zero undeclared
  ones is *clean*: every remaining gap is visible to the next reader.
- Report declared gaps as context, never as findings — otherwise the honest fix is punished and the
  next agent prefers a wrong pointer.
- Fleet-wide, expect different counts per tree. Publishing one total hides which tree regressed.

## C. The standing check

Silence-gated, one script, all trees:

- audit every tree with the same implementation (import it, do not re-implement);
- store per-tree `{findings, declared, citations, when}` in a state file;
- print **only** on first measurement, growth, shrinkage, or a change in declared count;
- always exit 0 — a missing tree is a finding in the text, not a job failure, because a red job page
  nobody reads is the same absence as no job.

A cron job needs a **real file** in `profiles/<seat>/scripts/` (no symlinks); put the logic in the
canonical script and make the cron entry a thin runner that hands off to it. Two copies of a rule are
two answers to the same question.

**Then prove the rail fires** — see "Prove the standing check can DELIVER" in `SKILL.md`. A job that
has only ever been silent has never delivered anything, and `delivery_outcome` is the receipt that
tells the two apart.
