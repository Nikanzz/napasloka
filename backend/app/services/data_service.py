"""Data service for loading processed observation datasets and preparing lag feature vectors."""

import logging
import threading
import pandas as pd

from backend.app.core.config import settings
from src.features.scenarios import resolve_scenario
from src.utils.identifiers import slugify_component

logger = logging.getLogger(__name__)


class DataService:
    """Manages processed historical observation datasets and builds lag feature vectors."""

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        self.locations_map = {loc["id"]: loc for loc in settings.get_locations()}

    def get_coordinate_id(self, location_id):
        """Resolve location slug to coordinate string matching dataset format."""
        loc_slug = slugify_component(location_id)
        if loc_slug in self.locations_map:
            loc = self.locations_map[loc_slug]
            lat = loc["latitude"]
            lon = loc["longitude"]
            return f"{lat}_{lon}"
        return location_id

    def load_dataset(self, pollutant):
        """Load and cache processed observations DataFrame in memory."""
        file_name = "jabodetabek_co_dataset.csv" if pollutant.lower() == "co" else "jabodetabek_co2_dataset.csv"
        with self._lock:
            if file_name not in self._cache:
                data_path = settings.processed_data_dir / file_name
                if not data_path.is_file():
                    raise FileNotFoundError(f"Processed dataset not found: {data_path}")

                logger.info("Loading processed dataset into memory from: %s", data_path)
                df = pd.read_csv(data_path)
                df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Jakarta")
                self._cache[file_name] = df

            return self._cache[file_name]

    def get_location_observations(self, location_id, pollutant):
        """Filter dataset for a specific location, sorted chronologically."""
        df = self.load_dataset(pollutant)
        coord_id = self.get_coordinate_id(location_id)
        mask = (df["location"] == coord_id) | (df["location"] == location_id)
        loc_df = df[mask].sort_values("datetime").reset_index(drop=True)

        if loc_df.empty:
            raise ValueError(f"Tidak ada data observasi untuk lokasi '{location_id}' (koordinat: {coord_id}).")

        return loc_df

    def build_next_hour_features(self, location_id, pollutant, scenario, reference_datetime=None):
        """Construct lag feature row for next-hour forecast (t+1) based on observations up to t."""
        loc_df = self.get_location_observations(location_id, pollutant)
        ref_tz = loc_df["datetime"].dt.tz

        if reference_datetime is not None:
            ref_ts = pd.to_datetime(reference_datetime)
            if ref_ts.tzinfo is None:
                ref_ts = ref_ts.tz_localize(ref_tz)
            else:
                ref_ts = ref_ts.tz_convert(ref_tz)
            loc_df = loc_df[loc_df["datetime"] <= ref_ts].reset_index(drop=True)

        if len(loc_df) < 3:
            raise ValueError("Data observasi tidak mencukupi (minimal 3 observasi berurutan diperlukan untuk lag 1-3).")

        # The last 3 rows:
        # row_t: observation at time t (most recent) -> corresponds to lag_1h for forecasting t+1
        # row_t_minus_1: observation at t-1h -> corresponds to lag_2h for forecasting t+1
        # row_t_minus_2: observation at t-2h -> corresponds to lag_3h for forecasting t+1
        last_3 = loc_df.tail(3).reset_index(drop=True)
        row_t_minus_2 = last_3.iloc[0]
        row_t_minus_1 = last_3.iloc[1]
        row_t = last_3.iloc[2]

        scenario_def = resolve_scenario(pollutant, scenario)
        pollutant_col = scenario_def.pollutant_column

        feature_dict = {}
        # Lag order: lag_3h, lag_2h, lag_1h
        feature_dict[f"{pollutant_col}_lag_3h"] = [float(row_t_minus_2[pollutant_col])]
        feature_dict[f"{pollutant_col}_lag_2h"] = [float(row_t_minus_1[pollutant_col])]
        feature_dict[f"{pollutant_col}_lag_1h"] = [float(row_t[pollutant_col])]

        if scenario == "scenario_2":
            meteo_vars = ["temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m"]
            for var in meteo_vars:
                feature_dict[f"{var}_lag_3h"] = [float(row_t_minus_2[var])]
                feature_dict[f"{var}_lag_2h"] = [float(row_t_minus_1[var])]
                feature_dict[f"{var}_lag_1h"] = [float(row_t[var])]

        ordered_features = [col for col in scenario_def.feature_names]
        X_df = pd.DataFrame(feature_dict)[ordered_features]

        metadata = {
            "latest_observation_time": row_t["datetime"],
            "latest_observation_value": float(row_t[pollutant_col]),
            "target_prediction_time": row_t["datetime"] + pd.Timedelta(hours=1),
            "feature_values": {col: float(X_df[col].iloc[0]) for col in ordered_features},
        }

        return X_df, metadata


data_service = DataService()
