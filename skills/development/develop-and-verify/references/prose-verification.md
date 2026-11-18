# Prose verification — draft with Jr, audit with Sr, fact-check with neither

Depth for the "Prose gets the same gate as code" rule. Load when you are about to send words to an outside
party under the user's name: an issue reply, a client message, a listing description, a public post.

## The three phases, and why the order is fixed

```
1 WRITE      prose-write.py    cheap model drafts FROM A FACT BLOCK and may claim nothing outside it
2 FACT-CHECK proofread.py      deterministic — no model: addresses, links, counts, hedges
3 PROOFREAD  prose-write.py    a different model reads the draft against the same fact block
```

**Deterministic checks run before the model, not after.** A wrong service count or an address that appears in no
record is a *fact*; a model's opinion cannot overrule it, and a model asked first will happily praise the sentence.

## The fact block is the mechanism, not a nicety

A draft can only be as honest as the block it was written from. Write it as claims plus an explicit prohibition:

```
FACTS (everything you may claim):
- <claim with its number>
- <claim with its number>
- We verified <thing>: <transaction / block / artifact> — <exact identifier>
- <the unflattering number, e.g. how small we actually are>

DO NOT CLAIM: that we solved their specific problem, that our approach is correct for their project,
any number not listed above, or that we have a fix ready as a pull request.
```

**Include the unflattering number.** A model told only the good facts writes a brochure; a model handed "we have
four payers in thirty days" volunteers it, and volunteering it is what makes the reply credible.

## Exit codes worth branching on

| code | meaning | what to do |
|---|---|---|
| 0 | PASS — sendable | send (the human still sends it) |
| 1 | REVISE — findings listed | fix the sentence, re-run |
| 2 | UNRESOLVED — an instrument could not run | do **not** treat as pass; the draft is unverified |
| 3 | FAIL — a false claim about our own system | **do not send** |

## Four traps that cost a round each

**A reasoning model returns deliberation, not a verdict.** Read `content` first and fall back to
`reasoning_content` only when it is empty — and **label the fallback**, because a transcript of the model thinking
aloud is not an answer, even when the `VERDICT:` line inside it is correct.

**A NON-REPLY passes both phases.** "We have not encountered this problem; that is all I can report" is true,
on-topic, and worthless. It costs the reader attention and returns nothing, and it looks like engagement. **The
writer may not draft one; the reader must judge one FAIL.** Test this explicitly with a facts block that does not
support a reply — the correct output is `NO REPLY — insufficient facts`, not a polite shrug.

**One templated remedy pasted across different claims manufactures the generic reply.** A scanner that detects
three failure classes and prints one fixed sentence produces nonsense on two of them. **Key every drafted sentence
to the claim it answers**; when no remedy exists for that claim, print that instead of borrowing one.

**An audit that never refuses is decoration.** Run the refusing case first: a draft with a wrong count, a dead link,
an unverified address, a hedge ("probably", "should be", "we believe"). If none of them fail, the gate is not wired.

The second reader is **cross-MODEL, not necessarily cross-provider**. Two models on one rail is a genuine
independent read of the model and leaves the shared-rail blind spot; say exactly that in the report rather than
claiming cross-provider. If the reader cannot be resolved at all, the work is **unaudited** — a known state, never
a pass.

## Scope the reader's reasoning to the question

Unscoped, a reasoning model spends its budget deciding how to phrase a *better* reply — the writer's job — and
returns style findings instead of truth findings. State it in the system prompt:

> Work only on the question "does this draft accurately represent the situation described in FACTS". Do not
> improve the writing. Do not propose a better reply. Do not invent facts.

## What the fact checker can and cannot see

It sees: `0x` and base58 identifiers that appear in no record we hold, links on our own domain that do not resolve,
claimed counts of services/rails that disagree with the live system, and hedging words.

It cannot see: whether the *argument* is right, whether the offer is worth making, or whether the reader cares. Those
remain the auditor's and the human's calls — which is why the human still presses send.
