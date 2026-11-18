# Authoring a Hermes plugin (memory provider, tools, hooks)

How to build a plugin against the real API — not the docs' description of it. Read the shipped source of a
bundled plugin before writing one: **`/opt/hermes/plugins/memory/<name>/__init__.py`** and
`/opt/hermes/agent/memory_provider.py` are the contract. The docs are the map; the ABC is the law.

## 1 · Layout and registration

```
$HERMES_HOME/plugins/<name>/
  plugin.yaml      # name, version, description, config_keys
  __init__.py      # def register(ctx): ...
  README.md
```

`register(ctx)` is the only entry point. It hands you a context object with registration calls:

| call | registers |
|---|---|
| `ctx.register_memory_provider(provider_instance)` | a memory backend |
| `ctx.register_tool(...)` | a model-facing tool |
| hooks (`on_*`) | lifecycle callbacks |

`plugin.yaml` needs `name`, `version`, `description`; `config_keys` names the `config.yaml` blocks the plugin
reads. A plugin runs in the plugin host (`plugins.isolation: host`) unless you build for isolation — verify
which you got from the validator's Isolation line rather than assuming.

## 2 · The gates — pass them, then test behaviour

```bash
hermes plugins validate <plugin-dir>   # schema, file layout, security scan, core-override check
hermes plugins doctor   <plugin-dir>   # runtime discovery → import → registration
```

**Both green means the plugin LOADS. Neither says it WORKS.** `validate` checks form; `doctor` proves the
import chain. Then exercise the primary feature on realistic input and assert on the ANSWER (see
`falsifiable-tests` → *A validator is not a test*). Reporting "validate 15/15" on its own reads as working
to everyone who hears it.

## 3 · Memory provider: the methods that matter

Subclass `agent.memory_provider.MemoryProvider`. The ones the host actually calls:

| member | contract |
|---|---|
| `name` (property) | stable id, matches `memory.provider` |
| `is_available()` / `unavailable_reason()` | cheap config/side-effect-free check, then a human sentence saying what to set |
| `initialize(session_id, **kwargs)` | bind paths **from `kwargs["hermes_home"]`** — never `~/.hermes` |
| `get_config_schema()` / `save_config(values, hermes_home)` | prompt-able fields; write non-secrets into the profile |
| `prefetch(query, *, session_id)` | inline recall injected before a model call |
| `queue_prefetch(...)` | background variant; make it a no-op when retrieval is a local read |
| `system_prompt_block()` | short capability note; return `""` when unavailable |
| `get_tool_schemas()` / `handle_tool_call(name, args, **kwargs)` | your tools; return `tool_error(...)` from `tools.registry` for failures, JSON strings for success |
| `on_memory_write(action, target, content, metadata)` | mirror built-in memory writes |
| `backup_paths()` | dirs the host should include in a profile backup |
| `on_pre_compress(messages, *, require_checkpoint)` | the durable checkpoint (below) |

## 4 · The compression checkpoint — opt into durability, fail closed

By default `on_pre_compress` is **best-effort**: raise and the host logs it and compresses anyway, and the
transcript is gone. That default is wrong for any provider whose job is keeping the record.

```python
class MyProvider(MemoryProvider):
    pre_compress_checkpoint_api_version = 2   # declaring v2 PROMISES: return ⇒ evidence is on disk

    def on_pre_compress(self, messages, *, require_checkpoint=False) -> str:
        ...write atomically, verify by re-read, raise on any failure...
```

With `compression.checkpoint_required: true` the host **blocks** a lossy rewrite when the checkpoint raises.
Rules that make the promise true:

- **Write beside, `fsync`, `os.replace`.** A crash mid-write must leave the old archive intact and the new
  one absent — a truncated file that reads as complete is worse than a refusal.
- **Verify by re-reading** (message count equal) before returning. A checkpoint you did not read back is a claim.
- **Never return partial success.** Raise; do not report "saved" for a half-written transcript.

## 5 · Pitfalls that cost real time

- **Do not create dirs in `initialize()` that can fail.** Measured: `initialize()` created the checkpoint
directory, so an unwritable archive path **took the provider down at agent startup**, before any compression
had happened. The failure belongs at *compression* time, where `require_checkpoint` can decide what to do.
Failing early converts "archiving is broken" into "memory is broken".
- **Bind every path from `hermes_home`.** One gateway can serve several profiles; a provider instance belongs
to exactly one and must never hardcode `~/.hermes` or rebind per call.
- **A mirror must never raise into the turn.** Wrap `on_memory_write` in `try/except` and log at debug —
failing to copy a note must not fail the agent's reply.
- **Invalidate the cache on write.** A read-through cache that survives a write makes the note you just
  saved invisible to the next search, which looks exactly like a broken store.
- **Read the response's error branch, not just the missing field** — see `falsifiable-tests` on errored-vs-empty.
- **`tool_error` is the error channel.** Returning a plain string for a failure makes the host treat a
  refusal as data.

## 6 · Retrieval without a dependency

