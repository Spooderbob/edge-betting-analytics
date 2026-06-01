from fastapi import APIRouter
import json
from pathlib import Path

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent / "data"

@router.get("/value-bets/{sport}")
def find_value_bets(sport: str):
    """
    Compare our model's implied probability vs the book's line.
    When our model says 60% but the book prices it at 50% (+100), that's +EV.
    """
    cache_file = DATA_DIR / f"odds_{sport}.json"
    if not cache_file.exists():
        return {"error": "No odds data cached. Fetch live odds first."}

    games = json.loads(cache_file.read_text())
    value_bets = []

    for game in games:
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        american = outcome["price"]
                        implied = american_to_implied(american)
                        # Placeholder: real model probability would come from stats engine
                        # For now flag anything with large implied vs 50% gap as a research target
                        if american >= 150:  # underdog with big payout
                            value_bets.append({
                                "game": f"{game.get('home_team')} vs {game.get('away_team')}",
                                "commence": game.get("commence_time"),
                                "book": bookmaker["title"],
                                "bet": outcome["name"],
                                "line": american,
                                "implied_prob": round(implied, 3),
                                "flag": "BIG UNDERDOG — research matchup",
                            })

    value_bets.sort(key=lambda x: x["line"], reverse=True)
    return {"count": len(value_bets), "bets": value_bets[:20]}

@router.get("/parlay-finder")
def find_correlated_parlays():
    """
    Find same-night games where outcomes may correlate.
    E.g. bad weather games → under; divisional underdogs on revenge spots.
    """
    # Will be expanded with real correlation logic
    return {"message": "Parlay correlation engine — coming next build"}

@router.get("/history")
def get_matchup_history():
    history_file = DATA_DIR / "matchup_history.json"
    if not history_file.exists():
        return []
    return json.loads(history_file.read_text())

def american_to_implied(american: int) -> float:
    if american > 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)
