# Credential-Safe Probes

How to probe a code host or API **without** putting a secret on a command line, and how to test a
credential without ever printing it. Command lines land in shell history, `ps` output, and any
process-args logger — so a token in argv is a token to rotate.

## Source the token from a file, never inline

```bash
T="$PROFILE/secrets/<host>-token"
ls -l "$T"                                     # metadata only: perms, size, mtime, owner
printf 'prefix: %s…\n' "$(cut -c1-4 "$T")"      # a 4-char prefix identifies it without exposing it
wc -c < "$T"                                   # length, so a truncated/empty file is visible
```

Never `cat` the file into output. Size + prefix + mtime answer "is this the credential I think it is"
without exposing the value.

## curl — header from a config file via process substitution

```bash
umask 077
curl -s \
  -K <(printf 'header = "Authorization: Bearer %s"\n' "$(cat "$T")") \
  -K <(printf 'header = "User-Agent: <agent-name>"\n') \
  -D - -o /dev/null \
  https://api.github.com/user
```

`-D -` dumps the response headers, which is how you read `x-ratelimit-limit` / `-remaining` and
`x-oauth-scopes` — the scope list tells you what the credential can do (e.g. whether it carries a
destructive scope) without you having to test destructively.

## git over HTTPS — Basic with `x-access-token`, NOT Bearer

```bash
umask 077
B64=$(printf 'x-access-token:%s' "$(cat "$T")" | base64 -w0)
printf '[http "https://github.com/"]\n\textraHeader = "Authorization: Basic %s"\n' "$B64" > /tmp/gcfg
chmod 600 /tmp/gcfg
GIT_CONFIG_GLOBAL=/tmp/gcfg git clone --depth 1 https://github.com/<owner>/<repo>.git <dir>
rm -f /tmp/gcfg
```

**The trap:** git-over-HTTPS rejects `Authorization: Bearer` and reports it as
`Repository not found`. A wrong header format therefore presents as a *missing repository* — do not
conclude the repo is absent until the header form is known-good and the namespace is confirmed
(read `clone_url` out of the repo list rather than hand-building the URL).

## Testing a credential without printing it

```bash
curl -s -K <(printf 'header = "Authorization: Bearer %s"\n' "$(cat "$T")") \
     https://api.github.com/user -o /tmp/u.json -w 'http=%{http_code}\n'
python3 - <<'EOF'
import json
d = json.load(open('/tmp/u.json'))
print('login:', d.get('login'), '| type:', d.get('type')) if 'login' in d else print('resp:', d.get('message'))
EOF
```

Report **which file path** you tested alongside the result. A dead credential and a hidden account
look similar from outside, and testing the wrong copy of a credential manufactures a problem that
does not exist.

## Run the control in the same batch

```bash
# control: a known-good stranger's tiny public repo, anonymous
timeout 60 git clone --depth 1 -q https://github.com/octocat/Hello-World.git /tmp/ctrl \
  && echo "anon clone of a STRANGER'S repo: WORKS" || echo "anon clone: FAILED (environment)"
```

Control works + our repo fails → the failure is scoped to **our content** (namespace, path, or
account) — not our network, TLS, or git. Control fails too → the problem is the **environment**.
Two different findings, two different responses; the control is what makes the split visible.
