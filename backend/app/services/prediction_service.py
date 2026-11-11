import logging
import pandas as pd

from backend.app.core.config import (
    ALGORITHM_METADATA,
    LOCATION_REGIONS,
    POLLUTANT_METADATA,
    SCENARIO_METADATA,
    settings,
)
from backend.app.schemas.prediction import (
    FeatureInputItem,
    NextHourPredictionResponse,
    PredictionStatus,
)
from backend.app.services.data_service import data_service
from backend.app.services.live_data_service import live_data_service
from backend.app.services.registry_service import registry_service
from src.features.scenarios import resolve_scenario
from src.utils.identifiers import build_experiment_id, slugify_component

logger = logging.getLogger(__name__)

MONTH_NAMES_ID = [
    "", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
]


def format_indo_timestamp(ts):
    """Format a timestamp into a standardized Indonesian display format in WIB (UTC+7)."""
    ts = pd.to_datetime(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("Asia/Jakarta")
    else:
        ts = ts.tz_convert("Asia/Jakarta")
    day = f"{ts.day:02d}"
    month = MONTH_NAMES_ID[ts.month]
    year = ts.year
    hour = f"{ts.hour:02d}"
    minute = f"{ts.minute:02d}"
    return f"{day} {month} {year}, {hour}:{minute} WIB"


def get_feature_display_info(feature_name, pollutant_unit):
    """Return human-readable label and measurement unit for a feature name."""
    labels_map = {
        "carbon_monoxide_lag_1h": ("CO (t-1: 1 Jam Lalu)", pollutant_unit),
        "carbon_monoxide_lag_2h": ("CO (t-2: 2 Jam Lalu)", pollutant_unit),
        "carbon_monoxide_lag_3h": ("CO (t-3: 3 Jam Lalu)", pollutant_unit),
        "carbon_dioxide_lag_1h": ("CO₂ (t-1: 1 Jam Lalu)", pollutant_unit),
        "carbon_dioxide_lag_2h": ("CO₂ (t-2: 2 Jam Lalu)", pollutant_unit),
        "carbon_dioxide_lag_3h": ("CO₂ (t-3: 3 Jam Lalu)", pollutant_unit),
        "temperature_2m_lag_1h": ("Temperatur Udara (t-1)", "°C"),
        "temperature_2m_lag_2h": ("Temperatur Udara (t-2)", "°C"),
        "temperature_2m_lag_3h": ("Temperatur Udara (t-3)", "°C"),
        "relative_humidity_2m_lag_1h": ("Kelembapan Relatif (t-1)", "%"),
        "relative_humidity_2m_lag_2h": ("Kelembapan Relatif (t-2)", "%"),
        "relative_humidity_2m_lag_3h": ("Kelembapan Relatif (t-3)", "%"),
        "rain_lag_1h": ("Curah Hujan (t-1)", "mm"),
        "rain_lag_2h": ("Curah Hujan (t-2)", "mm"),
        "rain_lag_3h": ("Curah Hujan (t-3)", "mm"),
        "wind_speed_100m_lag_1h": ("Kecepatan Angin (t-1)", "m/s"),
        "wind_speed_100m_lag_2h": ("Kecepatan Angin (t-2)", "m/s"),
        "wind_speed_100m_lag_3h": ("Kecepatan Angin (t-3)", "m/s"),
    }
    return labels_map.get(feature_name, (feature_name, pollutant_unit))


# Threshold constants for prediction status evaluation
# CO thresholds based on PP No. 22/2021 (1-Hour National Ambient Standard: 10,000 µg/m³)
CO_THRESHOLD_HALF = 5000.0  # 50% threshold for visual categorization
CO_THRESHOLD_LIMIT = 10000.0  # 1-hour national ambient standard

# CO2 empirical quartile cutoffs derived from 262,980 Jabodetabek observations
CO2_QUARTILE_1 = 449.0  # Q1 (lower 25%)
CO2_QUARTILE_3 = 472.0  # Q3 (upper 25%)


def evaluate_prediction_status(pollutant: str, value: float) -> PredictionStatus:
    """Evaluate concentration status using PP No. 22/2021 for CO and empirical quartiles for CO2."""
    if pollutant.lower() == "co":
        if value <= CO_THRESHOLD_HALF:
            return PredictionStatus(
                status_level="aman",
                category_label="Memenuhi Baku Mutu",
                color="#10b981",
                standard_name="PP No. 22 Tahun 2021 (Baku Mutu CO 1 Jam: 10.000 µg/m³)",
                description="Konsentrasi berada di bawah 50% dari baku mutu CO 1 jam nasional.",
                is_official_standard=True,
            )
        elif value <= CO_THRESHOLD_LIMIT:
            return PredictionStatus(
                status_level="perhatian",
                category_label="Mendekati Baku Mutu",
                color="#f59e0b",
                standard_name="PP No. 22 Tahun 2021 (Baku Mutu CO 1 Jam: 10.000 µg/m³)",
                description="Konsentrasi masih memenuhi baku mutu CO 1 jam nasional.",
                is_official_standard=True,
            )
        else:
            return PredictionStatus(
                status_level="waspada",
                category_label="Melebihi Baku Mutu",
                color="#ef4444",
                standard_name="PP No. 22 Tahun 2021 (Baku Mutu CO 1 Jam: 10.000 µg/m³)",
                description="Konsentrasi melebihi baku mutu CO 1 jam nasional sebesar 10.000 µg/m³.",
                is_official_standard=True,
            )
    else:
        # CO2 empirical quartile evaluation (Q1 = 449 ppm, Q3 = 472 ppm based on 262,980 Jabodetabek observations)
        if value <= CO2_QUARTILE_1:
            return PredictionStatus(
                status_level="aman",
                category_label="Rendah Relatif",
                color="#10b981",
                standard_name="Distribusi empiris data referensi Jabodetabek (Q1 = 449 ppm, Q3 = 472 ppm)",
                description="Termasuk dalam 25% konsentrasi terendah berdasarkan distribusi empiris data referensi Jabodetabek.",
                is_official_standard=False,
            )
        elif value <= CO2_QUARTILE_3:
            return PredictionStatus(
                status_level="perhatian",
                category_label="Tipikal Relatif",
                color="#3b82f6",
                standard_name="Distribusi empiris data referensi Jabodetabek (Q1 = 449 ppm, Q3 = 472 ppm)",
                description="Berada dalam rentang 50% nilai pusat distribusi historis Jabodetabek (Interquartile Range).",
                is_official_standard=False,
            )
        else:
            return PredictionStatus(
                status_level="waspada",
                category_label="Tinggi Relatif",
                color="#ef4444",
                standard_name="Distribusi empiris data referensi Jabodetabek (Q1 = 449 ppm, Q3 = 472 ppm)",
                description="Termasuk dalam 25% konsentrasi tertinggi berdasarkan distribusi empiris data referensi Jabodetabek.",
                is_official_standard=False,
            )


class PredictionService:
    def __init__(self):
        """Initialize prediction service with registry, historical, and live data services."""
        self.registry = registry_service
        self.data_service = data_service
        self.live_service = live_data_service
        self.supported_locations = {loc["id"]: loc for loc in settings.get_locations()}

    def predict_next_hour(self, request):
        """Execute next-hour prediction using the best or specified model."""
        loc_slug = slugify_component(request.location)
        if loc_slug not in self.supported_locations:
            valid_locs = ", ".join(self.supported_locations.keys())
            raise ValueError(f"Unknown location '{request.location}'. Valid locations are: {valid_locs}")

        best_entry = self.registry.get_best_model(loc_slug, request.pollutant, request.scenario)
        best_algo = best_entry["best_algorithm"]

        requested_algo = request.algorithm
        if requested_algo is None or requested_algo == "auto":
            effective_algo = best_algo
            is_final = True
            model_status = "Final deployment model"
        elif requested_algo == best_algo:
            effective_algo = best_algo
            is_final = True
            model_status = "Final deployment model"
        else:
            effective_algo = requested_algo
            is_final = False
            model_status = "Experiment model (Diagnostic)"

        loc_info = self.supported_locations[loc_slug]
        pollutant_info = POLLUTANT_METADATA[request.pollutant]
        scenario_info = SCENARIO_METADATA[request.scenario]
        algorithm_info = ALGORITHM_METADATA[effective_algo]

        reference_time = request.reference_datetime or request.end_datetime
        use_live = False
        if reference_time is None:
            use_live = True
        else:
            try:
                ref_ts = pd.to_datetime(reference_time)
                loc_df = self.data_service.get_location_observations(loc_slug, request.pollutant)
                max_dt = loc_df["datetime"].max()
                if ref_ts.tzinfo is None:
                    ref_ts = ref_ts.tz_localize(max_dt.tz)
                else:
                    ref_ts = ref_ts.tz_convert(max_dt.tz)
                if ref_ts > max_dt:
                    use_live = True
            except Exception:
                use_live = False

        if request.client_live_features is not None:
            scenario_def = resolve_scenario(request.pollutant, request.scenario)
            ordered_features = list(scenario_def.feature_names)
            feat_vals = request.client_live_features.feature_values
            row_dict = {col: [float(feat_vals.get(col, 0.0))] for col in ordered_features}
            X_df = pd.DataFrame(row_dict)[ordered_features]

            target_dt = pd.to_datetime(request.client_live_features.target_prediction_time)
            latest_dt = pd.to_datetime(request.client_live_features.latest_observation_time)
            if target_dt.tzinfo is None:
                target_dt = target_dt.tz_localize("Asia/Jakarta")
            else:
                target_dt = target_dt.tz_convert("Asia/Jakarta")
            if latest_dt.tzinfo is None:
                latest_dt = latest_dt.tz_localize("Asia/Jakarta")
            else:
                latest_dt = latest_dt.tz_convert("Asia/Jakarta")

            meta = {
                "latest_observation_time": latest_dt,
                "latest_observation_value": float(request.client_live_features.latest_observation_value),
                "target_prediction_time": target_dt,
                "feature_values": {col: float(X_df[col].iloc[0]) for col in ordered_features},
                "is_live_data": True,
            }
        elif use_live:
            X_df, meta = self.live_service.build_live_features(
                loc_slug,
                request.pollutant,
                request.scenario,
            )
        else:
            X_df, meta = self.data_service.build_next_hour_features(
                loc_slug,
                request.pollutant,
                request.scenario,
                reference_datetime=reference_time,
            )

        if is_final:
            model = self.registry.load_final_estimator(
                loc_slug,
                request.pollutant,
                request.scenario,
            )
        else:
            model = self.registry.load_estimator(
                loc_slug,
                request.pollutant,
                request.scenario,
                effective_algo,
            )

        pred_raw = float(model.predict(X_df)[0])
        pred_value = round(pred_raw, 2)

        latest_val = round(meta["latest_observation_value"], 2)
        delta_val = round(pred_value - latest_val, 2)
        delta_pct = round((delta_val / latest_val) * 100, 2) if latest_val != 0 else 0.0

        if delta_val > (0.02 * latest_val):
            trend = "naik"
        elif delta_val < -(0.02 * latest_val):
            trend = "turun"
        else:
            trend = "stabil"

        feature_inputs = []
        for col_name, val in meta["feature_values"].items():
            label, unit = get_feature_display_info(col_name, pollutant_info["unit"])
            feature_inputs.append(
                FeatureInputItem(
                    name=col_name,
                    label=label,
                    value=round(val, 2),
                    unit=unit,
                )
            )

        counterpart_algo = self.registry.get_counterpart_algorithm(effective_algo)
        counterpart_meta = ALGORITHM_METADATA.get(counterpart_algo, {})
        cp_pred_value = None
        cp_delta = None

        try:
            cp_model = self.registry.load_estimator(
                loc_slug,
                request.pollutant,
                request.scenario,
                counterpart_algo,
            )
            cp_raw = float(cp_model.predict(X_df)[0])
            cp_pred_value = round(cp_raw, 2)
            cp_delta = round(pred_value - cp_pred_value, 2)
        except Exception as e:
            logger.warning("Could not compute counterpart next-hour prediction: %s", e)

        target_ts = meta["target_prediction_time"]
        latest_ts = meta["latest_observation_time"]

        experiment_id = build_experiment_id(
            loc_slug,
            request.pollutant,
            request.scenario,
            effective_algo,
        )

        pred_status = evaluate_prediction_status(request.pollutant, pred_value)

        return NextHourPredictionResponse(
            experiment_id=experiment_id,
            location=loc_slug,
            location_name=loc_info["name"],
            region=LOCATION_REGIONS.get(loc_slug, "Jabodetabek"),
            latitude=loc_info["latitude"],
            longitude=loc_info["longitude"],
            pollutant=request.pollutant,
            pollutant_label=pollutant_info["label"],
            pollutant_unit=pollutant_info["unit"],
            scenario=request.scenario,
            scenario_label=scenario_info["label"],
            algorithm=effective_algo,
            algorithm_label=algorithm_info["label"],
            predicted_value=pred_value,
            target_time=target_ts.isoformat(),
            target_time_display=format_indo_timestamp(target_ts),
            latest_observation_time=latest_ts.isoformat(),
            latest_observation_display=format_indo_timestamp(latest_ts),
            latest_observation_value=latest_val,
            delta_value=delta_val,
            delta_percentage=delta_pct,
            trend=trend,
            status=pred_status,
            feature_inputs=feature_inputs,
            counterpart_algorithm=counterpart_algo,
            counterpart_label=counterpart_meta.get("label", counterpart_algo.upper()),
            counterpart_predicted_value=cp_pred_value,
            counterpart_delta=cp_delta,
            model_status=model_status,
            is_final_model=is_final,
            best_algorithm=best_algo,
            is_live_data=meta.get("is_live_data", False),
            live_data_error=meta.get("live_data_error"),
        )


prediction_service = PredictionService()
