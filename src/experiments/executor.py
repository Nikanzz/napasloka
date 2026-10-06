"""Generic execution of one research experiment and artifact persistence."""

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.data.preprocessing import chronological_train_test_split
from src.evaluation.metrics import calculate_regression_metrics
from src.evaluation.timing import PerformanceTimer
from src.experiments.experiment import ExperimentSpec
from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.interpretation.feature_importance import gain_feature_importance
from src.interpretation.shap_analysis import calculate_tree_shap, mean_absolute_shap
from src.modeling.prediction import predict
from src.modeling.training import create_estimator
from src.modeling.tuning import tune_on_training_set
from src.utils.config import load_yaml_config
from src.utils.paths import DATA_DIR


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

    # Feature engineering
    scenario_def = resolve_scenario(spec.pollutant, spec.scenario)
    df_features = create_lag_features(
        df_loc,
        pollutant=spec.pollutant,
        scenario=spec.scenario,
        drop_incomplete_rows=True,
    )

    feature_cols = list(scenario_def.feature_names)
    target_col = scenario_def.pollutant_column

    # Train-test split
    train_df, test_df = chronological_train_test_split(df_features, test_fraction=0.2)

    x_train = train_df[feature_cols]
    y_train = train_df[target_col]
    x_test = test_df[feature_cols]
    y_test = test_df[target_col]

    # Hyperparameter tuning
    base_estimator = create_estimator(spec.algorithm, parameters={"random_state": 42})

    with PerformanceTimer() as train_timer:
        search = tune_on_training_set(base_estimator, spec.algorithm, x_train, y_train)

    training_time_seconds = train_timer.elapsed_seconds or 0.0
    best_model = search.best_estimator_
    best_params = search.best_params_

    # Evaluation
    pred_result = predict(best_model, x_test)
    metrics = calculate_regression_metrics(y_test, pred_result.values)
    metrics["training_time_seconds"] = training_time_seconds
    metrics["prediction_time_seconds"] = pred_result.prediction_time_seconds

    # Interpretation
    shap_values = calculate_tree_shap(best_model, x_test)
    df_shap_global = mean_absolute_shap(shap_values, feature_cols)

    # Feature importance (Gain-based)
    df_gain = gain_feature_importance(best_model, feature_cols, normalize=True)

    # Save artifacts
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
