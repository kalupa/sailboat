# boat-search

Weekly automated monitoring of Pacific Northwest sailboat listings for a solo circumnavigation boat search. Runs as a Claude Code routine and opens a PR every Saturday with updates.

## What this does

Every Saturday morning, a Claude Code routine:

1. Fetches a Craigslist sailboat search (PNW, 180mi radius from Nanaimo, min 29')
2. Diffs against the previous week's snapshot
3. Scores new listings against target keywords (Valiant, Pacific Seacraft, Tayana, etc.)
4. Updates the living document (`circumnavigation_boat_search.md`) with new matches, price changes, and possibly-sold boats
5. Opens a PR for review

## Files

| File | Purpose |
|------|---------|
| `circumnavigation_boat_search.md` | Living document — the source of truth for tracked candidates |
| `scripts/parse_craigslist.py` | Local-only helper (Craigslist blocks cloud IPs; useful for testing parsing on your Mac) |
| `snapshots/` | Weekly JSON snapshots (append-only, never deleted) |
| `ROUTINE_PROMPT.md` | The prompt to paste into the Claude Code routines UI |
| `pyproject.toml` | uv-managed Python project |

## How the routine actually fetches

Craigslist returns 403 to most cloud IPs. The routine works around this by using Claude's hosted `web_fetch` tool (which has its own infrastructure Craigslist doesn't block) rather than making a direct HTTP request. The Python script in `scripts/` is kept for local development and parsing verification — it works fine from a residential IP.

## Local setup

```bash
# One-time
git clone git@github.com:kalupa/boat-search.git
cd boat-search
uv sync

# Test the scraper manually
uv run scripts/parse_craigslist.py
# -> writes snapshots/YYYY-MM-DD.json
```

## Routine setup

1. Go to [claude.ai/code/routines](https://claude.ai/code/routines)
2. Click **New routine**
3. Name: `Weekly boat search update`
4. Model: Sonnet or Opus (either is fine; Opus if you want the thoroughness, Sonnet for speed/cost)
5. Paste the contents of `ROUTINE_PROMPT.md` (everything below the "You are..." line) into the prompt field
6. Select this repository (`kalupa/boat-search`)
7. Environment: Default is fine. If the scraper fails due to restricted network, use an environment with full network access.
8. Trigger: **Schedule**, Weekly, Saturday, 08:00 in your local timezone
9. Connectors: include GitHub (for the PR). Others optional.
10. Click **Create**
11. Click **Run now** to test the first run

## Design notes

- **The scraper is deterministic; the routine does judgment.** The Python script only extracts data. Relevance scoring, living-doc updates, and prose writing are done by Claude in the routine session because they require judgment that changes over time (e.g., as the user's tier preferences evolve).
- **Snapshots are append-only.** Never deleted, so the full search history is preserved. Each week's scrape is a new file.
- **The living document is the source of truth.** The routine reads it to know what's currently tracked and only updates sections it's allowed to touch.
- **Branch protection.** Pushes default to `claude/weekly-update-{date}` branches. Main is safe.

## Manual operations

### Promote a Tier 2 candidate to Tier 1

Edit `circumnavigation_boat_search.md` directly. Move the entry from Tier 2 to Tier 1, expand with full specs, equipment, concerns, etc. The routine will continue to track price changes automatically.

### Eliminate a candidate

Edit `circumnavigation_boat_search.md`: move the entry to Tier 3 with a reason in the notes.

### Update a Tier 1 boat after viewing

Edit the living document directly with viewing notes, survey findings, etc. The routine won't overwrite your work — it only modifies prices and adds to a "concerns" list.

### Adjust the Craigslist search

Edit `SEARCH_URL` in `scripts/parse_craigslist.py`. The snapshot format doesn't depend on the search parameters.

### Add/remove target keywords

Edit the keyword lists in `ROUTINE_PROMPT.md` and update the routine in the claude.ai/code/routines UI.

## Troubleshooting

**The routine opened a PR titled "FETCH FAILED"**: `web_fetch` failed against Craigslist. Rare, but possible. Check the PR body for the failure note. If it recurs for multiple weeks, the routine prompt may need to be adjusted to handle the failure mode, or fall back to manual paste-based updates.

**The routine runs but misses an obvious match**: The keyword isn't in the HIGH or MEDIUM list. Edit the routine prompt at claude.ai/code/routines to add it.

**The routine flags too much**: Tighten the exclusion filters in the routine prompt.

**The routine parsed fewer listings than expected**: `web_fetch` returns markdown, and Craigslist's layout may occasionally change in a way that breaks the markdown shape assumed in the prompt. Look at the snapshot JSON to see what was parsed. Adjust the parsing description in Step 2 of the routine prompt.

**The routine modifies sections I told it not to**: Routines are autonomous. If the prompt's Constraints section isn't enough, add explicit don't-touch markers in the living document, e.g. `<!-- ROUTINE: DO NOT MODIFY BELOW -->`.
