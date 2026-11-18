---
name: fleet-identity-images
description: "Use when making or applying fleet profile pictures."
category: creative
version: 1.0.0
author: arthur
license: proprietary
tags: [avatar, profile-picture, identity, branding, telegram, image-generation]
metadata:
  hermes:
    tags: [avatar, profile-picture, identity, branding, telegram, image-generation]
    related_skills:
      - creative/brand-assets
      - security/key-custody-and-recovery
---

# Fleet Identity Images

Producing the picture that represents an agent, a department or a group — and actually applying it to
its surfaces. For GenTech's own brand palette and the SVG-first logo workflow, use `brand-assets`; this
skill covers the per-identity class: what size, how it is made, and where it gets set.

## When to Use

- "Make a profile picture for yourself / for this department / for this group".
- A new agent, seat, department or group is being stood up and needs an identity mark.
- An existing mark is a placeholder and is being replaced with a real one.

## Look before you draw

**Inventory the identities before generating anything.** Identity marks tend to already exist — often
several, for the fleet and for each department — and their sizes and construction are the spec you must
match. Read the brand/identity note and list the existing files with their real pixel dimensions; a mark
that is 512×512 is telling you what to emit.

**Record which marks are placeholders.** A mark drawn deterministically (or by hand, with no image API)
is legitimate and often shipped — but it must be labelled as such wherever it is listed, so nobody later
mistakes it for the finished article or tries to trace a pipeline that never existed.

## Order of operations

1. **Decide the concept in words first**, and state it to the owner before spending anything: the idea,
   the palette, the one thing it depicts. A brief is cheap; a render is not, and a redirect afterwards
   wastes the whole run.
2. **Gate the paid rail before generating.** If the image comes from a paid API, confirm the wallet that
   will actually be charged is the one on record and clears a small floor — a rail's SDK can create a
   wallet nobody planned for, and funding the recorded address then funds a different one. See
   `key-custody-and-recovery` (its `agent-capital-custody-and-recovery` reference carries the full
   gate text); if the gate fails, name the exact address needing funds and
   stop. Never report "no image yet" as a finished job.
3. **Generate once at the model's size, then emit the whole export set in the same run.** Image models
   emit ≥1024px and the surfaces disagree, so one master becomes three files — all of them offline
   downscales:

   ```bash
   ffmpeg -y -i master.png -vf scale=512:512:flags=lanczos -frames:v 1 mark-512.png      # web, group photo
   ffmpeg -y -i master.png -vf scale=400:400:flags=lanczos -frames:v 1 mark-400.png      # AgentScan / IPFS
   ffmpeg -y -i master.png -vf scale=512:512:flags=lanczos -frames:v 1 -q:v 2 mark-512.jpg  # Telegram bot
   ```

   (ffmpeg is present wherever audio work happens; PIL and cairosvg are not guaranteed.) The `.JPG` is a
   **format** conversion, not just a resize — it is the one a pipeline forgets, and it is the only file
   the bot photo will accept.
4. **Never overwrite the mark you are replacing.** Write the new file under a distinct name so a worse
   result is reversible by filename alone, and keep the previous one on disk as the known-good fallback.
5. **Accept at the smallest place it is seen.** A chat list renders a mark at ~40px, a marketplace
   avatar smaller still. If it does not read there, it is too complex however good it looks at 1024px.
6. **Apply it per surface, and verify the surface accepted it.** Generating the file is not applying it.

## Surfaces — know which you control before promising anything

The table below is **measured, not remembered**. Before promising an owner that a surface can be set,
probe the method **with no arguments**: a *parameter* error (`Bad Request: photo isn't specified`) means
the method exists and you are missing an input, while a `404 Not Found` means it genuinely does not
exist. Those two answers are the difference between a capability and one you imagined — and asserting a
capability from memory is how an owner gets told "no" for no reason, sometimes for months.

