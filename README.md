# FACEIT API Demo Download Tester

Tests whether your FACEIT API key can authenticate, fetch match details, and download CS2 demo files.

## Setup

```bash
pip install -r requirements.txt
export FACEIT_API_KEY="your-api-key-here"
```

## Usage

```bash
# Test with a specific match ID
python test_faceit_api.py 1-abc12345-def6-7890-abcd-ef1234567890

# Test with a FACEIT match URL
python test_faceit_api.py "https://www.faceit.com/en/cs2/room/1-abc12345-..."

# Test using a player's most recent match
python test_faceit_api.py --player YourNickname

# Save API responses to JSON files
python test_faceit_api.py --player YourNickname --save-json
```

## Tests Run

1. **API Authentication** — Verifies your API key is valid
2. **Match Details** — Fetches full match data from FACEIT API v4
3. **Demo URL Availability** — Checks if the demo download URL exists
4. **Demo Download** — Downloads first 1 MB to verify access and checks file format
5. **Match Statistics** — Fetches player stats for the match
