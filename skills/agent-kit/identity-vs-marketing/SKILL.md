---
name: identity-vs-marketing
description: "Use when renaming or publishing a product, service, endpoint or agent. Name changes must not move identity."
version: 1.0.0
author: Gentech
tags: [naming, metadata, identity, catalogues, x402, api, registries]
---

# Identity vs marketing — a rename must never move an identity

**Learned the hard way, 2026-11-21.** We renamed ten services for search-friendliness — `Treasury Defender` →
`Token Risk Score` — and the surface guard went red with **`10 ≠ 10`**: the same count, a different set.

Nothing was broken in production. **The rename had silently become a re-identification**, because the check
resolved display names through a hardcoded map and a miss fell through to slugifying the new name.

---

## The rule

**Three fields, three jobs, and they must never be the same string.**

| field | holds | who may change it | what breaks if it changes |
|---|---|---|---|
| `name` | the **company** | almost never | external references that quote the org |
| `id` (or `routePrefix`, `slug`) | the **identity** | **never** | routes, cache keys, billing, other systems' records |
| `description` / display `name` | the **search text** | whenever a better phrase is found | nothing — this is the point |

**A product's display name is marketing. Its identity is its route/slug/key.** If both live in one string,
**a rename is a migration**, and nobody will treat it as one.

### Every surface has its own identity field — find it before renaming

**A rename is not "change the name everywhere". It is "change the display name, and leave each surface's
identifier alone".** Enumerate the surfaces and classify the field on each:

| surface | display (change freely) | identity (never change) |
|---|---|---|
| registry metadata / manifest | `name`, `description` | `id`, `routePrefix`, `url` |
| **MCP `tools/list`** | the tool **description** | **the tool `name`** |
| `llms.txt`, bazaar copy, front page | everything in it | the endpoints it links |

**MCP tool names are identities.** A client that connected yesterday holds `treasury_defender` by name; renaming
the tool breaks it, while renaming only its description breaks nothing. **So an MCP surface that still lists
pre-rename tool names is CORRECT, not stale — do not "fix" it.** Put the searchable product name in the
description and leave the tool name alone. The reflex that renames everything is the same reflex that produced
the `10 ≠ 10` guard failure, one layer up.

---

## The publish checklist

1. **Every service object carries a stable `id`** alongside its display name. If it does not, add one before
   renaming anything.
2. **Every consumer reads `id` first**, then any legacy key, then the display name as a last resort.
3. **One resolution function, used everywhere.** We needed `_native` stripped from `gas_oracle_native` in
   *two* places — the builder and the checker — and only one had it. **A rule implemented twice drifts.**
4. **Regenerate from the source, never edit published surfaces.** Five surfaces, one generator.
5. **Verify after, with a checker that compares SETS, not COUNTS.** `10 = 10` is not agreement; the guard
   that reported our bug compared the actual members and named the diff.
6. **Check the name that appears in a SEARCH, not the one you like.** A company pitch as the product name
   matches no query: *"GenTech Labs — Agentic Treasury + x402 Rail"* could never surface for *"score a token
   before you swap."*
7. **Before you commit to the new name, search it in the directory that ranks.** A search-friendly product name
   can already be another company's slug at **#1** — measured: the name chosen for exactly this reason was taken,
   by a competitor on a different host, on the agent search engine that matters. **A name collision is cheap to
   find beforehand and expensive to discover after six surfaces and a re-index.** If the incumbent is unhealthier
   or dearer than you, keeping the name and beating the card is a defensible call — **make it deliberately, because
   two renames in a week is churn nobody forgives.**

---

## Never let a display name be a lookup key

```python
# WRONG — the map is a second source of truth, and a miss is silent
key = DISPLAY_TO_KEY.get(name.lower(), name.lower().replace(" ", "_"))

# RIGHT — the stable key is published, so it is always available
key = svc.get("id") or svc.get("routePrefix") or slugify(svc["name"])
```

**A hardcoded display→key map works until someone renames something**, which is exactly what a map like that
invites. **The fix is not a longer map — it is publishing the key.**

---

## Publish the key the TRUTH SET speaks — not the most obvious stable key

**Before adding an `id`, find out what the check compares AGAINST.** A surface-agreement check has a truth
side (the live gate / readiness state) and a published side (the generated files). **The published side must
use the same key space as the truth side, or you have added a third vocabulary instead of fixing the first.**

Measured failure order when fixing a `10 ≠ 10` rename:

