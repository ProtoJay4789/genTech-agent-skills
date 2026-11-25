# Publishing a repo under a PERSON, not an org

A portfolio repo is published under a **person's** account because the reader evaluates the person: a
personal profile is a body of work, an org page is a company. Credit the company in the README
second paragraph instead, and keep the org's mirror repos separate and private (see §9 of SKILL.md).

**The pre-flight is identical to §9** — scan CONTENT for credential shapes, not filenames — but the
stakes are different: this tree is about to be world-readable under a real name, permanently, and
the author will be asked about every line.

## 1 · Confirm which credential is which, without printing it

Two tokens on one box can belong to two different identities, and picking the wrong one publishes to
the wrong namespace. Test each candidate file with `GET /user` and compare the returned `login`:

```bash
for f in <secrets dir>/github-token <secrets dir>/github-token-<person>; do
  T=$(cat "$f" | tr -d '\n\r ')
  curl -s -H "Authorization: Bearer $T" https://api.github.com/user \
    | python3 -c "import json,sys;print(json.load(sys.stdin).get('login'))"
  sleep 3
done
```

Never generalise from one file to "the token" — a stale copy and a live one look identical from
outside. Print only the login, never the secret.

## 2 · Create with the metadata in the POST — one write, not three

The repo description belongs in the create call, so the operation is a single content-generating
request rather than a create-then-patch pair. Topics are a separate endpoint and can follow after a
spaced pause (or be skipped — they are cosmetic).

```bash
curl -s -X POST https://api.github.com/user/repos \
  -H "Authorization: Bearer $T" -H "Accept: application/vnd.github+json" \
  -H "User-Agent: <Agent>/<version>" \
  -d '{"name":"<repo>","description":"<one sentence, the problem not the stack>",
       "private":false,"has_issues":true,"has_wiki":false,"auto_init":false}'
```

Expect **201**. A `422 name already exists` means the namespace check in §1 was wrong, not that the
name is taken globally.

## 3 · Push without leaving the token on disk

`git push` needs credentials, and the two ways to give them differ in what they leave behind.

- **`-c http.extraheader="Authorization: Bearer …"` may not authenticate at all** (the push falls
  through to an interactive prompt and fails with `could not read Username`). Do not debug it — move on.
- **The reliable path is the token in the remote URL, then scrub and verify:**

```bash
T=$(cat <secrets>/github-token-<person> | tr -d '\n\r ')
git remote set-url origin "https://x-access-token:${T}@github.com/<owner>/<repo>.git"
GIT_TERMINAL_PROMPT=0 git push -u origin main
git remote set-url origin "https://github.com/<owner>/<repo>.git"
grep -c "x-access-token" .git/config || echo "0 token refs remain"   # must be 0
```

**The scrub is not optional and the check is the evidence** — a token left in `.git/config` persists
in every later clone of that working copy and in any backup of it.

If the push fails with `src refspec main does not match any`, the local branch is named `master`:
`git branch -M main` then push. Do not create an empty commit to force it.

## 4 · Verify as a STRANGER, not as the owner

An authenticated `200` is the owner's view; the owner always sees their own repo, including one that
is hidden or newly created. Measure what an outsider gets, with no credentials:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://github.com/<owner>/<repo>
curl -s -o /dev/null -w "%{http_code}\n" https://raw.githubusercontent.com/<owner>/<repo>/main/README.md
curl -s https://api.github.com/repos/<owner>/<repo> | python3 -c \
  "import json,sys;d=json.load(sys.stdin);print(d['private'], d['default_branch'])"
```

Then read the **tree**, which is the only statement about what is actually in the repo:

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/git/trees/main?recursive=1"
```

- **`size: 0 KB` on the repo object is NOT a failure** — GitHub's byte counter is asynchronous and
  lags a fresh push. The tree read is the truth about contents; never report a repo as empty off the
  size field.
- Assert the properties that matter from the blob list: the expected count, the diagram present, no
  credential file, and anything you believed was excluded actually absent.

## 5 · Content scan before the first push — and read every hit

```bash
grep -rInE "sk_|sd_[A-Za-z0-9]|ghp_|github_pat_|AKIA[0-9A-Z]{8,}|-----BEGIN|Bearer [A-Za-z0-9]" . \
  --exclude-dir=.git --exclude-dir=.terraform
grep -rInE "[0-9]{1,3}(\.[0-9]{1,3}){3}|telegram:-?[0-9]+|/opt/|srv[0-9]+" . --exclude-dir=.git
grep -rInE "[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}|0x[a-fA-F0-9]{40}" . --exclude-dir=.git
```

The third battery is the one a code-shaped scan misses: **an email, a home directory path or a wallet
address is not a credential and still identifies the author's infrastructure**. Read every hit in
context rather than deleting on the match — provider hashes in a Terraform lock file, and a
`Bearer` mentioned inside documentation about headers, are both expected.

**A repo that publishes a person's operating practice also publishes their hostnames and chat ids**
unless this runs. That is the disclosure nobody thinks of, because nothing in it looks like a secret.

## 6 · What belongs in the published tree

- **The author's name and the business problem in the first two lines** — a repo with no author line
  is a code dump, and this tree is an application.
- **A licence chosen, not implied.** Absent a licence, no reuse is granted and the reader cannot tell
  whether that was a decision. MIT for a small tool; the copyright line names a person or a company
  depending on who owns the work — decide it deliberately, it is a legal statement.
- **Every unexercised claim labelled in the artifact** ("validate passes; not applied — no cloud
  credentials on this seat").
- **A "what I would do next" section naming the real gaps**, including defects found in the artifact
  itself. The first question in an interview is what is wrong with it.
- **Excluded on purpose:** anything that is a *record of decisions about money* — positions, sizes,
  P&L. A working system is verifiable by a stranger; a trading record invites the reader to grade
  judgement instead of engineering. Publish the mechanism, keep the book private, and do not smuggle
  one in as a "workload" example.
