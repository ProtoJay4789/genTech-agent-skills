# Builder grants — the lane that pays for a SHIPPED DEMO

Federal RFPs and builder grants are different universes and must never share a filter. A federal program wants
an institution with a grants office, a 30-page narrative and a DUNS number. A builder program wants a public
repo, a live demo link and a changelog. **Scoring one with the other's rules produces a list that is either
unawardable or unsubmittable** — and the failure looks like "no good opportunities" rather than "wrong lane".

## The standing rule: our own history is the best source

**Check who we have already submitted to, or signed up for, before searching for strangers.** Those platforms
have already accepted an application from us, which means the account, the profile and the fit are proven —
the only unknown is whether a round is open. A new round on a platform we are already on is the highest
probability opportunity available, and a keyword search across the internet will never surface it.

Sources for "who we already signed up with": the marketplace/listings registry, completion registry, any
`submitted`/`applied` note in HQ, and the platform list on the public site. Sweep those first, every time.

## What the lane looks like

- **Programs run in WAVES with countdowns, not annual windows.** The listing carries `Building` / `Judging` /
  `Pending` plus a live `Nd Nh left`. Read the listing, not a blog post — aggregators lag by weeks and invent
  deadlines.
- **Judging is weighted toward the artefact.** Typical split: user value ~30%, working demo ~25%, product logic
  ~20%, **their API integration ~15%**. That last number is the real work: the demo usually already exists, and
  the integration is the only new thing.
- **Submission needs:** public repo with README, public live demo URL, short video (optional but scored),
  team info, and a **per-wave changelog** — a resubmission that repeats wave 1's text scores as no progress.
- **A demo that is already live is worth more than a promise.** If a public dashboard with real data exists,
  the honest build plan is "their data feeding the surface we already have", which is days not weeks.

### Akindo (`app.akindo.io`) — "Buildathons"

Long-running programme host with dozens of concurrent buildathons, each sponsored by a protocol, each with its
own waves and prize pool. Page: `https://app.akindo.io/wave-hacks`. Cards expose sponsor, tags, wave number,
pool size, status and time left — enough to rank without opening a detail page. Detail pages add the eligibility
and judging weights.

**A detail page may render empty** if the card list is where the metadata lives; read the listing, then open only
the two or three you will actually consider.

## Before you scope a submission: three gates that decide whether the window is usable

**1 · The API key may not be self-serve — and an application form is the critical path, not the code.** Read the
vendor's setup page before estimating the build. A key that requires an account plus an approval form can sit in
review for days, and **no amount of engineering compresses an approval.** If the key is the gate, the honest plan
names it as the gate and gives the fallback — submit the concept plus the live artefact you already have and take
the integration-weight hit — rather than implying the build starts tomorrow.

**2 · Confirm the submission artefacts exist and are PUBLIC before committing.** A buildathon asks for a public
repo with a README and a public demo URL. Measured on this fleet: every repo on our own account was **private**,
so "we'll just submit the existing project" was false and publishing a clean public repo became its own task.
Check the account's visibility, not the project's quality.

**3 · Distinguish the SUBMISSION deadline from the JUDGING deadline.** Listings carry both and the later one is
often the more visible. Measured: a wave believed to close "tomorrow" had stopped accepting submissions weeks
earlier — the tracked date was when judging ended, and the wave was lost while several notes in the fleet
repeated the wrong date. **Read the field name (`submitDeadline` vs `judgementDeadline`), not the countdown**, and
record which WAVE is open rather than that the programme exists.

**A programme you signed up for and never submitted to is the highest-risk repeat** — the account exists, the fit
is proven, and the failure mode is the same timestamp trap as last time. Re-read that programme's fields before
assuming this round behaves like the last one.

## Design of the watcher: a registry, not a discovery engine

A scanner that claims to "find grants" will return whatever its search terms match, which is how a medical
research RFP ends up in an AI company's list. **The page that cannot be stale is the programme's own page.** So:

1. Keep a **curated registry** (JSON) of programmes worth applying to: id, name, URL, one line of fit, status.
2. **Hash the normalised visible text** of each page and report a change.
3. **Strip the noise before hashing** — long hex/build ids, nonces, ISO timestamps, epoch numbers, scripts and
   styles. A modern JS page changes hash every hour for reasons that are not news; a job that reports "changed"
   hourly is switched off within a week and then protects nothing.
4. **A change is a signal to read the page, never a claim that a round opened.** Say so in the output, or the
   reader treats "changed" as "apply now".
5. **Report upcoming deadlines** parsed out of the pages you already watch (window ~30 days).
6. **Exit 2 when every page fails.** An unreachable programme is *unread*, not *closed* — print it as such and
   keep it in the registry.
7. **Silence on a no-change day.** One log line, no message.

## Filters that decide whether a grant is real

- **Discipline is judged on the TITLE, not the body.** A medical grant's description mentions AI in passing; a
  title in another field disqualifies the row no matter what the text says.
- **Eligibility is contract data — read it from the API/page, never from memory.** Applicant-type codes are
  opaque integers whose meaning is not guessable; a wrong assumption silently marks a programme open that is
  restricted to a different class of applicant. Enumerate the codes the endpoint actually returns and match on
  those.
- **A close date in the past is not an opportunity**, and a forecasted programme with no date is a pipeline
  signal rather than a deadline.
