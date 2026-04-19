#!/usr/bin/env python3
"""Fetch the Craigslist sailboat search and emit a structured JSON snapshot.

This script is a LOCAL-DEVELOPMENT helper. It exists so you can:
- Verify the parsing logic works against the current Craigslist markup
- Generate a fresh snapshot from your Mac for a manual update

Craigslist blocks most cloud/datacenter IPs with 403, so this script CANNOT
run from the Claude Code routine environment. The routine uses Claude's
`web_fetch` tool instead (see ROUTINE_PROMPT.md).

Usage (from your Mac, on a residential network):
    uv run scripts/parse_craigslist.py
    # -> writes snapshots/YYYY-MM-DD.json

Exit codes:
    0 - success
    1 - fetch failed (often 403 from Craigslist; try from a residential IP)
    2 - parse returned zero listings (markup may have changed; investigate)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# The user's current search: Pacific Northwest, 180mi radius from Nanaimo,
# sailboats, min 29ft.
SEARCH_URL = (
    "https://nanaimo.craigslist.org/search/nanaimo-bc/boo"
    "?boat_propulsion_type=1"
    "&bundleDuplicates=1"
    "&lat=49.0707"
    "&lon=-124.0978"
    "&min_boat_length_overall=29"
    "&search_distance=180"
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

# Canadian Craigslist subdomains -> CAD, everything else -> USD.
# This is a convention, not always correct, but a safe default for PNW.
CAD_SUBDOMAINS = {
    "vancouver",
    "victoria",
    "nanaimo",
    "comoxvalley",
    "abbotsford",
    "sunshine",
    "kamloops",
    "kelowna",
    "whistler",
}


@dataclass
class Listing:
    post_id: str
    title: str
    price_raw: str
    price_numeric: float | None
    currency: str
    location: str
    url: str


def fetch_search_page(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    with httpx.Client(follow_redirects=True, timeout=30.0, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def infer_currency(url: str) -> str:
    match = re.match(r"https?://([^.]+)\.craigslist\.org", url)
    if not match:
        return "USD"
    return "CAD" if match.group(1) in CAD_SUBDOMAINS else "USD"


def extract_post_id(url: str) -> str | None:
    # Craigslist post URLs end with /{10_digit_id}.html
    match = re.search(r"/(\d{10})\.html", url)
    return match.group(1) if match else None


def parse_price(price_str: str) -> float | None:
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", price_str)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def parse_listings(html: str) -> list[Listing]:
    """Parse Craigslist search results.

    Craigslist's static search page uses <li class="cl-static-search-result">
    with an anchor containing title/price/location children. The dynamic
    gallery view uses different markup but the static fallback works for
    bots that don't run JS (which is us).
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    # Primary selector: the static search result li items.
    items = soup.select("li.cl-static-search-result")

    # Fallback: older/alternate markup.
    if not items:
        items = soup.select("li.result-row")

    for item in items:
        link = item.find("a", href=True)
        if not link:
            continue
        url = link["href"]
        if not isinstance(url, str):
            continue

        post_id = extract_post_id(url)
        if not post_id or post_id in seen_ids:
            continue
        seen_ids.add(post_id)

        title_elem = item.select_one(".title") or link
        price_elem = item.select_one(".price")
        location_elem = item.select_one(".location")

        title = title_elem.get_text(strip=True) if title_elem else ""
        price_raw = price_elem.get_text(strip=True) if price_elem else ""
        location = location_elem.get_text(strip=True) if location_elem else ""

        listings.append(
            Listing(
                post_id=post_id,
                title=title,
                price_raw=price_raw,
                price_numeric=parse_price(price_raw),
                currency=infer_currency(url),
                location=location,
                url=url,
            )
        )

    return listings


def main() -> int:
    try:
        html = fetch_search_page(SEARCH_URL)
    except httpx.HTTPError as e:
        print(f"FETCH_FAILED: {e}", file=sys.stderr)
        return 1

    listings = parse_listings(html)

    if not listings:
        print(
            "PARSE_ZERO: fetched page but found no listings. "
            "Craigslist markup may have changed.",
            file=sys.stderr,
        )
        # Still write the empty snapshot so the routine can see what happened.

    today = datetime.now(timezone.utc).date().isoformat()
    snapshot = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "search_url": SEARCH_URL,
        "listing_count": len(listings),
        "listings": [asdict(listing) for listing in listings],
    }

    snapshots_dir = Path(__file__).resolve().parent.parent / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    snapshot_path = snapshots_dir / f"{today}.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n")

    print(f"Wrote {len(listings)} listings to {snapshot_path}")
    return 0 if listings else 2


if __name__ == "__main__":
    raise SystemExit(main())
