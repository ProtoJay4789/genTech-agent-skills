# Market requirement mining — building a curriculum backward from real postings

Jordan's rule, and the whole point of the exercise: **the curriculum's job is to DELETE the irrelevant
prerequisite.** Colleges bill for a dozen general-education courses before the major. The market's actual
stated requirements are a short list. That gap is the product — so the curriculum is derived from postings,
never from our opinion about what matters.

Use this when the question is *"what should the curriculum teach?"* or *"what should I learn next?"* for a
job or career track.

## The procedure

### 1. Fix the target roles FIRST, from the user's own filters

Mine only the titles the user will actually apply to. Getting this wrong makes the whole harvest useless.

- Write the filter down and hold it: title family, seniority, remote, working language, **and the roles the
  user has explicitly EXCLUDED.**
- **A user filter can invalidate roles already on the list.** When the user says *"avoid dev roles and
  DevRel,"* that removes items that were previously marked "qualify-now." **Re-sort the list in front of him
  and say which entries just fell out** — never keep them silently.
- **A title is not a function.** One title can cover two different jobs. Split the results before ranking,
  or the ranking describes a job the user has told you not to take.

### 2. Harvest real postings, not listicles

Collect **20–40 individual postings, full text** — not search snippets. Prefer ATS-hosted pages: they render
without a login wall and carry the whole requirement block.

| Source shape | Use | Note |
|---|---|---|
| `jobs.ashbyhq.com/<company>/<uuid>` | ✅ best | full text, no wall |
| `job-boards.greenhouse.io/<company>/jobs/<id>` | ✅ best | full text |
| `jobs.lever.co/<company>/<uuid>` | ✅ good | full text |
| company `/careers/<id>` | ✅ good | full text |
| `himalayas.app`, `remoterocketship`, `builtin` | 🟡 index pages | many titles, thin text — discovery only |
| ziprecruiter / indeed / glassdoor / linkedin | ❌ | walls and snippets |

**Append every extracted page to a workspace file as you go** (`postings-text.json`), so a timeout costs one
batch rather than the run. Extract in batches of 5–15; check the char count and skip anything under ~1,500
chars rather than counting an error page as evidence.

### 3. Rank by PER-POSTING frequency, not mention count

The number that means something is **how many of the N postings ask for it**, not how many times it appears.

- Pattern-match a taxonomy across the corpus (cloud · containers · languages · APIs · AI/agents ·
  customer-facing · security · meta-gates).
- Report `k/N` plus a percentage. *"18/30 ask for onboarding or post-sales adoption"* is a decision the
  curriculum owner can act on; *"onboarding came up 40 times"* is not.
- Keep **comp features (equity) and culture words (startup, fast-paced) OUT of the ranking** — they are not
  learnable requirements and they inflate the table.

### 4. Score every requirement against what we already ship

Three states, and **the tally is the argument**:

- **✅ shipped** — running in production with a receipt
- **🟡 partial** — the mechanism exists, no public proof
- **🔴 gap** — genuinely absent

Grade against the **whole stack** (services, crons, skills, memory), not the project you happen to remember.

### 5. Order the chapters from the evidence, then hand it over

The output is the evidence **base**, not the finished curriculum. The seat that owns the learning surface
chooses what becomes a module — writing the modules yourself routes around that seat.

---

## The findings that shape every version of this

### Measure the degree gate — it is the headline number

**Run "mentions a degree requirement" and "mentions years of experience" as first-class rows.** Across one
30-posting corpus a degree appeared in **13%** of postings, and the engineering gen-ed canon (algorithms, data
structures, discrete math) appeared in the requirement text **nowhere**. Report that number explicitly — it is
what converts a soft claim about communication skill into a market fact, and it is the direct argument against
sequencing prerequisite learning.

### Separate the SCREEN-CLEARERS from the differentiator

Rank by frequency, then **split the list**. The high-frequency boring items (APIs, cloud, comms,
troubleshooting) get you past the screen; the low-frequency advanced items (protocols, frameworks, evals) make
you memorable once you are through. **A differentiator sitting at 0–13% is not a requirement — say so plainly
rather than presenting our strongest asset as the market's top ask.** Order the curriculum by the
screen-clearers and use the depth as the closer.

### The talking half is a requirement, not a soft skill

Expect customer-facing communication, demos and discovery/scoping to rank in the top third on any
solutions/deployment-shaped title. Treat it as a teachable, provable module — the submitted work and the
teaching already done are its receipts — never as a fallback for a candidate who "cannot code."

### Two tracks, always

- **Track A — understand the domain** (what the subject *is*: yield sources, market hours, custody)
- **Track B — use the instrument** (how to actually get there: read the reports, set a target, know when it
  is wrong)

Most programs teach A and forget B — which is why people can define a concept and still cannot operate
anything. Ship both, in parallel.

### One state file, every surface derives

A live curriculum needs the *"cleared this goal, next is this"* behaviour, and that comes from a single state
file that every surface renders — the public page, the daily brief, the module list. **The failure mode is the
one this whole practice exists to avoid: several surfaces each stating their own count.** If two of our pages
disagree about how many chapters or services exist, the missing single source is the finding, not either
number.

---

## Pitfalls

- **A 0% from a small corpus is a signal to look closer, not a proof of absence.** An item scoring 0/N may
  reflect the pattern list rather than the market. Name which rows are pattern-risk and re-probe before
  reporting a gap.
- **Pattern-counting is not human coding.** A passing mention counts the same as a mandatory line. **State
  that limit in the output** — directionally sound, not precise — because the table gets quoted back as fact.
- **Check the source mix before generalising.** AI-native boards over-represent AI items and under-represent
  legacy-enterprise items (Linux, SQL, IaC). Name the skew; do not launder it into a market-wide claim.
- **Report the sample size honestly.** If the scope was ~40 and the run produced 30, say 30. Never round up to
  the number you planned.
- **Never reprofile the evidence base into a syllabus.** It is input for a curriculum owner, not a course.
