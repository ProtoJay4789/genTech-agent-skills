# Worker SOUL authoring + bot-group ownership (session learnings, Aug 16 2026)

## 1. Worker SOUL — specialist personality, not coordinator clone
`hermes profile create <name> --clone --clone-from gentech` copies the MAIN agent's
SOUL.md verbatim. Result: gizmo/Labs was running the generic "Gentech — Solo Operation"
coordinator SOUL with zero Labs personality, and desmond/dmob/yoyo were still on default
Hermes boilerplate. Every new worker MUST get its own SOUL.md after cloning.

Family SOUL format (matches gentech / The Steward / Pixel):
- **Identity**: Name, Role (one lane), Group (its chat_id), Vault Folders it owns, Personality (1-line voice)
- **What it owns** — concrete deliverables in its lane
- **Personality / voice** — distinct + on-brand; Entertainment = punchy/play-first, Treasury = calm authority
- **Rules** — family rules (Jordan is boss, blockers flagged immediately, build first talk later,
  vault not conversation, stop-point → write it down) + anti-endearment (never "papi", Vanito's only)
- **End-of-Day Report (REQUIRED)** — the group return-loop: write
  `01-HANDOFFS/<group>-to-gentech/YYYY-MM-DD.md`, append to `<group>-completions.md`, git commit
- **Vault + avatar path** — local vault, `ob sync`, domain-only writes,
  `Entertainment/branding/<worker>-avatar.png` style

Workflow: draft SOUL in the vault (e.g. `Entertainment/branding/<worker>-SOUL.md`) for Jordan
review BEFORE wiring it as the live profile SOUL.

Pixel (Entertainment worker) drafted Aug 16:
- Avatar → `Entertainment/branding/pixel-avatar.png` (+ `pixel-avatar-512.png`)
- SOUL → `Entertainment/branding/pixel-SOUL.md`
- Glowing pixel-art arcade mascot beside neon cabinet, cyan/magenta glow, "come play" energy.
  Play-first on-ramp lane: arcade, Seedance/films, X/social, hackathon demos, Vanito collabs.

## 2. Bot-token → group ownership mapping (403 on the wrong bot)
The gentech bot token (ProtoJaybot) returned HTTP 403 sending to the Labs group. Root cause:
the gentech bot had been **kicked from Labs** — Labs is served by the gizmo bot (FollowTheCodebot),
not gentech. A bot kicked from a supergroup returns 403 on `sendMessage`/`getChat` for that chat
even while its `getMe` is healthy. Always map group→bot before posting.

Live fleet map — **RE-MEASURED 2026-10-16** (`getMe` per seat; the Aug-16 names below were WRONG):

| Profile | Bot username | Bot id | Serves |
|---------|--------------|--------|--------|
| gentech | `@Gentechlabsbot` | 8983403162 | Gentech HQ (<telegram-group-id>) |
| gentech-treasury | `@AgenticTreasurybot` | 8859788654 | Strategies/Treasury (<telegram-group-id>) |
| arthur | `@GentechEDU_bot` | 8695731797 | Gentech EDU (<telegram-group-id>) |
| protojay | `@ProtoMagicbot` | 8572791411 | Gentech Social media (<telegram-group-id>) |
| forge | *(desktop — no bot on this host)* | — | — |

Retired: `gizmo` (`@FollowTheCodebot`, served Labs before the EDU rename), `pixel` (Entertainment).

> ⚠️ **The Aug-16 map was wrong on every row and stayed wrong for two months.** It named
> **`ProtoJaybot`** for gentech (live: `@Gentechlabsbot`) and **`GentechDeskbot`** for treasury
> (live: `@AgenticTreasurybot`) — and it sent the 2026-10-16 bot-out-of-group diagnostic chasing
> `GentechDeskbot` (id 8981389550), a bot that isn't the treasury seat. A name in a doc is not a
> measurement. **Re-run `getMe` per seat before diagnosing a 403** — and when you learn a bot's
> real identity, fix this table in the same breath.

Diagnose a 403:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<group>"
# "ok":false, error_code:403 → bot kicked / not a member
```
Re-add the kicked bot, or route the send via the correct group's bot token.
