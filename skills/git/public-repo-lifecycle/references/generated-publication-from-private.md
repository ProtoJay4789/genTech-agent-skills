# Generated publication from a private vault — the gate recipe

One direction only: **private vault → allowlist → gates → scratch render → human read → remote.**
Nothing is ever edited in the public tree; it is regenerated.

---

## 1 · The allowlist file

A plain list of paths, one per line, relative to the vault root. No globs on the first pass — a glob is a
policy nobody read. Default is **denied**; a path is published because it appears here.

```
coordination/handoff-protocol.md
standards/evidence-requirements.md
examples/worked-handoff.md
```

Keep it small enough that a human can read the whole list in one screen. If it needs a page, the
publication is a different project from the one you agreed to.

---

## 2 · Gate 1 — path

```python
ROOT = Path(vault).resolve()
ALLOWED_EXT = {".md"}
VETO = ("treasury", "career", "journal", "secret", "backup", ".env", ".key", ".token", "credential")

def check_path(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise Refuse(f"escapes root: {rel}")          # ../ and symlink escapes
    if p.suffix not in ALLOWED_EXT:
        raise Refuse(f"extension not allowed: {rel}")
    low = rel.lower()
    for v in VETO:
        if v in low:
            raise Refuse(f"vetoed fragment '{v}': {rel}")
    if not p.is_file():
        raise Refuse(f"missing: {rel}")
    return p
```

Test both directions: a valid path resolves, and `../../etc/passwd`, a `.png`, and a vetoed name each
raise.

## 3 · Gate 2 — secret patterns, refusing the WHOLE build

Collect hits across every file, then refuse once. One leaked file in a 39-file publication is a leak.

```python
PATTERNS = {
  "evm_private_key": r"\b0x[0-9a-fA-F]{64}\b",
  "github_token":    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
  "pem_header":      r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
  "stripe_live":     r"\bsk_live_[A-Za-z0-9]{16,}\b",
  "jwt":             r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
  "card":            r"\b(?:\d{16}|\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}|\d{4}[ -]\d{6}[ -]\d{5})\b",
  "ssn":             r"\b\d{3}-\d{2}-\d{4}\b",
  "email":           r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
}
```

**The card pattern is the one that goes wrong.** `\b(?:\d[ -]*?){13,16}\b` matches a date range
(`2026-11-20 to 2026-11-27`) and a chat id, so it refuses clean documents. Anchor on the three real
formats and nothing else.

**Fixture both ways, and run it before trusting the gate:**

```python
MUST_FLAG = ["0x" + "a1"*32, "ghp_" + "x"*36, "-----BEGIN RSA PRIVATE KEY-----",
             "sk_live_" + "A1"*10, "a.b@c.co", "4111 1111 1111 1111", "123-45-6789",
             "eyJhbGciOi.eyJzdWIiOi.SflKxwRJ"]
MUST_PASS = ["ordinary prose about the handoff protocol",
             "telegram chat <telegram-group-id>",
             "window 2026-11-20 to 2026-11-27",
             "unix 1731000000 and 1731003600"]
```

The run that refuses its own clean fixtures is the run that would have been switched off later.

## 4 · Gate 3 — the human read

Print, one line each: `file:line  <the line>`. No verdicts, no filtering to "likely" hits, no blocking.
Group by file, keep the line text verbatim, and let the operator decide per line.

The categories worth surfacing: real names · place names and timezones · family and household
references · anything that reads as an internal incident · anything that states a capability we would
not want advertised (a key, a burned address, a funded wallet).

**Publishing method beats publishing notes.** What is worth showing an outside reader is the *system* —
how agents share a brain, how a handoff carries an agreement block, how a completion must carry evidence —
not the working notes underneath it. That framing is also the one that survives a stranger's read: a
sanitised brain dump is a curiosity, a documented coordination system is a contribution.

## 5 · Render, then stop

```
build → ./scratch/out/          (a directory, not a repo)
review → the lines needing a decision
human approves the file list
create remote → push → tag the snapshot
```

**A snapshot is tagged and dated** so what a reader sees is what was chosen. A live-feed publication is
the copy-that-drifts problem wearing a CI badge.

---

## What this replaces

| shape | why it fails |
|---|---|
| copy the vault, delete the personal files | a denylist cannot prove a negative, and the filter is wrong in both directions |
| one shared tree edited by hand | two writers, two truths, the public one goes stale |
| publish everything, redact later | history keeps the first commit; crawlers keep copies |
| a script that publishes on a timer | the decision to ship a file is a human's, once, per file |
