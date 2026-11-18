---
name: verification-vantage
description: Use when verifying a service works. A pass must exercise the thing it claims; a 402/storefront check never proves a backend exists.
version: 1.0.0
---

# Verification vantage — what a check can and cannot see

**Origin:** 2026-10-31. The gateway was found selling 15 routes with **nothing behind
any of them**, and three separate checks had all reported green.

## The failure, stated once

**Every paid route answered a correct `402`. Every check that looked at it said `HEALTHY`.**

A `402` is issued by the **gateway**, before any backend is contacted. It is a price tag.
It proves *"this is for sale"*. It proves nothing about whether anything can *serve* it.

**So the storefront was verified, and reported as the shop.**

## The rule

**A check may only be trusted for the question it actually asks.** Name the vantage before
trusting the result:

| check | what it truly asks | what it can NEVER see |
|---|---|---|
| HTTP status of a public route | will the edge price/serve this path | whether a backend exists |
| advertised-route vs served-route (`surface-probe`) | does the edge match the contract | same — both sides are the gateway |
| `402` seen from outside | the gateway is healthy | the entire backend layer |
| TCP connect to the backend port | **is a process listening** | whether it returns real data |
| call the backend and inspect the BODY | **does it actually serve** | nothing — this is the real one |

**Three checks in our own estate shared this blind spot simultaneously:**
`surface-probe` (advertised vs served — both the gateway), `api-audit` (labels `402` as
`HEALTHY`, reachable even on a backend port), and my own `curl -w '%{http_code}'` habit.

## Rules, each learned the hard way

1. **Verify at the layer you are claiming.** Claiming "the service works" requires a call
   that reaches a *service*. A status code from the edge is a claim about the edge.

2. **A check that cannot fail will report success.** `test -f` on a file that cannot exist,
   a `grep` with a pattern that cannot match, a `--maxdepth` too shallow to reach the
   target — each returns "nothing there" and reads as "all clear". **Before trusting a
   negative, deliberately make it fail once and confirm it can.** `surface-probe` does
   exactly this: its selftest asserts the detector *flags* a wrong route.

3. **`UNKNOWN` must be a real verdict.** A probe that cannot distinguish "it works" from
   "I could not check" will collapse both into "fine". Give the probe a third state.

4. **Do not override an instrument with an inference.** At 22:35 `/status` correctly said
   `down`; I had it on screen and built a theory that the *instrument* was wrong, because a
   different check "knew" the services were fine. The instrument was right. **When a live
   probe disagrees with your reasoning, suspect the reasoning first.**

5. **Green from the wrong vantage looks identical to green from the right one.** Both print
   `✅`. The distinguishing question is not *"did it pass"* but *"what did it touch"*.

6. **A presence check answers "is it on PATH", not "does it exist".** `which` / `shutil.which` returns
   nothing for a binary that is real but merely not exported — and an ABSENT verdict on a tool that is
   present is the same defect as a pass on a service that is dead: confident, well-formatted, wrong.
   Measured: an audit reported a sync tool missing and the documented fact was right; the tool sat in a
   directory that simply was not on PATH. **Probe presence by EXECUTION against the candidate paths
   (`<path> --version`), and when you report an absence, name the lookup that produced it** — otherwise
   the reader cannot tell "not installed" from "not on my PATH", which have opposite fixes.

### A check can fail in the OTHER direction — a broken comparison still prints a verdict

Rule 2 above says a check that cannot fail will report success. **The mirror image is harder to catch:
a check whose comparison never ran still prints a conclusion, and it prints FAILURE.**

Measured: two freshly rendered clips were labelled `🔴 still` by a shell one-liner whose
`[ {} -gt 1 ]` never received its substitution — the test silently never evaluated, `xargs` still
produced output, and the verdict line rendered anyway. **Two real videos were reported as broken by a
check that never executed its own logic.** The evidence that settled it was already in hand (121 frames
of h264); the check was the only new thing in the room.

- **Never build a verdict from a pipeline you have not watched produce both branches.** Run it once on
  input you know is true and once on input you know is false, in the same invocation, before letting it
  emit a conclusion.
- **When a fresh verdict contradicts evidence you already hold, suspect the comparison first.** A
  conclusion that arrives from a new instrument and disagrees with a known measurement is a statement
  about the instrument.
- **Prefer a real script over a shell one-liner whenever the result must be trusted.** One-liners are for
  looking; scripts are for concluding. Substitution, quoting and exit-status semantics inside a pipeline
  are where one-liners become confidently wrong.

### A health check that inspects its INPUTS is not checking its DEPENDENCY

File existence is a **deployment** claim. The question a health check exists to answer is whether the thing can
**serve**, and those are different artifacts.

Measured: a plugin's `health()` returned `ok: true` while the runtime that every one of its hooks shells out to was
absent — the check inspected three file paths (`the entry script`, `a bundled asset`, `package.json`) and none of
them was the interpreter. Not one request could have been served, and the health surface said green. A caller that
trusted it installed a component that could only fail.

- **Enumerate what the feature actually EXECUTES, then check at least one of those paths end to end.** An entry
  script that is `present` proves a file was unpacked, nothing more.
- **A check list made entirely of `os.path.exists` / `_check_file` rows is a manifest, not a health check.** The
  tell is that every row could pass on a machine where the process never starts.
