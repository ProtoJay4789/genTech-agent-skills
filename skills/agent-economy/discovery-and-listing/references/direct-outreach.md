# Direct outreach — asking a named counterparty to carry you

Catalogue work (see the parent SKILL.md) is passive: fix the artifact, settle once, wait to be indexed. **Outreach is the
other half — asking a specific company, client or tool maintainer to point their users at you.** It fails differently,
and mostly it fails silently.

## Choose the channel by whether it leaves a RECORD

| channel | keeps a record | when to use |
|---|---|---|
| **Issue on their own public repo** | ✅ permanent, authored, replyable | first choice whenever it exists — it is a public commitment to answer |
| A vendor's published support portal / form | ✅ usually returns a case id | second choice; note the case id or it never happened |
| Email to a published address | ✅ Sent folder | fine, **only if the address is published by them** |
| X / social DM | ❌ | last resort. An unknown small seller gets left on read, and there is no follow-up artefact |

**Do not send a DM and call it an ask.** "We reached out" with no record is indistinguishable from never having tried, and
it cannot be escalated on day three because there is nothing to escalate.

## Find the channel from THEIR own surfaces, in this order

1. **The site's own links.** A product page frequently links the exact repo that accepts issues even when it publishes no
   contact address at all. Follow the links before concluding "no channel exists".
2. **The repo's `has_issues` flag.** A repo can exist and have issues **disabled** — a one-way mirror, and a dead end for
   an ask. Check the flag, do not assume.
3. **Sibling repos in the same org.** When the flagship repo has issues off, a supporting repo (SDK, toolkit, examples)
   often has them on — and it is read by the same people.
4. **Their support portal** for anything that is a customer-relationship question rather than a product one.

**Never invent an address.** A guessed `support@<vendor>.com` that bounces is worse than using their portal: it costs the
send, teaches nothing, and gives a false sense of having reached them. **"They publish no email; here is their portal" is
the correct finding, not a failure.**

**A JS-only contact page usually names the real channel in its own copy.** If `contact-us` renders a form that points at a
help-desk host, **that portal is the channel** — an HTML scrape of the page returns no address because none is published,
and treating the empty scrape as "no channel" is wrong in the same direction as inventing one.

### Read what a published contact page REFUSES, not just what it offers

**A published address is not an invitation to every class of ask.** Vendors increasingly spell out the boundary on the
contact page itself — one facilitator's reads: *"Please do not email us with promotional engagements… unsolicited sales
pitches… We do not accept these requests through this email channel,"* while naming **that same address** as the place for
*"technical support, integration and API questions, bug reports"*.

⇒ **Sort your ask before choosing the door.** A distribution/commercial ask to a vendor who refuses promotional email is a
misdelivery that gets correctly ignored — and it costs the one channel you had. The same page usually names the right one:
**a community chat for integration problems, a support portal for cases, the repo for reproducible defects.**

- **Re-frame only if it is genuinely the other class.** "Do settlements through your facilitator propagate to
  <catalogue>?" IS an integration question and belongs in the channel they published for exactly that. "Please list us"
  is a commercial ask and does not.
- **Quote the refusal when reporting the channel choice** — the next session re-derives "email them" otherwise, and the
  refusal is what stops it.

### Read the THREAD'S own close guidance before adding to it

**A maintainer who closed a thread leaves an instruction, and it governs the venue — it is not a suggestion.** Measured: a
long thread on a catalogue indexing bug was closed with a note preferring **resource-specific new tickets over
corroboration on the old thread**. Posting "we see this too" under the closed thread is therefore a misdelivery even
though the bug matches exactly.

- **Search the repo for the failure first, then read how that thread ENDED** — the close note, the bot's redirect, the
  "please use the template" reply. That sentence is the contract for your submission.
- **A cross-posted issue names where the owner wants it.** When one says *"maintainer there confirmed this belongs in
  <other repo>"*, the destination is settled — do not re-litigate it in the original.
- **A reproducible, ours-is-different ticket beats agreement**, because a corroborating comment gives the maintainer no
  new information and no work to accept.

### Classify the ASK before you pick the repo

**A sibling repo with issues enabled is a valid channel for a PRODUCT or SUPPORT ask and the wrong queue for a
COMMERCIAL one.** Measured: a flagship protocol repo had issues **disabled**, its adjacent toolkit repo was open — but a
listing/discovery ask posted there would land in a maintainer's product backlog, where nobody owns distribution.

| the ask | right door |
|---|---|
| "your client doesn't handle our endpoint shape" | sibling SDK/toolkit repo — read by the same engineers |
| "list us in your catalogue / let your users pay us" | the **commercial / merchant / catalogue** route, or the support portal |
| "your validator rejects our manifest" | the repo that ships the validator, with the verbatim error |

**Check whether one channel closes several items.** Where a vendor's catalogue and their outreach door are the same team,
**one conversation can fix both your listing and your catalogue refresh** — say so when you report, so nobody opens the
same conversation twice from two different lists.

## Duplicate-check before you post

**Search their repo for your own author handle before writing.** `search/issues?q=repo:<org>/<repo>+author:<you>` returning
zero is the proof that this is a first ask, not a second one. A repeat ask on a public tracker reads as spam and burns the
channel you only get once.

## Write the ask this way

- **Lead with what they can verify in one call** — the endpoints, the price range, the manifest/OpenAPI URLs, the rails you
  actually settle on.
- **State your weaknesses before they find them.** Traffic that is mostly catalogue robots, a small number of unique
  payers, anything a reviewer would discover and distrust. **A stated limitation is credibility; a discovered one is a
  lie.**
- **Make the ask one of two concrete things:** *add us*, or *tell us the shape you expect and we will match it.* The second
  is often the better one — it converts a submission into a conversation.
- **Offer something you can actually keep** — a signed test call with an on-chain receipt is worth more than a promise of
  support, because it is checkable.
- **One ask per channel.** Do not stack product, partnership, pricing and feedback into one thread.

## Account for it honestly

**An open issue is not a conversation.** Track the asks as: *sent* (verified by re-reading the thread, not by trusting the
create response) → *replied* → *integrated*. Report the count as "N of M sent, 0 replied" for as long as that is true —
**a deposit with a URL is exactly what the measurement says everyone else ignores.**

- **Verify a post by reading it back**, including the author handle and `state`. A 201 from the API is a claim.
- **Write the channel map down** (who, which channel, what state) in one note, so the next session does not re-derive it
  or double-send.
- **A channel you cannot operate is the honest blocker.** When only a human can open a form or a DM, say that in one line
  and hand over the exact URL — do not convert it into "sent" by hopeful phrasing.
