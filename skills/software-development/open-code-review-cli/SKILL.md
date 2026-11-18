---
name: open-code-review-cli
description: Use when running Alibaba's `ocr` code-review CLI.
version: 1.0.0
author: Gentech (HQ)
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, static-analysis, second-opinion, opencode-go, cli]
    related_skills: [requesting-code-review, develop-and-verify, codebase-architecture-analysis, codebase-security-audit]
---

# Open Code Review (`ocr`) — install, configure, run

Alibaba's hybrid code-review CLI: **deterministic pipeline picks and bundles files; an LLM agent reads them.**
Apache-2.0, Go, single static binary. <https://github.com/alibaba/open-code-review>

**It is a second opinion, not a replacement for our own review pass.** Recall is deliberately lower than a
general agent — precision over exhaustiveness. It will miss things.

## When to Use

- A second-opinion review of a diff before it lands — **money-code, pre-push gates, or an unfamiliar repo.**
- You want cross-file estate-convention checking (it argues from how *sibling* files do things, not from the diff alone).
- Auditing a commit whose stated purpose was to fix a bug — that is when new convention drift gets introduced.

**Do NOT use it** for every commit (see Cost), or as the only review on a security-critical change.

## Install — the release binary, never `npm -g`

The global npm prefix on this host is **not writable**, so `npm install -g` fails. Use the release binary:

```bash
cd /opt/data/dl
curl -sL -o opencodereview-linux-amd64 \
  https://github.com/alibaba/open-code-review/releases/latest/download/opencodereview-linux-amd64
curl -sL -o sha256sum.txt \
  https://github.com/alibaba/open-code-review/releases/latest/download/sha256sum.txt
sha256sum opencodereview-linux-amd64   # compare against sha256sum.txt BEFORE installing
install -m 755 opencodereview-linux-amd64 /opt/data/bin/ocr
export PATH="/opt/data/bin:$PATH"
ocr version
```

**Verify the hash against the release's own `sha256sum.txt`** — a 56 MB download over a flaky link is a real
failure mode, and `install` runs whatever landed.

## Configure — the OpenCode Go session wall

**OpenCode Go rejects any request lacking `x-opencode-session`:** HTTP 400 `{"type":"MissingSessionID"}`.
This is not an auth failure and the key is fine — do not go hunting for a new key.

```bash
K=$(grep -E "^OPENCODE_GO_API_KEY=" /opt/data/profiles/<seat>/.env | cut -d= -f2- | tr -d '"\n\r ')
ocr config set custom_providers.opencode-go.url https://opencode.ai/zen/go/v1
ocr config set custom_providers.opencode-go.protocol openai
ocr config set custom_providers.opencode-go.api_key "$K"
ocr config set provider opencode-go
ocr config set model glm-5.3-flash
ocr config set custom_providers.opencode-go.extra_headers 'x-opencode-session=<anything>'
```

- **`extra_headers` is `key=value`, NOT JSON.** The JSON form (`'{"k":"v"}'`) is rejected:
  `invalid extra header ... expected key=value`.
- **`glm-5.3-flash` is the working model** (verified text-capable on OpenCode Go).
- The `ocr config set` output **masks the key** (`oc_s***KMnA`) — that is expected, not a truncated write.

## Run

```bash
cd <repo>
ocr delegate preview                 # what would it review? no LLM, no cost
ocr delegate preview --from A --to B # scope a range
ocr scan --preview                   # full-file mode
ocr review --from HEAD~1 --to HEAD --format json --color never
```

- **A plain `ocr review` on a clean tree reports `0 reviewable files`** — it reviews *diffs*, so give it a
  commit range or make changes first. That is not a broken install.
- `--format json` writes to stdout; redirect stderr separately for the human log.
- Sessions are resumable: `ocr review --resume <session-id>`.
- `ocr delegate` emits a spec for the host agent to do the review — **the no-API-key path.**

## Cost — the number that decides when to run it

**Measured: 102,528 tokens (87,797 in + 14,731 out, 59,392 cache-read) and 2m02s for a 27-line diff**, with
9 tool calls (`code_search` ×5, `file_read` ×2).

**The tokens go on repository context — and that is exactly what makes the findings good.** It found a real
defect by searching sibling files, not by reading the diff. But ~100K tokens per review is not a per-commit
tool on a metered rail. **Use it for money-code and pre-push gates.**

## Verify its findings before repeating them

**The tool's output is a claim; the file is the evidence.** Hand-check the load-bearing finding against the
repo before you act or report it — it argues from convention, and convention can be misread.

Worked example (`gentech-treasury-code`, 2026-10-27): it flagged that a commit's new `_PROFILE_ROOT` read
`STEWARD_PROFILE_ROOT` while siblings used `HERMES_PROFILE_DIR`. **Check:** `grep -c HERMES_PROFILE_DIR` across
the tools directory → 4 of 5 files matched, `steward-council.py` was the only divergence. **TRUE.**
**A finding you have not checked is a claim you are forwarding, not a finding you made.**

## Gate wrapper — `scripts/ocr-gate.sh`

**A review tool you must remember to run is not a gate.** `scripts/ocr-gate.sh` wraps `ocr review` with two
refusals and a real verdict:

```bash
ocr-gate.sh --range HEAD~1 HEAD          # refuse if scope or rail is unsafe
ocr-gate.sh --from-json saved.json       # ZERO-COST verdict test on a saved result
```

**Exit codes:** `0` clean · `1` findings / review failure / unreadable result · `3` refused by a guard.

**The two guards, and why they exist:**
- **Scope ceiling** (default 800 lines) — cost scales with scope because `ocr` searches siblings per group.
- **Rail ceiling** (default 90% monthly on the usage gate) — a multi-file review outspends a day of cron.

### Rules this wrapper is built on

**A gate that passes WITH findings is not a gate.** Findings must exit non-zero. The first version printed the
finding count and still exited `0` — a green light over a real defect, the same bug class as the deploy skill's
`expect HTTP 200`.

**Fail closed when you cannot read your own result.** Unparseable JSON, or JSON with no `summary` block, exits
`1` — never `0`. Reporting "clean" because the check could not read its output is worse than reporting nothing:
it launders silence into a pass.

**Never print a cost line you cannot populate.** The first version grepped stderr with a pattern that never
matched and printed `usage unavailable` while real tokens were being spent — a line that implies "free". Read
cost from the JSON body (`summary.total_tokens`), which is authoritative, and say so loudly when it is `0`.

**Make the verdict testable without paying for it.** `--from-json` evaluates a saved result, so the parse +
exit logic is falsified with fixtures instead of a 100K-token LLM call. **A paid-only code path is untested code
path.** Prove the battery before trusting it on real code: findings→1, clean→0, unreadable→1, no-summary→1,
missing-file→3.

**Do not edit a running script.** Bash reads a script progressively; patching mid-execution mixes old and new
lines. Copy the output, wait for exit, then edit.
