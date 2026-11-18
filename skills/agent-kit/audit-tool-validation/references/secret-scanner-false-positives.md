# Secret-scanner false positives — classify by context before severity

A credential detector is the most reliable false-positive machine in a vault, because a rule that fires on a
*shape* (`0x` + 64 hex, a 40-char base58 run, `-----BEGIN … PRIVATE KEY-----`) has no notion of context. It
fires on bytecode, documentation, placeholders and — most reliably — **on its own source**.

Measured: a weekly secret audit reported **891 findings, 705 of them CRITICAL**, and classifying all 891
produced **zero real secrets**. The control had been exiting "findings" every week for months, which is why
nobody had read it. **A control nobody reads is not a control.**

## Classify by context before assigning severity

Every bucket below is checkable in code, and each needs a reason printed next to the hit so the suppression
stays auditable.

| class | the tell | why it is not a secret |
|---|---|---|
| **BUILD_ARTIFACT** | path contains `out/`, `artifacts/`, `build-info/`, `.next/`, `dist/` | the hex is bytecode, ABI data and event topics |
| **CONFIG_REFERENCE** | value is `${VAR}`, `process.env.X`, `/path/to/key`, `secrets/<name>` | a reference to a credential, not a credential |
| **PLACEHOLDER** | `your_…_here`, `change-this`, `xxxx`, `pk_live_1234567890abcdef`, a `.env.example` file | written to be fake |
| **TEST_PATH** | under `tests/`, `fixtures/`, `mocks/`, `hardhat.config` | fixtures carry published test keys |
| **PUBLISHED_TEST_KEY** | matches a known Hardhat/Anvil/Ganache account key | in every tutorial on earth, controls nothing |
| **SCANNER_PATTERN** | the file is a secret scanner / `gitleaks` / `trufflehog` config | **the detector detecting itself** |
| **DUPLICATE** | the same value appears in 4+ files | fixtures get copy-pasted; a leak rarely does |

- **Match the detector's own source out first.** A regex literal `-----BEGIN RSA PRIVATE KEY-----` inside
  `secret-scanner.js` is the single most embarrassing false positive in this class, and it is trivially
  excluded by path.
- **Path alone can settle a class.** Requiring hash-shaped context *as well* leaves Foundry `artifacts/*.json`
  in the real bucket; build output is not a secret *source*, so the path is sufficient evidence.
- **Frequency is evidence.** A value repeated across many files is a fixture; a leaked key is usually alone.
  Use it as a classifier, never as a verdict — one leaked key pasted into ten tutorials is still a leak.
- **State what was suppressed in the output.** "N findings, 0 real, suppressed by class" is auditable;
  a silent filter is a second blind instrument.

## Prove the CLASSIFIER before trusting its silence — selftest in both directions, every run

Classifying findings is itself a detector, and it fails in the direction nobody notices: **a rule that is
slightly too wide manufactures silence**, and silence is what a secret control is trusted for. Give the
classifier a `--selftest` with cases in both directions and run it **before** the scan; if it fails, exit
non-zero and report nothing as clean.

```
PASS  real key in src        want=REAL_CANDIDATE    got=REAL_CANDIDATE
PASS  real provider key      want=REAL_CANDIDATE    got=REAL_CANDIDATE   ← failed on the first implementation
PASS  build artifact         want=BUILD_ARTIFACT    got=BUILD_ARTIFACT
PASS  env reference          want=CONFIG_REFERENCE  got=CONFIG_REFERENCE
PASS  placeholder            want=PLACEHOLDER       got=PLACEHOLDER
PASS  the scanner's own src  want=SCANNER_PATTERN   got=SCANNER_PATTERN
```

- **Co-occurrence is the trap.** A suppression rule written as "the line also contains a function call"
  silently files a real credential under `CODE_ASSIGNMENT`, because a real integration line usually also
  contains `client = OpenAI(`. Require the **assigned name** to look secret AND the **value** to look
  code-shaped — never merely that both appear on one line. Two of the six cases above exist only to catch this.
- **`acknowledged`-style hand-clearing is not a control.** Clearing the last ten hits by eye means the next
  ten get cleared by eye too, and eventually one is waved through. Convert the eye into a rule *and* into a
  selftest case before the next run, or the clean report is a habit rather than a measurement.
- **A clean result from an unproven classifier is indistinguishable from a blind one.** The gate is the whole
  point: the scan may not print "0 real" until the classifier has shown it still catches a planted key.

## Notes on this vault's own scans

A vault carries notes *about* secrets, which is a class the table above does not name: filenames matching a
secret pattern across dozens of markdown files were all notes documenting where a credential lives, and a
64-hex hit was a storage slot. **The path class that settles it is `.md` under a notes tree** — a credential
in a note is prose, and the note should be corrected, not the scan muted.
