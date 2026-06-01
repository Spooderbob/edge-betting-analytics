import httpx
import asyncio
from typing import Optional

MLB_BASE = "https://statsapi.mlb.com/api/v1"

# ---------------------------------------------------------------------------
# Park factors (1.0 = neutral, >1.0 = hitter-friendly, <1.0 = pitcher-friendly)
# Based on multi-year run-environment data. Update annually.
# ---------------------------------------------------------------------------
PARK_FACTORS = {
    "COL": 1.18,   # Coors Field
    "CIN": 1.10,   # Great American Ballpark
    "TEX": 1.08,   # Globe Life Field
    "BOS": 1.07,   # Fenway Park
    "PHI": 1.05,   # Citizens Bank Park
    "MIN": 1.04,   # Target Field
    "BAL": 1.03,   # Camden Yards
    "DET": 1.02,   # Comerica Park
    "TOR": 1.01,   # Rogers Centre
    "LAA": 1.00,   # Angel Stadium
    "CHW": 1.00,   # Guaranteed Rate Field
    "NYY": 0.99,   # Yankee Stadium
    "ATL": 0.99,   # Truist Park
    "KC":  0.98,   # Kauffman Stadium
    "CLE": 0.98,   # Progressive Field
    "ARI": 0.97,   # Chase Field
    "HOU": 0.97,   # Minute Maid Park
    "SEA": 0.96,   # T-Mobile Park
    "SF":  0.95,   # Oracle Park
    "NYM": 0.95,   # Citi Field
    "MIL": 0.95,   # American Family Field
    "LAD": 0.94,   # Dodger Stadium
    "PIT": 0.94,   # PNC Park
    "SD":  0.93,   # Petco Park
    "MIA": 0.93,   # loanDepot park
    "OAK": 0.93,   # Oakland Coliseum
    "WAS": 0.97,   # Nationals Park
    "CHC": 1.02,   # Wrigley Field
    "STL": 0.98,   # Busch Stadium
    "TB":  0.96,   # Tropicana Field
}

# Lineup position factors: how often each spot in the order gets AB / produces hits
# Leadoff and cleanup see more AB and pitcher attention; 9-hole sees less.
LINEUP_FACTORS = {
    1: 1.06,   # leadoff — most PA, sets table
    2: 1.05,   # high OBP slot
    3: 1.04,   # best hitter, most RBI situations
    4: 1.03,   # cleanup
    5: 1.01,
    6: 0.99,
    7: 0.97,
    8: 0.95,
    9: 0.93,   # 9-hole — fewest meaningful PA
}


async def _get(url: str, params: dict = None) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

async def get_batter_splits(batter_id: int) -> dict:
    """Season hitting splits. Falls back to league-average defaults on failure."""
    data = await _get(f"{MLB_BASE}/people/{batter_id}/stats",
                      {"stats": "season", "group": "hitting"})
    try:
        s = data["stats"][0]["splits"][0]["stat"]
        return {
            "avg": float(s.get("avg", 0)),
            "obp": float(s.get("obp", 0)),
            "slg": float(s.get("slg", 0)),
            "ops": float(s.get("ops", 0)),
            "hits": int(s.get("hits", 0)),
            "atBats": int(s.get("atBats", 1)),
        }
    except (KeyError, IndexError):
        return {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "hits": 0, "atBats": 1}


async def get_batter_platoon_split(batter_id: int, pitcher_hand: str) -> float:
    """
    Return batter AVG specifically vs LHP or RHP.
    pitcher_hand: 'L' or 'R'
    Falls back to season avg default on failure.
    """
    stat_type = "vsLeft" if pitcher_hand == "L" else "vsRight"
    try:
        data = await _get(f"{MLB_BASE}/people/{batter_id}/stats",
                          {"stats": "careerStatSplits", "group": "hitting",
                           "sitCodes": stat_type})
        s = data["stats"][0]["splits"][0]["stat"]
        return float(s.get("avg", 0.250))
    except (KeyError, IndexError):
        return 0.250


async def get_batter_last7(batter_id: int) -> float:
    """
    Return batter AVG over the last 7 days.
    MLB API does not expose a direct last-7 endpoint; we query the recent
    game log and compute manually.  Falls back to 0.250 on failure.
    """
    try:
        data = await _get(f"{MLB_BASE}/people/{batter_id}/stats",
                          {"stats": "lastXGames", "group": "hitting", "limit": 7})
        s = data["stats"][0]["splits"][0]["stat"]
        hits = int(s.get("hits", 0))
        ab = int(s.get("atBats", 1))
        return hits / ab if ab > 0 else 0.250
    except (KeyError, IndexError):
        return 0.250


