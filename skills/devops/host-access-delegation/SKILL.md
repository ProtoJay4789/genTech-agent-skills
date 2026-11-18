---
name: host-access-delegation
description: "Use when a task needs host access the agent lacks. Decide whether it is really the user's, then hand it over one line at a time."
version: 2.0.0
category: devops
author: gentech — consolidated 2026-10-17 (absorbed gentech-ops/host-task-handoff)
license: MIT
tags: [host-access, root, delegation, handoff, mobile, ops, runbook]
trigger: "Before filing any task as 'the user's to do' because it appears to need host or root access."
metadata:
  hermes:
    tags: [host-access, root, delegation, handoff, mobile, ops, runbook]
    related_skills:
      - devops/safe-update-restart
      - gentech-ops/hermes-profile-clone-worker
      - source-of-truth-verification
---

# Host Access Delegation — handing a host task to the user

## When to Use

- a task appears to need host root, a container runtime socket, or a provider console
- you are about to write "this one is yours" into a status report or handoff
- the user reports he cannot reach a terminal from where he is (phone, browser)
- **the user says he will "do it later", or that the terminal is hard to reach from his phone** — that is a
  signal the **handoff format** is the problem, not the task
- the same class of root task has come up more than once and you want to stop handing it over

Some work genuinely needs a shell this agent does not have (root on the host, a container runtime socket, a
provider console). Most work that *looks* like it needs one does not. **This skill is the decision and the
handoff protocol** — it exists because getting either wrong costs the user an evening. The default (paste a
runbook and hope) is the version that fails.

> **Consolidation note (2026-10-17):** absorbed `gentech-ops/host-task-handoff`. Same author, same trigger,
> the same rules **renumbered** — a variation of one skill rather than an addition to it. Its unique content
> (the false-receipt rule, the ordering and survey pitfalls) is merged below.

## Rule 1 — Test whether you can do it yourself before filing it as the user's

Before writing "this one is yours, it needs root", **measure the claim**. Most of it is a guess.

- Is there a CLI for this, and does it run from where you are? Try `--help`; it is one call.
- Is the directory writable by the agent's uid? `[ -w <dir> ]` settles it.
- Does the operation need the *host* kernel, or only a file the agent already owns?

Measured: a retired-seat cleanup was filed as the user's work for a day — `hermes profile delete` runs
in-container and the profiles directory is writable by the agent uid. The task never needed him.

**The question is never "does this need root?" It is "does this need root, or do I just think it does?"** A
task you can run is a task you should run. **Separate the two kinds of blocker:** a *write to a running
service* needs root; *a value the user must supply* (a token, a click, a consent) is the user's by nature —
only the second is theirs. **A task handed to a human that the agent could have run is the most common
mis-filing**, and every one you leave in costs the user's trust in the whole list.

## Rule 2 — Never hand over a runbook. One line at a time.

A multi-step document assumes a reader who will hold context, scroll back, and edit commands. Do not assume
that. Assume **a phone, a browser that is not a terminal, and no appetite for it** — that is the reported
condition, and it is the normal one.

**The protocol:**
1. Post **ONE single-line command**, no preamble, no "first do X".
2. The user pastes it, then pastes the **raw output** back into the chat.
3. You read the output and post **the next one line** — or do the rest yourself.

Each message is self-contained. The user never reads a runbook, never edits a command, never holds state.
**The runbook lives on your side, not his.**

- Prefer the one command whose **output you need** over the whole fix. Diagnose, then act.
- Never bundle two commands with `&&` when the second depends on reading the first.
- Never ask him to interpret output. He pastes, you read.

### Label the SURFACE on every line — a shell prompt runs everything

**The user pastes what you write into whatever terminal he is at. If a line is not a shell command, saying
so is part of the command.** Measured: a handoff mixing a contract call, a URL, two form fields and a
placeholder was pasted into bash *four times* — each answering with `syntax error near unexpected token` /
`No such file or directory` / `command not found`. Every one was avoidable by a label.

- **Prefix each item with where it goes:** `SHELL:` / `BROWSER:` / `FORM FIELD:` / `WALLET APP:`. If a
  block contains more than one surface, do not hand it over as one paste — that is Rule 2 with extra steps.
