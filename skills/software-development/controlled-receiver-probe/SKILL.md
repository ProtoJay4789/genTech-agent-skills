---
name: controlled-receiver-probe
description: "Use when a client's error contradicts its config or source."
version: 1.0.0
tags: [debugging, http, client-server, requests, headers, auth, black-box]
author: Gentech
license: MIT
metadata:
  hermes:
    tags: [debugging, http, client-server, requests, headers, auth, black-box]
    related_skills: [proving-a-negative, claim-provenance, systematic-debugging]
trigger: "A client fails against a service in a way its configuration does not explain — 401/403/404/timeout — or its docs, source, or error message disagree with what the server reports."
---

# Controlled Receiver Probe

## When to Use

- A client (CLI, SDK, cron job, peer service) fails against an endpoint in a way its config cannot explain.
- The client's error **names a cause** that the server's own evidence contradicts.
- You need the **exact bytes a client sends** — path, header names, body — and reading the client's source
  is slower, ambiguous, or spans a dependency you do not own.

## The Principle

**You cannot debug a request you have not seen.** When a client and a server disagree, the fastest way to
settle it is to remove the real server and put a receiver **you control** in its place. The client will talk
to it exactly as it talks to the real one, and you get ground truth without reading anybody's code.

This is a *black-box* instrument: it measures the client, not the server. Use it **before** rotating a
credential, editing a config, or filing a defect against either side.

## Procedure

1. **Stand up a minimal HTTP receiver** that records method, full path + query, every header NAME, and the
   body. Render secrets **fingerprinted, never raw** (length + short hash) — you need to compare them, not
   read them. `scripts/controlled-receiver.py` is a ready receiver.
2. **Point the client at it through the client's OWN registration path**, never by hand-typing an equivalent.
   Registering is part of what you are testing: re-typing the URL or flag makes the probe a different
   program, and a mismatch found that way may be your own typo.
3. **Invoke the client exactly as the failing path invokes it.**
4. **Read the captured request** and compare it against what the server expects.
5. **Clean up** — remove the probe registration and stop the receiver.

## The Deduction That Usually Ends It: Follow the ABSENT Log Line

**If the real server's own log shows no access/auth event for the failing call, the request never reached
that server — so the fault is the DESTINATION, not the credential.** Check the receiving side before you
rotate anything.

Measured: a client returned `401 Invalid API key`. The server at the address the client was configured with
logged **no** such rejection at that moment — its only recorded rejections came from a hand-typed `curl`
probe. The credential was correct throughout (the same key returned `200` via `curl`, and its fingerprint
matched the server's). The client was reaching a different endpoint or being routed elsewhere, and **the
401 named the wrong layer**.

> **An absent log line at the component you believe is involved is positive evidence about where the
> request actually went.** Absence at the receiver is the instrument; the client's error message is not.

## Pitfalls

- **A correct value in the wrong header is a 401.** Capture header NAMES too — a key sent as `X-API-Key`
  fails exactly as an invalid key does. Compare the header the client sends against the one the server reads.
- **Do not trust a client's own receipt about what it did.** A tool that reports "stored in `<path A>`" may
  have written to `<path B>` (the active profile/home/dir). Grep the actual file before believing the message.
- **The client may be reaching a DIFFERENT instance of the same service.** Verify which process owns the port
  by mapping the listening socket's inode to a pid, rather than assuming the instance you know about.
- **Prefer an OS-level listener map over a tool you have not confirmed exists.** A port check that silently
  returns nothing because the checker is not installed reads exactly like "nothing is listening" — a false
  negative that will have you report a healthy service as down. Confirm the probe can produce output at all.
- **Mask secrets in what you print.** You are capturing credentials in order to compare them; fingerprint
  them (length + hash) and never echo the value.
- **A probe that only proves the client *can* reach the receiver is not yet a finding.** The comparison is
  the finding: what it sent versus what the server required.

## Verification

- [ ] The capture includes method, full path with query, header NAMES, and body.
- [ ] Secrets appear only as length + fingerprint, never raw.
- [ ] The client was pointed at the receiver through its own registration path.
- [ ] The receiver and any probe registration were cleaned up.
- [ ] If the real server logged nothing for the call, that absence is stated as the finding.

## Support Files

- `scripts/controlled-receiver.py` — a re-runnable receiver that logs each request with secrets fingerprinted.
