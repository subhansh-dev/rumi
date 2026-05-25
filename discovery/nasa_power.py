"""NASA POWER API — free climate/energy data, no key needed.

For climate & energy domain. Provides: temperature, solar irradiance,
precipitation, wind speed for any geographic region.
"""

import json
import time
import urllib.request
import urllib.parse

POWER_BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


PARAMETERS = {
    "temperature": "T2M",
    "max_temperature": "T2M_MAX",
    "min_temperature": "T2M_MIN",
    "precipitation": "PRECTOTCORR",
    "solar_irradiance": "ALLSKY_SFC_SW_DWN",
    "wind_speed": "WS2M",
    "humidity": "RH2M",
}


def get_climate_data(lat: float = 40.0, lon: float = -100.0, year: int = 2023) -> dict:
    """Get monthly climate data for a location.

    Defaults to central US. Returns annual averages.
    """
    params = urllib.parse.urlencode({
        "parameters": ",".join(PARAMETERS.values()),
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": year,
        "end": year,
        "format": "JSON",
    })
    url = f"{POWER_BASE}?{params}"
    data = _fetch(url)
    if not data:
        return {}

    props = data.get("properties", {}).get("parameter", {})
    result = {}
    for key, param in PARAMETERS.items():
        values = props.get(param, {})
        monthly = [v for k, v in values.items() if isinstance(v, (int, float))]
        if monthly:
            result[key] = round(sum(monthly) / len(monthly), 2)
    return result


def get_region_summary(region_name: str = "global") -> dict:
    """Get representative climate data for a broad region."""
    regions = {
        "global": (40.0, -100.0),
        "tropical": (0.0, 0.0),
        "arctic": (70.0, 0.0),
        "europe": (50.0, 10.0),
        "asia": (30.0, 100.0),
        "africa": (0.0, 20.0),
        "australia": (-25.0, 135.0),
        "south_america": (-15.0, -60.0),
    }
    coords = regions.get(region_name.lower(), regions["global"])
    return get_climate_data(lat=coords[0], lon=coords[1])


def enrich_entities(graph) -> int:
    """Add climate context to paper entities.

    Returns count of enriched papers (currently 1 global climate snapshot).
    """
    climate = get_region_summary("global")
    if not climate:
        return 0
    graph.climate_data = climate
    return 1
