# Staleness Policy and Four-List Routing

Depth behind rules 5–7 of the parent skill. The policy is **data**: one JSON file the sweep reads every
run, editable by the user without touching code.

---

## The class table

Evaluated **in order — first match wins**, so exemptions come first. Each class: a glob list, a max age,
and the action required when the age is exceeded.

| # | class | max age | action when overdue |
|---|---|---|---|
| 1 | **permanent** — archives, backups, generated trees, machine artifacts, completion records | `null` | none. A record must not be refreshed; a backup that gets updated is not a backup |
| 2 | **deadlines** | 7d | move it forward or kill it — an expired deadline does not get to sit |
| 3 | **the human's queue** | 7d | anything not actionable this week goes to pending **with its gate named** |
| 4 | **decisions / travel / project status** | 14d | decide, park with a date, or archive |
| 5 | **ideas** | 21d | promote, park with a revisit date, or drop — an untriaged idea is not a plan |
| 6 | **environment facts** | 30d | verify it is still true; a stale fact loads into every decision from that folder |

A useful starting rule of thumb: *"the oldest item maybe a week or two, depending on what the
information is"* — the classes differ, so the number must too.

### Writing the globs

- **Exempt machine artifacts explicitly** (`node_modules`, backup dirs, snapshots, asset folders) — they
  are not stale, they are not ours.
- **Longest/most specific pattern first.** A `permanent` file inside a stale-prone folder is the common
  false positive, and a sweep that flags it nightly trains its reader to ignore the sweep.
- **Match against the path RELATIVE to the corpus root**, and test both the full path and a
  directory-prefix form, or a `**/dir/**` style pattern silently misses.

---

## Structural findings (not TTL violations)

These are the highest-value output of a curation sweep and have no max-age:

- **Empty folders** — structure without content. Compute over the **subtree**, never the immediate
  listing, and report them as their own section. After a restore or migration these are the loudest
  signal that a skeleton came back without its contents.
- **One subject, several homes** — the same subject split across N folders. Group by a subject token and
  report the folder list. **Exclude anything classified `permanent`** and exclude namespace folders
  (handoff lanes, cloned third-party repos) or the report is dominated by a snapshot archive's internal
  folders and reads as noise.

---

## The four lists and their routing

Map each policy class to the list that owns it, in the policy file — adding a class must not mean
editing the writer.

```
class                 ->  list            owner
human-gated classes   ->  their own list   the human
work we can do        ->  build queue      the seat that owns the domain
an external verdict   ->  pending          (state the gate + release)
anything finished     ->  completed        (with proof)
```

**Row shape per list.** Each list has its own; match it exactly.

- bullet lists: `- [ ] **<what>** — <detail> <br>*owner: X · first seen <date>* <!-- id: cur:… -->`
- markdown tables: one row per finding, **and the table header on first write**
- JSON registries: an item object with `id`, `title`, `completed`, `owner`, `proof`, `source_list`

Keep the id in a form that survives both rendering and grep — an HTML comment in markdown, a code span
in a table cell — so the dedupe can find it without the human reading it.

---

## What the wake consumer does with all this

One consumer, once, at wake time. It reads the state files the overnight jobs wrote and:

- names **the single most consequential** new row and which list it landed in — never the whole set
  (the rows are already IN the lists; that is the point of routing);
- says what **closed**;
- names the worst overdue class and **one** file from it, not the table;
- reports a job's absence by the **age of its artifact**, not by a missing success message.

A brief that enumerates is a report the reader skips; a brief that points is an instruction the reader
acts on.
