# Protocol-compatibility verification — commands

Deciding whether an external rail speaks OUR protocol (x402, MPP, or any challenge scheme) before anyone
builds on the assumption. Every command here is read-only; none of it installs or executes the package.

## 1. Find the package, then read its metadata in one call

```bash
# is there a package at all? Search the registry, not a search engine.
curl -s "https://registry.npmjs.org/-/v1/search?text=<name>&size=10" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);[print(o['package']['name'],o['package'].get('version'),o['package'].get('description')) for o in d.get('objects',[])]"

# the packument: README + keywords + dependencies + publish dates
curl -s "https://registry.npmjs.org/@scope/<pkg>" -o /tmp/pkg.json
python3 - <<'PY'
import json
d = json.load(open('/tmp/pkg.json'))
latest = d['dist-tags']['latest']
v = d['versions'][latest]
print('name/version:', d['name'], latest, '| published:', d.get('time', {}).get(latest))
print('keywords:', v.get('keywords'))
print('deps:', list((v.get('dependencies') or {}).keys()))
print('homepage:', v.get('homepage'))
print('readme chars:', len(d.get('readme') or ''))
PY
```

**Why each field:**

| field | what it answers |
|---|---|
| `time[latest]` | **how old the analysis may be** — a protocol can be retired between versions |
| `keywords` | what the author thinks it is; a chain or scheme name here is a positive signal |
| `dependencies` | whether a protocol client is even present |
| `homepage` | the docs host worth fetching next |
| `readme` | the only text the author controls that is not marketing-tuned per-channel |

## 2. Count our protocol in the README — then read every hit in context

```bash
python3 - <<'PY'
import json, re
d = json.load(open('/tmp/pkg.json'))
r = d.get('readme') or ''
for term in ('x402', '402', '<their-protocol>', '<their-coin>', 'wallet', 'card'):
    print(f"{term:14s} {r.lower().count(term.lower())}")
for m in re.finditer('402', r):                     # read hits with surrounding context
    print('---', ' '.join(r[max(0, m.start()-300):m.end()+300].split()))
PY
```

**A count of zero is the verdict**; a count above zero is only a lead — read the surrounding sentence, because a
protocol can appear solely in the sentence that says it was dropped.

## 3. Fetch the vendor's docs and strip them to text

Docs pages are JS-rendered; strip tags before grepping or every term looks absent.

```bash
curl -s "https://<docs-host>/<page>" -o /tmp/doc.html
python3 - <<'PY'
import re, html
t = re.sub(r'<script.*?</script>|<style.*?</style>', '', open('/tmp/doc.html', encoding='utf-8', errors='ignore').read(), flags=re.S)
t = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t)).split())
print('chars:', len(t))
for m in re.finditer(r'(x402|refus|not offered|no_[a-z_]+_charge|retired)', t, re.I):
    print('---', t[max(0, m.start()-260):m.end()+320])
PY
```

**The valuable artifact is the refusal table** — a list of inputs the vendor will *not* accept. One row naming our
protocol as refused beats any amount of feature prose. Look for refusal language before feature language.

## 4. The four-axis verdict

Fill this in and quote the evidence per row; a verdict is only as good as its weakest axis:

| axis | ours | theirs | source |
|---|---|---|---|
| protocol / challenge scheme | | | readme + docs |
| chain | | | docs settlement table |
| asset | | | docs token list |
| version / date | | | `time[latest]` |

**Any single mismatch is sufficient to say no** — and it is worth naming which axis failed first, because a team
that hears "wrong chain" may believe a bridge fixes it, while "wrong protocol" ends the conversation.

## 5. Legal pages live on another host

```bash
for u in https://<host>/legal/terms https://<host>/legal/privacy; do
  printf '%-44s ' "$u"; curl -s -o /tmp/l.html -w '%{http_code} %{size_download}B\n' --max-time 25 "$u"
done
```

A 200 with tens of kilobytes is a real agreement — read the operator entity, the age gate, the sanctions
representations and the arbitration clause out of it rather than concluding "no terms" from a product page that
merely fails to link them.

## What NOT to conclude

- **"It returns 402, so it speaks our protocol"** — the status code is shared by every challenge scheme.
- **"The landing page says coming soon, so the docs are stale"** — the product and the announcement often
describe two different rails of the same launch.
- **"An analyst blog says convergence"** — blogs describe builds; registries describe what ships today.
