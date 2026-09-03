"""Open-Meteo Historical Weather request builder; no download occurs on import."""

from typing import Any

import httpx

from ml_pipeline.utils.config import load_yaml_config


WEATHER_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_100m",
)


def build_weather_params(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Build Open-Meteo historical-weather parameters for one location."""

    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(WEATHER_VARIABLES),
        "timezone": "Asia/Jakarta",
    }


def fetch_weather(params: dict[str, Any], *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Fetch one response; callers are responsible for preserving raw payloads."""

    url = load_yaml_config("data.yaml")["sources"]["weather"]["base_url"]
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()
