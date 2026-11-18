# The secret/PII preflight gate — rules, tuning, and how to validate it

Companion to `scripts/pii_secret_preflight.py`. The body of the skill carries the standing rules
(match CONTENT not filenames; two positional classes; exclude placeholders; state the method).
This file carries the depth: how to tune a detection gate so it stays obeyed, and the measured
false-positive classes that any similar heuristic will hit.

## Why tuning is the actual work

**A detection rule is not finished when it fires on a true positive. It is finished when it stops
firing on the corpus you believe is clean.** The first working version of this gate reported
**~6,300 findings on a corpus that held exactly one real key.** At that volume the gate is worse
than nothing: it **buries the finding it exists to surface** and converts "we check" into "we
check and then ignore it" — indistinguishable from not checking, except that it feels covered.
Tuned, the same corpus yields ~440 findings: still a triage backlog, but a triageable one, and the
true positive still fires.

## Measured false-positive classes

Every one of these was a **measurement**, not a guess. Any heuristic in this family will meet them.

| naive rule | hits | why it fired |
|---|---|---|
| seed-phrase = "a BIP-39 word followed by 9+ words" | **732** | `about` and `able` are BIP-39 words **and** among the commonest words in English, so the rule matched ordinary prose — including the fleet's own documentation. |
| same, tightened to "12+ lowercase words, ≤1 function word" | **459** | `import argparse import csv import json import sys from datetime import date` is twelve lowercase short words with one function word. **Every Python file with an import block fired.** |
| credential field name matching anything containing `token`/`seed` | **1,075** | matched `tokenizer` (330 of them), `tokens`, `token0_balance`, `credential_type`. |
| Luhn over any 13–19 digit run | **496** | block numbers, timestamps, JSON numbers all pass Luhn by chance. |
| PII (emails/phones) in a mixed scan | **3,678** | a private vault legitimately holds thousands of addresses. |

## The fixes, as general rules

- **Require DISTINCT words and no code keywords** in any natural-language heuristic. Repetition and
  language keywords are what separate source code from prose-and-mnemonics.
- **Name the fields that HOLD a secret; deny the ones that merely contain the word.** A substring
  match on `token` reaches `tokenizer`; an anchored field name (`api_key`, `access_token`,
  `private_key`) does not.
- **A value that is a path, URL, slug or bare number is not a secret.** Check the value's shape, not
  just its length and character mix.
- **Luhn alone is worthless.** Add the network IIN prefix and require a bounded or separated run.
- **Separate classes by their failure cost.** Secrets are never acceptable → always fail. **Personal
  data in a private vault is expected → make it opt-in (`--pii`).** Mixing the two classes is what
  made the first version unusable, not the individual rules.

## Validate the gate in BOTH directions

Point it at fixtures that MUST fire **and** at a corpus you believe is clean, and confirm it returns
**opposite** verdicts. One direction only teaches you half of what is wrong — and the half it hides
(the clean corpus) is the half that decides whether anyone obeys the gate.

Regression suite this gate is held to:

| fixture | expected |
|---|---|
| a file with a bare 64-hex alone on a line + key language | **FAIL** |
| the public BIP-39 test-vector phrase (12 distinct words) | **FAIL** |
| ordinary prose containing `about` / `able` / `zoo` | **PASS** |
| a `sha256:` value on its own line | **PASS** |
| a Python import block | **PASS** |
| an empty/clean text file | **PASS** |

Re-run all six after ANY change to a rule — loosening one guard to fix a miss reliably re-breaks
another.

## Two classes a pattern table cannot see

These are **positional**, not lexical, and they are where real secrets hide:

- **`NAME=value` where NAME is credential-shaped AND the value is real.** A `sha256` written in a doc
  is fine; an **assignment** is not. This is the class that found five config backups holding a live
  provider key that every hex-based rule had walked past.
- **A 64-hex with no hash vocabulary anywhere in the file.** Hashes arrive beside `sha256` / `txid` /
  `gasUsed` / `checksum`; keys arrive alone. Config backups are where these concentrate.

## Triage the hit set: CONTEXT beats pattern, and the LIVE tree is not the ARCHIVE

**A gate returning hits is not a gate returning findings.** Tuning (above) gets the count down to
something a human can face; triage is what turns that pile into verdicts. **Resolve each CLASS to its
context before reporting anything.** Measured on one vault: **815 token-shaped instances → exactly ONE
real credential.** The bulk resolve instantly once you know the signatures:

- **A provider's OWN published example credentials.** AWS's documentation key id (`AKIA…EXAMPLE`) and
  its companion example secret appear verbatim in security docs, in key-**detection** rulesets, and
  inside `assert _contains_secret("AKIA…EXAMPLE")` test assertions. **A file about catching leaks is
  full of sample leaks by construction** — the more security tooling in a tree, the more of these fire.
- **The canonical sample JWT shipped by jwt.io.** Recognise it by its fixed TAIL, not its header —
  every JWT begins `eyJ…`, so the header proves nothing.
- **Leak-detector corpora.** A ruleset named `*-leakage*.yaml` / `*secret*.yaml` is a list of
  deliberate examples; reading its contents as live credentials is a category error.
- **Placeholder-suffixed shapes** (`…456`, `…678`, `…789`, `…def`) and `EXAMPLE` / `***` / `0{6,}` runs.

**Order the triage by failure cost, not by hit count:**

1. **LIVE tree first, ARCHIVE second.** Re-scan with the backup/archive/snapshot trees excluded. A hit
   in a live config or secrets dir is a *current* exposure; a hit in an abandoned snapshot is history.
   Measured split on one corpus: **444 total → 24 in the live tree → 0 in live configs.** Reporting the
   archive count as the finding is the mistake that buries the live one.
2. **Then classify the live hits by context** — a variable *named* `passphrase` inside a code example, a
   `WALLET_PRIVATE_KEY = "0x0123…"` test fixture, a doc snippet — before any becomes an action item.
3. **Report the residual split by verification.** Say how many you verified individually and how many
   you explanation-mapped by class. **"Mostly fixtures" is not "all fixtures"** — mark the unverified
   remainder **flagged, not cleared**, in exactly those words.

**Never test whether a found credential is still LIVE by using it.** Calling the provider with it *is*
using it — the thing the standing rule forbids. Report it, name the owner (a provenance line like
*"token provided by <owner>"* tells you whose rotation it is), recommend rotation, and record liveness
as **unmeasured**. An honest unknown beats an unauthorised test.

**Where the secret accumulated decides the severity, so verify the location rather than assume it.**
An archive inside an encrypted, account-gated sync is within policy; the same tree inside a **git repo**
is not (a repo can be made public, forked or cloned, and history is forever). The check is one command
— `git ls-files | grep -c '<archive-path>'` returning **0** proves the archive is *not* in the repo.

