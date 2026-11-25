# Measuring a code library before recommending it

When the link is a **library or CLI** — README says `pip install` / `npm install` — a README summary is not a
verdict. Install it, run it, and make one of its claims fail on purpose.

## Procedure

1. **Isolated venv, never the seat's own python.**

   ```bash
   mkdir -p <scratch>/probe && cd <scratch>/probe
   python3 -m venv .venv
   .venv/bin/python -m ensurepip --version      # some builds ship without pip
   .venv/bin/pip install <package>
   .venv/bin/python -c "import <mod>; print(getattr(<mod>,'__version__','?'))"
   ```
   Print the version and the import path. A pin you did not read is a version you cannot describe.

2. **Run the README's own quickstart verbatim.** Not a paraphrase. If the shipped example fails, that is the
   finding — do not quietly write your own example and call the library working.

3. **Run every CLI subcommand once** (`check`, `draw`, `describe`, …) and record which outputs were produced and
   which were *skipped*. A skip is a capability you cannot claim.

4. **Break it on purpose.** Feed the one input the docs say it rejects, and confirm it **raises and names the
   fault** instead of drawing something silently wrong. A validator you have never seen fail is a validator you
   cannot trust — and its failure mode tells you whether it fails open or closed.

5. **Capture a real artifact plus the script that made it**, into the vault beside whatever will consume it. A
   regenerable artifact survives review; a hand-exported one rots the first time the words change.

6. **Record the maintenance risk in the note, not in your tone:** age, stars, number of maintainers, licence,
   dependency count. A young single-maintainer library is fine to *adopt* and unsafe to *depend* on — say which,
   and note that vendoring is cheap when it is small, MIT-ish and has one dependency.

## A tool's stated cause is a claim, not a diagnosis

When the library reports **why** something failed, verify the mechanism before writing it down:

- **Read the code path that produced the message.** Helper functions frequently return a bare `False` for *any*
  failure while the caller prints one guess. That guess can be flatly false — "dependency not found" when the
  dependency was found in the first statement.
- **Reproduce the failing step by hand, with the tool's exact arguments**, so the real error surfaces. Copy the
  argv the library builds, run it yourself, read the first `FATAL`/exception line.
- **Check the environment assumption explicitly:** is the binary on the path the helper checks, is the env var
  read with the case the code uses, does a launcher flag need to differ for this container or this uid.

Write the **verified** cause into the note. Recording the tool's guess sends the next session down a blind alley,
and "tool says X is missing" outlives the day X was actually missing.

## Verdict shape

1. what works **on this host**, with the output that proves it;
2. what does not, with the **real** cause and any workaround that does work;
3. what it does for us **specifically**, tied to a named open item ("this is the diagram M0 step 1 asks for") —
   a tool with no named consumer is a bookmark, not a build;
4. the risk, stated plainly.

**Do not record "X does not work here" as a permanent claim.** Record the workaround, so a later session with a
fixed environment is not locked out by a stale note.
