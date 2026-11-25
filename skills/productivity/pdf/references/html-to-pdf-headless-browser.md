# HTML → PDF with a headless browser, and how to prove it worked

Use when the document has to LOOK like a page — a portfolio, a one-pager, a report with real typography.
`reportlab` composes elements; it does not cascade CSS. For anything designed in HTML, print it with the browser
and skip the re-implementation.

## The command

```bash
CHROME=/path/to/chrome
cd "$(dirname "$HTML")"
timeout 90 "$CHROME" --headless=new --disable-gpu --no-sandbox \
  --no-pdf-header-footer --print-to-pdf=out.pdf --virtual-time-budget=4000 \
  "file://$PWD/in.html"
```

- **Success looks like a line on stderr: `NNNNN bytes written to file out.pdf`** plus exit 0. Treat that line as
  the render receipt, then verify with pypdf (below) — a written file is not yet a correct document.
- **`dbus`/`Failed to connect to the bus` errors are noise** on a headless box and do not affect the output.
  Do not chase them.
- **`--virtual-time-budget`** gives webfonts and layout a moment to settle; raise it for heavy pages.
- **`--no-pdf-header-footer`** removes the URL/date furniture the browser adds by default — the first thing that
  makes a generated PDF look generated.
- **`file://$PWD/...` needs the absolute path.** A relative URL silently yields a blank page.

## Page geometry lives in CSS, not in flags

```css
@page { size: Letter; margin: 16mm 18mm; }
h2 { page-break-after: avoid; }
.avoid { page-break-inside: avoid; }
```

`page-break-after: avoid` on headings and `page-break-inside: avoid` on self-contained blocks are what stop a
section title landing alone at the foot of a page. Body text at ~10.5pt with 1.5 line-height reads as a document;
12pt reads as a web page printed.

## Verify — three checks, all cheap

```python
from pypdf import PdfReader
r = PdfReader("out.pdf")
print("pages:", len(r.pages))
print("page1 chars:", len(r.pages[0].extract_text() or ""))
print((r.pages[0].extract_text() or "")[:200])
```

1. **Page count is plausible** for the word count — a 2,000-word document that comes back as 1 page lost its
   layout; 30 pages means the CSS broke.
2. **Text extracts and reads correctly** from page 1 and the last page. This proves a real text layer (selectable,
   searchable, ATS-readable) rather than an image of text.
3. **The last line is the real last line** — extraction that stops early means the content was clipped, not that
   the document ended.

Also render the HTML in the browser and screenshot it before printing: CSS that looks fine in code can collide,
and the PDF is not the place to discover that.

## Pitfalls

- **Do not hand-roll PDF text extraction with a zip/regex pass.** Decompressing the first stream you find can hit
  a font program and return runs like `fi fi fi ff` — that is your parser reading glyph data, not evidence that the
  PDF is garbled. Use pypdf; it handles the encoding.
- **`/Type /Page` counted by regex is an approximation**, not a page count — a `/Pages` node matches too. pypdf's
  `len(reader.pages)` is the number to report.
- **Printing HTML and printing SVG are different paths.** A browser that prints HTML cleanly can hang
  indefinitely on a `file://…svg` target. That is a property of the SVG path, not of the browser or the build — do
  not conclude "headless PDF is broken" from one hanging SVG. Render the SVG in a page and screenshot it instead.
- **Ship the HTML source beside the PDF.** A PDF is an output; the next edit needs the source or it gets rebuilt
  from scratch.
- **A document that goes to a third party carries its own disclaimers.** If the content is analysis, a sample or
  a small book, say so in the footer of the PDF itself — the reader of the file does not have the chat context.
