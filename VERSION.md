# GenTech Agent Kit — version marker

This file exists so that **"am I current?" is a command, not a conversation.**

```bash
git log -1 --format='%h %ci'        # what you have
git pull --ff-only                  # take what we have
```

## What moves in this repo

| path | what it is |
|---|---|
| `skills/agent-kit/` | the fleet's operating doctrine — the skills every GenTech seat runs |
| `skills/` | the full library, by category (payments, DeFi, education, comms) |
| `cron/` | scheduled-job patterns and the conformance rules behind them |
| `vault-structure/` | how the brain is laid out, if you want the same shape |
| `START-HERE.md` | read this first |

## How to install one skill

```bash
hermes skills install https://raw.githubusercontent.com/ProtoJay4789/genTech-agent-skills/master/skills/agent-kit/<skill>/SKILL.md
```

Or take the whole kit:

```bash
git clone https://github.com/ProtoJay4789/genTech-agent-skills.git
cp -a genTech-agent-skills/skills/agent-kit/. ~/.hermes/skills/agent-kit/
```

## A note on what these contain

Every skill here was written after a defect, and most of them say **what broke and what it cost**.
That is the point — the failures are the instructions. They include our own, by name.

Two things are deliberately **not** here: the private vault, and any credential. If a skill needs a
key, it reads it from your environment and says so.
