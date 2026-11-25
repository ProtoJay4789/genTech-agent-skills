# Scoring a repo BEFORE you spend a submission

Stars tell you who watches. **Merge latency tells you who acts.** Score a candidate on its own closed-PR
history and submit only to repos that actually merge outsiders.

## The four numbers

| number | how | what it decides |
|---|---|---|
| **median open→merge days** | `closed_at`/`merged_at` per merged PR, median over the last ~50 closed | do they review at all, and how fast |
| **external merge ratio** | merged ÷ (merged + closed-unmerged) | is the door open, or does it look open |
| **external merge count** | merges where `user.login != repo owner` | do they merge STRANGERS, not just teammates |
| **last push days** | `repo.pushed_at` | is it alive at all |

## Verdicts

- **ACCEPTING** — median ≤ 7d, ≥50% merge ratio, external merges present, pushed ≤ 30d → submit here.
- **SLOW** — median ≤ 30d → submit only if the listing genuinely matters.
- **CLOSED** — almost no external merges in the window. A low ratio with a *good* median means they triage fast
  and decline fast; more submissions will not change that.
- **DEAD** — no push in 90d. Every PR opened here is a deposit into a void, however good the rank.

**Read the ratio and the median together.** 8 days + 0.12 is a shop that answers every PR with a close. 1 day +
0.86 is a shop that merges strangers.

## The calls (read-only, no special scopes)

```bash
TOK=$(cat /opt/data/profiles/<profile>/secrets/github-token-<login>)
api() { curl -sL -m 25 -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $TOK" "$1"; }

api "https://api.github.com/repos/<owner>/<repo>" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['pushed_at'],(d['owner']['login']))"

api "https://api.github.com/repos/<owner>/<repo>/pulls?state=closed&sort=updated&direction=desc&per_page=50" \
  | python3 -c "
import json,sys,datetime as dt
ps=json.load(sys.stdin)
def d(a,b): return (dt.datetime.fromisoformat(b.replace('Z','+00:00'))-dt.datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()/86400
merged=[p for p in ps if p.get('merged_at')]
closed=[p for p in ps if p.get('closed_at') and not p.get('merged_at')]
lat=sorted(d(p['created_at'],p['merged_at']) for p in merged)
print('median',round(lat[len(lat)//2],1) if lat else None,'| merged',len(merged),'| closed-unmerged',len(closed),'| ratio',round(len(merged)/max(len(merged)+len(closed),1),2))"
```

**Filter bots out of anything you call a conversation.** Review robots comment on every PR; count only
`user.type != "Bot"` and logins not ending `[bot]`.

## Budget notes

- **Search API is the scarce resource** (30/min authenticated, 10/min code search); the plain REST calls above are
  cheap. Score in batches and cache the result to a JSON file — re-running a scan per submission wastes the budget
  that the inbox job needs.
- **Never score a repo by fetching every PR individually.** One `pulls?state=closed&per_page=50` per repo is the
  whole measurement; per-PR calls are only for rows you are already reporting.

## What the score cannot tell you

A repo that scores ACCEPTING and still ignores your PR is telling you about **your submission**. The next
measurement is a diff, not a ranking: fetch `pulls/<newest-merged>/files` and `pulls/<yours>/files`, compare the
SHAPE (runnable demo vs placeholder, assets present, path/layout conventions), and fix the gap.
