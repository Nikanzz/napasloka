"""Experiment matrix definition, registry state persistence, execution, and best model selection."""

import ast
import json
import logging
import os
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import joblib
import pandas as pd

from src.data.clean_data import chronological_train_test_split
from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.models.estimators import create_estimator, predict, tune_on_training_set
from src.models.interpretation import calculate_tree_shap, gain_feature_importance, mean_absolute_shap
from src.utils.config import ARTIFACTS_DIR, DATA_DIR, EXPERIMENTS_DIR, REGISTRY_DIR, load_yaml_config
from src.utils.identifiers import build_experiment_id, slugify_component
from src.utils.metrics import PerformanceTimer, calculate_regression_metrics

logger = logging.getLogger("experiments")

SUPPORTED_POLLUTANTS = {"co", "co2"}
SUPPORTED_SCENARIOS = {"scenario_1", "scenario_2"}
SUPPORTED_ALGORITHMS = {"xgboost", "lightgbm"}


# ==============================================================================
# 1. Experiment Specification & Matrix Builder
# ==============================================================================

@dataclass(frozen=True)
class ExperimentSpec:
    """Four dimensions that uniquely select one independent experiment."""

    location: str
    pollutant: str
    scenario: str
    algorithm: str

    def __post_init__(self) -> None:
        if self.pollutant not in SUPPORTED_POLLUTANTS:
            raise ValueError(f"Unsupported pollutant: {self.pollutant}")
        if self.scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario: {self.scenario}")
        if self.algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        slugify_component(self.location)

    @property
    def experiment_id(self) -> str:
        """Return the deterministic identifier used by logs and registry."""
        return build_experiment_id(
            self.location,
            self.pollutant,
            self.scenario,
            self.algorithm,
        )

    @property
    def artifact_directory(self) -> Path:
        """Return the required location/pollutant/scenario/algorithm path."""
        return EXPERIMENTS_DIR.joinpath(
            slugify_component(self.location),
            self.pollutant,
            self.scenario,
            self.algorithm,
        )

    def as_dict(self) -> dict[str, str]:
        """Serialize dimensions for metadata and registry records."""
        return asdict(self)


def build_experiment_matrix() -> list[ExperimentSpec]:
    """Expand configured locations across all research dimensions (15 loc x 2 pol x 2 scen x 2 algo = 120)."""
    locations = load_yaml_config("locations.yaml").get("locations", [])
    project = load_yaml_config("project.yaml")
    scenarios = load_yaml_config("features.yaml").get("scenarios", {})
    specs: list[ExperimentSpec] = []
    for location in locations:
        location_id = location.get("id")
        if not location_id:
            raise ValueError("Every configured location must have a non-empty id")
        for pollutant in project.get("pollutants", {}):
            for scenario in scenarios:
                for algorithm in project.get("algorithms", []):
                    specs.append(ExperimentSpec(location_id, pollutant, scenario, algorithm))
    return specs


# ==============================================================================
# 2. Experiment Registry & State Persistence
# ==============================================================================

