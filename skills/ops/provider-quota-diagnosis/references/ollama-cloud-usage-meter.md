# Ollama Cloud — reading the usage meter honestly

`GET https://ollama.com/api/usage?range=<24h|7d|30d>` with `Authorization: Bearer $OLLAMA_API_KEY`.

`/v1/usage` is **not** a path (`path "/v1/usage" not found`). Only `/api/usage` answers.

---

## There is no quota *endpoint* — but the allowance IS published, in the plan

Probed and **404**: `/api/subscription` · `/api/account` · `/api/plan` · `/api/limits` · `/api/billing` ·
`/api/credits`. `/api/me` returns **405**.

**That absence does not make "how much is left" unanswerable — it makes it a two-source question.** The meter
reports *credits drawn*; the plan page reports *credits included*. Remaining is the difference:

```
ollama.com/pricing   Pro $20/mo  →  includes $60 of usage credits per month
                     (resets monthly on the subscription start day)
/api/usage           totals.usage_usd  →  credits drawn so far

remaining ≈ pool − drawn        …but the period start is invisible to every endpoint
```

**Balance is a two-state answer, and the state is set by whether you know the period start.**

**State 1 — period start unknown.** Print **days-of-pace**, never a balance:

```
credit pool $60/mo · 39.7% of it gone in the last 7d · lasts ~17.7 days at this pace
```

That sentence is honest (it says *at this pace*) and needs no reset date.

**State 2 — period start known** (the account console shows it as *"This month · Since <date>"*). Now the
balance is derivable, so compute it — and **cross-check it against arithmetic anyone can see on the same
screen**:

```
spent + balance = pool        # the test. Measured: $28.02 + $31.98 = $60.00 exactly
```

If that identity does not hold, the period start is wrong and the figure is a guess — say so and fall back to
State 1. **A derived number that reproduces a published one to the cent stops being derived; it becomes a
measurement you can print daily without opening a browser.**

---

## The decision number is the DRY DATE — and who covers the gap

Balance alone does not say whether anything is wrong. Compute the whole curve:

```python
burn      = used_period / days_elapsed        # dollars per day since the period start
days_left = (pool - used_period) / burn
dry_at    = today + days_left
gap_days  = max(0, reset_at - dry_at)         # reset_at = period_start + 30d
```

Measured shape: `$31.98 left, burn $3.11/day → dry ~Dec 2, resets ~Dec 13 → 11-day GAP`. **The gap in days is
the whole decision.** Balance without it invites a shrug; the gap names the problem.

**Then ask who fills it.** A second subscription whose reset lands *inside* that window turns a shortfall into a
**handoff** — measured: a sibling rail's monthly reset fell two days before the primary ran dry, so switching
primary early covered the month at no extra cost. **Check the sibling reset before recommending a top-up**;
"buy credits" is frequently the expensive answer to a scheduling problem.

---

## Price per request is the pricing decision

`usage_usd ÷ request_count` is a real unit cost — measured ~$0.0033 per request. **Compare every product price
against it:** a route priced below that is a loss-leader in the literal sense, and a moat route earning 2–3× has
the only real margin. Quoting a price without this number is guessing.

---

## The meter is not a bill — label it

On a subscription plan, `usage_usd` is **credits being consumed**, not money being charged. The invoice is a flat
monthly fee. Reporting it as *"$101/month of spend"* turns a $20 subscription into a frightening and false
number.

| what you are showing | correct label |
|---|---|
| `totals.usage_usd` on a plan | **credits drawn** |
| the plan's monthly fee | **the bill** |
| `usage_usd` on pay-as-you-go | **spend** (there the two coincide) |

State both when the user is deciding anything: *"$23.81 of a $60 pool drawn this week; the plan itself is $20/mo."*

---

## Peak and off-peak: same tokens, half the price

Per Ollama's pricing footnotes, off-peak pricing applies **outside 12:00 and 18:00 UTC on weekdays, and all day at
weekends**. In US-Eastern terms the expensive window is roughly **07:00–13:00 ET, Monday–Friday**.

