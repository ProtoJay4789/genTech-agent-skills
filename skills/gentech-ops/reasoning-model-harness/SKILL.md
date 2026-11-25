---
name: reasoning-model-harness
description: "Use when reasoning models return empty content."
version: 1.1.0
author: gentech
category: gentech-ops
hermes:
  tags: [harness, reasoning, generation, delivery-rate]
  trigger: "When any reasoning model returns empty content / finish:length, or when comparing model tiers on a real task and you need a delivery rate rather than a vibe"
---

# Reasoning-Model Harness — Don't Burn the Tank in Neutral

## The Problem (proven Aug 16, 2026)
Reasoning-first models (Kimi K3, GLM 5.2) on OpenCode Go spend their ENTIRE
`max_tokens` budget on `reasoning_content` before emitting any `content`.
Result: `finish_reason: "length"`, `content: ""`, 40-56K chars of reasoning,
zero output. This is a HARNESS mismatch, not a broken model.

## Symptoms
- HTTP 200, `cost: 0`, but `content` is empty
- `usage.completion_tokens` == your `max_tokens` (all burned)
- `message.reasoning_content` is huge (tens of thousands of chars)
- `finish_reason: "length"`

## Fixes (in order of reliability)

### 1. Use a code-specialized model for generation
`kimi-k2.7-code` is tuned to write code directly. But it can ALSO reason long
on big tasks — if it hangs >5 min, kill it and build manually.

### 2. Try `thinking: {type: "disabled"}`
Works reliably on SHORT queries (verified: instant reply, no reasoning burn).
On COMPLEX generation tasks the model may still reason anyway. Worth one try.

```json
{"model":"glm-5.2","messages":[...],"max_tokens":16000,"thinking":{"type":"disabled"}}
```

### 3. Build it yourself (most reliable)
For a full artifact (landing page, dashboard), don't fight the API. You have
the baseline + requirements — write the file directly. The model is for
reasoning/audit, not for one-shot large generation through this harness.

## Ollama Cloud AUDIT access (verified Sep 8 2026 — "models down" was a false alarm)
All audit models are LIVE on Ollama Cloud: `glm-5.2`, `glm-5.3-flash`, `kimi-k2.7-code`, `kimi-k3`, `gpt-oss:20b/120b` etc (19 total, verify via `/v1/models`). Two false "can't audit" symptoms:
1. **EmptyStreamError** (log: `provider=ollama-cloud ... Stream drop ... EmptyStreamError ... via=Google Frontend`, HTTP 200, empty body) is an upstream SSE hiccup, NOT a dead model — retry clears it.
2. **Reasoning models return `content:""` + `finish:"length"` on small budgets** (the harness trap below) — give AUDIT calls ≥500 tokens (1000-4000 real audits). Verified both glm-5.3-flash + kimi-k2.7-code return real content at max_tokens:500.
Workaround curl (shared OLLAMA_API_KEY, no new creds): `curl -s -X POST https://ollama.com/v1/chat/completions -H "Authorization: Bearer $KEY" -d '{"model":"glm-5.3-flash","messages":[...],"max_tokens":2000}'`.

## MEASURED: thinking vs acting (2026-09-22) — and the counter-intuitive rule

Jordan's read: *"Kimi K3 had the same issue Jev had where it did more thinking and reasoning than
acting."* Measured directly — same task, two framings, two budgets:

| Framing | Budget | reasoning | answer | thinking share |
|---|---|---|---|---|
| as a QUESTION | 300 | 1,022 ch | **0 ch** (`done=length`) | 100% |
| as a QUESTION | 4000 | 2,838 ch | 545 ch | 84% |
| as a JOB | 300 | 649 ch | 62 ch (correct) | 91% |
| as a JOB | 4000 | 1,250 ch | **14 ch** | 99% |

**Two rules, both opposite to intuition:**

1. **A BIGGER BUDGET MAKES THE ANSWER SHORTER.** 4000 tokens bought a 14-character answer; 300
   bought a usable one. More rope is just more rope to think with. Budget it tight.
2. **Frame the ask as a JOB, not a question.** Question framing at a tight budget produced
   literally nothing; job framing at the same budget produced a correct answer.

**Why K3 is still worth using — the role, not the model.** As a WORKER this disposition is pure
waste: it spends the budget getting to an answer it never writes down. As an AUDITOR the reasoning
IS the deliverable. The exact trait that makes it a bad builder makes it a good critic. **Same
engine, different gear** — so we give it a GENEROUS budget for audits (we want the deliberation)
and a TIGHT one if we ever need it to emit something.

