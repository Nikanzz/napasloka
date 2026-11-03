import ast
import datetime
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.models.estimators import create_estimator
from src.models.experiments import (
    _get_coordinate_id,
    get_dataset,
    run_experiments,
)
from src.models.interpretation import (
    calculate_tree_shap,
    gain_feature_importance,
    mean_absolute_shap,
)
from src.utils.identifiers import slugify_component
from src.utils.config import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_model")

# Configuration for training mode and retraining behavior (final vs experiment)
MODE = "final"          
FORCE_RETRAIN = False   

# ==============================================================================
# Final Model Retraining Functions
# ==============================================================================

def retrain_single_final_model(
    entry,
    final_dir,
    force=False,
    compute_shap_samples=500,
):
    """Train a single final deployment model using optimal hyperparameters."""
    loc = entry["location"]
    pol = entry["pollutant"]
    scen = entry["scenario"]
    algo = entry["best_algorithm"]
    best_params = entry["best_params"]
    exp_metrics = entry["metrics"]

    model_dest = final_dir / "model.joblib"
    meta_dest = final_dir / "final_metadata.json"

    # Skip retraining if model artifact already exists
    if not force and model_dest.is_file() and meta_dest.is_file():
        logger.info(f"Final model already exists for {loc}/{pol}/{scen} -> SKIPPED (use FORCE_RETRAIN=True to overwrite)")
        with meta_dest.open("r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Retraining final deployment model: {loc} | {pol.upper()} | {scen} | {algo.upper()}")

    pollutant_file = "jabodetabek_co_dataset.csv" if pol == "co" else "jabodetabek_co2_dataset.csv"
    df = get_dataset(pollutant_file)
    coord_id = _get_coordinate_id(loc)

    df_loc = df[(df["location"] == coord_id) | (df["location"] == loc)].copy()
    if df_loc.empty:
        raise ValueError(f"No observation data for location: {loc} (coordinate: {coord_id})")

    df_loc = df_loc.sort_values("datetime").reset_index(drop=True)

    df_features = create_lag_features(
        df_loc,
        pollutant=pol,
        scenario=scen,
        drop_incomplete_rows=True,
    )

    scenario_def = resolve_scenario(pol, scen)
    feature_cols = list(scenario_def.feature_names)
    target_col = scenario_def.pollutant_column

    # Final deployment models utilize the complete historical dataset
    x_train = df_features[feature_cols]
    y_train = df_features[target_col]
    train_samples_count = len(df_features)
    shap_sample = df_features[feature_cols].tail(compute_shap_samples)

    estimator = create_estimator(algo, parameters=best_params)

    start_train = time.time()
    estimator.fit(x_train, y_train)
    retrain_duration = time.time() - start_train

    df_gain = gain_feature_importance(estimator, feature_cols, normalize=True)
    shap_vals = calculate_tree_shap(estimator, shap_sample)
    df_shap_global = mean_absolute_shap(shap_vals, feature_cols)

    final_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, model_dest)

    df_gain.to_csv(final_dir / "feature_importance.csv", index=False)
    df_shap_global.to_csv(final_dir / "shap_global.csv", index=False)

    data_start_iso = df_features["datetime"].min().isoformat()
    data_end_iso = df_features["datetime"].max().isoformat()

    metadata = {
        "model_name": "Sistem NapasLoka Final Deployment Model",
        "model_status": "final_deployment",
        "model_version": "1.0.0",
        "creation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "location": loc,
        "pollutant": pol,
        "scenario": scen,
        "algorithm": algo,
        "best_params": best_params,
        "target_variable": target_col,
        "features": feature_cols,
        "n_features": len(feature_cols),
        "n_train_samples": train_samples_count,
        "training_data_type": "full_historical_dataset",
        "data_start": data_start_iso,
        "data_end": data_end_iso,
        "training_time_seconds": round(retrain_duration, 4),
        "experiment_id": entry["experiment_id"],
        "experiment_metrics": exp_metrics,
        "selection_rule": "lowest_mae_then_rmse",
        "academic_note": (
            "Model final ini dilatih menggunakan 100% data historis yang tersedia (hingga cutoff deployment) khusus untuk kebutuhan prediksi operasional aplikasi. "
            "Evaluasi komparatif skripsi (MAE/RMSE/MAPE/R2) tetap dibekukan dari model eksperimen hold-out 80:20."
        ),
    }

    with open(meta_dest, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved final deployment model and metadata to: {final_dir}")
    return metadata


def select_best_models(
    summary_csv_path=None,
    registry_output_path=None,
    primary_metric="mae",
    secondary_metric="rmse",
):
    """Select the best-performing algorithm for each location, pollutant, and scenario combination."""
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

    # Sort so that the lowest primary and secondary metrics appear first.
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


def retrain_final_models(
    location=None,
    pollutant=None,
    scenario=None,
    force=False,
    primary_metric="mae",
):
    """Execute retraining for all selected best models."""
    logger.info("Generating/verifying Best Model Registry from summary_metrics.csv...")
    registry_file = ARTIFACTS_DIR / "registry" / "best_models.json"
    registry = select_best_models(
        summary_csv_path=ARTIFACTS_DIR / "summary_metrics.csv",
        registry_output_path=registry_file,
        primary_metric=primary_metric,
    )
    logger.info(f"Best Model Registry ready with {registry['total_combinations']} combinations at: {registry_file}")

    best_models = registry["best_models"]
    to_retrain = []

    for key, entry in best_models.items():
        if location and entry["location"] != slugify_component(location):
            continue
        if pollutant and entry["pollutant"] != pollutant.lower():
            continue
        if scenario and entry["scenario"] != scenario.lower():
            continue
        to_retrain.append(entry)

    if not to_retrain:
        logger.warning("No model combinations matched the requested filter.")
        return

    logger.info(f"Starting retraining of {len(to_retrain)} final deployment models...")
    start_total = time.time()
    completed = 0

    for idx, entry in enumerate(to_retrain, start=1):
        loc = entry["location"]
        pol = entry["pollutant"]
        scen = entry["scenario"]
        final_dir = ARTIFACTS_DIR / "final" / loc / pol / scen

        logger.info(f"[{idx}/{len(to_retrain)}] Processing {entry['key']}...")
        retrain_single_final_model(
            entry,
            final_dir,
            force=force,
        )
        completed += 1

    total_elapsed = time.time() - start_total
    logger.info(f"Finished retraining {completed} final models in {total_elapsed:.2f} seconds!")


# ==============================================================================
# Research Experiment Training Functions
# ==============================================================================

def train_experiments(force=False, retry_failed=False):
    """Execute the full 120-experiment research matrix."""
    run_experiments(force=force)


# ==============================================================================
# Execution Entry Point
# ==============================================================================

def main():
    """Run model training directly based on configuration settings above."""
    if MODE == "final":
        retrain_final_models(force=FORCE_RETRAIN)
    elif MODE == "experiment":
        train_experiments(force=FORCE_RETRAIN)


if __name__ == "__main__":
    main()
