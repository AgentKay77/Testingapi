"""
test_faceit_api.py — Test FACEIT API endpoints for demo downloading.

Tests:
1. API key authentication
2. Fetching match details
3. Checking demo URL availability
4. Downloading a demo file (small partial download to verify access)
5. Fetching match stats

Usage:
    # Set your API key first:
    export FACEIT_API_KEY="your-key-here"

    # Run with a match ID or URL:
    python test_faceit_api.py <match_id_or_url>

    # Run with a specific player's recent matches:
    python test_faceit_api.py --player <nickname>
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required. Install with: pip install requests")
    sys.exit(1)

FACEIT_API_BASE = "https://open.faceit.com/data/v4"

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def passed(msg):
    print(f"  {GREEN}PASS{RESET} {msg}")


def failed(msg):
    print(f"  {RED}FAIL{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}WARN{RESET} {msg}")


def info(msg):
    print(f"  {CYAN}INFO{RESET} {msg}")


def get_api_key() -> str:
    """Load FACEIT API key from env or config file."""
    key = os.environ.get("FACEIT_API_KEY")
    if key:
        return key

    config_path = Path.home() / ".demo2yt" / "faceit_api_key"
    if config_path.exists():
        return config_path.read_text().strip()

    print(f"{RED}ERROR: No FACEIT API key found.{RESET}")
    print("Set FACEIT_API_KEY env var or create ~/.demo2yt/faceit_api_key")
    sys.exit(1)


def extract_match_id(match_input: str) -> str:
    """Extract match ID from a FACEIT URL or return as-is."""
    patterns = [
        r"faceit\.com/\w+/cs2/room/([a-zA-Z0-9-]+)",
        r"faceit\.com/\w+/csgo/room/([a-zA-Z0-9-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, match_input)
        if match:
            return match.group(1)
    return match_input.strip()


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_auth(api_key: str) -> bool:
    """Test 1: Verify API key works by hitting a simple endpoint."""
    print(f"\n{BOLD}[Test 1] API Authentication{RESET}")
    try:
        # Use the games endpoint as a lightweight auth check
        resp = requests.get(
            f"{FACEIT_API_BASE}/games",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        if resp.status_code == 200:
            passed(f"Authenticated successfully (HTTP {resp.status_code})")
            return True
        elif resp.status_code == 401:
            failed(f"Invalid API key (HTTP 401)")
            return False
        else:
            failed(f"Unexpected status: HTTP {resp.status_code}")
            info(f"Response: {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        failed(f"Request error: {e}")
        return False


def test_player_lookup(api_key: str, nickname: str) -> str | None:
    """Look up a player by nickname and return their player_id."""
    print(f"\n{BOLD}[Test] Player Lookup: {nickname}{RESET}")
    try:
        resp = requests.get(
            f"{FACEIT_API_BASE}/players",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"nickname": nickname, "game": "cs2"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            player_id = data.get("player_id")
            elo = data.get("games", {}).get("cs2", {}).get("faceit_elo", "N/A")
            level = data.get("games", {}).get("cs2", {}).get("skill_level", "N/A")
            passed(f"Found player: {nickname} (Level {level}, ELO {elo})")
            info(f"Player ID: {player_id}")
            return player_id
        elif resp.status_code == 404:
            failed(f"Player '{nickname}' not found")
            return None
        else:
            failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.RequestException as e:
        failed(f"Request error: {e}")
        return None


def test_player_matches(api_key: str, player_id: str) -> str | None:
    """Get a player's most recent CS2 match and return the match_id."""
    print(f"\n{BOLD}[Test] Recent Matches{RESET}")
    try:
        resp = requests.get(
            f"{FACEIT_API_BASE}/players/{player_id}/history",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"game": "cs2", "offset": 0, "limit": 5},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if not items:
                warn("No recent CS2 matches found for this player")
                return None
            passed(f"Found {len(items)} recent match(es)")
            for i, m in enumerate(items):
                match_id = m.get("match_id", "?")
                status = m.get("status", "?")
                started = m.get("started_at", 0)
                ts = time.strftime("%Y-%m-%d %H:%M", time.gmtime(started)) if started else "?"
                info(f"  [{i+1}] {match_id[:16]}... | status={status} | {ts}")
            # Return the most recent finished match
            for m in items:
                if m.get("status") == "finished":
                    return m["match_id"]
            return items[0].get("match_id")
        else:
            failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.RequestException as e:
        failed(f"Request error: {e}")
        return None


