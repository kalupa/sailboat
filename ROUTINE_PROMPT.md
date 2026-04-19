# Routine Prompt: Weekly Boat Search Update

**Paste everything below (starting at "You are...") into the prompt field at [claude.ai/code/routines](https://claude.ai/code/routines).**

---

You are running a weekly automated update for a solo circumnavigation boat search. Your work will be reviewed by the user in a pull request on Saturday morning. Be thorough but concise. Prefer factual diffs over editorialising.

## Context

The user is searching for a single sailboat that will serve both a 2027-2033 learning phase and a 2033-2037 solo circumnavigation. Budget ceiling is $90,000 USD / $123,000 CAD for purchase. The living document `circumnavigation_boat_search.md` is the source of truth for tracked candidates.

## Repository layout

```
.
├── circumnavigation_boat_search.md   # the living document (source of truth)
├── scripts/
│   └── parse_craigslist.py           # local-only helper (Craigslist blocks cloud IPs)
├── snapshots/
│   └── YYYY-MM-DD.json               # weekly snapshots
├── pyproject.toml
└── README.md
```

## The search URL

```
https://nanaimo.craigslist.org/search/nanaimo-bc/boo?boat_propulsion_type=1&bundleDuplicates=1&lat=49.0707&lon=-124.0978&min_boat_length_overall=29&search_distance=180
```

## Steps

### 1. Fetch the Craigslist search page

Use the `web_fetch` tool on the search URL above. Do NOT try to run the Python scraper — Craigslist blocks cloud IPs. Only the hosted `web_fetch` tool works.

If `web_fetch` fails or returns empty content:

- Create `snapshots/{today}-error.txt` with a one-line description of what happened
- Open a PR titled "Weekly update: FETCH FAILED {today}" with that description in the body
- Skip remaining steps

### 2. Parse the fetched content

The `web_fetch` tool returns markdown-formatted content. Each listing appears as a numbered item with this approximate shape:

```
N. [Title of Listing

   $PRICE

   Location](https://subdomain.craigslist.org/path/post-slug/POST_ID.html)
```

Extract each listing as a structured record:

- **post_id** — the 10-digit number at the end of the URL before `.html` (stable identifier)
- **title** — the text inside the square brackets, first line
- **price_raw** — the `$XXX` text (may be missing; record as empty string if so)
- **price_numeric** — parsed as a float, or null if missing
- **currency** — `CAD` if the URL subdomain is one of `vancouver`, `victoria`, `nanaimo`, `comoxvalley`, `abbotsford`, `sunshine`, `kamloops`, `kelowna`, `whistler`; otherwise `USD`
- **location** — the location line inside the brackets (may be missing)
- **url** — the full URL

Skip items that don't have a parseable post_id. Skip items with titles like "WANTED:" or "STOLEN" or that are clearly moorage/accessory listings rather than boats.

### 3. Write the snapshot

Save the parsed listings to `snapshots/{today}.json` with this structure:

```json
{
  "scraped_at": "2026-04-25T08:03:47+00:00",
  "search_url": "https://nanaimo.craigslist.org/search/nanaimo-bc/boo?...",
  "listing_count": 142,
  "listings": [
    {
      "post_id": "7927838122",
      "title": "1975 Westsail 32 Sailboat",
      "price_raw": "$46,500",
      "price_numeric": 46500,
      "currency": "CAD",
      "location": "Victoria",
      "url": "https://victoria.craigslist.org/boa/d/sidney-1975-westsail-32-sailboat/7927838122.html"
    }
  ]
}
```

Commit this as `data: add snapshot for {today}`.

### 4. Compare against the previous snapshot

Find the most recent snapshot file from a prior date (not today's). Compute three sets keyed on `post_id`:

- **NEW**: in today, not in previous
- **PRICE_CHANGED**: in both, different `price_numeric`
- **REMOVED**: in previous, not in today

### 5. Score NEW listings for relevance

Classify each NEW listing by title (case-insensitive):

**HIGH relevance** — title contains any of:

> Valiant, Pacific Seacraft, Tayana, Hans Christian, Westsail, Baba, Swan, Nautor, Cabo Rico, Hallberg-Rassy, Hallberg Rassy, Morris, Najad, Amel, Bristol Channel Cutter, BCC, Shannon, Crealock, Mason, Cape George

**MEDIUM relevance** — title contains any of (and not already HIGH):

> bluewater, blue water, offshore, cutter, circumnavig, world cruiser, long distance, Taiwan, Ta Shing, Tashiba, Panda, Endurance, Freedom 36, Pearson Triton, Allied Seawind, Alberg 35, Cape Dory, double-ender

**LOW relevance** — everything else.

**Exclusion filters** (drop regardless of keyword matches):

- Title contains "partnership", "share", "fractional", "1/3", "1/4", "1/5"
- Title contains "WANTED" (people looking to buy, not to sell)
- Title contains "project", "for parts", "hull only"
- Title contains "ferro"
- Title contains "STOLEN"
- Title contains "moorage" without a boat name
- Title is a gear/accessory listing (sails, rigging only, decals, inverter, genoa, etc.)

### 6. Identify changes on tracked boats

Parse `circumnavigation_boat_search.md` to extract URLs in Tier 1 and Tier 2 sections.

For each tracked boat:

- If its URL appears in PRICE_CHANGED: note the price change
- If its URL appears in REMOVED: the boat was absent from results this week. Do NOT eliminate on first absence — may be a one-week glitch.
- If its URL has been absent from two consecutive snapshots (check the snapshot before the previous one too): move to Tier 3 with reason "Possibly sold — removed from Craigslist results on {date}".

For boats not sourced from Craigslist (YachtWorld listings like Freja, Saoirse, and any others without a `craigslist.org` URL), this step does nothing. Those are tracked manually.

### 7. Update the living document

Modify `circumnavigation_boat_search.md`:

1. Increment the version in the header (v1.0 -> v1.1 -> v1.2 ...)
2. Update "Last Updated" to {today}
3. Add a new section at the top of Tier 2 titled "### New This Week ({today})" containing:
   - A bulleted list of HIGH-relevance NEW listings, each with: make/model, price, location, URL, and a one-sentence reason (which keyword matched)
   - A nested "**Also notable (medium relevance):**" list with MEDIUM-relevance NEW listings, each as a one-liner
   - If no new HIGH or MEDIUM listings: a single line "No new matches this week."
4. For any PRICE_CHANGED Tier 1 / Tier 2 boats:
   - Update the `Price` field at the top of their entry
   - Append to their "Concerns / open questions" list: "Price changed from ${old} to ${new} on {today}"
5. For tracked boats absent from results twice in a row:
   - Move their entry from Tier 1/2 to Tier 3
   - Add notes: "Possibly sold — removed from Craigslist results on {date}. Verify before eliminating entirely."
6. Prepend a new changelog entry at the bottom:

```
| {today} | v{new-version} — N new HIGH, M new MEDIUM, K price changes, P possibly sold |
```

Commit this as `docs: weekly update for {today}`.

### 8. Open the PR

Create the branch `claude/weekly-update-{today}`. Push both commits. Open a pull request titled `Weekly boat search update: {today}` with this body structure:

```markdown
## Summary

- **New listings**: N HIGH, M MEDIUM, K excluded/LOW
- **Price changes on tracked boats**: N
- **Tracked boats absent from results this week**: N
- **Moved to Tier 3 (possibly sold)**: N

## High-relevance new listings

- **Make Model** — $price location — [link]
  - Matched: `keyword`

(or "None this week")

## Medium-relevance new listings

- Title — $price — [link]

(or "None this week")

## Price changes

- **Boat Name** (Tier 1/2): $old → $new
  - [link]

(or "None this week")

## Possibly sold

- **Boat Name** (previously Tier 1/2): absent for 2+ weeks, moved to Tier 3

(or "None this week")

## Snapshot metadata

- This week: `snapshots/{today}.json` — N listings
- Previous: `snapshots/{previous-date}.json` — N listings
```

## Constraints

- Do NOT modify any Tier 1 candidate's detailed analysis (equipment lists, concerns lists, estimated all-in). Only update their Price field and add to concerns list as specified.
- Do NOT delete old snapshots.
- Do NOT analyse individual listings in depth. The weekly PR is for surface-level diffs. Deep analysis is human-initiated.
- Do NOT change the "Decision Framework" section, eliminated candidates narrative, or decision timeline.
- If parsing an individual listing fails (missing title, malformed URL), skip it silently. One bad listing is not worth a PR failure.
- If the repo has been updated since the last run (e.g., user moved a boat between tiers manually), respect those changes — read the current state fresh each time.
