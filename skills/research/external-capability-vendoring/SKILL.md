---
name: external-capability-vendoring
description: "Use when adopting free third-party code or data."
version: 1.0.0
author: Arthur (Gentech EDU)
license: MIT
tags: [research, adoption, licensing, dependencies, github, data]
metadata:
  hermes:
    tags: [Research, Adoption, Licensing, Dependencies, Data, Fallback]
    related_skills: [third-party-skill-import, autonomous-web-research, blocked-page-recovery]
---

# External Capability Vendoring

**Standing instruction:** when we lack a capability, look for a free open-source source rather than building it
from scratch. This is the procedure for doing that **without importing the risk** — a stranger's licence,
a stranger's dependency graph, and a stranger's release cadence.

The deliverable is never "I found a repo". It is either **a file in our product** or **a stated, reasoned
decline**.

## When to Use

- The user says "see what you can find on github", "whatever skills you lack, find online for free", or asks
  whether a named library, tool, dataset or API can do something for us.
- You are about to `git clone` or `uv pip install` something to meet a need — run this first, so the evaluation
  happens **before** the dependency lands.
- A capability is missing and building it from scratch would cost days.
- You already know the tool you want, but not whether it is licensed, maintained, or safe enough to ship.

## Procedure

### 1. Discover — and treat a refused search API as a GATE, not an empty shelf
Use any general search surface. If the platform's own **search** endpoint refuses your account, say so out
loud — "the gate is X" — because the user needs to know a wall exists, not that the world is empty.
Platforms routinely block *search* while their **core API and `git clone` keep working**, and the tell is
`/rate_limit` reporting the **anonymous** bucket, which also proves the token was never honoured.

### 2. Verify the REPO, not the snippet
A search result carries no licence, no star count and no last-push date — and those are the facts that
decide adoption. Hit the core API per candidate:

```bash
python3 scripts/verify-repos.py owner/repo owner/other-repo
```

### 3. Run it before judging it
`uv venv` + `uv pip install` in throwaway scratch (a host with no `pip` module is normal). Point the library
at **our real material**, not a toy string. A candidate that finds a real defect in our own data on the first
run has earned its place; one you can only *describe* is documentation, not tooling.

#### If the candidate WRAPS another engine, test the ENGINE first — the wrapper's value IS that engine

A downloader, scraper, transcriber or converter is usually a front-end over a core tool it bundles or invokes.
Install the wrapper, see it handle a small case, and it is tempting to rule — but the wrapper inherits every
limit of its core, and the limit that decides adoption is **reachability from this host**.

**The stripped test, before any feature reading:** invoke the underlying engine directly (`yt-dlp -F <url>`,
`ffmpeg -i <url>`, `curl` at the target) and see whether it reaches the source at all. If the engine cannot fetch
from this address, the wrapper's format list, GUI and 1,800-site count are moot — nothing above the core can work,
and the verdict belongs to the engine, not the packaging. Say that in one line and stop, rather than spending the
session evaluating a front-end for a core that is not answering.

The general form: **when a candidate's value is delegated, evaluate the delegate.** Same reasoning as the plugin
case below, which tests registration against the platform's own predicate rather than the vendor's table.

#### If the candidate is a PLUGIN for our own platform, test REGISTRATION — not the vendor's compatibility table

A plugin's README states a minimum platform version, and that number is usually counted on a **different scheme**
than the engine reports (a marketing version like `1.70` against an engine reporting `0.22.6`). Comparing them is
not a comparison, so the version gap gets guessed at — and the guess becomes the reason a test never happens.

**The platform can answer it directly, in code, without installing anything:**

```bash
python3 scripts/hermes-plugin-gate.py /path/to/cloned-plugin
```

It calls the **engine's own discovery predicate** (never a re-implementation — a copy of the rule tests your copy),
reproduces the loader's import, and asserts the provider subclasses the platform's own base class. Read the
loader source when the predicate surprises you; it is the authoritative answer and it is short.

**Then check the two things registration cannot tell you:**

