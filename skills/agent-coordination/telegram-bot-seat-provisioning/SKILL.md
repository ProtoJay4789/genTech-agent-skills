---
name: telegram-bot-seat-provisioning
description: "Use when wiring a new Telegram agent seat."
version: 1.0.0
author: gentech
tags: [telegram, onboarding, profile, bot-token, verification, allowlist]
---

# Provisioning a Telegram agent seat

## When to Use
Adding a new agent (or replacing a retired one) that must **hear and answer in a Telegram room**:
create the profile, wire its own bot, prove it is live. Six steps, in this order — each exists
because skipping it produced a false "done".

## The order matters

1. **Verify the token before anything else.** `getMe` costs one call and reports id + username + name:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getMe"    # -> ok:true, result.username, result.first_name
   ```
   **An id is not a token.** A numeric id names a bot; a token (`NNNNNNNNN:AA…`) authenticates one.
   Ids get mistaken for tokens — if you were handed a bare number, say so plainly and ask for the
   BotFather token; there is nothing to install otherwise. Expect the **username to differ from the
   display name** — read both, or you will wire the wrong bot.
2. **Create the seat's profile.**
   ```bash
   hermes profile create <name> --clone --clone-from <source> --description "<role>"
   ```
   `--clone` (light) copies config, `.env`, SOUL, skills and memories. **Never `--clone-all`** — it drags
   the multi-GB `home/` tree of tool caches and stalls or half-finishes. Messaging channels are
   deliberately NOT cloned, which is correct: two gateways on one token fight (409).
3. **Give the seat its OWN SOUL.** The clone carries the SOURCE agent's `SOUL.md`, so a fresh seat wakes up
   believing it is the source agent. Overwrite `<profile>/SOUL.md` from the canonical vault copy
   (`00-System/agent-profiles/<name>/SOUL.md`) and read line 1 back to confirm.
4. **Wire its own `.env`, never by hand.** Use `scripts/wire-profile-bot.py <profile> <token_file>
   <home_channel> <allowed_csv>` (ships with this skill). Set three keys: `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_HOME_CHANNEL`, `TELEGRAM_ALLOWED_USERS`. Store the token at
   `/opt/data/.bot-tokens/<name>.token`, directory `700`, file `600`, and never echo its value — report it
   by sha256 fingerprint if you must confirm it landed.
   **Include every human who must be heard in that room**, not just the owner — a learner or collaborator the
   seat is meant to serve is silently dropped if their id is absent.

   **Three keys is the wiring floor, not the routing.** Who may run slash commands is a separate
   axis: `allow_admin_from` / `group_allow_admin_from` for admins and `user_allowed_commands` for the
   floor (everyone else gets only `help` and `whoami`). No admin list set = gating OFF and every
   allowed user is an admin. If a non-owner shares the room, name the floor at provisioning time
   rather than discovering it later — see `telegram-group-routing`.

   **`TELEGRAM_HOME_CHANNEL` earns its keep only when some delivery names no target.** If every cron
   job in the seat carries an explicit `origin` chat id, the home channel is a convenience, not a
   requirement — and leaving it unset produces a "No home channel is set" notice on the first message
   of every new session. Set it with `/sethome` in the room, or accept the nag knowingly.
5. **Prove the adapter is up.** Check the gateway log, not the config:
   ```bash
   grep -h "telegram connected" /opt/data/logs/gateway.log | tail
   hermes profile list      # Gateway: running
   ```
   On a multiplexed host (no `systemctl`, one supervising gateway serving all profiles) writing the token
   is enough — the multiplexer re-scans on `.env` change. A profile can read `Gateway: running` while
   reporting `(0 adapter(s) connected)` in the reconcile line, which means **it is not hearing Telegram**.
   If you wrote the token after the profile was registered, `touch <profile>/.env` and re-check.
   **Do not call `getUpdates` on the token to "test" it** — the gateway long-polls the same token and you
   will steal or conflict its updates.
6. **Prove the seat can SEE its room** — the step most often skipped:
   ```python
   getChat(chat_id=<id>)                                            # -> title, type
   getChatMember(chat_id=<id>, user_id=<bot's OWN id from getMe>)    # -> status: administrator/member
   ```
   `chat not found` means the id is wrong **or** the bot is not a member. **`getChatMember` wants the
   bot's user id — passing the chat's id returns `Bad Request: invalid user_id specified`.**

## Home channel — a delivery default, not a routing fact

`TELEGRAM_HOME_CHANNEL` is where cron results and cross-platform notices go **when a job names no
target**. It is not what lets the bot hear a room — that is membership plus the routing gates.

- **Absent home channel = a nag on every new session.** `gateway/run_turn_prepare.py` posts the
  `no_home_channel` notice when a fresh session starts and the key is unset in the profile secret
  scope and `config.yaml`. The notice reappearing is evidence of an unset value — not of a broken
  seat, and not of damage from an update.
- **Explicit `origin` chat ids are stronger than a home channel.** Audit before "fixing" anything:
  ```python
  import json, collections
  jobs = json.load(open("/opt/data/profiles/<seat>/cron/jobs.json"))["jobs"]
  print(collections.Counter((j.get("origin") or {}).get("chat_id") for j in jobs))
  ```
  Jobs carrying their own chat id deliver regardless; only a job created *without* a target needs
  the home channel. Reporting "results are fine anyway" is the honest answer when the counts cover
  every job.
- **The fix is one command in the target room** — `/sethome` — never a hand-edited `.env`. It saves
  chat id, display name and thread for that platform, per profile.
- **The line is usually already there, commented.** `# TELEGRAM_HOME_CHANNEL=` in the template is not
  a missing feature; anchor any edit on `^KEY=` or you will edit the comment.
- **Confirm which bot is asking.** `getMe` on the profile token and match the id — a delivery notice
  can arrive in a room a different seat's gateway is answering, and the id in it names the bot.
- **Home channel is required for handoff threads.** Startup handoff delivery raises "no home channel
  configured; run /sethome on the desired chat first" — so a seat with none cannot receive those.

## A seat that WAS live and went silent — discriminate before you rotate

**A dead token and an unreachable bot do not look the same, and only one of them is fixed by BotFather.** Read
the response *shape* before replacing anything, because rotating a credential that is not the fault burns the
user's time and hides the real cause.

Run the same call against three inputs and compare **both** the status and the time:

```bash
for t in "<seat-token>" "$BOGUS"; do                       # $BOGUS = any well-formed junk token
  curl -s -o /dev/null -w "$t HTTP=%{http_code} %{time_total}s\n" --max-time 20 \
    "https://api.telegram.org/bot$t/getMe"
 done
curl -s -o /dev/null -w "root HTTP=%{http_code} %{time_total}s\n" --max-time 15 https://api.telegram.org/
```

| shape | means | next move |
|---|---|---|
| **`200` in well under a second** | token valid, bot reachable | the fault is elsewhere — the gateway, not the credential |
| **`401` in well under a second** | token invalid — Telegram read it and refused it | rotate it; this is the case BotFather fixes |
| **`000` after 15–45 s (a hang)** | **not a credential verdict** — nothing answered | **do not rotate yet**; grep the seat's own log, then discriminate the network path |

**A `401` is an ANSWER; a hang is an ABSENCE.** Authentication never takes 45 seconds — Telegram evaluates the
token before doing any work. So a timeout is the wrong layer entirely: either the bot is restricted at the
provider, or something on this host is intercepting that specific id.

> **⚠️ A curl hang does NOT mean the client has no verdict — read the seat's log FIRST.** The hang is what
> *your* request sees; the gateway's own adapter may already have recorded the answer in plain words. Measured:
> raw `getMe` timed out at 20 s while the seat log held `ERROR [Telegram] Failed to connect to Telegram: The
> token '869…'` — a **token rejection**, recorded minutes earlier. Reading the transport and theorising about
> DNS, TLS, egress and provider restriction cost several exchanges; one search of the seat log would have named
> it immediately. **Order: seat log → curl shape → network split.** The log is the cheapest vantage and the only
> one that quotes the error verbatim.

**The decisive test: a FRESH token must be tried before concluding anything about credentials.** If a
token just issued by BotFather fails in the identical shape, the credential is exonerated in one step.
Measured: a seat that had answered normally hours earlier began timing out; a newly generated token for the
same bot timed out in exactly the same way, at the same 20 s ceiling. **Two different tokens, one failure
shape, means the token was never the variable** — and continuing to regenerate is a loop, not a fix.

**Then split provider from host, which is the only remaining question:**

- Reproduce the same `getMe` from a **different network** (the user's laptop, any other box). Answers there and
  hangs here → **this host's egress**. Hangs there too → **the bot itself**, and only BotFather can act.
- A bare `https://api.telegram.org/` returning `302` while the token URL hangs is evidence the **host reaches
the API** — it narrows the fault to the request carrying that token, not to DNS, TLS or the network in general.
- **Do not install a token you have not seen answer.** Writing it into `.env` and restarting converts a clean
  "cannot connect" into a seat that fails differently and looks wired.

**A silent seat is not an idle seat.** Grep its own log before theorising about the agent:
```bash
 grep -E 'Failed to connect|Disconnected from Telegram|delivered to' <profile>/logs/agent.log | tail
```
An 8/8 exhausted reconnect loop with `Failed to connect … Timed out` means it **cannot receive**, so the
user's unanswered message is a delivery problem, never the agent ignoring him. Say that plainly and early —
the reader assumes silence is a choice.

**A gateway that comes back on its own needs no restart command from you — read the log before handing one over.**
Measured: a supervisor restarted the seat and it connected (`Connected to Telegram (polling mode)`, then
`set_my_commands OK`) without the operator running anything. A restart command suggested as the next step was
both unnecessary **and** named a binary absent from the host shell. **Confirm the current state before
prescribing the fix; a command for an already-healed service is noise that erodes the next instruction.**

## When the bot cannot be revived — rebuild the seat around a NEW bot ID

**Once a fresh BotFather token for the same bot id fails in the same shape, the bot is dead at the provider
and no credential work will bring it back.** Replace the bot, keep the seat.

> **A seat is not its bot. The bot is a transport adapter; the seat is `SOUL.md` + `memories/` + `config.yaml`
> + skills + `cron/jobs.json`.** Every platform (Telegram, WhatsApp, Discord) can revoke an app or disable a
> bot without notice, so any seat whose identity lives only in a platform account is one policy decision from
> being gone. Provision every seat as re-provisionable from its own files.

**Do not rebuild by copying the profile directory.** It is mostly machine state, and carrying it into a fresh
bot carries caches and stale binaries and calls that continuity:

```
~430 MB  home/       tool caches, runtimes — rebuildable
 ~38 MB  bin/        installed binaries — rebuildable
 ~33 MB  cache/      rebuildable
 ~42 MB  state.db    conversation history — OPTIONAL, the only large file worth choosing
 ~21 MB  skills/     do NOT copy verbatim: the canon is the skills distribution; re-promote, then diff
```

**The capture set — five things, all on our disk, not the platform's:**

| carry | why |
|---|---|
| `SOUL.md` | identity, voice, lane |
| `memories/MEMORY.md` + `memories/USER.md` | everything it has learned |
| `config.yaml` | rail, model, toolset |
| `cron/jobs.json` | its jobs — and the delivery targets they carry |
| skills | **re-promote from the distribution**, then diff against the old seat for local edits |
| `state.db` (+`-wal`) | optional searchable history; stop the gateway first so it is not mid-write |

**Order — nothing is deleted until the replacement is proven.**

1. **Capture while the old seat still exists.** `hermes -p <seat> gateway stop` so `state.db` is quiescent,
   then copy the capture set to a dated snapshot directory outside the profile. Record every job id **and its
   delivery target** — a successor that silently re-points a job's room has not inherited it.
2. **The user creates a NEW BOT in BotFather (`/newbot`) — not a new token.** A reissued token keeps the dead
   id. Write down the new bot id.
3. **Prove the new bot before wiring anything:** `getMe` must return **200 in well under a second**. If it
   hangs, stop — that is the same defect on a fresh identity and no configuration fixes it.
4. **Build the successor**: install the token into the **profile's own `.env`** (mode 600, `^KEY=` anchored),
   restore the capture set, re-promote skills, restore or recreate the jobs.
5. **Prove it before retiring:** `getMe` 200 → one real message **seen in the room** → the scheduler's own
   `delivered to <platform>:<chat_id>` line in the seat log for each job.
6. **Retire reversibly**: stop the old gateway, mark the old profile `retired-bot-blocked` with the date, and
   **keep the snapshot**. Deleting the directory on day one throws away the rollback for disk you already own.

**Add the new bot to every room the seat serves before calling it live** — a successor wired to one room is a
regression the old seat did not have.

## Always-on rules

- **"Profile exists + token in `.env`" is not live.** Live = `✓ telegram connected (profile: <name>)` in
  the gateway log **and** `getChat` shows the bot inside its room. Report the weaker state honestly rather
  than letting "wired" imply "working".
- **A documented value is not a measured value.** Chat ids get copied between notes, routing tables and
  SOULs until they look verified. Test every id with `getChat` before building on it, and treat the set of
  ids the gateway has actually received from as the truth set:
  `grep -o 'chat=-[0-9]*' /opt/data/logs/gateway.log | sort | uniq -c` — **an id with zero inbound has never
  been real.** When you find you propagated a bad id yourself, correct it everywhere and say so.
- **Anchor every `.env` edit on `^KEY=`.** These files carry a COMMENTED template line
  (`# TELEGRAM_ALLOWED_USERS=`) far above the live one; a bare substring match edits the comment, exits 0,
  and wires nothing.
- **Never type a token into a shell command inline** — it trips the parser blocklist. Read it from the
  mode-600 file inside a script.
- **A token pasted in chat is exposed.** Install it, then tell the user it persists beyond the message
  (token-shaped strings survive in `state.db`, so "delete the message" is not erasure). Recommend
  `BotFather` → `/revoke` if they want it rotated, and never repeat the value back.
- **The vault record is intent; the allow-list is fact.** After any rebuild (re-image, wipe, re-clone,
  `.env` regeneration) a previously-added id can vanish while a progress note still claims "access
  enabled". Re-verify the live line for **every** profile serving a room the person is in.

## Pitfalls

- **Partial verification reads as success.** Reading a file back after editing it is the check that catches
  the commented-line bug, the wrong-bot wiring and the missed allow-list. Do it every time.
- **`0 adapter(s) connected` looks healthy in `profile list`** — only the reconcile line and the
  `telegram connected` line distinguish them.
- **The seat's first real inbound is the acceptance test.** Columns in a table prove wiring; a message
  from the room proves the room. Never call a seat live before that, and say so when it has not happened.

## Supporting files
- `scripts/wire-profile-bot.py` — token-safe, `^KEY=`-anchored wiring of a profile's Telegram keys.