- **When you cannot probe the dependency, the verdict is `UNKNOWN`, not `ok`.** Same third-state rule as above:
  a check that only knows how to say `ok` is not reporting on the system.
- **Read a vendored component's health output as a claim about ITS code, then verify the dependency yourself** —
  a foreign project's green is exactly as trustworthy as its author's definition of healthy, which is usually
  "the files are there".

### The measuring command can destroy its own vantage

`pkill -f <pattern>` matches **full command lines, including the shell running it.** Issued from a command
line that contains the same string, it kills its own caller — the run dies mid-way and the truncated
output reads as "the tool crashed" rather than "I shot myself." Resolve the target first
(`pgrep -f` and filter out your own PID and its parent) or use a pattern your own invocation cannot
contain. The same shape applies to any broadcast kill/cleanup: **the cleanup step must not be able to
select the process that is performing it.**

### An unauthenticated health endpoint is not a health check of the lane

**`/health` returning `200` says a process is listening. It says nothing about whether a single authenticated
call can get through** — and when the credential is the thing that broke, the check that cannot fail is the one
everyone wires to an alarm.

Measured: a peer lane answered `{"status":"ok"}` on `/health` while **every** authenticated call returned
`401 Invalid gateway API key`. Neither side would ever have noticed: the liveness probe was green, and the only
thing that mattered was dead. It was found by the peer trying to use it, not by any monitor.

- **The only valid probe of a keyed lane is a KEYED call.** For any endpoint that requires auth, the probe must
  send the credential and assert `200` — and, as a control in the same pass, assert that the same call WITHOUT
  the credential is refused (`401`). Both directions, or you have measured the socket.
- **When you hand a credential to another host, the pickup is not the verification.** Require the peer to prove
  it with a keyed call and report the status code, never "I set it".
- **A 401 is a statement about the key, not about the host.** Never report "the lane is down" without
  distinguishing unreachable (`000`/timeout), unauthenticated (`401`), unauthorised (`403`), and misrouted
  (`404`) — they have four different owners and four different fixes.
- **`000` is not automatically a block — sometimes the host does not exist.** `curl` reports `000` for a firewall
  and for a name that resolves to nothing, identically. Before calling anything unreachable, resolve it at a
  public resolver:
  ```bash
  curl -s 'https://dns.google/resolve?name=<host>&type=A'   # "Status": 3 = NXDOMAIN, the name is wrong
  ```
  Measured: two report cycles spent on "the vendor blocks us" for a hostname that had never existed, because it
  was **composed from the pattern of other APIs** instead of read from theirs. **A hostname you invented is
  evidence about your guess, not about the vendor.**
- **Read the base URL out of the contract; never assemble it.** API docs print a Base URL line — take it verbatim
  from the Introduction/quick-start page. And **a vendor's marketing site answering `403` behind Cloudflare says
  nothing about its API host**: different subdomain, different posture. Test the host you will actually call, and
  report the two separately when both were probed.
- **After rotating or re-pointing an endpoint, the old key stays valid-looking in every report.** A registry that
  updates the URL but not the key produces exactly this: healthy-looking lane, dead calls. Check that the
  host entry and the credential were changed in the same pass.

## The namespace case — a probe in the wrong container cannot see the service

**Measured 2026-11-01.** A liveness monitor reported `12 DOWN — nothing listening` every
four hours while the service was demonstrably up and answering on the same host.

```
backends   containers with `--network host`, uvicorn bound to --host 127.0.0.1
           ⇒ they listen on the HOST's loopback and NOTHING else
probe      ran inside the agent container — own network namespace
           ⇒ its 127.0.0.1 is a DIFFERENT machine
result     0 of 12 loopback ports visible from there, permanently
```

**`127.0.0.1` is not an address; it is a *namespace-relative* name.** Two containers can
both hold services on `127.0.0.1:8088` and neither can reach the other's. **A check that
cannot be right is worse than no check: it trains you to ignore the alarm.**

**Two rules that follow:**

1. **Before trusting a negative, prove the vantage can produce a positive.** Connect to
   something you *know* is listening from that same process. If you cannot, the check is
   blind and every "down" it reports is an artifact. *Try to reproduce a known-up service
   before reporting a known-down one.*
2. **When your vantage cannot see the thing, report UNKNOWN — and either find the process
   that CAN see it, or say plainly that you could not verify.** A service whose own
   namespace is the only place it is visible is verified only from that namespace. Here the
   gateway runs `--network host`, so its `/status` is a legitimate authoritative read — the
   one case where reading the monitored system's own view is not self-congratulation but
   the only probe positioned to measure.

**And a probe can also fail on something as small as a header.** The same script worked
under `curl` and got `403 Forbidden` from Python, because Cloudflare rejects the default
`Python-urllib/3.x` User-Agent. **UNKNOWN-forever from a header is as useless as
DOWN-forever from a namespace.** Send a User-Agent when probing a real host.

## Scanning a catalogue — sampling, filters, and key paths

Any probe against a large external list (a registry, a bazaar, an index) can produce a
confident false answer in three ways that all look like data.

1. **A page is not the population.** A paged API returning 100 items tells you nothing about
   how many exist. **Read `pagination.total` (or the equivalent) before believing any count or
   absence derived from page one.** A catalogue with 30,004 entries and a 100-item default page
   means the first query saw one third of one percent — small enough to miss anything, large
   enough to look like a survey.
