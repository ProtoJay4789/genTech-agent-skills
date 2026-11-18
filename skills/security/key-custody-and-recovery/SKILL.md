---
name: key-custody-and-recovery
description: "Use when key custody must survive a host wipe."
category: security
version: 1.0.0
author: Hermes curator
tags: [custody, keys, secrets, backup, disaster-recovery, wallets, shamir, threshold]
related_skills: [gentech-wallet-management, destructive-write-guards, claim-provenance]
metadata:
  hermes:
    tags: [custody, keys, secrets, backup, disaster-recovery, wallets, shamir, threshold]
    related_skills: [gentech-wallet-management, destructive-write-guards, claim-provenance]
---

# Key custody and recovery

## When to Use

Load this when any of the following is true:

- keys, seeds or credentials must survive a host rebuild, migration or wipe;
- a new wallet or rail is being created and will be funded;
- an existing wallet must be operated and you have not yet located its key;
- someone asks for a "backup plan" for funds, or proposes backing up key files more often;
- a host, volume or account was lost and you are assessing what is recoverable.

How to hold keys and secrets so a host rebuild cannot destroy them — and how to prove that claim instead
of asserting it.

**One rule above all: a key that exists only on this host dies with this host, however many copies of it
live on this host.** A backup sharing a failure domain with the original is not a backup. When a host is
lost, "back up more often" is the wrong repair; the correct repair is **custody**.

## The three custody rules

- **C1 — the means to open the vault must live elsewhere.** Ciphertext may sit on the host; the passphrase
  must not be derivable from the host alone. A `.key.enc` beside its own `.passphrase` is two-factor
  custody that fails as a single factor.
- **C1b — a remediation is judged against the FAILURE DOMAIN, not the path.** Before proposing a move,
  NAME the domain (host / volume or device / account / identity) and check the move crosses one. A
  relocation *within* a single domain relocates nothing. Measured: "move the passphrase out of the backup
  directory" was proposed and would have changed nothing, because both paths sat on the same volume — and
  the volume WAS the domain. **Assert domain identity by measuring it** (`(hostname, st_dev)`), never by
  reading a directory name; two paths under different trees are one domain, and two mounts under one tree
  are two. A fix that cannot be distinguished from the state it claims to remedy is the same defect as a
  number with no instrument.
- **C2 — no funded account may have exactly one key-holder.** Where the agent is the only signer, a host
  loss cannot move funds *and* cannot freeze them: one failure with two outcomes. Threshold custody
  (Safe-style m-of-n, agent holding exactly one signer, human holding the rest) removes both.
- **C3 — a backup that has never been restored is a hypothesis.** Restore must be a command, and it must
  be drilled against the recorded addresses *before* the account holds anything.

## A SPLIT KEY IS NOT A THRESHOLD — the rule C2 is easy to misread without

**A 2-of-3 shard split and a 2-of-3 Safe are different mechanisms, and only one gives accountability.**
A Shamir share set splits **one** key: any m shares **rebuild that one key**, and then **one signer
signs**. The transaction carries a single signature, indistinguishable from the original key's — so
there is **no attribution**, and nothing in the result says who authorised it. A Safe holds **n distinct
keys** and requires m signatures, so *"who authorised this"* is answerable by construction.

**Consequence, and it is the whole point: "multiple key signers" cannot be built by splitting one key.**
Split it a hundred ways and there is still one signer. If the requirement is accountability, the artifact
is a Safe (or equivalent m-of-n) — **a build, not a config**. If the requirement is only "no single shard
opens it", a split suffices and must be described as a split, never as multi-signer custody.

**And check WHICH secret the split protects.** Measured: a keystore index reading
`"passphrase_shards": "3 shards, threshold 2"` was splitting the **bundle passphrase**, not the key — so
the shares guarded a door whose key sat in the same directory, and the threshold was decorative the whole
time. **Name the secret the shares rebuild before calling any scheme a threshold.**

## Custody is a declared MODE, with its price printed where the choice is made

One holder per book is a **decision**, so record it as one. Three modes:

- **SOLO — the default, and the right default.** One person, one key, ciphertext off the host. **Ship
  this and only this as a product default:** it needs no consent apparatus, and it cannot leave a user
  believing they hold a safeguard they do not have. *"Everybody makes their own"* is honest and simple;
  complexity is where custody fails.
- **DELEGATED — one holder, n beneficiaries.** Legitimate, and common in a family book. **Two things make
  it a model rather than an accident, and only two: (1) informed consent from each beneficiary, recorded
  in the book's own state; (2) a documented RECOVERY RIGHT — a break-glass that survives the holder
  being unreachable.** State its risk plainly, in the record: **the holder can move any member's funds
  unilaterally, the holder IS the single point of failure, and any threshold is decorative** because the
  holder satisfies it alone.
- **THRESHOLD — n distinct signers, m required (a Safe).** The only mode with real accountability.

Always-on rules that apply to every delegated book:

- **Trusting someone with an ACCOUNT is not consenting to custody of a SIGNING KEY.** Different grants;
  ask for the one you need, and record the answer.
