import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from backend.app.core.config import settings
from backend.app.services.data_service import data_service
from src.features.scenarios import resolve_scenario
from src.utils.identifiers import slugify_component

logger = logging.getLogger(__name__)

# Key format: (lat, lon, YYYY-MM-DD-HH)
_LIVE_CACHE = {}


def _get_current_wib_hour():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m-%d-%H")


def fetch_open_meteo_live(lat, lon):
    hour_key = (round(lat, 4), round(lon, 4), _get_current_wib_hour())
    if hour_key in _LIVE_CACHE:
        return _LIVE_CACHE[hour_key]

    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,rain,wind_speed_100m"
        f"&past_days=2&forecast_days=1&timezone=Asia%2FBangkok"
    )
    air_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=carbon_monoxide,carbon_dioxide"
        f"&past_days=2&forecast_days=1&domains=cams_global&timezone=Asia%2FBangkok"
    )

    with httpx.Client(timeout=8.0) as client:
        w_resp = client.get(weather_url)
        w_resp.raise_for_status()
        w_json = w_resp.json().get("hourly", {})

        a_resp = client.get(air_url)
        a_resp.raise_for_status()
        a_json = a_resp.json().get("hourly", {})

    w_df = pd.DataFrame(w_json)
    a_df = pd.DataFrame(a_json)

    merged = pd.merge(w_df, a_df, on="time", how="inner")
    merged["datetime"] = pd.to_datetime(merged["time"], utc=True).dt.tz_convert("Asia/Jakarta")
    merged = merged.sort_values("datetime").reset_index(drop=True)

    _LIVE_CACHE[hour_key] = merged
    return merged


class LiveDataService:
    def __init__(self):
        self.locations_map = {loc["id"]: loc for loc in settings.get_locations()}

    def build_live_features(self, location_id, pollutant, scenario):
        loc_slug = slugify_component(location_id)
        if loc_slug not in self.locations_map:
            raise ValueError(f"Unknown location '{location_id}'.")

        # Skip remote calls in automated test runners to avoid network dependency.
        if "pytest" in sys.modules or os.getenv("TESTING") == "1":
            return data_service.build_next_hour_features(loc_slug, pollutant, scenario)

        loc = self.locations_map[loc_slug]
        lat, lon = loc["latitude"], loc["longitude"]

        try:
            df = fetch_open_meteo_live(lat, lon)
            now_wib = pd.Timestamp.now(tz="Asia/Jakarta")
            valid_df = df[df["datetime"] <= now_wib].reset_index(drop=True)

            if len(valid_df) < 3:
                valid_df = df.tail(3).reset_index(drop=True)

            last_3 = valid_df.tail(3).reset_index(drop=True)
            row_t_minus_2 = last_3.iloc[0]
            row_t_minus_1 = last_3.iloc[1]
            row_t = last_3.iloc[2]

            scenario_def = resolve_scenario(pollutant, scenario)
            pollutant_col = scenario_def.pollutant_column

            feature_dict = {
                f"{pollutant_col}_lag_3h": [float(row_t_minus_2[pollutant_col])],
                f"{pollutant_col}_lag_2h": [float(row_t_minus_1[pollutant_col])],
                f"{pollutant_col}_lag_1h": [float(row_t[pollutant_col])],
            }

            if scenario == "scenario_2":
                meteo_vars = ["temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m"]
                for var in meteo_vars:
                    feature_dict[f"{var}_lag_3h"] = [float(row_t_minus_2[var])]
                    feature_dict[f"{var}_lag_2h"] = [float(row_t_minus_1[var])]
                    feature_dict[f"{var}_lag_1h"] = [float(row_t[var])]

            ordered_features = list(scenario_def.feature_names)
            X_df = pd.DataFrame(feature_dict)[ordered_features]

            metadata = {
                "latest_observation_time": row_t["datetime"],
                "latest_observation_value": float(row_t[pollutant_col]),
                "target_prediction_time": row_t["datetime"] + pd.Timedelta(hours=1),
                "feature_values": {col: float(X_df[col].iloc[0]) for col in ordered_features},
                "is_live_data": True,
            }
            return X_df, metadata

        except Exception as e:
            logger.warning("Failed to fetch live data from Open-Meteo (%s). Falling back to local data.", e)
            X_df, meta = data_service.build_next_hour_features(loc_slug, pollutant, scenario)
            meta["is_live_data"] = False
            return X_df, meta


live_data_service = LiveDataService()
