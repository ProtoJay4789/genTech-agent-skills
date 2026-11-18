# Registry vs world — status semantics and the drift classes

Depth for `chat-room-membership-audit`. Read when mapping API statuses into the report fields, or when the
audit output feeds a migration.

## Status → membership (Telegram Bot API)

| API `status` | report as |
|---|---|
| `creator`, `administrator`, `member` | **present** |
| `left` | **left** |
| `kicked` | **kicked** |
| `HTTP 400 Bad Request: member not found` | **never** |
| anything else / call failed | **UNKNOWN** |

- **`member not found` means "this chat has no record of that id."** The API also returns it for an id it
  cannot resolve in that chat at all, so report the fact in exactly that wording. Do not upgrade it into
  "this person does not exist", and do not read it as "removed".
- **`left` and `kicked` are different facts with different remedies.** `kicked` means a ban exists (only a
  holder of `can_restrict_members` can lift it); `left` means they walked away and can return. A registry
  almost never claims either.
- **The admin list is a subset of the roster, never the roster.** A room holds members with no admin entry.

## Drift classes to look for and name

1. **`status: active` that measures `left` or `never`.** The registry carries a status the platform does not
   corroborate. **Expect the same defect independently in other rooms** — when the same broken field shows
   up in a second room, say so: one field wrong in several places is a registry-wide failure, not one stale
   row, and per-room patching will not fix it.
2. **A person with no `status` field at all.** A missing field reads as "not a problem" to every consumer
   that assumes presence, which makes it worse than a wrong value. Report the absence explicitly.
3. **A stored username the live account no longer carries** (`username: null` on the user object, sometimes
   a different display name). No effect on membership, **fatal for any username-keyed mapping** — flag it
   whenever the audit feeds a migration.
4. **Case-only handle differences.** No operational effect; still record them. The audit is a file-vs-world
   comparison, not a file-vs-flattering-reading of the file.
5. **Registry rows for people who were never in this room.** Not errors in the file, but they become errors
   in the migration — carry the arithmetic (present / former / never) into the report.

## Portability

The *discipline* above is platform-independent: owner-only measurement, reconcile the count, claim vs
measurement, UNKNOWN over guessing, migration arithmetic. The *calls* are not — Telegram's read-only
membership surface is `getChat` / `getChatMemberCount` / `getChatAdministrators` / `getChatMember`, and
another platform's will differ in shape (no per-id `status` string, different removal semantics, different
not-found wording). Re-derive them for the platform in front of you rather than translating method names,
and state in the report which platform was measured.
