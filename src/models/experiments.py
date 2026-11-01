import ast
import json
import logging
from datetime import datetime, timezone

import joblib
import pandas as pd

from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.models.estimators import create_estimator, predict, tune_on_training_set
from src.models.interpretation import calculate_tree_shap, gain_feature_importance, mean_absolute_shap
from src.utils.config import ARTIFACTS_DIR, DATA_DIR, EXPERIMENTS_DIR, load_yaml_config
from src.utils.identifiers import build_experiment_id, slugify_component
from src.utils.metrics import PerformanceTimer, calculate_regression_metrics

logger = logging.getLogger("experiments")

SUPPORTED_POLLUTANTS = {"co", "co2"}
SUPPORTED_SCENARIOS = {"scenario_1", "scenario_2"}
SUPPORTED_ALGORITHMS = {"xgboost", "lightgbm"}


class ExperimentSpec:
    """Four research dimensions identifying one model experiment."""

    def __init__(self, location, pollutant, scenario, algorithm):
        self.location = slugify_component(location)
        self.pollutant = pollutant.lower()
        self.scenario = scenario.lower()
        self.algorithm = algorithm.lower()
        self.experiment_id = build_experiment_id(self.location, self.pollutant, self.scenario, self.algorithm)
        self.artifact_directory = EXPERIMENTS_DIR / self.location / self.pollutant / self.scenario / self.algorithm

    def as_dict(self):
        return {
            "location": self.location,
            "pollutant": self.pollutant,
            "scenario": self.scenario,
            "algorithm": self.algorithm,
        }

    def __getitem__(self, item):
        return getattr(self, item)


def build_experiment_matrix():
    """Generate 120 experiment combinations (15 locations x 2 pollutants x 2 scenarios x 2 algorithms)."""
    locations = load_yaml_config("locations.yaml").get("locations", [])
    project = load_yaml_config("project.yaml")
    scenarios = load_yaml_config("features.yaml").get("scenarios", {})

    specs = []
    for loc in locations:
        loc_id = loc.get("id")
        if not loc_id:
            continue
        for pol in project.get("pollutants", {}):
            for scen in scenarios:
                for algo in project.get("algorithms", []):
                    specs.append(ExperimentSpec(loc_id, pol, scen, algo))
    return specs


def _get_coordinate_id(location_id):
    """Map location id to latitude_longitude string when matching raw observation rows."""
    locations = load_yaml_config("locations.yaml").get("locations", [])
    for loc in locations:
        if loc.get("id") == location_id:
            return f"{loc['latitude']}_{loc['longitude']}"
    return location_id


_DATASET_CACHE = {}


def _get_dataset(pollutant_file):
    """Load and cache processed datasets in memory to prevent repeated disk reads."""
    if pollutant_file not in _DATASET_CACHE:
        data_path = DATA_DIR / "processed" / pollutant_file
        if not data_path.exists():
            raise FileNotFoundError(f"Processed dataset not found: {data_path}")
        df = pd.read_csv(data_path)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Jakarta")
        _DATASET_CACHE[pollutant_file] = df
    return _DATASET_CACHE[pollutant_file]


def chronological_train_test_split(frame, test_fraction=0.2):
    """Split dataset chronologically without shuffling to preserve temporal causality."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    split_index = int(len(frame) * (1 - test_fraction))
    if split_index == 0 or split_index == len(frame):
        raise ValueError("Dataset is too small for the requested split")
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()


def execute_single_experiment(spec, artifact_dir=None):
    """Train, tune, evaluate, and persist all artifacts for a single experiment."""
    if artifact_dir is None:
        artifact_dir = spec.artifact_directory

    pollutant_file = "jabodetabek_co_dataset.csv" if spec.pollutant == "co" else "jabodetabek_co2_dataset.csv"
    df = _get_dataset(pollutant_file)

    coord_id = _get_coordinate_id(spec.location)
    df_loc = df[(df["location"] == coord_id) | (df["location"] == spec.location)].copy()
    if df_loc.empty:
        raise ValueError(f"No observation data found for location: {spec.location}")

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

    with PerformanceTimer() as timer:
        search = tune_on_training_set(base_estimator, spec.algorithm, x_train, y_train)

    best_model = search.best_estimator_
    best_params = search.best_params_
    training_time = timer.elapsed_seconds or 0.0

    pred_result = predict(best_model, x_test)
    metrics = calculate_regression_metrics(y_test, pred_result.values)
    metrics["training_time_seconds"] = training_time
    metrics["prediction_time_seconds"] = pred_result.prediction_time_seconds

    # Calculate model interpretability via TreeSHAP and gain importance.
    shap_values = calculate_tree_shap(best_model, x_test)
    df_shap_global = mean_absolute_shap(shap_values, feature_cols)
    df_gain = gain_feature_importance(best_model, feature_cols, normalize=True)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, artifact_dir / "model.joblib")

    with open(artifact_dir / "best_params.json", "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=2)

    with open(artifact_dir / "metrics.json", "w", encoding="utf-8") as f:
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

    metadata = {
        "spec": spec.as_dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "best_params": best_params,
        "features": feature_cols,
        "n_train_samples": len(train_df),
        "n_test_samples": len(test_df),
    }
    with open(artifact_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    with open(artifact_dir / "experiment_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


def run_experiments(specs=None, force=False):
    """Execute all research experiments sequentially, skipping previously completed runs."""
    if specs is None:
        specs = build_experiment_matrix()

    logger.info(f"Starting execution of {len(specs)} research experiments...")
    for idx, spec in enumerate(specs, start=1):
        metrics_file = spec.artifact_directory / "metrics.json"
        if not force and metrics_file.exists():
            logger.info(f"[{idx}/{len(specs)}] SKIPPED (already completed): {spec.experiment_id}")
            continue

        logger.info(f"[{idx}/{len(specs)}] RUNNING: {spec.experiment_id}")
        execute_single_experiment(spec)
        logger.info(f"[{idx}/{len(specs)}] FINISHED: {spec.experiment_id}")

    logger.info("Batch execution finished!")


class ExperimentRunner:
    """Compatibility runner preserved for external caller interfaces."""

    def __init__(self, registry=None):
        pass

    def run(self, spec, executor=None, force=False, **kwargs):
        return execute_single_experiment(spec)

    def run_many(self, specs, executor=None, force=False, **kwargs):
        return run_experiments(specs, force=force)


def select_best_models(
    summary_csv_path=None,
    registry_output_path=None,
    primary_metric="mae",
    secondary_metric="rmse",
):
    """Select the winning algorithm (lowest MAE then RMSE) for each location, pollutant, and scenario."""
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

    # Sort so that the lowest primary metric and secondary metric comes first.
    df_sorted = df.sort_values(
        by=["location_slug", "pollutant_lower", "scenario_lower", primary_metric, secondary_metric],
        ascending=[True, True, True, True, True],
    )

    best_df = df_sorted.groupby(["location_slug", "pollutant_lower", "scenario_lower"]).first().reset_index()

    total_expected = 15 * 2 * 2
    if len(best_df) != total_expected:
        raise ValueError(
            f"Expected {total_expected} best model combinations, but found {len(best_df)}. "
            "Please check summary_metrics.csv completeness."
        )

    best_registry = {
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
    with open(registry_output_path, "w", encoding="utf-8") as f:
        json.dump(best_registry, f, indent=2)

    return best_registry
