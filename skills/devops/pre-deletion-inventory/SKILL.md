---
name: pre-deletion-inventory
description: "Use before deleting or purging any remote artifact."
version: 1.0.1
author: gentech
tags: [deletion, inventory, recovery, git, verification, data-loss]
metadata:
  hermes:
    tags: [deletion, inventory, recovery, verification]
    related_skills: [destructive-write-guards, github-account-compliance, backup-and-restore-drills]
---

# Pre-Deletion Inventory

For the decision *before* the delete: what is uniquely inside this thing, and where else does a copy live.
A guard on the operation stops accidents; this skill answers the different question — whether the content
exists anywhere else at all. Applies to repositories, forks, branches, and backup/snapshot stores.

**Deleting is the only operation here with no local undo**, so the burden of proof sits on the delete, not
on keeping the artifact.

## When to Use

- **Before deleting or purging a remote artifact** — a repository, a fork, a branch, a backup or snapshot
  store — and especially when a policy or compliance reason makes the delete feel routine.
- When a deletion list was built from **metadata** (sizes, flags, labels) rather than from contents.
- When the decision to delete rests on a comparison that returned **"identical" or "nothing unique"**.
- Before retiring a fork you may have contributed from, and before removing any store that has ever been used
  as a backup target.

## The order: PRESERVE → INVENTORY → DELETE. Never delete → discover.

1. **Preserve at full fidelity** before touching the remote: clone it, archive it, checksum it.
2. **Inventory** its contents against the live counterpart, and classify every difference as unique or as a
   moved/renamed duplicate.
3. **Act on the classified list** — which is routinely much smaller than the raw diff.

### A policy label explains why something must not be a TARGET, not that its contents are worthless

The classification and the contents are independent facts, and deletion work is where they diverge. A store
that violates "don't use this as a backup target" can *simultaneously* be the last surviving copy of a system
that exists nowhere else — in which case deleting it as remediation destroys the recovery source and reports
as cleanup.

**The tell that the inventory was skipped: you can say why the artifact violates policy and not what is
inside it.** When the only reason to delete is a rule and the content is unexamined, the order was wrong.

## A fork: compare EVERY ref, not the default branch

A default-branch comparison answers about the default branch. It returns `ahead_by: 0` for a clone that is
merely *behind* upstream, and identically for one carrying a contribution branch nobody merged — while the
action you are licensing covers all refs.

```bash
git ls-remote --heads https://github.com/<fork>.git          # NAMES first: the authorship tell
git ls-remote https://github.com/<fork>.git   | awk '{print $1}' | sort -u > fork.sha
git ls-remote https://github.com/<parent>.git | awk '{print $1}' | sort -u > parent.sha
comm -23 fork.sha parent.sha                                 # object IDs unique to the fork
```

Two git calls, zero API quota, and exhaustive in the direction an API branch listing is not.

- **A fork inherits upstream's branch list at fork time**, so a branch name referencing your own project,
  product, or feature is fork-only by construction. Names settle authorship faster than commit inspection.
- A SHA unique to the fork is a **candidate**, not proof. Separate the two causes: upstream rebased or
  force-pushed away an inherited commit (not ours) versus a branch authored after the fork (ours).
- **Never delete a fork with an open contribution against upstream.** Check the PRs, not only the refs —
  deleting a fork closes its side of a live pull request.

## Metadata is not contents

- An API `size` is the **packed git-object size including history**, not the working tree. A repo whose HEAD
  holds a dozen README files can weigh hundreds of MB: a file removed from HEAD is still in the repository
  and still counts. **Never judge a repository by its file list**, and never report "we cleaned it" from a
  listing.
- `fork: true`, a name, a description, a violation label — each describes *shape and policy*. None can go
  red on the thing the delete destroys.
- **Budget one contents-level probe for every irreversible action**: a tree diff, a checksum, a record
  count. Say which one you ran.

## A comparison that has never said "DIFFERENT" cannot say "the same"

