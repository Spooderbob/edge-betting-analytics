import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

from fastapi import APIRouter
from ev_calculator import remove_vig, calculate_ev, ev_to_human, scan_cached_odds_for_ev

router = APIRouter()


@router.get("/calculate")
def calc_ev(home_odds: int, away_odds: int, our_prob: float):
    vig = remove_vig(home_odds, away_odds)
    ev = calculate_ev(our_prob, home_odds)
    return {"our_prob": our_prob, "ev": ev, "ev_human": ev_to_human(ev), "vig_info": vig}


@router.get("/scan/{sport_key}")
def scan_ev(sport_key: str):
    results = scan_cached_odds_for_ev(sport_key, {})
    return {"count": len(results), "bets": results}
