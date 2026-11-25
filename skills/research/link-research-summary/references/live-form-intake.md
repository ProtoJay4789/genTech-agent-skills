# Reading a live application form without applying

The goal is the **requirement list an outsider cannot see**: the exact questions, their order, and what the form
presupposes. Reached by walking the form in a browser; never by submitting it, never by paraphrasing it.

## When to use

- A fellowship, accelerator, cohort, partner programme or job posting whose real screen sits behind a form.
- Any page whose HTML is a shell — `curl` returns `Loading your application…` and nothing else.
- Deciding WATCH vs APPLY for someone, where the decision turns on what the form asks.

## Procedure

**1. Static fetch first — it still tells you whether the shell is worth driving.**

```bash
curl -sL "<url>/apply" -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36" \
  -o /tmp/form.html -w "HTTP %{http_code} size %{size_download}\n"
```

Strip tags and print the text, then harvest the outbound links (`/apply`, an announcement post, LinkedIn profiles in
a fellows list) — those are free and often richer than the form. A page returning only `Loading your application…`
confirms the form is client-rendered and a browser is required.

**2. Drive the browser, paginate, read the questions.**

```python
new_tab("<url>/apply"); wait_for_load()
print(js("document.body.innerText.substring(0,4000)"))
```

Page 1 is identity. To reach page 2, fill every visible input with obviously-fake preview values and advance.
Nothing is submitted until the final button on the final page, and these forms are typically stateless before that
— but say so explicitly in the report: **"walked both pages, nothing submitted."**

**3. Diagnose a stuck form from the DOM, not from the wording.**

```javascript
// is it actually blocked?
[...document.querySelectorAll('button')].map(b => `${b.innerText.trim()} disabled=${b.disabled}`)
// which controls carry real state?
[...document.querySelectorAll('button')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.innerText)
// is there an unselected option list?
[...document.querySelectorAll('[role=option], li, [class*=option]')].map(e => e.innerText.trim()).filter(Boolean)
```

- **`disabled=true` with all fields filled = an autocomplete that was typed into but never selected.** Click the
  option node; the button enables immediately. This is the most common block, and the failure mode is wasting turns
  re-typing an answer that was never the problem.
- **`aria-pressed` false after a coordinate click = the control needs a real element `.click()`.** Use
  `document.querySelectorAll('button')[…].click()`; React listens for the element event, not the hit test.
- Read labels/placeholders through the DOM when precision matters; screenshot when the *layout* is the question.

**4. Read page 2 out loud, verbatim.** Screening questions are short prose. Quote them exactly; a paraphrase
destroys the only thing that made them useful — the presupposition each one carries.

**5. Report shape.**

- The identity fields, and which only the human can supply (phone, legal name, personal email).
- **The screening questions quoted verbatim**, plus what they presuppose.
- The deadline in days from today, computed — not the raw date.
- Costs and commitments stated on the page, and explicitly *not stated* where absent.
- The verdict: WATCH / APPLY / structurally ineligible, with the gate named.
- One line confirming nothing was submitted.

## Pitfalls

- **Reading a presupposition as a question.** "How does that compare with what they own in *your organisation*" is
  not asking whether you understand the role — it is stating that applicants already hold it. The presupposition is
  usually the most valuable finding on the page; lead the analysis with it.
- **Describing the form from its marketing page.** A landing page lists benefits and a register link; it never lists
  the questions. "The application asks for your background" is a claim about a page you did not open.
- **A partial form that "saves on this device" is not a submission** — but it is not nothing: note the state in the
  report so a later session does not mistake a half-filled draft for an application actually sent.
- **The deadline is a fact, the review cadence is a claim.** "Rolling review, limited spots" means the real cut-off
  is earlier than the stated date; say both and recommend against relying on the last week.
- **A cohort/fellow list is a hiring-manager list.** The people who hold the title are the ones who hire for it —
  harvest the names and employers as a target list, and check the form for unadvertised channels (an "open to
  introductions" checkbox is a job-market function the landing page hides).
- **Never submit to learn something.** If the only way to see the last page were to send it, the answer is to
  describe what is verifiable and say the rest is unread — an application is a one-shot first impression.
