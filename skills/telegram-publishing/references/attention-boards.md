# Attention boards

A board is **one pinned message per topic** that gets edited in place forever. It exists because pinning by hand
produces a graveyard of stale pins, and every agent that pins its own message turns the top of the chat into a
pile of outdated claims nobody can rank.

The spec, in the principal's words: *"Any agent can pin a message… we want it easy to pin with added
information and unpin the old information. We'll call this an attention board."*

## Design decisions that are not optional

**Edit, do not repost.** `editMessageText` keeps the message id, so update and pin are one atomic step. A
repost-then-pin leaves a window where two pins exist, and if the pin call fails the old one is already gone.

**Identify the board by a MARKER inside the text, not by being the current pin.** Telegram's `getChat` reports
only ONE pinned message per chat, so if another agent pinned anything, the board is still in the group but no
longer the pin. Search by content first, pinned second — otherwise you repost a duplicate and leave two boards.

**Boards live in a registry.** A dict mapping board key → title/emoji, at the top of the script. Adding a board
is adding a key; never edit the logic below it.

**The script is the interface.** `--board <key> --render <file.json> --chat <id>`, plus `--status`, `--unpin`,
`--dry-run`. Take the chat id from `--chat` or an env var — never hardcode a group id into a fleet script.

**Render file shape:** `{"title": "one-line subtitle", "updated": "…", "lines": ["…"]}`. Content edits never
touch code.

## The marker must survive Telegram Markdown

This is the failure that costs the most time, and it is self-inflicted:

- **`[board:jobs]` breaks the message.** `[` opens a **link entity** in Telegram Markdown. An unclosed `[`
  makes the API reject the entire message with `can't parse entities: Can't find end of the entity starting at
  byte offset N`. **Never use square brackets in a marker** — use `⟦board:jobs⟧` or another bracket-like glyph.
- **A handle's underscore breaks the message the same way.** `@exe_nf` contains `_`, which opens an *italic*
  entity that never closes; Telegram then rejects the **whole** post. Escape `_`, `[` and `]` in every piece of
  prose you assemble, and keep the escaping in ONE helper used for each line.
- **One bad entity kills the whole update, not the line.** So a stray character in a footer costs the entire
  board refresh and presents as a mysterious 400.

## A failed edit must be fatal

**The trap:** `editMessageText` returns `ok: false`, the script falls through to `pinChatMessage`, that succeeds
because the message was already pinned, and the script prints `VERIFY pinned ✅`. The report says the board is
current; the board was never updated. This is the same class as a grader that scores a perfect extraction zero —
a tool asserting success on work it did not do.

- After a failed edit, **retry once as plain text** (drop `parse_mode`) — it clears entity errors instantly.
- If the retry also fails, **exit non-zero and say the board was NOT updated.** Never reach the pin call.
- Read `ok` on every call. A 429 `retry_after` is not a text problem — sleep and retry, do not "fix" the content.

## Verify by reading the pin back

`pinChatMessage` returning `ok` is not proof. Re-fetch the chat and match:

```
pinned = getChat(chat_id).result.pinned_message
assert pinned.message_id == intended_id
```

Then assert the **content** — that the expected sections are present in `pinned.text` and the character count is
what you expect. A pin pointing at the right message id with stale text passes an id check and fails the reader.

## Changing the marker is a MIGRATION, not an edit

Having changed the marker character to fix the bracket bug, the script no longer recognised the existing board
and **posted a second one**. When an identity field changes:

1. **Adopt the old marker first** — append the new marker to the existing message (plain text, no `parse_mode`,
   because the legacy body may itself contain markdown Telegram now rejects).
2. Then run the normal update path so it edits the existing message.
3. Only after that, delete or unpin the legacy message.

Deleting before adopting is how a board gets lost.

## Content rules for a board that other agents read

- **Carry the exclusions, not just the targets.** A board that lists only what to pursue gets re-litigated next
  session. Include a **DO NOT** block with a one-line reason per entry.
- **Mark each row with its verification state and the date it was checked.** A board is a claim about the
  outside world; it decays.
- **Never let a board assert a fact the underlying artifact contradicts.** A pinned link carrying the wrong
  location or workplace type is worse than no pin, because pins read as authority.
- **One-line subtitle states the rule the board was built under** ("Remote only · hybrid filtered out · every
  link re-checked on the employer's own board").
