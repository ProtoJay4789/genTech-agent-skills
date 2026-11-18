# Getting a one-off on-chain write signed without taking custody of the key

**The request looks like this:** an identity/registry contract must be updated (a `tokenURI`, an
allowlist entry, an ownership change), the signing key is the human's and lives in their wallet app,
and the whole point is that the fleet never takes custody of it.

**The rule: never take custody to perform one write.** A single transaction is not a reason to put a
live key on a server — every other rule in this skill applies with full force to a key that exists
for "just one call".

## Why the obvious paths fail (diagnosis, not options)

- **Block explorers need an injected provider.** A contract's *Write* tab calls `window.ethereum`; a
  mobile browser or an in-app wallet browser typically has none, so the connect button does nothing
  and the page looks broken. Nothing is misconfigured — the page simply cannot see a wallet.
- **A file on the host works and is the wrong trade.** It creates a live key on the box to move a
  metadata pointer. It also costs round trips: a heredoc whose line is a *placeholder* gets pasted
  verbatim, and the downstream length check then reports the placeholder's length instead of the key's.
- **A stored credential may be the wrong SHAPE for the provider you are pointed at.** Probe the
  provider's own auth surface before planning around a key you hold; a `401` on every standard scheme
  means re-pointing is a build, not a config edit.

## The method that works: host your own signing page

Serve a minimal static page (a Cloudflare Worker returning one HTML document is enough — no build
step, no framework) that:

1. requests `eth_requestAccounts` and switches/adds the chain (`wallet_switchEthereumChain`, falling
   back to `wallet_addEthereumChain` on error code `4902`);
2. **reads the CURRENT on-chain value first**, so the before-state is captured and printed;
3. sends the one call, then re-reads the value after confirmation and prints it.

Ethers v5 UMD from a CDN is sufficient (`unpkg.com/ethers@5.7.2/dist/ethers.umd.min.js`); note that
`ethers.providers.*` is the v5 namespace — `JsonRpcProvider` is **not** a top-level export.

Repeat back the URL, the exact function and its arguments, and the expected gas. **The page is the
deliverable; the key never leaves the wallet.**

## The guards, and each one is load-bearing

- **Refuse to write unless the connected address equals the expected owner.** A wrong connected
  wallet produces a *perfectly valid* signature from the wrong account, which then reads as a
  contract problem. Compare before signing and say the verdict on screen.
- **The page must have ZERO `<input>` elements — and say so.** Count them
  (`document.querySelectorAll('input').length`) and put the count in the message to the user: "there
  is nowhere on this page to type a key" is a verifiable claim, not reassurance.
- **State the address the call goes TO, and warn against the sibling.** Contracts behind a proxy have
  two addresses: the **proxy holds the data**, the **implementation holds the code**. Calling the
  implementation succeeds, costs gas, emits an event, and **changes nothing about your record** — a
  transaction that mines is not a change that took effect. Print the proxy address as the target and
  the implementation as *do not call*.
- **Confirm the function name from the contract's own ABI, not from documentation.** A signature
  copied from a months-old note is a guess. Read the ABI (the explorer's API for the
  **implementation** address is what carries it) and confirm the selector and argument types.
- **Serve it `noindex`, hold no keys, log nothing.**

## Verify the write from the CHAIN, not from the page

The page saying "confirmed" is the wallet's view. Prove it independently:

```
eth_call  tokenURI(id)  → the NEW value            # did the state actually change?
HTTP GET  <the new value>  → content-type + parse  # does it serve what it claims?
```

- **Capture the before-value before asking for the signature.** "It changed" needs something to have
  changed *from*, and the before-state is free to record and impossible to recover afterwards.
- **Check CONTENT, not status.** A value that returns `200 text/html` when a structured document was
  expected is the same defect the write was meant to fix.
- **A `200` on the URL is not a `200` for the reader.** Fetch it the way the consumer will, and parse it.

## Contract-independent checks worth doing first

- **Confirm the wallet has the gas asset** for that chain before handing over steps, and quote the
  balance and the estimated cost (`gasLimit x gasPrice`) side by side.
- **Never ask for, accept, or accept-and-discard a private key in chat.** If a user volunteers one,
  refuse the channel and route them to the wallet — see the main skill's "What may never travel
  through chat".
