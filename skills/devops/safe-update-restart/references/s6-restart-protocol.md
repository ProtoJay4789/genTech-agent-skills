# Restart protocol — the s6 / Docker host (measured 2026-10-17)

> **Read this before the systemd sections of the parent skill.** The main SKILL.md describes a systemd
> topology (`systemctl --user`, per-profile units, a single `hermes-gateway.service`). **That host shape does
> not exist here.** This container has **no systemd** (`systemctl: command not found`,
> `/run/systemd/system` absent) — it is **s6-overlay**, and the restart mechanism is **`s6-svc`**.
> Everything below is measured on this host, not inferred.

## The measured topology

```
7 s6 gateway slots          state                        what its run script execs
gateway-default             UP   (pid 250, 60304s)      hermes                gateway run --replace
gateway-gentech             DOWN (not started yet)       hermes -p gentech     gateway run --replace
gateway-gentech-treasury    DOWN (not started yet)       hermes -p gentech-treasury gateway run --replace
gateway-arthur              DOWN (not started yet)       hermes -p arthur      gateway run --replace
gateway-protojay            DOWN (not started yet)       hermes -p protojay    gateway run --replace
gateway-gizmo               DOWN (not started yet)       hermes -p gizmo       gateway run --replace
gateway-pixel               DOWN (not started yet)       hermes -p pixel       gateway run --replace
dashboard                   UP   (pid 202)               hermes dashboard --host 0.0.0.0 --port 4860
main-hermes                 UP   (pid 201)
```

**The shape is not "one unit" and not "seven units". It is seven slots with exactly one live gateway.**
`gateway-default` runs the **multiplexer** (`multiplex_profiles: true`), which serves **all seven profiles**.
The other six slots are held **down** by a `down` file in their service directory — their scripts are present
and armed, but s6 will not start them.

Ports actually listening: **`:4860`** (dashboard, `0.0.0.0`) · **`:8642`** (api_server / peer rail,
`127.0.0.1`) · `:43689` (container DNS). Nothing on `:8090` — the x402 gateway is dark, expected.

## The restart commands

```bash
S6=/package/admin/s6/command

# 1. The whole fleet's gateway — ALL SEVEN PROFILES AT ONCE (highest blast radius)
$S6/s6-svc -r /run/service/gateway-default

# 2. The dashboard only
$S6/s6-svc -r /run/service/dashboard

# 3. Graceful stop / start of the fleet gateway
$S6/s6-svc -d /run/service/gateway-default     # down
$S6/s6-svc -u /run/service/gateway-default     # up   ← ONLY ever for gateway-default
```

Useful reads — **assert the state, never assume the command worked**:

```bash
$S6/s6-svstat /run/service/gateway-default
#   expect: up (pid <NEW>) <seconds since start>   — a NEW pid and a RESET uptime are the proof
$S6/s6-svstat /run/service/dashboard
cat /opt/data/gateway.pid      # {"pid":…, "kind":"hermes-gateway", …} — cross-check against s6-svstat
python3 -c "import json;d=json.load(open('/opt/data/gateway_state.json'));print(d.get('gateway_state'), (d.get('platforms') or {}).keys())"
```

## ⚠️ THE FOOTGUN — never `-u` an inert slot

**All seven run scripts carry `--replace`.** The six inert slots exec `hermes -p <seat> gateway run
--replace`. `--replace` means *take the gateway lock from whoever holds it.*

So `s6-svc -u /run/service/gateway-arthur` does **not** "bring the arthur gateway up alongside the others."
It starts a single-profile gateway that **seizes the lock from the live multiplexer (pid 250)**. The
multiplexer then exits — and `gateway-default`'s own `finish` script **exits 125 on a clean exit (code 0),
which tells s6 not to restart it.** The likely end state: **one `arthur` gateway serving, six profiles dark.**

**An innocent "start the arthur gateway" can decapitate the fleet.**

> ⚠️ **HONEST SCOPE:** this is reasoned from the run scripts, the `finish` exit-code logic, and `--replace`
> semantics — **it was deliberately NOT tested, because testing it would take the fleet down.** Treat it as a
> high-confidence hazard, not a measured outcome. The safe rule needs no test: **`-u` is only ever for
> `gateway-default`.**

**Corollary — a per-seat restart is impossible on this host.** "Restart just Treasury" has no s6 path. The
only gateway restart available is the whole multiplexer. If a single profile's gateway must be bounced, that
is a **design change** (start that slot deliberately, having first stopped `gateway-default`), not a restart
command.

## What a restart does and does not touch

| Artifact | Survives a gateway restart / container recreate? | Why |
|---|---|---|
| `/opt/data` (all 7 profiles, vault, `.env`, cron, secrets, state) | **yes** | host bind mount |
| `state.db` + its un-checkpointed `-wal` | **yes** | SQLite replays the WAL on next open |
| queued writes under `pending/` | files survive — but remain **unapplied** | on disk ≠ applied |
| anything held **in an in-memory turn** | **no** | this is what the ACK exists to protect |
| an **image swap** (vs a recreate) | **no** — the mount is replaced | see `hermes-update-prep-2026-10-17.md` |

## Who gates a restart

Per the parent skill: the **VPS seats** gate it (gentech, gentech-treasury, arthur, protojay are the live
ones; gizmo and pixel are retired-but-running). **Forge (Desktop) is contact-as-available, not a blocker.**

**And the ACK must satisfy RULE ONE (Jordan, 2026-10-17): FINISH → LOG → VERIFY → *then* ACK.** An ACK means
*"I am complete, or cleanly parked in the brain"* — with a **named resume point** — not "I saved something."
A seat that cannot finish returns `NOT READY — mid-<task>`, which is a **gate that has not opened**.

## The order, end to end

1. **Baseline** — `s6-svstat` every slot, `gateway.pid`, the listening ports, the public endpoints.
2. **Dispatch the checkpoint** to every live seat (vault handoff + `hermes peer dm` wake), carrying the
   FINISH-not-save requirement.
3. **Wait for real ACKs** — read them for resume points, not for the phrase. `NOT READY` = do not proceed.
4. **Restart** — `s6-svc -r /run/service/gateway-default` (the only gateway restart there is).
5. **Verify** — new pid + reset uptime, `dashboard` still up, `:4860` and `:8642` listening, public
   endpoints matching the baseline, and **the gateway's start time compared against the install/repair
   mtime** (an ACK is not proof the process is on current code).
6. **Warn the seats** — a bounce drops live sessions; they rebuild on the next turn.

## Why this file exists

The parent skill's topology section told the reader to verify "one multiplexer unit" and to use
`systemctl --user`. **Both are wrong for this host**, and the failure mode the parent skill already warns
about — *"a script that references the wrong unit topology is a silent no-op, not a restart"* — is live here:
`s6-svc -r` on any of the six down slots does **nothing**, exits 0, and looks like success. Measure the slot
state first; the command's exit code is not the outcome.
