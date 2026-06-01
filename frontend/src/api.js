import axios from 'axios'
// Empty string = same origin (works on Render). Falls back to localhost for local dev.
const BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')
export const api = {
  getLiveOdds: (sport) => axios.get(`${BASE}/odds/live/${sport}`),
  getCachedOdds: (sport) => axios.get(`${BASE}/odds/cached/${sport}`),
  getBestOdds: (sport) => axios.get(`${BASE}/edges/best-odds/${sport}`),
  getValueBets: (sport) => axios.get(`${BASE}/edges/value-bets/${sport}`),
  calculateEV: (homeOdds, awayOdds, ourProb) =>
    axios.get(`${BASE}/ev/calculate`, { params: { home_odds: homeOdds, away_odds: awayOdds, our_prob: ourProb } }),
  getKelly: (bankroll, probWin, americanOdds) =>
    axios.post(`${BASE}/bankroll/kelly`, { bankroll, prob_win: probWin, american_odds: americanOdds }),
  getSharpSignals: () => axios.get(`${BASE}/sharp/signals`),
  getSteamMoves: () => axios.get(`${BASE}/sharp/steam`),
  getRLM: () => axios.get(`${BASE}/sharp/rlm`),
  getPublicFade: () => axios.get(`${BASE}/sharp/public-fade`),
  getRegression: (sport) => axios.get(`${BASE}/signals/regression/${sport}`),
  getNBAHalftime: () => axios.get(`${BASE}/signals/nba-halftime`),
  getWeather: () => axios.get(`${BASE}/signals/weather`),
  getMLBSchedule: () => axios.get(`${BASE}/mlb/schedule`),
  analyzeMatchup: (batterId, pitcherId) =>
    axios.get(`${BASE}/mlb/matchup`, { params: { batter_id: batterId, pitcher_id: pitcherId } }),
  analyzeHitProp: (batterId, pitcherId, bookLine) =>
    axios.get(`${BASE}/props/mlb/hit/${batterId}`, { params: { pitcher_id: pitcherId, book_line: bookLine } }),
  getCLVReport: () => axios.get(`${BASE}/clv/report`),
  getHealth: () => axios.get(`${BASE}/health`),
}
