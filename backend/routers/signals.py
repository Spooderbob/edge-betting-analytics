import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))
from fastapi import APIRouter
from regression_signal import turnover_regression_signal, nba_shooting_regression, team_record_regression
from nba_halftime import halftime_edge, analyze_nba_game_total

router = APIRouter()

@router.get("/nfl/regression")
def nfl_regression(to_margin: float, games_played: int):
    return turnover_regression_signal(to_margin, games_played)

@router.get("/nba/shooting-regression")
def nba_regression(player: str, current_fg: float, season_fg: float, games: int):
    return nba_shooting_regression(player, current_fg, season_fg, games)

@router.get("/nba/halftime-edge")
def halftime(full_game_total: float, h1_total: float, high_pace: bool = False):
    return halftime_edge(full_game_total, h1_total, high_pace)

@router.get("/team/record-regression")
def record_regression(wins: int, losses: int, pythagorean_wins: float):
    return team_record_regression(wins, losses, pythagorean_wins)
