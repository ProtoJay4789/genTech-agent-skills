#!/usr/bin/env python3
"""
pii_secret_preflight.py — the standing gate that says: before this artifact is committed,
synced, or shipped, prove it carries no secret and no personal information.

WHY THIS EXISTS (measured):
  A filename-pattern sweep of 68 repos reported "no key material anywhere". It was wrong.
  A rail-wallet key file matched none of the key-shaped NAME patterns. A CONTENT scan found it
  on the first try. Lesson: sweep WHAT IS IN THE FILE, never what the file is called.
  Second miss in the same pass: five `*config*.yaml` backups each assigned a real API key.
  The hex test could not see them (not hex). The credential-ASSIGNMENT test did.

WHY IT IS TUNED THE WAY IT IS (also measured — read before loosening any rule):
  The first working version reported ~6,300 findings on a corpus that held ONE real key. A gate
  at that volume is not a gate: it trains people to skip it, and it BURIES the true finding.
  Every clause below removes a measured false-positive class:
    - seed-phrase heuristic "BIP-39 word + 9 words"      -> 732 hits: `about` and `able` are
      BIP-39 words AND among the commonest words in English, so it fired on prose.
    - tightened to "12+ lowercase words, <=1 function word" -> 459 hits: an import block
      (`import argparse import csv import json import sys from datetime import date`) is twelve
      lowercase short words with one function word. Every Python file with imports fired.
    - credential name matching any field containing `token`/`seed` -> 1,075 hits: matched
      `tokenizer`, `tokens`, `token0_balance`, `credential_type`. Name the fields that HOLD
      secrets; deny the ones that merely contain the word.
    - Luhn over any 13-19 digit run                            -> 496 hits: block numbers,
      timestamps, JSON numbers. Also require a real card-network IIN prefix and a bounded run.
  Result after tuning: ~440 findings on the same 41k-file corpus — triageable, and the true
  finding still fires.

USAGE
  python3 pii_secret_preflight.py <path> [<path> ...] [--fail-on-find] [--json OUT] [--quiet] [--pii]
  # as a preflight gate: exits 1 when anything is found, 0 when clean.
  # --pii is OFF by default: secrets are never acceptable, personal data in a private vault is
  #   expected. Mixing the two classes is what made the first version unusable.

WIRE IT IN
  - develop-and-verify: run over the artifact BEFORE the "verified" claim
  - key-custody-and-recovery / privacy sweep: run over the repo BEFORE any push or sync
  - any commit/sync job: run over staged paths

VERIFY THE GATE ITSELF — BOTH DIRECTIONS. Validate against fixtures that MUST fire and against a
corpus you believe is clean. One direction only teaches you half of what is wrong. The regression
suite this tool is held to: key file -> FAIL, mnemonic vector -> FAIL, prose -> PASS, sha256 alone
on its own line -> PASS, python import block -> PASS, clean file -> PASS.
"""
import os, re, sys, json, argparse

# ---- what we look for ------------------------------------------------------
# 1. KEY MATERIAL (content, not name)
RE_RAW64   = re.compile(r'(?<![0-9a-zA-Z])(?:0x)?[0-9a-fA-F]{64}(?![0-9a-zA-Z])')
RE_PEM     = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')
RE_KEYCTX  = re.compile(r'(private\s*key|secret\s*key|privkey|signing\s*key|key\s*custody|'
                        r'mnemonic|seed\s*phrase|keystore)', re.I)
RE_HASHCTX = re.compile(r'(sha256|sha-256|sha1|md5|keccak|blake2|hash|checksum|digest|'
                        r'integrity|source_sha256|last_output_hash|tx\s*id|txid|gasUsed|'
                        r'block\s*\d|fingerprint|selector|topic0|merkle)', re.I)

# MNEMONICS — see the header. A real seed phrase is a run of 12/15/18/21/24 DISTINCT lowercase
# words with almost no ordinary function words and no code keywords.
RE_MNEMONIC_CANDIDATE = re.compile(r'\b([a-z]{3,8}(?:\s+[a-z]{3,8}){11,23})\b')
COMMON_WORDS = re.compile(
    r'\b(the|and|for|with|that|this|from|are|was|were|has|have|had|not|but|you|your|our|their|'
    r'its|his|her|they|them|there|here|what|when|where|which|who|whom|how|why|all|any|some|'
    r'more|most|other|such|only|own|same|than|too|very|can|could|will|would|shall|should|may|'
    r'might|must|about|above|after|again|against|being|below|between|both|during|each|few|'
    r'further|into|itself|myself|ourselves|over|under|until|while|because|before|once|able|'
    r'also|just|like|make|made|many|much|need|new|now|one|out|see|so|still|take|two|use|used|'
    r'way|well|were|been|does|did|doing|done|get|got|go|going|if|in|is|it|of|on|or|at|as|an|a|to)\b',
    re.I)