class ExperimentStatus(StrEnum):
    """Allowed lifecycle states for one experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentRegistry:
    """Persist experiment progress after every independent model run."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or REGISTRY_DIR / "experiments.json"

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "experiments": {}}
        with self.path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data.get("experiments"), dict):
            raise ValueError(f"Invalid experiment registry: {self.path}")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            delete=False,
            suffix=".tmp",
        ) as temporary:
            json.dump(data, temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.path)

    def register(self, spec: ExperimentSpec) -> dict[str, Any]:
        """Create a pending record if the experiment is not registered."""
        data = self._read()
        records = data["experiments"]
        record = records.setdefault(
            spec.experiment_id,
            {
                "experiment_id": spec.experiment_id,
                "status": ExperimentStatus.PENDING,
                "spec": spec.as_dict(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._write(data)
        return record

    def update(
        self,
        spec: ExperimentSpec,
        status: ExperimentStatus,
        *,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Update an experiment record."""
        data = self._read()
        records = data["experiments"]
        record = records.setdefault(
            spec.experiment_id,
            {
                "experiment_id": spec.experiment_id,
                "spec": spec.as_dict(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        record["status"] = str(status)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        if error is not None:
            record["error"] = error
        elif "error" in record and status == ExperimentStatus.COMPLETED:
            record.pop("error", None)
        self._write(data)
        return record

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        """Return the current experiment record."""
        return self._read()["experiments"].get(experiment_id)

    def should_run(self, spec: ExperimentSpec, *, retry_failed: bool = False) -> bool:
        """Determine whether an experiment needs to be executed."""
        record = self.get(spec.experiment_id)
        if not record:
            return True
        status = record.get("status")
        if status == ExperimentStatus.COMPLETED:
            return False
        if status == ExperimentStatus.FAILED:
            return retry_failed
        return True


# ==============================================================================
# 3. Experiment Runner & Executor
# ==============================================================================

ExperimentExecutor = Callable[[ExperimentSpec, Path], dict[str, Any]]


class ExperimentRunner:
    """Run independent specs while persisting status after every model."""

    def __init__(self, registry: ExperimentRegistry | None = None) -> None:
        self.registry = registry or ExperimentRegistry()

    def run(
        self,
        spec: ExperimentSpec,
        executor: ExperimentExecutor,
        *,
        retry_failed: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Execute one experiment, or return its existing record when skipped."""
        self.registry.register(spec)
        if not force and not self.registry.should_run(spec, retry_failed=retry_failed):
            return self.registry.get(spec.experiment_id) or {}

        artifact_directory = spec.artifact_directory
        artifact_directory.mkdir(parents=True, exist_ok=True)
        self.registry.update(spec, ExperimentStatus.RUNNING)
        try:
            metadata = executor(spec, artifact_directory)
            _write_metadata(spec, artifact_directory, metadata)
        except Exception as exc:
            self.registry.update(spec, ExperimentStatus.FAILED, error=str(exc))
            raise
        return self.registry.update(spec, ExperimentStatus.COMPLETED)

    def run_many(
        self,
        specs: Iterable[ExperimentSpec],
        executor: ExperimentExecutor,
        *,
        retry_failed: bool = False,
    ) -> list[dict[str, Any]]:
        """Run specs sequentially so every completion is independently durable."""
        return [self.run(spec, executor, retry_failed=retry_failed) for spec in specs]


def _write_metadata(spec: ExperimentSpec, directory: Path, metadata: dict[str, Any]) -> None:
    path = directory / "metadata.json"
    payload = {
        "spec": spec.as_dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "details": metadata,
    }
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)


def _get_coordinate_id(location_id: str) -> str:
    """Map location id from config to coordinate string in dataset if needed."""
    locations = load_yaml_config("locations.yaml").get("locations", [])
    for loc in locations:
        if loc.get("id") == location_id:
            lat = loc["latitude"]
            lon = loc["longitude"]
            return f"{lat}_{lon}"
    return location_id


_DATASET_CACHE: dict[str, pd.DataFrame] = {}


def _get_dataset(pollutant_file: str) -> pd.DataFrame:
    """Cache loaded dataset in memory to avoid reading CSV 120 times."""
    if pollutant_file not in _DATASET_CACHE:
        data_path = DATA_DIR / "processed" / pollutant_file
        if not data_path.exists():
            raise FileNotFoundError(f"Processed dataset not found: {data_path}")
        df = pd.read_csv(data_path)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Jakarta")
        _DATASET_CACHE[pollutant_file] = df
    return _DATASET_CACHE[pollutant_file]


def execute_single_experiment(spec: ExperimentSpec, artifact_dir: Path) -> dict[str, Any]:
    """Execute one complete research experiment and persist all artifacts."""
    pollutant_file = "jabodetabek_co_dataset.csv" if spec.pollutant == "co" else "jabodetabek_co2_dataset.csv"
    df = _get_dataset(pollutant_file)

    coord_id = _get_coordinate_id(spec.location)
    df_loc = df[(df["location"] == coord_id) | (df["location"] == spec.location)].copy()
    if df_loc.empty:
        raise ValueError(f"No data found for location {spec.location} (coordinate: {coord_id})")

    df_loc = df_loc.sort_values("datetime").reset_index(drop=True)

    scenario_def = resolve_scenario(spec.pollutant, spec.scenario)
    df_features = create_lag_features(
        df_loc,
        pollutant=spec.pollutant,
        scenario=spec.scenario,
        drop_incomplete_rows=True,
    )

    feature_cols = list(scenario_def.feature_names)
    target_col = scenario_def.pollutant_column

    train_df, test_df = chronological_train_test_split(df_features, test_fraction=0.2)
    x_train = train_df[feature_cols]
    y_train = train_df[target_col]
    x_test = test_df[feature_cols]
    y_test = test_df[target_col]

    base_estimator = create_estimator(spec.algorithm, parameters={"random_state": 42})

    with PerformanceTimer() as train_timer:
        search = tune_on_training_set(base_estimator, spec.algorithm, x_train, y_train)

    training_time_seconds = train_timer.elapsed_seconds or 0.0
    best_model = search.best_estimator_
    best_params = search.best_params_

    pred_result = predict(best_model, x_test)
    metrics = calculate_regression_metrics(y_test, pred_result.values)
    metrics["training_time_seconds"] = training_time_seconds
    metrics["prediction_time_seconds"] = pred_result.prediction_time_seconds

    shap_values = calculate_tree_shap(best_model, x_test)
    df_shap_global = mean_absolute_shap(shap_values, feature_cols)
    df_gain = gain_feature_importance(best_model, feature_cols, normalize=True)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, artifact_dir / "model.joblib")

    with (artifact_dir / "best_params.json").open("w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2)

    with (artifact_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    predictions_df = pd.DataFrame({
        "datetime": test_df["datetime"].astype(str),
        "actual": y_test.values,
        "predicted": pred_result.values,
        "residual": y_test.values - pred_result.values,
    })
    predictions_df.to_csv(artifact_dir / "predictions.csv", index=False)
    df_shap_global.to_csv(artifact_dir / "shap_global.csv", index=False)
    df_gain.to_csv(artifact_dir / "feature_importance.csv", index=False)

    return {
        "metrics": metrics,
        "best_params": best_params,
        "features": feature_cols,
        "n_train_samples": len(train_df),
        "n_test_samples": len(test_df),
    }


# ==============================================================================
# 4. Best Model Registry Selection
# ==============================================================================

def select_best_models(
    summary_csv_path: Path | None = None,
    registry_output_path: Path | None = None,
    primary_metric: str = "mae",
    secondary_metric: str = "rmse",
) -> dict[str, Any]:
    """Determine the winning algorithm for each (location, pollutant, scenario) combination."""
    if summary_csv_path is None:
        summary_csv_path = ARTIFACTS_DIR / "summary_metrics.csv"
    if registry_output_path is None:
        registry_output_path = ARTIFACTS_DIR / "registry" / "best_models.json"

    if not summary_csv_path.exists():
        raise FileNotFoundError(f"Summary metrics CSV not found at: {summary_csv_path}")

    df = pd.read_csv(summary_csv_path)
    df["location_slug"] = df["location"].apply(slugify_component)
    df["pollutant_lower"] = df["pollutant"].str.lower()
    df["scenario_lower"] = df["scenario"].str.lower()
    df["algorithm_lower"] = df["algorithm"].str.lower()

    df_sorted = df.sort_values(
        by=["location_slug", "pollutant_lower", "scenario_lower", primary_metric, secondary_metric],
        ascending=[True, True, True, True, True],
    )

    best_df = df_sorted.groupby(["location_slug", "pollutant_lower", "scenario_lower"]).first().reset_index()

    total_expected = 15 * 2 * 2  # 60 combinations
    if len(best_df) != total_expected:
        raise ValueError(
            f"Expected {total_expected} best model combinations, but found {len(best_df)}. "
            "Please check summary_metrics.csv completeness."
        )

    best_registry: dict[str, Any] = {
        "version": 1,
        "selection_rule": f"lowest_{primary_metric}_then_{secondary_metric}",
        "total_combinations": len(best_df),
        "best_models": {},
    }

    for _, row in best_df.iterrows():
        loc = row["location_slug"]
        pol = row["pollutant_lower"]
        scen = row["scenario_lower"]
        algo = row["algorithm_lower"]

        key = f"{loc}__{pol}__{scen}"
        experiment_id = f"{loc}__{pol}__{scen}__{algo}"

        params_val = row.get("best_params", "{}")
        if isinstance(params_val, str):
            try:
                best_params = ast.literal_eval(params_val)
            except Exception:
                best_params = {}
        elif isinstance(params_val, dict):
            best_params = params_val
        else:
            best_params = {}

        best_registry["best_models"][key] = {
            "key": key,
            "location": loc,
            "pollutant": pol,
            "scenario": scen,
            "best_algorithm": algo,
            "experiment_id": experiment_id,
            "metrics": {
                "mae": round(float(row["mae"]), 4),
                "rmse": round(float(row["rmse"]), 4),
                "mape": round(float(row["mape"]), 4),
                "r2": round(float(row["r2"]), 4),
                "training_time_seconds": round(float(row["training_time_seconds"]), 4) if pd.notna(row.get("training_time_seconds")) else None,
                "prediction_time_seconds": round(float(row["prediction_time_seconds"]), 4) if pd.notna(row.get("prediction_time_seconds")) else None,
            },
            "best_params": best_params,
            "experiment_artifact_dir": f"artifacts/experiments/{loc}/{pol}/{scen}/{algo}",
            "final_model_dir": f"artifacts/final/{loc}/{pol}/{scen}",
        }

    registry_output_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_output_path.open("w", encoding="utf-8") as f:
        json.dump(best_registry, f, indent=2)

    return best_registry