1. published `routePrefix` — looked stable, but the truth set was keyed by **backend/service name** → still red
2. published the raw backend — **still red**, because the truth set normalises a suffix (`gas_oracle_native`
   → `gas_oracle`) and only one side stripped it
3. published the backend **with the same normalisation applied** → green

**So the order is: read the truth set's key derivation FIRST, copy its normalisation exactly, then publish.**
Two vocabularies that both look stable still fail; the goal is ONE vocabulary with two readers.

**Corollary:** any normalisation (suffix strip, case fold, slugify) must be a single shared function called by
both sides. Re-implementing it on the published side is how step 2 stays red while looking correct.

---

## Editing the name table without breaking the file

**A name table is usually a dict of tuples, and a regex over it will eat a closing paren.** Measured: a rewrite
matching `("key": ("Name", "Desc"))` swallowed the `)` on a line that carried a trailing comment, and the file
stopped parsing. Three attempts, one broken file, one restore from backup.

**Do it line-based, never with one clever pattern:**

```python
# match only the line's PREFIX, then rebuild the tuple and keep whatever followed it
m = re.match(r'^(\s*)"(\w+)"\s*:\s*\(', line)
if m and m.group(2) in NEW:
    tail = line[line.rfind(')'):][1:]          # everything after the closing paren, INCLUDING any comment
    lines[i] = f'{m.group(1)}"{m.group(2)}": ({name!r}, {desc!r}){tail}'
```

**The order that makes this safe:**

1. **Snapshot the file** (`shutil.copy2` with a timestamp) before the first edit — every failed attempt costs one
   copy instead of a reconstruction.
2. **Edit, then `python3 -m py_compile`** before running anything. A generator that fails to parse is obvious;
   a generator that parses but lost a key is not.
3. **Regenerate, never hand-edit the published surfaces.**
4. **Run the set-comparison guard and require silence.** If it names a diff, read the diff — do not widen the
   comparison until it agrees.
5. **If a fix fails twice, restore and change approach.** Two failures of the same shape mean the approach is
   wrong, not that the third attempt will land.

**A `repr()` in the rebuilt tuple is deliberate** — it escapes quotes and backslashes correctly for names that
contain them, which hand-concatenated quotes do not.

---

## What a rename actually touches

**Enumerate before editing. The list is always longer than expected:**

- the generator's name table (the one place to change)
- every **generated** surface it produces — manifest, registry metadata, bazaar copy, tool list, `llms.txt`
- **every HAND-MAINTAINED surface** — the website, a profile README, a deck, a listing someone typed by hand
- **any consumer that matched on the old string** — a guard, a monitor, a report, a test
- **external catalogues that cached the old name** — they refresh on their own schedule, so a brief
  disagreement between your surfaces and theirs is expected, not a regression

### Generated surfaces propagate; typed surfaces do not

**The surfaces fed by one generator are free. The surfaces a human typed are the ones that go stale** — and they
are exactly the ones the guard does not know about, because the guard was built from the generator's output list.

Measured: a rename reached five generated surfaces and the agreement check reported **5/5** — while the public
homepage still sold the old names, because nothing generates it. **Green guard, wrong site.** The site was a
sixth surface that existed only in a browser.

**So the surface list is itself a claim to verify, not a constant:**

1. **Fetch what a customer actually reads** — the live hostnames, not the files you know about — and grep the
   served HTML for the old AND new names. `curl -s https://<host>/ | grep -c '<old name>'` is the whole test.
2. **Add the served page to the agreement check as a source**, so the next rename that misses it fails the
   guard instead of being found hours later by an unrelated audit.
3. **Treat "the guard passed" as "the guard's list passed",** and name that limit out loud when you report it.
4. **A set comparison is blind to WORDS.** Every retired name that still maps to a valid key parses to a
   perfectly good member, so `{old, new}` and `{new}` compare equal and the surface passes while it sells the
   name you renamed away from. **A member comparison is not a vocabulary check.** Add a separate tripwire that
   greps each surface for the RETIRED display names and fails on a hit — it is the only check that can see a
   stale word, and it is cheap: one list, one substring test per surface.

### A generated surface can read the WRONG FIELD and keep the old words forever

**"Generated, therefore correct" is false when the generator reads a different field than the one you renamed.**
Measured: ten products renamed in the manifest's `bazaarName`, and `llms.txt` — the file agents load first —
kept publishing all nine retired names, because its generator preferred `mcpTitle` and fell back to the slug.
Nothing errored; the renderer was doing exactly what it was written to do.

- **Before declaring a rename done, grep the generators for every field that can hold a display name**
  (`bazaarName`, `mcpTitle`, `name`, `title`, `display_name`) and confirm they all resolve to the renamed one.
