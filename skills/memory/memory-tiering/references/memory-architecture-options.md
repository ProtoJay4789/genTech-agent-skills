# Memory architecture options — runtime memory vs vault memory

Load this when the question moves past *"trim the file"* to *"change what memory IS here"*, or when someone
asks which third-party memory framework we should adopt.

## The design to aim at

**Runtime memory is a pointer and a retrieval index. The vault is where the facts live.**

Everything loaded every turn must earn its place by applying to EVERY turn. Anything else has a better home:

| what it is | where it goes |
|---|---|
| applies to every turn (identity, red lines, rails, live caps) | MEMORY.md / USER.md |
| governs one class of task (a procedure, a workflow, a check) | a SKILL.md — it loads only when relevant |
| reference material, findings, history, measurements | the vault — searched when the topic returns |
| a fact that stopped being true | deleted in the same turn its replacement is written |

**The consequence to state out loud:** a curtailed memory file only helps if the facts it gave up are
still reachable. Deleting without a home for the fact is not architecture, it is forgetting.

## Why a rule-based trim cannot reach a 40–50% target

- **The ranker's levers are finite.** WRONG SEAT → SUPERSEDED → POINTER → NARRATIVE. Once all four are spent,
the only way to keep "finding cuts" is to weaken a rule, and a weakened rule deletes a fact the seat needs
every turn.
- **Do the arithmetic before agreeing to a percentage.** On 3200 / 1800 caps, 40–50% is roughly 1,280 / 800
characters — for most mature files that is a rewrite, not a trim.
- **What mechanical cleanup can actually reach is ~60%**: duplicated identity blocks across seats, stale
entries, entries that belong in a skill. Below that, only a design change moves the number.

## The benchmark that reorders the whole question

The MemGPT team (Letta) scored agent memory on **LoCoMo**, the standard long-conversation retrieval benchmark:

| approach | LoCoMo |
|---|---|
| **plain filesystem + `grep` / `search_files` / `open` tools** (GPT-4o mini, minimal prompt tuning) | **74.0%** |
| Mem0's best graph variant (their own published number) | 68.5% |

Their conclusion, not ours: specialised memory tools built for single-hop retrieval are *less* effective than
letting the agent iteratively search its own files — agents are already competent at filesystem tools because those
were in their training data.

**What this does to the criteria below:** a markdown vault plus search is not the budget option, it is the winning
architecture on the public benchmark. So:

- **Stop shopping for a memory STORE.** Every product in the table below competes against a filesystem on a
  benchmark the filesystem won.
- **The remaining value is write policy, not storage or recall** — what gets written down, in what form, and what
  retires. That is the deterministic consolidation pass, and it is cheaper to build than to buy.
- **Score our OWN recall before authorising any spend.** Twenty questions whose answers live in the vault, each
  requiring a cited note, decides whether a memory purchase is justified at all. If recall is already strong,
  every product on this list is unnecessary — say that plainly rather than migrating for its own sake.
- **Discriminate retrieval on the layer it reads: titles vs bodies.** A provider that substring-matches page
  TITLES and one that scores note TEXT are different capabilities, and no feature list distinguishes them. Run
  both over the same real corpus and compare the answers.

## Judging a third-party memory system — criteria in order

Star count is not a fit criterion. Rank on these, and stop at the first hard failure.

1. **Native provider for this engine, or an adapter you would have to write?** A provider interface
(`memory.provider`) is the difference between a config line and an integration project. An adapter means WE
become the maintainer of the seam.
2. **Markdown-first, or its own store?** A system that keeps memories in its own database adds a SECOND place
to look — the exact opposite of the goal. The vault must remain inspectable, diffable and portable.
3. **Does its install documentation name an engine version at or below what is running?** An unmeasured
version gap is the FIRST thing to prove, not the last thing to discover. A doc that references features from
a later release is a signal, not a blocker — but the registration test decides.
4. **Multi-profile behaviour.** Under a multiplexed gateway, one provider process per profile or one shared?
Per-profile identity must come from the profile's own environment, not the gateway process.
5. **Runtime dependencies.** A missing runtime is an install step, not a rejection — but confirm it before
recommending, and never present an unverified dependency as free.
6. **Is the consolidation pass deterministic?** A rule-consolidation pass that runs no model costs nothing,
cannot hallucinate a rule, and can be audited line by line. A pass that needs an LLM to decide what to
forget is a second agent with write access to the thing that governs behaviour.

## The four classes — and the half a promotion rule cannot see

Tiering on "does this apply every turn" is necessary but too coarse to move bytes. Split what remains by what it
DOES, because each class has a different home and a different decay:

| class | example | home | decay signal |
|---|---|---|---|
| **identity** | who the agent is, the boss, speech rules, hard boundaries | ACTIVE, always | none — human-curated |
| **standing rule** | never fake a receipt, never sign, write only your own domain | ACTIVE, or the SKILL.md governing that task | **got it wrong once** |
| **environment fact** | paths, uid, container layout, rate limits, cron ids | **a generated command card, not a memory line** | **rots on its own** |
| **queue / pending** | a thing to handle later, with a gate | the handoff mesh's existing machine states | expires |

