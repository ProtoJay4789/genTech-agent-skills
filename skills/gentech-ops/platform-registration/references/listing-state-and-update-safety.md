# Listing state machines and safe updates

Any platform that hosts a page FOR us (a project page, a profile, a vendor listing) has two states that look
identical from the inside and are nothing alike: **what the owner can set** and **what the platform decides**.
Confusing them turns "it isn't live yet" into a hunt for a button that does not exist.

## 1 · Read the state machine before hunting for the publish control

Hosted listings commonly run a four-state workflow: `draft` → `pending` → `approved` / `declined`.

- **`pending` means SUBMITTED, not unfinished.** The owner has done everything they can. The remaining
  actor is the platform.
- **The owner-settable flag and the platform's approval are different fields.** Typical shape:
  `isPublished: true` (ours) alongside `approved: false` (theirs). A UI badge like "not public yet" is
  showing the second field, which reads as a to-do and is not one.
- **Confirm the direction of the gate from the vendor's own docs**, not from the badge. The sentence to look
  for is the one saying the approval *cannot be set by the owner*.

**When it is pending, the only lever is the platform's humans.** Any further "publish" clicking is motion.

**Locate the control once before assuming it is missing.** The publish action is usually a switch in the
owner's dashboard plus an `isPublished` field on the REST object — and a platform's **CLI often ships
`create` / `update` deliberately WITHOUT a publish flag**, because publishing is a review submission and
not a routine edit. Absence from `--help` is a design decision, not an undocumented feature to hunt for:
check the object's own field and the dashboard before concluding the platform cannot be published to.

## 2 · Never send a field you do not want changed

Partial-update endpoints (`PUT`/`PATCH`) usually apply **only the keys present**. So the safe write includes
nothing but the fields being changed.

- **Do not echo a publish flag back as `true` "for safety".** It is a needless write on live state, and some
  platforms treat *any* write to it as a state transition.
- **The dangerous value is `false`, not omission.** A documented trap: unpublishing a project **that is still
  in review** returns it to `draft` — i.e. out of the queue — while an already-approved one keeps approval
  and merely goes hidden. Unpublish-then-republish to "refresh" a queue position is how you move backward.
- **Array fields usually REPLACE the whole array.** To add one entry, send the full array including the
  existing entries; to remove one, send it without. Sending only the new entry silently deletes the rest.

## 3 · Snapshot before mutating, and re-read to verify

```bash
# 1. capture the whole object first — this is the undo
curl -s -H "X-API-Key: $KEY" "$API/object?multi=true" > snapshot-$(date +%F).json
# 2. write the minimum
# 3. RE-READ and assert every untouched field is byte-identical
```

The verification that matters is not the 200 — it is that **the fields you did not touch are unchanged**,
with the state fields (`reviewStatus`, `approved`, `published`) checked first. A 200 with a silently reset
state is the failure this exists to catch.

## 4 · A 400 is better documentation than the docs page

Schema prose routinely under-specifies nested shapes. When a write is rejected, **read the validation body** —
it names the exact path and expected type:

```json
{"error":"Validation error","details":[{"expected":"object","code":"invalid_type",
  "path":["teamMembers",0,"links",0],"message":"Invalid input: expected object, received string"}]}
```

That one line says `links` is a list of **objects** (`{"type": "github", "url": "…"}`), not strings — a fact
visible in the vendor's request *example* but not in their field table. Prefer indexing on the error than on
prose; a rejected write with zero state change costs nothing.

## 5 · Public visibility: an SPA "200" proves nothing

A hosted page is usually a single-page app, so **every route returns 200** — including ones that do not
exist. Never read a 200 from the page URL as "it is live".

Assert on the **API, logged out**, which is what a stranger actually gets:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$API/public/objects/<slug>"     # no key
# 404 + {"error":"… not found"}  = invisible to strangers
# and check the listing/search endpoint for the slug, not just the detail route
```

Cross-check against the public index (paginated listing) for the slug as well: a detail route can be gated
while the index is the surface that matters. Both are "logged out" measures; an authenticated read is the
owner's view and is **not** evidence of visibility.

## 6 · Derived cards are earned by what you already published

Hosted pages auto-derive credibility blocks from links already on the record — repo activity, credibility
scores, market data. Two consequences:

- **A derived card is free credibility you are leaving on the table** if none of your links matches the pattern
  the platform looks for (e.g. a card that renders only for a `github.com/{owner}/{repo}` URL, and every link
  on the page points at a marketing domain). Check the pattern, then add the link to the *least destructive*
  field (a team-member link) rather than overwriting the website.
- **The badge is conditional on ownership.** "Verified" typically requires the platform to match the repo to
  the linked account — so linking a repository you do not own loses the badge, and linking your organisation's
  repo may not count as "yours". Prefer the canonical personal/org identity the owner already chose.

**Do not link an EMPTY repository.** Name-matching is worthless if a reviewer clicks through to a blank page;
link real content, and if the name-matched repo is empty, say so and name the publishing decision it needs.

## 7 · State what the write can and cannot prove

Fields written are provable by re-read. A **rendered card is not** — while the page is 404 to strangers there
is no surface to inspect, so the honest report is "field set, rendering unverifiable until approved". Same for
any badge whose condition lives inside the platform.
