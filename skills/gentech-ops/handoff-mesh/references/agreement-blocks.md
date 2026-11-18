# Agreement blocks — proving a note LANDED and each seat AGREES

Extends the ACK + START rule from *"did you read my note"* to *"does your copy of the brain agree with
mine."* Use when a fleet needs cross-seat verification of what is in the shared vault, not merely
delivery confirmation.

**Do not build a second ACK system.** Check the existing handoff ACK checker first — it usually works,
and the gap is almost always SCOPE (it covers handoffs and nothing else), not mechanism. Extending one
checker keeps one vocabulary; a parallel system guarantees two definitions of "acknowledged."

## The block a note carries

```markdown
## Agreement

| seat | state | at | evidence |
|---|---|---|---|
| gentech | acknowledged | 2026-11-01T18:00Z | queue pruned 4544 -> 298 lines, verified |
| gentech-treasury | pending | — | — |
| arthur | not-applicable | 2026-11-01T18:10Z | curriculum lane; no queue of its own |
```

## Four states, and what each is allowed to be silent about

| state | meaning | reported? |
|---|---|---|
| `pending` | not yet read — the default | **yes, by AGE** |
| `acknowledged` | read, and the seat states what it did | no, **if** evidence is present |
| `not-applicable` | read and genuinely irrelevant | no, **with a reason** |
| `blocked` | read, cannot comply | yes, **with the blocker** |

## The three rules that make it more than a read receipt

1. **`acknowledged` with no evidence is `unproven`.** A bare "ACK" is the silent pickup the handoff
   rule already forbids. Require a minimum evidence length, and report short ones as unproven rather
   than passing them.
2. **`pending` is reported by age, never as silence.** A seat that never signs is *the finding*. Silence
   is not consent, and a checker that treats absence of a row as agreement has certified everyone.
3. **A note with no block is `uncovered`, not clean.** You cannot agree with something nobody asked you
   to agree to. Report uncovered separately from unproven — they have different remedies (add the block
   vs. do the work).

## The block is authored by the SENDER, at post time

**A note with no block cannot be signed, so coverage stays at zero no matter how diligently the fleet
acks.** Measured: 0 of 557 dated handoff notes carried a block, and `pending` was 0 too — not because
everyone agreed, but because **nobody had been asked**. The reader is not the defect; the artifact is.

**So the fix belongs in the note TEMPLATE, not in the auditor and not in a reminder.** Put `## Agreement`
with one `pending` row per required seat into the canonical handoff format that the writer copies. Until
that ships, every audit reports the same number forever — and a number that cannot move is one the
reader learns to skip, which costs the whole mechanism.

**Diagnostic:** if `uncovered` is 100% and `pending` is 0, the block was never in the template. If
`uncovered` is low and `pending` is high, the template is fine and the seats are ignoring it — two
completely different repairs that a single "ack coverage" number cannot distinguish.

**A retroactive fill is impossible.** Nothing can be signed for an event nobody witnessed, so the
historical pile is context, never a target. Judge the mechanism by whether **new** notes arrive covered.

## Verify the checker in BOTH directions before trusting it

A checker with only a silent path is a script that does nothing, passing. Three backdated fixtures are
enough:

```
acked WITH evidence      -> must NOT be flagged   (proves it can pass)
"acknowledged: ACK"      -> must be flagged       (proves the evidence rule bites)
pending, 4 days old      -> must be flagged by age (proves the age path bites)
```

Backdate by mtime, not by editing a date field, so the age logic is exercised rather than mocked.

## Reporting contract

**Exceptions only.** A nightly "all 47 notes acknowledged" is a report nobody reads, and it trains the
reader to skip the one that matters. Speak on: pending seats by age, acked-without-proof, recent
substantive uncovered notes, and disagreements. Stay empty when every covering note is fully signed.

Report the **delta** against a stored baseline, not the absolute backlog — a first run over an existing
vault finds a large uncovered count simply because no one was ever asked, and that number cannot fall on
its own. Coverage of *new* notes is the signal; the historical pile is context.

## The boundary to state out loud

This layer verifies **arrival and agreement**. It does not verify the note is *correct*, and until the
evidence itself is checked against the artifact it names, it does not verify the *claim* either — a seat
writing "acknowledged — queue pruned" without pruning will pass. Say which of those three the layer
covers, because "the agents verify each other" is heard as the strongest one.

**Next step when asked to harden it:** make the evidence checkable — parse the artifact named in the
evidence line and confirm the stated change is present. That is the difference between a receipt and
agreement.

## Three ways a sign-off count lies — check all three before believing it

**1 · The checker reads ONE closing heading and the rule defines two.** A note carrying `## Supersede` is
closed by the same rule that closes one carrying `## Agreement`, and the SLA instrument honours both —
so a sign-off checker matching only `## Agreement` re-reports every superseded note as *"nobody was asked
to agree"*, forever. **The set of closing headings is ONE list, shared by every instrument.** When the
rule gains a closing form, grep every checker for its marker regex in the same change: three instruments
disagreeing about "closed" is three different truths about the same file, and the noisiest one wins the
reader's attention.

**2 · Suppression makes the count FALL without anything being fixed.** A note listed unchanged on N
consecutive runs drops to a count — but the header must still total it (`12 (no change) + 9
already-reported`) and the delta must compare like with like, or the report reads as progress that did
not happen. The full rule set (including the silent-exit trap) lives in `silence-gated-monitors` under
*"SUPPRESSION CHANGES THE HEADLINE, NEVER THE COUNT"*.

**3 · The lane you filed in is not the lane the checker reads.** A checker enumerating `INBOX/<target>/`
cannot see a broadcast lane like `<sender>-to-fleet/`, so agreements appended there are never chased and
the note ages as silent while every seat has in fact replied. **A broadcast lane is still a lane:** either
enumerate it, or never use one for anything requiring an ACK.

## A seat with no channel cannot be late

SLA and sign-off both measure *reply latency*. A seat whose lane has no transport — no registered peer, no
DM path, a note it can only read by chance — produces **silence that is structural, not behavioural**.
Counting it as a missed deadline reports a colleague as negligent for a doorbell that was never installed.

- **Exclude it from the nudge path by name**, in the same list as the reporting seat itself (a seat does
  not chase itself either).
- **Annotate its outstanding notes once**, with the reason and the release condition ("SLA suspended until
  a channel exists"), so the next reader inherits the fact instead of the alarm.
- **Say the exclusion out loud in the report.** An unexplained absence from a list is indistinguishable
  from an oversight, and the next reader will assume the seat is clean rather than unreachable.
- When the channel lands, drop the exclusion and let the notes age normally — never retroactively score
  the suspended days.
