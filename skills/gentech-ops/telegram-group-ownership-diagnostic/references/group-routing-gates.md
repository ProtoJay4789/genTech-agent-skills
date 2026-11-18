# Telegram group routing gates — where they live and how to read them

Depth for "the bot is in the room but did not answer". Membership (`getChat` → `ok:true`) proves the
message *reached* us; these gates decide whether it *dispatched*.

## Source locations (installed engine)

| File | What it holds |
|---|---|
| `plugins/platforms/telegram/adapter.py` | the `_telegram_*` gate readers, `_should_process_message`, `_should_observe_unmentioned_group_message`, `_bot_sender_suppressed` |
| `plugins/platforms/telegram/telegram_context.py` | `group_reply_expected`, `group_trigger_text`, `group_identity_prompt` — the reply-eligibility and mention-stripping logic |
| `cli-config.yaml.example` (`platforms.telegram.extra`) | the documented shape of every knob, with comments |
| `hermes_cli/config_defaults.py` | defaults for the whole config surface |
| `gateway/run_turn_prepare.py` | the once-per-session `no_home_channel` notice (delivery, not routing) |

## Gates, defaults, effect

| Key (env) | Default | Effect when set |
|---|---|---|
| `exclusive_bot_mentions` (`TELEGRAM_EXCLUSIVE_BOT_MENTIONS`) | `true` | An @mention of a *sibling* bot excludes us from this message |
| `bots_require_mention` (`TELEGRAM_BOTS_REQUIRE_MENTION`) | `false` | Another bot must @mention us; its quote-replies are suppressed |
| `require_mention` (`TELEGRAM_REQUIRE_MENTION`) | `false` | Plain group chatter needs an @handle, reply, or wake word |
| `mention_patterns` (`TELEGRAM_MENTION_PATTERNS`) | unset | JSON regex list, compiled at adapter load |
| `free_response_chats` (`TELEGRAM_FREE_RESPONSE_CHATS`) | unset | Every message dispatches in these chats |
| `free_response_topics` (`TELEGRAM_FREE_RESPONSE_TOPICS`) | unset | `<chat_id>:<thread_id>` entries; General = `1` |
| `allowed_chats` (`TELEGRAM_ALLOWED_CHATS`) | unset | Non-empty ⇒ other chats need `guest_mode` + @mention |
| `allowed_topics` (`TELEGRAM_ALLOWED_TOPICS`) | unset | Non-empty ⇒ other topics are ignored |
| `ignored_threads` (`TELEGRAM_IGNORED_THREADS`) | unset | Thread ids to skip entirely |
| `observe_unmentioned_group_messages` (`TELEGRAM_OBSERVE_UNMENTIONED_GROUP_MESSAGES`) | `false` | Store unaddressed chatter as context, no reply |
| `guest_mode` (`TELEGRAM_GUEST_MODE`) | `false` | Explicit @mentions from non-allowlisted groups get through |

`group_sessions_per_user` (top-level config, default `true`) is adjacent but different: it decides one
session per participant in a room vs one shared "room brain".

## Read-out: what is this seat actually set to?

```bash
# knobs set in the profile (the live ones; template lines start with '#')
grep -E '^TELEGRAM_[A-Z_]+=' /opt/data/profiles/<seat>/.env | sed 's/=.*/=<set>/'
grep -n -A20 'telegram:' /opt/data/profiles/<seat>/config.yaml
```

A key absent from both is running at the default in the table above. Judge a room's behaviour from the
**effective** value, not from what a note or SOUL claims.

## Gate order when a message seems ignored

1. Is the bot a member? `getChat` → `ok:true`, else stop here.
2. Did the message arrive? inbound lines in `gateway.log`; an id with zero inbound was never real.
3. Does the text @mention a sibling? `exclusive_bot_mentions` excludes us — and `group_trigger_text`
   deliberately leaves our handle in place when others are named too.
4. Was it sent by another bot without naming us? `bots_require_mention` suppresses it silently; the
   message is still stored as observed context if observation is on.
5. Is the chat/topic out of scope? `allowed_chats`, `allowed_topics`, `ignored_threads`.
6. Only now consider the gateway itself (stale code, flood control, stuck tool).

## Why the loop breakers exist

Two bots in one room will otherwise answer each other's replies indefinitely — each reply is a new
message, each message is a new trigger. `bots_require_mention` breaks the loop at the *sender* check;
`exclusive_bot_mentions` breaks it at the *addressee* check. Leaving both at defaults is usually right.

## Reporting

State the effective value of each gate that explains the silence, and name the one key that would change
the behaviour. "We are not using it" (at default) is a complete answer; a list of available knobs is not.
