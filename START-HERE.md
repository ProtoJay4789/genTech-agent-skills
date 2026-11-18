# START HERE — install the six skills that make an agent behave like ours

**This is the shortest honest path from "I have a Hermes agent" to "my agent works the way GenTech agents work."**
Everything below was verified by running it on 2026-11-18, not copied from a doc.

---

## ⚠️ Two traps that will waste your first ten minutes

**1 · The default branch is `master`, NOT `main`.** A `main` URL returns **404**, and `hermes skills inspect` reports
it as *"Could not find … in any source"* — which reads like a broken skill instead of a wrong branch.

**2 · A skill lives three levels deep:** `skills/<category>/<skill>/SKILL.md`.
`skills/agent-coordination/SKILL.md` does not exist; `skills/agent-coordination/agent-to-agent-messaging/SKILL.md` does.

---

## The six — in this order

```bash
BASE=https://raw.githubusercontent.com/GentechLabs/genTech-agent-skills/master/skills

hermes skills install $BASE/development/develop-and-verify/SKILL.md        --yes
hermes skills install $BASE/agent-kit/verify-after-every-action/SKILL.md   --yes
hermes skills install $BASE/claim-provenance/SKILL.md                      --yes
hermes skills install $BASE/agent-kit/falsifiable-tests/SKILL.md           --yes
hermes skills install $BASE/agent-coordination/agent-to-agent-messaging/SKILL.md --yes
hermes skills install $BASE/gentech-ops/handoff-mesh/SKILL.md              --yes
```

**Verify what landed:**
```bash
hermes skills list | grep -E 'develop-and-verify|verify-after|claim-provenance|falsifiable|agent-to-agent|handoff-mesh'
```

## Why these six, and not the other 176

**Every one of them replaces a habit that produces confident wrong answers.** **That is the whole difference between an
agent that sounds useful and one you can act on.**

| skill | the habit it kills |
|---|---|
| **develop-and-verify** | "I wrote the code, so it works." **Build it, run it, report what execution actually returned.** |
| **verify-after-every-action** | "The command succeeded, so the task succeeded." **A 200 is not a delivery.** |
| **claim-provenance** | Reporting a number without saying where it came from. **A figure with no source is a rumour.** |
| **falsifiable-tests** | A test that passes on everything. **If it cannot fail, it is not a test.** |
| **agent-to-agent-messaging** | "I sent it, so they got it." **A wake must be observed, never assumed.** |
| **handoff-mesh** | Verbal agreements that evaporate. **Written handoffs are the delivery of record.** |

**Install these first and the rest of the library makes sense.** **Install the library first and you have 182 skills and
no discipline.**

---

## The whole library, if you want it

**Skills live in `$HERMES_HOME/skills/`** (per profile: `profiles/<seat>/skills/`).

```bash
git clone https://github.com/GentechLabs/genTech-agent-skills.git ~/gentech-agent-skills
cp -r ~/gentech-agent-skills/skills/* "$HERMES_HOME/skills"/
hermes skills list | wc -l
```

**Copy, do not symlink.** **Cron and the skill loader resolve real paths; a symlinked tree breaks on the next
container recreate.**

## What is in here besides skills

```
vault-structure/README.md   the vault layout our agents read, and why each folder exists
docs/memory-rules.md        how our agents size and trim their own memory
docs/hermes-gateway-troubleshooting.md
erc-8004/                   agent identity
cron/                       a sample cron snapshot
```

## What we will not give you

**No `.env`, no keys, no wallet material.** **Skills are shareable; credentials are not.** **Generate your own provider
key.** **If you want our paid APIs, pay per call like any customer — that is the product, not a favour.**

---

**Maintained by GenTech Labs (HQ).** **If a command here stops working, that is a defect in this file — say so, and it
gets fixed the same day.**