2. **A filter that ignores its parameter is indistinguishable from a filter with no matches.**
   Run the identical query with a **known-present control value**. If the control and the target
   return the same total, the parameter was silently ignored and the answer is `UNKNOWN` — not
   `absent`. Only a control returning a *different* number licenses the negative. And note that
   even a control-verified negative is a **snapshot**: re-run it after any change that could
   plausibly alter the result, because the thing you are measuring may be responding to you.
3. **Confirm the key path before calling a field missing.** Reading `item.accepts[0].resource`
   when the field lives at `item.resource` produces "present but unusable" — a dramatic defect
   report on healthy records. **Dump one whole object before asserting a field is absent**; a
   missing value at the path you guessed is not a missing value in the document.

**The general shape:** before reporting an absence, say which of these could be producing it —
sample size, an inert parameter, or a wrong key — and close each one. "I looked and it wasn't
there" is only a finding when the looking could have found it.

## Two endpoints, two true answers — a disagreement is not a contradiction

**Before calling someone else's number wrong, confirm both numbers came from the same endpoint with the same
parameters.** A weaker or broader query returns a second, entirely true value, and the difference looks exactly
like one of you being mistaken.

Measured: one party reported an entity appearing in **30** pairs; an independent check of the same entity reported
**14**. Neither was wrong — `/search?q=<symbol>` matched 14, `/tokens/<address>` matched 30. The disagreement was
the QUERY, and the version that got published as a correction was the weaker one.

- **A count over a collection is only meaningful with its predicate attached.** "30 pairs" and "14 pairs" are not
  competing facts; "30 on the token endpoint, 14 on search" is one fact. Quote the endpoint, the parameter, and the
  filter, or the number is unfalsifiable.
- **When a peer challenges your number, re-run YOUR check through the canonical path first.** Testing their claim
  with your original instrument reproduces your original answer and feels like confirmation — it is a tautology.
  Reach for the authoritative endpoint *specifically because it might disagree with what you already have*.
- **A query-dependent number must never be hardcoded.** Where two valid queries give two valid counts, the value
  belongs computed per run and reported with its provenance — never stored as a constant in a spec, a test, or a
  threshold.
- **Correct the record where you published the error, in the same place.** A contradiction announced to a user or
  in a shared note stays true until it is struck there; fixing it in the next report leaves the wrong claim
  standing in the record that others cite.

## Confirm the OBJECT you tested is the one you are claiming about

**Two services can share a name, and a probe against the sibling returns a perfectly valid answer to a
question nobody asked.** A wrong-object read is indistinguishable from a finding: the status code is real,
the body is real, and only the conclusion is about a different product.

Measured: a route called `score` was reported to be issuing **payable** challenges while the platform's own
readiness record listed it as down — i.e. a customer could pay for a dead backend. The probe had called
`/v1/security/score/<address>`, which resolves to a **different backend**: a live token-security service
with every right to charge. The route that was genuinely down, `/v1/score`, answers `503` with no
challenge at all. Same word, two products, and the alarming report was about the healthy one.

- **Resolve the path against the route table before interpreting any status.** The map from public path to
  backend (`BACKEND_ROUTES`, an nginx `location`, a gateway config) is the authority. A name appearing in a
  price list, a manifest, or a `/status` map is not the mapping.
- **Separate the two controls.** A `404` on a nonsense path proves the edge is not 402-ing everything — it
  does **not** prove the route you care about is gated. The control that settles it is the path that
  *should* be dead: call it and assert **no challenge**, not merely "not found".
- **Quote the path in the finding, not just the product name.** "score charges for a dead backend" is
  unfalsifiable; "`/v1/score` returns 503 while `/v1/security/score` returns 402 on a READY backend" is a
  claim the next reader can re-run in one command.
- **When two products share a name, file it as a naming defect.** A senior seat reading the manifest
  conflated them inside one note, so a buyer will too. The collision is real even when the money path is fine.

## The deployed artifact is not the served artifact

**A write that succeeds is a claim about the API. It is not a claim about the address.**
Measured on a worker upload: `PUT` returned `success: true` and the public URL still
answered **404**, because route/subdomain activation is a *separate* setting that defaults
to off. **Two different questions, two different checks:**

1. **Read the change back at the address the world uses** — not at the API that accepted
   it. `success:true` + `size_download>0` on the upload tells you a file was stored.
2. **A REJECTED write leaves the PREVIOUS version serving.** If the deploy fails, every
   probe afterwards measures the old build — and if the old build was also 200/402 in the
   shape you expect, the probes read as success for the *wrong artifact*. **Check the
   write's own status before you trust any probe that follows it; a 4xx there invalidates
   everything measured after.** This is the loudest version of the trap: old output
   wearing the new change's clothes.
3. **Deploy to a shadow name, prove it, then promote — and delete the shadow.** The shadow
   exercises real infrastructure with no exposure, and it keeps "is the new build correct"
   separable from "is the change live".
4. **After promoting, prove the shadow-only test surface is GONE** (its route should 404).
   A debug or selftest route that survives promotion is a hole, and a leak of the data you
   meant to sell never announces itself.

