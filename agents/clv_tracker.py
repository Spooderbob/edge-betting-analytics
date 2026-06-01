import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CLV_FILE = DATA_DIR / "clv_history.json"


def _load() -> list:
    if CLV_FILE.exists():
        return json.loads(CLV_FILE.read_text())
    return []


def _save(data: list):
    DATA_DIR.mkdir(exist_ok=True)
    CLV_FILE.write_text(json.dumps(data, indent=2))


def _american_to_prob(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def log_bet(game_id: str, side: str, american_odds: int) -> dict:
    record = {
        "game_id": game_id,
        "side": side,
        "entry_odds": american_odds,
        "entry_prob": round(_american_to_prob(american_odds), 4),
        "timestamp": datetime.utcnow().isoformat(),
        "closing_odds": None,
        "clv": None,
        "status": "open",
    }
    history = _load()
    history.append(record)
    _save(history)
    return record


def close_bet(game_id: str, side: str, closing_odds: int) -> dict:
    history = _load()
    for record in history:
        if record["game_id"] == game_id and record["side"] == side and record["status"] == "open":
            closing_prob = _american_to_prob(closing_odds)
            entry_prob = record["entry_prob"]
            # Positive CLV = we got better odds than closing line (good)
            record["closing_odds"] = closing_odds
            record["closing_prob"] = round(closing_prob, 4)
            record["clv"] = round((entry_prob - closing_prob) * 100, 3)
            record["status"] = "closed"
            break
    _save(history)
    return record


def clv_report() -> dict:
    history = _load()
    closed = [r for r in history if r["status"] == "closed" and r["clv"] is not None]
    if not closed:
        return {"message": "No closed bets yet", "count": 0}
    clvs = [r["clv"] for r in closed]
    positive = [c for c in clvs if c > 0]
    return {
        "total_bets": len(closed),
        "avg_clv": round(sum(clvs) / len(clvs), 3),
        "positive_clv_pct": round(len(positive) / len(clvs) * 100, 1),
        "best_clv": max(clvs),
        "worst_clv": min(clvs),
        "verdict": "Profitable bettor profile" if sum(clvs) / len(clvs) > 0 else "Needs improvement",
    }


def get_history() -> list:
    return _load()
