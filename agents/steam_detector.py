import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
HISTORY_FILE = DATA_DIR / "line_history.json"


def _load() -> list:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []


def _save(data: list):
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def record_line(game_id: str, book: str, odds: int, market: str = "h2h", side: str = "home"):
    entry = {
        "game_id": game_id,
        "book": book,
        "odds": odds,
        "market": market,
        "side": side,
        "timestamp": datetime.utcnow().isoformat(),
    }
    history = _load()
    history.append(entry)
    _save(history)
    return entry


def detect_steam(game_id: str, side: str, time_window_minutes: int = 5,
                 min_books: int = 3, min_move_odds: int = 10) -> dict:
    history = _load()
    cutoff = datetime.utcnow() - timedelta(minutes=time_window_minutes)
    recent = [
        r for r in history
        if r["game_id"] == game_id
        and r["side"] == side
        and datetime.fromisoformat(r["timestamp"]) > cutoff
    ]
    books_moved = set()
    for entry in recent:
        older = [
            r for r in history
            if r["game_id"] == game_id
            and r["book"] == entry["book"]
            and r["side"] == side
            and datetime.fromisoformat(r["timestamp"]) <= cutoff
        ]
        if older:
            baseline = older[-1]["odds"]
            if abs(entry["odds"] - baseline) >= min_move_odds:
                books_moved.add(entry["book"])
    is_steam = len(books_moved) >= min_books
    return {
        "game_id": game_id,
        "side": side,
        "is_steam": is_steam,
        "books_moved": list(books_moved),
        "books_count": len(books_moved),
        "window_minutes": time_window_minutes,
    }


def detect_rlm(game_id: str, public_side: str, bet_pct: float, handle_pct: float) -> dict:
    history = _load()
    game_lines = [r for r in history if r["game_id"] == game_id and r["side"] == public_side]
    if len(game_lines) < 2:
        return {"rlm_detected": False, "reason": "Insufficient line history"}
    open_odds = game_lines[0]["odds"]
    current_odds = game_lines[-1]["odds"]
    line_moved_toward_public = (
        (bet_pct > 50 and current_odds < open_odds) or
        (bet_pct < 50 and current_odds > open_odds)
    )
    handle_gap = abs(handle_pct - bet_pct)
    rlm = not line_moved_toward_public and handle_gap >= 15 and bet_pct > 55
    return {
        "game_id": game_id,
        "public_side": public_side,
        "bet_pct": bet_pct,
        "handle_pct": handle_pct,
        "handle_gap": handle_gap,
        "open_odds": open_odds,
        "current_odds": current_odds,
        "rlm_detected": rlm,
        "sharp_side": "opposite" if rlm else "unclear",
    }


def get_all_signals() -> list:
    history = _load()
    game_ids = set(r["game_id"] for r in history)
    signals = []
    for gid in game_ids:
        for side in ["home", "away"]:
            result = detect_steam(gid, side)
            if result["is_steam"]:
                result["signal_type"] = "STEAM"
                signals.append(result)
    return signals