⚠️ **Do not repeat Jordan's Jev analogy without checking it.** Our own Sep 19 deep dive recorded
TypeSafe AI's Jev as a **System One** decision model — deliberately fast, ~0.4 s typed decision,
calibrated confidence. Its whole design is about NOT over-thinking, so it is the wrong comparison
for a reasoning-burn failure. Correct the premise rather than agreeing with it.

## Calling OpenCode Go DIRECTLY (not via Hermes) — three things that fail first

When you bypass the agent and curl the rail yourself (`https://opencode.ai/zen/go/v1/chat/completions`),
these three all look like a broken model and are not:

1. **`{"type":"MissingSessionID"}` — the `x-opencode-session` header is REQUIRED.**
   Send any stable string: `-H "x-opencode-session: <anything-stable>"`. Without it the rail refuses
   to route at all.
2. **Model ids are BARE — no provider prefix.** `deepseek-v4.1-flash` works;
   `deepseek/deepseek-v4.1-flash` returns `{"message":"Upstream request failed: Model is unavailable."}`.
   List the real ids with `GET /v1/models` rather than guessing from Hermes config (which uses the
   slashed form for a different provider).
3. **The rail serves 28 models; the reasoning-heavy ones are the ones that return empty.** Measured
   on a plain structured question: `kimi-k3`, `glm-5.3`, `deepseek-v4.1-flash` → `finish_reason:
   length` with **0 characters of content**; `deepseek-v4-pro` and `qwen3-max` did not return inside
   180 s. All of these answered cleanly and fast: `claude-haiku-5-5` (1.1 s), `glm-5.3-flash`
   (1.4 s), `minimax-m3.1-flash` (1.5 s), `mimo-v2.6-flash` (4.0 s), `qwen3.8-flash` (8.2 s),
   `grok-4.7` (12.6 s).

**Rule: for a structured, checkable answer, reach for a fast non-reasoning model first.** Reserve the
reasoning models for genuine audits where the deliberation IS the deliverable.

## ⚠️ Six models answering one question is NOT verification — measured

