---
name: watchers
description: Poll RSS, JSON APIs, and GitHub with watermark dedup.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [cron, polling, rss, github, http, automation, monitoring]
    category: devops
    requires_toolsets: [terminal]
    related_skills: []
---

# Watchers

Poll external sources on an interval and react only to new items. Three ready-made scripts plus a shared watermark helper; wire them into a cron job (or run them ad-hoc from the terminal).

## When to Use

- User wants to watch an RSS/Atom feed and be notified of new entries
- User wants to watch a GitHub repo's issues / pulls / releases / commits
- User wants to poll an arbitrary JSON endpoint and get notified on new items
- User asks for "a watcher for X" or "notify me when X changes"

## Mental model

A watcher is just a script that:

1. Fetches data from the external source
2. Compares against a watermark file of previously-seen IDs
3. Writes the new watermark back
4. Prints new items to stdout (or nothing on no-change)

The scripts below handle all three. The agent runs them via the terminal tool — from a cron job, a webhook, or an interactive chat — and reports what's new.

## Ready-made scripts

All three live in `$HERMES_HOME/skills/devops/watchers/scripts/` once the skill is installed. Each reads `WATCHER_STATE_DIR` (defaults to `$HERMES_HOME/watcher-state/`) for its state file, keyed by the `--name` argument.

| Script | What it watches | Dedup key |
|---|---|---|
| `watch_rss.py` | RSS 2.0 or Atom feed URL | `<guid>` / `<id>` |
| `watch_http_json.py` | Any JSON endpoint returning a list of objects | Configurable id field |
| `watch_github.py` | GitHub issues / pulls / releases / commits for a repo | `id` / `sha` |

All three:

- First run records a baseline — never replays existing feed
- Watermark is a bounded ID set (max 500) to cap memory
- Output format: `## <title>\n<url>\n\n<optional body>` per item
- Empty stdout on no-new — the caller treats that as silent
- Non-zero exit on fetch errors

## Usage

Run a watcher directly from the terminal tool:

```bash
python $HERMES_HOME/skills/devops/watchers/scripts/watch_rss.py \
  --name hn --url https://news.ycombinator.com/rss --max 5
```

Watch a GitHub repo (set `GITHUB_TOKEN` in `${HERMES_HOME:-~/.hermes}/.env` to avoid the 60 req/hr anonymous rate limit):

```bash
python $HERMES_HOME/skills/devops/watchers/scripts/watch_github.py \
  --name hermes-issues --repo NousResearch/hermes-agent --scope issues
```

Poll an arbitrary JSON API:

```bash
python $HERMES_HOME/skills/devops/watchers/scripts/watch_http_json.py \
  --name api --url https://api.example.com/events \
  --id-field event_id --items-path data.events
```

## Wiring into cron

Ask the agent to schedule a cron job with a prompt like:

> Every 15 minutes, run `watch_rss.py --name hn --url https://news.ycombinator.com/rss`. If it prints anything, summarize the headlines and deliver them. If it prints nothing, stay silent.

The agent invokes the script via the terminal tool inside the cron job's agent loop; no changes to cron's built-in `--script` flag are needed.

## State files

Every watcher writes `$HERMES_HOME/watcher-state/<name>.json`. Inspect:

```bash
cat $HERMES_HOME/watcher-state/hn.json
```

Force a replay (next run treated as first poll):

```bash
rm $HERMES_HOME/watcher-state/hn.json
```

## Writing your own

All three scripts use the same template: load watermark, fetch, diff, save, emit. `scripts/_watermark.py` is the shared helper; import it to get atomic writes + bounded ID set + first-run baseline for free. See any of the three reference scripts for how little boilerplate it takes.

## Common Pitfalls

1. **Printing a "no new items" header every tick.** Callers rely on empty stdout = silent. If you print anything on an empty delta, you spam the channel. The shipped scripts handle this; custom scripts must too.
2. **Expecting the first run to emit items.** It won't — first run records a baseline. If you need an initial digest, delete the state file after the first run or add a `--prime-with-latest N` flag in your own script.
3. **Unbounded watermark growth.** The shared helper caps at 500 IDs. Raise it for high-churn feeds; lower it on constrained filesystems.
4. **Putting the state dir where the agent's sandbox can't write.** `$HERMES_HOME/watcher-state/` is always writable. Docker/Modal backends may not see arbitrary host paths.
5. **None value crashes in Python API scripts** (Jun 2026): CoinMarketCap, CoinGecko, and other APIs often return `None` for fields like `price`, `percent_change_24h`, or `market_cap`. If your script does `data["price"]` or `price >= 1000` without null checks, it crashes with `TypeError: '>=' not supported between instances of 'NoneType' and 'int'`. Always use: `data.get("price") or 0` for numeric fields, and `if price is None: return default` in format functions. Proven Jun 11, 2026: Three separate scripts (cmc-watchlist, cmc-news-trigger, narrative-rotation) all crashed on None values from CMC API.

6. **Treat 404 and 500 from a feed host as THROTTLING, not as a dead feed.** Some hosts answer a burst of feed reads with `404` — indistinguishable from "the resource was deleted" — or `500`. The same URL returns a normal payload once the IP has been idle, so **a retry loop deepens the block instead of surviving it.** One attempt per source, several seconds apart, no retries; pick it up next tick.

   Distinguish `throttled` from `failed` in the output. **A run that read nothing must never print "no failures reported"** — that is a clean bill of health issued for a run that measured nothing, and it is indistinguishable from a genuinely quiet period. Print the two categories separately, and say which one applies.

7. **Poll at the rate the source's window can absorb, not the rate you want data.** A feed carrying ~15 entries covers roughly two days of a fast publisher's output, so twice a day cannot miss anything while hourly only raises the chance of being throttled. **Frequency buys nothing the window already gives you, and costs you the ability to read it.**

8. **A message must carry its own context.** Emitting a bare state code (`LONGS_PAYING`), a bare delta, or a number with no scale forces the reader to remember a convention that only exists in the code. Print the value, a sentence saying what it means, and the direction of the change. **If the reader has to ask what the message means, the watcher has failed at the only thing it does.**

9. **An endpoint that returns a UNION of record types must be classified from the record's own discriminator — never from the URL you fetched it with.** GitHub's `/repos/<owner>/<repo>/issues` returns **pull requests and issues in one list**; a record is a PR if and only if it carries a `pull_request` key. Deriving the label from the endpoint gave every entry the same tag, so a feed of twelve rows said nothing about any of them — and a reader who cannot tell a shipped fix from a bug report will stop reading the feed rather than ask. Classify from the payload:

    ```python
    kind = "release" if "releases" in url else ("pr" if it.get("pull_request") is not None else "issue")
    ```

    **Then expose the sub-state that decides whether the reader should act.** For a PR: `state` (`open`/`closed`) and whether `merged_at` is set — **merged means the change already shipped and may imply an upgrade owed; closed-unmerged means the idea was rejected.** Those are opposite verbs, and a single `[pr]` tag hides both. Report them as distinct labels (`pr-merged` / `pr-closed` / `pr-open`).

    The same shape recurs wherever an API merges collections into one endpoint — Jira subtasks, a mailbox listing sent and received, any `/issues`-style route. **Before choosing a label, check whether the collection is homogeneous**; if it is not, the discriminator field is the only honest source of the type.

