---
name: demo-video-production
description: "Automated demo video pipeline: html-video (HTML→MP4 via agent + 21 templates) as primary, HyperFrames for custom GSAP compositions, Remotion as legacy fallback. Natural language or GitHub repo link → polished MP4. Covers hackathon demos, product promos, portfolio showcases, and social content."   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `hackathon` exists on this seat -->
version: 2.0.0
author: Gentech
tags: [demo, video, html-video, hyperframes, hackathon, automation, ffmpeg, templates]
trigger: "When building demo videos for hackathon submissions, product demos, portfolio pieces, or social content. Also triggers when the user mentions html-video, video rendering, screen recording editing, programmatic video generation, or 'make a demo video'."
related_skills:
  - hackathon  # submission materials pipeline
  - hyperframes  # custom GSAP compositions
  - voice-content-production  # voiceover generation
---

# Demo Video Production

## Overview

Automated pipeline for creating polished demo videos. **html-video** is the primary tool — describe what you want (or paste a GitHub repo link), the agent picks a template, fills in content, and renders MP4 locally. No cloud fees, no per-render costs.

## Pipeline Selection

| Need | Tool | When |
|------|------|------|
| **Quick demo from description/link** | html-video | Default. Natural language → template → MP4 |
| **Custom GSAP animation** | HyperFrames | When you need specific motion graphics, audio-reactive, or shader transitions |
| **React-based programmatic video** | Remotion | Legacy fallback only. Complex multi-component compositions |

**Default: always try html-video first.** Only drop to HyperFrames/Remotion if html-video's 21 templates don't cover the use case.

## Primary Pipeline: html-video

### Setup (one-time)

```bash
cd /root && git clone https://github.com/nexu-io/html-video.git
cd html-video && pnpm install && pnpm -r build
```

Verify: `node packages/cli/dist/bin.js doctor` — all checks should be OK.

### Quick Reference

```bash
# Search templates by intent
node packages/cli/dist/bin.js search-templates --intent "product demo dark theme" --top 3

# Create project + set template + render
node packages/cli/dist/bin.js project-create --name "My Demo" --intent "AI agent framework promo"
node packages/cli/dist/bin.js project-set-template <project-id> --template frame-product-promo
node packages/cli/dist/bin.js project-render <project-id> --output /tmp/demo.mp4

# Launch browser studio (interactive)
node packages/cli/dist/bin.js studio --port 3071
# → http://127.0.0.1:3071
```

### 21 Templates (Apache-2.0 / MIT, license-clean)

**Data Viz:** NYT-style charts, Swiss/Vignelli grids
**Titles & VFX:** Glitch, kinetic type, typewriter cursor
**Heroes:** Liquid gradients, light-leak, warm grain
**Product Promos:** 15s/30s multi-scene
**Explainers:** Decision trees, flow diagrams

### Workflow: Description → Video

1. **Pick template:** `search-templates --intent "your description"`
2. **Create project:** `project-create --name "..." --intent "..."`
3. **Set template:** `project-set-template <id> --template <template-id>`
4. **Render:** `project-render <id> --output demo.mp4`

Or use the **studio UI** at port 3071 — pick template, chat with agent, edit frames, add soundtrack, export.

### Workflow: GitHub Repo → Video

Paste a repo URL into the studio. The agent fetches README + structure via GitHub API, generates a multi-scene explainer video automatically. Great for:
- Hackathon project explainers
- Portfolio project promos
- Open source showcases

### Soundtrack (Optional)

MiniMax integration for AI-generated music + narration:
- **Background music:** Describe a mood → MiniMax generates instrumental
- **Narration:** Type a script → MiniMax TTS
- Both mixed into exported MP4 (music ducked under voice)

No API key configured? Rest of studio works unchanged.

### Render Specs

- **Resolution:** 1920x1080 default, supports 16:9
- **FPS:** 30 default, supports 60
- **Engine:** Hyperframes (headless Chromium + ffmpeg, libx264)
- **Local only:** No cloud render, no per-clip fee

## Fallback: HyperFrames (Custom GSAP)

When html-video templates don't cover the need (custom motion graphics, audio-reactive, shader transitions):

```bash
npx hyperframes init my-video --non-interactive
npx hyperframes preview           # live preview at port 3002
npx hyperframes render --quality high --output final.mp4
```

See the `hyperframes` skill for full GSAP animation, captioning, TTS, and audio-reactive capabilities.

## Fallback: Remotion (Legacy)

