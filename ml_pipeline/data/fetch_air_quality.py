"""Open-Meteo Air Quality request builder; no download occurs on import."""

from typing import Any

import httpx

from ml_pipeline.utils.config import load_yaml_config


AIR_QUALITY_VARIABLES = {
    "co": "carbon_monoxide",
    "co2": "carbon_dioxide",
}


def build_air_quality_params(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    pollutant: str,
) -> dict[str, Any]:
    """Build explicit CAMS/Open-Meteo query parameters for one location."""

    if pollutant not in AIR_QUALITY_VARIABLES:
        raise ValueError(f"Unsupported pollutant: {pollutant}")
    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": AIR_QUALITY_VARIABLES[pollutant],
        "domains": "cams_global",
        "timezone": "Asia/Jakarta",
    }


def fetch_air_quality(params: dict[str, Any], *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    """Fetch one response; callers are responsible for preserving raw payloads."""

    url = load_yaml_config("data.yaml")["sources"]["air_quality"]["base_url"]
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()