# code keywords — a run containing these is source, not a seed phrase. This is the fix for the
# 459-hit round: `import argparse import csv import json import sys from datetime import date`
# is twelve lowercase 3-8 letter words with one function word, so it satisfied the v2 heuristic.
CODE_WORDS = {
    'import','from','def','class','return','self','none','true','false','print','elif','else',
    'try','except','finally','lambda','async','await','yield','pass','raise','while','with','as',
    'or','and','not','in','is','for','if','global','nonlocal','assert','del','break','continue',
    'str','int','float','list','dict','set','tuple','bool','len','range','open','main','args',
    'argv','sys','os','json','csv','re','time','datetime','pathlib','typing','argparse','sub',
    'err','out','log','file','path','name','data','num','idx','val','tmp','tmpdir','base','get',
    'set','add','run','cmd','env','cfg','src','dst','init','test','input','output','require',
}

def looks_like_mnemonic(text):
    """Each clause removes a measured false-positive class:
      - common words -> prose (732 hits); allow up to 3, since about/able are legitimately BIP-39
      - code words   -> import blocks / identifier runs (459 hits)
      - repetition   -> `import` x3 and friends (mnemonics essentially never repeat)"""
    for m in RE_MNEMONIC_CANDIDATE.finditer(text):
        run = m.group(1).split()
        if len(run) < 12:
            continue
        if len(set(run)) != len(run):
            continue
        if {w.lower() for w in run} & CODE_WORDS:
            continue
        if len(COMMON_WORDS.findall(" ".join(run))) > 3:
            continue
        return True
    return False

# 2. CREDENTIAL ASSIGNMENTS (catches what hex cannot)
#    NARROW on purpose: a bare `token`/`seed` name matched `tokenizer`, `tokens`, `token0_balance`
#    and `credential_type`. Name the fields that actually hold secrets.
RE_CRED_KV = re.compile(
    r'^[ \t]*(?:export\s+)?["\']?([A-Za-z0-9_.\-]*(?:api[_-]?key|apikey|access[_-]?token|'
    r'auth[_-]?token|refresh[_-]?token|secret[_-]?key|client[_-]?secret|_secret|password|'
    r'passwd|private[_-]?key|privkey|mnemonic|passphrase)["\']?)'
    r'\s*[:=]\s*["\']?([^\s"\'#]{16,})',
    re.I | re.M)
# a name that merely CONTAINS a trigger word is not a credential field
RE_CRED_NAME_DENY = re.compile(
    r'(tokenizer|token_count|token_?id|token0|token1|token_?balance|tokens$|token_?type|'
    r'credential_?type|seed_?count|seed_?length|num_tokens|max_tokens)', re.I)
RE_PLACEHOLDER = re.compile(
    r'(\$\{|<%|<[A-Z_]+>|REDACT|\*{3,}|x{6,}|X{6,}|your[_-]|CHANGE[_-]?ME|placeholder|'
    r'example|sample|dummy|fake|test[_-]?key|env\.|getenv|os\.environ|process\.env|'
    r'_env$|_ENV$|\.env\.|\.\.\.|getenv\()', re.I)
# a VALUE that is a path, URL, slug or bare number is not a secret
RE_VALUE_NOT_SECRET = re.compile(
    r'(^[/~.]|://|^https?:|^[a-z_]+\.(py|md|json|yaml|yml|sh|ts|js)$|^[A-Za-z_]+$|'
    r'^\d+$|^<|^\$|^\{|^\[|^-|^\s)', re.I)