- **CONSENT EXPIRES SILENTLY UNLESS IT IS RE-ATTESTED.** A commitment recorded once and never revisited
  is how *"one person holds everything"* quietly becomes permanent — members leave, a holder becomes
  unreachable, circumstances change. **Attach a re-attestation milestone (annually is a sane default)
  and make SILENCE NOT COUNT AS RENEWAL.** The duty runs both ways: the holder owes the beneficiary a
  reachable break-glass, and the holder's own milestone confirms it is still reachable.
- **`host_holds: none` is an INVARIANT, not a mode.** No shard and no passphrase on any host, under any
  mode, ever. **If a host holds shard material beside the ciphertext it unlocks, the declared mode is
  fiction** — the protection is nominal no matter what the record says.
- **Report a declared-but-incomplete mode as such.** A Delegated book with consent recorded and **no
  break-glass named** is DECLARED, NOT COMPLETE. Say which half exists.

The mode table, the per-book disclosure record, and how to record a consent faithfully are in
`references/custody-modes-and-consent.md`.

## Order of operations — do not reorder these

1. **Build the recovery path.**
2. **Generate the keys** under it.
3. **Drill the restore** and quote the drill output (derive every address, compare to the recorded set,
   and assert that a sub-threshold share opens nothing).
4. **Get the human-held half off the host** — this is the critical path, not a formality.
5. **Fund last.** An address handed over before the drill exists is the standing rule *never park real
   funds where we hold keys in only one place* rebuilt by hand.

## Locate the key before you plan any operation

An account is operable only if its key is in exactly one of three places: a **host file**, a
**provider-managed keystore you control via API** (e.g. CDP), or **a human's custody**. Locate it and
**derive the address from the key material** to confirm it matches — before planning a sweep, rebalance or
transfer.

If the answer is "nowhere", the honest report is **unrecoverable**, not "recover it later". Say so before
anyone plans around the balance or scopes work that depends on it. Two traps here:

- **A non-root agent cannot check root's material.** Check your own uid first; a key file under `/root`
  that survives is the human's to find, and "I found nothing" is not the same as "nothing exists".
- **Missing key material is a finding, not a green light.** It means the accounts are unoperable and the
  rails are down. Report that, rather than quietly rebuilding on top of it.

## Proving a wallet is UNSPENDABLE — a zero needs a denominator

**"No key on this box" is a claim of absence, so it needs the same complete probe as any other negative.**
Do it by derivation and report three numbers, never one:

```python
# every 64-hex in every credential-shaped file, each derived to an address
from eth_account import Account
for m in re.finditer(r'(?:0x)?([0-9a-fA-F]{64})(?![0-9a-fA-F])', text):
    Account.from_key('0x'+m.group(1)).address        # compare, never print
```

Report **files scanned · distinct addresses derived · matches for the target**. "Zero matches across 2,393
files yielding 88 addresses" is a measurement; "the key isn't here" is a guess, and it reads identically
to a scan that never ran.

**Run `scripts/key-sweep.py --root <dir> --targets <addr…>` rather than hand-typing the loop** — it reports
the three numbers, prints paths only (never key material), exits 2 when `eth_account` is absent so a missing
dependency cannot read as "clean", and stamps the hash-inflation caveat into its own header. **Run it per
scope (vault, whole estate, each host volume) and report each separately** — one combined number hides which
tier was actually covered.

- **The derived-address denominator is inflated by HASHES — say what it actually bounds.** Every 64-hex string
  derives to a valid address, and any real filesystem is full of `sha256` digests, so a whole-estate sweep
  reports tens of thousands of "addresses" that are hashes (measured: 207,791 files → 172,046 derived, the top
  hits being a Tcl encoding table at 219 files). **Publishing that number as "172,046 keys exist" is false, and
  discarding it is worse.** The correct sentence is bounded by the input class: *"among every 64-hex string
  anywhere on this host — keys and hashes alike — not one derives to the target."* That is a genuine negative
  with a denominator; anything vaguer is unreadable and anything more confident is uninformed.
- **A key-shaped string that derives is not necessarily a WALLET key.** `API_SERVER_KEY`, session tokens and
  HMAC secrets are frequently 64-hex, so a match list can be entirely non-wallet material. **Name the variable
  each derived address came from (never its value)** — `API_SERVER_KEY`, not "a key found in `.env`" — so the
  reader can dismiss it in a second instead of chasing it.

- **A documented wallet is not a held wallet.** The address in a note, a skill or a memory entry is a
  *separate claim* from the key material, and when they disagree the note is what is wrong. Measured: a
  skill's "the FUNDED wallet" was funded and unreachable — no key anywhere derived to it — while the
  address the shared key file actually controlled held the same token and no gas.
- **`nonce 0` proves "this wallet never SENT" — never "this wallet never PAID".** Read nonce only as a
  statement about the wallet's own outbound transactions. Under **EIP-3009 `transferWithAuthorization`** the
  **facilitator** submits the transaction, so a payer's nonce stays `0` however many times they pay an x402
  endpoint: measured on one day, a wallet with `nonce 2` had made **ten** payments and a wallet with `nonce 0`
  had made one. The inverse also misleads — a high nonce (`53`) means an *active wallet*, not a repeat customer.
  **When grading payers, count settlements from the ledger or the chain's Transfer logs, never from nonce** —
  and say which of the two you counted, because "nonce 0, so one-shot agent" is a sentence that reads like a
  measurement and is not one.
