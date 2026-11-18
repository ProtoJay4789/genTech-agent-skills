#!/usr/bin/env python3
"""
resolve_name.py — speech-to-text name resolution for the GenTech fleet.

Why this exists: voice messages mangle our OWN proper nouns ('Jintek Mauston' for
'GenTech Milestone'). An agent that takes a mangled name literally goes hunting the
brain for a product that was never called that, and reports "not found" — a false
negative dressed as a finding.

Rule it enforces: resolve a noun BEFORE searching. A name returning zero hits is more
often misheard than missing.

Stdlib only. Deterministic. Exit codes:
  0 = resolved to a canonical name
  1 = no known variant matched (report as UNKNOWN, do NOT guess)
  2 = the map could not be read (fail loud, never silent)
"""
import json, os, sys, unicodedata

DEFAULT_MAP = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "variants.json"
)


def _norm(s: str) -> str:
    """Lowercase, strip accents, collapse punctuation/whitespace so 'Gen-Tech' == 'gen tech'."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c if (c.isalnum() or c.isspace()) else " " for c in s)
    return " ".join(s.lower().split())


def load_map(path=None):
    path = path or os.environ.get("NAME_VARIANTS", DEFAULT_MAP)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_index(doc):
    idx = {}
    for ent in doc.get("entities", []):
        canon = ent["canonical"]
        idx[_norm(canon)] = (canon, ent.get("kind", ""), "canonical")
    # Variants second, and never allowed to overwrite a canonical entry — a variant that
    # normalises to its own canonical (e.g. 'Arthur' vs 'arthur') must not relabel the
    # canonical match as a mishearing. setdefault, not assignment.
    for ent in doc.get("entities", []):
        canon = ent["canonical"]
        for v in ent.get("variants", []):
            idx.setdefault(_norm(v), (canon, ent.get("kind", ""), "variant"))
    return idx


def resolve(term, idx):
    """Return (canonical, kind, how) or None. Exact-normalised match only — no fuzzy guessing."""
    return idx.get(_norm(term))


def main(argv):
    if len(argv) < 2:
        print("usage: resolve_name.py <term> [term ...]", file=sys.stderr)
        return 1
    try:
        idx = build_index(load_map())
    except Exception as exc:                       # noqa: BLE001 - fail loud
        print(f"UNKNOWN: map unreadable ({exc})", file=sys.stderr)
        return 2

    rc = 0
    for term in argv[1:]:
        hit = resolve(term, idx)
        if hit:
            canon, kind, how = hit
            tag = "" if how == "canonical" else f"  (was a mishearing of {kind})"
            print(f"{term}  ->  {canon}{tag}")
        else:
            print(f"{term}  ->  UNKNOWN  (no known variant — report it, do not guess)")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
