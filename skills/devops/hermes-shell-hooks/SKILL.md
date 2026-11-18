---
name: hermes-shell-hooks
description: "Use when wiring a shell hook or memory gauge in Hermes."
version: 1.0.1
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [hermes, hooks, config, memory, observability]
    related_skills: [hermes-agent, agent-load-path-audit, hermes-memory-and-restart]
---

# Hermes shell hooks

## When to Use

- A warning or state line must reach the **agent** mid-task, not just a log (memory fill, quota, rate state).
- A lifecycle event must **gate** an action (block a tool call, veto a turn).
- A configured hook fires but "contributes nothing" and you need to know why.
- `hermes hooks list` shows `✗ not allowlisted` and the feature looks dead.

Shell hooks run a script at lifecycle events. Use them for things that must be visible to the AGENT
(an injected warning) or that must gate an action.

## The wire contract — the part that wastes an hour if you miss it

- **stdout must be JSON `{"context": "..."}`.** Plain text is parsed, fails, and logs
  *"contributed nothing to the dispatcher"* — the hook runs, exits 0, and does nothing.
  `hermes hooks test <event>` prints `parsed: <none>` for this exact failure, so always read that line,
  not just `exit=0`.
- **`pre_tool_call` cannot carry context.** Its parser only understands `block` / `modify` / `approve`.
  To inject information every turn, use **`pre_llm_call`** (which falls back to context parsing).
- **`on_session_start` fires once**, so a reading taken there ages across a long session. Pair it with a
  per-turn hook for anything time-sensitive.
- Events seen: `on_session_start`, `pre_llm_call`, `pre_tool_call`, `post_tool_call`, `pre_verify`,
  `on_session_end`, `on_session_finalize`, `on_session_reset`, `pre_api_request`, `post_api_request`.
  `hermes hooks test <event>` fires synthetic payloads so you can inspect the real stdin shape.

## Consent is per seat, and the hook is silent until it is given

- `hermes hooks list` → `✗ not allowlisted` means **the hook will not fire at runtime**.
- **`hermes hooks test` runs the script ANYWAY — a passing test is not proof the hook is live.** It bypasses
  consent to show you the wire shape. So `parsed: {...}` from `test` plus `not allowlisted` from `list` is a
  coherent, common state: **the code is right and the feature is off.** Do not report "hooks are wired" off a test
  result; the pair (`test` parsed + `list` allowlisted) is the only combination that means armed.
- Allowlist lives at `profiles/<seat>/shell-hooks-allowlist.json` (HERMES_HOME resolves to the profile dir),
  so **one seat's approval does not arm another's**.
- Approve via the **TTY prompt** (per hook) or `--accept-hooks` on a run (approves whatever is in config).
- **Do not set `hooks_auto_accept: true` to skip it.** It auto-trusts any hook added later, forever —
  a broader hole than most features close. An agent approving the security control that guards it is
  not an approval.
- `hermes hooks doctor` is the real check: exec bit, allowlist, mtime drift, JSON smoke test, timing.

## Config edits: use the CLI, not a file write

`patch` and `write_file` **refuse** `profiles/<seat>/config.yaml` (security guard). Change it with:

```bash
hermes config set --force hooks '{"on_session_start":[{"command":"/path/hook.py --hook","timeout":10}]}'
```

`--force` is required to replace a structured section; a dotted path only sets leaf keys.

**There is no `--profile` flag.** To configure ANOTHER seat, point `HERMES_HOME` at its profile dir:

```bash
HERMES_HOME=/opt/data/profiles/<seat> hermes config set model.provider <provider>
HERMES_HOME=/opt/data/profiles/<seat> hermes config get model.provider   # verify per seat, never assume
```

**Verify per seat after writing** — a loop that reports success and a loop that actually landed are different
claims, and fleet alignment means every seat, not the one you were sitting in.

## Memory gauge — the worked example

`/opt/data/scripts/memory-gauge.py` prints how full a seat's `MEMORY.md` / `USER.md` are, because a cap
learned by having a write rejected is learned too late.

- Bands on the **exact ratio, never the rounded percent**: 2,557/3,200 (79.9%) must stay silent while
  2,560 (80.0%) warns — warning below your own stated threshold teaches the reader to distrust it.
- **Name the tight file.** "MEMORY near cap" when `USER.md` is the full one sends the agent to trim the
  wrong file.
- An unreadable file prints **UNKNOWN**, never 0%.
- `--hook` emits the wire shape; `--warn-only` silences it below the band so a per-turn hook is not noise;
  no `--quiet` on the session-start hook — a gauge the agent never sees is not a gauge.

## Verification that actually counts

1. `hermes hooks test <event>` → read `parsed (Hermes wire shape): {...}`, not `exit=0`.
2. `hermes hooks list` → `✓ allowlisted`.
3. **One real session printing the line.** A config that looks right and a hook that fires are different
   claims; until a turn shows the output, say "wired, not armed".
