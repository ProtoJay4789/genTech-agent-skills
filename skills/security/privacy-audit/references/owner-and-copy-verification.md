# Owner and copy verification

Depth for the `Check Repo Visibility` section. Use when a repo, file, or exposure is reported as present,
absent, or fixed, and before any of those claims reaches a report.

## Why a single-owner probe is not a search

An organisation and a same-named personal account are **different owners**. `Gentech-Labs` (org) and
`GentechLabs` (personal) are unrelated GitHub namespaces that happen to differ by one hyphen and one letter's
case. `/repos/<Org>/<name>` and `/repos/<User>/<name>` share no lookup path.

So: **404 at owner A says nothing about owner B.** The failure this produces is confident and wrong — "the
repo does not exist, it was deleted or never published" — when in fact it is live and public under a name you
did not think to try. Announce absence only after enumerating the variants.

```bash
for owner in "$ORG" "$USER" "${ORG//-/}" "${USER//-/}"; do
  printf '%-28s ' "$owner"
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' -m 15 "https://api.github.com/repos/$owner/$REPO"
done
```

An anonymous HTML probe is the same evidence one layer out, and it needs no token:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -m 15 "https://github.com/$owner/$REPO"
```

A `200` here from an unauthenticated client is public exposure, regardless of what any internal note says
about visibility.

## "Fixed" is per copy, never global

GitHub serves a file from whichever repo physically contains it. Two accounts holding the same file are **two
doors**, and closing one leaves the other open.

When a scrub is reported:

1. Re-probe **each owner** independently — do not transfer a clean result.
2. Fetch the **served bytes** (`raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>`), not the API's
   metadata; a commit hash proves an edit was authored, not that the branch now serves the new content.
3. Report a per-copy table: `owner → path → branch → verdict`.
4. If one copy cannot be edited (a pull-only token, an account you do not own), say so explicitly — that copy
   stays an **open finding**, not a caveat.

A branch-head deletion also does not remove a value from history. The line is still in the blobs of every
previous commit, reachable by anyone who clones. **Scrubbing closes the future; rotation closes the past.**

## Classify the value, not the variable name

A variable-name grep answers "is there an assignment here?" — never "is there a secret here?". Both
polarities are wrong:

- **False alarm:** `export PRIVATE_KEY="changeme"` matches `PRIVATE_KEY` and contains nothing sensitive.
- **False clean:** a key stored under `DEPLOYER` or `MAINNET_SIGNER` matches no name in your pattern set.

Measure length and shape, print neither the value nor a prefix of it that identifies it:

```python
import re
m = re.search(r'(?:PRIVATE_KEY|SIGNER|MNEMONIC)\s*=\s*["\']?([^"\'\s]+)', line)
v = m.group(1) if m else ""
real = bool(re.fullmatch(r'(0x)?[0-9a-fA-F]{64}', v))
print(f"len={len(v)} hexish={real}")     # 9 chars -> placeholder; 66 chars 0x+64hex -> key material
```

Report the pair: **"assignment present, value is a placeholder"** is a verified fix. Both halves are needed —
the first alone is an alarm, the second alone is a guess.

## Do not handle a leaked key to learn its address

Deriving an address means reading the private key. Every reader is a copy that can land in a log, a shell
history, a transcript, or another agent's context.

- If **another party** has already derived the address, take theirs. Quoting a published address is free;
  re-deriving is a fresh exposure with no new information.
- Derivation is the **owner's** action, and then only from a file path or stdin — never argv (world-readable in
  `ps`, and it lands in history), never an inline string, never a chat message.
- State in the report that you did **not** derive it and why. That sentence is what stops the next reader from
  "just checking" and compounding the leak.

## Passing mention is a scan opportunity

Bulk scans (hex patterns, key-pattern regexes) produce noise in EVM repos: calldata, transaction hashes,
storage slots and event topics are all 64-hex and all public by nature. A blunt scan buries the real key in
false positives and trains the reader to skim.

The reliable hit usually comes from a pass that **reads files for a different reason** — writing a
description, reviewing a README, auditing presentation. That pass opens the file that no secret-scanner would
have prioritised, and finds the key sitting in prose. Treat any content-reading task over a repo as a
secrets opportunity, not just a documentation task.
