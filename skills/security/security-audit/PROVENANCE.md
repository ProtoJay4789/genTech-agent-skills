# Provenance

Vendored from **cloudflare/security-audit-skill** — MIT licensed.

- Source: https://github.com/cloudflare/security-audit-skill
- Commit: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`
- Vendored: 2026-10-19
- License: MIT (see `LICENSE`)

**Do not edit these files in place.** Upstream is Cloudflare's; local changes belong in a
`references/` note that says what we changed and why, so a re-vendor does not silently drop them.

**Verified at vendoring:** both validators' own test suites pass — 34/34 (`validate-findings.test.cjs`)
and 31/31 (`validate-coverage-ledger.test.cjs`), 65 tests total, on Node v26.5.1.

## Local constraint (ours, not upstream's)

The skill wants an **OS-enforced sandbox** — networking disabled, sanitized allowlisted environment,
resource limits, writes only to assigned scratch — before it executes target-controlled code.

We are uid 10000 with no root and no network-namespace control. Therefore:

- **Our own code:** full audit, hunting complete.
- **Untrusted third-party code:** never execute it. Findings stay `needs_validation`, and the report
  must say so rather than implying a sandbox that does not exist.
