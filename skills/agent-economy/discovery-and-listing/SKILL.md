---
name: discovery-and-listing
description: "Use when a live agent service gets no traffic."
tags: [discovery, listing, x402, erc-8004, mcp, a2a, directories, reputation, distribution]
trigger: "When a live, working agent service still gets no traffic. When listing/submitting to a directory, marketplace, facilitator or registry. When a listing was accepted but nothing shows up. When asked 'why aren't we getting found?'"
version: 1.0.0
author: Gentech
---

# Discovery & Listing — getting noticed in the agent economy

Full playbook (layers, gates, validators, the surface registry and the funnel):
**`references/surface-registry.md`** — read it before submitting anywhere.

**The hard lesson, measured on ourselves:** a service can be completely built, correct, payable and
live — and still be invisible. Every surface has its own gate, the gates are unrelated to each other,
and each one fails silently. "We're not getting found" is almost never one bug; it is a stack of
unchecked ones.

## The layers, each with its own gate (all observed first-hand)

| Layer | What it gates | Real rules we hit |
|---|---|---|
| **Payment / facilitator** | whether a settle is accepted | Facilitators are per-protocol and differ. CDP: no gating on payer/payee being registered (they told us directly) — the trap is a **307 instead of 402**, i.e. the advertised resource URL must equal the route that challenges. OKX: rejects **multi-network `accepts[]`** and unknown extension blocks. Dexter: expects a different SDK envelope. |
| **Directory / registry** | whether you appear at all | 8004scan: card needs a top-level `type` and `services[].endpoint` (we shipped `url`, so their parser extracted **nothing** — 11 warnings, `services: null`). Re-parse is **owner-signed and cooldown-limited**, and derived fields come from a **separate scoring pass**. x402-list: graded compliance + an ownership proof file at a well-known path. GitHub-catalog PRs: a PR from an account invisible to logged-out readers **does not exist** to crawlers. |
| **Protocol** | whether an agent can call you | MCP (`tools/list` shape, POST JSON-RPC), A2A (`/.well-known/agent-card.json`), x402 (402 + `accepts[]`). Declaring a protocol you don't serve is a falsifiable claim in public metadata. |
| **Identity / reputation** | whether you get chosen | ERC-8004 registries. Score tracks **feedback count**, and feedback is written by real callers with a real client address. It cannot be self-manufactured. |

## The procedure — for ANY new surface

1. **Ask who the buyer is and how they search**, not how to list. Listing is not distribution.
2. **Probe the surface's own validator with the real artifact.** Never trust its docs; docs and
   validators disagree constantly. Submit the real thing and read the exact error.
3. **Capture the failure text verbatim** — it usually names the missing field (`Missing required
   field: type`, `Agent has no endpoints configured`).
4. **Fix the canonical artifact once**, regenerate every copy from it, and verify the **served bytes**
   (repo/vault/webroot drifting apart is normal).
5. **Write the gate into the surface registry as a test** so the next regression is caught by us, not
   by a reviewer.
6. **Probe before you declare.** Every capability in public metadata must answer 200 right now.
7. **Before EVER saying "we are not listed", run the owner lookup, not a page walk.** Ask the catalogue
   for YOUR identifier (`?payTo=`, merchant route, resource URL) and confirm the filter works by first
   passing a value you know is present. **A bounded page walk of a large catalogue is not evidence of
   absence** — one pass reported us missing from a 99,564-item catalogue by walking 12,000 of it, and a
   later owner lookup found every entry. A bare-array read of page 1 is the same trap one size smaller.
   **The failure mode is asymmetric and it matters: a false "we are invisible" sends the whole team to fix
   discovery that already works, while a true "we are invisible" costs only a delay.** So the claim carries
   the burden of proof — name the query, the filter control, and the pages scanned, or report **UNKNOWN**.

## Before treating a directory as a target, ask whether its ENTRIES can PAY you

**A directory of payment rails is not a directory of buyers, and being listed where nobody transacts is
decoration.** When a new index appears, classify every entry by one test: **can that product's client send a
payment to an ARBITRARY endpoint of yours?** Measured over a 30-entry agent-payments index: **5 open x402
clients that could pay any endpoint we advertise · 5 gated or chain-narrow (allowlists, Solana-only) · 6
planned/beta/no published workflow · 13 card rails and own-catalogue checkouts that are structurally
incapable of paying an API · 1 direct competitor.** A listing among those 13 reaches a reader looking for a
wallet, not a service.

- **Read each entry's "how it works", not its category label.** The category is marketing; the sentence
telling you where the payment comes FROM is the fact. *"discovers an endpoint, checks schema and price, signs,
retries"* = open. *"pays our catalogue"*, *"issues you a card"*, *"supported sellers only"* = not a buyer
for you until you integrate.
- **Then prove reach from your OWN request log, one grep per listed name.** Measured: of all 30 names, exactly
one had ever knocked — the directory's own discovery crawler, 191 requests, all `402` — and zero from the
twenty-nine others. **Clients like these discover through catalogues they read, not by crawling the web**, so
"we are not in the catalogue their client walks" is the whole finding, and it is a catalogue problem rather
than a visibility problem.
- **A competitor in the index is a research asset, not a target.** Read their OpenAPI and pricing before
writing a single submission.
- **Say the count you excluded.** "Five of thirty can ever pay us" is the sentence that stops the team
spending weeks on the other twenty-five.

## Positioning outranks placement — and a listing DRIFTS as the product grows

Measured on ourselves, twice: **a correct, live, payable service can be invisible not because nobody
listed it, but because the listing names the wrong CATEGORY.** Our product is an Agentic Treasury, and
the live ERC-8004 metadata + x402 manifest led with *Token security / Rugcheck* — the saturated
category — so directories and agents read us as one more generic security API. **We built treasury-first and
listed security-first.** The code was never the problem.

> **Classification precedes discovery. The category in your metadata decides whether the code is
> allowed to matter** — a perfectly-configured listing that names a crowded category wins nothing.

So before adding ANY new surface, fix the story on the surfaces that already point at you.

**And a listing drifts the moment the product moves.** Any listing that carries a count is a claim
about your surface, and it rots. Measured in one pass: one directory read **6** endpoints, another
**10**, while the gateways served **14**. A directory that undercounts you is actively mis-describing
you — a buyer deciding whether to call is reading a smaller product than you have.

- **Sweep every live listing for the served figure after ANY endpoint/service change**, and read the
  count off the LIVE surface — never off the submission you once made.
- **The front door every listing points at must ANSWER.** A listing's URL is the one thing a directory
drives a human to. Measured: our root returned `403, 17 bytes` — *"a worse impression than a 404,
  because a 403 reads as closed to you"* — so every listing led a buyer to a refusal. Serve a real
  payload at `/` that names the API (see `public-repo-lifecycle`: a dead link invalidates the page).

### Audit your OWN entry's links, not just its counts — a root 200 proves nothing

**Every URL in your listing is a promise, and a listing's link can answer perfectly at the root while
its every functional route fails.** Measured: our own directory entry carried a gateway link whose `/`
returned `200` with a tidy health document — while **all sixteen of its paid endpoints returned `500`.**
**A root-status check passes a surface that cannot sell anything**, so probe the entry's links at the
paths a buyer actually calls, not at the home page.

