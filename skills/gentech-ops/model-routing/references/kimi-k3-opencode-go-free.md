# Kimi K3 on OpenCode Go — RE-VERIFIED 2026-10-23, with the exact model id

## Verdict (updated 2026-10-23)
Kimi K3 is reachable through our **OpenCode Go** provider — **and the current model id is
`kimi-k3.1-pro`**, not `kimi-k3-pro` (which 400s `"Model is unavailable"`).

**Measured 2026-10-23, same key, same minute:**
| model id | result |
|---|---|
| **`kimi-k3.1-pro`** | ✅ **200** — the one to use |
| `kimi-k3` | ✅ 200 — still serves |
| `kimi-k2.6` | ✅ 200 |
| `kimi-k3-pro` | ❌ 400 `"Model is unavailable"` — wrong id |

## The two mandatory headers (this is why the rail looked dead in September)
```
-H "x-opencode-session: <stable value>"     # without it: 400 MissingSessionID, and uncached-token pricing
-H "User-Agent: Mozilla/5.0 ..."            # without it: 403 Forbidden (Cloudflare bot block)
```
> ⚠️ **The September 2026 note that "opencode-go returned 403 Forbidden" and therefore Ollama Cloud was the
> working rail is superseded.** The 403 was **intermittent and almost certainly a User-Agent block** — the
> routing skill already documents *"a 403 from this API is usually your UA, not your key."*
> **The `senior-audit-kimi-k3` skill carried the stale version and would have routed a seat around a rail
> that answers 200. Corrected 2026-10-23.**

## The false-empty trap — re-confirmed
A **30-token** probe returned **HTTP 200 with `content: None`**: the model burned the whole budget on
internal reasoning. **For an audit, budget 16000.** `content: None` means *under-budgeted*, not *broken*.

## Failover: the SAME model is on the Nous portal
**`moonshotai/kimi-k3.1-pro` is present in the Nous model list (426 models, measured 2026-10-23) and answers 200.**
That makes the allowance failover clean — **the same model, one config change.**
⚠️ **METERED:** `x-nous-credits-remaining-usd: 17.28` of a `22.00` cap; **`x-nous-tool-pool-gated-off: true`.**
**Price it before committing — it is a second, smaller ceiling, not free runway.**

## Live verification (Aug 15, 2026)
Direct API call succeeded and reported `"cost":"0"`:

```bash
KEY=$(grep -oE 'OPENCODE_GO_API_KEY=.*' ~/.hermes/profiles/gentech/.env | cut -d= -f2)
curl -s -X POST "https://opencode.ai/zen/go/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"kimi-k3","messages":[{"role":"user","content":"Reply with exactly: KIMI_K3_OK"}],"max_tokens":100}'
```
Result: `content: 'KIMI_K3_OK'`, `model: kimi-k3`, `cost: "0"` (or `None` in some response shapes).

## Why this works
`kimi-k3` is already in the opencode-go provider's models array in `config.yaml` (line ~16):
```
models: ["deepseek-v4-flash","deepseek-v4-pro","kimi-k2.7-code","kimi-k3","glm-5.2","glm-5","qwen3.7-plus"]
```
And `OPENCODE_GO_API_KEY` is already set in `~/.hermes/profiles/gentech/.env`. Nothing new to install or configure.

## Provider status matrix (all three setups checked Aug 15, 2026)
| Setup | Kimi K3 | Use? |
|-------|---------|------|
| **OpenCode Go** | ✅ AVAILABLE + FREE (cost 0) | **Best route** for coding + web-design work |
| **Ollama Cloud** | ⚠️ `kimi-k3:cloud` but NOT in any sub tier (even Max) — PAYG extra credits | Avoid while conserving the weekly reset |
| **Nous Portal** | ✅ Listed in Hermes catalog (`moonshotai/kimi-k3`) | Native sub path; second choice |

## Known caveat
`opencode run --model opencode-go/kimi-k3` (the CLI) returned `UnknownError: Unexpected server error` on first attempt. The **direct API call is the reliable path**. The CLI model-name format for K3 is still unpinned — retest after an OpenCode CLI update or with a bare `kimi-k3` name.

## Two-birds-one-stone
This route both (a) gives access to K3's premium web-design capability (the viral "13-min website" trick) AND (b) routes coding work through a free provider instead of burning Ollama Cloud's weekly cap. Aligns with conserving usage until the next reset.

*Recorded 09-Green Room/kimi-k3-access.md in the vault as well.*