**And prove the refusal branch, not just the happy path.** A gate that should decline is
only real if you can watch it decline: force a failure (a parameter the upstream rejects, a
bad input) and confirm the refusal — with its reason — instead of an assumption that the
`catch` block works.

### A DISCOVERY change is proven by the CONSUMER, not by the spec

Deployed vs served is two layers. A published document that other machines read has a **third**: the
spec is our claim, and the **consumer's behaviour is the receipt**. A discovery surface can be
correctly regenerated, correctly served, and still be wrong to ship — or fixed and still look broken —
and only the traffic tells you which.

Measured: a crawler called a templated path thousands of times and got a `404` every time. The gateway
was behaving correctly (a template is not a resource); the spec was inviting it. After the spec stopped
advertising templates, the proof was **not** "the JSON looks right" — it was that **the last template
call in the request ledger was stamped at the restart instant, and none followed**, in a burst window
where a dozen were previously due by rate. That is the only claim a reader should be asked to believe.

- **Quote the rate and the silence, not just the absence.** "Zero since" is unconvincing on its own;
  "zero in 5 minutes against a prior rate of ~2.6/min" is a measurement. Give the expected count.
- **Expect a lag, and say what it is.** A consumer that polls hourly cannot change behaviour in a
  minute, so a clean first hour does not disprove the fix and a dirty one does not disprove the spec.
  State the consumer's cadence or mark the result provisional.
- **Pair every must-now-fail probe with a must-still-work CONTROL in the same pass.** When the change
  removes or refuses something, one unchanged behaviour has to prove the change did not overshoot —
  measured live: three dead routes went `404` **and** a real paid route still issued `402`. Without the
  control you cannot distinguish "fixed" from "turned it all off", and both look green.
- **A count that drops for a known reason is a fix; the same count dropping silently is an outage.**
  Print the old and new numbers side by side so the reader can tell which one happened.


## A 2xx is a response, not a transaction — classify by SHAPE, never by status alone

**A status code says what the server decided, not what the caller did.** Any metric derived from
request logs inherits that ambiguity, and it does so silently.

Measured: a conversion report classified `2xx` as "served / paid" and `402` as "quoted /
walked away". Two routes came back at **461% and 468% conversion** — more sales than quotes, which is
arithmetically impossible. The cause was not a good day: those routes return **`200` with a signpost
body** (`{"collection_root": true, "payable": false}`) when called **without** their required path
parameter. Crawlers read the signpost; the report booked it as a sale.

**Rules, in order of how much they save you:**

1. **An impossible ratio is the instrument telling on itself.** Above 100%, negative, or a
   numerator that cannot exceed its denominator — stop and fix the classifier. **A number that
   cannot be true is a stronger signal than any number that looks good**, and it costs one glance.
2. **Classify by request SHAPE, not by status.** Path carries its required parameter? Body says
   `payable: false`? Then it is a signpost, whatever the status. Where the log lacks the body, infer
   from the path shape and **say that you inferred it**.
3. **Every non-business outcome needs its own bucket, printed.** `quoted / served / signpost /
   refused / unknown` — a report with only two buckets will fold crawl noise into one of them and
   call it business. A bucket that exists and stays at zero is information; a bucket that does not
   exist is a silent merge.
4. **A rate for a broken thing is a lie.** If the backend behind a route is down, its conversion
   rate is `n/a`, not `0%`. Zero says "nobody wanted it"; `n/a` says "it could not have been bought".
   Those drive opposite decisions.
5. **The source log rotates. Snapshot it on a schedule.** A one-day file cannot answer a week-long
   question, and the day it rolls over is the day the baseline disappears. Write a dated snapshot
   every run and compute against accumulated history — **losing the raw log is expected; losing the
   history is the bug.**
6. **Before calling an unclassified bucket demand, dump the FULL user-agent strings.** A classifier
   that matches a truncated prefix under-classifies, and the residue reads as buyers. Measured: a
   live-window bucket of 1,317 "unknown" requests resolved, on full-UA inspection, to **zero**
   customers — generic runtimes pattern-walking every route, a vulnerability scanner wearing a
   desktop-browser UA (hitting `/.env`, `.git/HEAD`, WordPress paths), and self-named readers and
   censuses. **Demand is a `200` on a paid route from a caller that is not a monitor.** Knock volume
   measures discoverability; a `503` on a paid route proves the product could not have been delivered
   to any buyer it attracted.

7. **Re-measure the classifier's own documented assumptions — the code comments are claims too.**
   A report carried a docstring stating a bare `/v1/<service>` returns `200` with an index body and is
   therefore free; a live probe of the same paths returned **`402`**. If that comment is stale, part of
   the "public/free — not sales" bucket may be paid routes answering without payment, i.e. the report
   would be *vouching for* the one defect that matters most. **A rule about what a path means is a
   measurement that expired silently.** Probe one path from each shape the classifier distinguishes,
   every time the classification changes a business number — and if you cannot settle it, say which
   bucket is now unverified rather than letting the old comment keep the assurance.

**The general shape:** before publishing any rate, ask *what else could produce this number*
— a catch-all handler, a crawler reading a signpost, a default page, a rotated source. If the
answer is "a lot of things", the number is a claim about your classifier, not about demand.

### A wildcard router answers 200 for paths that do not exist

