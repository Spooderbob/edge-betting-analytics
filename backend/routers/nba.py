from fastapi import APIRouter
import httpx
import json
from pathlib import Path

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent / "data"

NBA_BASE = "https://stats.nba.com/stats"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
}

@router.get("/player/{player_id}/stats")
async def get_player_stats(player_id: int, season: str = "2024-25"):
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(
            f"{NBA_BASE}/playercareerstats",
            params={"PlayerID": player_id, "PerMode": "PerGame"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        (DATA_DIR / f"nba_player_{player_id}.json").write_text(json.dumps(data, indent=2))
        return data

@router.get("/game-logs")
async def get_recent_game_logs(player_id: int, season: str = "2024-25"):
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(
            f"{NBA_BASE}/playergamelog",
            params={"PlayerID": player_id, "Season": season, "SeasonType": "Regular Season"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()