- **A contract call is not a command.** `setAgentURI(1770, "…")` reads as Solidity; it must be marked as
  **a call to make in a wallet/explorer UI**, and the fields listed separately.
- **A URL is never a command.** Say "open this in a browser". A bare URL pasted into a shell returns
  `No such file or directory`, which reads to the user as "the thing is missing."
- **When the user pastes a mixed block into a shell anyway, do not let him retry it.** Name which line was
  a browser step, and re-hand only the part that is actually theirs to run.

### A placeholder must be impossible to paste literally

**If the destination line contains a human-readable instruction, expect it to be copied verbatim.** A
heredoc line reading `<paste the key on THIS line>` arrived in the file intact — 47 chars, matching the
placeholder's own length exactly, because it *looked* like content.

- **Give the placeholder an unmistakable shape** (`__PASTE_KEY_HERE__`) and say "replace this whole line".
- **When a value is missing or wrong-length, print the destination's own dimensions** (`bytes on disk`,
  `trimmed N chars`, `starts with 0x?`) so the diagnosis is arithmetic, not opinion.
- **Recognise the signature:** a length that exactly equals your placeholder's length, or a value starting
  `<`, means the placeholder was copied — say that plainly and kindly rather than implying a bad key.

### An ellipsis is a placeholder too — and the most dangerous one

**Never abbreviate a command with `...`.** A skeleton is read as a complete command by someone who is pasting
rather than reading, and the elision is exactly the part that made it valid. Measured: a `docker run …` line
ended in `...` standing in for the image and every flag; pasted literally it answered
`docker: invalid reference format` — and the container it was meant to recreate had **already been removed by
the line above it**, so a revenue-serving service went down and stayed down.

- **Reconstruct the complete command before sending it** — every flag, the image, the entrypoint. Find it in
  the runbook (`grep -n 'docker run' <runbook>`) rather than writing it from memory.
- **If you cannot find it, hand a LOCATOR, not a shape.** `docker inspect <name>` *before* destroying anything,
  or `history | grep 'docker run'`, gives the complete command from the machine itself.
- **`...` is indistinguishable from a valid argument to a reader.** If a value genuinely must be filled in, use
  an unmistakable token (`__IMAGE_TAG__`) and say which line to replace — the same rule as a value placeholder.

### Never destroy the old thing in the same message as a command you have not proven

**Ordering is a safety property, and a handoff is where it is easiest to get wrong.** `docker rm -f <name>`
followed by a `run` that fails leaves the service down with no rollback — the destructive step succeeded and
the replacement did not.

- **Establish the replacement first, remove second.** Verify the full command resolves (image present, flags
  correct, mount sources exist) before the thing it replaces is gone.
- **If the removal must come first, hand it as its own line after the new one is confirmed running** — never
  bundled above an unproven command.
- **When your own handoff has already taken something down, lead the next message with that fact and the
  recovery**, not with an explanation of the mistake. A service that is down because of our command is the
  first thing the reader needs, and "here is the exact command to restore it" is the whole message.
- **Say what the command will destroy before it is pasted.** A one-line consequence note is cheap; an
  unrecoverable container is not.

### Enforce it with the checker, not with resolve

Prose rules are followed when remembered. This one is cheap to make mechanical — run it on every command
before it leaves the seat:

```bash
python3 scripts/command-readback.py --file <runbook>     # scans only the fenced code blocks
printf '%s\n' "$CMD" | python3 scripts/command-readback.py
python3 scripts/command-readback.py --selftest           # 7 cases, both directions
```

It refuses a bare `...`/`…` used as an argument, `<placeholder>` tokens, and **destructive-before-constructive
ordering** (`rm …` above an unproven `run …`). It warns (without blocking) on a `$VAR` used but never set,
because that command still *runs* — silently wrong, which is worse than one that fails.

- **On a markdown runbook it scans only the fenced blocks.** Prose with angle brackets is not a command, and a
  gate that fires on `<this file>` in a sentence is the gate everyone learns to ignore.
- **The read-back is the check; the paste is the deploy.** Clean exit means the command is runnable as written —
  not that it is the right command. The consequence note above is still yours to write.
- **When it fires, do not soften the rule to make the message pass.** Fix the command: find the real image and
  flags, or hand a locator (`docker inspect <name>`).

## Rule 3 — Name the right surface, and say why

