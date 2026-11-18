# Auditing a public surface — publishing path, source provenance, canonical counts

How to audit a live hostname's *content* without re-doing work that was already done, and without mistaking
a delivery failure for a copy failure.

## 1. Establish the publishing PATH before reading the copy

Three independent paths can serve content on the same hostname, and they fail differently. Determine which
one is answering **before** you audit or edit anything.

| Path | Publishes by | Characteristic failure |
|---|---|---|
| **VPS static files** (nginx `root`) | files on disk, served directly | editing the app's embedded copy does nothing — the static file wins regardless |
| **Cloudflare Worker route** | a route bound to a worker script | the worker intercepts and shadows the origin; a stale deployed version keeps serving even while its build is failing |
| **Cloudflare Pages project** | a git branch + output dir, deployed on push | **ages silently** — a deployment from months ago serves indefinitely, with nothing errored |

**`curl` cannot tell these apart.** A `200` looks identical from all three. Read the headers, then confirm by
API or by on-disk inspection.

## 2. Check the DEPLOYMENT DATE first — it is the fastest finding available

For a Pages project:

```bash
# newest deployments for the project
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT/pages/projects/$PROJECT/deployments?per_page=5" \
| python3 -c "import json,sys; [print(d.get('created_on'), d.get('environment')) for d in json.load(sys.stdin)['result']]"
# the project record also names its bound domains + the source branch/output dir
curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT/pages/projects" \
| python3 -c "import json,sys; [print(p['name'], p.get('domains'), p.get('source')) for p in json.load(sys.stdin)['result']]"
```

**If the newest deployment predates your last copy correction, the correction never shipped.** That is a
complete finding on its own, and it changes the work: the task is a **redeploy**, not a rewrite.

- **A corrected file sitting on disk that never reached the apex is a DELIVERY failure, not a copy failure.**
  Say which one it is, or you will re-audit — and re-fix — work that was already done and documented.
- Differential tell: the live page still carries the *old* wording while an archived copy of the same
  document already carries the corrected wording.

## 3. Search the vault for a PRIOR audit of this exact surface

The fleet keeps its own audits, truth-passes and sync reports. **A fresh audit assembled from the live page
will contradict a document that already recorded the correction and the reasoning behind it.** Search the
surface's name (hostname, product, doc filename) across the vault's audit and content trees before writing
anything new. If a prior pass exists, your job becomes *"did its corrections ship?"* — a far smaller and more
honest question than *"what is wrong with this page?"*

## 4. `Deployed != source` — locate the source, or say you cannot

Before promising a fix, confirm a **source of record** exists and name where it is. Check, in order:

1. The vault's content / archive trees.
2. The org's repos — **fetch the tree.** A repo that exists is not the repo that holds the page; a
   front-door repo may contain only a `templates/` directory.
3. An archived copy of the corrected public files.

If no source exists anywhere on the host, **every "fix" is a hand-patch of live HTML**, and the real task is
recovering or re-creating the source. State that plainly instead of proposing a copy edit.

> **Corollary:** a page with no source and no repo behind it is also a *provenance* gap — publishing the
> artifact into a repo fixes the copy and the missing source in the same move.

## 5. One canonical COUNT, derived from one file

A public surface usually states a count — *"N APIs"*, *"N services"*, *"N chains"*. Those numbers rot
independently on every surface that hardcodes them, and they are simultaneously the most-quoted and
least-verified claim a stranger reads.

- **Before editing any copy, check whether a single file defines the count.** Four of our own surfaces
  carrying four different figures is the disease; picking a new number for one of them is not the cure.
- **Pick the UNIT and say it.** "Services", "endpoints" and "APIs" are different denominators; a page that
  mixes them cannot be corrected, only rewritten.
- **Derive every surface from that one file** — the same discipline as version numbers: one manifest, every
  surface reads it, and a bump cannot skew a surface you forgot.
- **Verify the count by probing, not by reading the copy.** The measured number is the one a hostile reader
  will reproduce.
- **Never lead with the count of your WEAKEST surface.** Advertising the figure belonging to a host that
  returns `500` while a larger healthy surface goes unmentioned is the honesty rule inverted.

## Audit checklist

- [ ] Which publishing path answers this hostname? (static / Worker / Pages)
- [ ] Pages: newest deployment date — does it postdate the last copy correction?
- [ ] Does a prior audit of this surface already exist in the vault?
- [ ] Does a source of record exist, and where? In a repo, or only on the live page?
- [ ] Is there one canonical count, in one file, in one unit?
- [ ] Are the discovery / manifest surfaces derived from that same file?
- [ ] After any fix: re-read the LIVE page, not the file you just wrote.
