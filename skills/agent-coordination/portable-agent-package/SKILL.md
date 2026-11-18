---
name: portable-agent-package
description: Use when handing an agent to another person or host.
---

# Portable agent package

Give someone else a working agent — another person, another machine, another provider — without
handing over our stack. The deliverable is one folder they can install: **soul, memory, skills**, and
nothing that only makes sense on this host.

**Use this when the agent will live somewhere you do not administer.** When it will live on the SAME
host as a worker seat that needs our config, bot token and cron jobs, that is
`hermes-profile-clone-worker` instead — the two look similar and share almost nothing.

---

## The boundary — decide this before writing a single file

| in the package | out of the package |
|---|---|
| `SOUL.md` — the identity | `config.yaml`, `.env` — our rail, our paths, our providers |
| `memories/MEMORY.md`, `memories/USER.md` | any credential, token, key, or client secret |
| `skills/` — a curated set | `cron/jobs.json` — schedules that fire where nobody is watching |
| `manifest.json` — provenance | `state.db`, session logs |
| `README.md` — how to install | the vault — it holds credentials and private handoffs |

**A package that carries config carries our rail, our absolute paths and our peer names — none of
which are true where it lands.** Ship identity, not environment.

---

## Procedure

### 1 · Inventory the source before writing anything

Measure what actually exists: the profile note, any skills backups, memory files, prior packages.
Record sizes. **Do not invent a persona from imagination when the material is on disk** — a
hand-written soul that contradicts the existing profile note is worse than no package.

**⚠️ But the profile note is a CLAIM, not evidence.** It was written by someone, at some time, and
nobody has re-checked it since. Everything in the package inherits whatever it asserts — so verify the
one or two facts the whole document rests on (who the recipient is, what relationship they have to the
people already in the system) **before** building, not after. **A note that has been wrong for months
reads exactly like a note that is right**, because both are prose.

**The tell that a fact is load-bearing:** if it were false, the soul would address the recipient
wrongly, or the memories would describe a different person's life. Those are the facts to confirm,
and the cheapest confirmation is one question to the owner — not a search, and never an inference
from a shared surname, a shared room, or a shared tone.

### 1b · When a load-bearing fact turns out to be wrong, sweep — do not just patch the soul

A correction applied only to `SOUL.md` leaves the same falsehood in every file derived from it.
**Grep the packaged folder for the stale phrase and fix each hit**, then re-check:

```bash
grep -rin "<the stale phrase>" <package>/
```

**Expect hits in the GENERATED files, not just the written ones** — `manifest.json` notes, `README`
prose, and memory files all repeat what the soul says, and those are the copies a recipient reads
first. A grep that returns a hit whose surrounding sentence is unrelated is a false positive; read the
line rather than rewriting on the match.

**Then repair upstream, not only downstream.** The profile note that carried the error will keep
re-infecting every future package until it is corrected at the source — and the correction belongs
there with the owner's words, plus a line saying the old text was wrong, so the next reader does not
re-derive it.

### 2 · Write `SOUL.md` for the receiving agent, not about them

Cover, in this order: who the agent is and who it serves; how it talks (length-matching, no filler);
the lines that do not move; how it works (check before building, verify what you made); the voice.

**Carry over every hard line the recipient's work depends on** — likeness prohibitions, never-post-
without-approval, key handling. A package that drops them hands someone an agent that will breach
them on day one.

**⚠️ Stay neutral on anything you cannot verify.** If a source note says two people are the same
person and the request implies two people, write the soul about *the person served* without asserting
the relationship, and flag the ambiguity in the README. A shipped file is not the place to resolve a
question the owner has not.

### 3 · Skills — check PROVENANCE before you copy

**A skill is not the recipient's because it was used during their work.** Skills are authored *inside
whoever's infrastructure the work happened in*, so a backup of "their" skills is usually a snapshot of
your own stack mid-project: your seat names, your absolute paths, your wallet addresses, your hostnames,
and sometimes a shared registry of other people's accounts.

**Test every candidate skill for your own identity before it goes in:**

```python
OURS = {"seats": r"(?i)\b(<your seats|org>)\b",
        "paths": r"/opt/<stack>/|<your private dir>",
        "wallets": r"0x[0-9a-fA-F]{40}",
        "hosts": r"(?i)<your domain|hostname|github login>"}
# any hit  → this skill is YOURS. Do not copy it, and do not placeholder it.
```

**Rewrite, don't strip.** A skill full of `<omitted>` reads as complete and breaks the first time it is
followed — it points the new owner at paths and hosts that do not exist on their machine. **The
correction is a smaller, self-contained skill covering the same capability with no reference to anyone's
infrastructure:** "how to write lyrics", "how Seedance works", "how to keep a brain in sync". Shorter
than the original is the expected outcome, and it is the right one.

