import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

from fastapi import APIRouter
from pydantic import BaseModel
from steam_detector import record_line, detect_steam, detect_rlm, get_all_signals

router = APIRouter()


class LineRequest(BaseModel):
    game_id: str
    book: str
    odds: int
    market: str = "h2h"
    side: str = "home"


class RLMRequest(BaseModel):
    game_id: str
    public_side: str
    bet_pct: float
    handle_pct: float


@router.post("/record-line")
def record(req: LineRequest):
    return record_line(req.game_id, req.book, req.odds, req.market, req.side)


@router.get("/steam/{game_id}")
def steam(game_id: str, side: str = "home"):
    return detect_steam(game_id, side)


@router.post("/rlm")
def rlm(req: RLMRequest):
    return detect_rlm(req.game_id, req.public_side, req.bet_pct, req.handle_pct)


@router.get("/signals")
def signals():
    return get_all_signals()
