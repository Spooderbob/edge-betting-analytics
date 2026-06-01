def american_to_decimal(american: int) -> float:
    if american > 0:
        return (american / 100) + 1
    return (100 / abs(american)) + 1


def full_kelly(prob_win: float, decimal_odds: float) -> float:
    # Kelly formula: (b*p - q) / b  where b=decimal_odds-1, p=prob_win, q=1-prob_win
    b = decimal_odds - 1
    q = 1 - prob_win
    return (b * prob_win - q) / b


def fractional_kelly(prob_win: float, decimal_odds: float, fraction: float = 0.25) -> float:
    return full_kelly(prob_win, decimal_odds) * fraction


def kelly_recommendation(bankroll: float, prob_win: float, american_odds: int, fraction: float = 0.25) -> dict:
    decimal = american_to_decimal(american_odds)
    fk = full_kelly(prob_win, decimal)
    safe = fractional_kelly(prob_win, decimal, fraction)
    safe = max(0, safe)
    return {
        "bankroll": bankroll,
        "prob_win": prob_win,
        "american_odds": american_odds,
        "decimal_odds": round(decimal, 3),
        "full_kelly_pct": round(fk * 100, 2),
        "quarter_kelly_pct": round(safe * 100, 2),
        "recommended_bet": round(bankroll * safe, 2),
        "max_bet_full_kelly": round(bankroll * max(0, fk), 2),
    }


def sizing_table(bankroll: float) -> list:
    rows = []
    for edge_pct in [1, 2, 3, 5, 7, 10, 15]:
        for odds in [-110, -150, +100, +150, +200]:
            prob = edge_pct / 100 + _american_to_implied(odds)
            rec = kelly_recommendation(bankroll, prob, odds)
            rows.append({
                "edge_pct": edge_pct,
                "odds": odds,
                "bet_size": rec["recommended_bet"],
                "kelly_pct": rec["quarter_kelly_pct"],
            })
    return rows


def _american_to_implied(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)
