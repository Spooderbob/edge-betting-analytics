import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))
from fastapi import APIRouter
from pydantic import BaseModel
from public_fade import public_fade_score, scan_for_fades, fade_performance

router = APIRouter()

class FadeRequest(BaseModel):
    ticket_pct: float
    handle_pct: float
    line_drift: float
    game: str = ""
    sport: str = ""

@router.post("/analyze")
def analyze_fade(req: FadeRequest):
    return public_fade_score(req.ticket_pct, req.handle_pct, req.line_drift)

@router.post("/scan")
def scan_games(games: list):
    return scan_for_fades(games)

@router.get("/performance")
def performance():
    return fade_performance()
