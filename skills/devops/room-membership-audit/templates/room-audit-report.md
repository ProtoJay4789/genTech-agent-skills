# <Room name> — membership audit

**Audited by:** <seat> · **Method:** read-only (`getMe`, `getChat`, `getChatMemberCount`, `getChatAdministrators`, `getChatMember` × N)
**Verified at:** <one timestamp, taken during the calls — every row below shares it>
**Filed:** <timestamp> · **Delivery:** filed to `<return lane path>` / DM receipt: `<none | session id>`

## Room as measured

| field | value |
|---|---|
| chat id | |
| title | |
| type | |
| member count (platform) | |
| reconciliation | `N = bots (a) + humans present (b)` → balances / gap of `N` |

> Audit covers this room only. A seat sees its own room exclusively — `getChat` on any other seat's room
> returns `chat not found` — so this inventory cannot be cross-checked from outside.

## Members

| group | person | platform id | membership | scope | authority | verified at |
|---|---|---|---|---|---|---|
| | | | present (creator) / present (member) / former / kicked / no record | | read / recommend / act / UNKNOWN | |

Bots in the room are listed and labelled — they count toward the reconciliation, not toward the humans.

## Reconciliation

```
platform member count : N
bots                  : a  (<names>)
humans present        : b  (<names>)
a + b                 : N   -> no unlisted human in this room
```

## Drift against the registry

| person | registry says | room says | drift class | action needed |
|---|---|---|---|---|
| | active | former | status drift | |
| | active | no record | no participation record, or id unresolvable there | |
| | (no status field) | | missing field | |
| | `@handle` | (different handle) | handle drift — blocks username-keyed migration | |

## Limits of this audit

- Join dates, historical membership, invite links, pending join requests, and the reason anyone left are not
  exposed by these methods.
- `getChatMemberCount` is a number, never a roster; the reconciliation above is what makes it evidence.
- `<anything else you could not measure>`

## Changes made

**None.** No add, remove, promote, invite, or unban was issued. Calls used: `<list>`.

## What would close the open rows

- `<drift row>` → `<the specific check or the human decision it needs>`
