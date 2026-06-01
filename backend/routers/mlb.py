from fastapi import APIRouter
import asyncio
import httpx
import json
from pathlib import Path

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

MLB_BASE = "https://statsapi.mlb.com/api/v1"

async def get_json(url: str, params: dict = None):
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

@router.get("/schedule")
async def get_schedule():
    data = await get_json(f"{MLB_BASE}/schedule", {"sportId": 1, "hydrate": "probablePitcher"})
    (DATA_DIR / "mlb_schedule.json").write_text(json.dumps(data, indent=2))
    return data

@router.get("/pitcher/{pitcher_id}/stats")
async def get_pitcher_stats(pitcher_id: int):
    data = await get_json(
        f"{MLB_BASE}/people/{pitcher_id}/stats",
        {"stats": "season,career", "group": "pitching"}
    )
    return data

@router.get("/batter/{batter_id}/stats")
async def get_batter_stats(batter_id: int):
    data = await get_json(
        f"{MLB_BASE}/people/{batter_id}/stats",
        {"stats": "season,career", "group": "hitting"}
    )
    return data

@router.get("/matchup")
async def analyze_matchup(batter_id: int, pitcher_id: int):
    """
    Core edge analysis: score a batter vs pitcher matchup.
    Returns a 0-100 edge score. 70+ = strong lean, 85+ = high confidence.
    """
    batter_data, pitcher_data = await asyncio.gather(
        get_json(f"{MLB_BASE}/people/{batter_id}/stats", {"stats": "season", "group": "hitting"}),
        get_json(f"{MLB_BASE}/people/{pitcher_id}/stats", {"stats": "season", "group": "pitching"}),
    )

    batter_stats = _extract_hitting(batter_data)
    pitcher_stats = _extract_pitching(pitcher_data)

    edge_score = _calculate_edge(batter_stats, pitcher_stats)

    result = {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "batter_avg": batter_stats.get("avg"),
        "pitcher_era": pitcher_stats.get("era"),
        "pitcher_whip": pitcher_stats.get("whip"),
        "edge_score": edge_score,
        "verdict": _verdict(edge_score),
    }

    # Save matchup analysis
    history_file = DATA_DIR / "matchup_history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    history.append(result)
    history_file.write_text(json.dumps(history, indent=2))

    return result

def _extract_hitting(data: dict) -> dict:
    try:
        splits = data["stats"][0]["splits"]
        if splits:
            s = splits[0]["stat"]
            return {
                "avg": float(s.get("avg", 0)),
                "obp": float(s.get("obp", 0)),
                "slg": float(s.get("slg", 0)),
                "ops": float(s.get("ops", 0)),
                "strikeoutRate": float(s.get("strikeOuts", 0)) / max(float(s.get("atBats", 1)), 1),
            }
    except Exception:
        pass
    return {}

def _extract_pitching(data: dict) -> dict:
    try:
        splits = data["stats"][0]["splits"]
        if splits:
            s = splits[0]["stat"]
            return {
                "era": float(s.get("era", 99)),
                "whip": float(s.get("whip", 99)),
                "strikeoutsPer9": float(s.get("strikeoutsPer9Inn", 0)),
                "walksPer9": float(s.get("walksPer9Inn", 99)),
            }
    except Exception:
        pass
    return {"era": 99, "whip": 99}

def _calculate_edge(batter: dict, pitcher: dict) -> int:
    score = 50  # neutral baseline

    era = pitcher.get("era", 4.5)
    if era >= 6.0:
        score += 20
    elif era >= 5.0:
        score += 12
    elif era >= 4.5:
        score += 5
    elif era <= 2.5:
        score -= 15
    elif era <= 3.5:
        score -= 8

    whip = pitcher.get("whip", 1.3)
    if whip >= 1.6:
        score += 10
    elif whip >= 1.4:
        score += 5
    elif whip <= 1.0:
        score -= 10

    avg = batter.get("avg", .250)
    if avg >= .300:
        score += 10
    elif avg >= .275:
        score += 5
    elif avg <= .220:
        score -= 10

    ops = batter.get("ops", .720)
    if ops >= .900:
        score += 8
    elif ops >= .800:
        score += 4
    elif ops <= .650:
        score -= 8

    return max(0, min(100, score))

def _verdict(score: int) -> str:
    if score >= 85:
        return "STRONG EDGE — high confidence bet"
    elif score >= 70:
        return "LEAN — good value, monitor lineup"
    elif score >= 55:
        return "SLIGHT EDGE — situational"
    elif score >= 45:
        return "NEUTRAL — no clear edge"
    else:
        return "FADE — batter disadvantaged"
