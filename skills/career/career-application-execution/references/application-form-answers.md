# Long-form application answers — how to answer "most impactful build" and "how did you know it worked"

Application forms ask two questions in sequence and candidates treat both as a chance to sound impressive.
They are not. The first asks **what you did**; the second asks **how you judge your own work**. The second
question is the one that separates a builder from someone who describes building, and it is answered with
checks, not adjectives.

---

## The shape: pick the failure first, then the checks

Before writing anything, name **the one failure the system exists to prevent**. Not "outages" — the specific
failure that would make the system wrong rather than merely down. For a pay-per-call API it is *charging for a
call and then serving it free anyway*; for an ingest pipeline it is *counting one event twice*; for a
permissions layer it is *an action executing without a verdict*. Everything after that is the checks that catch
**that** failure.

Then give three checks, in the order a request meets them, each with what a bad result looks like:

| Check | What it asserts | How it fails |
|---|---|---|
| The contract is well-formed | the first response carries the price/quote/schema the caller can act on | malformed or absent payload |
| Enforcement is server-side | the caller cannot underpay, downgrade or bypass by editing its own request | accepted below the stated bar |
| The thing behind it actually answers | health/status surfaces probe dependencies, not just the front door | "up" while the dependency is dead |

**Three is the right number.** One reads as luck, five reads as a checklist written for the form.

---

## Rules that apply every time

1. **Open the link before writing the claim.** Any sentence of the form "it is live / returns 200 / serves N
   services" has a shelf life and an audience with a browser. Verify in the same session as the draft. If it
   fails today, that failure belongs in the answer, not in a footnote you omitted.
2. **A current outage does not weaken the answer — hiding it does.** "Right now that health endpoint returns
   404, and that is what the discipline looks like: I found it by checking, not by trusting the last report I
   wrote" is stronger than a clean narrative, because it is a demonstrated behaviour rather than a claim.
3. **Never print a metric you cannot reproduce.** Uptime, call counts, revenue, users, latency, "N services".
   An unmeasured number is `UNMEASURED`, not an approximation; a round number in an application is a promise
   the interview will test.
4. **Do not let the impact claim outrun the artifact.** If the work is a demo, say demo. The interviewer's
   first follow-up is always "who used it", and that question is kinder than being caught.
5. **Eligibility and credentials are not yours to assert** — pass results, citizenship, clearance, degree,
   work authorization. Ask, then write.

---

## Worked answer — "how did you know it worked?"

> The gateway's whole job is to say no correctly. A pay-per-call API has one failure that matters more than any
> outage: asking for payment, then serving the response for free anyway. So I defined correctness in those
> terms, and every check I ran was built to catch that specific failure.
>
> Three checks, in order. **The challenge is well-formed:** a request with no payment returns the payment-required
> status carrying a versioned body — price in atomic units, the payee, the network, the scheme. Malformed means
> fail. **The price is enforced server-side:** the proof is verified against the payment verifier and the settled
> amount is compared to the expected price, so an underpaid proof is rejected rather than rounded in the caller's
> favour. **The service is actually answering:** a health endpoint and a status page that probe each backend, so
> "the gateway is up" is never confused with "the thing behind it works".
>
> Then I checked the same way when it broke. Right now that health endpoint returns 404. That is what the
> discipline looks like: I found it by checking the live URL, not by trusting the last report I'd written.

**Why this works:** it answers the literal question, it names a specific failure instead of a generic one, it
makes the checks auditable, and it ends on a behaviour the interviewer can test in their own browser.

---

## The sibling question — "what's the most impactful thing you've built?"

Answer with the system, its one-line purpose, your specific contribution, and **one** proof of life. No
adjectives about scale. If the honest contribution was "I specified it, directed the build and ran the
verification", say that — an orchestration role is a real engineering role and inflating it into "I wrote every
line" collapses under one follow-up.

Order that reads well: *what it is → the failure it prevents → what I specifically did → how I knew it worked*.
That last clause hands the next question over already answered, which is why it is worth writing both answers
in one sitting.

---

## Pre-submit checklist

- [ ] Every link in the answer opened in this session, and the status quoted is what it returned.
- [ ] One named failure, not a list of features.
- [ ] Three checks, each with its failure mode.
- [ ] No metric that cannot be reproduced on request.
- [ ] Contribution stated at its real size.
- [ ] No eligibility fact asserted on the candidate's behalf.