async def get_pitcher_stats(pitcher_id: int) -> dict:
    """Season pitching stats including BAA (avg against)."""
    data = await _get(f"{MLB_BASE}/people/{pitcher_id}/stats",
                      {"stats": "season", "group": "pitching"})
    try:
        s = data["stats"][0]["splits"][0]["stat"]
        return {
            "era": float(s.get("era", 4.50)),
            "whip": float(s.get("whip", 1.30)),
            "avg_against": float(s.get("avg", 0.250)),
            "k_per9": float(s.get("strikeoutsPer9Inn", 8.0)),
            "hand": s.get("pitchHand", {}).get("code", "R") if isinstance(s.get("pitchHand"), dict) else "R",
        }
    except (KeyError, IndexError):
        return {"era": 4.50, "whip": 1.30, "avg_against": 0.250, "k_per9": 8.0, "hand": "R"}


# ---------------------------------------------------------------------------
# Factor helpers
# ---------------------------------------------------------------------------

def _era_tier_factor(era: float) -> float:
    """
    Convert ERA to a 0–1 factor representing pitcher quality.
    Elite ERA -> low factor (hard to get hits).
    Poor ERA  -> high factor (easier to get hits).
    Normalized so ~4.50 (league average) returns 0.50.
    """
    if era >= 6.50:
        return 0.82
    elif era >= 6.00:
        return 0.78
    elif era >= 5.50:
        return 0.73
    elif era >= 5.00:
        return 0.67
    elif era >= 4.50:
        return 0.60
    elif era >= 4.00:
        return 0.53
    elif era >= 3.50:
        return 0.47
    elif era >= 3.00:
        return 0.42
    elif era >= 2.50:
        return 0.37
    else:
        return 0.32


def _recent_form_factor(last7_avg: float, season_avg: float) -> float:
    """
    Compare last-7-day trend to season average.
    Returns a signed delta capped at ±0.060 to avoid over-weighting hot/cold streaks.
    """
    delta = last7_avg - season_avg
    return max(-0.060, min(0.060, delta))


def _rest_days_factor(rest_days: int) -> float:
    """
    Voulgaris-inspired pace/context adjustment.
    Batters are slightly better after 1-2 rest days (fresh legs / clear eyes).
    Back-to-back performance tends to be marginally weaker.
    Returns a multiplier centered on 1.0.
    """
    if rest_days == 0:
        return 0.97   # no rest — slight fatigue drag
    elif rest_days == 1:
        return 1.00   # standard one-day rest
    elif rest_days == 2:
        return 1.02   # optimal recovery window
    elif rest_days <= 4:
        return 1.01   # still fresh
    else:
        return 0.99   # long layoff — rust factor


# ---------------------------------------------------------------------------
# Core composite model (Benter-style multi-variable weighted scoring)
# ---------------------------------------------------------------------------

def estimate_hit_probability(
    batter: dict,
    pitcher: dict,
    *,
    platoon_avg: float = None,
    last7_avg: float = None,
    park_team: str = None,
    lineup_spot: int = None,
    rest_days: int = 1,
) -> dict:
    """
    Compute hit probability using a 7-factor composite score.

    Weights (sum to 1.0):
        batter_season_avg     0.20
        platoon_split_avg     0.25  <- most important per research
        pitcher_baa           0.20
        pitcher_era_tier      0.15
        recent_form (7-day)   0.10
        park_factor           0.05
        rest_days_factor      0.05

    Returns a dict with the composite score, individual factor values,
    and the final clamped hit probability.
    """
    season_avg = batter.get("avg", 0.250)

    # Factor 1: Batter season average (raw, weight 0.20)
    f_season = season_avg

    # Factor 2: Platoon split vs pitcher hand (weight 0.25)
    f_platoon = platoon_avg if platoon_avg is not None else season_avg

    # Factor 3: Pitcher BAA (weight 0.20)
    f_baa = pitcher.get("avg_against", 0.250)

    # Factor 4: Pitcher ERA tier — converted to hit-probability space (weight 0.15)
    # ERA tier yields a value in ~[0.32, 0.82]; scale to hit-prob range [0.18, 0.46]
    era_tier_raw = _era_tier_factor(pitcher.get("era", 4.50))
    f_era = 0.18 + (era_tier_raw - 0.32) * (0.46 - 0.18) / (0.82 - 0.32)

    # Factor 5: Recent form — season avg adjusted by last-7 delta (weight 0.10)
    last7 = last7_avg if last7_avg is not None else season_avg
    form_delta = _recent_form_factor(last7, season_avg)
    f_form = season_avg + form_delta

    # Factor 6: Park factor — translate multiplier to hit-probability space (weight 0.05)
    park_mult = PARK_FACTORS.get(park_team, 1.00) if park_team else 1.00
    f_park = season_avg * park_mult

    # Factor 7: Rest days (weight 0.05)
    rest_mult = _rest_days_factor(rest_days)
    f_rest = season_avg * rest_mult

    # Weighted composite
    composite = (
        f_season  * 0.20
        + f_platoon * 0.25
        + f_baa     * 0.20
        + f_era     * 0.15
        + f_form    * 0.10
        + f_park    * 0.05
        + f_rest    * 0.05
    )

    # Lineup position multiplier (applied after composite — multiplicative effect)
    spot = lineup_spot if (lineup_spot and 1 <= lineup_spot <= 9) else None
    lineup_mult = LINEUP_FACTORS.get(spot, 1.00)
    adjusted = composite * lineup_mult

    # OPS quality boost / drag (secondary signal, small effect)
    ops = batter.get("ops", 0.720)
    if ops >= 0.900:
        adjusted *= 1.04
    elif ops <= 0.650:
        adjusted *= 0.96

    final_prob = round(min(max(adjusted, 0.10), 0.65), 4)

    return {
        "composite_score": round(composite, 4),
        "factor_season_avg": round(f_season, 4),
        "factor_platoon_avg": round(f_platoon, 4),
        "factor_pitcher_baa": round(f_baa, 4),
        "factor_era_tier": round(f_era, 4),
        "factor_recent_form": round(f_form, 4),
        "factor_park": round(f_park, 4),
        "factor_rest": round(f_rest, 4),
        "lineup_mult": lineup_mult,
        "ops_adjusted": round(adjusted, 4),
        "hit_probability": final_prob,
    }


