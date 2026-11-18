# Memory visibility — the hook instrument

**Purpose:** put the memory fill number into the *agent's* context before it writes, not only into a report a
human reads. A dietician that mails percentages does not stop a seat from discovering its cap by being rejected
mid-task.

Two moments, two different jobs:

| event | job | behaviour |
|---|---|---|
| `on_session_start` | awareness — the number is on the table for the whole session | always prints |
| `pre_llm_call` | warning — the number arrives at the moment of the decision | **prints only at/above the band** |

A single top-of-session reading ages (memory is frozen at session start, so the injected prompt does not move)
and a per-turn reading below the band is wallpaper. Neither alone is enough, which is why there are two.

---

## The wire — what Hermes actually accepts

A shell hook gets stdin JSON (`hook_event_name`, `tool_name`, `tool_input`, `session_id`, `cwd`) and its stdout is
**parsed as JSON**, never read as text.

```json
{"context": "memory [seat] MEMORY 2542/3200 (79%) · USER 1399/1800 (78%)"}
```

- **Plain text is dropped.** The dispatcher logs a warning and the run reports
  *"contributed nothing to the dispatcher"* — indistinguishable, at a glance, from a hook that printed nothing.
- **`pre_tool_call` cannot carry context.** Its parser recognises only `block` / `modify` / `approve` and returns
  `None` for anything else. Context injection belongs on `pre_llm_call` (which falls back to the context parser)
  or on `on_session_start`.
- **A `pre_tool_call` hook that returns exit 2 blocks**, even with no JSON — a legitimate but *different* tool:
  blocking a write at 100% is a last resort, not the awareness mechanism.

---

## Configuration

```bash
hermes config set --force hooks '{
  "on_session_start": [{"command": "/opt/data/scripts/memory-gauge.py --hook", "timeout": 10}],
  "pre_llm_call":     [{"command": "/opt/data/scripts/memory-gauge.py --hook --warn-only", "timeout": 10}]
}'
```

- **`--force` is required to replace a nested section.** Without it the CLI replies with a dotted-path hint and
  writes nothing.
- **The agent-facing file tools refuse `config.yaml`** — that guard is correct; the CLI is the sanctioned path.
- **Shell hooks need per-command consent.** `get_hermes_home()` resolves to the **profile** directory, so the
  allowlist is `profiles/<seat>/shell-hooks-allowlist.json` — **one approval per seat**, not one per host. A
  configured-but-unapproved hook never fires, and four seats reporting "configured" is not four seats firing.
- **Do not set `hooks_auto_accept` to skip consent.** It auto-trusts any hook later added to config — a broader
  hole than the feature closes. Surface it as a gate for the user instead.

---

## Verification

```bash
hermes hooks list                 # configured + consent status per command
hermes hooks test on_session_start    # fires against a synthetic payload
hermes hooks doctor               # exec bit · allowlist · mtime drift · JSON smoke test
```

**Read the `parsed:` line, not the exit code.** `parsed (Hermes wire shape): {"context": …}` means it landed;
`parsed: <none — hook contributed nothing>` means the JSON contract was missed. A hook can exit 0 and contribute
nothing, so a green exit is not delivery.

---

## The gauge's own correctness — five rules, each measured

1. **Band on the EXACT ratio, not the rounded display.** 2,557/3,200 = 79.9%, prints as `80%`, and a `>= 80` test on
the rounded value fires *before its own stated threshold*. Compare `chars/limit`; print the rounded figure separately.
2. **Name WHICH file is tight.** "MEMORY near cap" when `USER.md` is the full one sends the next session to trim the
wrong file. Report `tight = max()` and say `USER.md`.
3. **Include the headroom in characters.** `85%` is a mood; `482 chars of room in MEMORY.md` is a budget.
4. **An unreadable file is `UNKNOWN`, never `0%`.** Missing, corrupt and empty are three states and only one of them
means the agent may write.
5. **Say what the band means for the NEXT action**, not just the level: at `>=90%` the next add is a coin flip; at
`>=100%` the tool **will reject** it, and the fix is archive-then-rewrite.

---

## Bands that survive contact

| fill | label | what it tells the agent |
|---|---|---|
| `<80%` | quiet | headroom exists; per-turn hook stays silent |
| `>=80%` | NEAR CAP | consolidate before adding a big fact |
| `>=90%` | TRIM NOW | the next add may be rejected |
| `>=100%` | AT CAP | a write **will** be rejected — archive, then rewrite |

**Fixture the boundaries, not the middle.** The failure modes live at the edges: 2,557 chars must be silent,
2,560 must warn, 2,880 must go red, 3,200 must say REJECT. A gauge verified at 50% proves nothing.

---

## The honest limit, stated in the tool's own header

**A gauge prints a number; it cannot make anyone act on it.** Memory is frozen at session start, so any single
reading ages — which is why the per-turn hook exists and why it must be warn-only. Write that limit into the script
so the next reader does not mistake a printed percentage for a guaranteed behaviour.