def test_match_details(api_key: str, match_id: str) -> dict | None:
    """Test 2: Fetch match details and check for demo URL."""
    print(f"\n{BOLD}[Test 2] Match Details{RESET}")
    info(f"Match ID: {match_id}")
    try:
        resp = requests.get(
            f"{FACEIT_API_BASE}/matches/{match_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            passed(f"Fetched match details (HTTP 200)")

            # Display key match info
            status = data.get("status", "unknown")
            game = data.get("game", "unknown")
            competition = data.get("competition_name", "unknown")
            info(f"Game: {game} | Status: {status} | Competition: {competition}")

            # Check teams
            teams = data.get("teams", {})
            for side in ["faction1", "faction2"]:
                team = teams.get(side, {})
                name = team.get("name", "?")
                roster = [p.get("nickname", "?") for p in team.get("roster", [])]
                info(f"  {side}: {name} \u2014 {', '.join(roster)}")

            # Map info
            try:
                voting = data.get("voting", {})
                map_pick = voting.get("map", {}).get("pick", [])
                if map_pick:
                    info(f"Map: {map_pick[0]}")
            except (KeyError, IndexError):
                pass

            return data
        elif resp.status_code == 404:
            failed(f"Match not found (HTTP 404)")
            return None
        else:
            failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.RequestException as e:
        failed(f"Request error: {e}")
        return None


def test_demo_url(match_data: dict) -> str | None:
    """Test 3: Check if demo URL is present and accessible."""
    print(f"\n{BOLD}[Test 3] Demo URL Availability{RESET}")

    demo_url = match_data.get("demo_url")
    if not demo_url:
        failed("No 'demo_url' field in match data")
        info("Demo may not be available yet (takes a few minutes after match ends)")
        return None

    # Handle list of URLs
    if isinstance(demo_url, list):
        if len(demo_url) == 0:
            failed("demo_url is an empty list")
            return None
        info(f"demo_url is a list with {len(demo_url)} URL(s)")
        demo_url = demo_url[0]

    passed(f"Demo URL found")
    info(f"URL: {demo_url[:120]}...")

    # Detect compression format
    if demo_url.endswith(".zst"):
        info("Format: Zstandard (.dem.zst)")
    elif demo_url.endswith(".gz"):
        info("Format: Gzip (.dem.gz)")
    else:
        info("Format: Unknown (will try auto-detect)")

    return demo_url


def test_demo_download(demo_url: str) -> bool:
    """Test 4: Verify demo is downloadable (partial download)."""
    print(f"\n{BOLD}[Test 4] Demo Download Test{RESET}")
    try:
        # HEAD request first to check availability and size
        info("Sending HEAD request to check demo availability...")
        head_resp = requests.head(demo_url, timeout=30, allow_redirects=True)
        if head_resp.status_code == 200:
            content_length = head_resp.headers.get("content-length")
            content_type = head_resp.headers.get("content-type", "unknown")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                passed(f"Demo is accessible (HEAD 200)")
                info(f"File size: {size_mb:.1f} MB")
                info(f"Content-Type: {content_type}")
            else:
                passed(f"Demo is accessible (HEAD 200, size unknown)")
        else:
            warn(f"HEAD returned HTTP {head_resp.status_code} (some servers don't support HEAD)")

        # Download first 1 MB to verify actual download works
        info("Downloading first 1 MB to verify download access...")
        resp = requests.get(
            demo_url,
            headers={"Range": "bytes=0-1048575"},
            stream=True,
            timeout=30,
        )

        if resp.status_code in (200, 206):
            chunk = resp.content
            size_kb = len(chunk) / 1024
            passed(f"Downloaded {size_kb:.0f} KB successfully (HTTP {resp.status_code})")

            # Check if it looks like a valid compressed demo
            if chunk[:4] == b"\x28\xb5\x2f\xfd":
                info("File header: Valid Zstandard compressed data")
            elif chunk[:2] == b"\x1f\x8b":
                info("File header: Valid Gzip compressed data")
            elif chunk[:8] == b"HL2DEMO\x00":
                info("File header: Uncompressed Source demo file")
            else:
                info(f"File header bytes: {chunk[:8].hex()}")
            return True
        elif resp.status_code == 403:
            failed("Download forbidden (HTTP 403) \u2014 demo may have expired")
            return False
        elif resp.status_code == 404:
            failed("Demo file not found (HTTP 404)")
            return False
        else:
            failed(f"Download failed: HTTP {resp.status_code}")
            return False

    except requests.RequestException as e:
        failed(f"Download error: {e}")
        return False


def test_match_stats(api_key: str, match_id: str) -> bool:
    """Test 5: Fetch match statistics."""
    print(f"\n{BOLD}[Test 5] Match Statistics{RESET}")
    try:
        resp = requests.get(
            f"{FACEIT_API_BASE}/matches/{match_id}/stats",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            rounds = data.get("rounds", [])
            if rounds:
                r = rounds[0]
                round_stats = r.get("round_stats", {})
                map_name = round_stats.get("Map", "?")
                score = round_stats.get("Score", "?")
                passed(f"Stats available \u2014 Map: {map_name}, Score: {score}")

                # Show top player stats
                teams = r.get("teams", [])
                for team in teams:
                    team_name = team.get("team_stats", {}).get("Team", "?")
                    players = team.get("players", [])
                    for p in players[:2]:
                        ps = p.get("player_stats", {})
                        nick = p.get("nickname", "?")
                        kills = ps.get("Kills", "?")
                        deaths = ps.get("Deaths", "?")
                        kd = ps.get("K/D Ratio", "?")
                        info(f"  [{team_name}] {nick}: {kills}K/{deaths}D (K/D: {kd})")
            else:
                warn("Stats response has no rounds data")
            return True
        elif resp.status_code == 404:
            warn("Stats not available for this match (HTTP 404)")
            return False
        else:
            failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        failed(f"Request error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Test FACEIT API demo download capabilities"
    )
    parser.add_argument(
        "match",
        nargs="?",
        help="Match ID or FACEIT match URL (optional if --player is used)",
    )
    parser.add_argument(
        "--player",
        help="FACEIT nickname \u2014 will look up their most recent match",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save API responses to JSON files",
    )
    args = parser.parse_args()

    if not args.match and not args.player:
        parser.error("Provide a match ID/URL or use --player <nickname>")

    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  FACEIT API Demo Download Tester{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    api_key = get_api_key()
    results = {}

    # Test 1: Auth
    auth_ok = test_auth(api_key)
    results["auth"] = auth_ok
    if not auth_ok:
        print(f"\n{RED}Authentication failed \u2014 cannot proceed.{RESET}")
        sys.exit(1)

    # Resolve match ID
    match_id = None
    if args.player:
        player_id = test_player_lookup(api_key, args.player)
        if player_id:
            match_id = test_player_matches(api_key, player_id)
        if not match_id:
            print(f"\n{RED}Could not find a match for player '{args.player}'.{RESET}")
            sys.exit(1)
    else:
        match_id = extract_match_id(args.match)

    # Test 2: Match details
    match_data = test_match_details(api_key, match_id)
    results["match_details"] = match_data is not None

    if not match_data:
        print(f"\n{RED}Could not fetch match details \u2014 cannot proceed.{RESET}")
        sys.exit(1)

    # Test 3: Demo URL
    demo_url = test_demo_url(match_data)
    results["demo_url"] = demo_url is not None

    # Test 4: Demo download (only if URL exists)
    if demo_url:
        results["demo_download"] = test_demo_download(demo_url)
    else:
        results["demo_download"] = False

    # Test 5: Match stats
    results["match_stats"] = test_match_stats(api_key, match_id)

    # Save JSON if requested
    if args.save_json:
        out_dir = Path("test_output")
        out_dir.mkdir(exist_ok=True)
        with open(out_dir / f"{match_id}_details.json", "w") as f:
            json.dump(match_data, f, indent=2)
        info(f"Saved match details to test_output/{match_id}_details.json")

    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Results Summary{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    total = len(results)
    passed_count = sum(1 for v in results.values() if v)
    for test_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {test_name}")

    print(f"\n  {passed_count}/{total} tests passed")

    if results.get("demo_download"):
        print(f"\n  {GREEN}{BOLD}Demo download is working! Your API key can download FACEIT demos.{RESET}")
    elif results.get("demo_url"):
        print(f"\n  {YELLOW}Demo URL was found but download failed. Check URL expiry or network.{RESET}")
    else:
        print(f"\n  {RED}No demo URL available for this match.{RESET}")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
