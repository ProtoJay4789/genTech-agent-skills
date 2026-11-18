# Rendering a static, styled map (districts, routes, POIs)

Turning open geo data into a finished map image or page: a tourist district breakdown, a service
coverage map, a route map. The `search`/`nearby`/`directions` commands in SKILL.md get you the
DATA; this file is about turning it into an artifact a person looks at.

## The first decision: never generate a map with an image model

**An image model produces a beautiful map with invented streets.** A map someone navigates by, plans
a trip with, or files in a report has to be geographically true — a plausible fabricated road is
worse than no map, because the reader has no way to tell it is wrong. Real base + real geometry is
slightly more work and infinitely more defensible.

## Licensing: what you may ship, and what you may only display

| layer | source | ship in a PNG/PDF? |
|---|---|---|
| satellite/aerial | Esri World Imagery tiles | yes — with visible attribution |
| roads, POIs, boundaries | OpenStreetMap | yes — ODbL, attribution required |
| Google basemap tiles | Google Maps Platform | **no** |

Google's terms (Maps Platform ToS + Map Tiles API policies) forbid precisely the actions a static map
performs: no caching/pre-fetching/storing tiles, no scraping "roads information, places information",
and no including Google Maps Content "in any electronic or printed documents". They also bar
non-visualisation uses (image analysis, geodata extraction, resale).

**The distinction that makes Google usable anyway:** you may pay Google for *data* and redraw it on
your own base — Places/Geocoding/Routes results (names, hours, coords, polylines) rendered by you are
not their tiles. **You cannot ship their *picture*.** So: Google for POI content if the product earns
it, open data for the picture, always.

**Print the attribution on the artifact**, not in the README: `IMAGERY © ESRI · ROADS © OPENSTREETMAP
CONTRIBUTORS (ODbL)`. Both licences require it and a shared image travels without its README.

## Acquiring the data

**Roads (and anything with geometry) — Overpass `out geom`:**

```bash
# POST the query as a FILE — URL-encoding a long query inline is where this fails.
curl -s -m 150 -A "<app-name>/1.0" -X POST \
  --data-urlencode "data@q.overpassql" \
  -H "Accept: application/json" \
  https://overpass-api.de/api/interpreter > roads.json
```

- **Send a User-Agent.** The main endpoint answers **406 Not Acceptable** without one.
- **Prefer the main endpoint; mirrors may time out.** A mirror that hangs wastes the whole budget —
  launch the fetch in the background and build the renderer while it runs.
- **When the endpoint is congested, ask for LESS, more often — TILE the bounding box.** A whole-city
  query for named arterials can be refused outright (502/504, or a long backoff that never clears)
  while the same data is served instantly in four sub-queries. Measured: one bbox for a large capital
  returned nothing across repeated backoff attempts; splitting it into a 2×2 grid returned 1,440 +
  1,353 + 960 + 720 ways **on the first attempt**, and the tiles concatenate into one valid payload.
  Tiling also caps the damage from a partial failure — you lose one quadrant, not the whole map.
- **Only named ways, only road classes you intend to draw**: `way["highway"~"^(trunk|primary|secondary)$"]["name"](s,w,n,e); out geom;`
- **Road names come back in the LOCAL SCRIPT.** Match on the native name (`ถนนสุขุมวิท`,
  `พัทยาสายหนึ่ง`) and map it to the label a reader expects (Sukhumvit Rd, Beach Rd) in your config.
  This is the step that surprises every non-English destination.
- **A name exists in two languages and only one of them helps the reader.** OSM commonly carries the
  native form in `name` and a Latin form in `name:en`. Emit `name:en` when present, fall back to `name`,
  and keep the native form for MATCHING (geocoding, tag filters) — a map or a suggestion list that
  renders `หาดพัทยา` to a traveller has told them nothing they can use. Same order applies to any label
  a person reads: reader's language first, native form as the fallback, never the reverse.

**Anchors for districts/landmarks** — Nominatim, one request per second:

```bash
curl -s -A "<app>/1.0" "https://nominatim.openstreetmap.org/search?q=<place>&format=json&limit=1"
```

**Reject any anchor that lands outside the city's bounding box — a geocoder miss is silent and
confident.** A place name can resolve to a same-named street on another continent; measured: one
city's central district geocoded to **55.6°N 37.5°E**, thousands of kilometres away, and nothing in the
response said so — `lat`/`lon` and a plausible `display_name` came back as usual. A district polygon
drawn there would be a fabricated claim about geography in a document whose whole purpose is
trustworthy geography. So: define the expected `lat`/`lon` window first, drop any anchor outside it,
**print the rejected names**, and never let a fallback quietly substitute a nearby guess. Fewer
honest districts beat a full set with one on the wrong continent.

**Validate the payload SHAPE, never the exit code.** `curl -o roads.json` will happily save an HTML
error page under a `.json` name and exit 0 — the render then draws zero roads and says nothing. Check
`json.load` succeeds and `len(features) > 0` before using it, or the failure is silent.