**Every `SKILL.md` needs `name:` and `description:` in frontmatter**, or the agent installs it and can
never route to it. Verify before packaging:

```python
fm = t.startswith("---")
name = re.search(r"(?m)^name:\s*\S", t[:900])
desc = re.search(r"(?m)^description:\s*\S", t[:1600])
```

**Curate, do not dump.** Add only skills that fit the recipient's work: the ones they actually need,
plus a small number written fresh to close an obvious gap. A package of three hundred skills is a
library, not an agent.

### 4 · `manifest.json` — provenance and hashes

Record package name/version, build time, per-file `sha256_16` and byte size, and the source path for
each group of files. **A later audit must be able to answer "what was in the box and where did it come
from" without the builder.** Include explicit `contains_credentials: false` and any open questions.

### 5 · `README.md` — three install paths

1. **Fresh profile** — `hermes profile create <name>`, then copy `SOUL.md`, `memories/*.md`,
   `skills/*` into it.
2. **Existing install** — same copy, **with an explicit overwrite warning**: if that install already
   has a soul or memories, merge instead of replacing.
3. **Read by hand** — every file is plain markdown; soul → system prompt, memories → memory store,
   skills → skill library.

**State what is deliberately absent** (credentials, vault, crons, peers) so the recipient does not
go looking for what was left out on purpose.

**Put any privacy note here, not in the soul.** Personal details that make creative work faithful
become a liability the moment the package leaves your control — say which section to strip.

### 6 · Verify — four checks, all cheap, all mandatory

```bash
# a) frontmatter validity across every skill   → expect all valid
# b) credential scan                           → expect 0 hits
#    sk-…, ghp_…, xoxb-, BEGIN … PRIVATE KEY, api_key/token/secret = <20+ chars>
# c) OWNERSHIP scan                            → expect 0 hits
#    your seats, org, host paths, wallets, hostnames, logins, other people's ids
# d) REAL INSTALL TEST                         → expect every skill enabled
```

**⚠️ (b) and (c) are different questions and (c) is the one that gets forgotten.** A credential scan
asks *"did a secret slip in?"*. An ownership scan asks *"does this belong to someone else?"* — and a
package can pass (b) with flying colours while carrying your entire infrastructure in prose.

**(c) is the one that matters and the one that gets skipped.** Stage the package into a throwaway
home and let the product list what it loaded:

```bash
export T=/tmp/pkg-install-test && rm -rf "$T" && mkdir -p "$T/skills" "$T/memories"
cp SOUL.md "$T/"; cp memories/*.md "$T/memories/"; cp -r skills/* "$T/skills/"
HERMES_HOME="$T" hermes skills list
# expect: "N local — N enabled, 0 disabled"
rm -rf "$T"
```

**The layout under test is the layout that ships**: identity file at the home root, `memories/` and
`skills/` as siblings. Validate it in the same shape it will be installed in.

### 7 · Tar it

Bundle the folder (not the parent) so the archive unpacks as one named directory, and report the
entry count and byte size. **A tar that unpacks into the recipient's CWD as loose files is a mess they
will not clean up.**

### 8 · Deliver — and prove the recipient can actually open it

**A tar file is only a delivery if the recipient can receive it.** When there is no shared filesystem,
a private repo is the fastest route — but **"private" is not the same as "they can see it"**, and a
private repo on a free plan is visible to the owner only.

**Read `references/delivery-via-private-repo.md` before promising a repo handoff.** It carries the
order that matters: measure token scopes first; prove privacy with an **anonymous** 404 before the
first upload; read the git tree back rather than trusting the PUT responses; purge `.bak`/`__pycache__`
artifacts before uploading; and ask for the recipient's username in the same message that reports the
repo is ready.

**Phrase the close honestly.** "Repo created, private, N files" is true and useless if the recipient
needs a collaborator invite. Say which of the two is done.

#### Opening the repo is a PUBLISH, not a delivery step

When the recipient cannot see a private repo, the tempting shortcut is "make it public for a few
minutes, they'll copy it, we delete it tonight." **That is a publication to the whole internet, and the
window is not reversible by deleting afterwards** — repos are crawled within minutes and caches and
forks do not follow a visibility flip back.

**So the order is fixed:**

```
1  ownership scan  (c)          → 0 hits required
2  credential scan (b)          → 0 hits required
3  notify a human to look       → only after 1 and 2 both pass
4  flip public  →  recipient reads
5  flip private / delete
```

**⚠️ Never flip visibility before step 1.** A package can pass the credential scan and still be full of
the sender's material — and once public, "we removed it" is a claim about a branch head, not about what
was already copied. **If the recipient genuinely cannot reach a private repo, ask for their handle, or
send the tarball — both are cheaper than a public window.**

