# Federal grants feed — grants.gov, no key, no account

Public JSON API, POST, JSON body. Two endpoints do everything:

```bash
# search
curl -s -X POST 'https://api.grants.gov/v1/api/search2' -H 'Content-Type: application/json' \
  --data '{"keyword":"artificial intelligence","oppStatuses":"forecasted|posted","rows":60}'
# one opportunity's detail (eligibility, award floor/ceiling, response date)
curl -s -X POST 'https://api.grants.gov/v1/api/fetchOpportunity' -H 'Content-Type: application/json' \
  --data '{"opportunityId":<id>}'
```

Hits carry only `id · number · title · agencyCode · agency · openDate · closeDate · oppStatus · docType · cfdaList`.
**Eligibility is NOT in the search result — it costs one detail call per candidate.** Budget for that: check the
nearest deadlines first and cap the number of detail calls.

## The two filters the API will not do for you

### 1 · Applicant types — read the codes, never recall them

`data.synopsis.applicantTypes[].id` is contract data. Verified against the live API:

| code | meaning |
|---|---|
| `06` | public/state-controlled institutions of higher education |
| `23` | **small businesses** |
| `25` | Others (see the "Additional Information on Eligibility" text field) |
| `99` | **unrestricted** — open to any entity type |

`07` / `08` are **tribal governments**, not for-profit entities. Guessing that wrong marked a transport grant
eligible when its page said "Native American tribal governments" — a false positive that reads as a real lead.
Keep the raw `applicantTypes` list in the output so a reader can see whether the door is open narrowly (small
businesses only) or widely (unrestricted).

### 2 · A keyword hit is not a fit — judge the TITLE's discipline

"Artificial intelligence" appears in the **body** of orthopaedic, breast-cancer and rare-disease RFPs, so a
keyword search returns a wall of DOD medical research. **Rule: a title that names another discipline disqualifies
the row no matter what the body says**, and a title must name a domain we build in. Measured on one run: 229 rows
dropped by that rule alone, 13 by eligibility, leaving 3 genuinely open.

Disqualifying title words (extend as needed): `cancer · orthopaedic · clinical · therapeutic · drug · patient ·
disease · vaccine · surgery · medical · biomedical · nursing · dental · cardio · oncology · agricultural ·
wildlife · housing · transportation · school · teacher · library`.

## Shape of the scanner that worked

- **Watermark by opportunity id**; report only ids never seen. First run is a **baseline** — cap it (~12) and say so.
- **Silence when nothing is new** — one log line, not a message.
- **Exit 2 when every query fails.** A broken scanner and a quiet scanner must never print the same sentence.
- Deadline gate: drop already-closed, drop beyond ~150 days out. A forecasted opportunity with no close date is
  still worth listing — it is pipeline, not a task.
- Search terms that map to what we build: `artificial intelligence · machine learning · agentic · autonomous
  agents · distributed ledger · blockchain · data science · cybersecurity`. Broad terms like "technology" return
  thousands of hits and the list stops being read.

## Registering the job

State a PURPOSE and a RETIRES WHEN in the script header and in `00-HQ/cron-register.md` — grants scanners are the
class of job that outlives its reason (award won, API changed) and keeps running because nobody wrote the exit
condition down.
