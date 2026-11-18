# Proving a fallback actually fails over

A configured `fallback_providers` list is a **claim**. Until a request is made against a broken primary and a
lower rung answers, all you know is that a config key holds JSON. This is the drill that converts it into a
receipt — cheap, reversible, and it touches no live seat.

## Why a reply is not the proof

`hermes -z 'say OK'` returns `OK` whether the primary served it or the fallback did. **The reply is the same
string in both worlds.** The only evidence is the log line naming the provider that produced the completion.
So the drill always ends by reading `profiles/<scratch>/logs/agent.log`, never by trusting the text.

## The drill

```bash
# 1 · a throwaway profile — a COPY, never a live seat
cp -r profiles/<seat> profiles/railfail        # or: copy .env + config.yaml only
chmod 600 profiles/railfail/.env

# 2 · mute every channel so the scratch seat cannot speak to the world
#     blank TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, API_SERVER_ENABLED, API_SERVER_KEY

# 3 · break ONLY the scratch seat's primary key (live seats untouched)
sed -i 's/^PRIMARY_KEY_ENV=.*/PRIMARY_KEY_ENV=sk-deliberately-invalid/' profiles/railfail/.env

# 4 · one real turn
HERMES_HOME=/opt/data/profiles/railfail hermes -z 'Reply with exactly: FALLBACK-OK'

# 5 · THE RECEIPT — which provider produced it
grep -E 'provider=|API call #|Fallback' profiles/railfail/logs/agent.log | tail -12

# 6 · clean up: restore the key, delete the profile
rm -rf profiles/railfail
```

**Wipe the scratch seat's channel credentials in step 2 before the broken-key turn in step 3.** A test profile
that can still reach Telegram is a live agent with a wrong key attached to it — it will retry, log, and in the
worst case speak.

## What a passing drill looks like

```
API call failed (attempt 1/3, not retryable) error_type=Auth…
Fallback to <provider>/<model>: clearing provider state
Fallback to <provider>/<model>: attached fallback
OpenAI client created  provider=<provider>
API call #1: model=<model> provider=<provider>   ← delivered
```

**Three properties to confirm, and the third is the one people skip:**

1. the failure is **classified** (`error_type=Auth`), not a generic timeout;
2. it is marked **not retryable** — a retry of the same dead key would burn the whole attempt budget before any
   failover;
3. the completion is attributed to the **lower rung by name** in the API-call line.

**A failover that reports "fallback" but whose API-call line still names the primary is not a failover** — it is
a retry with a louder log.

## After the drill — verify you did not move the live fleet

```bash
for s in <seats>; do HERMES_HOME=/opt/data/profiles/$s hermes config get model.provider; done
# and confirm the live key is still good, by a call that costs nothing:
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $PRIMARY_KEY" \
  -H 'User-Agent: Mozilla/5.0 (compatible; Fleet/1.0)' <primary-base>/models
```

## Scope the claim honestly

**One rung proven is not the ladder proven.** State which rung the drill exercised, and that these remain
unmeasured:

- **the second-and-lower rungs** — each needs its own drill, with the rung above it broken;
- **a mid-stream failure** (429 or disconnect after the first tokens) — a different decision path from a
  request that never started, and it can surface as a truncated answer rather than a failover;
- **credential expiry** — a key that stops working on a live seat at an unknown hour is the same test with a
  different trigger.

**And name which pot the fallback spends from.** A failover onto a metered provider is resilience that bills; a
failover onto a `:free` model on a metered provider cannot bill. That distinction belongs in the same sentence
as the pass, or the drill reads as a free safety net it may not be.