A file-backed provider needs no embeddings to beat keyword matching, and no vendor to be honest about its
limits. BM25 is ~15 lines: corpus doc-frequencies give IDF, term-frequency saturates (`k1`, `b`), and the
score sums per query term. Two things it will not do on its own:

- **Inflection.** `settle` ≠ `settles` ⇒ score 0.00 on the right document. A crude suffix fold (plural,
  `-ed`, `-ing`, `-er`, `-ation`, trailing `e`) fixes the common English cases at the cost of occasional false
  merges. State that trade in the README rather than implying semantic recall.
- **Paraphrase.** Terms that never co-occur will never match. Say so; pointing at embeddings without taking
  the dependency is the honest shape.
- **Score whole LINES for the snippet, not the first character window.** The first hit is usually the H1, so
  a window returns `# Title **Saved:** …` and the caller never sees the sentence that answers them. Skip
  generated header lines (title, saved-at, tags) and return the line carrying the most query terms.

Rank against a **decoy**: a document that repeats a common query word many times must lose to the relevant
one. That assertion is what turns "returned something" into "chose right".

## 7 · Shipping it: the catalog, not the official repo

**`NousResearch/hermes-official-plugins` is Nous-maintained — a third-party plugin does NOT PR there.**
Its own CONTRIBUTING says so: *"Official plugins are maintained by Nous Research … Third-party plugins
belong in their author's repo and enter the plugin catalog from there."* The door is one YAML added to
**`:plugin-catalog/<name>.yaml` in the `hermes-agent` repo**, merged by a human.

Copy a neighbouring entry rather than inventing the schema (`agentmemory.yaml`, `agentvault.yaml`):

```yaml
name / title / repo / sha / subdir / version / description / maintainer
tier: community / category / requires_hermes / docs_url / readme: true
platforms: [...] / capabilities: {provides_tools, provides_hooks, provides_middleware, requires_env}
known_issues: ["..."]        # quote each item — an unquoted `key: value` inside a list item is a YAML error
```

Admission rules that change what you BUILD, not just what you submit:

- **Full 40-character SHA.** Branches, tags and short SHAs are rejected by the loader.
- **No self-updating code** — no in-app "check for updates", no remote loader. The SHA pin *is* the trust model.
- **Owner or major contributor only.** Drive-by submissions of somebody else's repo are declined, so the
  repo has to exist under the account that opens the PR.
- **Declared capabilities must match what actually registers.** Undeclared creep is handled as a security issue.
- **`hermes plugins validate` runs at admission** — `dangerous` blocks, `caution` is read by a reviewer first.
- **`description` carries a `Disclosure —` sentence** naming what is stored, where, and what leaves the
  machine. Write it deliberately; it is the paragraph a reviewer reads closest.

Two traps:

- **A memory provider declares `provides_tools: []`.** Tools returned by `get_tool_schemas()` are not
  `ctx.register_tool` registrations, and the validator reports *"no tools to check"*. Declaring them invents
  capability the admission rule then reads as a mismatch.
- **`requires_hermes` must be a build you actually ran.** In a container image `pyproject.toml` can read
  `version = "0.0.0"`; take the real value from `hermes --version` and pin the floor to THAT, putting the
  older-build degradation into `known_issues` instead of guessing a version you never tested.

## 8 · Prove the behaviour through the HOST, not just your object

Green `validate` + `doctor` prove the plugin LOADS. To prove the feature, drive the host's own code path:
for a memory provider, construct `MemoryManager()`, assign `mgr._providers = [provider]`, and call
`mgr.on_pre_compress(messages, require_checkpoint=True)` yourself. Three runs, same transcript:

| archive | `require_checkpoint` | expected |
|---|---|---|
| writable | `True` | archive written, count verified by re-read |
| unwritable | `True` | **the host raises** → the lossy rewrite is blocked |
| unwritable | `False` | returns `""` → logged, compression proceeds, transcript **lost** |

The third row is what makes the result persuasive: it proves the config line is load-bearing rather than
decorative. Also confirm the host will even forward your kwarg — it only passes `require_checkpoint` when
`agent.memory_manager._accepts_require_checkpoint(provider.on_pre_compress)` says the signature takes it.

**An exception you raise reaches an operator, so name the consequence.** A bare `FileNotFoundError` from a
missing checkpoint directory says nothing about what is about to be lost; raise a `RuntimeError` that states
what failed to happen and which setting decides the outcome.

## 9 · Demo it deterministically

**Record a script, not ad-hoc typing.** A `demo.py` that builds its own throwaway corpus, prints one
section per scene, and runs the host-path cases rehearses the exact output before the camera (and leaves a
reviewer something re-runnable). Improvised terminal typing risks a live empty result on camera and proves
nothing afterwards. Back it with a `tests/` suite whose cases each assert a behaviour that was **observed
broken first** — the inflection miss, the decoy out-ranking the answer, the unwritable archive that must
raise — so the suite documents the defects instead of restating the implementation.