# ---------------------------------------------------------------------------
# Odds / EV helpers
# ---------------------------------------------------------------------------

def _american_to_prob(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def _edge_label(prob: float) -> str:
    if prob >= 0.45:
        return "STRONG — high hit probability"
    elif prob >= 0.38:
        return "LEAN — above average matchup"
    elif prob >= 0.30:
        return "NEUTRAL"
    else:
        return "FADE — tough matchup"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_hit_prop(
    batter_id: int,
    pitcher_id: int,
    *,
    book_line: Optional[int] = None,
    park_team: Optional[str] = None,
    lineup_spot: Optional[int] = None,
    rest_days: int = 1,
    pitcher_hand: Optional[str] = None,
) -> dict:
    """
    Full 7-factor hit-prop analysis.

    Parameters
    ----------
    batter_id   : MLB person ID for the batter
    pitcher_id  : MLB person ID for the pitcher
    book_line   : American odds for Over 0.5 hits (e.g. -135)
    park_team   : Home team abbreviation for park factor lookup (e.g. 'COL')
    lineup_spot : Batting order position 1–9
    rest_days   : Days since batter last played (0 = back-to-back)
    pitcher_hand: 'L' or 'R' — used for platoon split lookup
    """
    # Resolve pitcher hand if not provided
    _hand = pitcher_hand  # may be None; fetcher will fill it in

    # Concurrent data fetch: season stats + pitcher info first
    batter_season, pitcher = await asyncio.gather(
        get_batter_splits(batter_id),
        get_pitcher_stats(pitcher_id),
    )

    # Use returned pitcher hand if caller did not supply one
    effective_hand = _hand or pitcher.get("hand", "R")

    # Fetch platoon split and last-7 concurrently
    platoon_avg, last7_avg = await asyncio.gather(
        get_batter_platoon_split(batter_id, effective_hand),
        get_batter_last7(batter_id),
    )

    model = estimate_hit_probability(
        batter_season,
        pitcher,
        platoon_avg=platoon_avg,
        last7_avg=last7_avg,
        park_team=park_team,
        lineup_spot=lineup_spot,
        rest_days=rest_days,
    )

    our_prob = model["hit_probability"]

    result = {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "pitcher_hand": effective_hand,
        # Raw inputs
        "batter_season_avg": batter_season["avg"],
        "batter_platoon_avg": platoon_avg,
        "batter_last7_avg": last7_avg,
        "pitcher_baa": pitcher["avg_against"],
        "pitcher_era": pitcher["era"],
        "pitcher_whip": pitcher["whip"],
        # Model outputs
        "composite_score": model["composite_score"],
        "factors": {
            "season_avg":  model["factor_season_avg"],
            "platoon_avg": model["factor_platoon_avg"],
            "pitcher_baa": model["factor_pitcher_baa"],
            "era_tier":    model["factor_era_tier"],
            "recent_form": model["factor_recent_form"],
            "park":        model["factor_park"],
            "rest":        model["factor_rest"],
        },
        "lineup_spot": lineup_spot,
        "lineup_mult": model["lineup_mult"],
        "park_team": park_team,
        "rest_days": rest_days,
        "our_hit_probability": our_prob,
        "edge_label": _edge_label(our_prob),
    }

    if book_line is not None:
        book_prob = _american_to_prob(book_line)
        ev = (our_prob - book_prob) / book_prob
        result["book_line"] = book_line
        result["book_implied_prob"] = round(book_prob, 4)
        result["ev_pct"] = round(ev * 100, 2)
        result["value_bet"] = our_prob > book_prob * 1.05

    return result
