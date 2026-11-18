# Offline Recovery Recon — establishing what survived, before planning anything

Use when you are called in after a total loss (wiped host, lost volume, revoked account) and there is
no usable backup yet. **The order matters more than the effort:** every step below is cheap, and each
one can invalidate the plan you were about to write.

## Why order matters

Plans written before the recon are plans written on assumptions. Two of the most expensive wrong turns
are (a) declaring data gone when it is sitting in a directory the agent cannot read, and (b) declaring
data recoverable when it is behind a permission wall only the human can pass. Both are settled by a
single command each — run them first.

## The recon order

1. **Enumerate what is actually present, read-only.** Directory listings and file counts, not
   conclusions. "The brain survived: N files, M directories" is a finding; "the brain is fine" is not.
2. **Ask what exists that you cannot read, and say so plainly.** A `permission denied` is not a `no` —
   it is an unanswered question, and it is the one class of item worth handing to the human immediately
   with a single copy-pasteable command. Do not report a permission wall as a loss.
3. **Sweep shell histories, editor backups and config copies for plaintext credentials.** History files
   record *commands*, which means a credential embedded in a clone/PAT URL is sitting there in clear
   text. Two things follow: (a) tell the human to **revoke** it immediately, and (b) never use it
   yourself, even when it would unblock the task. A recovery session that harvests a pasted credential
   has traded a security incident for a shortcut.
4. **Re-census anything with independent state.** Wallets, on-chain positions, external accounts,
   registrations. Chain state is not lost by losing a host — it is only *unreachable* without keys, and
   "readable but not movable" is a materially different status from "gone". Report balances and
   ownership separately.
5. **Re-issue versus recover, as two lists.** Separate what must be *recovered* (data, keys, positions)
   from what must be *re-issued* (API keys, tokens, bot credentials). An inventory of what used to exist
   converts an unbounded loss into a checklist — that inventory is usually the most valuable surviving
   artifact, more valuable than the data itself.
6. **Measure documentation drift before trusting any doc.** After an infrastructure migration, path
   references rot silently: the docs still describe *what* to do but point at directories that no
   longer exist. Count how many files cite each dead path, then fix in this order — a canonical
   old→new translation table first, then the *operational* instructions, and **leave historical
   references alone**. Rewriting a past measurement's paths falsifies the record that explains the loss.
   The metric to report is not "references remaining" but **"no remaining instruction is unfollowable"**.
7. **Only then plan.** Every plan item should name the step it depends on, and the first item should be
   the thing that prevents a repeat — usually making the second copy real.

## Reporting rules for a recon

- **Mark provenance per claim** — verified against the live system, designed but unbuilt, or assumed.
  A recon that hides which lines are unbuilt gets trusted as if all of it were verified.
- **Label a weak signal as weak at the moment you cite it.** A directory mtime, an inode number, a
  "looks untouched" timestamp is suggestive, never evidence. If you use one, say what it is worth in the
  same sentence; and if it later turns out wrong, lead the correction with the fact that you
  over-claimed it rather than quietly dropping the claim.
- **Correct aggressively and early.** A wrong number, a wrong direction (e.g. which leg of a position
  holds the volatile asset), or a wrong scope ("only one account is affected" when two are) must be
  retracted in the next message, in plain text, not folded silently into new advice.
- **Cross-validate every recovered figure against a second source** before reporting it as fact — an
  independent note, a second query, a controlled probe. Two sources agreeing is confidence; one source
  is a number.
