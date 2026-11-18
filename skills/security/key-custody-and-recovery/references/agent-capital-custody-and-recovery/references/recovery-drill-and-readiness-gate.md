# Recovery Drill & Readiness Gate

Depth behind the standing custody rules in SKILL.md.

## 1. Decompose a loss into failure axes, not one story

A total loss is almost never one failure. Check four axes separately, because each needs a different
fix:

1. **Custody concentration** — did every key live in one failure domain (one host, one directory, one
   account)?
2. **Factor co-location** — did the ciphertext and its passphrase share a domain? Directory modes
   protect against other local users and against nothing in host loss.
3. **Backup restoration** — was the offsite copy independently reachable, or did it depend on the same
   identity that broke?
4. **Inventory survival** — is there a record of which credentials existed? This axis is the one that
   usually still works, and it is what the rebuild is built from.

## 2. Recovery ladder by blast radius

| Failure | What breaks | Recovery |
|---|---|---|
| Host loss / wipe | session keys + single-host copies | re-issue session key from a held signer + offsite shard |
| Agent key stolen | attacker holds the *session* key only | bounded by caps; revoke = rotate that session key from the cold signer |
| One human principal unavailable | nothing transactable | m-of-n still signs; no funds frozen |
| Brain / notes lost | documentation only | on-chain state is the truth for positions; restore notes from the second offsite copy |
| Code-host account lost | nothing that matters | keys were never in a repo; the brain has a second target |

Every row after the first is survivable **only because of threshold authority**. Without it, key theft,
principal loss and host loss all collapse into the same total-loss row.

## 3. Readiness gate — assert values, treat silence as failure

A sentinel that is silent when healthy proves delivery by the **target**, not by an observed message.
So every row prints PASS/FAIL with the observed value, and a row that did not run counts as a failure:

1. Newest offsite key-bundle age ≤ 36h
2. Last restore drill ≤ 30 days ago **and** recorded as passed
3. Every wallet in the census is either threshold-authority with the agent as a non-sole signer, or
   unfunded
4. Every `.key.enc` has its passphrase in a **different failure domain** (assert: no sibling
   `.passphrase`)
5. The treasury session key has an expiry set, ≤ 30 days out

Run it on a schedule and record the result in the durable brain; an unrecorded pass is
indistinguishable from a check that never ran.

## 4. Monthly drill recipe (mandatory)

Decrypt the newest offsite bundle in a scratch directory → derive every address → compare against the
inventory → sign one no-op message. Never rehearse against live key material.

What the drill is actually testing:
- that the bundle on the offsite target is complete and decryptable;
- that the passphrase a human holds still opens it;
- that the derived addresses match the custody map (catches a bundle that silently contains an older
  generation of keys);
- that signing works end-to-end from cold material, not merely that the file exists.

A backup that has never been restored is a hypothesis, not a backup.