Given identical evidence and one factual question with two halves ("repo is size 0, 54 scripts exist
locally — built, partially built, or not built?"), six working models split **2 vs 4** and every
answer was confident:

```
partially built : glm-5.3-flash, claude-haiku-5-5     (both noticed the local scripts)
not built       : qwen3.8-flash, mimo-v2.6-flash, minimax-m3.1-flash, grok-4.7   (both noticed the empty repo)
```

**Not one said "this depends which half you mean."** They each resolved the ambiguity silently in a
different direction.

**So: a model call is an opinion, not a measurement.** Do not aggregate several model opinions and
call the majority a verdict — on an ambiguous question the split is 50/50 dressed as certainty, and a
larger model just writes a more persuasive version of the same coin-flip. **If the question has two
halves, split it into two questions before asking anything.** For facts about the estate, read the
filesystem or the API and let a model only summarise what you already proved.

## The Lesson (Jordan's insight)
> The model is the engine. The harness is the transmission. Same engine, wrong
> gear = burn the whole tank in neutral.

This is why harnesses are "the next big thing" — a reasoning model called wrong
is useless; the same model called right is a weapon. Match the model to the
task: reasoning models for hard problems, code models for generation, and
manual build when the harness fights you.

## 🚨 FIELD NAME TRAP — the right key DEPENDS ON THE ENDPOINT (corrected 2026-09-23)
**`reasoning_content` is never the right key on Ollama Cloud.** But the correct key is not one name
either — measured live on `kimi-k3`, same question, both endpoints:

| endpoint | message keys | deliberation in | `usage` |
|---|---|---|---|
| `/v1/chat/completions` | `['content','reasoning','role']` | **`reasoning`** | returned |
| `/api/chat` | `['content','role','thinking']` | **`thinking`** | `None` |

An extractor reading `reasoning_content` gets `""` for both, and a *successful* 44K-char audit
reports `reasoning: 0, content: 0, finish: length` — which reads exactly like "burned the budget in
neutral." It did not. Read `content` for the answer in both cases; pick the deliberation key by
endpoint. **DUMP `sorted(message.keys())` before concluding a model is broken or empty.** Costs one
call and prevents a false "the model can't do it" verdict.

## Using a reasoning model as an AUDITOR / READER — scope the thinking, or it edits instead of checks

**The trait that makes a reasoning model a bad writer makes it a good critic — but only if the audit question is
the ONLY thing it is allowed to think about.** Left unstated, a reasoning model spends its budget on *how to phrase
a better answer*, and the "audit" comes back full of style notes and absent of truth notes.

Three settings, all measured on a writer/reader pair (cheap model drafts, reasoning model audits):

1. **STATE THE SCOPE IN THE SYSTEM PROMPT, narrowly.** One question — *"does this draft accurately represent the
   situation described in FACTS"* — plus explicit refusals: do not improve the writing, do not propose a better
   answer, do not invent facts. The reader's value is that it did not write the thing; give it a licence to
   improve the text and it stops being an independent read.
2. **Send the effort/budget EXPLICITLY; never inherit it.** The seat's own `reasoning_effort` is tuned for
   different work (writing, code, routing) and a reader call that inherits it reasons to the wrong depth for the
   wrong job. Set it on the call.
3. **Read `content` FIRST; treat the deliberation key as a transcript, and LABEL it if you print it.** Use the
   endpoint's key — `reasoning` on `/v1/chat/completions`, `thinking` on `/api/chat`, never `reasoning_content`
   on Ollama Cloud (see the field-name section below). A reader
   call can return a clean verdict in `content` **and** thousands of characters of deliberation in
   that key — the first version of a proofreader printed the transcript, so a correct `VERDICT: PASS`
   arrived buried inside what looked like the model thinking out loud, and the human-facing output was unreadable.
   If you must fall back to the transcript, say so in the output (`[deliberation transcript — verdict read from
   it, not quoted]`); an unlabelled transcript reads as the verdict itself.
4. **An empty reader response is UNRESOLVED, never PASS.** Same rule as everywhere else in this skill: a 0-char
   answer did not clear the work. A verification pipeline that defaults an empty audit to "passed" is the
   false-green this whole family exists to prevent.

**Say which model answered, and whether the rails were independent.** When only one provider key exists, a
writer/reader pair on the same rail is **cross-model on one rail** — a genuine independent read of the model, and
a false claim of independence at the provider level. Print the distinction on every verdict rather than calling it
cross-provider.

**The refusing direction is the test.** A reader that PASSes everything is decoration: feed it an input that must be
rejected (facts that do not support the draft, a claim its own evidence block contradicts) and confirm it FAILs,
before trusting any PASS it gives.

## DELIVERY RATE IS THE METRIC — a tier is not better because it is bigger

Measured on one real task (a 120-word status note from a fixed fact sheet, every claim sourced, `UNKNOWN`
where unknown, plus one named risk), same prompt, same 2,600-token budget, five tiers:

| tier | seconds | words in `content` | finish |
|---|---|---|---|
| `gpt-oss:20b` | 4 | 127 | `stop` |
| `deepseek-v4-pro` | 8 | 115 | `stop` |
| frontier A | 47 | **0** | `length` |
| frontier B | 22 | **0** | `length` |
| frontier C | 53 | **0** | `length` |

**Three of five delivered nothing**, at a budget a 20B model finished inside. So the first number to quote for
any tier comparison is **delivery rate** — non-empty `content` with `finish: stop` — before quality is discussed
at all.

- **A landing instruction in the system prompt does NOT fix it.** Telling the model that its reasoning "exists
  only to produce the finished note" and that "thinking without shipping = failure" changed nothing: six calls
  across three models, all still empty at the same budget. Do not spend a session on prompt wording for this.
  Budget, framing (job vs question, above) and model choice are the levers with measured effects.
- **Score quality only on models that delivered.** Rating a non-delivering tier on accuracy is rating an empty
  string.
- **The axis that separates a cheap tier from an expensive one is fact-integrity, not fluency.** On the two that
  delivered: the small model inverted a decisive fact — it claimed a settlement transaction we had verified was
  *absent* from the log and named that absence as the biggest risk — while the larger one stated the negative
  correctly. Same length, same shape, one unusable. That is what to score.

## THE FIX, MEASURED — `reasoning_effort: "low"` is the intent dial (2026-11-14)

Jordan's read, before any measurement: *"when you're testing those other models, you have to add intent. The reasoning
has to have the intent or it's gonna crash out on itself."* Correct, and it is the only lever that worked.

Same 120-word document task, five models, four settings, one variable each:

| setting | delivered | total tokens | note |
|---|---|---|---|
| baseline (no effort hint), 2,600 | **1/5** | 12,778 | three models returned `content: ""` |
| `max_tokens: 8000` | **3/5** | 29,131 | 2.3× the cost, still two dead |
| system prompt: *"your reasoning exists only to produce the answer; thinking without shipping = failure"* | **2/5** | 9,954 | prose intent does not reach the sampler |
| **`reasoning_effort: "low"`** | **5/5** | **10,402** | the cheapest AND the only complete setting |

Per model, `words in content / tokens spent`:

| model | baseline | 8k budget | low effort |
|---|---|---|---|
| `kimi-k3.1-pro` | 0 / 2600 | 161 / 6771 | **145 / 1281** |
| `minimax-m3` | 0 / 2600 | **0 / 8000** | **143 / 4677** |
| `mistral-large-4` | 0 / 2600 | **0 / 8000** | **98 / 823** |
| `deepseek-v4-pro` | 0 / 2600 | 146 / 4893 | **106 / 1734** |
| `gpt-oss:20b` | 139 / 2378 | 145 / 1467 | 123 / 1887 |

**Four rules, all measured:**

1. **Intent must reach the REQUEST, not the prose.** A system prompt explaining what the reasoning is *for* changed
   nothing (2/5). `reasoning_effort` changed everything (5/5). If you are writing persuasive sentences to a model
   about being brief, you are working on the wrong layer.
2. **A bigger budget is not a lever — it is a bigger bill.** 8,000 tokens bought 2.3× the spend and `minimax-m3`
   still delivered nothing. This is the same finding as the 2026-09-22 table (bigger budget → shorter answer),
   now with a delivery rate attached.
3. **Low effort is cheaper, not a compromise.** `mistral-large-4` wrote the same 98-word document in **823 tokens**
   at low effort after burning **8,000** for nothing at baseline. 10× cheaper to succeed than to fail.
4. **Default it, do not remember it.** Every caller of `scripts/rail.py` now builds its body through
   `rail.chat_payload(...)`, which sets `reasoning_effort: "low"` unless told otherwise. A hand-built payload that
   omits it fails **silently** — HTTP 200, empty `content`, no error — so it can survive for months.

**When to raise it:** only when the deliberation IS the deliverable (a genuine audit, a design review). Then set a
generous budget *and* a higher effort deliberately, and say so at the call site. Never leave it unset.

## 🚨 AN EMPTY RESPONSE MUST NOT BECOME AN EMPTY RESULT SET

**The most damaging form of the empty-content failure is downstream, not upstream.** A script that asks a model for
*N items* and gets `""` back will happily parse it into an empty list, then report **"0 items generated"** — which
reads exactly like *the source had nothing in it*. That is the same false-green family as a monitor reporting
a green light it never checked: an instrument failure wearing the costume of a finding.

Measured on structured generation (a JSON array of questions from a ~5 KB source, `deepseek-v4.1-flash`):

| `max_tokens` | deliberation | `content` |
|---|---|---|
| 3000 | ~2,000–2,600 tokens | **0 chars** |
| 4000 | ~2,600 | full array |
| 9000 | ~2,000 | full array |

Rules that follow, and they apply to every generator script:

1. **Budget must clear deliberation AND the artefact.** The rule "budget it tight" applies to short prose answers;
   a multi-item JSON artefact over a multi-KB source needs the deliberation cost *plus* the output, and ~3,000
   tokens does not cover both. Scale the budget with the size of the requested artefact.
2. **Treat `content == ""` as an ERROR with the `finish_reason` attached** — retry once at double the budget, then
   raise naming the reason. Never return it as an empty collection.
3. **Print the funnel, not just the count.** `generated N · kept M · dropped K` distinguishes "the source was
   empty" from "the model returned nothing" from "the output failed validation". A bare `0` cannot.
4. **A validator that never rejects anything is not running.** If every generated item survives, check the
   rejection path against a deliberately ungrounded input before believing the pass.

## Pitfalls
- Don't retry the same reasoning model with a bigger budget — it just reasons longer, and (measured)
  it answers SHORTER. Tighten the budget, and frame the ask as a job rather than a question.
- A reasoning model that returns an empty `content` did not decline the task — it spent the budget
  reasoning and was cut off. Check `done_reason == "length"` before assuming anything else.
- `thinking: disabled` is not a guarantee on complex tasks.
- Dump the message keys before trusting a length check — read the endpoint's deliberation key
  (`reasoning`, `thinking`), not `reasoning_content`.
- **When you find the field trap, sweep the reader FAMILY, not the script that bit you.** The trap was documented
  in this skill for months while the extractor in every downstream script still read a key that does not exist on
  the rail — so a reasoning model's real answer arrived as an empty string, indistinguishable from
  `finish: length`, and `proofread` reported "no output" instead of a verdict. Grep the whole script tree for the
  wrong key and make shared readers accept the endpoint-appropriate one, or the bug returns through another tool.
- **An unlabelled deliberation print reads as the verdict.** When the reasoning stream is the fallback and it
  carries the real conclusion, labelling it is not cosmetic — the reader cannot otherwise tell a model thinking
  out loud from a model's answer.
- OpenCode Go reports `cost: 0` — free, but don't waste time on it.
