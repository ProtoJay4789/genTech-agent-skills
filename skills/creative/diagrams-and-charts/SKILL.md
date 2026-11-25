---
name: diagrams-and-charts
description: "Use when a system or measured numbers need a picture."
version: 1.1.0
author: Arthur (EDU)
license: MIT
metadata:
  hermes:
    tags: [diagrams, charts, svg, honesty, visualization]
    related_skills: [architecture-diagram, concept-diagrams, code-wiki]
tags: [diagrams, charts, svg, honesty, visualization]
---

# Diagrams and charts on this seat

## When to Use

- A lesson, handoff, or report needs a **picture of a system** — architecture, flow, pipeline, layers, data model.
- A set of **measured numbers** needs a chart, especially when some values were never measured.
- A Mermaid block already exists somewhere (a wiki, a note) and needs to become a **real SVG file** with a
  pass/fail on its layout.
- You are about to install a charting or diagramming library and should first check what this seat already has.

**Not this skill:** dark-themed HTML visuals for pages and decks — `architecture-diagram` and
`concept-diagrams` already own that destination. Use this one when the picture must be **checked and
regenerable**, not when it must be **styled**.

Two different jobs, two different tools. Do not force one to do the other.

| Need | Tool | Why |
|---|---|---|
| Architecture, flow, pipeline, data model, layers | **`open-diagram`** (pip) | measures labels from the font, checks its own layout, names collisions |
| Data charts — bars, comparisons of measured numbers | **`EDU/visuals/chart.py`** | no dependency, and it CANNOT draw a missing value as zero |
| A PNG for Telegram / a slide | **browser harness** (see below) | headless Chrome needs `--no-sandbox` here; the libraries don't pass it |

## Diagrams — open-diagram

```bash
python3 -m venv .venv && .venv/bin/pip install open-diagram   # no root needed
```

Describe panels/tiles/links in ~12 lines, or JSON, or Mermaid. It writes SVG always, PNG only if a
usable Chrome is found. `describe()` returns the picture in plain words — use that to verify the picture
matches the request without looking at it.

```python
from open_diagram import Diagram, Panel, Tile
d = Diagram("GenTech fleet", tag="M0")
src = d.add(Panel("Sources", ["30 ATS boards", "X / Tavily"]))
eng = d.right_of(src, Panel("Engine", [Tile("Scorer"), Tile("Level gate", status="building")]), align="center")
d.link(src, eng)
d.save("fleet")
```

**Known blocker — PNG.** It prints *"Chrome or Chromium not found"*, which is FALSE. The real error is
`No usable sandbox!`: this container disables unprivileged user namespaces and the library omits
`--no-sandbox`. `svg_to_png()` returns False for ANY failure and the caller always blames a missing
browser. Don't chase the browser; use the harness.

### The Mermaid bridge — the highest-value use

`code-wiki` already emits ```mermaid flowchart TD``` in its `templates/architecture.md`. open-diagram reads
Mermaid and re-lays it out **with measurement and collision checks**, so text that used to render only in a
Mermaid-aware viewer becomes a real SVG with a pass/fail:

```bash
open-diagram check flow.mmd      # 0 layout problem(s)  -> exit 0
open-diagram describe flow.mmd   # plain words, verify before showing anyone
open-diagram draw flow.mmd       # writes flow.svg
```

Verified on code-wiki's own template (640x512, 0 problems). **It re-lays out and does NOT preserve the
author's direction** — `TD` came back left-to-right. That is fine when the check is the point; do not promise
direction fidelity.

## Charts — `EDU/visuals/chart.py`

No matplotlib/numpy here (measured). This emits SVG directly.

```python
import sys; sys.path.insert(0, "/opt/data/.obsidian-vault/EDU/visuals")
from chart import Chart
c = Chart("Scanner level split", y_label="roles", sub="175 of 7,684 roles · 30 boards")
c.bar("junior", 7, "#2E7D4F"); c.bar("mid-band", 98); c.bar("never measured", None)
c.save("levels")          # raises ChartProblem if the layout is bad
print(c.describe())        # plain words, agent-checkable
```

### The rule that makes this ours

**A value of `None` is UNMEASURED and is drawn as a hatched full-height slot labelled UNMEASURED.** It is
never drawn as zero, because a chart that renders "we never measured this" as `0` is a fabricated number
wearing a picture — and unlike a sentence, nobody audits a chart.