- **Put the searchable name first in every fallback chain**, not merely somewhere in it.
- **Then check the served bytes of each generated surface** for retired words — the generator's intent is not
  evidence of its output.

**A hand-maintained surface also has no source of truth until you make one.** If the served page cannot be
matched byte-for-byte to a file on disk, fix that before editing anything — see
`eat-the-meat-spit-out-the-bones` for the recover-and-merge order.

**Then verify with the set-comparison guard and confirm silence.** Silence is the pass.

---

## In a CATALOGUE, an entry is OWNED before it is named

**Before consolidating or renaming registry listings, enumerate the OWNER address of each one.** A directory that
shows `N` entries under your name is not necessarily `N` duplicates — **it may be `N` registrations made by
different wallets at different times**, and those are three different questions:

| what the entries share | what the job actually is |
|---|---|
| **one owner, many names** | a real dedupe — rename and retire freely |
| **several owners** | **a CUSTODY decision** — which key is authoritative, and do we still hold each one? |
| **same owner, several chains** | a placement decision — keep the chains that earn their place |

**Group by owner address before forming any plan.** Measured on our own listings: seven entries that looked like
one identity spread thin were **three distinct owner addresses across four chains** — so "consolidate them" would
have meant acting on registrations we might not control.

**And registry records are frequently ON-CHAIN: they do not delete.** If the signing key is lost, a stale entry is
permanent, and the only honest options are *fix the card* (if held) or *report it* (if not). **That asymmetry is why
custody must be settled BEFORE a rename plan is written**, not discovered halfway through one.

- **A signing test is the answer; a memory is not.** "We own that wallet" is a claim until a key signs something.
- **Route the question to whoever owns the keys**, not the seat that noticed the listings — and say plainly that
you are not touching wallets either way.
- **Classify each row and stop:** `CANONICAL` · `FIX THE CARD` · `CANNOT TOUCH (key not held)` · `RETIRE WHEN
  POSSIBLE`. A list of four verdicts is actionable; a list of seven rows and an opinion is not.

### Unverified listings are not presence

**An entry that is unverified, unscored and unreviewed is not distribution — it is a claim like everyone else's.**
Measured across our own seven: **all unverified, all score 0.0**, two advertising a protocol, the rest advertising
none. **Seven listings in that state is not seven times the discovery; it is one identity spread thin, and it reads
as a spammer to anyone who checks.** Count the listings that a stranger could actually find something through, and
report that number — not the row count.

---

## The front page sells PRODUCTS — a repo list is not a catalogue

**A rename audit is the moment to check what the most-read page actually says.** Measured on our own org profile:
**six repos, ten products, and zero product names** — the page explained how we build and never said what anyone
can buy. **The rename did not break it; it exposed that the page had never done that job.**

- **Lead with what is purchasable, one row per product, and put the routes with a real moat on top.** The cheap
  commodities go last — they attract attention and convert nobody.
- **Link a live endpoint, not a landing page about one.** A stranger who clicks should get a price, not a pitch.
  *The front page should be testable.*
- **Say what you do NOT serve**, and point at the machine-readable block that lists it. Almost nobody publishes
  their own gaps, so that sentence differentiates more than the table does.
- **Attach the guard before the copy is old.** If a link checker already scrapes that page, every new link is
  guarded from the next run — that is the cheapest way to stop a front page rotting.
- **Verify the push through the API, not the raw CDN**, and expect a brief disagreement while the edge catches up.

**A company name in the title and a product name in every row** is the whole structure: *who built it* above,
*what you can buy* below, and neither one pretending to be the other.

### Audit the SERVED page, not only the profile README

**Two different pages are both "the front page", and fixing one does not fix the other.** In one session the org
profile README gained the full product table while the actual website — the hostname a customer types — still
carried **zero product names** and an endpoint list headed "9 Endpoints" that was already down to nine when ten
were servable.

**The cheap, repeatable test is a fetch plus a grep:** pull the live HTML and count how many of the product names
appear in it, plus whether a price and the payment rail are mentioned at all. **Zero of the names is a finding;
a partial match names the ones you forgot.**

**Run that test as a script with a silence contract** (findings print, clean exits 0, unreachable exits non-zero),
and before trusting its silence, **point it at a deliberately broken page and confirm it produces a long findings
list.** A guard whose only demonstrated output is silence has not been shown to work.

**Three checks to keep honest while writing that script:**