Consequences for any cost analysis:

- **A weekend sample is a best case.** Hourly buckets pulled on a Saturday show 100% off-peak and will make any
  weekday projection look pessimistic or absurd. **Check the weekday of every bucket before concluding anything**
  from it, and say when a sample is weekend-only.
- **A per-day average mixes two price tiers.** Weekday and weekend days are not the same unit. If the buckets
  span both, split them before quoting a rate.
- **Timing is a lever, but only on billable work.** Count jobs that actually pay a model before proposing a
  reschedule: in this fleet most are `no_agent` and cost nothing, so the spend is interactive turns — a schedule
  change would have saved zero.

---

## Where the spend actually comes from

Before optimising, attribute. Two different answers, and only one of them is about cron:

1. **Count billable jobs** — `no_agent: true` costs zero tokens. If the fleet is almost entirely `no_agent`, cron
   is not the driver.
2. **The remainder is interactive turns** — and those are timed by the human, not by a schedule. The honest
   report says that, because it relocates the decision to the person who can act on it.

---

## The response shape (meter is in DOLLARS, not percentages)

```json
{
  "range": "7d", "scope": "self", "granularity": "day",
  "from": "...", "until": "...",
  "totals": { "request_count": 0, "usage_usd": 0.0,
              "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0 },
  "buckets": [ { "from": "...", "until": "...", "request_count": 0, "usage_usd": 0.0,
                 "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0,
                 "partial": true } ]
}
```

- `range=24h` → `granularity: hour`; `7d`/`30d` → `day`.
- **There is no `limits` object.** If a response carries one, read the keys and branch on what is present — a
  gate written for the other schema dies on `KeyError`, and the traceback reads like a quota problem when it is a
  schema mismatch.
- **The newest bucket is `partial: true`** while the day is still running.

---

## The computation that makes the number useful

```python
full   = [b for b in buckets if not b.get("partial")]
days   = [b["usage_usd"] for b in full]
avg    = sum(days) / len(days) if days else None
today  = next((b for b in reversed(buckets) if b.get("partial")), None)
cache  = cached_input / input * 100 if input else None
```

**Exclude `partial` from the average.** Including a two-hour bucket as if it were a day drags the average down and
the projection reads optimistically — which is the direction that gets someone caught out.

---

## How to render it

Order matters — a reader scanning a chat message needs the actionable line first:

```
$23.77 over 7d (7023 requests) — CREDITS DRAWN, not a bill
  BALANCE $31.98 of $60 (period from <start>, burn $3.11/day)
  runs dry ~<date> · resets ~<date> · **N-day GAP to cover**   (or: · covered)
  burn ~$3.38/day over 7 full days
  cache hit 95.9% (cheapest lever we control)
  today $0.10 so far (76 req)
```

**Lead with the label, then balance, then the gap** — the label prevents a $60 pool being read as a $101 bill,
and the gap is the only line that prompts a decision.

**Raw `input`/`output` token counts belong last or nowhere.** A billion cached input tokens is true and tells
nobody whether they can keep working. A report is judged on whether the person can act on it without asking a
follow-up question.

---

## Two readings that get misread

**A month-to-date total that looks cheap may be a dark fleet.** Total for 30 days is not the burn rate; five
working days plus four days at $0.0001 reads as thrift and is really a partial sample. Always show the per-day
buckets or the full-day average beside the total.

**A high cache-hit rate is the bill's biggest single lever.** Measured on a healthy rail: 1.86B input tokens,
1.78B of them cached → **95.9%**. A slip to ~90% roughly **doubles** cost with no additional requests. It earns
its own line in the report, and it is the first thing to check when the pace jumps without volume changing.

---

## Scope

The endpoint answers `scope: "self"` — the calling key's usage only. Several seats spending through one key
aggregate here; several keys do not. **Read per key before calling any total "our" spend.**
