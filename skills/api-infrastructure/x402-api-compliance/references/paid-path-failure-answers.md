# The paid path — what a buyer gets when serving fails

The gate is the easy half. The half that costs trust is what happens **after** the payment verifies and the
request goes wrong. A buyer who is charged and then receives a 500 has been sold a promise, and the record
of it usually looks healthy.

## A dict is not a Response — and the framework will not save you

FastAPI/Starlette serialize the return value of a **route handler**. They do nothing of the sort for an
arbitrary helper the handler calls. So a helper in the paid path that returns `{"error": ..., "status":
"degraded"}` hands the handler a plain dict, which reaches Starlette as an unserializable return value and
becomes **HTTP 500 with no body and no reason** — after the money moved.

The decorated handler returning a dict is fine and idiomatic. **The bug only exists in helpers**, which is
exactly where nobody looks for a response-shape problem.

**Audit rule:** in the post-verification proxy function, every `return` must produce a `Response`-family
object. List them mechanically rather than by eye:

```python
import re
src = open(GATEWAY).read().splitlines()
start = next(i for i, l in enumerate(src) if "def _route_to_backend" in l)
seg = src[start:start + 140]
print("bare dicts:", [start + 1 + i for i, l in enumerate(seg) if re.match(r"\s+return \{", l)])
```

**The two paths that almost always carry it**, because both are the "we cannot serve this" branches a
healthy system never exercises:

1. **No backend mapped** for a configured service — returns a status dict instead of a refusal.
2. **Backend connection error** — returns an error dict instead of a 503.

Both must answer a real status: **503 with a reason**. A buyer can retry a 503; a 500 with an empty body is
indistinguishable from the server having died.

**Check the import too.** `JSONResponse` is frequently used and never imported, because the reference sat in
a branch nobody ran. `ast.parse` will not catch a missing name — only an import-time smoke test will.

## Log the payment AFTER the endpoint, so a failure still leaves a record

A paid call that fails in delivery must still appear in the payment log. Put the payment write in HTTP
**middleware**, after `call_next(...)` returns, not at the end of the success branch inside the endpoint:

```python
async def _traffic_middleware(request, call_next):
    response = await call_next(request)   # runs the endpoint; any status comes back here
    _payment_log(request, response.status_code)
    return response
```

The endpoint stamps the verdict on `request.state` (`stat="verified"`, rail, tx); the middleware writes the
row whatever the status turned out to be. **That ordering is the whole defence against "money taken,
nothing served"** — the row exists even when the response was a 500. Verify it by reading the middleware,
not by assuming; a log written inside the success branch records nothing precisely when it matters.

## Falsify the repair before claiming it

A green test proves the current code is not the broken code, and nothing more. Prove the test can go **red**:

1. Plant the defective return shape back into the function (the old bare dict).
2. Run the test; require a non-zero exit and a message naming the object type (`dict status=MISSING`).
3. Restore the fix; require exit 0 with the real status on both paths.

**A test that cannot fail on the original defect is decoration.** Two paths, two assertions, one planted
regression — that is the minimum that means anything.

> Sibling depth: `references/v2-payment-challenge.md` for the gate itself,
> `references/bazaar-catalogue-indexing.md` for discovery. This file is only about what the buyer receives
> once the gate passes.
