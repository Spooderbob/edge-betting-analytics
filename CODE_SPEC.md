# EDGE Betting Analytics — Technical Specification

## Overview

These specifications target the existing FastAPI project. All new routers follow the established pattern. Data persists to SQLite at `edge/data/bets.db`. All odds use American format as input; internal calculations use decimal.

---

## 1. Kelly Criterion Bankroll Calculator

**Endpoint:** `POST /api/bankroll/kelly`

**Input (JSON body):**
```json
{
  "win_prob": 0.54,
  "odds_american": -110,
  "bankroll": 5000.00,
  "kelly_fraction": 0.25,
  "max_bet_pct": 0.05
}
```

**Output:**
```json
{
  "full_kelly_pct": 4.40,
  "recommended_pct": 1.10,
  "recommended_amount": 55.00,
  "ev_pct": 3.18,
  "unit_tier": "standard",
  "bet_approved": true,
  "reasoning": "Quarter-Kelly on 3.18% edge. Standard unit."
}
```

**Core logic:**
```python
def kelly_size(win_prob: float, odds_american: int, bankroll: float,
               fraction: float = 0.25, max_pct: float = 0.05) -> dict:
    decimal_odds = (abs(odds_american) / 100 + 1) if odds_american < 0 \
                   else (odds_american / 100 + 1)
    b = decimal_odds - 1
    q = 1 - win_prob
    full_kelly = max(0.0, (b * win_prob - q) / b)
    recommended_pct = min(full_kelly * fraction, max_pct)
    ev_pct = (b * win_prob - q) * 100

    tier_map = [(6.0, "max"), (3.5, "strong"), (1.5, "standard"),
                (0.75, "micro"), (0.0, "no_bet")]
    unit_tier = next(t for threshold, t in tier_map if ev_pct >= threshold)

    return {
        "full_kelly_pct": round(full_kelly * 100, 2),
        "recommended_pct": round(recommended_pct * 100, 2),
        "recommended_amount": round(bankroll * recommended_pct, 2),
        "ev_pct": round(ev_pct, 2),
        "unit_tier": unit_tier,
        "bet_approved": ev_pct >= 1.5  # minimum threshold
    }
```

**Additional endpoint:** `GET /api/bankroll/summary`

Returns current bankroll, peak bankroll, drawdown%, win rate, ROI, and average CLV — all computed from the `bets` table. Drawdown above 20% triggers a `half_sizing: true` flag in the response that the frontend must surface visibly.

**SQLite table required:**
```sql
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sport TEXT, game_id TEXT, bet_type TEXT,
    side TEXT, line REAL, odds_american INTEGER,
    stake REAL, bankroll_at_time REAL,
    kelly_pct REAL, model_win_prob REAL, ev_pct REAL,
    closing_line REAL, closing_odds INTEGER, clv REAL,
    result TEXT DEFAULT 'pending', profit REAL, notes TEXT
);
```

---

## 2. Closing Line Value (CLV) Tracker

**Endpoints:**

`POST /api/bets` — log a bet at entry price

`PATCH /api/bets/{bet_id}/close` — record closing line after game locks

`GET /api/performance/clv-summary` — rolling CLV stats

**Input for POST /api/bets (JSON body):**
```json
{
  "sport": "nfl",
  "game_id": "2024_week8_KC_BUF",
  "bet_type": "spread",
  "side": "away",
  "line": -2.5,
  "odds_american": -110,
  "stake": 55.00,
  "bankroll_at_time": 5000.00,
  "model_win_prob": 0.54
}
```

**Input for PATCH /api/bets/{id}/close:**
```json
{
  "closing_line": -3.5,
  "closing_odds": -115
}
```

