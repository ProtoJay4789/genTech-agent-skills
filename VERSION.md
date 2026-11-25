# Version

**261 skills · published 2026-11-25**

```bash
git log -1 --format='%h %ci'
```

## What changed in this release

- **Curated to 261 skills** from a 362-skill internal library. Held back: trading venues, the paid product
  line, people-specific lanes, and housekeeping. The test is on the README: would this make a stranger's agent
  better without needing our venues, our money or our people?
- **Seven duplicate pairs merged** — each absorbed body kept verbatim under `references/<name>/`, each survivor
  carrying an `Absorbed:` line naming what it took in. Nothing deleted to look tidy.
- **Every dangling reference either recovered or declared.** 0 undeclared dead citations; 31 declared under
  `## Missing references`, where a reader can see them.
- **Secret + PII preflight on the published tree:** 0 group ids, 0 mesh IPs, 0 hostnames, 0 credentials.
  One test fixture legitimately contains a detector pattern; it is allowed by path, with a written reason.
- **README rewritten.** The previous one described an August 2026 product (identity/execution/audit pillars)
  that this repository no longer contains.
