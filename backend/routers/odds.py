from fastapi import APIRouter, HTTPException
import httpx
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_BASE = "https://api.the-odds-api.com/v4"

SPORTS = {
    "mlb": "baseball_mlb",
    "nba": "basketball_nba",
    "nhl": "icehockey_nhl",
    "ncaa_basketball": "basketball_ncaab",
    "ncaa_football": "americanfootball_ncaaf",
    "nfl": "americanfootball_nfl",
}

async def fetch_odds(sport_key: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{ODDS_BASE}/sports/{sport_key}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        # Persist to disk so data survives session resets
        cache_file = DATA_DIR / f"odds_{sport_key}.json"
        cache_file.write_text(json.dumps(data, indent=2))
        return data

@router.get("/live/{sport}")
async def get_live_odds(sport: str):
    if sport not in SPORTS:
        raise HTTPException(400, f"Sport must be one of: {list(SPORTS.keys())}")
    return await fetch_odds(SPORTS[sport])

@router.get("/all")
async def get_all_odds():
    results = {}
    for name, key in SPORTS.items():
        try:
            results[name] = await fetch_odds(key)
        except Exception as e:
            results[name] = {"error": str(e)}
    return results

@router.get("/cached/{sport}")
def get_cached_odds(sport: str):
    """Return last saved odds without burning an API call."""
    if sport not in SPORTS:
        raise HTTPException(400, f"Sport must be one of: {list(SPORTS.keys())}")
    cache_file = DATA_DIR / f"odds_{SPORTS[sport]}.json"
    if not cache_file.exists():
        raise HTTPException(404, "No cached data yet. Call /live/{sport} first.")
    return json.loads(cache_file.read_text())
