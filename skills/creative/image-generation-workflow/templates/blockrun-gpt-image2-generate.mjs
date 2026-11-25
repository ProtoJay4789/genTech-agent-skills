// BlockRun GPT Image 2 TEXT->IMAGE — direct SDK, no MCP tool, no source photo.
//
// Use this (not the `edit` template) when the subject is an ORIGINAL character: a text->image render
// invents a person, while an img2img edit inherits the reference's face. Do not pass a photo here when the
// brief would require altering a real person's identity — describe the aesthetic in prose instead.
//
// Run from the SDK root so bare imports resolve:
//   cd /opt/data/tools/blockrun && node /path/to/this-file.mjs
import { ImageClient } from '/opt/data/tools/blockrun/node_modules/@blockrun/llm/dist/index.js';
import { readFileSync, writeFileSync } from 'node:fs';

// ---------------- CONFIG ----------------
const OUT = '/opt/data/profiles/<seat>/image_cache/<name>.png';
const MODEL = 'openai/gpt-image-2';   // measure: ~$0.064 per 1024x1024 render
const SIZE = '1024x1024';             // portrait sizes are NOT achievable on this lane — expect square
const PROMPT = `
SCENE: <who and where, 2-3 sentences. Lead with the subject so the model does not lose them>.

SUBJECT: an ORIGINAL character — <age, build, complexion, distinguishing feature such as freckles>.
<Hair in concrete terms — length, texture, how it is worn>. <Wardrobe as materials and colours>
<Jewellery / accessories, named specifically>. <Expression and attitude>. <Pose and what the hands are doing>.

BACKGROUND / SETTING: <3-4 concrete objects> plus <one light direction and time of day>.

STYLE: <rich digital painting | photorealistic film still | etc.>, clean linework, saturated colour.
ABSOLUTELY NO TEXT, NO LETTERING, NO LOGOS, NO WATERMARKS, NO SIGNATURES anywhere in the image.
`;
// ----------------------------------------

const key = readFileSync('/opt/data/.blockrun/.session', 'utf8').trim();
const client = new ImageClient({ privateKey: key });   // zero ETH balance is fine — no payer gas needed

// TEXT->IMAGE: generate(prompt, opts). The edit signature is different — do not swap them.
const res = await client.generate(PROMPT, { model: MODEL, size: SIZE });
// res carries price/usage/payment; there is no cost_usd in this build. The on-chain USDC delta is the receipt.
console.log('price/usage:', JSON.stringify(res.price ?? res.usage ?? null));

const item = (res.data && res.data[0]) || res;
if (item.b64_json) writeFileSync(OUT, Buffer.from(item.b64_json, 'base64'));
if (item.url) {
  const r = await fetch(item.url);        // download first; don't feed the CDN url straight to vision
  writeFileSync(OUT, Buffer.from(await r.arrayBuffer()));
}
console.log('wrote', OUT);

// Before delivering: open the file and look at it. Check the subject actually landed, and scan for
// garbled pseudo-text, stray watermarks and broken hands. `file` may not exist on this host — use PIL:
//   python3 -c "from PIL import Image; im=Image.open('<OUT>'); print(im.format, im.size, im.mode)"
