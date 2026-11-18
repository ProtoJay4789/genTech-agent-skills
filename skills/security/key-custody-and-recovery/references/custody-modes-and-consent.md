# Custody modes, consent, and the disclosure record

Depth for the *"Custody is a declared MODE"* section of SKILL.md. Load this when choosing or recording a
mode for a book, when a co-holder's key custody is being arranged, or when auditing whether a declared
mode is actually enforced.

---

## The mode table

| mode | who holds | protects against | the risk you must state | right for |
|---|---|---|---|---|
| **SOLO** | one person, one key | device loss (if backed up); host compromise | lose the vault → lose the funds; no accountability trail; one signature looks like every other | **the default**, and a single-person book |
| **DELEGATED** | one member, for the team | a beneficiary losing their own share; coordination overhead | the holder can move any member's funds unilaterally; the holder IS the single point of failure; **any threshold is decorative** | a family/team book with a working operator |
| **THRESHOLD** | n distinct signers; m required (Safe) | any single signer acting alone — including the operator, including the agent | lose more than n−m shares → locked out permanently; higher ops cost; quorum latency | a team book that needs attribution |

**A mode is a choice among these — never a default arrived at by adding a shard to a vault.**

---

## The per-book disclosure record

Every book's own state carries, at minimum:

```
custody_mode        : solo | delegated | threshold
holder(s)           : …
threshold           : M-of-N  (mode 3)  |  "decorative" (mode 2)
risk_accepted       : <the mode's risk line, verbatim — from the table above>
consent             : <signed, dated — mode 2 only>
recovery_path       : <where the break-glass lives>
re_attestation      : <the date the consent is next re-asked>
host_holds          : none
```

**`host_holds: none` is not a field to fill in — it is an invariant to enforce.** If it is not true, the
mode is fiction no matter what the other lines say.

---

## Recording a consent faithfully

When a co-holder agrees to delegated custody, the record must be readable by a stranger — and must not
claim more than was actually given.

1. **Quote the agreement verbatim**, in the holder's own words.
2. **Name the source**: channel, date, and the form (*a message replying to a voice note*, *in person*).
3. **State the scope as it was described, and mark what you did NOT verify.** If the risk list was
delivered in a voice note you cannot hear, the record attests to **the fact of consent and the scope as
reported** — **not** to a line-by-line written acknowledgement of the risks. Say that explicitly.
   A consent record that silently upgrades "he said he understands" into "he acknowledged these four
   specific risks" is a fabricated claim wearing a signature.
4. **Record the pending half beside the done half.** *"Consent ✅ / break-glass ⏳"* — the reader must not
   have to infer which is missing.

**Why delegation is nonetheless legitimate:** the operator really is the operator, and the realistic
alternative — nobody holds a usable key — is strictly worse. Consent plus a recovery right are what
convert *"one person has your keys"* from a risk into a decision. Say it that way rather than arguing the
risk away.

---

## The break-glass — and why it is not optional

A bank box, a third family member, a sealed envelope. **Its function: a beneficiary who cannot reach the
holder must not be locked out of their own money.**

**Until it is named, the mode is DECLARED BUT NOT COMPLETE** — and that is how it should be reported.
Sole control and a beneficiary's recovery right are not in conflict; the second one just has to be built
deliberately, because it never appears on its own.

**The duty is two-directional.** Accepting holdership is accepting a duty, not a privilege. If only the
beneficiary gets a milestone, the record binds the weaker party and calls it accountability.

---

## Where the agent sits in this

- **The agent records and scores; it does not endorse and does not dispute.** A custody promise and a
  market call are both claims — the job is to make them falsifiable, not to agree with them.
- **Values stay out of chat, always.** The mode, the consent text and the risk line may be written down;
  the holder's shards and passphrase may not. Hand them over as a **path plus a physical destination**.
- **A deleted message is not a remediation** — see the paste section of SKILL.md.

---

## Optional: an on-chain attestation of the record

Where the fleet holds an identity on a public registry, publishing the **hash** of the disclosure record
with a timestamp makes the commitment **verifiable while the content stays private** — anyone can check
that a commitment exists, only the parties can read it. This is worth doing only when it costs nothing
operationally; it is an upgrade to the record's credibility, not a substitute for the break-glass.
