// BlockRun GPT Image 2 img2img edit — direct SDK, no MCP tool, no public hosting.
// Verify the SDK path first:
//   ls -d /opt/data/tools/blockrun/node_modules/@blockrun/llm/dist/index.js
// Run from the install root so any bare imports resolve:
//   cd /opt/data/tools/blockrun && node /path/to/this-file.mjs
import { ImageClient } from '/opt/data/tools/blockrun/node_modules/@blockrun/llm/dist/index.js';
import { readFileSync, writeFileSync } from 'node:fs';

// ---------------- CONFIG ----------------
const SRC = '/opt/data/profiles/<seat>/image_cache/<source>.jpg';   // local path is fine here
const OUT = '/opt/data/profiles/<seat>/image_cache/<output>.png';
const MODEL = 'openai/gpt-image-2';   // ~$0.064 per 1024x1024 edit (measured)
const SIZE = '1024x1024';             // portrait sizes are NOT supported on this lane
const PROMPT = `
KEEP EXACTLY UNCHANGED: <face shape, skin tone, hair, beard connection, eyewear, expression, head angle>; same age, same pose; do not alter his features, ethnicity or body.
CHANGE (setting and wardrobe only): <new costume, materials, accents — and what replaces each old gear element>.
BACKGROUND: <new world, 3-4 objects, one light direction>.
STYLE: photorealistic cinematic film still, 35mm anamorphic, shallow depth of field. ABSOLUTELY NO TEXT, NO LOGOS, NO WATERMARKS.
`;
// ----------------------------------------

const key = readFileSync('/opt/data/.blockrun/.session', 'utf8').trim();
const client = new ImageClient({ privateKey: key });          // zero ETH balance is fine — no payer gas needed
const uri = `data:image/jpeg;base64,${readFileSync(SRC).toString('base64')}`;

const res = await client.edit(PROMPT, uri, { model: MODEL, size: SIZE });
// response keys: id, created, data, price, usage, payment  — there is no `cost_usd` in this build
console.log('price/usage:', JSON.stringify(res.price ?? res.usage ?? null));

const item = (res.data && res.data[0]) || res;
if (item.b64_json) writeFileSync(OUT, Buffer.from(item.b64_json, 'base64'));
if (item.url) {
  const r = await fetch(item.url);                 // download first; don't feed the CDN url straight to vision
  writeFileSync(OUT, Buffer.from(await r.arrayBuffer()));
}
console.log('wrote', OUT);
// Receipt: query USDC balanceOf before and after the run — that delta is the real charge.
// Keep a copy of the source beside the output (<name>_source.jpg) so each edit stays comparable.
