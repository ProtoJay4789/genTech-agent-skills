# Rail switch procedure — moving a live fleet from one model provider to another

Use when the user says *"we're on <new provider> now, switch everything over."* A config edit is the
smallest part of this. The failure mode is a fleet that **looks** switched and still spends on the old rail.

---

## 0 · Pre-flight — prove the new rail before touching a single config

A `/models` list answers 200 with **no key at all**, and a key that lists fine can still 404 on every model
you actually use. Probe **one real completion per model you intend to run**, and record the status:

```python
body = json.dumps({"model": m, "messages": [{"role": "user", "content": "2+2"}],
                   "max_tokens": 8}).encode()
req = urllib.request.Request(base + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "gentech-rail/1.0"}, method="POST")
```

Probe the default **and** the auditor tier — an auditor that is not offered on the new rail turns every
Sr audit into a silent same-model self-check. Expect some models to be **not offered**; that is a finding,
not a failure, and the resolver should print it as one.

Also confirm the new provider exposes a **usage meter** and what shape it is (percent windows vs USD
buckets). If it exposes none, say so out loud — do not infer spend from our own call logs.

---

## 1 · Snapshot, then switch each seat through the command

```bash
cp /opt/data/profiles/<seat>/config.yaml /opt/data/profiles/<seat>/config.yaml.bak-railswitch
/opt/hermes/bin/hermes -p <seat> config set model.provider <new-provider>
/opt/hermes/bin/hermes -p <seat> config set model.base_url <new-base>
```

**Use `hermes config set`, never a file edit.** The running process re-persists its own copy over text edits
(observed with `fallback_providers`), and the command's own confirmation is the only receipt that proves what
the owner loaded.

**Do not change `model.default`** unless the user asked for a model change. "Same model setup, new rail" is
the common ask, and quietly swapping the model makes a rail review into an unrequested model review.

---

## 2 · The key goes into EVERY profile, not the root

Hermes resolves credentials **per profile, from that profile's own `.env`**. A key in the root `.env` is
invisible to the seats, and the failure is not an error message the user sees — it is a **fallback**:

```
WARNING runtime_provider: Primary provider auth failed (No usable credentials found for
provider '<new>'. … profile '<seat>' reads keys only from its own .env …).
Falling back to <fallback>/<free-model>
```

The turn then **succeeds** — on the wrong rail, billed to the wrong pot. Copy the key into each profile
without ever printing it:

```python
val = next(l.split("=", 1)[1].strip() for l in open(ROOT_ENV) if l.startswith(f"{NAME}="))
for seat in seats:
    p = f"/opt/data/profiles/{seat}/.env"
    txt = open(p).read()
    if any(l.startswith(f"{NAME}=") for l in txt.splitlines()):
        continue
    open(p, "a").write(f"{NAME}={val}\n")
    os.chmod(p, 0o600)
```

Skip the write when the line already exists — appending a second copy of the same key silently shadows or
duplicates depending on the loader.

---

## 3 · Scripts are the layer nobody owns

Cron jobs that are `no_agent` scripts do not read `config.yaml` at all. Find every hardcoded rail:

```bash
grep -rn '<old-rail-host>' /opt/data/scripts /opt/data/profiles/*/scripts
```

**Resolve the wrapper hop before believing a clean result.** A cron `--script` is usually a two-line `.sh`
that execs a canonical `.py`; grepping only the wrapper reports "no reference" while the job still calls the
old rail 24 times a day. Match each job's script, then follow every `*.py` it names.

Replace each hardcoded `(url, key-env)` pair with one import:

```python
sys.path.insert(0, "/opt/data/scripts")
import rail
url     = rail.base_url().rstrip("/") + "/chat/completions"
headers = rail.headers(session="<caller-name>")
```

`rail.py` keeps a `RAILS` table (`base_url`, key env var, per-rail extra headers, default model). Adding a
rail is one row; a switch is a config change. **Keep the fallback branch in each script** (old URL) so a
broken import degrades to something that still runs, but log the rail used — an unlogged fallback is how
this defect returns.

---

## 4 · Move the monitors with the fleet

A usage gate still pointed at the retired rail reports **the retired rail's** numbers with the new rail's
confidence. After the switch:

- the **primary** gate reads the NEW provider's meter (USD if it offers USD — more useful than a percent);
- the retired rail becomes a **retired-rail line**, kept readable on purpose, labelled as readable-only;
- spend is printed beside the health verdict: **a green rail is not a cheap rail.**

---

## 5 · Verification ladder — four rungs, in this order

| rung | check | what it proves |
|---|---|---|
| 1 | `grep -A3 '^model:' profiles/*/config.yaml` | the file says what you think |
| 2 | one real turn per seat | the seat can complete |
| 3 | `grep -oE 'API call #.*provider=[a-z-]+' profiles/<seat>/logs/agent.log` | **which rail actually served it** |
| 4 | the provider's own usage totals, before vs after | the traffic really moved |

**Rung 2 alone is a false green.** A `RAIL-OK` reply is produced identically by the right rail, the fallback
rail, and a silent downgrade. Only rung 3 names the provider, and only rung 4 shows the money.

---

## 6 · Two things that look like failures and are not

- **A live gateway caches its provider at startup.** The seat config is correct, but the already-open session
  keeps calling the old rail until it restarts or a new session begins. Report the session as stale — do not
  re-edit the config.
- **A retired rail that still answers is an asset.** Keep its key on disk: it is the only way a stale client
  shows up as a visible call in the ledger instead of vanishing into a silent 401. Retire it in the routing
table, not in the credentials.
