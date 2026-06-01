# NBA Halftime edge detector
# Based on Haralabos Voulgaris' documented NBA inefficiency:
# 2H totals are consistently underpriced vs actual 2H scoring rates

import httpx
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Historical NBA: 2H scores ~51.5% of full game, with variance by team pace
HISTORICAL_2H_RATIO = 0.515
HIGH_PACE_RATIO = 0.520  # Fast-paced teams (top quartile pace)
LOW_PACE_RATIO = 0.510   # Slow-paced teams


def halftime_edge(full_game_total: float, first_half_book_total: float,
                   is_high_pace: bool = False) -> dict:
    """
    Detect edge when 2H total is mispriced vs historical averages.

    full_game_total: the game total (e.g., 224.5)
    first_half_book_total: the 1H total the book is offering (e.g., 112)
    is_high_pace: whether both teams are top-quartile pace
    """
    ratio = HIGH_PACE_RATIO if is_high_pace else HISTORICAL_2H_RATIO

    implied_2h = full_game_total - first_half_book_total
    fair_2h = full_game_total * ratio
    edge_points = fair_2h - implied_2h

    ev_estimate = edge_points * 3.2  # ~3.2% EV per point of edge in NBA totals

    return {
        "full_game_total": full_game_total,
        "book_1h_total": first_half_book_total,
        "implied_2h_total": round(implied_2h, 1),
        "fair_2h_estimate": round(fair_2h, 1),
        "edge_points": round(edge_points, 2),
        "ev_estimate_pct": round(ev_estimate, 2),
        "bet": "OVER 2H" if edge_points > 0.5 else "UNDER 2H" if edge_points < -0.5 else "NO EDGE",
        "confidence": "HIGH" if abs(edge_points) > 1.5 else "MEDIUM" if abs(edge_points) > 0.5 else "LOW",
        "voulgaris_note": "2H totals are softest market in NBA — books reprice slowly after halftime.",
    }


def analyze_nba_game_total(game_total: float, h1_total: float,
                            team1_pace: float = None, team2_pace: float = None) -> dict:
    """Full analysis with pace adjustment."""
    # NBA average pace ~100 possessions/game. Top quartile = 102+
    high_pace = False
    if team1_pace and team2_pace:
        avg_pace = (team1_pace + team2_pace) / 2
        high_pace = avg_pace >= 102.0

    result = halftime_edge(game_total, h1_total, high_pace)
    result["pace_adjusted"] = high_pace
    return result


def log_halftime_result(game_id: str, bet: str, result_won: bool, edge_points: float):
    """Track 2H total bets to validate edge over time."""
    history_file = DATA_DIR / "nba_halftime_history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    history.append({
        "game_id": game_id, "bet": bet, "won": result_won, "edge_points": edge_points
    })
    history_file.write_text(json.dumps(history, indent=2))
