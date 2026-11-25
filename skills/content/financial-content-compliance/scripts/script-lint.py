#!/usr/bin/env python3
"""script-lint.py — mechanical gate for finance content before any voice is generated.

Enforces the compliance shape: no second-person prescription, no certainty language, and the three spoken
statements present. It is a lint, not a lawyer: it cannot tell you a sentence is legal, only that it has the
shape we agreed to.

Usage:  python3 script-lint.py <script.txt> [--json]
Exit:   0 clean · 1 blocking findings · 2 missing required block
"""
import json
import re
import sys

BLOCK_PHRASES = [
    # second-person prescription / directed calls
    "you should", "you must", "you need to", "you ought", "you have to",
    "i recommend", "we recommend", "i suggest you", "my recommendation is",
    "consider buying", "consider selling",
    "this is a buy", "this is a sell", "buy this", "sell this",
    "go long", "go short", "take profits", "take profit now",
    "add to your position", "cut your losses",
    "copy this", "copy my trades", "copy our trades", "follow my trades",
    "dm me", "message me", "ask me in the chat", "tell me your bag",
    # certainty / performance promises
    "guaranteed", "guarantee", "risk-free", "risk free", "can't lose",
    "cannot lose", "no downside", "sure thing", "will hit", "will pump",
    "will moon", "to the moon", "100% safe", "safe bet",
    # affiliation / signal framing
    "signals", "signal group", "trade alerts", "our calls are",
]

WARN_PATTERNS = [
    (r"\b(buy|sell|long|short)\b", "trade verb — allowed only about our own completed action, check the subject"),
    (r"\brecommend\w*\b", "the word 'recommend' itself"),
    (r"\badvice\b", "the word 'advice'"),
    (r"\bshould\b", "modal 'should' — check who it is aimed at"),
    (r"\b\d+\s?%\s*(per|a)\s*(week|month|year)\b", "return-rate claim"),
    (r"\b(always|never)\b", "absolutist language"),
]

REQUIRED = [
    ("position card", [r"\bwe hold\b", r"\bwe hold none\b", r"\bwe don't hold\b", r"\bwe do not hold\b"]),
    ("as-of stamp", [r"\bas of\b"]),
    ("payment disclosure", [r"\bnobody (paid|pays) us\b", r"\bwe are paid\b", r"\bwe're paid\b",
                            r"\bsponsor", r"\baffiliate", r"\bwe sell\b", r"\bour product\b"]),
    ("non-personalisation", [r"\bnot (a )?recommendation\b", r"\bnot tailored to you\b",
                             r"\bnot advice for you\b", r"\bnot personalised\b", r"\bnot personalized\b"]),
]


def lint(text):
    low = text.lower()
    findings = []
    for phrase in BLOCK_PHRASES:
        for m in re.finditer(re.escape(phrase), low):
            findings.append({"severity": "BLOCK", "rule": phrase,
                             "line": low.count("\n", 0, m.start()) + 1,
                             "ctx": text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")})
    for pat, why in WARN_PATTERNS:
        for m in re.finditer(pat, low):
            findings.append({"severity": "WARN", "rule": why,
                             "line": low.count("\n", 0, m.start()) + 1,
                             "ctx": text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")})
    missing = [name for name, pats in REQUIRED if not any(re.search(p, low) for p in pats)]
    return findings, missing


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not args:
        print("usage: script-lint.py <script.txt> [--json]")
        return 2
    text = open(args[0], encoding="utf-8").read()
    findings, missing = lint(text)
    blocks = [f for f in findings if f["severity"] == "BLOCK"]
    warns = [f for f in findings if f["severity"] == "WARN"]

    if as_json:
        print(json.dumps({"file": args[0], "block": blocks, "warn": warns,
                          "missing_required": missing,
                          "verdict": "FAIL" if blocks or missing else "PASS"}, indent=2))
    else:
        print(f"file: {args[0]}  ({len(text)} chars)")
        for f in blocks + warns:
            print(f"  [{f['severity']}] line {f['line']:<4} {f['rule']}\n        … {f['ctx']} …")
        if missing:
            print("  [MISSING] required block(s): " + ", ".join(missing))
        print(f"\n  BLOCK {len(blocks)} · WARN {len(warns)} · MISSING {len(missing)}")
        print("  VERDICT: " + ("FAIL" if (blocks or missing) else "PASS (shape only — not legal review)"))

    if blocks:
        return 1
    if missing:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
