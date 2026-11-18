# Retargeting a resume to a specific posting

Produce a version of the resume aimed at ONE posting, without inventing anything and without losing the
numbers that make the original credible.

## 0. Establish the source of truth first

- Check whether the connected document store is actually reachable before promising to read it. A connector
  that is not connected, or a key that is rejected, is a fact to report in the first line of the reply — not
  something to work around silently.
- Fall back to the **newest local master by mtime** (`ls -la` the resumes directory) and ask him to confirm
  which copy is current. Say which file you used.
- Never state or imply that you read a cloud document you could not open.

## 1. Pull the requirements from the ATS payload, verbatim

The rendered posting page is for humans; the payload is for matching.

```
# Greenhouse — full posting including the requirements block
https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}      # -> content (HTML)
# Ashby — the whole board, each job carries a plain-text description
https://api.ashbyhq.com/posting-api/job-board/{token}             # -> jobs[].descriptionPlain
```

Strip tags, then read the requirement list as a numbered set. Those lines — not a summary you wrote — are the
ledger you are matching against. Note the administrative gates explicitly (citizenship, clearance, degree,
student/graduation date) because they decide eligibility before skill is discussed.

## 2. Build a keyword ledger and MEASURE the delta

A table, produced by a script, not by impression:

| term | before | after |
|---|---|---|
| `ci/cd` | no | YES |
| `runbook` | no | YES |
| `kubernetes` | no | no — real gap |

Only move a term to YES when the work behind it is genuinely his. Renaming shipped work in the industry's
vocabulary is the whole win here: the labour already happened, the market just uses a different word for it.

## 3. Retarget the SHAPE, not only the vocabulary

A resume is read as a claim about which job you do. If the posting is a support role, the lede, the first
section and the section order must look like a support engineer's — Linux, case lifecycle, triage,
documentation — even when the underlying evidence is the same evaluation and observability work. Keep the
numbers; change what they are evidence *of*.

Delete duplicate prose while retargeting. A summary paragraph that restates the Experience section is the most
common reason a one-page resume silently becomes two.

## 4. The gaps stay gaps — disclose them in the letter

For each requirement he cannot meet, one line, in the cover letter:

- what he does instead (the adjacent, real capability);
- the honest position on the gap ("I have not shipped Ruby", "I run Docker on bare Linux, not an
  orchestrated cluster");
- why it is not the thing that sinks him (transfer, or learnable in the first month on real cases).

Never add a keyword he cannot defend. The interview is one question deep; a fabricated term costs the whole
application.

## 5. Eligibility facts belong to him

Citizenship, clearance, work authorization, degree completion, certification passes: ask, then write. Resume
honesty for certifications is already strict in the parent skill — the same standard applies to eligibility
lines, which are even less negotiable.

## 6. Render to exactly one page and PROVE it

When no markdown→PDF toolchain is available, render through a real browser.

1. Convert the markdown to minimal HTML. Keep print CSS explicit: `@page` size letter, body ~9.1pt Georgia,
   `line-height` ~1.2, `h2` uppercase with a hairline border, and `text-wrap: pretty` to kill orphan lines.
2. Open it and print with CDP:

```python
cdp('Page.printToPDF', printBackground=True, paperWidth=8.5, paperHeight=11,
    marginTop=0.35, marginBottom=0.35, marginLeft=0.5, marginRight=0.5, scale=0.92)
```

3. Iterate `scale` downward (0.92 → 0.90 → 0.86) and stop at the first value whose PDF is one page.
4. **Verify, do not assume:**

```python
from pypdf import PdfReader
r = PdfReader(path)
assert len(r.pages) == 1
print(r.pages[0].extract_text()[-400:])   # last lines present => nothing clipped at the bottom
```

5. **Cache-bust before re-rendering.** A second print of an unchanged `file://` URL can reuse the cached DOM
   and return a byte-identical PDF even after you edited the HTML — which reads as "my edit did nothing". Load
   with a changing query string (`?v=2`) or re-navigate, then confirm the edit took by reading a computed
   style back out of the DOM.
6. **Measure layout defects; do not judge them from a screenshot.** Wrapped lines aligning to the wrong edge
   is a Range-rect question:

```python
js("(() => {const r=document.createRange(); r.selectNodeContents(document.querySelector('li'));
     return [...r.getClientRects()].map(x=>Math.round(x.left));})()")
```

   All lines should share one left offset. A vision pass over a screenshot will confidently report a hanging
   indent as broken when the measurement says it is correct — the numbers decide.

## 7. Verify the links the resume ADVERTISES, by content-type

Before an application goes out, check that the surfaces printed on the resume actually serve what they claim.

```bash
curl -s -o /dev/null -D - -L <url> | grep -i 'content-type\|^HTTP'
```

**A 200 is not a pass.** A catch-all rule can answer `/resume.pdf` with the site's homepage as `text/html`,
which returns 200, looks fine to a status check, and hands a recruiter a link that downloads nothing. Require
`application/pdf` (or an HTML page that *renders* the resume) — and if it fails, say so: a broken public
resume link silently costs every application that cites it.

**Distinguish "missing file" from "catch-all" with a control path.** Request a deliberately nonexistent asset
(`/nonexistent-abc123.pdf`) and compare status, byte count and hash with the real one. Identical responses mean
no static serving exists at all and *every* path on that domain resolves to one page — a different defect from a
single missing upload, and one no amount of re-uploading fixes.

## 8. Name the deliverable DRAFT until he signs off

`<name>_<date>_<variant>-DRAFT.md/.pdf` beside the master, never over it. Report the file paths and the two
things still needing his word (usually: which copy is current, and any eligibility line).

## 9. The rendered artifact must contain nothing you would not send

A PDF is not a preview of the markdown — it is the document the employer opens. Working notes that sit at the
top of a draft file (a `Status: DRAFT` line, a role URL, a comp band, a "before this is sent" checklist) render
straight into the deliverable unless the HTML is built from a body slice.

- **Convert from the salutation forward:** `body = md[md.index("Dear "):]`, then cut the trailing internal
  section before building HTML. Never convert the whole file and hope the notes are far enough down.
- **Verify with a negative assertion, not a glance.** Text extraction is the only check that reads what a
  reader will read:

```python
from pypdf import PdfReader
t = "".join(p.extract_text() for p in PdfReader(path).pages)
assert "DRAFT" not in t and "Before this is sent" not in t
assert "U.S. citizen" in t          # and assert the content you DID mean to send
```

- **Resume and letter are separate renders with separate CSS.** A letter is set larger and airier than a
  resume, so the scale that fits the resume will not fit the letter. Fit each to its own budget — resume: one
  page; letter: one page when the body is roughly 450 words or fewer, otherwise cut words rather than type size.
- A leaked internal header is the highest-embarrassment failure in this workflow, and it survives every visual
  check because the page still *looks* correct.
