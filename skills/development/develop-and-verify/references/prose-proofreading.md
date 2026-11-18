# Proofreading prose — the Jr/Sr pair applied to a MESSAGE

Code gets an audit. So does anything we publish: a GitHub issue reply, a README line, a pitch, a handoff that a
partner reads. The failure mode is different — a sentence can be perfectly spelled and still be a lie about our
own system — so the checks are different too.

## Why two models, and why the second one is not optional

The author is the worst proofreader of their own text: they check it against what they **meant**, not what they
**wrote**. So: cheap model drafts, a different model reads cold with the single intent *"find a claim about our
system that the text cannot support."*

Model names are resolved at call time, never hardcoded (`audit-model-resolve.py`). When the reader lands on the
same rail as the writer, that is **cross-model on one rail** and must be declared in those words — calling it
cross-provider is the false green this whole pipeline exists to prevent.

## Order of checks — deterministic first, model second

A model's opinion is expensive and flattering. Run the facts first; they can stop a draft before a model is paid
to read it.

| check | what it catches | why it is not a model's job |
|---|---|---|
| **unverified address** | any `0x…`/base58 in the draft that appears in none of our records | a hallucinated payTo is a money-routing bug in prose |
| **dead link** | a URL on our own domain that answers 000/404/410 | a dead link in a message is a lost reader |
| **claimed count vs the LIVE source** | "9 services", "6 rails" — compared against the manifest / a real 402 body, not against memory | a count in prose drifts the moment the surface changes |
| **hedge words** | probably · should be · might be · we believe · hopefully · presumably | each one hides an unmeasured claim |
| **model reader** | claims the facts block cannot support; a sentence that does not answer the question the message exists to answer | judgement, which is what a model is for |

**A failing deterministic check does not need a second opinion — it is a fact.** Report it as `FAIL`, not as a
suggestion.

## The FACT BLOCK is the whole discipline

Give the writer a block of facts and tell it: **you may claim nothing outside this block.** That single
constraint converts "model writes plausible marketing" into "model arranges what we measured". Include an
explicit `DO NOT CLAIM:` line — solving their specific bug, that our approach is correct for them, any number
not listed, a fix we have not written.

Without a fact block the writer will invent a number that sounds like ours. With one, the worst it can do is
word our own measurements badly.

## The non-reply trap — the failure that passes every naive check

Faced with facts that do not support a reply, a writer produces something **true, on-topic, and useless**:
*"We have not encountered that problem. That is all I can report from our side."*

Both a spellchecker and a "are the claims supported" reader pass it. **It is still a non-reply**, and posting it
under our name costs credibility for nothing. Two rules close it:

- **Writer:** if the only true thing you can say is that we have no relevant experience, that is the same as
  `NO REPLY` — say that.
- **Reader:** a message whose substance is *"we have not seen this"* is a **FAIL**, not a pass.

A non-reply is worse than silence because it consumes the reader's attention and returns nothing.

## Drafts must not share a template remedy

If every draft is assembled from one boilerplate remedy sentence, the reply to a schema question will carry the
remedy for a recorder question — **which is exactly the generic text maintainers already filter out.**

Key the remedy to the specific claim: a table of `claim → what we changed`. When no remedy exists for the
matched claim, print *"no written remedy for this one yet — say only what you can prove"* rather than borrowing
one. The absence is information.

## Scope the reader's reasoning to ONE question

A reasoning-capable proofreader, given no scope, spends its budget on the writer's job: how the reply could be
**phrased better**. It then reports style findings, which is not the check. So state the scope in the reader's
system prompt, in these terms:

> *Work only on the question "does this draft accurately represent the situation described in FACTS". Do not
> improve the writing. Do not propose a better reply. Do not invent facts.*

And send the effort level **explicitly** (`reasoning_effort`) rather than inheriting the seat's own setting — that
setting is tuned for different work, and a proofreader's budget should be its own. The reader's reasoning is a
verification aid; the moment it starts composing, it is a second writer with no fact block.

## Display bugs that make a correct verdict useless

- **A reasoning model returns its thinking in `reasoning_content` and a clean answer in `content`.** Reading
  them in the wrong order prints a wall of deliberation where a verdict belongs. Prefer `content`; fall back to
  `reasoning_content` only when content is empty — and **label the fallback as a deliberation transcript**.
- **A 0-char response is not a pass.** It is `UNRESOLVED`, and the draft stays uncleared.
- **Silence about a draft reads as "a reply was impossible".** Print `NO EVIDENCE — do not reply` explicitly, so
  a skipped draft is a decision rather than an omission.

## Verdicts and what they mean

| verdict | meaning | exit |
|---|---|---|
| `PASS` | facts clean, reader found nothing | 0 |
| `REVISE` | findings listed with the offending words | 1 |
| `FAIL` | a false claim about our own system, or a non-reply — do not send | 3 |
| `UNRESOLVED` | a model could not be reached or returned nothing — the draft is **not** cleared | 2 |

Exit non-zero is not "the job failed"; it is the instrument saying what it found. Route on the code, and never
map `UNRESOLVED` onto `PASS` to keep a cron quiet.

## Wiring it without blocking

A cron must not wait on an LLM. Run the **deterministic half inline** (addresses, links, counts, hedges) and
stamp each draft `CLEARED` or `DO NOT SEND`; run the model half as a separate command a human or a follow-up job
invokes. That way every draft that reaches a person has been fact-checked, and the expensive opinion stays
on-demand.

## The selftest every prose checker needs

Both directions, on fixtures, before you trust it:

```
clean draft                       → PASS
wrong service count               → FAIL
hedged claim                      → REVISE
dead link on our own domain       → FAIL
address that exists nowhere       → FAIL
facts that do not support a reply → NO-REPLY
```

A checker never tested in its refusing direction is decoration — and the non-reply case is the one a naive
checker always passes.
