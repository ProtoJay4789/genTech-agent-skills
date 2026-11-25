# GenTech Agent Kit

**261 skills that make a Hermes agent better at its job.** MIT.

Most of these were written the only way durable doctrine gets written: something broke, and the fix needed to
outlive the session that found it. Each skill says **what it is for** — and the ones that matter say **what broke
first**, because that is the part that transfers.

## Install one skill

```bash
hermes skills install https://raw.githubusercontent.com/ProtoJay4789/genTech-agent-skills/master/skills/<category>/<skill>/SKILL.md
```

## Install everything

```bash
git clone https://github.com/ProtoJay4789/genTech-agent-skills.git
cp -a genTech-agent-skills/skills/. ~/.hermes/skills/
```

## Am I current?

```bash
git log -1 --format='%h %ci'     # what you have
git pull --ff-only               # take what we have
```

## What is in here

| area | what it covers |
|---|---|
| `agent-kit/` | the operating doctrine — verification, memory, cron health, claim provenance |
| `research/` `media/` `creative/` `productivity/` | doing the work: finding, making, producing |
| `software-development/` `devops/` `security/` | building it and proving it still works |
| `agent-coordination/` `autonomous-ai-agents/` | several agents on one job, without lying to each other |
| `ops/` `email/` `web/` `mcp/` `memory/` | the plumbing |

**Start with these three:**

- `agent-kit/whats-actually-being-said` — five rules about reports that lie, each from a defect that shipped
- `development/develop-and-verify` — the Jr/Sr loop: one model writes, a different one reads it cold
- `devops/duplicate-skill-merge` — how to consolidate a skill library without losing a lesson

## What is deliberately *not* here

Our trading venues, our paid product line, our people, our housekeeping. Nothing in this repo names a wallet, a
group chat, a host, or a credential. **Publishing this set runs a secret-and-PII preflight before every push.**
The one file that contains a detector pattern is a test fixture, and it says so.

## Two absences worth naming

- **A reference a skill cites but does not ship** is listed under a `## Missing references` heading. Visible,
  not silent — the reader is told rather than left to find nothing.
- **A skill that absorbed another** names it in an **Absorbed:** line and keeps the full body under
  `references/<name>/`. Nothing was deleted to make the library smaller; it was moved.

## License

MIT — see `LICENSE`. Use it, fork it, correct it. If you find a rule here that is wrong, the bug report is worth
more than the star.
