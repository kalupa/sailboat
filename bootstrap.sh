#!/usr/bin/env bash
# Bootstrap the boat-search repo.
#
# What this does:
# 1. Sanity check you're in the repo root
# 2. Run `uv sync` to install dependencies
# 3. Run an initial scrape to verify everything works
# 4. Stage the files (but not commit; you review first)
#
# Usage:
#   cd boat-search
#   ./bootstrap.sh

set -euo pipefail

if [ ! -f "pyproject.toml" ] || [ ! -f "scripts/parse_craigslist.py" ]; then
    echo "error: run this from the boat-search repo root" >&2
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "error: uv is not installed. See https://docs.astral.sh/uv/" >&2
    exit 1
fi

echo "==> Installing Python dependencies with uv"
uv sync

echo "==> Running initial Craigslist scrape (may fail; that's OK)"
echo "    Note: Craigslist blocks most cloud IPs. This script works from"
echo "    residential IPs (your Mac) but not from cloud infrastructure."
echo "    The routine uses Claude's web_fetch tool instead, which works."
echo
if uv run scripts/parse_craigslist.py; then
    echo "==> Scrape succeeded"
else
    exit_code=$?
    if [ $exit_code -eq 2 ]; then
        echo "==> Scrape returned zero listings (snapshot written, parsing may need attention)"
    elif [ $exit_code -eq 1 ]; then
        echo "==> Scrape failed — likely a 403 from Craigslist"
        echo "    This is expected if you're on a VPN or cloud network."
        echo "    The routine will work regardless (uses web_fetch)."
    else
        echo "error: scrape failed with exit code $exit_code" >&2
        exit $exit_code
    fi
fi

echo
echo "==> Snapshot files:"
ls -la snapshots/

echo
echo "Next steps:"
echo "  1. Review the snapshot JSON to confirm parsing looks correct:"
echo "     cat snapshots/\$(ls snapshots/ | tail -1)"
echo
echo "  2. If scrape looked good, commit and push to GitHub:"
echo "     git init"
echo "     git add ."
echo "     git commit -m 'Initial boat-search setup'"
echo "     git branch -M main"
echo "     git remote add origin git@github.com:kalupa/boat-search.git"
echo "     git push -u origin main"
echo
echo "  3. Create the routine at https://claude.ai/code/routines"
echo "     using the prompt in ROUTINE_PROMPT.md"
