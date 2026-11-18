---
name: career-application-execution
description: Use when drafting, tracking, or submitting job applications
trigger: After opportunity evaluation is complete, when ready to draft/submit applications; user says "let's apply", "submit applications", or "prepare application packets"
input: Evaluated opportunities with role details, resume variant mapping, user personal details (name, LinkedIn, portfolio)
output: Ready-to-submit application packets (cover letters + tracking) and submission checklist
---

# Career Application Execution — Drafting to Submission

## Overview
This skill governs the **execution phase** after opportunity research and evaluation. It covers turning evaluated opportunities into actual submissions: drafting tailored cover letters, consolidating multi-application packets, tracking, and final submission. It emphasizes **vault-based coordination** and **batch processing** to minimize context-switch.

## When to Use
- `career-platform-research` has produced go/no-go recommendations
- Multiple opportunities need to be applied to in a single batch
- User has confirmed which roles to pursue and is ready to draft/submit
- Need to maintain version control across cover letters and track submission dates

## Pre-Flight: Intent Clarification

**CRITICAL CHECK BEFORE PROCEEDING:** When a user shares a link to a company's careers page, product page, or announcement, you MUST clarify their intent before diving into analysis. Common intents:

| User Says / Links | Likely Intent | Your Response |
|---|---|---|
| "Check these guys out" / company careers URL | 🔍 **Job-fit evaluation** — they want to know if they qualify | Lead with role fit assessment, not partnership or competitive analysis |
| "Saw this, interesting project" / product or doc link | 🤝 **Partnership or integration** — they want tech fit analysis | Lead with technical overlap, integration possibilities |
| "What do you think of X?" / product launch or blog | 📊 **Competitive or market intelligence** | Lead with positioning, threat/opportunity assessment |

**Pitfall:** Defaulting to partnership/competitive analysis when the user wanted job-fit evaluation wastes time and requires a correction. When in doubt about intent, ask a short clarifying question before producing a full analysis.

**If intent is job evaluation:** Skip directly to Role Fit Assessment (below) — do not write partnership recommendations, competitive positioning, or market analysis. The user needs ONE thing: "Do I fit this role?"

## METHODOLOGY — Five-Phase Workflow

### Link Format Rule (User Preference)
When sharing job application links on Telegram, send bare URLs on their own line — NOT wrapped in markdown tables or [text](url) format. Telegram makes bare URLs tappable. Example:

```
Binance Pioneer Talent — AI Agent Developer

https://himalayas.app/companies/binance/jobs/pioneer-talent-program-ai-agent-developer

Deadline: June 22, 2026
```

This applies to ALL job/apply links shared in conversation.

### Phase 1: Inventory & Gap Analysis
1. **Check existing application drafts** in vault (`04-Entertainment/Applications/` or similar)
   - Look for: `{Company}-{Role}-CoverLetter.md` standalone files
   - Look for: consolidated docs like `College.xyz-{Name}-{Roles}.md`
2. **Identify gaps** — which roles lack cover letters?
3. **Catalog resume variants** available (`02-Labs/Resumes/`):
   - Growth-focused resume
   - Analyst-focused resume
   - Master/General resume
   - Verify file existence and PDF generation

### Phase 2a: Standalone Draft Creation (for missing roles)
For each missing role, create a standalone cover letter file following `career-platform-research` template structure:
- Use company/role-specific emphasis from the evaluation doc
- Include: subject line, why-I'm-interested, why-I-fit, contributions, links, sign-off
- Keep length: 200–300 words (concise but substantive)
- Save as: `{Company}-{Role}-CoverLetter.md`

**Do not** edit consolidated master yet — keep versioned.

### Phase 2b: Single-Role Direct Email Application (Crypto/AI Startup Pattern)

For crypto-native startups that accept applications via email (no portal), use this alternate flow:

1. **Extract resume content** — The resume is only available as PDF. Use `pdftotext` to extract content for reference:
   ```
   pdftotext "/path/to/Resume.pdf" -
   ```

