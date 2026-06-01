from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from routers import odds, mlb, nba, edges, ev, bankroll, clv, sharp, props, public_fade, signals

app = FastAPI(title="EDGE — Value Betting Engine")

# Allow all origins for Render.com deployment (frontend on separate domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(odds.router, prefix="/odds", tags=["Live Odds"])
app.include_router(mlb.router, prefix="/mlb", tags=["MLB"])
app.include_router(nba.router, prefix="/nba", tags=["NBA"])
app.include_router(edges.router, prefix="/edges", tags=["Edge Finder"])
app.include_router(ev.router, prefix="/ev", tags=["EV Calculator"])
app.include_router(bankroll.router, prefix="/bankroll", tags=["Bankroll"])
app.include_router(clv.router, prefix="/clv", tags=["CLV Tracker"])
app.include_router(sharp.router, prefix="/sharp", tags=["Sharp Signals"])
app.include_router(props.router, prefix="/props", tags=["Props"])
app.include_router(public_fade.router, prefix="/public-fade", tags=["Public Fade"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])


@app.get("/health")
def health():
    return {"ok": True}


# Serve React frontend — must come AFTER all API routes
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file = STATIC_DIR / full_path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def root():
        return {"status": "EDGE engine running", "version": "2.0"}


@app.get("/weather", tags=["Weather"])
def weather(venue: str = ""):
    """
    Placeholder weather endpoint.
    Pass ?venue=<stadium_name> to get conditions for a game location.
    Wire in a real weather API (e.g. Open-Meteo) as needed.
    """
    return {
        "venue": venue,
        "conditions": "clear",
        "temp_f": None,
        "wind_mph": None,
        "note": "Weather data not yet configured. Integrate Open-Meteo or WeatherAPI here.",
    }
