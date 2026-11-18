---
name: telegram-group-ownership-diagnostic
description: Diagnose "agent X isn't replying in group Y" across a multi-profile Hermes fleet. Determines which bot token actually owns a Telegram group before touching gateway recovery, and distinguishes bot-membership gaps from stuck-tool errors and flood-control throttling.
category: devops
tags: [telegram, gateway, multi-agent, diagnostic, group]
---

# Telegram Group Ownership Diagnostic

When a user reports "agent X isn't replying in group Y", the gateway is often **fine** — the bot wired to that profile may simply not be a member of that group, so it never receives the messages. This is the #1 false-alarm for "gateway down" in a multi-profile setup.

## Core insight

Multiple profiles can have routing context for the same group in their `config.yaml` (`channel_prompts`), but only **ONE bot token is actually a member** of that group. A profile can be configured to route to a group without its bot being in it — so messages there never reach it.

## Diagnostic order (do this BEFORE gateway recovery)

1. **Determine which bot owns the group.** For each profile, check membership:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<group_id>"
   ```
   - `ok:true` → that bot owns the group (it can see + send)
   - `ok:false` → that bot is NOT a member; it can't see the messages
   - `"Forbidden: bot was kicked"` → banned, re-invite
   - `"Bad Request: chat not found"` → wrong chat ID or never added

2. **Cross-check the owning profile's home channel.** `grep TELEGRAM_HOME_CHANNEL <profile>/.env` — the profile whose home channel matches the group is the intended owner.

3. **Only then check the owning bot's gateway** — process (`ps aux | grep "gateway run"`), log freshness, and the group's inbound/response lines in `gateway.log`.

## Multi-bot rooms — the routing gates decide who answers

In a shared room, silence is often **correct**: the message was addressed elsewhere, or a sibling bot
was named. Before treating it as a fault, read the gates — all of them live in
`plugins/platforms/telegram/adapter.py` as `_extra_bool("<key>", "TELEGRAM_<KEY>", "<default>")`.

- `exclusive_bot_mentions` (default **true**) — if the text @-mentions another bot and not us, it is
  dropped for us. The most common false alarm in a multi-agent room.
- `bots_require_mention` — another *bot's* message needs an explicit @mention of us; its quote-reply
  or plain chatter is suppressed, which is what stops two bots answering each other forever. Human
  replies are unaffected.
- `require_mention` — whether plain group chatter reaches us at all (default false).
- `mention_patterns` — regex wake words, an alternative to the @handle.
- `free_response_chats` / `free_response_topics` — chats, or `<chat_id>:<thread_id>` pairs, where
  every message dispatches (a forum's General topic is thread `1`). Also the way to serve one topic
  in a room we otherwise ignore.
- `allowed_chats` / `allowed_topics` / `ignored_threads` — membership and scope filters.
- `observe_unmentioned_group_messages` (default **false**) — store unaddressed chatter as context
  without replying; observation is chat/topic-scoped and needs an explicit chat allowlist.

Gate table, source lines and read-out commands: `references/group-routing-gates.md`.

**In-room routing is not the handoff mesh.** An `@seat` decides *who speaks next*; it is not durable,
does not survive a machine being off, and leaves no record. Work still moves by vault handoff, and a
mention or `hermes peer dm` only wakes the seat.

## Stuck reply ≠ dead gateway

A message received but never answered is usually one of:
- **Mid-turn tool error** — an MCP call failed mid-response (e.g. `get_execution_status not found`, `404 Execution not found`). The agent errored out before producing a reply. Check `gateway.log` for the tool error near the inbound timestamp.
- **Telegram flood control** — `Flood control exceeded. Retry in N seconds` in `gateway.log`. Sends are throttled; replies delay or drop. Restart the gateway to reset retry state if stuck >10 min.
- **Session compression** — a long session auto-compressing mid-turn can delay the reply.
- **Stale code after Hermes update** — the gateway process has been running since before an update and now crashes on every inbound message with an `ImportError` or `AttributeError` from a module that changed (e.g. `cannot import name 'slash_confirm' from 'tools'`, `No module named 'tools.send_message_tool'`, `No module named 'run_agent'`). The gateway receives the message and logs `Flushing text batch` followed immediately by the import error — no reply is ever sent. Fix: restart the gateway so it picks up the current installed code. Check gateway start time with `ps -o lstart= -p <pid>` — if it predates the last `hermes update`, this is the cause.

## A token that HANGS is not a bad token — the bot is unreachable, so the messages are undelivered

When the seat is silent, the gateway log will show the *symptom*: repeated `Connecting to Telegram (attempt
N/8)`, then `Failed to connect to Telegram: Timed out`, then a slower `Secondary telegram reconnect retry in
Ns`. **That log cannot tell you why** — it records that the connection failed, not whether the credential, the
bot, or the network is at fault. Probe the token itself.

**Any single-token probe is unreadable — the answer only means something next to two CONTROLS.** Run all
three against the same endpoint in the same pass:

```bash
# 1 · control A: a known-good token from another profile  → expects 200, ~0.3s
# 2 · control B: a deliberately bogus token               → expects 401, ~0.3s
# 3 · the suspect token                                   → ???
curl -s -o /dev/null -w 'HTTP=%{http_code} time=%{time_total}s\n' --max-time 25 "https://api.telegram.org/bot$TOK/getMe"
```

| observation | meaning |
|---|---|
| good token → `200`, fast | Telegram is reachable and the endpoint is healthy |
| bogus token → `401`, fast | the endpoint **answers bad credentials quickly** — latency is not the problem |
| suspect token → `000`, hangs to the timeout | **Telegram will not answer THAT token.** Not malformed (a malformed one returns 401) and not a network fault (the controls disprove it) |

**Read the pair, never the single value.** `000` alone is "network" if you did not run the controls; `000`
next to a fast `401` for a bogus token is a credential/bot verdict. **Never report "the token is invalid" from
a hang** — invalid returns 401 — **and never report "gateway down"**: the gateway is running fine and retrying a
connection it cannot make.

**What to tell the user: their messages are undelivered, not ignored.** A seat whose token is refused cannot
receive, so silence is not a colleague choosing not to answer — and saying so plainly is the difference between
"Arthur is dropping the ball" and "Arthur is cut off".

**Bound the outage before blaming any recent change.** Find the last successful send and the first total
failure; the window between them is the outage, and it usually starts *after* the last thing you did.
```bash
grep -E 'Sending response.*to -' <profile>/logs/agent.log | tail -2      # last known-good send
grep -E 'Failed to connect to Telegram' <profile>/logs/agent.log | head -1  # start of the failure block
```

**The human-gated part, and the test that splits the two causes:** the numeric prefix of the token is the bot
id, and `https://t.me/bot<bot_id>` still renders **200** even when the API will not answer — proving the bot
still exists. So:

