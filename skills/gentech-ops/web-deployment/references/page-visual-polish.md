# Making a page look like it was typeset, not generated

**Use when a page is functionally done and the feedback is "make it look better" — or before publishing a page whose
job is to be read by a stranger.** The loop below produced the accepted result on the first revision after a
one-line brief; the first version had passed every functional check and still read as an unstyled template.

---

## The loop (do not skip the review steps)

1. **Render at two widths and LOOK.** 390px (phone) and 1280px (desktop). A page judged only in source is not judged.
2. **Ask a vision model for a designer's critique, not a description** — "what looks weak, dated, or unpolished; be
   specific about typography, hierarchy, spacing, and what would make it premium."
3. **Fix the whole list at once, redeploy, re-render, re-review.** Two or three passes is normal; one is luck.
4. **Assert mechanically what the eye cannot:** no horizontal overflow (`scrollWidth > innerWidth`), no line of prose
   past ~75 characters, no token split across lines, every font actually loaded (`document.fonts.check`).
5. **Cache-bust before every review pass** (see the pitfall in SKILL.md) — a stale render manufactures defects.

## Typography is the single biggest tell

- **One system font at every size reads as "unstyled HTML".** Ship a real text face for body and a mono for tokens,
  labels, brand and code. **Self-host it:** download the `woff2` from the foundry/CDN once into `/fonts/`, serve it
  from your own origin with `font-display: swap` and `<link rel=preload>`. **No third-party font CDN in the critical
  path** — it adds a failure mode and a tracking surface for a page that is trying to look trustworthy.
- **Modern CSS families ship as a single VARIABLE file.** Fetch the family once and assert the signature is `wOF2`;
  three "weights" that download at byte-identical sizes are one variable file, so keep one and declare
  `font-weight: 100 900`. Shipping three copies costs 3× for nothing.
- **Display sizes need negative tracking** (`letter-spacing: -.03em`) and `font-weight: 800`; without it a large
  heading reads loose and amateur. Use `clamp()` so the same rule works at 390 and 1280.
- **Give the one important token its own treatment** — the protocol name, the price, the version. Mono inside a subtle
  tinted chip signals craft and survives translation into code blocks.
- **Kickers are microtype, not subtitles:** 11–12px, uppercase, `letter-spacing: .14em`, muted. A kicker at body size
  cannot decide whether it is a label or a paragraph.

## Structure beats decoration

- **Pull the numbers out of the prose into a stat strip** (3–4 large numerals over small caps labels, hairline rules
  above and below). A data-led page whose only numbers are inside a paragraph hides its own argument.
- **Colour exactly one number**, and make it the honest one. If the flattering number is coloured and the
  unflattering one is grey, the design is lying on the data's behalf.
- **Use an 8pt spacing scale with named tokens** (`--s1..--s8`) instead of per-block margins; inconsistent rhythm is
  what makes a hand-built page feel improvised.
- **Cards carry: index → title → status pill → labelled rows** (`COST` / `REQUIRES` / `GOTCHA`). Label-above-value on
  phones, two columns on desktop, via one `grid-template-columns` media query.
- **Tint status pills by meaning** (teal = go, amber = wait, rose = stop) with a matching border and 8–10% fill. Never
  a saturated solid fill — it becomes the loudest thing on the page.
- **Depth comes from hairlines and one radial glow**, not shadows: `inset 0 1px 0 rgba(255,255,255,.045)` on cards and
  a single top-edge `radial-gradient` behind the hero.
- **Set `color-scheme: dark`** on a dark page, or the browser paints a light scrollbar and form controls against it.

## Measure and line-breaking

- **Body 60–75 characters; a callout at 105 characters is the longest and most-read paragraph on the page and the
  worst place to be lazy.** Cap prose blocks with `max-width: 62ch` rather than shrinking the type.
- **Keep tokens whole:** `code { white-space: nowrap }` — a chip that wraps mid-token renders as two different
  identifiers, and readers believe what they see.
- **Bind small phrases with `white-space: nowrap`** so a headline cannot leave an article orphaned ("an" alone on a
  line) and a kicker cannot strand its separator at a line end.
- **Verify the binding did not create overflow** — nowrap on a group that is too wide is worse than the wrap it fixed.

## Accessibility and touch, checked not assumed

- Muted labels at 10–11px sit near 4.5:1 on a near-black field; lift the token until it clears AA rather than
  eyeballing it.
- Nav links need real hit area (`padding: 8px 2px`) — a 15px text link in a 44px bar is a miss on a phone.
- `@media (prefers-reduced-motion: reduce)` kills every transition you added.

## What to report back

List what changed and **why each change exists** ("the pill was a two-line capsule fighting its own text"), then the
measured state: byte count, fonts `200`, no horizontal overflow at 390, the capped measure. **Attach the phone
screenshot** — the owner judges the render, not the diff.