2. **Draft cover letter** with these specific structural choices that match this user's style:
   - **Subject line**: `{Role} — {Name} — {Hook Phrase}` (e.g., "Research Engineer Intern — Jordan Jones — Agentic Systems + DeFi Infrastructure Builder")
   - **Opening**: Direct, warm, no "I am writing to express my interest" boilerplate
   - **Body structure**:
     - 3-4 shipped artifacts as bullets (never just "I worked on X" — always "I shipped X, it does Y, Z people use it")
     - Reference the company's specific research focus, product, or recent announcement (proves you read their stuff)
     - Frame the intern angle positively: "I can prove shipping velocity without a credential"
   - **Honest constraints section**: If the user has a day job or time-bound commitment (Amazon Thu-Fri), disclose it directly. Crypto-native startups value honesty over resume-gloss. Better to say "I work Thu-Fri, the rest is full-time on this" than to imply unlimited availability.
   - **Closing**: Offer to hop on a call, reference something specific about their work (their Chief Scientist's constrained autonomy research, their D0 product, etc.)

3. **Save cover letter** to `10-Labs/Resumes/{Company}-{Role}-CoverLetter.md`

4. **Application tracking entry** — Add to build queue as a new item with:
   - Status: "Draft ready — Forge to send"
   - Steps checklist: Read cover letter → Attach resume PDF → Send to {email} → Optional: DM founder on X
   - Founder X handle and company handle for optional DM outreach
   - Track reply: [ ]

5. **Optional X DM** — After sending, DM the founder/CTO with a 1-2 sentence intro:
   - Mention you just applied
   - One-sentence hook on what you build that's relevant to them
   - Ask for a conversation

### Phase 3: Consolidation
Patch the master application document (e.g., `College.xyz-Jordan-Hibachi-Injective.md`) to integrate new role:
1. Add role to **Target Roles** header
2. Insert **Role Overview** section (mission, needs, requirements, comp)
3. Add to **Distinguishing Factors** under Application Strategy
4. Insert **Cover Letter Template** section with full letter
5. Update **Tracking** checklist with new role entry
6. Update **Social Media Templates** to include new company/handle
7. Expand **Decision Framework** table if multi-offer scenario possible
8. Update **Notes / Customization** with role-specific tips

**Commit message style:** "Add {Role} to college.xyz application batch — cover letter, strategy, tracking."

### Phase 4: Cross-Check & Delegation
- **Resume mapping:** Confirm each role gets correct resume variant (Growth→Growth_Resume, Analyst→Analyst_Resume, Product→Master or tailored)
- **DMOB handoff:** Send message to GenTech HQ or DMOB group:
  - "Verify resume PDFs exist for [list roles]"
  - "Prepare simple tracking sheet (date, resume used, status)"
- **Personal details fill-in:** Create checklist of brackets to replace: [Name], [Email], [LinkedIn], [Portfolio], [Quantifiable achievements]

### Phase 5: Submission Execution
- User submits all applications in **single batch** (same sitting)
- Use direct links or college.xyz portal
- Screenshot confirmations or log submission URLs for tracking
- Optional: post social media templates (Twitter/LinkedIn) to signal interest
- Mark tracking checklist as submitted with dates

## OUTPUT TEMPLATE

```markdown
# Application Packet — [Date] — [User]

## Applications Submitted
| Company | Role | Resume Used | Date | Portal Link |
|---------|------|-------------|------|-------------|
| Hibachi | Growth Intern | Jordan_Growth_Resume.pdf | 2026-05-05 | [link] |
| Injective | PM Intern | Jordan_Master_Resume.pdf | 2026-05-05 | [link] |
| No Limit Holdings | Investment Analyst Intern | Jordan_Analyst_Resume.pdf | 2026-05-05 | [link] |

## Follow-Up Schedule
- [ ] Day 3–5: DM hiring managers (handles listed)
- [ ] Week 2: Follow-up email if no response
- [ ] Update tracking sheet with status changes

## Social Posts
- [ ] Twitter posted (URL)
- [ ] LinkedIn posted (URL)

## Next Steps
- [ ] Prepare for potential interviews (see `interview-and-offer-prep` skill)
- [ ] Update portfolio with recent projects if needed
```

## AI-Native & Web3 Roles

When applying to AI-native or Web3 companies for "Demo Engineer", "Builder", "Developer Advocate", or "Ecosystem" roles, the application strategy shifts significantly. These companies value **shipping speed over production quality** and **AI tool fluency over years of experience**. See `references/ai-native-web3-roles.md` for detailed patterns, signals to look for in job descriptions, and application strategy adjustments.

**Key adjustment:** Lead with your hackathon repos, live demos, and agent projects as your primary credentials. Frame AI orchestration (multi-agent fleets, autonomous workflows) as your differentiator. **Be honest on wins vs. submissions — Jordan has hackathon experience and shipped builds, but NO wins yet.** Present velocity through completed builds, working code, and live deployments, not claimed victories. Don't over-index on Solidity depth — demo roles care about showing what's possible.

### AI Job Search Framework (28.1K ⭐)

The [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) repo (28.1K ⭐, MIT) is an AI-powered job application framework built on Claude Code. The creator used it to land an AI engineer role after 69 applications, 20 interviews, 1 signed contract. It automates the full pipeline:

| Command | What It Does |
|---------|-------------|
| `/setup` | Fill in profile once |
| `/scrape` | Search job portals, get fit ratings |
| `/apply <url>` | Evaluate fit, draft tailored CV + cover letter in LaTeX, reviewer agent critiques and revises |
| `/interview` | Prep mode |

**Integration with this skill:** Fork the repo, fill in Jordan's profile, and use it to automate the Phase 2-5 workflow. The `/apply` command replaces manual cover letter drafting. The reviewer agent catches what Flash misses — good use of K2.7.

**GenTech Academy angle:** Package as a module — "AI-Powered Job Search" case study showing real results.

**Queued at:** build queue #20 [HIGH] — fork + set up Jordan's profile.

**Target companies (remote):** Zapier, Supabase, Temporal, Render, Linear, Cresta, Fieldguide, Chainguard, Vanta, RevenueCat. Micro1 called Jordan a top prospect — AI test after GOAT meeting.

## Crypto Research / Agent Roles — Cover Letter Strategy

When the role is a **research engineer, founding researcher, or agentic systems role** at a crypto/AI startup, the cover letter strategy shifts further:

| Do This | Not This |
|---|---|
| Lead with 3-4 **shipped production systems** with real users | Lead with education credentials or theory |
| Frame intern/early career as "shipping velocity without credentials" | Apologize for lack of formal experience |
| Reference their **specific research focus** (paper, product feature, founder tweet) | Generic "I'm passionate about crypto" |
| Disclose honest **time constraints upfront** | Pretend unlimited availability |
| Mention hackathon track record as proof of velocity | List coursework |
| Close with a **specific technical connection** to their work | Generic "hope to hear from you" |

**Key insight for crypto research intern roles:** These companies hire for **ownership mindset**, not credentials. The cover letter should read like a co-founder pitch, not a job application.

**Cover letter structure template:**
```
Subject: {Role} — {Name} — {Hook Phrase}

Hi {Founder/Team},

I'm {Name} — {one-line identity}.

I saw you're hiring for {Role} focused on {specific area}. Here's what I've shipped:

- **{Project 1}** — {One-line: what it does + proof of life}
- **{Project 2}** — {Same pattern}
- **{Project 3}** — {Same pattern}

Why this role: {2-3 sentences tying their specific focus to your experience}

Time honesty: {Current constraints and flexibility}

Best,
{Name}
{Contact links}
```

## Chain Foundation Grant Applications

When applying to blockchain ecosystem grants (Solana Foundation, Chainlink BUILD, Arbitrum Foundation, etc.), the strategy differs from job applications. Grants fund **projects**, not people. Lead with the artifact, not the resume.

### Grant Application Structure

| Section | Content | Length |
|---------|---------|--------|
| **Project Name** | Clear, descriptive (e.g., "Agent Registry — Open Infrastructure for AI Agents on Solana") | 1 line |
| **One-Liner** | What it does + why it matters | 1 sentence |
| **Problem** | What problem does this solve for the ecosystem? | 1 paragraph |
| **Solution** | How does your project solve it? | 1 paragraph |
| **Why [Chain]** | Why is this chain the right home? (speed, cost, ecosystem, community) | 3-5 bullets |
| **Artifacts** | Proof of work — repos, tests, deployments, hackathon wins | Table |
| **Milestones** | Concrete deliverables with timelines | Table |
| **Funding Request** | Amount + use of funds | 1 paragraph |
| **Team** | Who you are + track record | 1-2 sentences |

### Grant-Specific Tips

1. **Lead with the artifact, not the resume** — "128 tests passing, deployed on Solana" beats "self-taught developer"
2. **Frame as ecosystem value** — "Brings AI agents to Solana" not "I need money for my project"
3. **Attach hackathon wins** — They prove you ship, not just plan
4. **Non-dilutive preferred** — Grants > equity deals for early-stage
5. **Rolling applications** — Apply anytime, don't wait for "the right moment"
6. **Reuse narrative** — One core story, customized per chain's focus areas

### Grant Target Checklist

Before applying, verify:
- [ ] Project fits the chain's focus areas
- [ ] We have working code (not just a concept)
- [ ] Artifacts are public (GitHub, testnet deployments)
- [ ] Milestones are concrete and time-bound
- [ ] Funding request is reasonable for the scope

**See:** `references/grant-application-patterns.md` for chain-specific templates and examples.

## Grant Applications

For Web3/AI ecosystem grants (Solana Foundation, Chainlink BUILD, Arbitrum, etc.), see `references/grant-applications.md` for grant categories, application template, and strategy. Grant applications differ from job applications — you're pitching a project, not yourself.

## PITFALLS & EDGE CASES

1. **Pitfall**: Defaulting to partnership/competitive analysis when user wants job-fit evaluation.
   - **Root cause:** The agent sees a company link and produces technical/ecosystem analysis instead of role-fit assessment.
   - **Fix:** When user shares a company URL, run the intent clarification check first (see Pre-Flight section). If intent is unclear, ask a short question: "Are you looking at these guys for a job, partnership, or just intel?" before writing a full analysis.
   - **Correction history (Jul 8, 2026):** Agent analyzed Donut AI as a partnership opportunity. User corrected: "the reason why I sent this was because I was curious to see if we fit any of the roles."

1. **Pitfall**: Submitting before resume verification — PDF missing or wrong variant.
   - **Fix**: DMOB sign-off required before submission morning. Check `02-Labs/Resumes/` for file existence.
   - **Verification**: `ls 02-Labs/Resumes/` → confirm all three PDFs present.

2. **Pitfall**: Inconsistent personal details across letters (different name spelling, missing LinkedIn).
   - **Fix**: Create a single `personal-details.md` snippet and paste into each letter before finalizing.
   - **Verification**: Read all three letters side-by-side; spot-check brackets.

3. **Pitfall**: Forgetting to update consolidated doc after creating standalone letter.
   - **Fix**: Always perform Phase 3 immediately after Phase 2. The standalone file is draft; the consolidated doc is source of truth.
   - **Verification**: grep for company name in consolidated doc; ensure present.

4. **Pitfall**: Not noting application portal quirks (some require separate account creation).
   - **Fix**: When evaluating, note "Application portal: Greenhouse / Lever / external". Allocate extra time for account setup.
   - **Verification**: Click each APPLY button before batch session to confirm flow.

5. **Pitfall**: Missing social media handles in follow-up step.
   - **Fix**: During consolidation, research and note Twitter/LinkedIn handles of hiring managers in the document.
   - **Verification**: Check each company's career page or Twitter bio for team members.

6. **Pitfall**: Applying to roles requiring multilingual skills without checking first.
   - **Fix**: Before applying, verify language requirements in job description. Skip roles requiring multilingual if not qualified.
   - **Verification**: Search job description for "language", "multilingual", "bilingual", "English + [language]".

8. **Pitfall**: Verifying job links by HTTP status only — pages return 200 but jobs are expired/filled/redirected.
   - **Root cause:** curl/browser tools can't bypass bot detection on job boards. HTTP 200 means the page loads, NOT that the job is live. Greenhouse, Lever, and Workday pages always return 200 even when showing "position filled" or redirecting to a different listing. This has failed TWICE (Jun 18 and Jun 19, 2026) — 4 out of 5 listings were dead or mismatched despite returning HTTP 200.
   - **Fix, cheapest first — ask the employer's OWN board, not the page.** The ATS feed is the authoritative "still posted" signal and it costs one request per company, not one per role:
     - Greenhouse: `boards-api.greenhouse.io/v1/boards/{token}/jobs` — a role absent from the `jobs` array is gone, however healthy its page looks.
     - Ashby: `api.ashbyhq.com/posting-api/job-board/{token}` — each entry carries `workplaceType`, `location` and `publishedAt`.
     **On Ashby, `workplaceType` is the field that decides, not `isRemote`** — `isRemote: true` co-occurs with
     `workplaceType: "Hybrid"` on the same record, so a boolean read alone reports an in-person role as remote.
     Treat `Hybrid`/`Onsite` as a disqualifier rather than a downgrade: a role he cannot commute to is not a
     lower-ranked lead, it is not a lead.
     **Match on exact title + location, not a substring** — a reposted or renamed sibling will otherwise pass for the original. The same payload also yields the years-required and the pay range, so liveness, eligibility and comp come from one call.
   - **Then extract the full page content** (`web_extract` or the browser snapshot) and READ the actual page before sharing. Check for:
     - Job title matches the listing (not redirected to a different role)
     - Requirements section (look for hidden: bachelor's degree, 3+ years, seniority labels)
     - Application status ("position filled", "no longer accepting", "closed")
     - Relocation fine print (check for "must be in X city", "relocation required")
     - Apply button exists and is clickable
   - **Verification checklist (run for EVERY link before sharing):**
     1. ✅ Page content extracted and read (not just HTTP 200)
     2. ✅ Job title matches search result
     3. ✅ No degree requirement beyond "preferred"
     4. ✅ No experience requirement beyond 0-3 years
     5. ✅ English-only (no bilingual requirement)
     6. ✅ Truly remote (no hidden relocation)
     7. ✅ Apply button present
   - **Standard:** When sharing job links, add a status badge: ✅ VERIFIED (all 7 checks pass) or ⚠️ CHECK (couldn't fully verify). NEVER present unverified links as confirmed. If you can't extract the page content, say so — don't guess.
   - **User correction (Jun 19, 2026):** "almost same problem as last time... The Lightblocks link is no longer available... the OpenZeppelin one is expired... the EigenLayer description said they wanted a senior. Even I got mad at that one because why not put senior agentic AI engineer."

9. **Pitfall**: Resume header includes location when user prefers email-only.
   - **Fix**: Use email in header, not location. Remove LinkedIn if not ready.
   - **Verification**: Check header format: Email, GitHub, Portfolio, Telegram (no location, no LinkedIn).

8. **Pitfall**: Education section empty or outdated.
   - **Fix**: Add current learning (e.g., "Cyfrin Updraft — In Progress") with focus areas.
   - **Verification**: Education section shows active learning, not just degrees.

## Resume Formatting Preferences

**CV = Resume (Jordan uses these interchangeably).**

**Header format (Jordan's preference):**
```
# Jordan Jones — Resume (Master)

**Email:** jordanjones0902@gmail.com
**GitHub:** https://github.com/GentechLabs
**Portfolio:** https://protojay4789.github.io
**Telegram:** @ProtoJay4789
```

**Education format:**
```
## EDUCATION

**AWS Certification Path** — In Progress
- Cloud Practitioner ($0 — Amazon covers the exam) → SAA-C03 ($75 on the CCP voucher) → AI Practitioner → ML Engineer – Associate
- Cloud + infrastructure-as-code is the measured FDE skill-list line (AWS 14 postings, Terraform 9)

**Cyfrin Updraft** — In Progress
- Solidity fundamentals, security patterns, smart contract development
- Learning approach: AI agent codes, humans audit
```

⚠️ **Resume honesty rule (unchanged):** list a certification as "In Progress" **only when it is genuinely in
progress**, and never imply a pass that has not happened. `10-Labs/Resumes/FLAGGED.md` audits this nightly and
found no completion event for either — that check is correct and should stay strict. Planned-but-not-started
certs do **not** go on the resume.

**PDF generation workflow:**
1. Write resume as markdown (`Jordan_Master_Resume.md`)
2. Convert to PDF — WeasyPrint when the toolchain is present; if it is not, render through a browser
   (see `references/resume-retargeting.md` for the CDP `printToPDF` recipe)
3. **Target ONE page for a career-changer resume, and prove it by reading the page count back**
   (`PdfReader(p).pages` == 1). Two pages is not a failure, but it is not the default he should get.
   Fitting is iterative: tighten type/spacing first, then trim duplicated content (a summary that
   repeats the Experience section is the usual culprit), then adjust print scale last.
4. **Extract the rendered TEXT and assert no internal marker survived the render** — `"".join(p.extract_text()
   for p in PdfReader(path).pages)` and check for `DRAFT`, `TODO`, bracket placeholders, and any
   answer-key/notes section that lived in the markdown. A PDF is built from a *file*, not from the part of
   it you meant to send: an internal status header and a "before this is sent" review block both rendered
   into a real letter, and only the text extraction caught them. Page count proving one page says nothing
   about whether the page is the page you meant.
5. Use tables for skills section in the markdown source

## Retargeting a resume to one posting — the rules that apply EVERY time

Full procedure and the render/verify recipe: `references/resume-retargeting.md`.

1. **Confirm which copy is the source of truth BEFORE editing, and say what you could not open.** A cloud
   store may be unreachable (connector not connected, key rejected). If it is, report the failure honestly,
   use the newest local master by mtime, and ask him to confirm it is current. Never imply you read a document
   you could not open — this is the same rule as never printing a number you could not derive.
2. **Take the requirements from the ATS payload, verbatim, not from the rendered page or your memory.** Then
   build a keyword ledger: term → present before → present after. Measure the delta; do not assert "improved".
3. **Add only words he can defend in an interview.** Renaming shipped work in industry vocabulary is free and
   correct; adding `Kubernetes` because a posting wants it is a fabricated credential that fails at the first
   follow-up question. Leave the absent terms absent.
4. **Name the real gaps in the cover letter, in plain language, one line each, with what transfers.** A letter
   that says "I have not operated under DISA STIG controls; that is the real gap for federal support" reads as
   honest and competent. A letter that hides it gets caught in screening and burns the application.
5. **Never assert an eligibility fact on his behalf** — citizenship, security clearance, work authorization,
   degree completion, or a certification pass. Ask, then write the sentence only after he confirms. An
   application built on an invented eligibility line is worse than a late one.
6. **Save as DRAFT and never overwrite a master without his sign-off.** He reviews resume content changes;
   produce the variant, show it, keep the master intact.
7. **Trace EVERY factual bullet to a record in the vault before the document leaves the machine — and delete the
   bullet when the record disagrees or does not exist.** Do not rely on "it sounds like something we did". Two
   distinct failures, both of which read as competent prose:
   - **The contradiction.** A bullet asserted a real-sounding security finding ("audited our public repos and
     found a committed private key"). The vault held the triage note: the scanner raised hundreds of CRITICALs
     and every one triaged to a false positive, and **the audit's actual result was zero real leaks.** The claim
     inverted a documented negative into a positive. A prior note that disproves a bullet is the single cheapest
     check available — grep for the artifact ID (`EVAL-7`, `TOOL-42`, an audit name) and read what it concluded,
     because an audit's *verdict* is frequently the opposite of its *headline count*.
   - **The invention.** A bullet described reviewing third-party files for a class of vulnerability. Nothing in
     the vault mentioned the activity; the phrase existed **only inside the draft**. If the only source for a
     claim is the sentence making it, it is fabricated, however plausible.
   **Grep the distinctive noun, not the concept.** `grep -ri '<the exact technique or artifact>'` across the
   record; zero hits means the claim dies. Then rewrite from what the record actually says — an honest
   "hundreds of false alarms reduced to zero" is a stronger security bullet than an invented catch, because it
   shows detection discipline and it survives the interview question that follows.
   **Apply the same check to the surrounding claims in one pass** — the resume is submitted whole, so one
   unverified sentence discredits the verified ones beside it.

**Primary Goal format:**
```
**Primary Objective:** Transition from Amazon Flex to full-time remote crypto role.

**Strategy:**
1. Learn Solidity via Cyfrin Updraft → create projects that solve real problems
2. Hackathon wins → establish public credibility + prize income
3. Agent Kit v2 → distribute modular agent framework
4. DeFi Model → deploy API endpoint
5. Protocol contributions → open-source recognition
```

**Note:** No relocation timeline — Jordan stays in Cincinnati for family. Goal is remote job, not relocation.

## Grant Applications (Non-Dilutive Funding)

Grant applications differ from job applications — they're **project-focused**, not person-focused. The evaluation criteria is "does this project advance the ecosystem?" not "is this person qualified?"

### Grant Application Workflow

**Phase 1: Research**
1. Search for active grant programs (web_search: "[chain] grants 2026 apply")
2. Extract: amount, focus areas, application URL, deadline, review timeline
3. Check eligibility: crypto-native (they WANT crypto) vs blockchain-agnostic (frame as AI/utility)
4. Save research to `03-Strategies/Grant-Applications-Queue.md`

**Phase 2: Framing**
- **Crypto-native grants** (Solana Foundation, Chainlink BUILD, Arbitrum): Lead with the project, mention chain explicitly
- **Blockchain-agnostic grants** (EF, OWASP, OpenAI): Lead with the PROBLEM we solve, NOT the blockchain. "AI agent security tooling" not "Solana smart contract"
- **Key insight:** "ETH price ≠ Ethereum ecosystem value" — L2s (Base, Arbitrum) have separate ecosystems and grant programs

**Phase 3: Drafting**
Create standalone draft at `02-Labs/{Program}-Grant-Application-DRAFT.md`:
- **Project Name** — one-liner
- **Problem Statement** — what problem does this solve?
- **Solution** — how does it work?
- **Why [Chain/Ecosystem]** — alignment with their goals
- **Artifacts** — proof of work (repos, tests, deployments)
- **Milestones** — deliverables + timeline
- **Funding Request** — amount + use of funds
- **Team** — track record

**Phase 4: Queue Management**
- Update `03-Strategies/Grant-Applications-Queue.md` with new entry
- Update `00-HQ/hackathon-tracker.md` Grant Applications section
- Track status: Draft → Submitted → Under Review → Accepted/Rejected

### Grant-Specific Patterns
- **Reuse narrative across applications** — multi-agent systems, AI agent economy, Solana-native
- **Attach existing artifacts** — hackathon submissions prove shipping velocity
- **Cross-reference hackathon wins** for credibility
- **Non-dilutive preferred** — all grants should be non-dilutive (no equity)
- **Landing rate target:** 3-5 of 7+ applications

### Grant Queue Template
```markdown
| # | Grant Program | Amount | Focus | Status | Notes |
|---|---------------|--------|-------|--------|-------|
| 1 | Program Name | $X-Y | Focus area | 🟢 DRAFT READY | Apply: URL |
```
## ⛔ READ COMPENSATION PER-ROW FROM THE ATS PAYLOAD — never from a neighbouring row

**This shipped a wrong number to the user.** An ATS jobs API returns a *list* of postings, each with its own
compensation block. Reading a range off the wrong row produces a **plausible, well-formed number attached to
the wrong job** — the silent-killer class, in a resume context.

**What happened:** an Ava Labs queue entry was "corrected" to claim the **Senior Forward Deployed Engineer**
paid **$225,029–$337,543**, and the original **$143K–$179K** was declared "wrong by ~$80–150K". **The original
was right.** $225,029–$337,543 is the **Senior Engineering Manager, Fortary Platform** row. The "correction"
propagated into a brief delivered to the user.

**Rules:**
1. **Iterate the jobs array and print `title | location | compensation` together** — never index into a
   neighbouring entry.
2. **Never "correct" a figure you cannot re-derive per-row from the source.** A correction is a claim; it needs
   the same evidence as the original.
3. **When you fix a propagated error, record the error in the artifact** rather than quietly swapping the
   number — otherwise the next reader re-derives the wrong value from the same bad reasoning.
4. **A "correction" that reverses your own earlier claim is the highest-risk edit in the vault.** If it flips a
   prior note, re-read the raw source before publishing.

## The number that matters is applications SENT — instrument the RESPONSE, not the search

**A scanner with no response loop is a machine for optimising a proxy.** Leads found measures the instrument;
replies received measures the candidate. So when the record shows several instruments built and **zero
applications sent**, the answer to "what should I do next?" is the next application, never the next tool — say
it plainly and in that order, because building is the more comfortable task and it always looks like progress.

**The same rule applies one level up when a NEW channel is proposed** — a bounty market, a protocol's builder
programme, a freelance platform, a new job board. Before scoping it, enumerate the human actions still pending in
the channels already open and name the single blocking one. A fourth lane opened on top of three unsubmitted ones
is a fourth instrument, and a quiet month on an existing channel is not evidence that the channel is wrong — it is
usually evidence that nothing was sent.

**Answer a quiet-channel question with demand, not with a new door.** Measure where the work actually is (who
funds it, who pays, how many postings per board) and say plainly which channel has a payer on the other end. A
demand map costs nothing and keeps the standing gates in place; another instrument costs a session and moves
nothing. **Count, don't list:** tally priced or labelled openings per organisation and per board, and say how many
the big names actually run — the largest organisations by repository and follower count frequently run **no**
bounty programme at all, because their demand arrives as paid roles and accepted pull requests. A list of famous
companies is not a demand map; a count per channel is.

- **Log `applied` and `response` on the durable registry at the moment each goes out**, and compute callback
  rate per resume version and per lane. Without that loop, every fit judgement is a prediction that never
  gets corrected, and the whole search is unfalsifiable.
- **An application sent yesterday is not a non-response. Exclude it from the denominator.**
  `decided = total applications − those still inside the reply window (14 days to start)`, then
  `rate = replied / decided`. When `decided == 0` the answer is **UNMEASURED, not 0%** — printing 0% over a
  batch that is two days old manufactures a failure out of silence, and it is the same lie as printing a
  dropped milestone as 0%. Print the known-numeral counts (`replied`, `rejected`, `awaiting`, `of which N
  inside the window`) so the reader can see the denominator being withheld rather than taken on trust.
- **Parse recorded dates permissively; never rewrite records to suit the parser.** A registry accumulates
  writers, so one entry stores `YYYY-MM-DD` and the next stores a full ISO timestamp
  (`2026-10-30T03:46:46+00:00`). `date.fromisoformat()` then raises on the oldest, most important row. Slice to
  10 characters in one helper and treat an unparseable date as `UNKNOWN (age)`, not as age zero.
  Rewriting the user's record to fit your code silently edits the evidence.
- **Prove the rule with a selftest that asserts both directions, not with a comment.** Three cases cover it:
  N fresh applications → `UNMEASURED` (never 0%); old rejections + one fresh → the fresh one excluded from the
  denominator; one reply among N old → exactly `1/N`. A rate function that has only ever been run on the
  happy path is a rate function you have not tested. Implementation: `profiles/arthur/scripts/job-log.py`
  (thin `.sh` wrapper beside it), which extends the scanner's registry in place rather than creating a second
  store — discovery fields stay with the scanner, application fields live with this tool.
- **Dry-run any write path against a COPY and `cmp` the live file afterwards.** State files are the one place
  a test can destroy the thing it was testing.
- **Give the sample size in the same breath as the rate.** At four applications a callback rate is noise; it
  becomes a signal around **15–20**. Volume first, measurement second — twenty imperfect applications teach
  more than four polished ones.
- **A zero-reply batch is a FINDING, not a verdict on him.** It changes the resume or the lane, and it is the
  only evidence that can — so state it that way rather than as encouragement or as failure.

## Entry-level gates to check BEFORE recommending a role

**A live posting is not an eligible posting.** Two administrative requirements are unfixable by skill — read
them first:

- **Degree gates: read the posting BODY for the words, and tell a "plus" from a gate.** Search the ATS body
  (`content` on Greenhouse, `descriptionPlain` on Ashby) for `bachelor · degree · university · graduat ·
  diploma · gpa · master · phd`. **"Having a degree in Computer Science is a plus too" is NOT a gate** and a
  role carrying it stays on the list — quoting a "plus" as a requirement talks him out of a job he can win.
  The inverse also holds: **the application FORM can gate where the body does not** (a mandatory university
  picker, a graduation-year field), so read the form before promising an application.
- **One employer's gate is not the market's — count the prevalence before letting him generalise.** Measured:
  of ~156 live remote entry-tolerant roles, **10 carried a degree gate and all ten were the same employer**,
  while every top-scoring role carried none. When he hits a gate mid-application, report that prevalence in
  the same message. "I need a degree" is a conclusion that silently ends a job search, and one rejected form
  is exactly the evidence that produces it.
- **A posting dies between the scan and the application — re-verify at the moment you hand it over.** A
  closed Greenhouse-backed posting answers **`302 → /404`** and its id disappears from the board array, while
  the URL still looks healthy in a prior audit. A role confirmed live two days earlier can be gone today, so
  re-run the liveness check immediately before recommending, and never carry yesterday's "verified" forward.
- **Student gates.** "Must be graduating in December 20XX or Spring 20XX" closes a New-Grad track to every
  career-changer regardless of ability. **New-Grad and internship tracks are pipeline roles — read the
  graduation-date line before presenting one as an option.**
- **Degree gates vs experience gates are different, and the experience gate is the real one.** The consistent
  hard gate across FDE hiring is *"shipped and maintained real, live systems"* — **not** a degree. Screen on
  demonstrated production work; do not treat a non-CS background as disqualifying.
- **Always scan the WHOLE board for the weaker sibling posting.** Where a New-Grad role is student-gated, an
  **internship** on the same board often says *"pursuing **or received** a degree"* — which admits graduates.
- **Timeline honesty:** the widely-quoted "6 months to FDE" assumes an **experienced developer**; sources
  converge on **18–24 months** without a production-engineering background. **Quote the right one.**

## Answering "what do I qualify for" — give the FUNNEL, and the ONE blocking gate

A question about what he qualifies for is a measurement request, not an opinion request. Answer it from live
postings and show the arithmetic.

1. **Run the scan before you answer — and check for an existing scanner first.** The fleet has a job scanner on
   a schedule; read its script or its latest artifact rather than building a parallel one, or you will hand him
   two disagreeing lists. If you change the scanner, the change is a claim: run it and quote the numbers.
   **Find it before writing anything:** the canonical scorer is `/opt/data/scripts/opportunity-scanner.py`,
   called by a thin per-profile `scripts/opportunity-scan.sh` wrapper and scheduled as an `Opportunity List`
   cron job — `grep -rl opportunity-scan /opt/data/profiles/*/scripts/` locates its seats in one command, and
   the newest digest sits in `09-Green Room/job-apps/scan-<date>.md`. A hand-rolled curl scanner built before
   that grep returns a second, disagreeing list.
2. **Quote the funnel, not just the winners:** *roles seen → entry-tolerant → surviving his hard constraints →
   carrying no visible gate*. A shortlist without denominators reads as opinion and cannot be argued with.
3. **Name what the constraint COSTS.** If "remote" removes most of the entry-tolerant market, say the fraction.
   The cost is what makes the remaining list credible instead of disappointing — and it tells him which axis to
   relax if the list is too short.
   **A fraction is only as good as its denominator, and the denominator is the number you did not compute.**
   Deriving "~65% removed" from `kept + dropped` and then quoting it is how a true calculation becomes a false
   claim: the drop count typed into your own note can disagree with the count the run itself printed, and with
   two recorded figures for one measurement **neither is usable until the run is repeated**. Read the drop
   count out of the artifact the run produced (the digest or the state file), not out of a note you wrote
   afterwards; if the two disagree, say the range and say it is unresolved. Treating a plausible denominator as
   self-evident is the same error as inventing a number — it just survives longer, because the arithmetic in
   front of it is correct.
4. **Say which order the list is in.** "Best evidence match" (a ranking) and "easiest to win" (a ranking of
   screens) are different orders. Handing over one while he is asking for the other wastes his week.
5. **Every role carries its ONE blocking gate in the same breath** — the gate he passes, in the posting's own
   words, and the requirement that is his genuine gap. A role presented without its gate is a role he has to
   re-research.
6. **A willingness most candidates lack is an advantage, never a cost.** Night shift, weekends, on-call,
   holiday coverage: search postings for that language explicitly and say plainly *why* those roles are easier
   to win. Do not present the hours as a sacrifice he is making.
7. **Never hand-type a posting URL from the role title.** Read it out of the scan artifact, then check it
   resolves. A remembered title is not a URL: a hand-typed slug 404s and he is left holding a dead link. For the
   real requirements, read the ATS API rather than the rendered page — Greenhouse
   `boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}` returns the posting `content`, and Ashby's
   `posting-api/job-board/{token}` carries `descriptionPlain`; both are what the *requirements* live in.
8. **Separate "nothing closes the door" from "you will get the job."** Say which one your qualify flag means,
   in the same message. Otherwise the flag is read as a prediction and the misses land on the tool.
9. **When his hard constraint changes, change the SCORER in the same session — then test it without touching
   live state.** A constraint that lives only in your reply gets re-litigated next week; the gate in the script
   is what makes it stick. A scheduled scorer carries state files (seen-set, registry, digest). Import the
   script as a module and override its state/output path constants into a scratch directory before calling its
   entrypoint — a "test" that writes the real seen-set marks every record as already-seen and the next genuine
   run reports zero new leads, which reads exactly like a quiet week.
   **Then verify the written artifact by TYPE, not by exit code.** A dict literal followed by a stray comma
   becomes a one-element tuple, `json.dump` accepts it happily, and every downstream reader breaks on a payload
   that looks present and well-formed. Re-open the file and assert the shape (`isinstance(d, dict)` and the
   expected top-level keys) before believing the run succeeded.
   **Match location strings on word boundaries, never substrings.** `india` matches `Indiana` and `mexico`
   matches `New Mexico`, so a substring geo-reject silently removes US roles — keep an explicit exemption list
   (`new mexico`) for the names that legitimately contain a foreign country.
   **Blocklist the ABBREVIATIONS too, not just the country names.** A posting renders the employer's own
   shorthand, so a list that knows `saudi` but not `ksa` lets a Gulf role rank into the top ten looking
   US-eligible — add the codes and capital cities for each blocked country (`ksa`, `uae`, `riyadh`, `doha`).
   The tell that a geo list is incomplete is a top-ten entry whose location is a city you have never seen in
   a US posting; read the ranked output for place names, don't just count rejections.
10. **If the job belongs to another seat, file a handoff naming the job id and the expected behaviour change.**
    Editing a canonical script that another profile schedules is a fleet change, not a private fix. State what
    changed, that fewer or no leads is the filter working rather than a fault, and which counter to read before
    assuming breakage — otherwise the first thin week is debugged as a regression.
11. **A FEED is not a board — measure its yield before claiming the lane is covered.** Some employers (data
    vendors, contract shops staffing research labs) never appear on Greenhouse/Ashby/Lever, so an ATS-only
    scanner cannot see them however many boards it holds. The cheap fix is an RSS/Atom adapter, and three
    things go wrong with it every time:
    - **Yield is tiny and it must be measured, not assumed.** One feed returned twenty postings across all
      categories and exactly one passed the scorer — below the ranked cut, so it would have been invisible.
      Either give feed-sourced roles their own line in the digest or the tap is decorative.
    - **The employer is per-ITEM, not the source name.** A feed yields many companies; overwriting the record's
      company with the source label attributes every lead to the aggregator.
    - **An empty location field silently fails a remote-only gate.** Feeds for remote-only listings often leave
      location blank, and a hard remote requirement then drops 100% of the feed while reporting a normal run.
      Default a remote-only feed's blank location to `Remote` at parse time.
    **Then say plainly what the lane is worth** — a feed that yields one candidate a week is a tap, not
    coverage, and the honest reply is that the real signal for that lane arrives by email alert or by checking
    the vendor's own application page.

## "Are we still pursuing X?" — read the served track, then answer NO if that is the truth

A question about whether a lane is still current is a **lookup**, not a strategy session. The plan is served
from one file and the answer is in it; the failure mode is treating an old job title or a demoted track's
milestone as evidence of a live lane and announcing a pivot that never happened.

1. **Read the selector first: `10-Labs/skills-distribution/edu/data/active-track.json` → which pack is served.**
   Then read that pack's `target` block. That `target` is the lane; anything else is context.
2. **Authority order is stated in the selector and it outranks mtime: the learner's explicit decision, then the
   pack matching it, then newest write — last.** A track file written later to close a milestone has not moved
   the lane, and saying it did invents a decision he never made.
3. **Grep the served pack for the lane name before answering.** `grep -ic "<lane>" career-track.json` → **0** is
   decisive and takes one command. Zero mentions plus a milestone list that never contains it means the lane is
   not in the plan at all — say that plainly rather than hunting for a stage to rename.
4. **Separate the three things a lane word can mean, because they live in different files:**
   - **the lane** — the pack's `target` (what he is studying toward);
   - **skill coverage** — a milestone inside a *demoted* track that survives because the skill is market-measured
     (a 8-hour SQL milestone is a skill, not a career target);
   - **an applied lead** — one record in the job registry, which is a lead and not a strategy even at n=1.
5. **Answer with the genealogy, then the verdict.** Name where the idea came from (which record, which demoted
   track, which past tiering exercise), say which of the three it actually is, and state that the plan needs no
   change. "Nothing moved" is a finding worth proving, not a disappointing non-answer.
6. **Name the drift risk that a deferred milestone creates, and give it a date.** A cert deferred indefinitely is
   `UNMEASURED` — not started, not passed, not scheduled — and the honest flag is a decision point at a named
   date, not an exhortation to study harder.

## Application form free-text — answer with a verification discipline, never a success story

Every long-form question on an application ("most impactful thing you built", "how did you know it worked",
"what does success look like") is testing **how you judge your own work**, not how proud you are of it. Answer
procedure, checks and evidence; skip adjectives.

- **Verify every factual claim against the live thing immediately before writing it, and never print a status
  you could not reproduce.** "200 / live / N services" is a claim with a shelf life: applications stay open for
  weeks and an engineer may click the link. Open the URL, quote what it returns today, and if it fails, the
  failure becomes the answer rather than being quietly dropped.
- **Name the specific failure the system exists to prevent, then the checks that catch THAT failure.** Correctness
  defined in one sentence beats a feature list; three named checks beat "I tested it thoroughly".
- **Say what a BAD result would have looked like.** A check whose failure mode you cannot describe is not a check.
- **A break you found yourself is the strongest material in the answer** — "I found it by checking the live URL,
  not by trusting the last report I'd written" demonstrates the discipline the role is hired for. Do not hide a
  current outage to protect the narrative; that is the one thing that turns a strong answer into a fragile one.
- **Never assert an eligibility or credential fact he has not confirmed** (pass, citizenship, clearance, degree).
  Same rule as the resume: ask, then write.

Worked structure, the three-check template and a full example: `references/application-form-answers.md`.

## When a lane gets demoted, measure the REPLACEMENT — do not argue about the old one

He will revise the target, sometimes after applying. The old lane does not get a rebuttal; it gets a demotion
written where the engine reads it, and the replacement is chosen by counting, not by intuition.

1. **Count role FAMILIES across the boards already being scanned.** One pass over the ATS feeds, bucketing every
   title into families (support, solutions/SE, apply/deploy, ai-agent engineering, research, infra, data, security,
   sales-side) gives the ring that is hiring this quarter. Families are cheap to count and impossible to eyeball.
2. **Prefer the ADJACENT ring to the aspirational one.** Adjacent means the day job overlaps what he is already
   building — integration, customer-facing deployment, technical support — without demanding a discipline he has
   not practised. Research/scientist titles look closest on vocabulary and are furthest on discipline: exclude
   them explicitly so they stop reappearing in rankings.
3. **Record the demotion where the engine reads it, not only in the reply.** A `superseded_claims` line plus a
   dated correction field in the active-track or pack JSON, naming what survives as *skill coverage* versus what
   dies as a *placement strategy*. Skills outlive lanes: a Go or IaC milestone can keep its place while the lane
   that spawned it is retired.
4. **When he says the old lane is unreachable, your own earlier audit is the corroboration.** If a measured
   years-gate in your prior work agrees with him, cite that number — do not restate the old plan's case as a
   counter-argument. He is revising on evidence; supply the evidence, not a defence.
5. **Retarget the resume to the new ring in the same pass.** A document pitched at the abandoned lane is now
   pointed at roles he is no longer pursuing, and shipping it wastes the applications.

## A stored verdict EXPIRES — re-measure before repeating it

**A status file records what was true when it was written, not what is true now.** Resume-sync logs, monitoring
notes and prior audits are the highest-risk source in this lane, because they read as authoritative and get
quoted verbatim into advice. Both shapes below shipped a wrong sentence to him in one session:

- **The stale 200.** A sync log asserting "all surfaces 200" had been right for months; on the day it was
  quoted, every one of those URLs answered **404**. The log had not changed — reality had.
- **The stale 404.** A note asserting an account was "hidden, 404 to logged-out readers" had been true when
  written and was false later: the account answered **200** anonymously to anyone who asked.

**Rules:**
1. **Re-run the exact probe before quoting the verdict** — one status-code call per surface, and probe
   **anonymously** when visibility is the question. An authenticated 200 on your own artifact proves only that
   the owner can see it.
2. **Label which you did** — "measured just now" versus "carried from the log, not re-measured". A carried
   claim spoken without that label is an assertion about today built from data about last month.
3. **When a live probe contradicts your own stored note, the probe wins and the correction gets written down** —
   including when the correction makes earlier advice of yours wrong. Fixing it only inside the reply is not
   enough: the next reader will quote the stale line again.
4. **Never quote a log's conclusion into an application, a resume, or a message** without re-probing. The shelf
   life of "live / 200 / visible" is shorter than the life of an application.

### A 404 is not damage until something links to it

Before escalating a broken surface as an applicant-facing loss, grep the live pages for that path. Measured on
two live properties: **zero** references to the resume on either — so the 404s were a stale claim inside a log,
not a broken funnel, and saying that was more useful than manufacturing an emergency. **The test is "who points
here?", not "does it return 200?"**, and the same test decides whether the fix is urgent or cosmetic.

### The master is older than the evidence it should cite

Before any application push, compare the resume master's mtime against the newest shipped artifact. A master
older than the portfolio means applying with yesterday's credentials: **the artifact exists and the document
cannot mention it.** Refresh first, publish second — a stale master re-hosted at a fresh URL is staleness made
permanent. Say the comparison out loud (master date vs artifact date) rather than deciding silently that the
resume is "fine".

## Certification questions — absence of a keyword is not a verdict

"Should I get cert X" has three instruments behind it and they measure different things. Separate them out loud.

1. **Keyword counts measure what postings SAY, not what a screener DOES.** Counting cert names across
   text-bearing postings is cheap and worth doing, and a near-zero is the expected result — certifications are
   almost never written into a posting body; a recruiter filter applies them and the corpus cannot see it.
   **Report the zero and state the blindness in the same breath.** Turning "0 postings mention it" into "it does
   not matter" is a fabricated verdict manufactured from a real measurement, which is the worst kind.
2. **A provider's own page is not evidence.** Weigh a cert by whether a posting he actually wants names it. A
   course page quoting a salary bump is an advertisement.
3. **Order by deadline and by cost-to-him, not by prestige.** A voucher with a calendar-year expiry outranks any
   optional certification, because expiring free money is a decision to pay later. Confirm the employer-funded
   door before recommending anything paid.
4. **Never let a cert substitute for an artifact.** The standing rule is that a purchase before the artifact is a
   substitute for the work. When the gap is a capability, the deliverable is the artifact; the badge is at most
   packaging applied afterwards.

## Pay bands — publish only what the posting publishes, and treat a stated floor as a floor

Two different numbers get confused here, and the confusion is expensive.

1. **A blank is not a low number.** If the posting carries no salary, write "not published" — never leave the
   cell to be read as zero, and never borrow a figure from the company's other row. `references/…` aside, the
   rule is the same one that governs compensation generally: read it per-row from the ATS payload.
2. **A range belongs to the posting that states it.** When one role on a board publishes a band and its
   neighbour does not, that band says nothing about the neighbour. Say which roles published and which did not.
3. **When he names an acceptable floor, it is a FLOOR, not a target.** "Even 60–70K is fine to start" is
   permission, not a preference — it does not shrink the list to roles in that band. Keep the higher-band roles
   first, and say plainly that the risk is **under-applying to the band he already qualifies for because a lower
   number was in his head**, then accepting the first low offer that arrives.
4. **Repeat the floor back as a constraint you are honouring, not as an ambition you are lowering.** The reply
   should make clear which roles publish more than his floor and which are the realistic floor-band entries, so
   the choice stays his.

## Contract and data-vendor gigs — a different purchase from a job

Some postings are not employment. Expert-data shops that staff AI labs (they sell RL environments, evals and
grading rubrics for model training) advertise **contract** roles with technical titles, a per-hour rate and a
fixed term. Evaluating one as if it were a job wastes the read.

1. **Work out what the employer SELLS before describing the role.** The same title means different work at a
   different business model: a "security engineer" at a data vendor is an **eval author** — building deliberately
   flawed systems and labelling the findings to make training data — not an operator defending a production
   estate. Read the company's own site (what they sell, who buys it) first; it reframes the posting correctly and
   frequently converts a weak-looking match into a strong one.
2. **Confirm the domain is the right company.** Similar names belong to unrelated businesses — a studio's
   game-server site sitting one letter away from the vendor's consultancy site is a different employer. Take the
   canonical domain from the aggregator's company page, then read that domain's description of itself. A role
   attributed to the wrong company yields a confident, useless assessment.
3. **Count the total, then say what it is.** rate × hours per week × weeks is the entire engagement. State the
   figure AND state plainly that it does not replace the day job — a per-hour contract that totals a few thousand
   is a credential purchase, not an exit. Never let a contract rate be read as an annual salary, and compare the
   full-time equivalent against his stated floor in the same breath.
4. **Judge a gig on what it leaves behind.** The return is the title it puts on the resume, the skill family it
   exposes him to (RL environments, evals, annotation pipelines are current and scarce), and a small portfolio
   artifact. Say that out loud, because the money alone would not justify it — and name the load that is
   realistic alongside his existing shift pattern.
5. **Read the application FORM before promising an application, and treat its fields as gates.** Forms carry
   blockers the posting body omits: a mandatory public profile link, a graduation-year field, a residency
   dropdown. A field he cannot fill is a blocker to surface before he sits down, not during.
6. **Ask what the pilot pays and what the agreement assigns.** Vendors of this shape run a small qualification
   batch — confirm it is paid before any work starts, and read the contributor/confidentiality terms for IP
   assignment and exclusivity. Cheap questions before signing, impossible afterwards.
7. **A gig does not pause the credential clock.** Keep the funded certification and the role applications running
   in parallel; a four-week contract is not a reason to let a deadline-bound voucher expire.

## The INFRASTRUCTURE gate — screen it first, and it is not closable by effort

**Some must-haves are a different discipline, not a higher level of the one he has.** Before recommending
any platform/infrastructure role, search the must-haves for cloud-infrastructure ownership language:

> *"Own infrastructure end to end in Python on **GCP**, with a **cloud warehouse** and
> **infrastructure as code**"* — Supabase, AI Platform Engineer, 2026-10-15.

That sentence asks for a cloud-infra engineer's history: a provisioned cloud account, a warehouse, IaC,
and having deployed, monitored and rolled back systems inside it. **A single VPS in Docker does not
answer it, and no amount of interview quality closes it** — the screener is matching a CV line, not
judging architecture. **Jordan's own call on it: "if I don't have any experience then it will just go
ahead and skip it."** He does not want this class of role surfaced as an option.

- **Screen it out at read time, and say so in one line.** Do not present a role with an infra gate as a
  [GO] with a caveat and a strategy — a caveat costs him the time the verdict was supposed to save.
- **Distinguish it from the experience gate that IS closeable.** "Shipped and maintained real, live
  systems" is answerable with artifacts (the fleet, the kit, the measured cost work). "Own GCP + a
  warehouse + IaC" is not answerable with a different artifact; it is a missing discipline.
- **The pattern to keep recommending:** agent/eval/FDE roles whose must-haves are *shipped systems,
  evaluations, MCP servers, API depth, adoption, taste about contacting humans.* Those are the five he
  can answer from the fleet — and the fleet is the case study, not a job history.

## Jobs won by CONTRIBUTION, not application — search them deliberately

Some employers have no application funnel and say so in writing: the role is earned by shipping a reviewed
change in public. The channel is real and queryable, but only on the right surface.

- **Search LABELS and repo identity, never body phrases.** `label:bounty`, `label:"Help Wanted"`, `label:hiring`
  return a bounded, curated set; a phrase query over issue bodies returns tens of thousands of unrelated hits
  (game servers, guild banks) at roughly 1,000:1. Phrasing is a human cue; labels are the machine cue.
- **The price is usually in the issue TITLE** (`[$250] …`), not a field — parse it there, and treat a missing
  price as unpaid.
- **Read the repo's own CONTRIBUTING before the work.** Bounty programmes gate payment behind a platform
  account and, typically, a proposal accepted **before any code is written** — so the first hours are always
  unpaid. Surface the payout path before he invests, not after.
- **Set the expectation at "rejected proposal", not "money".** A first-time contributor competes publicly with
  people who have done hundreds; the public PR is the return, the payout is the upside.
- **Prefer a bounty in a domain he can already demonstrate**, so the artifact argues instead of the resume — and
  compare its hours against a normal application rather than presenting it as a shortcut.
- **The contribution is judged under an ACCOUNT — verify that account is visible before doing the work.** Query the
  profile endpoint with no credentials (`GET /users/<login>`); anything other than `200` means the submission will
  be reviewed as never sent, however good the code is. Use the account that answers `200` anonymously for every
  outbound PR, and do not treat a second account as interchangeable: **invisibility is a property of the account,
  not of the work**, so a contribution moved to a visible account is a different contribution, not the same one
  resubmitted. This gates every open-source channel at once and costs one request to check.
- **Availability lives in the THREAD, not in the `assignee` field.** These markets claim by comment and by a linked
  open PR, so an issue showing `assignee: null` can be completely spoken for. Read the last stretch of comments
  before recommending anything, keep claimed items visible with their evidence rather than silently dropping them,
  and rank **recent and quiet above well-matched and busy** — the best-fitting work is taken within hours by
  regulars, so the window beats the fit for anyone without standing in that repo.

Full decision table, selection criteria and verification notes: `references/contribution-hiring-channel.md`.

## RELATED SKILLS

- `career-platform-research` — research → evaluation → recommendation phase
- `gentech.vault-compliance-audit` — track deadlines and follow-ups in vault
- `agent-coordination` — handoff patterns to DMOB and GenTech HQ

## Support Files

- `references/application-form-answers.md` — long-form application questions ("most impactful build", "how did
  you know it worked"): verification-discipline answers, the three-check template, and the verify-before-claim rule.
- `references/contribution-hiring-channel.md` — GitHub as a hiring surface: bounty programmes, label queries,
  payout-path gates, first-bounty selection, and why body-phrase search is unusable.
- `references/resume-retargeting.md` — Aim one resume at one posting: ATS requirement extraction, keyword
  ledger, gap disclosure, eligibility rules, and the one-page render/verify recipe.
- `references/grant-application-template.md` — Template for grant applications (crypto-native + blockchain-agnostic). Includes narrative patterns, artifact tables, milestone format, and active grant targets.
- `references/application-batch-2026-05-04.md` — Previous application batch details
- `references/ai-native-web3-roles.md` — Patterns for AI-native/Web3 demo roles
- `references/crypto-startup-email-application-example.md` — Full worked example: Donut AI direct email application (cover letter structure, tracking pattern, DM outreach)
- `hackathon` — hackathon submissions as grant credentials

## MAINTENANCE
College.xyz UI changes may affect APPLY button behavior or external form flows. Revalidate quarterly.
Grant program URLs and focus areas change quarterly — revalidate each quarter.

---
**Status:** Available