- **Check the GAS asset separately from the token balance.** A wallet holding USDC and zero native ETH
  cannot send anything; reporting "it has funds" is true and useless. State both, and state which one is
  the blocker.
- **A ghost wallet is a relabel job, not a recovery job.** When the key is provably gone, the honest output
  is "retired, X unspendable, do not fund it" — and every instruction file that still names it must be
  corrected (see the retirement step below). Do not keep a dead address in a live procedure because the
  money is visible on-chain.

## One key file, many seats — UNIFY BY SYMLINK, never by copy

**"Everyone uses the same wallet" is a property of the key file, not of the address in the docs.** Seats
that each generate their own key on first use silently become different wallets — measured on this fleet as
four key files resolving to three addresses, two of them empty. A shared mount makes the fix trivial:

```bash
for seat in <seats>; do
  ln -sfn /opt/data/.blockrun/.session /opt/data/profiles/$seat/home/.blockrun/.session
done
```

- **Verify by inode AND by derivation**, not by a directory listing: all paths must share one inode, and
  each seat's own path must derive the canonical address. Two checks, because a symlink to the wrong file
  looks correct.
- **A copy-per-seat model is what produced the drift.** Copies diverge the moment one seat's client
  regenerates; one file cannot.
- **Back up any superseded key before replacing it, even an empty one**, and get the owner's word before
  deleting key material — that action is one-way and the balance being zero does not make it reversible.

## Receiving addresses vs spending wallets

- **Receiving / payTo addresses must have a permanently held key** — the human's own EOA, or a
  fleet-held key file.
- **Provider-managed wallets rotate**, so they are for *spending* only, where a rotation costs the
  deliberately small float.

Routing a payment to a rotating wallet strands it the moment the wallet is superseded — money arrives at
an address whose key nobody holds. This is a recurring mistake, not a hypothetical.

## Retiring a burned key — a key that has been READ is burned, whether or not anyone found it

**"Nobody found it" is not a reason to keep using a key.** Once key material has been written into a
document, a repo, a commit or a chat log, copies exist in places you do not control and cannot
enumerate. **Deletion closes the future; it does not un-share the past.** Retire and regenerate.

Retirement procedure, in this order:

1. **Prove the key is live before acting on it.** Derive the address from the stored material and
   compare to the recorded address (`eth_account.Account.from_key(k).address`). A key-shaped string
   that derives its own address is a working key, not a fixture. **Never print it** — compare and
   report the verdict only.
   - ⚠️ **DERIVE IT — never trust a recorded key↔address pairing, including one in your own notes.** The
     pairing is a separate claim from the key material, and when the two disagree the pairing is what is
     wrong. Measured: a leaked key recorded against address X actually derived to address Y — a
     *different* address that merely appeared in the same file — so the entire severity assessment had
     been aimed at the wrong wallet. Derivation is cheap; a severity call built on a stale pairing is not.
     If no derivation tool is present, get one rather than reasoning from the note.
   - **Bound the blast radius by measurement, cheapest check first — three checks:**
     1. **Anonymous exposure.** Fetch the published artifact with NO credential. An authenticated read of
        your own file shows the owner's view and cannot establish that a stranger can read it.
     2. **What the derived address holds.** Balance AND nonce, on every chain that matters. `nonce 0` with
        a zero balance states "never signed, nothing held" — a stronger fact than "empty."
     3. **Overlap with live wallets.** Compare the derived address against every address the fleet actually
        operates (payTo, payers, treasury, keystore). **Zero overlap is the finding that turns "exposed
        key" from an emergency into a cleanup** — say it in those words, because it changes the response.
   - **An empty balance is not by itself evidence of safety — ask WHY it is empty.** An address that is a
     known sweep target is empty *because* it is drained: that bounds the risk (nothing can accumulate)
     while leaving it permanently unsafe to fund (the standing order must keep saying so). "Empty" and
     "drained" produce the same number and opposite postures; name which one you measured.
   - **Severity is a measurement, not a narrative.** State what the key controls, what it cannot reach, and
     what remains unknown (chains you could not read). Do not inherit yesterday's urgency wording into a
     report whose numbers have changed — restate the severity from today's numbers, even when the
     conclusion reverses.
2. **Enumerate what the ADDRESS owns and is, before retiring it.** ⚠️ An address is not only a
   balance. Agent-identity registrations, name records, NFTs, allowlist entries and approved spenders
   are bound to the **ADDRESS**, and retiring the key does not move them. Measured: an apparently
   trivial rail wallet also held an **ERC-8004 `AgentIdentity` ERC-721**, so sweeping and retiring
   would have stranded the identity. Check holdings (`/token-balances`) and, for each, whether it can
   migrate (`ownerOf` / `transferFrom` on its registry) or is soulbound — **before** announcing
   "safe to retire".