**CLV calculation logic:**
```python
def compute_clv(bet_type: str, entry_line: float, entry_odds: int,
                closing_line: float, closing_odds: int) -> dict:
    if bet_type == "spread":
        # Positive = you got more points = good
        clv_points = closing_line - entry_line
    elif bet_type == "ml" or bet_type == "total":
        clv_points = None

    # Probability-based CLV (works for all bet types)
    def to_dec(o): return (abs(o)/100+1) if o < 0 else (o/100+1)
    entry_implied = 1 / to_dec(entry_odds)
    closing_implied = 1 / to_dec(closing_odds)
    # Negative = you got better odds than close = good
    clv_prob = closing_implied - entry_implied

    return {
        "clv_points": clv_points,
        "clv_prob": round(clv_prob, 4),
        "beat_close": clv_prob < 0,
        "clv_pct": round(clv_prob * -100, 2)  # positive = good
    }
```

**Output for GET /api/performance/clv-summary:**
```json
{
  "total_bets": 87,
  "bets_with_clv_data": 71,
  "avg_clv_pct": 1.34,
  "pct_beating_close": 0.61,
  "roi_pct": 4.2,
  "verdict": "positive_edge_confirmed",
  "note": "500+ bets needed for full confidence. Current n=71."
}
```

The `verdict` field returns `positive_edge_confirmed` only when `n >= 500` and `avg_clv_pct > 0`. Below 500 bets it returns `insufficient_sample`. This prevents premature confidence.

**Closing line source:** Pinnacle via scrape or Betmetrics API. The CLV update job runs as a nightly cron (midnight ET) against all bets where `result != 'pending'` and `closing_odds IS NULL`.

---

## 3. Steam Move Detector

**Endpoint:** `GET /api/signals/steam?sport=nfl&lookback_minutes=10`

**Output:**
```json
{
  "sport": "nfl",
  "checked_at": "2024-10-27T14:32:00Z",
  "steam_moves": [
    {
      "game_id": "2024_week8_KC_BUF",
      "game": "Kansas City Chiefs @ Buffalo Bills",
      "market": "spread",
      "side": "away",
      "move_direction": "down",
      "move_magnitude": 1.0,
      "books_moved": ["DraftKings", "FanDuel", "BetMGM"],
      "books_moved_count": 3,
      "window_minutes": 7,
      "open_line": -2.5,
      "current_line": -3.5,
      "first_move_at": "2024-10-27T14:25:11Z",
      "confidence": "high"
    }
  ],
  "total_found": 1
}
```

**Core detection logic:**

This runs against the `odds_history` table which the existing odds poller already populates. No new data source required for the detection itself.

```python
def detect_steam_moves(db, sport: str, lookback_minutes: int = 10,
                       min_move: float = 0.5, min_books: int = 3) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(minutes=lookback_minutes)

    # Pull recent snapshots from odds_history
    recent = db.execute("""
        SELECT game_id, book, market, side, line, recorded_at
        FROM odds_history
        WHERE sport = ? AND recorded_at >= ?
        ORDER BY game_id, book, market, side, recorded_at
    """, (sport, cutoff.isoformat())).fetchall()

    # Also pull the open line (first recorded today) for comparison
    opens = db.execute("""
        SELECT game_id, book, market, side, line
        FROM odds_history
        WHERE sport = ? AND DATE(recorded_at) = DATE('now')
        GROUP BY game_id, book, market, side
        HAVING recorded_at = MIN(recorded_at)
    """, (sport,)).fetchall()

    steam_moves = []
    # Group by (game_id, market, side)
    # For each group, find books where abs(current_line - open_line) >= min_move
    # If count of such books >= min_books AND all moved same direction: steam confirmed
    ...
    return steam_moves
```

**Direction logic:** A steam move requires all qualifying books to move the same direction. Mixed movement (some up, some down) is not steam — it is noise. Flag `confidence: "high"` only when 4+ books move together within 5 minutes. Flag `confidence: "medium"` for 3 books within 10 minutes.

**Polling requirement:** The existing odds poller must run at 60-second intervals and write every snapshot to `odds_history`. Steam detection is purely a query against that table — no additional API calls at detection time.

