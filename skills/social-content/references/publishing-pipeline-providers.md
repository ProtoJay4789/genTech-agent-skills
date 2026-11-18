# Publishing Pipeline Providers — choosing where posts actually go out

The content rail has two ends. Creation is cheap and usually already solved. **Publishing is the end that
silently does not exist** — a finished MP4 with no upload path is not a pipeline.

This file is for the question "what do we publish *through*?" — not what to post.

---

## Rule 1 — price the $0 path before quoting any subscription

A recommendation of "$29/mo" without a measured free alternative is an incomplete recommendation, and the
user will (rightly) push back. Hosted schedulers commonly include **API + MCP on their free tier** — that is
table stakes in this category now, not a premium feature.

**Verify free-tier agent access on the vendor's OWN page, not a comparison blog.** Three checks that settle it:

1. Pricing/help page sentence stating the API or MCP is included on the free plan.
2. The MCP endpoint answering when probed (`curl -sI https://mcp.<vendor>.com/mcp` → **405 on GET is a live
   MCP endpoint**; 404 means the path is wrong, not that the feature is absent).
3. The plan feature table listing the *specific* capability you need (video uploads, the platform you care
   about) as available on free.

Vendor claims and aggregator tables disagree constantly and both go stale. Quote the vendor page, and say
which one you read.

## Rule 2 — check the container runtime before recommending self-host

"Self-hosting is free" is only true if you can run the thing. Before proposing a self-host route, confirm the
runtime is reachable from the seat that would do it:

```bash
docker ps        # exit 0 = usable; "cannot connect to the daemon" = not available to this seat
command -v docker-compose podman
id -u            # non-root with no sudo cannot manage a system service
```

If the runtime isn't reachable, self-host is a **host-access task for the user**, not a seat task — say so and
price the hosted plan instead. Some projects also ship a **single static binary + systemd** path that needs no
container runtime at all; check for one before writing a project off as self-host-only.

## Rule 3 — the free tier is usually limited by (channels x queue depth), not by posts

Typical free-tier shape: **3 channels, ~10 queued posts per channel, 1 API key, a monthly request budget**
(thousands of requests for a few posts a week is plenty of headroom). Read the limits as a *cadence* budget
rather than as a wall.

## Rule 4 — check what "YouTube support" means before promising it

Schedulers vary enormously here, and the difference decides whether the tool fits:

| Support level | What it can do |
|---|---|
| **Shorts only** | Vertical clips up to ~3 min, 9:16 or 1:1. **No long-form.** |
| **Long-form video** | Full uploads, multi-GB, many hours, arbitrary duration. |

A vertical short-form operation is *not* blocked by Shorts-only support — a 9:16 clip under three minutes is
already a Short, so nothing about the format changes. Long-form episodes are the only thing that forces the
more expensive tier. Confirm which one the vendor actually offers on their own help page; do not infer it
from a platform logo in the integration list.

## Rule 5 — some destinations require a public HTTPS media URL

Several platforms (Facebook, Instagram, TikTok, Threads, Pinterest) fetch the asset themselves and will
reject a local file. YouTube and X accept a direct upload. If the seat has no writable public web root, those
destinations are blocked **independently of which scheduler you pick** — check for a public file host before
promising them.

---

## Why DIY is usually the *expensive* option

The tempting reasoning is "we have ffmpeg and an API key, skip the middleman." Two gates make that wrong:

- **YouTube's unverified-project lock.** `videos.insert` from an API project that has not passed Google's
  compliance **audit** uploads as **private only**. The audit takes weeks. Quota is no longer the constraint —
  a default project gets its own dedicated upload bucket (order of ~100 uploads/day after the dedicated-bucket
  change); the audit is.
- **Metered social APIs.** Posting through a platform's own API can be billed per call, and a post containing
  a link is often priced far above a plain post. At a few posts a day that is a real monthly line item, and
  it can exceed a scheduler's whole free tier.

**The subscription is not buying software — it buys somebody else's approved provider apps**, i.e. the audit
work and the app-review queue. That is the honest framing to give the user when they ask why a scheduler
costs money, and the reason a free tier on a hosted scheduler can beat DIY.

---

## Provider shape, not provider ranking

Specific prices and free-tier limits change often; treat any number here as something to re-verify. What stays
stable is the *shape* of the options:

| Shape | Characteristics | Watch for |
|---|---|---|
| **Hosted scheduler, free tier** | Own approved apps, no dev-app registration, MCP included | Channel cap, queue depth, Shorts-only YouTube |
| **Hosted scheduler, paid** | Same, more channels / long-form | Cheapest tier is often still per-channel |
| **Self-hosted, container** | Free licence, unlimited channels | You register every dev app; needs a container runtime |
| **Self-hosted, single binary** | Free licence, no runtime needed | Still needs a public HTTPS reverse proxy + dev apps |
| **Direct platform APIs** | Full control, no middleman | Audit gates and per-call billing |
| **AI-actor / UGC generators** | Produce the video too | May structurally conflict with a real-face/real-voice rule |

AGPL is common in the self-hosted column: fine for internal use, but a *modified* version run as a network
service for others obliges source disclosure. Note it before building a product on top.

## Rule 6 — approval queues are a feature

Hosted schedulers typically land agent-created posts in a **queue for human approval** rather than publishing
immediately. When the brand rule is "a person signs off on anything that carries an opinion," this is not a
limitation to work around — it is the control mechanism, enforced by the tool instead of by discipline. Prefer
it over an auto-publish path for opinion-bearing content.

---

## Verification that a publish actually happened

An API returning `ok` is not a post. After the first real publish, read the platform back (or the scheduler's
post record) and capture the **identifier + URL**. Log every publish — platform, account, asset, id, status —
before the second one. The post log is the one artefact here that cannot be reconstructed if it is lost.
