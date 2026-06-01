import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

from fastapi import APIRouter
from pydantic import BaseModel
from kelly import kelly_recommendation, sizing_table

router = APIRouter()


class KellyRequest(BaseModel):
    bankroll: float
    prob_win: float
    american_odds: int
    fraction: float = 0.25


@router.post("/kelly")
def get_kelly(req: KellyRequest):
    return kelly_recommendation(req.bankroll, req.prob_win, req.american_odds, req.fraction)


@router.get("/sizing-table")
def get_sizing_table(bankroll: float = 1000.0):
    return sizing_table(bankroll)
