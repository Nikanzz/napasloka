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
    AirQualityAssessment,
    FeatureInputItem,
    NextHourPredictionResponse,
    PredictionRequest,
)
from backend.app.services.data_service import data_service
from backend.app.services.live_data_service import live_data_service
from backend.app.services.registry_service import registry_service
from src.utils.identifiers import build_experiment_id, slugify_component

logger = logging.getLogger(__name__)

MONTH_NAMES_ID = [
    "", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
]


def format_indo_timestamp(ts):
    day = f"{ts.day:02d}"
    month = MONTH_NAMES_ID[ts.month]
    year = ts.year
    hour = f"{ts.hour:02d}"
    minute = f"{ts.minute:02d}"
    return f"{day} {month} {year}, {hour}:{minute} WIB"


def get_feature_display_info(feature_name, pollutant_unit):
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


def assess_air_quality(pollutant, value):
    if pollutant.lower() == "co":
        if value <= 4000:
            return AirQualityAssessment(
                category="Baik",
                color="#10b981",
                description="Tingkat mutu udara sangat baik, tidak memberikan dampak negatif terhadap manusia, hewan, dan tumbuhan.",
                standard="Baku Mutu ISPU / WHO 24-jam (4.000 µg/m³)",
            )
        elif value <= 8000:
            return AirQualityAssessment(
                category="Sedang",
                color="#f59e0b",
                description="Konsentrasi dapat diterima masyarakat umum, namun kelompok sensitif disarankan membatasi aktivitas fisik di luar ruangan.",
                standard="Baku Mutu ISPU Permen LHK",
            )
        elif value <= 15000:
            return AirQualityAssessment(
                category="Tidak Sehat",
                color="#ef4444",
                description="Tingkat kualitas udara mulai merugikan kesehatan pada populasi rentan (penderita penyakit kardiovaskular/pernapasan).",
                standard="Baku Mutu ISPU Permen LHK",
            )
        elif value <= 30000:
            return AirQualityAssessment(
                category="Sangat Tidak Sehat",
                color="#8b5cf6",
                description="Kualitas udara membahayakan kesehatan pada sejumlah segmen populasi. Hindari aktivitas luar ruangan yang berkepanjangan.",
                standard="Baku Mutu ISPU Permen LHK",
            )
        else:
            return AirQualityAssessment(
                category="Berbahaya",
                color="#b91c1c",
                description="Tingkat kualitas udara berbahaya secara umum bagi seluruh populasi dan berpotensi memicu masalah kesehatan serius.",
                standard="Baku Mutu ISPU Permen LHK",
            )
    else:
        if value <= 450:
            return AirQualityAssessment(
                category="Normal Ambien",
                color="#10b981",
                description="Konsentrasi Karbon Dioksida berada pada tingkat normal ambien troposfer bumi (~415 - 430 ppm).",
                standard="Baseline Global Troposfer Ambien",
            )
        elif value <= 600:
            return AirQualityAssessment(
                category="Terakumulasi Sedang",
                color="#f59e0b",
                description="Tingkat konsentrasi CO₂ sedikit terakumulasi akibat kepadatan aktivitas lalu lintas atau emisi lokal.",
                standard="Indikator Emisi Urban",
            )
        else:
            return AirQualityAssessment(
                category="Tinggi",
                color="#ef4444",
                description="Akumulasi gas CO₂ tinggi di lapisan permukaan akibat emisi kendaraan dan pembakaran bahan bakar padat.",
                standard="Indikator Emisi Urban",
            )


class PredictionService:
    def __init__(self):
        self.registry = registry_service
        self.data_service = data_service
        self.live_service = live_data_service
        self.supported_locations = {loc["id"]: loc for loc in settings.get_locations()}

    def predict_next_hour(self, request):
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
        if reference_time is not None:
            X_df, meta = self.data_service.build_next_hour_features(
                loc_slug,
                request.pollutant,
                request.scenario,
                reference_datetime=reference_time,
            )
        else:
            X_df, meta = self.live_service.build_live_features(
                loc_slug,
                request.pollutant,
                request.scenario,
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

        assessment = assess_air_quality(request.pollutant, pred_value)

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
            assessment=assessment,
            feature_inputs=feature_inputs,
            counterpart_algorithm=counterpart_algo,
            counterpart_label=counterpart_meta.get("label", counterpart_algo.upper()),
            counterpart_predicted_value=cp_pred_value,
            counterpart_delta=cp_delta,
            model_status=model_status,
            is_final_model=is_final,
            best_algorithm=best_algo,
            is_live_data=meta.get("is_live_data", False),
        )


prediction_service = PredictionService()