3. **Validate the DESTINATION before a single unit moves**, then sweep the balance out to it. Two checks,
   both cheaper than the incident: **the EIP-55 checksum must match its own canonical form** (a mistyped
   character almost always breaks the checksum, which is precisely what it is for), and **the address must
   be an EOA, not a contract** — `eth_getCode` returning bytecode means funds sent there may be
   unrecoverable. Never send to an address that has only been typed at you. A dust balance is
   still worth sweeping: the object is the discipline, not the amount.
   - **A `403` from a public RPC is usually a header block, not an outage.** Before concluding a chain is
     unreachable, retry with a real `User-Agent` and try several providers — five public RPCs for the
     same chain answered with `chainId` once a UA was set, where every one had refused a default one.
   - **Watch the gas asset.** On a chain where the native token pays gas you cannot send the full balance;
     leave enough for the transfer, and show the computed amount **before** sending, never after.
4. **Regenerate on the same rail** under the standing custody rules (new key in the keystore or the
   human's password manager — never a document, never a repo), and repoint every config that named
   the old address.
   - **Split the repoint sweep: INSTRUCTION files get edited, HISTORY files do not.** A dated ledger
     naming the old address is a true record of a past spend; rewriting it destroys evidence. Edit only
     files that tell a reader what to do now — skills, reference docs, live configs, scripts — and count
     the two classes separately so the ratio is auditable (measured split: 57 instruction files corrected,
     48 history files deliberately untouched).
   - **Relabel, do not delete.** The retired value keeps its place with a status line: what it was, that
     it is retired, that its balance is unspendable, and **do not fund it**. Deleting the mention makes the
     next reader re-derive the same dead end from the chain.
   - **Mark the value in prose, leave code fences alone.** A blanket replace inside an example turns valid
     JSON into broken JSON; walk the file fence-aware and annotate only the prose occurrences.
   - **Insert the status banner after the first heading, never above the frontmatter**, or the skill stops
     parsing. Verify the frontmatter still loads after the edit rather than trusting the write.
   - **Fix the richest copy and promote it up.** Seat copies are often ahead of CORE on unrelated lines;
     diff first, edit the best copy, then write it to every tree so the sweep does not fork a second
     divergence.

**"Make this wallet single-chain" is not a thing a key can be configured to be.** An EVM private key
derives the **same** address on every EVM chain, so a compromised key is compromised on all of them at
once and there is no per-chain scope inside it to set. **Enforce isolation in the SIGNER instead:**

- **one key per rail** — never one key reused across rails;
- **bind the signer to a chain** — refuse to sign when the transaction's `chainId` does not match the
  rail that key belongs to (this extends the existing "signer must equal the configured wallet" guard);
- the rail's config names its own wallet per chain, so one rail's signer is unreachable from another
  rail's settlement path.

Then report isolation as **enforced**, not promised. "It has no activity on other chains" is an
observation about the present, not a property of the key.

## What may never travel through chat

- **Never type, paste or accept a private key, seed phrase or share/shard in chat** — not even to "get it
  saved". It lands in session history, logs and the model transcript, which is a permanent exposure with
  no rotation story.
- When a human hands you key material anyway, **route around it**: point at a file path, have them copy it
  themselves, and tell them to rotate. Never reuse it because it was convenient.
- The human-held half of a custody scheme is handed over as a **path plus a physical destination**, never
  as content in a message.
- **"I'll delete the message afterwards" is not a remediation — the copy is not in the message.** A user who
  wants to move a share through chat will offer exactly that plan, and it must be refused. Measured on a
  credential already pasted: **8 indexed copies** survive — 5 in the message row itself (`content`,
  `tool_calls`, `reasoning`, `reasoning_content`, `api_content`) and **3 in the full-text search shadow
  tables** (`messages_fts.*`, `messages_fts_trigram.*`), which keep **their own** copy of the text. A delete
  that cleaned the message row would not clean the index built from it — and an agent typically has **no
  message-delete capability at all**, so even the visible half of the plan is not executable.
  - **Give the count, not the warning.** The user's model is "a message is a thing that can be removed";
    naming the row AND the derived indexes is the form of the argument that reaches them. Restating the
    risk abstractly a second time does not.
  - **Offer the transport that costs nothing extra: a file.** If the user describes the recipient
    *downloading* something, they have already chosen a file transfer — point at that instead of inventing
    a new channel.
  - **Accept the override, correct the transport.** An owner may legitimately override a custody ordering
    and still be wrong about this one link in it. The safe channel rarely costs more than the unsafe one,
    so this is not the place to trade safety for speed.

## Where a pasted secret ENDS UP — the paste becomes an archive

**The chat message is only the first copy.** The chain that follows is what makes the exposure durable:

**pasted into chat → session transcript → long-term memory → nightly backup → archived snapshot.**

Measured on this fleet's own vault: a corpus of **~540 token-shaped strings sat in the archived memory
backups**, not in any live config — **every live `config.yaml` was clean.** So the residue of pasting is
not a chat problem that ages out; it is a corpus that **accumulates in the backup/archive tier and is
inherited by every future restore.** That is the mechanism behind the rules in this section, and it is
why "reference secrets by name" is a standing preference and not etiquette.

Two consequences worth stating in the report:

- **Treat a backup/archive tree as a credential corpus, not as notes.** Any job that copies one into a
  repo, a bundle or a mirror moves every pasted secret into a durable, shareable store — gate that path
  with the preflight before it runs (see `references/secret-preflight-gate.md`).
- **Where the archive lives decides the severity.** Encrypted, account-gated sync = within policy; a
  **git repo** = not. Verify which one holds it rather than assuming, and prove the negative with a
  command (`git ls-files | grep -c '<archive-path>'`).
- **Never poke a found credential to see whether it is still live.** Calling the provider with it *is*
  using it. Report, name the owner, recommend rotation, and record liveness as **unmeasured**.

## Handing the human-held half to a human

- **A password manager, never a notes app.** Notes apps are cloud-synced plaintext: one account compromise
  and the wallet is gone. A password manager or paper in a safe gives the same convenience with real
  encryption.
- **Prefer a BIP-39 seed phrase to a raw private key.** 12 words are writable and re-readable by hand and
  derive both EVM and Solana keys; 64 hex characters have no error tolerance and a typo is
  indistinguishable from a wrong key until it fails on-chain. Convert before funds exist — the restore
  story is what matters at 3am after a wipe, not the derivation convenience today.
- **The human runs the restore, not the agent.** Hand them the command so the plaintext appears only in
  their own terminal, and tell them to delete the dump directory afterwards.
- **Ship the command that moves ONE share to a destination.** A manifest states destination *slots*
  (password manager / paper / the other person), but a scheme with no extraction step gets completed by
  whatever is easiest at the time — which is chat. Provide a narrow command that copies a single named share
  to a user-supplied path, applies `0600`, and **never prints the contents**, and print the slot labels
  beside the copy. Then the safe path is also the shortest one, which is the only way it wins.
- **A notes app is not the failing side of this — the *form* is.** A password manager's **secure note** holds
  arbitrary text and is the correct home for a share; the restriction is on the browser-autofill class whose
  mechanism is injecting a secret into a bound origin's form. When a user says they are "waiting for a
  password manager that can store this", they are waiting on a capability they already have — say so, rather
  than letting a 15-minute task queue behind a feature request.

## Brokering credentials is not the same as holding keys

Two different problems, two different answers — do not solve one with the other's tool:

- **API/service credentials → broker them.** The agent holds a placeholder and a local proxy injects the
  real value outbound, so the agent's process never contains the secret and a prompt-injection exfiltration
  has nothing to steal. Right shape for provider keys, tokens and PATs.
- **Wallet signing keys → never broker them.** They sign locally. A proxy in the signing path is a new place
  to steal them while bounding nothing, because the signature only has to happen once.
- **The trap:** a broker holding every credential is **single-host custody in a new costume**. It needs its
  own restore story, and a failure domain for its unwrap secret that differs from the host's, *before* it
  holds anything real — otherwise the host wipe gets rebuilt under a nicer name.

**The same test rules out the password-manager-shaped tools for keys.** A browser autofill vault stores
logins, cards and addresses, and its whole mechanism is *inject the password into a form on the bound
origin*. A signing key has no origin and no form, so the abstraction does not merely work badly — it
cannot apply. Use that class of tool for **logins** (venue dashboards, RPC and exchange accounts) and
never as the home of a key. When asked "can we use the password tool for the wallet?", the answer is a
**shape mismatch, not a missing feature** — say it that way, or the next session goes looking for the
config flag that would make it work.

Landscape of agent-credential brokers, and how to evaluate one without trusting its README, is in
`references/agent-credential-brokers.md`.

## The copy half: what a host backup does and does not carry

Ciphertext surviving the host is only half the requirement; the other half is that a copy exists to
restore *from*. When the agent's own product offers a backup command, **audit what it puts in the
archive before trusting it** — list the entries rather than reading the feature description:

- **It should carry the ciphertext and NOT the shards.** Verify both directions. A backup that carries the
  shards beside the bundle is a backup that defeats itself: the archive can no longer be stored anywhere
  untrusted, which is the only reason to have one.
- **A host backup is usually not a keystore backup.** It captures whatever sits inside the product's home
  directory, which may include a synced copy of the ciphertext and exclude the working key directory. So it
  is a valid copy path **only while the published copy is current** — and the publish step, not the backup
  step, is what keeps it current.
- **State the split in the report.** "The backup takes the ciphertext and leaves the shards" is the
  finding, and it is a good one. "We have a backup" is not a finding.

### How to verify the copy half — and why a bare negative is worthless

Asserting "the archive does not carry its own passphrase" is a claim until a scan shows it. The scan has
one hard requirement: **it must be able to fail.** List the archive's members and search them for the
secret's path **without ever writing the decrypted stream to disk or printing its contents** — decrypt to
a pipe, list from the pipe:

```
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$PASS_FILE" -in "$BUNDLE" | tar -tJf - > /tmp/members
```

Then report **three** numbers, never one:

1. the match count for the secret (`grep -c '<passphrase-file-basename>' /tmp/members`);
2. a **positive control** — the count for something that MUST be present (the vault tree, the state DB);
3. the archive's total member count.

**A zero is meaningless without (2).** A decrypt that silently produced an empty or truncated stream
reports exactly the same zero as a genuinely clean archive, and the reader cannot tell them apart. The
control is what distinguishes *"absent"* from *"the scan did not run."* The denominator in (3) is what
makes "absent" a bounded claim rather than an open one — *"0 of N members, with M vault entries found"*
is a measurement; *"not present"* is a guess.

This is the same discipline the secret-preflight gate needs below: **one direction only teaches you half
of what is wrong, and the half it hides is the unusable one.**

## A restore path must pin everything it depends on

**A restore command that fails on an unrecorded dependency is the same defect as a backup that was never
drilled** — it looks like a recovery path and is not one.

- **Pin the interpreter.** A tool needing a third-party crypto library dies with an ImportError under the
  host's system interpreter. Name the exact interpreter in the documented restore command **and say why**,
  so the next reader does not "tidy" it back to the default.
- **Publish the instructions with the ciphertext.** After a host wipe there is no memory of the scheme,
  only files. Write a **recovery manifest** into the same off-host place as the bundle: the addresses, the
  bundle filename and hash, **where each shard is supposed to go**, the exact restore command, and a live
  status line reading *"all shards are still on this host"* until they are moved. Generate it in the
  publish step so it cannot drift from the bundle it describes.
- **Leak-check the manifest before shipping it.** Search the published artefacts for the raw bytes of every
  real secret. A manifest carrying a fragment of the thing it was meant to describe is not a manifest.

## Reporting standard

- **Never let "the tool exists" be reported as "the assets are protected".** State which half is done and
  which half is pending, every time.
- **Name the residual gap in the output, not in the reader's inference.** A protection that does not cover
  the most likely failure (host loss, account loss) must say so in its own report.
- **A write-off is a fact to state, not a thread to chase.** If keys are gone, the balance is stranded
  permanently — say "unrecoverable" rather than proposing a recovery that cannot exist.
- **A field's NAME is not its VALUE — read the code that writes it before declaring a breach.** An audit
  flagging a metadata key named `*_shards` sitting beside the ciphertext looks exactly like a
  two-factors-collapsed-into-one violation, and it may be a **human-readable label**. Two cheap decisive
  checks, both faster than the incident a false alarm starts: the source line that produces the field, and
  a byte-level leak check over every published artefact. **Do not state the reason without reading the
  case** — the same failure as explaining behaviour you never ran.

## Taking custody of a key you did not generate

**A keystore that can only GENERATE keys cannot take custody of one that already exists** — and the moment
you need that most is the moment a key surfaces somewhere it should not be and must be re-homed safely.
Provide an explicit **import** path beside `init`, and make it earn its keep:

- **Import from a FILE, never from argv.** A private key on a command line is visible to every process on
  the host via `ps`. Take a `--key-file` and read it there. The same discipline applies to extraction
  paths: a script that prints a key to stdout to "get it out" has published it to the terminal scrollback
  and every log that captures it.
- **Verify key↔address by DERIVATION at import, and REFUSE on mismatch.** If the file states an address
  and the key derives a different one, the file is wrong — stop, do not archive it. This is the check that
  prevents the worst outcome in this whole area: a key stored confidently for the wrong wallet.
- **Mark the bundle as imported, not generated**, with where it came from, so a later reader knows the
  address matches by construction (verified) rather than by assumption.
- **A `restore --dump-dir` drill writes PLAINTEXT to disk** — that is the point of a drill, and it is also
  a fresh exposure you created. **Shred the dump in the same session you make it**, and say that you did.
  A drill that leaves plaintext keys in a temp directory has traded one exposure for another.
- **Round-trip it before you trust it:** import, run the self-check (every two-of-n shard pair rebuilds,
  a single share does not), restore from two shares, and derive the address from the recovered key to
  confirm it matches the original. An import that has never been restored is a hypothesis.

## A keystore is a recovery path only for the address it DECLARES

**Before counting an encrypted bundle as recovery, read its own index and name the address it holds — then
compare that to the address you are trying to recover.** An intact, well-formed keystore can be perfectly
healthy and guard the wrong wallet; nothing about a valid ciphertext, a full shard set and a clean
`selfcheck` says *which* address is inside.

Measured: two tenants had real bundles with 3-of-3 Shamir shards and a keystore index — and the index
declared the **post-wipe generated** addresses (`nonce 0`, empty), not the funded addresses that predated
the keystore. **The recovery machinery worked exactly as designed and protected two empty wallets**, while
the unspendable ones were assumed recoverable because "we have shards on disk".

- **Generate-on-first-use is the defect.** A keystore that mints a key when it holds none for a tenant will
  silently replace a recorded wallet with a valid, empty, well-formed one. Every downstream check passes —
  the address is a real address — so **no alarm exists unless the recorded address is compared against the
  held key.**
- **The guard is a refusal, not a habit:** *a keystore must refuse to generate for a tenant whose recorded
  address exists and whose key it does not hold, naming the missing key.* Minting a replacement is never the
  fallback. `scripts/keystore-mint-guard.py` implements the check (exit 1 = violation, exit 2 = could not
  read, never a pass); run it against the real registry before any key operation, not only after a wipe.
- **Retire on the owner's word, then enforce it.** When the key is provably gone, the owner decides retirement
  and the record states the balances **at retirement** (a dated read is evidence; a deletion destroys it) —
  and every *instruction* file gets a `RETIRED — DO NOT FUND` banner while history files keep their text.
  A funded-looking address that cannot sign is the one shape that keeps attracting money, so the prohibition
  has to be written where an operator reads, not only where an auditor looks.

## Where the old instance's data lives once its CONTAINER is gone

**When a container is deleted, its data does not disappear with it — it lands in an anonymous volume.** So
"no container older than the wipe" is not "no data older than the wipe", and a `docker ps -a` that shows
nothing is the START of the search, not its end. Enumerate volumes before concluding anything:

```bash
for v in $(docker volume ls -q | grep -v traefik); do
  mp=$(docker volume inspect "$v" --format '{{.Mountpoint}}')
  echo "== $v  [$(du -sh "$mp" 2>/dev/null | cut -f1)]"; ls "$mp" 2>/dev/null | head -6
done
```

**Read a profile by its shape, not its size.** A volume listing `SOUL.md config.yaml .env cron/ profiles/`
is an agent home; one listing `.npm/.local/.profile` is a dependency cache wearing 132 MB — and `du` will
show them as similar sizes. **Never open a volume with `docker cp`; mount it `:ro` and copy**, so a mistake
cannot write to a live agent's state:

```bash
docker run --rm -v <vol>:/a:ro -v <incoming>:/dst --entrypoint sh <image> \
  -c 'mkdir -p /dst/vol-a; cp -a /a/. /dst/vol-a/; du -sh /dst/vol-a; ls -a /dst/vol-a | head -20'
```

- **`cp -a` preserves mtimes — read them to prove LIVENESS, and do not skip this check.** A volume whose
  files were written minutes ago belongs to a **running** agent, and `docker ps -a` missing its container
  proves only that the mount moved, not that the agent died. Measured: two "orphan" volumes had 32 files
  modified within the hour and belonged to two live containers nobody had in the fleet roster. **Treating a
  live profile as an archaeological find is how you copy a running agent's live credentials.**
- **Budget the cleanup before you copy.** Docker writes the copy as **root**, so the agent that created it
  often cannot delete it — and what it just copied is every `.env` in that profile. Have the `rm -rf` ready
  for the human in the same message that asks them to run the copy, not after.
- **A live-looking profile that is not in the roster is a finding in its own right** — it is spending money
  and holding credentials with nobody watching. Report it; do not fold it into the key hunt.

## A recovery tool must DISCOVER, never default

**A hard-coded default path in a recovery tool is a defect that only fires during the emergency it was
built for.** When the keystore was split from one bundle into per-tenant bundles, the restore tool's
`--out` default kept pointing at the pre-split directory. `show` and `selfcheck` then died with
`FileNotFoundError` — which a person after a wipe reads as **"the keys are gone"**, when the truth is
**"the default is stale."** The tool survives review because the *explicit* path still works; only the
bare command breaks, and only after the layout has moved.

- **Resolve the target by discovery** (every directory holding the keystore index), and let an explicit
  argument win when given. Make read-only commands multi-target so `show` / `selfcheck` need no arguments.
- **Commands that mutate ONE tenant (init, restore, publish, seal) must refuse on ambiguity** and print
the candidates as literal `--out` lines, rather than guessing which tenant was meant.
- **Re-verify the negatives after the change**, not just the happy path: a single shard must still be
  REFUSED, an unconfirmed delete must still be REFUSED, and an ambiguous init must still be REFUSED. A
  discovery default makes it easy to widen a guard by accident.

**A stubbed or dead input must ABSTAIN, not vote.** A calendar/gate layer that cannot read its source and
still prints a confident "nothing scheduled" is the false-value class: a failed read rendered as a
measurement. Return an explicit unknown, make the permissive branch unreachable through a missing input,
and report the abstention even when the outcome is otherwise confident.

**A signal that only appears attached to another signal is decoration.** If a gate's output is printed
inside a block that another trigger controls, then the one moment it has something to say is the one
moment it stays quiet. Give the transition its own trigger — and then prove the silence still holds on an
unchanged re-run.

## Implementation

The working key-vault implementation — encrypted bundle, 2-of-3 Shamir shard split, the drill commands,
and where the ciphertext is allowed to live — is in `references/reset-proof-key-custody.md`.

Custody MODES (solo / delegated / threshold), the per-book risk-disclosure record, and how to record a
co-holder's consent faithfully — including what a consent record does and does not attest — are in
`references/custody-modes-and-consent.md`.

Evaluating an agent-credential broker (the two mechanisms, current candidates, and the canary test that
must pass before one holds anything real) is in `references/agent-credential-brokers.md`.

**Getting a ONE-OFF on-chain write signed by a key you must NOT take custody of** — the hosted
`window.ethereum` signing page, the identity guard that refuses a wrong connected wallet, the
proxy-vs-implementation trap, and how to verify the write from the chain rather than from the page — is
in `references/signing-without-custody.md`.

## Gate the artifact BEFORE it ships, and match CONTENT not filenames

**A filename-pattern sweep is not a content sweep, and a leak found after the push is a rotation, not a
fix.** Run `scripts/pii_secret_preflight.py <paths> --fail-on-find` (exit 1 = do **not** commit, sync or
ship) as a **preflight** — before the push, the sync, or any "verified" claim — and never as a post-mortem.
It covers four classes: key material (PEM blocks, 64-hex with key language, **a bare 64-hex alone on a
short line**, mnemonics), credential ASSIGNMENTS, known token shapes, and PII.

Why the method matters, measured: a sweep of **68 repos keyed on key-shaped file NAMES** reported "no key
material anywhere" and was false — a live private key to a funded wallet sat in a file called
`celo-rail-key`, which matches **none** of the usual name patterns (`private[-_]?key`, `*.key`, `keystore`,
`*.enc`). **Re-run over file CONTENTS, it was found on the first attempt.** Two consequences:

- **Never filter by filename or extension when hunting secrets** — open every text file and scan its
  bytes. The name was chosen by whoever wrote the file; the secret is in the content.
- **The two classes a pattern table cannot see** are positional, not lexical: `NAME=value` where NAME is
  credential-shaped (`api_key`, `token`, `secret`, `password`, `private_key`) **and** the value is real
  (a `sha256` in a doc is fine, an **assignment** is not) — and **a 64-hex with no hash vocabulary
  anywhere in the file**, because hashes arrive beside `sha256`/`txid`/`gasUsed` and keys arrive alone.
  **Config backups are where these concentrate.**
- **Exclude placeholders or the gate gets ignored** (`${…}`, `<REDACTED>`, `xxx`, `your_`, `CHANGE_ME`,
  `getenv`, `_env$`). A gate that cries wolf costs exactly what a miss costs.
- **State the method with any clean verdict.** *"Filename patterns at HEAD"* is a much narrower claim
  than *"no key material exists"* — and the narrower one would have been true where the broad one was false.

**But never verify a gate on its own fixtures.** Point it at one known-bad file and one known-clean file
and confirm it gives **opposite** answers, or a broken detector and a clean corpus are indistinguishable.

### Tune the gate, or it becomes noise people learn to skip

**A detection rule is not finished when it fires on a true positive. It is finished when it stops
firing on the corpus you believe is clean.** This gate reported **~6,300 findings on a corpus holding
exactly one real key** before tuning, and ~440 after — same true positive, but now triageable. Three
rules, and the measured false-positive classes behind them (BIP-39 words that are common English words;
import blocks that look like 12-word runs; `token` matching `tokenizer`; Luhn over digit runs), are in
`references/secret-preflight-gate.md`, along with the six-fixture regression suite to re-run after ANY
rule change, and **how to triage the hits that remain (context beats pattern: the live tree is not the
archive, and a provider's own example keys are its own).**

- **Validate in BOTH directions** — fixtures that MUST fire, and a corpus you believe is clean. One
direction only teaches you half of what is wrong, and the half it hides is the unusable one.
- **Separate the classes by their failure cost.** Secrets are never acceptable → always fail. **Personal
data in a private vault is expected → make it opt-in (`--pii`).**
- **Precision beats recall in a gate.** A miss is bad; a gate nobody obeys is worse, because it is
indistinguishable from not checking except that it feels covered.

### Deleting a file does not un-share a secret — prove it before reporting remediation

A key removed from a working tree is **still in the repository's history**, and still readable by anyone
who can clone it. **Demonstrate this rather than asserting it:** `git show <commit>:<path>` returns the
secret bytes (measured: 346 bytes, retrievable after the file was deleted from the tree). So a working-tree
delete plus a `.gitignore` rule prevents **future** re-adds and nothing more. State the residual exposure
in the same breath as the fix, and name the only two complete answers: **rewrite history** (a force-push
to a shared repo — never done without the owner saying so explicitly) **or rotate the key**. It is
legitimate to accept the exposure when the repo is private with no forks and the stake is dust; it is not
legitimate to present the delete as the fix.


## Consolidated references

These were separate skills until 2026-10-19. Their triggers duplicated this one, so the bodies moved here rather than being rewritten — **the original text is preserved verbatim**, because a merge that paraphrases a procedure loses the details that made it work.

- **`wallet-key-custody-and-recovery`** — absorbed, full text at `references/wallet-key-custody-and-recovery/wallet-key-custody-and-recovery.md`. Trigger: "wallet key custody and recovery" questions that used to resolve to a separate skill.
- **`agent-capital-custody-and-recovery`** — absorbed, full text at `references/agent-capital-custody-and-recovery/agent-capital-custody-and-recovery.md`. Trigger: "agent capital custody and recovery" questions that used to resolve to a separate skill.
