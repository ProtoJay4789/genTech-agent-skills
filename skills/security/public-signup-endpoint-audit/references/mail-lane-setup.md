# Standing up the mail sender that makes verification real

A double-opt-in gate is only a gate if mail actually leaves the building. Two states look
identical from the code and are opposites in reality: **validation-by-shape** (the address
matches a regex, nothing is sent, nothing is proven) and **validation-by-action** (a message
arrives and someone acts on it). This file is how to get from the first to the second.

## 0. Check whether the domain can send or receive AT ALL, before writing code

A domain with no MX and no SPF cannot deliver, and nothing in your application will say so.

```bash
# DoH keeps this working with no dig installed
curl -s 'https://cloudflare-dns.com/dns-query?name=<domain>&type=MX'  -H 'accept: application/dns-json'
curl -s 'https://cloudflare-dns.com/dns-query?name=<domain>&type=TXT' -H 'accept: application/dns-json'
# Status 0 with an empty "Answer" array = the record does not exist.
```

An empty answer is the finding: every "we'll email them" in the codebase is a promise the
system cannot keep. Say that plainly rather than building the flow on top of it.

## 1. Provider setup, in order

1. Create the account (free tiers are sufficient for verification mail: ~100/day, ~3,000/month).
2. **Add the domain** in the provider's dashboard → it returns the exact DNS records to publish.
3. **Publish those records at the DNS host** (do this programmatically if you hold a token with
   DNS write scope — prove the write scope first with a throwaway `TXT` record, then delete it).
   Typical set:

   | record | name | purpose |
   |---|---|---|
   | `MX` | sending subdomain | bounce/complaint handling |
   | `TXT` (SPF) | `send.<domain>` | authorises the provider to send |
   | `TXT` (DKIM) | `<selector>._domainkey.<domain>` | signing — the one that decides inbox vs spam |
   | `TXT` (DMARC) | `_dmarc.<domain>` | policy; **start at `p=none`**, tighten after a clean month |

   `p=none` first is a decision, not a default: it accepts mail while you gather evidence, and
   moving to `p=quarantine` later is a separate call made on real data.
4. **Wait for the provider to report the domain `verified`.** DNS TTL makes this minutes-to-an-hour;
   do not treat a slow verification as a failure.
5. Store the API key at a mode-600 path (`umask 077`), never echo it, and never interpolate it
   into a shell command string — see `secret-handling-in-chat`.

## 2. Key SCOPES — a scope refusal looks exactly like a broken credential

Most providers issue **sending-only** and **full-access** keys, and the sending-only one is the
right default for a mailer. The trap is what happens next:

```
GET /domains  ->  401 {"name":"restricted_api_key",
                       "message":"This API key is restricted to only send emails"}
```

**A valid, working sending key returns 401 on every read endpoint.** If your `--check` verifies the
lane by listing domains, it reports a healthy lane as broken — and the temptation is to ask the user
for a new key when nothing was wrong with the old one.

- **Verify the lane the way it will be used: send something, and require the provider's message id
  back.** A `200` without an id is not a send.
- **Read the error's `name`/`message`, not just its status.** `restricted_api_key` is a statement
  about scope; `invalid_api_key` is a statement about the credential. They have different fixes.
- Ask for **full access** only if you genuinely need to read domain/DNS state programmatically;
  otherwise keep the narrower key and probe by sending.

## 3. The sandbox sender, and the 403 that means "not verified yet"

Most providers ship a sandbox From-address (e.g. `onboarding@<provider>.dev`) that sends **before**
your domain is verified. Use it for the first end-to-end test so you separate "our code is wrong"
from "our DNS is not live yet".

Sending **from your own domain** before verification returns `403` — that is a DNS state, not a
credentials problem, and it is the single most common misread. Sequence the two tests separately:

1. sandbox From → proves the key and the code path
2. own-domain From → proves the domain

## 4. Fail CLOSED in the application

- **If the send fails, revoke the credential you just issued.** A key nobody was told about must
  not be usable. Never leave a half-issued live key behind on an exception path.
- **A mailer with no key must REFUSE loudly**, never return success. `exit 3` with "not configured"
  is correct; a silent no-op is how a fleet comes to believe it is emailing people.
- **Never log the mail body.** It carries a plaintext API key or a verify token, and a log file is
  readable by every process on the box.
- **Keep the plaintext credential out of the signup response.** Return it at verification, so bulk
  signup yields nothing usable even while the mail lane is down.

## 5. The check that proves the whole chain

```
provider key exists            -> refuse loudly if not
send from sandbox address      -> assert a message id comes back
provider reports domain verified -> assert status == verified
send from own domain           -> assert a message id comes back
signup without address         -> 400       (control: the gate is not a rubber stamp)
key before verification        -> 403       (gate)
link redeemed                  -> key handed over exactly once
link redeemed twice            -> same result, no second key
expired link                   -> refused with its own status, not a generic error
```

Every one of these has a failure mode that still returns a plausible-looking success, which is why
the control and the refusal branches are in the list, not just the happy path.
