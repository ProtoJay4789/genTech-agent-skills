# Plain Language & the Reaction Format

Two things that belong together: how to write so a broad audience understands, and how to build an opinion
on top of somebody else's claim without misrepresenting them.

---

## 1. Swap table

Say the term the first time, then define it in under ten words. Second use onward: plain English only.

| Term | Say this, once |
|---|---|
| TVL | "total value locked — all the money sitting in the pool" |
| APR | "the yearly rate, if it held all year" |
| APY | "same idea, but with compounding baked in" |
| yield | "the money it pays you" |
| LP / liquidity provider | "someone who leaves money in a pool for others to trade against" |
| impermanent loss | "what you give up when the price moves away from what you put in" |
| slippage | "the worse price you get because your own trade moved the market" |
| rebalance | "moving the money back into its range" |
| position | "what we're holding right now" |
| drawdown | "how far we've fallen from the top" |
| liquidation | "the platform sells your money to pay a debt you can't cover" |
| on-chain | "written on the blockchain — anyone can check it" |
| gas | "the fee you pay to make the network do something" |
| notional | "the size of the trade before fees" |
| signal | "a claim somebody made" |
| verdict | "our call on whether they were right" |
| alpha | avoid — say "an edge" or "something most people don't know yet" |

**Never say:** synergize, leverage (as a verb), "position ourselves", "ecosystem play", "narrative arc",
"asymmetric opportunity".

**Sentence shape:** one idea per sentence, 8–14 words, say the thing then the number. "It paid us back" beats
"it generated positive net returns". "We were wrong" beats "that call was directionally disconfirmed".

**Silence is free.** A pause between beats costs nothing; a viewer who got lost costs the whole piece.

---

## 2. The four verdicts — always explained, never bare

| Verdict | Plain meaning to say out loud |
|---|---|
| **Confirmed** | they said it, and it happened — here's the proof |
| **Mixed** | right direction, wrong on the details — say which detail |
| **Missed** | it didn't happen, or it went the other way |
| **Noise** | it was never checkable in the first place — say why it was never a real call |

On screen: label + one plain line + the receipt. A verdict chip with nothing behind it is decoration.

**Consistency note:** keep the four words fixed across every piece. They are the product — the audience learns
them, and the day you rename one you lose the recognition you built.

---

## 3. Reaction / branch format

Somebody else's claim is the spine. Their words, our check. The opinion is ours; the claim is theirs.

```
1. THE CLAIM     Quote it verbatim. Attribute. Link. Screenshot it in-frame if it's short.
2. TRANSLATE     What did they actually mean, in plain words?
3. THE CHECK     What does the data / chain / record say? Number or it didn't happen.
4. VERDICT       Confirmed / Mixed / Missed / Noise.
5. THE BRANCH    Our read, going further than the check. ONE idea. This is where the opinion lives.
```

### Rules that keep it clean

- **Quote, then check. Never editorialise inside the quote.**
- **Never paraphrase someone into a position they didn't take.** That is how reaction content becomes
  defamation. If the claim is ambiguous, say it is ambiguous.
- **Unverifiable = Noise, and say so.** Declining to score something is the most credible move a channel can
  make, and it is still content.
- **Our own misses go in the same piece.** Always.
- **Attribute every time, including when the source is small.** Small accounts notice, and they share.

### Sourcing claims

| Source | Method | Note |
|---|---|---|
| X post | `curl -s "https://api.fxtwitter.com/i/status/<ID>"` | No auth. Returns text, author, timestamp, media, and the quoted post |
| YouTube | transcript API | Needs a key — check it is configured before promising video reactions |
| Article | the URL itself | Quote the line, link the page |

**Pitfall — the quoted post is often the substance.** A short reaction post frequently quotes a longer article.
fxtwitter exposes it under `quote` → `article.title` / `preview_text`. Read the quoted material before scoring
the outer post, or you will verdict the reaction instead of the claim.

**Pitfall — reaction content is not a licence to be first.** Score the claim you can actually check. A verdict
published on a claim you half-read is the one that gets quoted back at you.
