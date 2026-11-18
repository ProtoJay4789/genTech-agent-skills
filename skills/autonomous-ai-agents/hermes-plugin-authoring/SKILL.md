---
name: hermes-plugin-authoring
description: "Use when building, validating or submitting a Hermes plugin."
version: 1.0.0
author: gentech
license: MIT
tags: [hermes, plugin, memory-provider, catalog, validation, checkpoint]
metadata:
  hermes:
    tags: [hermes, plugin, memory-provider, catalog, validation, checkpoint]
    related_skills: [hermes-agent, fleet-compatible-skills]
---

# Authoring a Hermes plugin

Building a plugin is three separate jobs and they fail differently: **registering** (does the host find and
load it), **behaving** (does the host do the right thing when your code refuses), and **admitting** (will the
catalog take it). The docs describe the API; this file is the order that gets a plugin census-clean, plus
the traps that pass every test while being wrong.

## When to Use

- Writing a plugin: memory provider, tool provider, platform adapter, context engine, cron provider.
- Auditing or porting an existing plugin to the current checkpoint/contract version.
- Submitting to the plugin catalog, or bumping a catalog pin.

## Procedure

1. **Scaffold from a bundled plugin of the SAME kind** — not from scratch, and not from docs prose.
   `ls /opt/hermes/plugins/<kind>/` gives a working example per kind (`memory/`, `platforms/`, `image_gen/`).
   Read its `plugin.yaml` and its `register(ctx)`; those are the two things a hand-written manifest gets wrong.
2. **Manifest with only keys the validator knows.** An unknown key is a silent no-op, not an error — so a
   typo'd declaration reads as "declared nothing".
3. **Validate first:** `hermes plugins validate <dir>`. Same gate as the catalog CI, including a
   **capability probe** (`register()` executed in isolation) and a **security scan**. `dangerous` fails
   admission; `caution` is a warning a reviewer reads.
4. **Prove runtime load, which validate does not:** `hermes plugins doctor <dir>` → expects *"runtime
   discovery, manifest parsing, import, and registration passed"*.
5. **Exercise the contract through the HOST**, not by calling your own method (see pitfalls).
6. **Only then** package for the catalog.

## Pitfalls — each with the mechanism

- **Calling your own method proves your code runs; it proves nothing about the host's policy around it.**
  A host wraps provider calls in policy — retries, best-effort swallowing, version gating, redaction. Test
  through the object that will call you in production (`MemoryManager`, the adapter, the engine), then assert
  on the host's OUTCOME. A provider that raises correctly, inside a host that treats providers as
  best-effort, has a defect no method-level test can see.
- **A declared version attribute is worthless unless the host reads it — and the host may also require a
  matching signature.** Check the host source for the attribute name and for how it decides to pass extra
  kwargs; a keyword the host never sends, or never sends because your signature does not accept it, leaves
  the stronger behaviour silently off while every test on your side passes.
- **Never do eager filesystem work in `initialize()`.** Creating an output or checkpoint directory there
  means an unusable path takes the whole provider down at agent startup — before the feature was ever asked
  for. Defer to the moment of use, where a failure can be refused and reported.
- **Verify an archive by re-reading it, and make partial failure impossible.** Write beside the target,
  `fsync`, rename, then re-read and assert the record count. A half-written archive that looks complete is
  worse than a refusal, because nothing downstream can tell the difference.
- **Mirror, never merge, when installing a plugin over an existing copy.** A merging copy leaves files the
  destination has and the source lacks, so the trees never match and every later install re-reports drift.
  Temp-dir copy, then swap.
- **Backups taken inside a scanned tree become plugins.** A `<name>.bak-<stamp>` directory holding a manifest
  is discovered and registered as a second live plugin with a nonsense name. Keep backups out of the tree.

## Catalog admission — the rules that reject an otherwise-working plugin

The entry is not part of your repo: it is one YAML file per plugin in the Hermes agent repo under
`plugin-catalog/<name>.yaml`, added by **PR**, human-merged.

- **Third-party plugins do NOT go into the official-plugins repo** — that one is vendor-maintained. Your
  plugin lives in your own repo; only the catalog entry is contributed.
- **A full 40-character commit SHA is mandatory.** Branches, tags and short SHAs are rejected by the loader.
- **Owner or major contributor submits.** Drive-by submissions of someone else's repo are declined, so the
  repo must be one you actually control.
- **No self-updating code.** The pinned SHA *is* the trust model; an updater lets an installed copy move to a
  commit nobody reviewed. Updates arrive as a new SHA-bump PR.
- **Declared capabilities must equal reality.** List the tools/hooks/middleware/env actually registered at the
  pinned commit. A provider that exposes tools through its own schema accessor registers nothing into the
  plugin context — declare the empty list and explain it in the PR, rather than listing tools it never
  registers.
- **Write the disclosure paragraph the other entries write:** what leaves the machine, what is stored and
  where, and whether anything reaches a model provider. An entry without it reads as hiding something.

## Shipping a memory provider specifically

Bundled providers under `plugins/memory/` are the reference implementation. Two contracts matter:

- **The ABC's method set is the whole surface** — name/availability, `initialize` (bind paths from the
  passed home, so one gateway serving several profiles keeps them separate), retrieval (`prefetch` /
  `queue_prefetch`), `system_prompt_block`, write hooks, tool schemas + dispatch, backup paths, shutdown.
- **The pre-compress checkpoint is the second contract.** Default behaviour is *best-effort*: a provider
  that raises is logged and the lossy rewrite proceeds, so a transcript is discarded with only a debug line.
  The only shape that can actually BLOCK the rewrite is a provider that declares the higher checkpoint API
  version, accepts the require-checkpoint signal, and writes a verified archive — and even then only when
  the host config asks for it. State that dependency plainly; do not imply the guarantee is unconditional.

### Retrieval quality — the two defects a "working" search plugin ships with

Both of these pass every structural test (the provider loads, returns hits, and is fast) and both make the
feature useless in the only situation it exists for.

- **Exact-token matching cannot inflect.** A query for *"which chains settle payments"* scores **0.00**
  against a note that says *"settles"* — the store contains the answer and refuses to hand it back, and that
  is the whole reason a ranked-search provider exists instead of a flat file. A deliberately crude suffix
  fold (plural / `-ed` / `-ing` / `-ation`, apply once, keep a 4-char floor) is cheap and fixes the common
  cases; a real stemmer is a dependency most plugins should refuse. Do not ship without it.
- **Test with a DECOY that repeats one query term.** Score a note that shouts the single most common query
  word eight times against the real answer. Under raw term-frequency the decoy wins; under IDF-weighted
  scoring it must reach **zero**. Assert the decoy ranks below the answer — that one fixture is what proves
  the ranking is doing anything.
- **Return the LINE carrying the most query terms, not the character window around the first hit.** The
  first hit is almost always the title or a generated header line, so a first-hit window hands the caller
  `# Note title **Saved:** 2026-…` instead of the sentence that answers the question. Score whole lines,
  skip headings and generated metadata, and return the best line.

## Verification checklist before saying it works

```
hermes plugins validate <dir>     # checks incl. capability probe + security scan
hermes plugins doctor   <dir>     # runtime import + registration
<host-path probe>                 # the contract exercised through the host, BOTH directions:
                                  #   success -> artefact exists AND is verified
                                  #   failure -> host raises / blocks (not silently continues)
```

Report the three separately. "validate passes" and "doctor passes" are statements about the manifest and
about import — never about behaviour.
