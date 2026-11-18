# Hiring-challenge submissions (public-repo challenges)

**When:** a company hires through a public challenge repo instead of a résumé — a brief, a fixture, a
baseline answer, and a linter. Treat it as an application, but **submit an artifact, not prose.**

## Procedure

1. **Pull the whole kit before writing anything:** `brief.md`, the published baseline answer, the scoring
   rubric, the challenge README, and — most valuable — **their own pre-screen validator script**. Fetch raw:
   `raw.githubusercontent.com/<owner>/<repo>/main/<path>`.
2. **Read the validator's SOURCE, not just its output.** It names the required sections, the label tokens it
   expects, and what it treats as an integrity violation. **The required-sections list IS the submission's
   table of contents.**
3. **Build the artifact and actually run it.** A described architecture that was never executed scores as
   if it does not exist. Fetch the fixture, checksum it (`shasum -a 256`), run the code, keep the outputs.
4. **State the brief/fixture version** the submission answers. These rotate, so an answer written against a
   stale version is graded against traps it never saw.
5. **Run their validator — then fix what is real and STOP at what is not.** Advisory heuristics fire on
   false positives: a version stamp, a checksum, an identifier like `L-006` all read as "unlabeled number".
   **Do not reword honest prose to silence a regex** — the rubrics explicitly name "playing it safe" and
   rubric-gaming as failure modes. Fix the substantive warnings, then state in the submission which
   warnings remain and why.
6. **Quote adversarial content inside a fenced code block or blockquote.** Injection linters flag
   instruction-override phrasing in prose, but the READMEs exempt quoted material — and you need the quote
   in the write-up to show you caught it.
7. **Keep the naive version runnable** (below).

## The reproducible-bad-output rule

Almost every brief asks for "at least one bad output your agent produced." **Do not narrate a bad output —
keep the naive version in the same file behind a flag (`--naive`) so the reviewer can reproduce it.**

- The bad output becomes a **measurement rather than a claim**, and it costs the reviewer one command.
- It makes the improvement legible: run both modes and diff them.
- **A submission claiming zero bad outputs reads as untested** — the briefs say this outright.

## Evidence tiers and source labels ARE our doctrine

These briefs ask for exactly what our own record-keeping already requires: an operating artifact, an
evidence log with a tier per claim, and every number labelled observed / estimated / benchmarked / assumed.
**Their rule that an unsupported high-tier claim "is scored as Tier 0: claims only" is "never fake a
receipt" written by someone else.**

- **Self-rate honestly.** A claim the reviewer cannot open is not a top-tier claim; rate it where it
  actually sits and say why. Disclosing a weakness costs less than over-claiming and being checked.
- **A live FAILING endpoint belongs in the submission.** Showing only green checkmarks is the fastest way
  to lose trust the first time something breaks in production.
- **Verify every link before publishing the packet** — open it. A dead artifact link scores as Tier 0.
- **Name every assumption** the brief left open (a threshold you chose, a floor you invented) and put it in
  a single constant so a human can change it.

## Screening a challenge before committing time

- **Check the location gate FIRST.** A culture-perfect challenge is worthless if the role is not remote — and
  challenge pages often omit location entirely. Verify before building.
- **Read whether the tracks are internships or senior roles.** "Anyone can enter" is a different offer from
  "internship, rolling" or "Senior Engineer" — and a senior-titled track is out of lane.
- **A challenge format is reusable beyond the challenge.** A packet shaped as artifact + evidence log +
  sourced numbers + failure handling is a better application format than a résumé, and the structure can be
  lifted for ordinary applications.
