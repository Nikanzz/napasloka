"""Core configuration and metadata definitions for NapasLoka backend."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.config import load_yaml_config
from src.utils.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR, EXPERIMENTS_DIR, PROJECT_ROOT, REGISTRY_DIR


# Administrative region mapping for the 15 Jabodetabek observation points
LOCATION_REGIONS: dict[str, str] = {
    "taman-kamal": "Jakarta Barat",
    "pelabuhan-muara-baru": "Jakarta Utara",
    "daerah-pelabuhan-tanjung-priuk": "Jakarta Utara",
    "petamburan-perkantoran-transjakarta": "Jakarta Pusat",
    "smpn-92-jakarta-timur": "Jakarta Timur",
    "perumahan-dekat-tol-depok-antasari": "Jakarta Selatan",
    "tmii": "Jakarta Timur",
    "metland-cyberpuri": "Kota Tangerang",
    "tol-serpong-interchange": "Kota Tangerang Selatan",
    "pancoran-mas": "Kota Depok",
    "jl-tol-jagorawi": "Kota Depok",
    "pantai-makmur": "Kabupaten Bekasi",
    "kaliabang-tengah": "Kota Bekasi",
    "mustikasari": "Kota Bekasi",
    "cibinong": "Kabupaten Bogor",
}

POLLUTANT_METADATA: dict[str, dict[str, Any]] = {
    "co": {
        "id": "co",
        "name": "Karbon Monoksida",
        "symbol": "CO",
        "unit": "µg/m³",
        "column": "carbon_monoxide",
        "label": "Karbon Monoksida (CO)",
        "description": "Gas polutan tidak berwarna dan tidak berbau yang dihasilkan dari pembakaran tidak sempurna bahan bakar fosil.",
        "who_guideline": "4.000 µg/m³ (rata-rata 24 jam)",
    },
    "co2": {
        "id": "co2",
        "name": "Karbon Dioksida",
        "symbol": "CO₂",
        "unit": "ppm",
        "column": "carbon_dioxide",
        "label": "Karbon Dioksida (CO₂)",
        "description": "Gas rumah kaca utama di atmosfer bumi yang berkontribusi terhadap perubahan iklim dan pemanasan global.",
        "baseline_ambient": "~420 ppm (rata-rata global troposfer)",
    },
}

SCENARIO_METADATA: dict[str, dict[str, Any]] = {
    "scenario_1": {
        "id": "scenario_1",
        "label": "Skenario 1 (Lag Polutan)",
        "short_label": "Skenario 1",
        "description": "Menggunakan 3 fitur autoregresif historis konsentrasi polutan pada lag t-1, t-2, dan t-3.",
        "feature_count": 3,
        "features": ["lag_1h", "lag_2h", "lag_3h"],
    },
    "scenario_2": {
        "id": "scenario_2",
        "label": "Skenario 2 (Lag Polutan + Meteorologi)",
        "short_label": "Skenario 2",
        "description": "Menggunakan 15 fitur: 3 lag polutan ditambah 3 lag untuk masing-masing variabel meteorologi (temperatur, kelembaban relatif, curah hujan, dan kecepatan angin).",
        "feature_count": 15,
        "features": [
            "pollutant_lag_1h", "pollutant_lag_2h", "pollutant_lag_3h",
            "temperature_lag_1h", "temperature_lag_2h", "temperature_lag_3h",
            "humidity_lag_1h", "humidity_lag_2h", "humidity_lag_3h",
            "rain_lag_1h", "rain_lag_2h", "rain_lag_3h",
            "wind_speed_lag_1h", "wind_speed_lag_2h", "wind_speed_lag_3h",
        ],
    },
}

ALGORITHM_METADATA: dict[str, dict[str, Any]] = {
    "xgboost": {
        "id": "xgboost",
        "name": "XGBoost",
        "label": "XGBoost (eXtreme Gradient Boosting)",
        "description": "Algoritma gradient boosting berbasis pohon keputusan yang efisien, fleksibel, dan menggunakan regularisasi L1/L2.",
    },
    "lightgbm": {
        "id": "lightgbm",
        "name": "LightGBM",
        "label": "LightGBM (Light Gradient Boosting Machine)",
        "description": "Framework gradient boosting berbasis tree dengan teknik Leaf-wise split dan Histogram-based binning untuk pelatihan cepat dan efisien.",
    },
}


@dataclass
class Settings:
    """Application runtime settings and path references."""

    app_name: str = "Sistem NapasLoka"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    project_root: Path = PROJECT_ROOT
    config_dir: Path = CONFIG_DIR
    data_dir: Path = DATA_DIR
    processed_data_dir: Path = DATA_DIR / "processed"
    artifacts_dir: Path = ARTIFACTS_DIR
    experiments_dir: Path = EXPERIMENTS_DIR
    registry_dir: Path = REGISTRY_DIR
    final_models_dir: Path = ARTIFACTS_DIR / "final"
    best_models_file: Path = REGISTRY_DIR / "best_models.json"

    allowed_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ])

    default_test_start: str = "2026-03-28T11:00:00+07:00"
    default_test_end: str = "2026-08-04T23:00:00+07:00"

    def get_locations(self) -> list[dict[str, Any]]:
        """Return enriched list of configured Jabodetabek monitoring locations."""
        raw_locations = load_yaml_config("locations.yaml").get("locations", [])
        enriched = []
        for loc in raw_locations:
            loc_id = loc["id"]
            enriched.append({
                "id": loc_id,
                "name": loc["name"],
                "region": LOCATION_REGIONS.get(loc_id, "Jabodetabek"),
                "latitude": float(loc["latitude"]),
                "longitude": float(loc["longitude"]),
            })
        return enriched

    def get_pollutants(self) -> list[dict[str, Any]]:
        """Return supported pollutants with units and descriptions."""
        return list(POLLUTANT_METADATA.values())

    def get_scenarios(self) -> list[dict[str, Any]]:
        """Return supported modeling scenarios."""
        return list(SCENARIO_METADATA.values())

    def get_algorithms(self) -> list[dict[str, Any]]:
        """Return supported machine learning algorithms."""
        return list(ALGORITHM_METADATA.values())


settings = Settings()