- **Does every hook shell out to a runtime we do not have?** A provider can import cleanly, register cleanly, and
  still be unable to serve one request because each hook spawns a helper. Grep the package for the runtime it
  requires and run that helper once. A user-space runtime installs into a scratch prefix with no root (and when
  the vendor's installer needs a tool the box lacks, the release archive usually extracts by another route).
  **Price the runtime as part of the adoption** — it is a real dependency, not an install detail.
- **Read the candidate's own health/doctor function before trusting its green.** Measured: a provider's `health()`
  returned `ok: true` on a box where its required runtime was absent, because it asserted three *file paths existed*
  and never touched the runtime every hook routes through. **A health check that only proves presence is a false
  green**, and it is the exact class this fleet keeps finding in its own instruments.

#### If the candidate is a GRADED CURRICULUM, test the grader on BOTH sides — and count only what runs here

A repo whose selling point is "every project is graded" is asking you to trust its own instrument. Treat the
grader as the thing under evaluation, not the thing doing the evaluating.

- **Run the reference solution AND the starter.** Reference passes, starter must **FAIL**. A grader that passes
  both grades nothing, and its "N/N green" is a description of a directory, not of learning. Quote both runs.
- **Read the exit codes, not just the words.** `solution → 0` and `starter → 1` is the shape that can be wired
  into a pipeline; a grader that exits `0` on a learner failure is unusable, however green the output looks.
  Capture the status with `out=$(cmd); rc=$?` — piping the command into another program reports the last stage's
  status, not the grader's.
- **Gate the adoption on the TOOLCHAIN the corpus needs, per item, and expect the headline count to shrink.**
  Count the machine-readable manifests and their declared languages first (`projects/*/project.json`), then
  compare against the runtimes the seat actually has. Measured on one candidate: Python 39 · TypeScript 28 ·
  Go 13 · Rust 10 against a box with `python3` and `node` only — so **four of the six projects that mapped to
  work we already run printed `SKIP … missing executable`**. Those four are not adopted, they are **deferred**,
  and a `SKIP` is never a pass: say which items grade today and what installing the runtime would cost
  (user-space install, no root), rather than adopting a track you cannot execute.
- **Count what the repo CONTAINS, not what its blurb claims.** A directory that is a harness or a docs folder
  sits inside the same listing as the items; counting subdirectories over-reports by one and every downstream
  ratio inherits it. Count manifests, print the number you counted, and correct the vendor's figure in the
  ruling.
- **Prefer LINK + PIN THE SHA over vendoring a media-heavy repo, and keep only the adopted subset.** A clone of
  a course repo ran to **329 MB on disk** because every item carried GIFs and screenshots — into a **synced**
  vault that is the wrong trade at any price. Pin the commit, link the source, vendor only our own adaptation
  notes plus upstream's licence — and if you keep the gradable subset locally, **re-run the grader from the
  pruned copy** to prove it is self-contained (`329 MB → 3.1 MB`, same 5/5 stages passing).

### 4. Apply the gates (a decline is a result, not a failure)

| Gate | Pass | Decline |
|---|---|---|
| **Licence** | permissive (`MIT`, `Apache-2.0`) | **no licence at all** — especially for DATA |
| **Activity** | pushed within months | dormant + no maintainer |
| **Blast radius** | a library we call | an installer that edits every profile's config/`.env` |
| **Fit** | solves a problem we have | "cool to have", or solves a solved problem |
| **Cost** | no key, or a key we hold | metered middleman over capability we own |

**An unlicensed repo is not public domain** — attractive data in exactly our domain is still a hard decline,
because you cannot build a shipped artifact on it and cannot untangle it once embedded. **A permissive code
licence does not cover the repo's DATA:** when the two differ, assume the data carries the stricter terms, and
say which one you checked.

**"Permissive" is not one thing, and "open source" does not mean MIT.** Measured across five candidate projects in
a single evaluation: exactly **one** was MIT and **four** were Apache-2.0. Apache-2.0 is still adoptable but it is
not interchangeable with MIT — it carries an explicit **patent grant**, a **NOTICE-file obligation** you must
carry into whatever you distribute, and it is incompatible with GPLv2-only projects. Read the licence **per
repo** (`GET /repos/<owner>/<repo>` → `license.spdx_id`) instead of accepting "they're all open source" for a
it is one cheap call per repo and it is the difference between a clean adoption and a remediation.

**A licence can be present, visible, and still unusable.** The gates table's two poles — permissive, or none at
all — leave out the shape that actually catches people, because a repo can display a licence file and still
forbid the only thing we do with it. Read for two families explicitly, both of which advertise themselves as
open source:

- **NonCommercial** (`CC BY-NC`, `CC BY-NC-SA`): fine to read, fatal to ship. A model, dataset or codebase under
  NC cannot appear in anything we sell, so *"it runs on our box"* and *"we may use it"* are different verdicts —
  state which one you established.
- **A vendor "Community Licence" wearing the word open**: a bespoke grant carrying a **territorial carve-out**
  (a header excluding the EU / UK / South Korea) and a **MAU trigger** requiring a negotiated licence above a
  user threshold. Source and weights may both be public and it is still not OSI open source; quoting it as free
  is a wrong claim about a real file.

**The check is one line of the licence head, not a survey:** `NonCommercial`, `does not apply in the`,
`monthly active users`, `research purposes only`. Run it per item and name the ones that fail — a set of ten
candidates routinely holds three or four, and they tend to be the ones with the best demo videos. **A repo that
ships a licence has not thereby granted us our use of it.**
remediation.

**Taking the IDEA and taking the CODE are different acts.** A licence governs the code; an algorithm, a rule or a
data flow described in a project's docs is not licensed material, so a clean reimplementation written from the
*description* is not a licence event — while copying the file is. Decide which one you are doing before citing the
licence, and when the answer is "the idea", say plainly that no code was copied, so a later reader does not have
to reconstruct which it was.

## Adopting for USE is a different question from adopting for RESALE

**A licence that lets you call a service says nothing about your right to sell its output.** The gates above
decide whether we may *use* a capability. The moment the plan is to charge for it, run one more test first,
because a per-call product built on someone else's data is a resale, and resale is a separate permission.

**The test: does the vendor ship code we run, or is every call to their endpoint?** Read the integration's own
disclosure line before anything else — a catalog entry or README usually states it outright. A connector
described as *hosted-only, no local code, every tool call goes to the vendor's server* is the answer: there is
no artifact to self-host and no data to sublicense. Reselling it is reselling their service.

**Rank the alternatives by CONTROL, not by how quickly they can be wired:**

| source | control | the catch |
|---|---|---|
| **Direct commercial API / the primary supplier** | **high** — a real agreement with published terms | onboarding, and the cheap tier is usually sandbox |
| **Partner / affiliate / redistribution API** | **medium** — built to be passed on | attribution rules; caching often forbidden |
| **Self-hosted scraping** | **full** — our box, our code | fragile by construction, and the terms exposure is now ours |
| **Hosted vendor connector** | **none** | resale is not ours to grant; their limits become our outage |

- **Design so the vendor's data is INPUT, not the product.** The durable asset is what we add on top — a stored
  price history, a scoring rule, a verdict the raw feed cannot produce. A product that *is* the vendor's output
  is one terms change away from zero, and it prices at their margin, not ours.
- **Say which gate blocks the product before quoting a price.** "We can search fares today" and "we can sell
  fares" are different claims; conflating them is how a business case gets built on an unusable source.
- **The cheapest work here costs nothing:** start accumulating the derived asset (history, rules, verdicts) on
  internal traffic now, so a licensed source later plugs into a product that already has a moat.

### 5. Vendor the ARTIFACT, never the dependency
Run the tool **once** to generate a static file the product stores; the consumer reads the file. The dependency
stays in the evaluation venv and never ships.

Why this is the default and not a nicety: an artifact works offline, cannot break when upstream releases,
cannot silently change our answers, and keeps the runtime surface at zero. Take a runtime dependency only when
the capability is genuinely dynamic (live data, a model, a service you must call each time).

### 6. Record the limit INSIDE the artifact
Give the file `_tool` (what generated it, with version), `_why`, and a `_LIMIT` field stating what it does
**not** do. A generated file that omits its own gaps gets read later as ground truth. Measured limits belong in
the artifact and in the write-up, not only in the chat that produced them.

### 7. Prove it end to end
Run the consumer and show the real output. Then add a guard so the artifact can never silently miss an entry —
a selftest that fails when a served item has no lookup is worth more than the artifact itself.

## Pitfalls

- **Verify the INCUMBENT is configured, not merely deployed, before benchmarking against it.** The
  "does it beat what we run" test above is only valid if what we run is doing its job. Measured: an incumbent
  recall provider was deployed, enabled and reporting healthy on every seat — while its read root pointed at a
  folder holding **1 to 7 files** against a 6,000+ note library, so its scores were the scores of a system that
  was barely running. Benchmarking a candidate against that would have made any competitor look better than it
  is. **Print the incumbent's own load/scan count and compare it to the size of the source** — a provider whose
  corpus is 1/1000th of the library has never been tested, it has been assumed.
- **REGISTERING IS NOT BEING BETTER — measure the candidate against the incumbent you already run, on the axis
  the user actually uses.** A capability can pass every gate, install cleanly on our engine, and still be a
  downgrade. Measured: a memory provider that registered perfectly backed its recall with a case-insensitive
  substring match over **page titles**, while the provider already deployed did BM25 over **note bodies** — so
  adopting it would have traded working text recall for a title index. The registration test answered "can we
  load it", which is not the question; the question is "does it beat what runs today on the data we have".
  **Run both against the same real corpus and compare the axis, not the feature list.**
- **Adopt the PIECE, not the package.** The valuable part of a declined candidate is often one algorithm inside a
  large runtime. Name the piece, price it against a ~60-line local implementation, and take the cheap version —
  "we declined the dependency" and "we got the capability" are not in conflict, and shipping both is the win.
- **Verify the installed API shape before writing the call — signature AND return container.** A library's
  README, its blog examples and the version actually pip-installed are three different things. Measured: the
  documented `FlightData(...)` constructor did not exist in the installed release (the real entry point was
  `create_query()`), and the call returned a plain list where the docs implied an object with `.flights`. Two
  wrong shapes read as "the library is broken" when the library was fine — the second one produced **0 offers
  from 11 real results**, a false negative indistinguishable from no data. Print `inspect.signature(fn)` and
  `type(result)` once, on the first run, before judging anything.
- **A second independent source is the cheapest validation there is — use it when one exists.** Two sources
  reporting the same number for the same input is worth more than either one being plausible: it validates the
  figure AND both instruments at once. Measured: a self-hosted rung and the hosted vendor both returned the
  identical fare for the same route and date, which is the first real cross-check on a price we quote.
  **Disagreement is equally useful** — it tells you which of the two is reading a different product (a
  different window, currency, or fare class) before either number reaches a decision.
- **Generate the artifact keyed by the value the CONSUMER looks up — after every transform, not before.** If
the consumer rewrites the key (a variant swap, a normalisation, a rename) the source key will never match and
the lookup fails silently for exactly one slice of users. Enumerate every rendered variant when you generate,
and let the guard prove each one resolves.
- **A tool's fallback is a wrong answer wearing a default.** If the capability has no proper value for this
input, resolve to **nothing** and have the consumer refuse; a borrowed default produces confident garbage that
nobody traces back to the substitution.
- **A comment claiming a capability is missing outlives the fact.** Config comments go stale while the config
keeps working, so re-verify against the live account or service — list what it *actually* has — rather than
trusting the sentence someone wrote when they wired it up.
- **Decline for WEIGHT loudly.** "No licence" is a hard no; "452 MB, and the data terms differ from the code
terms" is a different, equally valid verdict — name which one applies and why, or the next reader re-opens the
evaluation from scratch.
- **Never print a credential, and never pass one in argv.** Read keys from the seat's own `.env` or secrets
file inside the script; the key must not appear in output, in an error body, or in the process table.
- **Report compatibility (measured) and worth it (judged) as two separate claims.** A vendor can be perfectly
compatible and still be the wrong purchase.

## Related

- `third-party-skill-import` — same instincts for whole **agent skill** collections (SKILL.md packages), incl.
the decides-alone test and cherry-picking a catalogue.
- `autonomous-web-research`, `blocked-page-recovery` — what to do when a surface refuses to be fetched.