- A chart where **every** row is `None` **refuses to render** (`UnmeasuredChart`).
- Bars scale into `ph - LABEL_BAND` so a value label can never climb into the subtitle band.
- A chart too short to hold the label band reports a problem by name.
- `python3 chart.py --selftest` proves all of the above can fire. Run it after any edit.

## Getting a PNG (Telegram, slides)

Headless Chrome here needs `--no-sandbox`, and it hangs on `file://…svg`, so drive the harness:

```python
new_tab("file:///abs/path/diagram.svg"); wait_for_load()
cdp('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=2, mobile=False)
capture_screenshot()   # then copy the path into the vault
```

Set width/height slightly above the SVG's own size (it prints `WxH` on save).

### No SVG yet? Render Mermaid in the browser instead

When the diagram is Mermaid source and `open-diagram` is not installed, skip the library: put the Mermaid block in
a local HTML page that loads the runtime from a CDN, open it, screenshot the rendered SVG. One file, no venv.

```html
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<pre class="mermaid">flowchart TD … </pre>
<script>mermaid.initialize({startOnLoad:true, theme:'base',
  themeVariables:{fontFamily:'Helvetica, Arial, sans-serif'},
  flowchart:{curve:'basis', nodeSpacing:44, rankSpacing:62, useMaxWidth:false}});</script>
```

```python
new_tab("file:///abs/path/diagram.html"); wait_for_load(); time.sleep(6)   # mermaid renders async
print(js("document.querySelector('.mermaid svg').getBoundingClientRect().height"))
cdp('Emulation.setDeviceMetricsOverride', width=1280, height=SVG_H+40, deviceScaleFactor=2, mobile=False)
capture_screenshot()
```

**Measure before you shoot.** Read the rendered SVG's own `getBoundingClientRect()` and size the viewport from
that — not from the nominal diagram size. A viewport shorter than the rendered diagram yields a **silently
clipped** PNG that looks complete until someone reads the bottom of it; `getBoundingClientRect().height` against
`innerHeight` is the check. `deviceScaleFactor: 2` gives a crisp image at README size.

**Subgraph labels collide with the nodes beneath them.** Mermaid draws each subgraph's title at its top edge, so
a title on one line and a node row on the next overlap. Fix by shortening the titles (two or three words) and
raising `rankSpacing` / `nodeSpacing` — not by moving nodes. Re-render and look at it; the collision is invisible
in the source.

Keep the `.html` next to the `.png` and a `.mmd` beside both: the PNG is an output, and the next edit needs the
source.

## Pitfalls

- **A check that cannot fail at the current geometry is decoration — replace it, do not keep it.** After fixing
  an overlap by reserving space, the assertion that had caught it became geometrically impossible (the label
  could no longer reach the band), so it could never fire again. The reachable failure in that shape is the
  *chart too small to hold the reserved band*, so that is what the check tests now — and the selftest builds a
  90px-tall chart to prove it fires. **When a fix removes a defect's geometry, move the assertion to the
  condition that can still fail, and construct that case once.**
- **A test that greps the whole artifact will match its CHROME, not its content.** Asserting "no zero value"
  against the full SVG failed a correct chart because the y-axis tick at zero carries the same markup as a value
  label. **Strip the furniture before asserting on content** (drop `text-anchor="end"` axis ticks, then look for
  the value), and re-run the test against a known-good artifact once — a guard that fails correct output gets
  disabled by the next person, which is worse than no guard.
- **Verify the picture, not the status code.** A 200 from a diagram host can be an error page; a green from
  a chart tool proves nothing. Look at the rendered image.
- **Check your own chart for the collision you were about to criticise.** The first real chart this tool
  drew overlapped its subtitle, and its own checker missed it. A collision detector that only checks the
  axis is decoration — test the thing you claim to guard.
- **Don't put a young dependency on a load-bearing path.** open-diagram is MIT, single-author and days
  old: vendor it if it becomes essential.
- **Cloud icons (AWS/Azure/GCP) are Python-only and NOT MIT** — they are the vendors' marks under their own
  terms. Credit them when sharing.
- **MCP mode needs `uv`**, which is absent here. `pip install "open-diagram[mcp]"` is the untested no-uv path.