| Surface | Use it for |
|---|---|
| **The chat** | the control plane — *not* a fallback. Most tasks are triggerable from here. |
| **A phone SSH app** (Termius/JuiceSSH) with the host saved | the rare command that genuinely needs host root. |
| **A web dashboard** on a configured port | config and session inspection, browser-shaped. |

**The missing piece is usually a terminal app, not a better browser.** Say it plainly: the credentials the
user already holds were never the blocker — a browser is not a terminal. One install, host saved once, and it
is two taps to a prompt forever. That single step removes the whole complaint.

## Rule 4 — The durable fix: delegate the ABILITY, not the task

Handing over a task costs the user time every time. A **whitelisted host helper** — a small script plus a
unit on the host that watches for a signed command file and runs only pre-approved actions — converts a whole
class of root tasks into agent work after **one** install by the user.

The distinction is the point: *"here is the command"* delegates a task; *"install this once and I will never
need you for this class again"* delegates the ability. **Propose the second whenever the same class has come
up twice** — the one-time install pays for itself on the second task.

## Rule 5 — Name the honestly desktop-bound step instead of forcing it into the protocol

Some steps need a real browser with a working localhost redirect — an OAuth consent, a local-auth flow. On a
headless box that fails, and pasting a failed redirect URL back from a phone is miserable. **Say so, and
assign it to the machine that has a browser** (a desktop agent, a laptop) rather than pretending the one-line
protocol covers it. An honest exception is worth more than a protocol that silently breaks on step three.

**When the user says a machine already exists for a job ("he's our home agent"), check what else that
unlocks.** Owning a desktop step can also mean the credential never has to cross to the server — that is a
design improvement, not just a convenience, and worth saying out loud.

## Rule 6 — Never claim a delivery that did not land

When the handoff channel is down (a dead peer rail, an unwoken seat), a handoff is **filed, not sent**. Say
*"filed in `<path>`; the reader picks it up on its next sync"* — never *"I messaged X."* **A wake that did
not land is a false receipt**, and it is the same class of error as a fabricated measurement.

## Rule 7 — When a third-party UI blocks the handoff, build the one page that does the job

**An explorer's "write contract" tab is not the only way to make a signed call, and it is often the
one that fails.** A browser without the wallet extension, an injected provider the page never sees, a
phone browser that cannot reach the site — all present to the user as *"nothing happens when I click
Connect"*, and he has no way to tell a broken page from his own mistake.

**If two third-party UIs both refuse to hand off, stop shopping and ship the page.** A static
one-page signer is small, verifiable, and removes every dependency between the user and the call:

- **Extension wallet via `window.ethereum`** — one `eth_requestAccounts`, then one contract call.
  Offer to switch/add the chain (`wallet_switchEthereumChain`, falling back to `wallet_addEthereumChain`
  on error `4902`), and load the library from a CDN so the page stays static.
- **REFUSE to sign when the connected address is not the expected one**, and say so on the page.
  **A wrong-but-valid signer produces a successful transaction that changes nothing** — the same
  silent no-op as calling an implementation instead of its proxy.
- **Zero input fields and no key anywhere.** Verify it programmatically
  (`document.querySelectorAll('input').length === 0`) and serve the page `noindex`.
- **Give it a read path beside the write path, and exercise the read from a real browser before
  handing it over.** The read needs no wallet, so it is testable by you alone — and it proves the
  wiring while showing the user the before-state in the same view.
- **Echo the transaction hash with a block-explorer link, then verify the effect in the target
  yourself** — never trust the page's own "confirmed".

**Say what you are actually asking for:** not trust in a page you wrote, but a signature in the
wallet the user already holds, on a page you have shown is read-only until one button is pressed.

## Pitfalls

- **Do NOT bury the item that matters.** Order a user-facing list by **what it unblocks**, highest-leverage
  first — not oldest, not easiest.
- **Do NOT present a survey of options.** Give the recommended path plus the one blocking fact; a menu of
  possibilities reads as evasion rather than as a decision aid.
- **Do not hand over a numbered procedure.** The numbered procedure is for your notes. He gets one line.
- **Do NOT hand over a multi-step sequence.** If a step needs three commands, post the first and wait for the
  output.
- **Do not assume a task needs root because it *sounds* like infrastructure.** Test it; the test is one call,
  and the answer is often no.
