---
name: browser-account-registration
description: "Register or diagnose sign-in on JS-rendered platforms."
tags: [registration, browser, email-code, signup, passkey, signin, oauth]
trigger: "When the user asks to register/sign up for an account on a JS-rendered web platform (buildathon dashboards like AKINDO, hackathon portals, marketplace signups) that uses email-verification-code auth; when a sign-in or 'create a key' step fails for the user and you must identify which credential mechanism the product actually uses; or when a listing page returns no data via curl/web_extract."
version: 1.0.0
author: Gentech
---

# Browser Account Registration (Email-Code Platforms)

Registering accounts on modern web platforms that use **email-verification-code
sign-in** (no password, no OAuth). Proven on AKINDO (akindo.io) Aug 2026, but the
pattern generalizes to any JS-rendered dashboard with email-code auth.

## When to use
- User asks "are you able to register us / sign us up" on a buildathon or
  marketplace platform.
- A listing/registration page returns empty content via `web_extract` or curl —
  it's JS-rendered and needs the browser.

## Core pattern
1. **Listing pages are JS-rendered.** If `web_extract`/curl returns a shell with
   no card data, use `browser_navigate` + `browser_snapshot` to see the actual
   content (buildathon cards: name, grant, wave, deadline, builder count).
2. **Grab the registration URL** by clicking a card and reading
   `window.location.href` via `browser_console`. URL pattern is usually
   `{platform}/wave-hacks/{id}` or similar.
3. **Sign-in is email-only.** Enter the user's email → platform emails a
   verification code → enter code → done. No password, no OAuth, no wallet.
4. **The verification code is the ONE step the agent cannot do solo** — the
   agent cannot read the user's email inbox. Ask the user for the code
   explicitly and wait for it.

## FIRST: classify the CREDENTIAL TYPE — never instruct a sign-in you have not walked

**"Go to the site and create a key" is an instruction that can cost someone an evening if the product has no
keys.** Before handing a human any sign-in step, open the wall yourself and identify which mechanism the product
uses. There are six, and only two of them involve a secret the user can type:

| Mechanism | What the user holds | Can an agent complete it? |
|---|---|---|
| **Email code** (this skill's main pattern) | a code mailed to their inbox | **no** — needs their inbox |
| **API key** | a pasted string, created in a dashboard | **only if a key-creation route exists** — verify it renders before promising it |
| **OAuth / social** | an existing third-party account | no — their identity |
| **Passkey / WebAuthn** | a platform authenticator (Touch ID, Windows Hello, security key) | **never** — a headless host has none |
| **Wallet signature** | a key they control | no — and never ask for the key |
| **Beta invite** | an invite from the operator | no — it is a request, not a form |

**The tell for the passkey case:** the login page offers *"open with / continue in the app"* and the target page
says the connection must be **started inside the app** so it can return control. That is not a broken button —
it is a flow that requires a device. Say so in one line and hand over the single action instead of retrying.

### A blocked popup is where the REAL flow lives — capture its target, then read it

An OAuth/passkey wall usually opens a popup, and when the popup is blocked the parent page only says so. The
authentication product is at the popup URL, so **intercept `window.open` to read the target instead of guessing at
it**:

```js
window.__popup = null;
window.open = ((orig) => (u, n, f) => { window.__popup = u; return null; })(window.open);
document.querySelector('button')?.click();
// then read window.__popup and open THAT url in a new tab
```

- **Read the popup's own page, and its query string.** `?op=signin&origin=…&walletStore=provisional` names the
  operation and the relying party — which tells you whether the wall is authentication, wallet creation, or a
  provider claim, three different tasks.
- **Follow a link on that page when it is the only control.** A "open the wallet / continue in app" button
  usually links a real path (`/wallet`); open it directly and read the two or three actions offered.
- **Then read the product's docs for the CURRENT state of the flow, not its marketing page.** A docs banner
  reading *"we're preparing the new account for private beta — request access"* beside *"previous setup
  instructions"* means **two generations of credential exist and the one the login page links may be the
  retired one**. Quote that banner; it is the finding.

### Stop at the wall with ONE action, not a tutorial

When the wall is genuinely the user's to cross, the reply is: what the gate is, why the agent cannot cross it,
and **one** action with its URL. Anything longer is a checklist for a task they did not ask to own.

- **Never offer a fake choice between mechanisms.** If there is no key-creation surface, saying *"create a key
  or sign in with it"* is describing a product that does not exist in front of them.
- **Name the residual uncertainty and who resolves it.** *"Whether publishing here requires settling through
  their rail is unstated in the docs — the sign-in wall is where that gets answered."* That is a real finding,
  and it stops the next agent re-deriving it.
- **Do not read the wall as a defect in anything we built.** A beta gate and a passkey-only flow fail for
  everyone; reporting them as our bug sends the team to fix working code.

## Verified sign-in steps (AKINDO example)
1. `browser_navigate` to `https://app.akindo.io/login`
2. `browser_type` the email into `input[name=email]`, click **Continue**.
3. Page shows **Verification** — "We have sent a verification code to your email
   address." Code input is `input[name=code]`.
4. `browser_type` the code, click **Sign in**.

## Pitfalls (learned the hard way)
- **React form quirk — MUST use `browser_type`, not console value-setting.**
  Setting `input.value` via `browser_console` (even with
  `dispatchEvent(new Event('input'))`) does NOT register with React. The field
  shows the text but the form still reports "code is required" / "email is
  required". Real keystrokes via `browser_type` are required. This applies to
  the email field too.
- **Code invalidation on page reset.** If the page resets (navigate away and
  back, or session drops) and you re-enter the email, the platform sends a FRESH
  code and the old one is invalidated. If you get "Invalid code", ask the user
  for the newest code — do not retry the stale one.
- **Codes are single-use and time-limited** — enter promptly once received.
- **Don't burn the user's time with a stale code.** If the flow reset, tell the
  user a fresh code was sent and ask for the newest one.
- **A "sign in" button that does nothing visible is usually a popup that was blocked.** Capture its target
  (`window.open` interception above); the wall you can see is the parent, never the auth product.
- **Never paste a credential you were given into a page that asks for one, and never accept one in chat.** If a
  flow needs a secret, the owner types it.

## After sign-in
- Join the target program from its dashboard (JOIN button).
- Many platforms (AKINDO WaveHack) accept both new and existing projects; you can
  join any wave and resubmit improved versions. Grants paid on-chain, no equity.

## Reference
- `references/akindo-registration-flow.md` — full AKINDO-specific detail
  (URLs, field names, verified steps).
