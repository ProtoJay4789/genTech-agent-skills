# Verifying a Cloudflare Pages deploy — the artifacts that make a good deploy look broken

The pages.dev custom-domain flow is covered in `cloudflare-pages-deployment.md`. This file is only about
**verification**: how to tell a real deploy from a fake one, and how to stop the instrument from lying in
either direction.

## Pages rewrites your bytes on the way out

**Cloudflare mutates HTML in flight, so `served_sha != local_sha` is usually an artifact, not a failed
deploy.** Three transformations, all measured on real deploys:

- **A newline is injected before `</body>`** on some paths — one byte, every page, every time.
- **`mailto:` links are rewritten** into `/cdn-cgi/l/email-protection`, with an `email-decode` script injected.
  Any page carrying a contact address therefore has a permanently different hash.
- **`/page.html` 308s to `/page`.** Link the clean URL. A checker that fetches the `.html` form gets an empty
  redirect body and concludes the page is missing.

Normalise before comparing: strip the `email-decode` script, blank `data-cfemail`, collapse `/cdn-cgi/…`,
and squeeze whitespace immediately before `</body>`. Then a hash difference means a real difference.

**Why it matters:** a verification step that reports drift on every run teaches the operator to ignore it —
the same failure as a check that can never go red.

## A fresh custom domain answers 522 while it is pending

422/522 on a just-bound subdomain is the binding initialising, not a broken deploy. Poll the domain object
until `status: active`, then verify by content.

Measured shape: 522, 522, then 200 with a hash matching the local file on the third poll. **Do not report a
failure inside the propagation window** — and do not extend the window silently either; say which poll
succeeded.

## One project per page

A Pages deploy REPLACES the project's entire deployment. On a project with **no git source**, the live URL is
the only copy, so adding a page to an existing multi-file site is a restore drill, not an edit.

- **New page → new project** (`<name>-services`, `<name>-demo`, …) with its own proxied CNAME. Zero blast
  radius, independent deploys, and a bad build cannot take the front door down.
- **Single-file site → safe to redeploy.** Crawl it first and confirm it really is one file (`index.html`): a
  full crawl that returns exactly one path is proof, not an assumption.

## Generated pages must be byte-deterministic

**Never stamp a build timestamp (or any clock) into a page a drift checker compares.** A page that changes
every run can never be in sync, so the checker redeploys nightly and reports a change that is not a change.

Print the source of truth instead — a manifest path, a count, a service list — and prove determinism by
running the generator twice and expecting **no output at all** on the second pass.

## The four-line verification set

```bash
sha256sum page.html                                            # local
curl -s "https://<host>/?v=$(date +%s)" | sha256sum            # served (cache-busted)
curl -s "https://<host>/<cannot-exist>" | sha256sum            # control: must DIFFER on a real origin
curl -s -o /dev/null -w "%{http_code}\n" "https://<host>/<cannot-exist>"
```

On a catch-all host every path returns 200 with real content, so **the hash mismatch against the control is
the only proof the host is serving files rather than one fallback**. Pair it with a marker grep (a string
that exists only in the new build) so a normalised-equal result cannot hide a wrong page.
