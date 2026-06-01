import React, { useState, useEffect } from 'react'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = {
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

// ── Styles ──────────────────────────────────────────────────────────────────

const S = {
  app: {
    minHeight: '100vh',
    background: '#0a0a0f',
    color: '#e2e8f0',
    fontFamily: 'Courier New, monospace',
    paddingBottom: 72, // space for bottom nav
  },
  header: {
    background: '#111827',
    borderBottom: '1px solid #1f2937',
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  title: { fontSize: 20, fontWeight: 'bold', color: '#10b981', letterSpacing: 3 },
  subtitle: { fontSize: 10, color: '#6b7280', letterSpacing: 1 },
  content: { padding: '16px', maxWidth: 1400, margin: '0 auto' },
  card: {
    background: '#111827',
    border: '1px solid #1f2937',
    borderRadius: 8,
    padding: 14,
    marginBottom: 10,
  },
  label: { fontSize: 10, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 },
  value: { fontSize: 20, fontWeight: 'bold', color: '#f9fafb' },
  green: { color: '#10b981' },
  yellow: { color: '#f59e0b' },
  red: { color: '#ef4444' },
  blue: { color: '#60a5fa' },
  // Responsive grids — stack on mobile, spread on desktop
  grid2: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 10,
    marginBottom: 14,
  },
  grid3: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
    gap: 10,
    marginBottom: 14,
  },
  grid4: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
    gap: 10,
    marginBottom: 14,
  },
  input: {
    background: '#1f2937',
    border: '1px solid #374151',
    color: '#e2e8f0',
    padding: '11px 12px',
    borderRadius: 6,
    fontFamily: 'inherit',
    fontSize: 13,
    width: '100%',
    boxSizing: 'border-box',
    minHeight: 44,
  },
  btn: {
    background: '#10b981',
    color: '#000',
    border: 'none',
    padding: '12px 18px',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: 12,
    letterSpacing: 1,
    whiteSpace: 'nowrap',
    minHeight: 44,
    width: '100%',
  },
  btnSm: {
    background: '#10b981',
    color: '#000',
    border: 'none',
    padding: '10px 14px',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: 11,
    letterSpacing: 1,
    minHeight: 44,
  },
  btnOutline: (active) => ({
    background: active ? '#10b981' : 'transparent',
    color: active ? '#000' : '#10b981',
    border: '1px solid #10b981',
    padding: '10px 14px',
    borderRadius: 6,
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: 11,
    letterSpacing: 1,
    minHeight: 44,
  }),
  verdict: (score) => ({
    marginTop: 14,
    padding: '12px 14px',
    borderRadius: 6,
    fontWeight: 'bold',
    fontSize: 14,
    background: score >= 70 ? '#064e3b' : score >= 50 ? '#78350f' : '#450a0a',
    color: score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444',
    borderLeft: `4px solid ${score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'}`,
  }),
  // Bottom nav bar
  bottomNav: {
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
    background: '#111827',
    borderTop: '1px solid #1f2937',
    display: 'flex',
    zIndex: 100,
  },
  navBtn: (active) => ({
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '10px 4px',
    minHeight: 56,
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
    color: active ? '#10b981' : '#6b7280',
    fontSize: 9,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    borderTop: active ? '2px solid #10b981' : '2px solid transparent',
    gap: 3,
  }),
  navIcon: { fontSize: 18, lineHeight: 1 },
  signalBadge: (type) => {
    const map = {
      steam: { bg: '#064e3b', color: '#10b981' },
      rlm: { bg: '#1e1b4b', color: '#818cf8' },
      fade: { bg: '#78350f', color: '#f59e0b' },
      value: { bg: '#064e3b', color: '#10b981' },
      sharp: { bg: '#1e1b4b', color: '#818cf8' },
      weather: { bg: '#0c4a6e', color: '#38bdf8' },
      regression: { bg: '#450a0a', color: '#ef4444' },
      halftime: { bg: '#064e3b', color: '#10b981' },
    }
    const c = map[type] || { bg: '#1f2937', color: '#e2e8f0' }
    return {
      display: 'inline-block',
      background: c.bg,
      color: c.color,
      fontSize: 10,
      fontWeight: 'bold',
      padding: '2px 8px',
      borderRadius: 4,
      letterSpacing: 1,
      textTransform: 'uppercase',
    }
  },
}

// ── Shared components ────────────────────────────────────────────────────────

function Stat({ label, value, color }) {
  return (
    <div style={S.card}>
      <div style={S.label}>{label}</div>
      <div style={{ ...S.value, ...(color || {}) }}>{value ?? '—'}</div>
    </div>
  )
}

