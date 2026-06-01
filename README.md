# EDGE — Sports Analytics & Value Betting Engine

Built by Aaron + Claude. The goal: find real statistical edges before the books close them.

## Architecture
- `backend/` — Python FastAPI, all analysis agents
- `frontend/` — React dashboard
- `data/` — All collected stats, persisted locally (never lost)
- `agents/` — Individual analysis modules

## Data Sources
- The Odds API (live lines from all major books)
- ESPN API (players, injuries, schedules)
- MLB Stats API (pitcher/batter splits)
- NBA Stats API
- NHL API

## Edge Logic
- Pitcher vs batter matchup scoring
- Line value detection (expected value calculator)
- Public money fade signals
- Parlay correlation finder
- Closing line value tracker