**SQLite table required:**
```sql
CREATE TABLE IF NOT EXISTS odds_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sport TEXT, game_id TEXT, book TEXT,
    market TEXT, side TEXT, line REAL, odds INTEGER
);
CREATE INDEX IF NOT EXISTS idx_odds_history_lookup
    ON odds_history(sport, game_id, market, side, recorded_at);
```

---

## 4. Player Props Model — Baseball Hit Props

**Endpoint:** `GET /api/props/mlb/hits?player={name}&date={YYYY-MM-DD}`

**Output:**
```json
{
  "player": "Freddie Freeman",
  "date": "2024-10-27",
  "opponent": "New York Yankees",
  "opposing_pitcher": "Gerrit Cole",
  "book_line": 0.5,
  "over_odds": -145,
  "under_odds": 118,
  "projection": 1.18,
  "p_over_0_5": 0.692,
  "book_implied_over": 0.591,
  "edge_pct": 10.1,
  "ev_pct": 8.3,
  "bet_over": true,
  "confidence": "high",
  "factors": {
    "season_avg": 0.311,
    "last_14_days_avg": 0.342,
    "vs_rhp_avg": 0.318,
    "pitcher_whip": 1.04,
    "ballpark_factor": 1.02,
    "lineup_position": 3,
    "projected_pa": 4.3
  }
}
```

**Projection model:**

```python
from scipy.stats import poisson

def project_hits(player_stats: dict, pitcher_stats: dict,
                 game_context: dict) -> dict:
    # Base rate: weighted average of recency windows
    base_avg = (
        player_stats["season_avg"] * 0.30 +
        player_stats["last_30_avg"] * 0.40 +
        player_stats["last_14_avg"] * 0.30
    )

    # Platoon split adjustment
    pitcher_hand = pitcher_stats["throws"]
    if pitcher_hand == "R":
        platoon_factor = player_stats["vs_rhp_avg"] / max(player_stats["season_avg"], 0.001)
    else:
        platoon_factor = player_stats["vs_lhp_avg"] / max(player_stats["season_avg"], 0.001)
    platoon_factor = max(0.75, min(platoon_factor, 1.35))  # cap at ±35%

    # Pitcher quality adjustment: WHIP z-score vs league average (1.28)
    league_avg_whip = 1.28
    pitcher_factor = 1.0 - ((pitcher_stats["whip"] - league_avg_whip) * 0.08)
    pitcher_factor = max(0.80, min(pitcher_factor, 1.20))

    # Plate appearances: lineup spot drives expected PA
    pa_by_slot = {1: 4.65, 2: 4.55, 3: 4.45, 4: 4.35,
                  5: 4.25, 6: 4.10, 7: 3.95, 8: 3.85, 9: 3.75}
    projected_pa = pa_by_slot.get(game_context["lineup_position"], 4.1)

    # Park factor (1.0 = neutral; 1.05 = 5% more offense)
    park_factor = game_context.get("park_factor", 1.0)

    # Final projection: hits per game
    projection = base_avg * platoon_factor * pitcher_factor * park_factor * projected_pa

    return round(projection, 3)

def prop_edge(projection: float, line: float,
              over_odds: int, under_odds: int) -> dict:
    # Poisson probability of exceeding the line
    p_over = 1 - poisson.cdf(int(line), projection)

    # No-vig implied probability
    def to_dec(o): return (abs(o)/100+1) if o < 0 else (o/100+1)
    raw_over = 1 / to_dec(over_odds)
    raw_under = 1 / to_dec(under_odds)
    nv_over = raw_over / (raw_over + raw_under)

    edge = p_over - nv_over
    dec_over = to_dec(over_odds)
    ev = (p_over * (dec_over - 1)) - ((1 - p_over) * 1.0)

    return {
        "p_over": round(p_over, 4),
        "book_implied_over": round(nv_over, 4),
        "edge_pct": round(edge * 100, 2),
        "ev_pct": round(ev * 100, 2),
        "bet_over": edge > 0.04  # minimum 4% edge to flag
    }
```