- **A `402` from a paid endpoint is a PASS, not a broken link.** A naive checker treats any non-2xx as broken, so
  publishing ten live pay-per-call routes produced **ten false alarms in one run** — the checker could not tell
  "the endpoint is down" from "the endpoint is up and quoting a price", which is the exact state the product
  exists to be in. **Treat `402` as healthy only when it carries a payment challenge** (`payment-required` /
  `x-payment-required` header); a bare `402` with no challenge is a misconfigured paid route and stays red.
  **A guard that flags the thing you just shipped correctly teaches everyone to ignore it.**
- **Count render dependencies (`src`), not outbound links (`href`).** A first version counted both and reported
  "13 external origins — each is a connection the buyer waits on" for a page that loaded exactly one script.
  **A monitor that cries wolf about a page it just helped fix stops being read.**
- **Check the social-preview tags too** (`og:title`, `og:description`, `og:image`, `twitter:card`). Without them
  every link shared to a chat or social feed renders as a bare URL — which is the distribution loss nobody sees,
  because it happens on the other person's screen.

**And when you generate the preview image, measure the text width and shrink to fit — never eyeball it.** Render at
the target size, compute each line's width, reduce the font until every line fits the safe margin, then look at the
result and confirm no glyph is clipped. **A clipped last word in an OG card is invisible in code review and obvious
to everyone who sees the link.**

---

## The NUMBER is a surface too — identity can be right while the price is wrong

**A guard that compares names will pass while the price drifts.** Measured the same week as the rename: the
agreement check returned **6/6 green** while the service charged **$0.050** for an endpoint the public page
advertised at **$0.005** — a 10× gap on seven of ten routes. Nothing about names, ids or descriptions can
catch that. **The catalogue and the till are two surfaces, and only the number proves they agree.**

### Find the copy that is actually SERVED by probing behaviour

**Three price-bearing files existed side by side; exactly one was loaded.** Filenames, mtimes and "the newest
one looks right" all pointed at the wrong file. The test that worked was mechanical:

```
for each candidate file: count how many of its prices match the amounts an unauthenticated call is quoted
pick the file that matches on ALL of them  ← that is the served copy
```

**A 402 challenge is the cheapest oracle you have** — it states the exact amount a buyer must pay, per route,
with no payment and no auth. **Probe two or three routes and compare, before editing any file.**

Then:

- **Mark the non-served copies in-file** (a `_role` field: `SERVED` · `NOT SERVED, kept price-identical`) and
  set them to the same numbers anyway. A stale copy that still quotes a different number is a trap with a
  future reader's name on it.
- **Anything loaded at import needs a restart to change.** Config read once at boot means an edit is invisible
  until the process bounces — verify by re-probing the live amount, never by trusting the edit.
- **Surfaces computed from the loaded config follow the restart for free; static pages do not.** Separate the
  two in the plan: one bounce covers the API-side surfaces, and the static page needs its own edit and deploy.
- **Order the rollout so the published number is never LOWER than the charged one for long.** A page quoting
  below the till does not merely confuse a buyer — it makes every price you publish untrustworthy, which is
  worse than being expensive.

### Price against a measured band, not a feeling

**Sample the marketplace before setting a number, and quote the percentile you chose.** From a thousand live
listings the medians by category gave a defensible ladder: commodities at the median, a genuine moat route at
the 90th percentile, nothing outside the band. **A route priced above every listed p90 is invisible to anyone
sorting by price** — which is a distribution problem wearing a pricing costume.

---

## The trap this belongs to

**A count is not an equality.** Two sets of ten different things both count ten. **Any check that reports a
number and stops has the same defect as a monitor that cannot tell *clean* from *blind*** — the family of bugs
this fleet spent a week killing:

- a probe that exited `2` on findings, filed as a crash
- a wrapper that printed `INSTRUMENT FAILED` and exited `0`
- a job that ran and delivered nowhere, recorded as `ok`
- **a rename that kept the count and changed the members**

**Compare the members. Always.**

**And a field is not its name — read its VALUES before claiming what it proves.** A new field was added to the
served-traffic log and reported as *"we now record who was served."* Reading the writer and the column showed
otherwise: the field records the **kind** of caller (`human / x402-auth / mpp / absent`), **not an identity** — and
every one of the requests since the deploy carried `absent`, meaning nobody presented a payment or a key. **The
instrument worked perfectly; the label was invented by the reader.**

So before quoting a fresh instrument as proof: **grep the field name to the line that writes it, then histogram its
values.** A column that is one value everywhere is either a healthy instrument reporting a real state or a broken
one — say which. **Never translate a category into an identity**, and never let a field's helpful name stand in for
the question you were actually asked.
