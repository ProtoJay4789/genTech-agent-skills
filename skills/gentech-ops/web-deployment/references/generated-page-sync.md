# Keeping a generated page in step with the machine, and shipping it without wrecking the site

Two problems, one file: how to make a page that *cannot* go stale, and how to deploy it onto a Pages
project you do not have the source of.

## 1 · Determinism is the precondition for drift detection

A sync check compares the freshly generated page with what the edge is serving. That only works if the
generator is a pure function of its inputs.

- **Never stamp a build time into the page.** A `Generated at <timestamp>` line makes the output differ
  from live on *every* run, so the drift detector reports drift forever. A detector that cries wolf daily
  is ignored within a week — which is the same failure as having no detector.
- **Put the volatile information in the data, not the template.** If the page must show freshness, render
  the *source's* own `updated` field, which only changes when the data changed.
- **Prove determinism once:** run the generator twice and diff. Identical output is the test; a silent
  second run from the sync script is the same evidence in production form.

## 2 · Normalise CDN-injected bytes before comparing hashes

Cloudflare (and most edges) rewrite HTML on the way out. Raw byte comparison therefore reports permanent
drift on any page carrying a contact address:

| injection | what it looks like |
|---|---|
| email obfuscation | `mailto:person@example.com` → `/cdn-cgi/l/email-protection`, plus an `email-decode` script and `data-cfemail` attributes |
| whitespace | an extra newline inserted before `</body>` |
| analytics | a `cloudflareinsights` beacon script appended |

Strip those three patterns from **both** sides before hashing, and keep the normaliser in one place so the
build and the verify step cannot disagree about what "equal" means.

**A hash mismatch is not automatically a failed deploy.** Normalise first, diff second, and only then
conclude. Report which artefact accounted for the difference.

## 3 · Verify with a retry, because propagation is seconds not instant

A verify that fires immediately after `wrangler pages deploy` can read the previous deployment and look
exactly like a failure. Retry three or four times with a few seconds between attempts before calling it.

## 4 · Deploying onto a project whose source you do not hold

`wrangler pages deploy <dir>` **replaces the whole deployment.** If the project has no git source, the
live edge is the only copy of every file the crawler did not find.

- **Crawl first, hash per file.** Walk the origin following same-origin `href`/`src`/css `url()`/JS string
  paths, save each body with its sha256, and treat any fetch failure as fatal — a partial snapshot is not a
  snapshot.
- **A one-file site makes the redeploy safe.** Measured: a crawl of a marketing apex returned exactly one
  file because every path served the same `index.html`. That single fact turned a risky full redeploy into
  a one-file swap. **Establish how many files exist before deciding whether a replace is acceptable.**
- **Prefer a new project over a replace.** Adding a page to a no-source project can instead ship as a
  *separate* Pages project on its own subdomain — zero blast radius, and it can be linked from the apex
  once verified. Reserve the full replace for a site you have completely snapshotted.

## 5 · Pages behaviours that read as failures and are not

- **Custom domain `pending` → HTTP 522.** The binding has to initialise; 522s during that window mean
  "not routed yet". Poll the domain status and the content together, and only call it broken once the
  status reaches `active` and the bytes still disagree.
- **`/page.html` returns 308.** Pages redirects to the clean URL (`/page`). Verify the clean URL, and link
  the clean URL — a link to the `.html` form works but takes an extra hop.
- **A catch-all serves `index.html` for every path**, so *status codes and body hashes are both useless*
  as existence tests on the same project. Verify the **title or a known marker** for the page you meant,
  and remember a path that cannot exist returning 200 is the expected behaviour, not a fault.

## 6 · A nav bar is a claim: probe every destination before linking it

When wiring subdomains into a suite nav, **probe each host first** and link only the ones that answer with
real content. Measured: of 30 subdomain records, **6 answered**; the rest returned 404 from an origin that
had not served them for months. Pointing a front door at a 404 reproduces exactly the defect the page was
being fixed for.

- Group the failures by **reason** — dead origin (`A` record to a host that 404s), never-deployed project,
  pending binding — because the fix differs per group.
- A stale `A` record can beat a correct binding: **delete the wrong-type record** and create the proxied
  `CNAME` to `<project>.pages.dev`, then read the record back.
- Keep the personal/internal surfaces out when the user says so, even when they are live. Being reachable
  is not the same as belonging in the public suite nav.