**Data sources:**
- Season/recent splits: Baseball Savant (`https://baseballsavant.mlb.com/statcast_search` CSV export) or `pybaseball` library
- Confirmed lineups: MLB.com official lineup endpoint or RotoWire (available 60-90 min before first pitch)
- Park factors: FanGraphs park factors table (scrape once per season, store in `park_factors` table)

**Endpoint also required:** `GET /api/props/mlb/hits/batch?date={YYYY-MM-DD}` — runs the model against every player in every confirmed lineup for that date, returns all props with `edge_pct > 3` sorted descending. This is the primary daily workflow view.

---

## 5. Expected Value Calculator

**Endpoint:** `POST /api/ev-calc`

This is the foundation every other module calls. Build it as a standalone utility endpoint and import the functions directly in other routers.

**Input:**
```json
{
  "your_win_prob": 0.54,
  "odds_american": -110,
  "opposing_odds_american": -110,
  "stake": 100.00
}
```

**Output:**
```json
{
  "decimal_odds": 1.909,
  "no_vig_win_prob": 0.500,
  "your_win_prob": 0.540,
  "edge_over_market": 0.040,
  "ev_dollars": 3.64,
  "ev_pct": 3.64,
  "breakeven_prob": 0.524,
  "is_positive_ev": true,
  "vig_pct": 4.55,
  "bet_recommendation": "BET — edge exceeds minimum threshold"
}
```

**Core functions (place in `edge/utils/math.py`, import everywhere):**

```python
def american_to_decimal(odds: int) -> float:
    return (abs(odds) / 100 + 1) if odds < 0 else (odds / 100 + 1)

def no_vig_prob(odds_a: int, odds_b: int) -> tuple[float, float]:
    raw_a = 1 / american_to_decimal(odds_a)
    raw_b = 1 / american_to_decimal(odds_b)
    total = raw_a + raw_b
    return raw_a / total, raw_b / total

def expected_value(win_prob: float, decimal_odds: float,
                   stake: float = 100.0) -> float:
    return (win_prob * (decimal_odds - 1) * stake) - ((1 - win_prob) * stake)

def breakeven_prob(odds_american: int) -> float:
    dec = american_to_decimal(odds_american)
    return 1 / dec

def vig_pct(odds_a: int, odds_b: int) -> float:
    raw_a = 1 / american_to_decimal(odds_a)
    raw_b = 1 / american_to_decimal(odds_b)
    return round((raw_a + raw_b - 1) * 100, 2)
```

**Batch endpoint:** `POST /api/ev-calc/batch` accepts a list of bet objects and returns EV for each. Used by the dashboard to rank all currently detected edges by EV descending.

**Validation rules enforced in the endpoint:**
- `win_prob` must be between 0.01 and 0.99
- If `your_win_prob` is not provided, `no_vig_prob` from the two odds inputs is used as the baseline (zero-edge baseline)
- `edge_over_market` below 0.0 returns `is_positive_ev: false` and `bet_recommendation: "NO BET"` regardless of raw EV sign

---

## 6. LLM Council Integration

**Endpoint:** `POST /api/council/analyze`

**Input:**
```json
{
  "bet_description": "KC Chiefs -3.5 (-110) vs Buffalo Bills, Week 8",
  "supporting_data": {
    "sport": "nfl",
    "game_id": "2024_week8_KC_BUF",
    "bet_type": "spread",
    "side": "home",
    "line": -3.5,
    "odds_american": -110,
    "model_win_prob": 56.2,
    "ev_pct": 4.1,
    "stake": 110,
    "pct_of_bankroll": 2.2,
    "signals": {
      "rlm": "Line moved from -2.5 to -3.5 despite 62% public on Bills",
      "steam": "3 books moved within 6 minutes at 2:14 PM ET",
      "public_pct": 38,
      "handle_pct": 61
    },
    "context": {
      "injury_notes": "Bills WR Diggs questionable",
      "rest_days": {"home": 7, "away": 7},
      "weather": "Cold, 28F, 12mph wind"
    }
  }
}
```

