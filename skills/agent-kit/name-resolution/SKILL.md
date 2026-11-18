---
name: name-resolution
description: "Use when a name from speech or chat returns zero results. Resolve before searching."
version: 1.0.0
author: gentech-treasury
license: MIT
tags: [stt, transcription, names, search, fleet]
trigger: "When Jordan (or anyone) names a product, person, agent or tier and a brain search returns zero hits, or the name looks like a speech-to-text mangling of one of our own nouns. NOT for genuinely new names — an UNKNOWN result means report it, not invent a variant."
metadata:
  hermes:
    tags: [stt, transcription, names, search, fleet]
    related_skills: [link-research-summary, routing, identity]
---

# Name Resolution — resolve before you search

**A name that returns zero hits is more often misheard than missing.**

This fleet runs on voice. Jordan dictates, speech-to-text renders our own proper nouns as
near-misses, and the agent takes the mangling literally — then searches the brain for a product
that was never called that, finds nothing, and reports a clean "not found." **That is a false
negative dressed as a finding**, and it is worse than an error: it looks like diligence.

**Observed, 2026-10-18:** *"Jintek Mauston"* → **GenTech Milestone.** The agent searched, found
nothing, and nearly recorded a brand name it had misheard.

## The procedure

1. **Before searching for a named thing, resolve the name.**
   ```
   python3 scripts/resolve_name.py "<the name you heard>"
   ```
2. **Exit 0** → search for the **canonical** name, not the variant.
3. **Exit 1 (UNKNOWN)** → **report it as UNKNOWN. Do not guess, do not invent a variant.**
   A genuinely new name is a legitimate answer; a fabricated match is not.
4. **Exit 2** → the map is unreadable. **Fail loud.** A resolver that silently passes everything
   through is the same blindness as a monitor that never fires.

## The map

`variants.json` — one row per **observed** miss. **Add a row only when a real transcript produced
it.** Do not pre-load speculative misspellings: a map full of guesses resolves nothing and buries
the real ones. `link-research-summary` already carries the manual version of this rule (*"try
phonetic variants before giving up"*) — this skill is that rule with a data file behind it, so it
stops depending on an agent remembering.

## Why the canonical must win

A variant that normalises to its own canonical (variant `Arthur`, canonical `arthur`) must not
relabel the canonical match as a mishearing. **The index is built canonical-first and variants use
`setdefault`.** *(This bug shipped and was caught by its own test — worth keeping, because the
label is the part a human reads.)*

## The inverse failure: a name that resolves to the WRONG entity

The procedure above guards against a false negative. **The opposite error is worse, because it produces a confident, sourced, wrong answer.**

**A handle, slug or URL match is NOT an identity match.** A bare name can be owned by an unrelated party, and the platform will happily confirm the exact handle you asked for — because it is that handle.

**Measured:** resolving the AI company *Anthropic* on YouTube returned a **PUBG/speedrun channel** whose handle is genuinely `@Anthropic`, display name *"Matt Gregory"*. `canonicalBaseUrl` and `vanityChannelUrl` both returned `@Anthropic`. Every identity field agreed and it was still the wrong party — one scrape deeper and a gamer's view counts would have been attributed to an AI lab.

**The rule: after resolving a name to an entity, compare the DISPLAY NAME against what you asked for, and refuse on mismatch.** Normalise both (strip case/punctuation) and require correspondence before using the data.

- Handle equality, canonical URL equality, and "the token appears on the page" are all insufficient — a page of *search or related* results contains the token without being the entity.
- **A refusal is a legitimate finding.** Report *name mismatch, refused* and name what it actually resolved to. A confidently attributed wrong entity is a fabrication even when every field looked right.
- This applies beyond speech: any name→resource resolution (handle, slug, repo, ticker, contract). The failure mode is identical and it is silent.

## Garbles of our own VOCABULARY are the dangerous class

**A misheard proper noun sends you to the brain and returns nothing. A misheard COMMON noun reads as
a strange instruction and you act on it.** The second is the one that costs a session.

Observed in ordinary sentences: *cron job* → "crown job" · *Snowtrace* → "NoTrace" ·
*Avalanche / AVAX* → "AVEX".

**The tell: the sentence stops parsing in the domain.** "The crown job is for our backend and our
services" parses as English and as nothing else — a job has no crown. **When a dictated token leaves
the sentence semantically empty, treat it as a transcription error before treating it as a new
concept.**

**The move:** re-read the WHOLE sentence and substitute phonetic neighbours **from our own
vocabulary** — our nouns, our tools, our chains, our job names. If one substitution makes the sentence
parse, that is the reading.

- **Do not stall on the mangled token, and do not ask the user what he meant by it.** A vocabulary
garble resolves in one substitution; asking costs a round trip and reads as not listening.
- **Say the canonical form back** in your reply ("assuming *cron job*") so a wrong guess is one word
to correct.
- **Fall through to UNKNOWN only when no substitution of our own vocabulary parses.** A genuinely new
  term is a legitimate answer — a fabricated match is not.
- The variants map is for proper nouns that must be SEARCHED; a vocabulary garble is resolved by
  reading the sentence, so it needs no row. **Add one only when a garble becomes a recurring word.**

## A capitalised word is not a proper noun — check for PROSE before you check for a product

**The third failure class: the name was never a name.** A word heard in passing gets researched as a vendor,
and because common English words almost always collide with *some* real company, the search returns a
confident, sourced answer about a business the user never mentioned.

**Measured:** *"let's look into Vanilla's API key"* — grepping the vault returned zero product hits and every
occurrence was ordinary prose: *"the **vanilla** `@x402/core` client"*, *"the vanilla x402 client signs with…"*.
The word was an adjective. A web search would still have produced a real vendor with that name — which is how
a sentence becomes a fabricated integration plan.

**The move, before any web search:**

```bash
grep -rin '<token>' "$VAULT" --include='*.md' | grep -v backups | head -8
```

**Read the sentences, not the hit count.** All-lowercase appearances adjacent to a known noun (*vanilla
client* · *vanilla JS* · *vanilla config*) mean the token is an adjective here, and there is nothing to
research.

- **Answer with what you found and one line of the alternative**, not a flat refusal: *"no Vanilla in the
  brain — every hit is 'the vanilla x402 client'. If it's a real service, give me its name and I'll chase it."*
  A fabricated vendor and a dead stop are both worse than that sentence.
- **A common word needs this check BEFORE the web, never after.** Once you have a vendor's homepage in hand, the
  mistake looks like research; the vault grep is the only step that can tell you the name was never a noun.
- **Do not add it to `variants.json`.** That map is for proper nouns that must be SEARCHED; a word that is prose
  needs no row, and a row would teach the resolver to normalise an adjective into a product.
- **Never wire anything from that reading.** No key, no endpoint, no config — the cost of the wrong entity here is
  an integration with a company that has nothing to do with us.

## ⚠️ The privacy rule that sits beside this one

**Voice is a transcript, and a transcript is a log.** Transcription runs off-box
(`stt.provider: nous`). So: **never dictate a secret in any channel.** The means to recover a
key belong in a password manager or on paper — never in a voice message, which becomes text,
which becomes history. This is the same rule as *never paste a secret in chat*, extended to
the microphone.
