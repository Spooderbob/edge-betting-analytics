import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _american_to_implied(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def find_best_odds(game: dict, side_name: str) -> dict:
    best_book = None
    best_odds = None
    worst_book = None
    worst_odds = None
    all_odds = {}
    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                if outcome["name"] == side_name:
                    odds = outcome["price"]
                    all_odds[book["title"]] = odds
                    if best_odds is None or odds > best_odds:
                        best_odds = odds
                        best_book = book["title"]
                    if worst_odds is None or odds < worst_odds:
                        worst_odds = odds
                        worst_book = book["title"]
    savings = None
    if best_odds and worst_odds:
        savings = round(_american_to_implied(worst_odds) - _american_to_implied(best_odds), 4)
    return {
        "side": side_name,
        "best_book": best_book,
        "best_odds": best_odds,
        "worst_book": worst_book,
        "worst_odds": worst_odds,
        "all_odds": all_odds,
        "prob_savings": savings,
    }


def arbitrage_check(home_best_odds: int, away_best_odds: int) -> dict:
    home_prob = _american_to_implied(home_best_odds)
    away_prob = _american_to_implied(away_best_odds)
    total = home_prob + away_prob
    arb_exists = total < 1.0
    return {
        "arb_exists": arb_exists,
        "total_implied": round(total, 4),
        "profit_pct": round((1 - total) * 100, 2) if arb_exists else 0,
    }


def arbitrage_stakes(home_odds: int, away_odds: int, total_stake: float) -> dict:
    home_dec = (home_odds / 100 + 1) if home_odds > 0 else (100 / abs(home_odds) + 1)
    away_dec = (away_odds / 100 + 1) if away_odds > 0 else (100 / abs(away_odds) + 1)
    home_stake = total_stake * away_dec / (home_dec + away_dec)
    away_stake = total_stake - home_stake
    home_payout = home_stake * home_dec
    profit = home_payout - total_stake
    return {
        "home_stake": round(home_stake, 2),
        "away_stake": round(away_stake, 2),
        "guaranteed_payout": round(home_payout, 2),
        "guaranteed_profit": round(profit, 2),
        "roi_pct": round(profit / total_stake * 100, 2),
    }


def scan_for_best_odds(sport_key: str) -> list:
    cache_file = DATA_DIR / f"odds_{sport_key}.json"
    if not cache_file.exists():
        return []
    games = json.loads(cache_file.read_text())
    results = []
    for game in games:
        home = find_best_odds(game, game.get("home_team", ""))
        away = find_best_odds(game, game.get("away_team", ""))
        arb = {}
        if home["best_odds"] and away["best_odds"]:
            arb = arbitrage_check(home["best_odds"], away["best_odds"])
        results.append({
            "game": f"{game.get('home_team')} vs {game.get('away_team')}",
            "commence": game.get("commence_time"),
            "home": home,
            "away": away,
            "arbitrage": arb,
        })
    return results