- **Check the entry's own numbers against the surface it names.** Measured on one entry: it claimed *48
  endpoints* while the linked gateway declared *16* and the estate that actually served had *10*. **Read the
  count off the LIVE surface the entry points at** — the listing, the manifest and the gateway can each
  describe a different size of the same product.
- **One product can exist TWICE, and the listing decides which one a buyer reaches.** Measured: a container
  estate behind an API hostname (which we had just repaired) and an edge/Worker estate under a `*.workers.dev`
  URL (which the entry linked, and which was broken). **Before fixing anything, confirm which estate the entry
  points at** — a fix applied to the wrong one reaches nobody.
- **Correct the entry; do not add a second one.** A self-correction — *"our entry overstated its endpoints and
  linked a gateway that 500s; here are the measurements"* — is a legitimate, well-received contribution, and
  far better received than a fresh placement.
  - **A form-only directory may have NO edit path — read the submission TYPES before hunting for one.**
    Measured: a listing site offered exactly two `submission_type` values (`service`, `facilitator`) and no
    update/claim route at all, so correcting an existing entry had to go through the NEW-service form with the
    correction stated in a free-text `notes` field that names the existing slug and what changed. **That is not
    a second listing — it is the only channel the surface has**, and the notes field is the thing that stops a
    reviewer reading it as a duplicate.
  - **Build the payload from the LIVE artifact, never from memory:** endpoint list and count from the served
    manifest, the category from the platform’s own enum, and the contact address the owner actually reads.
    An endpoint list copied from an old submission is how the entry got wrong in the first place.
  - **Read the response for STATE, not for success.** A form POST commonly answers `303` with an empty body; the
    state lives at the redirect target (`?submitted=1` → *pending review*) and in the record afterwards.
  - **Verify by re-reading the record you are trying to change** — `GET /api/v1/services?search=<brand>` — and
    compare `endpoint_count` / `networks` / `status` against what you submitted. A review that has not landed
    shows the OLD numbers, so the honest report is *"submitted, record unchanged"*, never *"fixed"*. **Keep it to ONE change** (the repo's own rule), **preserve the
  file's line endings**, and verify `git diff --stat` shows a **single insertion and deletion** before you
  open it. A whole-file diff from an accidental CRLF rewrite gets a correction rejected as noise.
- **Match the entry's stated format, not the one already there.** If the contributing guide specifies
  `- [Name](link) - Description.`, a pre-existing em-dash entry is drift to fix, not a style to copy.
- **Know which KIND of list you are looking at before writing a submission.** An *index of indexes*
  (`sindresorhus/awesome` and its peers) accepts **lists, not projects** — its contributing guide has a
  section literally titled "Adding an awesome list". **You appear there by running a curated list, never by
  submitting a service**, and a submission attempt is wasted effort on a surface that has no slot for it.
- **Read the contributing rules for a DELETION bar as well as an addition one.** *"Exclude: dead links or
  abandoned projects"* is the clause that makes a broken link a defect the maintainer wants reported —
  **the same document that governs your submission also tells you a correction is in scope.**

## Two kinds of surface — know which one you are looking at

The registry is NOT a list of submission forms. It holds **two opposite kinds of gate**, and applying
the wrong play costs weeks:

1. **Submit-gated** — a form, a PR, a well-known proof file. The work is the submission.
2. **CLOSED / fed by your own traffic** — the directory indexes only what flows through ITS OWN
   facilitator, or what your own manifest advertises. **There is no form.** The lever is a correct
   manifest plus one real settle; a submission is not merely unnecessary, it is not possible.

- **An empty manifest is a connected pipe feeding on nothing.** Measured: our discovery endpoints
  advertised `services: 0` for months while the real catalog (14 services) sat unmounted — so every
  facilitator-driven index had nothing to catalogue and only 2 services were ever seen. The pipes were
  not broken; they were starved. **Fix the artifact and settle once — then the index follows traffic.**
- **A consumed cooldown is spent.** Where a re-parse is owner-signed and cooldown-limited, **do NOT
  re-submit to nudge a pending record** — you burn the window and can lock yourself out. Monitor, fix
  the cause, then submit ONCE.
- **"Not listed" and "cannot be listed" are different findings.** A surface walked exhaustively
  (thousands of items, zero of ours) is evidence it has **no self-serve path**, not that we forgot a
  form. A facilitator's search API can return `402` with a **0-byte body** — a refusal is not a
  directory.
- **A marketplace that has never paid anyone is retired, not a target.** Check for lifetime payouts
  before investing in a listing: zero lifetime settlements is zero distribution, however good the fit.

## Presence follows the FACILITATOR — a manifest advertises you, a SETTLEMENT files you

**Two catalogues, same product, opposite verdicts in one pass — and registration was never the
difference:**

| Catalogue | Size | Us? | Why |
|---|---|---|---|
| **PayAI facilitator catalogue** (`facilitator.payai.network/discovery/resources`) | 24,130 | ✅ **19 entries**, every one our payTo | we settled through **PayAI's** facilitator |
| **CDP Bazaar** (`api.cdp.coinbase.com/platform/v2/x402/discovery/merchant?payTo=…`) | 99,564 | ✅ **15 entries — all 14 services** (was **4**, the subset catalogued via **CDP's** facilitator, before we settled through CDP itself) | both catalogues index us; each holds the subset that settled through **ITS OWN** facilitator |

**⚠️ An earlier pass recorded us as ABSENT from the CDP Bazaar and that was WRONG** — a bounded page
walk (12,000 of 99,564) found nothing, which is not the same as not being there. **Never conclude absence
from a page walk of a large catalogue; ask the merchant lookup.** The walk missed four real entries.

**The same bounded read also manufactures false ALARMS, and those cost more than a missed listing because
they send everyone chasing a delisting that never happened.** Measured: a presence check that read only the
first 1,000-item page reported our facilitator catalogue as *dropped 14 → 10*; paginating to `offset=1000`
returned all ten, intact and repriced. A catalogue grows past its page size, so **a single-page change
detector will announce "we disappeared" the moment it does.**

⇒ **Any "we dropped / were delisted" alert must first re-locate the entry by its own identifier (`payTo`,
resource URL) across pages before it is allowed to speak.** A detector that cannot paginate is only entitled
to report **UNKNOWN**, never a drop. And when a drop is real, say which page range was scanned — "10 of 10
found at offset 1000" and "0 found in 9,000" are different findings and only one of them is news.

**A facilitator's catalogue indexes what settles through THAT facilitator.** The x402 FAQ states it
outright — *"Catalog indexing is a facilitator implementation detail… contact the facilitator or catalog
operator you're using first"* — so for any settlement-gated catalogue, the lever is **the facilitator you
point your buyer at**. Correct manifest, correct positioning, resubmission: none of them substitute.

**And a catalogue can hold a SUBSET of you.** Four catalogued entries against fourteen live services is
not visibility; it is a directory describing a quarter of the product. **Compare the catalogued count
against the served count for every catalogue, not just listed/not-listed.**

**So "not listed" is a claim about a facilitator, not about a product. Always name the catalogue AND the
facilitator that feeds it before you report either way** — and check the catalogue of the facilitator you
actually settle through before concluding you are invisible anywhere.

### A settled call files you AND republishes your worst surface

**Indexing crawls what you ADVERTISE, not only what you charge.** The settle that files you also causes the
catalogue to read your manifests and your prose files — so **whatever every advertised surface said at the
moment of settlement becomes the copy published under your name.** Measured: a first-ever settled payment
produced a listing within seconds carrying **fifteen services when only nine could be served**, because one
human-readable surface had never been filtered while four others already agreed. The gap was not in the
catalogue; it was in a file we had forgotten was public.

- **Filter EVERY advertised surface before the first real payment, not after.** One unfiltered surface is
  enough for an aggregator to publish a product you cannot deliver — and the payment is the trigger.
- **Enumerate what a crawler can actually reach:** discovery manifest, bazaar document, registry metadata,
  `llms.txt`, `openapi.json`, MCP `tools/list`. **The prose files are the ones forgotten, and they are
  crawled hardest.** Fix them with the SAME servability predicate that decides your refusals — one
  predicate, every surface, or the surfaces will disagree again the next time inventory changes.
- **An advertised count that exceeds your servable count is a defect with a deadline**, and the clock is the
  crawler's, not yours. Nothing about it is cosmetic: a directory now describes a bigger product than you
  sell, in your voice.
- **Re-check the catalogue AFTER the surfaces are fixed** — the published copy only corrects itself on a
  re-crawl, so "we fixed the file" and "the listing is right" are separate claims with separate proofs.

**⚠️ And before promising a facilitator switch, probe whether that facilitator needs CREDENTIALS.**
Measured: one facilitator's entire surface — `verify`, `settle` **and even `/supported`** — returns
`401 Unauthorized` without a key, while a different facilitator serves `/supported` openly. **So "settle
through the right facilitator" can be gated on an API key the requester must go and obtain, and the entire
indexing lever then waits on an account signup that may itself involve identity review.** Probe the target
facilitator unauthenticated FIRST and report the gate before it becomes the plan — **a distribution plan
that silently depends on a signup is not yet a plan, and finding that out after the promise is a broken
one.** Its free browsing/validation endpoints being open says nothing about its settle path.

**And once the credential exists, the switch is ONE SCRIPT — and it is verifiable in the same run.**
Settling through the target facilitator took a catalogue from **4 services to all 14 in a single pass** (the
merchant lookup went **4 → 15**). The proof arrives as a response header: a Bazaar-supporting facilitator
echoes **`EXTENSION-RESPONSES: {"bazaar":{"status":"processing"}}`** — *the discovery metadata was
accepted and is being catalogued asynchronously*. **A facilitator that returns no such header never
ingested the metadata, which is why an identical, correct manifest settled elsewhere produced no listing at
all.** Recipe, credential class, dry-run gate and pacing live in the **`x402-api-compliance`** skill, in its
`cdp-bazaar-indexing` reference.

### A settle files you only if the PAYLOAD names the resource — the last silent gate

**Everything a buyer can see can be correct and the catalogue still learn nothing.** A correct manifest, a
valid `extensions.bazaar`, a top-level `resource.url` on the live 402, six CAIP-2-clean rails and real
settlements through the right facilitator are **all necessary and jointly insufficient**: the catalogue reads
`resource` **inside `paymentPayload`**, and a settle envelope built as
`{x402Version, paymentPayload, paymentRequirements}` omits it. The money moves — settlement never needed the
field — and the listing never appears.

⇒ **When a settle succeeds and no entry appears, grep the settle path for the field before theorising about
the catalogue:**

```bash
awk '/def verify_proof_via_cdp/,/^def /' server.py | grep -n 'resource'   # zero hits = this defect
```

Set it from the request being served (`_pp.setdefault("resource", str(request.url))`) on **every**
facilitator builder, not just the one that complained — the same envelope is spoken by every Bazaar
facilitator, and a field on one path but not another is the rails-not-all-CAIP-2-clean defect one layer
deeper. **Never synthesise the URL**: a settlement attributed to a route that was not called is worse than
no listing.

- **Our payload being wrong is the first hypothesis, not the last.** Before any vendor ticket, prove three
  things in order: the declaration validates against the SDK's own type, the settle went through the
  catalogue's own facilitator, and the payload carried `resource`. Fail any one and it is our bug — and a
  ticket filed for it gets dismissed, correctly, spending credibility in the one repo that owns the index.
  The validator snippet and the exact SDK-type gotcha live in `x402-api-compliance` → `cdp-bazaar-indexing`.
- **"We already settled, so we should be listed" is a reasonable assumption and a false one.** Settling
  proves the payment path; being catalogued proves the *metadata* path. They are separate claims with
  separate proofs, and an operator who has done one will assume the other.

### Control-test the filter before you read a zero

**A query parameter that is silently ignored returns a plausible page, and a page reads as a
measurement.** Two catalogues, opposite behaviour, one session:

- **CDP's `resources?payTo=` is INERT** — filtering by our payTo returned 100 unrelated resources carrying
  71 distinct payTos, i.e. the default page. **The control that proved it: filter by an address you already
  saw in the unfiltered results.** If the set does not narrow to that address, the filter does not exist.
- **PayAI's `discovery/resources?payTo=` WORKS** — returned exactly our 19 entries.

⇒ **Filter by a value you KNOW is present before concluding anything from a zero.** An unfiltered page
and a genuine "no results" are indistinguishable while the filter is dead.

**And when the LIST filter is dead, look for a MERCHANT endpoint before declaring absence.** CDP exposes
`/discovery/merchant?payTo=<payTo>` — a purpose-built payee lookup that works where the list filter does
not. **The generalisation: a catalogue's list endpoint is for browsing, and per-owner verification usually
has its own route.** Hunt for it (read the vendor's discovery docs / SDK surface) rather than concluding
the catalogue cannot answer the question.

### A preflight validator beats every guess about why you are not listed

**Vendors increasingly ship a FREE, unauthenticated validate endpoint that scores your live artifact and
names the failing check.** CDP's is `POST /platform/v2/x402/validate` with
`{"resource": "<url>", "method": "GET"}` — no key, no auth.

**Run the validator BEFORE any of the reasoning in this skill.** It converted a session of inference
(which catalogue, which facilitator, which metadata) into one field name in a single call. Every layer in
the table above has a gate — **the vendor's validator tells you which gate you are standing at**, which is
strictly better than testing layer by layer.

**And read a `parse`-class failure as a WHOLE-document failure, not a per-field one.** One invalid
`accepts[]` entry can fail the entire payload, so you can be rejected everywhere while every field you can
see is correct. **Fix the malformed value; do not delete the rail.**

**Probe with the method the endpoint actually serves.** The validator cross-checks the verb you probed
against the verb the artifact declares (`…bazaar.info.input.method.matches_request`), so a `GET` probe
against a `POST` route returns a FAILURE that is entirely yours, not the service's — and it names the fix
in words (*"declares POST but was probed with GET — re-run validation with method=POST"*). **Expect a
false failure on every non-GET route on the first sweep.** Re-probe with the right verb before reporting a
count, and read an instrument that corrects its operator as working — not as broken.

### Confirm the sort order before treating absence as evidence

**An absence only means something once you know how the catalogue is ordered.** Fetch page 1 and a deep
page, compare their timestamp ranges. Measured: CDP page 1 spanned `10-04 → 10-30` while offset 11,900
spanned `10-18 → 10-19`, so it is roughly recency-descending — which is what makes "we settled today and
are not in the first 12,000" a finding rather than a coin flip.

**Report the ordering, pages scanned, and the total together.** "12,000 of 99,564" is a bounded
measurement; "we are not listed" is not.

### A published UPTIME is a census of your listed ROWS — count the dead ones before calling it a fault

**A directory's uptime score is computed over the resources IT lists, so a template path you once submitted
drags the number forever.** Measured: a third-party score of **0.53** — and the cause was not the gateway. One
catalogue listed **11 resources for our payTo and 5 were dead placeholder shapes** (`/v1/defi/lp/:address`,
`/v1/security/score/:solana_address`, … — every one probed **404**); the other catalogue listed **11 and zero
were dead**. **5 of 11 dead = 0.545, which is the score, to two decimals.**

- **Read each catalogue separately and probe every listed path.** "Both listings are dirty" was the assumption;
  one was spotless. A cleanup plan built on the shared assumption spends a week on the clean one.
- **A dead `:placeholder` row is a submission artefact, not a deploy gap** — a template path advertised as a
  real resource. Fix the ROW; do not restart or rebuild the service to chase a number.
- **Never quote an uptime without naming the denominator** — `6/11 broken (54%)` is actionable, `0.53` reads as
  a flaky server.

### A listing EXPIRES — "listed" is not a durable state

**Before treating a listing as permanent, check whether the catalogue delists on inactivity.** A large
Bazaar removes any resource that goes **30 days without a settlement**, from both the catalog and search
results. So a service that was catalogued and then stopped settling **silently disappears**, and that
looks identical to never having been listed.

- **Turn `last_settlement_at` (or the record's `lastUpdated`) into an explicit deadline**, not a footnote.
  A listing with a stale settlement date is a listing already on the clock.
- **The indexing lever and the expiry fix are the same action** — settle through the right facilitator and
  you are both filed and kept filed. One action, two problems.
- **Distinguish "delisted" from "stale" and from "never listed."** Each needs a different response:
  delisted → re-establish traffic; stale fields → a resubmission (where one exists); never listed → find the
  gate. **A registry entry that says `live` plus `stale in N fields` may be wrong about the stronger thing:
  the record may not exist at all.** Verify existence by the owner/id lookup, not by the note that says live.

### A submitted listing has a STATE MACHINE — read the state, not the UI label

**"Not public yet" on your own dashboard is a STATUS, not a missing setting.** Before hunting for a
toggle, read the record's review state from the API. Measured: a marketplace labelled a project
*"Not public yet"* while its own record already read `isPublished: true`, `approved: false`,
`reviewStatus: "pending"` — **the publish switch was on and the gate belonged to the operator.**

- **Confirm invisibility the way a stranger sees it:** the unauthenticated detail route returning
  *not found*, plus absence from the public enumeration. Those two are the evidence; the dashboard
  label is the hint.
- **"Approved" is routinely not an owner-settable field.** The common shape is four states —
  `draft` → `pending` (submitted, waiting on review) → `approved` (listed) → `declined` — and only the
  first is yours. **So "make it public" can be a request, not an action, and saying so early beats
  hunting for a switch that does not exist.**
- **⚠️ Never toggle publish off and on to "refresh" a pending review.** Marketplaces document that
  unpublishing returns a record to `draft` *while it is in review* — a refresh that silently moves you
  to the back of the queue is worse than waiting. Read the provider's state-transition notes before any
  state-changing call on a listing that has been queued for weeks.
- **A state you cannot set means the lever is a message to the operator, not a form.** Say that plainly;
  it converts a stalled listing from a puzzle into a follow-up.
- **Do not experiment on a long queue position.** Whether an *edit* (as opposed to an unpublish) disturbs
  review is usually undocumented. An unverified mutation is not worth weeks of position — if it is wanted,
  it gets done knowing it may reset the clock, and the risk is stated first.

#### Check which fields the platform DERIVES from links you already supply

**A listing surface often renders cards from URLs you control, and an unused derivation is free
credibility left empty.** Measured: a marketplace builds a repository-activity card — and marks it
**verified** — whenever the website, a product URL, or a team link points at a repository URL. Every one
of ours pointed at a marketing domain, so the slot stayed blank and the page read as text plus an avatar.

- **Enumerate the derivable slots before submitting, and point at least one at the proof.** Repo activity
  and a linked social/credibility profile are usually derived, not configured.
- **Empty galleries are a self-inflicted weak submission.** Where a page allows N images and none are
  supplied, the reviewer judges prose alone — so the cheapest improvement is filling slots that already exist.

### Split a listing's fields into DECLARABLE and MEASURED before proposing a fix

**A listing carries two kinds of field and only one kind is fixable by submitting.** Measured: a
directory's owner-update API accepts name, description, website, category, contact email and endpoint
add/remove/method changes — and its own documentation states that *"measured fields (verified, uptime,
pricing, status, payTo) are read-only for everyone and cannot be updated through this channel."*

⇒ **Sort the wrong fields into the two buckets BEFORE proposing an update.** A `degraded` status, an
uptime figure, a price, a payTo or a verification flag can only move by changing the underlying reality
and letting the publisher recompute — **no submission will touch them, and filing one for a measured field
burns the cooldown on a no-op.** Declarable fields are the ones worth a request. Read the platform's
OpenAPI/schema for the update endpoint: it enumerates exactly which fields are declarable.

- **A bad measured status is often SELF-HEALING — read its clock before calling it actionable.** Compare
the publisher's recompute timestamp against the fix you just made. A status dated *before* your fix, on a
record with zero consecutive failures and a `payment_ready_until` in the future, is **waiting for its next
cycle, not broken**. **Report the recompute date beside the status** so a future reader can tell the two apart.
- **A figure the publisher cannot represent is not your defect either.** Before "fixing" an undercount,
  read the publisher's **supported set**. Measured: one directory's network list held 10 entries and
excluded a mainnet we serve (it carried only that chain's *testnet*) and a whole chain we serve — so our
`3 of 5 networks` was correct and **unfixable by us**. **Check the supported set before reporting an
undercount as a gap on our side.**

### Which endpoints are missing tells you HOW the directory discovers

**When a directory undercounts your endpoints, read the missing list for a pattern before assuming a stale
submission.** Measured: four of fourteen were absent, and **every endpoint the directory listed was `GET`
while both of ours that were missing were `POST`** — a discoverer that only walks GET routes never sees a
POST-only service, however many times you resubmit.

- **Group the missing endpoints by HTTP method and by path family.** A clean method split is structural
  (the crawler's limit, not yours to fix); a scattered split is staleness (yours).
- **Say which it is when you report it** — *"they walk GET only"* and *"we never added them"* lead to
  different next actions, and only one of them is worth a submission.

### Read the traction a directory already publishes before building your own instrument

**Rule: before instrumenting demand yourself, check whether a directory is already measuring it.** Measured:
a directory's per-service record carried `unique_buyers_30d`, `tx_count_30d`, `volume_usd_30d`,
`volume_usd_all_time`, `first_settlement_at`, `last_settlement_at`, `median_settlement_usd_30d` and
`top_buyer_share_30d` — **richer than the ledger we were about to hand-build, over a longer window, at zero
cost** — plus its own honest caveat (*"conservative undercount: a measured floor, not an estimate"*).

A hand-built ledger is still worth having (it sees the **near-misses**, which no on-chain-derived metric can),
but read the published numbers first: they may answer the question before you write a line.

- **Prefer a stated-floor metric to an invented one.** A number published with *"this is an undercount"* is
  more trustworthy than a self-built figure with no caveat — and it cannot be quietly flattering.
- **The field names differ per directory — read them off a live item, never from the vendor's prose.** CDP's
  Bazaar returns a `quality` block on every resource: `l30DaysTotalCalls`, `l30DaysUniquePayers`, `lastCalledAt`.
  Measured over our own 11 listed resources: **43 calls in 30 days**, with one route at **18 calls from 5 unique
  payers**. **A per-route payer count is a signal no self-built traffic ledger can produce**, because it counts
  payers *after settlement* — read it before concluding what demand looks like, and attribute the addresses
  against your own-wallet registry before calling any of them customers.
- **Use the SEARCH route for an owner lookup, not only the merchant route.** `GET {facilitator}/discovery/search?query=<brand>`
  returned **all 11** of our resources with `partialResults: false`, where the list endpoint's `payTo` filter
  returned a generic page. **Read the SDK's own parameter class before forming the URL** (`query` required;
  `pay_to`, `network`, `extensions` optional) — a guessed parameter name returns HTTP 200 with a plausible page
  and no error, which is the exact shape that re-confirms a false "we are not listed".
- **A search result dates the listing for you.** Each item's `lastUpdated` is the timestamp of the last paid call
  that filed it, so a single lookup answers *listed?*, *when?*, and *did the settle we just made land?* at once —
  and a `lastUpdated` matching your settlement to the second is proof the indexing trigger fired.
- **It also dates the problem for you.** A `last_settlement_at` weeks in the past on an otherwise healthy
  service is the signature of an outage that stopped the demand — a different finding from "nobody was ever
  interested," and a different fix. **Before reporting "we get no traffic," check whether we HAD traffic and
  lost it.**

### One indexing can reach several channels — choose the facilitator for its DISTRIBUTION

**Before choosing which facilitator to settle through, ask which downstream channels that indexing feeds.**
Measured: one facilitator's own documentation states that being discovered makes the endpoint reachable
*"through CDP APIs, the Bazaar MCP server, and Amazon Bedrock AgentCore, and to people browsing
agentic.market"* — **four surfaces from one registration, free on the entry tier.**

- **The facilitator choice is a distribution decision, not a plumbing detail.** Two facilitators can both
  settle flawlessly and differ by an order of magnitude in who sees you. **Read what the index feeds before
  you pick, and say which channels a given catalogue reaches when you report on it.**
- **MCP is a separate listing type where the catalogue supports it.** Where tools are first-class resources
  (`info.input.type: "mcp"` with a `toolName` + input schema), **every tool on an MCP server is separately
  discoverable** — a slot that can be near-empty. Sample the catalogue to see how many entries are MCP
  before assuming the format is unused, and **report the sample size honestly** ("none in my 2,500", never
  "none exist").

### Before changing a protocol identifier, ask the counterparty's supported-list

**An in-repo comment that says "this exact string is mandatory" is a CLAIM, not a spec — check the
counterparty.** Measured: a code comment insisted a rail's full network string was required *"so proofs
verify"*; the facilitator's own `/supported` endpoint advertised **both** that form and the spec-correct one.
Reading `/supported` turned a risky edit into a safe one.

- **When a spec and a comment disagree: the spec governs the FORMAT, the counterparty governs ACCEPTANCE.**
  Verify both before editing, and never assume an old comment is right because it is old.
- **Check how the value is USED before you change it.** A prefix test (`network.startswith("algorand:")`)
  survives a reference change; an equality test elsewhere does not. Confirm which, then edit every copy
  (live code + tests asserting the old value) — and leave historical backups/snapshots alone, they are
  records, not code.
- **Identifier correctness has its own reference: `references/network-identifiers.md`** — the CAIP-2 format,
  the truncation recipe that a naive value gets wrong, and the trap where one bad identifier fails the whole
  document.

### Quote the WIRE, never your own variable names

**When you document a protocol field, read it off a live payload — not off your own code.** Measured: a
brief told agents to *"read `amountUsdc` from the challenge"*. **That field does not exist** (grep the live
`402` body: zero hits) — `amountUsdc` was a **local variable inside our own settle script**, which reads
the correct field and then renames it for readability. A name from our code had leaked into a description
of the wire format, and an agent following it would grep, find nothing, and conclude the challenge was
malformed.

- **A variable's tag is not a document's key.** Dump the payload, paste the real key path (`accepts[0].amount`,
  a STRING of raw base units), and state the conversion (`÷ 1e6`) beside it.
- **This is the same class as probing a guessed path:** an invented identifier produces a confident, wrong
  instruction. Field names are checkable in one grep — so check them before they reach a reader.
- **Correct it in BOTH directions:** fix the living doc in place, and append a correction to any
  append-only record that carried it. A record is edited by addition; a quick-start is edited by repair.

### A 200 on a JS app shell is not a listing

**Control-test any page URL with a deliberately-invalid slug before reading a 200 as presence.** Measured:
`/agent/<our-slug>` returned HTTP 200, which reads as *"our listing page is live"* — and a garbage slug
returned **the same bytes, byte-identical**. It is the SPA catch-all; the 200 carries no information.

- **Use the API for presence, and read the control before the result.** One 200 can be a cache or a
  catch-all; only **distinct content at distinct paths** proves a thing is real.
- **Find the real route by probing, not guessing.** A guessed `/api/v1/search` returned 404 while
  `/api/v1/services?q=` worked — **the query parameter lived on the collection route.** Two probes beat one
  inferred schema.

### Traffic on a path you do NOT advertise is a census, not demand

**Before building a service to satisfy a caller, name the caller.** Measured: three routes deleted months earlier were
still receiving **~400 requests/day, steady, every day** — 4,065 since the recording began. Read as a total that is
demand for a missing product. Read by UA it is nothing of the kind: every request came from a catalogue monitor or an
uptime prober, and the status pattern was `404` then `503` — **monitors grading the seller as broken, not buyers**.

- **Bucket by UA before you scope any build.** A steady, flat, day-after-day rate with no variance is the signature of a
  crawler: real demand has a shape (bursts, retries, a funded wallet, a settle).
- **`404`/`503` on a path you never advertise is a stale-catalogue artefact**, so the lever is the catalogue or the
  route's own answer — not a new service. **Never stand up a product to satisfy a crawler:** it converts a monthly pile
  of 404s into a monthly pile of 402s nobody pays, and adds a maintenance surface with no buyer.
- **Retire loudly instead of deleting quietly.** A withdrawn route should answer **`410 Gone`** with a pointer to the live manifest: a monitor can act on "gone on purpose" and stop probing, while a 404/503 keeps it re-probing and keeps the seller reading as broken.
  Keep retired names in an explicit set so genuinely unknown paths still `404`. **And put EVERY internal name the path resolves to in that set, not the public segment** — measured: `/v1/deals/deals` stayed `404` after the retire-set was updated, because the segment maps to a service key (`deal_tracker_native`) that was never added. The public name and the key it resolves to are different strings, and only the key decides.
  **Verify the retired path's LIVE status code before reporting the retirement** — `404` after an edit means the wrong alias was retired, not that the deploy failed, and a `410` you did not probe is the same unfounded claim as a health check you did not run.
- **The honest close for an unbuilt service is "retired", with the evidence attached** — absent from the manifest, the
  OpenAPI and the catalogue rows. Rebuilding becomes a decision to make when someone wants it, not a queue row that
  makes the team feel behind.

### Asking a specific counterparty directly — repo issue over DM over form

Recipe, channel-choice table and the "sent is not a conversation" accounting: **`references/direct-outreach.md`**.
When the ask is to a named company or client rather than to a catalogue, read that before writing anything.

## The mistake to never repeat

Solving each surface ad hoc and then forgetting the rule. The expensive part is not the fix — it is
rediscovering the rule every time. **A surface without a recorded gate is a surface we will fail
again.**

## Funnel — measure discovery, not effort

`presence (listed?) → reachability (endpoint answers?) → discovery (do agents find us?) →
conversion (paid calls from non-us) → reputation (feedback)`

Be strict about "non-us": self-traffic inflates every stage above it. A successful submit is not a
successful listing — refresh accepted ≠ re-parsed ≠ fields populated ≠ ranked. Verify each hop
separately.

### Count the PAID tier before blaming the free tier

**"The free tier is eating our sales" is a hypothesis, and one table falsifies it.** Read the key/plan
record and count plans that are **not** free. Measured: 11 issued keys, **all `free`**, **zero paid plans
ever sold**, **8 calls in a month across all eleven** (most at zero). The free tier was cannibalising
nothing — there was nothing to cannibalise.

- **The conversion denominator is non-free plans sold — not signups, not calls, not keys.** If it is zero,
  the finding is **NO DEMAND**, and every free-tier question is unaskable until that changes.
- **No-demand and low-conversion need OPPOSITE work.** Low conversion → pricing, onboarding, paywall. No
  demand → standing in front of buyers who already spend money. Diagnosing the second as the first produces
  a pricing change that moves nothing.
- **Do not close the free tier to "turn the income on" while paid sales are zero.** It is then the only
  usage that exists; removing it leaves zero and destroys the one path that proves the product works.
- **Free-tier call counts are not service calls until you read what they are.** Measured: 22k "free calls"
  were index, manifest, docs and MCP-handshake traffic — a figure that reads as adoption and is
  infrastructure.
- **Price is not the obstacle if nobody reached it.** Sub-cent per-call pricing with zero buyers is not a
  pricing problem; discounting into silence hides the missing demand rather than fixing it.
- **Benchmark against the catalogue's own PRICE DISTRIBUTION, not one headline competitor.** "We are 5x cheaper
  than <famous API>" is an anchor, not a market: that product sells a different thing. Measured over 2,000 live
  listings, the median was **$0.05** with the largest band at $0.01–0.05 while our whole catalogue sat at the
  floor — a service priced like something free is its own kind of invisible, and the correction is **upward on
  the routes that sell judgement**, never downward on the ones that sell data. Pull the catalogue, compute
  median/band counts, and quote the sample size with the number.
- **A catalogue that publishes its own price list also publishes its own CATEGORY mix** — count what the index is
  full of before concluding a gap is a pricing gap. A lane already carrying dozens of listings is saturated, not
  underserved, however empty it feels from inside.

### ⚠️ A revenue figure can be wrong in BOTH directions — check the deflation too

**Self-traffic inflates the stages above conversion. A bad classifier DEFLATES conversion, and that is
the worse failure** — because an inflated number sends you chasing a phantom, while a deflated one
makes you stop looking for customers you already have.

Measured on ourselves: a revenue report said **zero external payments**, with a self-check that agreed
(`balance delta == log sum`) and a bucket labelled *"self/test settlements"*. The chain said **19 real
payments from an address we do not own**, spread over two half-hour bursts. The classifier bucketed them
as self/test **by transaction shape** — a bot buying nineteen small calls in two bursts is
indistinguishable from a test script if you classify by pattern.

- **Classify money by WHO PAID. Never by what the transaction looks like.** Keep an explicit set of every
  wallet you control; anything outside it is external, full stop.
- **A cross-check that compares your own two figures proves arithmetic, not classification.** Both sides
  can be right and both describing only your own wallet.
- **When a report says zero and a human says "somebody paid", go to the chain before defending the
  number.** The dashboard is a claim; the receipt is the record.
- **Report the payer set beside the amount.** *"19 payments from 1 address"* and *"19 payments from 1
  address — ours"* are the same figure and opposite findings.

**Recipe for reading the chain directly (JSON-RPC log scan, per-provider block caps, the funding-transfer
test that proves a payer is a stranger): `references/onchain-payment-verification.md`.**

### Separate OURS / CRAWLERS / HUMANS before saying there is no demand

**"We get traffic but no customers" is not one number, and the traffic ledger will lie by default.**
Measured over 12,108 requests: **78.7% monitors and indexers · 17.1% no-UA · 3.3% a browser · 0.9%
ourselves** — and the paid-call count was zero from all four buckets.

- **Bucket by user-agent against an explicit marker list, and print the buckets, not the total.** A single
  request count reads as demand; the split shows it is a health-check chorus.
- **⚠️ Never classify an ambiguous UA as a bot without a reason it self-states.** `node`, `python-requests`,
  `curl` are exactly what a real buyer's script looks like — **over-classifying erases the only class that
  can become a customer**, so leave them in an `other` bucket and read them rather than sweeping them in.
- **A buyer has a shape of its own:** a wallet funded, then a call, then a settle. Crawlers have none of
  those three. When checking whether demand existed, look for that sequence rather than a UA string.
- **Widen the marker list only for UAs that name their own purpose** (*liveness probe*, *monitor*,
  *collector*, *security scanner*, *directory*). Self-identification is not inference; a hunch is.

#### Read the UA *and* the PATH with it — a UA string alone under-classifies

**Classify on the full UA plus the path it asked for, or the scanner reads as a customer.** Measured in one
7-day window: the cron's own diagnostic hint dumped `ua[:60]`, which truncates the tail that names the tool;
and the rows that looked most human — Safari and Chrome desktop strings — were a vulnerability scanner
probing `/.env`, `/.git/HEAD`, `/wp-includes/wlwmanifest.xml`, `/api/fs/read`. Meanwhile `undici`, `axios`,
`Deno`, `Bun` and `python-httpx` walked **every** route in the catalogue in one pass: a census, not a buyer.

- **A browser UA that requests secret paths is a scanner; a runtime UA that requests the whole catalogue is a
  census.** Neither is demand, and neither is caught by a bot-marker list.
- **A caller that requests the template path itself (`/v1/defi/lp/:address`) never had an address to look up**
  — a directory crawler, not a caller.
- **Dump the UAs before you bucket them, and classify on the full string.** "259 unclassified, not yet
  evidence of demand" is an honest placeholder; the dump is what converts it into a finding either way.

#### Partition by ROUTE CLASS before you read caller SHAPE

**"Single-path caller" is a buyer shape only when the single path is a PAID service route.** Measured in a
20-hour ledger: 199 of 536 callers were single-path, and the highest-volume ones were **all `/mcp` returning
200** — a free handshake/index surface, hit 480 and 127 times by one tool, 168 and 45 by another, plus a
collector, a search bot and a client. A caller with one path and no purchase is exactly what a directory
crawler looks like when the thing it is crawling is the free surface.

- **Split the ledger into public/index routes** (`/`, `/mcp`, `/openapi.json`, `/status`, `/.well-known/*`)
  **and paid service routes, and analyse demand only in the second.** Mixing them lets a crawler of your
  index read as a shopper at your till — and the count is large enough to look like traction.
- **On a paid route, read the UA NAME against the sale.** Measured: every `200` on paid routes came from
  catalogue monitors (`x402-list-monitor` at 550 and 140 calls, a conformance checker at 5 × 12 addresses).
  A UA that names itself a monitor, lister, prober or conformance suite is running a check, not buying —
  **even when it is served.** A 200 there is a *keyed call*, which is a weaker claim than a sale.
- **Arrivals are not demand, and a catalogue layer arriving is a sign you are listed, not bought from.**
  When the visiting set is indexers, probes and comparison bots, the honest finding is *"we are in the index
  and nobody came through the door"* — which is a discovery finding, not a conversion one.
- **A diagnostic hint that says "unclassified caller — read it by name" is an instruction, not a finding.**
  Reading the name is the work; reporting the hint as the result leaves the question exactly where it was.

### A 503 is the opposite of a knock — check capacity before blaming discoverability

**402 proves the price is discoverable. 200 proves it was served. 503 proves it cannot be delivered** — and
a 503 on a route that crawlers are already walking is the worst of the three: the interest existed and the
product failed it. Measured: two services being walked by indexers answered **503** while the inventory read
as live. So before reporting "no customers", read the backend map the gateway publishes about itself
(`/status` → `backends{}`) and name every *sellable* service that is down. "6 of 14 sellable down" is a
distribution answer no crawler count can substitute for.

- **Never sum 402s and 503s into "traffic".** 402 = a knock refused by design; 503 = a buyer we would have
  lost. They are opposite findings about the same route.
- **An advertised-but-unservable service is a lie the crawler will republish** — the same predicate that
  decides refusals must decide the manifest (see "A settled call files you AND republishes your worst
  surface").

### The PAYMENT CHALLENGE is an advertised surface too — list only rails you can settle

**A `402` body is a public claim about how you can be paid, and it is read by every crawler that walks
your catalogue.** Measured: the challenge offered **five networks** (two EIP-155 chains, one L2, Algorand,
Solana) while settlement worked on **two**. A caller holding USDC on any of the other three is shown a
price they cannot pay — and it fails as a *refusal*, not an error, so it looks exactly like a closed door.

- **Enumerate the live challenge against your settle path before adding a rail.** `curl` a paid route and
  read every `accepts[].network`; compare that set with the rails your facilitator actually settles. The
  difference is the number of buyers you are advertising to and cannot serve.
- **The advertised set is the honest one, so shrink it or wire it — never leave it aspirational.** This is
  the same defect class as a manifest naming a service you cannot deliver, one layer down: the challenge
  is the last advertisement a real buyer reads, and it is the one they act on.
- **A missing rail is a conversion finding, not a listing finding.** A desktop-browser UA arriving at a
  Solana-priced route and failing has told you which rail to add; it is not evidence of no demand.
- **Read the field name off the live body before quoting it.** The challenge carries the price in a field
  whose name differs between spec revisions and older prose (`amount` as a **string of raw base units** in
  one, `maxAmountRequired` in another). Cite what the wire returns, and state the divisor beside it.

### A served manifest can be loaded ONCE at import — a file edit is not a deploy

**Before telling a user to "update the file", establish whether the process reads it per request or at
startup.** Measured: a gateway did `MANIFEST = json.load(open(path))` at module import, so a corrected file
on disk changed nothing until the process restarted — and `curl` kept returning the old bytes, which reads
as a failed edit rather than an un-applied one.

- **Grep the loader before promising a fix took effect**: `grep -n 'json.load(open' <service>.py` — module
  scope means restart, a function scope means per-request.
- **Prefer the deploy path that already exists over a hand-typed restart.** If a repo ships an apply script,
  read its paths first: a script written before a container/host migration can point at directories that no
  longer exist, and it will fail on its own safety check while looking like a permissions problem.
- **Verify from outside after the restart, not from the CLI that reported success.** The reading that
  matters is the one a stranger's `curl` gets.

### A 200 on a paid route is a claim about an INSTANT — re-probe before calling it a leak

**A ledger records history; a leak is a present-tense fact.** Measured: six `200`s on paid routes from
non-monitor UAs clustered in two deploy windows, which reads as "paid routes serve without payment" — and a
live unpaid probe of the same routes at reporting time returned **402**. The gate was closed; those six were
restart-window artifacts (a pre-challenge path still mounted, a warm cache).

- **Re-run the unpaid probe on the same route before reporting a leak**, and give both readings with their
  timestamps: *"six 200s at 13:36 and 22:42; unpaid GET now returns 402 — closed, unexplained history."*
- **Do not delete the anomaly either.** A historical 200 nobody can explain is either a bug that was fixed or
  a live one you failed to reproduce. Say which one you think it is, and that you did not settle it.

### Confirm the free surface is actually free before "closing the tap"

**A 200 on a service root is usually a COLLECTION ROOT, not a paid resource given away.** Measured: a
root served `200` with `{"collection_root": true, "payable": false}` — a signpost telling callers where
the billable path is — while `/<address>` on the same prefix returned a correct `402`. Closing the root
would have broken discovery and earned nothing.

⇒ **Read the body before recommending a policy change.** Probe the bare route AND a fully-parameterised
route; if the bare route answers with a `payable: false` marker and the parameterised one challenges, the
tiering is correct. **Check every paid route challenges before claiming a leak exists** — a claim of "free
money leaking" that turns out to be a signpost costs credibility you will need for the real finding.

### Two routes can share a NAME — a 402 on the name is not a 402 on the service

**Before believing any claim that a dead service is still charging, resolve the path to its BACKEND.**
Measured: a senior seat reported a real, payable `402` from a service the manifest had already declared
unservable — a customer paying for a `ConnectionRefusedError`. It was not. The dead route (`/v1/score`)
answered **`503` with no challenge**; the `402` came from `/v1/security/score/<address>`, a **different
service on a live port** that has every right to charge. Two products were both called *score*, and the
one note conflated them.

- **The discriminating control is the path that SHOULD be dead**, not one that should be live. A `404` on
  `/v1/zzz/qqq` only proves the gateway is not 402-ing everything — it says nothing about the dead route.
  Probe the dead route itself: a `503` (or a gated refusal) is the finding; a `402` is the alarm.
- **Read the route table before the challenge.** The path segment maps to a service key, and the service
  key maps to a port; a name that looks familiar can belong to a sibling backend.
- **Two products sharing a display name is a measurement defect before it is a buyer defect.** Report it
  as a naming collision, fix the display strings — your own fleet will keep mis-reading it otherwise, and
  a buyer reading the manifest has less context than your own agents do.

### A clean spec does NOT cure a stale cached copy — answer the template path server-side

**Fixing your OpenAPI removes the template routes from what YOU publish; it does not reach the copies already
in directories.** Measured after a spec cleanup verified at **0 literal-template paths**: over the next ~4,000
requests, **1,250 were 404s**, and **747 of those were crawlers calling the placeholder itself**
(`/v1/wallet/portfolio/:address`, `/v1/security/score/:solana_address`, `/v1/defi/lp/:address`,
`/v1/defender/classify/8453/:address`). The publishing surface was correct; the CACHED copies were not.

- **Do not re-open the spec looking for the bug.** If `openapi.json` has zero `:`/`{` paths and the 404s
  persist at a steady rate, the caller is reading someone else's copy. Re-editing the same file is a no-op
  that will be reported as a fix that "didn't take".
- **The only fix that reaches those callers is an answer at the path they asked for.** Serve a **`402` whose
  body shows the correct example call** (or `410` with a pointer to the live manifest) instead of `404`.
  A 404 is a dead end for an agent mid-task; a 402 teaching the right shape is the same request recovered.
- **Count it as a conversion defect, not hygiene.** These are strangers who already arrived. Report
  "N of M requests were template-path 404s — that is traffic we paid for and dropped", with the paths and
  their counts, never as a total 404 figure.
- **`/robots.txt` 404 is in the same bucket and costs nothing to serve.** A crawler that cannot read it may
  throttle itself against you.

### Probe MCP with POST — a GET returning 405 is not "not served"

**An MCP endpoint is POST-only, so a GET probe answers `405` and reads as a broken or absent surface.**
Measured: `/mcp` was the single most-requested path in the gateway's traffic (~646 hits) and `GET /mcp`
returned **`405`**; `POST /mcp` with a JSON-RPC `initialize` returned **`200`** with `protocolVersion`,
`serverInfo` and a tool list. Reporting the 405 as absence would have retired the highest-intent free surface
the service has.

```bash
curl -s -X POST -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}' \
  https://<host>/mcp
```

- **Re-probe with the protocol's own verb before any verdict**, and then `tools/list` — a server that
  advertises a `list_services`-style discovery tool is the clearest "buyers can shop here" evidence you have.
- **A high free-surface hit count is listing evidence, not demand.** Keep it out of the conversion count
  (see the route-class partition above) while still counting it as proof the surface works.

### Instrument the NEAR-MISS, or it is gone forever

**On-chain settlements are permanent and unlosable. Traffic that looked and did not buy leaves no trace
unless you write it down** — and it is the only signal that separates "nobody is looking" from "people
look and bounce." Measured: a gateway answered `402` to every caller and forgot them the instant it
replied; there was no access log, no counter, no state file, so "how many are knocking?" was unanswerable
and the demand side of the funnel was simply blank.

**Build the ledger as a middleware keyed on the RESPONSE STATUS, not as per-endpoint counters.** A status
-keyed hook captures every 402/200 regardless of which handler produced it and **cannot drift out of sync
with the route table** — a route added and forgotten is still seen. N hand-placed counters rot the first
time someone adds a route.

Rules that make it safe and useful:

- **Exclude your own monitors on BOTH write and read** (`/health`, `/.well-known/*`, favicons). A monitor
  counted as a `200` inflates "served" — the number the business is judged by — and the defect is invisible
  because the total still looks plausible. Filter at the reader too, defensively.
- **Store a HASH of the caller, never the raw address.** The ledger answers *"how many, from how many
distinct callers, asking for what"* — never *"who"*. Salt with the day so buckets do not become a
permanent cross-day fingerprint.
- **Record the served PATH, not just the status.** That one field gives per-service demand (and per-service
  sales) for free — the thing you would otherwise build a separate instrument for.
- **Make every write best-effort inside a `try/except`.** Telemetry must never be the reason a paid call
  fails; an unwritable path degrades to a no-op.
- **Bound the file** (rotate on size) so an unbounded ledger cannot fill a disk.
- **A MISSING ledger is "not recording", not "no traffic"** — different findings, and the reader must not
  confuse them. In practice it usually means the process has not been restarted since the middleware
  landed (most app servers do not hot-reload), so say that in the output rather than reporting a quiet
  zero. *This is the same rule as everywhere else: an unreadable instrument reports UNKNOWN.*
- **Report knocks against sales, not knocks alone.** `402 count` and `200 count` per path, with distinct
  callers for each, is the funnel stage the ledger exists to fill. Conversion is the derived number — print
  both inputs.

### Did the knock come BACK? A 402 is interest; a retry is intent; a retry on a FREE path is neither

**The most useful thing a status+path+caller ledger can answer is what a caller did NEXT.** Group the
ledger by caller, sort by time, and for every `402` look at that same caller's next request inside a short
window (two minutes is a reasonable line — longer is a new session).

```python
by = collections.defaultdict(list)
for r in rows: by[r['caller']].append(r)
for b, rs in by.items():
    rs.sort(key=lambda x: x['t'])
    for i, r in enumerate(rs[:-1]):
        if r['s'] == 402 and rs[i+1]['t'] - r['t'] < 120:
            print(b, r['path'], '->', rs[i+1]['path'], rs[i+1]['s']); break
```

Measured on ourselves over 7 days: **3,884 callers, 397 of whom retried within 120s of a 402 — and every
single one retried a FREE path** (`/openapi.json`, a different unpaid route). **Zero paid retries, zero
`402 → 200` with a payment header.**

- **Read that as three different findings, and never merge them.** *Retried the same paid route and got
  served* = a conversion. *Retried a different PAID route* = it is shopping and the first price was wrong.
  *Retried a FREE path* = it is looking for something free, which is a discovery problem wearing a
  conversion problem's clothes.
- **A paywall with zero paid retries and a healthy 402 rate is NOT a pricing problem.** The obstacle sits
  upstream of the price — the client has nothing to sign a payment with, or has never been taught that the
  paywall is payable. **Do not discount a price nobody reached for;** fix which clients arrive, and check
  that the advertised challenge names an asset and rail those clients actually hold.
- **This instrument only exists if the ledger hashes the caller.** Status and path alone cannot tell a
  retry from a different stranger, which is the entire question — so the caller hash is not a privacy
  nicety, it is the join key for intent.
- **State the denominator.** "397 of 3,884 callers came back" is a measurement; "people retry a lot" is
  not, and the two lead to opposite decisions.
