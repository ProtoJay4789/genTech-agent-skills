# BlockRun music lane — song generation, the async traps and the charges

Depth for the `minimax/music-2.5+` song/instrumental lane. Everything here was measured on a real render,
not read off a doc.

## Call it

Script: `/opt/data/profiles/protojay/scripts/blockrun-music.mjs` (copy per seat; it hardcodes the shared
`/opt/data/tools/blockrun/node_modules/@blockrun/llm` install and reads `/opt/data/.blockrun/.session`).

```bash
cd /opt/data/tools/blockrun && node <path>/blockrun-music.mjs out.mp3 \
  "cinematic podrace theme, tribal percussion, brass stabs, desert wind" \
  --instrumental --duration 30
# with vocals: --lyrics-file lyrics.txt   (omit --instrumental)
```

Endpoint: `POST https://blockrun.ai/api/v1/audio/generations`
Body: `{model, prompt, lyrics?, instrumental?, duration_seconds?}`. Model list: `GET /api/v1/audio/models`
(**not** `/api/v1/music/models` — that 404s with `unknown_endpoint`).

## Four things that will bite you

1. **It is asynchronous and the SDK does not poll it.** `MusicClient.generate()` returns
   `202 {status:"queued", poll_url:"/api/v1/audio/generations/<id>", payment_status:"verified"}` with
   **no url**. `ImageClient` has `pollImageJob()`; `MusicClient` has nothing. Poll yourself.
2. **`poll_url` is RELATIVE.** `fetch("/api/v1/audio/generations/<id>")` throws
   `TypeError: Failed to parse URL` / `ERR_INVALID_URL`. Prefix `https://blockrun.ai`.
3. **The poll endpoint answers 402 without a payment header.** Message: *"a fresh signature from the
   same wallet works"* — the server binds payer→job. Re-sign with `createPaymentPayload` from the 402's
   `accepts` and send it as `PAYMENT-SIGNATURE` (and `X-PAYMENT`) on every poll. Settlement happens on the
   first poll returning `completed`, so the track is charged **once** (~$0.20). Wallet balance is the check:
   submit alone moves nothing; only a completed poll does.
4. **`duration_seconds` is advisory.** Asked 30 s, got 94.7 s; asked 60 s (with lyrics), got 91.6 s. `ffprobe`
   the result — never quote the request as the length. Both renders finished in 61–75 s.
   Output is consistently **loud and near-clipping** (peak +0.6 to +0.8 dBFS, −10.3 LUFS): pull ~1 dB off with
   `ffmpeg -af "volume=-1dB"` before layering anything under it.

Response: `202` while generating (status queued/in_progress), then
`200 {status:"completed", url:"https://blockrun.ai/api/media/media/audios/..."}`. Download immediately —
CDN URLs expire (~24 h).

**Re-polling a settled job is free** — verified: a second signed poll on a completed job returned
`completed` with the same URL and the wallet balance did not move. So a crashed/orphaned client can always
be recovered from its `poll_url` without paying again; only the first completed poll settles.

Renders take 60–120 s; run it backgrounded with notify, don't sit on it in the foreground.
