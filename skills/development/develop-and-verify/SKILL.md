---
name: develop-and-verify
description: "Use when building, fixing, or changing ANY code or asset — and whenever you find a bug while working. The Jr/Sr default (DeepSeek V4 writes, Kimi K2.7-code audits), the fix-it-don't-ask rule for bugs found in scope, and the silent-wrongness checklist. Fleet standard, Jordan 2026-09-21."
version: 3.0.0
author: gentech
tags: [build, audit, workflow, jr-sr, bug-discovery, silent-wrongness, fleet-standard]
---

# Develop & Verify — Consolidated Pipeline

## Media Pre-Publish Verification (Video/Audio/Images) — added Aug 31, 2026

**Jordan's directive:** "make sure everything is being verified before we put it out for the final" — applies to animated/demo videos, narrated content, thumbnails, and any media shipped publicly (hackathon judges, YouTube, X). Same DONE-means-verified bar as code.

### Frame-level encoding audit (caught live: em-dash mojibake in 0G demo v1)
Every rendered frame/card gets a vision-model readback BEFORE video assembly:
- [ ] **Mojibake scan** — vision_analyze each rendered frame asking for ANY special characters, mojibake (â€", â€™, Ã©), tofu boxes (□), or U+FFFD. Em dashes, smart quotes, and arrows (→) are the repeat offenders.
- [ ] **Pure-ASCII rule for rendered text** — generated HTML/SVG frames MUST declare <meta charset="utf-8"> AND use ASCII-only copy (hyphens not em dashes, '>' not →). The demo runbook rule now applies to video frames.
- [ ] **Font-glyph check** — verify the rendering font actually contains every glyph used (DejaVu covers →, most terminal fonts do NOT).

### Fact/number verification against live sources (claims in frames)
- [ ] Every number rendered in the video is re-checked against the LIVE source in the same session (not memory): chain IDs, balances, prices, versions, amounts.
- [ ] Every claim ("4/4 tests pass", "TEE-verified") is traceable to a real captured artifact (log file, API response) stored alongside the project.

### Audio verification
- [ ] Duration check with ffprobe (>3s, matches intended length ±10%).
- [ ] Voice = intended voice (correct voice_id used), no truncation of the final sentence.
- [ ] Cloned voices: segments ≤35s, model eleven_multilingual_v2 (see elevenlabs-voice-generation skill).

### Assembly verification
- [ ] Final render watched end-to-end (or ffprobe duration == expected sum of cards).
- [ ] Audio/video lengths reconciled (-shortest artifacts checked — no abrupt cut).
- [ ] File delivered to ALL required surfaces: repo (raw 200 verified), vault commit, chat MEDIA delivery.
- [ ] Prior-version cleanup: superseded files removed or explicitly marked deprecated in README/repo.

### Pipeline placement
Media builds run the same 5 phases: PLAN (storyboard + fact list w/ sources) → BUILD (render frames/audio) → **REVIEW (vision-audit every frame + audio check — the AUDIT gate is where mojibake gets caught)** → FINISH (assemble, mux) → VERIFY (numbers re-checked live, raw URL 200, file sizes match).

## Core Pattern — Three Tiers

| Phase | Model | Provider | Cost | What |
|-------|-------|----------|------|------|
| **DEV (Jr)** | **the FREE model on the `nous` rail** — `meituan/longcat-2.5:free` (Jordan, 2026-11-25: *"we'll treat the free model we use as the Jr by default"*) | `nous` | **$0** | Draft code, mechanical work, classify/extract/rewrite |
| **AUDIT (Sr)** | **resolved at call time from the ladder** | **the OTHER rail** (resolved at call time) | ~$0-2/M out | Code tracing, bug hunting, security, architecture review |
| **BIG BOY** | Kimi K3 | either rail | ~$15/M out | Architecture decisions, security audits, design reviews, full-codebase analysis |

**Jr-by-default, measured before it was adopted.** Four free models were probed with two live completions each on
2026-11-25: `meituan/longcat-2.5:free` (17 tokens for a one-word reply — cheapest), `tencent/hy4-flash:free` (42),
and `stepfun/step-3.7-flash:free` **which returned HTTP 400 twice and was rejected**. The alias we had been
pointing at for months, `upstage/solar-mini4:free`, also returns **HTTP 400** — a configured fallback that had
never worked. **Prove the tier before you assign work to it.**

**Two tasks are deliberately NOT Jr, and the reason is a failure, not a preference:**

- **`compression`** writes the summary a future session reads *instead of* the transcript. A small model that
  compresses badly destroys context for every later turn — the saving buys amnesia.
- **`vision`** needs an image-capable model; none of the free set is proven for images.

Both stay on the capable aux model (`glm-5.3-flash`). **Everything mechanical — approval classifier, triage
specifier, curator, session search, skills hub, MCP, web extract, background review — runs free on all four seats.**

**DUAL-RAIL ROUTING (Jordan, Sep 21 2026 — this is the rule):**

> *"We need to be able to switch between providers depending on our situation. Last night we were
> using opencode-go but as soon as Ollama Cloud is back, we are back to our original and no longer
> using our fallback. So this rule needs to go for both providers that we use, so that when we
> switch between the two it just works."*

We run on **two rails, and we switch between them by circumstance** — not by editing docs:

| Rail | Role | Notes |
|------|------|-------|
| `ollama-cloud` | **primary / original** | the default. When it is healthy, we are here. |
| `opencode-go` | **fallback** | used while ollama-cloud is capped/degraded. NOT retired. |

**The auditor is ALWAYS resolved at call time on the rail the worker is NOT using.** That is what
makes verification genuinely cross-provider. Never hardcode the auditor to one provider — a
hardcoded rail is exactly the bug fixed on Sep 21 (see below).

### ⚠️ INTENT is the constant; MODEL NAMES are the variable (Jordan, 2026-10-31)

> *"As models get upgraded or they launch new models, there are models that get deprecated, or
> maybe the provider just has a limited-time thing. So we can't have a definitive model — but
> **we always provide intent, and that's our basis for the audit, and that's how we choose the
> model based on the intent.**"*

**A hardcoded ladder of model names is a guess about the future, and it rots.** Models are added,
renamed, quietly retired, or put behind a limited-time allowance. Any list we write in a skill
file is **wrong within a quarter** and gives no signal when it goes wrong — it just starts
silently picking a worse auditor, or a dead one.

**Intent does not rot.** *"Find what would make this print a confident wrong answer"* is a valid
instruction on every model that will ever exist. So:

**1 · WRITE THE INTENT FIRST — it is the audit, not a preamble to it.** The intent is
**one question + the number that answers it** (§The AUDIT INTENT below). No number, no audit.
The prompt is *evidence + intent*; the model is a substitutable executor of that intent.

**2 · CHOOSE THE MODEL *BY* THE INTENT, not by a name list.** Ask what the intent demands:
does it need long-context source reading, deep reasoning, cheap volume, or a specific modality?
Then pick the strongest **currently-offered** model that satisfies it. **The requirement is
derived at call time; only the requirement is durable.**

**3 · DISCOVER THE CANDIDATES FROM THE RAIL AT CALL TIME** — never from this file. Ask the
endpoint what it offers (`GET /v1/models`) and choose from *that* answer. A model named in a
doc is a hint about tier, not a fact about availability.

**4 · RANK BY CAPABILITY TIER, NOT BY PRODUCT NAME.** Tier is the durable property: *frontier
reasoner · strong code model · cheap worker flash*. A new frontier model should slot into the
ladder automatically, without an edit here. This is why the resolver's ladder is a *tier
preference with named examples*, not a canon.

**5 · FALL THROUGH ON FAILURE, AND SAY WHICH MODEL ANSWERED.** Timeout, 0-char response, or
HTTP error → try the next. **Record the model that produced the audit in the report** — an
audit whose provenance is unrecorded cannot be re-run or trusted later.

### When a second provider does not exist — SEARCH THE SAME PROVIDER (Jordan, 2026-10-31)

**A single rail is a real constraint, not permission to skip the audit.** When only one provider
key exists on the host, the rule is:

> **Exhaust the same-provider Sr ladder before declaring a downgrade.** *"Different provider" is
> the ideal, not the only bar.*

**Same-provider-but-different-model is a genuine verification step** — it removes the
**shared-model** blind spot even though the shared-rail blind spot remains. Declaring that
honestly is strictly better than refusing to audit.

**The ladder, strongest first** (`kimi-k3.1-pro` → `kimi-k3` → **`glm-5.3`** →
**`kimi-k2.7-code`** → `qwen3.8-max` → `grok-4.7`). `glm-5.3` and `kimi-k2.7-code` are the
named same-provider alternatives — `kimi-k2.7-code` is the fleet's established Sr auditor,
`glm-5.3` is a different model family and therefore a genuinely independent read.

**Two requirements, or the search is theatre:**

1. **SHOW THE LADDER AND ITS VERDICT** — every candidate printed with why it was or was not
   chosen (`CHOSEN` / `available (fallback)` / `not offered` / `excluded — worker tier`).
   The difference between *"we could not find one"* and *"we did not look"* is the printout.
2. **STILL DECLARE THE DOWNGRADE.** Same-provider must never be reported as cross-provider.
   Say **"cross-model on one rail"**, and name the missing key. An undeclared same-rail auditor
   called *"cross-provider (strongest available)"* is the Sep 21 false green verbatim.

**Never let "only one rail" silently escalate to "no audit".** If the ladder is truly empty,
say `UNRESOLVED`, exit non-zero, and label the work **unaudited** — that is a known state.

**Resolve it, never assume it:**
```bash
python3 /opt/data/profiles/gentech/scripts/audit-model-resolve.py            # worker -> auditor
python3 /opt/data/profiles/gentech/scripts/audit-model-resolve.py --explain  # full candidate table
python3 /opt/data/profiles/gentech/scripts/audit-model-resolve.py --selftest # prove BOTH rails work
```
It reads the **active provider from the profile's own config.yaml**, picks the best auditor
against it, and **declares the downgrade when it cannot get a different provider**. If nothing is
available it exits non-zero — so no caller can claim a verified result on nothing.

> **⚠️ BUG FIXED Sep 21 2026 — the auditor rail was silently single-rail.** The resolver read
> `^provider:` **anchored at column 0**, but our configs nest the key under `model:` indented two
> spaces. The regex **never matched** and the function fell through to a **hardcoded default of
> `opencode-go`**. While we ran on opencode-go it was *coincidentally right*, so nothing looked
> wrong. The moment we switched back to ollama-cloud it was **wrong**: it believed the worker was
> opencode-go, excluded opencode-go from the candidates as if it were the worker's own rail, and
> then labelled a **same-rail auditor** as *"cross-provider + cross-model (strongest available)."*
> A false green in the one place whose entire job is to not produce false greens. Fixed to parse
> the YAML properly; now correct on **both** rails with no edit when we switch, guarded by
> `--selftest`. Related: the config is not the only column-0-anchored reader we have had — prefer
> a real parser over a regex for nested keys.

**Provider status history:** GLM-5.3-flash via **Z.AI is DEAD** (`1113 Insufficient balance`) —
**do NOT route to it or name it as the auditor.** Ollama Cloud previously hit a weekly cap (429,
resets weekly) — that cap is why the fallback rail exists and must keep working.

**Rule of thumb:** Start with Flash. If it fails or output is wrong, retry on K2.7. Only reach for K3 when the answer is worth $15. Jordan's directive (Jul 27, 2026).

## Modular Build Strategy

Build every component as a **pluggable module** — not a monolithic project. This lets us enter multiple hackathons without rebuilding from scratch.

**Core principle:** Each piece (x402 gateway, ERC-8004 identity, AgentEscrow, Agent Credit Score) is a standalone module. To enter a new hackathon, we swap the settlement layer (Arc, Solana, Base) and keep the agent logic. Config changes, not rewrites.

**Proven pattern (Jul 2026):**
- Arc Programmable Money Hackathon: x402 contracts deploy to Arc with config change + new deploy script. Agent logic unchanged.
- XPRIZE ($50K Circle Prize): Same stack, add Gemini API call + Google Cloud product. No rebuild.
- Future hackathons: Same modules, new chain config. Days, not weeks.

**Hackathon qualification shortcut:** When Jordan asks "do we need to build something or do we already have it?" — the answer is usually "we have it, just needs a config change." Our existing live infrastructure (x402 gateway, ERC-8004, AgentEscrow, Agent Credit Score) qualifies directly for agentic payments / agent economy hackathons. Don't plan a new build unless the specific track requires it.

## Big Brother Audits — Model Strategy

You don't need every model to be the best. You need a **cheap coder + a powerful auditor**.

| Pattern | Coder | Auditor | Cost vs using auditor for everything |
|---------|-------|---------|--------------------------------------|
| **Current** | DeepSeek V4 Flash (Jr) | Kimi K2.7-code (Sr) | Both free on Ollama Cloud |
| **Local fallback** | Nemo Tron 12B (free) | K3 (BlockRun — $3/M in, $15/M out) | ~90% cheaper than K3 for everything |
| **Emergency** | Mistral 7B (free) | Claude Opus (pay-per-call via Gata $20/mo) | ~95% cheaper than Opus for everything |

The auditor doesn't run every call — it spot-checks the important ones. The **AUDIT phase** in the build pipeline is where the expensive model goes. The **DEV phase** uses the cheap model for the bulk of the work.

For audits that need a frontier model (Opus 4.8, GPT-5):
- Use **blockrun_chat mode="coding"** or mode="powerful" for one-off reviews
- Use **Gata Starter ($20/mo)** as a fallback if OpenCode Go is down — gives access to Opus 4.8, GPT-5, Gemini 2.5 Pro with automatic failover

**Total infrastructure:** ~$62/mo ($20 Ollama Cloud Pro + $42 VPS) — OpenCode Go retired, Hermes portal (Nous) is the free fallback

## Fast-Track Rule

When Jordan provides a clear task list from prior context (status report, build queue, green-lit design doc), skip brainstorming. Jump straight to plan or build. **Karpathy gates still apply.**

## Build Pipeline (5 Phases)

### Phase 1: PLAN
- Check what already exists (`ls`, `find`, `pytest` existing tests)
- Break work into bite-sized tasks (2-5 min each)
- Each task: exact file paths, code outline, verification step
- **Karpathy Gate:** Every task has testable success criteria, not "make it work"

### Phase 2: BUILD (DEV — DeepSeek V4 Flash on Ollama Cloud)
- Write failing test FIRST (TDD: RED → GREEN → REFACTOR)
- Write minimal code to pass
- **Karpathy Gates:**
  - No features beyond what was asked
  - No speculative abstractions
  - Touch only what you must
  - No "improving" adjacent code

### Phase 3: REVIEW (Sr — Kimi K2.7-code on Ollama Cloud)
- Security scan (no hardcoded secrets, no injections)
- Plan compliance check
- **Specific audit checks that catch real bugs:**
  - **Error detail leakage** — `str(e)` in exception handlers leaks stack context to clients. Fix: log with `exc_info=True`, return generic error message without `detail=str(e)`.
  - **Log injection** — User-controlled input (URL params, headers) logged via f-strings allows log forging. Fix: sanitize with `safe = input[:64].replace("\n","").replace("\r","")`, use `%r` parameterized logging.
  - **Input length bounds** — Regex patterns without max-length pre-checks allow ReDoS-adjacent resource exhaustion. Fix: enforce max length before regex matching.
  - **Race conditions in async counters** — `global count; count += 1` is not atomic in async contexts. Use `asyncio.Lock` or a proper metrics library.
- **Weak randomness for identifiers (CWE-338)** — `random.randint()` or `hash(str(ts))` for scan/request IDs is predictable and collision-prone. Fix: use `secrets.token_hex(16)` or `uuid.uuid4()`. This applies to any generated ID that could be enumerated or guessed (scan reports, payment requests, session tokens).
- **Pre-compile regex patterns at module load** — `re.search(pattern_string, text)` in a loop recompiles the pattern on every call. For modules that scan many inputs (tool descriptions, URLs, configs), compile all patterns once at module level: `_COMPILED = [(re.compile(p), label) for p, label in RAW_PATTERNS]`. Then use `pattern.search(text)` in the hot path. Also prevents ReDoS by keeping compilation cost out of the per-input loop.
- **Individual try/except per sub-operation, not one big wrapper** — When orchestrating multiple independent sub-scans (identity check + MCP scan + x402 audit), wrap each in its own try/except. A failure in one sub-scan should not prevent the others from running. Log with `exc_info=True` and let the result be `None` — downstream checks handle `None` gracefully.
- **Operation ordering in security-sensitive code** — Signature verification, auth checks, and access control must execute BEFORE any state mutation (caching, persistence, database writes). A verify-then-cache ordering bug lets an attacker poison the cache with forged data even when their signature fails. Fix: verify first, then mutate state. This applies to payment middleware, webhook handlers, and any endpoint that validates then stores.
- **A check that records while it checks burns evidence a later step still needs** — even if the earlier step refuses, its write has already consumed a token the downstream step needs. If every guard must agree before acceptance, **record only after all guards have agreed**. Measured: a replay guard inserted the `jti` while checking it; a token then refused by a later step (stale roster) had already burned its `jti`, so re-presenting the same valid token after the roster refreshed failed as a replay for a call that never happened. Fix: separate `is_seen` (read-only check) from `claim` (accept-once write), and call `claim` last.
- **Runtime-only variable name errors after renaming a dict/var** — Renaming a module-level variable (e.g. `KNOWN_SERVICES` → `KNOWN_SENDERS`) leaves stale `Name` references in down-branch code paths. These pass `ast.parse` (the old name is still a syntactically valid Python identifier) but crash with `NameError` at runtime the first time that branch executes. Fix: after renaming any module-level variable, run `grep -n 'OLD_NAME' <file>` to catch every reference — don't trust that the linter caught them all. The linter is blind to this because the old name may still be assigned elsewhere, or the down-branch is enclosed in a `try/except Exception: pass` that swallows the error.
- **`ast.parse` passing is NOT a syntax check of your EDIT — it is a check of the file you left behind, and the LINT DIAGNOSTICS that arrive after a patch are the check that catches the rest.** Measured: a multi-line function was replaced by slicing the source between two index markers (`s[:s.index("def A")] + new + s[s.index("def B"):]`), and the slice landed mid-file and **deleted an unrelated module-level constant** that sat between the markers. `ast.parse` returned clean because the name was still *used* — a missing assignment is a runtime `NameError`, not a syntax error. The script then died on its first real run, two edits later, pointing at a constant nobody had touched. **Rule: after ANY scripted/automated multi-line rewrite, RUN the script (or `python3 -c "import ast,sys; …"` plus a `grep -n '^NAME'` for every global it references), never just parse it.** **Prefer a unique-anchor replace over index slicing** — `s.replace(OLD, NEW, 1)` with an `assert OLD in s` fails loudly when the anchor drifts; `s.index(...)` silently finds the wrong one. And when a rewrite touches a region containing a lookup table, verify the table still has a definition, not merely a use.
  - **Rewriting a TABLE of rows: splice LINE BY LINE, never regex the whole block.** A pattern like
    `\('key'\s*:\s*\()[^)]*\)` to retype a dict-of-tuples **eats the closing paren on any row that carries a
    trailing comment**, and the file still imports cleanly enough to look plausible until you run it. Measured: a
    ten-row table rewrite destroyed a row that ended in `),  # note`; the guard was `py_compile`, which passed
    because the damage was one row down. **The shape that survives:** keep a timestamped copy first, then split on
    `lines`, `re.match` the key at the START of each line, rebuild only that line, and **preserve everything after
    the last `)` verbatim** so comments survive — then `py_compile`, then re-read the table and confirm the count
    and every name.
  - **Prefer a line-oriented transform over a whole-block regex even when the regex looks simpler.** A block regex
    has no idea which delimiter belongs to which row; a line that starts with the key you are editing is
    unambiguous, and the diff is reviewable row by row instead of one opaque blob.
  - **Read the editor's diagnostics — a red one is a real defect, not background noise.** Three patch hazards, all caught by the checker and none by intent: (1) replacing a line that was the **opening line of a docstring** leaves the body as bare code → `SyntaxError: invalid character '⚠'` at the emoji five lines down; (2) a patch written with typographic punctuation can insert a **smart quote inside an f-string** → `SyntaxError: invalid character '”'`, invisible because `”` and `"` look identical in a diff; (3) a module-level constant referenced under a near-miss name (`_PREFIXED` vs `PREFIXED`) **compiles clean and raises `NameError` on first use**. **After every patch: read the returned diagnostics block, and never dismiss a lint error because the file "was already like that" — check whether your edit created it.** A patch tool that reports `lint: ok` is reporting on the file it just wrote; a patch that reports one error is telling you the deploy would have failed.
  - **A file with TWO `def main()` blocks compiles and parses cleanly.** Python simply binds the second; `py_compile` returns 0 while the first copy sits there as dead code with an orphaned tail. Measured: a run of targeted patches left a duplicate `main()` in a 395-line script, the compile check printed `COMPILE-OK`, and the script then died at runtime on a `NameError` from the orphaned half. **After a scripted rewrite, compare STRUCTURAL COUNTS against expectation** (`grep -c '^def main'`, `grep -n '^def '`) — a count that rose by one is the tell. **When a patch loop has already produced duplicate definitions, stop patching**: slice at the last known-good header, rebuild the body once, then execute it. Repeated patching on a corrupted region is how one small edit becomes a rewrite.
  - **A helper's PARAMETER LIST and its BODY can disagree, and no parser checks that for you.** Measured: a
    probe was edited to `def probe(key, model)` while its body still interpolated a different free name; the
    `NameError` was raised *inside an error handler* whose own message read *"could not read <external thing>"* —
    so the first diagnosis was a broken rail, and the rail was fine. **When any gate says it could not read
    something, read the exception TYPE before the noun.** `NameError` / `AttributeError` inside a "could not
    read" message is a code defect wearing a transport costume; debugging the network will never find it.
    After changing a signature, print the definition AND the body together (`grep -n -A12 'def <name>'`) — a
    renamed parameter and the old free name it replaced look identical in a diff.
  - **Never pass a long or punctuated argument through a shell string.** A ~2 KB `hermes cron edit --prompt '<prose>'` run through `bash -c` died with `syntax error near unexpected token '('` and `unrecognized arguments: …` — parentheses in the payload were evaluated as shell syntax and the argument was split on whitespace. A *truncated* prompt is the worse outcome: half the instructions land and nothing errors. **Invoke the CLI as an argv list** (`subprocess.run([hermes_bin, '-p', profile, 'cron', 'edit', '--prompt', prompt, job_id])`) and believe the tool's own confirmation line (`Updated job: <id>`) plus a re-read of the stored value, not the absence of an exception.
- **Persistence verification:** `cat` each modified file — does content match expectations? `git diff --stat` — verify changed files list matches what was modified
- **Karpathy Gate:** If something seems wrong, stop and name the confusion

### Phase 4: FINISH
- Run full test suite
- Commit and push
- Verify deployment (curl the URL, check the output)

### Phase 5: VERIFY (mandatory after every action)
**"Done" means verified, not declared.** Before declaring any task complete:
```bash
# File persistence
ls -la <file_path>
cat <file_path> | head -20

# Git persistence
git status
git diff --stat
git log -1 --oneline

# Deployment (static files behind CDN) — check BOTH origin and public URL
curl -s http://localhost/<path>          # Origin (nginx) — confirms file is served correctly
curl -s https://domain/<path>            # CDN — may be stale if Cloudflare caches
curl -s https://domain/<path> | grep -c "expected content"  # Content check, not just HTTP status
```
**⚠️ CDN verification gap:** An HTTP 200 from `curl https://domain/path` does NOT mean your new content is live. If Cloudflare (or any CDN) has a cached version of the old page, it returns the cached response even after nginx serves the updated file. The status code is correct but the content is wrong. Always:
1. Verify locally first (`http://localhost/path`) — confirms nginx + filesystem are correct
2. Then verify via CDN (`https://domain/path`) — but do a *content check*, not just a status check
3. If CDN is stale, you need to either:
   - Purge the Cloudflare cache (dashboard or API)
   - Remove any Worker route that intercepts the path on the root domain
   - Add a cache-busting query param (`?v=<timestamp>`)
4. File size comparison: if `curl -s https://domain/path | wc -c` differs significantly from the local file size, CDN is serving a different version (compressed or cached) — investigate.
- **Karpathy Gate:** If something seems wrong, stop and name the confusion

### When the deploy needs a restart only the USER can perform, verify on a SCRATCH INSTANCE first

**A change gated on `docker restart` / a host command is not a reason to hand back unverified work.** Run the new
code beside the live process on a spare port, read ITS output, kill it — then ask for the restart with the answer
already known.

```bash
# same files, different port, no deploy — the code the container will run
python3 -c "import os,uvicorn,importlib.util as u; os.environ['PORT']='8899';\
 s=u.spec_from_file_location('srv','server.py'); m=u.module_from_spec(s); s.loader.exec_module(m);\
 uvicorn.run(m.app, host='127.0.0.1', port=8899, log_level='error')"
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8899/status   # then read its OWN responses
```

- **Verify on a route computed IN-PROCESS.** A route that proxies to a backend will answer `503` from a scratch
  instance in a different network namespace — **that refusal is the guard working, not a failure**, but it means a
  proxy route's *content* cannot be proven this way while its *metadata and challenge shape* can.
- **Kill it and prove the port is closed** (`curl` → `000`) before moving on. A stray listener on a spare port is
  the kind of leftover that shadows a later test.
- **Then say what the restart will change, in one line.** "The metadata is read at import; this restart is the
  only step left, and I have already read the new challenge from the new code" is a complete handoff.
- **⚠️ Give the user ONE copy-pasteable command, alone in the message.** He may be driving from a phone between
  other work; a command buried in prose does not get run. **Then verify by re-probing the live surface yourself** —
  "I ran it" is a report, and the served bytes are the proof. (This also means a phone can ship a change: prepare
  it, hand over one line, verify the result.)
## Pre-Publish Audit Checklist

Run through **Kimi K2.7-code** (Ollama Cloud) before pushing to public repos:

### 1. Hardcoded Secrets
- [ ] Any hardcoded API keys, tokens, or passwords?
- [ ] Any wallet addresses (0x...) that shouldn't be there?
- [ ] Any personal names, emails, usernames?
- [ ] Any absolute paths (/root/, /home/, /Users/)?

### 2. Security
- [ ] API keys read from env vars, not hardcoded?
- [ ] Error messages sanitized (no raw exception leak)?
- [ ] Input validation present (regex, bounds, charset)?
- [ ] Startup failure if required config missing?

### 3. Code Quality
- [ ] Syntax errors checked?
- [ ] Proper HTTP client management (shared, not per-call)?
- [ ] Resources cleaned up in `finally` blocks?
- [ ] Unused imports removed?
- [ ] Type annotations complete?

### 4. Open-Source Readiness
- [ ] LICENSE file present (MIT)?
- [ ] README with install + config instructions?
- [ ] `.gitignore` excludes `__pycache__`, `.env`, `.venv/`?
- [ ] `.env.example` with placeholder values (no real secrets)?

## Anti-Temptation Rules

1. **No building beyond the plan** — If it's not in the plan, it doesn't get built
2. **Build easy to hard** — Quick wins first, they build momentum
3. **No optimizing before it works** — Make it work, then make it fast
4. **No refactoring without tests** — If there's no test, you can't refactor
5. **No skipping audit** — Every build gets a **Sr** pass (Kimi K2.7-code) before moving on
6. **No "just one more feature"** — Scope creep kills submissions
7. **No silent assumptions** — State what you're assuming in the log and keep going
   > The trailing "or ask" was removed on Jordan's directive (Sep 21, 2026). It sat there as
   > written permission to stop, and it produced ask-creep: 50 questions where the answer was
   > already obvious. An assumption is not a question.
8. **No drive-by improvements** — Touch only what you must
9. **No declaring done without proof** — Verify persistence before stopping

## Bug Discovery — Fix It, Do Not Ask (Jordan, Sep 21 2026)

> *"A lot of times we find stopping points pretty often and instead of just continuing through
> I'll be asked 50 questions to fix it… if we're actively doing stuff and you'll say 'hey, I
> discovered this bug, do you want me to go ahead and patch that?' — by the fall, we should
> already go ahead and do that."*

**When you find a bug while working, fix it. Then report what you fixed.**

Discovering a defect *inside work already in scope* is not a new decision — it is the work.
Do not stop to ask permission to do the thing you were already sent to do.

**What this looks like in practice:**
- Find it → fix it → verify the fix → **log it** (what broke, what you changed, the proof) → next item.
- The report is the deliverable. "I found X, fixed it as Y, verified by Z" — not "I found X, want me to fix it?"
- An honest blocker still gets reported. But a *bug you can fix* is not a blocker.

**Where planning DOES live** (and this is the distinction Jordan drew):
- **Build queue / Jordan's list / pending** — for bigger projects, plans, things needing his call.
- **Active work** — bugs found in flight get fixed in flight.
Planning is deliberate. Working is not.

**Stop and ask only for:** money movement · a public release · a legal/account/platform action ·
an approval gate Jordan explicitly owns · a hard blocker with no path forward.
Everything else: decide, act, log the assumption, continue.

---

## ⚠️ A GATE THAT READS A FILE A HUMAN MUST REFRESH IS NOT A GATE (2026-11-01)

**Proven on the x402 backend restore.** Fifteen routes were selling with no backend.
The fix added a readiness gate that refused them — correct. **But the first version
read a state file regenerated by hand, and that reintroduced the same defect at one
remove:**

- the gateway's `/opt/data` was a **Docker volume**, not the host tree — so
  host-written state landed on a **different filesystem** than the gateway read;
- a host reboot could kill the backends while the file still said `READY`, so **the
  gateway would keep advertising a dead port.**

**A file kept in sync with reality by a human will be stale, and it fails silently
in the permissive direction — which is the worst direction.**

**The rule:** when a check can ask the system directly, **ask the system**. Prefer
a **live probe with a short TTL cache** over a materialized snapshot of the same
fact. Loopback is cheap; a stale `READY` is not.

**When a file really is needed** (no reachable vantage, expensive probe, remote
system), then: put it where **both reader and writer resolve the same path by
construction** (a path relative to a bind-mounted file, not two configured paths
that can drift), and give the value a **TTL** so staleness is bounded rather than
unbounded.

**And keep the failed mechanism as a fallback, not a deletion.** An escape hatch
that still works is how you diagnose a broken primary. Removing a working path while
fixing a different one costs you that.

**The test:** *"if this source of truth goes stale, does the system fail closed or
open?"* A gate that fails **open** when stale is not a gate.

### ⚠️ The same defect wearing an allowlist: an exemption with no expiry

The stale-`READY`-file version above is one shape. The other is an **out-of-service allowlist**: a
monitor that holds a dict of "known-down, do not alert" entries.

**Measured:** a backend-liveness job ran every four hours for a night and reported `silent — empty
output` on every run. It was **correct every time**. Three routes were down, and all three were in
its `OUT_OF_SERVICE` dict, written months-to-days earlier with the reason *"router not started"*.
The router had never been started at all — a service that was never started is a hole, not a
decision.

**The rule:**

> **Every allowlist entry MUST carry an OWNER and an EXPIRY. Past its expiry it alerts like any
> other fault.** A permanent exemption is a blindfold with a written note.

**Why it fails silently:** the list only grows. Each addition is locally reasonable ("we know about
that one, stop nagging"), and the aggregate is a monitor that cannot report the exact class of
outage it was built for. **A keyword match is not a fact** — the entry says "not started", and
nobody re-reads whether not-started was ever true or ever meant to be permanent.

**Two mechanical checks that catch it:**

1. **Diff the excuse list against the live failure set.** For every entry, ask *when was this
   written, by whom, and what would have to be true to remove it?* No answer → delete the entry and
   let it alert.
2. **Ask what the entry SUPPRESSES, not what it declares.** An entry naming three routes suppresses
   three routes forever; if one of them is load-bearing, the monitor has been off for that service
   since the day the line was typed.

**Corollary — "down, advertised, excused" is not a state.** For each failing component the only
outcomes are **RESTORE · REBUILD · REMOVE**. A component that is dead, still advertised, and
carries a written excuse is the configuration version of the false-value family.

## ⚠️ INVESTIGATE THE ROADBLOCK — a blocker is a lead, not just an obstacle (Jordan, 2026-11-01)

> *"Essentially, we may need to add a new rule for develop and verify. Now that you have intent and
> you know what you're looking for, anytime you hit a roadblock, the roadblock needs to be
> investigated alongside what you're doing because you may discover other bugs or other fixes for
> other things."*

**The rule above says fix bugs found in scope. This is the sibling rule for what you CANNOT fix.**

A **roadblock** differs from a bug: the obstacle lies outside the work you were sent to do — a
missing permission, a tool that lies, a rail that returns nothing, a file that cannot be written.
**The instinct is to route around it and get back to the task. That instinct throws away the most
valuable finding available.**

**Investigate the roadblock in parallel with the work. It is the cheapest bug-audit you will ever
get, because you are already standing in the failure.**

### Why it pays (measured, one session)

Four roadblocks hit during unrelated tasks; each investigation found something bigger than the task:

| roadblock | what routing around it would have missed |
|---|---|
| `ob sync` exits 0 without syncing | four seats silently drifting; a cron trusting the code would report success forever |
| GitHub answers HTTP/2 with LF | the secret audit reporting **"0 repos · 0 files · all clean"** while the token returned 143 |
| `hermes config set` accepts any string | `provider: nous` — invalid — inherited by every seat, breaking **every voice note silently** |
| one model returned 0 chars | **every reasoning model on the rail** does it; six non-reasoning ones answer fine |

**None of these were the task. All four cost less to find than to rediscover later — and three were
actively producing wrong answers the whole time.**

### What "investigate" means — four steps, in order

1. **Name what blocked you, precisely.** Not "it failed" — *"exit 0 while doing nothing"*, *"HTTP 200
   with an empty body"*, *"the config accepted a value the engine cannot resolve."* **The wording of
   the block is usually the name of the bug.**
2. **Ask whether it is OURS or the world's.** Wrong path, wrong key, wrong assumption → ours, fix it
   now. Genuinely external (a permission, a vendor, a missing credential) → record and route.
3. **Find the BLAST RADIUS — this is the part that finds the other bugs.** *Who else reads this?*
   `grep` for the same call, the same path, the same assumed behaviour. **A roadblock on one code
   path is a signal about every path shaped like it.** The LF-split bug was not one audit's problem;
   it was every script that parses a GitHub response.
4. **Prove the failure direction.** Feed it the input that must be rejected and watch the *right*
   thing happen. A guard never tested in its blocking direction is decoration.

### Then decide, and never just "work around" silently

| finding | action |
|---|---|
| a bug in our code | **fix it now**, log it (rule above) |
| a bug in our *assumption* | fix the assumption and every place it is encoded |
| an external limit | **record it** so the next attempt does not pay twice |
| a lie from a tool we trust | **fix the tool or stop trusting its output** — never hand-tune around it |

**Record roadblocks in a durable place, not in the conversation.** A roadblock rediscovered is a
roadblock paid for twice. Keep a dated roadblock file in HQ with: what blocked it, what unblocks it,
and whether it is **fixed / worked-around / open**.

### ⚠️ The one thing this must NOT become

**An investigation that never ends.** The rule is *investigate alongside the work*, not *abandon the
work to chase the blocker*. **Time-box it: name the blocker, find who else is affected, try one fix,
record the rest.** A roadblock you understand and have written down is a win — even if it stays open.


> *"Whenever we're fixing something, we want to look for permanent solutions to the bugs and the problems
> that come up. So instead of fixing something in its temporary, we want to verify that it's a permanent
> solution. That should be how it is going forward — for everybody and all the groups."*

**Fleet-wide. Every seat, every fix.** A fix is not done when the symptom stops; it is done when the defect
**cannot recur** — and you can say **why**.

### The case that produced the rule (Treasury, Jun 30 2026)

A monitor reported the wrong LP shape and a stale price. **Fixing the numbers would have been the temporary
fix, and it would have come back the same day** — because the defect was not the numbers:

- **three** copies of `.lfj-aae-config.json` existed with different data (one correct, **two stale**);
- `HERMES_HOME` resolves differently in cron than in a shell, so scripts silently read a **stale** copy;
- **two** cron jobs wrote the same dashboard JSON, so a correct write was **overwritten seconds later**.

The permanent fix was `lp-monitor-v2.py`: hardcode the one true path, read only from config + live API, and
**delete the shared intermediate file entirely** so there is nothing left to race over. The old jobs were
**removed, not patched.** *"File locks and read-only flags are band-aids; removing the dependency is the
cure."*

### The test — run this before calling ANY fix done

| Temporary (a band-aid) | Permanent (the fix) |
|---|---|
| Corrects the value | Removes the path that produced it |
| Adds a lock / retry / flag around the race | **Removes the shared dependency** so no race exists |
| Patches the one call site reported | Patches the **transform**, then greps for the transform |
| Syncs the copies | **Deletes the stale copies — they ARE the bug** |
| Works in this shell, this context | Works in cron, in a shell, and **after a restart** |
| "Fixed" | "Fixed, **and here is why it cannot recur**" |

**The highest-value move is almost always: delete the duplicate.** A second copy is not a backup when
nobody knows which is authoritative — it is a coin-flip the code takes on every single run.

### Prove it, do not assert it

1. **State the class, not the instance.** *"This was not one wrong number; it was N readers of one file."*
2. **Kill the recurrence path, then search for the shape again** — `grep` the old read, the old path, the
   old helper. A fix one call site short of the end is the normal failure.
3. **Guard it.** Add a regression check to the selftest so the defect fails **loudly** if it returns —
   that is the step that converts "fixed" into "cannot silently recur."
4. **Verify BOTH directions** — it fires when it should, and stays silent when it shouldn't.
5. **Ask what a restart / update / redeploy would undo.** A fix that evaporates on the next deploy (an
   uncommitted live patch, or a vault-only edit while cron runs the *deployed* copy) is temporary no matter
   how correct it looks today.
6. **Say "permanent" only with the reason attached.** "Permanent" is a claim, and an unfalsifiable claim is
   the exact class this pipeline exists to catch. Write *why* it cannot come back — **if you cannot write
   that sentence, you have a temporary fix; label it one.**

**Boundary — what this must NOT be read as.** Permanence is a property of the *fix*, not a licence to
rebuild. Rewriting a working subsystem to make it "more permanent" is scope creep (anti-temptation rule 1).
The only question is *"will this defect return?"* — never *"could this be nicer?"*

## The Permanent-Fix Rule — fix the CLASS, not the instance (Jordan, Sep 23 2026)

> *"Whenever we're fixing something, we want to look for permanent solutions to the bugs and the problems
> that come up. So instead of fixing something in its temporary, we want to verify that it's a permanent
> solution. That should be how it is going forward — for everybody and all the groups."*

**Fleet-wide. Every seat, every fix.** A fix is not done when the symptom stops; it is done when the defect
**cannot recur** — and you can say **why**.

### The case that produced the rule (Treasury, Jun 30 2026)

A monitor reported the wrong LP shape and a stale price. **Fixing the numbers would have been the temporary
fix, and it would have come back the same day** — because the defect was not the numbers:

- **three** copies of `.lfj-aae-config.json` existed with different data (one correct, **two stale**);
- `HERMES_HOME` resolves differently in cron than in a shell, so scripts silently read a **stale** copy;
- **two** cron jobs wrote the same dashboard JSON, so a correct write was **overwritten seconds later**.

The permanent fix was `lp-monitor-v2.py`: hardcode the one true path, read only from config + live API, and
**delete the shared intermediate file entirely** so there is nothing left to race over. The old jobs were
**removed, not patched.** *"File locks and read-only flags are band-aids; removing the dependency is the
cure."*

### The test — run this before calling ANY fix done

| Temporary (a band-aid) | Permanent (the fix) |
|---|---|
| Corrects the value | Removes the path that produced it |
| Adds a lock / retry / flag around the race | **Removes the shared dependency** so no race exists |
| Patches the one call site reported | Patches the **transform**, then greps for the transform |
| Syncs the copies | **Deletes the stale copies — they ARE the bug** |
| Works in this shell, this context | Works in cron, in a shell, and **after a restart** |
| "Fixed" | "Fixed, **and here is why it cannot recur**" |

**The highest-value move is almost always: delete the duplicate.** A second copy is not a backup when
nobody knows which is authoritative — it is a coin-flip the code takes on every single run.

### Prove it, do not assert it

1. **State the class, not the instance.** *"This was not one wrong number; it was N readers of one file."*
2. **Kill the recurrence path, then search for the shape again** — `grep` the old read, the old path, the
   old helper. A fix one call site short of the end is the normal failure.
3. **Guard it.** Add a regression check to the selftest so the defect fails **loudly** if it returns —
   that is the step that converts "fixed" into "cannot silently recur."
4. **Verify BOTH directions** — it fires when it should, and stays silent when it shouldn't.
5. **Ask what a restart / update / redeploy would undo.** A fix that evaporates on the next deploy (an
   uncommitted live patch, or a vault-only edit while cron runs the *deployed* copy) is temporary no matter
   how correct it looks today.
6. **Say "permanent" only with the reason attached.** "Permanent" is a claim, and an unfalsifiable claim is
   the exact class this pipeline exists to catch. Write *why* it cannot come back — **if you cannot write
   that sentence, you have a temporary fix; label it one.**

**Boundary — what this must NOT be read as.** Permanence is a property of the *fix*, not a licence to
rebuild. Rewriting a working subsystem to make it "more permanent" is scope creep (anti-temptation rule 1).
The only question is *"will this defect return?"* — never *"could this be nicer?"*

## The Jr/Sr Default (fleet directive, Sep 21 2026)

**Every agent, on any build — not a Labs speciality.**

```
Jr  (DeepSeek V4 Flash)   write it, make it work, pass the tests      ~$0
Sr  (Kimi K2.7-code)      read it back, hunt what Jr cannot see       spot-check
```

**The division of labour is the point.** Jr produces; Sr distrusts. **The author of code is the
worst person to audit it** — they check it against what they *meant*, not what they *wrote*.
Sr reads it cold and asks: *"what would make this print a confident wrong answer?"*

### What Sr is for — and it is not style

Not formatting, not preferences. **Silent wrongness.** Every item below passes a linter and a
happy-path test, and every one produced a wrong answer in a single night:

| Bug | What it printed |
|---|---|
| bare `except: return {}` | an entire balance block vanished — looked like "nothing to report" |
| `0x`-prefixed topic filter | **"no rebalances"** with total confidence, having matched nothing ever |
| action fn with no expiry check | a **10-day-old** stand-down, reported as current, daily |
| hard-coded `int(21.33 * 1e6)` | the **wrong amount** sent, irreversibly |
| missing `positionUsd` after a rewrite | **`$0.00/day`** beside a 163% APR |
| stale "CONFIRMED" in a buy list | **"ZERO COQ pools above $50K"** — there was a $705K pool |

**Six bugs. Not one raised an error.**

### The checklist Sr runs

- **Never swallow an exception bare.** A swallowed error is a false negative that reads as a fact.
- **Empty because nothing happened, or empty because the check failed?** The output must say which.
  "Unknown" is valid. "Zero" is not, unless measured.
- **Verify the refusing direction.** A boundary never tested in the direction it blocks is not
  known to work.
- **Hard-coded value in an executing path?** Make it required, or give it an expiry that is checked.
- **After rewriting OR EXTENDING a function, diff its RETURN SHAPE.** Callers depend on fields that vanish
  silently, and a new branch is a new return. **A path that means "reject" must return the type its caller
  already unpacks** — `None`, an empty list, `(False, reason)` — never a bare reason string, because the
  string was written for a human to read and the caller was written to unpack something else. Measured: a
  gate returning a human-readable reason was added to a scorer whose reject path returned `None`; the caller
  unpacked it as a pair and the entrypoint died on `ValueError: too many values to unpack`, producing **no
  output at all** rather than a wrong one — which reads to the user as "nothing new this week". **A reason
  nobody can print is worth less than a row the user can read and argue with: put the gate where the reason
  is DISPLAYED, not where the value is computed.** And prove it by running the composed entrypoint — a
  direct call to the function you just edited passes happily while every real caller breaks.
- **After a fix, re-audit — and re-test what the OLD code gave you for free.** A fix for a bug in a
  text/data transformer silently drops behaviour the previous implementation had. Proven: replacing
  `str.title()` with a custom title-caser fixed substring corruption (`solana`→`SOLana`) but lost
  hyphen-boundary casing (`On-Demand`→`On-demand`) — a live regression in the same function, invisible
  because every check counted fields instead of reading text. Ask: *what did the thing I replaced do
  that I am no longer doing?*
- **A single audit pass is not an audit.** Round 1 found an original bug; round 2 found the regression
  introduced by fixing round 1. Audit the FIX, not just the original change.
- **Fixing a bug class one call site short of the end is the normal failure.** When an audit reports
  "`x or 0` on fields A, B, C", the fix belongs to the COERCION, not to A, B, C — otherwise the same
  bug survives on the neighbouring fields and re-audit finds it. Proven: a missing-field→0 fix landed on
  the four reported keys and left three adjacent ones bare; a later round found the *optional-field*
  helper doing the same thing, which also re-opened a crash class an earlier fix had closed. Two rounds
  lost to fixing call sites instead of the pattern. **Rule: fix the transform, then grep for the
  transform.**
- **A cross-check whose emitter does not exist is not a cross-check.** Adding a "wallet scanned must
  equal wallet named" guard in the parent is inert if the child never emits the scanned address —
  `.get()` returns None, the comparison is skipped, and the check can never fail while looking present
  in the code. After adding any guard, confirm the INPUT it reads is actually produced, and prove the
  guard fires by feeding it a mismatch. Same family: a tolerance scaled to the WRONG quantity (1% of
  total capital to compare two valuations of the DEPLOYED amount) passes almost any real divergence.
- **An EMPTY container makes every per-key validator pass — fail on the empty container, not just on the
  bad value.** A validator shaped `lookup(key) -> reason_or_""` returns `""` for **every** key when its
  source is empty, so the guard reports "nothing wrong" for the whole route and the next step prices,
  charges, or acts on definitions nobody loaded. Measured: a manifest was read from a hardcoded host path
  that did not exist where the process ran; the reader swallowed `FileNotFoundError`, the per-service
  lookup returned `None`, the path validator short-circuited to `""`, and a **placeholder/template route
  received a fully payable challenge** — charge-before-validate, on a route that could never deliver.
  **Fix at the container:** if the loaded definition set is empty, refuse the whole request and print a
  FATAL at startup. **Then prove it the only way that counts:** run the same probe against an empty tree
  and watch it go RED. A guard whose only tested state is "everything loads" is decoration.
- **When you scale a threshold, check the direction and then check the OUTPUT.** A bin-step scaling
  written as `30*step/10` instead of `30/step` produced a window that swallowed the entire position;
  the code ran clean and nothing errored. The tell was the metric jumping 35.8% → 98.8%. A number that
  suddenly reads "everything is fine" is a signal to inspect the window, not a result to report.
- **Two independent valuations that agree are worth more than one confident number.** A "ledger says X"
  and a "chain scan says X" that reconcile to <0.1% closed a weeks-old "the ledger under-reports by 6.7%"
  ticket — the gap was a decode artifact, not a real discrepancy. Keep the cross-check LIVE (emit the
  delta) rather than resolving it once: a divergence alarm that never reaches a human is not an alarm,
  and a "we disagree" result must have its own display branch — otherwise it falls through to
  "unavailable" and a check that ran and FAILED reports as a check that did not run.
- **"Found a value" is not "found a working value."** A config/credential reader that returns the first
  match will happily return a dead one. Probe the candidate (auth call, parse, exec) and assert the
  outcome before using it. Proven: a dead 13-char key in a shared `.env` shadowed the live 57-char key in
  the profile `.env` for any first-match reader — a 401 with no error at the point of selection.
- **After a patch, re-read the file and re-run the output.** A patch that didn't apply looks
  identical to one that worked.
- **A redacted rendering is not the source — check the BYTES before "fixing" code that reads wrong.**
  Tool output that shows file contents redacts credential-shaped spans, so a line that is **correct on
  disk** can *display* as broken in the transcript. Measured: a `Bearer {token}` f-string rendered as
  `Bearer ***`, and an edit was attempted against text that was never in the file — the file had been
  right the whole time. Confirm with bytes, not a rendering: `open(p,'rb').read()[i:i+40]` around the
  match, or a byte-level `grep`, then decide. **Treat `***` in display as UNKNOWN, never as evidence** —
  and apply the same rule in the other direction before you conclude a secret is absent.
- **When you change a value's CONTENT, keep its TYPE.** Concretising a value is not the same as
  re-typing it. Proven 2026-09-22: a helper that replaced a RELATIVE path with a concrete one returned
  an ABSOLUTE url; every consumer of that field concatenates a base, so a verifier received
  `https://api.gentechlabs.nethttps://api.gentechlabs.net/v1/...` and 7 services that had passed one
  run earlier were rejected (DISCOVERY READINESS 14/14 -> 7 rejects). Assert the shape, not just the
  absence of the thing you removed — "no template remains" passes happily on a broken URL.
- **A rail can be PERMANENTLY dead because it requires an input its source cannot provide.** The
  worst member of the false-value family, because the refusal is CORRECT and therefore looks like
  good engineering. Proven 2026-09-22: the regime classifier demanded 7d momentum before it would
  name a regime ("a missing input is not a flat market" — right call). It read that momentum from
  DexScreener's `pair.priceChange.h7d`, and **DexScreener does not publish h7d** — it returns
  exactly `[m5,h1,h6,h24]`, verified live on both pools. So momentum was `None` on EVERY tick,
  forever: the classifier refused correctly every time, the regime sat UNKNOWN, and downstream
  `REGIME_SHAPE.get(unknown, "CURVE")` silently returned CURVE while a tilt map silently returned
  its neutral fallback. **A dead rail that looked calm instead of broken.** Rule: for every field a
  component REQUIRES, verify the producer actually emits it — do not infer it from the field's name
  appearing in a schema or a sibling. Then check the consuming lookup's DEFAULT: `.get(key, default)`
  on a decision table converts "we don't know" into "act as if the common case", which is how a
  broken classifier wears a working disguise. An UNKNOWN that maps to a safe posture is fine; an
  UNKNOWN that maps to the DEFAULT without saying so is a silent wrong answer.
- **A provenance label can be a hardcoded lie.** A dict field named `source` was literally
  `"source": "coingecko-btc"` — a constant in the writer — while the data came from a DexScreener
  pool read and (after the fix) a CoinGecko AVAX series. It read as fact, it persisted into the
  state file, and it sent a debugging session chasing BTC for an AVAX position. When a value's
  origin is knowable, DERIVE the label from the code path that fetched it (a `momentum_source`
  variable set at each branch), never type it once in the result dict. A stale label is worse than
  no label, because it is confidently wrong.
- **Never learn a value by scraping the SOURCE TEXT of the script that computes it.** Recurring
  (3rd occurrence, 2026-09-22): a reader regexed `lfj-curve-deploy.sh` for `BID_NEAR`/`ASK_FAR`.
  When that shell was changed to DERIVE those from a shared table and PRINT them, the numeric regex
  matched a Python expression instead, found no number, and the plan degraded to `"legs UNREADABLE
  — do not trust this plan"` 144x/day. A reader coupled to the *text* of its producer breaks the
  moment the producer is refactored, and it breaks SILENTLY. Import the shared module and call it.
  If a value must cross a language boundary, have the producer emit it as data (JSON/env), not as
  source text to be pattern-matched.
- **A monitor can be structurally blind to the EXACT condition it exists to catch — and it will
  look healthy. FEED THE CLASSIFIER THE FAILURE OUTPUT; do not read the code path.** Proven
  2026-09-23: both treasuries sat EMPTY all night and the Position Watchdog never spoke. The
  re-center hit its flat-book branch, printed `"nothing to withdraw — flat"`, and **returned before
  the idle and efficiency checks** — so it exited `rc=0` carrying text matching none of the
  classifier's patterns (`IDLE CAPITAL|DRIFTED|OUT OF RANGE|REBALANCE NOW|⚠️`). Feeding the real
  output to the classifier gave `ACTIONED=0 MATERIAL=0 ERROR=0` — silence on the one event the
  monitor was built for. An early return is the usual culprit: it is upstream of every check that
  could have flagged the condition, and it reads as harmless tidiness. Also note the inverse trap:
  the same watchdog gate spoke for a **routine** action at 3am while staying quiet for a **material**
  one — the urgency category was inverted. **Test rule: enumerate the conditions the monitor must
  fire on, synthesize each one's output, and assert the classifier fires. A monitor never tested in
  its firing direction is decoration.** Corollary: an hour mask on a cron suppresses the whole RUN,
  not just delivery — masking 'quiet hours' this way silently blinds monitoring for those hours.

### If Sr is unreachable

Say so, label the work **unaudited**, and do not call it verified. **An unaudited build is a
known state; an unaudited build called verified is how a bug ships.**

### A missing INSTRUMENT is not a weaker claim — install it, then measure (the sibling rule)

**"The tool isn't on this box" is a setup fact, not a reason to downgrade the proof.** The temptation is to ship
`validate: not run — terraform absent` in the artifact and call the work done. That turns a five-minute install
into a permanently weaker claim, and the artifact reader cannot tell the difference between *not exercised* and
*does not work*.

**Reach for a user-writable install before you ever write "untested":**

```bash
mkdir -p "$HOME/bin"
curl -sL -o /tmp/x.zip "https://releases.hashicorp.com/terraform/<ver>/terraform_<ver>_linux_amd64.zip"
python3 -c "import zipfile;zipfile.ZipFile('/tmp/x.zip').extractall('$HOME/bin')"   # when `unzip` is absent
chmod +x "$HOME/bin/terraform" && "$HOME/bin/terraform" validate -no-color
```

Static release binaries need no root — `unzip` is the usual absentee, and Python's `zipfile` covers it.

- **Then quote the real verdict** (`"Success! The configuration is valid."`), not a description of the tool.
- **If it genuinely cannot be installed, say `UNVERIFIED — <reason>`**, and name what would verify it. The
distinction that must survive: *I could not run it* is honest; *it passes* on an unrun check is the bug class
this whole skill exists to catch.
- **Never let the absence hide in a silent pass** — a step skipped for lack of a binary must print its absence in
the same output a reader consumes.

### Calling Sr directly over HTTP (the gotchas)

The `opencode-go` OpenAI-compatible endpoint (`https://opencode.ai/zen/go/v1/chat/completions`)
needs **two** things beyond `Authorization` + `Content-Type`, and both fail in confusing ways:

1. **`x-opencode-session: <uuid>` is REQUIRED.** Without it: `HTTP 400`
   `{"error":{"type":"MissingSessionID"...}}` — which reads like an auth/model problem and is not.
2. **The answer may be in `message.reasoning_content`, not `message.content`.** Kimi is a
   reasoning model: `content` comes back `null`/empty and the real analysis sits in
   `reasoning_content`. Reading only `content` yields a 0-char "successful" audit — a silent
   false green. Read `content or reasoning_content`, and set `max_tokens` generously (6000+).

Send a browser `User-Agent` too (Cloudflare bans bare client signatures).

3. **⚠️ Do NOT send `temperature` to a kimi model on this rail.** Measured 2026-10-31:
   any value but 1 is refused — `{"error":{"type":"invalid_request_error","message":
   "Upstream request failed: [invalid_request_error] invalid temperature: only 1 is allowed"}}`
   — and it arrives as **HTTP 400**, which reads like a bad model name or a missing header and
   is neither. Omit the field entirely. **Diagnostic that settles it in one call:** send the
   smallest possible payload (`max_tokens:16`, content `"say OK"`) — if that returns 200 and
   your real call 400s, the fault is in your payload, not the rail or the model name.

**Never trust a 0-char audit as a pass.** An auditor that returned nothing did not clear the
work — treat empty output as unreachable and label the build unaudited.

### The bug class worth naming

**The false-value family** — a mechanism reporting success while doing nothing, or reporting a
number it cannot actually compute. **A green that cannot go red is not a signal.**

### Two probe failures that masquerade as findings

**① A probe blocked at the edge reads as "the endpoint is broken."**

Measured: a Python probe using bare `urllib` received **HTTP 403 Forbidden** from a Cloudflare-fronted
hostname that the same machine fetched **200** from with `curl`. The difference was the `User-Agent`
— `Python-urllib/3.x` is blocked, `curl/8.x` passes. The probe then reported *"COULD NOT READ the
manifest"*, which a reader correctly interprets as *the service is down*.

> **Any probe that talks to a hostname we do not control the edge of MUST send a real
> `User-Agent` and `Accept` header.** Otherwise "we were blocked" is indistinguishable from "it is
> broken", and the probe has manufactured a finding.

**Diagnostic in one step:** fetch the same URL twice — once with the probe's client, once with
`curl` — and compare. A 403/`curl 200` split is the edge, not the service. Then check whether the
failure message names the *transport* or the *content*: "could not read" is honest, "no data" is a
lie about a blocked request.

**② A rate above 100% is proof the classification is wrong — never a good day.**

Measured: the first run of a conversion metric printed **461%** and **468%** on two routes — more
served than quoted, which is arithmetically impossible. The cause was that a *collection-root*
endpoint returns **HTTP 200** with `{"collection_root": true, "payable": false}` when called
without its required parameter. Those 200s were counted as sales.

> **When a derived metric lands outside its own possible range, stop and fix the CLASSIFIER. Do not
> report the number and add a caveat.** An impossible value is the cheapest self-detecting bug there
> is, and a plausible-looking correction applied on top of a broken denominator buries it.

**How to catch it in the design:**

- **A 2xx is not a sale.** Enumerate what each status code means *for this route shape* before
  counting it: for parameterised routes, a 2xx on the **bare prefix** is a signpost (index, help,
  collection root), never consumption. Classify on **shape**, not status alone.
- **Keep the unclassified bucket visible.** Print signposts as their own column so they can never be
  silently absorbed into either numerator or denominator. A dropped bucket is a hidden lie.
- **A rate for a route that cannot serve prints `n/a`, never a number.** Quoting a price on a
  backend that is down manufactures demand that could never have converted.
- **State the denominator in the same line as the rate.** "0 of 5,492" cannot be misread; "0.0%"
  can.

### ③ A passing smoke test proves SOMETHING ran — never that the RIGHT thing ran

Switching a provider, endpoint, binary or config and then confirming with a happy-path call is the most common
false green there is: **the fallback answers for the thing you replaced, and the output looks exactly correct.**

Measured: a provider switch was verified per seat with `hermes -p <seat> -z "reply OK"`. Every seat returned `0`
and the exact text — **all of them served by the fallback provider**, because the new rail's key was missing from
each profile's own `.env`. The test result was compatible with success and with total failure.

> **Assert the ACTOR, not the output.** "It worked" is compatible with "it worked somewhere else." Read the actor
> from a log line that names it (`model=… provider=…`), or from a counter that exists ONLY on the target (that
> provider's own usage meter moving). If neither is available, the switch is unverified, not verified.

The general shape: any check that reads only the *result* cannot tell you *who produced it*. Name the actor in the
check itself, and when a second actor could satisfy the same assertion, that assertion is not a test.

### ④ Turning a refusal into a helpful response — assert the DANGEROUS FIELD is absent

When a guard stops rejecting and starts *correcting* (a 404 becomes a 402 saying "here is the call you meant"),
the obvious regression test — *"it is no longer a 404"* — **passes on the catastrophe.** The dangerous state is not
the old error; it is the new response being **actionable in the wrong way** — a price a client can pay against a
route that cannot deliver.

**Write the suite in both directions, in one run:**

| case | must be | must NOT be |
|---|---|---|
| the malformed / template input | the new helpful status | **payable** — no `accepts`/price block, nothing to settle |
| the well-formed input | still payable, unchanged | — |
| a retired route | still a hard "gone", never a challenge | payable |

And include one **negative harness**: run the same probe against a deliberately broken setup (an empty definition
set, no backing service, the fallback disabled) and require it to go RED. A guard whose only tested state is
"everything loads" is decoration.

### ⑤ A checker's THRESHOLD must come from the code that ENFORCES it — never from a display width

**A validator is only as right as the constant it compares against, and that constant is usually guessed.**
Measured: a skill audit was written with a **60-character description limit** and reported **145 healthy
skills as defects**. Sixty was the width of a **table cell** in the CLI's listing view (`_truncate(desc, 60)`),
not a rule; the loader's actual limit was **1024** (`MAX_DESCRIPTION_LENGTH`). Corrected, findings fell
**242 → 98**.

> **Read the limit off the code that REJECTS or TRUNCATES — the loader, the validator, the schema — not off the
> view that renders it, not off a doc, not off memory.** Then say where you got it, in the checker, as a comment.

**The tell is the same as the false-positive table below:** a brand-new checker reporting a large count on a
corpus you believe is healthy is **evidence against the checker** until each finding is triaged. **A checker's
first output is a test of the checker.**

**Corollary — filter the checker's own noise classes before reporting a count.** A path-existence check will
flag placeholders (`<name>`), globs, by-design markers (`DISK-MARKER-*`) and generic example paths
(`scripts/config.json`) equally with real missing tools. **Classify findings (missing-and-recoverable ·
by-design · genuinely dead) and report the classes separately** — an unclassified list of 55 looks like 55
breakages and buries the 7 that matter.

### ⑥ A COMMENT that promises behaviour the code does not implement is a defect with a note attached

**Prose next to code is a specification claim, and nothing parses it.** Measured: a router's comment stated that
two specific routes "are RETIRED and answer 410", while the set the code actually consulted did not contain them —
so those routes answered **404**. The comment was right about intent and the code was wrong, and the comment made
the gap invisible: a reader checking behaviour against the docstring would have concluded it worked.

> **When you read a comment that asserts a behaviour, EXERCISE that behaviour in the same pass.** Cheap, and it
turns documentation into a test. Where the claim is a *set membership* (the comment names what it covers), diff
the named set against the code's set — that diff is the defect, and it is one `grep` away.

## The AUDIT INTENT — what to look for

**An audit without a stated intent is not an audit, it is a look around.** Before any audit, write down the
**ONE question** it answers and **the number that answers it**. **No number, no audit.**

### The ten failure classes, each with the question that finds it

1. **The EXEMPTION / bypass audit — do this FIRST.** Every bypass is a hole. Ask what feeds it, and whether the
   action it permits can **CREATE the condition that justifies the next one**. *A leak lives in an exemption.*
2. **The TRIGGER audit** — which condition actually fired, not which rule the docs describe. **A category
   present in 100% of runs is a HEADER, not a cause.**
3. **The NECESSITY test** — for any "it does X too much", reconstruct **per event** whether the stated condition
   was met.
4. **The COST decomposition** — mechanism cost vs external change vs income, and **report the RATIO**.
5. **The READER audit** — a sample taken mid-rewrite is a **frame, not a state**; a write is verified by its
   **receipt**, not by a number read afterwards.
6. **The RESERVE / limit audit** — a limit must cover the operation's **full step count**; ask whether the
   guarantee comes from the **ORDER** (provision-then-spend) rather than the **SIZE** of the reserve.
7. **The CONSTANT-vs-MECHANISM test** — did we move a number, or change a mechanism? *A fix that has to be
   re-applied is evidence, not progress.*
8. **The RECORD audit** — does the record carry the values **at the moment of decision**? Is there a writer for
   every reader? Is the published number the number the system acts on?
9. **The BANNER-OVER-A-NO-OP class** — a confident success line over an action that did nothing. **Read the
   POST-STATE, never the banner.**
10. **The FALSE-VALUE family** — a failed or unreadable read printed as a real value, **especially as ZERO**.
    "Unknown" is valid; "zero" is not unless measured.

### The two rules that make it an audit rather than a walk

- **Prove the direction it should REFUSE.** A guard never tested in the direction it blocks is decoration.
- **Re-audit after the fix — round 2 finds the regression round 1 introduced.**

### The order

measure first → **exemption audit** → trigger audit → necessity + cost ratio → readers/record → fix in the
**canonical copy** (never a side copy a sync reverts) → syntax check → sync → **verify the deployed copy by
hash** → **watch one full cycle.**

### The case that produced this (Treasury, 2026-10-04)

A book lost ~$7/day; the question was *"is it the rebalances or the market?"* The answer came from the checklist,
not from opinion:

- **42 re-actions in 24h against a cap of 2 — and 0 of 41 justified by price** (median move **0.19%** against a
  **1.20%** band). The book was in range and earning the whole day.
- **Cause: an exemption.** An idle-capital trigger written `(>25%) OR (>= $10)` fired on **change the loop's own
  last rebuild left in the wallet** — and that trigger **bypassed the churn cap**. Rebuild → change → "idle" →
  rebuild, forever. **The cap was never broken; it was bypassed, so the budget was never consulted.**
- **The fix that did NOT work:** raising the gas floor $1.00 → $1.50 — *a number, not a mechanism* — and the
  same failure returned the same day (class 7, in action).
- **The rule broken while writing the tool meant to enforce it:** the new watcher read a state file from the
  wrong path, failed silently, and printed **`0 re-centers`** on books that ran **31** and **42** (class 10,
  exactly).

## Parallel Subagent Builds

When the build plan has **independent module groups** (e.g., engine + UI), delegate them to parallel subagents. Each subagent gets a self-contained prompt with exact file paths, API contracts, and acceptance criteria.

**When to parallelize:**
- Engine/logic and UI are independent
- Two unrelated features that share no code
- Test suite and implementation can be written simultaneously

**When NOT to parallelize:**
- Module B depends on Module A's internal implementation
- Shared state or configuration between modules
- Subagents would need to coordinate

- `scripts/pdf_text_probe.py` — **prove what a generated PDF literally SAYS**, by reading its own
  text layer with no external tools. *"A PDF renderer prints a success message, and a success
  message is not the document."* Catches two real failures: a render that **never read the input**
  (identical byte count to the previous render is the tell), and prose claims that are **not in the
  shipped file**. Usage: `pdf_text_probe.py FILE.pdf "phrase" [--absent "phrase"]`; exit 0 = every
  assertion held, 1 = failed, 2 = no text layer. **The same discipline as every other check here:
  assert on the artifact, never on the tool's own success message.**

## Prose is an artifact too — proofread what we SEND, not just what we build

**The same Jr/Sr split applies to a message as to a code file: one model drafts, a different model reads it
cold for claims the text cannot support.** A sentence can be perfectly spelled and still be a lie about our own
system, which is why a spellchecker is not the check.

**Run the DETERMINISTIC half first — it is free and a model's opinion is not:** any `0x…`/base58 address that
appears in none of our records · a URL on our own domain answering 000/404/410 · a claimed count compared
against the LIVE source (manifest, a real 402 body) rather than against memory · hedge words (*probably, should
be, we believe, hopefully*), each of which hides an unmeasured claim.

**The three tools (all in `/opt/data/scripts/`):** `prose-write.py` — writer drafts from a FACT BLOCK, reader
resolved at call time from the audit ladder (never hardcoded) · `proofread.py` — the model-free fact-checker,
`--selftest` proves both directions · `gh_compliance.py` — the façade every GitHub-touching cron imports
(`gh_get` delegating to the one guarded transport, `gh_write` requiring `allow_write=True`, `prose_gate()`).

**Give the writer a FACT BLOCK and forbid anything outside it**, with an explicit `DO NOT CLAIM:` line. Without
one, the writer invents numbers that sound like ours; with one, the worst it can do is word our own measurements
badly.

**The failure every naive check passes is the NON-REPLY** — *"we have not encountered that problem, that is all
I can report"*. True, on-topic, useless, and it costs credibility. Rule: a message whose substance is "we have
not seen this" is a FAIL, not a pass; the writer must emit `NO REPLY` instead.

**Never template one remedy across every draft** — the reply to a schema question then carries the remedy for a
recorder question, which is the exact generic text maintainers filter out. Key the remedy to the specific claim
and say *"no written remedy for this one yet"* when there is none.

**A 0-char model response is `UNRESOLVED`, never a pass.** And a reasoning model may return its thinking in
`reasoning_content` with a clean answer in `content` — read `content` first and label any fallback as a
deliberation transcript.

**Scope the reader's reasoning or it will do the writer's job.** Unscoped, a reasoning proofreader spends its
budget proposing better phrasing and returns style findings; state that it reasons on ONE question only — *does
this draft accurately represent FACTS* — and send its effort level explicitly rather than inheriting the seat's
setting, which is tuned for different work.

**Drafts are ours; sending is the user's.** A tool may write the reply and stamp it `CLEARED` / `DO NOT SEND`;
nothing in the pipeline posts under his name.

**A LEAD SCANNER'S NUMBER IS `CONTACTED`, NOT `FOUND`.** A job that surfaces good candidates and ends at a
notification has a yield of zero however sharp its filter is — measured: nine runs surfaced three real, recent,
almost-comment-less issues from a target field, and not one reply was ever sent. The filter was working; the
pipeline stopped one step short of the only step that counts. **Report found-vs-contacted side by side** (3 found ·
0 answered), and when the gap is total, the fix is not a better filter — it is making the reply one paste away
(draft attached, fact-checked, verdict stated). A scanner that keeps finding and never speaks is spending
attention every day and returning nothing.

Full procedure, verdict/exit mapping, selftest fixtures and the non-reply trap: **`references/prose-proofreading.md`**.

## Scheduled jobs are artifacts too — tier them, do not blanket-harden them

**A cron job shares the failure classes but not the treatment.** The parts of this method that apply depend on
**what the job reads**:

- **Tier A — reads a network or a shared external quota.** Needs an identifying `User-Agent`, a throttle treated as
a **boundary** (`403`/`429` → INCOMPLETE, never a finding, never a retry), and the words to say *"I could not look"*.
- **Tier B — local only, but prints numbers a human acts on.** Needs one rule: a missing input prints
`UNKNOWN`/`NOT RUN`, never `0`.
- **Tier C — local, mechanical, self-verifying** (backup, sync, sweep). **Needs nothing; leave it alone.** A UA
and a throttle guard here are decoration, and 20 acts of theatre dilute the standard until it means nothing.

**Measure the file that actually runs before judging a job** — half of a mature fleet's cron scripts are two-line
wrappers that exec a canonical `.py`, so a grep of the wrapper reports "no network, no UNKNOWN" about the wrapper
and the reader believes it about the job. **And follow imports**: a job calling a shared transport inherits that
transport's `User-Agent`; a per-file grep calls it a gap and manufactures a finding. **Fix the instrument before
accusing the code** — a checker that invents gaps trains its reader to ignore it.

**The class that hides in every monitor: a failed read entering a comparison.** `live = ""` on a fetch failure then
`local != live` reports **DRIFT** — and an `--apply` flag redeploys a page that was never wrong. Keep an
`unverified` bucket and print it as its own column.

**A detector that declines should also LEARN — the refusal is the payload.** A job that surfaces candidates and
ends them at *"no evidence of ours — do not reply"* discards the failure modes we have never paid for. Give it a
companion output that classifies every surfaced item against the **same evidence table** and keeps a durable
register (mode · first seen · times seen · do we have evidence?). Wake a human only on a **new** mode. And when
that companion is built, audit it as an instrument: a record carrying only an ID cannot be classified (printing it
as `UNCLASSIFIED` turns an **absence** into the loudest number of the run), and an accumulating register must
**recompute totals from a dated ledger** rather than `total += n`, or every rerun doubles it.

**When the platform exposes a repair command, the watcher fixes and reports the action — but if the repair is
asynchronous, say "requested, not yet observed" and name the proof.** A request is not a result.

Full tiers, the wrapper/import resolution, the shared-quota ledger, the refusal register and the honest cost of
turning these on: **`references/cron-conformance.md`**.

## Reference Files

- `references/prose-proofreading.md` — Proofreading published prose: deterministic checks, the FACT BLOCK, the non-reply trap, template-remedy drift, cross-model declaration, and the six-case selftest. — Three-way scan pattern for evaluating and contributing to open-source ecosystems. Covers forking workarounds, execution flow, and repos scanned.
- `references/upstream-fix-proof.md` — Proving a fix to someone ELSE's code: toolchain from the manifest, behavioural tests over field assertions, why `[build failed]` is not a red test, root cause as a TYPE rather than a condition, and re-proving your own counter-example.
- `references/pitfalls.md` — **INDEX** for 143 accumulated failure-mode lessons, the ledger behind this skill's silent-wrongness rule. The items live in `references/pitfalls-1.md`, `-2.md` and `-3.md` (**part 3 is the LIVE one — append new lessons there**); the index carries the part list, their counts and digests, and the stated census rule for checking an extraction. **Read on demand.**
- `references/audit-findings-catalog.md` — Real bugs caught by Kimi K2.7 / Claude Opus 4.8 review sessions. CWE-338, CWE-1333, CWE-117, and exception isolation patterns with fixes and provenance.

## Secret & PII preflight — run it BEFORE you claim "verified" (standing rule, 2026-10-17)

**Jordan's instruction:** *"During our auditing phase or our develop-and-verify phase, we want to make
sure we didn't put any personal information or anything like this here."*

**Match CONTENT, never filenames.** A filename-pattern sweep of **68 repos** reported *"no key material
anywhere."* It was wrong. A **live private key to a funded wallet** sat in a file called
`celo-rail-key` — which matches **no** key-shaped NAME pattern (`private[-_]?key`, `*.key`, `keystore`,
all missed it). A content scan found it on the first attempt.

**Second miss in the same pass:** five `*config*.yaml` backups each assigned a real `HIVE_API_KEY`.
Invisible to a hex test — the value wasn't hex. The credential-ASSIGNMENT test caught all five.

```bash
python3 tools/pii_secret_preflight.py <paths...> --fail-on-find   # exit 1 => do NOT commit/sync/ship
python3 /opt/data/scripts/publish-preflight.py <paths...>        # fleet-shared gate, selftest-proven
```

**Both run before a publish. They are not alternatives — they fail differently.** `pii_secret_preflight` is
broader (four classes, PII opt-in); `publish-preflight` is tuned so that the shapes we publish *on purpose*
stay silent: a `0x…` contract address, a placeholder, a documented insecure default, a PEM block inside
`tests/`. **Measured 2026-11-25 across 150 public repos: 168 secret-shaped hits, 147 fixtures, and 6 of the
remaining 7 were token CONTRACT ADDRESSES.** A gate that calls those secrets gets skipped, and a skipped gate
is worse than none. `--selftest` proves both directions on every run.

**Every exemption needs a reason, and it lives in `/opt/data/shared/` — never in `~`.** Each seat has its own
HOME (`/opt/data/profiles/<seat>/home`), so a per-seat allowlist is invisible to the rest of the fleet and the
same benign shape gets re-litigated seat by seat. An entry with no `reason` is refused at load.

Four classes, and **the second is the one that fools people**:

1. **KEY MATERIAL** — PEM blocks, 64-hex appearing with private-key language, **a bare 64-hex alone on a
   short line**, mnemonic wordlist runs.
2. **CREDENTIAL ASSIGNMENTS** — `NAME=value` where NAME is credential-shaped and the value is real.
   **A sha256 in a doc is fine; an ASSIGNMENT is not.** Placeholders (`${…}`, `<REDACTED>`, `xxx`,
   `your_`, `getenv`, `_env$`) are excluded — or the gate cries wolf and gets ignored.
3. **KNOWN TOKEN SHAPES** — `github_pat_`, `gh[pousr]_`, `sk-`, `sk-ant-`, `AIza`, `xox[baprs]-`,
   `AKIA`, JWTs, `sk_live_`.
4. **PERSONAL INFORMATION** — emails, phone numbers, US SSNs, Luhn-valid card numbers.

**Two rules that make it an audit rather than a walk** (same ones as §The two rules that make it an audit):
**a name-pattern sweep is not a content sweep**, and **"I looked and it seemed fine" is not a finding.**
If you report a sweep as clean, state the method — *"filename patterns at HEAD"* is a narrower claim
than *"no key material exists"* and it would have been true where my sweep was false.

### ⚠️ A gate that fires on everything gets ignored — tune it against a KNOWN-CLEAN corpus

The first working version of the preflight reported **6,338 findings on a corpus that held one real
key.** A gate at that volume is not a gate; it is noise that trains people to skip the check — and it
would have **buried the one true finding**. Every rule below was a measured false-positive class, not a
guess, and the tool now carries a **6-case regression suite** (key file → FAIL, mnemonic vector → FAIL,
prose → PASS, sha256-on-its-own-line → PASS, python import block → PASS, clean → PASS):

| rule | false positives | why |
|---|---|---|
| seed-phrase heuristic: *"a BIP-39 word followed by 9+ words"* | **732** | `about` and `able` are BIP-39 words **and** among the commonest words in English. It fired on prose — including the fleet's own docs. |
| same rule, tightened to *"12+ lowercase words, ≤1 function word"* | **459** | `import argparse import csv import json import sys from datetime import date` is twelve lowercase short words with one function word. **Every Python file with an import block fired.** |
| credential name matched any field containing `token`/`seed` | **1,075** | matched `tokenizer` (330), `tokens`, `token0_balance`, `credential_type`, `PARAMS.seed`. Name the fields that *hold* secrets, and deny the ones that merely contain the word. |
| Luhn over any 13–19 digit run | **496** | block numbers, timestamps, JSON numbers. Also require a real card-network IIN prefix and a bounded/separated run. |

**Three lessons worth carrying to every heuristic you build:**

1. **Tune against a corpus you believe is clean, and validate against fixtures you know must fire.**
   Both directions, or you only learn half of what is wrong.
2. **Separate the classes by their failure cost.** Secrets are never acceptable → always fail. **PII in
   a private vault is expected → make it opt-in (`--pii`).** Mixing them is what made the first version
   unusable.
3. **Precision beats recall in a gate.** A missed detection is bad; a gate nobody obeys is worse,
   because it converts "we check" into "we check and then ignore it" — and that is indistinguishable
   from not checking, except that it feels covered.

## Pitfalls

> **The ledger lives in `references/pitfalls.md` — an INDEX since 2026-09-28** — 143 accumulated silent-wrongness lessons, in three part files (`references/pitfalls-1.md`, `-2.md`, `-3.md`; **part 3 is LIVE and takes new lessons**). Read the part you need with `skill_view(name='develop-and-verify', file_path='references/pitfalls-1.md')`, or grep the three. The index carries each part's count, digest and the stated census rule.
> Extracted from this file 2026-09-28 to restore headroom (SKILL.md had reached 103,752 chars against the 100,000-char platform cap, which makes every write refuse), then SPLIT into parts the same evening when the single ledger reached 93,842 chars against the same per-file cap. **The cap is enforced PER FILE, not per directory** — so the parts, not the directory, are what must stay under it.
> **Nothing was deleted — the section moved.**
## A read that stopped early is a FLOOR, never a total — and measure in the unit the limit enforces

Two reporting errors from one family. Both produce a confident, wrong number that nothing in the output flags.

**① A paged or capped read counts as a total.** A sample of a deep collection reports only what fitted.
Measured: an inbox paged to its cap yielded `779` messages in one year, and a query the source itself bounded
(date filter, not enumeration) returned **2,472** for the same period — 32% of the truth, reported as the truth.
**Before reporting any count from a paged source, ask whether the last page carried a continuation token.** If it
did, the number is `>= n`. Prefer the count the source can bound itself over one you truncated, and state which
one you used.

**② The unit you measured is not the unit enforced.** A limit expressed in CHARACTERS refuses writes by
character; a filesystem reports BYTES. Multi-byte glyphs (em dash, section sign) cost 1 char and 2-3 bytes, so a
byte-based headroom figure drifts in the **permissive** direction — it reports room where the enforcement will
refuse, or an alarm where there is none. Measured: two files reported as `-31` and `-75` (over cap) were actually
`+99` and `+13`; the whole remediation that followed was fixing a problem that did not exist.
**Read the constant off the code that ENFORCES it, then measure in that unit.**

**③ A successful write is not a change.** Removing a label, setting a flag, or clearing a field on rows that
already lacked it succeeds and alters nothing. After any bulk mutation, capture the pre-state or re-run the
query the user would run — the API's success means the call was accepted, not that the world moved.

## The CANDIDATE-vs-FINDING rule — time it before you name it

**A list of what a thing COULD be is not a finding. If you cannot say which one it IS, the answer is `UNKNOWN`.**

Measured over one investigation (peer-mesh, 2026-10-05/06), where the same finding needed **three** corrections:
a rate that was a snapshot, a trigger hypothesised then falsified, and a cause hypothesised then falsified. **Every
correction came from measuring again; none came from thinking harder.**

The rules that would have prevented all three:

1. **A count is not a rate.** Before writing `%`, check the events' TIMESTAMPS. Five calls that all land inside one
   minute are one event, not 3% — and the count staying flat while the denominator grows is what a fixed cluster
   looks like. *The number was one command away the whole time.*
2. **A correlation is not a cause, and SHARED PATH is not SHARED MECHANISM.** Two anomalies on the same code path
   looked like one bug. Timing the path showed **0.15 s against a 30 s ceiling** — two hundred times under the
   limit the theory blamed. **A limit cannot cause a timeout on a call that finishes in a fraction of it: check the
   LATENCY before blaming the CEILING.**
3. **Falsify your own hypothesis before handing it over.** Adding a deliberately mis-configured input and watching
   it reproduce the exact symptom (including the same record id) is what turned a guess into a finding — and the
   same method is what killed the two guesses that were wrong.

**Corollary for handoffs: report the DISTINCTION, not the tidier story.** *"This is a real correctness bug AND it is
not the explanation for the failure you saw"* is worth more to the next person than a single confident cause that
happens to fit both.
