# Memory budget — the fleet's instruments, what each one does, and the rules for touching memory

Depth for the always-on rules in SKILL.md. Read this before writing, extending or retiring anything that
measures or trims a memory file.

## The stack

| what | where | what it does |
|---|---|---|
| `memory-dietician.py` | **`/opt/data/scripts/`** — shared, outside every profile | measures **every seat's** MEMORY.md + USER.md; reads caps from each profile's own `config.yaml`; archives a dated copy; prints `CUT?` proposals **with the rule that fired**. **Never writes a memory file.** Silent + exit 0 when every seat is healthy. `--check` is the default and never writes |
| `memory-dream.py` | same tree | proposes promotion (a line removed then re-observed) and retirement (a standing rule nobody has mentioned in N runs) |
| `memory-relieve.py` | `<profile>/scripts/` — HQ-local, **not** on the shared path | the only ACTOR: moves **one** archival-shaped entry per over-trigger file, verbatim, ledgered |
| protocol | `01-HANDOFFS/_archive/memory-trim-protocol.md` | the six-question keep/delete evaluation and the hard rules |
| archive | `11-Mess Hall/memory-archive/` | where cut lines go, fleet-standard |

**Caps are per-seat and live in `config.yaml`** — `memory.memory_char_limit` and `memory.user_char_limit`. Read
them from the seat's own config and quote that number. Never maintain a remembered cap table: a table of stale
caps is how an instrument ends up reporting a limit the seat does not run under, and the dietician's own history
contains exactly that drift.

## What each instrument's output means

- **`CUT? [RULE] …`** — a proposal with the rule that fired (superseded, pointer-shaped, narrative).
- **`CUT? [NO RULE FIRED] … every one is doing work. ACTION: this seat must consolidate BY HAND`** — the file is
  crowded but load-bearing. **This is a correct answer, not a failure of the tool.** Merge same-topic entries,
  push detail to the vault, keep a one-line pointer.
- **Silence** — every seat is healthy. A silent run is the normal output.

A non-zero exit from either instrument is an **instrument failure, not a finding** — say so loudly rather than
letting an empty report read as "all healthy".

## Why an auto-trimmer is the wrong shape

The dietician was rebuilt to stop trimming, and its header states the reason: the earlier version *"trimmed by
position — a destructive write of the agent's own durable memory, dressed as maintenance, where the cut lines are
exactly the ones the agent would have kept."*

Therefore:

- **A "keep-score" is position-trimming with arithmetic.** Identifiers score high, prose scores low, and the
  fleet's protected categories (preferences, corrections, wallet rules, language rules) score **below** a bare
  address — so a scorer nominates them first, every time.
- **Relief moves ONE entry per run, deliberately.** Incremental and reversible beats a batch rewrite; a bad
  single move costs one entry, a bad batch costs the file.
- **Relief never touches USER.md** — facts about the user are not a size decision.
- **Archive, then read the archive back, then complete the write.** The only reason a bad trim is recoverable is
  that the cut text already exists on disk.
- **Two trimmers on one file is worse than one.** They race, they disagree on thresholds, and the loser's archive
  silently misses entries.

## Safe pressure relief that needs no new code

1. **Merge, don't delete.** Several related entries become one shorter line that keeps every identifier.
2. **Move procedures out.** A procedure belongs in a skill or a vault note; memory keeps a one-line pointer if
   the pointer itself saves steering.
3. **Get under the WARN threshold, not merely under the cap** — otherwise the next write is refused and the trim
   bought nothing.
4. **Prefer a pointer to a payload.** Memory is the index; the vault is the library. An entry naming a vault note
   is cheap; the same facts inlined are not.
5. **Write terser the first time.** The instrument is fine; the writer is the variable. Fewer, higher-signal
   entries beat a bigger budget — an elaborate memory stack can *reduce* performance by filling context with
   noise.

## If a seat has no actor

A fleet measurer with no actor attached prints the same proposals forever. The correct fix is to get the actor
onto the shared path (`/opt/data/scripts/`), requested from the seat that owns it — **not** to write a
seat-local third tool beside a fleet instrument.