**And when a human says "just make it public", the ownership scan is the thing you run first, in that
breath, before the PATCH.** A term-scrub is not a content audit, and the strain of "this is only for
<recipient>" is exactly the pressure that skips it.

### When the handoff is "just tell them to check out the repo", the README IS the product

A public repo is handed over in one sentence, and that sentence makes the README's **first command** the
first thing the recipient runs — before they have seen one file of the actual work. **A documented install
step the tool rejects is worse than no step at all**: it is line one, it is unambiguous, and it makes the
whole kit read as abandoned.

**Walk the path as a STRANGER before you send the message** — no token, no logged-in browser, because the
recipient has neither:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com/repos/<org>/<repo>          # 200, not 404
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/README.md | head -40            # read what they read
<the first documented command> --help   # does the tool even HAVE that subcommand?
curl -s -o /dev/null -w '%{http_code}\n' https://api.github.com/repos/<owner>/<repo-the-README-names>
```

- **A `404` anonymously means the recipient sees nothing** — the same failure as a private repo, except
  nobody was told. "Public" is a setting; "reachable" is a measurement, and only the second one matters.
- **Resolve the repo the README names, not the one you assume it means.** Two copies of one kit (an org
  repo plus an older personal fork) is the normal state after a rename, and a README still naming the fork
  sends every new user to the copy nobody updates. Whichever copy is maintained, **the doc must name that
  one**, and the other should redirect or be archived — otherwise the next reader picks by star count.
- **Check the example paths in the doc exist at `HEAD`.** A README showing a directory the tree has since
  moved out of teaches the reader a path that is not there, and they will conclude the kit is stale rather
  than misread.
- **"Is it ready?" takes three measured facts, not a judgement:** reachable with no credentials, first
  documented command runs, doc names the maintained copy. Anything short of three is *nearly* — and
  "nearly ready" told to a person who is waiting costs them an afternoon and us the first impression.
- **A public repo carries the same scans as a tarball.** Publishing is publishing: run the credential and
  ownership scans (6b/6c) against the tree *before* it is public. The audience is now everyone, and git
  history is permanent in a way a visibility flip is not.

---

## Pitfalls

- **A skill is the sender's, not the recipient's, because it was authored during the recipient's work.**
  Work done *inside* your stack leaves your hosts, paths, wallets and seat names in every file. Test for
  your own identifiers before copying; rewrite rather than placeholder, because a redacted skill breaks
  the first time it is followed.
- **A term-scrub is not a content audit.** Removing the words you thought of leaves everything you did
  not. The gate before any sharing is *"does every file belong to the person it is for?"*, not *"does it
  contain the words I searched for?"*.
- **A package that was never load-tested is a folder, not a deliverable.** The receipt is
  `hermes skills list` reporting every skill enabled — not the file count and not the tarball size.
- **Overwriting an existing install's soul or memories destroys a working agent's behaviour.** Merge;
  do not replace. The README must say so in the path that does the copying.
- **Never ship the brain.** Vault, credentials and handoffs do not travel, no matter how convenient
  the copy would be.
- **No crons and no peers.** A personal agent starting with an empty schedule is correct — anything
  that fires while nobody is watching is a liability you cannot debug from another machine.
- **Personal details are the one section to offer to strip.** Say which, and why, so the recipient can
  decide rather than discovering it later.
- **Don't resolve an identity ambiguity by guessing.** Neutral prose plus a flagged question is the
  only honest packaging of an unanswered question.
- **A backup file beside a skill is a stale copy of that skill.** `.bak`, `.orig`, `__pycache__` and
  editor droppings ride along into every upload and give the recipient two versions of the same file
  with no way to tell which is current. Filter the file list before enumerating, not after.
- **"Private" is a visibility setting, not an invitation.** A private repo on a free plan reaches one
  account. Report the repo and the collaborator step as two separate facts.

---

## Verification checklist

- [ ] Every skill has a valid `name` + `description` frontmatter
- [ ] No skill references the SENDER's seats, paths, wallets, hosts or accounts
- [ ] Credential scan returns zero hits
- [ ] Ownership scan returns zero hits — **run BEFORE any visibility flip, not after**
- [ ] Install test shows every skill enabled, zero disabled
- [ ] Manifest records provenance and hashes
- [ ] README states the three install paths and the three absences
- [ ] Tar unpacks as a single named directory
- [ ] If delivered via repo: anonymous 404 proves privacy, and the recipient's access step is stated
      separately from "the repo exists"
- [ ] Repo handoff: README fetched anonymously, its FIRST documented command actually runs, and it names
      the maintained copy rather than an older fork
