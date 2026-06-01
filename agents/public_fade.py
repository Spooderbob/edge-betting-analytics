# Public fade signal detector
# Based on Action Network bet percentage data patterns
# Billy Walters insight: fade public extremes (>70% on one side)

from typing import Optional
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def public_fade_score(ticket_pct: float, handle_pct: float,
                       line_drift_from_open: float) -> dict:
    """
    ticket_pct: % of bets on the public side (0-100)
    handle_pct: % of money on the public side (0-100)
    line_drift_from_open: how many points line moved toward public side (positive = moved toward public)

    Returns fade signal with confidence score.
    """
    score = 0
    reasons = []

    # Strong public lean
    if ticket_pct >= 80:
        score += 40
        reasons.append(f"{ticket_pct}% of tickets on public side (extreme)")
    elif ticket_pct >= 70:
        score += 25
        reasons.append(f"{ticket_pct}% of tickets on public side (strong)")
    elif ticket_pct >= 65:
        score += 10
        reasons.append(f"{ticket_pct}% of tickets on public side (moderate)")

    # Line already moved toward public (public already priced in)
    if line_drift_from_open >= 2.0:
        score += 30
        reasons.append(f"Line moved {line_drift_from_open} pts toward public (fully priced in)")
    elif line_drift_from_open >= 1.0:
        score += 15
        reasons.append(f"Line moved {line_drift_from_open} pts toward public")

    # Sharp money on the other side (handle < tickets = sharps on fade side)
    sharp_gap = ticket_pct - handle_pct
    if sharp_gap >= 20:
        score += 25
        reasons.append(f"Sharp money on fade side (ticket/handle gap: {sharp_gap:.0f}%)")
    elif sharp_gap >= 10:
        score += 10
        reasons.append(f"Some sharp money on fade side (gap: {sharp_gap:.0f}%)")

    return {
        "ticket_pct_public": ticket_pct,
        "handle_pct_public": handle_pct,
        "sharp_gap": round(sharp_gap, 1),
        "line_drift": line_drift_from_open,
        "fade_score": min(score, 100),
        "fade_signal": score >= 50,
        "confidence": "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LOW",
        "reasons": reasons,
        "action": f"Fade the public: bet the other side" if score >= 50 else "No clear fade signal",
    }


def scan_for_fades(games_data: list) -> list:
    """
    Scan a list of games with public data and return fade opportunities.
    games_data: list of dicts with ticket_pct, handle_pct, line_drift, game_name
    """
    fades = []
    for game in games_data:
        result = public_fade_score(
            game.get("ticket_pct", 50),
            game.get("handle_pct", 50),
            game.get("line_drift", 0),
        )
        if result["fade_signal"]:
            result["game"] = game.get("game", "Unknown")
            result["sport"] = game.get("sport", "")
            fades.append(result)

    fades.sort(key=lambda x: x["fade_score"], reverse=True)
    return fades


def log_fade_result(game: str, fade_score: int, won: bool):
    """Track fade bet outcomes to validate the signal over time."""
    history_file = DATA_DIR / "fade_history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    history.append({"game": game, "fade_score": fade_score, "won": won})
    history_file.write_text(json.dumps(history, indent=2))


def fade_performance() -> dict:
    """Win rate by confidence bucket."""
    history_file = DATA_DIR / "fade_history.json"
    if not history_file.exists():
        return {"message": "No fade history yet"}
    history = json.loads(history_file.read_text())
    if not history:
        return {"message": "No fade history yet"}

    buckets = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for entry in history:
        score = entry["fade_score"]
        bucket = "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LOW"
        buckets[bucket].append(entry["won"])

    return {
        bucket: {
            "count": len(results),
            "win_rate": round(sum(results) / len(results) * 100, 1) if results else None
        }
        for bucket, results in buckets.items()
    }
