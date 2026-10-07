"""
NOTE: retained from an earlier parallel session for reference.
The canonical, tested pipeline for this project lives in `pipeline/`
(see pipeline/run.py and pipeline/parse_corrections.py). Prefer those.
"""
#!/usr/bin/env python3
"""
NFL Stat Corrections Fetcher
Polls the NFL.com stat corrections page and detects new corrections.

Usage:
    python fetch_corrections.py [--notify]

This script is designed to be run on a schedule (e.g., daily cron job)
during the NFL season to detect new stat corrections.
"""

import json
import hashlib
import os
import sys
import re
from datetime import datetime
from pathlib import Path

# Optional imports (graceful degradation)
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("Warning: 'requests' and 'beautifulsoup4' not installed.")
    print("Install with: pip install requests beautifulsoup4")


# Configuration
NFL_CORRECTIONS_URL = "https://fantasy.nfl.com/research/statcorrections"
ESPN_CORRECTIONS_URL = "https://fantasy.espn.com/football/statcorrections"
DATA_DIR = Path(__file__).parent.parent / "data"
STATE_FILE = DATA_DIR / "last_check_state.json"

# Market-relevant keywords that indicate significant corrections
MARKET_RELEVANT_KEYWORDS = [
    "touchdown", "TD", "fumble", "sack", "interception", "safety",
    "field goal", "extra point", "two-point", "passing yards",
    "rushing yards", "receiving yards", "reception", "catch",
    "yards changed", "scored", "points"
]

# Scoring-related stat categories
SCORING_STATS = [
    "passing_td", "rushing_td", "receiving_td", "fumble", "fumble_lost",
    "interception", "sack", "safety", "blocked_kick", "defensive_td",
    "passing_yards", "rushing_yards", "receiving_yards", "receptions"
]


def load_state():
    """Load the last known state of corrections."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_hash": "", "last_check": "", "known_corrections": []}


def save_state(state):
    """Save the current state."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def fetch_nfl_corrections():
    """Fetch corrections from NFL.com stat corrections page."""
    if not HAS_REQUESTS:
        print("Cannot fetch: install requests and beautifulsoup4")
        return []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; NFLScoringDiscrepBot/1.0)'
        }
        response = requests.get(NFL_CORRECTIONS_URL, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        corrections = []

        # Parse the corrections table
        # NFL.com uses a table with Player, Date, Stat, and Points columns
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    correction = {
                        'player': cells[0].get_text(strip=True),
                        'date': cells[1].get_text(strip=True),
                        'stat_change': cells[2].get_text(strip=True),
                        'points': cells[3].get_text(strip=True) if len(cells) > 3 else '0.00'
                    }
                    corrections.append(correction)

        return corrections

    except Exception as e:
        print(f"Error fetching NFL corrections: {e}")
        return []


def is_market_relevant(correction):
    """Determine if a correction could affect a market-relevant outcome."""
    stat_change = correction.get('stat_change', '').lower()

    for keyword in MARKET_RELEVANT_KEYWORDS:
        if keyword.lower() in stat_change:
            return True

    return False


def detect_new_corrections(current, known):
    """Detect corrections that are new since the last check."""
    known_set = set()
    for c in known:
        key = f"{c.get('player', '')}|{c.get('date', '')}|{c.get('stat_change', '')}"
        known_set.add(key)

    new_corrections = []
    for c in current:
        key = f"{c.get('player', '')}|{c.get('date', '')}|{c.get('stat_change', '')}"
        if key not in known_set:
            new_corrections.append(c)

    return new_corrections


def format_alert(correction):
    """Format a correction as a human-readable alert."""
    player = correction.get('player', 'Unknown')
    date = correction.get('date', 'Unknown')
    change = correction.get('stat_change', 'Unknown change')
    points = correction.get('points', '0.00')
    relevant = is_market_relevant(correction)

    alert = f"""
{'🚨 MARKET-RELEVANT CORRECTION' if relevant else 'ℹ️ Stat Correction'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Player: {player}
Date: {date}
Change: {change}
Fantasy Points Impact: {points}
Market Relevant: {'YES ⚠️' if relevant else 'No'}
Source: {NFL_CORRECTIONS_URL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return alert


def run_check(notify=False):
    """Run a correction check and report results."""
    print(f"\n{'='*60}")
    print(f"NFL Stat Corrections Check — {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    state = load_state()
    corrections = fetch_nfl_corrections()

    if not corrections:
        print("No corrections fetched (or unable to fetch).")
        print(f"Source: {NFL_CORRECTIONS_URL}")
        print("\nNote: NFL.com may not have corrections this week, or the page structure may have changed.")
        return

    print(f"Fetched {len(corrections)} corrections from NFL.com")

    # Detect new corrections
    new = detect_new_corrections(corrections, state.get('known_corrections', []))

    if new:
        print(f"\n🆕 Found {len(new)} NEW correction(s):\n")
        market_relevant = [c for c in new if is_market_relevant(c)]

        if market_relevant:
            print(f"⚠️  {len(market_relevant)} are MARKET-RELEVANT:\n")
            for c in market_relevant:
                print(format_alert(c))
        else:
            print("None are market-relevant (mostly defensive tackle corrections).\n")

        for c in new:
            if not is_market_relevant(c):
                print(f"  - {c.get('player', 'Unknown')}: {c.get('stat_change', 'Unknown')}")
    else:
        print("\n✅ No new corrections since last check.")

    # Update state
    state['last_check'] = datetime.now().isoformat()
    state['known_corrections'] = corrections
    current_hash = hashlib.md5(json.dumps(corrections).encode()).hexdigest()
    state['last_hash'] = current_hash
    save_state(state)

    print(f"\nState saved. Next check will compare against {len(corrections)} known corrections.")


if __name__ == '__main__':
    notify = '--notify' in sys.argv
    run_check(notify=notify)