| Surface | How it is set |
|---------|---------------|
| Telegram **group** photo | `setChatPhoto` — works only if the bot is an administrator with `can_change_info`; check with `getChatMember` first |
| Telegram **bot's own** photo | **`setMyProfilePhoto`** — this IS a Bot API surface; an earlier version of this skill said it was not, and that was **wrong**. It takes an **`InputProfilePhoto` OBJECT, not a bare file**: `-F 'photo={"type":"static","photo":"attach://mypic"}' -F "mypic=@mark-512.jpg"`, with a **static `.JPG`** (512×512) — a PNG will not do, and that is the one conversion most easily forgotten. A plain `-F photo=@mark.jpg` is rejected with **`Bad Request: photo isn't specified`**, which reads like a missing file and is really a missing object; an animated MP4 ≤5s at 640×640 is accepted via the same object form. BotFather `/setuserpic` remains the manual path |
| Marketplace agent avatar (OKX, AgentScan) | The marketplace's own metadata/update call, not a file drop. **OKX**: `onchainos agent upload --file` → returns a `static.okx.com` URL → `--picture "<url>"`; a local path where a URL belongs returns *"not a valid uploaded avatar"*; 500×500, ≤50 KB. **AgentScan**: 400×400 PNG → IPFS |
| Hub, portfolio, repo | A published file path plus whatever links to it |

Set the **group** picture only when the new art is ready — moving a placeholder around the surfaces is
churn the members see and gain nothing from.

### Verifying it was actually applied — per surface, because they differ

An `ok: true` is the call reporting on itself. Compare the surface before and after where the API
allows it:

- **Group photo** — read `getChat`, keep `result.photo.big_file_unique_id`, set the photo, read again.
  A **changed id is proof**; an unchanged one means the write did not land however green the response was.
- **Bot's own photo** — there is **no read-back** (`getMyProfilePhoto` returns `404`, so it genuinely does
  not exist), which makes this the one surface where the API's own `ok` is the only confirmation
  available. Say so plainly instead of implying it was measured; the owner can see the real state in
  their chat list.
- **Paid rail spend** — if the generator reports `cost` as unreported/absent, take the number from the
  **balance delta** across the run rather than quoting the response body or leaving the cost blank.

## Pitfalls

- **A generated file with no generator is a dead end.** If a mark exists but nothing in the repo produces
  it, record how it was made or treat it as frozen history — do not imply a pipeline you cannot re-run.
- **Do not treat "the API needs funding" as "this cannot be done".** Establish the gate, name the exact
  address and amount, and have everything else — brief, script, size, apply path — finished and verified,
  so the owner's single action is the only thing left.
- **A correct format still gets rejected when the mark does not show the work.** OKX refused the same
  agent's avatar twice for *"avatar does not match the agent description"* before a version that
  **depicted the service** passed. A monogram reads beautifully in a chat list and will not survive a
  marketplace that wants the capability shown — so let the venue decide the concept, not just the size.
- **A monogram is the most crowded visual form in software — check for a brand collision before you apply.**
  A letter in a ring or a letterform in negative space occupies, at 40px, exactly the visual space every other
  software mark does, so it maximises the chance of reading as somebody else's product. Run the vision pass as
  a **brand question** ("what existing company or app does this resemble?"), not only a quality question — a
  mark that is beautiful and looks like a well-known learning app is a liability, not a near-miss. Prefer a
  mark that **depicts the work** (the object the agent operates) over one that letters its name; a letterform
  idea that only survives at full size is dead at the size it will actually be seen.
- **A concept that wins on cleverness can still lose at the smallest size.** Judge each variant at 40px before
  spending on another: a letter hidden in negative space reads as the letter at 1024 and as nothing at 40, so
  the legible object usually beats the ingenious one.
- **Do not let one identity's mark stand in for another.** Per-agent, per-department and per-group marks
  are separate files; reusing one because the palette matches is how identities get muddled.

## Related

- `brand-assets` — GenTech brand palette, SVG-first logo workflow, AI-vs-SVG decision table.
- `key-custody-and-recovery` — the wallet/address assertion gate any paid image rail needs (the former
  `agent-capital-custody-and-recovery` body is preserved under its `references/`).