An empty result is evidence about the comparator until proven otherwise. Two ways the zero is manufactured:

- **Unnormalised operands.** A tree nested one directory deeper than its counterpart (`store/…` against the
  store root) shares no path with it, so the diff reports **100% unique for identical content**. Strip the
  shared prefix before comparing.
- **A filter that exempts the whole class.** A classifier tuned until nothing matches reports clean while
  looking away. Say what was filtered and on which rule.

**Prove the comparator discriminates**: feed it a known-present item, watch it report the difference, then
remove it. A check whose output does not change when the input does is a constant with a name.

Also **state the denominator**: "no unique content" renders identically whether you read 43,000 files or
zero. Print how many you examined.

## Export before delete, with provenance

```bash
git clone --filter=blob:none --single-branch --branch <BR> \
    https://github.com/<owner>/<repo>.git /tmp/<repo>-<BR>
git -C /tmp/<repo>-<BR> log --format='%H|%ae|%cI|%s' > commits.txt
git -C /tmp/<repo>-<BR> archive --format=tar.gz -o <name>.tar.gz HEAD
sha256sum <name>.tar.gz
```

`--filter=blob:none` keeps the clone small; `git archive` fetches exactly the blobs the tip needs. Record
**branch name, tip SHA, and commit log alongside the archive** — an archive with no provenance is not a
recovered contribution, and a holding of an unnamed snapshot is a copy of the holding of a copy.

## Delete paced, and READ IT BACK

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE \
  -H "Authorization: token $TOKEN" https://api.github.com/repos/<owner>/<repo>
# then re-read the SAME path; expect 404
```

- A `204` is the receipt for the **request**; the `404` on the follow-up read is the receipt for the
  **deletion**. Never report a delete from the request's status alone.
- **Space them.** A burst of deletions is its own traffic shape and is trivially avoidable; a paced loop with
  a sleep and a readback is the whole cost.
- Report the reclaimed total from **measured** sizes, not from a repository count.
- **Check the platform's restore window** rather than asserting irreversibility, and say which it is.

## A `404` is about the CALLER until a second credential agrees

Scope belongs to the credential, not the resource. A private or org-owned repository returns `404` for a
token with no membership and `200` for a member token, on the same path, in the same minute, with no error
explaining the difference.

- Re-read with the second credential and **record which one answered**. Never record "gone" or "absent"
  from a single caller's `404`.
- When two disagree, check **membership and permissions** (`/user/orgs`, the repo's `permissions`,
  `admin: true`) rather than the path.
- Probing the **wrong spelling** of an owner returns the same clean, meaningless `404`. Probe the exact
  identifier, and keep a control request in the same batch so a failure of the probe is distinguishable from
  a failure of the resource.

## The askpass trap: works from one launcher, fails from another

```bash
export GIT_ASKPASS=<helper> GIT_TERMINAL_PROMPT=0 GIT_TOKFILE=<tokenfile>
```

A launcher that constructs the child environment explicitly (an inline python block, a CI step) passes every
variable itself — so the helper works there and fails in a plain shell where the variable was assigned but
never **exported**. Before suspecting the helper, confirm every variable it reads is in the child's
environment, and give the helper a loud non-zero failure (`askpass: GIT_TOKFILE unset or missing`) instead of
an empty `cat ''`, which reports as "unable to read askpass response" and hides the cause. Reading the
credential through a helper rather than the clone URL also keeps it out of the process list.

## Credentials: ROTATE first, purge second

For a committed credential the order is **rotate → purge history → verify**. A history purge of a secret that
is still live removes the evidence and leaves the exposure. This does not contradict the preserve rule above:
for a credential the *existence* of the copy is the problem, so there is nothing to preserve — but you still
name what you are about to destroy and why.

## References

- `references/repo-deletion-recipe.md` — copy-paste ladder for retiring a repo or fork: metadata pass, ref
  diff, contents diff with normalised paths, export, paced delete with readback, and a reclaimed-total ledger.