- **exists but unanswered** → the bot is restricted/blocked at Telegram's end (BotFather → `/mybots`), or the
token was **regenerated elsewhere** and this `.env` holds the superseded one.
- **no page at all** → the bot is deleted.

The fix is a human action in both branches — an agent cannot mint or restore a bot token. Report which branch
the evidence supports and stop; do not loop restarts against a credential that is not being accepted.

## Multiple bots per account — identify the LIVE one first

A fleet profile can have several Telegram bots (main agent bot, a "Treasury" desk bot, a gizmo bot, etc.), each with its own token. The token that actually owns a group is the one that answers `getChat` with `ok:true`. Before diagnosing a "kicked" bot:

1. **Find the live token** — `grep -E "^TELEGRAM_BOT_TOKEN=" ~/.hermes/profiles/<profile>/.env` (it lives in the profile `.env`, NOT always in `/root/.env` or `.bashrc`). Don't assume a token from a backup or a switch script is current.
2. **Identify each bot** — `curl getMe` returns `first_name` + `username`. Match that handle to the group's membership.
3. **Probe every group you care about with the live bot** in one pass, so you see the full blast radius (a kick is rarely isolated to one group).

## Confirmed case (Aug 10, 2026): live bot kicked from TWO groups

`@ProtoJaybot` (id 8710327768, the live Gentech bot) was kicked from **Labs** (`-1003872552815`) AND **Treasury** (`-1002916759037`) — which is why Gizmo couldn't run the Opportunity Scanner and those group-delivery crons kept failing with `Forbidden: bot was kicked from the supergroup chat`. HQ and Entertainment were still `ok:true`. Root cause: group admin removal / privacy-settings change. **The fix is human-gated** — a kicked bot cannot rejoin itself; a group admin must re-add `@ProtoJaybot` via the members list. After the user re-adds it, re-run the diagnostic to confirm `ok:true` before declaring it resolved. Note: the Treasury group had some crons "migrated to gentech-treasury profile" (a separate bot, `@GentechDeskbot` id 8981389550) — always check whether a group is intentionally served by a different bot before flagging a kick.

## Confirmed case (Aug 9, 2026)

Labs and Treasury groups "not replying" simultaneously — both gateways had been running since 00:36 and were crashing on every inbound message with `cannot import name 'slash_confirm' from 'tools'`. The underlying Hermes installation had been updated but the gateways were never restarted, so they held stale code in memory. The main Gentech gateway (started 54min later after the update completed) was fine. Restarting both gateways resolved it. Additionally, the Treasury group had a double-gateway (systemd Restart=on-failure spawned a second instance alongside a manual nohup restart), amplifying Telegram rate-limiting.

## Confirmed case (Aug 7, 2026)

Entertainment group "not replying" was a **combination**: the bot that owned the group was processing messages, but a Vanito message was stuck on a KeeperHub MCP tool error (`get_execution_status not found`), compounded by Telegram flood-control throttling. The gateway was healthy the whole time. Restarting the gateway (to clear the stuck session + flood state) was the fix — not a gateway outage.

## Pitfalls

- Don't restart gateways before confirming which bot owns the group — you may restart the wrong profile.
- A profile with `channel_prompts` for a group in config.yaml does NOT mean its bot is in that group.
- Bot username/handle is cosmetic; chat IDs + membership are what matter.

## Related
- **A member who was removed cannot rejoin, links "don't work", or a new collaborator's messages
  never arrive** → `agent-kit/telegram-member-recovery` (removal bans; `can_invite_users` mints links
  but only `can_restrict_members` lifts a ban; the allowlist is the other half of the fix).
