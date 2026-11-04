import json
import logging
import joblib
import pandas as pd

from backend.app.core.cache import model_cache, predictions_cache
from backend.app.core.config import (
    ALGORITHM_METADATA,
    LOCATION_REGIONS,
    POLLUTANT_METADATA,
    SCENARIO_METADATA,
    settings,
)
from backend.app.schemas.registry import (
    CounterpartModelInfo,
    ModelArtifactStatus,
    ModelDetailResponse,
    ModelMetrics,
)
from src.models.experiments import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_POLLUTANTS,
    SUPPORTED_SCENARIOS,
    build_experiment_matrix,
)
from src.models.train_model import select_best_models
from src.utils.identifiers import build_experiment_id, slugify_component

logger = logging.getLogger(__name__)


class RegistryService:
    def __init__(self):
        self.experiments_dir = settings.experiments_dir
        self.registry_dir = settings.registry_dir
        self.final_models_dir = settings.final_models_dir
        self.best_models_file = settings.best_models_file
        self.supported_locations = {loc["id"]: loc for loc in settings.get_locations()}
        self._best_models_cache = None

    def validate_dimensions(self, location, pollutant, scenario, algorithm):
        loc_slug = slugify_component(location)
        if loc_slug not in self.supported_locations:
            valid_locs = ", ".join(self.supported_locations.keys())
            raise ValueError(f"Unknown location '{location}'. Valid locations are: {valid_locs}")
        if pollutant not in SUPPORTED_POLLUTANTS:
            raise ValueError(f"Unknown pollutant '{pollutant}'. Valid pollutants are: {SUPPORTED_POLLUTANTS}")
        if scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'. Valid scenarios are: {SUPPORTED_SCENARIOS}")
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{algorithm}'. Valid algorithms are: {SUPPORTED_ALGORITHMS}")

    def get_artifact_directory(self, location, pollutant, scenario, algorithm):
        self.validate_dimensions(location, pollutant, scenario, algorithm)
        return self.experiments_dir.joinpath(
            slugify_component(location),
            pollutant,
            scenario,
            algorithm,
        )

    def get_artifact_status(self, location, pollutant, scenario, algorithm):
        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        has_model = (dir_path / "model.joblib").is_file()
        has_metrics = (dir_path / "metrics.json").is_file()
        has_predictions = (dir_path / "predictions.csv").is_file()
        has_fi = (dir_path / "feature_importance.csv").is_file()
        has_shap = (dir_path / "shap_global.csv").is_file()
        has_meta = (dir_path / "experiment_metadata.json").is_file()

        is_ready = all([has_model, has_metrics, has_predictions, has_fi, has_meta])

        return ModelArtifactStatus(
            model_joblib=has_model,
            metrics_json=has_metrics,
            predictions_csv=has_predictions,
            feature_importance_csv=has_fi,
            shap_global_csv=has_shap,
            experiment_metadata_json=has_meta,
            is_ready=is_ready,
        )

    def get_metadata(self, location, pollutant, scenario, algorithm):
        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        metadata_file = dir_path / "experiment_metadata.json"
        if not metadata_file.is_file():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_metrics(self, location, pollutant, scenario, algorithm):
        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        metrics_file = dir_path / "metrics.json"
        if not metrics_file.is_file():
            raise FileNotFoundError(f"Metrics file not found: {metrics_file}")
        with open(metrics_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ModelMetrics(
                mae=float(data["mae"]),
                rmse=float(data["rmse"]),
                mape=float(data["mape"]),
                r2=float(data["r2"]),
                training_time_seconds=data.get("training_time_seconds"),
                prediction_time_seconds=data.get("prediction_time_seconds"),
            )

    def get_counterpart_algorithm(self, algorithm):
        return "lightgbm" if algorithm == "xgboost" else "xgboost"

    def get_counterpart_info(self, location, pollutant, scenario, algorithm):
        counterpart_algo = self.get_counterpart_algorithm(algorithm)
        try:
            status = self.get_artifact_status(location, pollutant, scenario, counterpart_algo)
            if not status.is_ready:
                return None
            metrics = self.get_metrics(location, pollutant, scenario, counterpart_algo)
            counterpart_id = build_experiment_id(location, pollutant, scenario, counterpart_algo)
            algo_meta = ALGORITHM_METADATA.get(counterpart_algo, {})
            return CounterpartModelInfo(
                algorithm=counterpart_algo,
                algorithm_label=algo_meta.get("label", counterpart_algo.upper()),
                experiment_id=counterpart_id,
                metrics=metrics,
                is_available=True,
            )
        except Exception as e:
            logger.warning("Failed to load counterpart info for %s: %s", algorithm, e)
            return None

    def get_model_details(self, location, pollutant, scenario, algorithm):
        self.validate_dimensions(location, pollutant, scenario, algorithm)
        loc_slug = slugify_component(location)
        loc_info = self.supported_locations[loc_slug]
        pollutant_info = POLLUTANT_METADATA[pollutant]
        scenario_info = SCENARIO_METADATA[scenario]
        algorithm_info = ALGORITHM_METADATA[algorithm]

        metadata = self.get_metadata(location, pollutant, scenario, algorithm)
        metrics = self.get_metrics(location, pollutant, scenario, algorithm)
        artifact_status = self.get_artifact_status(location, pollutant, scenario, algorithm)
        counterpart = self.get_counterpart_info(location, pollutant, scenario, algorithm)

        experiment_id = build_experiment_id(location, pollutant, scenario, algorithm)

        return ModelDetailResponse(
            experiment_id=experiment_id,
            location=loc_slug,
            location_name=loc_info["name"],
            region=LOCATION_REGIONS.get(loc_slug, "Jabodetabek"),
            pollutant=pollutant,
            pollutant_label=pollutant_info["label"],
            pollutant_unit=pollutant_info["unit"],
            scenario=scenario,
            scenario_label=scenario_info["label"],
            algorithm=algorithm,
            algorithm_label=algorithm_info["label"],
            features=metadata.get("features", []),
            best_params=metadata.get("best_params", {}),
            metrics=metrics,
            counterpart=counterpart,
            artifact_status=artifact_status,
        )

    def load_estimator(self, location, pollutant, scenario, algorithm):
        cache_key = build_experiment_id(location, pollutant, scenario, algorithm)
        cached_model = model_cache.get(cache_key)
        if cached_model is not None:
            return cached_model

        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        model_path = dir_path / "model.joblib"
        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found at: {model_path}")

        estimator = joblib.load(model_path)
        model_cache.set(cache_key, estimator)
        return estimator

    def load_test_predictions(self, location, pollutant, scenario, algorithm):
        cache_key = f"pred__{build_experiment_id(location, pollutant, scenario, algorithm)}"
        cached_df = predictions_cache.get(cache_key)
        if cached_df is not None:
            return cached_df

        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        pred_path = dir_path / "predictions.csv"
        if not pred_path.is_file():
            raise FileNotFoundError(f"Predictions file not found at: {pred_path}")

        df = pd.read_csv(pred_path)
        df["datetime"] = pd.to_datetime(df["datetime"])
        predictions_cache.set(cache_key, df)
        return df

    def get_feature_importance(self, location, pollutant, scenario, algorithm):
        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        fi_path = dir_path / "feature_importance.csv"
        if not fi_path.is_file():
            raise FileNotFoundError(f"Feature importance file not found at: {fi_path}")

        df = pd.read_csv(fi_path)
        return df.to_dict(orient="records")

    def get_global_shap(self, location, pollutant, scenario, algorithm):
        dir_path = self.get_artifact_directory(location, pollutant, scenario, algorithm)
        shap_path = dir_path / "shap_global.csv"
        if not shap_path.is_file():
            raise FileNotFoundError(f"Global SHAP file not found at: {shap_path}")

        df = pd.read_csv(shap_path)
        return df.to_dict(orient="records")

    def get_all_models_summary(self):
        matrix = build_experiment_matrix()
        total = len(matrix)
        ready_count = 0
        models_list = []

        for spec in matrix:
            status = self.get_artifact_status(
                spec["location"],
                spec["pollutant"],
                spec["scenario"],
                spec["algorithm"],
            )
            if status.is_ready:
                ready_count += 1

            models_list.append({
                "experiment_id": spec["experiment_id"],
                "location": spec["location"],
                "pollutant": spec["pollutant"],
                "scenario": spec["scenario"],
                "algorithm": spec["algorithm"],
                "is_ready": status.is_ready,
                "artifacts": status.model_dump(),
            })

        return {
            "total_experiments": total,
            "completed_experiments": ready_count,
            "ready_ratio": round((ready_count / total) * 100, 2) if total > 0 else 0.0,
            "locations_count": len(self.supported_locations),
            "pollutants": list(SUPPORTED_POLLUTANTS),
            "scenarios": list(SUPPORTED_SCENARIOS),
            "algorithms": list(SUPPORTED_ALGORITHMS),
            "models": models_list,
        }

    # Best Models Section
    def load_best_models_registry(self, force_reload=False):
        if self._best_models_cache is not None and not force_reload:
            return self._best_models_cache

        if not self.best_models_file.is_file():
            from src.models.train_model import select_best_models
            registry_data = select_best_models(
                registry_output_path=self.best_models_file,
                primary_metric="mae",
            )
            self._best_models_cache = registry_data
            return registry_data

        with open(self.best_models_file, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
            self._best_models_cache = registry_data
            return registry_data

    def get_best_model(self, location, pollutant, scenario):
        loc_slug = slugify_component(location)
        if loc_slug not in self.supported_locations:
            valid_locs = ", ".join(self.supported_locations.keys())
            raise ValueError(f"Unknown location '{location}'. Valid locations are: {valid_locs}")
        if pollutant.lower() not in SUPPORTED_POLLUTANTS:
            raise ValueError(f"Unknown pollutant '{pollutant}'. Valid pollutants are: {SUPPORTED_POLLUTANTS}")
        if scenario.lower() not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'. Valid scenarios are: {SUPPORTED_SCENARIOS}")

        registry = self.load_best_models_registry()
        key = f"{loc_slug}__{pollutant.lower()}__{scenario.lower()}"
        best_models = registry.get("best_models", {})
        if key not in best_models:
            raise KeyError(f"No best model registered for combination: {key}")
        return best_models[key]

    def get_all_best_models(self):
        return self.load_best_models_registry()

    def get_final_artifact_directory(self, location, pollutant, scenario):
        loc_slug = slugify_component(location)
        return self.final_models_dir.joinpath(loc_slug, pollutant.lower(), scenario.lower())

    def load_final_estimator(self, location, pollutant, scenario):
        loc_slug = slugify_component(location)
        cache_key = f"final__{loc_slug}__{pollutant.lower()}__{scenario.lower()}"
        cached = model_cache.get(cache_key)
        if cached is not None:
            return cached

        final_dir = self.get_final_artifact_directory(loc_slug, pollutant, scenario)
        final_model_path = final_dir / "model.joblib"

        if final_model_path.is_file():
            estimator = joblib.load(final_model_path)
            model_cache.set(cache_key, estimator)
            return estimator

        best_entry = self.get_best_model(location, pollutant, scenario)
        return self.load_estimator(
            location,
            pollutant,
            scenario,
            best_entry["best_algorithm"],
        )

    def get_final_metadata(self, location, pollutant, scenario):
        final_dir = self.get_final_artifact_directory(location, pollutant, scenario)
        meta_file = final_dir / "final_metadata.json"
        if meta_file.is_file():
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return self.get_best_model(location, pollutant, scenario)

    def get_final_feature_importance(self, location, pollutant, scenario):
        final_dir = self.get_final_artifact_directory(location, pollutant, scenario)
        fi_path = final_dir / "feature_importance.csv"
        if fi_path.is_file():
            df = pd.read_csv(fi_path)
            return df.to_dict(orient="records")

        best_entry = self.get_best_model(location, pollutant, scenario)
        return self.get_feature_importance(location, pollutant, scenario, best_entry["best_algorithm"])

    def get_final_global_shap(self, location, pollutant, scenario):
        final_dir = self.get_final_artifact_directory(location, pollutant, scenario)
        shap_path = final_dir / "shap_global.csv"
        if shap_path.is_file():
            df = pd.read_csv(shap_path)
            return df.to_dict(orient="records")

        best_entry = self.get_best_model(location, pollutant, scenario)
        return self.get_global_shap(location, pollutant, scenario, best_entry["best_algorithm"])


registry_service = RegistryService()
