---
name: borrow-the-mechanism
description: Jordan's preferred analytical frame for evaluating reference repos/links he shares — extract the mechanism, map against our stack, verify it runs, and reject the tool while adopting the idea. "Eat the meat, spit out the bones."
version: 1.0.0
author: Gentech
license: MIT
tags: [research, evaluation, github, reference-repo, mechanism-analysis, a2a]
---

# Borrow-the-Mechanism Analysis

Jordan's preferred frame for any reference repo/link he shares: **do NOT adopt the tool wholesale — extract the mechanism(s) that benefit us, wire them into our own stack, and reject the rest.** He stated it plainly (Aug 3, 2026) and it recurred across three links the same session (LoopX, awesome-llm-apps, kroger-mcp). He endorsed it explicitly: *"we can take different philosophies that benefit us and add them to the stack even if small."*

End every evaluation with a clear "borrow vs spit out" verdict — not a generic thumbs-up/down.

## The Frame — 5 steps

1. **Pull the repo** — GitHub API metadata + README, or clone to `/tmp` / `/root/repos/` for a real look (depth-1 clone is fine).
2. **Identify the core mechanisms** — what primitives does it actually implement? Name them concretely (e.g. "delegation scope narrowing", "trust scoring", "quota-aware should-run", "evidence lineage").
3. **Map each mechanism against our stack** — a table is clearest: `| primitive | we already have | borrow? |`. Mark `✅ already have` vs `🔴 real gap` vs `🟡 partial`.
4. **Verify it actually runs** — don't just read it. If self-contained, run it (`python3 file.py` or the repo's run command) to confirm before calling it real. A repo that "reads well but doesn't run" is a red flag. For a *skill/prompt* repo (agents, personas, curricula) "runs" means read the operational file end to end — the SKILL.md or system prompt is the artifact, and the enforcement text inside it is where the mechanism lives.

   **4a. Check the DELIVERY SHAPE can exist on the target host before judging features.** A GUI desktop app,
   a plugin that needs a display server, an MCP server that needs a runtime you do not have — each is
   *inoperable by construction* on a headless seat, and that is a **verdict about the tool**, not a gap to work
   around. Establish it first (does the host have a display? the toolchain to build it? the runtime the server
   declares?) so a long feature review does not end in "and none of it can run here".

   **4b. For a WRAPPER, test the ENGINE it wraps — on this host, before the wrapper.** A wrapper inherits every
   constraint of its engine and adds a UI; if the engine cannot do the job from here, the wrapper's feature list
   is decoration. Reproduce the engine's own call and read its real error: a network gate, a missing runtime, an
   auth requirement all survive the wrapping, and the wrapper's error message may blame something else entirely.
   **Then say which constraint it was** — "the engine is blocked from this host" is a finding about the world;
   "the app is bad" is a wrong conclusion drawn from it.

   **4c. When the artifact needs HARDWARE this host does not have, the test becomes the HOSTED DEMO — and the
   hardware question belongs to the seat that owns it.** Check for an accelerator first (`nvidia-smi`,
   `rocm-smi`); with none, nothing in that class is runnable here, and saying it once per item *is* the verdict
   rather than a caveat. Then find the publisher's own hosted demo (a HuggingFace Space, a browser build) and
   read its status code — **that is the only capability claim you can settle without the hardware, so it is the
   one worth reporting**, and a live demo is also the cheapest evidence that the mechanism is real at all. No
   hosted demo anywhere means the item is a **case study, not a candidate**. Do not estimate another seat's rig:
   accelerator capability is that seat's jurisdiction — hand the question to them and say plainly that you did.

   **4d. A published number about hardware ("67 FPS on an RTX 5080", "fits small-VRAM GPUs") is the author's
   measurement on the author's box.** Report it as their claim, name the missing variable (the card, the
   resolution, the batch size), and never let it stand in for "runs for us". Same rule as 4b: the constraint
   survives the marketing.

5. **Cross-check the math / invariants independently** — for any code that computes numbers (finance, risk, rates, percentages, APR, runway, PnL), **re-derive the formula from the docstrings and sweep it against the shipped code with your own probe.** A green test suite is only evidence that the test author believed the same thing; a randomized invariant sweep is evidence the code actually conserves the property. Report the number of cases and any mismatches explicitly. A mismatch is a `100×` unit discrepancy more often than a sign error, so check units first.
5. **Check whether it's really a product for us, not just a tool** — a shared artifact with our exact feature can be a **competitor's implementation or a customer's requirement list** rather than a build candidate. Name which one before assigning work.
5. **Borrow / spit out verdict** — be explicit:
   - **BORROW (the meat):** the 1-3 mechanisms worth taking into our design. Name each + where it wires in (skill, queue item, module).
   - **SPIT OUT (the bones):** the tool as a dependency, licensing constraints, wrong stack, corporate-owned control plane, non-applicable projections.

## Licence is a GATE, not a footnote — determine it before the verdict

