# Outlier analysis — find what beats a channel's own baseline, for free

Sorting posts by view count tells you who is big. It does not tell you what **worked**. A 200k-view video
from a channel that averages 180k is filler; a 40k-view video from a channel that averages 8k is a hit.
**The unit of analysis is lift against that channel's own median, never raw views.**

Use this to answer "what should we make" — hook shapes, topics, formats — without buying a social-data API.

---

## The method

1. **Pull at least 20 recent posts** per channel (more is better for a stable baseline).
2. **Keep raw metrics separately** before combining anything — views, likes, comments, shares. For video-first
   platforms views are the primary metric; for text-first, likes + replies + reposts.
3. **Baseline = MEDIAN, not mean.** One viral post drags a mean far enough to hide the next outlier.
4. **lift = post_metric / median_metric**, computed per channel and per format (short vs long, reel vs
   carousel — mixing formats corrupts the baseline).
5. **Label:** `HUGE` ≥5x · `STRONG` 2–5x · `mild` 1.5–2x · below that is normal noise.
6. **State confidence.** Under ~10 posts, say **LOW** in the output. A median from six posts is an anecdote.
7. **Enrich only the winners** — fetch transcript/caption for the top 2–3, and read the comments if you want
   audience language.

## Free data sources (no key, no paid API)

| Source | Endpoint | Gives |
|---|---|---|
| YouTube uploads | `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` | Latest ~15 uploads with **exact `viewCount`** in `media:community/media:statistics` |
| YouTube resolve | `https://www.youtube.com/@handle` (HTML) | `externalId` / `channelId` → the `UC…` id |
| X posts | `https://api.fxtwitter.com/<handle>` and `/i/status/<id>` | Text, views, likes, timestamp, quoted post |

YouTube RSS is the useful one: it is an Atom feed with real numbers, so an outlier table needs no scraping
framework and no API quota.

**Runnable implementation:** `scripts/` in this skill's tree is the place for a re-runnable version — parse the
RSS, median it, emit the table. Do not hand-compute medians.

## Choosing the baseline channel — the step people skip

**Do not use the biggest or most convenient account in the niche. Use one whose format you would actually adopt.**

A channel whose entire output is the thing you refuse to make teaches you the wrong lesson twice: its outliers
are outliers *for a style you won't use*, and copying its top performers drags you toward that style. Before
adopting a baseline, read its 15 latest titles. If they are all-caps urgency ("EMERGENCY", "BLOODBATH",
"MASSIVE") and its lift spread is flat, it is a hype channel — its ceiling is 1.3x because the hype *is* the
baseline. That is a channel to define yourself against, not a model to copy.

The useful baseline is one with a **wide lift spread** (a 5–7x hit in the recent window) whose top performers
are topically and tonally adjacent to what you intend to make. Wide spread means the format is doing work;
adjacent means the lesson transfers.

## Read the outlier list for the SEAM, not the topic

When several outliers in one window share a subject, that is the demand signal. Often it is not the subject
itself but an intersection — e.g. "a new technology" × "what it does to jobs and money" — that carries the
lift. Name the intersection, then ask what we can say about it **with a receipt** that nobody else can.

## Pitfalls

- **Median, always.** Mean makes every channel look like it has no outliers, or one fake one.
- **Never compare lift across platforms or formats.** A Short baseline and a long-form baseline are two
  different numbers; so are a reel and a carousel.
- **Verify entity identity before analysing.** A handle match is not an identity match: a bare name can belong
  to an unrelated channel, and the platform will confirm the exact handle you asked for because it *is* that
  handle. After resolving, compare the **display name** to what you asked for and refuse on mismatch — an
  analysis of the wrong channel is a confident, sourced, wrong answer. (See `name-resolution` for the rule.)
- **Refuse to publish a baseline from fewer than ~5 usable posts.** Say `INSUFFICIENT DATA` and the count.
  A median of three is not a baseline, and presenting it as one is the same failure as a fabricated metric.
- **Stale windows lie quietly.** A channel that stopped uploading years ago produces a baseline from an era
  that says nothing about now. Check the newest post date before trusting the table.
- **Do not report lift as a forecast.** It describes what already happened on someone else's audience.

## Output shape

```
## YouTube @handle — "Channel Name"
- sample N posts · window YYYY-MM-DD → YYYY-MM-DD
- baseline median views = N · confidence MEDIUM

| rank | post | date | views | lift |
|---:|---|---|---:|---:|
| 1 | [title](url) | date | 205,283 | 7.06x HUGE |

**Outliers (>=2x baseline): 6 of 15.**
```

The count line matters as much as the table: *6 of 15* says the format is repeatable; *1 of 15* says it was a
fluke, and a single fluke is not a strategy.
