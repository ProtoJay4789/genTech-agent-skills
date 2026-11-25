# The inbound reply lane — answering on OUR repos, safely

**The human-in-the-loop rule exists because an OUTBOUND PR spends someone else's attention and reputation.**
An **INBOUND** question on a repo we own is support work: nobody needs protecting from it, and silence there is
the damage. Conflating the two produces the worst available outcome — a stranger's question sits for months
while the agent that could answer it cites a rule about not commenting.

```
OUTBOUND (someone else's repo)   human, unchanged. No agent speaks there.
INBOUND  (our repo)              a bounded reply lane: it answers, never argues, cannot invent.
```

## Gate order — enforced in code, not in a prompt

```
allowed_repo(owner is ours)  →  token_for(owner)  →  can_push(repo)  →  body gates  →  post  →  read back
```

## Three owners, and two of them differ by ONE HYPHEN

An **org** and a **user** can carry names one character apart, and a given token holds **opposite** write
permissions on them. Measured: one token held `push: true` on the org's repos and `push: false` on a
catalogue repo owned by the similarly-named user account, while the other token was the exact mirror image.

- **Route the credential by the REPO'S OWNER**, never by "the GitHub token". Keep an explicit owner→token map
  and read the owner off `full_name`.
- **Preflight with `GET /repos/{repo}` → `permissions.push`.** A gate that cannot fail is a decoration. Without
  it a perfect draft dies `403` at the last step, which reads as a permissions mystery rather than a routing
  mistake.
- **A write that SUCCEEDS with the wrong token is worse than one that fails.** A comment on an org repo posted
  with a personal token is published in a person's voice — an identity claim nobody authorised. Check
  `GET /user` for the token's identity and name which account spoke in the report.

## Gates that make an auto-reply safe

1. **A reply may only restate what we PUBLISH.** Scan every claim-bearing sentence (*we support*, *is live*,
   *price is*, *fixed in*, *now available*, *we offer*) and require an anchor from the docs or manifest that
   actually says it. Unanchored → **demote to a draft for the human, do not post.** A bot that invents "yes we
   support that" to a customer is a fabricated receipt aimed outward.
   **When the gate refuses a sentence that is TRUE, do not weaken the gate — replace the sentence with a
   checkable handle.** A line saying a change is "live" has no evidence attached even when it is correct; the
   same line naming the merge commit, the response header, or the byte count is auditable by the reader. The
   refusal is the gate doing its job, and the rewrite is always the better copy.
2. **A minimum length, or it is a shrug.** A two-word acknowledgement is indistinguishable from a bot that read
   nothing; require a sentence that references their actual ask.
3. **Idempotence by body hash, per `(repo, number)`.** A daily job that re-posts its own reply every morning is
   worse than no lane. Record the normalised body and refuse a verbatim repeat.
4. **No merge, no close, no label outside a fixed vocabulary.** Those are publishing decisions.
5. **A class you cannot decide is the human's.** Price, commitment, timeline, security, or a submission's
   acceptance are `HUMAN` by default — the safe class, never the convenient one.

## Classify into exactly three buckets

| class | test | action |
|---|---|---|
| **ANSWERABLE** | the ask maps to something we publish (docs location, liveness, how to pay, how to connect) | draft from the published anchor, post allowed |
| **HUMAN** | a decision, price, promise, timeline, security report, or acceptance of a submission | suggested reply written to a drafts dir, labelled for the owner, **never posted** |
| **COURTESY** | they thanked us, conceded, or withdrew | one-line close, no question asked back |

The default for anything unclassifiable is **HUMAN**. An empty or unreadable thread is **UNKNOWN**, and must
never fall through to a draft that guesses.

## ⚠️ A PR with ZERO comments carries its question in the BODY

Reading only `/issues/{n}/comments` returns an empty list and reports *"could not read the thread"* — a
different and much more alarming claim than *"there is no comment yet"*. A fresh submission or issue is exactly
this shape: an opening message, no replies, and the thing to answer sitting in the body.

- **Fall back to `/issues/{n}` and read `body`; record which source the text came from.** "Last comment" and
  "opening message (no replies yet)" are different findings about how stale the thread is.
- **Verify a posted reply by re-reading the thread** and report the comment id + URL. A `201` from the POST is a
  claim; the comment appearing in the collection is the record.

## Pipeline shape

```
reader (existing inbox job) → snapshot of inbound ids
   → classifier (this lane)  → drafts dir, one file per thread, class in the header
   → poster (gated)          → allowed_repo → token_for → can_push → body gates → post
   → ledger (jsonl)          → (repo, num, body_key, url) for idempotence and audit
```

**Every draft is written to disk with its class in the header**, so the daily report can print the class beside
the thread. The human read is never removed — it is ROUTED.
