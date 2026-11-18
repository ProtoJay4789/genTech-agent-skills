---
name: hermes-tool-provider-config
description: "Wire a Hermes tool to a provider; secret + output checks."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [hermes, config, provider, tts, secrets, env, verification]
trigger: "Wiring or re-pointing a Hermes tool's provider; a tool errors '<KEY> not set' right after you set it; writing an API key into .env; a generated artifact (audio/image) must be verified before delivery."
metadata:
  hermes:
    tags: [hermes, config, provider, tts, secrets, env, verification]
    related_skills: [hermes-auxiliary-config, safe-update-restart, backup-and-restore-drills]
---

# Wiring a Hermes Tool to a Provider

A Hermes built-in tool (TTS, vision, media generation, web extraction) is **provider-driven**: it runs
whatever backend its config names. Its stock default is often a weak fallback, so "this tool can't do X"
is usually a **config fact you haven't checked yet**, not a limitation. Check the config before believing
the limitation.

## When to Use

- A tool errors `<KEY> not set` **immediately after** you wrote that key to `.env`.
- You are wiring or re-pointing a tool's provider: TTS, vision, media generation, web extraction.
- You need to put an API key into a profile `.env` (see `scripts/set_env_key.py`).
- You must prove a generated artifact (audio, image, video) is real before delivering it.
- You are about to **restart a gateway** so a config change takes effect — check the env section first.

---

## The two layers — settings vs secret

| Layer | Goes in | Set with |
|---|---|---|
| Provider, model, voice id, timeouts | `config.yaml` | `hermes config set <dotted.key> <value>` |
| API keys and tokens | the profile `.env` | argv to a script (see below) |

```bash
hermes config get <section>      # READ the whole block first — never assume a key's name or default
hermes config set tts.provider elevenlabs
hermes config env-path           # where this profile's .env lives
```

**Resolve, never assume.** Read the existing value with `hermes config get` before and after a change: a
`set` that landed under the wrong parent looks exactly like one that worked (see Pitfalls).

**Never hand-edit `config.yaml`.** It is whitespace-sensitive and a stray indent breaks the live gateway;
the file is also protected against direct `patch`/`write_file` (you will get a refusal). Use `hermes config
set`/`unset` — and then **read the section back**, because `set` writes whatever dotted path you gave it and
will happily create a new key beside the one the tool actually reads.

### Targeting a PROFILE — it is `HERMES_HOME`, not `HERMES_PROFILE`

```bash
HERMES_HOME=/opt/data/profiles/<seat> hermes config set <key> <value>   # ✅ the seat's own config
HERMES_HOME=/opt/data              hermes config set <key> <value>   # ✅ the default profile
```

**⚠️ `HERMES_PROFILE` is silently ignored by `hermes config`.** It does not error — it just writes to the
default/active profile anyway, so a loop over four seats produces four successful-looking messages and **one
file actually written**. The only trustworthy confirmation is the **path the command prints** (`✓ Set … in
…/config.yaml`). Read that path, not the variable you set, and treat any `get`/`set` run with the wrong
selector as measuring one file N times — which silently invalidates whole per-profile verifications.

### A config block can exist and still be INERT

A `provider:` line only means something if the section is a real schema key that a plugin reads. Before
wiring, confirm the section is schema-known and the plugin has a credential:

```bash
# is the section in the schema at all? `None` here means the tool is reading NOTHING
/opt/hermes/.venv/bin/python -c "from hermes_cli.config import load_config; print(load_config().get('<section>'))"

# which providers does the plugin actually ship?
ls /opt/hermes/plugins/<tool_family>/          # e.g. image_gen/: fal, krea, openai, xai, deepinfra …
```

**A section absent from `DEFAULT_CONFIG` returns `None` even though the YAML visibly contains it**, because
unknown top-level keys are not carried through. The tool is then provider-less while the file reads as
configured — the exact silent shape this whole audit hunts. And provider selection is **credential + plugin**,
not the `provider:` line: a family with no key anywhere has no lane, whatever the line says.

---

## 🔴 Config hot-reloads; the process's ENVIRONMENT does not

This is the one that costs an hour. Provider/model changes take effect live. **A credential added to `.env`
after the process started does not** — the process read its environment once at startup. So the tool keeps
failing `… API_KEY not set` while the file on disk is verifiably correct, and `hermes config set` on the
provider cannot fix it: the provider is fine, the *credential* is absent from the live environment.

Confirm the diagnosis instead of guessing (pid 1 in a container is usually the Hermes process):

```bash
tr '\0' '\n' < /proc/<hermes-pid>/environ | grep -c '^ELEVENLABS_API_KEY='
# 0  => the process predates your write. Config and .env are RIGHT; the process is stale.
# >=1 => the process has it; the failure is elsewhere (wrong scope, wrong key, provider error).
```

**Deliver that one task through the provider's REST API directly** rather than restarting the gateway. A
restart to produce a single voice note or image is a large risk for a small outcome (`safe-update-restart`).
The config and `.env` are already correct; they apply at the next natural restart.

---

## Writing the secret safely

**Use `scripts/set_env_key.py` — never build an `.env` writer from an unquoted shell heredoc.**

```bash
python3 scripts/set_env_key.py /opt/data/profiles/<profile>/.env ELEVENLABS_API_KEY "$KEY"
```

Why: `python3 - <<PY` (a heredoc whose delimiter is **unquoted**) lets the shell expand `$` **inside your
Python source**. A regex containing `$'` is silently rewritten, the write never lands, and the script still
prints its own success message. Quote the delimiter (`<<'PY'`) or, better, keep the payload in a file and pass
data as **argv** so the shell's parser never touches it.