**Environment facts are the class that rots, and the numbers are blunt.** On one seat, 25% of memory was environment
fact and **3 of 11 entries were wrong inside three weeks — while zero rules and zero identities were wrong.** Every
one of the three was a path, a layout or a rate limit. An env fact in memory is a copy of something the filesystem
or the CLI answers authoritatively; move it to a card the agent regenerates each night.

**A rule is OBEYED, not recalled — so a recall-frequency signal cannot govern it.** Promotion keyed on "looked up
twice" silently excludes the highest-value class, because a rule that works is never looked up. The promotion signal
for a rule is a **mistake** ("I got this wrong once"), so rules need a different intake from facts.

**Demotion is the half a promotion rule cannot see.** Design only entry to ACTIVE and ACTIVE converges on the cap,
reproducing today's file with more machinery. A fact not recalled *and acted on* within N turns leaves; the seat's
own record of what it used is the evidence, and the pass stays deterministic.

**Size the ACTIVE cap as identity + rules, not as one number.** An identity block alone can exceed 1,300 characters on
a seat that carries person-boundary rules, so a ~1,200-character ACTIVE tier starves identity before touching a
single rule. Measure identity and rule bytes per seat first, then set the cap above their sum.

**The queue usually already exists.** Before designing a memory queue, look for the one the fleet runs: handoff notes
with machine states, an SLA clock and an owner already ARE a queue with a drain. A second queue in memory has no
owner and inherits the known failure — a drain that retries without re-reading whether the item is still open.

## The candidate shapes, and what discriminated them

| shape | example class | verdict logic |
|---|---|---|
| **Native provider + markdown vault + deterministic consolidation** | `itechmeat/open-second-brain` | the only shape that MATCHES the design on paper: native provider, vault stays markdown, consolidation runs no model. **Measured outcome: declined anyway** — see below |
| Markdown vault + many commands, adapters for OTHER agents | `eugeniughelbur/obsidian-second-brain` | popular and capable, but no native provider here — adopting it means we write and own the adapter |
| Vault that wants to own the structure | `breferrari/obsidian-mind` | fights an existing vault layout; a structural takeover is a migration, not an install |
| Memory-as-a-service store | `mem0ai/mem0` | stores memories in its own backend — a second place to look, the failure this design exists to avoid |
| Database-first (SQLite/FTS) | `Gentleman-Programming/engram` | strong engineering, but the brain becomes a database: not readable, not diffable, not portable as notes |

**Read the install documentation, not only the README.** The README sells the idea; the install page states
the engine version, the runtime dependencies and the profile-scope behaviour that decide whether it works here.

**Matching the design on paper is not passing the gate.** The top row above was evaluated end to end and declined:
the provider registered cleanly and queried the real vault, but its recall was a case-insensitive substring over
page **titles** (the incumbent scores note **bodies**), the hook that feeds context each turn returned an **empty**
preferences file, and its `health()` reported `ok: true` on a box where its required runtime was absent. Take the
consolidation algorithm and build it locally; decline the runtime. The general gate lives in
`external-capability-vendoring` — this note exists so nobody re-opens the same evaluation from scratch.

## The engine's provider-swap mechanics

- The key is **`memory.provider`** under `memory:` in the profile's config. **Exactly one external provider
is active at a time**, and built-in MEMORY.md / USER.md stay active alongside it.
- `hermes memory status` reports the provider and whether it is available. `hermes memory setup` is the
interactive selector. `hermes memory off` reverts to built-in only.
- **Installing makes a provider AVAILABLE, not ACTIVE.** Activation is the separate config change — a plugin
that installed cleanly and never activated looks exactly like one that is running, from the install output.
- **A copy in the engine's bundled plugins directory shadows the installed one**, so updates appear to change
nothing. Remove the stray copy and restart the gateway.
- **Rollback is one key.** Point `memory.provider` back and restart; nothing about the vault is destroyed by
trying a provider, which is what makes the registration test cheap.

## The gate before adopting — prove registration, then migrate

**Never migrate several seats on the strength of a README.**

1. Install into ONE throwaway or scratch profile. Change nothing on a live seat.
2. Start it and read the registration line: a provider advertises its tool count at registration; **`(0 tools)`
means the version predates the tool set** and the install is not what the doc describes.
3. Read `hermes memory status` and the gateway log together. A bridge failure surfaces LATER as a runtime
start error, not at install — so an install that printed success proves nothing.
4. Only then migrate one real seat, and keep the old provider's key handy as the rollback.

## The fallback when nothing fits

A vault-backed provider plus a one-line spill/return path implements retrieval, and somewhere for overflow to go
without loss — **provided its configured root points at the brain.** Verify that before crediting it: a provider's
root is normally one subfolder, and a recall tool indexing 3 files looks exactly as healthy as one indexing 6,000
(§ *The recall you measured is only the corpus it indexed* in SKILL.md). What the architecture then still lacks is:

- a **write policy** (what gets promoted from the vault into runtime memory, and what demotes back out),
- a **consolidation pass** (repeated corrections becoming one rule, unused rules retiring).

Those two things are smaller to build than an adapter for someone else's system, and they are the part that
actually changes what the fleet remembers. Say so plainly rather than recommending a migration for its own sake.
