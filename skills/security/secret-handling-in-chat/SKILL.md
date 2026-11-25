---
name: secret-handling-in-chat
description: "Protocol for when a user pastes a sensitive credential into chat — API keys, client keys, wallet private keys. Covers store/verify/never-echo, the private-key-in-chat compromise rule, key-privilege triage (client key vs private key), domain-restricting client keys, and coaching the user to stop pasting secrets. Use when a credential arrives as a raw value in a message and must be secured."
category: security
---

# Secret Handling in Chat

When a user pastes a raw credential value (API key, PAT, client key, or wallet private key) into a chat message, the agent must secure it AND calibrate urgency by what type of secret it is. This skill complements the (manually-authored, read-only) `credential-security-behavior` and `agent-security-hardening` skills, which cover the underlying Hermes redaction/scanner mechanics and key-material protection at rest.   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `agent-security-hardening` exists on this seat -->

## Core protocol — store / verify / never echo

1. **Receive** — key value arrives in a chat message.
2. **Store** — write to a locked-down path with explicit `umask 077` (so it can never be world-readable), `chmod 600`.
3. **Verify** — confirm write via `wc -c` (byte count) and `sha256sum` (record hash for later comparison). **Never `cat` or `read_file` it back** — those always redact or expose.
4. **Never echo the value** back into the conversation. Reference it by name / path only.

Example for a wallet secret:
```bash
install -d -m 700 /root/.blockrun
umask 077 && printf '%s' '<key>' > /root/.blockrun/<wallet-name>-secret
chmod 600 /root/.blockrun/<wallet-name>-secret
wc -c < /root/.blockrun/<wallet-name>-secret   # verify byte count, never cat
sha256sum /root/.blockrun/<wallet-name>-secret # record hash for later comparison
```

## The private-key-in-chat rule (higher stakes than API tokens)

A wallet **private key** pasted into chat is a **compromise event by itself** — chat history is frequently cloud-synced, so the value is exposed regardless of what the agent does afterward. Two obligations:
- Tell the user to **rotate the key / move funds** after the integration is swapped over. Never imply the local copy makes it safe.
- Do not treat it as "handled" just because it was stored to disk.

Proven Aug 4, 2026: Coinbase wallet secret pasted in chat; stored but flagged for rotation.

## Key-privilege triage — don't assume urgency

Not all keys are equal. Before acting, identify the privilege class so the user knows what's actually at risk:

| Key type | Risk | Response |
|---|---|---|
| **Client API key** (e.g. CDP client key — "cannot access portfolios or funds", for RPC/OnchainKit) | Low | Low urgency. **Domain-restrict it** if it'll be used in an app. Rotation can wait. |
| **Server/secret API key** (can touch account data / write) | Medium | Store securely; recommend rotation. |
| **Wallet private key** (moves funds) | High | Compromise event; advise rotation/move funds immediately. |
| **Provider "wallet secret"** (e.g. a CDP wallet secret: PKCS#8 EC key that decrypts/signs for a
  server-side wallet) | High, but **not** the API door | Store, wire to the wallet-owning service. It authenticates
  NOTHING — the SDK must already be authenticated by the key pair before this is read. Confusing it with an API
  key produces "the key is saved but the service still says not configured". |