- **Do NOT file a task as the user's without checking whether the agent can run it.** See Rule 1.
- **Do NOT report a host task as done from a successful command.** Success is **the user's pasted output
  showing the intended effect** — verify in the target, not in the exit code.
- **Do not solve a transport problem by putting a credential through chat or the vault.** If a step needs to
  move a secret between machines, the fix is a path between the machines, not a synced directory holding the
  key. Keep the credential where the browser is.
- **The command you hand over must resolve on HIS surface, not yours.** The fleet runs containerised while
the user is root on the host, so a path that is correct in the agent's shell can be absent in his:
`sh: cannot open /opt/data/profiles/<seat>/scripts/x.sh: No such file` **on a host where that file plainly
exists in your container** is the signature of a namespace mismatch, not a missing file. **Two fixes, in
order of preference:** (1) **wrap it — `docker exec <container> <cmd>` needs no host path at all**, so verify
the container name (`docker ps`) and hand that; (2) **translate the path before handing it over** (see below).
Never let the user conclude a file is gone because a path from the wrong namespace did not open.

- **⚠️ Do not guess the host path, and do not trust a remembered one — LOCATE IT with a marker file.**
  `grep ' /opt/data ' /proc/mountinfo` is **not reliable** for this: it reports the *device* (`/dev/sda1 … ext4`)
  rather than the host directory, so it names nothing you can hand a user. Measured: two handoffs failed in a
  row — one on a path recalled from old notes (`/root/vaults/<project>/…`, gone since a rebuild) and one on the
  container's own `/opt/data/…` — while the file was present and correct the whole time. **The user pastes,
the command 404s, and the natural reading is "the work doesn't exist."**

  **The reliable technique — let the mark travel, then let the host find it:**
  ```bash
  # 1. AGENT side: drop a uniquely-named file where the handoff needs to land
  echo "locate-$(hostname)" > /opt/data/HOSTPATH-MARKER-$(hostname).txt

  # 2. USER side: one line, its output IS the answer
  sudo find / -name 'HOSTPATH-MARKER-<container-id>.txt' 2>/dev/null

  # 3. The printed directory is the host-side root. Every path you hand over is that prefix + your
  #    container path. Record the mapping the first time; it does not change per task.
  ```
  **Use the container's hostname in the marker name** — it is unique, already known, and makes the file
  self-identifying when several fleets share a host.

- **Verify the translated path with a harmless read before handing over anything destructive.** One `ls -la`
  on the translated path costs the user a paste and prevents handing him a `bash <path>` that cannot open. **A
  handoff command that fails on the first line teaches him the work is broken; a two-step handoff that succeeds
  on the probe then does the job reads as competence.**

- **Never issue the same failing command twice.** If a handed-over path 404s, the next message is a
  **locator**, not another guess: the second failure converts "one bad path" into "this agent doesn't know where
  anything is."
- **Confirm a destructive step is really yours to take before offering to run it** — "I can run this" is a
  claim like any other, and a profile deletion deserves an archive first.
- **A binary missing on HIS host is usually present in a container you already have — borrow it rather than
  asking him to install anything.** `apt install` is a host mutation and a decision he did not ask for.
  Run the tool from the fleet image with the needed paths mounted and the host network:
  ```bash
  docker run --rm --network host \
    -v /root/<secret-file>:/key:ro \
    -v /docker/hermes-agent-XXXX/data/profiles/<seat>/scripts:/s:ro \
    -v /docker/hermes-agent-XXXX/data/tools/<libdir>:/bl:ro \
    --entrypoint node <image:tag> /s/<script>.mjs --key /key --dry-run
  ```
  **`--entrypoint <binary>` is the whole trick** — without it the image's own entrypoint runs instead of your
  command, and the container appears to hang or do the wrong thing. **Mount the secret read-only** (`:ro`),
  and note that the user's `/root` is *not* your `/root`: a bind mount is how his file reaches the container,
  and it is why you cannot read it yourself (which is the point).
- **A missing binary is a fact about the host, not a durable rule about the tool** — do not record it as
  "X does not work here". Record the container invocation that worked.
- **Prefer the surface where a secret never touches the server.** When a browser extension or a device the
  user already owns can do the job, that is not a fallback — it is the better answer, and it should be the
  recommendation even when a server-side path is technically available.
