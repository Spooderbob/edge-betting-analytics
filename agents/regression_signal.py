# Regression-to-Mean signal detector
# Research: 54% of NFL turnover margin = luck (nflfastR verified)
# NBA: shooting variance regresses to season mean within 10 games


def turnover_regression_signal(current_to_margin: float, games_played: int) -> dict:
    """
    NFL turnover margin regression.
    current_to_margin: team's current TO margin (positive = team winning TO battle)
    games_played: games played so far this season
    """
    LUCK_FRACTION = 0.54  # 54% of TO margin is luck, per nflfastR research

    expected_regression = current_to_margin * LUCK_FRACTION
    projected_true_margin = current_to_margin - expected_regression

    # Signal strength: larger margin + fewer games = stronger fade signal
    signal_strength = abs(current_to_margin) / max(1, games_played ** 0.5)

    fade = current_to_margin >= 5 and games_played <= 10
    back = current_to_margin <= -5 and games_played <= 10

    return {
        "current_to_margin": current_to_margin,
        "games_played": games_played,
        "luck_component": round(expected_regression, 2),
        "projected_true_margin": round(projected_true_margin, 2),
        "signal_strength": round(signal_strength, 2),
        "fade_signal": fade,
        "back_signal": back,
        "action": (
            f"FADE this team — margin of +{current_to_margin} expected to regress by ~{expected_regression:.1f} TOs"
            if fade else
            f"BACK this team — margin of {current_to_margin} expected to improve by ~{abs(expected_regression):.1f} TOs"
            if back else
            "No strong regression signal"
        ),
    }


def nba_shooting_regression(player_name: str, current_fg_pct: float,
                              season_fg_pct: float, games_sample: int) -> dict:
    """
    NBA shooting regression signal.
    Detects when a player is on a hot/cold streak that will regress.
    """
    if games_sample >= 20:
        weight = 0.3  # small regression expected, large sample
    elif games_sample >= 10:
        weight = 0.5  # moderate regression expected
    else:
        weight = 0.7  # strong regression expected, tiny sample

    expected_true = season_fg_pct * (1 - weight) + current_fg_pct * weight
    deviation = current_fg_pct - season_fg_pct

    hot_streak = deviation >= 0.08 and games_sample <= 10
    cold_streak = deviation <= -0.08 and games_sample <= 10

    return {
        "player": player_name,
        "current_fg_pct": current_fg_pct,
        "season_fg_pct": season_fg_pct,
        "games_sample": games_sample,
        "deviation": round(deviation, 3),
        "expected_true_pct": round(expected_true, 3),
        "hot_streak": hot_streak,
        "cold_streak": cold_streak,
        "action": (
            f"UNDER on {player_name} scoring props — shooting {current_fg_pct:.0%} vs {season_fg_pct:.0%} season avg, regression incoming"
            if hot_streak else
            f"OVER on {player_name} scoring props — shooting {current_fg_pct:.0%} vs {season_fg_pct:.0%}, due to bounce back"
            if cold_streak else
            "Shooting within normal variance, no regression play"
        ),
    }


def team_record_regression(wins: int, losses: int,
                             pythagorean_wins: float) -> dict:
    """
    Compare actual record to Pythagorean expected wins.
    Teams overperforming Pythagorean expectation by 2+ games are due to regress.
    Pythagorean wins = pts_scored^13.91 / (pts_scored^13.91 + pts_allowed^13.91) * games
    """
    games = wins + losses
    win_pct = wins / games if games > 0 else 0
    pythag_pct = pythagorean_wins / games if games > 0 else 0
    overperformance = wins - pythagorean_wins

    return {
        "actual_record": f"{wins}-{losses}",
        "pythagorean_wins": round(pythagorean_wins, 1),
        "overperformance": round(overperformance, 1),
        "fade_team": overperformance >= 2,
        "back_team": overperformance <= -2,
        "action": (
            f"FADE — team is {overperformance:.1f} wins LUCKY, expect regression to {pythagorean_wins:.0f}-{games-pythagorean_wins:.0f}"
            if overperformance >= 2 else
            f"BACK — team is {abs(overperformance):.1f} wins UNLUCKY, expect bounce back"
            if overperformance <= -2 else
            "Record in line with performance, no regression play"
        ),
    }
