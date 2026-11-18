# Agent credential brokers — landscape and evaluation

Services that hold a secret on the agent's behalf so the agent's own process never contains it. Relevant
because a compromised agent process (prompt injection, a poisoned dependency) can exfiltrate anything in
its environment — brokering removes the thing worth stealing.

**Scope first: this is for API/service credentials only.** Wallet signing keys do not belong in any of these
— see SKILL.md, "Brokering credentials is not the same as holding keys".

## The two mechanisms

| Mechanism | How it works | Strength | Weakness |
|---|---|---|---|
| **MitM broker** | Agent gets a *placeholder*; an `HTTPS_PROXY` intercepts outbound calls and substitutes the real value. | The agent's process never holds the secret, not even briefly — exfiltration has nothing to grab. | A proxy sits in every outbound path, so a bug there is a fleet-wide interception surface. Needs a trusted root CA installed into the agent. |
| **Lease / killswitch store** | Agent receives the real value for a bounded session (TTL), with rotation hooks and a killswitch. | Small to run; strong audit and revocation story; no proxy in the path. | The agent *does* hold the secret while the lease is live, so a compromise inside that window still leaks it. |

## Candidates seen (verify before trusting — none audited)

- **Infisical `agent-vault`** — MitM broker, Go, self-hosted single binary. Names `hermes` as a supported
  agent in its own docs. Ships egress filtering, per-request logging, multi-vault tenancy, deny mode.
- **`joelhooks/agent-secrets`** — lease store, Go. Age encryption, session-scoped leases with TTL,
  killswitch, append-only audit log.
- Also surfaced: Tuskira's secured MCP gateway (Apache-2.0), **Agentgateway** (Linux Foundation / Agentic AI
  Foundation), Bitwarden's Agent Access SDK (just-in-time access + human-in-the-loop approval), Keeper's
  agent kit, and several small MIT "credential firewall for LLM agents / MCP servers" projects.

## Evaluation checklist

1. **Verify the artifact before running it.** Download the release **and** its `checksums.txt`, and compare
   `sha256sum`. A broker fetched without verification is a supply-chain hole wearing a security badge.
2. **Confirm it binds loopback.** Start the server and check it listens on `127.0.0.1`, not `0.0.0.0`. Use a
   throwaway master password, never a real one.
3. **Read what it sets on the child process** (`run --help` or equivalent): those env vars define what the
   agent can reach. Prefer a tool that hands the child a scoped, short-lived token over one that hands it
   the master credential.
4. **Require a canary substitution test before trusting it.** Register a throwaway upstream holding a canary
   value, route one request through the broker, and read what the far end actually received. Until that
   passes, "it runs" is not "it brokers".
5. **Ask where its unwrap secret lives.** If the master password exists only on the same host, this is
   single-host custody with extra steps — see SKILL.md.

Running a binary and proving it serves HTTP is **not** evidence that it brokers correctly. Report those as
separate claims, and stop the test instance when done.