**A live query that returns nothing is not a query that found nothing.** The same contract applies to
any tool that asks Overpass at runtime (a nearby/suggestion feature): a rate limit, a mirror timeout or
an HTML error body produces an empty element list, which renders as "there is nothing here" — a false
statement about the world, made confidently. Return an explicit **COULD NOT READ** state with a
non-zero exit instead of an empty list, and say in the output that it is not proof of absence. Overpass
throttles under repeated queries, so a correct response and a silent zero can alternate within a minute
of each other on identical input — which is exactly why the empty case cannot be allowed to pass as an
answer.

## Rendering: Leaflet + aerial tiles in a fixed-size container

- **Base:** Esri World Imagery tiles (`server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`).
- **Container:** a fixed pixel box (e.g. 1080×1350 portrait) so the composition is repeatable.
- **Scrim + vignette over the tiles.** Neighbouring satellite tiles are separate captures and show
  hard brightness seams; a flat `rgba(6,12,26,.28)` scrim plus a radial vignette unifies them, drops
the base back, and reads as deliberate framing instead of a mosaic artifact.
- **Build the page from a plain string with `__PLACEHOLDER__` tokens — not an f-string.** JavaScript is
  full of braces and an f-string turns every `{` into a format field; the file becomes a Python
  `SyntaxError` sitting inside its own template, and the error points at the JS.
- **`zoomSnap: 0` + a fractional zoom** fits a long narrow strip (a coastline, a corridor) into one
  portrait frame. Integer zoom either crops the ends or leaves dead sea.

## The label system — where every renderer goes wrong

**1. One label per road NAME, not per segment.** OSM splits one road into dozens of ways — a single
major road can be 100+ segments. Labelling each way draws hundreds of pills stacked on one line. Keep
the **longest way per road name** and label that one: the pill marks the road, not a fragment of it.

**2. A label that exists in the DOM is not a label on the map.** `latLngToContainerPoint()` called
before the map has sized itself and settled its view returns coordinates for a viewport that then
changes — so the DOM holds every label and the image shows almost none. **Register overlays with their
`{lat, lon}` and reposition ALL of them on `moveend`/`zoomend`/`resize`/`viewreset`, plus after a tick.**
Anything anchored to geography and placed once is correct only by luck.

**3. Resolution beats placement.** Hand-placing labels works for one city and breaks for the next.
Let the layout resolve itself:

- assign a **priority** (`district name` 3 > `POI` 2 > `road pill` 1);
- paint in priority order, checking each new label's bounding box against those already placed;
- on collision, search a **RING in BOTH axes** (perimeter-first: offsets where `max(|dx|,|dy|) == ring`,
  ring 1..7, ~17px steps), not just up/down;
- **a vertical-only slide is enough for a sparse coastline and fails completely in a dense core.**
  Measured: two PRIMARY district names lost their seats to road pills in a packed city centre and were
  suppressed while the map still looked plausible — the priority ordering was right and the search
  space was one-dimensional. Widening to both axes took that map from 8/10 visible labels to 10/10.
  If your primary labels are being hidden, the resolver is the suspect before the layout is;
- **if it still cannot find a home, HIDE it rather than leave it overlapping.** A missing label is
  honest; a collided one is noise. The road itself still draws, so nothing is lost.

Expect to suppress a few pill labels in a dense corridor — report that count rather than pretending
the layout is perfect.

**4. Give the primary labels a plate, not a nudge.** A translucent dark rounded backing behind district
names (`rgba(4,9,20,.62)`, padding, z-index above the pills) makes them legible wherever they land, and
ends the cycle of nudging them around the map while pills keep arriving on top.

## Verify by rendering and LOOKING

A map "renders" is not a map that reads. The loop:

1. render → open in a browser → wait for **`document.fonts.ready`** and for tiles (a font swap
   mid-capture composites two renders and looks like ghosted text);
2. screenshot the container at its **exact** size via CDP clip (`Page.captureScreenshot` with
   `clip={x,y,width,height}` + `captureBeyondViewport`), not a viewport screenshot;
3. count the labels in the DOM *and* read the image — a mismatch between the two is the positioning bug
   above;
4. inspect the image itself for collisions, clipped edges and illegible text, then fix and re-render.
   Expect several cycles; each one surfaces a defect the previous one hid.

## Layout notes worth reusing

- Sea/water side is dead space — **put POI labels there** with thin leader lines ending in a dot, so the
  city area stays uncluttered. The dot is what makes the label unambiguous.
- **Orientation devices** let a first-time viewer self-locate in seconds: highway shields with route
  numbers, distance arrows to the next major city, and a north arrow. A district map is read rotated
  far more often than people admit.
- District **colours must differ between ADJACENT** districts, not merely be distinct; two greens
  separated by red read as one zone.
- **District polygons for informal tourist zones are a reading aid, not a legal boundary.** They are
  not administrative units, so say that plainly instead of implying precision. Anchor the polygons on
  real coordinates so the claim is at least auditable.
