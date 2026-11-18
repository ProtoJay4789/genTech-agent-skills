# Avatar construction — circle-safe geometry and the even rim

Companion to the "Avatars — the small-size discipline" section in SKILL.md. These are the concrete
recipes behind those rules. Adjust the radii to the source size; the ratios matter more than the
pixels (examples assume a 1024² source).

## 0. The order that works

1. Fix the **tone** (palette/lighting) before anything decorative — a collapsed silhouette is the
   real defect and everything else is noise until it is fixed.
2. Place any mark by **geometry** against the crop radius; discard marks that cannot fit.
3. Build the **ring** last, from layers (backing disc → masked portrait → gap → gradient ring → glow).
4. Test at 160px on **both** page backgrounds.
5. Look at it **and** measure a face-region luminance. Then show the user.

## 1. The circle the platform will crop to

```python
S = im.size[0]; cx = cy = S // 2; R = S // 2     # crop radius = half the width
# a mark survives only if it fits inside:
import math
inside = math.hypot(mx - cx, my - cy) < R
```

A 1024² source crops to r=512. Practical safety margin: keep content inside ~0.78·R if the platform
may also apply a slightly tighter mask.

**Cheat sheet for placement decisions:** the chest of a head-and-shoulders portrait typically falls
at r ≈ 0.7–0.9·R from centre — i.e. right on the crop edge. The space *above the hair* is usually
only 0.2–0.35·R of clearance and is consumed by hair at the top of the circle. **On a tight portrait
there is often no circle-safe place for a badge at all** — that is a finding, not a failure.

## 2. Composing the portrait + ring (layer order)

```python
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

S = src.size[0]; cx = cy = S // 2; R = S // 2
yy, xx = np.mgrid[0:S, 0:S]
rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

# (a) EVEN rim: blend toward a CONSTANT colour — never add light.
#     Additive tinting brightens the light background more than a dark garment -> uneven rim.
RIM = (38, 116, 225); RIMW = 30; STRENGTH = 0.42
band = np.clip(1 - np.abs(rad - (R - RIMW)) / RIMW, 0, 1) ** 0.9
band = band * (rad < R)
bl = (band * STRENGTH)[..., None]
arr = np.asarray(src.convert("RGBA")).astype(float)
for i, c in enumerate([v / 255 for v in RIM]):
    arr[..., i] = arr[..., i] * (1 - bl[..., 0]) + (255 * c) * bl[..., 0]
# optional: firm the outer seam so the circle holds on a white page
vg = np.clip((rad - (R - 90)) / 90, 0, 1) * 0.18
arr[..., :3] *= (1 - vg[..., None])
portrait = Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).convert("RGBA")

# (b) dark backing disc — gives the gap something to be, on BOTH themes
canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(canvas).ellipse([cx - 522, cy - 522, cx + 522, cy + 522], fill=(8, 11, 17, 255))

# (c) the portrait, MASKED — this is the step that must NOT use fill= on the gap
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse([cx - 496, cy - 496, cx + 496, cy + 496], fill=255)  # mask fill IS correct
mask = mask.filter(ImageFilter.GaussianBlur(1.0))
ph = portrait.copy(); ph.putalpha(mask)
canvas = Image.alpha_composite(canvas, ph)

# (d) the ring — an ANNULUS (outline=) with a directional gradient + glow
ringmask = Image.new("L", (S, S), 0)
ImageDraw.Draw(ringmask).ellipse([cx - 507, cy - 507, cx + 507, cy + 507], outline=255, width=14)
t = np.clip((xx + yy) / (2 * S), 0, 1)                 # 0 top-left -> 1 bottom-right
top, bot = np.array([132, 208, 255]), np.array([22, 86, 188])
ga = np.zeros((S, S, 4), dtype=float)
for i in range(3):
    ga[..., i] = top[i] * (1 - t) + bot[i] * t
ga[..., 3] = 255
gradient = Image.fromarray(ga.astype("uint8"))
ring = Image.composite(gradient, Image.new("RGBA", (S, S), (0, 0, 0, 0)), ringmask)
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([cx - 507, cy - 507, cx + 507, cy + 507], outline=(58, 138, 235, 110), width=20)
glow = glow.filter(ImageFilter.GaussianBlur(10))
canvas = Image.alpha_composite(canvas, glow)
canvas = Image.alpha_composite(canvas, ring)
```

**Why a backing disc + a masked portrait:** the gap between portrait edge (r=496) and ring inner edge
(≈r=500) shows the backing disc. Without it the "gap" is transparent and disappears on a light page.

## 3. The gap/annulus trap

```python
# ❌ WRONG — fill= paints a SOLID disc straight over the subject
d = ImageDraw.Draw(im)
d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(8, 11, 17, 255))

# ✅ RIGHT — outline= draws only the ring; or composite a masked layer
d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(8, 11, 17, 255), width=14)
```
`fill=` fills the interior, `outline=` strokes the boundary. Reaching for `fill=` when you mean a
separator erases the artwork and produces an image that looks *finished* and empty.

## 4. Verification — the two checks that must both pass

```python
from PIL import Image, ImageDraw
import numpy as np

# (a) the subject survived — MEASURE, do not eyeball
chk = np.asarray(canvas.convert("RGB")).astype(float)
face = chk[380:520, 430:600].mean()          # sample the face region for YOUR framing
assert face > 60, f"face looks wiped: luma {face:.1f} (a wiped face reads ~10)"

# (b) the 160px circular composite on both themes
def circ(im, size=160):
    y = im.resize((size, size), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    y.putalpha(m); return y
for bg, label in (((13, 17, 23), "dark"), ((255, 255, 255), "light")):
    page = Image.new("RGB", (400, 215), bg)
    page.paste(circ(canvas), (20, 28), circ(canvas))
    page.save(f"check-{label}.png")
```

Then run the vision pass on `check-dark.png` and `check-light.png` — the dark one is where tonal
collapse shows. Ask the reviewer explicitly whether the silhouette reads all the way around, and
whether any text is legible; a confabulated reading is a fail.

## 5. Measuring "happier" — don't trust the expression alone

Re-rendering an expression changes the face; it does not change the mood at small size. Measure the
mood instead:

```python
a = np.asarray(img.convert("RGB")).astype(float)
bg   = a[10:120, 380:640].mean(axis=(0, 1))     # background band above the head
face = a[380:520, 430:600].mean(axis=(0, 1))    # face region
print(f"bg luma {bg.mean():5.1f} | face luma {face.mean():5.1f} | warm ratio {face[0]/max(face[2],1):.2f}")
```

A background luma in the 50–60 range against a dark page reads closed and moody however the mouth is
drawn; lifted toward ~110 it reads open and approachable. Report both numbers, and if the winning
render changed more than one variable, say so — an unattributed win is not a verified cause.