Only for React-based programmatic video with complex multi-component compositions. Project at `/root/repos/hackathon-demos/`.

## Title Screen Generation

Static title screens for videos/thumbnails — render HTML to PNG via Chrome headless:

```bash
google-chrome --headless --no-sandbox --disable-gpu \
  --screenshot=/path/to/output.png --window-size=1920,1080 \
  /path/to/title.html
```

**Pitfalls:**
- Chrome headless requires `--no-sandbox` when running as root.
- **Google Fonts do NOT load in headless Chrome.** Slides render blank text. Always use system fonts: `Liberation Sans, DejaVu Sans, Arial, sans-serif` for body text, `DejaVu Sans Mono, Courier New, monospace` for code. Verify with `fc-list` what's available.
- Emoji rendering may be inconsistent — prefer text labels or simple Unicode (→, ←) over emoji in headless renders.

## Quick Slide-to-Video Pipeline

For hackathon demos where you need polished slides fast:

1. Create one HTML file per slide (1920x1080, dark theme, system fonts)
2. Render each to PNG: `google-chrome --headless --no-sandbox --disable-gpu --window-size=1920,1080 --screenshot=slide.png slide.html`
3. Create ffmpeg concat file (list each PNG with `duration 4`)
4. Combine: `ffmpeg -y -f concat -safe 0 -i concat.txt -vf "fps=30,format=yuv420p" -c:v libx264 -pix_fmt yuv420p -movflags +faststart output.mp4`

This is faster than html-video templates when you need custom content per slide. Use html-video templates when you want GSAP animations.

## Source-Clip Meme Edits (Downloaded Clip + drawtext Overlays)

Transform a downloaded source video (X/Twitter clip, TikTok, etc.) into a captioned meme short with ffmpeg drawtext — terminal boot logs, staggered captions, title/punchline cards. **Free, no model costs.** Proven: "Gentech Boot Sequence" (rowers whirlpool clip → 9 agents powering on, Jul 2026).

### Workflow

1. **Get the source clip** — for X/Twitter, fxtwitter API returns the direct mp4 URL + thumbnail:
   `curl -s "https://api.fxtwitter.com/i/status/{ID}"` → parse `media.videos[].url`, then `curl -sL` download it. Check `ffprobe` for dimensions/duration (vertical 720x1280 = reel format).
2. **Build the edit in ONE ffmpeg call** — lavfi color title card → concat with processed source:
   - Title card: `-f lavfi -i "color=c=black:s={W}x{H}:d={D}:r=30"` + drawtext centered
   - Source overlays: persistent terminal prompt (boxed), staggered caption lines with `enable='between(t,start,end)'`
   - Punchline card: `enable='gte(t,N)'`
   - Concat + encode: `[title][vid]concat=n=2:v=1:a=0[vout]`, `-c:v libx264 -crf 23 -g 48 -keyint_min 48 -pix_fmt yuv420p -movflags +faststart`