The script sets the key atomically and then **re-reads the file** to assert exactly one `KEY=` line exists.

### The independent-reader rule

**A writer's own success message is not evidence.** After any write to a file that a reader will consume,
re-read it with a *separate* read — a different tool, or at least a fresh open of the file on disk. When the
writer and the reader disagree, **the disagreement is the finding**, and reporting on a single check is how a
broken `.env` gets shipped. Two checks that agree mean something; one check never does.

---

## Proving the artifact is real

The same rule applies to generated output. **`HTTP 200` plus a plausible byte count is not proof of valid
output** — an error payload saved with `-o file` is a 200 in many APIs.

```bash
head -c 4 out.mp3 | xxd        # 'ID3' / MPEG frame-sync => real audio; '{' or '[' => you saved JSON
file out.mp3                   # second, independent read
```

Reconcile the size against the input as a third check (audio ≈ 130 bytes/s at 112 kbps; ~1 MB for ~2 min).
A size that does not match the script length means truncation, not success.

---

## Worked example — TTS to a cloned voice

`text_to_speech` defaults to `edge`, which **discards a cloned voice's character**. Point it at ElevenLabs
and it speaks any cloned voice on the account directly, no curl wrapper:

```bash
hermes config set tts.provider elevenlabs
hermes config set tts.elevenlabs.voice_id <voice_id>
hermes config get tts                 # full block: every provider's keys, model ids, voice ids
```

Delivering while the process is stale (see the env section above) — same voice, same generation:

```bash
curl -s -o out.mp3 -X POST "https://api.elevenlabs.io/v1/text-to-speech/<voice_id>" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" -H "Content-Type: application/json" \
  --data-binary @script.json
# script.json: {"model_id":"eleven_multilingual_v2","voice_settings":{...},"text":"..."}
```

Send a long script with `--data-binary @file`, **never** `-d '…'` — a 300-word script inside a shell `-d` is
a quoting minefield, and the shell will eat characters you did not intend.

---

## 🔴 A secret write returning 200 proves the WRITE, not that anything READS it

Binding secrets through a provider's API (Cloudflare Workers secrets, a vault, a keyring) reports success per
slot. That tells you the value is stored. It says nothing about whether the running code has a **binding for the
selector** that points at it. Measured shape: three keys bound `200 ok` while the service's own `/health` named a
*different* provider — the code defaults to one backend unless an explicit selector secret is present, and that
selector was **not bound at all**. The install looked perfect and changed nothing.

So verify in this order, and stop at the first disagreement:

```bash
# 1 · which secret NAMES are bound (names only — never print values)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/scripts/$WORKER/secrets" \
  | python3 -c "import sys,json;print(sorted(x['name'] for x in json.load(sys.stdin)['result']))"

# 2 · what the LIVE service says it is actually using
curl -s https://<service>/health | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('facilitator') or d.get('provider'))"
```

**If step 2 names something other than the credentials you just installed, the install is staged, not live.**
Say exactly that: which keys are bound, which selector is missing, and which backend is serving today. Do not
report "installed and working" from step 1 alone — the value is in a slot nothing reads.

### Validate the checker's own probe before believing its verdict

An install script ships with a hardcoded probe path and a two-way verdict (`402` = alive, `500` = broken).
**A retired endpoint returns `404`, which is neither**, so the script prints an inconclusive result and the
operator reads it as failure. Before acting on any probe, exercise its path by hand once; if the path is gone,
the instrument is wrong, not the rail. Verify against a route that is still advertised, and confirm the negative
case too — a bogus payment header must be **rejected** (`402` + a reason string), because a broken verifier
returns `5xx` and a permissive one returns the payload.

---

## Pitfalls

- **Concluding "the tool can't do X" from its default behaviour.** The default backend is a config value.
  Read `hermes config get <section>` before reporting a limitation; a one-key change is common.
- **A `hermes config set` that landed under the wrong parent.** `set` writes the dotted path verbatim and
  creates a NEW key if the parent is wrong — no error, and the tool keeps reading the old one. Read the
  section back afterwards and confirm only one reference exists.
- **Piping a command and trusting the exit code.** `cmd | tail -3` reports the **pipe's** status (0) and
  hides the command's own failure. Never read `$?` after a pipe; never let a pipeline's success stand in for
  the action's success.
- **Validating output by HTTP status or byte count alone.** Check the magic bytes, then a second independent
  signal. A saved error body is a 200.
- **`grep KEY .env` matches the COMMENTED line.** `# FAL_KEY=…` satisfies a bare `grep -q FAL_KEY`, so a
  credential check reports "present" for a tool that has no credential at all. Anchor it:
  `grep -q '^KEY=' .env || echo ABSENT`. **A keyword match is not a fact** — read the line, and confirm the
  value is non-empty. The same file can hold a live key for one tool and a commented placeholder for another,
  which is why the check has to be per-key rather than per-file.
- **A section that is not in `DEFAULT_CONFIG` loads as `None`.** The YAML can contain a whole provider block
  and the tool still reads nothing, because unknown top-level keys do not survive `load_config`. Verify with
  `load_config().get('<section>')`, not with a file grep.
- **Writing a secret anywhere but `.env`.** Not in `config.yaml`, not in a note, not into a repo. A key that
  has been in a repo is burned (`backup-and-restore-drills`).
- **Reporting a secret install as done from the write API's own 200s.** Per-slot success is a write receipt.
  Ask the live service which backend it is using; a missing selector secret means the keys are inert.
- **Trusting a shipped probe's two-way verdict.** A retired probe path answers 404 — neither "alive" nor
  "broken" — and an install script that only knows 402/500 will report a false failure. Test the probe path
  itself first.
