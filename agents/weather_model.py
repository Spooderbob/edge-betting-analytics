# MLB Weather impact model
# Wind out 15+ mph = +1 run to expected total (OVER lean)
# Wind in 15+ mph = -1 run (UNDER lean)
# Temp < 50F = -0.5 runs
# Uses Open-Meteo API (free, no key needed)

import httpx
import asyncio
from typing import Optional

# MLB stadium coordinates for weather lookup
STADIUM_COORDS = {
    "wrigley": (41.9484, -87.6553),      # Chicago Cubs - extreme wind effects
    "oracle": (37.7786, -122.3893),       # SF Giants - wind off bay
    "coors": (39.7559, -104.9942),        # Colorado - altitude increases HR
    "fenway": (42.3467, -71.0972),        # Boston
    "yankee": (40.8296, -73.9262),        # New York Yankees
    "dodger": (34.0739, -118.2400),       # LA Dodgers
    "pnc": (40.4469, -80.0057),           # Pittsburgh
    "great_american": (39.0979, -84.5082), # Cincinnati
    "globe_life": (32.7512, -97.0832),    # Texas Rangers - heat
    "kauffman": (39.0517, -94.4803),      # Kansas City
}

PARK_FACTORS = {
    "coors": 1.35,      # 35% more runs at altitude
    "great_american": 1.12,
    "globe_life": 1.08,
    "fenway": 1.05,
    "yankee": 1.04,
    "wrigley": 1.02,    # varies wildly by wind
    "oracle": 0.92,     # pitcher friendly
    "pnc": 0.96,
}


async def get_weather(lat: float, lon: float) -> dict:
    """Fetch current weather from Open-Meteo (free, no API key)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,wind_speed_10m,wind_direction_10m,precipitation",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "forecast_days": 1,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        current = data.get("current", {})
        return {
            "temp_f": current.get("temperature_2m"),
            "wind_mph": current.get("wind_speed_10m"),
            "wind_dir": current.get("wind_direction_10m"),
            "precip_mm": current.get("precipitation"),
        }


def wind_run_adjustment(wind_mph: float, wind_dir_deg: float,
                        stadium_orientation_deg: float = 0) -> float:
    """
    Calculate run adjustment based on wind.
    wind_dir_deg: direction wind is blowing FROM (meteorological)
    stadium_orientation_deg: direction from home plate to center field
    Returns: run adjustment (positive = more runs, negative = fewer)
    """
    import math

    # Convert to radians and find relative angle
    wind_rad = math.radians(wind_dir_deg)
    stadium_rad = math.radians(stadium_orientation_deg)

    # Dot product to find how much wind is blowing toward/away from CF
    # Positive = blowing OUT (more runs), Negative = blowing IN (fewer runs)
    alignment = math.cos(wind_rad - stadium_rad)

    if wind_mph < 5:
        return 0.0
    elif wind_mph < 10:
        return alignment * 0.3
    elif wind_mph < 15:
        return alignment * 0.6
    elif wind_mph < 20:
        return alignment * 1.0
    else:
        return alignment * 1.3


def temperature_run_adjustment(temp_f: float) -> float:
    """Cold air = denser = ball doesn't carry as far."""
    if temp_f >= 75:
        return 0.3
    elif temp_f >= 65:
        return 0.1
    elif temp_f >= 55:
        return 0.0
    elif temp_f >= 45:
        return -0.4
    else:
        return -0.7


async def analyze_game_weather(stadium: str, game_total: float) -> dict:
    """Full weather analysis for a MLB game."""
    coords = STADIUM_COORDS.get(stadium.lower())
    if not coords:
        return {"error": f"Stadium '{stadium}' not in database"}

    weather = await get_weather(*coords)
    park_factor = PARK_FACTORS.get(stadium.lower(), 1.00)

    wind_adj = wind_run_adjustment(
        weather.get("wind_mph", 0),
        weather.get("wind_dir", 0),
    )
    temp_adj = temperature_run_adjustment(weather.get("temp_f", 65))
    total_adj = wind_adj + temp_adj

    adjusted_total = game_total + total_adj

    return {
        "stadium": stadium,
        "weather": weather,
        "park_factor": park_factor,
        "wind_adjustment": round(wind_adj, 2),
        "temp_adjustment": round(temp_adj, 2),
        "total_adjustment": round(total_adj, 2),
        "book_total": game_total,
        "weather_adjusted_total": round(adjusted_total, 1),
        "bet": (
            f"OVER {game_total} — weather adds ~{total_adj:.1f} runs" if total_adj >= 0.7
            else f"UNDER {game_total} — weather removes ~{abs(total_adj):.1f} runs" if total_adj <= -0.7
            else "No significant weather edge"
        ),
        "confidence": "HIGH" if abs(total_adj) >= 1.2 else "MEDIUM" if abs(total_adj) >= 0.7 else "LOW",
    }
