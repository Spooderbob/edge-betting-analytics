import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def american_to_prob(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def prob_to_american(prob: float) -> int:
    if prob >= 0.5:
        return round(-prob / (1 - prob) * 100)
    return round((1 - prob) / prob * 100)


def remove_vig(home_odds: int, away_odds: int) -> dict:
    home_implied = american_to_prob(home_odds)
    away_implied = american_to_prob(away_odds)
    total = home_implied + away_implied
    return {
        "home_true_prob": round(home_implied / total, 4),
        "away_true_prob": round(away_implied / total, 4),
        "vig_pct": round((total - 1) * 100, 2),
    }


def calculate_ev(our_prob: float, american_odds: int) -> float:
    if american_odds > 0:
        win_amount = american_odds / 100
    else:
        win_amount = 100 / abs(american_odds)
    ev = (our_prob * win_amount) - ((1 - our_prob) * 1)
    return round(ev, 4)


def ev_to_human(ev: float) -> str:
    pct = round(ev * 100, 1)
    if pct > 0:
        return f"+{pct}% edge"
    return f"{pct}% edge"


def find_positive_ev_bets(games: list, model_probs: dict) -> list:
    results = []
    for game in games:
        game_id = game.get("id")
        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market["outcomes"]:
                    side = outcome["name"]
                    key = f"{game_id}_{side}"
                    our_prob = model_probs.get(key)
                    if our_prob is None:
                        continue
                    ev = calculate_ev(our_prob, outcome["price"])
                    if ev > 0:
                        results.append({
                            "game": f"{game.get('home_team')} vs {game.get('away_team')}",
                            "bet": side,
                            "book": book["title"],
                            "odds": outcome["price"],
                            "our_prob": our_prob,
                            "implied_prob": round(american_to_prob(outcome["price"]), 4),
                            "ev": ev,
                            "ev_human": ev_to_human(ev),
                        })
    results.sort(key=lambda x: x["ev"], reverse=True)
    return results


def scan_cached_odds_for_ev(sport_key: str, model_probs: dict) -> list:
    cache_file = DATA_DIR / f"odds_{sport_key}.json"
    if not cache_file.exists():
        return []
    games = json.loads(cache_file.read_text())
    return find_positive_ev_bets(games, model_probs)
