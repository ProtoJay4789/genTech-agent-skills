---
name: public-signup-endpoint-audit
description: "Use when a public endpoint mints keys or free quota."
version: 1.0.0
author: gentech
license: MIT
tags: [security, signup, abuse, free-tier, email-verification, gateway]
metadata:
  hermes:
    tags: [security, signup, abuse, free-tier, email-verification]
    related_skills: [agent-credential-architecture, security-audit, himalaya]
---

# Auditing a public signup endpoint

## When to Use

Load this when any of these is true:

- You are building, reviewing, or debugging an endpoint that issues API keys, accounts, or a free quota.
- Someone asks "is our free tier safe?", "what can a stranger get from us?", or "should we remove
  the free tier?"
- A monitor reports authenticated traffic you cannot attribute to a named key.
- A signup endpoint has been deployed without an abuse test.

**The question this skill answers: can a stranger getting nothing from us obtain something that
costs us money — without a human ever noticing?** Measured on our own gateway, the answer was yes
for weeks.

## The finding that produced this skill

2026-11-18, x402 gateway, measured with one command:

```bash
curl -X POST https://api.gentechlabs.net/v1/human/signup \
  -H 'content-type: application/json' -d '{"plan":"free"}'
# -> 200 {"api_key":"gt_...","plan":"free","monthly_calls":50}
```

**A live 50-call key, no auth, no email, no card, no browser.** Caps were 3 keys/hour/IP and 100
keys total, so the whole free allowance — ~5,000 paid-route calls — was scriptable by anyone with
curl. Nobody noticed, because nothing measured it: it returned 200 and looked like a feature
working.

## Probe safely FIRST — a schema probe on a live service is a registration

**Before the audit order below, know what your probe will create.** Measured: sending
`{"name":"schema-probe-do-not-create"}` to a public `POST /api/agents` **minted a live agent and API
key on a service we do not own.** The intent was to read the validation schema (a half-finished body
tells you which fields are required). It succeeded instead, and the entry now exists under our name.

Rules, in order of what saves you:

- **To learn a schema, send a body that MUST fail.** `{}` or deliberately omit the required field. You
get the same field list from a 400 and you create nothing. Never send a plausible-looking value to
"see what happens" on a write endpoint you do not control.
- **Treat every POST / PUT / DELETE as a real action**, whatever you meant by it. There is no
"probe-only" flag on someone else's API, and a test account is still an account.
- **Assume the credential is shown ONCE.** Many services return the key in the create response and
  mask it on every later read. A blind probe leaves you holding an artifact you cannot use and cannot
delete — check whether a delete path exists *before* you create, not after.
- **If you do create something by accident, say so plainly and immediately.** Report the id, what it is
  named, and what it will take to remove. Do not quietly hope it goes unnoticed — a stray entry with
  your fingerprint is worse than a deliberate one.
- **Prefer a documented read endpoint over a write probe** for anything you only need to observe. If the
  service publishes a listing/discovery route, use it; a 401 there still proves the route exists.

## The audit, in order — each step answers a different question

1. **Does it answer unauthenticated?** Send the request with no headers and an empty body. If it
   returns a credential, stop and write down what a stranger can mint.
2. **What is the ceiling?** Multiply the per-call allowance by the total-key cap. That number, not
   the per-key number, is the exposure. (100 keys x 50 calls = 5,000 — the per-key figure reads
   harmless and is not the answer.)
3. **Is the identity verified or merely required?** An address field checked for shape is not a
   verification. Ask: *could a script invent this value and succeed?* If yes, it is a required
   field, not an identity.
4. **Is the credential usable before verification?** If the key works the moment it is returned,
   verification is decorative.
5. **Does anything measure it?** Count the calls. A signup endpoint with no usage counter is a
   leak that reports no flow. Here: 11 keys existed, 8 calls had ever been made — the tier was
   earning nothing and nobody had asked.

## The fix, in the order that matters

- **Deferred activation.** The key is issued INERT (`state: pending`). Only a redeemed token
  flips it to `verified`. A script that invents an address gets a key that returns 403.
- **One identity, one live key.** Case-insensitive and whitespace-trimmed duplicate check —
  `Jordan@x.com` and `jordan@x.com` are one person. A *revoked* key must not block a re-signup.
- **The plaintext is handed over at verification, not at signup.** This alone defeats bulk
  scripting, even before any mail is sent.
- **If the mail cannot be sent, REVOKE the key.** A key nobody was told about must not be usable.
  Never leave a half-issued live key behind on an exception path.
- **Fail CLOSED when the verifier itself is missing.** A stand-in that raises beats a null module
  that is silently skipped.

## Traps, each measured

- **Absent state is LEGACY, not pending.** Existing keys have no `state` field. Reading a missing
  field as `pending` silently breaks every key issued before the rule. Absent = keep working.
- **Redeeming twice must not mint twice.** Make redemption idempotent on the token, and return the
  plaintext exactly once. A double-click that issues a second key is a quota leak.
- **Store the token HASHED.** A store holding plaintext tokens means any file read is a
  key-minting capability.
- **Expiry is a timestamp comparison, never a job that should have run.** A cleanup cron that
  fails leaves tokens live forever and reports nothing.
- **Never log the mail body.** It carries a plaintext key or a verify token; a log file is
  fleet-readable.
- **A UI that reports an error is not a failing job — check before you chase.** A ⚠️ block inside a
  cron's message reads as an error while the job is `ok`. Read `cron list` before debugging.
- **A claim about who was served needs a field that records it.** A traffic ledger with no key,
  plan or auth column cannot support "free-tier keys or our own probes" — that was an inference
  printed as a finding. If the ledger cannot say who, the honest answer is "unknown"; file the
  missing field as work.

## Verify the fix with probes that can FAIL

Every assertion needs a control that must stay false:

```
valid address          -> accepted
garbage / empty        -> refused        <- the control
unverified key serves  -> 403           <- the gate
verified key serves    -> 200
duplicate address      -> 409
the same address, differing case -> 409  <- the trap
revoked-key address    -> accepted      <- must NOT block
legacy key (no state)  -> 200           <- must NOT break
bogus token            -> 404
expired token          -> 410
```

Run them against the real functions lifted from the source (exec the defs, stub the store), not
against a copy — a copy passes and drifts.

## Related

- `agent-credential-architecture` — where the key lives once issued.
- `security-audit` — the wider codebase pass.
- `himalaya` / the mail lane — the sender that makes verification possible. **A verify flow with no
  mail provider is an address-shape check wearing a verify badge.** Say which one you shipped.

## Before you build the gate: can the domain send at all?

**Check MX/SPF before writing any verification code.** A domain with no mail records delivers
nothing, and nothing in your application will report it — you will ship a gate that cannot verify
anyone and a signup that returns `503` on every attempt. The 30-second DNS query, the provider setup
order, the record set, and the **sending-only key that returns `401` on every read endpoint** (so a
`--check` reports a healthy lane as broken) are in `references/mail-lane-setup.md`.