A site whose catch-all serves the index page for any URL makes `curl -w '%{http_code}'` return **`200` on every
path that has never existed** — including a data file that was deleted years ago. Status alone cannot tell the two
apart, and a migration "verified" this way moves a dependency onto a path that serves the homepage.

Measured: a `curl` against a per-tenant JSON path returned `200`, which read as "the feed is live on the new host".
The body was `<!DOCTYPE html>` — the homepage — for that path, for a sibling path, and for the directory itself.
The real 404 had been replaced by a confident fake success, and the consumer script would have parsed HTML as data.
The move was reverted; a known-broken URL is safer than a confidently-wrong one.

- **Assert `content_type` and one identifying byte of the BODY, never status alone.** For a JSON dependency check
  `curl -s -o body -w '%{content_type}'` and require `application/json` before parsing.
- **Probe the parent directory AND a nonsense sibling in the same call — and compare BYTE COUNT or sha, not
  just content-type.** Measured: a real product path, its parent directory, and `this-does-not-exist-xyz` all
  returned **exactly 18,148 bytes** of the same homepage. Identical size is the fastest catch-all signature
  available; content-type alone can match while the bodies differ.
- **On such a host, NO link or route verdict means anything — establish catch-all first, then audit.** A link
  checker run against a wildcard site reports every path `200`, so a clean "all links resolve" is a statement
  about the router, not the site. **Test the nonsense sibling before you validate a single real URL**, and if it
  answers with the index page, say the link audit is void rather than reporting green.
- **A 404 is a more informative answer than a 200 with the wrong body** — when a migration turns a 404 into a 200,
  the fix has made the failure quieter, not smaller.

## Proving EXPOSURE needs a third-party vantage — and a control port

**A request from inside the estate to your own public address is not proof that anyone outside can reach
it.** Hairpin NAT and host routing can answer a call no external client can complete. The mirror trap is
just as real: a proxy answering for a port you believed was private.

Measured: a service bound `0.0.0.0:<port>` was genuinely reachable from the open internet while every
sibling bound `127.0.0.1` was not. The evidence that settled it came from a third party, not a local curl.

- **Ask a third party to fetch it.** Any external fetcher (URL-to-text service, remote probe, hosted
  browser) is a vantage you do not control. Fetch the same path on a port you believe is loopback-bound as
  a **control**: public answers + control times out = the exposure is real; both answer = the vantage is
  lying and you measured a proxy, not a port.
- **Name the door by its headers.** `server: cloudflare` + `cf-ray` = through the CDN; `server: uvicorn`
  (or no proxy headers) = direct to origin. Same application, two doors — and once the raw one is open,
  every edge control is optional to anyone holding the IP.
- **Read the bind from the socket, not from the config.** `ss -ltnp | grep -v '127.0.0.1'` lists every
  publicly bound listener; anything absent from that list is private. If a framework hardcodes
  `host="0.0.0.0"` at startup, find that line — the port will re-open on the next deploy.
- **`ufw status: inactive` proves nothing either way** — no host filter, or the filter lives at the
  provider. Check the provider firewall before concluding "protected" *or* "exposed". And never enable a
  host firewall blind on a Docker box: Docker owns its own chains and a wrong rule locks you out of SSH.
- **Price the exposure, not just the port.** An open origin puts an unauthenticated status or debug route
  on the public internet — a map of which services are down is competitive reconnaissance.
- **Contain before you refactor.** Close the hole with the rule that cannot break the app (provider
  firewall), then change the bind, then re-verify the public hostname still serves 200. The reverse order
  takes the product down while you are still proving the hole exists.

**Read the port's OWNER, not just its address.** `ss -ltnp` prints the process beside each socket, and the
owner decides the whole remediation: `traefik` on `*:443` is the front door you intended; **`docker-proxy`
on `0.0.0.0:<port>` is Docker publishing the container directly, which bypasses whatever reverse proxy you
believe is in front of it**; a `python3` on `0.0.0.0` is the app binding every interface itself. Three
owners, three different fixes — only the last is fixed by editing the app.

**A single open port can be the CONTROL PLANE, not a product.** An agent dashboard, admin panel or status
API answers `/api/health` and `/api/status` unauthenticated by design — version, commit, config schema —
so a scanner learns exactly what it is before it ever reaches a login form. Price that separately from a
data endpoint: a leaked catalogue is a competitive problem, a control plane behind only a password is an
incident waiting for a weak one. And ask the question that cannot be answered from outside: **was a
password ever set?** If nobody can confirm it was, treat the port as already compromised.

**If the reverse proxy has no route for the app, the loopback rebind is not the fix yet.**
`docker inspect <proxy> --format '{{json .Config.Labels}}' | grep -i <app>` returning nothing means the
public hostname is served by something you have not identified — a tunnel, another proxy, or the raw IP.
**Rebinding the app to `127.0.0.1` in that state takes the product offline**, which is exactly why
containment at the provider firewall comes first and the code change waits for the route to be found.

**Reaching it is not the same as being able to buy it.** A gateway that refuses every valid proof with
`payment_proof_invalid` is a verification-mode defect, and while it stands a zero-revenue number measures
the door, not the market. Depth lives in the `x402-api-compliance` skill's
`payment-verification-modes` reference file.

## Closing the hole: a rule that matched nothing looks exactly like a rule that worked

**Finding the exposure is half the job; the containment has its own silent failures, and all of them leave the
chain looking guarded.** Apply these in order and verify each one in the direction that can actually fail.

