#!/usr/bin/env node
/**
 * On-chain USDC / ETH balance for the BlockRun wallet on Base — use it as the RECEIPT.
 *
 * The API response carries `price` (the quote) but not the charge, and `client.getBalance()` is
 * broken in this build. So: run this BEFORE a paid call and AFTER it, subtract, and that is the cost.
 * It also answers "did that failed/orphaned call charge me?" — unchanged balance = it did not.
 *
 * A zero ETH balance is NORMAL and does not block paid calls: BlockRun settles x402 server-side
 * from the signed authorization, so the payer needs no gas.
 *
 *   cd /opt/data/tools/blockrun && node scripts/blockrun-balance.mjs
 */
import { getOrCreateWallet } from '/opt/data/tools/blockrun/node_modules/@blockrun/llm/dist/index.js';

const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const RPC = 'https://mainnet.base.org';

const wallet = await getOrCreateWallet();
const addr = wallet.address || wallet;
// balanceOf's data arg takes the address WITHOUT 0x — a double 0x makes the RPC reject 'Invalid params'.
const bare = addr.replace(/^0x/, '');

async function rpc(method, params) {
  const r = await fetch(RPC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 }),
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message || 'rpc error');
  return j.result;
}

const usdcHex = await rpc('eth_call', [
  { to: USDC_BASE, data: `0x70a08231000000000000000000000000${bare}` },
  'latest',
]);
const ethHex = await rpc('eth_getBalance', [addr, 'latest']);

const usdc = Number(BigInt(usdcHex)) / 1e6;   // USDC has 6 decimals
const eth = Number(BigInt(ethHex)) / 1e18;

console.log(`address : ${addr}`);
console.log(`USDC    : ${usdc.toFixed(6)}`);
console.log(`ETH     : ${eth.toFixed(6)}  (0 is fine — no payer gas)`);
console.log('');
console.log('Charge for a job = the reading taken before it, minus this one.');
