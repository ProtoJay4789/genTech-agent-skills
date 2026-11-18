---
name: agent-tool-contracts
description: "Use when an agent calls a tool with generated arguments."
version: 1.0.0
author: arthur
license: MIT
metadata:
  hermes:
    tags: [agents, tools, schemas, validation, fail-closed, observability]
    related_skills: [falsifiable-tests, claim-provenance, develop-and-verify]
---

# Agent tool contracts — the boundary that refuses junk

A language model will eventually send a string where a number belongs, omit a required field, and invent an
enum value. The contract is the code that stands between that and your data.

**The governing rule: a tool that accepts junk and returns a plausible number is worse than a tool that
refuses.** A refusal costs one turn. A wrong number costs the decision made on it, and nobody can tell it
from a right one.

## When to Use

- Building or reviewing any tool/function an agent calls with generated arguments.
- A tool is returning plausible values you cannot trace to valid input.
- An agent loop is silently producing defaults, zeros, or empty results.
- Wiring an MCP server, function-calling schema, or internal tool registry.

## Procedure

### 1. Declare the schema strictly, and validate at the boundary

Every parameter gets: type, required/optional, enum where the domain is finite, min/max where it is
numeric. Validate **before** the tool body runs, never inside it — a check buried in the body runs after
side effects have begun.

The four checks that catch almost everything:

```python
# type is exact — no silent coercion
if want in ("number", "integer") and isinstance(val, str):
    reject(f"{name}: expected a {want}, received the string {val!r}")

# bool is an int in Python — it will pass an isinstance check and price at 1/0
if want in ("number", "integer") and isinstance(val, bool):
    reject(f"{name}: expected a {want}, received a boolean")

# enums and ranges at the boundary, not in the body
if rule.get("enum") and val not in rule["enum"]:
    reject(f"{name}: must be one of {rule['enum']}, received {val!r}")

# unknown keys are a schema error, not something to ignore
if extra and spec.get("additional_properties") is False:
    reject(f"{unexpected}: not in this tool's schema; allowed: {list(params)}")
```

**Never coerce.** `"5"` becoming `5` in one place and `"5 apples"` becoming `0` in another — silently, with
no error — is the exact failure the contract exists to prevent. If the caller sent a string, say so.

### 2. Write the rejection FOR THE MODEL, not for a log

The error message is the interface. A model cannot act on `ValidationError: field_2`, and it cannot act on a
stack trace. Give it four things in this order:

```
Invalid arguments for `get_price`:
  - quantity: expected a number, received the string "2". Send it as a JSON number: 2
Fix these and call `get_price` again.
```

Name the field, what it expected, **what arrived**, and **the shape that would pass**. The trailing hint is
what turns a complaint into a correction.

### 3. One retry, then FAIL CLOSED

On rejection, hand the message back for exactly one corrected attempt. If the second attempt is also invalid,
return a structured failure — **and never a value**.

```python
# fail closed = the absence of a value is the answer
return {"ok": False, "class": cls, "message": msg, "exhausted": True}   # no "value" key at all
```

One retry because a concrete error message usually fixes the call. A third attempt mostly burns tokens on the
same mistake, and every extra attempt is a chance the model "succeeds" by inventing something plausible.

### 4. Log failure CLASSES with shape, never values

One JSONL line per rejection: timestamp, tool, class, attempt, and the **argument shape** (types, not
values). Shape is enough to debug and cannot leak a customer's data.

Useful class set: `missing_required`, `wrong_type`, `enum_violation`, `out_of_range`, `unexpected_field`,
`retry_exhausted`. A dashboard can then count categories, which is what tells you whether the contract is
catching a real pattern or nobody is hitting it.

### 5. Test every guard in the direction that BLOCKS

A boundary never tested in the direction it refuses is not known to work. Ship the selftest with the
contract, and make it a table:

| trial | expect |
|---|---|
| valid numbers | pass |
| numeric **string** | `wrong_type` |
| `"5 apples"` | `wrong_type` |
| `True` as a number | `wrong_type` |
| missing field | `missing_required` |
| bad enum | `enum_violation` |
| out of range | `out_of_range` |
| unexpected field | `unexpected_field` |
| first call bad, model corrects | value returned, `retry_used` |
| model repeats the mistake | `exhausted`, **no value** |

See `falsifiable-tests` for the discipline behind the table.

### 6. Measure the natural error rate before claiming you fixed anything

The ticket that says "the agent sometimes sends a string" may not reproduce. Run a handful of natural calls
and count. **Three calls is not a rate** — if none err, the honest finding is *"observed 0 of 3 —
UNMEASURED, not 0%"*, and the contract's value is stated as **a boundary, not a fix for an observed defect**.
A guard is still worth shipping on that basis; a *claim* of a fix is not.

## Pitfalls

- **Silent coercion is the defect, not the convenience.** A reader that converts `"5"` to `5` masks every
  caller bug forever, and the one case it cannot convert becomes a `0` nobody notices.
- **`isinstance(True, int)` is True.** Booleans pass numeric checks and price at 1/0. Guard explicitly.
- **A default is fail-OPEN.** `args.get("quantity", 1)`, `or 0`, `except: return {}` — each turns a caller
  error into a plausible value. Missing means refuse, not default.
- **One event, one record.** Logging both the violation class and the terminal outcome for the same rejection
  doubles every count in the dashboard while each class stays internally consistent. Write one record and
  carry the rest as fields (`class`, `attempt`, `terminal`).
- **A selftest that writes to the production log reports fixtures as traffic.** Redirect the log to a temp
  file for the duration of the selftest; the measured tell is a class count that is a multiple of the real
  one (2 real, 6 reported).
- **Do not log argument values.** Shape only. An error log is the most commonly shared artifact in a system
  and the last place a secret should land.
- **A tool that succeeds with an empty result is indistinguishable from a broken read.** If the tool can
  legitimately find nothing, return an explicit empty state, not the same shape as a failure.
- **`--help` working is not the tool working.** Run the real call against real input; a required field the
  parser accepts can still be rejected by the provider (e.g. an endpoint that refuses `temperature: 0` while
  another accepts it). The first live call is the receipt.

## Related

- `falsifiable-tests` — proving a guard goes red for the right reason.
- `claim-provenance` — reporting the resulting failure counts without inflating them.
- `develop-and-verify` — the build/audit split for the code itself.
