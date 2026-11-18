# Staleness Policy — shelf lives as data

The maintainer's rulebook, kept in a config file the user can edit. It lives in data rather than in
the maintainer's habits so that a rebuilt tool behaves identically after the script is gone, and so the
user can change a shelf life without touching code.

A policy with no file is a habit; a habit dies with the session that held it.

## Schema

```json
{
  "ttl_days": {
    "deadline":      7,
    "queue":         7,
    "consideration": 14,
    "travel":        14,
    "project":       14,
    "idea":          21,
    "hq_fact":       30,
    "mess_hall":     30
  },
  "permanent": [
    "_archive/**", "**/_archive/**", "backups/**", "**/backups/**",
    "10-Archive/**", "memory-archive/**", "assets/**", "node_modules/**",
    "skills-distribution/**", "*completions*"
  ],
  "permanent_reason": "a record is not 'updated', and a backup that gets refreshed is not a backup"
}
```

## The two lists, and why both are needed

- **`ttl_days`** — classes where age is meaningful. Past TTL means *someone must look*, never *delete*.
- **`permanent`** — classes where age is NOT meaningful. These are never flagged, never refreshed,
  never "tidied". Getting this list wrong is what makes a maintainer destructive: an archive and a
  backup look exactly like a stale folder to a rule that only knows age.

## Classifying a path — the order that matters

1. **Permanent by path first.** A backup or archive that happens to sit inside a live tree is still
   permanent. Check the path against `permanent` before consulting `ttl_days`.
2. **Then class by lane.** Map the file's lane to a TTL class; an unmapped lane is a defect in the
   policy, not a licence to guess — say `UNCLASSIFIED` rather than assigning the nearest class.
3. **Then measure age** from the file's last real edit, and compare.

## Pitfalls

- **A swallowed path is not a clean scan.** If the permanent-matching rule matches the vault's own
  containing directory, the whole tree is skipped and the run reports a pristine result. Print the
  files actually scanned alongside the verdict.
- **A restore or backup tree contains its own internals** — pre-wipe snapshot copies, `legacy/` trees,
  vendored dependencies. Counting those internals as "homes" for live lanes produces false positives on
  the first run of any ported rule. Treat backup/archive/legacy/vendored trees as permanent wholesale.
- **An empty top-level folder is a finding, not noise.** It usually means a lane was designed and never
  filled — worth knowing, and the opposite of "nothing to do here".
- **An empty-looking directory can hold the only copy of something** (records, pointers). Before pruning
  an "empty" structure, ask what made it empty and whether anything points into it.
