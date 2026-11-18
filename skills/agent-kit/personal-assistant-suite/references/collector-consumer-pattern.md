# The collector → consumer wiring

## Why the shape exists
Standalone monitoring jobs each message the human, so N jobs = N pings, and several of them end up
reporting simulated or stale data. The human reads noise and stops reading. The fix is structural: move
the data-gathering off the human's channel entirely and give the human ONE voice.

## Collector rules
- `deliver=local` (or no delivery at all). The output is written for the consumer, not for a human.
- Deterministic output, no timestamps, no random ordering — stable output is what lets a change-detector
  gate skip the expensive reasoning step when nothing moved.
- One data source per collector. A collector that gathers two unrelated things cannot be gated or
  reclassified independently.
- Provenance: a collector that cannot cite where its numbers came from will eventually feed the consumer a
  fabricated success. Read live state (on-chain balance, file mtime, job status), never a cached claim.

## Consumer rules
- Reads every collector's most recent output at fire time — chain with the engine's
  "inject job N's last output as context" field, not by reading a file another job wrote.
- The consumer is the only job with a human-visible delivery target.
- One consumer per channel. Two consumers on one channel re-create the N-pings problem with fewer jobs.

## Scheduled-job conventions the consumer must obey
- **Silent when healthy.** On platforms that deliver a scheduled job's stdout verbatim, empty output sends
  nothing. Build the report so a clean run prints nothing, or exactly the agreed quiet line.
- **Speak only on failure.** The same applies to watchdogs and drift checks: a job that reports "all fine"
  every day trains the reader to ignore it, and then the one real alert is ignored too.
- **Prove the delivery path, don't assume it.** Delivery is proven by the job's target field plus a
  readback — not by the absence of an error. When a job is supposed to wake or message another agent and
  that channel is not configured, the note in the durable lane IS the delivery; say so instead of claiming
  a wake.
- **Rebuild the job, not just the prompt.** A reporting layer is three things: the collectors, the consumer
  job, and the durable rules the consumer reads. Restoring only the cron entry leaves it reading nothing.
- **Measure the job's own cost.** An LLM consumer firing many times a day costs real money per fire; the
  morning brief and the wrap are the slots the human reads. If the schedule grew without a decision, trim
  it — and prefer a deterministic script gate in front of the expensive reasoning step where one fits.