The "spit out" list names licensing as a bone category. That is not enough: the licence decides whether an
otherwise-perfect mechanism can be used at all, so it is determined **before** the keep-list, not noted after
it. A shared post that advertises a set as *"open source"* or *"all free"* is making the claim you test.

**Procedure:**

1. **Read the API's `license.spdx_id`.** `MIT`, `Apache-2.0`, `BSD-*`, `MPL-2.0` are safe to build on.
2. **`NOASSERTION` means "go read the file" — never "unlicensed" and never "fine".** Fetch
   `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `License.txt` on both `main` and `master`; GitHub will not classify a
   custom agreement for you.
3. **Recognise the two classes that look open and are not:**
   - **`CC BY-NC-*` (NonCommercial)** — prohibits the commercial use a paid product, an x402 route or a
     customer deliverable requires. Perpetual bone, whatever the star count.
   - **Vendor "community licence" agreements** (Tencent, NVIDIA, Meta and peers publish their own) — these
     routinely **exclude territories** (*"does not apply in the European Union, United Kingdom and South
     Korea"*) and gate commercial use behind a **monthly-active-user threshold** that obliges you to request a
     licence. **They are not OSI open source** and must never be listed in a "free" column unqualified.
4. **State the licence beside every row, not once at the bottom.** A ten-item list where four are
   non-commercial is a different recommendation from a ten-item list that is all permissive, and a single
   footer sentence gets skimmed.
5. **Separate licence from maintenance.** A last push two years ago is a staleness fact; it says nothing about
   rights. Report both, and do not let "it is stale" stand in for "we cannot use it".

**A listicle is N evaluations, not one.** Measure every item — existence, stars, licence, last push — and say
which single one you would keep. Nodding at ten projects because the post is enthusiastic is the failure the
frame exists to prevent.

## Scope every benchmark number to the fixture that produced it

A reference repo that publishes an accuracy figure is publishing **a measurement on the author's
fixture, with the delta the author chose.** That is useful evidence and it is not our number.

- **Absorb the apparatus, re-measure the figure.** Take the mechanism; run it against **our**
  fixture before the number is ever repeated to a user or a customer. Quote it only as
  "their benchmark, on their contest" — never as a capability we can promise.
- **A published before/after delta is the most borrowable thing in the repo.** Vendors usually
  print only the after number. A repo that prints the weak version *beside* the strong one is
  handing over an honesty apparatus, and that apparatus is often worth more than the feature.
- **Name what the mechanism must NOT be allowed to mean, in the same breath as what it is for.**
  An absorbed capability drifts into a claim within days unless the boundary is written down with
  it. State the limit at absorption time, not at the first overreach.

## Classify the source by its sales motion before adopting its backlog

Before treating any list, curriculum, or backlog as a build order, ask **who is selling what to
whom.** The same item can be a product for us and a chore for someone else.

- A list written from the **consultancy / deploy-into-their-stack** side is frequently a
  **buyer's requirements document** — it describes the thing *we* sell. Read it as demand
  evidence, not as our roadmap.
- Enterprise-machinery items (SSO/SAML/SCIM connectors, HITL approval gates for chat tools,
  legacy-UI computer-use, compliance proxies, SOW pipelines) are **bones** for a company that has
  no enterprise contract to unblock. They look professional, which is exactly why they get
  mistaken for priorities.
- Apply the DECIDES-ALONE TEST to the whole list: does it make us better at deciding and acting on
  our own, or does it add deliberation and hand decisions back? A backlog of professional-looking
  deliberation is a bone however well-written it is.

**Pitfall: re-reading a list is not the same as refining it.** A second pass over the same source
that yields a *different* set of "meat" items means the first pass was associative, not
principled. Pick the frame (does it make us decide alone? what do we already sell?) and let it
determine the keep-list, so two passes agree.

**Pitfall: unit inconsistency across sibling modules is the most dangerous kind of correctness.**
Two functions in the same org, both named `apr`, returning a FRACTION in one module and a
PERCENT in the other is not a test failure — it is a semantic failure. Always compare units
across adjacent outputs before calling the math verified, and state the unit explicitly when
reporting a number.

## When the ask is "what do the OTHER PLAYERS do — let's mimic them"

**This is the same frame applied to peers instead of repos: find the standard, borrow it, ignore the taste.**
The unit of analysis is not a README, it is *the surface a buyer actually loads before deciding to pay.*

**Procedure, in this order:**

1. **Pick 4–6 peers that are actually getting used**, including at least one that ranks for your own product
   name. A peer that ranks has already solved discovery; its docs are the answer to the question you are asking.
2. **Read the machine surfaces, not the marketing page.** `llms.txt`, `skill.md`, `openapi.json`,
   `/.well-known/*`, and the per-product page. The marketing site tells you what they wish they were; the
   surface an agent loads tells you what they actually ship.
3. **Extract by RECURRENCE.** A pattern three peers share is a **standard** — not having it is a gap. A
   pattern one peer has is **taste** — borrow it only if it is cheap. Write the table with the count:
   `pattern | peers doing it | our status`.
4. **Read their failure documentation, which is usually the highest-trust block on the page.** A peer that
   publishes *"known failure modes"* per route hands an agent the ability to handle errors instead of
   retrying in a loop. Almost nobody does it, which is exactly why it differentiates.
5. **Separate the borrowable mechanism from the SEO furniture.** Tracking parameters stapled to the endpoint a
   reader is meant to call, canned "when to prefer this product" paragraphs, and keyword-stuffed headings are
   written for a crawler. An agent reads them as noise and they cost you nothing to skip.
6. **Ship the standard, not the imitation.** Adopt the shape, then generate it from your own source of truth
   (manifest, catalogue, inventory) so it cannot drift — the `discovery-and-listing` skill carries the
   build-and-verify recipe in its `buyer-facing-docs` reference.

**The tone rule, and it is the user's own:** a comparison like this is a **learning** exercise, not a
postmortem. Report `we don't have this` as a specification we have not met yet — and file each one in the
roadblock ledger with its gate, so the discovery becomes a check instead of a note nobody re-reads.

**Pitfall — do not stop at "we are missing X".** A sweep that produces a list of absences has produced a
backlog, not a plan. Convert each finding into one of three verdicts: *borrow now* (cheap, mechanical),
*borrow when triggered* (needs a precondition, e.g. a repeat payer), or *reject* (their reader is not our
reader). An un-triaged absence list becomes permanent guilt.

## Key pitfalls
- **Empty allow-list must mean DENY, never ALLOW.** Caught a real security bug in awesome-llm-apps' trust layer: an empty `allowed_actions` set originally read as "all allowed" (least-privilege hole). In ANY delegation/permission logic we build, an empty allow-list must deny.
- **Borrowing a mechanism ≠ adopting the dependency.** Often the right move is porting a ~200-line core into our own design (LoopX state kernel, trust-layer core), not installing their tool. Keeps us independent and avoids building around corporate-owned or churn-heavy projects.
- **Verify the tool actually solves the problem before recommending a key/cost.** e.g. kroger-mcp still needed a Kroger API key — it wrapped the blocker, didn't remove it. Don't oversell a repo with an external credential gate the user can't pass.
- **Re-anchor on the real problem.** When Jordan clarifies the true goal (e.g. "the Cookbook is about substitutions, not grocery prices"), re-evaluate against the real problem, not the initial framing.
- **When you correct your own finding, say so in the report — and update the skill, not just the log.** A wrong suspicion (e.g. "their CI is red") that you later disprove should be **withdrawn publicly** and the corrected conclusion stated. Do not leave the wrong claim in the transcript for the next agent to read as fact.

## Output shape Jordan expects
Lead with the verdict, not the architecture explainer:
```
**{Project}** — {stars/license/stack}
**The mechanism worth borrowing:** {one-liner}
**Where it wires into our stack:** {skill / queue item / module}
**Verdict:** Borrow the {mechanism}; spit out the {tool/dependency}
```

## Where the borrows land
- Mechanisms worth adding to our design → `agent-handoff-enforcement`, `considerations.md`, build queue, or a new spec under `09-Green Room/specs/`.   <!-- ⚠️ not installed (checked 2026-11-17): no skill named `agent-handoff-enforcement` exists on this seat -->
- Deep-dive analysis notes → `09-Green Room/specs/{topic}-deep-dive.md` (or `03-Projects/Research/`).
- Vault changes should follow the wiring: one link can trigger multiple vault files (spec + queue item + skill patch).

## Support references
- `references/vault-routing-file.md` — how to route vault writes efficiently before scanning.
- `references/port-and-verify-mocked-backend.md` — porting a mechanism and testing it against a mocked backend without API cost.
- `references/independent-math-verification.md` — when the repo computes numbers: re-derive, sweep, and check units across modules.

## Working examples (Aug 3, 2026)
- **LoopX** (state kernel / control plane, 680★) → borrowed: explicit user gates, quota-aware `should-run`, evidence-lineage stubs; rejected: the tool + Feishu projection + Bytedance-adjacent control plane. Wired into `agent-handoff-enforcement` skill; spec at `09-Green Room/specs/loopx-a2a-handoff-borrow.md`.
- **awesome-llm-apps multi-agent trust layer** (Apache-2.0, 130K★, verified running) → borrowed: delegation-scope narrowing + trust scoring; cloned to `/root/repos/`; deep-dive at `09-Green Room/specs/a2a-trust-layer-deep-dive.md`.
- **kroger-mcp** (66★) → evaluated, found it still needs the Kroger API key the user can't get → pivoted to the real Cookbook substitution problem (no external keys needed).

## ⚠️ Same phrase, different job

**"Eat the meat, spit out the bones" is used in two places, and they are not the same procedure:**

- **here** — evaluating a reference repo or link: extract the mechanism, reject the tool
- **`agent-kit/eat-the-meat-spit-out-the-bones`** — processing an *archive*: read it once, keep what
  earns keeping, drop the rest, write the receipt

**If the task is "someone shared a repo/idea," use this skill. If the task is "we have an old folder /
backup / dump," use the other one.**