1. **`INPUT --dport <published-port> -j DROP` cannot match a Docker-published port.** Docker's `nat`
   PREROUTING rewrites the destination address **and port** to the container's before the INPUT filter is
evaluated, so a rule keyed on the host port is accepted, listed, and matches nothing. Measured: the raw port
   stayed open while the rule sat in the chain. Block published ports in `DOCKER-USER` (traversed after DNAT)
   keyed on the **container** port, or delete the publish so there is nothing to block.
2. **`iptables -t nat … -j DROP` is refused outright** on the nft backend (*"the nat table is not intended for
   filtering"*). `nat` rewrites; it does not drop. An error is at least honest — but it disappears inside a
   `&&` chain, so run the rule and the save as separate lines.
3. **An `-i eth0` rule can only ever protect, and can never be proven, from inside the host.** Traffic from the
   host (or a container on it) to the host's own public address is routed over **`lo`**, so it never matches an
   `-i eth0` rule: a local curl returns `200` before *and* after a perfectly correct rule. Reading that as "the
   fix failed" invites you to loosen a rule that was working. The same hairpin is the path a reverse proxy
   takes, which is precisely why an `-i eth0` rule fails **safe** for a host-networked app.

**So verify containment the way you verified exposure — from outside, before and after.** Inside, verify by
**counter, not by presence**: `iptables -L INPUT -n -v --line-numbers` prints packets matched per rule, and a
rule with `0` packets after real attempts has never matched anything, whatever its position looks like.

**Persist to the path the boot unit actually reads.** On Debian/Ubuntu, `iptables-persistent` restores
`/etc/iptables/rules.v4` via `netfilter-persistent save`; a hand-written `/etc/iptables.rules` is read by
nothing and the hole reopens at the next boot. Two side effects to state before the operator runs it: installing
the package **removes `ufw`**, and it prompts through `debconf` — which in a terminal presents as a **hang with a
blinking cursor**. Use `DEBIAN_FRONTEND=noninteractive`.

**When the fix needs an env var the container cannot take without a recreate, make the switch a FILE.** An
optional config file read at start-up — default unchanged, switched by writing the file and restarting, reverted
by deleting it and restarting — costs one restart either way and never rebuilds a container that nine other
services depend on. Prefer it over both "hardcode the new bind" and "recreate to add an env var".

**And record which window the containment covers.** A firewall rule protects the port, not the class: the same
accident will recur on the next service that binds `0.0.0.0`, so the durable artifact is a list of every
non-loopback listener with an owner beside it, re-read after any deploy.

Depth — the per-owner decision table and the exact commands: `references/port-containment.md`.

## Verifying a CHANGED artifact — three ways it lies, in the order they bite

A deploy is not a measurement, and the checks around it fail in three distinct ways. Each one produced a
confident wrong answer in a single evening.

1. **THE LOCAL HARNESS CAN SHARE YOUR BLIND SPOT — so a green matrix before deploy proves the model, not
the system.** A 16-case matrix was run against the real config and passed 16/16; the deploy then failed on
exactly the case the matrix had mis-modelled (an alias path the patch deliberately skipped). The harness was
built from the same mental model as the patch, so it could only ever confirm it. **Rule: read the change's
assumptions back out of the config, not out of your patch — and treat the first live request as the audit,
not as a formality after it.** A pre-deploy matrix is a good filter and a bad proof; say which one it is.

2. **A CONFIG SOURCE IS ONLY WIRED WHEN *EVERY* DECISION POINT READS IT.** Adding a loader inside the
implementation while the dispatcher still tests the old source means the new path is never entered — and the
failure message blames the old source, so it reads as "not configured" rather than "never consulted".
**Grep the gating condition, not just the feature.** After adding any new credential/config origin, find
every `if getenv(...)` / `if exists(...)` that routes on it and convert them all.

3. **A ROLLBACK HANDED OVER AS A SAFETY NET IS AN UNDO, AND IT WILL BE RUN AS IF IT WERE A REPAIR.** A
verified deploy was reverted by a "if anything looks wrong" command the operator ran *because* the previous
attempt had errored — the copy succeeded that time and silently restored the pre-patch file. **Label it
`UNDO` in the heading and the sentence, never offer it beside the deploy command, and after any restart
prove which artifact is live:**

```bash
# the file on disk must equal the patched copy AND differ from the pre-patch backup
cmp -s server.py /path/PATCHED-copy.py        && echo "live == patched"
cmp -s server.py /path/pre-patch.bak          && echo "⚠️ ROLLED BACK — the fix is NOT deployed"\
                                               || echo "live != pre-patch ✅"
grep -c '<marker-from-the-patch>' server.py    # 0 means the old code is running
```

Then verify the behaviour, not just the file: the acceptance probes must show the NEW answers (a refusal
where a successful charge used to be) with the OLD ones still intact on real paths.

**Corollary — hygiene that sweeps `*.bak*` will eat the rollback point it was written to protect.** A vault
cleanup pattern removed a code backup minutes after it was created, and the next rollback attempt reported
the copy "missing". **Code backups are rollback points and stay beside the code; only note backups are
clutter.** Keep a second copy of the patched artifact outside any swept tree.

## The instrument must read the artifact the SYSTEM writes, not a copy of it

**A log is only the log if you read the path the writer uses.** Measured twice in one session, in two
independent scripts: a log directory had been moved out of a synced tree to save quota and both scripts
were repointed at the new copy — but the service computes its log path from its OWN module location
(`dirname(__file__)/logs`), so its next restart recreated the directory at the original path and wrote
there. The copies stopped at 7,612 records; the live file passed 8,549 and contained **the first real
sale in company history** — invisible to the watcher built to find it.

- **Resolve the path the way the WRITER resolves it.** Read the producer's code for how it computes its
  output location and point the consumer at exactly that. A path you chose is a path you hoped for.
- **Never trust a path because it exists and is non-empty.** Both files were valid JSONL with plausible
  content. Compare **mtime and line count against the live process's start time**, or read a field only
  the live writer can produce.
- **When a watcher reports a number that has not moved, suspect the path before the system.** "Zero
  events" from a frozen file is indistinguishable from "zero events" from a healthy one.
- **Keep a fallback list ordered live-first, and print which path was used.** A silent fallback to a
  stale copy is the failure; a printed path makes it visible.

### A field that is absent from THIS artifact inverts the classification

Before splitting any population on a field, confirm the field exists in the file you are reading.
Measured: a report classified requests by payment-signature evidence — which exists only in the
**payments** log. In the **traffic** log that key never appears, so every request read as "no signature"
and **every sale classified as free**: the same lie the report had just been fixed to remove, pointing the
other way.

- **`d.get(field)` returning `None`/empty means "not in this file" as often as "not set".** Dump one
  whole record and list its keys before classifying on any of them.
- **If the field lives in another artifact, the classifier is a JOIN on a stable key** (path + timestamp,
  request id, tx hash) — and the join width must be printed, because a join that silently matches nothing
  looks exactly like a clean result.
- **Run the split against one case you know is true.** One real paid request and one known-free request in
  the same run; if the paid one lands in the free bucket, the instrument is wrong, not the world.

### Reading a program is not measuring it

A source-parsing audit of "does this job stay silent when it has nothing to say" produced **four false
accusations in one sitting** — a header-only read, two regexes that missed indirection, a three-line
wrapper judged as the program, and an 18-line shim mistaken for the work. Each was confident, each was
wrong.

**To know what a program does, run it and measure the output**: twice, on input that produces nothing, and
count BYTES. A parser is a hypothesis about behaviour; the run is the behaviour. Keep the parser as a
cheap pre-filter and let the probe overrule it — never the reverse.

## A monitor must read the LIVE binding, not a constant — and must know the difference between "answers" and "has capacity"

**A gate that is told which thing to check will drift from the thing that is running.** Measured: an allowance
gate held `binding_name = "ollama-cloud"` as a literal and a comment declaring the actually-active rail
"retired". Every run was green, about the fallback, while the primary served all traffic — and when the provider
changed its response shape the gate crashed on every run for days without anyone noticing, because a monitor that
fails is a quiet as a monitor that passes.

- **Read the binding out of the same config the system reads**, on every run, and **report a disagreement** when
the estate is not uniform (one seat left on an old rail must surface, not be averaged away).
- **Never let a monitor crash into silence.** Exit non-zero and say `CANNOT RUN`; a monitor whose own failure is
  indistinguishable from its success has negative value.
- **Liveness is not capacity.** A completion proves the rail *answers*; it says nothing about remaining
  allowance. On any metered or subscription surface, derive the verdict from the **binding constraint** — the
  fullest window, the lowest balance — not from the happy path. A gate that can only say "up" reports 99%
  spent as healthy right up until the moment it stops answering.
- **Report every lane in the chain, each against the meter that lane actually publishes.** A fallback is capacity
  and, on a metered rail, it is money: the bill and the thing that carries you during an outage are both
  invisible if you only watch the primary. Where a provider publishes no meter, the verdict is `NO_PROVIDER_METER`
  — never a number inferred from your own logs.

## A checker must accept the closure formats the system actually writes — including its own annotations

**A real reply in an unrecognised format is indistinguishable from silence, and it teaches the responder that
answering does not register.** Measured: two checkers independently reported notes as unanswered for 8 days
while the notes carried `## STATUS: ANSWERED — closure record` with dated, measured answers; the scanners only
knew `## Receipt` / `## Agreement` / `## Supersede`.

- **Grep the artefact for near-miss formats before concluding a thing did not happen.** The cheapest diagnostic
  is `grep -iE 'answered|closed|receipt|ack'` over the files the checker says are missing — it separates "nobody
  replied" from "nobody replied in my dialect" in one command.
- **Accept documented absence as a pass.** A skill or note that says *"this file does not exist"* is the repair,
  not the defect; a scanner that flags it leaves the count unchanged and re-fixes the same item forever. Same for
  a note naming itself.
- **Count and NAME the delta.** "+3 since last run" with one example is a nag: the reader knows something exists
  and cannot act on it. Any delta must list every new item, then the aggregate.
- **Do not print the same item under two headings.** Two sections derived from overlapping predicates (a receipt
  fact and an age band) will list the same rows twice, and a reader who counts lines concludes the queue is
  twice its real size. Emit each item once, under its worst status, and say what the other section now means.

## The right status with the WRONG VALUES is the most convincing failure there is

**A `200`, a `402`, or a green deploy all answer "did the request succeed", and none of them answers "is
the number right".** Wrong values wear every marker of success: correct status, correct shape, plausible
magnitude. Read the values a consumer would receive, then check each one against a second source.

Measured, three ways in one evening:

- **A paid route issued a perfect `402` on all six rails and charged the default price.** The service was not
  in the manifest the gateway actually loaded, so the price fell through to a fallback. The status was right;
  the amount was 10× the advertised one. **On anything priced, assert the AMOUNT, not the challenge.**
- **A dashboard rendered an index table full of `—`.** Status `200`, layout perfect, deploy reported success —
  and every cell was a placeholder because the field names were **guessed** (`change_24h`, `returns`) instead of
  the provider's (`change_pct_24h`, `roi_7d`). **A dash in a data table reads as "no data" when it is really
  "I asked for a key that does not exist". Dump one whole provider object and map its real keys before
  formatting.**
- **The same table printed `+0.03%` for a move of `2.56%`.** The provider returns **fractions**, and the
  formatter assumed percents — a silent 100× error that still looked like a small, believable number.
  **Never infer a unit from magnitude; find it in the payload or a worked example.** A value of `0.0256` is
  either 2.56% or 0.03% depending entirely on a contract you have to read, and both render fine.

### A page can  serve the new code and still RENDER the old values

**`200` + the new string present in the HTML + matching byte count is not a rendering check.** A cached edge
copy, a stale browser document, or a client-side `fetch` of cached JSON shows the previous state while every
byte-level assertion passes.

- **Read the rendered cells, not the source** — query the DOM for the values a user sees and assert those; text
extraction of `document.body.innerText` is the only read that covers fetch → parse → format.
- **Cache-bust with a value that cannot collide** (a timestamp — and note that `"?cb=$(date +%s)"` inside
SINGLE quotes is not expanded, so the fetch silently returns the previous body).
- Deploy-specific depth — the dash-for-a-missing-key signature, fraction-vs-percent formatting, `_headers`
survival, catch-all 404s — lives in `portfolio-deployment`. Note the overlap only; do not restate it here.

**The general shape:** for any surface whose value matters, the acceptance assertion is on the **number the
consumer receives**, cross-checked against a second source (a receipt, a contract endpoint, the provider's own
object) — never on the status, the deploy result, or the presence of the new code in the artefact.

## The artifact you EDITED may not be the artifact that is READ

**An edit that produces no behavioural change after a restart is a claim about WHICH file is loaded, not
about the code.** Measured: three consecutive deploys-plus-restarts of a route that had been added correctly
changed nothing — every edit had landed on a copy the process never consulted, and a search order decided
which copy won. The failure looks like "the code is wrong" and invites a fourth edit of the same file.

- **Enumerate every candidate copy before editing, and determine which one WINS.** `find / -name '<artifact>'`
  inside the container the process runs in, then read the loader's candidate list. A directory holding four
  variants of one config is a search order, and the order is the specification.
- **`Errno 30 Read-only file system` means the path is a bind mount, not that the file is protected.** The
  writable original is the **bind source** on the host side; edit there. Copying over the mount point fails for
  the same reason, and an `except` that "restores a backup" into the same read-only path fails identically —
  twice in one run, which is how a fix script reports failure with a traceback about its own error handler.
- **Prefer a search order in which a WRITABLE copy outranks a read-only mirror**, and write the measurement into
  the comment so the next reader does not re-derive it. A file the process cannot write must never be the one it
  reads: every future edit is silently discarded and every symptom returns after the next restart.
- **The tell is a value reverting to a DEFAULT rather than to the previous version.** A price that comes back as
  the platform default (`0.01` where `0.003` was written) is not a stale cache — it is a lookup that missed and
  fell through, which means the entry was never loaded at all.

### Replacing a registry or manifest — prove SUPERSET, never just "it works"

When the change is to **replace a whole file of records** (a service manifest, a price list, a routing table, a
allow-list), a working probe afterwards proves almost nothing: it proves the entries you happened to test are
present. **The risk is what the swap REMOVED or altered**, and that failure is invisible from any passing check.

1. **Diff old against new before deploying.** Count entries on both sides, then assert **the only delta is the
   intended addition** — print it as a line a reader can check (`source 14 · written 15 · altered other than the
   addition: NONE`), not as "looks right".
2. **Generated from the live source, never hand-edited.** Produce the new file from the copy that is already
   serving, so lineage is provable; a hand-written replacement is a rewrite wearing a patch's clothes.
3. **Probe a survivor live, and assert its VALUE.** One unchanged route must still return its original amount
   (or price/count), not merely a 2xx. A swap that fixes one entry and silently reprices nine is worse than the
   bug it fixed, because the nine are already selling.
4. **Keep the refusal behaviour too.** Entries marked unservable, excluded or deprecated must still be excluded —
   a regenerated file that drops the exclusion block resurrects things on purpose retired.

**Same rule for any "replace the whole tree" deploy**: the acceptance test is that everything OUTSIDE the change
is byte-identical afterwards, and the cheapest way to prove it is to check the untouched set, not the changed one.

## The test to apply before reporting anything as verified

> **"What would have to be true for this check to fail, and has it ever failed that way?"**

If the answer is "it could not fail", the check carries no information. Go find one that can.
