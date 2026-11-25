# Memory gauge + shell hooks — making the cap visible before the write

Depth for the two SKILL.md sections *"Make the cap VISIBLE"* and *"A measuring tool must resolve the seat"*.
Load this when installing, approving or debugging a per-turn memory reading.

## Why it exists

A cap you discover by *hitting* it is not a limit, it is a wall: the rejection arrives **after** the agent decided
what to write and has nowhere to put it. The reading that matters is taken at session start and again at the moment
of the decision, so the number is visible **before** the write rather than inferred from the failure.

## Install (per profile — never hand-edit `config.yaml`)

```bash
hermes config set --force hooks '{"on_session_start": [{"command": "<gauge> --hook --profile <seat>", "timeout": 10}],
 "pre_llm_call": [{"command": "<gauge> --hook --warn-only --profile <seat>", "timeout": 10}]}'
hermes hooks list                     # ✓/✗ allowlisted, per hook
hermes hooks doctor                   # exec bit, allowlist, mtime drift, JSON validity, timing
hermes hooks test on_session_start    # fires a synthetic payload; proves the wire shape and the numbers
```

Verify the write **by reading the config file back** (`grep -A8 '^hooks:' profiles/<seat>/config.yaml`) and by the
path the command printed — a success message is not a persisted value.

## Four mechanics, each measured

1. **Hook stdout must be JSON `{"context": "…"}`.** Plain text is **dropped** — "contributed nothing to the
dispatcher" — and that failure is *identical* to a hook that never ran. Print one line, always, in that shape.
2. **`pre_tool_call` cannot carry context — it only blocks.** Use `pre_llm_call`, which fires every turn, and pair
   it with `--warn-only` so it emits nothing below the threshold. `on_session_start` always reports.
3. **Consent is PER SEAT** — `profiles/<seat>/shell-hooks-allowlist.json`. An unapproved hook **will not fire**:
   `hermes hooks list` shows `✗ not allowlisted`, and `doctor` skips its smoke test with "approve the hook first".
   Two legitimate consent routes: `--accept-hooks` once, or confirm at the TTY prompt. **Do not set
   `hooks_auto_accept`** to skip it — that auto-trusts any hook later added to config, a broader hole than the
   feature closes.
4. **`hooks test` is not proof it fires in a session.** It proves the command runs, exits 0, and parses as the
   wire shape. Report the difference explicitly: *"configured, waiting on approval"* / *"tested, not yet observed
   in a real turn"* — the same discipline as reporting `refresh-prompts` as REQUESTED rather than applied.

## Bands

`<80%` quiet · `≥80%` NEAR CAP · `≥90%` TRIM NOW · `≥100%` AT CAP (the write will be rejected).

- **Band on the exact ratio, not the rounded display.** 2,557/3,200 is 79.9%; a rounded `80` that warns before its
own stated threshold teaches the reader to distrust the number.
- **Name the tight FILE, not just the seat.** "MEMORY NEAR CAP" when `USER.md` is the full one sends the agent to
trim the wrong file. Report the worst file by exact ratio and its headroom in chars.
- **Unreadable prints `UNKNOWN`, never `0%`** — absence of data is not a good score.

## Resolve the seat from the environment, and prove it

**A gauge that names the wrong profile is worse than no gauge: it reports a healthy number for a seat you are not
on.** A gauge resolved the profile from `HERMES_PROFILE` (empty in this runtime), then from cwd, then fell back to
a hardcoded default — so run inside one seat it printed **another seat's** counts and graded them `OK`, while the
seat it ran in was in the NEAR CAP band.

- Prefer **`HERMES_HOME`** (basename is the profile) or derive the seat from the file path being measured
  (`/profiles/([a-z0-9-_]+)/`). Treat `HERMES_PROFILE` as unreliable until proven set in the process.
- **Print the resolved profile in the line** (`[<seat>] …`), so a wrong resolution is visible without comparing
  numbers by hand.
- **Pin `--profile <seat>` in the hook command** while the resolver is unfixed — an explicit argument cannot fall
  back — and report the resolver defect to whoever owns the shared script instead of editing another lane's tool.
- After approval, confirm with `doctor`: it should show `✓ allowlisted` plus a JSON smoke test.
