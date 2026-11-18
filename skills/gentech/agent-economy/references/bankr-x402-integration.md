# Bankr x402 Cloud Integration

## Overview

Bankr's x402 Cloud lets you deploy paid API endpoints with x402 payments built in. Zero x402 knowledge required — write a simple handler function, set your price, deploy with one command.

**Website:** https://bankr.bot
**Docs:** https://docs.bankr.bot
**SDK:** `@bankr/sdk` v0.1.0-alpha.8 (npm, MIT, 49.8KB)
**CLI:** `@bankr/cli`

## What Bankr Offers

| Feature | Benefit |
|---------|---------|
| Zero x402 knowledge required | Write plain Request → Response handlers. They wrap the payment layer. |
| Deploy in seconds | `bankr x402 deploy` bundles and ships your code instantly |
| Any token on Base | Accept USDC by default, or price in any ERC-20 |
| Real-time logs | See every request, payment, and console output in the dashboard |
| Agent discovery | Your endpoints are automatically discoverable by AI agents |
| Secure secrets | Environment variables are encrypted at rest and isolated per-service |
| Usage-based pricing | Set a max price, settle only the actual cost with the upto scheme |

## Supported Chains

Base, ETH, Polygon, Unichain, World Chain, Arbitrum, BNB Chain, Solana, Hyperliquid

## Integration Path for GenTech

1. Install SDK: `npm i -g @bankr/sdk`
2. Login: `bankr login`
3. Deploy APIs: `bankr x402 deploy`
4. List in agent discovery
5. Apply for $100K Inference Program (forms.gle/Pb7bWZGfynbHMw)

## Revenue Model

- Bankr agents call our APIs → x402 micropayments → recurring revenue
- 57% trading fees from token launches → additional revenue
- $100K inference credits → fund compute costs

## $100K Inference Program

**Announced:** June 8, 2026
**What:** Free inference credits for AI agent builders
**Application:** Google Form (forms.gle/Pb7bWZGfynbHMw)
**Status:** Credits being sent out as of June 14, 2026
**Eligibility:** Teams building on Bankr

## Competitive Positioning

Bankr = payment rails + token launchpad
GenTech = data layer + risk scoring + DeFi intelligence

**Don't compete on payments. Compete on intelligence.**

Bankr agents need data before they trade. We provide:
- Rugcheck v2 (token risk scoring)
- DeFi Intelligence (protocol data)
- Token Security (11-factor scoring)
- Crypto Price, Gas Price, Deal Tracker

---

## Papertrade (observed 2026-10-12) — the mechanic, and the opening

**Source tweet:** `@bankrbot`, Oct 12 2026 16:21 UTC, 5,757 views / 32 likes / 27 replies.
> Papertrade on Bankr, from a real trade last night:
> `> 100x ETH long, TP + SL armed` · `> stop-loss hit, the loss minted 1,590 PAPER` ·
> `> Bankr staked it automatically to earn USDC`
> try now from the console, or directly on X. — learn more: bankr.bot/papertrade

**First finding: it is not in their documentation.** Grepped their own `docs.bankr.bot/llms-full.txt`
(**809,026 bytes**): **`paper` = 0 occurrences.** Control greps in the same file prove the search works —
`x402` = 305, `mint` = 25, `stake` = 78, `perpetual` = 13. **The product shipped on X and is undocumented**,
so **the source of the USDC yield is not verifiable from their own material.** That is the question to ask
them, and it is unanswered here on purpose.

**Mechanic:** `PAPER` is minted by *trading activity* — demonstrated, notably, by a **loss** — and
auto-staked to earn USDC.

**Doctrine test — `fees are durable, emissions are fragile`:** a reward token minted by activity is an
**emissions structure by construction**. Supply grows with engagement; the claim on USDC grows with supply;
the fee pool it draws on does not grow with either. Any structure where the reward is minted by *doing the
thing* has a supply schedule that outruns the revenue backing it. **This is the shape our LP thesis is
built against** — we want to hold the pool that *collects* the fee, not the token that *pays* one.

**Second-order concern:** "100x long, stop hit, and you were rewarded" pays for **churn**, not for skill. A
metric that pays for the wrong behaviour is a familiar bug class in this estate. It is fine as a growth
mechanic and worthless as a signal about trading ability — do not read their user numbers as edge.

**THE OPENING — this is a distribution event, not a competitor.** Their own docs advertise the demand:
`bankr agent -m claude-sonnet-5.5 "what are my best yield options?"` — an agent that trades perps, launches
tokens and asks for yield. Papertrade increases the volume of **new, low-quality tokens and leveraged
positions** flowing into their stack, which is precisely the demand side for **Rugcheck v2 / token risk
scoring / 11-factor Token Security**. Our standing position is unchanged and now has a delivery vehicle:
**don't compete on payments — compete on intelligence.** Ship the risk layer into the flow Papertrade
manufactures.

**What their docs DO confirm — the stack is real, not just a launchpad:**
- Agent wallet, **gas covered**, cross-chain
- Token launchpad: **57% of trading fees flow back to fund compute** ("self-sustaining from day one")
- **Trading via Hyperliquid (primary) and Avantis on Base** — perps in crypto, **stocks, commodities, forex**,
  plus **Polymarket**; limit / stop / **DCA / TWAP** orders
- **BNKR staking on Base** — stake, unstake cooldown, claim/restake, legacy vault
- x402 Cloud (305 doc mentions), skills system

**Note the Avantis line against our tokenization thread:** they already list **tokenized equities and
commodities** as tradable underlyings. That is Morgan Stanley's $3–10T market showing up inside a Base
launchpad, one product release at a time.