**Output:**
```json
{
  "verdict": "EDGE",
  "confidence": "HIGH",
  "consensus_strength": "MAJORITY",
  "sizing_recommendation": "STRONG",
  "timing_note": "Bet now — sharp action already confirmed, line likely moves further",
  "reasons_to_bet": [
    "Handle disparity (61% on home vs 38% tickets) confirms sharp money on KC",
    "Steam move corroborates syndicate action within a 6-minute window",
    "Weather suppresses Bills passing game which is their primary path to cover"
  ],
  "reasons_to_pass": [
    "3.5 crosses a key number — middle risk if Bills win by 3",
    "Mahomes road record vs spread has regressed in cold weather games"
  ],
  "council_summary": "Four of five analysts favored the bet...",
  "timestamp": "2024-10-27T14:45:22Z",
  "cost_usd": 0.18
}
```

**Implementation — `edge/council/analyze.py`:**

```python
import asyncio
import httpx
import os
from datetime import datetime

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

COUNCIL_MEMBERS = [
    {
        "model": "openai/gpt-4o",
        "role": "Sharp Money Analyst",
        "prompt": "Analyze from a sharp bettor perspective. Focus on steam, RLM, "
                  "line shopping value, CLV expectations. Cite specific numbers. "
                  "Output 2-3 reasons this does or does not represent sharp action."
    },
    {
        "model": "anthropic/claude-sonnet-4-6",
        "role": "Quantitative Analyst",
        "prompt": "Analyze using statistical frameworks. Calculate implied probability "
                  "from the given odds. State minimum win probability for positive EV. "
                  "Flag if the claimed edge is statistically significant given sample size."
    },
    {
        "model": "google/gemini-1.5-pro",
        "role": "Situational Analyst",
        "prompt": "Analyze situational factors: injuries, rest, weather, schedule spot, "
                  "motivation, coaching tendencies. Every claim must reference the specific matchup."
    },
    {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "role": "Devil's Advocate",
        "prompt": "Find every reason NOT to place this bet. Steelman the opposing side. "
                  "Find the trap, the recency bias, the narrative masquerading as edge. Be harsh."
    },
    {
        "model": "mistralai/mistral-large-2411",
        "role": "Risk Assessor",
        "prompt": "Assess timing and risk profile. Should we bet now or wait? "
                  "What is worst-case scenario? Is this high or low variance? "
                  "Recommend sizing tier: MICRO / STANDARD / STRONG / MAX."
    }
]

CHAIRMAN_MODEL = "openai/gpt-4o"
CHAIRMAN_PROMPT = """You are the chairman of a sports betting analysis council.
Synthesize the analysts' work into this exact format:

VERDICT: [EDGE | NO EDGE | FADE | WAIT]
CONFIDENCE: [HIGH | MEDIUM | LOW]
CONSENSUS_STRENGTH: [UNANIMOUS | MAJORITY | SPLIT | DISSENTING]
SIZING_RECOMMENDATION: [MICRO | STANDARD | STRONG | MAX | NO BET]
TIMING_NOTE: [one sentence]

REASONS_TO_BET:
- bullet
- bullet

REASONS_TO_PASS:
- bullet
- bullet

COUNCIL_SUMMARY: [1-2 paragraph synthesis noting strong disagreements]"""

async def _call(client, model, system, user):
    r = await client.post(
        OPENROUTER_BASE,
        json={"model": model, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ], "temperature": 0.3, "max_tokens": 700},
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_KEY']}",
            "HTTP-Referer": "https://edge-analytics.local"
        }
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def run_council(bet_description: str, supporting_data: dict) -> dict:
    import json
    context = f"{bet_description}\n\nData:\n{json.dumps(supporting_data, indent=2)}"

    async with httpx.AsyncClient(timeout=90.0) as client:
        # Stage 1: all analysts in parallel
        s1_results = await asyncio.gather(*[
            _call(client, m["model"], m["prompt"],
                  f"Analyze this bet:\n\n{context}")
            for m in COUNCIL_MEMBERS
        ])

        # Stage 2: each analyst critiques the others (parallel)
        s2_results = await asyncio.gather(*[
            _call(
                client, COUNCIL_MEMBERS[i]["model"],
                COUNCIL_MEMBERS[i]["prompt"],
                f"Bet:\n{context}\n\nPeer analyses:\n" +
                "\n\n".join([
                    f"[{COUNCIL_MEMBERS[j]['role']}]\n{s1_results[j]}"
                    for j in range(len(COUNCIL_MEMBERS)) if j != i
                ]) + "\n\nCritique what they missed or got wrong."
            )
            for i in range(len(COUNCIL_MEMBERS))
        ])

        # Stage 3: chairman synthesizes
        chairman_input = (
            f"BET:\n{context}\n\n"
            "--- STAGE 1 ---\n" +
            "\n\n".join([f"[{COUNCIL_MEMBERS[i]['role']}]\n{s1_results[i]}"
                         for i in range(len(COUNCIL_MEMBERS))]) +
            "\n\n--- STAGE 2 CRITIQUES ---\n" +
            "\n\n".join([f"[{COUNCIL_MEMBERS[i]['role']}]\n{s2_results[i]}"
                         for i in range(len(COUNCIL_MEMBERS))]) +
            "\n\nDeliver your verdict."
        )
        verdict_raw = await _call(client, CHAIRMAN_MODEL,
                                   CHAIRMAN_PROMPT, chairman_input)

    return {
        "verdict_raw": verdict_raw,
        "stage1": [{"role": COUNCIL_MEMBERS[i]["role"], "analysis": s1_results[i]}
                   for i in range(len(COUNCIL_MEMBERS))],
        "timestamp": datetime.utcnow().isoformat()
    }
```