# well-known token SHAPES — these are never placeholders
RE_TOKENS = [
    ("github_pat", re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}')),
    ("github_ghp", re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}')),
    ("openai_sk",  re.compile(r'\bsk-[A-Za-z0-9]{20,}')),
    ("anthropic",  re.compile(r'\bsk-ant-[A-Za-z0-9\-_]{20,}')),
    ("google_api", re.compile(r'\bAIza[0-9A-Za-z\-_]{30,}')),
    ("slack",      re.compile(r'\bxox[baprs]-[0-9A-Za-z\-]{10,}')),
    ("aws_akid",   re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ("jwt",        re.compile(r'\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}')),
    ("stripe",     re.compile(r'\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}')),
    ("twilio",     re.compile(r'\bSK[0-9a-fA-F]{32}\b')),
]

# 3. PERSONAL INFORMATION (opt-in — see --pii)
RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
RE_PHONE = re.compile(r'(?<![\d.\-])(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?![\d.\-])')
RE_SSN   = re.compile(r'(?<![\d\-])\d{3}-\d{2}-\d{4}(?![\d\-])')
RE_CC    = re.compile(r'(?<![\d\-])(?:\d[ \-]?){13,19}(?![\d\-])')

SKIP_EXT = {'.png','.jpg','.jpeg','.gif','.webp','.ico','.mp3','.mp4','.wav','.zip','.gz','.tar',
            '.woff','.woff2','.ttf','.otf','.eot','.splat','.pack','.idx','.wasm','.so','.pyc',
            '.dylib','.bin','.pdf','.xlsx','.docx','.pptx'}
SKIP_DIR = {'.git', 'node_modules', '.next', '__pycache__', '.venv', 'venv', 'dist', 'build',
            '.mypy_cache', '.pytest_cache', 'cache'}

def _luhn(s):
    d = [int(c) for c in re.sub(r'\D', '', s)]
    if len(d) < 13: return False
    tot, par = 0, len(d) % 2
    for i, n in enumerate(d):
        if i % 2 == par:
            n *= 2
            if n > 9: n -= 9
        tot += n
    return tot % 10 == 0

def scan_text(text, include_pii=False):
    """Return a list of (class, label, line_no, redacted_excerpt)."""
    hits = []
    lines = text.splitlines()
    # --- key material
    for i, L in enumerate(lines, 1):
        if RE_PEM.search(L):
            hits.append(("SECRET-KEY", "PEM private-key block", i, "-----BEGIN ... PRIVATE KEY-----"))
    if RE_RAW64.search(text):
        ctx_key, ctx_hash = RE_KEYCTX.search(text), RE_HASHCTX.search(text)
        bare = [ (i,L) for i,L in enumerate(lines,1)
                 if len(L.strip()) < 100 and RE_RAW64.fullmatch(L.strip().lstrip('="\' ').rstrip('",\' ')) ]
        if ctx_key and not ctx_hash:
            hits.append(("SECRET-KEY", "64-hex with private-key language", (bare[0][0] if bare else 1), "<REDACTED 64-hex>"))
        elif bare and not ctx_hash:
            hits.append(("SECRET-KEY", "bare 64-hex alone on a line (raw key shape)", bare[0][0], "<REDACTED 64-hex>"))
    if looks_like_mnemonic(text):
        hits.append(("SECRET-KEY", "seed-phrase wordlist pattern", 1, "<REDACTED mnemonic>"))
    # --- credential assignments
    for m in RE_CRED_KV.finditer(text):
        name, val = m.group(1), m.group(2)
        if RE_CRED_NAME_DENY.search(name):
            continue                          # tokenizer / token0_balance / credential_type
        if RE_PLACEHOLDER.search(val) or RE_PLACEHOLDER.search(name):
            continue
        if RE_VALUE_NOT_SECRET.search(val):
            continue                          # a path, URL, slug or number is not a secret
        if len(val) >= 20 and (any(c.isdigit() for c in val) or any(c.isupper() for c in val)):
            ln = text[:m.start()].count("\n") + 1
            hits.append(("SECRET-CRED", f"assigned credential `{name}`", ln, f"{name}=<REDACTED {len(val)} chars>"))
    # --- token shapes
    for label, rx in RE_TOKENS:
        for m in rx.finditer(text):
            ln = text[:m.start()].count("\n") + 1
            hits.append(("SECRET-TOKEN", f"known token shape: {label}", ln, f"<REDACTED {len(m.group(0))} chars>"))
    # --- personal information (OPT-IN: PII in a private vault is expected; secrets never are)
    if include_pii:
        for i, L in enumerate(lines, 1):
            for m in RE_EMAIL.finditer(L):
                e = m.group(0)
                if RE_PLACEHOLDER.search(e) or e.lower().endswith(('example.com','test.com','localhost','domain.com','email.com')):
                    continue
                hits.append(("PII-EMAIL", "email address", i, e))
            for m in RE_SSN.finditer(L):
                hits.append(("PII-SSN", "US SSN pattern", i, "<REDACTED ssn>"))
            for m in RE_PHONE.finditer(L):
                if _luhn(m.group(0)) and len(re.sub(r'\D','',m.group(0))) >= 13:
                    continue
                hits.append(("PII-PHONE", "phone-number pattern", i, "<REDACTED phone>"))
            # CARDS: a bare Luhn test over 41k files returned 496 hits — nearly all false (long
            # digit runs in JSON, block numbers, timestamps). Require a plausible network prefix
            # AND a bounded/separated run, so ordinary numbers stop qualifying.
            for m in RE_CC.finditer(L):
                s = m.group(0)
                digits = re.sub(r'\D', '', s)
                if not (13 <= len(digits) <= 19):
                    continue
                if not _luhn(s):
                    continue
                if not re.match(r'^(4|5[1-5]|3[47]|6(?:011|5)|35|2[2-7])', digits):
                    continue                      # not a real card-network prefix
                if not re.search(r'[ \-]', s) and not re.search(r'\b' + re.escape(s) + r'\b', L):
                    continue                      # an unbounded digit run inside a longer number
                hits.append(("PII-CARD", "card number (Luhn + network prefix)", i, "<REDACTED card>"))
    return hits

def scan_paths(paths, include_pii=False):
    findings, scanned = [], 0
    for root in paths:
        if os.path.isfile(root):
            walk = [(os.path.dirname(root), [], [os.path.basename(root)])]
        else:
            walk = os.walk(root)
        for dp, dn, fn in walk:
            # prune by DIRECTORY NAME only. A substring test on the path (e.g. `'/.x' in dp`)
            # silently matches a path that merely CONTAINS it and skips the whole tree — the
            # wrong answer and the right answer then look identical.
            dn[:] = [d for d in dn if d not in SKIP_DIR]
            for f in fn:
                if os.path.splitext(f)[1].lower() in SKIP_EXT: continue
                p = os.path.join(dp, f)
                try:
                    if os.path.getsize(p) > 3_000_000: continue
                    t = open(p, 'r', errors='ignore').read()
                except Exception:
                    continue
                scanned += 1
                for cls, label, ln, ex in scan_text(t, include_pii):
                    findings.append({"file": p, "class": cls, "label": label, "line": ln, "excerpt": ex})
    return findings, scanned

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--fail-on-find", action="store_true", help="exit 1 if anything is found (preflight gate)")
    ap.add_argument("--json", metavar="OUT", help="write findings as JSON")
    ap.add_argument("--quiet", action="store_true", help="only print the verdict line")
    ap.add_argument("--pii", action="store_true",
                    help="ALSO scan for personal information (emails/phones/SSNs/cards). "
                         "Off by default: PII in a private vault is expected, secrets never are — "
                         "mixing them is what made the first version too noisy to obey.")
    a = ap.parse_args()

    findings, scanned = scan_paths(a.paths, a.pii)
    by_class = {}
    for f in findings:
        by_class.setdefault(f["class"], []).append(f)

    if not a.quiet:
        print(f"\n   scanned {scanned} file(s) under {len(a.paths)} path(s)")
        if not findings:
            print("   ✅ clean — no secret, credential, token or personal information found\n")
        for cls in ("SECRET-KEY", "SECRET-CRED", "SECRET-TOKEN", "PII-SSN", "PII-CARD", "PII-PHONE", "PII-EMAIL"):
            if cls in by_class:
                print(f"\n   ⛔ {cls} — {len(by_class[cls])} finding(s)")
                for f in by_class[cls][:25]:
                    print(f"      {f['file']}:{f['line']}  [{f['label']}]  {f['excerpt']}")
                if len(by_class[cls]) > 25:
                    print(f"      … and {len(by_class[cls])-25} more")

    if a.json:
        json.dump({"scanned": scanned, "findings": findings,
                   "counts": {k: len(v) for k, v in by_class.items()}}, open(a.json, "w"), indent=1)
        if not a.quiet: print(f"\n   json → {a.json}")

    if not a.quiet:
        hard = sum(len(v) for k, v in by_class.items())
        verdict = "FAIL — do not commit/sync/ship until resolved" if hard else "PASS"
        print(f"\n   VERDICT: {verdict}\n")
    if a.fail_on_find and findings:
        sys.exit(1)

if __name__ == "__main__":
    main()
