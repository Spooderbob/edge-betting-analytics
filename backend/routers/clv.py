import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

from fastapi import APIRouter
from pydantic import BaseModel
from clv_tracker import log_bet, close_bet, clv_report, get_history

router = APIRouter()


class LogBetRequest(BaseModel):
    game_id: str
    side: str
    american_odds: int


class CloseBetRequest(BaseModel):
    game_id: str
    side: str
    closing_odds: int


@router.post("/log-bet")
def log(req: LogBetRequest):
    return log_bet(req.game_id, req.side, req.american_odds)


@router.post("/close-bet")
def close(req: CloseBetRequest):
    return close_bet(req.game_id, req.side, req.closing_odds)


@router.get("/report")
def report():
    return clv_report()


@router.get("/history")
def history():
    return get_history()
