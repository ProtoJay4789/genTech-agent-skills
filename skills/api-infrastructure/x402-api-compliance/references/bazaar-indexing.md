# Bazaar indexing — why a payable API earns nothing

An API can pass every x402 check, answer 402 correctly on six rails, settle payments, and still earn **zero**: because no buyer is ever *shown* it. Discovery and correctness are separate gates, and a service can fail discovery while passing correctness perfectly.

---

## 1. THE GATE: a catalogue indexes on SETTLEMENT, not on registration

The CDP Bazaar (the catalogue agents actually query) has **no registration form**. It catalogues a resource **the first time that resource settles a payment**. Two consequences that combine into a trap:

- **You need a buyer to become visible to buyers.** A brand-new service with no sales is listed nowhere, so it cannot attract its first sale.
- **Visibility is revocable by silence.** A listed resource with no activity inside a rolling window (~30 days) drops out of results. Newly indexed resources are exempt until they have calls.

⇒ **A service that is quiet for a month must re-earn its listing.** Treat a maintenance call as part of staying listed, not as optional traffic.

**Facilitator choice decides which catalogue can see you.** A settlement routed through facilitator A does not appear in facilitator B's catalogue, and some catalogues only see settlements routed through *their own* endpoint. If you settle through several facilitators, check each catalogue separately rather than assuming a settlement propagates everywhere.

---

## 2. `paymentPayload.resource` — OPTIONAL in the spec, REQUIRED for discovery

The x402 v2 spec marks `resource` **Optional** in `PaymentPayload` (§5.2.2) and **Required** in `PaymentRequired` (§5.1.2). Nothing rejects a settlement payload that omits it, and no error appears anywhere. **That optionality is why the defect survives for weeks** — the payment succeeds, the money moves, and only the listing is silently absent.

The vendor's seller guide is stricter than the spec:

> *"The payment payload sent to the facilitator must include `paymentPayload.resource` so the facilitator knows which resource to catalog."*

⇒ **A field that is optional-for-correctness can still be required-for-discovery.** When a vendor's success path depends on a field its own spec calls optional, the vendor guide outranks the spec — and neither replaces reading what you actually send.

**The diagnostic that finds it:** settle takes the same structure as verify (`{paymentPayload, paymentRequirements}`), so **whatever the payload does not say, settlement does not say.** Grep the settlement builder for the resource field. If it appears zero times, every settlement you have ever taken is **real but unattributable** — money moved, nothing was catalogued.

### Attach it in ONE helper, at every call site

A gateway supporting several facilitators normally has **several near-identical settlement builders** (CDP, a generic facilitator client, plus one per non-EVM rail). Each builds the same envelope. **A field present on one path and absent on another is not a partial fix — it is an intermittent fix whose failure depends on which rail the buyer chose**, and it stays invisible until someone buys through the unpatched one.

```python
def _with_resource(pp: dict, request_url: str | None) -> dict:
    """Attach paymentPayload.resource — the field that lets a facilitator INDEX what was bought."""
    if not request_url:
        return pp                    # degrade: never invent a URL
    out = dict(pp)
    out.setdefault("resource", {    # setdefault: never overwrite a caller-supplied value
        "url": request_url,
        "description": "<service> x402 resource",
        "mimeType": "application/json",
    })
    return out
```

Three properties are load-bearing, and each is testable in isolation:

- **`setdefault`, not assignment** — a caller that already supplied `resource` keeps it.
- **The URL is always the REQUEST being served**, never a value taken from the caller's payload. A settlement must never be attributable to a route that was not called.
- **No URL → return unchanged.** Degrading beats inventing a resource.

Then call it from **every** builder. Verify by counting call sites against the number of builders — if the counts differ, one path is unpatched.

---

## 3. MEASURE YOUR OWN PRESENCE — the index is public

The discovery catalogues answer without credentials, so "are we listed?" is measurable, not an opinion. Query it, paginate it, and match on **your own `payTo`**.

```python
import json, urllib.request
base, ours = "<facilitator>/discovery/resources", "0xYOURPAYTO".lower()
hits = total = offset = 0
while True:
    d = json.load(urllib.request.urlopen(f"{base}?limit=100&offset={offset}", timeout=30))
    items = d.get("items") or []
    total = (d.get("pagination") or {}).get("total", total)
    hits += sum(1 for x in items for a in x.get("accepts", [])
                if (a.get("payTo") or "").lower() == ours)
    offset += len(items)
    if not items or (total and offset >= total):
        break
print(f"{hits} of {total} listings pay to us")
```