3. **Verify before delivering (MANDATORY)** — extract frames at key moments, crop the text band (`-vf "crop=720:320:0:430"`), `vision_analyze` reading text verbatim. Never ship an unverified overlay.
4. **Deploy** — `cp` to `/var/www/gentechlabs/videos/` with a FRESH filename (Cloudflare cache — see pitfall #16 below), verify `curl -sI` returns HTTP 200, deliver via `MEDIA:` path + shareable link.

Full reproducible command: `references/ffmpeg-drawtext-meme-edit-command.md`

### Pitfalls (drawtext)

- **`alpha=` expressions do NOT evaluate per-frame in drawtext.** A fade-in like `alpha='if(lt(t,30.2),0,min(1,(t-30.2)*2))'` silently renders the text invisible for the ENTIRE clip (evaluated once, not per frame). Use `enable='gte(t,N)'` for time-gated appearance — it works, proven. No per-frame alpha fades in drawtext.
- **`enable` timestamps run on the SOURCE clock BEFORE concat.** With a 2.2s title card concat'd in front, all overlay windows shift +2.2s in the final output. Verify at `final_t = source_t + title_duration`, not the intended display time — checking too early makes correct text look missing (cost two verification rounds, Jul 2026).
- **Never inline `text=` for user-visible strings — use `textfile=`.** Inline drawtext text fails on `%`, on a
  bare `/`, and on `:` — and it fails **at render time**, not at parse time, with the signature
  `Nothing was written into output file, because at least one of its streams received no packets` plus
  `libx264 … Terminating thread with return code -22`. So one bad line in frame 4 kills a video whose frames
  1-3 already rendered, and the error names libx264 rather than the text that caused it. **Backslash escaping
  is not the fix** — the filter graph is parsed twice, so `\:` / `\,` / `\%` are consumed by the first pass and
  the second pass sees the bare character again. Write each string to its own file and pass
  `textfile=/path/t0_3.txt`; there is no escaping left to get wrong. Keep a bash `esc()` helper only for
  single-line ad-hoc proofs, never for a script that must run unattended. **And if a renderer already has an
  `esc()` that returns its input unchanged, delete it** — a function named for a job it does not do is read
  by every later maintainer as "escaping is handled here", which is worse than no helper at all.
- **Verify by reading pixels, not by trusting the exit code.** Extract a still from each distinct frame
  (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`) and read the text back with `vision_analyze`, checking for
  clipping at the right edge. A render can succeed and still ship text that overflows or never appeared.
- **Box behind text** — `box=1:boxcolor=black@0.55:boxborderw=8` keeps captions readable over busy video (splashing water, crowd motion).
- **Mono font for terminal aesthetics** — DejaVu Sans Mono at `/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf`; check `fc-list` for alternatives.

## Demo From Measured Output (no screen recording, no customers)

When a form asks for "a 1-minute demo" and there is **no recording to cut and no users to show**, do not
fabricate one and do not silently skip the field. Render a terminal-style explainer whose every line is a
command you actually ran or a value you actually read.

**Procedure**

1. **Collect the evidence first, video second.** Run the calls and capture real output before writing a
   frame: the live JSON response, the response headers, a decoded payment/quote payload. If a fact cannot be
   measured, it does not go in the video.
2. **One frame per fact, 4-8 seconds each.** Open with the product name, then the real output, then the
   structural proof (headers, challenge, registry listing), then the honest numbers, then the address.
3. **Include an honesty frame — it is the strongest frame in the video.** State what is *not* true yet as
   numbers and what is deliberately not served (`n of m servable, the rest declared unservable with
   reasons`). A reviewer who checks will find the gap anyway; showing it first turns the one thing they
   could hold against you into evidence of discipline.
   **But an honesty frame is where a fabricated zero hides best**, because a humble number reads as
   discipline and nobody audits it. **Never put `0` on screen for a quantity your instrument does not
   record.** Measured: a headline honesty line read *"0 paid calls · 0.000000 USDC received"* while an
   independent ledger showed four paying wallets and one returning payer — the traffic log had **no
   payment field at all**, so the zero was an absence of data wearing the costume of a measurement, and
   it was about to go on a grant application over the operator's signature. **Before any zero ships,
   print the schema of the source you are reading:** if the field is absent, the honest options are
   (a) take the figure from the ledger that *does* record it (a payment/settlement ledger, an outside
   observatory) or (b) drop the number and say the metric is not instrumented. "One agent paying
   repeatedly" is a stronger and safer sentence than a false zero — small-and-real beats none.
4. **Never include a settlement/transaction frame you cannot produce.** If no payment has landed there is no
   receipt, and an implied one is a fabricated receipt.
5. **Render, then read it back.** Frames → MP4 → extract stills → `vision_analyze` for legibility and clipping.
6. **Deliver the file, not a promise**, and say what each frame contains.
7. **Re-measure every on-screen number AFTER the render, and treat drift as a re-cut rather than a footnote.**
   Live counters move while you encode — a caller count written into frame 3 can be stale by the moment the
   file exists. Keep a claims sheet (`claim → verified value → status`) and re-probe it when the render lands;
   a submission built on last-hour numbers needs last-hour evidence. **Prefer a rounded floor for any figure
   the video will live with for months** ("over twelve hundred callers") over an exact count that is wrong
   within the hour — but never round UP, and never round a bucket you did not classify ("all of them
   crawlers" becomes "each a crawler, an indexer, or one of our own probes" when part of the traffic is
   unclassified).
8. **Quote arrays in PAYLOAD ORDER, and say which element is first.** When a frame reproduces a list from a
   live response (payment rails, chains, endpoints), the order IS information: a client that reads the first
   element and signs for it gets a different result than a client reading the second. Rebuild the list from
   the live payload at render time, never from an older note — measured: a rail list written days earlier led
   with the rail a standard client is *least* able to sign, while the live challenge led with a different one,
   and the video would have contradicted the thing it was demonstrating. If the ordering itself changed, that
   is a re-cut, and the small print should name the lead element (`accepts[] order — X first`).
9. **A video has two channels, and pixels do not prove the words.** Extracting a still and reading it back
   verifies typography; it says nothing about what the narrator said. When the read changes but the card does
   not (or the reverse), report exactly that — *"card verified from pixels; narration not transcribed"*.
   Claiming "I verified the video" after checking one channel is the same class of false receipt as reporting
   a wake that never landed.

`templates/measured-demo-renderer.py` is a working starting point: textfile-based frames, per-frame durations,
concat, and an `ffprobe` duration read-back.

### Timing the picture to the voice, not the voice to the picture

**Generate the voiceover FIRST, one clip per frame, measure each clip, then let those measured durations
BE the frame durations.** Writing frame lengths first and stretching the audio to fit (`atempo` across a
single long read) makes speech and text drift apart, and the drift grows with every section — by the last
frame the narrator is describing something that left the screen ten seconds ago.

1. Split the script into one paragraph per frame; synthesise each separately (`text_to_speech` takes a
   `speed`; pick it so the natural read lands NEAR the target — a 60s slot usually wants ~1.2–1.3 — rather
   than fixing it all with time-stretch afterward).
2. `ffprobe` every clip; those are the frame durations. Sum them; if the total misses the slot, apply ONE
   uniform `atempo` to all clips and re-measure — a single factor keeps relative pacing intact.
3. Render each frame at exactly its clip's duration, concat video and audio separately, then mux with
   `-shortest`. Result: 60.000s, and no frame can outlive its sentence.
4. **Verify all three channels before delivering:** duration (`ffprobe` = exact target), non-silent audio
   (`ffmpeg -af volumedetect` → print `mean_volume` and `max_volume`; a mux can succeed with a dead track),
   and pixels (extract a still per claim-bearing frame and transcribe it with `vision_analyze`).
5. **When the brief asks for a SLOW, explanatory read, the fit direction inverts — cut copy, never speed the
   voice.** A deliberate cloned read runs ~115–125 wpm (≈150 words per 60s, not 200), and a comma-chained
   paragraph adds seconds per comma. Rewrite the script into short sentences and apply a slowing factor
   (0.90–0.97); raising `speed` past ~1.2 is the one edit that destroys the cadence the brief asked for.
   Landing the slot exactly is a pad→trim→fade→`loudnorm` step on the joined track, not a fractional tempo.

Full procedure with the filter graph and the mux commands: `references/voice-timed-frames.md`.

## Dashboard Screenshots (HTML→PNG)

For data visualization dashboards that render to PNG screenshots (milestone trackers, portfolio views, agent performance cards), use the same headless browser pipeline as video production.

### Theme System

| Theme | Colors | Best For |
|-------|--------|----------|
| **Gold** | Dark + gold accents | Milestone celebrations, DeFi |
| **Green** | Dark + green accents | Position tracking, yields |
| **Cyberpunk** | Dark + neon green/blue/purple | Agent performance, tech |
| **Minimalist** | White/light + clean | Professional, reports |
| **Retro Gaming** | 8-bit, pixel art | Fun, social, squads |

### Data Binding

Use `{{variable}}` syntax for template variables:

```html
<div class="stat-value">{{position.total_usd}}</div>
<div class="progress-bar-fill" style="width:{{milestone.progress}}%">
    {{milestone.progress}}%
</div>
```

### Screenshot Generation

```python
from playwright.sync_api import sync_playwright

def generate_screenshot(html_path, output_path, width=1400, height=900):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_path}")
        page.screenshot(path=output_path, full_page=True)
        browser.close()
    return output_path
```

### Dashboard Types

1. **Milestone Tracker** — Progress toward financial goals (position, APR, milestones)
2. **Yield Farm Detail** — Deep-dive into position mechanics (token breakdown, fees, range)
3. **Agent Performance** — What the agent is doing (status, actions, metrics)
4. **Squad Dashboard** — Competitive view for teams (leaderboard, combined stats)
5. **Celebration Card** — Milestone achievement announcement
6. **Alert Card** — Urgent notification requiring action
7. **Weekly Summary** — Periodic performance review

### Design Principles

1. Dark mode by default — better contrast for screenshots
2. Mobile-first — Telegram screenshots at 1400x900 viewport
3. Consistent branding — GenTech colors (gold/green/blue)
4. Data is visual — progress bars, composition bars, color-coded stats
5. Context matches emotion — calm for daily, exciting for celebration, urgent for alert

### Pitfalls

- **Viewport size matters** — Telegram screenshots look best at 1400x900
- **Font loading** — Local fonts may not render in headless browser; use system fonts
- **Template variables** — Always provide defaults; missing data should show "N/A" not blank
- **Color contrast** — Ensure text is readable on dark backgrounds

### Integration

- **Cron jobs** — Generate dashboard on schedule, attach PNG to Telegram message
- **Agent layer** — Generate after each action for before/after comparison
- **Hackathon submissions** — Generate demo screenshots for submission materials

---

## Social Media Engine Integration

The Social Media Engine cron (`e7b632043e30`, Wed/Sat 10am ET) generates text drafts for Gentech + Forge. To produce short-form video from those drafts, extend the pipeline with Remotion rendering on Forge's desktop (RTX 3070).

### Pipeline Flow

```
Wed/Sat 10am → Social Media Engine drafts text → saved to vault
7pm (Forge desktop) → picks up draft → Remotion renders MP4 → Entertainment group
```

### Why Forge's Desktop

Remotion renders via headless Chrome + ffmpeg. Our VPS can do it, but Forge's RTX 3070 is significantly faster. The 7pm cron on Forge's desktop means:
- Rendering happens during Jordan's evening availability
- GPU acceleration for faster encodes
- No VPS resource contention

### Setup Requirements (Forge)

1. **Remotion project** — Set up a Remotion project on Forge's desktop with video templates (talking head, code walkthrough, product demo)
2. **Template components** — React components that take the text draft as props and render frames
3. **Cron job** — 7pm daily cron on Forge's desktop that:
   - Reads the latest draft from the vault (via GitHub sync)
   - Feeds it into the Remotion template
   - Renders MP4
   - Delivers to the Entertainment Telegram group

### Template Ideas

| Template | Use Case | Duration |
|----------|----------|----------|
| Talking head | Steve Harvey-style motivational clips | 30s |
| Code walkthrough | Build-in-public, hackathon demos | 60s |
| Product demo | New feature announcements | 30-45s |
| Text overlay | Quote cards, hot takes | 15s |

### Integration Points

- **Social Media Engine cron** generates the text draft (existing, no changes needed)
- **Vault** stores the draft as a JSON file with timestamp
- **Forge's cron** picks it up, renders, delivers
- **Entertainment group** receives the final MP4

### Pitfalls

- Remotion rendering is CPU/GPU intensive — don't run during gaming sessions
- Ensure the vault is synced to GitHub before Forge's cron runs (vault sync runs every 6 hours)
- First render on a new template is slow (Chrome cache warm-up). Subsequent renders are faster.
- Remotion license: free for individuals and teams ≤3. We qualify.

## Per-Hackathon Color Themes

| Hackathon | Background | Accent | Frame |
|-----------|-----------|--------|-------|
| Somnia | Deep purple/blue | `#00d4ff` (cyan) | macbook |
| Mantle | Dark violet | `#a855f7` (purple) | browser |
| Google Rapid | Navy blue | `#4285f4` (Google blue) | macbook |
| Sui Overflow | Teal/dark | `#6dd5ed` (Sui blue) | macbook |
| Agora | Warm dark | `#f59e0b` (amber) | macbook |

## Multi-Hackathon Pattern

The same project can be demo'd across multiple hackathons with:
1. Different template/config (colors, hackathon name, tagline angle)
2. Same screen recording (if the demo is similar)
3. Different voiceover (tailor the pitch to each track's judging criteria)

This maps to the `hackathon` skill's multi-hackathon submission pattern — build once, demo everywhere.

## Quality Gate (MANDATORY)

**Do NOT publish demo videos to YouTube without review.** Public videos represent GenTech Labs brand.

Before publishing:
1. Test-render a short clip to validate pipeline
2. Review full render for: audio sync, framing quality, text readability, voiceover clarity
3. Get Jordan's explicit approval before upload
4. Write proper title, description, tags for YouTube SEO

A half-baked demo hurts more than no demo. Quality over speed.

**A channel that exists is not a channel we control.** Fetching the public channel URL proves it is visible, not
that anyone on the fleet can publish to it — check for the credential itself (`YOUTUBE*`/`GOOGLE*` env names, an
oauth token file, upload tooling) and say **"the channel exists; ownership unproven; nobody here can upload"**
rather than promising a link. Then hand the upload to the human as one small action (Studio → upload → visibility
**Unlisted** → send the link) and log the URL back against the artifact.

- **Never create a channel, page or account under a personal account to satisfy a company submission.** A public
  surface is the owner's decision, not a producer's convenience.
- **If a link is needed before a human is reachable**, the honest alternatives are: submit the field blank, or ask
  for one word of approval to publish on a surface we already control. Do not quietly route around the approval.

## Handing the cut to another seat (and verifying what comes back)

Producing the source cut yourself and delegating the polished version is often the right split — HQ supplies
measured truth, the social seat supplies craft. The failure mode is a returned file whose report you trust.

**In the brief, state the constraints as prohibitions:** no invented terminal output, no settlement/receipt frame
when no payment exists, keep the honesty frame, keep the total duration, and which screen holds may shrink to pay
for a longer read (never the honesty frame). Give the receiver the **claims sheet** so a number they change is
changed everywhere, and tell them what \"done\" looks like — file path, duration, and a written note in the shared
lane.

**On return, verify the artifact, not the report:**

```bash
ffprobe -v error -show_entries format=duration,size -of default=nw=1 out.mp4
sha256sum out.mp4
diff <(ffmpeg -ss 40 -i out.mp4 -frames:v 1 -f image2 -) /dev/null   # or extract stills and read them
```

Extract a still from every frame that carries a claim and read it back with `vision_analyze`; check audio has a
non-silent stream (`ffprobe -select_streams a`) and that no key or token appears in any log or artifact. **Then say
which channel you verified.** A clean ffprobe plus legible stills does not prove the narration says what the brief
asked for — if you did not transcribe the audio, write *"card verified from pixels; narration not transcribed"*.
That sentence costs one line and prevents the one false receipt a reviewer would find.

**When the brief includes a voiceover, specify the read or the receiver will improvise it.** Give the voice id,
not the voice name; the model (`eleven_multilingual_v2` for any cloned voice — turbo drifts past ~30s on a clone);
the settings; and the segmentation rule (split into ~25–35s chunks, then stitch with re-encode, never `-c copy`,
which produces non-monotonic DTS on MP3 concat). Add one attribution line on the close when the voice is synthetic
(`voice: our cloned council voice · drawn from real measurements`) — on a funder-facing video the disclosure is
an asset, and it is the cheapest defence against "whose voice is that" later. Voice mechanics live in
`elevenlabs-voice-generation`; the demo brief only needs to state them.

## Pitfalls

- **Chrome headless does NOT load Google Fonts.** When rendering slides via `google-chrome --headless --screenshot`, `@import url('https://fonts.googleapis.com/css2?family=...')` silently fails — text disappears or falls back to missing glyph boxes. **Fix:** Use system fonts in headless-only HTML: `font-family: Liberation Sans, DejaVu Sans, Arial, sans-serif`. Available on VPS: Liberation Sans, DejaVu Sans, DejaVu Sans Mono, FreeSans. Google Fonts work fine in html-video (Hyperframes/Puppeteer handles font loading), but NOT in raw `--headless --screenshot` renders.
- **html-video templates have empty input schemas.** The agent generates content by modifying the HTML directly. Don't try to pass `--inputs` with custom data — the templates are agent-driven, not data-driven.
- **Studio renders are local only.** No cloud render. Ensure Chrome + ffmpeg are installed (`doctor` command checks).
- **Recording quality matters more than effects.** A clean 1080p screen recording with good audio beats fancy effects on a blurry recording.
- **Duration sync:** For Remotion fallback, get voiceover duration first (`ffprobe`), then set `durationInSeconds` in config to match.
- **Remotion license:** Free for individuals and teams ≤3. Company license required for 3+ employee orgs. We qualify for free.
- **Probe a provider before repeating a status claim about it — a stale "cancelled / do not use" line is the most
  expensive note in a skill.** It reads as a standing prohibition, so a working capability goes unused and a
  re-cut ships with a weaker voice than the one we already pay for. Verify in two calls: `GET
  /v1/user/subscription` returning `tier` + `character_count` proves the account is alive, and one short
  synthesis proves the voice actually speaks. Measured: this file carried a "cancelled" line while the
  Creator-tier account still held **116k characters of unused headroom** and the cloned council voice rendered
  clean on the first try.
- **Don't force screen recording when it won't work.** If the testnet agents aren't active or the product needs a backend that isn't running, an animated explainer (html-video template) is better than a broken demo. Judges understand constraints — honesty + clean architecture beats a broken live demo.