**Two credentials on one platform can look interchangeable and not be.** Measured on CDP: the API key pair
(`CDP_API_KEY_ID` + `CDP_API_KEY_SECRET`, Ed25519, secret = 88 base64 chars decoding to 64 bytes) authorises
requests; the wallet secret (PKCS#8 EC, ~138 bytes DER) signs for wallets and is useless alone. Establish which
class a pasted value is by **shape**, then say which door it opens before wiring it:

```python
import base64
raw = base64.b64decode(secret)
len(raw) == 64   and b'\x30' not in raw[:1]   # -> ed25519 API secret (JWT signing)
raw[:1] == b'\x30'                            # -> DER/PKCS#8 EC key material (wallet secret)
```

**Ask what the key is FOR before treating it as an action item.** A CDP client key vs a wallet private key vs a Base wallet pending funding are different actions. Don't assume the most recent key is the one a pending transaction needs.

### Scope, not just class — a READ-ONLY key authenticates and then refuses the write

**A credential can be the right class and still be the wrong scope, and the success of the READ is what
hides it.** Measured: a platform API key validated on login, returned the wallet and the live endpoint
list with real counters — and the first state change came back *"403: This API key has read-only
access."* Nothing before the write distinguishes the two.

- **Probe the write path, or ask, before building a plan whose steps are writes.** "The key works" is a
  claim about authentication and says nothing about authorisation. If the plan is pause / deploy / rotate /
  delist, the key's write scope is a precondition of the plan, not a detail discovered at step one.
- **Prefer a read-only credential for a measurement task, and say why.** It cannot move funds or change
  state, so custody risk is nil while you establish what is true. Escalate to a write-scoped key only for
  the step that writes, and let the owner issue it.
- **A 403 that names the scope is the good outcome** — a refusal with a fix attached. Quote the exact
  sentence and the URL it points at; "it didn't work" hides the one instruction that unblocks it.
- **A successful read is not evidence the account already matches the plan.** A key that can read `active`
  cannot make it `paused`, and a plan written against the read has executed nothing.

## Domain-restricting a client key

For client keys that will be used in an app: restrict to exact full domains **before** the app goes live. Enter the full domain without `https://`; **wildcards are not supported**; the key is inert outside allowed domains if it leaks.

## Agent-side echo — the OTHER leak path (not just user pastes)

The user isn't the only source of raw secrets in chat: **the agent's own tool calls leak them too.** Proven Aug 31, 2026: `execute_code` (or `terminal`) ran a command that embedded an API key fetched from a secrets file — and the full command line with the literal key value was echoed back into the conversation transcript via the tool result. Same exposure as a user paste, self-inflicted.

**Rules when handling secrets programmatically:**
- Read secrets **inside** the script's memory (Python reads the file) — never interpolate values into shell command strings, `bash -c "...$KEY..."`, or the code text itself.
- Never print, echo, or `repr()` a credential, even "to confirm it loaded" — print a boolean (`key_found: True`) instead.
- Before running any command that will surface in the transcript, ask: *does this command line contain the secret value?* If yes, restructure until it doesn't.
- If an echo happens anyway, log the incident, flag the key for rotation in the reply, and do not re-print it.

### The GUARD's failure path is a leak path (the one that actually bit)

**A validator that refuses a bad secret must not print the bad secret — and by default, libraries do.**
Measured: `new Wallet(secret)` on a malformed value throws a message containing the offending input
verbatim — `invalid hexlify value (argument="value", value="<0x…")`. The wrapper sliced that message to
60 chars for neatness and printed it. **Result: key material in the transcript, from the code path written
specifically to protect the key.**

- **Every error path that can contain the secret needs redaction, not just the success path.** Before
  printing any exception from a validator/parser/decoder, strip hex-looking runs:
  `re.sub(r'0x[0-9a-fA-F]{4,}', '0x<REDACTED>', msg)` and likewise any bare run of 16+ hex chars.
- **Audit the refusal branch as carefully as the happy path.** Guards are written to "never print the
  key"; the refusal branch is written later, in a hurry, exactly when a bad value is in scope.
- **This applies to shells too** — `set -x`, a wrapper echoing its args, or a CLI that prints its input on
  failure. Never rely on "it only prints on success."

### Tool output redacts secrets — the file you read is not the file on disk

`read_file`, `cat`, `grep`, and even `cat -v` pass their output through the secret scanner. A line holding a
credential-shaped value comes back as `***`. **That is the display layer, not the file.** Two opposite and
equally expensive mistakes follow:

- **False defect.** Grepping a script for `Authorization: Bearer` displays `Bearer ***`, so the code *looks*
  like it hardcodes the literal `***`. "Fixing" that invents a bug that never existed — and the patch may not
  apply (the text you matched is not in the file), or worse, writes a literal `***` over a working
  interpolation, turning a correct line into the exact defect you thought you were removing.
- **False clean.** The reverse also holds: a search for a value you are looking for by literal can never
  match redacted output, so `0 hits` means nothing about the file.

**Verify the BYTE, not the rendering** — read bytes and print a bounded window around the anchor:

```python
b = open(path, 'rb').read()
i = b.find(b"Authorization: Bearer ")
print(repr(b[i+22:i+40]))          # b'{token}']   <- the real text, unaffected by display redaction
print(hashlib.sha256(b).hexdigest()[:16])
```

**Then confirm the interpolated NAME exists in the enclosing scope.** A correct-looking `{token}` is only
correct if `token` is a parameter or local where it is used. The defect you are hunting is often a renamed
parameter — and the display layer hides that while manufacturing a different, fake one. Read the signature
and the body together (`grep -n -A12 'def <name>'`); a renamed parameter and the free name it replaced look
identical in a diff.

**Never author a `patch` / `.replace()` whose `old_string` was copied out of redacted output.** Compose the
anchor from bytes, or use a unique structural anchor (`def <name>`), then re-run the behaviour afterwards —
a patch that silently did not apply looks exactly like one that worked.

**A `replace()` that returns its input unchanged is the tell that your anchor was never in the file.** Check
`new == old` before writing and treat equality as *"my assumption about this file is wrong"* — not as *"already
fixed"*. That one comparison is what stops a phantom fix from shipping with a green report behind it.

### EXTRACT the secret; do not demand an exact paste

**Rejecting a correct secret for a cosmetic reason pushes the user toward "let me try a different key"
when the key was right.** Pasted values arrive wrapped: `<key>`, `"key"`, a trailing label, a break
mid-string. Measured: a file holding `<0x…>` (68 chars) was a correct key plus two brackets.

- Find the value with a pattern (`(?:0x)?([0-9a-fA-F]{64})`) and use the **match**, not the raw text.
- **Extraction cannot make a wrong secret look right — the identity check is still the guard.** Extraction
  only stops a right secret looking wrong. Keep both: extract, then verify identity (derived address /
  hash / prefix matches what you expect).
- **Report the file's own shape before failing** (byte count, whether it starts `0x`). "47 chars, no 0x" is
  a diagnosis; "invalid key" is not.
- **A leading `<` or a suspiciously round length usually means a PLACEHOLDER was pasted, not a key.**
  Offer that as the likely cause and ask for the byte count.

### Never hand the user a REDACTED template to copy

**A redacted example and a literal value are indistinguishable once copied.** Writing an install
instruction as `CDP_API_KEY_ID=***` / `CDP_API_KEY_SECRET=***` gets pasted verbatim — the user has no way to
tell the asterisks were the display layer hiding a secret rather than the value itself. Measured: two
`***` lines landed in the credentials file, and the service failed with a *key-format* error that looked
like a bad credential rather than a bad instruction.

- **Describe the shape, never a masked sample.** Correct: "the ID starts with `organizations/` and runs
  ~90 chars; the secret is exactly 88 base64 chars." Wrong: any line a user could copy that is not real.
- **Say out loud that the redaction is a redaction** the first time a masked value appears: *"the `***`
  below are redactions — copy the real string from the provider's modal."*
- **Give a shape check that prints no values**, so the user can self-diagnose the paste before you ask for
  it again:
  ```bash
  awk -F= '/^MY_KEY_ID/{print "ID_len=" length($2) " prefix=" substr($2,1,14)}
           /^MY_KEY_SECRET/{print "SEC_len=" length($2) " prefix=" substr($2,1,4)}' <file>
  ```
  Length + first characters answer "placeholder or real key?" without exposing anything.
- **A length that matches the placeholder text is the giveaway** (3 chars for `***`), not a rotated key.
  Diagnose the instruction before asking the user to rotate anything.

### Measure the exposure BEFORE reacting to it

**Do not escalate on "a secret was in the transcript" — measure what fraction, and whether the whole thing
is there.** The difference between a fragment and a full key is the difference between a cleanup and a
compromise.

```python
# longest hex run containing a known leaked fragment -> is a FULL secret present?
runs = {len(m.group(0)) for m in re.finditer(rb'[0-9a-fA-F]{8,128}', raw) if frag in m.group(0)}
# any run >= 64 chars for a key = the whole key is on disk; 9-11 chars = a fragment only
```

**State the bit count, not adjectives.** "9 hex characters = 36 bits of a 256-bit key; not reconstructable"
is a finding. "Small leak" is not, and "compromised" overstates it. **Correct your own earlier estimate out
loud if it was wrong** — an inflated exposure figure is a bad number like any other, and it costs the user a
needless key rotation.

## Capture-then-DELETE: use the channel's own revocation

If the platform lets the bot delete messages, the protocol gains a step: **capture the value, then delete
the message that carried it, then confirm `ok:true`.** That removes the platform's copy immediately —
strictly stronger than a retention timer, and cheaper than asking a user with a phone to reach a terminal.

- **Check the right first, don't assume it.** Telegram: the bot must be an admin with `can_delete_messages`.
  Verify with `getChatMember?chat_id=<g>&user_id=<bot_id>` and read the boolean. A bot can always delete
  its OWN messages; deleting a USER's message needs that admin right.
- **Get the message id from the session DB, not the logs.** Gateway logs record that a message arrived,
  not its text, so the id lives in `messages.platform_message_id` (state.db). Match the row by credential
  **shape** (`^\d{8,10}:[A-Za-z0-9_-]{30,}$`), cross-check the content LENGTH against the expected value
  plus any prefix, then delete by id. **Never print the value while searching for it** — print the id,
  the length, and the match count.
- **Capture the id BEFORE redacting the DB — redaction destroys the locator.** The redactor rewrites the
  very string you would search on, so a lookup keyed on the secret (or on a fragment of it) returns zero
  rows afterwards and the delete step silently has no target. Order: install → **capture id** → delete
  message → redact DB → verify residue. If you have already redacted, fall back to locating the message by
  **recency plus a content prefix you know survived** (e.g. the first words of the message), then confirm the
  row's length still matches before deleting — never delete by recency alone, a neighbouring message will be
  the casualty.
- **Deletion is irreversible and is not gated by a dry run.** Confirm the id belongs to the secret message
  (shape + length agree) before calling `deleteMessage`; never delete by guess or by recency alone.
- **State what deletion does NOT cover.** It removes the CHAT exposure. The value still transits the
  agent's transcript, the session DB, the encrypted backups, and the model provider's request logs. So
  this lowers chat risk; it does not make the credential unexposed. Non-revocable material (wallet keys,
  seeds, passphrases) is still refused on arrival regardless of deletion.
- **Treat this as the default routine, not a favour.** Once the right exists, every pasted credential gets
  captured and the message removed in the same turn, and the reply says so — so the user never has to
  decide again.
- **Never hand the deletion back to the user.** Writing "delete that message when you see this" is a protocol
  failure, not a courtesy: the bot holds `can_delete_messages`, the id is in `state.db`, and the user is very
  likely on a phone. If the sentence you are about to send contains "please delete it", replace it with the
  `deleteMessage` call and report `ok:true` + the message id. The user has already told us this is their rule;
  restating it as their chore reads as not listening.

## Storage is not delivery — four links, and the chain fails at any one

**"I saved the key" and "the service has the key" are different claims.** A credential has to survive four hops; a
failure at any hop looks identical from the outside ("it says not configured") and invites the wrong diagnosis:

1. **Written** — name AND non-empty value, mode 600, read back to prove it parsed. A name with `""` is worse than
   an absent name: it makes every inventory report say "configured".
2. **Visible to the consuming process** — check the mount table, not the filesystem you are standing in:
   `docker inspect <container> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'`.
   A host-side `.env` that is **not mounted** cannot reach a containerised service, no matter how perfectly it was
   written. Concluding "the key was lost" before checking mounts is a misdiagnosis with a forensics bill attached.
   Then read the **running process's own environment** — `docker exec <container> env | grep -E '^(PREFIX)_'` —
   before inferring configuration from source code. Code defaults are not runtime values: a source file can show
   an empty default and a "borrowed fallback" while the container carries a complete, deliberate set of overrides.
   Announcing a config defect from the code alone is a false alarm that costs a retraction and the user's trust;
   one `env` read settles it.
3. **Consulted at the DISPATCH** — adding a credential loader *inside* the verifier/consumer is dead code if the
   caller still gates on the old condition:
   ```python
   if os.getenv("PROVIDER_KEY"):        # ← the decision point still reads ENV only
       result = verify_via_provider(...)  # ← loader inside here is never reached
   else:
       result = simulate(...)             # ← and this is the branch that runs, forever
   ```
   **Grep for every `getenv`/`environ` read of that credential and patch them all.** A one-site fix produces a
   failure message from the *fallback* path, which reads like "credential absent" while the file sits right there.
4. **Recorded** — a rotation/removal line in a durable log (`00-System/credential-rotations.md`): what changed, when,
   where it now lives (or that it lives nowhere). A credential that vanished with no note costs the next session
   twenty minutes of forensics.

### Prove the credential AT THE PROVIDER before you touch production

**A restart is not a test, and it is the expensive way to learn that a key is malformed.** Call the provider with the
credential first, from a scratch venv, and read the status code:

```bash
python3 -m venv /tmp/v && /tmp/v/bin/pip install -q pyjwt cryptography
# mint the token the provider expects (EdDSA for CDP), then GET a cheap authenticated endpoint
```

`200` = the key is real and the claim format is accepted — wire it. `401` = fix the credential, not the code. This
turned a night of "not configured → PEM error → still refused" into one decisive answer, and it also proves the
quiet assumption nobody stated: **a bare UUID key id can be a valid JWT `kid`** (the `organizations/…/apiKeys/…`
form is one accepted shape, not the only one). Verify by call, never by eyeballing the format.

**Then shape-check at the consumer.** A loader that trusts any readable file will happily use a placeholder and
surface a format error that looks like a bad key. Reject values that fail the expected decode length and fall
through to the next source:

```python
if len(base64.b64decode(sec + '=' * (-len(sec) % 4))) != 64:   # not an ed25519 secret
    print(f"WARN: {path} skipped — not a credential"); continue
```

### Absence forensics — search by SHAPE, never by name

When asked "didn't I give you that key?", a name search produces false comfort: documentation *outlives* the secret,
so dozens of files will match `PROVIDER_API_KEY` and not one will contain a value.

```python
# Search every session store by VALUE SHAPE, print only shape + surrounding words.
SHAPES = {'key_id':   re.compile(r'organizations/[A-Za-z0-9-]{20,}/apiKeys/[A-Za-z0-9-]{20,}'),
          'b64_64':   re.compile(r'\b[A-Za-z0-9+/]{86,90}={0,2}\b')}   # 64 bytes -> 88 b64 chars
```

- **Report shape, not values:** length, prefix, decode-length, and the sentence around it. "0 key-shaped strings
  across 5 stores" is a finding; "no matches" from a name grep is not.
- **Then check the older copies:** live `.env`, every `.env.bak-*`, and `/proc/<pid>/environ` of the *running*
  process. A key that works in a file but not in the process means hop 2 or 3, not a lost key.
- **Say which of the two explanations holds** — never quoted/pasted (deliberately not retained), or revoked/rotated
  without a note. Both leave the same trace; distinguishing them tells the user whether to re-issue.
- **A doc asserting "both present in .env" is history, not status.** Check the file's own mtime and value lengths
  before repeating its claim to the user.

## One secret, N copies — replication is a rotation hazard

**The same credential living in every seat's `.env` is not redundancy; it is N documented ways to break
something.** Measured on a fleet: one provider key present in four profiles with an identical value, while the
fleet's own runbook said *"rotate `PROVIDER_API_KEY` in each agent's `.env` independently; credentials are NOT
shared."* That instruction is a recipe for a rotation that lands in three seats and misses the fourth — and the
symptom is *"this agent can't stay connected"*, never "one seat has a stale key".

- **Treat a shared credential as ONE record with N readers, not N copies.** One source resolved at start-up
  (a secret manager, or a single file every process reads) makes rotation one write. N hand-edited copies make
  rotation an N-step procedure that must never be interrupted.
- **Diagnose a one-seat failure by comparing value HASHES, never values**: `md5sum` (or `sha256sum`) of the
  extracted value per seat. Identical hash + failure everywhere = the provider revoked it. **Differing hashes =
  the rotation missed a seat** — and that is fixable in one write, no support ticket.
- **A working credential proves nothing about the consumers.** Check the key at the provider (a cheap
authenticated GET) *and* the consumer's own read path, because a valid value that one process cannot see fails
identically to an invalid one.
- **Before writing "rotate in each seat" into a runbook, ask whether the seats can share one source instead.**
  A runbook that instructs N manual copies is a documented way to leave N−1 broken.

## Handing a credential to another SEAT or host — three traps, all silent

**The receiver asking for the key is a delivery problem, not a chat problem.** Get it wrong and nothing errors:
the file does not appear, or it appears where the receiver's user cannot read it.

- **Never put a key in a git-tracked path, and exclude it BEFORE creating the file.** A key in history is a key
  you can never revoke cleanly, so the order is `echo '<dir>/*.key' >> .gitignore` → `git check-ignore -v` → then
  write. Add the ignore rule for the file pattern, not the whole directory, so the protocol README beside it stays
  trackable.
- **`read -rs` needs a real TTY.** In a non-interactive shell (a pasted block, a script, a `docker exec` without
  `-t`) `read` hits EOF immediately, returns non-zero, and an `&&` chain **aborts the whole rest of the command** —
  the user sees a clean prompt, no error, and no file. Measured: two attempts produced nothing and reading as "the
  key is in there" cost a round trip. **Have the user paste into a `read -rs` at an interactive prompt, or accept
  the value another way** — and always verify with a byte count (`wc -c`) before believing it landed.
- **A cross-mount `install -m 600` can land in a path that is not the container's.** `docker cp` into the
  container's own path plus `chown` to the agent's uid is deterministic where a host-side path guess is not; the
  failure mode of the guess is a sparse, unreadable or absent file. **Confirm with `ls -l` from the RECEIVER's
  side, not from the host.**
- **Ownership is part of delivery.** A mode-600 file owned by `root` is readable by the agent in a bind mount
  but **not writable**, and an app that writes its own config beside the key fails with `EACCES` on the
  *directory* — which reads as a permissions bug in the app. Fix the owner, not the mode.

## Coach the user on future pastes (durable preference)

Gently ask the user to **reference secrets by name** ("the CDP client key") instead of pasting raw values into chat. This is a durable workflow preference that prevents repeated exposure. Do not scold — a single calm, clear request.

## Pitfalls

- Do NOT read the secret back (`cat`, `read_file`) even to confirm — always verify indirectly (byte count, hash).
- Do NOT assume a private key is safe because it was stored to a `600` file — chat exposure still requires rotation.
- Do NOT confuse a low-privilege client key with a fund-moving private key when advising the user on urgency.
- **Before raising a permission alarm, check whether the path is a SYMLINK.** A symlink's own mode is always `lrwxrwxrwx`; the mode that matters is the TARGET's. Alarming on the link is a false positive, and a false alarm about secrets is its own kind of damage — it teaches the user to discount the next one. Resolve the target (`stat`/`ls -la` the resolved path) before reporting.
- Do NOT echo the raw value anywhere in the reply; use the path/name reference only.
- **Do NOT diagnose a credential line from `read_file`/`grep`/`cat -v` output** — they redact, so a correct file reads as broken (`Bearer ***`) and a literal search reads as clean. Read bytes, print a bounded window, compare a hash. Never patch an anchor copied out of redacted output.
- Do NOT build shell commands by interpolating secret values fetched from env/secrets files — the command string lands in tool output and the transcript. Keep secrets inside the script's process memory.

---

## Making "delete the message" TRUE (verified 2026-10-16)

**The chat is not the record.** A pasted secret lands in the profile's `state.db`, and Telegram's
`deleteMessage` cannot reach those copies. Measured on one pasted bot token: **21 cells across 8
columns in 3 tables** —

`messages.content` · `messages.tool_calls` · `messages.reasoning` · `messages.reasoning_content` ·
`messages.api_content` · `messages_fts.content` · `messages_fts.tool_calls` ·
`messages_fts_trigram.content`

…and the FTS indexes carry **no** `platform_message_id`, so no bot API call can ever touch them.
Until the DB is redacted, "capture → install → delete → confirm" is theatre.

### The complete protocol — four steps, all verified

1. **Install** the secret to a mode-600 file (`umask 077`; e.g. `/opt/data/.bot-tokens/<name>.token`).
   Then never retype it — **read it from that file**. Putting it inline in a shell command or heredoc
   writes it into `state.db` as yet another copy (this is how the cell count grows).
2. **Delete the message** with the Bot API. Our bots are **administrators with
   `can_delete_messages: True`** in their groups (verified for `@Gentechlabsbot` in HQ), so:
   ```bash
   curl -s "https://api.telegram.org/bot$TOKEN/deleteMessage" -d chat_id=<chat> -d message_id=<id>
   ```
   Find the id from `state.db`: `SELECT id, platform_message_id FROM messages WHERE content LIKE '%<needle>%'`.
3. **Redact the DB copies** — `profiles/gentech/scripts/redact-secret.py --file <secret-file> --yes`.
   It replaces the literal with `[REDACTED]` across the scanned `messages` columns in one transaction and
   rebuilds both FTS indexes (they are external-content; the triggers usually cover it, the rebuild is
   belt-and-braces). Then verify with `scripts/scan-residue.py` (below), not with the tool's own report.
4. **Confirm from measurement, not intention** — re-scan every `state.db` for the literal and report the
   residual count. `0` is the only acceptable answer.

### ⚠️ The redactor's own report is not evidence — it counted work, not matches

**Three defects found in `redact-secret.py` by disbelieving its output** (it reported `44,501 cells
redacted`, four orders of magnitude more than a 9-character needle could touch):

- **`--pattern` selected EVERY row.** With no literal to `LIKE` against, the query fell back to `LIKE '%'`,
  which matched every row, rewrote every row, and incremented the counter for every row. **Work performed
  was reported as matches found.** A count that cannot go down is not a measurement. Fixed by filtering in
  Python and counting only cells that actually changed (`subn`, then `if new == val: continue`).
- **A column absent from the scanned list is a column the tool cannot clean.** `reasoning_details` was not
  in `COLS`, and 6 of 7 live matches were sitting in it — so the tool's "clean" report covered everything
  except where the secret was. **When a redaction reports zero, confirm the column list covers every column
  the secret could have landed in**, and check `PRAGMA table_info(messages)` yourself.
- **The naive fix is worse:** dropping to `WHERE <col> LIKE ?` with the pattern as the parameter is what
  produced the every-row behaviour. Filter in the language, not in SQL.

**Two limits the tool cannot remove — state them with every run:**

- **Raw bytes persist in `state.db-wal` and in freed pages until a checkpoint + VACUUM.** A clean logical
  scan is not a clean file on disk. Measure both: count the needle in the raw bytes of `state.db` **and**
  `state.db-wal`. If bytes remain, a checkpoint + VACUUM clears them. **The checkpoint alone is usually enough for
the WAL, and it is cheap enough to run straight away:**

  ```python
  import sqlite3
  con = sqlite3.connect("<profile>/state.db")
  con.execute("PRAGMA wal_checkpoint(TRUNCATE)")   # truncates the WAL file to 0 bytes
  con.commit(); con.close()
  ```

  Measured: a 64 MB WAL truncated to **0** mid-session, and the needle count went to zero, with no
  restart needed. **VACUUM is the heavier step** (it rewrites the whole DB to clear freed pages) and
  is the one worth deferring to a quiet window. Verify by re-counting in the raw bytes of both files,
  not by the absence of an error.
- **A live conversation keeps re-introducing the value.** Any turn that quotes the secret (including your
own analysis of it, or the user pasting the error again) writes a fresh copy. **Assemble the needle from
parts in your own commands** (e.g. `P="8ab2""bcfe5"`) so the tool call itself does not re-insert it, and
stop quoting it in prose — refer to it as "the fragment" from then on.

#### Your own VERIFICATION is the most likely re-contamination — sweep, then scan without typing it

**A scan that embeds the literal in order to search for it creates the copy it then fails to find.** Measured:
after a clean sweep reported every cell changed, a residue scan still found **one full copy of each token** —
sitting in `messages.tool_calls`, written by the `for t in ("<literal>", "<literal>"):` line of the scan that
was checking for them. Nothing malicious; the instrument was the leak.

- **Read the needle from the staged file inside the scanner**, never retype it in the source:
  `toks = {os.path.basename(f): open(f).read().strip() for f in glob.glob("<dir>/*.token")}`. The literal then
  never enters the transcript, the tool call, or the DB.
- **Run the sweep a second time after your own investigation.** Redaction is not idempotent-by-accident: every
  turn between the sweep and the final scan can add a row. Sweep → scan → if residue, sweep again → scan.
  Report the **closing** count, not the first one.
- **Treat "0 rows" from a scan you wrote as a claim about your scan.** The tool's own report and a hand-written
  query are both instruments; only a scan whose needle never touched the transcript can be trusted to prove 0.

#### Scan the places the DB sweep cannot reach: the vault and the mirror

`state.db` is not the only durable copy. On a fleet where the vault syncs to a hosted service **and** mirrors to
a code host, a secret written into a note propagates to both — and neither is touched by the redactor.

```bash
grep -rl "$(cat <staged-secret-file>)" <vault-root> 2>/dev/null | head   # hosted-sync copy
grep -rl "$(cat <staged-secret-file>)" <any-code-tree> --include='*.md' --include='*.json' --include='*.py'
```

- **Pass the value by file expansion (`$(cat …)`), never inline** — the command line is itself a transcript entry.
- **Check the mirror's committed tree, not just the working tree** — a note committed then deleted locally is
  still on the remote.
- **A hit in a synced surface outranks a hit in the DB**: it is published, cached and replicated. Rotate rather
  than redact when one appears.
- **Finish by listing where the secret is supposed to live** (the one credential file, mode 600) and deleting
  every staging copy you created. "Redacted" is not the same as "no leftover copies".

### Verify with `scripts/scan-residue.py` — not with the redactor's own report

```bash
P="<value>" python3 scripts/scan-residue.py --needle-env P --profiles gentech
```

Scans **every column of every table** plus the **raw bytes of `state.db`, `-wal` and `-shm`**, prints
counts and the longest hex run containing the needle (so you learn fragment-vs-full-key by length), and
**never prints the value**. Exit `0` = clear; `2` = residue. Assemble the value from parts in the shell
(`P="8ab2""bcfe5"`) so the command line does not re-insert it.

### Rules
- **A redacted DB row is fine; an unredacted one is a leak.** Revocable secrets (bot tokens, PATs) can
  live in `state.db` briefly because they can be `/revoke`d — but the residue should still be cleared.
- **Non-revocable material never enters chat at all** (wallet keys, seeds, passphrases) — redaction does
  not make an unrecoverable secret recoverable.
- **Logs are already safe** — the Hermes scanners redact token-shaped strings in the gateway/agent logs
  (verified: no raw token in any log file). `state.db` is the gap, not the logs.

### Never keep a credential backup inside a profile directory (2026-10-16)
Hermes' export guard drops credential files by **exact filename** (`auth.json`, `.env`, `bot-desktop`) and
scrubs secrets out of known **text suffixes**. A backup like **`.env.bak-managed`** matches neither, so an
export would carry it **unscrubbed**. Found live: `profiles/gentech/.env.bak-managed` holding
`OPENCODE_GO_API_KEY` + `TAVILY_API_KEY`. **Move credential backups out of profile trees entirely**
(e.g. `/opt/data/backups/credential-baks/`, mode 600) — don't rename them and hope.