**FastAPI router (`edge/routers/council.py`):**

```python
from fastapi import APIRouter
from edge.council.analyze import run_council

router = APIRouter(prefix="/api/council", tags=["council"])

@router.post("/analyze")
async def analyze_bet(payload: dict):
    result = await run_council(
        payload["bet_description"],
        payload.get("supporting_data", {})
    )
    # Parse structured fields from verdict_raw for clean response
    # Store to council_analyses table
    return result
```

**When to trigger the council — enforced in calling code, not the endpoint:**
- Stake > 2% of bankroll: always run
- Mixed signals (positive EV but no RLM/steam confirmation): always run
- Prop bet > $200 with edge between 3-6%: always run
- Pure arbitrage: never run (math is deterministic)
- Injury window closing (< 10 minutes): never run (too slow)

**SQLite table required:**
```sql
CREATE TABLE IF NOT EXISTS council_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    bet_description TEXT,
    verdict TEXT, confidence TEXT, sizing_rec TEXT,
    full_response JSON,
    acted_on INTEGER DEFAULT 0,
    bet_id INTEGER REFERENCES bets(id)
);
```

---

## Integration Notes

**Dependency installation required:**
```
pip install scipy pybaseball nfl-data-py nba_api httpx
```

**Environment variables to add to `.env`:**
```
OPENROUTER_KEY=
ODDS_API_KEY=
OWM_API_KEY=
```

**Router registration order in `main.py`** (add after existing routers):
```python
from edge.routers import bankroll, clv, steam, props_mlb, ev_calc, council
app.include_router(bankroll.router)
app.include_router(clv.router)
app.include_router(steam.router)
app.include_router(props_mlb.router)
app.include_router(ev_calc.router)
app.include_router(council.router)
```

**Build order recommendation:** EV calculator first (everything else depends on it), then Kelly, then CLV tracker, then steam detector, then props model, then council last. The council has the highest runtime cost (~$0.15-0.25 per call) and should only activate after the quantitative stack is already flagging bets.