**One page is not the catalogue** — catalogs run to tens of thousands of entries and `limit` alone silently truncates. **`0 of N` is the finding that ends the guessing:** it converts "buyers are not converting" into "we are not in the room", which are different problems with different fixes.

---

## 4. "WE QUOTE BUT NEVER SELL" — the diagnostic ladder, in order

Run these in sequence. Each rung rules out a whole class of cause, and stopping early is how a wrong cause gets a confident write-up.

**Rung 1 — who is actually knocking?** Classify by declared `User-Agent`, not by count.

| caller kind | can it ever pay? |
|---|---|
| uptime / liveness / health-check probes | **never — by design** |
| directory / crawler / list-observer | no — indexing, not buying |
| conformance / spec testers | no — verifying, not purchasing |
| unlabelled HTTP clients (`curl`, `axios`, `node`) | unknown |

Many say so in their own header string (`…unpaid liveness check, never settles`, `…never pays`). **A high request count made of monitors and directories is not demand**, and calling it demand is the flattering number that hides the gap for weeks.

**Rung 2 — did anything reach a PAID route?** Split `2xx` on deep routes from `2xx` on index/manifest/docs/health endpoints. The second set is not traffic, it is discovery of the door.

**Rung 3 — are we in the catalogue?** §3. If zero, everything above is irrelevant: buyers are not choosing against you, they were never shown you.

**Rung 4 — is our price out of line with the market?** Measure rather than reason: pull the catalogue's own listings and compare medians for comparable categories. **Rule price out LAST, and rule it out with a number** — a price war fought against traffic that cannot buy destroys margin and changes nothing. If the cheapest route in a catalogue converts at zero, price is not the binding constraint.

⇒ **Write-ups must name which rung failed.** "Not pricing" is only a finding once rungs 1–3 have been measured.

---

## 5. BEFORE BLAMING THE VENDOR, READ YOUR OWN PAYLOAD

A vendor's index not containing you looks identical whether the vendor is broken or your request is malformed. Filing first is expensive: it burns credibility in the one repo that owns the catalogue, and the answer is often in your own code.

**The pre-ticket audit — every one of these must pass before a ticket is defensible:**

1. The 402's required fields (`x402Version`, `resource`, `accepts`) and every `accepts[]` required field (`scheme`, `network`, `amount`, `asset`, `payTo`, `maxTimeoutSeconds`).
2. Every `network` in CAIP-2 form — **one malformed rail invalidates the entire payload**, so validate all of them, not just the one you are testing.
3. Your discovery extension validates against the **SDK's own model**, not against your reading of the docs. Import the type and validate your live object with it.
4. The settlement payload carries everything §2 requires.
5. The settlement actually routed to the facilitator that owns the catalogue you are checking.

Only when all five pass is "our request is spec-correct and the catalogue is empty" a sentence worth publishing.

**Then respect the venue.** Read the project's `CONTRIBUTING.md` and issue-template config before opening anything: trackers routinely route "my service is not indexed" **away** from the tracker to a chat channel, and a maintainer may ask for **resource-specific new tickets, not corroboration on old threads.** Corroborating a months-old thread is the fastest way to be ignored; a fresh ticket carrying your endpoint, facilitator, `payTo`, settlement transaction and the exact empty query is not.

**Vendor contact pages frequently prohibit sales outreach.** Read the contact page before drafting: many state plainly that promotional or partnership requests are not accepted on the support channel. An integration question ("does a settlement through you propagate to catalogue X?") belongs there; "what should we build?" does not.

---

## 6. NEVER FABRICATE A SETTLEMENT TO TRIGGER INDEXING

The temptation is obvious: listing is gated on a settlement, so take one yourself. If you do this at all it must be a **real call to a real route returning real data, with real money moving through the facilitator that owns the catalogue.** A simulated or self-signed "settlement" to force a listing produces a catalogue entry backed by nothing — the same class of defect as a fabricated receipt, and the kind of thing a reviewer finds.

It may not work anyway: independent reports describe settlements that carried a correct declaration, returned an accepted status, and never appeared. So **budget for the possibility that the listing fails for reasons outside your control**, keep the audit trail proving your request was well-formed, and treat that evidence — not another attempt — as the next deliverable.

---

## 7. THE AUDIT HABIT

Three wrong diagnoses in one sitting all came from testing the wrong layer: traffic behaviour (when the traffic could never buy), index presence (right fact, wrong owner), and field requirement (right defect, wrong severity — *optional* in the spec). **Each correction came from checking exactly one layer deeper than the claim.**

⇒ Before publishing a cause, ask: *is the thing I measured the thing that decides this?* If the answer is a count of visitors, a timestamp, or a field's spec severity, it probably is not.