function StatusDot({ ok }) {
  return (
    <span
      style={{
        width: 8, height: 8, borderRadius: '50%',
        background: ok ? '#10b981' : '#6b7280',
        display: 'inline-block', marginRight: 6, flexShrink: 0,
      }}
    />
  )
}

function SectionHeader({ title, sub }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 13, fontWeight: 'bold', color: '#f9fafb', letterSpacing: 1, textTransform: 'uppercase' }}>{title}</div>
      {sub && <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function EmptyState({ msg }) {
  return (
    <div style={{ ...S.card, color: '#6b7280', fontSize: 13, textAlign: 'center', padding: 24 }}>{msg}</div>
  )
}

function ErrorMsg({ msg }) {
  return <div style={{ color: '#f59e0b', marginBottom: 12, fontSize: 12 }}>{msg}</div>
}

function SignalCard({ badge, title, detail, score, meta }) {
  return (
    <div style={S.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <span style={{ fontWeight: 'bold', fontSize: 14 }}>{title}</span>
        {badge && <span style={S.signalBadge(badge)}>{badge}</span>}
      </div>
      {detail && <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>{detail}</div>}
      {meta && <div style={{ fontSize: 11, color: '#6b7280' }}>{meta}</div>}
      {score !== undefined && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, background: '#1f2937', borderRadius: 4, height: 6 }}>
            <div style={{ width: `${Math.min(100, score)}%`, height: 6, borderRadius: 4, background: score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444' }} />
          </div>
          <span style={{ fontSize: 11, color: '#9ca3af', minWidth: 32 }}>{score}%</span>
        </div>
      )}
    </div>
  )
}

// ── Panels ───────────────────────────────────────────────────────────────────

function OddsPanel() {
  const [sport, setSport] = useState('mlb')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadCached = async (s) => {
    setLoading(true); setError(null)
    try { const r = await api.getCachedOdds(s); setData(r.data) }
    catch { setError('No cached odds yet — tap FETCH LIVE to load.'); setData([]) }
    setLoading(false)
  }
  const fetchLive = async () => {
    setLoading(true); setError(null)
    try { const r = await api.getLiveOdds(sport); setData(r.data) }
    catch { setError('API key required — add ODDS_API_KEY to backend/.env') }
    setLoading(false)
  }

  useEffect(() => { loadCached(sport) }, [sport])

  const sports = ['mlb', 'nba', 'nhl', 'ncaa']
  const sportKeys = { mlb: 'mlb', nba: 'nba', nhl: 'nhl', ncaa: 'ncaa_basketball' }

  return (
    <div>
      <SectionHeader title="Live Odds" sub="Market prices across major sportsbooks" />
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {sports.map(s => (
          <button key={s} style={S.btnOutline(sport === s)} onClick={() => { setSport(sportKeys[s]); setData(null) }}>
            {s.toUpperCase()}
          </button>
        ))}
      </div>
      <button style={{ ...S.btn, marginBottom: 14 }} onClick={fetchLive} disabled={loading}>
        {loading ? 'LOADING...' : 'FETCH LIVE ODDS'}
      </button>
      {error && <ErrorMsg msg={error} />}
      {data && data.length === 0 && !error && (
        <EmptyState msg="No data. Tap FETCH LIVE ODDS (requires Odds API key in backend/.env)." />
      )}
      {data && data.slice(0, 20).map((game, i) => (
        <div key={i} style={S.card}>
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 'bold', fontSize: 14 }}>{game.home_team} vs {game.away_team}</div>
            <div style={{ color: '#6b7280', fontSize: 11, marginTop: 2 }}>{game.commence_time?.slice(0, 10)}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {game.bookmakers?.slice(0, 5).map((book, j) => (
              <div key={j} style={{ fontSize: 12, background: '#1f2937', borderRadius: 4, padding: '6px 10px', minWidth: 80 }}>
                <span style={{ color: '#6b7280', display: 'block', marginBottom: 2, fontSize: 10 }}>{book.title}</span>
                {book.markets?.[0]?.outcomes?.map(o => (
                  <div key={o.name} style={{ color: o.price > 0 ? '#10b981' : '#e2e8f0', fontSize: 12 }}>
                    {o.name.split(' ').pop()} <strong>{o.price > 0 ? '+' : ''}{o.price}</strong>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function MatchupPanel() {
  const [batterId, setBatterId] = useState('660271')
  const [pitcherId, setPitcherId] = useState('621111')
  const [bookLine, setBookLine] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const analyze = async () => {
    setLoading(true)
    try {
      const r = await api.analyzeHitProp(batterId, pitcherId, bookLine ? parseInt(bookLine) : undefined)
      setResult(r.data)
    } catch { setResult({ error: 'MLB API error — check player IDs' }) }
    setLoading(false)
  }

  const score = result ? Math.round((result.our_hit_probability || 0) * 100) : 0

  return (
    <div>
      <SectionHeader title="Matchup / Props" sub="MLB hit probability vs pitcher — find batter edge" />
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
        Find IDs at mlb.com/players — Spencer Steer = 660271
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div>
          <div style={S.label}>Batter ID</div>
          <input style={S.input} value={batterId} onChange={e => setBatterId(e.target.value)} />
        </div>
        <div>
          <div style={S.label}>Pitcher ID</div>
          <input style={S.input} value={pitcherId} onChange={e => setPitcherId(e.target.value)} />
        </div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={S.label}>Book Line (optional)</div>
        <input style={S.input} value={bookLine} onChange={e => setBookLine(e.target.value)} placeholder="-130 or +110" />
      </div>
      <button style={S.btn} onClick={analyze}>{loading ? 'ANALYZING...' : 'ANALYZE MATCHUP'}</button>

      {result && !result.error && (
        <div style={{ marginTop: 16 }}>
          <div style={S.grid4}>
            <Stat label="Hit Probability" value={`${(result.our_hit_probability * 100).toFixed(1)}%`} color={result.our_hit_probability >= 0.38 ? S.green : S.red} />
            <Stat label="Batter AVG" value={result.batter_avg} />
            <Stat label="Pitcher ERA" value={result.pitcher_era} color={result.pitcher_era >= 5 ? S.green : result.pitcher_era <= 3 ? S.red : {}} />
            <Stat label="WHIP" value={result.pitcher_whip} color={result.pitcher_whip >= 1.5 ? S.green : result.pitcher_whip <= 1.1 ? S.red : {}} />
          </div>
          {result.ev_pct !== undefined && (
            <div style={S.grid3}>
              <Stat label="Book Line" value={result.book_line > 0 ? `+${result.book_line}` : result.book_line} />
              <Stat label="Book Implied" value={`${(result.book_implied_prob * 100).toFixed(1)}%`} />
              <Stat label="Edge (EV%)" value={`${result.ev_pct > 0 ? '+' : ''}${result.ev_pct}%`} color={result.ev_pct > 0 ? S.green : S.red} />
            </div>
          )}
          <div style={S.verdict(score)}>{result.edge_label}</div>
          {result.value_bet && (
            <div style={{ marginTop: 8, color: '#10b981', fontSize: 13, fontWeight: 'bold' }}>
              VALUE BET — model shows +5% edge over book price
            </div>
          )}
        </div>
      )}
      {result?.error && <div style={{ color: '#ef4444', marginTop: 12, fontSize: 13 }}>{result.error}</div>}
    </div>
  )
}

function BankrollPanel() {
  const [bankroll, setBankroll] = useState('1000')
  const [prob, setProb] = useState('0.55')
  const [odds, setOdds] = useState('-110')
  const [result, setResult] = useState(null)

  const calc = async () => {
    try {
      const r = await api.getKelly(parseFloat(bankroll), parseFloat(prob), parseInt(odds))
      setResult(r.data)
    } catch (e) { console.error(e) }
  }

  return (
    <div>
      <SectionHeader title="Kelly Sizer" sub="Mathematically optimal bet sizing based on your edge" />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div>
          <div style={S.label}>Bankroll ($)</div>
          <input style={S.input} value={bankroll} onChange={e => setBankroll(e.target.value)} />
        </div>
        <div>
          <div style={S.label}>Win Probability</div>
          <input style={S.input} value={prob} onChange={e => setProb(e.target.value)} placeholder="0.55 = 55%" />
        </div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={S.label}>American Odds</div>
        <input style={S.input} value={odds} onChange={e => setOdds(e.target.value)} />
      </div>
      <button style={S.btn} onClick={calc}>CALCULATE KELLY</button>
      {result && (
        <div style={{ marginTop: 16 }}>
          <div style={S.grid3}>
            <Stat label="Recommended (1/4 Kelly)" value={`$${result.recommended_bet}`} color={S.green} />
            <Stat label="Kelly % of Bankroll" value={`${result.quarter_kelly_pct}%`} />
            <Stat label="Full Kelly (aggressive)" value={`$${result.max_bet_full_kelly}`} color={S.yellow} />
          </div>
          <div style={{ ...S.card, color: '#6b7280', fontSize: 12 }}>
            Use 1/4 Kelly for safety. Full Kelly causes massive drawdowns even with a real edge. Never risk more than 5% of bankroll on a single game.
          </div>
        </div>
      )}
    </div>
  )
}

function CLVPanel() {
  const [report, setReport] = useState(null)
  useEffect(() => {
    api.getCLVReport().then(r => setReport(r.data)).catch(() => {})
  }, [])
  return (
    <div>
      <SectionHeader title="CLV Tracker" sub="Closing Line Value — the #1 indicator of long-term profit" />
      {report && report.count > 0 ? (
        <div style={S.grid4}>
          <Stat label="Total Bets" value={report.total_bets} />
          <Stat label="Avg CLV" value={`${report.avg_clv > 0 ? '+' : ''}${report.avg_clv}%`} color={report.avg_clv > 0 ? S.green : S.red} />
          <Stat label="Positive CLV Rate" value={`${report.positive_clv_pct}%`} color={report.positive_clv_pct > 50 ? S.green : S.red} />
          <Stat label="Verdict" value={report.verdict} color={report.avg_clv > 0 ? S.green : S.yellow} />
        </div>
      ) : (
        <EmptyState msg="No bets logged yet. Use POST /clv/log-bet to start tracking your CLV." />
      )}
    </div>
  )
}

// ── Sharp Signals panel ──────────────────────────────────────────────────────

function SharpSignalsPanel() {
  const [steam, setSteam] = useState(null)
  const [rlm, setRlm] = useState(null)
  const [fade, setFade] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadAll = async () => {
    setLoading(true); setError(null)
    try {
      const [sRes, rRes, fRes] = await Promise.allSettled([
        api.getSteamMoves(),
        api.getRLM(),
        api.getPublicFade(),
      ])
      if (sRes.status === 'fulfilled') setSteam(sRes.value.data)
      if (rRes.status === 'fulfilled') setRlm(rRes.value.data)
      if (fRes.status === 'fulfilled') setFade(fRes.value.data)
      if (sRes.status === 'rejected' && rRes.status === 'rejected' && fRes.status === 'rejected') {
        // Fallback: try the combined endpoint
        const r = await api.getSharpSignals()
        setSteam(r.data?.steam_moves || [])
        setRlm(r.data?.rlm || [])
        setFade(r.data?.public_fade || [])
      }
    } catch (e) {
      setError('Sharp signal endpoints not available — backend may need updating.')
    }
    setLoading(false)
  }

  useEffect(() => { loadAll() }, [])

  const renderList = (items, badge) => {
    if (!items) return <div style={{ color: '#6b7280', fontSize: 12 }}>Loading...</div>
    if (!Array.isArray(items) || items.length === 0) return <EmptyState msg="No signals right now." />
    return items.map((item, i) => (
      <SignalCard
        key={i}
        badge={badge}
        title={item.game || item.team || item.matchup || `Signal ${i + 1}`}
        detail={item.description || item.detail || item.note}
        meta={[item.time, item.book, item.line].filter(Boolean).join(' · ')}
        score={item.confidence_score || item.score}
      />
    ))
  }

  return (
    <div>
      <SectionHeader title="Sharp Signals" sub="Steam moves, RLM, and public fade alerts in one place" />
      <button style={{ ...S.btn, marginBottom: 16 }} onClick={loadAll} disabled={loading}>
        {loading ? 'REFRESHING...' : 'REFRESH SIGNALS'}
      </button>
      {error && <ErrorMsg msg={error} />}

      <div style={{ marginBottom: 8, fontSize: 11, color: '#10b981', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Steam Moves
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Line moved fast — sharp money hit one side quickly
      </div>
      {renderList(steam, 'steam')}

      <div style={{ marginTop: 20, marginBottom: 8, fontSize: 11, color: '#818cf8', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Reverse Line Movement
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Public bets one side but line moves the other — sharp action
      </div>
      {renderList(rlm, 'rlm')}

      <div style={{ marginTop: 20, marginBottom: 8, fontSize: 11, color: '#f59e0b', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Public Fade
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Heavy public side with sharp money on the other — fade the public
      </div>
      {renderList(fade, 'fade')}
    </div>
  )
}

// ── All Signals panel ────────────────────────────────────────────────────────

function AllSignalsPanel() {
  const [regression, setRegression] = useState(null)
  const [halftime, setHalftime] = useState(null)
  const [weather, setWeather] = useState(null)
  const [sport, setSport] = useState('mlb')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadAll = async (s) => {
    setLoading(true); setError(null)
    const results = await Promise.allSettled([
      api.getRegression(s),
      api.getNBAHalftime(),
      api.getWeather(),
    ])
    if (results[0].status === 'fulfilled') setRegression(results[0].value.data)
    else setRegression([])
    if (results[1].status === 'fulfilled') setHalftime(results[1].value.data)
    else setHalftime([])
    if (results[2].status === 'fulfilled') setWeather(results[2].value.data)
    else setWeather([])
    if (results.every(r => r.status === 'rejected')) {
      setError('Signal endpoints not available yet — check backend routes.')
    }
    setLoading(false)
  }

  useEffect(() => { loadAll(sport) }, [sport])

  const sports = ['mlb', 'nba', 'nhl', 'ncaa']

  const renderList = (items, badge, emptyMsg) => {
    if (!items) return <div style={{ color: '#6b7280', fontSize: 12 }}>Loading...</div>
    if (!Array.isArray(items) || items.length === 0) return <EmptyState msg={emptyMsg} />
    return items.map((item, i) => (
      <SignalCard
        key={i}
        badge={badge}
        title={item.game || item.team || item.matchup || `Signal ${i + 1}`}
        detail={item.description || item.detail || item.edge}
        meta={[item.stat, item.expected, item.actual].filter(Boolean).join(' · ')}
        score={item.confidence_score || item.score}
      />
    ))
  }

  return (
    <div>
      <SectionHeader title="All Signals" sub="Regression to mean, NBA halftime edges, weather impacts" />
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {sports.map(s => (
          <button key={s} style={S.btnOutline(sport === s)} onClick={() => setSport(s)}>
            {s.toUpperCase()}
          </button>
        ))}
      </div>
      <button style={{ ...S.btn, marginBottom: 16 }} onClick={() => loadAll(sport)} disabled={loading}>
        {loading ? 'LOADING...' : 'REFRESH'}
      </button>
      {error && <ErrorMsg msg={error} />}

      <div style={{ marginBottom: 8, fontSize: 11, color: '#ef4444', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Regression to Mean
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Teams/players performing far from their true talent level — bounce-back likely
      </div>
      {renderList(regression, 'regression', 'No regression signals for this sport right now.')}

      <div style={{ marginTop: 20, marginBottom: 8, fontSize: 11, color: '#10b981', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        NBA Halftime Edge
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Second-half lines where rest patterns, pace, and score gap create edges
      </div>
      {renderList(halftime, 'halftime', 'No NBA halftime signals right now.')}

      <div style={{ marginTop: 20, marginBottom: 8, fontSize: 11, color: '#38bdf8', letterSpacing: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Weather Impact
      </div>
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 10 }}>
        Wind, rain, and cold suppressing totals in outdoor games
      </div>
      {renderList(weather, 'weather', 'No significant weather signals right now.')}
    </div>
  )
}

// ── App shell ────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'odds',    label: 'Odds',    icon: '📊' },
  { id: 'sharp',   label: 'Sharp',   icon: '⚡' },
  { id: 'signals', label: 'Signals', icon: '🔍' },
  { id: 'matchup', label: 'Props',   icon: '⚾' },
  { id: 'bankroll',label: 'Kelly',   icon: '💰' },
  { id: 'clv',     label: 'CLV',     icon: '📈' },
]

export default function App() {
  const [tab, setTab] = useState('odds')
  const [apiOk, setApiOk] = useState(null)

  useEffect(() => {
    api.getHealth().then(() => setApiOk(true)).catch(() => setApiOk(false))
  }, [])

  return (
    <div style={S.app}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}>EDGE</div>
          <div style={S.subtitle}>Sports Analytics Engine</div>
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#6b7280', display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          <StatusDot ok={apiOk} />
          {apiOk === null ? 'Connecting...' : apiOk ? 'API Online' : 'API Offline'}
        </div>
      </div>

      {/* Page content */}
      <div style={S.content}>
        {tab === 'odds'     && <OddsPanel />}
        {tab === 'sharp'    && <SharpSignalsPanel />}
        {tab === 'signals'  && <AllSignalsPanel />}
        {tab === 'matchup'  && <MatchupPanel />}
        {tab === 'bankroll' && <BankrollPanel />}
        {tab === 'clv'      && <CLVPanel />}
      </div>

      {/* Bottom navigation */}
      <nav style={S.bottomNav}>
        {TABS.map(t => (
          <button key={t.id} style={S.navBtn(tab === t.id)} onClick={() => setTab(t.id)}>
            <span style={S.navIcon}>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  )
}
