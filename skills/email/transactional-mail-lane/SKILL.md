---
name: transactional-mail-lane
description: "Use when a service must send mail from a shared host."
version: 1.0.0
author: gentech
license: MIT
tags: [email, resend, dns, dkim, spf, dmarc, verification, delivery]
metadata:
  hermes:
    tags: [email, transactional, dns, deliverability, api]
    related_skills: [himalaya, email-inbox-triage, public-signup-endpoint-audit, verification-vantage]
---

# Transactional Mail Lane

Standing up a sender that a service can actually rely on: domain verification, the key, the probe that proves
it, and the failure modes that make a working lane read as broken.

## When to Use

- A service must send mail to strangers: signup verification, receipts, alerts, password resets.
- Someone asks for a verification link, a "welcome mail", or an email-gated signup.
- "The mailer isn't working" — before you touch the key, read Pitfall 1.
- Before you write "we'll email them" anywhere in a design. A flow that promises mail with no sender
  configured is a promise the system cannot keep, and nothing will flag it.

## The build order — each step unblocks the next

1. **Choose the provider and establish its CAPABILITY GRANULARITY.** Sending and receiving are separate
   capabilities, often behind separate keys and separate DNS. Know which one you are buying before you start.
2. **Add the domain at the provider.** It emits the exact records; do not hand-write them from memory.
3. **Publish DNS in this order: DKIM → SPF → DMARC → MX.**
   - **DKIM** (TXT on `resend._domainkey`-style host) carries the literal value the provider gave. Copy it
     exactly; a truncated paste still saves and still shows as present.
   - **SPF** as the provider specifies — sometimes CNAMEs rather than an apex TXT.
   - **DMARC** TXT on `_dmarc`, starting `v=DMARC1; p=none;`. Policy tightens *after* evidence, never before.
   - **MX LAST, and only if you want inbound.** Publish it after sending is proven; it addresses a different
     capability and adding it early tells you nothing about whether mail leaves.
4. **Point records at the provider with proxying OFF.** Any CDN/proxy in front of a mail CNAME breaks routing.
   Set it explicitly and re-read the record to confirm the flag stuck.
5. **Store the key beside the code that uses it** — not in the operator's home (Pitfall 2) — and add the
   ignore rule **before** the file exists (Pitfall 8).
6. **Prove it with a real send.** A provider message id is the only evidence mail left. Domain lists, dashboard
   ticks and HTTP 200s are not (Pitfall 3).

## Pitfalls

### 1. With no User-Agent, the edge blocks you with an error that looks like a bad key

A default HTTP-library user agent (`Python-urllib/3.x`, similar for others) gets **403** from a provider's
edge for reads AND sends, while the same key and body through `curl` returns 200 with a message id. The tell
is the body: the provider's own errors carry its schema (`statusCode`/`name`/`message`), while a WAF refusal
is a bare `{"error":"Forbidden"}`.

- **Always set an explicit identifying UA** on every programmatic call to a mail API.
- **A 403 whose shape does not match the provider's documented error shape is the edge, not the credential.**
  Check that before rotating a working key — rotating costs a re-deploy and fixes nothing.
- The same trap exists on model/API rails generally; the UA is not decorative on any metered endpoint.

### 2. Code a CONTAINER runs must live in that container's mount, not the agent's profile tree

A sidecar service (gateway, worker) mounts one directory and sees nothing else. A module imported from the
agent's home loads fine in your shell and is **invisible from inside the container**, so the import fails at
startup and every request returns a generic "unavailable" — which reads like a code bug, not a layout bug.

- **Keep a module the service imports as a sibling of its entrypoint** (`os.path.dirname(__file__)`), and
  resolve the key from that same directory.
- **Test the import from the service's own namespace, not yours.** A successful local run proves the module
  works; it proves nothing about whether the service can see it.
- **When the service returns a generic failure for a path-dependent feature, suspect layout before logic.**

### 3. A capability-restricted key cannot verify itself — hand over the check that can

A sending-only key is refused `401/403` on the domain list, the domain create, and the verification trigger.
So a `--check` that reads domain status reports failure on a perfectly working lane.

- **Detect the restriction and say so** rather than reporting a refusal: a sending-only key cannot verify,
  and pretending otherwise sends the reader to rotate a good key.
- **Offer the probe that CAN prove it:** one real send, accepted with a message id. Acceptance is provable;
  *delivery* (inbox vs spam) needs the human to look — say which one you verified.
- **A check that cannot verify must never return success.** Exit non-zero with the reason and the next command.

### 4. "Created: true" is not "resolvable"

An API accepting a DNS record and the internet answering with it are different facts, and only the second
matters. Query **public resolvers** after writing:

```bash
# DoH — works from anywhere, no dig dependency
curl -s 'https://cloudflare-dns.com/dns-query?name=<host>&type=TXT' -H 'accept: application/dns-json'
curl -s 'https://cloudflare-dns.com/dns-query?name=<apex>&type=MX'  -H 'accept: application/dns-json'
```

Read the `Answer` array. An empty `Answer` with `Status: 0` means no record; `Status: 3` means the name does
not exist. **Wait and re-poll** — propagation is not instant, and a single early empty read is not a failure.

### 5. "Partially verified" is per-capability, not a warning

A domain can show DKIM/SPF verified and MX pending simultaneously, and **sending works in that state**. Read
the per-record status list before concluding anything is broken: a verified DKIM plus a verified SPF CNAME is
a working sender. The pending row is usually the capability you do not need yet.

### 6. Never log or echo the message body

A verification mail carries a live token; a receipt carries amounts and addresses. Logging the body writes a
credential into a fleet-readable file. Log the provider **id** and the recipient, nothing else.

### 7. Missing provider config is a REFUSAL, never a silent no-op

A mailer that returns "ok" with no key is how a fleet comes to believe it is emailing people. Refuse with a
named reason and a non-zero exit, and make the caller **revoke or refuse the thing it was about to grant** —
if the mail could not be sent, the credential it was meant to activate must not be usable.

### 8. Add the ignore rule BEFORE the secret file exists

A key placed in a shared, deployed, or synced tree is one `git add -A` from publication. The order is:
write the ignore pattern, prove it matches (`git check-ignore -v <path>`), and only then create the file
`chmod 600`. **Confirm with `git ls-files | grep <name>` returning nothing** after the fact — the ignore file
is a claim until the tracking query agrees.

## Verification block

Run all four before saying the lane works:

```bash
# 1. key present and readable by the consumer
ls -l <key-path>                       # expect 600, owned by the consumer's uid

# 2. provider accepts a real send  → a message id is the proof
<mailer> --probe <an-inbox-you-control>

# 3. DNS resolves from the public internet (Pitfall 4)
curl -s 'https://cloudflare-dns.com/dns-query?name=<dkim-host>&type=TXT' -H 'accept: application/dns-json'

# 4. the secret is NOT tracked
cd <repo> && git ls-files | grep -i <key-name> || echo 'untracked ✓'
```

**A lane is only as proven as its weakest of these four.** Sending proves the key and the domain; DNS proves a
receiving client will trust the mail; the tracking check proves you did not just publish a credential.

## Related

- `himalaya` — operating a mailbox over IMAP/SMTP, which is the *inbound/read* side of this lane.
- `public-signup-endpoint-audit` — the deferred-activation pattern this lane usually serves.
- `verification-vantage` — why a passing probe from the wrong vantage proves nothing.
